"""Pocket CEO shared library. Python standard library only, so it runs on any Mac or PC."""
import json, os, datetime
from pathlib import Path

LIB = Path(__file__).resolve().parent
RATES_DIR = LIB.parent.parent / "rates"


def data_dir():
    """The owner's private folder. POCKET_CEO_HOME overrides it (used by tests)."""
    return Path(os.environ.get("POCKET_CEO_HOME") or (Path.home() / "Documents" / "Pocket CEO"))


def load_rates(year=None):
    """Load the rates table for a tax year. Falls back to the newest table at or before that year
    and records the fallback in rates['_warning'] so callers can tell the owner."""
    files = sorted(RATES_DIR.glob("[0-9][0-9][0-9][0-9].json"))
    if not files:
        raise SystemExit("No rates file found in " + str(RATES_DIR))
    year = int(year or datetime.date.today().year)
    pick = [f for f in files if int(f.stem) <= year] or files[:1]
    f = pick[-1]
    rates = json.loads(f.read_text(encoding="utf-8"))
    if int(f.stem) != year:
        rates["_warning"] = ("No rates table for %d yet; using the %s table. Treat the result as an estimate "
                             "and check for new rates." % (year, f.stem))
    return rates


def source_lines(rates, ids):
    """Human-readable source lines for a list of source ids."""
    out = []
    for i in dict.fromkeys(ids):
        s = rates["sources"].get(i)
        if s:
            chk = s.get("checked")
            out.append("%s (%s) %s" % (s["name"], "checked " + chk if chk else "NOT re-checked, confirm before quoting", s["url"]))
    return out


PROVINCE_ALIASES = {
    "alberta": "AB", "british columbia": "BC", "b.c.": "BC", "manitoba": "MB", "new brunswick": "NB",
    "newfoundland": "NL", "newfoundland and labrador": "NL", "nova scotia": "NS", "northwest territories": "NT",
    "nunavut": "NU", "ontario": "ON", "prince edward island": "PE", "pei": "PE", "quebec": "QC", "québec": "QC",
    "saskatchewan": "SK", "yukon": "YT",
}


def province_code(text):
    t = (text or "").strip()
    if t.upper() in PROVINCE_ALIASES.values():
        return t.upper()
    code = PROVINCE_ALIASES.get(t.lower())
    if not code:
        raise SystemExit("Unknown province: %r. Use a two-letter code like ON, AB, QC." % text)
    return code


def money(x, cents=False):
    if x is None:
        return "n/a"
    neg = x < 0
    s = ("{:,.2f}" if cents else "{:,.0f}").format(abs(x))
    return ("-$" if neg else "$") + s


def r2(x):
    """Round to cents the way people expect (half up)."""
    return float(int(abs(x) * 100 + 0.5 + 1e-9)) / 100 * (-1 if x < 0 else 1)
