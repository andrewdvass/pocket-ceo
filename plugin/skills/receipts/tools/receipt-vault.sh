#!/usr/bin/env bash
# Pocket CEO receipt vault: saves every receipt so it can never be lost.
#   save <file> <name>   copy into receipts/<year>/, lock it, fingerprint it, back it up
#   verify               check every saved receipt is still there and unchanged; repair from backup;
#                        also copies the receipt log and summary to the backup
#   find <words>         search the receipt log (vendor, date, amount, category)
#   where                print the folder and backup locations
set -u
HOME_DIR="$HOME/Documents/Pocket CEO"
R="$HOME_DIR/receipts"
SUMS="$R/fingerprints.txt"

backup_dir() {
  for d in "$HOME/Library/Mobile Documents/com~apple~CloudDocs" "$HOME/OneDrive" "$HOME/Dropbox" "$HOME/Google Drive/My Drive"; do
    [ -d "$d" ] && { echo "$d/Pocket CEO Backup/receipts"; return; }
  done
  echo "$HOME/Pocket CEO Backup/receipts"
}
hash() { if command -v shasum >/dev/null; then shasum -a 256 "$1" | cut -d' ' -f1; else sha256sum "$1" | cut -d' ' -f1; fi; }

case "${1:-}" in
  save)
    src="$2"; name="$3"; [ -f "$src" ] || { echo "ERROR: file not found: $src"; exit 1; }
    year="${name:0:4}"; mkdir -p "$R/$year"
    dest="$R/$year/$name"
    if [ -e "$dest" ]; then
      [ "$(hash "$src")" = "$(hash "$dest")" ] && { echo "ALREADY SAVED: $dest"; exit 0; }
      n=2; while [ -e "${dest%.*}_$n.${dest##*.}" ]; do n=$((n+1)); done; dest="${dest%.*}_$n.${dest##*.}"
    fi
    cp -p "$src" "$dest" && chmod 444 "$dest"
    h=$(hash "$dest"); rel="${dest#$R/}"
    echo "$h  $rel" >> "$SUMS"
    B=$(backup_dir); mkdir -p "$B/$year"; cp -p "$dest" "$B/$rel"; cp "$SUMS" "$B/fingerprints.txt"
    [ "$(hash "$B/$rel")" = "$h" ] || { echo "ERROR: backup copy failed for $rel"; exit 1; }
    if [ -d "$HOME_DIR/.git" ]; then (cd "$HOME_DIR" && git add -A receipts >/dev/null 2>&1 && git commit -qm "receipt $rel" >/dev/null 2>&1 && git push -q >/dev/null 2>&1) || echo "NOTE: online backup push failed; local copies are safe"; fi
    echo "SAVED: $rel"; echo "BACKUP: $B/$rel"; echo "FINGERPRINT: ${h:0:12}"
    ;;
  verify)
    [ -f "$SUMS" ] || { echo "OK: no receipts saved yet"; exit 0; }
    B=$(backup_dir); bad=0; n=0
    while read -r h rel; do
      n=$((n+1)); f="$R/$rel"
      if [ ! -f "$f" ] || [ "$(hash "$f")" != "$h" ]; then
        if [ -f "$B/$rel" ] && [ "$(hash "$B/$rel")" = "$h" ]; then
          mkdir -p "$(dirname "$f")"; chmod 644 "$f" 2>/dev/null; cp -p "$B/$rel" "$f" && chmod 444 "$f"; echo "REPAIRED from backup: $rel"
        else echo "MISSING: $rel (not in backup either)"; bad=$((bad+1)); fi
      elif [ ! -f "$B/$rel" ]; then mkdir -p "$(dirname "$B/$rel")"; cp -p "$f" "$B/$rel"; echo "BACKED UP: $rel"; fi
    done < "$SUMS"
    for lf in "$R"/*/receipts-*.md "$R"/*/receipts-*.csv "$R"/*/summary-*.md; do
      [ -f "$lf" ] && { rel="${lf#$R/}"; mkdir -p "$(dirname "$B/$rel")"; cp -p "$lf" "$B/$rel"; }
    done
    [ $bad -eq 0 ] && echo "OK: all $n receipts safe (2 copies each)" || echo "WARNING: $bad of $n receipts missing"
    ;;
  find)
    shift; q="$*"; grep -i -h -- "$q" "$R"/*/receipts-*.md 2>/dev/null || echo "No receipts match: $q"
    ;;
  where)
    echo "Receipts: $R"; echo "Backup:   $(backup_dir)"
    ;;
  *) sed -n 2,7p "$0" ;;
esac
