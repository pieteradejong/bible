#!/usr/bin/env python3
"""Split the public-domain KJV into one JSON file per book, keyed by OSIS.

The KJV is read from the same source as the comparison translations, so all six
editions come from one place and share one parser.

clean() survives from an earlier source that marked translator-supplied words
and marginal notes with braces ("darkness {was} upon", "{in: or, upon}"). The
current source carries no such markup, but the function is kept and tested: it
is the guard that stops apparatus reaching the reader if a source ever
reintroduces it. Supplied words become <i>; anything with a colon is apparatus
and is dropped.

Output: web/data/text/<OSIS>.json  {"osis": "Gen", "chapters": [[verse, ...]]}
"""
import json, pathlib, re, sys

BOOKS = json.loads(pathlib.Path("data/curated/books.json").read_text())
BY_NAME = {b["name"]: b for b in BOOKS}
SRC = pathlib.Path("data/raw/en_kjv.json")
OUT = pathlib.Path("web/data/text")

ROMAN = re.compile(r"^(III|II|I) ")
ALIASES = {
    "Revelation of John": "Revelation",
    "Song of Songs": "Song of Solomon",
    "Acts of the Apostles": "Acts",
}


def canonical(name):
    """'II Kings' -> the canon row for 2 Kings; None for anything outside it."""
    name = ROMAN.sub(lambda m: f"{len(m.group(1))} ", name.strip())
    return BY_NAME.get(ALIASES.get(name, name))

BRACE = re.compile(r"\{([^{}]*)\}")


def clean(verse):
    def sub(m):
        body = m.group(1)
        # A marginal note always carries a colon; a supplied word never does.
        return "" if ":" in body else f"<i>{body}</i>"
    return re.sub(r"\s{2,}", " ", BRACE.sub(sub, verse)).strip()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    doc = json.loads(SRC.read_text(encoding="utf-8-sig"))
    verses = seen = 0
    for book in doc.get("books", []):
        meta = canonical(book.get("name", ""))
        if meta is None:
            continue
        chapters = [[clean(v.get("text", "")) for v in ch.get("verses", [])]
                    for ch in book.get("chapters", [])]
        if len(chapters) != meta["chapters"]:
            print(f"!! {meta['osis']}: {len(chapters)} chapters, "
                  f"expected {meta['chapters']}", file=sys.stderr)
            return 1
        seen += 1
        verses += sum(len(c) for c in chapters)
        (OUT / f"{meta['osis']}.json").write_text(json.dumps(
            {"osis": meta["osis"], "name": meta["name"], "chapters": chapters},
            separators=(",", ":")) + "\n")
    if seen != len(BOOKS):
        print(f"!! source yielded {seen} canon books, expected {len(BOOKS)}",
              file=sys.stderr)
        return 1
    print(f"text: {seen} books, {verses} verses")


if __name__ == "__main__":
    sys.exit(main())
