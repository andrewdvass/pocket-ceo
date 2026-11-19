"""Match bank transactions to logged receipts, and list purchases that have no receipt."""
import csv, datetime, re
from pathlib import Path
from . import data_dir, r2
from .bank import load_ledger, NO_RECEIPT_NEEDED

D = datetime.date


def load_receipts(year):
    p = data_dir() / "receipts" / str(year) / ("receipts-%s.csv" % year)
    if not p.exists():
        return []
    out = []
    with open(p, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            try:
                r["_total"] = float(str(r.get("total", "")).replace("$", "").replace(",", ""))
                r["_date"] = D.fromisoformat(r["date"][:10])
            except (ValueError, KeyError):
                continue
            out.append(r)
    return out


def _tokens(s):
    return {w for w in re.findall(r"[A-Z]{3,}", (s or "").upper()) if w not in {"THE", "AND", "INC", "LTD", "STORE", "POS", "PURCHASE"}}


def reconcile(year, min_amount=0.0, lag_before=3, lag_after=6):
    bank = [t for t in load_ledger() if t["date"].startswith(str(year)) and t["amount"] < 0
            and t["category"] not in NO_RECEIPT_NEEDED and t["business_pct"] > 0 and -t["amount"] >= min_amount]
    receipts = load_receipts(year)
    used = set()
    matched, missing = [], []
    for t in sorted(bank, key=lambda t: t["date"]):
        td, amt = D.fromisoformat(t["date"]), -t["amount"]
        cands = []
        for i, r in enumerate(receipts):
            if i in used or abs(r["_total"] - amt) > 0.011:
                continue
            lag = (td - r["_date"]).days
            if -lag_before <= lag <= lag_after:
                score = len(_tokens(t["description"]) & _tokens(r.get("vendor"))) * 10 - abs(lag)
                cands.append((score, i))
        if cands:
            _, i = max(cands)
            used.add(i)
            matched.append({"bank_id": t["id"], "date": t["date"], "amount": r2(amt), "bank": t["description"],
                            "receipt": receipts[i].get("file") or receipts[i].get("vendor")})
        else:
            missing.append({"id": t["id"], "date": t["date"], "amount": r2(amt), "description": t["description"],
                            "category": t["category"]})
    no_bank = [{"date": r["date"], "vendor": r.get("vendor"), "total": r["_total"], "file": r.get("file")}
               for i, r in enumerate(receipts) if i not in used]
    total_missing = r2(sum(m["amount"] for m in missing))
    by_cat = {}
    for m in missing:
        by_cat[m["category"]] = r2(by_cat.get(m["category"], 0) + m["amount"])
    return {"year": year, "bank_purchases_checked": len(bank), "matched": len(matched),
            "missing_receipts": missing, "missing_count": len(missing), "missing_total": total_missing,
            "missing_by_category": by_cat,
            "receipts_without_bank_match": no_bank,
            "headline": ("%d purchases, $%s, have no receipt." % (len(missing), format(round(total_missing), ","))
                         if missing else "Every business purchase in the bank file has a receipt."),
            "matches": matched,
            "note": "Receipts with no bank match were often paid in cash or on a card that hasn't been imported yet."}
