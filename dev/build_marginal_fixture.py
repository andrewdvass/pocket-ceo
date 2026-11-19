#!/usr/bin/env python3
"""Download TaxTips' combined federal+provincial marginal rate tables for a year and save them as the
test fixture the engine is checked against.   python3 dev/build_marginal_fixture.py 2027
Uses only the standard library. TaxTips is a secondary source that reconciles its tables to CRA."""
import datetime, json, re, sys, urllib.request
from html.parser import HTMLParser
from pathlib import Path

PROVS = "ab bc mb nb nl ns nt nu on pe qc sk yt".split()


class Text(HTMLParser):
    def __init__(self):
        super().__init__(); self.o = []; self.skip = 0
    def handle_starttag(self, t, a):
        if t in ("script", "style", "nav", "footer"): self.skip += 1
        if t in ("tr", "p", "h1", "h2", "h3", "li", "br", "div", "table"): self.o.append("\n")
        if t in ("td", "th"): self.o.append(" | ")
    def handle_endtag(self, t):
        if t in ("script", "style", "nav", "footer"): self.skip -= 1
    def handle_data(self, d):
        if self.skip <= 0: self.o.append(d.replace("\r", " ").replace("\n", " "))


def rows(html, year):
    p = Text(); p.feed(html)
    text = re.sub(r"[ \t\xa0]+", " ", "".join(p.o))
    num = lambda s: float(s.replace("$", "").replace(",", "").replace("%", ""))
    if not re.search(r"Combined Federal .{0,80}%d" % year, text):
        return []  # page doesn't have this year's table yet
    out = []
    for line in text.splitlines():
        c = [x.strip() for x in line.split("|")][1:]
        if len(c) >= 5 and re.match(r"(first|over)", c[0]) and all("%" in x for x in c[1:5]):
            m = re.findall(r"\$([\d,]+)", c[0])
            lo = 0 if c[0].startswith("first") else num(m[0])
            hi = num(m[-1]) if ("up to" in c[0] or c[0].startswith("first")) else None
            out.append({"from": lo, "to": hi, "other": num(c[1]), "capital_gains": num(c[2]),
                        "eligible_div": num(c[3]), "non_eligible_div": num(c[4])})  # first 5 cells = newest year
    return out


def main(year):
    tables = {}
    for p in PROVS:
        req = urllib.request.Request("https://www.taxtips.ca/taxrates/%s.htm" % p, headers={"User-Agent": "Mozilla/5.0"})
        html = urllib.request.urlopen(req, timeout=60).read().decode("utf-8", "replace")
        tables[p.upper()] = rows(html, year)
        if not tables[p.upper()]:
            sys.exit("No %d table found for %s; TaxTips may not have published it yet." % (year, p.upper()))
    dest = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / ("taxtips_marginal_%d.json" % year)
    dest.write_text(json.dumps({"source": "https://www.taxtips.ca/taxrates/<province>.htm combined federal+provincial marginal rate tables for %d, retrieved %s" % (year, datetime.date.today()),
                                "note": "Rates are % of actual income; they exclude CPP/EI and the Ontario Health Premium.",
                                "tables": tables}, indent=1))
    print("wrote", dest, {k: len(v) for k, v in tables.items()})


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else datetime.date.today().year)
