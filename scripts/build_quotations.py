#!/usr/bin/env python3
"""Separate direct quotation from looser allusion in the cross-testament links.

The cross-reference data does not distinguish "Matthew is quoting Isaiah" from
"Matthew is evoking Isaiah". Nothing labels that, so we measure it: for every
cross-reference that crosses between the testaments, compare the two verses'
wording and record the longest run of words they share.

What this measures, and what it does not
----------------------------------------
This is *lexical overlap in the KJV*, not authorial intent. Three caveats the
view repeats to the reader:

1. The KJV translators deliberately harmonised New Testament quotations with
   their own Old Testament wording, which inflates overlap.
2. New Testament authors usually quote the Septuagint, whose Greek often
   differs from the Hebrew the English Old Testament renders - so a real
   quotation can score low.
3. A long shared run can be pure coincidence of common phrasing ("and it came
   to pass"), which is why the score also weighs how distinctive the shared
   words are.

Output: web/data/quotations.json
"""
import collections, json, math, pathlib, re, sys
from difflib import SequenceMatcher

BOOKS = json.loads(pathlib.Path("data/curated/books.json").read_text())
IDX = {b["osis"]: b["i"] for b in BOOKS}
OT = {b["i"] for b in BOOKS if b["testament"] == "OT"}
SRC = pathlib.Path("data/raw/cross_references.txt")
OUT = pathlib.Path("web/data")
TEXT = OUT / "text"

WORD = re.compile(r"[a-z]+")
REF = re.compile(r"^(\w+)\.(\d+)\.(\d+)$")

# Runs made only of these are not evidence of anything.
COMMON = {"and", "the", "of", "to", "in", "that", "he", "shall", "unto", "for",
          "i", "his", "a", "they", "be", "is", "with", "not", "them", "it",
          "which", "him", "me", "my", "you", "but", "their", "have", "will",
          "was", "are", "all", "we", "ye", "as", "thou", "thy", "said", "came",
          "pass", "when", "then", "there", "this", "these", "from", "by", "on"}


def load_text():
    t = {}
    for b in BOOKS:
        p = TEXT / f"{b['osis']}.json"
        if not p.exists():
            print(f"!! {p} missing; run build_text.py first", file=sys.stderr)
            sys.exit(1)
        t[b["i"]] = json.loads(p.read_text())["chapters"]
    return t


def words(s):
    return WORD.findall(re.sub(r"<[^>]+>", " ", s.lower()))


def parse(ref):
    m = REF.match(ref)
    if not m or m.group(1) not in IDX:
        return None
    return IDX[m.group(1)], int(m.group(2)), int(m.group(3))


def classify(run, distinct, jaccard):
    """run = shared word count; distinct = of those, how many are uncommon."""
    if run >= 6 and distinct >= 3:
        return "quotation"
    if run >= 4 and distinct >= 2:
        return "strong echo"
    if run >= 3 or jaccard >= 0.34:
        return "echo"
    return "allusion"


def main():
    text = load_text()

    def verse(bi, ch, vs):
        try:
            return text[bi][ch - 1][vs - 1]
        except (IndexError, KeyError):
            return None

    pairs, matrix = [], collections.Counter()
    classes = collections.Counter()
    scanned = 0

    with SRC.open() as fh:
        next(fh)
        for line in fh:
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 3:
                continue
            f = parse(parts[0])
            t = parse(parts[1].split("-")[0])
            if not f or not t:
                continue
            if (f[0] in OT) == (t[0] in OT):     # same testament: not our question
                continue
            # Orient every pair as New Testament -> Old Testament.
            nt, ot = (t, f) if f[0] in OT else (f, t)
            a, b = verse(*nt), verse(*ot)
            if not a or not b:
                continue
            scanned += 1
            wa, wb = words(a), words(b)
            if len(wa) < 3 or len(wb) < 3:
                continue
            m = SequenceMatcher(None, wa, wb, autojunk=False).find_longest_match(
                0, len(wa), 0, len(wb))
            shared = wa[m.a:m.a + m.size]
            distinct = sum(1 for w in shared if w not in COMMON)
            sa, sb = set(wa) - COMMON, set(wb) - COMMON
            jac = len(sa & sb) / len(sa | sb) if sa | sb else 0.0
            cls = classify(m.size, distinct, jac)
            classes[cls] += 1
            if cls == "allusion":
                continue                          # too many to ship, and least useful
            matrix[(nt[0], ot[0])] += 1
            pairs.append({
                "nt": f"{BOOKS[nt[0]]['osis']}.{nt[1]}.{nt[2]}",
                "ot": f"{BOOKS[ot[0]]['osis']}.{ot[1]}.{ot[2]}",
                "run": m.size, "distinct": distinct,
                "jac": round(jac, 3), "cls": cls,
                "shared": " ".join(shared),
                "votes": int(parts[2]) if parts[2].lstrip("-").isdigit() else 0,
            })

    # Strongest first: long distinctive runs beat long common ones.
    pairs.sort(key=lambda p: (-(p["distinct"] * 2 + p["run"]), -p["votes"]))
    seen, uniq = set(), []
    for p in pairs:
        k = (p["nt"], p["ot"])
        if k in seen:
            continue
        seen.add(k)
        uniq.append(p)

    (OUT / "quotations.json").write_text(json.dumps({
        "pairs": uniq,
        "matrix": [[a, b, n] for (a, b), n in matrix.most_common()],
        "classes": classes.most_common(),
        "scanned": scanned,
    }, separators=(",", ":")) + "\n")

    print(f"quotations: {scanned:,} cross-testament links scanned -> "
          f"{len(uniq):,} kept  " +
          "  ".join(f"{k}:{v:,}" for k, v in classes.most_common()))


if __name__ == "__main__":
    sys.exit(main())
