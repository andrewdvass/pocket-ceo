"""Canadian personal and small-corporation tax engine driven by shared/rates/<year>.json.

Scope: federal + provincial/territorial income tax, CPP/QPP (both halves for the self-employed),
CPP2, EI (employees, or self-employed who opt in), QPIP, Canadian dividends, Ontario surtax and
health premium, Ontario and BC low-income tax reductions, Manitoba and federal/Yukon basic personal
amount phase-outs, Quebec abatement.

Not modelled (say so when it matters): other personal credits (spouse, tuition, medical, donations,
age), low-income reductions in NB/NL/NS/PE, alternative minimum tax, OAS/EI clawbacks, refundable
benefits, Quebec-specific deductions. Quebec results are an estimate.
"""
from . import r2


def _bracket_tax(brackets, income):
    tax = 0.0
    for i, b in enumerate(brackets):
        lo = b["over"]
        hi = brackets[i + 1]["over"] if i + 1 < len(brackets) else float("inf")
        if income > lo:
            tax += (min(income, hi) - lo) * b["rate"]
    return tax


def _phase(maxv, minv, start, end, income):
    if income <= start:
        return maxv
    if income >= end:
        return minv
    return maxv - (income - start) * (maxv - minv) / (end - start)


def federal_bpa(R, net_income):
    b = R["federal"]["bpa"]
    return _phase(b["max"], b["min"], b["phase_start"], b["phase_end"], net_income)


def contributions(R, prov, employment=0.0, self_employed=0.0, ei_optin=False, ei_exempt=False):
    """CPP/QPP, CPP2, EI and QPIP for one person. Returns amounts plus the tax treatment pieces."""
    qc = prov == "QC"
    P = R["qpp"] if qc else R["cpp"]
    emp, se = max(0.0, employment), max(0.0, self_employed)
    ex, ympe, yampe = P["basic_exemption"], P["ympe"], P["yampe"]
    emp_earn = max(0.0, min(emp, ympe) - ex)
    se_earn = max(0.0, min(emp + se, ympe) - ex) - emp_earn
    emp2 = max(0.0, min(emp, yampe) - ympe)
    se2 = max(0.0, min(emp + se, yampe) - ympe) - emp2
    base, add, r2nd = P["base_rate"], P["first_additional_rate"], P["cpp2_rate"]
    out = {
        "cpp_employee": emp_earn * (base + add), "cpp2_employee": emp2 * r2nd,
        "cpp_employer": emp_earn * (base + add), "cpp2_employer": emp2 * r2nd,
        "cpp_self_employed": se_earn * 2 * (base + add), "cpp2_self_employed": se2 * 2 * r2nd,
        # credit is on the base employee share; the rest is a deduction from income
        "credit_base": (emp_earn + se_earn) * base,
        "deduction": emp_earn * add + emp2 * r2nd + se_earn * (base + 2 * add) + se2 * 2 * r2nd,
        "plan": "QPP" if qc else "CPP",
    }
    E = R["ei"]
    rate = E["quebec_employee_rate"] if qc else E["employee_rate"]
    ins_emp = 0.0 if ei_exempt else min(emp, E["max_insurable"])
    out["ei_employee"] = ins_emp * rate
    out["ei_employer"] = out["ei_employee"] * E["employer_multiplier"]
    out["ei_self_employed"] = min(se, E["max_insurable"] - ins_emp) * rate if ei_optin else 0.0
    out["qpip_employee"] = out["qpip_employer"] = out["qpip_self_employed"] = 0.0
    out["qpip_deduction"] = 0.0
    if qc:
        Q = R["qpip"]
        qi_emp = min(emp, Q["max_insurable"])
        qi_se = min(se, Q["max_insurable"] - qi_emp)
        out["qpip_employee"] = qi_emp * Q["employee_rate"]
        out["qpip_employer"] = qi_emp * Q["employer_rate"]
        out["qpip_self_employed"] = qi_se * Q["self_employed_rate"]
        out["qpip_deduction"] = qi_se * (Q["self_employed_rate"] - Q["employee_rate"])
    return out


def personal_tax(R, prov, employment=0.0, self_employed=0.0, other=0.0, eligible_dividends=0.0,
                 non_eligible_dividends=0.0, deductions=0.0, ei_optin=False, ei_exempt=False,
                 low_income_reductions=True, payroll=True):
    """Tax and contributions for one person for the year. Amounts are actual dollars received
    (dividends are grossed up inside). `deductions` = RRSP and similar. `payroll=False` skips
    CPP/EI entirely (used to reproduce published tax-only marginal rate tables)."""
    F, PV = R["federal"], R["provinces"][prov]
    c = contributions(R, prov, employment, self_employed, ei_optin, ei_exempt) if payroll else \
        {k: 0.0 for k in ("cpp_employee cpp2_employee cpp_employer cpp2_employer cpp_self_employed "
                          "cpp2_self_employed credit_base deduction ei_employee ei_employer ei_self_employed "
                          "qpip_employee qpip_employer qpip_self_employed qpip_deduction").split()}
    ge, gn = F["dividends"]["eligible"], F["dividends"]["non_eligible"]
    tde = eligible_dividends * (1 + ge["gross_up"])
    tdn = non_eligible_dividends * (1 + gn["gross_up"])
    net = max(0.0, employment + self_employed + other + tde + tdn - deductions - c["deduction"] - c["qpip_deduction"])
    taxable = net
    ei_paid = c["ei_employee"] + c["ei_self_employed"]
    qpip_credit = c["qpip_employee"] + (c["qpip_self_employed"] - c["qpip_deduction"])

    # federal
    fcr = F["credit_rate"]
    f_amounts = federal_bpa(R, net) + min(F["canada_employment_amount"], max(0.0, employment)) + c["credit_base"] + ei_paid + qpip_credit
    f_basic = max(0.0, _bracket_tax(F["brackets"], taxable) - fcr * f_amounts)
    f_tax = max(0.0, f_basic - tde * ge["dtc"] - tdn * gn["dtc"])
    if prov == "QC":
        f_tax = max(0.0, f_tax - F["quebec_abatement"] * f_tax)

    # provincial / territorial
    pcr = PV.get("credit_rate", PV["brackets"][0]["rate"])
    if PV.get("bpa_mirrors_federal"):
        pbpa = federal_bpa(R, net)
    elif PV.get("bpa_phase_out"):
        ph = PV["bpa_phase_out"]
        pbpa = _phase(PV["bpa"], 0.0, ph["start"], ph["end"], net)
    else:
        pbpa = PV["bpa"]
    p_amounts = pbpa
    if prov != "QC":  # Quebec's basic amount already stands in for QPP/QPIP/EI credits
        p_amounts += c["credit_base"] + ei_paid
    if prov == "YT":
        p_amounts += min(F["canada_employment_amount"], max(0.0, employment))
    p_basic = max(0.0, _bracket_tax(PV["brackets"], taxable) - pcr * p_amounts)
    surtax = 0.0
    for s in PV.get("surtax", []):
        surtax += max(0.0, p_basic - s["over"]) * s["rate"]
    p_tax = max(0.0, p_basic + surtax - tde * PV["dividends"]["eligible_dtc"] - tdn * PV["dividends"]["non_eligible_dtc"])
    reduction = 0.0
    if low_income_reductions and PV.get("tax_reduction"):
        tr = PV["tax_reduction"]
        if "basic" in tr:  # Ontario
            reduction = min(p_tax, max(0.0, 2 * tr["basic"] - p_tax))
        else:  # British Columbia
            reduction = min(p_tax, max(0.0, tr["max"] - max(0.0, net - tr["phase_start"]) * tr["rate"]))
    p_tax -= reduction
    premium = 0.0
    if low_income_reductions:
        for band in PV.get("health_premium", []):
            if taxable > band["over"]:
                premium = min(band["max"], band["base"] + (taxable - band["over"]) * band["rate"])
    p_tax += premium

    cpp_total = c["cpp_employee"] + c["cpp2_employee"] + c["cpp_self_employed"] + c["cpp2_self_employed"]
    qpip_total = c["qpip_employee"] + c["qpip_self_employed"]
    income_tax = f_tax + p_tax
    total = income_tax + cpp_total + ei_paid + qpip_total
    cash_in = employment + self_employed + other + eligible_dividends + non_eligible_dividends
    return {
        "province": prov, "cash_income": r2(cash_in), "taxable_income": r2(taxable),
        "federal_tax": r2(f_tax), "provincial_tax": r2(p_tax), "income_tax": r2(income_tax),
        "ontario_health_premium": r2(premium), "ontario_surtax": r2(surtax), "low_income_reduction": r2(reduction),
        "pension_plan": c.get("plan", "CPP"),
        "cpp": r2(c["cpp_employee"] + c["cpp_self_employed"]), "cpp2": r2(c["cpp2_employee"] + c["cpp2_self_employed"]),
        "ei": r2(ei_paid), "qpip": r2(qpip_total),
        "employer_cpp": r2(c["cpp_employer"] + c["cpp2_employer"]), "employer_ei": r2(c["ei_employer"]),
        "employer_qpip": r2(c["qpip_employer"]),
        "total_tax_and_contributions": r2(total), "after_tax_cash": r2(cash_in - total - deductions),
        "average_rate": round(total / cash_in, 4) if cash_in else 0.0,
    }


def marginal_rate(R, prov, kind="other", step=100.0, **base):
    """Extra tax per extra dollar of `kind` income on top of `base` (same keyword names as personal_tax)."""
    key = {"other": "other", "employment": "employment", "self_employed": "self_employed",
           "eligible_dividends": "eligible_dividends", "non_eligible_dividends": "non_eligible_dividends"}[kind]
    a = personal_tax(R, prov, **base)
    b2 = dict(base); b2[key] = b2.get(key, 0.0) + step
    b = personal_tax(R, prov, **b2)
    return (b["total_tax_and_contributions"] - a["total_tax_and_contributions"]) / step


def _notes(R, prov):
    n = list(R["provinces"][prov].get("notes", []))
    if R.get("_warning"):
        n.insert(0, R["_warning"])
    return n


def set_aside(R, prov, net_business_income, employment=0.0, other=0.0, deductions=0.0, ei_optin=False,
              revenue=None):
    """How much of what a sole proprietor earns should be parked for tax and CPP."""
    with_biz = personal_tax(R, prov, employment=employment, self_employed=net_business_income, other=other,
                            deductions=deductions, ei_optin=ei_optin)
    without = personal_tax(R, prov, employment=employment, other=other, deductions=0.0)
    owing = max(0.0, with_biz["total_tax_and_contributions"] - without["total_tax_and_contributions"])
    pct_profit = owing / net_business_income if net_business_income > 0 else 0.0
    import math
    out = {
        "province": prov, "net_business_income": r2(net_business_income),
        "tax_and_cpp_on_business_income": r2(owing),
        "income_tax_part": r2(with_biz["income_tax"] - without["income_tax"]),
        "cpp_part": r2(with_biz["cpp"] + with_biz["cpp2"] - without["cpp"] - without["cpp2"]),
        "ei_part": r2(with_biz["ei"] - without["ei"]), "qpip_part": r2(with_biz["qpip"] - without["qpip"]),
        "set_aside_pct_of_profit": math.ceil(pct_profit * 100),
        "per_month": r2(owing / 12),
        "marginal_rate_on_next_dollar": round(marginal_rate(R, prov, "self_employed", employment=employment,
                                                            self_employed=net_business_income, other=other,
                                                            deductions=deductions, ei_optin=ei_optin), 4),
        "detail": with_biz, "notes": _notes(R, prov),
    }
    if revenue:
        out["set_aside_pct_of_revenue"] = math.ceil(owing / revenue * 100)
    st = R["provinces"][prov]["sales_tax"]
    out["sales_tax_reminder"] = ("If you charge %s, the %s%% you collect is never yours: park all of it on top of this."
                                 % ("GST/HST" if st["type"] in ("GST", "HST") else st["type"].replace("+", " and "),
                                    ("%.3f" % (st["gst_hst"] * 100 + (st["pst"] * 100 if st["type"] == "GST+QST" else 0))).rstrip("0").rstrip(".")))
    return out


def instalments(R, prov, net_tax_owing_this_year, net_tax_owing_last_year, net_tax_owing_two_years_ago, year=None):
    I = R["instalments"]
    thr = I["threshold_quebec"] if prov == "QC" else I["threshold_net_tax_owing"]
    required = net_tax_owing_this_year > thr and (net_tax_owing_last_year > thr or net_tax_owing_two_years_ago > thr)
    y = year or R["tax_year"]
    return {
        "required": required, "threshold": thr, "rule": I["rule"],
        "due_dates": ["%d-%s" % (y, d) for d in I["due_dates"]],
        "prior_year_option_each": r2(net_tax_owing_last_year / 4),
        "current_year_option_each": r2(net_tax_owing_this_year / 4),
        "cheapest_safe_option": "prior-year" if net_tax_owing_last_year <= net_tax_owing_this_year else "current-year",
        "note": ("Net tax owing means income tax plus CPP on self-employment, minus tax already withheld. "
                 "Paying the prior-year or no-calculation amount on time avoids instalment interest even if "
                 "this year turns out higher. The current-year option risks interest if the estimate is low."
                 + (" Quebec residents count federal tax only for the CRA test and pay Revenu Québec instalments separately." if prov == "QC" else "")),
    }


def gst_quick_vs_regular(R, prov, sales_before_tax, taxable_expenses_before_tax, kind="services",
                         quick_rate=None, capital_purchases_before_tax=0.0):
    """Compare the regular method with the Quick Method for a business selling in its own province."""
    st = R["provinces"][prov]["sales_tax"]
    Q = R["gst_hst"]["quick_method"]
    rate = st["gst_hst"]
    collected = sales_before_tax * rate
    itc_exp = taxable_expenses_before_tax * rate
    itc_cap = capital_purchases_before_tax * rate
    regular_net = collected - itc_exp - itc_cap
    key = {0.05: "gst_5", 0.13: "hst_13", 0.14: "hst_14", 0.15: "hst_15"}.get(round(rate, 2))
    table = Q["service_rates"] if kind == "services" else Q["goods_rates"]
    qr = quick_rate if quick_rate is not None else table.get(key)
    out = {"province": prov, "gst_hst_rate": rate, "collected": r2(collected),
           "regular": {"input_tax_credits": r2(itc_exp + itc_cap), "remit": r2(regular_net)},
           "eligible_for_quick_method": sales_before_tax * (1 + rate) <= Q["eligibility_limit_sales_incl_tax"],
           "notes": [Q["note"]]}
    if qr is None:
        out["quick"] = None
        out["notes"].append("No verified Quick Method rate on file for this province and business type. Look it up in CRA guide RC4058 and re-run with the rate.")
        return out
    incl = sales_before_tax * (1 + rate)
    quick_net = incl * qr - min(incl, 30000) * Q["first_30000_credit_rate"] - itc_cap
    out["quick"] = {"remittance_rate": qr, "remit": r2(quick_net), "rate_verified": bool(Q.get("verified")) or quick_rate is not None}
    diff = regular_net - quick_net
    out["quick_saves"] = r2(diff)
    out["recommendation"] = ("Quick Method keeps about $%s more a year." % format(round(diff), ",") if diff > 50 else
                             "Regular method is better by about $%s a year." % format(round(-diff), ",") if diff < -50 else
                             "About the same; the Quick Method is still less bookkeeping.")
    if not out["eligible_for_quick_method"]:
        out["recommendation"] = "Not eligible for the Quick Method: sales including tax are over $400,000."
    if not out["quick"]["rate_verified"]:
        out["notes"].append(Q["verify_note"])
    if st["pst"]:
        out["notes"].append("%s (%.3g%%) is separate from this comparison and is handled with %s." % (st["pst_name"], st["pst"] * 100, st["pst_collector"]))
    return out


def gst_threshold_watch(R, quarterly_sales):
    """quarterly_sales: list of (label, taxable sales) in date order, calendar quarters.
    Finds when the $30,000 small-supplier limit is crossed."""
    lim = R["gst_hst"]["small_supplier_threshold"]
    rows, crossed = [], None
    for i, (label, amt) in enumerate(quarterly_sales):
        window = sum(a for _, a in quarterly_sales[max(0, i - 3): i + 1])
        rows.append({"quarter": label, "sales": r2(amt), "last_four_quarters": r2(window)})
        if crossed is None and (amt > lim or window > lim):
            crossed = {"quarter": label, "how": "single quarter" if amt > lim else "four quarters",
                       "what_it_means": ("Registered from the sale that crossed $30,000: charge GST/HST from that sale on."
                                         if amt > lim else
                                         "Small-supplier status ends one month after this quarter: register and start charging GST/HST by then.")}
    last = rows[-1]["last_four_quarters"] if rows else 0.0
    return {"limit": lim, "quarters": rows, "crossed": crossed, "room_left": r2(max(0.0, lim - last)),
            "rule": R["gst_hst"]["small_supplier_rule"]}


def corporate_small_rate(R, prov):
    C = R["provinces"][prov]["corporate"]
    small = C["small"]
    ch = C.get("small_change")
    if ch and ch["method"] == "prorate_days":
        import datetime
        y = R["tax_year"]
        d0, d1, dc = datetime.date(y, 1, 1), datetime.date(y + 1, 1, 1), datetime.date.fromisoformat(ch["date"])
        if d0 < dc < d1:
            small = (small * (dc - d0).days + ch["rate"] * (d1 - dc).days) / (d1 - d0).days
    return 0.09 + small, small


def salary_vs_dividend(R, prov, profit_before_owner_pay, other_income=0.0):
    """An owner-manager's corporation has `profit_before_owner_pay` and pays it all out, either as
    salary or as non-eligible dividends. Calendar-year CCPC under the small business limit; the
    owner holds more than 40% of the votes, so no EI."""
    P = profit_before_owner_pay
    # all salary: salary + employer CPP = P  (solve by bisection; employer CPP is monotone)
    lo, hi = 0.0, P
    for _ in range(60):
        mid = (lo + hi) / 2
        c = contributions(R, prov, employment=mid, ei_exempt=True)
        cost = mid + c["cpp_employer"] + c["cpp2_employer"] + c["qpip_employer"]
        if cost > P:
            hi = mid
        else:
            lo = mid
    salary = lo
    s = personal_tax(R, prov, employment=salary, other=other_income, ei_exempt=True)
    base = personal_tax(R, prov, other=other_income)
    sal = {"salary": r2(salary), "employer_cpp": s["employer_cpp"], "corporate_tax": 0.0,
           "personal_income_tax": r2(s["income_tax"] - base["income_tax"]),
           "employee_cpp": r2(s["cpp"] + s["cpp2"]),
           "total_cpp_paid": r2(s["cpp"] + s["cpp2"] + s["employer_cpp"]),
           "owner_keeps": r2(salary - (s["income_tax"] - base["income_tax"]) - s["cpp"] - s["cpp2"] - s["qpip"]),
           "rrsp_room_created": r2(min(salary * 0.18, 0.18 * 200000))}
    rate, prov_small = corporate_small_rate(R, prov)
    limit = R["provinces"][prov]["corporate"]["small_business_limit"]
    corp_tax = P * rate
    div = P - corp_tax
    d = personal_tax(R, prov, non_eligible_dividends=div, other=other_income)
    dv = {"dividend": r2(div), "corporate_tax": r2(corp_tax), "corporate_rate": round(rate, 5),
          "personal_income_tax": r2(d["income_tax"] - base["income_tax"]), "total_cpp_paid": 0.0,
          "owner_keeps": r2(div - (d["income_tax"] - base["income_tax"])), "rrsp_room_created": 0.0}
    diff = dv["owner_keeps"] - sal["owner_keeps"]
    notes = _notes(R, prov) + [
        "Salary pays into CPP (about $%s here), which buys a bigger CPP pension later; dividends pay nothing in and earn no CPP." % format(round(sal["total_cpp_paid"]), ","),
        "Salary creates RRSP room and is simpler for mortgages and child-care deductions; dividends do not.",
        "This assumes all profit is paid out. Leaving profit in the company defers the personal tax, which is the main advantage of a corporation.",
        "Not modelled: alternative minimum tax, tax on split income (dividends to family), personal credits beyond the basic amount.",
    ]
    cn = R["provinces"][prov]["corporate"].get("note")
    if cn:
        notes.append(cn)
    if P > limit:
        notes.append("Profit is over the %s small business limit; the part above it is taxed at the general rate and this comparison understates corporate tax." % ("$" + format(limit, ",")))
    return {"province": prov, "profit_before_owner_pay": r2(P), "all_salary": sal, "all_dividends": dv,
            "dividends_keep_more_by": r2(diff),
            "verdict": ("Dividends leave about $%s more in your pocket this year, but skip CPP." % format(round(diff), ",") if diff > 200 else
                        "Salary leaves about $%s more in your pocket this year, and builds CPP and RRSP room." % format(round(-diff), ",") if diff < -200 else
                        "Close to a tie this year; salary also builds CPP and RRSP room."),
            "notes": notes}


def employee_cost(R, prov, annual_salary):
    """What an employee really costs the employer, and what the employee takes home (basic credits only)."""
    c = contributions(R, prov, employment=annual_salary)
    t = personal_tax(R, prov, employment=annual_salary)
    employer = c["cpp_employer"] + c["cpp2_employer"] + c["ei_employer"] + c["qpip_employer"]
    return {"province": prov, "salary": r2(annual_salary), "employer_cpp": r2(c["cpp_employer"] + c["cpp2_employer"]),
            "employer_ei": r2(c["ei_employer"]), "employer_qpip": r2(c["qpip_employer"]),
            "employer_total_on_top": r2(employer), "true_annual_cost_before_wcb_and_vacation": r2(annual_salary + employer),
            "employee_take_home_estimate": t["after_tax_cash"], "employee_deductions": t,
            "notes": ["Not included: workers' compensation premiums, vacation pay (at least 4%), statutory holidays, provincial payroll or health taxes above their exemptions, benefits."]}
