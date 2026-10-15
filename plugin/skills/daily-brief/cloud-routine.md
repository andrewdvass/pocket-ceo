# Daily brief as a cloud routine

A cloud routine runs on Anthropic's servers, so the brief arrives even when the owner's computer is
off or asleep. Source: Claude Code docs, "Automate work with routines" (code.claude.com/docs/en/routines),
checked 2026-10-15. Routines are a research preview, so re-check these facts if anything fails.

## What it needs (check all four before offering it)
1. **A paid Claude plan** (Pro, Max, Team or Enterprise) and a claude.ai login. Routines aren't on the
   free plan. Team/Enterprise owners can turn routines off for their organization.
2. **The private online backup** from setup Step 3 (`pocket-ceo-<firstname>` on GitHub). A routine
   can't see files on the computer; it reads a fresh copy of that repository each morning. No backup,
   no cloud brief: offer the backup first, or fall back to the on-this-computer brief.
3. **GitHub connected to Claude** so the routine can read the repository. If `/schedule` reports that
   GitHub access is missing, have them open claude.ai/code and connect GitHub when it asks.
4. **Gmail (and Google Calendar, if they use it) connected at claude.ai/customize/connectors.** Cloud
   routines use claude.ai connectors, not connectors set up only on this computer.

## Before creating it: put the brief inside their repository
Routines run the skills committed to the cloned repository, not installed plugins. So:
1. Copy this skill's `SKILL.md` to `~/Documents/Pocket CEO/.claude/skills/daily-brief/SKILL.md`.
2. Make sure `profile.md` (with the **Personal** section) is in the folder.
3. Commit and push the folder to their private repository. Confirm the push worked.
Re-copy and push the skill whenever Pocket CEO is updated.

## Create the routine
Use the `schedule` skill (or tell them to type `/schedule`), with these settings:
- **Name:** Pocket CEO morning brief
- **Repository:** their private `pocket-ceo-<firstname>` repository only
- **Schedule:** daily at their chosen time, **7 minutes past** (e.g. 7:07 am, not 7:00, so it isn't
  delayed by the on-the-hour rush). Times are in their local zone.
- **Connectors:** keep only Gmail and Google Calendar. Remove every other connector.
- **Prompt:** paste the prompt below, filling in their email address.

If creating it from inside the chat doesn't work, walk them through claude.ai/code/routines →
**New routine** → **Cloud** with the same settings.

Then click **Run now** once (or ask the schedule skill to run it) and confirm with the owner that the
brief arrived. Don't say "it's set up" until they've seen one arrive.

## The routine prompt (paste as is, filling in the email)
```
You are Pocket CEO, writing the owner's morning brief. This is a scheduled run; nobody is watching,
so finish the whole job without asking questions.

1. Read profile.md in this repository (the Personal section has their city, time zone, teams,
   hobbies and spots). Read decisions.md for deadlines. Follow .claude/skills/daily-brief/SKILL.md
   for what to gather and the format.
2. Fact-check everything with web search: weather, game times, snow reports, tax deadlines.
   Never guess. If you can't confirm something, leave it out or write "couldn't confirm".
3. Use Gmail to count urgent emails from the last 24 hours, and Google Calendar (if connected) for
   today's events. Read only; never reply to, label, delete or archive anything.
4. Deliver it: send ONE email to OWNER_EMAIL from their own Gmail, with the brief as the body and the
   subject line from the skill. Send it to OWNER_EMAIL only, never to anyone else. If Gmail can't
   send, create it as a Gmail draft addressed to OWNER_EMAIL instead.
5. Do not change any files in this repository and do not push anything.
```

## Telling the owner
"Your brief now runs in the cloud, so it comes every morning at 7:07 even if your computer is off.
It reads your private backup each morning, so when you change your teams or hobbies with me, I'll
update the backup and tomorrow's brief picks it up. It uses a little of your Claude plan each day."

## If it stops arriving
- They can ask "why didn't my brief come this morning?" and you check it with the schedule skill
  (`/schedule why did my morning brief do nothing`).
- A green run status only means the session ran, not that the email went out: read the run.
- If GitHub is disconnected, the routine skips runs for up to 72 hours, then turns itself off.
  Reconnect GitHub and turn it back on at claude.ai/code/routines.
- If it hits their plan's usage limit, that morning's brief is skipped.
