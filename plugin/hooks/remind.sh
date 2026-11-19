#!/usr/bin/env bash
# Short reminder on every message so saving to memory never depends on the owner asking.
[ -d "$HOME/Documents/Pocket CEO" ] || exit 0
echo "Pocket CEO: if this message has a receipt photo or PDF, log it with the receipts skill. After answering, save any new fact (names, numbers, dates, decisions, promises, preferences) in full to ~/Documents/Pocket CEO/memory/ per the memory skill, and add it to today's log. Append only; never compress or delete. Numbers come from the Pocket CEO calculator and its sourced rates file, not memory; check anything else against an official source; if you cannot confirm it, say \"I don't know yet\" and what you need. Never guess."
exit 0
