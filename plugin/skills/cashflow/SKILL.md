---
name: cashflow
description: >
  The owner's cash-flow forecast. Use when they share a bank or credit card CSV, or ask "how's my
  cash", "will I have enough for…", "can I afford…", "should I buy the truck now or in March",
  "when will I run low", "what are my monthly bills", "what's coming out this month", /cash. Imports
  bank exports from any Canadian bank, learns how they categorise things, finds repeating bills and
  income, and projects the next 13 weeks week by week, including GST/HST and tax instalments, so
  "can I afford it?" gets an answer in dollars and a date.
---

# Cash flow

Running out of cash, not a lack of profit, is what closes most small businesses. Your job: tell the
owner what their bank balance will look like for the next 13 weeks, warn them early, and answer
"can I afford it?" in dollars. All numbers come from the calculator; see `../../shared/tools.md`.
Follow `../../shared/rules.md`.

## Getting their bank data (first time, then monthly)
1. Ask for a CSV export: "In your online banking, open the account, choose Download or Export
   transactions, pick CSV (or 'Spreadsheet'), and the last 3 to 6 months. Then drag the file in here."
   RBC, TD, BMO, Scotiabank, CIBC, Desjardins, ATB, Tangerine, National Bank and credit unions all
   offer it; if they can only find PDF, read the PDF for a one-off answer and ask for CSV next time.
2. `money import <file> --account "<bank and account, e.g. RBC business chequing>"`. For credit card
   files where purchases show as positive numbers, the tool warns you: re-run with `--flip`.
3. **Confirm it read correctly**: "I read 214 transactions from Aug 1 to Nov 18; the last balance is
   $6,412.10. Does that match your bank?" If not, stop and fix it before forecasting.
4. `money review`: ask about the unknowns **grouped by merchant**, biggest first, at most 5 questions
   per sitting ("Costco, 6 times, $1,240: business, personal, or split?"). Save every answer with
   `money learn "<merchant>" "<category>" --business <pct>` so it never asks again. One-off answers:
   `money set <id> ...`.
5. Save the account name and the date of the last import in `memory/money.md`. Each month, ask for
   the new export (the importer skips anything already loaded, so overlapping dates are fine).

## The forecast
`cash forecast [--balance <today's total cash>] [--floor <cushion>]`
- The balance comes from the bank file; if several accounts or the file is old, ask for today's total.
- Ask once for their **cushion** ("What's the lowest you're comfortable letting the account get?")
  and save it in `memory/preferences.md`. Pass it as `--floor`.
- GST/HST remittances are added automatically when the profile says they charge GST/HST (quarterly
  by default; `--gst annual` for annual filers). Tax instalments: `--instalment <amount each>` if
  they pay them (the accountant skill works out the amount).
- Planned money they know about and the bank doesn't: `money expect <date> <amount> "<what>"` (a
  client deposit expected, a truck, a tax bill, a slow month). Positive = in, negative = out.
- `--conservative` drops average everyday income and counts only repeating deposits and planned
  ones. Use it when their income is lumpy or they ask "worst case".

Report it in 4 lines, not the whole table (offer the table):
```
Cash for the next 13 weeks: starts at $6,412, lowest is $1,150 in the week of Apr 6
(rent + GST/HST $2,310 the same week). Ends around $9,800.
Biggest bills coming: rent $1,450 (1st), GST/HST $2,310 (Apr 30), insurance $890 (Mar 12).
Watch out: you dip under your $2,000 cushion in early April. Moving the $1,200 software renewal to May fixes it.
```
Always say what it assumes (everyday spending per week, everyday income) in one line.

## "Can I afford it?"
`cash afford <amount> <date> --what "<thing>" [--floor <cushion>]`
Answer with the tool's sentence ("If you buy the $8,400 truck on Mar 1, your lowest week is $1,150
in the week of Apr 6."), then one line on the alternative if it's tight (a later date, a deposit,
financing). If they'd go below zero, say "Not yet" plainly and show the date that works: try later
dates with the tool until it says yes. Log the decision in `decisions.md`.

## Monthly bills
`money recurring` lists what repeats (rent, phone, software, payroll, loan) with the next date and a
monthly total. Offer: "These 14 subscriptions cost $612 a month. Want me to flag ones you might not use?"

## In the morning brief
The daily brief runs `cash brief`. It prints one line only when something needs attention (a dip below
the cushion, a big bill in the next 7 days, GST/HST or an instalment coming). Nothing printed = skip the line.

## Never
Never ask for online banking logins or connect to their bank directly. Never move money. Only files
they export and give you.
