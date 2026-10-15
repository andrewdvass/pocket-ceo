#!/usr/bin/env bash
# Short reminder on every message so saving to memory never depends on the owner asking.
[ -d "$HOME/Documents/Pocket CEO" ] || exit 0
echo "Pocket CEO: if this message has a receipt photo or PDF, log it with the receipts skill. After answering, save any new fact (names, numbers, dates, decisions, promises, preferences) in full to ~/Documents/Pocket CEO/memory/ per the memory skill, and add it to today's log. Append only; never compress or delete. Fact-check every number, rate, deadline and law against an official source before stating it; if you cannot confirm it, say \"I don't know yet\" and what you need. Never guess."
exit 0
