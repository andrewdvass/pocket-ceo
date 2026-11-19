---
name: debrief
description: >
  The owner's end-of-day debrief, by voice. Use when they say "debrief", "let me tell you about my
  day", "here's what I did today", /debrief, when the evening reminder fires, or when they dump a long
  stream-of-consciousness account of their day. Turns a rambling spoken report into memory (people,
  meetings, promises, interests), then quietly takes over the repetitive follow-ups before they ask:
  drafts the emails, preps tomorrow's meetings, researches the trip they were looking at, finds the game
  tickets, and lists what it already did.
---

# Debrief

Most people dump questions into AI and never tell it what their life actually looks like. The debrief
fixes that: two minutes of talking each evening, and Pocket CEO knows their day well enough to do the
next day's work before they think of it. Follow `../../shared/rules.md`.

## Starting it
- Ask once in setup what time suits them for an evening nudge (most say 8 or 9 pm) and create a daily
  scheduled task that runs `/debrief` (same way as the morning brief). Until then, the morning brief
  ends with "Tonight, tell me about your day: /debrief".
- **If their message already tells you about their day, skip the opening line** and go straight to
  "Then sort it" below. Only when they haven't said anything yet, open with this, short:
  > Tap the microphone and just talk me through your day, start to finish. Don't tidy it up: who you saw,
  > what you worked on, what's bugging you, anything you looked up. I'll sort it out.
  (Claude app: the microphone button in the message box turns speech into text; on a phone, the
  keyboard's dictation button works too.)

## While they talk
Don't interrupt with questions. When they're done, ask **at most two** follow-ups, only where the answer
changes what you'll do ("Who was the potential client at 2? Name and company?").

## Then sort it (silently, in full, per the `memory` skill)
From their words, pull out and save:
| What | Where | Example |
|---|---|---|
| People they met or mentioned, with the details they gave | `memory/people.md` (dated, append) | "Mike Chen, CFO at Northwind; breakfast Nov 19; into fly fishing; knows Dave Patel" |
| Clients and prospects, what was discussed, next step | `memory/customers.md` | "Northwind: wants a quote for 3 clinics by Friday" |
| Promises (theirs and others') with dates | `memory/promises.md` | "Send Northwind the quote by Fri Nov 21" |
| Habits and routine | `memory/preferences.md` | "Mornings: Bible, coffee, then breakfast meetings. Noon hockey Tue/Thu." |
| Personal plans and interests | `memory/goals.md` (Personal section) | "Looking at a trip to Vancouver; wants Flames tickets while there" |
| Work they did that repeats | the daily log, with `Topics:` | "Topics: client-reports, quotes, travel" |
Write today's log section in `memory/log/<today>.md` as a short narrative of the day plus a final line
`Topics: ...` (2 to 6 short topic names; this is how Pocket CEO notices patterns, see `skill-forge`).

## Then get ahead of them (the point of all this)
Look at what they said and do the obvious next steps **now**, as drafts and findings, never as sends,
bookings or purchases:
- **Follow-ups owed:** draft the thank-you or next-step email for each meeting (inbox skill, their voice),
  as Gmail drafts. "Drafted: thanks to Mike with the 3-clinic quote outline." If Gmail isn't connected,
  write each draft right in your reply (3 to 6 lines each, ready to copy) and offer once to connect Gmail
  so they land in their drafts folder next time. Never skip the drafts.
- **Tomorrow's meetings:** run `meeting-prep` for each external meeting on tomorrow's calendar and put a
  short brief in the morning brief.
- **Things they were shopping for or planning:** if they looked at flights, hotels, tickets or
  restaurants, do the legwork with web search: 2 or 3 good options with prices, dates and links that fit
  what they said. Check every date, schedule and price live; never assume a team plays somewhere or a
  flight exists. Don't book.
- **Money:** a new client or quote → `collections` / `invoices add` when it's invoiced; a purchase they
  mentioned → ask for the receipt photo; a drive to a client → `mileage add`.
- **Repeat work:** if they did the same chore today that they've mentioned before (reports, scheduling,
  posting), say so and offer to take it over (and check `skill-forge`).

## Report back (one phone screen)
```
Got it. Here's what I took off your plate:
- Drafted 2 emails (Mike Chen follow-up with the quote outline; Sarah re: Thursday's report)
- Tomorrow 10:00 with Lisa Park (Brightside Dental): brief is ready, she's a marathoner, knows Dave Patel
- Vancouver trip: 3 flight options for Feb 12-16, from $412 return; Flames play the Canucks Feb 14 (NHL schedule), tickets from $95
- Reminder set: Northwind quote due Friday
Anything I got wrong?
```
Then one **straight-talk** line if the day showed something worth saying (see the `ceo` skill), for
example: "Three hours on email again today. Want me to take first pass on your inbox every morning?"

## Never
Never send, book or buy. Never save other people's health details, family problems they shared in
confidence, or anything the owner says to keep private. Never research someone's private life (home,
family, finances); only what's public and professional, or what the owner told you.
