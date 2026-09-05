#!/usr/bin/env python3
"""Flatten OpenBible's Bible-Geocoding-Data into a compact atlas dataset.

ancient.jsonl is one JSON object per biblical place, each carrying every
scholarly identification proposed for it, each identification carrying one or
more modern-location resolutions. We keep the highest-scoring resolution that
has coordinates, and record how confident the scholarship is about it so the
map can show doubt rather than hide it.

Outputs (web/data/):
  places.json         one row per geolocatable place: name, coords, type,
                      confidence, mention count, per-book mention counts.
  places_verses.json  place id -> full list of OSIS verse references.
  places_meta.json    type/testament tallies used to build the map legend.
"""
import collections, json, pathlib, re, sys

BOOKS = json.loads(pathlib.Path("data/curated/books.json").read_text())
IDX = {b["osis"]: b["i"] for b in BOOKS}
SRC = pathlib.Path("data/raw/ancient.jsonl")
OUT = pathlib.Path("web/data")

# Each identification carries the confidence votes of the scholarly sources that
# proposed it, as tag counts ("confidence_yes", "confidence_possible", ...).
# Collapse those into one label so the map can style how sure the siting is.
CONF_RANK = [
    ("confidence_yes", "certain"),
    ("confidence_likely", "likely"),
    ("confidence_mostlikely", "likely"),
    ("confidence_map", "possible"),
    ("confidence_possible", "possible"),
    ("confidence_unlikely", "disputed"),
    ("confidence_no", "disputed"),
]


def confidence(ident):
    """Label the winning identification by the strongest confidence tag on it."""
    tags = (ident.get("votes") or {}).get("tags") or {}
    if not tags:
        return "unknown"
    # Weight by how many sources voted each way, then take the strongest label
    # that at least a third of the sources back.
    total = sum(tags.values()) or 1
    for key, label in CONF_RANK:
        if tags.get(key, 0) / total >= 0.34:
            return label
    for key, label in CONF_RANK:
        if tags.get(key):
            return label
    return "unknown"


def display_name(name):
    """OpenBible disambiguates homonyms as "Bethel 1", "Bethel 2". The first is
    the primary one, so drop its suffix and parenthesise the rest."""
    m = re.match(r"^(.*) (\d+)$", name)
    if not m:
        return name
    return m.group(1) if m.group(2) == "1" else f"{m.group(1)} ({m.group(2)})"


def best_resolution(rec):
    """Highest-scoring (identification, resolution) pair that has coordinates."""
    best = None
    for ident in rec.get("identifications", []):
        score = (ident.get("score") or {}).get("vote_total")
        for res in ident.get("resolutions", []):
            if not res.get("lonlat"):
                continue
            if best is None or (score or 0) > (best[0] or 0):
                best = (score, ident, res)
    return best


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    places, verses_by_place = [], {}
    total_v = ungeo = 0

    for line in SRC.open():
        rec = json.loads(line)
        best = best_resolution(rec)
        if not best:
            ungeo += 1
            continue
        score, ident, res = best
        lon, lat = (float(x) for x in res["lonlat"].split(","))
        # How much of the scholarly vote the winning site takes, and how many
        # rival sites have been proposed: a place with three near-tied
        # candidates is genuinely unlocated, not merely "possible".
        scores = [max((i.get("score") or {}).get("vote_total") or 0, 0)
                  for i in rec.get("identifications", [])]
        share = round((score or 0) / sum(scores), 3) if sum(scores) > 0 else 0
        alts = sum(1 for x in scores if x > 0)

        per_book = collections.Counter()
        osises = []
        for v in rec.get("verses", []):
            osis = v.get("osis", "")
            book = osis.split(".")[0]
            if book in IDX:
                per_book[IDX[book]] += 1
                osises.append(osis)
        if not osises:
            continue
        total_v += len(osises)

        first = min(osises, key=lambda o: (IDX[o.split(".")[0]],
                                           int(o.split(".")[1]),
                                           int(o.split(".")[2])))
        testaments = {BOOKS[b]["testament"] for b in per_book}
        places.append({
            "id": rec["id"],
            "name": rec.get("friendly_id", "?"),
            "disp": display_name(rec.get("friendly_id", "?")),
            "slug": rec.get("url_slug", ""),
            "lat": round(lat, 5),
            "lon": round(lon, 5),
            "type": res.get("type") or (rec.get("types") or ["unknown"])[0],
            "kind": res.get("class", ""),          # human / natural
            "conf": confidence(ident),
            "share": share,
            "alts": alts,
            "n": len(osises),
            "books": {str(k): v for k, v in sorted(per_book.items())},
            "first": first,
            "t": "both" if len(testaments) > 1 else next(iter(testaments)),
        })
        verses_by_place[rec["id"]] = osises

    places.sort(key=lambda p: -p["n"])
    (OUT / "places.json").write_text(
        json.dumps(places, separators=(",", ":")) + "\n")
    (OUT / "places_verses.json").write_text(
        json.dumps(verses_by_place, separators=(",", ":")) + "\n")

    types = collections.Counter(p["type"] for p in places)
    (OUT / "places_meta.json").write_text(json.dumps({
        "count": len(places),
        "ungeolocated": ungeo,
        "mentions": total_v,
        "types": types.most_common(),
        "confidence": collections.Counter(p["conf"] for p in places).most_common(),
        "contested": sum(1 for p in places if p["alts"] > 1),
    }, indent=1) + "\n")
    print(f"places: {len(places)} geolocated, {ungeo} without coordinates, "
          f"{total_v} verse mentions, {len(types)} types")


if __name__ == "__main__":
    sys.exit(main())
