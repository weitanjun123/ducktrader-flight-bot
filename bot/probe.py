"""Debug probe: try the `fli` library (Google Flights GetShoppingResults API) for one
round trip and save what it returns, plus its source, into checks/probe/."""
import inspect, json, os, shutil, sys, traceback
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
out = os.path.join(ROOT, "checks", "probe"); os.makedirs(out, exist_ok=True)
log = []
def p(*a):
    s = " ".join(str(x) for x in a); print(s); log.append(s)
try:
    import fli
    from fli.search import SearchFlights
    from fli import models as M
    shutil.copytree(os.path.dirname(fli.__file__), os.path.join(out, "fli_src"), dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    p("search sig:", inspect.signature(SearchFlights.search))
    p("PassengerInfo fields:", getattr(M.PassengerInfo, "model_fields", {}).keys())
    p("FlightSearchFilters fields:", getattr(M.FlightSearchFilters, "model_fields", {}).keys())
    p("FlightSegment fields:", getattr(M.FlightSegment, "model_fields", {}).keys())
    segs = [M.FlightSegment(departure_airport=[[M.Airport.SIN, 0]], arrival_airport=[[M.Airport.CJU, 0]], travel_date="2027-05-24"),
            M.FlightSegment(departure_airport=[[M.Airport.CJU, 0]], arrival_airport=[[M.Airport.SIN, 0]], travel_date="2027-05-31")]
    f = M.FlightSearchFilters(trip_type=M.TripType.ROUND_TRIP,
                              passenger_info=M.PassengerInfo(adults=4, children=3),
                              flight_segments=segs, seat_type=M.SeatType.ECONOMY,
                              stops=M.MaxStops.ANY, sort_by=M.SortBy.CHEAPEST)
    sf = SearchFlights()
    kw = {}
    if "currency" in inspect.signature(sf.search).parameters: kw["currency"] = "SGD"
    if "top_n" in inspect.signature(sf.search).parameters: kw["top_n"] = 3
    res = sf.search(f, **kw)
    p("type:", type(res), "len:", len(res) if res else res)
    for r in (res or [])[:6]:
        p("----"); p(repr(r)[:3000])
except Exception:
    p(traceback.format_exc())
open(os.path.join(out, "probe.txt"), "w").write("\n".join(log))
