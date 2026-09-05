#!/usr/bin/env python3
"""Pre-compress every generated JSON file next to itself as <name>.json.gz.

JSON of this shape compresses to roughly a fifth of its size, and the browser
decompresses it for free. Real static hosts do this on the fly; scripts/serve.py
does it here by serving the .gz when one exists and is newer than its source.

Idempotent: files whose .gz is already current are skipped.
"""
import gzip, pathlib, sys

ROOT = pathlib.Path("web/data")


def main():
    if not ROOT.is_dir():
        print("!! web/data missing; run `make data` first", file=sys.stderr)
        return 1
    raw = comp = made = skipped = 0
    for src in sorted(ROOT.rglob("*.json")):
        dst = src.with_suffix(".json.gz")
        if dst.exists() and dst.stat().st_mtime >= src.stat().st_mtime:
            raw += src.stat().st_size
            comp += dst.stat().st_size
            skipped += 1
            continue
        data = src.read_bytes()
        # mtime=0 keeps the output byte-identical between runs.
        dst.write_bytes(gzip.compress(data, compresslevel=9, mtime=0))
        raw += len(data)
        comp += dst.stat().st_size
        made += 1
    print(f"gzip: {made} written, {skipped} already current  "
          f"{raw / 1e6:.1f} MB -> {comp / 1e6:.1f} MB ({comp / max(raw, 1):.0%})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
