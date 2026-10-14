#!/usr/bin/env bash
# init.sh — everything needed to work on bible. Idempotent; exit 0 = ready.
# Nothing to install: Python 3.11+ and Node 18+ stdlib only (package.json declares ES modules and
# wires `node --test`; it has no dependencies). This checks the toolchain and reports the data state.
#   ./init.sh            check python3 and node, report whether data/raw/ and web/data/ exist
set -euo pipefail
cd "$(dirname "$0")"

case "${1:-}" in
    -h|--help) sed -n '2,5p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    '') ;;
    *) echo "Unknown option: $1 (see ./init.sh --help)" >&2; exit 2 ;;
esac

command -v python3 >/dev/null 2>&1 || { echo "python3 (3.11+) is required" >&2; exit 1; }
python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' \
    || { echo "Python 3.11+ required, found $(python3 --version)" >&2; exit 1; }
echo "== python $(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:3])))')"
command -v node >/dev/null 2>&1 || { echo "node (18+) is required" >&2; exit 1; }
node_major="$(node -v | sed 's/^v//; s/\..*//')"
[ "$node_major" -ge 18 ] || { echo "Node 18+ required, found $(node -v)" >&2; exit 1; }
echo "== node $(node -v)"

if [ -d data/raw ] && [ -n "$(ls -A data/raw 2>/dev/null)" ]; then echo "== data/raw/: present"
else echo "== data/raw/: absent — ./run.sh data downloads the sources (~110 MB)"; fi
if [ -d web/data ] && [ -n "$(ls -A web/data 2>/dev/null)" ]; then echo "== web/data/: built"
else echo "== web/data/: not built — ./run.sh data"; fi

echo "ready:"
echo "  ./test.sh         fast suite (offline, ~5s); --all adds contracts, invariants and page smoke"
echo "  ./run.sh data     fetch sources and rebuild web/data/"
echo "  ./run.sh          serve web/ on http://localhost:8000/"
