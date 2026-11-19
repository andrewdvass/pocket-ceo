#!/usr/bin/env python3
"""Builds plugin/shared/rates/2026.json. Edit the numbers HERE (with their source id), then run:
    python3 dev/build_rates.py && python3 -m unittest discover -s tests
Every value carries a source id from SOURCES below. Never add a number without one."""
import json, pathlib

CHECKED = "2026-11-16"
SOURCES = {
 "cra_t4127": {"name": "CRA T4127 Payroll Deductions Formulas, 122nd edition, effective January 1, 2026 (Tables 8.1 to 8.8)",
               "url": "https://www.canada.ca/en/revenue-agency/services/forms-publications/payroll/t4127-payroll-deductions-formulas/t4127-jan/t4127-jan-payroll-deductions-formulas-computer-programs.html",
               "kind": "official", "checked": CHECKED},
 "tt_rates": {"name": "TaxTips.ca 2026 federal, provincial and territorial tax rate pages (revised Nov 8, 2026; reconciled to CRA)",
              "url": "https://www.taxtips.ca/marginal-tax-rates-in-canada.htm", "kind": "secondary", "checked": CHECKED},
 "tt_dtc_e": {"name": "TaxTips.ca eligible dividend tax credit rates", "url": "https://www.taxtips.ca/dtc/eligible-dividends/eligible-dividend-tax-credit-rates.htm", "kind": "secondary", "checked": CHECKED},
 "tt_dtc_n": {"name": "TaxTips.ca non-eligible dividend tax credit rates", "url": "https://www.taxtips.ca/dtc/non-eligible-dividend-tax-credit.htm", "kind": "secondary", "checked": CHECKED},
 "tt_corp": {"name": "TaxTips.ca 2026 corporate income tax rates (revised Nov 12, 2026)", "url": "https://www.taxtips.ca/smallbusiness/corporatetax/corporate-tax-rates-2026.htm", "kind": "secondary", "checked": CHECKED},
 "tt_cpp": {"name": "TaxTips.ca CPP/QPP contribution rates (revised Nov 13, 2026)", "url": "https://www.taxtips.ca/cpp-qpp-and-ei/cpp-qpp-contribution-rates.htm", "kind": "secondary", "checked": CHECKED},
 "tt_ei": {"name": "TaxTips.ca EI premium rates (revised Nov 14, 2026)", "url": "https://www.taxtips.ca/cpp-qpp-and-ei/employment-insurance-premium-rates.htm", "kind": "secondary", "checked": CHECKED},
 "tt_sales": {"name": "TaxTips.ca 2026 sales tax rates (revised Aug 28, 2026)", "url": "https://www.taxtips.ca/salestaxes/sales-tax-rates-2026.htm", "kind": "secondary", "checked": CHECKED},
 "tt_ohp": {"name": "TaxTips.ca Ontario Health Premium", "url": "https://www.taxtips.ca/ontax/ontario-health-premium.htm", "kind": "secondary", "checked": CHECKED},
 "tt_due": {"name": "TaxTips.ca personal tax return due dates (revised Nov 8, 2026)", "url": "https://www.taxtips.ca/filing/tax-return-due-date.htm", "kind": "secondary", "checked": CHECKED},
 "tt_gst": {"name": "TaxTips.ca GST/HST registration, small supplier and filing", "url": "https://www.taxtips.ca/gst/small-supplier.htm", "kind": "secondary", "checked": CHECKED},
 "tt_veh": {"name": "TaxTips.ca passenger vehicle limits and tax-free vehicle allowance rates (revised Nov 8, 2026)", "url": "https://www.taxtips.ca/smallbusiness/passenger-vehicle-limits.htm", "kind": "secondary", "checked": CHECKED},
 "tt_cca": {"name": "TaxTips.ca capital cost allowance", "url": "https://www.taxtips.ca/smallbusiness/capital-cost-allowance.htm", "kind": "secondary", "checked": CHECKED},
 "cra_inst": {"name": "CRA: who has to pay income tax instalments (checked 2026-10-14, see plugin/SOURCES.md)", "url": "https://www.canada.ca/en/revenue-agency/services/payments/payments-cra/individual-payments/income-tax-instalments/who-pays-instalments.html", "kind": "official", "checked": "2026-10-14"},
 "cra_rc4058": {"name": "CRA RC4058 Quick Method of Accounting for GST/HST", "url": "https://www.canada.ca/en/revenue-agency/services/forms-publications/publications/rc4058/quick-method-accounting-gst-hst.html", "kind": "official", "checked": None},
 "cra_cca": {"name": "CRA CCA classes", "url": "https://www.canada.ca/en/revenue-agency/services/tax/businesses/topics/sole-proprietorships-partnerships/report-business-income-expenses/claiming-capital-cost-allowance/classes.html", "kind": "official", "checked": None},
 "cra_t2125": {"name": "CRA Form T2125 Statement of Business or Professional Activities", "url": "https://www.canada.ca/en/revenue-agency/services/forms-publications/forms/t2125.html", "kind": "official", "checked": None},
 "fin_mega": {"name": "Department of Finance: Productivity Mega Deduction announcement, Sept 15, 2026", "url": "https://www.canada.ca/en/department-finance/news/2026/09/government-of-canada-introduces-new-productivity-mega-deduction-to-boost-canadas-advantage-as-the-most-competitive-g7-country-for-new-business-inve.html", "kind": "official", "checked": None},
 "small_claims": {"name": "Provincial court sites (limits found via search on 2026-11-16; only ON, QC, BC, AB located)", "url": "https://www.ontario.ca/laws/regulation/r25042", "kind": "secondary", "checked": CHECKED},
}

def br(*pairs):  # (threshold, rate) pairs
    return [{"over": a, "rate": r} for a, r in pairs]

FED = {
 "brackets": br((0, .14), (58523, .205), (117045, .26), (181440, .29), (258482, .33)),
 "credit_rate": .14,
 "bpa": {"max": 16452, "min": 14829, "phase_start": 181440, "phase_end": 258482},
 "canada_employment_amount": 1501,
 "quebec_abatement": .165,
 "dividends": {"eligible": {"gross_up": .38, "dtc": .150198}, "non_eligible": {"gross_up": .15, "dtc": .090301}},
 "source": ["cra_t4127", "tt_rates", "tt_dtc_e", "tt_dtc_n"],
}

CPP = {"ympe": 74600, "basic_exemption": 3500, "yampe": 85000,
       "employee_rate": .0595, "base_rate": .0495, "first_additional_rate": .01, "cpp2_rate": .04,
       "max_employee": 4230.45, "max_cpp2_employee": 416.00, "max_self_employed_total": 9292.90,
       "source": ["cra_t4127", "tt_cpp"]}
QPP = {"ympe": 74600, "basic_exemption": 3500, "yampe": 85000,
       "employee_rate": .063, "base_rate": .053, "first_additional_rate": .01, "cpp2_rate": .04,
       "max_employee": 4479.30, "max_cpp2_employee": 416.00, "max_self_employed_total": 9790.60,
       "source": ["cra_t4127", "tt_cpp"]}
EI = {"max_insurable": 68900, "employee_rate": .0163, "employer_multiplier": 1.4, "max_employee": 1123.07, "max_employer": 1572.30,
      "quebec_employee_rate": .0130, "quebec_max_employee": 895.70, "quebec_max_employer": 1253.98,
      "self_employed_min_earnings_prior_year": 9254,
      "note": "Self-employed people only pay EI if they opt in (special benefits only); they pay the employee rate, no employer share.",
      "source": ["cra_t4127", "tt_ei"]}
QPIP = {"max_insurable": 103000, "employee_rate": .0043, "employer_rate": .00602, "self_employed_rate": .00764,
        "self_employed_rate_verified": False,
        "note": "Employee and employer rates are from CRA T4127. The self-employed rate (0.764%) was found only on secondary sites; confirm on revenuquebec.ca before quoting.",
        "source": ["cra_t4127"]}

def prov(name, brackets, bpa, e_dtc, n_dtc, sales, corp, **extra):
    d = {"name": name, "brackets": br(*brackets), "bpa": bpa,
         "dividends": {"eligible_dtc": e_dtc, "non_eligible_dtc": n_dtc},
         "sales_tax": sales, "corporate": corp}
    d.update(extra); return d

def st(kind, gst_hst, pst=0.0, pst_name=None, who=None):
    return {"type": kind, "gst_hst": gst_hst, "pst": pst, "pst_name": pst_name, "pst_collector": who, "total": round(gst_hst + pst, 5)}
def co(small, general, limit=500000, **x):
    d = {"small": small, "general": general, "small_business_limit": limit}; d.update(x); return d

PROV = {
 "AB": prov("Alberta", [(0,.08),(61200,.10),(154259,.12),(185111,.13),(246813,.14),(370220,.15)], 22769, .0812, .0218, st("GST", .05), co(.02, .08)),
 "BC": prov("British Columbia", [(0,.056),(50363,.077),(100728,.105),(115648,.1229),(140430,.147),(190405,.168),(265545,.205)], 13216, .12, .0196,
            st("GST+PST", .05, .07, "PST", "BC Ministry of Finance"), co(.02, .12),
            tax_reduction={"max": 575, "phase_start": 25570, "rate": .0356, "phase_end": 41722},
            notes=["Lowest rate is 5.60% for 2026 (BC Budget 2026); CRA's January 2026 payroll table still showed 5.06%.",
                   "BC tax reduction figures are from CRA's January 2026 table; confirm they were not changed by BC Budget 2026."]),
 "MB": prov("Manitoba", [(0,.108),(47000,.1275),(100000,.174)], 15780, .08, .007835, st("GST+PST", .05, .07, "RST", "Manitoba Finance"), co(0.0, .12),
            bpa_phase_out={"start": 200000, "end": 400000}),
 "NB": prov("New Brunswick", [(0,.094),(52333,.14),(104666,.16),(193861,.195)], 13664, .14, .0275, st("HST", .15), co(.025, .14)),
 "NL": prov("Newfoundland and Labrador", [(0,.087),(44678,.145),(89354,.158),(159528,.178),(223340,.198),(285319,.208),(570638,.213),(1141275,.218)],
            13094, .063, .032, st("HST", .15), co(.02, .15),
            notes=["Basic personal amount is $13,094 for 2026 (NL Budget 2026); CRA's January 2026 payroll table showed $11,188."]),
 "NS": prov("Nova Scotia", [(0,.0879),(30995,.1495),(61991,.1667),(97417,.175),(157124,.21)], 11932, .0885, .015, st("HST", .14), co(.015, .14, 700000)),
 "NT": prov("Northwest Territories", [(0,.059),(53003,.086),(106009,.122),(172346,.1405)], 18198, .115, .06, st("GST", .05), co(.02, .115)),
 "NU": prov("Nunavut", [(0,.04),(55801,.07),(111602,.09),(181439,.115)], 19659, .0551, .0261, st("GST", .05), co(.03, .12)),
 "ON": prov("Ontario", [(0,.0505),(53891,.0915),(107785,.1116),(150000,.1216),(220000,.1316)], 12989, .10, .029863, st("HST", .13),
            co(.032, .115, small_change={"date": "2026-07-01", "rate": .022, "method": "prorate_days"}, note="Small business rate 3.2% until June 30, 2026 and 2.2% from July 1, 2026 (Ontario Budget 2026); prorate by days in the tax year."),
            surtax=[{"over": 5818, "rate": .20}, {"over": 7446, "rate": .36}],
            tax_reduction={"basic": 300},
            health_premium=[{"over": 20000, "base": 0, "rate": .06, "max": 300}, {"over": 36000, "base": 300, "rate": .06, "max": 450},
                            {"over": 48000, "base": 450, "rate": .25, "max": 600}, {"over": 72000, "base": 600, "rate": .25, "max": 750},
                            {"over": 200000, "base": 750, "rate": .25, "max": 900}]),
 "PE": prov("Prince Edward Island", [(0,.095),(33928,.1347),(65820,.166),(106890,.1762),(142520,.19),(200000,.20)], 15000, .105, .013, st("HST", .15), co(.01, .15, 600000),
            notes=["The 5th bracket starts at $142,520 per CRA (updated May 2026); TaxTips shows $142,250. The difference is under $4 of tax.",
                   "The 20% bracket over $200,000 was added by the PEI 2026 Budget."]),
 "QC": prov("Quebec", [(0,.14),(54345,.19),(108680,.24),(132245,.2575)], 18952, .117, .0342, st("GST+QST", .05, .09975, "QST", "Revenu Québec (also collects the GST in Quebec)"),
            co(.032, .115, small_change={"date": "2026-04-30", "rate": .022, "method": "tax_years_beginning_after"}, note="Small business rate drops from 3.2% to 2.2% for taxation years beginning after April 29, 2026. Quebec has extra eligibility conditions for its small business deduction."),
            credit_rate=.14,
            notes=["Quebec runs its own tax system (TP-1 return, Revenu Québec). Figures here give an estimate only; TaxTips notes the 2026 Quebec thresholds were not yet confirmed against Quebec Ministry of Finance publications.",
                   "Quebec residents get a 16.5% abatement of basic federal tax."]),
 "SK": prov("Saskatchewan", [(0,.105),(54532,.125),(155805,.145)], 20381, .11, .02519, st("GST+PST", .05, .06, "PST", "Saskatchewan Finance"), co(.01, .12, 600000)),
 "YT": prov("Yukon", [(0,.064),(58523,.09),(117045,.109),(181440,.128),(500000,.15)], None, .1202, .0067, st("GST", .05), co(0.0, .12),
            bpa_mirrors_federal=True),
}

GST = {
 "small_supplier_threshold": 30000,
 "small_supplier_rule": "Must register once taxable sales (worldwide, including associates) pass $30,000 in a single calendar quarter or over four consecutive calendar quarters. Over the limit in one quarter: registered from the sale that crossed it. Over four quarters: small-supplier status ends at the end of the month after that quarter.",
 "filing_frequency": [{"annual_sales_up_to": 1500000, "assigned": "annual", "optional": "monthly or quarterly"},
                      {"annual_sales_up_to": 6000000, "assigned": "quarterly", "optional": "monthly"},
                      {"annual_sales_up_to": None, "assigned": "monthly", "optional": None}],
 "annual_filer_instalment_threshold": 3000,
 "annual_filer_instalment_rule": "Annual filers whose net GST/HST for a fiscal year is $3,000 or more must pay equal quarterly instalments the next fiscal year.",
 "quick_method": {
   "eligibility_limit_sales_incl_tax": 400000,
   "first_30000_credit_rate": .01,
   "note": "Remit a flat % of GST/HST-INCLUDED sales instead of tracking input tax credits on everyday expenses (ITCs on capital purchases can still be claimed). 1% credit on the first $30,000 of eligible sales each fiscal year. Not allowed for accountants, bookkeepers, lawyers, financial consultants, and some others.",
   "service_rates": {"gst_5": .036, "hst_13": .088, "hst_15": .10, "hst_14": None},
   "goods_rates": {"gst_5": None, "hst_13": None, "hst_15": None, "hst_14": None},
   "verified": False,
   "verify_note": "Service rates 3.6% / 8.8% / 10% are for a business selling in its own province; they were corroborated only by secondary sites on 2026-11-16 because canada.ca could not be read. The Nova Scotia 14% rate and all goods-reseller rates are not filled in. Confirm on RC4058 before quoting.",
   "source": ["cra_rc4058"]},
 "source": ["tt_gst", "tt_sales"],
}

INSTALMENTS = {
 "threshold_net_tax_owing": 3000, "threshold_quebec": 1800,
 "rule": "Instalments are required when net tax owing is more than the threshold in the current year AND in either of the two previous years.",
 "due_dates": ["03-15", "06-15", "09-15", "12-15"],
 "methods": ["no-calculation (pay what CRA's reminder says)", "prior-year (last year's net tax owing, in four equal payments)", "current-year (estimate this year's tax, in four equal payments)"],
 "source": ["cra_inst"]}

DEADLINES = {
 "personal_return_and_balance_due": "04-30",
 "self_employed_return_due": "06-15",
 "self_employed_note": "Self-employed people (and their spouses) file by June 15, but any balance owing is still due April 30; interest runs from May 1.",
 "tax_year_2026": {"balance_due": "2027-04-30", "self_employed_filing": "2027-06-15"},
 "gst_annual_individual_dec31": {"file_by": "06-15", "pay_by": "04-30"},
 "gst_annual_other": "3 months after fiscal year end",
 "gst_quarterly_monthly": "1 month after the end of the reporting period",
 "t4_t4a_slips": "last day of February",
 "corporate": {"t2_due_months_after_year_end": 6, "balance_due_months": 2, "balance_due_months_ccpc_small": 3},
 "payroll_regular_remitter": "15th of the month after the pay date",
 "records_retention_years": 6,
 "source": ["tt_due", "cra_inst"]}

VEHICLE = {
 "class_10_1_ceiling": 39000, "zero_emission_class_54_ceiling": 61000,
 "ceiling_note": "Ceilings are before sales tax. A passenger vehicle costing more goes in its own class 10.1 and CCA is calculated on the ceiling.",
 "cca_rate": .30, "first_year_rate": .15,
 "tax_free_allowance_per_km": {"first_5000": .73, "after_5000": .67, "territories_first_5000": .77, "territories_after_5000": .71},
 "logbook": "CRA expects a logbook of business trips (date, destination, purpose, km) plus odometer readings at the start and end of the year. After one full base year, a representative 3-month sample can be used.",
 "source": ["tt_veh"]}

CCA = {
 "half_year_rule": "In the year you buy an asset, only half the normal CCA is usually allowed. Most class 12 items are exempt from the half-year rule.",
 "classes": {
   "1": {"rate": .04, "what": "Most buildings acquired after 1987"},
   "8": {"rate": .20, "what": "Furniture, appliances, tools costing $500 or more, equipment not in another class, photo and video gear"},
   "10": {"rate": .30, "what": "Motor vehicles, trucks, vans; passenger vehicles under the class 10.1 ceiling"},
   "10.1": {"rate": .30, "what": "A passenger vehicle costing more than the ceiling (each in its own class; CCA on the ceiling only)"},
   "12": {"rate": 1.00, "what": "Tools, kitchen utensils and medical or dental instruments under $500; linens, uniforms; most application software"},
   "14.1": {"rate": .05, "what": "Goodwill, customer lists, franchises with no fixed term"},
   "50": {"rate": .55, "what": "Computers, tablets and systems software"},
   "54": {"rate": .30, "what": "Zero-emission passenger vehicles (up to the ceiling)"},
 },
 "confidence": "Class rates are long-standing regulation values that could not be re-read on canada.ca on 2026-11-16. Confirm the class for any single asset over $5,000.",
 "proposed": {"name": "Productivity Mega Deduction", "status": "PROPOSED, not law as of late September 2026",
              "summary": "Announced Sept 15, 2026 with draft legislation: permanent 100% first-year write-off for most new or used depreciable property acquired on or after Sept 15, 2026. Check whether it has been enacted before using it; until then the engine uses normal CCA.",
              "source": ["fin_mega"]},
 "source": ["tt_cca", "cra_cca"]}

T2125 = {"income": {"8000": "Gross sales, commissions or fees (adjusted)", "8299": "Gross business or professional income", "9369": "Net income (loss) before adjustments", "9946": "Your net income (loss)"},
 "expenses": {"8521": "Advertising", "8523": "Meals and entertainment", "8590": "Bad debts", "8690": "Insurance", "8710": "Interest and bank charges",
              "8760": "Business taxes, licences and memberships", "8810": "Office expenses", "8811": "Office stationery and supplies",
              "8860": "Professional fees (includes legal and accounting fees)", "8871": "Management and administration fees", "8910": "Rent",
              "8960": "Repairs and maintenance", "9060": "Salaries, wages and benefits (including employer's contributions)", "9180": "Property taxes",
              "9200": "Travel expenses", "9220": "Utilities", "9224": "Fuel costs (except for motor vehicles)", "9275": "Delivery, freight and express",
              "9281": "Motor vehicle expenses (not including CCA)", "9936": "Capital cost allowance (CCA)", "9270": "Other expenses", "9945": "Business-use-of-home expenses"},
 "category_to_line": {"Advertising": "8521", "Meals and entertainment": "8523", "Bad debts": "8590", "Insurance": "8690", "Interest and bank charges": "8710",
              "Business taxes, licences, memberships": "8760", "Office expenses": "8810", "Supplies": "8811", "Legal, accounting, professional fees": "8860",
              "Management and administration fees": "8871", "Rent": "8910", "Repairs and maintenance": "8960", "Salaries, wages, benefits": "9060",
              "Property taxes": "9180", "Travel": "9200", "Telephone and utilities": "9220", "Fuel costs (except motor vehicles)": "9224",
              "Delivery, freight, express": "9275", "Motor vehicle expenses": "9281", "Software and subscriptions": "8810", "Business-use-of-home": "9945"},
 "meals_deductible_share": .5,
 "confidence": "Line numbers are from the T2125 form layout used for recent tax years and could not be re-read on canada.ca on 2026-11-16. The accountant should confirm against the current-year form.",
 "source": ["cra_t2125"]}

SMALL_CLAIMS = {"ON": {"limit": 50000, "note": "Raised from $35,000 on October 1, 2025 (O. Reg. 42/25)."},
 "QC": {"limit": 15000, "note": "Small Claims Division of the Court of Québec; principal before interest. Businesses with more than 10 employees generally cannot sue there."},
 "BC": {"limit": 35000, "note": "Civil Resolution Tribunal (online) handles claims up to $5,000; Provincial Court small claims from $5,001 to $35,000."},
 "AB": {"limit": 100000, "note": "Alberta Court of Justice, civil claims (since August 2023)."},
 "missing": ["SK", "MB", "NB", "NS", "PE", "NL", "YT", "NT", "NU"],
 "confidence": "Found through secondary legal sites on 2026-11-16. Look up the court's own site before filing; for provinces listed as missing, search the provincial court site.",
 "source": ["small_claims"]}

WATCH = [
 {"what": "Productivity Mega Deduction (100% first-year write-off)", "status": "Proposed Sept 15, 2026; not confirmed as enacted", "affects": "CCA on equipment bought on or after Sept 15, 2026"},
 {"what": "Tax return due date moving to May 15", "status": "Proposed in Budget 2026 for 2027 returns (filed in 2028). The 2026 return keeps April 30 / June 15", "affects": "deadlines from 2028"},
 {"what": "CPP 2027", "status": "Announced: YMPE $76,700, YAMPE $87,400, employee rate 5.75%", "affects": "2027 rates file"},
 {"what": "EI 2027", "status": "Announced: maximum insurable earnings $70,800, rate 1.64% (Quebec 1.29%)", "affects": "2027 rates file"},
 {"what": "Ontario non-eligible dividend tax credit", "status": "Drops from 2.9863% to 1.9863% on January 1, 2027", "affects": "2027 salary vs dividend"},
 {"what": "Quebec non-eligible dividend tax credit", "status": "Drops from 3.42% to 2.69% for 2027", "affects": "2027 salary vs dividend"},
 {"what": "BC basic personal amount", "status": "New BC government pledged $32,000 for 2027; not legislated", "affects": "2027 BC estimates"},
 {"what": "Newfoundland and Labrador", "status": "Small business rate 2% (2026), 1.5% (2027), 1% (2028); basic personal amount pledge of $15,000", "affects": "2027 NL estimates"},
]

out = {"tax_year": 2026, "checked": CHECKED,
 "how_to_use": "Skills read numbers from this file first and cite the source id. Web-search only when a value is null/missing, marked verified=false, listed under watch, or the question is about a different tax year.",
 "sources": SOURCES, "federal": FED, "cpp": CPP, "qpp": QPP, "ei": EI, "qpip": QPIP, "provinces": PROV,
 "gst_hst": GST, "instalments": INSTALMENTS, "deadlines": DEADLINES, "vehicle": VEHICLE, "cca": CCA, "t2125": T2125,
 "small_claims": SMALL_CLAIMS, "watch": WATCH}
for p in PROV.values():
    p.setdefault("source", ["cra_t4127", "tt_rates", "tt_dtc_e", "tt_dtc_n", "tt_corp", "tt_sales"])
dest = pathlib.Path(__file__).resolve().parent.parent / "plugin/shared/rates/2026.json"
dest.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
print("wrote", dest, dest.stat().st_size, "bytes")
