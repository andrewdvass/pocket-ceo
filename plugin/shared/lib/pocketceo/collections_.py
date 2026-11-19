"""Money owed to the owner: invoices, aging, follow-up stage, bank-deposit matching.
Ledger: <data_dir>/money/invoices.csv. Pocket CEO drafts reminders; it never sends them."""
import csv, datetime, re
from . import r2
from .bank import money_dir, load_ledger, _norm

D = datetime.date
FIELDS = ["id", "client", "client_email", "amount", "issued", "due", "status", "paid_on", "paid_amount", "reminders", "notes"]
STAGES = [(0, "not due yet", None), (1, "friendly reminder", "polite"), (15, "firm reminder", "firm"),
          (45, "final notice", "final"), (90, "small claims territory", "final")]


def _path():
    return money_dir() / "invoices.csv"


def load():
    p = _path()
    if not p.exists():
        return []
    with open(p, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        r["amount"] = float(r["amount"] or 0)
        r["paid_amount"] = float(r["paid_amount"] or 0)
    return rows


def save(rows):
    with open(_path(), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(dict(r, amount="%.2f" % r["amount"], paid_amount="%.2f" % r["paid_amount"]))


def add(client, amount, issued=None, due=None, terms_days=30, invoice_id=None, email="", notes=""):
    rows = load()
    issued = issued or D.today().isoformat()
    due = due or (D.fromisoformat(issued) + datetime.timedelta(days=terms_days)).isoformat()
    iid = invoice_id or "INV-%s-%03d" % (issued[:4], 1 + sum(1 for r in rows if r["issued"][:4] == issued[:4]))
    if any(r["id"] == iid for r in rows):
        raise SystemExit("Invoice %s already exists." % iid)
    r = {"id": iid, "client": client, "client_email": email, "amount": float(amount), "issued": issued, "due": due,
         "status": "open", "paid_on": "", "paid_amount": 0.0, "reminders": "", "notes": notes}
    rows.append(r)
    save(rows)
    return r


def mark_paid(invoice_id, amount=None, on=None):
    rows = load()
    for r in rows:
        if r["id"] == invoice_id:
            r["paid_amount"] += float(amount) if amount is not None else r["amount"] - r["paid_amount"]
            r["paid_on"] = on or D.today().isoformat()
            r["status"] = "paid" if r["paid_amount"] >= r["amount"] - 0.005 else "part paid"
            save(rows)
            return r
    raise SystemExit("No invoice " + invoice_id)


def log_reminder(invoice_id, stage):
    rows = load()
    for r in rows:
        if r["id"] == invoice_id:
            r["reminders"] = (r["reminders"] + ";" if r["reminders"] else "") + "%s %s" % (D.today().isoformat(), stage)
    save(rows)


def stage_for(days_late):
    cur = STAGES[0]
    for s in STAGES:
        if days_late >= s[0]:
            cur = s
    return cur


def aging(R=None, province=None, today=None):
    today = today or D.today()
    buckets = {"current": [], "1-30": [], "31-60": [], "61-90": [], "90+": []}
    for r in load():
        if r["status"] == "paid":
            continue
        owed = r2(r["amount"] - r["paid_amount"])
        late = (today - D.fromisoformat(r["due"])).days
        b = "current" if late <= 0 else "1-30" if late <= 30 else "31-60" if late <= 60 else "61-90" if late <= 90 else "90+"
        st = stage_for(late)
        last = r["reminders"].split(";")[-1] if r["reminders"] else ""
        buckets[b].append({"id": r["id"], "client": r["client"], "owed": owed, "due": r["due"], "days_late": max(0, late),
                           "next_step": st[1], "tone": st[2], "last_reminder": last})
    totals = {k: r2(sum(i["owed"] for i in v)) for k, v in buckets.items()}
    out = {"as_of": today.isoformat(), "buckets": buckets, "totals": totals, "total_owed": r2(sum(totals.values())),
           "overdue": r2(sum(v for k, v in totals.items() if k != "current"))}
    if R and province:
        sc = R["small_claims"].get(province)
        out["small_claims"] = ({"limit": sc["limit"], "note": sc["note"], "confidence": R["small_claims"]["confidence"]} if sc
                               else {"limit": None, "note": "Limit for this province not on file; look it up on the provincial court site."})
        over = [i for i in buckets["90+"] if sc and i["owed"] > sc["limit"]]
        if over:
            out["over_small_claims_limit"] = [i["id"] for i in over]
    return out


def match_deposits(today=None, window_days=120):
    """Suggest which bank deposits paid which open invoices (same amount, client name in the description)."""
    today = today or D.today()
    open_inv = [r for r in load() if r["status"] != "paid"]
    deps = [t for t in load_ledger() if t["amount"] > 0 and (today - D.fromisoformat(t["date"])).days <= window_days]
    out = []
    for r in open_inv:
        owed = r["amount"] - r["paid_amount"]
        name = [w for w in re.findall(r"[A-Z]{3,}", r["client"].upper())]
        for t in deps:
            if t["date"] < r["issued"] or abs(t["amount"] - owed) > 0.01:
                continue
            hit = any(w in _norm(t["description"]) for w in name)
            out.append({"invoice": r["id"], "client": r["client"], "deposit_date": t["date"], "amount": t["amount"],
                        "description": t["description"], "confidence": "high" if hit else "amount only"})
    return out
