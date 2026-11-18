"""Shared helpers: config, paths, Telegram, currency, Google Flights links."""
import json
import os
import re
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
PRICES_CSV = os.path.join(DATA, "prices.csv")
STATE_JSON = os.path.join(DATA, "state.json")
LAST_RUN_JSON = os.path.join(DATA, "last_run.json")
SGT = timezone(timedelta(hours=8))

PRICE_FIELDS = [
    "checked_at_utc", "checked_at_sgt", "check_dow", "check_hour_sgt", "mode",
    "depart", "return", "days_to_departure", "rank", "airline", "out_departure",
    "out_arrival", "duration", "stops", "price_raw", "currency", "price_total_sgd",
    "price_per_person_sgd", "google_level",
]


def load_config():
    with open(os.path.join(ROOT, "config.json")) as f:
        return json.load(f)


def date_pairs(cfg):
    """Every (depart, return) pair in the window, `nights` apart."""
    d = date.fromisoformat(cfg["depart_from"])
    end = date.fromisoformat(cfg["depart_to"])
    out = []
    while d <= end:
        out.append((d.isoformat(), (d + timedelta(days=cfg["nights"])).isoformat()))
        d += timedelta(days=1)
    return out


def pax(cfg):
    return cfg["adults"] + cfg["children"]


def load_json(path, default):
    try:
        with open(path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def save_json(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)


# ---------- currency ----------
SYMBOLS = {"S$": "SGD", "SGD": "SGD", "US$": "USD", "USD": "USD", "$": "USD",
           "₩": "KRW", "KRW": "KRW", "€": "EUR", "£": "GBP", "MYR": "MYR", "RM": "MYR"}


def parse_price(raw):
    """'$1,234' -> (1234.0, 'USD'). Returns (None, None) if no number."""
    if raw is None:
        return None, None
    s = str(raw).strip()
    num = re.sub(r"[^\d.]", "", s.replace(",", ""))
    if not num:
        return None, None
    cur = "USD"
    for sym in sorted(SYMBOLS, key=len, reverse=True):
        if sym in s:
            cur = SYMBOLS[sym]
            break
    return float(num), cur


def fx_to_sgd(currency, state):
    """Rate to convert `currency` into SGD. Free Frankfurter API; cached in state."""
    if currency == "SGD":
        return 1.0
    cache = state.setdefault("fx", {})
    today = datetime.now(SGT).date().isoformat()
    hit = cache.get(currency)
    if hit and hit.get("date") == today:
        return hit["rate"]
    try:
        url = f"https://api.frankfurter.app/latest?from={currency}&to=SGD"
        with urllib.request.urlopen(url, timeout=20) as r:
            rate = json.load(r)["rates"]["SGD"]
        cache[currency] = {"date": today, "rate": rate}
        return rate
    except Exception as e:  # keep using the last known rate
        print(f"FX lookup failed ({e}); using cached rate")
        if hit:
            return hit["rate"]
        return {"USD": 1.30, "KRW": 0.00095, "EUR": 1.45, "GBP": 1.70, "MYR": 0.30}.get(currency, 1.0)


# ---------- links ----------
def gf_link(cfg, depart, ret):
    """Google Flights link that opens exactly the bot's search (route, dates, 7 passengers)."""
    try:
        from fast_flights import FlightData, Passengers
        from fast_flights.filter import TFSData
        tfs = TFSData.from_interface(
            flight_data=[FlightData(date=depart, from_airport=cfg["origin"], to_airport=cfg["destination"]),
                         FlightData(date=ret, from_airport=cfg["destination"], to_airport=cfg["origin"])],
            trip="round-trip", seat=cfg["seat"], max_stops=0 if cfg.get("direct_only") else None,
            passengers=Passengers(adults=cfg["adults"], children=cfg["children"],
                                  infants_in_seat=0, infants_on_lap=0)).as_b64().decode()
        return f"https://www.google.com/travel/flights/search?tfs={urllib.parse.quote(tfs)}&hl=en&curr=SGD"
    except Exception as e:
        print("link build failed", e)
        return "https://www.google.com/travel/flights?hl=en&curr=SGD"


def nice_date(iso):
    return date.fromisoformat(iso).strftime("%a %d %b")


# ---------- telegram ----------
def _tg(method, data=None, files=None):
    token = os.environ.get("FLIGHT_BOT_TOKEN")
    chat = os.environ.get("FLIGHT_CHAT_ID")
    if not token or not chat:
        print("[telegram disabled] missing FLIGHT_BOT_TOKEN / FLIGHT_CHAT_ID")
        return None
    data = dict(data or {})
    data["chat_id"] = chat
    url = f"https://api.telegram.org/bot{token}/{method}"
    if files:
        import requests  # only needed for photo uploads
        r = requests.post(url, data=data, files=files, timeout=60)
        print("telegram", method, r.status_code, r.text[:200])
        return r.ok
    body = urllib.parse.urlencode(data).encode()
    try:
        with urllib.request.urlopen(url, body, timeout=30) as r:
            print("telegram", method, r.status)
            return True
    except Exception as e:
        print("telegram error", e)
        return False


def send_message(text):
    return _tg("sendMessage", {"text": text, "parse_mode": "HTML",
                               "disable_web_page_preview": "true"})


def send_photo(path, caption=""):
    with open(path, "rb") as f:
        return _tg("sendPhoto", {"caption": caption, "parse_mode": "HTML"}, {"photo": f})
