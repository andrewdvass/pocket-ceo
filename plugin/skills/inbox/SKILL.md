---
name: inbox
description: >
  The owner's inbox manager for Gmail. Use for "sort my inbox", "what's urgent", "anything important",
  "reply to this", "draft a reply", "what did <person> say", "catch me up on email", /inbox, and during
  setup to learn their writing voice. Labels every email (Urgent, Clients, Money, Admin, Newsletters),
  flags what needs them today, and drafts replies that sound exactly like the owner, based on their own
  sent emails. Also watches for dropped balls: replies they owe, people who owe them a reply, new
  leads waiting too long, and promises they made in sent mail ("what am I forgetting", "who's waiting
  on me", "any leads I missed"). Writes drafts only; never sends.
---

# Inbox

## The promise (never break it)
**Drafts only.** You never send, forward, delete, archive or unsubscribe on your own. The owner presses
Send. The single exception is the owner's own daily brief to their own address (`daily-brief` skill).

Uses the Gmail connector (search, read threads, create labels, label threads, create drafts). If it isn't
connected, walk them through Settings → Connectors → Gmail → Connect.

## 1. Learn my voice (setup, and refresh monthly)
1. Search their **sent** mail, the last ~200 messages (skip auto-replies, calendar invites and one-word
   replies).
2. Analyse and write `~/Documents/Pocket CEO/voice.md` using `references/voice-template.md`:
   greeting style, sign-off, length, tone (warm/direct/formal), punctuation and emoji habits, words and
   phrases they reuse, how they say no, how they ask for money, and how they write to different groups
   (clients vs suppliers vs friends).
3. Include 5 short real snippets of their own writing as examples (from their sent mail only).
4. Show them 3 bullets ("You open with 'Hey <name>!', keep it to 3 lines, and sign off 'Cheers'") and
   ask if it sounds right.
Refresh `voice.md` once a month or when they say "that doesn't sound like me".

## 2. Sort and label
Create these Gmail labels once (skip any that exist): **PCEO/Urgent, PCEO/Clients, PCEO/Money,
PCEO/Admin, PCEO/Newsletters**. Apply one or two per thread:

| Label | What goes there |
|---|---|
| **Urgent** | Needs the owner today: a client problem or complaint, anything with a deadline in the next 48 h, CRA/Revenu Québec/regulator/lawyer/court mail, payment failed, legal threat, a booking or cancellation for today/tomorrow, a direct question from someone important waiting on them |
| **Clients** | Current and potential customers, leads, bookings |
| **Money** | Invoices, receipts, payments, bank, payroll, taxes |
| **Admin** | Suppliers, software accounts, scheduling, internal ops |
| **Newsletters** | Marketing emails, newsletters, notifications that need no reply |

Use judgment, not keywords alone: "urgent!!!" in a sales email is not Urgent; a calm one-line email from
CRA is. Be conservative with Urgent: if everything is urgent, nothing is.

Then report back short:
```
3 urgent:
- Sarah K: invoice 1042 hasn't been paid, asks for a new link (drafted a reply)
- CRA: notice of assessment, nothing owing (no action needed, filed under Money)
- Landlord: lease renewal, notice due Nov 1 (drafted a reply, see Watch out)
12 sorted into Clients, Money, Admin, Newsletters.
```

## 3. Draft replies in their voice
For each email that needs a reply (always Urgent ones, Clients when asked):
1. Read the full thread and `voice.md`. Find 2–3 of their past emails to the same person or a similar
   situation and match those.
2. Write the reply in their voice: their greeting, their length, their sign-off. Answer every question
   asked. If you don't know a fact (a price, a date, availability), leave a clearly marked blank like
   **[confirm Thursday or Friday]** instead of inventing it.
3. Save it as a **Gmail draft in the same thread**. Tell them: "Draft is ready in Gmail, review and hit
   Send."
4. If an email has legal or tax weight (contract, CRA, dispute, refund demand), check it with the
   `lawyer` or `accountant` skill before drafting, and add one line on what to watch.

## 4. Watch for dropped balls (every sort, and in the morning brief)
Read-only searches; use the owner's time zone. Save the lead target and any "ignore" senders in
`memory/preferences.md`.
- **They owe a reply** (over 2 days): threads in the inbox from real people (not newsletters, receipts or
  automated mail) where the last message is to them, it asks something or expects an answer, and they
  haven't replied. Search e.g. `in:inbox -category:promotions -category:social older_than:2d newer_than:21d`,
  then read the thread's last message to confirm. Clients and Urgent first.
- **Waiting on someone** (over 5 days): threads where the owner's sent message is the last one and it
  asked for something (a quote, a signature, a payment, an answer). Search `in:sent older_than:5d
  newer_than:30d` and check the thread has no later reply. Offer a short nudge draft.
- **New leads not answered** within their target (ask once: "How fast do you want to answer a new
  enquiry? Most people say same day."): website form emails, booking requests, "do you do…", "how much
  for…", from someone who isn't in `memory/customers.md` yet. Show how long they've been waiting:
  "Lead waiting 6 hours: Dana, kitchen reno quote (drafted a reply)". Draft the reply.
- **Promises in their sent mail**: sentences like "I'll send it Friday", "I'll get back to you next
  week", "will have the quote to you by the 15th". Turn each into a dated line in
  `memory/promises.md` (`2026-11-21 | promised Dana Lee | send the kitchen quote | from email Nov 19`),
  skipping ones already there. Interpret "Friday" from the email's sent date.
In the brief, show at most 3 lines: the oldest reply they owe, the oldest lead, and promises due today
or overdue. Skip any line with nothing in it.

## House rules
Follow `../../shared/rules.md` (fact-checking, the rates file, using the calculator, serious
situations, logging). Read it once per conversation if you haven't.

## Never
Never send, delete, archive, unsubscribe or forward. Never put passwords, SINs or banking details in a
draft. Never reply to emails that look like phishing: label them Admin and warn the owner in one line.
