"""Recurring bills and income, the 13-week cash forecast, "can I afford it?", and the brief line.

Planned items the bank can't know about (an invoice due from a client, a truck in March, a tax
bill) live in <data_dir>/money/expected.csv: date,amount,description,kind. Amount > 0 is money in.
"""
import csv, datetime, re, statistics
from . import data_dir, r2
from .bank import load_ledger, money_dir, _norm, TRANSFER, INCOME, TAXPAY, GSTPAY, NOT_BUSINESS_EXPENSE

D = datetime.date
EXPECTED_FIELDS = ["date", "amount", "description", "kind", "added"]
CADENCES = [("weekly", 7, 2), ("every 2 weeks", 14, 3), ("twice a month", 15, 3), ("monthly", 30.4, 5),
            ("every 3 months", 91, 10), ("yearly", 365, 20)]


def _merchant(desc):
    d = _norm(desc)
    d = re.sub(r"\b(POS|PURCHASE|PREAUTHORIZED|PRE-AUTH|PAP|BILL PAYMENT|PAYMENT|DEBIT|VISA|MC|INTERAC|PURCH|RECURRING|AUTOPAY|ONLINE)\b", " ", d)
    d = re.sub(r"[^A-Z& ]", " ", d)
    return " ".join(d.split()[:3])


def recurring(today=None, lookback_days=200):
    """Find bills and income that repeat on a schedule. Returns a list sorted by size."""
    today = today or D.today()
    rows = [r for r in load_ledger()
            if r["category"] != TRANSFER and (today - D.fromisoformat(r["date"])).days <= lookback_days]
    groups = {}
    for r in rows:
        k = (_merchant(r["description"]), r["amount"] > 0)
        if k[0]:
            groups.setdefault(k, []).append(r)
    found = []
    for (m, is_in), g in groups.items():
        if len(g) < 3:
            continue
        g.sort(key=lambda r: r["date"])
        dates = [D.fromisoformat(r["date"]) for r in g]
        gaps = [(b - a).days for a, b in zip(dates, dates[1:]) if (b - a).days > 0]
        if len(gaps) < 2:
            continue
        med = statistics.median(gaps)
        cad = next((c for c in CADENCES if abs(med - c[1]) <= c[2]), None)
        if not cad:
            continue
        if sum(abs(x - cad[1]) <= cad[2] * 1.5 for x in gaps) < 0.7 * len(gaps):
            continue
        amts = [abs(r["amount"]) for r in g]
        typical = statistics.median(amts)
        if max(amts) > typical * 1.6 and len(g) < 5:
            continue  # amounts too uneven to call it a bill
        last = dates[-1]
        nxt = last + datetime.timedelta(days=round(cad[1]))
        if (today - last).days > cad[1] * 2 + cad[2]:
            continue  # stopped
        found.append({"name": m.title(), "direction": "in" if is_in else "out", "cadence": cad[0], "every_days": cad[1],
                      "typical": r2(typical if is_in else -typical), "last": last.isoformat(), "next": nxt.isoformat(),
                      "times_seen": len(g), "category": g[-1]["category"],
                      "monthly_equivalent": r2((typical if is_in else -typical) * 30.4 / cad[1])})
    return sorted(found, key=lambda x: x["monthly_equivalent"])


def load_expected():
    p = money_dir() / "expected.csv"
    if not p.exists():
        return []
    with open(p, newline="", encoding="utf-8") as f:
        return [dict(r, amount=float(r["amount"])) for r in csv.DictReader(f)]


def add_expected(date, amount, description, kind="planned"):
    p = money_dir() / "expected.csv"
    new = not p.exists()
    with open(p, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=EXPECTED_FIELDS)
        if new:
            w.writeheader()
        w.writerow({"date": date, "amount": "%.2f" % amount, "description": description, "kind": kind,
                    "added": D.today().isoformat()})


def current_balance(today=None):
    """Latest running balance per account from the bank files (credit cards excluded when negative)."""
    best = {}
    for r in load_ledger():
        if r["balance"] is not None and r["date"] <= (today or D.today()).isoformat():
            if r["account"] not in best or r["date"] >= best[r["account"]][0]:
                best[r["account"]] = (r["date"], r["balance"])
    return {a: {"as_of": d, "balance": b} for a, (d, b) in best.items()}


def _week_start(d):
    return d - datetime.timedelta(days=d.weekday())


def forecast(start_balance, today=None, weeks=13, extra=None, include_average_income=True, floor=0.0,
             tax_items=None):
    """Week-by-week cash forecast.
    start_balance: cash today. extra: list of (date, amount, description) to try ("can I afford it").
    tax_items: list of (date, amount, description) for GST/HST remittances and instalments."""
    today = today or D.today()
    end = today + datetime.timedelta(weeks=weeks)
    items = []
    rec = recurring(today)
    for b in rec:
        nxt = D.fromisoformat(b["next"])
        while nxt <= today:
            nxt += datetime.timedelta(days=round(b["every_days"]))
        while nxt < end:
            items.append((nxt, b["typical"], b["name"] + " (" + b["cadence"] + ")", "recurring"))
            nxt += datetime.timedelta(days=round(b["every_days"]))
    for e in load_expected():
        d = D.fromisoformat(e["date"])
        if today <= d < end:
            items.append((d, e["amount"], e["description"], e.get("kind") or "planned"))
    for d, a, desc in (tax_items or []):
        d = D.fromisoformat(d) if isinstance(d, str) else d
        if today <= d < end:
            items.append((d, a, desc, "tax"))
    for d, a, desc in (extra or []):
        d = D.fromisoformat(d) if isinstance(d, str) else d
        items.append((d, a, desc, "what-if"))
    # everyday spending and income that isn't a fixed bill: 90-day weekly average
    rec_names = {b["name"].upper() for b in rec}
    window = [r for r in load_ledger() if 0 <= (today - D.fromisoformat(r["date"])).days < 91
              and r["category"] not in (TRANSFER,) and _merchant(r["description"]) not in rec_names]
    span_weeks = max(1.0, min(13.0, (today - min((D.fromisoformat(r["date"]) for r in window), default=today)).days / 7))
    avg_out = sum(r["amount"] for r in window if r["amount"] < 0) / span_weeks
    avg_in = sum(r["amount"] for r in window if r["amount"] > 0) / span_weeks if include_average_income else 0.0
    rows, bal = [], start_balance
    lowest = None
    w0 = _week_start(today)
    for i in range(weeks):
        ws, we = w0 + datetime.timedelta(weeks=i), w0 + datetime.timedelta(weeks=i + 1)
        wk = [x for x in items if ws <= x[0] < we]
        frac = 1.0 if i else (we - today).days / 7
        cin = sum(a for _, a, _, _ in wk if a > 0) + avg_in * frac
        cout = sum(a for _, a, _, _ in wk if a < 0) + avg_out * frac
        bal += cin + cout
        row = {"week_of": ws.isoformat(), "in": r2(cin), "out": r2(cout), "end_balance": r2(bal),
               "items": [{"date": d.isoformat(), "amount": r2(a), "what": desc, "kind": k} for d, a, desc, k in sorted(wk)]}
        rows.append(row)
        if lowest is None or bal < lowest["end_balance"]:
            lowest = row
    short = [r for r in rows if r["end_balance"] < floor]
    return {"start_balance": r2(start_balance), "as_of": today.isoformat(), "weeks": rows,
            "lowest_week": {"week_of": lowest["week_of"], "balance": lowest["end_balance"]} if lowest else None,
            "first_short_week": short[0]["week_of"] if short else None, "floor": floor,
            "assumptions": {"everyday_spending_per_week": r2(avg_out), "everyday_income_per_week": r2(avg_in),
                            "recurring_items": len(rec), "planned_items": len(load_expected()),
                            "average_income_included": include_average_income}}


def afford(start_balance, amount, when, description="purchase", today=None, floor=0.0, **kw):
    base = forecast(start_balance, today, floor=floor, **kw)
    w = forecast(start_balance, today, floor=floor, extra=[(when, -abs(amount), description)], **kw)
    ok = w["first_short_week"] is None
    lw = w["lowest_week"]
    return {"amount": r2(abs(amount)), "when": when, "can_afford": ok,
            "lowest_week_without": base["lowest_week"], "lowest_week_with": lw,
            "answer": ("Yes. If you buy the %s ($%s) on %s, your lowest week is $%s (week of %s)." %
                       (description, format(round(abs(amount)), ","), when, format(round(lw["balance"]), ","), lw["week_of"]))
                      if ok else
                      ("Not yet. Buying the %s ($%s) on %s takes you below $%s in the week of %s (lowest: $%s)." %
                       (description, format(round(abs(amount)), ","), when, format(round(floor), ","), w["first_short_week"],
                        format(round(lw["balance"]), ","))),
            "forecast": w}


def gst_estimates(R, prov, today=None, period="quarterly", registered=True):
    """Rough GST/HST owing per reporting period from the ledger, with due dates. Uses the standard
    rate; says plainly that it is an estimate."""
    if not registered:
        return []
    today = today or D.today()
    rate = R["provinces"][prov]["sales_tax"]["gst_hst"]
    frac = rate / (1 + rate)
    rows = load_ledger()
    exempt = NOT_BUSINESS_EXPENSE | {"Interest and bank charges", "Insurance", "Salaries, wages, benefits", "Property taxes"}
    def net(a, b):
        sales = sum(r["amount"] for r in rows if r["category"] == INCOME and a <= r["date"] < b)
        itc = sum(-r["amount"] * r["business_pct"] / 100 for r in rows
                  if r["amount"] < 0 and r["category"] not in exempt and a <= r["date"] < b)
        return (sales - itc) * frac
    out = []
    if period == "quarterly":
        for y in (today.year - 1, today.year):
            for q in range(4):
                a, b = D(y, 3 * q + 1, 1), (D(y, 3 * q + 4, 1) if q < 3 else D(y + 1, 1, 1))
                due = (b + datetime.timedelta(days=31)).replace(day=1) - datetime.timedelta(days=1)
                if due >= today and a < today:
                    out.append((due.isoformat(), -r2(max(0.0, net(a.isoformat(), b.isoformat()))),
                                "GST/HST for %d Q%d (estimate)" % (y, q + 1)))
    elif period == "annual":
        a, b = D(today.year - 1, 1, 1), D(today.year, 1, 1)
        due = D(today.year, 4, 30)
        if due >= today:
            out.append((due.isoformat(), -r2(max(0.0, net(a.isoformat(), b.isoformat()))), "GST/HST for %d (estimate, pay by Apr 30)" % a.year))
    return out


def instalment_items(R, amount_each, today=None):
    today = today or D.today()
    out = []
    for y in (today.year, today.year + 1):
        for md in R["instalments"]["due_dates"]:
            d = D.fromisoformat("%d-%s" % (y, md))
            if d >= today:
                out.append((d.isoformat(), -abs(amount_each), "Tax instalment"))
    return out


def brief_line(start_balance, today=None, floor=0.0, **kw):
    """One line for the morning brief, or None when nothing needs attention."""
    today = today or D.today()
    f = forecast(start_balance, today, floor=floor, **kw)
    if f["first_short_week"]:
        return "Cash: heads up, you dip below $%s in the week of %s (lowest $%s)." % (
            format(round(floor), ","), f["first_short_week"], format(round(f["lowest_week"]["balance"]), ","))
    soon = [i for w in f["weeks"][:2] for i in w["items"] if i["amount"] <= -500 and i["date"] <= (today + datetime.timedelta(days=7)).isoformat()]
    tax = [i for w in f["weeks"][:3] for i in w["items"] if i["kind"] == "tax"]
    bits = []
    if tax:
        bits.append("%s $%s due %s" % (tax[0]["what"].split(" (")[0], format(round(-tax[0]["amount"]), ","), tax[0]["date"]))
    if soon:
        big = min(soon, key=lambda i: i["amount"])
        bits.append("%s $%s on %s" % (big["what"].split(" (")[0], format(round(-big["amount"]), ","), big["date"]))
    return ("Cash: " + "; ".join(bits) + ".") if bits else None
