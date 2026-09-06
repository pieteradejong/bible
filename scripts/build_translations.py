#!/usr/bin/env python3
"""Split each comparison translation into per-book files keyed by OSIS.

Six centuries of English rendering sit alongside the KJV in the reader:
Wycliffe (c.1395), Tyndale (1525/30), the KJV itself (1611), Young's Literal
(1898), Darby (1890) and the ASV (1901). All are public domain.

Coverage is uneven on purpose. Tyndale never finished the Old Testament and
Wycliffe's canon includes books this project does not; both are reported rather
than padded, and the reader shows a gap where a translation has no verse.

Output: web/data/tr/<CODE>/<OSIS>.json   {"chapters": [[verse, ...], ...]}
        web/data/translations.json        the manifest the reader reads
"""
import json, pathlib, re, sys

BOOKS = json.loads(pathlib.Path("data/curated/books.json").read_text())
BY_NAME = {b["name"]: b for b in BOOKS}
RAW = pathlib.Path("data/raw")
OUT = pathlib.Path("web/data/tr")

# Ordered oldest first: the point of the feature is watching the language move.
EDITIONS = [
    ("Wycliffe", "Wycliffe", "c. 1395", "Middle English, translated from the Latin Vulgate."),
    ("Tyndale", "Tyndale", "1525-1530", "The first printed English translation from Greek and Hebrew. Only the New Testament and the Pentateuch were finished before his execution."),
    ("KJV", None, "1611", "The King James Version, this project's base text."),
    ("Darby", "Darby", "1890", "John Nelson Darby's close, technical rendering."),
    ("YLT", "YLT", "1898", "Young's Literal Translation, which preserves Hebrew and Greek tense at the cost of English idiom."),
    ("ASV", "ASV", "1901", "The American Standard Version, ancestor of most twentieth-century revisions."),
]

ROMAN = re.compile(r"^(III|II|I) ")

# Names the source spells differently from the canon table.
ALIASES = {
    "Revelation of John": "Revelation",
    "Song of Songs": "Song of Solomon",
    "Canticles": "Song of Solomon",
    "Psalm": "Psalms",
    "Acts of the Apostles": "Acts",
}


def canonical(name):
    """'II Kings' -> '2 Kings'. Roman numerals and a few aliases differ."""
    name = ROMAN.sub(lambda m: f"{len(m.group(1))} ", name.strip())
    return BY_NAME.get(ALIASES.get(name, name))


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = []

    for code, source, year, note in EDITIONS:
        if source is None:                      # the KJV is already built
            manifest.append({"code": code, "year": year, "note": note,
                             "path": "text", "books": len(BOOKS), "verses": 31102})
            print(f"  {code:9s} {year:10s} {len(BOOKS):2d} books,  31,102 verses")
            continue
        src = RAW / f"tr_{source}.json"
        if not src.exists():
            print(f"  !! {code}: {src} missing, skipping", file=sys.stderr)
            continue
        doc = json.loads(src.read_text(encoding="utf-8-sig"))
        dest = OUT / code
        dest.mkdir(parents=True, exist_ok=True)

        books = verses = 0
        for book in doc.get("books", []):
            meta = canonical(book.get("name", ""))
            if meta is None:                    # deuterocanon and the like
                continue
            chapters = []
            for ch in book.get("chapters", []):
                chapters.append([v.get("text", "").strip()
                                 for v in ch.get("verses", [])])
            # Unfinished books are shipped padded with empty strings rather than
            # omitted -- Tyndale's Old Testament beyond the Pentateuch is all
            # blanks. Count real text, not slots, and skip a book with none.
            filled = sum(1 for c in chapters for v in c if v)
            if not filled:
                continue
            books += 1
            verses += filled
            (dest / f"{meta['osis']}.json").write_text(
                json.dumps({"chapters": chapters}, separators=(",", ":")) + "\n")

        manifest.append({"code": code, "year": year, "note": note,
                         "path": f"tr/{code}", "books": books, "verses": verses})
        print(f"  {code:9s} {year:10s} {books:2d} books, {verses:6,d} verses")

    (pathlib.Path("web/data") / "translations.json").write_text(
        json.dumps(manifest, indent=1) + "\n")
    print(f"translations: {len(manifest)} editions")


if __name__ == "__main__":
    sys.exit(main())
