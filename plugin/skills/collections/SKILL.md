---
name: collections
description: >
  Money owed to the owner. Use when they say "I invoiced…", "I sent Sarah a bill for…", "who owes me
  money", "who hasn't paid", "chase this invoice", "write a payment reminder", "they still haven't
  paid", "can I take them to small claims", or when the inbox shows an unpaid invoice. Tracks every
  invoice, ages them (current / 30 / 60 / 90 days), spots payments in the bank file, and drafts polite
  then firm then final reminders in the owner's voice. Drafts only; never sends.
---

# Collections

Getting paid is the owner's least favourite job. You track every invoice so nothing slips, and write
the awkward emails for them. Commands are in `../../shared/tools.md` (`invoices ...`). Follow
`../../shared/rules.md`. **Drafts only. Never send, and never contact a client any other way.**

## Tracking
- **They tell you:** "I invoiced Sarah $1,200 yesterday, due in 30 days" →
  `invoices add "Sarah Chen" 1200 --issued <date> --terms 30 --email <if known>`. Confirm in one line.
- **From Gmail** (when sorting the inbox or when asked "check my sent invoices"): search sent mail for
  `subject:(invoice OR facture) newer_than:90d` and invoice PDFs from their invoicing tool (QuickBooks,
  Wave, FreshBooks, Square, Jane, Stripe). Add any not tracked yet; ask if the amount or due date is unclear.
- **Paid:** `invoices match` looks for deposits in the imported bank file that equal an open invoice.
  Confirm with the owner, then `invoices paid <id> [--amount <part payment>]`.
- Save the client and their payment habits in `memory/customers.md` ("pays late but always pays").

## "Who owes me money?"
`invoices aging` gives totals and each invoice's next step. Answer:
```
You're owed $4,850; $2,300 of it is overdue.
- Sarah Chen $1,200, 49 days late: time for a final notice (drafted)
- Bob's Bakery $1,100, 12 days late: friendly reminder (drafted)
- Dr. Lee $2,550, not due until Dec 10
```

## Writing the reminder (in their voice, from `voice.md`)
Match the tool's `next step`, and check `memory/customers.md` first (a good long-time client gets a
softer touch). Every reminder has: the invoice number, amount, original due date, how to pay, and a
specific date. Never threaten anything they haven't decided to do.
- **Friendly reminder** (1 to 14 days late): assume it slipped. "Just a quick nudge on invoice 1042
  for $1,200, which was due Oct 1. Here's the payment link again. Thanks!"
- **Firm reminder** (15 to 44 days): clear and polite. States the days overdue and asks for payment or
  a date by a specific day. Offers a payment plan if that's the owner's style.
- **Final notice** (45+ days): states that if payment isn't received by a specific date (usually 10
  business days), they will take the next step **the owner chose**: stop work, send it to collections,
  or file in small claims court. Ask the owner which before drafting.
Save each as a Gmail draft in the original thread, then `invoices reminded <id> <polite|firm|final>`.
Add the follow-up date to `memory/promises.md` so the brief reminds them.

## Past 90 days: small claims
`invoices aging` includes the province's small claims limit from the rates file. Explain in plain words:
- The limit (for example Ontario $50,000, Alberta $100,000, BC $35,000 with claims up to $5,000 at the
  online Civil Resolution Tribunal, Quebec $15,000 where larger businesses can't use it). Where the
  rates file has no limit for their province, look it up on the provincial court's site and say the source.
- The steps: a final demand letter (draft it), then the court's claim form, filing fee, serving the
  client, and what happens if they don't respond. Check the court's own site for current forms and fees.
- The limitation period: in most provinces a claim must be started within 2 years of the debt being
  due (Quebec: 3 years; a few provinces allow longer). Check the province's limitations law before stating it, and put the
  deadline in `memory/promises.md`.
This is a dispute, so follow the serious-situations order in the house rules: full help first, and only
at the end a one-line note that a paralegal or lawyer can file it for them if it's large or contested.

## In the morning brief
The brief shows one line when something is overdue: "Owed to you: $2,300 overdue (Sarah 49 days)."

## Never
Never send, never call or text a client, never add late fees or interest that the invoice or contract
doesn't allow, and never threaten legal action the owner hasn't chosen.
