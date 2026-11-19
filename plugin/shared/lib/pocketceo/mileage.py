"""Vehicle logbook CRA expects for vehicle claims: date, destination, purpose, km.
Log: <data_dir>/receipts/<year>/mileage-<year>.csv. Known places (one-way km from home): money/places.csv.
Odometer readings (start and end of year): rows with purpose ODOMETER."""
import csv, datetime
from . import data_dir, r2

FIELDS = ["date", "destination", "purpose", "km", "source", "note"]


def _log(year):
    p = data_dir() / "receipts" / str(year) / ("mileage-%s.csv" % year)
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _places():
    p = data_dir() / "money" / "places.csv"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def load(year):
    p = _log(year)
    if not p.exists():
        return []
    with open(p, newline="", encoding="utf-8") as f:
        return [dict(r, km=float(r["km"] or 0)) for r in csv.DictReader(f)]


def places():
    p = _places()
    if not p.exists():
        return {}
    with open(p, newline="", encoding="utf-8") as f:
        return {r["place"].lower(): float(r["one_way_km"]) for r in csv.DictReader(f)}


def set_place(place, one_way_km):
    cur = places()
    cur[place.lower()] = float(one_way_km)
    with open(_places(), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["place", "one_way_km"])
        for k, v in sorted(cur.items()):
            w.writerow([k, "%g" % v])


def add(date, destination, purpose, km=None, source="owner", note="", round_trip=True):
    year = int(date[:4])
    if km is None:
        one = places().get(destination.lower())
        if one is None:
            raise SystemExit("I don't know how far %s is. Tell me the one-way km once and I'll remember it "
                             "(mileage place \"%s\" <km>)." % (destination, destination))
        km = one * (2 if round_trip else 1)
    rows = load(year)
    if any(r["date"] == date and r["destination"].lower() == destination.lower() and r["purpose"] != "ODOMETER" for r in rows):
        return None  # already logged (e.g. the calendar sweep ran twice)
    rows.append({"date": date, "destination": destination, "purpose": purpose, "km": float(km), "source": source, "note": note})
    rows.sort(key=lambda r: r["date"])
    with open(_log(year), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for r in rows:
            w.writerow(dict(r, km="%g" % r["km"]))
    return rows[-1]


def odometer(date, reading):
    return add(date, "odometer", "ODOMETER", reading, "owner", "odometer reading", round_trip=False) or True


def summary(year):
    rows = load(year)
    trips = [r for r in rows if r["purpose"] != "ODOMETER"]
    odo = sorted((r for r in rows if r["purpose"] == "ODOMETER"), key=lambda r: r["date"])
    business = sum(r["km"] for r in trips)
    total = (odo[-1]["km"] - odo[0]["km"]) if len(odo) >= 2 else None
    out = {"year": year, "trips": len(trips), "business_km": r2(business), "total_km": r2(total) if total else None,
           "business_pct": r2(100 * business / total) if total else None}
    if not total:
        out["missing"] = "Odometer readings for the start and end of the year (CRA expects them). Ask the owner for today's reading."
    return out
