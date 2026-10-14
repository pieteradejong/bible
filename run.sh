#!/usr/bin/env bash
# run.sh — the project's entry points; every command wraps a Makefile target.
#   ./run.sh                 same as `serve`
#   ./run.sh serve           static server for web/ on http://localhost:${PORT:-8000}/
#   ./run.sh data            fetch third-party sources (~110 MB, cached) and rebuild web/data/
#   ./run.sh refresh         re-download the sources even if cached, then rebuild
#   ./run.sh check           re-run the curated-data validators (no network)
#   ./run.sh invariants      assert the headline figures the README quotes
#   ./run.sh gzip            pre-compress web/data so serve can send it compressed
#   ./run.sh test [--all]    every check (./test.sh)
#   ./run.sh clean           remove generated files (keeps data/raw/)
set -euo pipefail
cd "$(dirname "$0")"

cmd="${1:-serve}"
[ $# -gt 0 ] && shift
case "$cmd" in
    -h|--help|help) sed -n '2,11p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    test) exec ./test.sh "$@" ;;
    serve|data|refresh|check|invariants|gzip|clean) exec make "$cmd" ;;
    *) echo "Unknown command: $cmd" >&2; echo >&2; sed -n '2,11p' "$0" | sed 's/^# \{0,1\}//' >&2; exit 2 ;;
esac
