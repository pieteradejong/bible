#!/usr/bin/env python3
"""Per-book geographic statistics: where each book's world actually sits.

Two things come out of this:

  drift      The mention-weighted centroid of every place a book names, in
             canonical order. Connected, it traces the biblical world's focus
             moving from Mesopotamia to Canaan, down into Egypt and Sinai, back
             to the Levant, and finally out across the Mediterranean.

  footprint  The set of places each book names, for small-multiple thumbnails
             drawn on one shared extent so they are honestly comparable.

Weighting by mentions rather than counting each place once is deliberate: a
book that names Jerusalem forty times and Tarshish once is centred on
Jerusalem, and an unweighted centroid would not say so.

Output: web/data/geostats.json
"""
import json, math, pathlib, sys

OUT = pathlib.Path("web/data")


def main():
    places_path, timeline_path = OUT / "places.json", OUT / "timeline.json"
    if not places_path.exists() or not timeline_path.exists():
        print("!! run build_places.py and build_timeline.py first", file=sys.stderr)
        return 1

    places = json.loads(places_path.read_text())
    books = json.loads(timeline_path.read_text())["books"]

    per_book = {b["i"]: [] for b in books}
    for p in places:
        for bi, n in p["books"].items():
            per_book[int(bi)].append((p["lat"], p["lon"], n, p["id"]))

    rows = []
    for b in books:
        pts = per_book[b["i"]]
        weight = sum(n for _, _, n, _ in pts)
        row = {
            "i": b["i"], "osis": b["osis"], "name": b["name"],
            "testament": b["testament"], "division": b["division"],
            "places": len(pts), "mentions": weight,
        }
        if pts:
            row["lat"] = round(sum(la * n for la, _, n, _ in pts) / weight, 4)
            row["lon"] = round(sum(lo * n for _, lo, n, _ in pts) / weight, 4)
            # How spread out the book is: mention-weighted mean distance from
            # its own centre, in km. Acts should dwarf Ruth.
            row["spread"] = round(sum(
                n * haversine(row["lat"], row["lon"], la, lo)
                for la, lo, n, _ in pts) / weight, 1)
            row["extent"] = [
                round(min(la for la, _, _, _ in pts), 4),
                round(min(lo for _, lo, _, _ in pts), 4),
                round(max(la for la, _, _, _ in pts), 4),
                round(max(lo for _, lo, _, _ in pts), 4),
            ]
            # Points for the thumbnail: id, position, weight.
            row["pts"] = [[la, lo, n] for la, lo, n, _ in
                          sorted(pts, key=lambda t: -t[2])[:400]]
        rows.append(row)

    located = [r for r in rows if "lat" in r]
    bounds = [
        min(r["extent"][0] for r in located), min(r["extent"][1] for r in located),
        max(r["extent"][2] for r in located), max(r["extent"][3] for r in located),
    ]
    dest = OUT / "geostats.json"
    dest.write_text(json.dumps({"books": rows, "bounds": bounds},
                               separators=(",", ":")) + "\n")
    thin = [r["osis"] for r in rows if r["places"] < 3]
    print(f"geostats: {len(located)} of {len(rows)} books located, "
          f"{len(thin)} with fewer than 3 places, "
          f"{dest.stat().st_size / 1e6:.2f} MB")


def haversine(lat1, lon1, lat2, lon2):
    """Great-circle distance in km. Good enough for a spread statistic."""
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(min(1.0, math.sqrt(a)))


if __name__ == "__main__":
    sys.exit(main())
