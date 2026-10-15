---
name: memory
description: >
  Pocket CEO's long-term memory. Use at the start of every conversation to load what you know about the
  owner, and after every meaningful exchange to save what you learned, without being asked. Also use
  when they say "remember this", "don't forget", "what do you know about…", "what did we decide about…",
  "who is…", or "what did I promise…". Keeps everything as plain Markdown files in their Pocket CEO
  folder, written in full, never compressed, so nothing is ever lost.
---

# Memory

Owners get busy and forget to tell you things twice. That's the point of you. **You remember for them.**
Your chat history gets cut and summarized; these files don't. If it isn't in a file, assume you'll
forget it.

## The memory folder (never change this layout)
```
~/Documents/Pocket CEO/memory/
  index.md          <- read FIRST every conversation: what's in each file + the 10 most important facts
  people.md         <- every person: name, who they are, how you know them, last contact, details
  customers.md      <- clients and leads: what they bought, what they want, problems, history
  money.md          <- prices, rates, recurring bills, income, debts, money decisions
  goals.md          <- goals, deadlines, plans, what they're working on this month
  promises.md       <- follow-ups: things THEY promised others and things others promised THEM
  preferences.md    <- how they like things done, what to never do, their tone, their routines
  log/
    2026-10-13.md   <- one file per day: everything that happened in today's conversations, in full
```
Create any missing file from `templates/` in this skill folder. The profile, voice, decisions and
receipts files stay where they are; memory is everything else.

## Start of every conversation
1. Read `memory/index.md`, then `promises.md` and `goals.md`.
2. Read today's and yesterday's `log/` files if they exist.
3. Read any other memory file the question touches (a person's name -> `people.md`).
4. If something is overdue in `promises.md`, mention it in one line at the end of your first answer.
Never make the owner repeat something that's already in memory.

## Saving (do this yourself, every time; don't wait to be asked)
Save after any message that contains a fact worth keeping: a name, a number, a date, a decision, a
promise, a preference, a problem, a plan, a feeling about a person or a deal.

**The rules that make memory reliable:**
1. **Never compress.** Write the full detail: names, numbers, dates, exact wording of promises and
   prices. "Talked to Sarah about the lease" is useless. "Sarah Chen (landlord, 403-555-0100) offered
   to renew the studio lease at $2,150/mo for 3 years, wants an answer by Nov 1; Andrew wants 2 years"
   is memory.
2. **Never delete or rewrite old entries.** Append. If something changed, add a new dated line:
   `2026-10-20: UPDATE: lease signed at $2,100/mo for 2 years (replaces the Oct 13 offer).`
3. **Never summarize a file to make it shorter.** Files are allowed to get long. When a file passes
   about 1,500 lines, start `people-2.md` (etc.) and list both in `index.md`. Don't shrink the old one.
4. **Date every entry** (YYYY-MM-DD) and say where it came from: chat, email, receipt, contract.
5. **Write to the daily log too**: every conversation gets a section in `log/<today>.md` with what
   they asked, what you answered (the key numbers and verdicts, not a one-liner), and anything saved.
6. **Update `index.md`** when you add a new file, a new important person, or a fact that should be in
   the top 10.
7. If they say "forget that" or "delete that", remove only that entry and add a dated line saying it
   was removed at their request (without repeating the content).

## Recall
When they ask "what do you know about X" or "what did we decide", search all memory files and the
logs (grep the folder), then answer with the dates: "On Oct 13 you decided… On Oct 20 that changed to…".
If memory has nothing, say so plainly. Never guess and present it as memory.

## Never save
Passwords, full card or bank numbers, SIN, CRA logins, health details about other people. If they
share one, don't write it down and tell them not to share it.

## Backup
If they set up the online backup in setup, commit and push the folder after saving
(`git add -A && git commit -m "memory <date>" && git push`), quietly. If it fails, keep going and
mention it once.
