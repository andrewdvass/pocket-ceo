---
name: hiring
description: >
  Hiring the owner's first (or next) person. Use for "should I hire someone", "I want to hire", "what
  does an employee cost", "write a job post", "interview questions", "offer letter", "how do I set up
  payroll", "do I need WSIB / WCB", "source deductions", "ROE", "vacation pay", "my first employee".
  Works out the true cost for their province, the job post, interview questions, an offer letter that
  fits their province's employment standards, and the full first-employee checklist (CRA payroll
  account, remittances, workers' compensation, T4s, ROEs) where owners lose the most to penalties.
---

# Hiring

Follow `../../shared/rules.md`. Numbers from the calculator (`../../shared/tools.md`). Employment law
is provincial (`../lawyer/references/province-laws.md`); check the current rule on the province's site
or CanLII before stating minimum wage, vacation, overtime, notice or holiday rules, and name the source.

## 1. Should they hire, and what will it cost?
1. Employee or contractor? Use the lawyer skill's **Contractor or employee?** check. Set days, their
   tools and their direction usually means employee, whatever the paper says.
2. True cost: `tax employee-cost --salary <yearly pay>` (employer CPP, CPP2, EI, QPIP in Quebec). Add,
   with sources checked live: vacation pay (at least 4% in most provinces, more after years of service),
   public holiday pay, workers' compensation premium for their industry rate, and any provincial payroll
   or health tax above its exemption (Ontario EHT, BC EHT, Manitoba levy, NL tax, Quebec HSF).
3. Can the business carry it? If a bank file is loaded, run `cash afford <monthly cost> <start date>`
   for the first month and `cash forecast` with the cost added as a planned monthly item
   (`money expect`), and say whether the lowest week stays above their cushion.
Answer: yes / not yet / yes if…, with the yearly cost and the monthly cash impact.

## 2. The job post and interview
- **Job post**, in their voice: what the business does in a sentence, the actual tasks, hours and days,
  pay (range or exact; several provinces require pay in public job posts, including Ontario and BC:
  check the current rule), location, how to apply. No age, family status or other protected grounds;
  "Canadian experience" requirements are restricted in some provinces (e.g. Ontario): avoid them.
- **Interview questions**: 6 to 8, about the real work ("Tell me about a time a customer was upset with
  you. What did you do?"), plus a short practical task where it fits. A one-page scoring sheet.
  Never ask about age, family plans, religion, health, or immigration beyond legal eligibility to work.

## 3. The offer letter
A plain offer letter (save as Word with `contract redline <file>.txt [] <file>.docx`, with an empty
change list) with: job title, start date, pay and pay schedule, hours, vacation (at least the provincial
minimum), probation, benefits if any, the confidentiality and IP terms that matter to them, and a
**termination clause that at least meets the province's employment standards**. A clause that pays less
than the minimum is void and the employee can then claim much more at common law, so write it to
meet or exceed the statute (and check current enforceability rules: Ontario courts have struck down many
termination clauses; suggest a one-time lawyer review of the template, last, if they'll reuse it).
Ontario: no non-compete for employees (with narrow exceptions); keep a non-solicit narrow. Quebec:
offer letter in French unless the employee asks for English, and CNESST rules.

## 4. The first-employee checklist (in order, with dates)
1. **CRA payroll account (RP)** added to their business number, before the first payday
   (online in My Business Account, or by phone).
2. **TD1 forms** (federal and provincial) from the employee on day one; their SIN for payroll only
   (the business collects it for CRA; Pocket CEO never stores it).
3. **Workers' compensation**: register with WSIB (ON), WorkSafeBC, WCB (AB, SK, MB, NS, NB, NL, PE,
   territories) or CNESST (QC) within the deadline after hiring (often 10 days; check theirs).
4. **Payroll method**: a payroll service (Wagepoint, Humi, QuickBooks Payroll, ADP) for most owners;
   CRA's PDOC calculator if they run it themselves.
5. **Remittances**: source deductions (tax, CPP, EI) are due by the 15th of the month after the pay date
   for most new small employers (regular remitter). Late remittances carry penalties from 3% to 10%
   and up. Put the 15th of each month in `memory/promises.md`.
6. **Records**: pay statements each payday, hours, vacation taken and owed, kept for the years the
   province and CRA require.
7. **Year end**: T4 slips to the employee and CRA by the last day of February; Quebec also RL-1.
8. **When someone leaves**: a Record of Employment (ROE). Filed electronically, it's generally due
   within 5 calendar days after the end of the pay period in which their earnings stopped (check
   Service Canada's current rule). Final pay and vacation pay by the provincial deadline.
9. **Workplace basics** by province: posters (Ontario's ESA poster), a harassment policy where required,
   health and safety training for the job.
Give it as a checklist with the dates for their start date, and save each date in `memory/promises.md`.

## Never
Never store an employee's SIN, bank details or health information. Never write a job post or interview
question that touches protected grounds. Never tell them a termination clause is "fine" without checking
it against their province's minimums.
