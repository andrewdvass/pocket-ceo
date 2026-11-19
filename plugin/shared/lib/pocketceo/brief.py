"""The money lines for the morning brief. Each line appears only when it has something in it."""
import datetime
from . import money
from . import cashflow, collections_ as inv
from .bank import load_ledger

D = datetime.date


def deadlines(R, today=None, days=14, structure="sole", gst=None, employees=False, instalments=False):
    """Tax dates in the next `days` days for this owner, from the rates file."""
    today = today or D.today()
    end = today + datetime.timedelta(days=days)
    y = today.year
    out = []
    def add(d, what):
        if today <= d <= end:
            out.append((d, what))
    dl = R["deadlines"]
    for yr in (y, y + 1):
        if structure != "corporation":
            add(D.fromisoformat("%d-%s" % (yr, dl["personal_return_and_balance_due"])), "Personal tax balance due (and return, if not self-employed)")
            add(D.fromisoformat("%d-%s" % (yr, dl["self_employed_return_due"])), "Self-employed tax return due (balance was due Apr 30)")
        if instalments:
            for md in R["instalments"]["due_dates"]:
                add(D.fromisoformat("%d-%s" % (yr, md)), "Tax instalment due")
        if employees:
            add(D(yr, 2, 28) if not (yr % 4 == 0 and (yr % 100 or yr % 400 == 0)) else D(yr, 2, 29), "T4 slips due to employees and CRA")
            for m in range(1, 13):
                add(D(yr, m, 15), "Payroll source deductions due (regular remitter)")
        if gst == "quarterly":
            for m in (1, 4, 7, 10):
                last = D(yr, m + 1, 1) - datetime.timedelta(days=1)
                add(last, "GST/HST return and payment due for last quarter")
        elif gst == "annual":
            add(D(yr, 4, 30), "GST/HST payment due (annual filer)")
            add(D(yr, 6, 15), "GST/HST return due (annual filer, Dec 31 year end)")
        elif gst == "monthly":
            for m in range(1, 13):
                last = (D(yr, m + 1, 1) if m < 12 else D(yr + 1, 1, 1)) - datetime.timedelta(days=1)
                add(last, "GST/HST return and payment due for last month")
    return sorted(set(out))


def money_lines(R, today=None, floor=0.0, balance=None, gst=None, structure="sole", employees=False,
                instalment_amount=None, days=14):
    today = today or D.today()
    lines = []
    if load_ledger():
        bal = balance
        if bal is None:
            b = cashflow.current_balance(today)
            bal = sum(v["balance"] for v in b.values()) if b else None
        if bal is not None:
            tax_items = []
            if instalment_amount:
                tax_items += cashflow.instalment_items(R, instalment_amount, today)
            l = cashflow.brief_line(bal, today, floor=floor, tax_items=tax_items)
            if l:
                lines.append(l)
    a = inv.aging(today=today)
    if a["overdue"] > 0:
        late = sorted((i for k, v in a["buckets"].items() if k != "current" for i in v), key=lambda i: -i["days_late"])
        lines.append("Owed to you: %s overdue (%s)." % (money(a["overdue"]), ", ".join(
            "%s %d days" % (i["client"].split()[0], i["days_late"]) for i in late[:3])))
    dls = deadlines(R, today, days, structure, gst, employees, bool(instalment_amount))
    if dls:
        lines.append("Coming up: " + "; ".join("%s %s" % (d.strftime("%b %-d") if hasattr(d, "strftime") else d, w) for d, w in dls[:3]) + ".")
    return lines
