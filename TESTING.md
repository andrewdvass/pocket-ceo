# Pocket CEO manual tests (Phase 1)

Run each test on a **clean** user account (a new macOS user, a Windows VM or a friend's PC), not your own
setup. Write pass / fail and what happened. Paste failures to Claude; it fixes them on a branch.

| # | Test | Pass when | Mac | Windows | Notes |
|---|---|---|---|---|---|
| 1 | Fresh install from the setup page, then `/start` | Profile, voice, memory and receipts folders exist; setup finishes without you typing a command | | | |
| 2 | Daily brief, local scheduled task | Fires next morning at the chosen time with the computer on; weather, team game and calendar lines are right | | | |
| 3 | Monday AI update task | Fires Monday 8:00; one tip, not a list; logged in `decisions.md` | | | |
| 4 | Cloud morning brief (`/cloud-brief`) | Arrives with the computer **off**; email goes only to the owner | | | |
| 5 | Video editor first run, Mac | Installs ffmpeg + faster-whisper itself; a phone clip comes back upright, captioned, in Downloads | | n/a | |
| 6 | Video editor first run, Windows | Same as 5 (winget path) | n/a | | |
| 7 | Receipts | Photo in → `SAVED` + `BACKUP`; `verify` after deleting the backup copy repairs it | | | |
| 8 | Memory across sessions | Tell it a fact, close the app, new session: it knows it without being asked | | | |

## New in v0.5 (money tools)

| # | Test | Pass when | Mac | Windows | Notes |
|---|---|---|---|---|---|
| 9 | Calculator on a fresh machine | During `/start`, the calculator check passes, or on a Mac without developer tools it asks you to click Install once and then passes. No surprise pop-ups at any other time | | | |
| 10 | "How much should I set aside?" | Gives a % and monthly amount for your province, with a source line. Spot-check against a TaxTips calculator: within 2% | | | |
| 11 | Real bank CSV import (your bank) | Drag in a real export: the transaction count, date range and ending balance match online banking. Try one credit card export too (it should warn about `--flip` if needed) | | | |
| 12 | Learning | Correct one merchant ("Costco is half personal"); import next month's file; it doesn't ask again | | | |
| 13 | Cash forecast and "Can I afford it?" | Names your real rent and bills; the lowest week looks believable; afford answer gives a date and amount | | | |
| 14 | Invoices | "I invoiced X $500 due in 2 weeks", then later "who owes me": correct; the reminder is a Gmail draft, never sent | | | |
| 15 | Year-end package | "Get everything ready for my accountant": folder with summary PDF, T2125, GST/HST, CCA, receipts. Show it to your accountant: would they use it? | | | |
| 16 | Morning brief money lines | With a bank file loaded, the brief shows a cash / owed / deadline line only when there's something to say | | | |

Tester, date, machine:
