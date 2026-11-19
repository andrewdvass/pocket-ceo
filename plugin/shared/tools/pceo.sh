#!/usr/bin/env bash
# Runs the Pocket CEO money tools with a real Python 3, without triggering installer pop-ups.
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
find_py() {
  if [ "$(uname)" = "Darwin" ] && ! xcode-select -p >/dev/null 2>&1 && [ ! -x /opt/homebrew/bin/python3 ] && [ ! -x /usr/local/bin/python3 ]; then
    return 1  # /usr/bin/python3 on a Mac without developer tools is a stub that opens an installer
  fi
  for p in python3 python py /opt/homebrew/bin/python3 /usr/local/bin/python3; do
    command -v "$p" >/dev/null 2>&1 || continue
    v=$("$p" -c 'import sys; print(sys.version_info[0])' 2>/dev/null)
    [ "$v" = "3" ] && { echo "$p"; return 0; }
  done
  return 1
}
PY=$(find_py) || {
  echo "NEEDS PYTHON: Pocket CEO's calculator needs Python 3."
  echo "Mac: run 'xcode-select --install' and tell the owner to click Install in the pop-up (about 5 minutes)."
  echo "Windows: run 'winget install -e --id Python.Python.3.12', then start a new chat."
  exit 3
}
exec "$PY" "$DIR/pceo.py" "$@"
