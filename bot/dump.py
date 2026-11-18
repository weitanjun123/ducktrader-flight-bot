"""Debug: save the installed fast-flights source and the raw Google Flights page
for one search into checks/raw/, so the parser can be checked against real pages."""
import inspect, json, os, pkgutil, shutil, sys, traceback
sys.path.insert(0, os.path.dirname(__file__))
from common import ROOT, load_config
import fast_flights
out = os.path.join(ROOT, "checks", "raw")
os.makedirs(out, exist_ok=True)
pkg = os.path.dirname(fast_flights.__file__)
shutil.copytree(pkg, os.path.join(out, "fast_flights_src"), dirs_exist_ok=True,
                ignore=shutil.ignore_patterns("__pycache__", "*.so", "*.pyc"))
info = {"version": getattr(fast_flights, "__version__", "?"), "exports": dir(fast_flights)}
cfg = load_config()
import scan
scan._patch_primp()
for depart, ret in [("2027-05-24", "2027-05-31"), ("2027-05-27", "2027-06-03")]:
    try:
        from fast_flights import FlightData, Passengers
        from fast_flights.filter import TFSData
        f = TFSData.from_interface(
            flight_data=[FlightData(date=depart, from_airport="SIN", to_airport="CJU"),
                         FlightData(date=ret, from_airport="CJU", to_airport="SIN")],
            trip="round-trip", seat="economy",
            passengers=Passengers(adults=4, children=3, infants_in_seat=0, infants_on_lap=0))
        b64 = f.as_b64().decode()
        info[depart] = {"tfs": b64}
        import primp
        c = primp.Client(impersonate="chrome_131", verify=False)
        for curr in ("SGD",):
            r = c.get("https://www.google.com/travel/flights",
                      params={"tfs": b64, "hl": "en", "tfu": "EgQIABABIgA", "curr": curr})
            open(os.path.join(out, f"{depart}_{curr}.html"), "w").write(r.text)
            info[depart][curr] = {"status": r.status_code, "len": len(r.text)}
    except Exception:
        info[depart] = {"error": traceback.format_exc()}
json.dump(info, open(os.path.join(out, "info.json"), "w"), indent=2, default=str)
print(json.dumps(info, indent=2, default=str)[:3000])
