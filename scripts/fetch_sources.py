#!/usr/bin/env python3
"""Download every third-party source into data/raw/ (gitignored).

Nothing here is committed: the sources are large, they have their own licenses,
and they change upstream. Run `make data` (or `python3 scripts/build_all.py`)
to fetch and then rebuild the derived files under web/data/.

Sources and licenses are catalogued in README.md -> "Data sources".
"""
import hashlib, io, json, pathlib, sys, tarfile, urllib.request, zipfile

RAW = pathlib.Path("data/raw")
UA = {"User-Agent": "bible-viz/0.1 (+https://github.com/pieteradejong/bible)"}

SOURCES = {
    "cross_references.txt": {
        "url": "https://a.openbible.info/data/cross-references.zip",
        "unzip": "cross_references.txt",
        "license": "CC-BY-4.0 (OpenBible.info)",
    },
    "ancient.jsonl": {
        "url": "https://raw.githubusercontent.com/openbibleinfo/"
               "Bible-Geocoding-Data/main/data/ancient.jsonl",
        "license": "CC-BY-4.0 (OpenBible.info)",
    },
    "modern.jsonl": {
        "url": "https://raw.githubusercontent.com/openbibleinfo/"
               "Bible-Geocoding-Data/main/data/modern.jsonl",
        "license": "CC-BY-4.0 (OpenBible.info)",
    },
    "en_kjv.json": {
        "url": "https://raw.githubusercontent.com/thiagobodruk/bible/"
               "master/json/en_kjv.json",
        "license": "Public domain (KJV text)",
    },
    "geometry.jsonl": {
        "url": "https://raw.githubusercontent.com/openbibleinfo/"
               "Bible-Geocoding-Data/main/data/geometry.jsonl",
        "license": "CC-BY-4.0 (OpenBible.info)",
    },
    # The region and river shapes live in ~1,200 small per-place GeoJSON files.
    # One tarball is far politer than 1,200 requests, and we keep only the
    # geometry we actually draw.
    "geometry/": {
        "url": "https://codeload.github.com/openbibleinfo/"
               "Bible-Geocoding-Data/tar.gz/refs/heads/main",
        "untar": "geometry/",
        "suffix": ".geojson",
        "license": "CC-BY-4.0 (OpenBible.info); geometry incorporates "
                   "OpenStreetMap data under ODbL-1.0",
    },
}

# Six centuries of English rendering, all unambiguously public domain. Wycliffe
# and Tyndale cover only part of the canon; the builder handles the gaps.
TRANSLATIONS = {
    "Wycliffe": "Wycliffe (1395), Middle English",
    "Tyndale": "Tyndale (1526-1530), NT and Pentateuch only",
    "YLT": "Young's Literal Translation (1898)",
    "Darby": "Darby (1890)",
    "ASV": "American Standard Version (1901)",
}
for _code in TRANSLATIONS:
    SOURCES[f"tr_{_code}.json"] = {
        "url": "https://raw.githubusercontent.com/scrollmapper/bible_databases/"
               f"master/formats/json/{_code}.json",
        "license": "Public domain",
    }


def fetch(name, spec, force=False):
    dest = RAW / name.rstrip("/")
    if dest.exists() and not force and (not dest.is_dir() or any(dest.iterdir())):
        if dest.is_dir():
            print(f"  = {name} ({len(list(dest.iterdir()))} files, cached)")
            return dest
        print(f"  = {name} ({dest.stat().st_size / 1e6:.1f} MB, cached)")
        return dest
    print(f"  ↓ {name} from {spec['url']}")
    req = urllib.request.Request(spec["url"], headers=UA)
    with urllib.request.urlopen(req, timeout=120) as r:
        blob = r.read()
    if "unzip" in spec:
        with zipfile.ZipFile(io.BytesIO(blob)) as z:
            blob = z.read(spec["unzip"])
    if "untar" in spec:
        # Pull one directory out of a GitHub tarball, flattening the leading
        # "<repo>-<ref>/" component the archive always carries.
        dest.mkdir(parents=True, exist_ok=True)
        want, suffix, n = spec["untar"], spec.get("suffix", ""), 0
        with tarfile.open(fileobj=io.BytesIO(blob), mode="r:gz") as t:
            for m in t:
                rel = m.name.split("/", 1)[-1]
                if not m.isfile() or not rel.startswith(want) or not rel.endswith(suffix):
                    continue
                src = t.extractfile(m)
                if src is None:
                    continue
                (dest / pathlib.Path(rel).name).write_bytes(src.read())
                n += 1
        print(f"    {len(blob) / 1e6:.1f} MB archive -> {n} files in {dest}/")
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(blob)
    print(f"    {len(blob) / 1e6:.1f} MB  sha256={hashlib.sha256(blob).hexdigest()[:16]}")
    return dest


def main(argv):
    force = "--force" in argv
    RAW.mkdir(parents=True, exist_ok=True)
    print("Fetching sources into data/raw/")
    for name, spec in SOURCES.items():
        try:
            fetch(name, spec, force)
        except Exception as e:  # noqa: BLE001 - report and keep going
            print(f"    !! failed: {e}", file=sys.stderr)
            return 1
    (RAW / "MANIFEST.json").write_text(json.dumps(
        {n: {"url": s["url"], "license": s["license"]} for n, s in SOURCES.items()},
        indent=1) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
