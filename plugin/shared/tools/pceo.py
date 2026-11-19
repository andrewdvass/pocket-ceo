#!/usr/bin/env python3
"""Pocket CEO money tools. Python 3.8+ standard library only.

  python3 pceo.py tax set-aside --profit 80000            how much of each payment to park for tax
  python3 pceo.py tax estimate --self-employed 80000      full tax and CPP estimate
  python3 pceo.py tax instalments --this-year 6000 --last-year 4500 --two-years-ago 0
  python3 pceo.py tax gst-compare --sales 90000 --expenses 12000     regular vs Quick Method
  python3 pceo.py tax gst-watch [--from-bank | 2026Q1=8000 2026Q2=9500 ...]
  python3 pceo.py tax salary-dividend --profit 120000     corporation owner pay
  python3 pceo.py tax employee-cost --salary 48000        first hire
  python3 pceo.py rates get provinces.ON.brackets         read the rates file
  python3 pceo.py money import ~/Downloads/statement.csv [--account "RBC chequing"] [--flip]
  python3 pceo.py money review | learn "TIM HORTONS" "Meals and entertainment" --business 100
  python3 pceo.py money set <id> --category "Office expenses" --business 100
  python3 pceo.py money summary --year 2026 | recurring | balance
  python3 pceo.py money expect 2026-12-15 -8400 "New truck"
  python3 pceo.py cash forecast [--balance 12000] [--floor 2000] [--conservative]
  python3 pceo.py cash afford 8400 2027-03-01 --what "truck"
  python3 pceo.py cash brief
  python3 pceo.py brief money                              all money lines for the morning brief
  python3 pceo.py contract redline lease.docx changes.json "lease - requested changes.docx"
  python3 pceo.py contract text lease.docx                 read a Word contract as plain text
  python3 pceo.py receipts reconcile --year 2026
  python3 pceo.py yearend build --year 2026
  python3 pceo.py invoices add "Sarah Chen" 1200 [--due 2026-12-01] | paid INV-2026-001 | aging | match
  python3 pceo.py mileage place "Dr. Lee clinic" 14 | add 2026-11-19 "Dr. Lee clinic" "client visit" | odometer 2026-01-01 48210 | summary

Province and GST/HST status default to the owner's profile.md. Add --json to any command for raw data.
"""
import argparse, json, re, sys, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
from pocketceo import load_rates, data_dir, province_code, money, source_lines  # noqa: E402
from pocketceo import tax, bank, cashflow, reconcile, yearend  # noqa: E402
from pocketceo import collections_ as inv  # noqa: E402
from pocketceo import mileage, brief, redline  # noqa: E402


def profile():
    p = data_dir() / "profile.md"
    out = {}
    if p.exists():
        t = p.read_text(encoding="utf-8")
        m = re.search(r"\*\*Province / territory:\*\*\s*(.+)", t)
        if m and m.group(1).strip():
            try:
                out["province"] = province_code(m.group(1).strip())
            except SystemExit:
                pass
        m = re.search(r"\*\*Charges GST/HST:\*\*\s*(\w+)", t)
        if m:
            out["gst"] = m.group(1).lower().startswith("y")
        m = re.search(r"\*\*Structure:\*\*\s*(.+)", t)
        if m and "corporation" in m.group(1).lower() and "/" not in m.group(1):
            out["structure"] = "corporation"
        m = re.search(r"\*\*Employees / contractors:\*\*\s*(.+)", t)
        if m and re.search(r"\b[1-9]\d* employee|employees?:?\s*[1-9]|\byes\b", m.group(1).lower()):
            out["employees"] = True
    return out


def prov_of(a):
    if getattr(a, "province", None):
        return province_code(a.province)
    p = profile().get("province")
    if not p:
        sys.exit("Province unknown: add --province, or fill in the province in profile.md.")
    return p


def out(a, data, text):
    if a.json:
        print(json.dumps(data, indent=1, default=str))
    else:
        print(text)


M = lambda x: money(x)
_day = lambda iso: datetime.date.fromisoformat(iso).strftime("%B %-d, %Y")
MC = lambda x: money(x, True)


def cites(R, ids):
    return "\n".join("Source: " + s for s in source_lines(R, ids))


# ---------- tax ----------
def c_set_aside(a):
    R = load_rates(a.year); p = prov_of(a)
    s = tax.set_aside(R, p, a.profit, employment=a.employment, other=a.other, deductions=a.rrsp, ei_optin=a.ei, revenue=a.revenue)
    t = ["Set aside %d%% of profit (about %s a month)." % (s["set_aside_pct_of_profit"], M(s["per_month"])),
         "On %s of %s business profit: %s total = income tax %s + %s %s%s%s." % (
             M(a.profit), R["provinces"][p]["name"], M(s["tax_and_cpp_on_business_income"]), M(s["income_tax_part"]),
             s["detail"]["pension_plan"], M(s["cpp_part"]),
             (" + EI " + M(s["ei_part"])) if s["ei_part"] else "", (" + QPIP " + M(s["qpip_part"])) if s["qpip_part"] else "")]
    if a.revenue:
        t.append("As a share of every payment that comes in: %d%%." % s["set_aside_pct_of_revenue"])
    t.append("Each extra dollar of profit costs about %.0f cents in tax and CPP." % (s["marginal_rate_on_next_dollar"] * 100))
    t.append("For %d: pay the balance by %s (interest starts the next day); self-employed returns are due %s. If you owed over %s last year too, CRA may expect instalments: run tax instalments." % (
        R["tax_year"], _day(s["due"]["pay_by"]), _day(s["due"]["file_by"]), M(R["instalments"]["threshold_quebec" if p == "QC" else "threshold_net_tax_owing"])))
    t.append(s["sales_tax_reminder"])
    t += ["Note: " + n for n in s["notes"]]
    t.append("Basic credits only (no RRSP, spouse, tuition, medical or donation credits unless given).")
    t.append(cites(R, ["cra_t4127", "tt_rates", "tt_cpp"]))
    out(a, s, "\n".join(t))


def c_estimate(a):
    R = load_rates(a.year); p = prov_of(a)
    r = tax.personal_tax(R, p, employment=a.employment, self_employed=a.self_employed, other=a.other,
                         eligible_dividends=a.eligible, non_eligible_dividends=a.non_eligible, deductions=a.rrsp,
                         ei_optin=a.ei)
    t = ["%s, %d estimate on %s of income:" % (R["provinces"][p]["name"], R["tax_year"], M(r["cash_income"])),
         "  Federal tax %s, provincial tax %s%s" % (M(r["federal_tax"]), M(r["provincial_tax"]),
                                                   (" (incl. Ontario Health Premium %s)" % M(r["ontario_health_premium"])) if r["ontario_health_premium"] else ""),
         "  %s %s, CPP2 %s, EI %s%s" % (r["pension_plan"], M(r["cpp"]), M(r["cpp2"]), M(r["ei"]), (", QPIP " + M(r["qpip"])) if r["qpip"] else ""),
         "  Total %s (%.1f%% of income). You keep %s." % (M(r["total_tax_and_contributions"]), r["average_rate"] * 100, M(r["after_tax_cash"]))]
    t.append("Each extra dollar of %s costs about %.0f cents." % (
        "self-employment income" if a.self_employed else "income",
        100 * tax.marginal_rate(R, p, "self_employed" if a.self_employed else "employment" if a.employment else "other",
                                employment=a.employment, self_employed=a.self_employed, other=a.other,
                                eligible_dividends=a.eligible, non_eligible_dividends=a.non_eligible, deductions=a.rrsp, ei_optin=a.ei)))
    t += ["Note: " + n for n in R["provinces"][p].get("notes", [])]
    t.append(cites(R, ["cra_t4127", "tt_rates"]))
    out(a, r, "\n".join(t))


def c_instal(a):
    R = load_rates(a.year); p = prov_of(a)
    r = tax.instalments(R, p, a.this_year, a.last_year, a.two_years_ago, a.year)
    if r["required"]:
        t = ["Yes, instalments are required (net tax owing over %s this year and in a recent year)." % M(r["threshold"]),
             "Prior-year option: %s on each of %s." % (MC(r["prior_year_option_each"]), ", ".join(r["due_dates"])),
             "Current-year option: %s each." % MC(r["current_year_option_each"]),
             "Lowest safe choice: the %s option." % r["cheapest_safe_option"]]
    else:
        t = ["No instalments needed. The rule: %s (threshold %s)." % (r["rule"], M(r["threshold"]))]
    t.append(r["note"]); t.append(cites(R, ["cra_inst"]))
    out(a, r, "\n".join(t))


def c_gst_compare(a):
    R = load_rates(a.year); p = prov_of(a)
    r = tax.gst_quick_vs_regular(R, p, a.sales, a.expenses, "goods" if a.goods else "services", a.quick_rate, a.capital)
    t = ["%s at %g%%: you collect %s." % (R["provinces"][p]["name"], r["gst_hst_rate"] * 100, M(r["collected"])),
         "Regular method: remit %s (after %s of input tax credits)." % (M(r["regular"]["remit"]), M(r["regular"]["input_tax_credits"]))]
    if r["quick"]:
        t.append("Quick Method at %g%%: remit %s." % (r["quick"]["remittance_rate"] * 100, M(r["quick"]["remit"])))
        t.append(r["recommendation"])
    t += ["Note: " + n for n in r["notes"]]
    t.append(cites(R, ["cra_rc4058", "tt_sales"]))
    out(a, r, "\n".join(t))


def _quarters_from_bank():
    q = {}
    for t in bank.load_ledger():
        if t["category"] == bank.INCOME:
            y, m = int(t["date"][:4]), int(t["date"][5:7])
            k = "%dQ%d" % (y, (m - 1) // 3 + 1)
            q[k] = q.get(k, 0) + t["amount"]
    return sorted(q.items())


def c_gst_watch(a):
    R = load_rates(a.year)
    qs = _quarters_from_bank() if a.from_bank or not a.quarters else [(k, float(v)) for k, v in (x.split("=") for x in a.quarters)]
    r = tax.gst_threshold_watch(R, qs)
    t = ["Taxable sales by quarter: " + ", ".join("%s %s" % (x["quarter"], M(x["sales"])) for x in r["quarters"])]
    if r["crossed"]:
        t.append("You passed $30,000 in %s (%s). %s" % (r["crossed"]["quarter"], r["crossed"]["how"], r["crossed"]["what_it_means"]))
    else:
        t.append("Under the $30,000 small-supplier limit. Room left in the last four quarters: %s." % M(r["room_left"]))
    t.append("Bank deposits can include transfers and loans; count only sales." if a.from_bank or not a.quarters else "")
    t.append(cites(R, ["tt_gst"]))
    out(a, r, "\n".join(x for x in t if x))


def c_sal_div(a):
    R = load_rates(a.year); p = prov_of(a)
    r = tax.salary_vs_dividend(R, p, a.profit, a.other)
    s, d = r["all_salary"], r["all_dividends"]
    t = [r["verdict"],
         "All salary: pay yourself %s; income tax %s, CPP %s (both halves); you keep %s." % (
             M(s["salary"]), M(s["personal_income_tax"]), M(s["total_cpp_paid"]), M(s["owner_keeps"])),
         "All dividends: company pays %s corporate tax (%.1f%%); dividend %s; personal tax %s; you keep %s." % (
             M(d["corporate_tax"]), d["corporate_rate"] * 100, M(d["dividend"]), M(d["personal_income_tax"]), M(d["owner_keeps"]))]
    t += ["Note: " + n for n in r["notes"]]
    t.append(cites(R, ["cra_t4127", "tt_corp", "tt_dtc_n"]))
    out(a, r, "\n".join(t))


def c_emp(a):
    R = load_rates(a.year); p = prov_of(a)
    r = tax.employee_cost(R, p, a.salary)
    t = ["A %s salary costs you %s a year before workers' comp and vacation pay:" % (M(a.salary), M(r["true_annual_cost_before_wcb_and_vacation"])),
         "  employer CPP %s, employer EI %s%s" % (MC(r["employer_cpp"]), MC(r["employer_ei"]), (", employer QPIP " + MC(r["employer_qpip"])) if r["employer_qpip"] else ""),
         "The employee takes home about %s (basic credits only)." % M(r["employee_take_home_estimate"])] + ["Note: " + n for n in r["notes"]]
    t.append(cites(R, ["cra_t4127"]))
    out(a, r, "\n".join(t))


def c_rates(a):
    R = load_rates(a.year)
    node = R
    for k in (a.path or "").split("."):
        if k:
            node = node[k] if isinstance(node, dict) else node[int(k)]
    print(json.dumps(node, indent=1, ensure_ascii=False))


# ---------- money ----------
def c_import(a):
    r = bank.import_file(a.file, a.account or "", a.dmy, a.flip)
    t = ["Read %d transactions from %s to %s (%s in, %s out)." % (r["rows"], r["from"], r["to"], M(r["money_in"]), M(r["money_out"])),
         "%d new, %d already imported. %d need your review." % (r["new"], r["already_had"], r["needs_review"])]
    if r.get("last_balance") is not None:
        t.append("Last balance in the file: %s. Does that match your bank?" % MC(r["last_balance"]))
    if r.get("warning"):
        t.append("Warning: " + r["warning"])
    out(a, r, "\n".join(t))


def c_review(a):
    r = bank.review_list(a.limit)
    t = ["%s: %d transactions, %s (last %s, example id %s)" % (g["merchant"], g["count"], MC(g["total"]), g["last"], g["example_id"]) for g in r]
    out(a, r, "\n".join(t) or "Nothing to review.")


def c_learn(a):
    n = bank.learn(a.pattern, a.category, a.business)
    out(a, {"changed": n}, "Saved: anything with \"%s\" is %s, %g%% business. Updated %d transactions." % (a.pattern.upper(), a.category, a.business, n))


def c_set(a):
    t = bank.set_row(a.id, a.category, a.business, a.note)
    out(a, t, "Updated %s %s %s: %s, %g%% business." % (t["date"], t["description"], MC(t["amount"]), t["category"], t["business_pct"]))


def c_summary(a):
    r = bank.summary(a.year, a.month)
    t = ["Business income %s, business expenses %s, profit %s (%d transactions)." % (M(r["business_income"]), M(r["business_expenses"]), M(r["profit"]), r["rows"])]
    for k, v in sorted(r["by_category"].items(), key=lambda kv: kv[1]["total"]):
        t.append("  %-40s %4d  %12s%s" % (k, v["count"], MC(v["total"]), ("  business " + MC(v["business"])) if v["business"] else ""))
    out(a, r, "\n".join(t))


def c_recurring(a):
    r = cashflow.recurring()
    t = ["%-28s %-15s %12s  next %s  (%s/month)" % (x["name"], x["cadence"], MC(x["typical"]), x["next"], MC(x["monthly_equivalent"])) for x in r]
    out(a, r, "\n".join(t) or "No repeating bills or income found yet (needs about 3 months of history).")


def c_expect(a):
    cashflow.add_expected(a.date, a.amount, a.description, a.kind)
    out(a, {"ok": True}, "Added to the forecast: %s %s on %s." % (a.description, MC(a.amount), a.date))


def c_balance(a):
    r = cashflow.current_balance()
    out(a, r, "\n".join("%s: %s (as of %s)" % (k, MC(v["balance"]), v["as_of"]) for k, v in r.items()) or "No balances in the imported files. Pass --balance.")


def _start_balance(a):
    if a.balance is not None:
        return a.balance
    b = cashflow.current_balance()
    if not b:
        sys.exit("No balance in the bank files. Pass --balance with today's total cash.")
    return sum(v["balance"] for v in b.values())


def _tax_items(a):
    R = load_rates(a.year)
    items = []
    gst = a.gst or ("quarterly" if profile().get("gst") else None)
    if gst:
        items += cashflow.gst_estimates(R, prov_of(a), period=gst)
    if a.instalment:
        items += cashflow.instalment_items(R, a.instalment)
    return items


def c_forecast(a):
    f = cashflow.forecast(_start_balance(a), weeks=a.weeks, floor=a.floor, include_average_income=not a.conservative, tax_items=_tax_items(a))
    t = ["13-week cash forecast from %s (start %s):" % (f["as_of"], MC(f["start_balance"]))]
    for w in f["weeks"]:
        flag = "  <-- below %s" % M(a.floor) if w["end_balance"] < a.floor else ""
        big = ", ".join("%s %s" % (i["what"].split(" (")[0], M(i["amount"])) for i in w["items"] if abs(i["amount"]) >= 300)
        t.append("  wk of %s  in %10s  out %10s  end %11s%s%s" % (w["week_of"], M(w["in"]), M(w["out"]), M(w["end_balance"]), flag, ("  [" + big + "]") if big else ""))
    lw = f["lowest_week"]
    t.append("Lowest week: %s (week of %s)." % (M(lw["balance"]), lw["week_of"]))
    s = f["assumptions"]
    t.append("Assumes everyday spending of %s/week%s, plus %d repeating bills/income and %d planned items." % (
        M(-s["everyday_spending_per_week"]), (" and everyday income of %s/week" % M(s["everyday_income_per_week"])) if s["average_income_included"] else ", no income beyond known repeating deposits",
        s["recurring_items"], s["planned_items"]))
    out(a, f, "\n".join(t))


def c_afford(a):
    r = cashflow.afford(_start_balance(a), a.amount, a.date, a.what, floor=a.floor,
                        include_average_income=not a.conservative, tax_items=_tax_items(a))
    out(a, r, r["answer"] + "\nWithout it, your lowest week is %s (week of %s)." % (M(r["lowest_week_without"]["balance"]), r["lowest_week_without"]["week_of"]))


def c_brief(a):
    line = cashflow.brief_line(_start_balance(a), floor=a.floor, tax_items=_tax_items(a))
    out(a, {"line": line}, line or "")


def c_reconcile(a):
    r = reconcile.reconcile(a.year, a.min)
    t = [r["headline"], "Checked %d business purchases; %d matched a receipt." % (r["bank_purchases_checked"], r["matched"])]
    groups = {}
    for m in r["missing_receipts"]:
        k = cashflow._merchant(m["description"]) or m["description"][:30].upper()
        g = groups.setdefault(k, {"n": 0, "total": 0.0, "dates": [], "cat": m["category"]})
        g["n"] += 1; g["total"] += m["amount"]; g["dates"].append(m["date"])
    t.append("By merchant (biggest first):")
    for k, g in sorted(groups.items(), key=lambda kv: -kv[1]["total"])[: a.limit]:
        when = g["dates"][0] if g["n"] == 1 else "%s to %s" % (min(g["dates"]), max(g["dates"]))
        t.append("  %-28s %2d x  %11s  %s  [%s]" % (k.title()[:28], g["n"], MC(g["total"]), when, g["cat"]))
    if len(groups) > a.limit:
        t.append("  ...and %d more merchants (--json for every row)." % (len(groups) - a.limit))
    if r["receipts_without_bank_match"]:
        t.append("%d receipts have no bank match (cash, or a card not imported yet)." % len(r["receipts_without_bank_match"]))
    out(a, r, "\n".join(t))


def c_yearend(a):
    p = prov_of(a) if (a.province or profile().get("province")) else None
    r = yearend.build(a.year, p)
    t = ["Year-end package for %d is in %s" % (r["year"], r["folder"]),
         "Sales %s, expenses %s, net business income %s." % (M(r["sales"]), M(r["expenses"]), M(r["net_income"])),
         "Summary: %s" % (r["pdf"] or (r["folder"] + "/summary.html"))]
    if r["gst"]:
        t.append("GST/HST net tax (line 109): %s" % M(r["gst"].get("109")))
    t += ["Check: " + w for w in r["warnings"]]
    out(a, r, "\n".join(t))


def c_inv_add(a):
    r = inv.add(a.client, a.amount, a.issued, a.due, a.terms, a.id, a.email or "", a.notes or "")
    out(a, r, "Tracking %s: %s owes %s, due %s." % (r["id"], r["client"], MC(r["amount"]), r["due"]))


def c_inv_paid(a):
    r = inv.mark_paid(a.id, a.amount, a.on)
    out(a, r, "%s is %s (%s received)." % (r["id"], r["status"], MC(r["paid_amount"])))


def c_inv_rem(a):
    inv.log_reminder(a.id, a.stage)
    out(a, {"ok": True}, "Logged a %s reminder on %s." % (a.stage, a.id))


def c_aging(a):
    R = load_rates(a.year)
    p = prov_of(a) if (a.province or profile().get("province")) else None
    r = inv.aging(R, p)
    t = ["Owed to you: %s (%s overdue)." % (M(r["total_owed"]), M(r["overdue"]))]
    for b, items in r["buckets"].items():
        for i in items:
            t.append("  %-8s %-22s %10s  due %s  %3d days late  next: %s%s" % (
                b, i["client"][:22], MC(i["owed"]), i["due"], i["days_late"], i["next_step"], ("  (last reminder " + i["last_reminder"] + ")") if i["last_reminder"] else ""))
    if r.get("small_claims") and r["buckets"]["90+"]:
        sc = r["small_claims"]
        t.append("Small claims limit in your province: %s. %s" % (M(sc["limit"]) if sc["limit"] else "not on file", sc["note"]))
    out(a, r, "\n".join(t))


def c_match(a):
    r = inv.match_deposits()
    out(a, r, "\n".join("%s (%s): deposit %s on %s looks like payment [%s]" % (m["invoice"], m["client"], MC(m["amount"]), m["deposit_date"], m["confidence"]) for m in r) or "No deposits match open invoices.")


def c_mi_place(a):
    mileage.set_place(a.place, a.km)
    out(a, {"ok": True}, "Saved: %s is %g km from home (one way)." % (a.place, a.km))


def c_mi_add(a):
    r = mileage.add(a.date, a.destination, a.purpose, a.km, a.source, a.note or "", not a.one_way)
    out(a, r, ("Logged %s: %s, %g km (%s)." % (r["date"], r["destination"], r["km"], r["purpose"])) if r else "Already logged.")


def c_mi_odo(a):
    mileage.odometer(a.date, a.reading)
    out(a, {"ok": True}, "Odometer %g km saved for %s." % (a.reading, a.date))


def c_mi_sum(a):
    r = mileage.summary(a.year)
    t = ["%d business trips, %s business km%s." % (r["trips"], format(r["business_km"], ",g"),
         (" of %s total km = %s%% business use" % (format(r["total_km"], ",g"), r["business_pct"])) if r["total_km"] else "")]
    if r.get("missing"):
        t.append("Missing: " + r["missing"])
    out(a, r, "\n".join(t))


def c_brief_money(a):
    R = load_rates(a.year)
    pr = profile()
    gst = a.gst or ("quarterly" if pr.get("gst") else None)
    lines = brief.money_lines(R, floor=a.floor, balance=a.balance, gst=gst, structure=pr.get("structure", "sole"),
                              employees=a.employees or pr.get("employees", False), instalment_amount=a.instalment, days=a.days)
    out(a, {"lines": lines}, "\n".join(lines))


def c_redline(a):
    changes = json.loads(Path(a.changes).read_text(encoding="utf-8"))
    r = redline.redline(a.contract, changes, a.out)
    t = ["Tracked-changes copy: %s (%d changes, %d comments)." % (r["file"], r["applied"], r["comments"])]
    for f in r["not_found"]:
        t.append("NOT FOUND, not applied: \"%s\". Copy the exact wording from the contract and try again." % f[:90])
    out(a, r, "\n".join(t))


def c_docx_text(a):
    print(redline.docx_text(a.file))


def main(argv=None):
    ap = argparse.ArgumentParser(prog="pceo", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--year", type=int, default=datetime.date.today().year)
    sub = ap.add_subparsers(dest="group", required=True)

    def cmd(group, name, fn, *args):
        g = groups[group]
        p = g.add_parser(name)
        p.set_defaults(fn=fn)
        p.add_argument("--json", action="store_true", default=argparse.SUPPRESS)
        p.add_argument("--year", type=int, default=argparse.SUPPRESS)
        p.add_argument("--province", default=None)
        for a in args:
            p.add_argument(*a[0], **a[1])
        return p
    groups = {}
    for g in ("tax", "rates", "money", "cash", "receipts", "yearend", "invoices", "mileage", "brief", "contract"):
        groups[g] = sub.add_parser(g).add_subparsers(dest="cmd", required=True)
    f = lambda *n, **k: (n, k)
    num = dict(type=float, default=0.0)
    cmd("tax", "set-aside", c_set_aside, f("--profit", type=float, required=True), f("--employment", **num), f("--other", **num),
        f("--rrsp", **num), f("--revenue", type=float), f("--ei", action="store_true"))
    cmd("tax", "estimate", c_estimate, f("--employment", **num), f("--self-employed", **num), f("--other", **num),
        f("--eligible", **num), f("--non-eligible", **num), f("--rrsp", **num), f("--ei", action="store_true"))
    cmd("tax", "instalments", c_instal, f("--this-year", type=float, required=True), f("--last-year", type=float, required=True),
        f("--two-years-ago", type=float, required=True))
    cmd("tax", "gst-compare", c_gst_compare, f("--sales", type=float, required=True), f("--expenses", **num), f("--capital", **num),
        f("--goods", action="store_true"), f("--quick-rate", type=float))
    cmd("tax", "gst-watch", c_gst_watch, f("quarters", nargs="*"), f("--from-bank", action="store_true"))
    cmd("tax", "salary-dividend", c_sal_div, f("--profit", type=float, required=True), f("--other", **num))
    cmd("tax", "employee-cost", c_emp, f("--salary", type=float, required=True))
    cmd("rates", "get", c_rates, f("path", nargs="?", default=""))
    cmd("money", "import", c_import, f("file"), f("--account"), f("--flip", action="store_true"), f("--dmy", action="store_true"))
    cmd("money", "review", c_review, f("--limit", type=int, default=25))
    cmd("money", "learn", c_learn, f("pattern"), f("category"), f("--business", type=float, default=100))
    cmd("money", "set", c_set, f("id"), f("--category"), f("--business", type=float), f("--note"))
    cmd("money", "summary", c_summary, f("--month", type=int))
    cmd("money", "recurring", c_recurring)
    cmd("money", "expect", c_expect, f("date"), f("amount", type=float), f("description"), f("--kind", default="planned"))
    cmd("money", "balance", c_balance)
    cash_args = [f("--balance", type=float), f("--floor", type=float, default=0.0), f("--conservative", action="store_true"),
                 f("--gst", choices=["quarterly", "annual"]), f("--instalment", type=float)]
    cmd("cash", "forecast", c_forecast, f("--weeks", type=int, default=13), *cash_args)
    cmd("cash", "afford", c_afford, f("amount", type=float), f("date"), f("--what", default="purchase"), *cash_args)
    cmd("cash", "brief", c_brief, *cash_args)
    cmd("receipts", "reconcile", c_reconcile, f("--min", type=float, default=0.0), f("--limit", type=int, default=30))
    cmd("yearend", "build", c_yearend)
    cmd("invoices", "add", c_inv_add, f("client"), f("amount", type=float), f("--issued"), f("--due"), f("--terms", type=int, default=30),
        f("--id"), f("--email"), f("--notes"))
    cmd("invoices", "paid", c_inv_paid, f("id"), f("--amount", type=float), f("--on"))
    cmd("invoices", "reminded", c_inv_rem, f("id"), f("stage", choices=["polite", "firm", "final"]))
    cmd("invoices", "aging", c_aging)
    cmd("invoices", "match", c_match)
    cmd("mileage", "place", c_mi_place, f("place"), f("km", type=float))
    cmd("mileage", "add", c_mi_add, f("date"), f("destination"), f("purpose"), f("--km", type=float), f("--one-way", action="store_true"),
        f("--source", default="owner"), f("--note"))
    cmd("mileage", "odometer", c_mi_odo, f("date"), f("reading", type=float))
    cmd("mileage", "summary", c_mi_sum)
    cmd("brief", "money", c_brief_money, f("--days", type=int, default=14), f("--employees", action="store_true"), *cash_args)
    cmd("contract", "redline", c_redline, f("contract"), f("changes"), f("out"))
    cmd("contract", "text", c_docx_text, f("file"))
    a = ap.parse_args(argv)
    if a.year and not 2000 < a.year < 2100:
        sys.exit("Year looks wrong: %s" % a.year)
    a.fn(a)


if __name__ == "__main__":
    main()
