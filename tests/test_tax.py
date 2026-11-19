import json, unittest
from tests.helpers import ROOT
from pocketceo import load_rates, tax

R = load_rates(2026)


def itax(p, **k):
    return tax.personal_tax(R, p, payroll=False, low_income_reductions=False, **k)["income_tax"]


class MarginalRatesMatchPublishedTables(unittest.TestCase):
    """Every 2026 combined marginal rate TaxTips publishes (federal + each province/territory,
    ordinary income and both kinds of dividends) must come out of the engine within 0.03 points."""

    def test_all_jurisdictions(self):
        fx = json.loads((ROOT / "tests/fixtures/taxtips_marginal_2026.json").read_text())["tables"]
        checked = 0
        for p, rows in fx.items():
            for r in rows:
                x = (r["from"] + r["to"]) / 2 if r["to"] else r["from"] + 50000
                if x < 25000:
                    continue  # inside the basic personal amount; tables ignore credits there
                step = 200.0
                got = (itax(p, other=x + step) - itax(p, other=x)) / step * 100
                self.assertAlmostEqual(got, r["other"], delta=0.03, msg="%s other @%d" % (p, x))
                for kind, col, g in (("eligible_dividends", "eligible_div", 1.38), ("non_eligible_dividends", "non_eligible_div", 1.15)):
                    base = itax(p, other=x - step * g)
                    got = (itax(p, other=x - step * g, **{kind: step}) - base) / step * 100
                    self.assertAlmostEqual(got, r[col], delta=0.03, msg="%s %s @%d" % (p, kind, x))
                checked += 3
        self.assertGreater(checked, 300)


class Contributions(unittest.TestCase):
    def test_cpp_employee_max_matches_cra(self):
        c = tax.contributions(R, "ON", employment=200000)
        self.assertAlmostEqual(c["cpp_employee"], 4230.45, places=2)
        self.assertAlmostEqual(c["cpp2_employee"], 416.00, places=2)
        self.assertAlmostEqual(c["ei_employee"], 1123.07, places=2)
        self.assertAlmostEqual(c["ei_employer"], 1572.30, places=1)

    def test_self_employed_pays_both_halves(self):
        c = tax.contributions(R, "AB", self_employed=200000)
        self.assertAlmostEqual(c["cpp_self_employed"] + c["cpp2_self_employed"], 9292.90, places=2)
        self.assertEqual(c["ei_self_employed"], 0.0)  # EI only if they opt in

    def test_self_employed_80k(self):
        c = tax.contributions(R, "ON", self_employed=80000)
        self.assertAlmostEqual(c["cpp_self_employed"], 2 * 71100 * 0.0595, places=2)
        self.assertAlmostEqual(c["cpp2_self_employed"], 2 * 5400 * 0.04, places=2)

    def test_quebec_uses_qpp_and_qpip(self):
        c = tax.contributions(R, "QC", employment=200000)
        self.assertEqual(c["plan"], "QPP")
        self.assertAlmostEqual(c["cpp_employee"], 4479.30, places=2)
        self.assertAlmostEqual(c["ei_employee"], 895.70, places=2)
        self.assertAlmostEqual(c["qpip_employee"], 442.90, places=2)

    def test_employment_then_self_employment_share_one_ceiling(self):
        c = tax.contributions(R, "ON", employment=60000, self_employed=40000)
        self.assertAlmostEqual(c["cpp_employee"], (60000 - 3500) * 0.0595, places=2)
        self.assertAlmostEqual(c["cpp_self_employed"], 2 * (74600 - 60000) * 0.0595, places=2)


class BasicAmounts(unittest.TestCase):
    def test_federal_bpa_phase(self):
        self.assertEqual(tax.federal_bpa(R, 100000), 16452)
        self.assertEqual(tax.federal_bpa(R, 300000), 14829)
        self.assertAlmostEqual(tax.federal_bpa(R, (181440 + 258482) / 2), (16452 + 14829) / 2, places=2)

    def test_no_tax_below_basic_amount(self):
        self.assertEqual(itax("ON", other=12000), 0.0)

    def test_ontario_health_premium_bands(self):
        hp = lambda inc: tax.personal_tax(R, "ON", other=inc)["ontario_health_premium"]
        self.assertEqual(hp(19000), 0)
        self.assertEqual(hp(30000), 300)
        self.assertEqual(hp(60000), 600)
        self.assertEqual(hp(100000), 750)
        self.assertEqual(hp(250000), 900)


class SetAside(unittest.TestCase):
    def test_set_aside_is_sane(self):
        s = tax.set_aside(R, "ON", 80000)
        self.assertTrue(20 <= s["set_aside_pct_of_profit"] <= 35, s["set_aside_pct_of_profit"])
        self.assertAlmostEqual(s["tax_and_cpp_on_business_income"],
                               s["income_tax_part"] + s["cpp_part"] + s["ei_part"] + s["qpip_part"], delta=0.05)

    def test_set_aside_rises_with_income(self):
        a = tax.set_aside(R, "BC", 50000)["set_aside_pct_of_profit"]
        b = tax.set_aside(R, "BC", 150000)["set_aside_pct_of_profit"]
        self.assertLess(a, b)

    def test_side_business_on_top_of_job_costs_more(self):
        alone = tax.set_aside(R, "AB", 30000)["set_aside_pct_of_profit"]
        side = tax.set_aside(R, "AB", 30000, employment=90000)["set_aside_pct_of_profit"]
        self.assertGreater(side, alone)


class Instalments(unittest.TestCase):
    def test_required_needs_two_years(self):
        self.assertTrue(tax.instalments(R, "ON", 5000, 4000, 0)["required"])
        self.assertFalse(tax.instalments(R, "ON", 5000, 2000, 2500)["required"])
        self.assertFalse(tax.instalments(R, "ON", 2900, 9000, 9000)["required"])

    def test_quebec_threshold(self):
        self.assertTrue(tax.instalments(R, "QC", 2000, 1900, 0)["required"])
        self.assertEqual(tax.instalments(R, "ON", 0, 0, 0)["due_dates"][0], "2026-03-15")


class GST(unittest.TestCase):
    def test_threshold_four_quarters(self):
        q = [("2026Q1", 6000), ("2026Q2", 8000), ("2026Q3", 9000), ("2026Q4", 8000)]
        w = tax.gst_threshold_watch(R, q)
        self.assertEqual(w["crossed"]["quarter"], "2026Q4")
        self.assertEqual(w["crossed"]["how"], "four quarters")

    def test_threshold_single_quarter(self):
        w = tax.gst_threshold_watch(R, [("2026Q1", 31000)])
        self.assertEqual(w["crossed"]["how"], "single quarter")

    def test_threshold_not_crossed(self):
        w = tax.gst_threshold_watch(R, [("Q1", 5000), ("Q2", 5000)])
        self.assertIsNone(w["crossed"])
        self.assertEqual(w["room_left"], 20000)

    def test_quick_method_ontario_services(self):
        g = tax.gst_quick_vs_regular(R, "ON", 100000, 10000)
        self.assertAlmostEqual(g["regular"]["remit"], 13000 - 1300, places=2)
        self.assertAlmostEqual(g["quick"]["remit"], 113000 * 0.088 - 300, places=2)
        self.assertGreater(g["quick_saves"], 0)
        self.assertFalse(g["quick"]["rate_verified"])

    def test_quick_method_unknown_rate_says_so(self):
        g = tax.gst_quick_vs_regular(R, "NS", 100000, 10000)
        self.assertIsNone(g["quick"])


class SalaryVsDividend(unittest.TestCase):
    def test_both_paths_spend_the_whole_profit(self):
        s = tax.salary_vs_dividend(R, "ON", 120000)
        a = s["all_salary"]
        self.assertAlmostEqual(a["salary"] + a["employer_cpp"], 120000, delta=1)
        d = s["all_dividends"]
        self.assertAlmostEqual(d["dividend"] + d["corporate_tax"], 120000, delta=1)

    def test_ontario_small_rate_prorated(self):
        rate, prov = tax.corporate_small_rate(R, "ON")
        self.assertTrue(0.022 < prov < 0.032)
        self.assertAlmostEqual(rate, 0.09 + prov)

    def test_verdict_present_everywhere(self):
        for p in R["provinces"]:
            self.assertIn("verdict", tax.salary_vs_dividend(R, p, 90000))


class EmployeeCost(unittest.TestCase):
    def test_employer_costs_on_top(self):
        e = tax.employee_cost(R, "ON", 50000)
        self.assertAlmostEqual(e["employer_cpp"], (50000 - 3500) * 0.0595, places=1)
        self.assertAlmostEqual(e["employer_ei"], 50000 * 0.0163 * 1.4, places=1)


class RatesFileIntegrity(unittest.TestCase):
    def test_every_section_has_a_known_source(self):
        ids = set(R["sources"])
        def walk(node, path):
            if isinstance(node, dict):
                if "source" in node:
                    for s in node["source"]:
                        self.assertIn(s, ids, path)
                for k, v in node.items():
                    if k != "sources":
                        walk(v, path + "/" + k)
            elif isinstance(node, list):
                for i, v in enumerate(node):
                    walk(v, path + "/%d" % i)
        walk(R, "")

    def test_all_13_jurisdictions(self):
        self.assertEqual(len(R["provinces"]), 13)
        for p, d in R["provinces"].items():
            self.assertEqual(d["brackets"][0]["over"], 0, p)
            overs = [b["over"] for b in d["brackets"]]
            self.assertEqual(overs, sorted(overs), p)

    def test_future_year_falls_back_with_warning(self):
        r = load_rates(2031)
        self.assertIn("_warning", r)


if __name__ == "__main__":
    unittest.main()
