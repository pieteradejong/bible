#!/usr/bin/env python3
"""Merge, validate and emit the curated chronology and journey routes.

Everything hand-authored under data/curated/ is checked here rather than
trusted: every scripture reference must name a verse that actually exists in
the KJV text, and every journey stop must resolve to a real gazetteer entry.
Authoring a chronology by hand guarantees typos; this is what catches them.

Outputs (web/data/):
  timeline.json   eras + events + people + book composition bands.
  journeys.json   routes with coordinates attached to every stop.
  genealogy.json  the descent graph, refs checked the same way.
"""
import json, pathlib, re, sys

CUR = pathlib.Path("data/curated")
OUT = pathlib.Path("web/data")
BOOKS = json.loads((CUR / "books.json").read_text())
IDX = {b["osis"]: b["i"] for b in BOOKS}
REF = re.compile(r"^([\w]+)\.(\d+)\.(\d+)$")

errors = []


def load(name):
    return json.loads((CUR / name).read_text())


def verse_index():
    """{osis: [verses per chapter]} from the built KJV text."""
    idx = {}
    for b in BOOKS:
        p = OUT / "text" / f"{b['osis']}.json"
        if not p.exists():
            errors.append(f"missing text file {p}; run build_text.py first")
            return {}
        idx[b["osis"]] = [len(c) for c in json.loads(p.read_text())["chapters"]]
    return idx


def check_refs(item, verses):
    """Every ref must be a real verse; annotate it with a readable label."""
    out = []
    for ref in item.get("refs", []):
        m = REF.match(ref)
        if not m or m.group(1) not in IDX:
            errors.append(f"{item.get('id')}: unparseable ref {ref!r}")
            continue
        book, ch, vs = m.group(1), int(m.group(2)), int(m.group(3))
        lens = verses.get(book, [])
        if ch > len(lens):
            errors.append(f"{item.get('id')}: {ref} - {book} has {len(lens)} chapters")
            continue
        if vs > lens[ch - 1]:
            errors.append(
                f"{item.get('id')}: {ref} - {book} {ch} has {lens[ch-1]} verses")
            continue
        name = BOOKS[IDX[book]]["name"]
        out.append({"osis": ref, "label": f"{name} {ch}:{vs}", "book": IDX[book]})
    item["refs"] = out
    return item


def build_gazetteer():
    """name -> {lat, lon, ...}, preferring the most-mentioned homonym."""
    g = {}
    for p in json.loads((OUT / "places.json").read_text()):
        for key in (p["name"], re.sub(r" \d+$", "", p["name"])):
            if key not in g or p["n"] > g[key]["n"]:
                g[key] = p
    for e in load("extra_places.json"):
        g.setdefault(e["name"], {**e, "n": 0, "conf": "n/a", "id": "x_" + e["name"]})
    return g


def main():
    verses = verse_index()
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1

    eras = [check_refs(e, verses) for e in load("eras.json")]
    events = [check_refs(e, verses) for e in load("events.json")]
    people = [check_refs(p, verses) for p in load("people.json")]

    seen = set()
    for coll, kind in ((eras, "era"), (events, "event"), (people, "person")):
        for item in coll:
            if item["id"] in seen:
                errors.append(f"duplicate id {item['id']!r} ({kind})")
            seen.add(item["id"])
            if item.get("end") is not None and item["end"] < item["start"]:
                errors.append(f"{item['id']}: end {item['end']} precedes start")

    gaz = build_gazetteer()
    for e in events:
        located = []
        for n in e.get("places", []):
            hit = gaz.get(n)
            if hit is None:
                errors.append(f"{e['id']}: unknown place {n!r}")
                continue
            located.append({"name": n, "lat": hit["lat"], "lon": hit["lon"]})
        e["places"] = located

    journeys = load("journeys.json")
    for j in journeys:
        for stop in j["stops"]:
            hit = gaz.get(stop["place"])
            if not hit:
                errors.append(f"journey {j['id']}: unknown place {stop['place']!r}")
                continue
            stop["lat"], stop["lon"] = hit["lat"], hit["lon"]
            stop.setdefault("label", stop["place"])
            stop["conf"] = hit.get("conf", "unknown")
        j["stops"] = [s for s in j["stops"] if "lat" in s]

    # The genealogy is hand-authored too, so its references get the same check.
    gen = load("genealogy.json")
    for person in gen["people"]:
        check_refs({"id": f"genealogy:{person['id']}", "refs": person["refs"]}, verses)
    edge_refs = {"id": "genealogy:edges",
                 "refs": sorted({e["ref"] for e in gen["edges"] if e.get("ref")})}
    check_refs(edge_refs, verses)
    ids = {p["id"] for p in gen["people"]}
    for e in gen["edges"]:
        for side in ("p", "c"):
            if e[side] not in ids:
                errors.append(f"genealogy: edge names unknown person {e[side]!r}")

    if errors:
        print(f"{len(errors)} validation error(s):", file=sys.stderr)
        print("\n".join("  " + e for e in errors), file=sys.stderr)
        return 1

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "timeline.json").write_text(json.dumps({
        "eras": eras, "events": events, "people": people,
        "books": [{"osis": b["osis"], "name": b["name"], "i": b["i"],
                   "testament": b["testament"], "division": b["division"],
                   "chapters": b["chapters"], "composed": b["composed"]}
                  for b in BOOKS],
    }, separators=(",", ":")) + "\n")
    (OUT / "journeys.json").write_text(
        json.dumps(journeys, separators=(",", ":")) + "\n")
    (OUT / "genealogy.json").write_text(
        json.dumps(gen, separators=(",", ":")) + "\n")
    print(f"genealogy: {len(gen['people'])} people, {len(gen['edges'])} edges, "
          "all refs resolved")
    print(f"timeline: {len(eras)} eras, {len(events)} events, {len(people)} people, "
          f"{len(journeys)} journeys ({sum(len(j['stops']) for j in journeys)} stops), "
          "all refs and places resolved")


if __name__ == "__main__":
    sys.exit(main())
