"""Bank and credit card CSV import, the transaction ledger, and the learning categorizer.

Ledger: <data_dir>/money/transactions.csv (one row per transaction, never deleted).
Learned rules: <data_dir>/money/rules.csv. Original exports are kept, read-only, in money/imports/.

Sign convention everywhere: amount > 0 is money IN, amount < 0 is money OUT.
"""
import csv, datetime, hashlib, io, re, shutil, stat
from pathlib import Path
from . import data_dir

LEDGER_FIELDS = ["id", "date", "account", "description", "amount", "balance", "category", "business_pct",
                 "how", "source_file", "note"]
RULE_FIELDS = ["pattern", "category", "business_pct", "added", "example"]

# Categories: the CRA T2125 expense names the receipts skill already uses, plus money-movement types.
INCOME = "Sales / income"
TRANSFER = "Transfer (not income or expense)"
OWNER = "Owner pay / draw"
TAXPAY = "Tax payment (CRA / Revenu Québec)"
GSTPAY = "GST/HST remittance"
LOAN = "Loan payment"
PERSONAL = "Personal (not deductible)"
REVIEW = "NEEDS REVIEW"

NO_RECEIPT_NEEDED = {TRANSFER, OWNER, TAXPAY, GSTPAY, LOAN, INCOME, PERSONAL, "Interest and bank charges"}
NOT_BUSINESS_EXPENSE = {TRANSFER, OWNER, TAXPAY, GSTPAY, LOAN, INCOME, PERSONAL, REVIEW, ""}

# (regex on upper-case description, category, business %, applies to: "out", "in" or "any")
BUILT_IN_RULES = [
    (r"UBER\s*\*?\s*EATS|SKIP ?THE ?DISHES|DOORDASH", "Meals and entertainment", 100, "out"),
    (r"TIM HORTONS|STARBUCKS|SECOND CUP|MCDONALD|A&W|SUBWAY|RESTAURANT|BISTRO|PUB\b|CAFE|COFFEE", "Meals and entertainment", 100, "out"),
    (r"\bCRA\b|CANADA REVENUE|REC(EIVER)? ?GEN|GOVT CANADA TAX|FED TAX|TAX CENTRE", TAXPAY, 0, "out"),
    (r"REVENU ?QU[EÉ]BEC|MINISTRE DU REVENU", TAXPAY, 0, "out"),
    (r"GST[/ ]?HST|HST PAYMENT|GST PAYMENT", GSTPAY, 0, "out"),
    (r"SHELL|PETRO[- ]?CAN|ESSO|HUSKY|PIONEER|ULTRAMAR|IRVING|CO-?OP GAS|CHEVRON|MOBIL|SUNOCO|FAS GAS|CENTEX|7-ELEVEN", "Motor vehicle expenses", 100, "out"),
    (r"IMPARK|INDIGO PARK|HONK|PAYBYPHONE|PRECISE PARK|GREEN P|PARKING|407 ETR", "Motor vehicle expenses", 100, "out"),
    (r"ROGERS|BELL CANADA|\bBELL\b|TELUS|FIDO|KOODO|VIRGIN PLUS|SHAW|VIDEOTRON|FREEDOM MOBILE|COGECO|EASTLINK|SASKTEL|PUBLIC MOBILE|CHATR", "Telephone and utilities", 100, "out"),
    (r"HYDRO|ENBRIDGE|FORTIS|EPCOR|ENMAX|ATCO|UTILITIES|DIRECT ENERGY", "Telephone and utilities", 100, "out"),
    (r"GOOGLE ?\*?ADS|GOOGLE ADWORDS|FACEBK|FB ?ADS|META ?PLATFORMS|META ADS|LINKEDIN ADS|TIKTOK ADS|YELP|MAILCHIMP|KLAVIYO|CONSTANT CONTACT|VISTAPRINT", "Advertising", 100, "out"),
    (r"ADOBE|MICROSOFT|MSFT|CANVA|ANTHROPIC|CLAUDE\.AI|OPENAI|CHATGPT|SHOPIFY \*|QUICKBOOKS|INTUIT|XERO|WAVE|FRESHBOOKS|ZOOM|DROPBOX|GOOGLE ?\*?(GSUITE|WORKSPACE|CLOUD)|SLACK|NOTION|GODADDY|SQUARESPACE|WIX|HIGHLEVEL|GOHIGHLEVEL|LEADCONNECTOR|JANE APP|CALENDLY|DOCUSIGN|APPLE\.COM/BILL", "Software and subscriptions", 100, "out"),
    (r"SERVICE CHARGE|MONTHLY FEE|PLAN FEE|ACCOUNT FEE|NSF|OVERDRAFT|INTEREST CHARGE|E-?TRANSFER FEE|WIRE FEE|ANNUAL FEE|STRIPE FEE|SQUARE FEE", "Interest and bank charges", 100, "out"),
    (r"INTACT|AVIVA|WAWANESA|CO-?OPERATORS|ECONOMICAL|DEFINITY|TD INSURANCE|BELAIR|SQUARE ONE|ZENSURANCE|APOLLO INSUR|INSURANCE", "Insurance", 100, "out"),
    (r"WSIB|WCB|WORKSAFE|CNESST|WORKERS COMP", "Salaries, wages, benefits", 100, "out"),
    (r"PAYROLL|WAGEPOINT|\bADP\b|CERIDIAN|DAYFORCE|PAYWORKS|HUMI|ROWAN", "Salaries, wages, benefits", 100, "out"),
    (r"CANADA POST|POSTES CANADA|PUROLATOR|\bUPS\b|FEDEX|CANPAR|DHL|INTELCOM|SHIPSTATION|CHIT CHATS", "Delivery, freight, express", 100, "out"),
    (r"STAPLES|BUREAU EN GROS|GRAND & TOY|BEST BUY", "Office expenses", 100, "out"),
    (r"AIR CANADA|WESTJET|PORTER|FLAIR|SWOOP|VIA RAIL|MARRIOTT|HILTON|HYATT|BEST WESTERN|AIRBNB|EXPEDIA|BOOKING\.COM|HOTEL|LYFT|UBER\s*\*?\s*TRIP|\bUBER\b|TAXI", "Travel", 100, "out"),
    (r"\bRENT\b|PROPERTY MGMT|PROPERTY MANAGEMENT", "Rent", 100, "out"),
    (r"LOAN PMT|LOAN PAYMENT|MORTGAGE|LINE OF CREDIT PMT|LOC PAYMENT|FINANCING", LOAN, 0, "out"),
    (r"PAYMENT - THANK YOU|PAYMENT THANK YOU|PAIEMENT|CREDIT CARD PAYMENT|VISA PAYMENT|MASTERCARD PAYMENT|AMEX PAYMENT|ONLINE BANKING PAYMENT TO .*CARD|TFR-TO|TFR-FR|TRANSFER TO|TRANSFER FROM|INTERNET TRANSFER|ONLINE TRANSFER|VIREMENT", TRANSFER, 0, "any"),
    (r"STRIPE|SQUARE|SHOPIFY|PAYPAL|MONERIS|HELCIM|CLOVER|JANE ?PAYMENTS|DEPOSIT|MOBILE DEPOSIT|E-?TRANSFER|INTERAC|AUTODEPOSIT|ETRANSFER", INCOME, 0, "in"),
    (r"AMAZON|AMZN|COSTCO|WALMART|CANADIAN TIRE|HOME DEPOT|RONA|LOWE'?S|IKEA|DOLLARAMA|SHOPPERS|LOBLAW|SOBEYS|SAFEWAY|METRO|NO FRILLS|SUPERSTORE", REVIEW, 100, "out"),
    (r"E-?TRANSFER|INTERAC|ETRANSFER|EMT\b", REVIEW, 100, "out"),
    (r"ATM|WITHDRAWAL|CASH", REVIEW, 0, "out"),
]


def money_dir():
    d = data_dir() / "money"
    (d / "imports").mkdir(parents=True, exist_ok=True)
    return d


# ---------- parsing ----------
DATE_FORMATS = ["%Y-%m-%d", "%Y/%m/%d", "%m/%d/%Y", "%d/%m/%Y", "%Y%m%d", "%d-%b-%Y", "%b %d, %Y", "%d %b %Y",
                "%m/%d/%y", "%Y-%m-%d %H:%M:%S", "%d-%m-%Y", "%b %d %Y"]


def parse_date(s, prefer_dmy=False):
    s = (s or "").strip().strip('"')
    if not s:
        return None
    fmts = list(DATE_FORMATS)
    if prefer_dmy:
        fmts.remove("%d/%m/%Y"); fmts.insert(2, "%d/%m/%Y")
    for f in fmts:
        try:
            return datetime.datetime.strptime(s, f).date()
        except ValueError:
            pass
    return None


def parse_amount(s):
    s = (s or "").strip().replace("−", "-")
    if not s:
        return None
    neg = s.startswith("(") and s.endswith(")") or s.endswith("-") or s.startswith("-")
    s = re.sub(r"[^\d.,]", "", s.replace("\u00a0", "").replace(" ", ""))
    if not s or not re.search(r"\d", s):
        return None
    if "," in s and "." not in s and re.search(r",\d{2}$", s):  # 1234,56 (French format)
        s = s.replace(",", ".")
    s = s.replace(",", "")
    try:
        v = float(s)
    except ValueError:
        return None
    return -v if neg else v


HEADER_WORDS = {
    "date": ["transaction date", "date posted", "posted date", "posting date", "date", "trans. date", "trans date", "date de transaction"],
    "description": ["description 1", "description", "transaction details", "details", "name", "payee", "merchant", "libellé", "description de la transaction", "transaction"],
    "description2": ["description 2", "memo", "sub-description", "notes"],
    "amount": ["cad$", "amount", "transaction amount", "montant", "amount (cad)"],
    "debit": ["debit", "withdrawal", "withdrawals", "money out", "retrait", "débit", "paid out"],
    "credit": ["credit", "deposit", "deposits", "money in", "dépôt", "crédit", "paid in"],
    "balance": ["balance", "solde", "running balance"],
    "account": ["account number", "account", "first bank card", "card number"],
}


def _match_header(cells):
    low = [c.strip().lower().strip('"') for c in cells]
    found = {}
    for key, words in HEADER_WORDS.items():
        for w in words:
            for i, c in enumerate(low):
                if i in found.values():
                    continue
                if c == w or (len(w) > 4 and c.startswith(w)):
                    found.setdefault(key, i)
                    break
            if key in found:
                break
    if "date" in found and ("amount" in found or "debit" in found or "credit" in found):
        return found
    return None


def sniff_rows(text):
    try:
        dialect = csv.Sniffer().sniff(text[:4096], delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel
    return [r for r in csv.reader(io.StringIO(text), dialect) if any(c.strip() for c in r)]


def _infer_headerless(rows, prefer_dmy=False):
    """Guess columns of a file with no header (TD, CIBC, Scotiabank, Desjardins style)."""
    sample = rows[:50]
    ncol = max(len(r) for r in sample)
    def col(i):
        return [r[i] if i < len(r) else "" for r in sample]
    date_col = next((i for i in range(ncol) if sum(parse_date(v, prefer_dmy) is not None for v in col(i)) >= 0.8 * len(sample)), None)
    if date_col is None:
        return None
    amount_re = re.compile(r"\s*-?\(?\$?-?(\d{1,3}([ ,\u00a0]\d{3})+|\d+)?([.,]\d{2})\)?-?\s*")
    num_cols = [i for i in range(ncol) if i != date_col and
                any(v.strip() for v in col(i)) and
                all(amount_re.fullmatch(v) for v in col(i) if v.strip())]
    text_cols = [i for i in range(ncol) if i not in num_cols and i != date_col and
                 sum(bool(re.search(r"[A-Za-z]{3}", v)) for v in col(i)) >= 0.5 * len(sample)]
    if not num_cols or not text_cols:
        return None
    desc = max(text_cols, key=lambda i: sum(len(v) for v in col(i)))
    m = {"date": date_col, "description": desc}
    filled = {i: sum(bool(v.strip()) for v in col(i)) for i in num_cols}
    # two sparse complementary columns = debit/credit; a dense last column = balance
    if len(num_cols) >= 3:
        m["debit"], m["credit"], m["balance"] = num_cols[0], num_cols[1], num_cols[-1]
    elif len(num_cols) == 2:
        a, b = num_cols
        both = sum(bool(r[a].strip()) and bool(r[b].strip()) for r in sample if max(a, b) < len(r))
        if both < 0.2 * len(sample):
            m["debit"], m["credit"] = a, b
        else:
            m["amount"], m["balance"] = a, b
    else:
        m["amount"] = num_cols[0]
    return m


def parse_csv(text, account="", prefer_dmy=False, flip=False):
    """Return (transactions, info). Each transaction: dict(date, description, amount, balance, account)."""
    text = text.lstrip("﻿")
    rows = sniff_rows(text)
    header_at, cols = None, None
    for i, r in enumerate(rows[:15]):
        m = _match_header(r)
        if m:
            header_at, cols = i, m
            break
    body = rows[header_at + 1:] if header_at is not None else rows
    if cols is None:
        cols = _infer_headerless(body, prefer_dmy)
        if cols is None:
            raise ValueError("Couldn't recognise this file's columns. Open it and check it is the bank's CSV export, "
                             "or tell me which columns hold the date, description and amount.")
    out, skipped = [], 0
    for r in body:
        g = lambda k: r[cols[k]].strip() if k in cols and cols[k] < len(r) else ""
        d = parse_date(g("date"), prefer_dmy)
        if d is None:
            skipped += 1
            continue
        if "amount" in cols:
            amt = parse_amount(g("amount"))
        else:
            dr, cr = parse_amount(g("debit")), parse_amount(g("credit"))
            if dr is None and cr is None:
                amt = None
            else:
                amt = (abs(cr) if cr else 0.0) - (abs(dr) if dr else 0.0)
        if amt is None:
            skipped += 1
            continue
        if flip:
            amt = -amt
        desc = " ".join(x for x in (g("description"), g("description2")) if x)
        desc = re.sub(r"\s+", " ", desc).strip()
        out.append({"date": d.isoformat(), "description": desc, "amount": round(amt, 2),
                    "balance": parse_amount(g("balance")), "account": account or g("account")})
    if not out:
        raise ValueError("No transactions found in this file.")
    dates = sorted(t["date"] for t in out)
    info = {"rows": len(out), "skipped_rows": skipped, "from": dates[0], "to": dates[-1],
            "money_in": round(sum(t["amount"] for t in out if t["amount"] > 0), 2),
            "money_out": round(-sum(t["amount"] for t in out if t["amount"] < 0), 2),
            "columns": {k: v for k, v in cols.items()}, "had_header": header_at is not None}
    # a credit card export usually shows purchases as positive numbers
    pos = sum(1 for t in out if t["amount"] > 0)
    if not flip and pos > 0.75 * len(out) and len(out) >= 5:
        info["warning"] = ("Most amounts in this file are positive. If this is a credit card export where purchases "
                           "show as positive numbers, import it again with --flip.")
    return out, info


# ---------- ledger ----------
def _read(path, fields):
    if not path.exists():
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return [dict({k: "" for k in fields}, **r) for r in csv.DictReader(f)]


def _write(path, rows, fields):
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    tmp.replace(path)


def ledger_path():
    return money_dir() / "transactions.csv"


def load_ledger():
    rows = _read(ledger_path(), LEDGER_FIELDS)
    for r in rows:
        r["amount"] = float(r["amount"])
        r["balance"] = float(r["balance"]) if r["balance"] not in ("", None) else None
        r["business_pct"] = float(r["business_pct"]) if r["business_pct"] not in ("", None) else 0.0
    return rows


def save_ledger(rows):
    out = []
    for r in sorted(rows, key=lambda r: (r["date"], r["id"])):
        r2 = dict(r)
        r2["amount"] = "%.2f" % r["amount"]
        r2["balance"] = "" if r["balance"] is None else "%.2f" % r["balance"]
        r2["business_pct"] = "%g" % (r["business_pct"] or 0)
        out.append(r2)
    _write(ledger_path(), out, LEDGER_FIELDS)


def _fingerprint(t, n):
    key = "%s|%s|%.2f|%s|%d" % (t["date"], t["account"], t["amount"], t["description"].upper(), n)
    return hashlib.sha1(key.encode()).hexdigest()[:12]


def import_file(path, account="", prefer_dmy=False, flip=False):
    path = Path(path)
    raw = path.read_bytes()
    for enc in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    account = account or path.stem
    txns, info = parse_csv(text, account, prefer_dmy, flip)
    ledger = load_ledger()
    have = {r["id"] for r in ledger}
    # occurrence index keeps two identical same-day purchases apart, and stays stable across overlapping exports
    seen, new = {}, []
    for t in txns:
        base = (t["date"], t["account"], t["amount"], t["description"].upper())
        seen[base] = seen.get(base, 0) + 1
        t["id"] = _fingerprint(t, seen[base])
        if t["id"] in have:
            continue
        t.update({"category": "", "business_pct": 0.0, "how": "", "source_file": path.name, "note": ""})
        new.append(t)
    rules = load_rules()
    for t in new:
        categorize(t, rules)
    ledger.extend(new)
    save_ledger(ledger)
    # keep the original export, locked, like receipts
    keep = money_dir() / "imports" / ("%s_%s" % (datetime.date.today().isoformat(), path.name))
    if not keep.exists():
        shutil.copy2(path, keep)
        keep.chmod(stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
    info.update({"new": len(new), "already_had": len(txns) - len(new), "account": account,
                 "needs_review": sum(1 for t in new if t["category"] == REVIEW or not t["category"]),
                 "last_balance": next((t["balance"] for t in reversed(txns) if t["balance"] is not None), None)})
    return info


# ---------- categorizing ----------
def load_rules():
    return _read(money_dir() / "rules.csv", RULE_FIELDS)


def _norm(desc):
    return re.sub(r"\s+", " ", re.sub(r"[#*]?\d{3,}|\s#\S+", " ", (desc or "").upper())).strip()


def categorize(t, rules=None, force=False):
    """Fill category/business_pct/how. Owner-set rows (how=owner) are never changed unless force."""
    if t.get("how") == "owner" and not force:
        return t
    rules = load_rules() if rules is None else rules
    d = _norm(t["description"])
    direction = "in" if t["amount"] > 0 else "out"
    for r in sorted(rules, key=lambda r: -len(r["pattern"])):  # learned rules first, most specific first
        if r["pattern"] and r["pattern"].upper() in d:
            t["category"], t["business_pct"], t["how"] = r["category"], float(r["business_pct"] or 0), "learned"
            return t
    for pat, cat, pct, applies in BUILT_IN_RULES:
        if applies in ("any", direction) and re.search(pat, d):
            t["category"], t["business_pct"], t["how"] = cat, float(pct), "guess"
            return t
    t["category"], t["business_pct"], t["how"] = (INCOME, 0.0, "guess") if direction == "in" else (REVIEW, 0.0, "")
    return t


def learn(pattern, category, business_pct=100, apply=True):
    """Save a rule ("anything with TIM HORTONS is Meals, 100% business") and re-apply it to every row
    that the owner hasn't set by hand. Returns how many rows changed."""
    pattern = _norm(pattern)
    rules = [r for r in load_rules() if r["pattern"] != pattern]
    rules.append({"pattern": pattern, "category": category, "business_pct": "%g" % business_pct,
                  "added": datetime.date.today().isoformat(), "example": ""})
    _write(money_dir() / "rules.csv", rules, RULE_FIELDS)
    if not apply:
        return 0
    ledger, n = load_ledger(), 0
    for t in ledger:
        if t["how"] != "owner" and pattern in _norm(t["description"]):
            before = (t["category"], t["business_pct"])
            categorize(t, rules)
            n += before != (t["category"], t["business_pct"])
    save_ledger(ledger)
    return n


def set_row(txn_id, category=None, business_pct=None, note=None):
    ledger = load_ledger()
    hit = [t for t in ledger if t["id"] == txn_id]
    if not hit:
        raise SystemExit("No transaction with id " + txn_id)
    t = hit[0]
    if category is not None:
        t["category"] = category
    if business_pct is not None:
        t["business_pct"] = float(business_pct)
    if note:
        t["note"] = (t["note"] + " | " if t["note"] else "") + "%s: %s" % (datetime.date.today().isoformat(), note)
    t["how"] = "owner"
    save_ledger(ledger)
    return t


def review_list(limit=25):
    """Rows that need the owner's eye, biggest first, grouped by merchant so one answer fixes many."""
    groups = {}
    for t in load_ledger():
        if t["category"] in (REVIEW, ""):
            k = _norm(t["description"])[:40]
            g = groups.setdefault(k, {"merchant": k, "count": 0, "total": 0.0, "example_id": t["id"], "last": t["date"]})
            g["count"] += 1
            g["total"] += t["amount"]
            g["last"] = max(g["last"], t["date"])
    return sorted(groups.values(), key=lambda g: g["total"])[:limit]


def summary(year=None, month=None):
    rows = load_ledger()
    if year:
        rows = [r for r in rows if r["date"].startswith(str(year))]
    if month:
        rows = [r for r in rows if r["date"][5:7] == "%02d" % int(month)]
    by = {}
    for r in rows:
        b = by.setdefault(r["category"] or REVIEW, {"count": 0, "total": 0.0, "business": 0.0})
        b["count"] += 1
        b["total"] += r["amount"]
        if r["category"] not in NOT_BUSINESS_EXPENSE and r["amount"] < 0:
            b["business"] += -r["amount"] * r["business_pct"] / 100
    income = sum(r["amount"] for r in rows if r["category"] == INCOME)
    expenses = sum(v["business"] for v in by.values())
    return {"rows": len(rows), "by_category": by, "business_income": round(income, 2),
            "business_expenses": round(expenses, 2), "profit": round(income - expenses, 2)}
