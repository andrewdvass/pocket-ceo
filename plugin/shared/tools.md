# The Pocket CEO calculator (`pceo`)

Exact numbers come from here, not from memory. It reads the sourced rates file and the owner's own
records in `~/Documents/Pocket CEO/`. Standard library Python only; nothing is sent anywhere.

**Run it:** `bash "<plugin>/shared/tools/pceo.sh" <group> <command> [options]`
The full path is printed at the start of each conversation ("Pocket CEO calculator: ..."). If you don't
see it: `find ~/.claude -name pceo.sh -path "*pocket-ceo*" | head -1`.
If it prints `NEEDS PYTHON`, do what it says for the owner, then retry.

Province and GST/HST status come from `profile.md` automatically; add `--province XX` to override.
`--year 2026` picks the tax year (default: this year; a year with no rates file falls back to the
newest one and says so). Add `--json` for raw numbers. Every answer ends with its sources: pass the
main one on to the owner in one line.

| Owner asks | Command |
|---|---|
| "How much should I set aside for tax?" | `tax set-aside --profit 80000 [--revenue 95000] [--employment 40000]` |
| "How much tax will I owe?" | `tax estimate --self-employed 80000 [--employment ..] [--eligible ..] [--non-eligible ..] [--rrsp ..]` |
| "Do I have to pay instalments?" | `tax instalments --this-year 6000 --last-year 4500 --two-years-ago 0` (net tax owing each year) |
| "Should I use the Quick Method?" | `tax gst-compare --sales 90000 --expenses 12000 [--goods] [--quick-rate 0.088]` |
| "Do I need to register for GST?" | `tax gst-watch --from-bank` or `tax gst-watch 2026Q1=8000 2026Q2=9500 ...` |
| "Salary or dividends?" (corporation) | `tax salary-dividend --profit 120000` |
| "What does an employee really cost?" | `tax employee-cost --salary 48000` |
| Any rate or deadline | `rates get provinces.ON.brackets`, `rates get deadlines`, `rates get watch` |
| A bank or card CSV | `money import <file> [--account "RBC chequing"] [--flip]` |
| Sort what it couldn't | `money review`, then `money learn "<merchant>" "<category>" --business 100` |
| Fix one transaction | `money set <id> --category "..." --business 50 --note "half personal"` |
| "How am I doing this year?" | `money summary [--month 10]` |
| Repeating bills | `money recurring` |
| A future payment in or out | `money expect 2027-03-01 -8400 "New truck"` |
| Cash for the next 13 weeks | `cash forecast [--balance 12000] [--floor 2000] [--conservative]` |
| "Can I afford it?" | `cash afford 8400 2027-03-01 --what "truck" [--floor 2000]` |
| The brief's cash line | `cash brief` (prints nothing when all is fine) |
| "Which purchases have no receipt?" | `receipts reconcile [--min 25]` |
| "Get everything ready for my accountant" | `yearend build --year 2026` |
| "I invoiced Sarah $1,200" | `invoices add "Sarah Chen" 1200 [--due 2026-12-01] [--email ..]` |
| "Who owes me money?" | `invoices aging`, `invoices match` (finds payments in the bank file) |
| After drafting a reminder | `invoices reminded INV-2026-003 firm` |
| They got paid | `invoices paid INV-2026-003 [--amount 600]` |

Categories match the receipts skill (`receipts/templates/categories.md`) plus: `Sales / income`,
`Transfer (not income or expense)`, `Owner pay / draw`, `Tax payment (CRA / Revenu Québec)`,
`GST/HST remittance`, `Loan payment`, `Personal (not deductible)`.

What the numbers include: federal and provincial tax with basic personal amounts, CPP/QPP and CPP2
(both halves when self-employed), EI (employees, or self-employed who opt in), QPIP, dividends, Ontario
surtax and health premium, Ontario and BC low-income reductions. What they leave out: other personal
credits (spouse, tuition, medical, donations, age), AMT, benefit clawbacks. Say "estimate, basic credits
only" when that matters. Quebec results are estimates.
