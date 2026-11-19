---
name: receipts
description: >
  Tracks the owner's receipts. Use whenever they send a photo, screenshot or PDF of a receipt or bill,
  say "receipt", "log this", "track this expense", "I bought…", or ask "how much did I spend on…",
  "what can I write off this month", "send my receipts to my accountant", or "get my receipts ready for
  taxes", "find my receipt for…", "pull up the receipt from…", "show me that receipt". Reads the
  receipt, saves the photo in a locked vault with a backup copy, logs every detail to a plain Markdown
  file, keeps running totals by month and tax category, and pulls any receipt back up on request.
  Also: "which purchases have no receipt", matching receipts to the bank statement, the vehicle
  mileage log ("log my drive", "how many business km"), and finding receipts sitting in Gmail.
---

# Receipts

The owner snaps a photo. You do everything else. They should never have to type a number.

**Receipts are legal records. Losing one can cost the owner money in an audit. Saving the photo safely
is the most important thing this skill does, more important than reading or categorizing it.**

## Where everything lives (never change this layout)
```
~/Documents/Pocket CEO/receipts/
  inbox/                         <- they can drop photos here any time; you file them
  2026/
    2026-10-13_costco_84.17.jpg  <- every receipt, renamed: date_vendor_total
    receipts-2026.md             <- THE LOG: one row per receipt, never deleted, never shortened
    receipts-2026.csv            <- same rows, for the accountant / spreadsheet
    summary-2026.md              <- totals by month and category, rebuilt from the log
```
Create any missing folder or file from `templates/` in this skill folder.

## When a receipt comes in (photo, screenshot, PDF, or a file in `inbox/`)
1. **Read it.** Pull out: date, vendor, what was bought (short), subtotal, each tax line
   (GST / HST / PST / QST, separately), tip, total, payment method (card last 4 if printed, never more),
   and the vendor's GST/HST number if shown (needed to claim the tax back).
2. **Categorize** using the CRA business-expense categories in `templates/categories.md`. If it
   could be personal, ask one quick question: "Was this for the business? All of it or part?"
   Record the business-use %.
3. **Check for duplicates**: same vendor, date and total already in the log? Ask before adding.
4. **Save the image with the vault tool** (never with a plain copy):
   `bash "${CLAUDE_PLUGIN_ROOT}/skills/receipts/tools/receipt-vault.sh" save "<file>" "<date>_<vendor>_<total>.<ext>"`
   (date first as YYYY-MM-DD, lowercase vendor, no spaces). The full path to the tool is printed at
   the start of each conversation ("Receipt vault tool: …"); if you don't see it, find it with
   `find ~/.claude -name receipt-vault.sh`. It copies the photo into
   `receipts/<year>/`, locks it read-only, records a fingerprint, and makes a second copy in the backup
   folder (iCloud Drive / OneDrive / Dropbox if they have one). Only say "saved" after it prints
   `SAVED` and `BACKUP`. If it prints `ERROR`, tell the owner plainly and try again.
   **Photo only in the chat?** A photo pasted into the chat may not exist as a file you can save. Read
   it, log it, then say: "I've logged it. To keep the photo itself safe, save it into Documents >
   Pocket CEO > receipts > inbox (or drag the file in instead of pasting) and I'll lock it in." Mark the
   row's File column `PHOTO NOT SAVED YET` until it's filed. Never pretend a photo is saved.
   For files in `receipts/inbox/`: save each one with the vault tool, and only after it prints `SAVED`,
   move the inbox copy to `receipts/inbox/filed/` (never delete it).
5. **Add one row** to `receipts-<year>.md` AND `receipts-<year>.csv` (same columns, see templates).
   Append only. Never rewrite, reorder, merge, or summarize old rows. In the CSV write dates as
   `YYYY-MM-DD` and money as plain numbers (`84.17`, no `$`), so the bank matching and the year-end
   package can read them. For `CAPITAL` rows put the CCA class in Notes when you know it (`class 50`
   for a computer, `class 8` for furniture or equipment, `class 10` for a vehicle).
6. **Update** `summary-<year>.md` (recalculate from the full log, don't estimate).
   Then run `receipt-vault.sh verify` so the log and summary are backed up too.
7. **Tell them in 2 lines:**
   "Logged: Costco, Oct 13, $84.17 (GST $4.01), Office supplies, 100% business.
   October so far: $1,240 in expenses, about $310 in tax savings."
   Mark anything unreadable as `CHECK` in the log and ask them about just that field.

## Tax rules to apply (confirm current rates on canada.ca when stating a number)
- **Input tax credits:** if their profile says they're GST/HST registered, the GST/HST they paid on
  business purchases is usually claimable back. Track it in its own column. PST is not claimable;
  it's part of the expense. Quebec: QST is claimed separately with Revenu Québec.
- **Meals and entertainment:** usually only 50% deductible. Log the full amount, flag 50%.
- **Vehicle, phone, home office:** log the business-use %, not 100%.
- **Big purchases** (equipment, computers, furniture, usually over about $500 and lasting more than a
  year) are often depreciated (CCA) instead of expensed at once. Flag as `CAPITAL`; the accountant
  skill explains it.
- Keep receipts **6 years** (CRA). The photo is the record; the paper can go.

## House rules
Follow `../../shared/rules.md` (fact-checking, the rates file, using the calculator, serious
situations, logging). Read it once per conversation if you haven't.

## Keeping them safe (never skip)
- **Never delete, overwrite, rename or edit a saved receipt photo.** They are locked read-only on purpose.
- Every receipt lives in **two places**: `~/Documents/Pocket CEO/receipts/` and the backup folder
  (`receipt-vault.sh where` shows both). If they set up the online backup in setup, it's in a third
  place, their private GitHub repository.
- At the start of every conversation (the session hook does this) and whenever they ask "are my
  receipts safe?", run `receipt-vault.sh verify`. It repairs anything missing from the backup copy.
  If it reports `MISSING`, tell the owner right away which receipt and ask if they still have the paper.
- Fixing a mistake changes the **log row only** (with a dated note), never the photo.

## Pulling them up
When they ask for a receipt ("the Costco one from March", "my laptop receipt", "everything over $500"):
1. Search with `receipt-vault.sh find <words>` (vendor, date, amount or category), or read the log.
2. Show the matching rows: date, vendor, total, category, and the file path.
3. Open the photo for them (`open "<path>"` on Mac, `start "" "<path>"` on Windows) or show it in chat.
4. If they need copies (for the accountant, CRA, a return or a warranty), copy the files into a new
   folder like `~/Documents/Pocket CEO/receipts/for-accountant-2026-10-14/` and tell them where it is.
   Never send them anywhere yourself.

## What they can ask
| They say | You do |
|---|---|
| "How much did I spend on X?" | Total from the log, with the list of rows |
| "What can I write off this month?" | Deductible total by category, tax saved estimate |
| "Any receipts missing?" / "Which purchases have no receipt?" | `receipts reconcile` (see below) |
| "Get my receipts ready for my accountant / taxes" | Hand off to the `accountant` skill's **Year-end package**: it builds the full folder (T2125, GST/HST, CCA, receipts copies, PDF summary) |
| "Log my drive to …" / "How many business km?" | Mileage log (see below) |
| "Find / pull up / show me the receipt for X" | Search, show the rows, open the photo |
| "Are my receipts safe?" | Run verify, report "All 214 receipts safe, 2 copies each" |
| "Fix that receipt" | Change only that row, and add a dated note in the Notes column saying what changed |

## Match receipts to the bank (the calculator does it)
Bank and card CSVs are imported with `money import` (see `../../shared/tools.md`). Then:
`bash "<plugin>/shared/tools/pceo.sh" receipts reconcile --year <year> [--min 25]`
It pairs each business purchase in the bank file with a receipt (same amount, within a few days) and
lists the ones with none. Tell them the headline in one line ("12 purchases, $1,840, have no receipt")
and the five biggest. Transfers, tax payments, loan payments and bank fees never need a receipt (the
statement is the record). Then offer the email sweep below; many "missing" receipts are in Gmail.
Receipts with no bank match were usually paid in cash or on a card that hasn't been imported.

## Find receipts in email (monthly, or when asked)
With the Gmail connector, search the last month (or the period they name) for receipts and invoices:
`(receipt OR invoice OR "order confirmation" OR "payment received" OR "your bill") newer_than:35d`,
plus the senders behind the missing list (Amazon, Uber, Apple, Google, Adobe, Shopify, Canva, phone and
internet companies). For each one:
1. Read the amount, date, vendor and tax lines from the email or its PDF attachment.
2. If an attachment exists, download it and save it with the vault tool like any receipt; otherwise
   log the row with File = `EMAIL: <subject> (<date>)` so it can be found again.
3. Skip anything already in the log (same vendor, date, total).
Report: "Found 9 receipts in your email ($612), all filed. 3 purchases still have no receipt."
Read only: never label, archive or delete their email for this.

## Mileage log (CRA expects one for any vehicle claim)
A logbook is date, destination, purpose and km, plus odometer readings at the start and end of the year.
Commands (see `../../shared/tools.md`): `mileage place "<place>" <one-way km>`,
`mileage add <date> "<place>" "<purpose>" [--km N]`, `mileage odometer <date> <reading>`,
`mileage summary --year <year>`.
- **First time:** ask for today's odometer reading and save it. Ask for their Jan 1 reading too if
  they have it (a service receipt often shows it).
- **From the calendar** (weekly, or when asked): read last week's events that have a location and
  aren't at home. Ask once per new place how far it is from home, one way, and save it with
  `mileage place`. Log each business trip as a round trip with the event title as the purpose
  (`--source calendar`). Ask about anything that might be personal; never log a commute to their
  regular workplace (it's personal).
- **On request:** "I drove to the supplier and back, about 30 km" → `mileage add <today> "Supplier" "pick up stock" --km 30`.
- In December, remind them once to send the year-end odometer reading. The year-end package uses the
  business-km share for vehicle expenses and CCA.

## Nudge, don't nag
On the first conversation of each week, if no receipts were logged in 7+ days, add one line:
"No receipts this week. Snap a photo of any you have and I'll log them."

## Also
- Append a dated line to the memory log (see the `memory` skill) for anything unusual: a big purchase,
  a new recurring bill, a vendor dispute.
- Never ask for full card numbers. Never pay or dispute anything for them.
