import csv, datetime, json, os, shutil, tempfile, unittest
from pathlib import Path
from tests.helpers import ROOT
from pocketceo import load_rates, bank, cashflow, reconcile, yearend
from pocketceo import collections_ as inv

FIX = ROOT / "tests" / "fixtures" / "bank"
D = datetime.date


class TempHome(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        os.environ["POCKET_CEO_HOME"] = self.tmp

    def tearDown(self):
        for p in Path(self.tmp).rglob("*"):
            try:
                p.chmod(0o700 if p.is_dir() else 0o600)
            except OSError:
                pass
        shutil.rmtree(self.tmp, ignore_errors=True)
        os.environ.pop("POCKET_CEO_HOME", None)

    def write(self, name, text):
        p = Path(self.tmp) / name
        p.write_text(text, encoding="utf-8")
        return p


class ParseEveryBankLayout(unittest.TestCase):
    CASES = {  # file: (rows, first amount, first description contains, has balance)
        "rbc.csv": (4, -95.00, "ROGERS", False), "td.csv": (4, -62.10, "SHELL", True),
        "tangerine.csv": (3, -27.99, "ADOBE", False), "cibc_card.csv": (3, -150.00, "GOOGLE", False),
        "bmo.csv": (3, -42.50, "STARBUCKS", False), "scotia.csv": (3, -55.20, "PETRO", False),
        "desj_like.csv": (2, -120.45, "HYDRO", True),
    }

    def test_layouts(self):
        for f, (n, amt, word, bal) in self.CASES.items():
            t, info = bank.parse_csv((FIX / f).read_text(encoding="utf-8"))
            self.assertEqual(info["rows"], n, f)
            self.assertAlmostEqual(t[0]["amount"], amt, places=2, msg=f)
            self.assertIn(word, t[0]["description"].upper(), f)
            self.assertEqual(t[0]["balance"] is not None, bal, f)

    def test_td_deposit_is_positive(self):
        t, _ = bank.parse_csv((FIX / "td.csv").read_text())
        self.assertEqual(t[1]["amount"], 800.0)

    def test_amount_formats(self):
        for s, v in [("1,234.56", 1234.56), ("(45.00)", -45.0), ("45.00-", -45.0), ("3 210,10", 3210.10),
                     ("$12.00", 12.0), ("", None), ("abc", None), ("-0.99", -0.99)]:
            self.assertEqual(bank.parse_amount(s), v, s)

    def test_flip_for_cards_that_show_purchases_positive(self):
        text = "Date,Description,Amount\n" + "".join("2026-10-%02d,STORE %d,%d.00\n" % (i, i, i) for i in range(1, 9))
        _, info = bank.parse_csv(text)
        self.assertIn("warning", info)
        t, _ = bank.parse_csv(text, flip=True)
        self.assertTrue(all(x["amount"] < 0 for x in t))

    def test_garbage_is_refused(self):
        with self.assertRaises(ValueError):
            bank.parse_csv("hello,world\nfoo,bar\n")


class ImportAndCategorize(TempHome):
    def test_import_dedupes_overlapping_exports(self):
        a = bank.import_file(FIX / "td.csv", "TD chequing")
        self.assertEqual(a["new"], 4)
        b = bank.import_file(FIX / "td.csv", "TD chequing")
        self.assertEqual((b["new"], b["already_had"]), (0, 4))
        self.assertEqual(len(bank.load_ledger()), 4)

    def test_two_identical_purchases_same_day_are_both_kept(self):
        p = self.write("dup.csv", "Date,Description,Amount\n2026-10-01,TIM HORTONS,-2.10\n2026-10-01,TIM HORTONS,-2.10\n")
        self.assertEqual(bank.import_file(p)["new"], 2)

    def test_original_export_kept_read_only(self):
        bank.import_file(FIX / "rbc.csv")
        kept = list((Path(self.tmp) / "money" / "imports").iterdir())
        self.assertEqual(len(kept), 1)
        self.assertEqual(kept[0].stat().st_mode & 0o222, 0)

    def test_built_in_categories(self):
        for f in ("rbc.csv", "td.csv", "cibc_card.csv", "tangerine.csv"):
            bank.import_file(FIX / f)
        cat = {t["description"][:18]: t["category"] for t in bank.load_ledger()}
        self.assertEqual(cat["MISC PAYMENT ROGER"], "Telephone and utilities")
        self.assertEqual(cat["Contactless Intera"], "Meals and entertainment")
        self.assertEqual(cat["CANADA REVENUE AGE"], bank.TAXPAY)
        self.assertEqual(cat["PAYMENT THANK YOU/"], bank.TRANSFER)
        self.assertEqual(cat["AMAZON.CA MKTP"], bank.REVIEW)
        self.assertEqual(cat["STRIPE PAYOUT Depo"], bank.INCOME)
        self.assertEqual(cat["GOOGLE *ADS1234"], "Advertising")
        self.assertEqual(cat["MONTHLY FEE"], "Interest and bank charges")

    def test_learning_applies_to_old_rows_but_not_owner_edits(self):
        p = self.write("a.csv", "Date,Description,Amount\n2026-10-01,AMAZON.CA ORDER 111,-40.00\n2026-10-08,AMAZON.CA ORDER 222,-60.00\n")
        bank.import_file(p)
        rows = bank.load_ledger()
        bank.set_row(rows[1]["id"], category="Personal (not deductible)", business_pct=0)
        n = bank.learn("amazon.ca", "Office expenses", 100)
        self.assertEqual(n, 1)
        cats = sorted(t["category"] for t in bank.load_ledger())
        self.assertEqual(cats, ["Office expenses", "Personal (not deductible)"])
        # and new imports use the learned rule
        p2 = self.write("b.csv", "Date,Description,Amount\n2026-11-01,AMAZON.CA ORDER 333,-10.00\n")
        bank.import_file(p2)
        self.assertEqual([t["how"] for t in bank.load_ledger() if t["date"] == "2026-11-01"], ["learned"])

    def test_review_groups_by_merchant(self):
        p = self.write("c.csv", "Date,Description,Amount\n2026-10-01,COSTCO WHOLESALE #123,-200\n2026-10-09,COSTCO WHOLESALE #456,-100\n")
        bank.import_file(p)
        g = bank.review_list()
        self.assertEqual(len(g), 1)
        self.assertEqual(g[0]["count"], 2)


def history(months=6, today=D(2026, 11, 19)):
    """Six months of a small business: rent, phone, software, weekly coffee, client deposits."""
    rows, bal = [], 10000.0
    d = today - datetime.timedelta(days=months * 30)
    while d < today:
        if d.day == 1:
            rows.append((d, "RENT STUDIO PROPERTY MGMT", -1450.0))
        if d.day == 5:
            rows.append((d, "ROGERS WIRELESS", -95.0))
        if d.day == 12:
            rows.append((d, "ADOBE *CREATIVE CLOUD", -27.99))
        if d.weekday() == 4:
            rows.append((d, "STRIPE PAYOUT", 1100.0))
        if d.weekday() == 1:
            rows.append((d, "TIM HORTONS #%d" % (d.day * 7), -12.5))
        d += datetime.timedelta(days=1)
    out = ["Date,Description,Amount,Balance"]
    for d, desc, amt in rows:
        bal += amt
        out.append("%s,%s,%.2f,%.2f" % (d.isoformat(), desc, amt, bal))
    return "\n".join(out) + "\n", bal


class CashFlow(TempHome):
    TODAY = D(2026, 11, 19)

    def setUp(self):
        super().setUp()
        text, self.bal = history()
        bank.import_file(self.write("hist.csv", text), "Chequing")

    def test_recurring_found(self):
        r = {x["name"]: x for x in cashflow.recurring(self.TODAY)}
        names = " ".join(r)
        self.assertIn("Rent", names)
        self.assertIn("Rogers", names)
        rent = next(v for k, v in r.items() if "Rent" in k)
        self.assertEqual(rent["cadence"], "monthly")
        self.assertEqual(rent["next"], "2026-12-01")
        stripe = next(v for k, v in r.items() if "Stripe" in k)
        self.assertEqual(stripe["cadence"], "weekly")

    def test_balance_from_file(self):
        b = cashflow.current_balance(self.TODAY)
        self.assertAlmostEqual(b["Chequing"]["balance"], self.bal, places=2)

    def test_forecast_shape(self):
        f = cashflow.forecast(self.bal, self.TODAY)
        self.assertEqual(len(f["weeks"]), 13)
        rent_items = [i for w in f["weeks"] for i in w["items"] if "Rent" in i["what"]]
        self.assertEqual(len(rent_items), 3)  # Dec, Jan, Feb
        self.assertTrue(f["weeks"][-1]["end_balance"] > f["start_balance"])  # profitable business

    def test_afford(self):
        yes = cashflow.afford(self.bal, 2000, "2026-12-10", "laptop", today=self.TODAY)
        self.assertTrue(yes["can_afford"])
        self.assertIn("lowest week", yes["answer"])
        no = cashflow.afford(500, 8400, "2026-11-25", "truck", today=self.TODAY, include_average_income=False)
        self.assertFalse(no["can_afford"])
        self.assertIn("Not yet", no["answer"])

    def test_expected_items_and_brief(self):
        cashflow.add_expected("2026-11-24", -5000, "Equipment deposit")
        line = cashflow.brief_line(1000, self.TODAY, include_average_income=False)
        self.assertIn("below", line)
        self.assertIsNone(cashflow.brief_line(10 ** 6, self.TODAY, include_average_income=False, floor=0) and None)

    def test_tax_items(self):
        R = load_rates(2026)
        items = cashflow.instalment_items(R, 1500, self.TODAY)
        self.assertEqual(items[0][0], "2026-12-15")
        g = cashflow.gst_estimates(R, "ON", self.TODAY, "quarterly")
        self.assertTrue(any("2026 Q3" in x[2] or "2026 Q4" in x[2] for x in g))


class ReconcileAndYearEnd(TempHome):
    def setUp(self):
        super().setUp()
        bank.import_file(self.write("b.csv",
            "Date,Description,Amount\n"
            "2026-03-02,STAPLES #123,-56.50\n"
            "2026-03-05,TIM HORTONS 99,-40.00\n"
            "2026-04-10,BEST BUY 22,-1695.00\n"
            "2026-05-01,ROGERS,-113.00\n"
            "2026-06-15,STRIPE PAYOUT,11300.00\n"
            "2026-07-15,STRIPE PAYOUT,22600.00\n"
            "2026-08-01,CANADA REVENUE AGENCY,-2000.00\n"), "Chequing")
        rd = Path(self.tmp) / "receipts" / "2026"
        rd.mkdir(parents=True)
        (rd / "2026-03-01_staples_56.50.jpg").write_bytes(b"x")
        (rd / "2026-04-09_bestbuy_1695.00.jpg").write_bytes(b"y")
        fields = "num,date,vendor,what,category,subtotal,gst_hst,pst_qst,tip,total,paid_with,business_pct,deductible,itc,vendor_gst_number,file,notes".split(",")
        with open(rd / "receipts-2026.csv", "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields); w.writeheader()
            w.writerow(dict(num=1, date="2026-03-01", vendor="Staples", what="paper", category="Office expenses", subtotal="50.00", gst_hst="6.50", total="56.50", business_pct="100", file="2026-03-01_staples_56.50.jpg"))
            w.writerow(dict(num=2, date="2026-04-09", vendor="Best Buy", what="MacBook Air laptop", category="CAPITAL", subtotal="1500.00", gst_hst="195.00", total="1695.00", business_pct="100", file="2026-04-09_bestbuy_1695.00.jpg"))
            w.writerow(dict(num=3, date="2026-09-09", vendor="Cash hardware", what="screws", category="Supplies", subtotal="10.00", gst_hst="1.30", total="11.30", business_pct="100"))

    def test_reconcile(self):
        r = reconcile.reconcile(2026)
        self.assertEqual(r["matched"], 2)
        miss = {m["description"]: m["amount"] for m in r["missing_receipts"]}
        self.assertEqual(set(miss), {"TIM HORTONS 99", "ROGERS"})  # CRA and deposits never need receipts
        self.assertEqual(r["missing_total"], 153.0)
        self.assertEqual(len(r["receipts_without_bank_match"]), 1)
        self.assertIn("2 purchases, $153", r["headline"])

    def test_year_end_package(self):
        ip = Path(self.tmp) / "year-end" / "2026"
        ip.mkdir(parents=True)
        inp = dict(yearend.INPUTS_TEMPLATE)
        inp.update(province="ON", gst={"registered": True, "method": "regular"},
                   home_office={"workspace_sq_ft": 100, "home_sq_ft": 1000, "rent": 24000, "utilities": 2400, "meets_rules": True})
        (ip / "inputs.json").write_text(json.dumps(inp))
        os.environ["POCKET_CEO_BROWSER"] = "/nonexistent"  # skip PDF in tests
        try:
            r = yearend.build(2026)
        finally:
            os.environ.pop("POCKET_CEO_BROWSER")
        self.assertAlmostEqual(r["sales"], 30000.0, places=2)          # 33,900 incl. 13% HST
        self.assertAlmostEqual(r["gst_collected"], 3900.0, places=2)
        lines = r["lines"]
        self.assertAlmostEqual(lines["8810"], 50.0, places=2)            # receipt amounts net of HST
        self.assertAlmostEqual(lines["8811"], 10.0, places=2)            # supplies, cash receipt with no bank match
        self.assertAlmostEqual(lines["8523"], 40 / 1.13 * 0.5, places=2) # meals, no receipt, 50%
        self.assertAlmostEqual(lines["9220"], 113 / 1.13, places=2)
        self.assertAlmostEqual(lines["9936"], 1500 * 0.55, places=2)     # class 50, first year 2x half-year rule
        self.assertAlmostEqual(lines["9945"], 2640.0, places=2)          # 10% of 26,400
        self.assertAlmostEqual(r["gst"]["106"], 6.50 + 195.00 + 1.30, places=2)
        self.assertEqual(r["missing_receipts"]["count"], 2)
        for f in ("summary.html", "T2125-worksheet.csv", "GST-HST-worksheet.csv", "CCA-schedule.csv", "missing-receipts.csv", "README.txt"):
            self.assertTrue((ip / f).exists(), f)
        self.assertTrue((ip / "receipts" / "2026-04-09_bestbuy_1695.00.jpg").exists())
        cca = list(csv.DictReader(open(ip / "CCA-schedule.csv")))
        self.assertEqual([c["class"] for c in cca], ["50"])
        self.assertIn("CLASS GUESSED", cca[0]["items"])  # guessed from "laptop", so flagged for the accountant

    def test_home_office_cannot_create_a_loss(self):
        ip = Path(self.tmp) / "year-end" / "2026"
        ip.mkdir(parents=True)
        inp = dict(yearend.INPUTS_TEMPLATE, province="ON", gst={"registered": True},
                   home_office={"workspace_sq_ft": 900, "home_sq_ft": 1000, "rent": 60000, "meets_rules": True})
        (ip / "inputs.json").write_text(json.dumps(inp))
        os.environ["POCKET_CEO_BROWSER"] = "/nonexistent"
        try:
            r = yearend.build(2026)
        finally:
            os.environ.pop("POCKET_CEO_BROWSER")
        self.assertAlmostEqual(r["net_income"], 0.0, places=2)
        self.assertGreater(r["home_office"]["carried_forward"], 0)


class Invoices(TempHome):
    def test_aging_and_stages(self):
        inv.add("Sarah Chen", 1200, issued="2026-09-01", due="2026-10-01")
        inv.add("Bob's Bakery", 800, issued="2026-11-10", due="2026-12-10")
        inv.add("Acme Corp", 60000, issued="2026-01-01", due="2026-02-01")
        a = inv.aging(load_rates(2026), "ON", today=D(2026, 11, 19))
        self.assertEqual(a["total_owed"], 62000)
        self.assertEqual(a["overdue"], 61200)
        sarah = a["buckets"]["31-60"][0]
        self.assertEqual((sarah["days_late"], sarah["next_step"]), (49, "final notice"))
        self.assertEqual(a["buckets"]["current"][0]["next_step"], "not due yet")
        self.assertEqual(a["small_claims"]["limit"], 50000)
        self.assertEqual(a["over_small_claims_limit"], ["INV-2026-003"])

    def test_paid_and_match(self):
        r = inv.add("Sarah Chen", 1200, issued="2026-09-01")
        bank.import_file(self.write("d.csv", "Date,Description,Amount\n2026-10-03,E-TRANSFER FROM SARAH CHEN,1200.00\n"))
        m = inv.match_deposits(today=D(2026, 11, 19))
        self.assertEqual((m[0]["invoice"], m[0]["confidence"]), (r["id"], "high"))
        inv.mark_paid(r["id"], on="2026-10-03")
        self.assertEqual(inv.aging(today=D(2026, 11, 19))["total_owed"], 0)

    def test_part_payment(self):
        r = inv.add("Dan", 1000, issued="2026-10-01")
        self.assertEqual(inv.mark_paid(r["id"], 400)["status"], "part paid")
        self.assertEqual(inv.aging(today=D(2026, 11, 19))["total_owed"], 600)


if __name__ == "__main__":
    unittest.main()


class Mileage(TempHome):
    def test_log_from_known_places(self):
        from pocketceo import mileage
        mileage.set_place("Dr. Lee clinic", 14)
        mileage.add("2026-03-02", "Dr. Lee clinic", "client visit", source="calendar")
        self.assertIsNone(mileage.add("2026-03-02", "Dr. Lee clinic", "client visit", source="calendar"))  # no doubles
        mileage.add("2026-03-09", "Supplier", "pick up stock", km=30)
        mileage.odometer("2026-01-01", 48000)
        mileage.odometer("2026-12-31", 58000)
        s = mileage.summary(2026)
        self.assertEqual((s["trips"], s["business_km"], s["total_km"], s["business_pct"]), (2, 58, 10000, 0.58))
        with self.assertRaises(SystemExit):
            mileage.add("2026-03-10", "Somewhere new", "meeting")


class BriefLines(TempHome):
    def test_deadlines_and_owed(self):
        from pocketceo import brief
        R = load_rates(2026)
        d = brief.deadlines(R, D(2026, 4, 20), 14, gst="quarterly", instalments=False)
        self.assertEqual(sorted(w for _, w in d), ["GST/HST return and payment due for last quarter",
                                                   "Personal tax balance due (and return, if not self-employed)"])
        self.assertEqual(brief.money_lines(R, D(2026, 11, 19)), [])  # nothing to say -> no lines
        inv.add("Sarah Chen", 1200, issued="2026-09-01", due="2026-10-01")
        lines = brief.money_lines(R, D(2026, 12, 10), instalment_amount=1000)
        self.assertIn("Owed to you: $1,200 overdue (Sarah 70 days).", lines)
        self.assertTrue(any("instalment" in l for l in lines))
