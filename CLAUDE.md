# CLAUDE.md

Guidance for AI coding assistants working in this repository.

## Overview

Seven static visualisations of the Protestant biblical canon — a zoomable
chronology, a Leaflet atlas, a cross-reference arc diagram/matrix, a measured
quotation-vs-allusion view, a genealogy graph, and a reader with live links and
six centuries of English translations. Python builds JSON from downloaded
sources plus hand-authored data; the browser draws it. No framework, no bundler,
no server-side code.

## Commands

```zsh
make data      # fetch sources into data/raw/, rebuild everything in web/data/
make refresh   # same, but re-download even if cached
make test      # fast suite: units, properties, pipeline, JS. Offline, ~5s
make test-all  # adds contract tests over real output, invariants, page smoke
make gzip      # pre-compress web/data (32 MB -> 9.1 MB)
make serve     # static server on :8000 (PORT=xxxx to change)
make check     # re-run the curated-data validators only (fast, no network)
make clean     # drop generated files, keep downloads
```

Python 3.11+ and Node 18+, both stdlib only -- `unittest` and `node:test`. There
is nothing to install; `package.json` exists only to declare ES modules and wire
`node --test`. `make test` must pass before anything is pushed.

## Architecture

- `data/raw/` — downloaded, gitignored. Written only by `scripts/fetch_sources.py`.
- `data/curated/` — hand-authored and **committed**: the canon table, eras,
  events, people, journeys, extra place coordinates.
- `scripts/build_*.py` — one builder per output family; `build_all.py` runs them
  in dependency order. `build_timeline.py` runs **last on purpose** because it
  validates the curated data against the outputs of every other builder.
- `web/data/` — generated, gitignored. Per-book files (`text/<OSIS>.json`,
  `xref/<OSIS>.json`) are loaded on demand; everything else loads up front.
- `web/js/common.js` — the only shared module: cached `load()`, OSIS parsing,
  tooltip, the nav shell. Each view is a single ES module with top-level await.

Books are keyed by **OSIS abbreviation** (`Gen`, `1Kgs`, `Phlm`, `Rev`)
everywhere — that is what OpenBible's data uses. Book *indexes* (0-65) are used
inside the compact generated arrays.

## Testing

Seven layers, described in the README. The standard is not coverage but *would
this have caught what we actually got wrong* -- every layer pins a defect that
really shipped. Two rules learned the hard way:

- **A test that cannot fail is worse than no test.** Two were written here that
  passed against a deliberately broken implementation: a `simplify` check whose
  second clause was always true, and an `alphaFor` monotonicity check that a
  constant satisfied. After writing a test, break the code and confirm it fails.
- **Unit tests cannot see wiring.** The `esc` re-export bug broke every page and
  no unit test could have caught it, because each module was individually
  correct. `tests/smoke.py` caught it immediately. Keep the smoke layer.

## Gotchas

- **Never loosen the validation in `build_timeline.py`.** It exists because
  hand-authored scripture references fail silently otherwise. If it rejects your
  edit, the edit is wrong, not the validator.
- **Place keys carry disambiguation suffixes.** OpenBible names homonyms
  `Bethel 1`, `Bethel 2`. `data/curated/` must use those exact strings; the
  views show `p.disp` (`Bethel`, `Bethel (2)`). Don't "clean up" the keys.
- **Certainty is the point, not decoration.** Every dated or located thing
  carries `attested` / `conventional` / `traditional` / `disputed`, and the
  views colour by it. Adding an entry without an honest certainty grade defeats
  the project.
- **`web/data/` is gitignored on purpose** — 12 MB of derived files. Anything
  that must survive a clone belongs in `data/curated/` or a build script.
- The cross-reference `To Verse` column may be a range (`Ps.148.4-Ps.148.5`);
  88,150 of the 344,799 rows are. The parser keeps the start verse and records
  the end verse only when the range stays inside one chapter.
- **Curated data must be emitted by a builder, not read from `data/curated/`.**
  The genealogy view broke exactly once because `gen_genealogy.py` wrote only to
  `data/curated/` while the browser loads from `web/data/`. `build_timeline.py`
  now validates and copies it across.
- **Anything additive on canvas needs alpha scaled to the number of marks.**
  The arc diagram at 190,000 arcs saturated to solid white; `alphaFor()` derives
  the per-arc alpha from the count actually drawn.
- **The timeline repacks rows on every render, not once.** A label needs a fixed
  number of pixels, which is a different number of *years* at each zoom level;
  packing in year units makes labels collide at every zoom but one.
- **`body` is the flex column**, not a wrapper element — the nav shell appends
  `<header>` and `<main>` straight into it, so a `.app` wrapper would never
  exist and `<main>` would collapse to content height.
- KJV brace spans: a colon means marginal note (drop it), no colon means a
  translator-supplied word (keep it, italicised). The current source carries no
  such markup -- `clean()` is kept as the guard in case one ever does.
- **The base text is scrollmapper's KJV, not thiagobodruk's.** The latter has
  the italic markup but is missing Matthew 2:16 and splits Revelation 12 into 18
  verses, which misnumbers everything after. Correct text beat pretty text. All
  six translations now come from one source.
- **Versification differs between traditions.** OpenBible cites 3 John 1:15,
  which the KJV does not have. `build_crossrefs.py` validates every reference
  against the built text and drops what cannot resolve, so nothing downstream
  ever links to a verse that is not there.
- **A JS re-export does not create a local binding.** `export { esc } from "..."`
  makes `esc` available to importers but *not* to the module's own code. This
  broke every page once.
- **A cached source is only valid if its URL has not changed.** `fetch_sources.py`
  records what each file came from and re-downloads on a mismatch; the CI cache
  has no restore-keys for the same reason.
- Tyndale and Wycliffe ship *padded with empty strings* for books they never
  covered. Count real text, never slots, or Tyndale looks like a complete Bible.
- Front-end libraries load from cdnjs at pinned versions and the basemap tiles
  come from OpenStreetMap (CARTO's free endpoint now demands an API key and
  stamps every tile). That is the complete list of outbound calls; keep it so.
