#!/usr/bin/env python3
"""Assert the headline figures the README quotes.

A source that changes shape upstream -- truncated, reversified, reordered --
would otherwise ship a quietly thinner site. This turns that into a build
failure. If a figure legitimately changes, verify the source first, then update
it here and in the README together.
"""
import json, pathlib, sys

DATA = pathlib.Path("web/data")

EXPECTED = {
    "books": 66,
    "chapters": 1189,
    "verses": 31100,
    "cross-references": 344799,
    "mapped places": 1278,
    "genealogy people": 133,
}


def main():
    if not (DATA / "timeline.json").exists():
        print("!! web/data is empty; run scripts/build_all.py first", file=sys.stderr)
        return 1

    books = json.loads((DATA / "timeline.json").read_text())["books"]
    chapters = verses = 0
    for b in books:
        text = json.loads((DATA / "text" / f"{b['osis']}.json").read_text())["chapters"]
        chapters += len(text)
        verses += sum(len(c) for c in text)

    actual = {
        "books": len(books),
        "chapters": chapters,
        "verses": verses,
        "cross-references": json.loads((DATA / "xref_books.json").read_text())["total"],
        "mapped places": len(json.loads((DATA / "places.json").read_text())),
        "genealogy people": len(json.loads((DATA / "genealogy.json").read_text())["people"]),
    }

    failed = False
    for name, want in EXPECTED.items():
        got = actual[name]
        ok = got == want
        failed |= not ok
        print(f"  {'ok  ' if ok else 'FAIL'} {name}: {got:,}"
              + ("" if ok else f" (expected {want:,})"))

    if failed:
        print("\nUpstream data has changed shape. Verify the source, then update "
              "these figures here and in the README together.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
