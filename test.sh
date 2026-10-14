#!/usr/bin/env bash
# test.sh — every check in one place. Exit 0 = all green = safe to push. `./run.sh test` runs this.
#   ./test.sh            fast suite: units, properties, pipeline, JS (make test, offline, ~5s), plus
#                        shell syntax, no tracked .env, and `make check` when data/raw/ is present
#   ./test.sh --all      also `make test-all`: contract tests over real output, invariants, page smoke
#                        (needs a build: ./run.sh data)
set -euo pipefail
cd "$(dirname "$0")"

ALL=0
for arg in "$@"; do
    case "$arg" in
        --all) ALL=1 ;;
        -h|--help) sed -n '2,6p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
        *) echo "Unknown option: $arg (see ./test.sh --help)" >&2; exit 2 ;;
    esac
done

echo "== toolchain"
python3 -c 'import sys; assert sys.version_info >= (3, 11), sys.version; print("   python", sys.version.split()[0])'
echo "   node $(node -v)"
echo "== secrets: no tracked env files"
tracked="$(git ls-files | grep -E '(^|/)\.env(\..+)?$' | grep -vE '\.env\.(example|template)$' || true)"
[ -z "$tracked" ] || { echo "env files must never be tracked:"; echo "$tracked"; exit 1; }
echo "== shell: bash -n, /bin/bash -n, shellcheck"
for f in ./*.sh; do bash -n "$f"; /bin/bash -n "$f"; done
if command -v shellcheck >/dev/null 2>&1; then shellcheck -S warning ./*.sh
else echo "   shellcheck not installed — syntax-checked only (brew install shellcheck)"; fi
echo "== compile"
python3 -m compileall -q scripts tests
echo "== unit: make test (units, properties, pipeline, node --test)"
make test
if [ -d data/raw ] && [ -n "$(ls -A data/raw 2>/dev/null)" ]; then
    echo "== check: make check (curated-data validators against data/raw/)"
    make check
else
    echo "== check: skipped (data/raw/ absent — ./run.sh data)"
fi
if [ "$ALL" -eq 1 ]; then
    [ -d web/data ] && [ -n "$(ls -A web/data 2>/dev/null)" ] || { echo "web/data/ is not built: ./run.sh data first" >&2; exit 1; }
    echo "== all: make test-all (contracts, invariants, smoke)"
    make test-all
else
    echo "== all: skipped (pass --all; needs web/data/ from ./run.sh data)"
fi
echo "== all green"
