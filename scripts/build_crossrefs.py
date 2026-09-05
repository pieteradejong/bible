#!/usr/bin/env python3
"""Turn OpenBible's 344k cross-references into the files the web views load.

Input:  data/raw/cross_references.txt  (From Verse \t To Verse \t Votes)
        "To Verse" may be a range: "Ps.148.4-Ps.148.5".

Outputs (web/data/):
  xref_books.json     66x66 book-to-book matrix, counts + vote-weighted totals.
  xref_chapters.json  chapter-to-chapter edges, for the chapter heatmap.
  xref/<OSIS>.json    per-book verse-level references, loaded on demand.

Votes are OpenBible's crowd score: higher means more users judged the link
apt. Negative-vote links (1242 of them) are kept but flagged, since "people
voted this down" is itself signal.
"""
import collections, json, pathlib, re, sys

BOOKS = json.loads(pathlib.Path("data/curated/books.json").read_text())
IDX = {b["osis"]: b["i"] for b in BOOKS}
N = len(BOOKS)
SRC = pathlib.Path("data/raw/cross_references.txt")
OUT = pathlib.Path("web/data")

REF = re.compile(r"^([\w]+)\.(\d+)\.(\d+)$")


def parse(ref):
    """'Gen.1.1' -> (book_index, chapter, verse); None if unparseable."""
    m = REF.match(ref)
    if not m:
        return None
    b = IDX.get(m.group(1))
    return None if b is None else (b, int(m.group(2)), int(m.group(3)))


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "xref").mkdir(exist_ok=True)

    book_mat = [[0] * N for _ in range(N)]     # link counts
    book_wt = [[0] * N for _ in range(N)]      # vote-weighted
    chap = collections.Counter()               # (fb, fc, tb, tc) -> count
    per_book = collections.defaultdict(lambda: collections.defaultdict(list))
    rows = skipped = 0

    with SRC.open() as fh:
        next(fh)  # header
        for line in fh:
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 3:
                continue
            frm, to, votes = parts[0], parts[1], parts[2]
            f = parse(frm)
            start, _, end = to.partition("-")
            t = parse(start)
            if not f or not t:
                skipped += 1
                continue
            te = parse(end) if end else None
            try:
                v = int(votes)
            except ValueError:
                v = 0
            rows += 1
            fb, fc, fv = f
            tb, tc, tv = t
            book_mat[fb][tb] += 1
            book_wt[fb][tb] += max(v, 0)
            chap[(fb, fc, tb, tc)] += 1
            # [target book, chapter, verse, end verse (0 = single), votes]
            per_book[fb][f"{fc}.{fv}"].append(
                [tb, tc, tv, te[2] if te and te[0] == tb and te[1] == tc else 0, v])

    (OUT / "xref_books.json").write_text(json.dumps({
        "books": [b["osis"] for b in BOOKS],
        "counts": book_mat,
        "weighted": book_wt,
        "total": rows,
    }, separators=(",", ":")) + "\n")

    edges = [[fb, fc, tb, tc, c] for (fb, fc, tb, tc), c in chap.items()]
    edges.sort(key=lambda e: -e[4])
    (OUT / "xref_chapters.json").write_text(
        json.dumps({"edges": edges}, separators=(",", ":")) + "\n")

    for bi, refs in per_book.items():
        osis = BOOKS[bi]["osis"]
        for k in refs:
            refs[k].sort(key=lambda r: -r[4])
        (OUT / "xref" / f"{osis}.json").write_text(
            json.dumps({"osis": osis, "refs": refs}, separators=(",", ":")) + "\n")

    print(f"xrefs: {rows} parsed, {skipped} skipped, "
          f"{len(edges)} chapter edges, {len(per_book)} per-book files")


if __name__ == "__main__":
    sys.exit(main())
