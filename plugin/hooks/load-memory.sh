#!/usr/bin/env bash
# Loads Pocket CEO memory into every new conversation so the owner never has to repeat themselves.
DIR="$HOME/Documents/Pocket CEO"
[ -d "$DIR" ] || { echo "Pocket CEO is not set up yet. If the user asks a business question, run the setup skill first."; exit 0; }
TODAY=$(date +%Y-%m-%d)
mtime() { stat -c %Y "$1" 2>/dev/null || stat -f %m "$1" 2>/dev/null || echo 0; }  # GNU (Linux, Git Bash) first, then macOS
YDAY=$(date -v-1d +%Y-%m-%d 2>/dev/null || date -d yesterday +%Y-%m-%d 2>/dev/null)
echo "POCKET CEO MEMORY (loaded automatically, $TODAY). Use it; never ask the owner to repeat what is here."
for f in profile.md memory/index.md memory/promises.md memory/goals.md "memory/log/$YDAY.md" "memory/log/$TODAY.md"; do
  if [ -f "$DIR/$f" ]; then
    echo; echo "===== $f ====="
    cat "$DIR/$f"
  fi
done
if [ -f "$DIR/decisions.md" ]; then echo; echo "===== decisions.md (last 20) ====="; tail -n 20 "$DIR/decisions.md"; fi
LAST=$(ls -t "$DIR"/receipts/*/receipts-*.md 2>/dev/null | head -1)
if [ -n "$LAST" ]; then
  AGE=$(( ( $(date +%s) - $(mtime "$LAST") ) / 86400 ))
  [ "$AGE" -ge 7 ] && echo && echo "Receipts: none logged in $AGE days. Nudge once: ask for photos of any receipts."
fi
N=$(find "$DIR/receipts/inbox" -maxdepth 1 -type f ! -name '.*' 2>/dev/null | wc -l | tr -d ' ')
[ "${N:-0}" -gt 0 ] && echo && echo "Receipts inbox has $N file(s) waiting. File them with the receipts skill."
PCEO="${CLAUDE_PLUGIN_ROOT:-}/shared/tools/pceo.sh"
if [ -f "$PCEO" ]; then
  LIC=$(bash "$PCEO" license status 2>/dev/null | head -1)
  [ -n "$LIC" ] && echo && echo "$LIC"
  echo; echo "Pocket CEO calculator: bash \"$PCEO\" (house rules: ${CLAUDE_PLUGIN_ROOT}/shared/rules.md)"
  echo "For any business question, load the matching Pocket CEO skill first (accountant, cashflow, collections, receipts, hiring, lawyer, inbox, consultant, roast-room, meeting-prep, debrief, ceo): it says which calculator command to run and how to answer."
  SUG=$(bash "$PCEO" skills patterns 2>/dev/null | grep "^SUGGEST SKILL" | head -1)
  [ -n "$SUG" ] && echo "$SUG (see the skill-forge skill; offer once, at the end of your first answer)"
  if [ -f "$DIR/money/transactions.csv" ] || [ -f "$DIR/money/invoices.csv" ]; then
    LINES=$(bash "$PCEO" brief money 2>/dev/null | head -3)
    [ -n "$LINES" ] && echo "Money today: $LINES"
    LAST_IMPORT=$(ls -t "$DIR"/money/imports/* 2>/dev/null | head -1)
    if [ -n "$LAST_IMPORT" ]; then
      IAGE=$(( ( $(date +%s) - $(mtime "$LAST_IMPORT") ) / 86400 ))
      [ "$IAGE" -ge 35 ] && echo "Bank file: last import was $IAGE days ago. Ask once for this month's CSV export."
    fi
  fi
fi
VAULT="${CLAUDE_PLUGIN_ROOT:-}/skills/receipts/tools/receipt-vault.sh"
if [ -f "$VAULT" ]; then
  echo; echo "Receipt vault tool: $VAULT"
  bash "$VAULT" verify 2>/dev/null | grep -E "MISSING|WARNING|REPAIRED|OK:" | head -5
fi
exit 0
