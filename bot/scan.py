"""Check Google Flights prices, save them to data/prices.csv and DM alerts.

Modes:
  full  - every date pair in the window (cheapest-week hunt)
  focus - planned dates + current cheapest pair (hourly, for the best-time-to-buy study)
  auto  - full if the last full scan is >= full_scan_every_hours old, else focus
"""
import argparse
import csv
import os
import random
import sys
import time
from datetime import date, datetime, timedelta, timezone

from common import (DATA, LAST_RUN_JSON, PRICE_FIELDS, PRICES_CSV, SGT, STATE_JSON,
                    date_pairs, fx_to_sgd, gf_link, load_config, load_json, nice_date,
                    parse_price, pax, save_json, send_message)


_PATCHED = False


def _patch_primp():
    """fast-flights asks primp for the browser profile "chrome_126", which newer primp
    versions removed. Wrap primp.Client so it falls back to a profile that exists."""
    global _PATCHED
    if _PATCHED:
        return
    import primp
    import fast_flights
    real = primp.Client
    fallbacks = ["chrome_133", "chrome_131", "chrome_130", "chrome_128", "chrome_127",
                 "chrome_126", "chrome", "random", None]

    good = {}

    def client(*a, **kw):
        want = kw.get("impersonate")
        order = [want] + [f for f in fallbacks if f != want]
        if "imp" in good:
            order.insert(0, good["imp"])
        for imp in order:
            try:
                if imp is None:
                    kw.pop("impersonate", None)
                else:
                    kw["impersonate"] = imp
                c = real(*a, **kw)
                good["imp"] = imp
                if imp != want:
                    print(f"  (using browser profile {imp!r} instead of {want!r})")
                return c
            except Exception as e:
                if "impersonate" not in str(e).lower():
                    raise
        raise RuntimeError("no usable primp browser profile")

    import importlib
    import pkgutil
    import sys as _sys
    for info in pkgutil.walk_packages(fast_flights.__path__, "fast_flights."):
        try:
            importlib.import_module(info.name)
        except Exception:
            pass
    for name, mod in list(_sys.modules.items()):
        if name.startswith("fast_flights") and mod is not None:
            for attr, val in list(vars(mod).items()):
                if val is real:
                    setattr(mod, attr, client)
    primp.Client = client
    _PATCHED = True


def search(cfg, depart, ret):
    from fast_flights import FlightData, Passengers, get_flights
    _patch_primp()
    last_err = None
    # "fallback" (a remote browser service) now blocks bots, so retry the direct fetch.
    errs = []
    for attempt in range(2):
        mode = "common"
        try:
            res = get_flights(
                flight_data=[
                    FlightData(date=depart, from_airport=cfg["origin"], to_airport=cfg["destination"]),
                    FlightData(date=ret, from_airport=cfg["destination"], to_airport=cfg["origin"]),
                ],
                trip="round-trip",
                seat=cfg["seat"],
                passengers=Passengers(adults=cfg["adults"], children=cfg["children"],
                                      infants_in_seat=0, infants_on_lap=0),
                fetch_mode=mode,
            )
            if res and res.flights:
                return res
            last_err = "no flights returned"
        except Exception as e:
            last_err = f"{type(e).__name__}: {str(e)[:200]}"
        errs.append(last_err)
        print(f"  {depart}: try {attempt + 1} failed -> {last_err}")
        time.sleep(random.uniform(5, 12))
    raise RuntimeError(" | ".join(dict.fromkeys(errs)))


def read_history():
    if not os.path.exists(PRICES_CSV):
        return []
    with open(PRICES_CSV, newline="") as f:
        return list(csv.DictReader(f))


def append_rows(rows):
    os.makedirs(DATA, exist_ok=True)
    new = not os.path.exists(PRICES_CSV)
    with open(PRICES_CSV, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=PRICE_FIELDS)
        if new:
            w.writeheader()
        w.writerows(rows)


def check_alerts(cfg, state, history, best_now, now_utc):
    """Alert only on real lows (see README). best_now: {depart: row}."""
    alerts = []
    alerted = state.setdefault("alerted", {})
    cutoff = (now_utc - timedelta(days=30)).isoformat()
    target = cfg.get("target_price_per_person_sgd")
    focus = set(cfg.get("focus_departures", []))
    r1 = [h for h in history if h["rank"] == "1" and h.get("price_per_person_sgd")]
    days_of_history = len({h["checked_at_sgt"][:10] for h in r1})
    enough = days_of_history >= cfg.get("min_history_days", 3)
    overall_low_before = min((float(h["price_per_person_sgd"]) for h in r1), default=None)
    cheapest_now = min(best_now, key=lambda d: float(best_now[d]["price_per_person_sgd"]))

    for depart, row in sorted(best_now.items(), key=lambda kv: float(kv[1]["price_per_person_sgd"])):
        pp = float(row["price_per_person_sgd"])
        past = [float(h["price_per_person_sgd"]) for h in r1 if h["depart"] == depart]
        past30 = [float(h["price_per_person_sgd"]) for h in r1
                  if h["depart"] == depart and h["checked_at_utc"] >= cutoff]
        drop = cfg["new_low_min_drop_pct"] / 100
        reasons = []
        if target and pp <= float(target):
            reasons.append(f"🎯 Under your target of S${float(target):,.0f}/person")
        if enough and depart == cheapest_now and overall_low_before and pp < overall_low_before * (1 - drop):
            reasons.append(f"🏆 Cheapest price of ANY week so far (before: S${overall_low_before:,.0f}/person)")
        if enough and depart in focus and past and pp < min(past) * (1 - drop):
            reasons.append(f"📉 Lowest price yet for your planned dates (before: S${min(past):,.0f}/person)")
        if enough and len(past30) >= 8:
            avg = sum(past30) / len(past30)
            pct = (1 - pp / avg) * 100
            if pct >= cfg["drop_vs_30d_avg_pct"]:
                reasons.append(f"🔥 {pct:.0f}% below this week's 30-day average (S${avg:,.0f}/person)")

        last = alerted.get(depart)
        if last and pp > last * 1.10:  # price went back up: allow a fresh alert next drop
            alerted.pop(depart, None)
            last = None
        if not reasons:
            continue
        if last and pp > last * (1 - cfg["realert_min_drop_pct"] / 100):
            continue  # already told you about this price
        alerted[depart] = pp
        alerts.append(
            f"✈️ <b>{nice_date(row['depart'])} → {nice_date(row['return'])}</b>\n"
            f"💰 <b>S${pp:,.0f}/person</b> · S${float(row['price_total_sgd']):,.0f} return for all {pax(cfg)}\n"
            f"🛫 {row['airline']} · departs {row['out_departure'].split(' on ')[0]} · {row['stops_text']}\n"
            + "\n".join(reasons) +
            f"\n🔗 <a href=\"{gf_link(cfg, row['depart'], row['return'])}\">Open this search on Google Flights</a>"
        )
    return alerts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", default="auto", choices=["auto", "full", "focus"])
    ap.add_argument("--no-telegram", action="store_true")
    args = ap.parse_args()

    cfg = load_config()
    state = load_json(STATE_JSON, {})
    now_utc = datetime.now(timezone.utc).replace(microsecond=0)
    now_sgt = now_utc.astimezone(SGT)

    mode = args.mode
    if mode == "auto":
        last_full = state.get("last_full_scan_utc")
        age_h = 999 if not last_full else (now_utc - datetime.fromisoformat(last_full)).total_seconds() / 3600
        mode = "full" if age_h >= cfg["full_scan_every_hours"] - 0.5 else "focus"

    pairs = date_pairs(cfg)
    if mode == "focus":
        want = set(cfg.get("focus_departures", []))
        if state.get("cheapest_depart"):
            want.add(state["cheapest_depart"])
        pairs = [p for p in pairs if p[0] in want]
    print(f"Mode: {mode} · {len(pairs)} date pairs · {now_sgt:%Y-%m-%d %H:%M} SGT")

    history = read_history()
    first_ever = not history
    rows, best_now, errors = [], {}, []
    queue = list(pairs)
    failed = {}
    no_flight = []
    second_pass = False
    for i, item in enumerate(queue):
        if item is None:
            second_pass = True
            continue
        depart, ret = item
        if second_pass and depart not in failed:
            continue
        if i:
            time.sleep(random.uniform(4, 9))  # be gentle with Google
        try:
            res = search(cfg, depart, ret)
            failed.pop(depart, None)
        except Exception as e:
            failed[depart] = str(e)
            continue
        parsed = []
        # Only keep real flights: an airline name AND a departure time. Prices Google
        # shows without them can't be tied to a flight, so they are never used.
        real = [fl for fl in res.flights if (fl.name or "").strip() and (fl.departure or "").strip()]
        if not real:
            no_flight.append(depart)
            continue
        for fl in real:
            amount, cur = parse_price(fl.price)
            if amount is None or amount <= 0:
                continue
            parsed.append((amount, cur, fl))
        parsed.sort(key=lambda t: t[0])
        days_to = (date.fromisoformat(depart) - now_sgt.date()).days
        for rank, (amount, cur, fl) in enumerate(parsed[: cfg["flights_kept_per_search"]], 1):
            total_sgd = amount * fx_to_sgd(cur, state)
            stops = fl.stops if isinstance(fl.stops, int) else str(fl.stops)
            row = {
                "checked_at_utc": now_utc.isoformat(), "checked_at_sgt": now_sgt.isoformat(),
                "check_dow": now_sgt.strftime("%a"), "check_hour_sgt": now_sgt.hour, "mode": mode,
                "depart": depart, "return": ret, "days_to_departure": days_to, "rank": rank,
                "airline": fl.name, "out_departure": fl.departure, "out_arrival": fl.arrival,
                "duration": fl.duration, "stops": stops, "price_raw": fl.price, "currency": cur,
                "price_total_sgd": round(total_sgd, 2),
                "price_per_person_sgd": round(total_sgd / pax(cfg), 2),
                "google_level": getattr(res, "current_price", ""),
            }
            rows.append(row)
            if rank == 1:
                best_now[depart] = dict(row, rank="1", stops_text=(
                    "Direct" if stops == 0 else f"{stops} stop{'s' if stops != 1 else ''}"
                    if isinstance(stops, int) else str(stops)))
        if best_now.get(depart):
            print(f"  {depart}→{ret}: S${best_now[depart]['price_per_person_sgd']:,.0f}/person "
                  f"({best_now[depart]['airline']})")

    errors = [f"{d}: {e}" for d, e in failed.items()]
    if rows:
        append_rows(rows)
    if mode == "full" and best_now:
        state["last_full_scan_utc"] = now_utc.isoformat()
        cheapest = min(best_now.values(), key=lambda r: r["price_per_person_sgd"])
        state["cheapest_depart"] = cheapest["depart"]

    send = (not args.no_telegram)
    if best_now and send:
        if first_ever:
            top = sorted(best_now.values(), key=lambda r: r["price_per_person_sgd"])[:5]
            lines = [f"{i}. <b>{nice_date(r['depart'])} → {nice_date(r['return'])}</b> · "
                     f"S${r['price_per_person_sgd']:,.0f}/person · {r['airline']}"
                     for i, r in enumerate(top, 1)]
            send_message(
                f"🦆 <b>Flight bot is live: {cfg['trip_name']}</b>\n"
                f"{cfg['adults']} adults + {cfg['children']} kids · {cfg['nights']} nights · economy\n\n"
                f"<b>Cheapest weeks right now</b>\n" + "\n".join(lines) +
                "\n\nI'll DM you when a price drops to a new low or is unusually cheap. "
                "Weekly report every Sunday evening.")
        else:
            alerts = check_alerts(cfg, state, history, best_now, now_utc)
            if alerts:
                send_message("🚨 <b>Cheap flight alert</b>\n\n" + "\n\n".join(alerts))

    ok = bool(rows)
    if not ok and send:
        last_fail = state.get("last_fail_notice_utc")
        if not last_fail or (now_utc - datetime.fromisoformat(last_fail)) > timedelta(hours=12):
            send_message("⚠️ <b>Flight bot problem</b>\nCouldn't read any prices this run. "
                         "Google Flights may have changed or blocked the check. I'll keep retrying.\n\n"
                         + "\n".join(errors[:3]))
            state["last_fail_notice_utc"] = now_utc.isoformat()

    save_json(STATE_JSON, state)
    save_json(LAST_RUN_JSON, {
        "run_at_sgt": now_sgt.isoformat(), "mode": mode, "pairs_checked": len(pairs),
        "pairs_ok": len(best_now), "rows_saved": len(rows), "errors": errors[:10], "ok": ok,
        "dates_without_readable_flight": no_flight,
    })
    print(f"Done: {len(best_now)}/{len(pairs)} ok, {len(rows)} rows, {len(errors)} errors")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
