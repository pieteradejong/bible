#!/usr/bin/env python3
"""Emit data/curated/genealogy.json: the biblical descent lines as a graph.

Authored from the text. Chains are written compactly and expanded here rather
than hand-typing a few hundred JSON objects, which is how transcription errors
get in.

Two conventions worth knowing:

* Display names are the modern standard English forms, so that Matthew's
  "Ozias" and Kings' "Uzziah" resolve to one node and the lines actually join.
  The KJV spelling is kept in `kjv` wherever it differs, since the reader shows
  KJV text.
* Matthew 1 and Luke 3 disagree about Jesus' ancestry. Both are recorded in
  full, as separate lines, and the graph shows where they split (at David) and
  where they briefly rejoin (Shealtiel and Zerubbabel). Reconciling them is a
  centuries-old argument this project does not take a side in.
"""
import json, pathlib

# --- chains: (line, [(name, kjv_or_None, ref, lifespan_or_None), ...]) --------
# A chain is father -> son, in order.

GEN5 = [  # Genesis 5, with the lifespans the text gives
    ("Adam", None, "Gen.5.3", 930), ("Seth", None, "Gen.5.6", 912),
    ("Enosh", "Enos", "Gen.5.9", 905), ("Kenan", "Cainan", "Gen.5.12", 910),
    ("Mahalalel", "Mahalaleel", "Gen.5.15", 895), ("Jared", None, "Gen.5.18", 962),
    ("Enoch", None, "Gen.5.21", 365), ("Methuselah", None, "Gen.5.25", 969),
    ("Lamech", None, "Gen.5.28", 777), ("Noah", None, "Gen.5.32", 950),
]

GEN11 = [  # Genesis 11:10-26, Shem to Abram
    ("Shem", None, "Gen.11.10", 600), ("Arphaxad", None, "Gen.11.12", 438),
    ("Shelah", "Salah", "Gen.11.14", 433), ("Eber", None, "Gen.11.16", 464),
    ("Peleg", None, "Gen.11.18", 239), ("Reu", None, "Gen.11.20", 239),
    ("Serug", None, "Gen.11.22", 230), ("Nahor", None, "Gen.11.24", 148),
    ("Terah", None, "Gen.11.26", 205), ("Abraham", "Abram", "Gen.11.27", 175),
]

RUTH4 = [  # Ruth 4:18-22, the line from Perez to David
    ("Perez", "Pharez", "Ruth.4.18", None), ("Hezron", None, "Ruth.4.18", None),
    ("Ram", None, "Ruth.4.19", None), ("Amminadab", None, "Ruth.4.19", None),
    ("Nahshon", "Naasson", "Ruth.4.20", None), ("Salmon", None, "Ruth.4.20", None),
    ("Boaz", "Booz", "Ruth.4.21", None), ("Obed", None, "Ruth.4.21", None),
    ("Jesse", None, "Ruth.4.22", None), ("David", None, "Ruth.4.22", None),
]

# Matthew 1:6-16, David to Jesus through Solomon and the kings of Judah.
MATT = [
    ("David", None, "Matt.1.6", None), ("Solomon", None, "Matt.1.6", None),
    ("Rehoboam", "Roboam", "Matt.1.7", None), ("Abijah", "Abia", "Matt.1.7", None),
    ("Asa", None, "Matt.1.7", None), ("Jehoshaphat", "Josaphat", "Matt.1.8", None),
    ("Joram", None, "Matt.1.8", None), ("Uzziah", "Ozias", "Matt.1.8", None),
    ("Jotham", "Joatham", "Matt.1.9", None), ("Ahaz", "Achaz", "Matt.1.9", None),
    ("Hezekiah", "Ezekias", "Matt.1.9", None), ("Manasseh", "Manasses", "Matt.1.10", None),
    ("Amon", None, "Matt.1.10", None), ("Josiah", "Josias", "Matt.1.10", None),
    ("Jeconiah", "Jechonias", "Matt.1.11", None),
    ("Shealtiel", "Salathiel", "Matt.1.12", None),
    ("Zerubbabel", "Zorobabel", "Matt.1.12", None),
    ("Abiud", None, "Matt.1.13", None), ("Eliakim", None, "Matt.1.13", None),
    ("Azor", None, "Matt.1.13", None), ("Zadok", "Sadoc", "Matt.1.14", None),
    ("Achim", None, "Matt.1.14", None), ("Eliud", None, "Matt.1.14", None),
    ("Eleazar", None, "Matt.1.15", None), ("Matthan", None, "Matt.1.15", None),
    ("Jacob (father of Joseph)", "Jacob", "Matt.1.16", None),
    ("Joseph", None, "Matt.1.16", None), ("Jesus", None, "Matt.1.16", None),
]

# Luke 3:23-31 read downward: David to Jesus through Nathan, not Solomon.
# Names are unique to this line, so they are suffixed where they collide.
LUKE = [
    ("David", None, "Luke.3.31", None), ("Nathan", None, "Luke.3.31", None),
    ("Mattatha", None, "Luke.3.31", None), ("Menan", None, "Luke.3.31", None),
    ("Melea", None, "Luke.3.31", None), ("Eliakim (Luke)", "Eliakim", "Luke.3.30", None),
    ("Jonan", None, "Luke.3.30", None), ("Joseph (of Jonan)", "Joseph", "Luke.3.30", None),
    ("Judah (Luke)", "Juda", "Luke.3.30", None), ("Simeon", None, "Luke.3.30", None),
    ("Levi (of Simeon)", "Levi", "Luke.3.29", None),
    ("Matthat (of Levi)", "Matthat", "Luke.3.29", None),
    ("Jorim", None, "Luke.3.29", None), ("Eliezer", None, "Luke.3.29", None),
    ("Joshua (Luke)", "Jose", "Luke.3.29", None), ("Er", None, "Luke.3.28", None),
    ("Elmodam", None, "Luke.3.28", None), ("Cosam", None, "Luke.3.28", None),
    ("Addi", None, "Luke.3.28", None), ("Melchi (of Addi)", "Melchi", "Luke.3.28", None),
    ("Neri", None, "Luke.3.27", None), ("Shealtiel", "Salathiel", "Luke.3.27", None),
    ("Zerubbabel", "Zorobabel", "Luke.3.27", None),
    ("Rhesa", None, "Luke.3.27", None), ("Joanna", None, "Luke.3.27", None),
    ("Judah (of Joanna)", "Juda", "Luke.3.26", None), ("Joseph (of Judah)", "Joseph", "Luke.3.26", None),
    ("Semei", None, "Luke.3.26", None), ("Mattathias (of Semei)", "Mattathias", "Luke.3.26", None),
    ("Maath", None, "Luke.3.26", None), ("Naggai", "Nagge", "Luke.3.25", None),
    ("Esli", None, "Luke.3.25", None), ("Nahum", "Naum", "Luke.3.25", None),
    ("Amos", None, "Luke.3.25", None), ("Mattathias (of Amos)", "Mattathias", "Luke.3.25", None),
    ("Joseph (of Mattathias)", "Joseph", "Luke.3.24", None),
    ("Jannai", "Janna", "Luke.3.24", None), ("Melchi (of Jannai)", "Melchi", "Luke.3.24", None),
    ("Levi (of Melchi)", "Levi", "Luke.3.24", None),
    ("Matthat (of Levi 2)", "Matthat", "Luke.3.24", None),
    ("Heli", None, "Luke.3.23", None), ("Joseph", None, "Luke.3.23", None),
    ("Jesus", None, "Luke.3.23", None),
]

CHAINS = [
    ("primeval", GEN5), ("primeval", GEN11), ("judah", RUTH4),
    ("matthew", MATT), ("luke", LUKE),
]

# --- edges the chains do not cover ------------------------------------------
# (parent, child, ref, kind, note)
EXTRA = [
    ("Noah", "Shem", "Gen.10.1", "son", None),
    ("Noah", "Ham", "Gen.10.1", "son", None),
    ("Noah", "Japheth", "Gen.10.1", "son", None),
    ("Ham", "Cush", "Gen.10.6", "son", None),
    ("Ham", "Canaan", "Gen.10.6", "son", "Cursed in Gen 9:25; the ancestor named for the land Israel enters."),
    ("Cush", "Nimrod", "Gen.10.8", "son", "\"A mighty hunter before the LORD\"; founder of Babel and Nineveh."),
    ("Terah", "Nahor (son of Terah)", "Gen.11.27", "son", None),
    ("Terah", "Haran", "Gen.11.27", "son", None),
    ("Haran", "Lot", "Gen.11.27", "son", None),
    ("Abraham", "Ishmael", "Gen.16.15", "son", "By Hagar. Ancestor of twelve princes (Gen 25:16)."),
    ("Abraham", "Isaac", "Gen.21.3", "son", "The child of the promise."),
    ("Isaac", "Esau", "Gen.25.25", "son", "The elder twin; ancestor of Edom."),
    ("Isaac", "Jacob", "Gen.25.26", "son", "Renamed Israel in Gen 32:28."),
    ("Jacob", "Reuben", "Gen.29.32", "son", None),
    ("Jacob", "Simeon (son of Jacob)", "Gen.29.33", "son", None),
    ("Jacob", "Levi", "Gen.29.34", "son", "Ancestor of the priestly tribe."),
    ("Jacob", "Judah", "Gen.29.35", "son", "The royal line runs through him."),
    ("Jacob", "Dan", "Gen.30.6", "son", None),
    ("Jacob", "Naphtali", "Gen.30.8", "son", None),
    ("Jacob", "Gad", "Gen.30.11", "son", None),
    ("Jacob", "Asher", "Gen.30.13", "son", None),
    ("Jacob", "Issachar", "Gen.30.18", "son", None),
    ("Jacob", "Zebulun", "Gen.30.20", "son", None),
    ("Jacob", "Dinah", "Gen.30.21", "daughter", None),
    ("Jacob", "Joseph (son of Jacob)", "Gen.30.24", "son", None),
    ("Jacob", "Benjamin", "Gen.35.18", "son", None),
    ("Joseph (son of Jacob)", "Manasseh (son of Joseph)", "Gen.41.51", "son", None),
    ("Joseph (son of Jacob)", "Ephraim", "Gen.41.52", "son", None),
    ("Judah", "Perez", "Gen.38.29", "son", "By Tamar, his daughter-in-law (Gen 38)."),
    ("David", "Absalom", "2Sam.3.3", "son", None),
    ("David", "Nathan", "2Sam.5.14", "son", "Luke's genealogy runs through him rather than Solomon."),
    ("David", "Solomon", "2Sam.12.24", "son", "By Bathsheba."),
    ("Jeconiah", "Shealtiel", "1Chr.3.17", "son",
     "Jeremiah 22:30 declares Jeconiah childless of a reigning heir, which is one "
     "reason Luke routes Jesus' descent around him."),
]

SPOUSES = [
    ("Adam", "Eve", "Gen.3.20"),
    ("Abraham", "Sarah", "Gen.17.15"),
    ("Abraham", "Hagar", "Gen.16.3"),
    ("Isaac", "Rebekah", "Gen.24.67"),
    ("Jacob", "Leah", "Gen.29.23"),
    ("Jacob", "Rachel", "Gen.29.28"),
    ("Judah", "Tamar", "Gen.38.6"),
    ("Boaz", "Ruth", "Ruth.4.13"),
    ("David", "Bathsheba", "2Sam.11.27"),
    ("Joseph", "Mary", "Matt.1.18"),
]

WOMEN = {"Eve", "Sarah", "Hagar", "Rebekah", "Leah", "Rachel", "Tamar", "Ruth",
         "Bathsheba", "Mary", "Dinah"}


def main():
    people, edges = {}, []

    def add(name, kjv=None, ref=None, age=None, line=None):
        p = people.setdefault(name, {
            "id": name, "name": name, "kjv": kjv, "refs": [],
            "age": age, "lines": [], "sex": "f" if name in WOMEN else "m",
        })
        if kjv and not p["kjv"]:
            p["kjv"] = kjv
        if age and not p["age"]:
            p["age"] = age
        if ref and ref not in p["refs"]:
            p["refs"].append(ref)
        if line and line not in p["lines"]:
            p["lines"].append(line)
        return p

    for line, chain in CHAINS:
        for i, (name, kjv, ref, age) in enumerate(chain):
            add(name, kjv, ref, age, line)
            if i:
                prev = chain[i - 1][0]
                edges.append({"p": prev, "c": name, "ref": ref,
                              "kind": "son", "line": line})

    for parent, child, ref, kind, note in EXTRA:
        add(parent, ref=ref)
        add(child, ref=ref)
        e = {"p": parent, "c": child, "ref": ref, "kind": kind, "line": "other"}
        if note:
            e["note"] = note
        edges.append(e)

    for a, b, ref in SPOUSES:
        add(a, ref=ref)
        add(b, ref=ref)
        edges.append({"p": a, "c": b, "ref": ref, "kind": "spouse", "line": "spouse"})

    # Deduplicate parent/child pairs that both a chain and EXTRA assert.
    seen, uniq = set(), []
    for e in edges:
        key = (e["p"], e["c"], e["kind"])
        if key in seen:
            continue
        seen.add(key)
        uniq.append(e)

    out = pathlib.Path("data/curated/genealogy.json")
    out.write_text(json.dumps({
        "people": list(people.values()),
        "edges": uniq,
        "lines": {
            "primeval": "Adam to Abraham (Genesis 5 and 11)",
            "judah": "Perez to David (Ruth 4)",
            "matthew": "David to Jesus via Solomon (Matthew 1)",
            "luke": "David to Jesus via Nathan (Luke 3)",
            "other": "Named family relationships outside the main chains",
            "spouse": "Marriages",
        },
    }, indent=1) + "\n")
    print(f"genealogy: {len(people)} people, {len(uniq)} edges "
          f"({sum(1 for e in uniq if e['kind'] == 'spouse')} marriages)")


if __name__ == "__main__":
    main()
