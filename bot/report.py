"""Weekly report: cheapest week to fly, best day/hour to buy, price trend."""
import argparse
import os
import sys
from datetime import datetime, timedelta, timezone

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from common import DATA, LAST_RUN_JSON, PRICES_CSV, load_json, SGT, gf_link, load_config, nice_date, send_message, send_photo

BG, PANEL, GOLD, WHITE, GREY, RED, GREEN = "#17181c", "#22242a", "#f2c14e", "#f5f5f5", "#8a8f98", "#e5484d", "#3fb950"
DOWS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
FULL_DOW = dict(zip(DOWS, ["Mondays", "Tuesdays", "Wednesdays", "Thursdays", "Fridays", "Saturdays", "Sundays"]))
OUT = os.path.join(DATA, "report")


def style(ax, fig):
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(PANEL)
    for s in ax.spines.values():
        s.set_color(GREY)
    ax.tick_params(colors=WHITE, labelsize=9)
    ax.title.set_color(WHITE)
    ax.xaxis.label.set_color(GREY)
    ax.yaxis.label.set_color(GREY)


def footer(fig, n_days):
    fig.text(0.99, 0.01, f"DUCKTRADER4444 · Google Flights prices · {n_days} days of data",
             color=GREY, fontsize=7, ha="right")


def chart_cheapest_week(df, path):
    # Latest price per departure date seen in the last 24h (Google doesn't show every date every run)
    r1 = df[df["rank"] == 1].copy()
    r1["ts"] = pd.to_datetime(r1["checked_at_utc"])
    r1 = r1[r1["ts"] >= r1["ts"].max() - pd.Timedelta(hours=24)]
    snap = r1.sort_values("ts").groupby("depart").tail(1).sort_values("depart")
    low = df[df["rank"] == 1].groupby("depart")["price_per_person_sgd"].min()
    fig, ax = plt.subplots(figsize=(10, 5.2), dpi=110)
    style(ax, fig)
    labels = [pd.Timestamp(d).strftime("%d %b") for d in snap["depart"]]
    vals = snap["price_per_person_sgd"].values
    best = vals.argmin()
    colors = [GOLD if i == best else "#5b6070" for i in range(len(vals))]
    ax.bar(labels, vals, color=colors)
    ax.scatter(labels, [low.get(d, np.nan) for d in snap["depart"]], color=GREEN, zorder=3, s=18,
               label="Lowest ever seen")
    ax.annotate(f"S${vals[best]:,.0f}", (best, vals[best]), xytext=(0, 6), textcoords="offset points",
                ha="center", color=GOLD, fontsize=10, fontweight="bold")
    ax.set_title("Cheapest week to fly · price per person (S$) by departure date", fontsize=12)
    ax.set_xlabel("Departure date (7 nights)")
    ax.tick_params(axis="x", rotation=60)
    ax.set_ylim(min(vals.min(), low.min()) * 0.85, vals.max() * 1.08)
    ax.legend(facecolor=PANEL, edgecolor=GREY, labelcolor=WHITE, fontsize=8)
    footer(fig, df["day"].nunique())
    fig.tight_layout()
    fig.savefig(path, facecolor=BG)
    plt.close(fig)
    return snap.iloc[best]


def buy_time_table(df):
    """% above/below each date pair's own median, averaged per (day, hour) of checking."""
    # Compare each price with the same dates' median over the surrounding 7 days,
    # so a general up/down trend doesn't get mistaken for a "cheap weekday".
    r1 = df[df["rank"] == 1].copy()
    r1["ts"] = pd.to_datetime(r1["checked_at_utc"])
    r1 = r1.sort_values("ts")
    base = (r1.set_index("ts").groupby("depart")["price_per_person_sgd"]
              .transform(lambda s: s.rolling("7D", center=True, min_periods=1).median()))
    r1["rel"] = r1["price_per_person_sgd"].values / base.values - 1
    return r1.pivot_table(index="check_dow", columns="check_hour_sgt", values="rel", aggfunc="mean")\
             .reindex(index=DOWS, columns=range(24)) * 100


def chart_heatmap(df, path):
    tbl = buy_time_table(df)
    fig, ax = plt.subplots(figsize=(11, 4.2), dpi=110)
    style(ax, fig)
    lim = max(2.0, np.nanmax(np.abs(tbl.values)) if np.isfinite(tbl.values).any() else 2.0)
    im = ax.imshow(tbl.values, cmap="RdYlGn_r", vmin=-lim, vmax=lim, aspect="auto")
    ax.set_yticks(range(7), DOWS)
    ax.set_xticks(range(0, 24, 2), [f"{h:02d}" for h in range(0, 24, 2)])
    ax.set_xlabel("Hour you check/buy (Singapore time) · blank = no data yet")
    ax.set_title("Best time to buy · green = cheaper than usual, red = pricier (%)", fontsize=12)
    cb = fig.colorbar(im, ax=ax, fraction=0.025)
    cb.ax.tick_params(colors=WHITE, labelsize=8)
    footer(fig, df["day"].nunique())
    fig.tight_layout()
    fig.savefig(path, facecolor=BG)
    plt.close(fig)
    return tbl


def chart_trend(df, cfg, path):
    r1 = df[df["rank"] == 1]
    daily_min = r1.groupby("day")["price_per_person_sgd"].min()
    fig, ax = plt.subplots(figsize=(10, 4.6), dpi=110)
    style(ax, fig)
    ax.plot(pd.to_datetime(daily_min.index), daily_min.values, color=GOLD, lw=2, marker="o", ms=3,
            label="Cheapest of any week")
    for d in cfg.get("focus_departures", []):
        s = r1[r1["depart"] == d].groupby("day")["price_per_person_sgd"].min()
        if len(s):
            ax.plot(pd.to_datetime(s.index), s.values, color=WHITE, lw=1.4, ls="--",
                    label=f"Your dates ({nice_date(d)})")
    ax.set_title("Price trend · S$ per person (daily lowest)", fontsize=12)
    ax.legend(facecolor=PANEL, edgecolor=GREY, labelcolor=WHITE, fontsize=8)
    fig.autofmt_xdate()
    footer(fig, df["day"].nunique())
    fig.tight_layout()
    fig.savefig(path, facecolor=BG)
    plt.close(fig)
    return daily_min


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-telegram", action="store_true")
    args = ap.parse_args()
    cfg = load_config()
    if not os.path.exists(PRICES_CSV):
        print("no data yet")
        return 0
    df = pd.read_csv(PRICES_CSV)
    df = df[df["price_per_person_sgd"] > 0]
    df["day"] = pd.to_datetime(df["checked_at_sgt"].str[:10]).dt.date.astype(str)
    os.makedirs(OUT, exist_ok=True)
    n_days = df["day"].nunique()

    p1, p2, p3 = (os.path.join(OUT, n) for n in ("1_cheapest_week.png", "2_best_time_to_buy.png", "3_trend.png"))
    best = chart_cheapest_week(df, p1)
    tbl = chart_heatmap(df, p2)
    daily = chart_trend(df, cfg, p3)

    r1 = df[df["rank"] == 1]
    low_row = r1.loc[r1["price_per_person_sgd"].idxmin()]
    lines = [
        f"📊 <b>Weekly flight report: {cfg['trip_name']}</b>",
        f"{cfg['adults']} adults + {cfg['children']} kids · {cfg['nights']} nights · {n_days} days of data",
        "",
        f"🏆 <b>Cheapest week now:</b> {nice_date(best['depart'])} → {nice_date(best['return'])} · "
        f"<b>S${best['price_per_person_sgd']:,.0f}/person</b> ({best['airline']})",
        f"📉 <b>Lowest ever seen:</b> S${low_row['price_per_person_sgd']:,.0f}/person "
        f"({nice_date(low_row['depart'])}, seen {low_row['day']})",
    ]
    if len(daily) >= 8:
        wk = daily.iloc[-1] - daily.iloc[-8]
        lines.append(f"{'🔻' if wk < 0 else '🔺'} <b>vs last week:</b> {'down' if wk < 0 else 'up'} "
                     f"S${abs(wk):,.0f}/person")
    if n_days >= 14:
        by_dow = tbl.mean(axis=1).dropna()
        by_hour = tbl.mean(axis=0).dropna()
        if len(by_dow) and len(by_hour):
            lines.append(f"🕒 <b>Best time to buy so far:</b> {FULL_DOW[by_dow.idxmin()]} (~{by_dow.min():+.1f}%), "
                         f"around {int(by_hour.idxmin()):02d}:00 SGT (~{by_hour.min():+.1f}%)")
            lines.append("<i>Small % = small effect. Booking timing matters more than weekday.</i>")
    else:
        lines.append(f"🕒 <b>Best time to buy:</b> needs ~2 weeks of hourly data ({n_days} so far)")
    nf = load_json(LAST_RUN_JSON, {}).get("dates_no_direct_flight", [])
    if nf:
        lines.append("✖️ <b>No direct flight shown on:</b> " + ", ".join(nice_date(d) for d in nf))
    lines.append(f"\n🔗 <a href=\"{gf_link(cfg, best['depart'], best['return'])}\">Cheapest week on Google Flights</a>")
    text = "\n".join(lines)
    print(text)
    if not args.no_telegram:
        send_message(text)
        send_photo(p1, "🏆 Cheapest week to fly")
        send_photo(p2, "🕒 Best time to buy (green = cheaper)")
        send_photo(p3, "📈 Price trend")
    return 0


if __name__ == "__main__":
    sys.exit(main())
