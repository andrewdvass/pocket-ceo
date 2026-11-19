---
name: daily-brief
description: >
  The owner's morning brief: one short email (or in-app note) that simplifies their day. Today's
  weather where they are, games on today for the teams they follow (local start time and where to
  watch), conditions for their hobbies (overnight and tomorrow snowfall at their ski resort, golf or
  fishing weather, etc.), plus their business day: urgent emails, today's meetings, and upcoming tax or
  contract deadlines. Use when the scheduled morning run fires, or when they ask "what's my day look
  like", "morning brief", "is there a game tonight", "how much snow is coming", "what's the weather".
---

# Daily brief

Goal: one glance at their phone over coffee and they know their day. Short, friendly, useful.

## Inputs
**In a cloud routine run** (no `~/Documents` folder, you're in a cloned repository): read `profile.md`
and `decisions.md` from the repository root instead, and follow the routine's prompt for delivery.
Read `~/Documents/Pocket CEO/profile.md`, section **Personal** (city, time zone, teams, hobbies and
their spots, brief time, delivery). If the Personal section is empty, ask the setup questions in
`setup` Step 6b and save them.

## Gather (use web search for anything live; never guess)
1. **Weather today** for their city: high/low, conditions, precipitation chance, wind, and anything
   unusual (extreme cold warning, snowfall warning, wildfire smoke). Prefer Environment Canada
   (weather.gc.ca) or another reliable forecast. One line, plus a one-line heads-up only if it matters
   ("Snow starts around 4 pm, leave early for your 5:30").
2. **Games today** for each followed team: opponent, **start time in the owner's time zone**, and
   where to watch (TV channel or streaming service) if easy to confirm. If no game today, say when the
   next one is in a few words. Add last night's result in one line if they played.
3. **Hobbies** (only the ones in their profile), for example:
   - Snowboarding/skiing: overnight and next-24h snowfall at their resort(s), current base, and whether
     lifts/terrain are open (resort snow report or a snow forecast site). Flag a powder day.
   - Golf, cycling, running: the best window today (dry, low wind).
   - Fishing, boating, hunting: wind, conditions, and any season dates coming up.
   - Anything else they named: the one number they'd care about.
4. **Business day:**
   - Urgent emails: count and one line each (from the `inbox` skill's Urgent label).
   - Today's calendar events, if a calendar connector is available.
   - **Money:** run `brief money` with the calculator (`../../shared/tools.md`; pass `--floor` with
     their cash cushion from `memory/preferences.md` and `--instalment` if they pay instalments). It
     prints up to three lines (cash, money owed to them, tax deadlines in the next 14 days) and prints
     nothing when there's nothing to say. Use its lines as they are; don't add money lines of your own.
   - Other deadlines in the next 14 days: contract renewals, notice dates and promises from
     `memory/promises.md` and `decisions.md`.
5. **Mondays only:** the 90-day plan scorecard from `memory/goals.md` (one line: last week vs target),
   and one AI tip from the `ai-coach` skill (one line).

## Format (keep it under ~150 words)
```
Subject: ☀️ Your day: -4°C, Flames 7pm, 12 cm at Sunshine

Good morning <name>!

Weather: -4°C, sunny, high of 2. Snow tonight after 9 pm.
Games: Flames vs Oilers, 7:00 pm on Sportsnet. Last night: Jays won 5-3.
Sunshine Village: 12 cm overnight, 18 cm more by tomorrow morning. Powder day! 🏂

Your day:
- 2 urgent emails (Sarah re: invoice, landlord re: lease renewal)
- 10:00 call with Dr. Lee
- Cash: rent $1,450 on Dec 1; GST/HST $2,310 due Jan 31.
- Owed to you: $1,200 overdue (Sarah 49 days). Reminder drafted.

Have a great one!
```
Lead with whatever is most exciting or most important today. Skip any section with nothing in it.

## Where it runs
- **Cloud (recommended):** a daily cloud routine, so it arrives even when their computer is off.
  Setup and requirements are in `cloud-routine.md` in this skill folder. Use it whenever they have a
  paid plan and the private online backup.
- **On this computer:** a Desktop scheduled task. Simpler, but it only runs if their computer is on
  and awake at brief time. Tell them that plainly.

## Delivery
- **Email to themselves** (only if they said yes during setup): send one email from their own Gmail to
  their own address. This is the only email Pocket CEO ever sends, and only to the owner. Never send
  the brief, or anything else, to anyone else.
- Otherwise, or if email delivery fails, show it in the app as the morning message.

## House rules
Follow `../../shared/rules.md` (fact-checking, the rates file, using the calculator, serious
situations, logging). Read it once per conversation if you haven't.

## Never
Never include passwords, account numbers or private client details in the subject line. Never invent a
game time, score or snowfall number: if a source can't be confirmed, leave that line out.
