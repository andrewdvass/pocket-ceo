#!/usr/bin/env bash
# Loads Pocket CEO memory into every new conversation so the owner never has to repeat themselves.
DIR="$HOME/Documents/Pocket CEO"
[ -d "$DIR" ] || { echo "Pocket CEO is not set up yet. If the user asks a business question, run the setup skill first."; exit 0; }
TODAY=$(date +%Y-%m-%d)
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
  AGE=$(( ( $(date +%s) - $(stat -f %m "$LAST" 2>/dev/null || stat -c %Y "$LAST") ) / 86400 ))
  [ "$AGE" -ge 7 ] && echo && echo "Receipts: none logged in $AGE days. Nudge once: ask for photos of any receipts."
fi
N=$(find "$DIR/receipts/inbox" -maxdepth 1 -type f ! -name '.*' 2>/dev/null | wc -l | tr -d ' ')
[ "${N:-0}" -gt 0 ] && echo && echo "Receipts inbox has $N file(s) waiting. File them with the receipts skill."
VAULT="${CLAUDE_PLUGIN_ROOT:-}/skills/receipts/tools/receipt-vault.sh"
if [ -f "$VAULT" ]; then
  echo; echo "Receipt vault tool: $VAULT"
  bash "$VAULT" verify 2>/dev/null | grep -E "MISSING|WARNING|REPAIRED|OK:" | head -5
fi
exit 0
