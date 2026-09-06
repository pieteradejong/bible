#!/usr/bin/env python3
"""Extract the areal and linear shapes from the gazetteer's GeoJSON.

Every biblical place ships a GeoJSON file, but most are single points we
already have. What is worth drawing is the ~280 places that are genuinely
regions, rivers, valleys and seas: Judea as an area rather than a dot, the
Jordan as a line rather than a pin.

The raw files total ~100 MB, far too much for a browser, so each ring is
simplified with Ramer-Douglas-Peucker and rounded to four decimals (~11 m).

Also extracts the uncertainty fields. For 55 places whose extent nobody knows
-- Amalek, Ammon, Aram, Assyria, Bashan -- the gazetteer ships *isobands*: a
stack of nested contours from min_confidence to max_confidence. The atlas draws
those as a graded field instead of a point pretending to know, which is the
whole argument of this project applied to space rather than time.

The files carry one min/max pair for the whole stack rather than a level per
ring, but the polygons arrive ordered by decreasing area -- broadest (least
confident) first, tightest (most confident) last -- so the level of ring i of n
is min + (max - min) * i / (n - 1).

Outputs:
  web/data/geometry.json     { placeId: {name, type, kind, rings} }
  web/data/uncertainty.json  { placeId: {name, min, max, bands: [{conf, ring}]} }
"""
import json, math, pathlib, sys

RAW = pathlib.Path("data/raw")
G = RAW / "geometry"
OUT = pathlib.Path("web/data")

# Point geometry adds nothing over the markers the atlas already draws.
AREA = {"Polygon", "MultiPolygon"}
LINE = {"LineString", "MultiLineString"}

TOLERANCE = 0.004   # degrees; ~450 m at this latitude
MIN_POINTS = 3


def perpendicular(p, a, b):
    """Distance from p to segment ab, in degrees. Good enough at this scale."""
    (px, py), (ax, ay), (bx, by) = p, a, b
    dx, dy = bx - ax, by - ay
    if dx == 0 and dy == 0:
        return math.hypot(px - ax, py - ay)
    t = max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def simplify(pts, tol=TOLERANCE):
    """Ramer-Douglas-Peucker, iterative so long rivers cannot blow the stack."""
    if len(pts) < 3:
        return pts
    keep = [False] * len(pts)
    keep[0] = keep[-1] = True
    stack = [(0, len(pts) - 1)]
    while stack:
        lo, hi = stack.pop()
        if hi <= lo + 1:
            continue
        worst, wi = tol, -1
        for i in range(lo + 1, hi):
            d = perpendicular(pts[i], pts[lo], pts[hi])
            if d > worst:
                worst, wi = d, i
        if wi >= 0:
            keep[wi] = True
            stack.append((lo, wi))
            stack.append((wi, hi))
    return [p for p, k in zip(pts, keep) if k]


def rings_of(geom):
    """Flatten any GeoJSON geometry into a list of coordinate rings."""
    t, c = geom.get("type"), geom.get("coordinates") or []
    if t == "Polygon":
        return list(c)
    if t == "MultiPolygon":
        return [ring for poly in c for ring in poly]
    if t == "LineString":
        return [c]
    if t == "MultiLineString":
        return list(c)
    if t == "GeometryCollection":
        return [r for g in geom.get("geometries", []) for r in rings_of(g)]
    return []


def first_geometry(doc):
    if doc.get("type") == "FeatureCollection":
        feats = doc.get("features") or []
        return feats[0].get("geometry") if feats else None
    if doc.get("type") == "Feature":
        return doc.get("geometry")
    return doc


def geometry_index():
    """{geometry id: record} for every isoband/probability surface on disk."""
    path = RAW / "geometry.jsonl"
    if not path.exists():
        return {}
    idx = {}
    for line in path.open():
        rec = json.loads(line)
        if rec.get("geometry") in ("isobands", "probability") and \
                rec.get("isobands_geojson_file"):
            idx[rec["id"]] = rec
    return idx


def geometry_ids(rec):
    """Every geometry id an ancient place points at, however it points."""
    out = set()
    for ident in rec.get("identifications", []):
        if ident.get("geometry_id"):
            out.add(ident["geometry_id"])
        for res in ident.get("resolutions", []):
            for key in ("radius_geometry_id", "precise_geometry_id"):
                if res.get(key):
                    out.add(res[key])
    return out


def build_uncertainty(geo_index):
    """Nested confidence contours, keyed by the ancient place they belong to."""
    out = {}
    for line in (RAW / "ancient.jsonl").open():
        rec = json.loads(line)
        hit = next((geo_index[g] for g in geometry_ids(rec) if g in geo_index), None)
        if not hit:
            continue
        path = G / hit["isobands_geojson_file"]
        if not path.exists():
            continue
        try:
            doc = json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        geom = first_geometry(doc)
        props = doc.get("properties") or {}
        lo = props.get("min_confidence", 10)
        hi = props.get("max_confidence", 90)
        rings = rings_of(geom or {})
        if len(rings) < 2:
            continue
        bands = []
        for i, ring in enumerate(rings):
            pts = [(float(x), float(y)) for x, y in ring
                   if isinstance(x, (int, float)) and isinstance(y, (int, float))]
            if len(pts) < MIN_POINTS:
                continue
            simple = simplify(pts, TOLERANCE / 2)   # these are small; keep detail
            conf = lo + (hi - lo) * i / max(len(rings) - 1, 1)
            bands.append({"conf": round(conf),
                          "ring": [[round(y, 4), round(x, 4)] for x, y in simple]})
        if len(bands) < 2:
            continue
        out[rec["id"]] = {
            "name": rec.get("friendly_id", "?"),
            "type": (rec.get("types") or ["unknown"])[0],
            "min": lo, "max": hi, "bands": bands,
        }
    return out


def main():
    if not G.is_dir():
        print("!! data/raw/geometry missing; run fetch_sources.py", file=sys.stderr)
        return 1
    OUT.mkdir(parents=True, exist_ok=True)

    out, pts_in, pts_out, skipped = {}, 0, 0, 0
    for line in (RAW / "ancient.jsonl").open():
        rec = json.loads(line)
        gf = rec.get("geojson_file")
        if not gf or not (G / gf).exists():
            continue
        try:
            geom = first_geometry(json.loads((G / gf).read_text()))
        except (json.JSONDecodeError, OSError):
            skipped += 1
            continue
        if not geom or geom.get("type") not in AREA | LINE:
            continue

        rings = []
        for ring in rings_of(geom):
            pts = [(float(x), float(y)) for x, y in ring
                   if isinstance(x, (int, float)) and isinstance(y, (int, float))]
            if len(pts) < MIN_POINTS:
                continue
            pts_in += len(pts)
            s = simplify(pts)
            if len(s) < MIN_POINTS:
                continue
            pts_out += len(s)
            # Leaflet wants [lat, lon]; GeoJSON gives [lon, lat].
            rings.append([[round(y, 4), round(x, 4)] for x, y in s])
        if not rings:
            continue

        out[rec["id"]] = {
            "name": rec.get("friendly_id", "?"),
            "type": (rec.get("types") or ["unknown"])[0],
            "kind": "area" if geom["type"] in AREA else "line",
            "rings": rings,
        }

    dest = OUT / "geometry.json"
    dest.write_text(json.dumps(out, separators=(",", ":")) + "\n")
    areas = sum(1 for v in out.values() if v["kind"] == "area")
    print(f"geometry: {len(out)} shapes ({areas} areas, {len(out) - areas} lines), "
          f"{pts_in:,} points simplified to {pts_out:,} "
          f"({pts_out / max(pts_in, 1):.1%}), {dest.stat().st_size / 1e6:.2f} MB"
          + (f", {skipped} unreadable" if skipped else ""))

    unc = build_uncertainty(geometry_index())
    udest = OUT / "uncertainty.json"
    udest.write_text(json.dumps(unc, separators=(",", ":")) + "\n")
    bands = sum(len(v["bands"]) for v in unc.values())
    print(f"uncertainty: {len(unc)} places drawn as graded fields, {bands} "
          f"confidence bands, {udest.stat().st_size / 1e6:.2f} MB")


if __name__ == "__main__":
    sys.exit(main())
