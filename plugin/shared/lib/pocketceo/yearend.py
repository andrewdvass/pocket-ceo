"""Year-end package for the owner's accountant (sole proprietor / T2125).

Builds <data_dir>/year-end/<year>/ with:
  summary.html (and summary.pdf when Chrome/Edge/Chromium is installed)
  T2125-worksheet.csv     expense and income totals by T2125 line
  GST-HST-worksheet.csv   sales, tax collected, input tax credits, net tax (if registered)
  CCA-schedule.csv        capital items by class, opening UCC, additions, CCA, closing UCC
  missing-receipts.csv    business purchases in the bank file with no receipt
  receipts/               copies of every receipt photo for the year
  inputs.json             the owner's answers (home office, vehicle km, GST method). Edit and rebuild.
"""
import csv, datetime, html, json, os, re, shutil, subprocess
from pathlib import Path
from . import data_dir, r2, money, load_rates, source_lines
from . import tax as taxmod
from .bank import load_ledger, INCOME, NOT_BUSINESS_EXPENSE, PERSONAL, REVIEW
from .reconcile import load_receipts, reconcile

INPUTS_TEMPLATE = {
    "_help": "Fill in what applies, leave the rest as null, then ask Pocket CEO to rebuild the package.",
    "province": None,
    "gst": {"registered": None, "method": "regular", "quick_method_rate": None},
    "home_office": {"workspace_sq_ft": None, "home_sq_ft": None, "rent": None, "mortgage_interest": None,
                    "utilities": None, "home_insurance": None, "property_tax": None, "maintenance": None,
                    "meets_rules": None,
                    "_rules": "Deductible only if it is your main place of business, or used only for business and regularly to meet clients."},
    "vehicle": {"business_km": None, "total_km": None, "logbook_kept": None},
    "opening_ucc": {},
    "capital_class_overrides": {},
    "other_business_income_not_in_bank": 0,
}

CLASS_GUESS = [(r"LAPTOP|MACBOOK|COMPUTER|\bPC\b|IMAC|IPAD|TABLET|MONITOR|SERVER|PRINTER", "50"),
               (r"CAR|TRUCK|VAN|VEHICLE|SUV", "10"),
               (r"SOFTWARE|LICENCE|LICENSE", "12"),
               (r".", "8")]
GST34_LINES = {"101": "Sales and other revenue", "103": "GST/HST collected or collectible", "106": "Input tax credits (ITCs)",
               "109": "Net tax"}


def _f(x):
    try:
        return float(str(x).replace("$", "").replace(",", "")) if x not in (None, "") else 0.0
    except ValueError:
        return 0.0


def _pct(x, default=100.0):
    v = _f(x)
    return v if v else default


def find_browser():
    cands = ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
             "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
             "/Applications/Chromium.app/Contents/MacOS/Chromium",
             r"C:\Program Files\Google\Chrome\Application\chrome.exe",
             r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
             r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
             r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
             "/opt/pw-browsers/chromium", "/usr/bin/chromium", "/usr/bin/chromium-browser", "/usr/bin/google-chrome"]
    env = os.environ.get("POCKET_CEO_BROWSER")
    for c in ([env] if env else []) + cands:
        if c and Path(c).exists():
            p = Path(c)
            if p.is_dir():  # playwright layout
                hit = list(p.glob("**/chrome")) + list(p.glob("**/chromium"))
                if hit:
                    return str(hit[0])
                continue
            return c
    for name in ("google-chrome", "chromium", "chromium-browser", "msedge"):
        w = shutil.which(name)
        if w:
            return w
    return None


def html_to_pdf(html_path, pdf_path):
    b = find_browser()
    if not b:
        return False
    try:
        subprocess.run([b, "--headless", "--no-sandbox", "--disable-gpu", "--no-pdf-header-footer",
                        "--print-to-pdf=" + str(pdf_path), Path(html_path).resolve().as_uri()],
                       check=True, capture_output=True, timeout=90)
        return Path(pdf_path).exists()
    except Exception:
        return False


def build(year, province=None, out_dir=None, today=None):
    R = load_rates(year)
    year = int(year)
    out = Path(out_dir) if out_dir else data_dir() / "year-end" / str(year)
    out.mkdir(parents=True, exist_ok=True)
    ip = out / "inputs.json"
    if not ip.exists():
        ip.write_text(json.dumps(INPUTS_TEMPLATE, indent=2), encoding="utf-8")
    inputs = json.loads(ip.read_text(encoding="utf-8"))
    prov = province or inputs.get("province")
    if not prov:
        raise SystemExit("Province needed: pass --province or set it in " + str(ip))
    st = R["provinces"][prov]["sales_tax"]
    gst_reg = bool((inputs.get("gst") or {}).get("registered"))
    rate = st["gst_hst"]
    line_of = R["t2125"]["category_to_line"]
    names = R["t2125"]["expenses"]
    warnings = []

    receipts = load_receipts(year)
    rec = reconcile(year)
    lines, capital, itc_total, itc_items = {}, [], 0.0, 0

    def add(line, amount, src):
        e = lines.setdefault(line, {"line": line, "name": names.get(line, "Other expenses"), "amount": 0.0, "from_receipts": 0.0, "from_bank_only": 0.0, "items": 0})
        e["amount"] += amount
        e["items"] += 1
        e["from_receipts" if src == "receipt" else "from_bank_only"] += amount

    veh = dict(inputs.get("vehicle") or {})
    from . import mileage as _mi
    ms = _mi.summary(year)
    if not (veh.get("business_km") and veh.get("total_km")) and ms["business_pct"] is not None:
        veh["business_km"], veh["total_km"] = ms["business_km"], ms["total_km"]
    veh_pct = None
    if veh.get("business_km") and veh.get("total_km"):
        veh_pct = 100.0 * _f(veh["business_km"]) / _f(veh["total_km"])

    for r in receipts:
        cat = (r.get("category") or "").strip()
        pct = _pct(r.get("business_pct"))
        if cat.startswith("Personal"):
            continue
        sub, gst, pst, tip = _f(r.get("subtotal")), _f(r.get("gst_hst")), _f(r.get("pst_qst")), _f(r.get("tip"))
        total = _f(r.get("total"))
        if cat == "CAPITAL":
            cost = (sub + pst + (0 if gst_reg else gst)) or total
            capital.append({"date": r["date"], "what": r.get("what") or r.get("vendor"), "vendor": r.get("vendor"),
                            "cost": cost * pct / 100, "business_pct": pct, "notes": r.get("notes", ""), "file": r.get("file", "")})
            if gst_reg:
                itc_total += gst * pct / 100; itc_items += 1
            continue
        if cat == "Motor vehicle expenses" and veh_pct is not None:
            pct = veh_pct
        base = (total - gst) if gst_reg else total  # registrants claim the GST/HST back as an ITC instead
        if prov == "QC" and gst_reg:
            base -= pst  # QST is also recovered (input tax refunds)
        ded = base * pct / 100
        itc = gst * pct / 100
        if cat == "Meals and entertainment":
            ded *= R["t2125"]["meals_deductible_share"]
            itc *= R["t2125"]["meals_deductible_share"]
        add(line_of.get(cat, "9270"), ded, "receipt")
        if gst_reg:
            if r.get("itc") not in (None, ""):
                itc = _f(r["itc"])
            itc_total += itc; itc_items += 1

    # bank purchases with no receipt: listed so the accountant decides; counted, flagged
    bank_only = []
    for m in rec["missing_receipts"]:
        t = next((x for x in load_ledger() if x["id"] == m["id"]), None)
        if not t:
            continue
        pct = t["business_pct"] or 100
        if t["category"] == "Motor vehicle expenses" and veh_pct is not None:
            pct = veh_pct
        amt = m["amount"] / (1 + rate) if gst_reg else m["amount"]
        ded = amt * pct / 100 * (R["t2125"]["meals_deductible_share"] if t["category"] == "Meals and entertainment" else 1)
        add(line_of.get(t["category"], "9270"), ded, "bank")
        bank_only.append(dict(m, deductible=r2(ded)))

    # income from bank deposits categorised as business income
    led = [t for t in load_ledger() if t["date"].startswith(str(year))]
    deposits = sum(t["amount"] for t in led if t["category"] == INCOME)
    deposits += _f(inputs.get("other_business_income_not_in_bank"))
    sales = deposits / (1 + rate) if gst_reg else deposits
    gst_collected = deposits - sales
    review_left = [t for t in led if t["category"] in (REVIEW, "")]
    if review_left:
        warnings.append("%d bank transactions (%s) are still NEEDS REVIEW and are not counted. Sort them first."
                        % (len(review_left), money(sum(-t["amount"] for t in review_left if t["amount"] < 0))))
    if not led:
        warnings.append("No bank transactions for %d were imported, so income is missing. Import the year's bank CSV." % year)

    # CCA
    ccar = R["cca"]
    fy = ccar.get("first_year", {})
    lo, hi = (fy.get("applies_to_available_for_use") or [0, 0])
    mult = fy.get("multiplier_vs_half_year", 1.0) if lo <= year <= hi else 1.0
    overrides = inputs.get("capital_class_overrides") or {}
    classes = {}
    for c in capital:
        cls = overrides.get(c["what"]) or overrides.get(c["file"])
        m = re.search(r"class\s*(\d+(?:\.\d)?)", c["notes"] or "", re.I)
        if not cls and m:
            cls = m.group(1)
        if not cls:
            cls = next(k for pat, k in CLASS_GUESS if re.search(pat, (c["what"] or "").upper()))
            c["class_guessed"] = True
        if cls == "10" and c["cost"] > R["vehicle"]["class_10_1_ceiling"] * 1.15:
            cls = "10.1"
            c["cost_capped"] = R["vehicle"]["class_10_1_ceiling"] * (1 + rate if not gst_reg else 1)
        c["class"] = cls
        k = classes.setdefault(cls, {"class": cls, "rate": ccar["classes"].get(cls, {}).get("rate"), "opening_ucc": _f((inputs.get("opening_ucc") or {}).get(cls)),
                                     "additions": 0.0, "items": []})
        k["additions"] += c.get("cost_capped", c["cost"])
        k["items"].append(c)
    for cls, v in (inputs.get("opening_ucc") or {}).items():
        classes.setdefault(cls, {"class": cls, "rate": ccar["classes"].get(cls, {}).get("rate"), "opening_ucc": _f(v), "additions": 0.0, "items": []})
    cca_total = 0.0
    for k in classes.values():
        if k["rate"] is None:
            k["cca"] = 0.0
            warnings.append("Class %s has no rate on file; the accountant must calculate its CCA." % k["class"])
        else:
            first = k["additions"] * 0.5 * mult if k["class"] != "12" else k["additions"]
            k["cca"] = min(k["opening_ucc"] + k["additions"], k["opening_ucc"] * k["rate"] + first * k["rate"] if k["class"] != "12" else k["opening_ucc"] + k["additions"])
        if k["class"] in ("10", "10.1", "54") and veh_pct is not None:
            k["business_use_note"] = "Claim %.0f%% of this CCA (business km share)." % veh_pct
        k["closing_ucc"] = k["opening_ucc"] + k["additions"] - k["cca"]
        cca_total += k["cca"] * ((veh_pct or 100) / 100 if k["class"] in ("10", "10.1", "54") else 1)
    if any(c.get("class_guessed") for c in capital):
        warnings.append("Some capital items had their CCA class guessed from the description. Check the CCA schedule.")
    if cca_total:
        add("9936", cca_total, "receipt")
        lines["9936"]["name"] = names["9936"]

    expenses_before_home = sum(v["amount"] for k, v in lines.items())
    net_before_home = sales - expenses_before_home
    # home office
    ho = inputs.get("home_office") or {}
    home = None
    if ho.get("workspace_sq_ft") and ho.get("home_sq_ft"):
        share = _f(ho["workspace_sq_ft"]) / _f(ho["home_sq_ft"])
        costs = sum(_f(ho.get(k)) for k in ("rent", "mortgage_interest", "utilities", "home_insurance", "property_tax", "maintenance"))
        claim = costs * share
        allowed = max(0.0, min(claim, net_before_home))
        home = {"share_pct": r2(share * 100), "total_home_costs": r2(costs), "business_share": r2(claim),
                "allowed_this_year": r2(allowed), "carried_forward": r2(claim - allowed),
                "meets_rules": ho.get("meets_rules")}
        if allowed:
            add("9945", allowed, "receipt")
        if ho.get("meets_rules") is not True:
            warnings.append("Home office: confirm it is your main place of business (or used only for business and to meet clients regularly) before claiming it.")
    total_exp = sum(v["amount"] for v in lines.values())
    net = sales - total_exp
    st_ = taxmod.set_aside(R, prov, max(0.0, net))
    gst_ws = None
    if gst_reg:
        method = (inputs.get("gst") or {}).get("method", "regular")
        if method == "quick":
            q = (inputs.get("gst") or {}).get("quick_method_rate")
            net_tax = deposits * _f(q) - min(deposits, 30000) * 0.01 if q else None
            gst_ws = {"method": "quick", "101": r2(sales), "103": r2(gst_collected), "quick_rate": q,
                      "109": r2(net_tax) if net_tax is not None else None}
            if not q:
                warnings.append("Quick Method chosen but no remittance rate given in inputs.json.")
        else:
            gst_ws = {"method": "regular", "101": r2(sales), "103": r2(gst_collected), "106": r2(itc_total), "109": r2(gst_collected - itc_total)}
        if bank_only:
            warnings.append("No input tax credits are claimed on the %d purchases without receipts. Finding those receipts could add about %s in ITCs."
                            % (len(bank_only), money(sum(b["amount"] for b in bank_only) * rate / (1 + rate))))
    if gst_reg is False and sales > R["gst_hst"]["small_supplier_threshold"]:
        warnings.append("Sales were over $30,000 but the profile says you are not registered for GST/HST. Ask the accountant about registering.")

    # ---- write files
    def wcsv(name, fields, rows):
        with open(out / name, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            w.writeheader(); w.writerows(rows)
    t_rows = [{"line": "8299", "name": "Gross business income (sales, excluding GST/HST)", "amount": "%.2f" % sales, "from_receipts": "", "from_bank_only": "", "items": ""}]
    for k in sorted(lines):
        v = lines[k]
        t_rows.append({kk: ("%.2f" % vv if isinstance(vv, float) else vv) for kk, vv in v.items()})
    t_rows.append({"line": "9369", "name": "Net income before adjustments", "amount": "%.2f" % net})
    wcsv("T2125-worksheet.csv", ["line", "name", "amount", "from_receipts", "from_bank_only", "items"], t_rows)
    wcsv("missing-receipts.csv", ["date", "amount", "description", "category", "deductible", "id"], bank_only)
    cca_rows = [{"class": k["class"], "rate": k["rate"], "opening_ucc": "%.2f" % k["opening_ucc"], "additions": "%.2f" % k["additions"],
                 "cca_claimed": "%.2f" % k["cca"], "closing_ucc": "%.2f" % k["closing_ucc"],
                 "items": "; ".join("%s %s (%s)%s" % (c["date"], c["what"], money(c["cost"], True), " CLASS GUESSED" if c.get("class_guessed") else "") for c in k["items"]),
                 "note": k.get("business_use_note", "")} for k in classes.values()]
    wcsv("CCA-schedule.csv", ["class", "rate", "opening_ucc", "additions", "cca_claimed", "closing_ucc", "items", "note"], cca_rows)
    (out / ("cca-closing-%d.json" % year)).write_text(json.dumps({k["class"]: r2(k["closing_ucc"]) for k in classes.values()}, indent=1))
    if gst_ws:
        wcsv("GST-HST-worksheet.csv", ["line", "name", "amount"],
             [{"line": k, "name": GST34_LINES.get(k, k), "amount": v} for k, v in gst_ws.items() if k != "method"])
    rd = out / "receipts"
    rd.mkdir(exist_ok=True)
    copied = 0
    src_dir = data_dir() / "receipts" / str(year)
    for r in receipts:
        f = src_dir / (r.get("file") or "")
        if r.get("file") and f.is_file():
            dst = rd / f.name
            if not dst.exists():
                shutil.copy2(f, dst); copied += 1
    for p in src_dir.glob("receipts-%d.*" % year):
        shutil.copy2(p, out / p.name)

    result = {"year": year, "province": prov, "folder": str(out), "sales": r2(sales), "gst_collected": r2(gst_collected),
              "expenses": r2(total_exp), "net_income": r2(net), "lines": {k: r2(v["amount"]) for k, v in sorted(lines.items())},
              "cca": cca_rows, "home_office": home, "vehicle_business_pct": r2(veh_pct) if veh_pct is not None else None,
              "gst": gst_ws, "missing_receipts": {"count": len(bank_only), "total": r2(sum(b["amount"] for b in bank_only))},
              "receipts_logged": len(receipts), "receipt_photos_copied": copied,
              "estimated_tax_and_cpp": st_["tax_and_cpp_on_business_income"], "warnings": warnings}
    page = _summary_html(R, result, names, lines, sales, classes, home, gst_ws, bank_only)
    (out / "summary.html").write_text(page, encoding="utf-8")
    result["pdf"] = str(out / "summary.pdf") if html_to_pdf(out / "summary.html", out / "summary.pdf") else None
    (out / "README.txt").write_text(
        "Year-end package for %d, built by Pocket CEO on %s.\n\nsummary.%s - one-page summary (start here)\n"
        "T2125-worksheet.csv - totals by T2125 line\nGST-HST-worksheet.csv - GST/HST return worksheet (if registered)\n"
        "CCA-schedule.csv - capital cost allowance by class\nmissing-receipts.csv - bank purchases with no receipt\n"
        "receipts-%d.csv / .md - the full receipt log\nreceipts/ - every receipt photo\ninputs.json - home office, vehicle and GST answers used\n\n"
        "These are working papers prepared from the owner's records, not a filed return. Please review before filing.\n"
        % (year, (today or datetime.date.today()).isoformat(), "pdf" if result["pdf"] else "html", year), encoding="utf-8")
    return result


def _summary_html(R, res, names, lines, sales, classes, home, gst_ws, bank_only):
    e = html.escape
    rows = "".join("<tr><td>%s</td><td>%s</td><td class=n>%s</td>%s</tr>" % (
        k, e(v["name"]), money(v["amount"], True),
        "<td class=n>%s</td>" % (money(v["from_bank_only"], True) if v["from_bank_only"] else "")) for k, v in sorted(lines.items()))
    warn = "".join("<li>%s</li>" % e(w) for w in res["warnings"]) or "<li>None.</li>"
    gst = ""
    if gst_ws:
        gst = "<h2>GST/HST return worksheet (%s method)</h2><table>%s</table>" % (e(gst_ws["method"]), "".join(
            "<tr><td>Line %s</td><td>%s</td><td class=n>%s</td></tr>" % (k, e(GST34_LINES.get(k, k)), money(v, True) if isinstance(v, (int, float)) else e(str(v)))
            for k, v in gst_ws.items() if k not in ("method", "quick_rate")))
    cca = "".join("<tr><td>Class %s</td><td>%s</td><td class=n>%s</td><td class=n>%s</td><td class=n>%s</td></tr>" % (
        k["class"], "%g%%" % (k["rate"] * 100) if k["rate"] else "?", money(k["additions"], True), money(k["cca"], True), money(k["closing_ucc"], True))
        for k in classes.values()) or "<tr><td colspan=5>No capital purchases.</td></tr>"
    ho = ("<p>Home office: %s%% of the home, %s of costs, %s claimed this year, %s carried forward.</p>"
          % (home["share_pct"], money(home["total_home_costs"]), money(home["allowed_this_year"]), money(home["carried_forward"]))) if home else ""
    src = "".join("<li>%s</li>" % e(s) for s in source_lines(R, ["cra_t2125", "cra_cca", "cra_aii", "tt_veh"]))
    return """<!doctype html><html><head><meta charset="utf-8"><title>Year-end %(y)s</title><style>
@page{size:letter;margin:16mm}body{font:11pt/1.45 -apple-system,Segoe UI,Helvetica,Arial,sans-serif;color:#1b1f24;max-width:820px;margin:24px auto;padding:0 16px}
h1{font-size:20pt;margin:0}h2{font-size:12.5pt;margin:22px 0 6px;border-bottom:1px solid #d0d7de;padding-bottom:3px}
.k{display:flex;gap:12px;margin:14px 0}.k div{flex:1;border:1px solid #d0d7de;border-radius:8px;padding:10px}.k b{display:block;font-size:15pt}
table{border-collapse:collapse;width:100%%;font-size:10pt}td,th{padding:4px 6px;border-bottom:1px solid #eaeef2;text-align:left}.n{text-align:right;font-variant-numeric:tabular-nums}
.muted{color:#57606a;font-size:9pt}ul{margin:4px 0 0 18px;padding:0}</style></head><body>
<h1>Year-end package, %(y)s</h1><div class=muted>%(prov)s sole proprietor. Prepared by Pocket CEO from the owner's receipts and bank records for the accountant's review. Not a filed return.</div>
<div class=k><div>Sales (excl. GST/HST)<b>%(sales)s</b></div><div>Business expenses<b>%(exp)s</b></div><div>Net business income<b>%(net)s</b></div></div>
<h2>Check these first</h2><ul>%(warn)s</ul>
<h2>T2125 expense lines</h2><table><tr><th>Line</th><th>Expense</th><th class=n>Deductible</th><th class=n>Of which, no receipt</th></tr>%(rows)s</table>
%(ho)s%(gst)s
<h2>Capital cost allowance</h2><table><tr><th>Class</th><th>Rate</th><th class=n>Additions</th><th class=n>CCA</th><th class=n>Closing UCC</th></tr>%(cca)s</table>
<h2>Records</h2><p>%(nrec)d receipts logged, %(ncopy)d photos copied into this folder. %(miss)s</p>
<p class=muted>Estimated income tax and CPP on this business income: %(est)s (estimate only, basic credits). Meals are at 50%%. Purchases are shown net of GST/HST when registered.</p>
<h2 class=muted>Sources</h2><ul class=muted>%(src)s</ul></body></html>""" % {
        "y": res["year"], "prov": e(R["provinces"][res["province"]]["name"]), "sales": money(sales), "exp": money(res["expenses"]),
        "net": money(res["net_income"]), "warn": warn, "rows": rows, "ho": ho, "gst": gst, "cca": cca,
        "nrec": res["receipts_logged"], "ncopy": res["receipt_photos_copied"],
        "miss": ("%d business purchases (%s) in the bank file have no receipt; see missing-receipts.csv." % (len(bank_only), money(res["missing_receipts"]["total"]))) if bank_only else "",
        "est": money(res["estimated_tax_and_cpp"]), "src": src}
