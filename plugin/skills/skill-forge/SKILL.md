---
name: skill-forge
description: >
  Builds new Pocket CEO skills for the owner's recurring needs. Use when the session hook or the
  calculator says "SUGGEST SKILL", when the owner keeps asking about the same kind of thing (pricing,
  Google Ads, hiring, a specific software, real estate, a sport they coach), when they say "can you
  get better at…", "make yourself an expert in…", "build me a skill for…", or "what else could you do
  for me". Researches the topic properly (the best books, experts and official sources), writes a skill
  and its knowledge files into their own skills folder, and suggests apps worth connecting.
---

# Skill forge

People keep asking AI the same kinds of questions without ever teaching it. Pocket CEO notices, and
offers to become an expert in exactly what this owner needs. Follow `../../shared/rules.md`.

## Noticing
- Every conversation's daily-log section ends with `Topics: ...` (the `memory` skill writes it).
- At the start of a conversation, and weekly in the Monday brief, run `skills patterns`
  (`../../shared/tools.md`). It lists topics raised 3+ times on 3+ different days in the last 45 days
  that have no skill yet and weren't declined.
- Also notice it yourself: the same chore in three debriefs, the same type of question three times.

## Offering (one short message, never pushy)
> I've noticed Google Ads has come up 4 times this month. Want me to build you a Google Ads expert
> that knows your business, your budget and what you've already tried? It takes me a few minutes.
Yes → build it. No → `skills decline "<topic>"` so you never ask again.

## Building it
1. **Interview, briefly** (2 or 3 questions): what they're trying to achieve, what they've tried, what
   they'd want it to do for them (answer questions, write things, check things, track numbers).
2. **Research properly** (web search, cite everything):
   - The 3 to 6 most respected books on the topic, and the core frameworks from each, summarized in
     your own words with the book and author named. Short quotes (a sentence) only when you've
     confirmed the exact wording from a reliable source, with the book named; never long passages.
   - The leading practitioners and what they teach (summarized, attributed; the skill is "built on the
     ideas of", never pretending to be that person).
   - Official or primary sources for any rules, rates or laws involved.
   - What's specific to Canada and to their province, if anything.
3. **Write the skill** with the calculator: put the body in a temp file and run
   `skills new "<topic>" --description "<when to use it, with trigger phrases>" --body <body.md>
   --knowledge <frameworks.md> <checklist.md> ...`
   It creates `~/.claude/skills/pceo-<topic>/` (their personal skills folder; Claude loads it in every
   new conversation). The body must include: who it serves (this owner, their business, their numbers
   from memory), how to answer (lead with the answer, their numbers, straight talk), when to use the
   calculator, the house-rules pointer (`Follow the Pocket CEO house rules in the plugin's shared/rules.md`),
   and what it must never do. Knowledge files hold the frameworks, checklists and source list, each
   dated.
4. **Tell them** in two lines what it knows and one example question to try. Log it in `decisions.md`.

## Connecting things (the other half of getting ahead)
When a pattern points at an app, suggest connecting it, one at a time, with the payoff in a sentence:
Google Calendar (meeting prep and drive logs), Google Drive (contracts and reports), Stripe or Square
(sales without bank files), QuickBooks or Wave (books), their CRM (GoHighLevel, HubSpot), Slack.
Point them to the Claude app: Settings → Connectors, and say what you'll do once it's on.

## Never
Never build a skill they didn't say yes to. Never impersonate a real person or present summaries as an
author's own words. Never copy long passages from books, courses or videos.
