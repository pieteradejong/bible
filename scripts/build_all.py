#!/usr/bin/env python3
"""Fetch sources if needed, then run every builder in dependency order."""
import subprocess, sys

STEPS = [
    ("fetch sources", "scripts/fetch_sources.py"),
    ("canon table", "scripts/gen_books.py"),
    ("KJV text", "scripts/build_text.py"),
    ("cross-references", "scripts/build_crossrefs.py"),
    ("places", "scripts/build_places.py"),
    ("region and river geometry", "scripts/build_geometry.py"),
    ("comparison translations", "scripts/build_translations.py"),
    ("quotation analysis", "scripts/build_quotations.py"),
    ("genealogy", "scripts/gen_genealogy.py"),
    ("timeline", "scripts/build_timeline.py"),   # validates against text + places
]


def main():
    for label, script in STEPS:
        print(f"\n== {label}")
        rc = subprocess.call([sys.executable, script, *sys.argv[1:]])
        if rc:
            print(f"\n!! {label} failed (exit {rc})", file=sys.stderr)
            return rc
    print("\nBuild complete. Serve with: make serve")
    return 0


if __name__ == "__main__":
    sys.exit(main())
