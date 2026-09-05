#!/usr/bin/env python3
"""Split the public-domain KJV into one JSON file per book, keyed by OSIS.

The source marks translator-supplied words and marginal notes with braces:
  "the earth was without form, and void; and darkness {was} upon the face"
  "...he called Night. {And the evening...: Heb. ...}"
  "they shall be to me a people {in: or, upon}"
Supplied words are kept (wrapped in <i>, which is what the italics mean);
marginal notes are dropped. The two are told apart by a colon: a note always
has the "lemma: gloss" shape, and of the 29,393 brace spans in the text not one
genuine supplied-word span contains a colon -- they are words like "is", "was"
and "shall be".

Output: web/data/text/<OSIS>.json  {"osis": "Gen", "chapters": [[verse, ...]]}
"""
import json, pathlib, re, sys

BOOKS = json.loads(pathlib.Path("data/curated/books.json").read_text())
SRC = pathlib.Path("data/raw/en_kjv.json")
OUT = pathlib.Path("web/data/text")

BRACE = re.compile(r"\{([^{}]*)\}")


def clean(verse):
    def sub(m):
        body = m.group(1)
        # A marginal note always carries a colon; a supplied word never does.
        return "" if ":" in body else f"<i>{body}</i>"
    return re.sub(r"\s{2,}", " ", BRACE.sub(sub, verse)).strip()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    raw = json.loads(SRC.read_text(encoding="utf-8-sig"))
    if len(raw) != len(BOOKS):
        print(f"!! source has {len(raw)} books, canon table has {len(BOOKS)}",
              file=sys.stderr)
        return 1
    verses = 0
    for book, meta in zip(raw, BOOKS):
        chapters = [[clean(v) for v in ch] for ch in book["chapters"]]
        if len(chapters) != meta["chapters"]:
            print(f"!! {meta['osis']}: {len(chapters)} chapters, "
                  f"expected {meta['chapters']}", file=sys.stderr)
            return 1
        verses += sum(len(c) for c in chapters)
        (OUT / f"{meta['osis']}.json").write_text(json.dumps(
            {"osis": meta["osis"], "name": meta["name"], "chapters": chapters},
            separators=(",", ":")) + "\n")
    print(f"text: {len(raw)} books, {verses} verses")


if __name__ == "__main__":
    sys.exit(main())
