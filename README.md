# Pocket CEO

Your accountant, cash-flow forecaster, collections helper, contract reviewer, inbox manager, business
consultant, video editor and AI coach, plus a morning brief with your weather, your games and your day.
Built for Canadian small-business owners.

---

## Setting it up (about 10 minutes, no tech skills needed)

**Easiest way:** open the Pocket CEO setup page you were sent and follow its 3 steps. The steps below
are the manual version.

### What you need
- A computer (Mac or Windows).
- A paid Claude plan (Pro or Max). Get one at **claude.ai**.
- Your Gmail account.

### Step 1: Get the Claude app
1. Go to **claude.ai/download**.
2. Click the download button for your computer and open the file.
3. Drag Claude into your Applications folder (Mac) or follow the installer (Windows).
4. Open Claude and sign in.

### Step 2: Add Pocket CEO
1. In the Claude app, click **Code** at the top and start a new session.
2. Copy this line, paste it into the box, and press Enter:
   ```
   /plugin marketplace add andrewdvass/pocket-ceo
   ```
3. Then copy this line, paste it, and press Enter:
   ```
   /plugin install pocket-ceo@pocket-ceo
   ```
4. If it asks you to restart or reload, click yes.

### Step 3: Start
Type this and press Enter:
```
/start
```
Pocket CEO asks you a few easy questions and does the rest: it connects your email, learns how you
write, sets up your private folder, and sends your first morning brief.

That's it.

---

## How to use it
Just talk to it like a person. Some things to try:

| You want to… | Say |
|---|---|
| Know what to put aside for tax | "How much should I set aside?" or `/set-aside` |
| Know if something is a write-off | "Can I write off my truck?" |
| See your cash for the next 3 months | Drag in a bank CSV and say "How's my cash?" or `/cash` |
| Check a big purchase | "Can I afford an $8,400 truck in March?" |
| Get paid | "I invoiced Sarah $1,200" · "Who owes me money?" or `/owed` |
| Get ready for tax time | "Get everything ready for my accountant" or `/year-end` |
| Log a business drive | "Log my drive to the supplier, 30 km" |
| Check a contract before signing | "Read this contract" and drag the file in. You get a Word copy with the changes tracked, ready to send |
| Hire your first person | "I want to hire someone at $50k" (true cost, job post, offer letter, payroll checklist) |
| Know your numbers | "What's my break-even?" "Am I charging enough?" |
| Clean up your email | "Sort my inbox" or `/inbox` |
| Reply to someone fast | "Draft a reply to Sarah" |
| Grow the business | "How do I get more customers?" or `/grow` |
| See your day | "What's my day look like?" or `/today` |
| Check the snow / your game | "How much snow is coming?" "Is there a game tonight?" |
| Save time with AI | "What's new with AI?" or `/ai-update` |
| Edit a video | Drag it in and say "Make this a Reel with captions" or `/edit-video` |
| Track a receipt | Send a photo of it, or `/receipt`. It reads it, files it and keeps your totals |
| See your spending | "How much did I spend on gas this year?" |
| Make sure it remembers | It saves what matters on its own. To be sure: "Remember that…" or `/remember` |

## It remembers you
Everything important (people, customers, prices, promises, goals) is saved as plain notes in
**Documents > Pocket CEO > memory**, written out in full, never shortened. Every new chat starts by
reading them, so you never have to explain yourself twice. You can open and read these notes any time.

## Receipts
Snap a photo, send it. Pocket CEO reads the vendor, date, taxes and total, sorts it into the right tax
category, saves the photo, and adds it to your receipt log (**Documents > Pocket CEO > receipts**).
At tax time say "Get my receipts ready for my accountant." You can also drop a pile of photos in the
**receipts > inbox** folder and it files them next time you chat.

## Exact numbers, not guesses
Pocket CEO does the tax math with a built-in calculator that uses the 2026 federal and provincial rates
(every number has its source and the date it was checked). It works out income tax, CPP (both halves
when you're self-employed), EI, GST/HST, instalments, salary vs dividends and what an employee really
costs, for your province. It checked out against all 336 published 2026 marginal tax rates (federal plus
all 13 provinces and territories). Rates are refreshed every January.

## Your cash and your bank file
Download a CSV of your business bank or credit card account from online banking and drag it in. Pocket
CEO sorts every transaction (and learns from your corrections), finds your repeating bills, forecasts
the next 13 weeks including GST/HST and tax instalments, and tells you before money gets tight. It
never asks for your banking password and never connects to your bank. It only reads files you give it.

## Tax time
Say "Get everything ready for my accountant." Pocket CEO matches your receipts to your bank, lists what's
missing, asks about your home office and car, and builds a folder for your accountant: T2125 totals,
a GST/HST worksheet, a CCA schedule, every receipt photo, and a one-page PDF summary.

## Your privacy
- Pocket CEO **never sends email to anyone**. It only writes drafts. You press Send. (The one exception
  is your own morning brief, sent only to you, if you turn it on.)
- Your notes live in a private **Pocket CEO** folder in your Documents. Only you can see it.
- It never asks for your SIN, bank passwords or CRA login. Don't share them.

## Important
Pocket CEO gives clear, practical answers about tax and law for your province and tells you when
something is serious enough to bring to a licensed accountant or lawyer. It isn't a law firm or an
accounting firm, and it doesn't replace one for big decisions (lawsuits, audits, buying or selling a
business, incorporating).
