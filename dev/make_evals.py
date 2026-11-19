#!/usr/bin/env python3
"""Generates plugin/evals/: one folder per case (case.yaml, scaffold.sh, graders/*.md).

    python3 dev/make_evals.py            # regenerate after changing a case or the rates
    cd plugin && claude plugin eval . --scaffold --allow-tools Bash WebSearch --trust-plugin

Each scaffold.sh recreates a realistic ~/Documents/Pocket CEO/ (profile, and for the bookkeeping cases
six months of imported bank history, receipts and invoices). It is built here with the real tools on
ANCHOR and shifted, in whole weeks, to the day the eval runs, so "today" questions stay realistic.
Expected numbers in the graders come from the tested engine (checked against all 336 published 2026
marginal rates); questions are pinned to the 2026 tax year.
"""
import base64, datetime, io, json, os, shutil, sys, tarfile, tempfile, textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "plugin" / "shared" / "lib"))
from pocketceo import load_rates, tax, bank, collections_ as inv, money  # noqa: E402

R = load_rates(2026)
ANCHOR = datetime.date(2026, 11, 19)
OUT = ROOT / "plugin" / "evals"

PROFILES = {
 "on_sole": dict(name="Maya", biz="Maya Lin Design", what="Graphic design and branding for local businesses", prov="Ontario",
                 struct="sole proprietor", gst="yes", rev="$30k–$100k", city="Ottawa, Eastern time"),
 "ab_corp": dict(name="Jordan", biz="Northline Electric Ltd.", what="Residential electrical contracting", prov="Alberta",
                 struct="corporation (CCPC)", gst="yes", rev="$100k–$500k", city="Calgary, Mountain time"),
 "bc_sole": dict(name="Priya", biz="Priya Shah Bookkeeping", what="Bookkeeping for trades businesses", prov="British Columbia",
                 struct="sole proprietor", gst="yes", rev="$30k–$100k", city="Kelowna, Pacific time"),
 "qc_sole": dict(name="Luc", biz="Luc Tremblay Photo", what="Wedding and event photography", prov="Quebec",
                 struct="sole proprietor", gst="yes", rev="$30k–$100k", city="Montréal, Eastern time"),
}


def profile_md(p):
    return textwrap.dedent("""\
    # Business profile

    - **Owner first name:** {name}
    - **Business name:** {biz}
    - **What they do (one sentence):** {what}
    - **Province / territory:** {prov}
    - **Structure:** {struct}
    - **Charges GST/HST:** {gst}
    - **GST/HST number:**
    - **Revenue range:** {rev}
    - **Fiscal year end:** December 31
    - **Employees / contractors:** none
    - **Regulated profession and regulator:** none
    - **Email:** Gmail connected no
    - **Backup:** private GitHub backup no
    - **Weekly AI update:** off

    ## Personal (for the daily brief)
    - **City and time zone:** {city}
    - **Teams they follow:**
    - **Hobbies and their spots:**
    - **Brief time:** 7:00 am
    - **Brief delivery:** in app

    ## Notes
    """).format(**p)


def bookkeeping_state(home):
    """Six months of bank history, receipts and invoices for the Ontario designer, as of ANCHOR."""
    os.environ["POCKET_CEO_HOME"] = str(home)
    rows, bal, d = [], 4200.0, ANCHOR - datetime.timedelta(days=182)
    while d < ANCHOR:
        if d.day == 1: rows.append((d, "PROPERTY MGMT RENT STUDIO", -1450.0))
        if d.day == 5: rows.append((d, "ROGERS WIRELESS", -95.0))
        if d.day == 12: rows.append((d, "ADOBE *CREATIVE CLOUD", -27.99))
        if d.day == 20: rows.append((d, "INTACT INSURANCE PAP", -64.0))
        if d.weekday() == 4: rows.append((d, "STRIPE PAYOUT", 1180.0))
        if d.weekday() == 1: rows.append((d, "TIM HORTONS #%d" % (d.day * 7), -14.25))
        if d.day == 16 and d.month % 3 == 1: rows.append((d, "CANADA REVENUE AGENCY GST/HST", -2150.0))
        if d.day == 9 and d.month in (8, 10): rows.append((d, "AMAZON.CA MKTP", -238.40))
        if d.day == 23 and d.month == 9: rows.append((d, "BEST BUY 112", -1695.00))
        if d.day == 3 and d.month in (7, 9, 11): rows.append((d, "STAPLES #331", -56.50))
        d += datetime.timedelta(days=1)
    lines = ["Date,Description,Amount,Balance"]
    for d, desc, amt in rows:
        bal += amt
        lines.append("%s,%s,%.2f,%.2f" % (d, desc, amt, bal))
    f = home / "rbc-export.csv"
    f.write_text("\n".join(lines) + "\n")
    bank.import_file(f, "RBC business chequing")
    f.unlink()
    bank.learn("AMAZON.CA", "Office expenses", 100)
    rd = home / "receipts" / "2026"
    rd.mkdir(parents=True, exist_ok=True)
    fields = "num,date,vendor,what,category,subtotal,gst_hst,pst_qst,tip,total,paid_with,business_pct,deductible,itc,vendor_gst_number,file,notes".split(",")
    rec = [("2026-09-22", "Best Buy", "MacBook Air laptop", "CAPITAL", 1500.00, 195.00, 1695.00, "class 50"),
           ("2026-07-03", "Staples", "printer paper and ink", "Office expenses", 50.00, 6.50, 56.50, ""),
           ("2026-09-03", "Staples", "sketchbooks", "Office expenses", 50.00, 6.50, 56.50, "")]
    import csv
    with open(rd / "receipts-2026.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields); w.writeheader()
        for i, (dt, v, what, cat, sub, g, tot, note) in enumerate(rec, 1):
            fn = "%s_%s_%.2f.jpg" % (dt, v.lower().replace(" ", ""), tot)
            (rd / fn).write_bytes(b"\xff\xd8\xff placeholder receipt image")
            w.writerow(dict(num=i, date=dt, vendor=v, what=what, category=cat, subtotal="%.2f" % sub, gst_hst="%.2f" % g,
                            total="%.2f" % tot, business_pct="100", deductible="%.2f" % sub, itc="%.2f" % g, file=fn, notes=note))
    inv.add("Sarah Chen", 1200, issued="2026-09-01", due="2026-10-01", email="sarah@example.com", notes="logo refresh")
    inv.add("Bob's Bakery", 850, issued="2026-11-05", due="2026-11-15", notes="menu boards")
    inv.add("Harbour Dental", 2400, issued="2026-11-10", due="2026-12-10", notes="website mockups")
    mem = home / "memory"; mem.mkdir(exist_ok=True)
    (mem / "preferences.md").write_text("# Preferences\n\n- 2026-10-02 (chat): Cash cushion: never let the business account go below $2,000.\n")
    (mem / "customers.md").write_text("# Customers\n\n- Sarah Chen (Chen Physio): long-time client since 2023, usually pays within a week; slower since summer.\n"
                                       "- Bob's Bakery (Bob Ferreira): new client, first invoice.\n- Harbour Dental: new client, website project.\n")
    (mem / "index.md").write_text("# Memory index\n\nSee people.md, customers.md, money.md, goals.md, promises.md, preferences.md.\n")
    (home / "decisions.md").write_text("2026-10-02 | cashflow | Cash cushion $2,000 | follow-up: monthly CSV\n")


def scaffold(profile_key, books=False):
    tmp = Path(tempfile.mkdtemp())
    home = tmp / "Pocket CEO"
    home.mkdir()
    (home / "profile.md").write_text(profile_md(PROFILES[profile_key]))
    if books:
        bookkeeping_state(home)
    files = {}
    for p in home.rglob("*"):
        if p.is_file():
            rel = str(p.relative_to(home))
            data = p.read_bytes()
            files[rel] = base64.b64encode(data).decode()
    for p in home.rglob("*"):
        try: p.chmod(0o700 if p.is_dir() else 0o600)
        except OSError: pass
    shutil.rmtree(tmp, ignore_errors=True)
    os.environ.pop("POCKET_CEO_HOME", None)
    payload = json.dumps({"anchor": ANCHOR.isoformat(), "shift_dates": books, "files": files})
    return SCAFFOLD % payload


SCAFFOLD = r'''#!/usr/bin/env bash
# Recreates the owner's ~/Documents/Pocket CEO/ for this eval case (generated by dev/make_evals.py).
set -e
python3 - <<'PY'
import base64, datetime, json, os, re
from pathlib import Path
S = json.loads(r"""%s""")
home = Path(os.path.expanduser("~/Documents/Pocket CEO"))
anchor = datetime.date.fromisoformat(S["anchor"])
shift = datetime.timedelta(weeks=round((datetime.date.today() - anchor).days / 7)) if S["shift_dates"] else datetime.timedelta(0)
mv = lambda m: (datetime.date.fromisoformat(m.group(0)) + shift).isoformat()
for rel, b64 in S["files"].items():
    data = base64.b64decode(b64)
    if shift and rel.endswith((".csv", ".md", ".json")):
        data = re.sub(r"\b20\d\d-\d\d-\d\d\b", mv, data.decode("utf-8")).encode("utf-8")
    rel = re.sub(r"20\d\d-\d\d-\d\d", mv, rel) if shift else rel
    p = home / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(data)
PY
'''


def case(name, prompt, graders, profile="on_sole", books=False, tags=(), max_turns=16, runs=3):
    d = OUT / name
    (d / "graders").mkdir(parents=True, exist_ok=True)
    (d / "case.yaml").write_text(textwrap.dedent("""\
    schema_version: "1.1"
    name: {name}
    tags: [{tags}]
    execution:
      prompt: {prompt}
      runs: {runs}
      max_turns: {mt}
      timeout_seconds: 420
      allowed_tools: [Bash, Read, Glob, Grep, Skill, WebSearch]
    context:
      scaffold_script: scaffold.sh
    """).format(name=name, tags=", ".join(tags), prompt=json.dumps(prompt), runs=runs, mt=max_turns))
    s = d / "scaffold.sh"
    s.write_text(scaffold(profile, books))
    s.chmod(0o755)
    for gname, g in graders.items():
        fm = {k: v for k, v in g.items() if k != "criteria"}
        body = g.get("criteria", "")
        (d / "graders" / (gname + ".md")).write_text("---\n" + "".join("%s: %s\n" % (k, json.dumps(v) if isinstance(v, str) and k in ("pattern", "input_match", "tool") else v) for k, v in fm.items()) + "---\n" + body.strip() + "\n")


def skill(n):
    return {"type": "tool_used", "tool": "Skill", "input_match": r'"skill"\s*:\s*"(?:[\w-]+:)?%s"' % n}


def llm(text):
    return {"type": "llm", "criteria": textwrap.dedent(text)}


def rx(pattern):
    return {"type": "regex", "pattern": pattern, "match": "contains"}


def M(x):
    return format(round(x), ",")


def build():
    if OUT.exists():
        for p in OUT.iterdir():
            if p.is_dir() and p.name != "results":
                shutil.rmtree(p)
    OUT.mkdir(parents=True, exist_ok=True)

    # ---------- accountant: exact numbers ----------
    s = tax.set_aside(R, "ON", 80000)
    case("acct-set-aside-ontario", "I'm self-employed in Ontario and I think I'll clear about $80,000 profit this year (2026). What percentage of every payment should I put aside for tax so I'm not caught short in April?",
         {"uses_skill": skill("accountant"),
          "percent": rx(r"\b(2[7-9])\s?%"),
          "quality": llm("""
            Grade the answer to an Ontario sole proprietor with $80,000 of 2026 profit asking what % to set aside.
            The correct figures (2026 rates): total income tax plus CPP on $80,000 is about ${t} (income tax about ${i},
            CPP about ${c} because a self-employed person pays both the employee and employer halves, including CPP2),
            which is about {p}% of profit. PASS only if ALL hold: (1) it gives a single set-aside % between 27% and 29%
            or a dollar total between $21,500 and $22,800; (2) it includes CPP as part of what must be set aside and
            makes clear the self-employed pay both halves (or a CPP figure between $8,400 and $9,300); (3) it says the
            HST collected is separate money that must also be kept aside (not part of this %); (4) it mentions the
            April 30 payment date. FAIL if it uses the 2025 15% federal rate, ignores CPP, or the % is outside 25-31%.
            """.format(t=M(s["tax_and_cpp_on_business_income"]), i=M(s["income_tax_part"]), c=M(s["cpp_part"]), p=s["set_aside_pct_of_profit"]))},
         tags=("accountant", "numbers"))

    i = tax.instalments(R, "ON", 6000, 4500, 0)
    case("acct-instalments", "Ontario sole proprietor. At tax time I owed $4,500 for 2025 and $0 for 2024. For 2026 I expect to owe about $6,000. Do I have to pay quarterly instalments this year, and how much on which dates?",
         {"uses_skill": skill("accountant"),
          "amount": rx(r"1,?125"),
          "quality": llm("""
            Correct answer: yes. Net tax owing is over $3,000 this year (about $6,000) and was over $3,000 in one of the
            two previous years ($4,500 for 2025), so instalments are required. Due dates: March 15, June 15, September 15
            and December 15. Using the prior-year option, each payment is $1,125 ($4,500 / 4); the current-year option
            would be $1,500 each. PASS only if it says yes, lists those four dates, and gives $1,125 per instalment
            (the prior-year amount) as an option. Bonus, not required: notes CRA's reminder (no-calculation) option,
            or that paying the prior-year amount on time avoids instalment interest. FAIL if it says no or gets the
            $3,000 rule wrong.
            """)},
         tags=("accountant", "numbers"))

    case("acct-gst-threshold", "I'm a sole proprietor graphic designer in Ontario and I'm NOT registered for HST yet. My sales: Jan-Mar 2026 $6,000; Apr-Jun $8,000; Jul-Sep $9,000; Oct-Dec I'll do about $8,000. Do I have to register? When do I have to start charging HST?",
         {"uses_skill": skill("accountant"),
          "quality": llm("""
            Facts: the small-supplier limit is $30,000 of taxable sales in a single calendar quarter or over four
            consecutive calendar quarters. Their four quarters total about $31,000, so they pass $30,000 during
            Oct-Dec 2026 (over four quarters, not in one quarter). Under the four-quarter rule they stop being a small
            supplier at the end of the month after that quarter, so they must register and start charging 13% HST
            by about February 1, 2027 (registration within 29 days after that is the usual CRA wording; either framing
            is fine). PASS only if it (1) says yes they must register because they pass $30,000 over four quarters,
            (2) says they don't have to charge HST retroactively on earlier sales, and (3) gives a start date around the
            end of January / February 1, 2027, or clearly explains the "end of the month after the quarter" rule.
            FAIL if it says they must charge from the sale that crossed $30,000 (that is the single-quarter rule) or
            says they don't need to register.
            """)},
         tags=("accountant", "gst"))

    g = tax.gst_quick_vs_regular(R, "ON", 90000, 12000)
    case("acct-quick-method", "I'm a graphic designer in Ontario, registered for HST. This year about $90,000 in sales (before HST) and about $12,000 of business expenses that had HST on them. Should I use the Quick Method? How much would it save me?",
         {"uses_skill": skill("accountant"),
          "quality": llm("""
            Correct figures: they collect 13% HST = $11,700. Regular method: remit $11,700 minus input tax credits of
            $1,560 = about ${reg}. Quick Method for a service business in Ontario remits 8.8% of HST-included sales
            ($101,700 × 8.8% = $8,950) minus the 1% credit on the first $30,000 ($300) = about ${q}. So the Quick Method
            saves about ${sv} a year. PASS only if the answer recommends the Quick Method, gets the saving within $150
            of ${sv} (or both remittance amounts within $150), and mentions it's based on HST-included sales and the
            $400,000 eligibility limit or the 1% first-$30,000 credit. FAIL if it says the regular method is better or
            the saving is off by more than $400.
            """.format(reg=M(g["regular"]["remit"]), q=M(g["quick"]["remit"]), sv=M(g["quick_saves"])))},
         tags=("accountant", "gst"))

    sd = tax.salary_vs_dividend(R, "AB", 120000)
    case("acct-salary-dividend-alberta", "My electrical company (Alberta, small CCPC) will have about $120,000 of profit in 2026 before I pay myself. Should I take it as salary or dividends? How much do I keep each way?",
         {"uses_skill": skill("accountant"), "quality": llm("""
            Reference figures (2026, all profit paid out, basic credits only): all salary: salary about ${sal} after the
            company's CPP share, owner keeps about ${ks}; all dividends: corporate tax at 11% (9% federal + 2% Alberta
            small business rate) about ${ct}, non-eligible dividend about ${dv}, owner keeps about ${kd}. Dividends keep
            about ${df} more this year but pay no CPP. PASS only if: (1) the answer gives an after-tax amount for each
            option, each within 5% of the reference; (2) it states the corporate small business rate in Alberta is 11%
            combined (or 9% federal and 2% Alberta); (3) it explains the CPP / RRSP room trade-off of dividends; and (4)
            it gives a clear recommendation or a mix. FAIL if the corporate rate or the direction of the difference is wrong.
            """.format(sal=M(sd["all_salary"]["salary"]), ks=M(sd["all_salary"]["owner_keeps"]), ct=M(sd["all_dividends"]["corporate_tax"]),
                       dv=M(sd["all_dividends"]["dividend"]), kd=M(sd["all_dividends"]["owner_keeps"]), df=M(sd["dividends_keep_more_by"])))},
         profile="ab_corp", tags=("accountant", "numbers"))

    e = tax.employee_cost(R, "ON", 50000)
    case("acct-employee-cost", "I'm thinking of hiring my first employee in Ontario at $50,000 a year. What will they actually cost me on top of the salary?",
         {"quality": llm("""
            Correct 2026 employer costs on a $50,000 salary in Ontario: employer CPP ${cpp} ((50,000 − 3,500) × 5.95%;
            no CPP2 below $74,600), employer EI ${ei} (1.4 × 1.63% × 50,000), total about ${tot} before workers'
            compensation (WSIB) premiums and vacation pay (at least 4% in Ontario). PASS only if: employer CPP within $50
            of ${cpp}, employer EI within $40 of ${ei}, and it mentions WSIB and vacation pay as further costs. Bonus: the
            Employer Health Tax exemption, payroll account setup. FAIL if it uses 2025 rates (CPP max $4,034, EI 1.64%)
            or forgets the employer EI multiplier.
            """.format(cpp=M(e["employer_cpp"]), ei=M(e["employer_ei"]), tot=M(e["true_annual_cost_before_wcb_and_vacation"])))},
         tags=("accountant", "numbers", "hiring"))

    case("acct-bc-2026-rate", "I'm self-employed in BC with about $45,000 profit in 2026. What's the BC provincial tax rate on my first bracket, and roughly what will my total income tax and CPP be?",
         {"rate": rx(r"5\.6\s?%|5\.60\s?%"),
          "quality": llm("""
            Key fact: BC Budget 2026 raised BC's lowest rate from 5.06% to 5.60% (first bracket up to $50,363).
            The federal lowest rate is 14% for 2026. On $45,000 of self-employment profit the reference total is about
            ${t} (income tax about ${i} and CPP about ${c}, both halves). PASS only if it says 5.6% (not 5.06%), uses 14%
            federal, and the total is within 10% of ${t}. FAIL if it says 5.06% as the 2026 rate.
            """.format(**{k: M(v) for k, v in dict(t=tax.set_aside(R, "BC", 45000)["tax_and_cpp_on_business_income"],
                                                   i=tax.set_aside(R, "BC", 45000)["income_tax_part"], c=tax.set_aside(R, "BC", 45000)["cpp_part"]).items()}))},
         profile="bc_sole", tags=("accountant", "numbers", "freshness"))

    q = tax.contributions(R, "QC", self_employed=60000)
    case("acct-quebec-qpp", "Je suis photographe travailleur autonome au Québec. Profit d'environ 60 000 $ en 2026. Combien vais-je payer au RRQ (QPP) et au RQAP? Answer in English please.",
         {"qpp": rx(r"7,?11[0-9]|7,?12[0-9]"),
          "quality": llm("""
            Reference (2026): Quebec Pension Plan for a self-employed person on $60,000 = 2 × (60,000 − 3,500) × 6.30%
            = ${qpp} (QPP rate dropped from 6.40% to 6.30% for 2026). QPIP self-employed rate about 0.764% on up to
            $103,000 = about ${qp}. PASS only if the QPP figure is within $60 of ${qpp} and it says the self-employed pay
            both halves. QPIP: any figure between $440 and $530 is fine, as long as it does not claim QPIP is the 0.43%
            employee rate only. FAIL if it uses the CPP 5.95% rate or 6.40%.
            """.format(qpp=M(q["cpp_self_employed"]), qp=M(q["qpip_self_employed"])))},
         profile="qc_sole", tags=("accountant", "numbers", "quebec"))

    case("acct-laptop-cca", "I bought a $2,000 laptop (plus HST) for my design business in October 2026. I'm HST registered. How much can I deduct for it on my 2026 return?",
         {"uses_skill": skill("accountant"),
          "quality": llm("""
            Current law: a computer is CCA class 50 (55%). For property available for use in 2024-2027 the Accelerated
            Investment Incentive phase-out suspends the half-year rule, so the 2026 claim is 55% of $2,000 = $1,100
            (the HST is claimed back separately as an input tax credit, $260). A plain half-year-rule answer ($550)
            is outdated but not dangerous. The "Productivity Mega Deduction" (100% write-off for property acquired on or
            after Sept 15, 2026) was announced as a proposal; it should be described as proposed / not yet law, not
            applied as fact. PASS if: it identifies class 50 at 55%, gives $1,100 (or $550 with the half-year rule, as long
            as it flags that the first-year rule may be more generous), says the HST is recovered as an ITC rather than
            deducted, and does not state the Mega Deduction as enacted law. FAIL if it says the full $2,000 is
            deductible this year as settled law, or ignores CCA entirely.
            """)},
         tags=("accountant", "cca"))

    case("acct-cra-review-letter", "I just got a letter from CRA. It says they're reviewing my 2025 return, specifically my vehicle expenses, and they want my logbook and receipts within 30 days of the letter date (Nov 12). I didn't really keep a logbook. I'm panicking. What do I do?",
         {"no_referral_first": {"type": "regex", "pattern": "^(\\W*)(talk to|consult|speak (to|with)|hire|see) (a|an|your) (lawyer|accountant|CPA|professional)", "match": "not_contains", "flags": "i"},
          "quality": llm("""
            This is a serious situation; the expected order is: what it is in plain words and how serious (a review is
            routine, Medium at most); the deadline in bold (about December 12, 2026, 30 days from Nov 12) and what
            happens if missed (the claim can be denied); numbered steps (gather receipts, rebuild the logbook from
            calendar, emails, invoices, maps, odometer readings from service records; never invent trips); a draft reply
            or cover letter; options (ask for an extension, accept a lower %, sample-period approach); and only at the end
            a short line suggesting a CPA review. PASS only if: the deadline is stated (Dec 12 or "30 days from Nov 12"),
            it gives a concrete reconstruction method, it warns not to fabricate a logbook, it includes or offers a
            draft letter, and any professional referral comes at the end, not the start. FAIL if it opens with "consult a
            professional" or tells them to make up a logbook.
            """)},
         tags=("accountant", "serious"))

    # ---------- cashflow (state pre-built in the scaffold) ----------
    case("cash-forecast", "How's my cash looking for the next 3 months?",
         {"uses_skill": skill("cashflow"),
          "quality": llm("""
            The owner's Pocket CEO folder has six months of imported RBC business chequing transactions (current
            balance about $18,000; weekly Stripe payouts of $1,180; rent $1,450 on the 1st; Rogers $95; Adobe $27.99;
            Intact insurance $64; past quarterly CRA GST/HST payments of $2,150) and a $2,000 cash cushion in preferences.
            The next GST/HST payment (end of January) should be estimated from their sales (anything from $800 to
            $2,500 is plausible), not left out or a token amount.
            A good answer uses THAT data (not generic advice): gives a starting balance, the lowest week (amount and
            week) over about 13 weeks, the biggest upcoming bills by name (rent and the next GST/HST payment at least),
            and whether they stay above the $2,000 cushion. It states its assumptions in a line. PASS only if it
            names real items from their bank file and gives a lowest-balance figure with a date. FAIL if it asks them to
            upload a bank statement or gives a generic cash-flow lecture.
            """)},
         books=True, tags=("cashflow",))

    case("cash-afford-laptop-vs-car", "Can I afford to put $6,500 down on a car three weeks from today? Be straight with me.",
         {"uses_skill": skill("cashflow"),
          "quality": llm("""
            The owner's folder has six months of bank history (balance trending up from weekly $1,180 Stripe payouts,
            with rent $1,450 monthly and quarterly GST/HST of $2,150) and a $2,000 cash cushion in memory. A good
            answer runs the purchase through their actual forecast: says yes / not yet with the lowest balance (amount and
            week) after the $6,500, compares it to the $2,000 cushion, and if it's tight suggests a specific later date or
            smaller down payment that works. It should mention any GST/HST payment that lands in the same period.
            PASS only if it gives a yes/no tied to a specific lowest-week dollar figure from their data and refers to
            the $2,000 cushion. FAIL if it answers in generalities or asks for a bank statement.
            """)},
         books=True, tags=("cashflow",))

    case("cash-monthly-bills", "What are all my regular monthly bills and what do they add up to?",
         {"rent": rx(r"1,?450"), "quality": llm("""
            From their imported bank file the repeating bills are: rent $1,450 (monthly), Rogers $95 (monthly),
            Intact insurance $64 (monthly), Adobe Creative Cloud $27.99 (monthly), plus quarterly GST/HST payments of
            $2,150 to CRA. Monthly total of the four monthly bills is about $1,637. PASS only if it lists at least rent,
            Rogers and Adobe with the right amounts, and gives a monthly total within $100 of $1,637 (or $2,354 if it
            converts the quarterly GST/HST into a monthly equivalent and says so). Mentioning weekly coffee spending
            (Tim Hortons, about $14 a week) as a habit is fine. Notes about a read-only folder are a test artifact:
            ignore them. FAIL only if it invents bills that aren't in the data or gets the rent wrong.
            """)},
         books=True, tags=("cashflow",))

    # ---------- collections ----------
    case("owed-who-owes-me", "Who owes me money right now?",
         {"uses_skill": skill("collections"), "quality": llm("""
            Their invoice list (dates shifted to today): Sarah Chen $1,200 due about 7 weeks ago (logo refresh),
            Bob's Bakery $850 due about 4-5 days ago (menu boards), Harbour Dental $2,400 due in about 3 weeks. Total
            owed $4,450, of which $2,050 is overdue. A good answer lists all three with amounts and how late each is,
            gives the total and overdue totals, and says the next step for each (Sarah: a final notice / firm reminder,
            Bob: friendly reminder, Harbour: nothing yet) and offers to draft the reminders. PASS only if totals are
            right ($4,450 and $2,050) and each client's lateness is right within a few days. FAIL if it says it has no
            record of invoices.
            """)},
         books=True, tags=("collections",))

    case("owed-sarah-reminder", "Sarah still hasn't paid the logo invoice. Write the reminder email for me. Don't send it.",
         {"uses_skill": skill("collections"), "amount": rx(r"1,?200"),
          "quality": llm("""
            Sarah Chen owes $1,200 for a logo refresh, due about 7 weeks ago; memory says she's a long-time client
            (since 2023) who usually pays within a week but has been slower since summer. A good draft: in a friendly
            but clear tone fitting a long-time client and ~49 days overdue (firm or final-notice stage, softened for the
            relationship); includes the amount, the original due date, how to pay, and a specific pay-by date; does not
            threaten court, collections or late fees unless the owner chose that (it may ASK the owner what step they
            want if she doesn't pay). It is presented as a draft for the owner to send. PASS only if all of those hold.
            FAIL if it claims to have sent it, threatens legal action unprompted, or invents a late fee.
            """)},
         books=True, tags=("collections",))

    case("owed-small-claims-ontario", "A client in Ontario has owed me $18,000 since March for a website I delivered. They've stopped answering. Can I take them to small claims court? What are the steps?",
         {"limit": rx(r"50,?000"), "quality": llm("""
            Facts: Ontario Small Claims Court handles claims up to $50,000 (raised from $35,000 on Oct 1, 2025), so
            $18,000 qualifies. Ontario's basic limitation period is 2 years from when the claim was discovered (here,
            when payment was due). Steps: a final demand letter with a deadline, file a Plaintiff's Claim (Form 7A)
            online or at the court office with a filing fee, serve the defendant, default judgment if no defence, then
            enforcement if needed. PASS only if it says yes, gives the $50,000 limit, mentions the 2-year limitation
            period, includes a final demand letter before filing (and offers to draft it), and outlines filing/serving.
            Any paralegal/lawyer mention should be a short line at the end. FAIL if it says the limit is $35,000.
            """)},
         tags=("collections", "freshness"))

    # ---------- receipts ----------
    case("receipts-missing", "Which of my business purchases this year don't have a receipt?",
         {"uses_skill": skill("receipts"), "quality": llm("""
            The owner's folder has bank transactions and a receipt log. Receipts exist for the Best Buy laptop
            ($1,695) and two Staples purchases ($56.50). Purchases in the bank file with no receipt include Rogers,
            Adobe, Intact insurance, Tim Hortons (meals), a third Staples ($56.50) and two Amazon orders ($238.40 each).
            Rent may be listed (a lease covers it), but CRA GST/HST payments and transfers never need receipts. A good answer gives a headline count and dollar total, lists the
            biggest items grouped sensibly (e.g. "Rogers, 6 bills"), and offers to look for them in email. PASS only if
            it uses their actual data, does not list the CRA GST/HST payments as missing receipts, and names at least
            Amazon (both orders or a total of $476.80) and Rogers. Notes about a read-only folder are a test artifact.
            FAIL if it asks for their bank statement or gives generic advice.
            """)},
         books=True, tags=("receipts",))

    # ---------- lawyer (parity checks) ----------
    case("law-contractor-vs-employee", "I want to bring on a helper 3 days a week in Ontario. Can I just pay them as a contractor so I don't have to do payroll?",
         {"quality": llm("""
            A good answer: explains it depends on the actual working relationship, not the label; lists the CRA factors
            (control over how/when work is done, who supplies tools and equipment, chance of profit / risk of loss,
            whether they can subcontract or work for others, integration into the business); notes that someone
            working set days under the owner's direction, with the owner's tools, is likely an employee; explains the
            risk (CRA can reassess unremitted CPP/EI plus penalties and interest; Ontario employment standards still
            apply); and gives a practical path (CRA ruling via CPT1 if unsure, or run payroll, with the true cost).
            PASS only if it covers the factors, says this specific setup is likely an employee, and names the CRA
            reassessment risk. FAIL if it says "yes, just call them a contractor".
            """)},
         tags=("lawyer",))

    case("law-serious-demand-letter", "A former client's lawyer sent me a letter saying I owe them $12,000 back because the website I built 'doesn't work', and they'll sue if I don't respond in 14 days. The site works fine, they just stopped paying their hosting. What do I do?",
         {"no_referral_first": {"type": "regex", "pattern": "^(\\W*)(talk to|consult|speak (to|with)|hire|see) (a|an|your) (lawyer|accountant|CPA|professional)", "match": "not_contains", "flags": "i"},
          "quality": llm("""
            Expected order (serious situation): what this is and how serious (a demand letter, not a lawsuit yet;
            Medium); the 14-day deadline in bold; steps (don't admit fault or ignore it, gather the contract, sign-off
            emails, invoices, proof the site works and that hosting lapsed on their side, screenshots or archive
            captures); a draft calm reply denying the claim with facts; options and likely outcomes (in Ontario $12,000
            is within Small Claims Court's $50,000 limit, so even if they sue it's small claims); only at the end a short
            note that a lawyer or paralegal can review the reply. PASS only if it includes a draft response, states
            the deadline, lists the evidence to gather, and the referral is last. FAIL if it opens with "get a lawyer"
            as the main advice.
            """)},
         tags=("lawyer", "serious"))

    # ---------- ceo: mixed decision ----------
    case("ceo-buy-van-decision", "Should I buy a $9,000 used van for the business next month? I'd use it about 70% for work.",
         {"quality": llm("""
            The owner has six months of bank history in their Pocket CEO folder, a $2,000 cash cushion, and is an
            HST-registered Ontario sole proprietor. A strong answer: checks affordability against their actual
            forecast (lowest balance after the purchase vs the $2,000 cushion), explains the tax side (class 10 at 30%,
            claim 70% business use, a logbook is required; the HST can be partly recovered as an ITC in proportion to
            business use since it's a passenger vehicle under 90%), gives an after-tax cost or yearly deduction estimate,
            and gives a clear yes / yes-if / not-yet in the short-answer format. PASS only if it uses their cash data
            for affordability AND covers the 70% business-use / logbook point. FAIL if it is generic with no numbers.
            """)},
         books=True, tags=("ceo",))


if __name__ == "__main__":
    build()
    print("cases:", len([p for p in OUT.iterdir() if p.is_dir() and p.name != "results"]))
