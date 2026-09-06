# Visualising the Bible

**[View it live →](https://pieteradejong.github.io/bible/)**

[![Build and deploy](https://github.com/pieteradejong/bible/actions/workflows/pages.yml/badge.svg)](https://github.com/pieteradejong/bible/actions/workflows/pages.yml)

Six visualisations of the Protestant canon — Old Testament and New — built from
public-domain text and openly licensed scholarly data:

| View | What it shows |
|---|---|
| **Timeline** (`timeline.html`) | Four thousand years on one zoomable axis: eras, kings, prophets, empires, the life of Jesus, the apostolic age, and when each of the 66 books was written — coloured by how firmly the date is actually known. |
| **Atlas** (`atlas.html`) | Every biblical place that can be put on a map (1,278 of them), sized by how often it is named and coloured by how confident scholarship is about *where* it was, plus eight reconstructed routes. |
| **Cross-references** (`network.html`) | The whole citation web: an arc diagram over all 1,189 chapters, and a 66×66 matrix of which book leans on which. 344,799 links. |
| **Quotations** (`quotations.html`) | Direct quotation separated from loose allusion by measurement rather than assertion: the longest run of words each New Testament verse shares with the Old Testament verse it cites. 314 outright quotations, 4,854 scored pairs. |
| **Genealogy** (`genealogy.html`) | Descent lines as a layered graph — Adam to Abraham, Perez to David, and Matthew's and Luke's irreconcilable genealogies of Jesus running in parallel and giving Joseph two different fathers. |
| **Reader** (`reader.html`) | The text itself with the links live — each verse carries its references in the margin, each place name opens on the map, six centuries of English rendering stack underneath, and a linked verse previews in a side panel without losing your place. |

Everything is static: Python builds JSON, the browser draws it. No server, no
database, no build step for the front end.

## Quick start

```zsh
make data     # download sources, build every derived file into web/data/
make gzip     # optional: pre-compress web/data (32 MB -> 9.1 MB)
make serve    # http://localhost:8000
```

`make data` fetches ~110 MB and takes a couple of minutes. It leaves ~166 MB in
`data/raw/` (mostly the 3,683 per-place GeoJSON files, of which 648 are actually
drawn) and ~41 MB of derived files in `web/data/`. Both are gitignored and
regenerable; `make clean` drops the derived half and keeps the downloads, so a
rebuild needs no network. Neither the downloaded
sources nor the generated files are committed — both are reproducible from this
repo plus a network connection.

```zsh
make refresh  # re-download sources even if cached, then rebuild
make check    # re-run the validators without downloading anything
make gzip     # pre-compress the generated JSON; `make serve` sends it as gzip
make clean    # remove generated files, keep the downloads
```

`make invariants` asserts the headline figures this README quotes (66 books,
1,189 chapters, 31,100 verses, 344,799 cross-references, 1,278 places, 133
people in the genealogy). CI runs it after every build, so an upstream source
that changes shape breaks the build rather than quietly shipping a thinner site.

`make serve` is a small custom server rather than `python -m http.server` for
exactly one reason: it sends the pre-compressed `.json.gz` when the browser
accepts gzip and the `.gz` is current, and falls back to the raw JSON otherwise
— the one behaviour a real static host would give for free.

Requires Python 3.11+ and nothing else. The stdlib does all the work.

---

## The one idea worth stating up front

Most Bible timelines and Bible atlases present every date and every location
with the same flat confidence. That is the wrong picture. The fall of Samaria
is fixed to 722 BCE by Assyrian records; the date of Abraham's migration is a
number arrived at by adding up ages in Genesis. Both appear in the same
chronologies, in the same typeface, with no visible difference.

So **certainty is the primary visual variable here**, not a footnote:

| | Meaning | Examples |
|---|---|---|
| 🟢 **Attested** | Fixed by a source outside the Bible — an inscription, a chronicle, a datable reign | Fall of Samaria (722 BCE); Jehoiachin's deportation, dated to the day by the Babylonian Chronicle; Gallio proconsul of Achaia (51 CE) |
| 🔵 **Conventional** | The date most scholars work with, inferred rather than documented | Solomon's temple; the crucifixion; Paul's journeys |
| 🟠 **Traditional** | Derived from the Bible's own internal chronology, with no external anchor | Everything before the monarchy — creation, the flood, the patriarchs |
| 🔴 **Disputed** | Serious competing proposals exist, and the view names them | The Exodus appears **twice**, at 1446 and at 1260 BCE |

The atlas does the same for space. OpenBible's gazetteer records every modern
site scholars have proposed for each ancient place, with the confidence votes of
the sources that proposed it. **728 of the 1,278 mapped places have more than one
rival site.** The "only places with rival sites" filter turns the map into a
picture of what is genuinely unlocated — which is most of the wilderness
itinerary and a good deal of the conquest.

---

## Data sources

Every third-party file is downloaded by `scripts/fetch_sources.py` into
`data/raw/` (gitignored) and recorded with its URL and license in
`data/raw/MANIFEST.json`. Sizes are as fetched on 2026-09-05.

### Used by this project

| Source | File | Size | License | Used for |
|---|---|---|---|---|
| [OpenBible.info cross-references](https://www.openbible.info/labs/cross-references/) — [download](https://a.openbible.info/data/cross-references.zip) | `cross_references.txt` | 8.3 MB | CC-BY 4.0 | 344,799 verse-to-verse links with reader vote counts. The whole cross-reference view, and the margins in the reader. |
| [openbibleinfo/Bible-Geocoding-Data](https://github.com/openbibleinfo/Bible-Geocoding-Data) — `data/ancient.jsonl` | `ancient.jsonl` | 11.6 MB | CC-BY 4.0 | Every place named in the Bible, each with its proposed modern sites, per-verse mentions, place type, and the confidence votes of 70+ reference works. |
| same repo — `data/modern.jsonl` | `modern.jsonl` | 3.2 MB | CC-BY 4.0 | Modern location records the ancient places resolve to. Fetched for completeness; the atlas currently reads coordinates straight off the resolutions in `ancient.jsonl`. |
| [thiagobodruk/bible](https://github.com/thiagobodruk/bible) — `json/en_kjv.json` | `en_kjv.json` | 4.6 MB | Public domain (KJV) | The full King James text, 31,100 verses. |
| same geocoding repo — `data/geometry.jsonl` | `geometry.jsonl` | 0.2 MB | CC-BY 4.0 | Metadata for the region and river shapes. |
| same geocoding repo — repository tarball, `geometry/` only | `geometry/` | 33 MB archive → 3,683 files | CC-BY 4.0; geometry incorporates OpenStreetMap under ODbL 1.0 | The per-place GeoJSON the atlas draws regions and rivers from. Fetched as one tarball rather than 3,683 requests. |
| [scrollmapper/bible_databases](https://github.com/scrollmapper/bible_databases) — `formats/json/{Wycliffe,Tyndale,Darby,YLT,ASV}.json` | `tr_*.json` | 40 MB total | Public domain | The five comparison translations in the reader. |

Attribution for the two CC-BY datasets is © [OpenBible.info](https://www.openbible.info/),
and is carried in the About page and in `data/raw/MANIFEST.json`. The geocoding
data incorporates OpenStreetMap geometry, licensed [ODbL 1.0](https://opendatacommons.org/licenses/odbl/).

### Front-end dependencies (loaded from CDN, pinned)

| Library | Version | Source | Used by |
|---|---|---|---|
| D3 | 7.9.0 | cdnjs | Timeline, arc diagram, matrix |
| Leaflet | 1.9.4 | cdnjs | Atlas |
| OpenStreetMap standard tiles | — | [tile.openstreetmap.org](https://www.openstreetmap.org/copyright) | Atlas basemap, darkened with a CSS filter; © OpenStreetMap contributors |

Nothing else is loaded. There is no analytics, no tracking, and no outbound call
beyond these.

### Sources evaluated and not used

Recorded so the next person does not re-do the search:

| Source | Why not |
|---|---|
| [`a.openbible.info/data/bible-locations.zip`](https://a.openbible.info/data/bible-locations.zip) | The 2007 geocoding dataset. Returns HTTP 403; superseded by the Bible-Geocoding-Data repo above. |
| [`a.openbible.info/geo/thumbnails.zip`](https://a.openbible.info/geo/thumbnails.zip) | 180 MB of place photographs. Excluded on size; the atlas does not need imagery. |
| [aruljohn/Bible-kjv](https://github.com/aruljohn/Bible-kjv) | KJV as one JSON file per book. Equivalent to the source chosen; the single-file version needed fewer requests. |
| `all.kml` in Bible-Geocoding-Data | A partial KML preview of the same data the per-place GeoJSON gives in full. Redundant once `geometry/` is fetched. |
| CARTO basemap tiles (`basemaps.cartocdn.com`) | Used first, then dropped: the free endpoint now returns tiles stamped "API KEY REQUIRED". OpenStreetMap's own tiles are keyless and are darkened in CSS instead. |
| BBE (Bible in Basic English) | Would have made a sixth comparison translation, but its public-domain status is murkier than the others'. Skipped in favour of editions that are unambiguously free. |

### Hand-authored in this repo

Under `data/curated/`, MIT-licensed code but CC-BY-4.0 content (see *Licensing*).
Compiled from standard reference works — Thiele's regnal chronology for the
kings, the Babylonian Chronicles and Assyrian annals for the attested dates,
mainstream critical consensus for book composition — and **validated on every
build against the actual text and the actual gazetteer**:

| File | Contents |
|---|---|
| `books.json` | The 66-book canon table: OSIS id, name, chapter count, testament, division, composition range. Generated by `scripts/gen_books.py`; 1,189 chapters total, which is the canonical figure. |
| `eras.json` | 14 eras from primeval history to the apostolic age. |
| `events.json` | 94 events, each with certainty, scripture references and place names. |
| `people.json` | 83 figures — every king of Israel and Judah, the writing prophets, the Persian and Roman rulers the text names, the apostolic generation — with reign or life spans. |
| `journeys.json` | 8 routes, 73 stops: Abraham's migration, the Exodus itinerary, the road into exile, the ministry of Jesus, Paul's three journeys, the voyage to Rome. |
| `extra_places.json` | 6 coordinates for sites the Bible does not name but the chronology does — Qumran, Masada, Modein, Delphi, Karnak, Qarqar. |

OpenBible disambiguates homonyms as `Bethel 1`, `Bethel 2`; `data/curated/` and
the journey files use those exact keys, while the views display `Bethel` and
`Bethel (2)`.

---

## How the pipeline works

```
data/raw/            data/curated/           web/data/
(downloaded)         (hand-authored)         (generated, gitignored)
─────────────        ──────────────          ────────────────────────
en_kjv.json ──────────────────────────────▶  text/<OSIS>.json      66 files, 4.3 MB
cross_references.txt ─────────────────────▶  xref_books.json       66×66 matrix
                                          ▶  xref_chapters.json    191,620 edges
                                          ▶  xref/<OSIS>.json      verse-level, 66 files
ancient.jsonl ────────────────────────────▶  places.json           1,278 places
                                          ▶  places_verses.json    place → verses
                                          ▶  places_meta.json      legend tallies
                     books.json ──┐
                     eras.json    ├───────▶  timeline.json
                     events.json  │
                     people.json ─┘
                     journeys.json ───────▶  journeys.json
                     extra_places.json ─┘
```

`scripts/build_all.py` runs the steps in dependency order. The timeline builder
runs **last on purpose**: it validates the hand-authored data against everything
the other builders produced.

### The validation step is the point

Hand-authoring a chronology guarantees typos, and a typo in a scripture
reference is invisible — `2Kgs.25.9` and `2Kgs.25.90` look equally plausible.
So `scripts/build_timeline.py` refuses to emit anything unless:

- every scripture reference names a verse that **actually exists** in the built
  KJV text (right book, chapter within the book, verse within the chapter);
- every place named by an event or a journey stop **resolves** in the gazetteer;
- no two entries share an id, and no span ends before it starts.

The same check runs over the genealogy: every person's references, every edge's
reference, and every edge endpoint must name a person who exists.

It caught five real errors on its first run, including a duplicate id and four
place names that do not exist in OpenBible's gazetteer under the spelling I
used. A build that passes prints:

```
genealogy: 133 people, 134 edges, all refs resolved
timeline: 14 eras, 94 events, 83 people, 8 journeys (73 stops), all refs and places resolved
```

`scripts/build_text.py` and `scripts/gen_books.py` cross-check each other the
same way: the text builder fails if any book's chapter count disagrees with the
canon table.

---

## The views in detail

### Timeline

A single zoomable axis from 4004 BCE to 1611 CE. Rows are packed greedily so
nothing overlaps, and each row group can be toggled: eras, narrative events, the
patriarchs, the kings, the prophets, Israel and Judah, foreign rulers, empires
and wars, Jesus and the church, text and canon, and the composition window of
each of the 66 books.

Scroll to zoom, drag to pan. Filtering by certainty is the interesting move:
switch off *traditional* and everything before roughly 1000 BCE disappears, which
is a fair picture of what is externally documented.

Clicking anything loads its scripture references **with the verse text inline**,
and its places link straight through to the atlas.

### Atlas

Leaflet, dark CARTO basemap. Marker area scales with mention count (Jerusalem is
named in 955 verses; most places appear once). Colour is confidence in the
identification, derived from the confidence tags each scholarly source attached.

Filters: testament, specific book, place type (settlement, region, mountain,
wadi, gate, well, …), minimum mentions, and *only places with rival sites*.

Routes draw as numbered stops; a disputed route (the Exodus) draws dashed.
Clicking a place lists every verse that names it, links each one into the
reader, and — where scholarship disagrees — says how many rival sites have been
proposed and what share of the vote the drawn one carries.

### Cross-references

Two modes.

**Arc diagram**: all 1,189 chapters laid left to right in canonical order along
the bottom, one arc per chapter pair that readers have linked. Rendered to
canvas with additive blending, so density reads as brightness. Hovering the
strip lights up one chapter's links — outgoing in warm white, incoming in blue.

**Book matrix**: 66×66, rows referring, columns referred to, log-scaled. The
bottom-left quadrant — New Testament citing Old — is the striking one.

Of the 344,799 links: 54.3% stay inside the Old Testament, 24.5% inside the New,
12.5% run Old→New and 8.8% New→Old. The most-referenced books are Psalms
(33,983 incoming), Isaiah (24,048), Jeremiah (17,397), Matthew (14,785) and Acts
(13,761).

Both honour the direction filter (Old→Old, Old→New, New→Old, New→New) and a
minimum-weight slider. Clicking a chapter lists its references verse by verse,
ordered by how many readers voted for each link.

### Reader

Book and chapter selectors, or arrive by deep link: `reader.html#Rom.5.12`.
Each verse shows its top references in the margin (1–20, adjustable); hovering
one previews the target verse in context in the right panel; clicking navigates
to it. Places named in the chapter are listed in the sidebar and link to the
atlas.

Translator-supplied words — the ones the KJV sets in italics — are preserved as
`<i>`; the marginal Hebrew and Greek glosses that share the same brace notation
in the source are stripped.

---

## How it is deployed

`.github/workflows/pages.yml` runs on every push to `main`: it fetches the
sources (cached weekly), runs the full build, checks the invariants, and
publishes `web/` to GitHub Pages. Because `build_timeline.py` runs last and
refuses to emit anything when a curated reference does not resolve, **a
validation failure blocks the deploy** — the site can only go live from data
that passed every check. Pull requests get the build and the checks but do not
deploy.

The pre-compressed `.json.gz` files are dropped from the Pages artifact; Pages
compresses on the fly, so they only matter to `make serve` locally.

## Repository layout

```
.
├── Makefile                  data / refresh / serve / check / clean
├── README.md
├── CLAUDE.md                 notes for AI coding assistants
├── LICENSE                   MIT, for the code
├── LICENSE-DATA              CC-BY-4.0, for data/curated/
├── data/
│   ├── raw/                  downloaded sources (gitignored)
│   └── curated/              hand-authored chronology, genealogy, journeys, canon
├── scripts/
│   ├── fetch_sources.py      download, unzip, untar into data/raw/
│   ├── gen_books.py          emit the 66-book canon table
│   ├── gen_genealogy.py      emit the descent graph
│   ├── build_text.py         KJV → per-book JSON
│   ├── build_crossrefs.py    344k references → matrix, edges, per-book files
│   ├── build_places.py       ancient.jsonl → atlas dataset
│   ├── build_geometry.py     100 MB of GeoJSON → 0.5 MB of drawable shapes
│   ├── build_translations.py five comparison editions → per-book JSON
│   ├── build_quotations.py   score every cross-testament link for word overlap
│   ├── build_timeline.py     merge + VALIDATE all curated data
│   ├── build_all.py          run everything in order
│   ├── gzip_data.py          pre-compress web/data (32 MB → 9.1 MB)
│   └── serve.py              static server that sends the .gz
└── web/
    ├── index.html            about, live counts, colour key
    ├── timeline.html  atlas.html  network.html
    ├── quotations.html  genealogy.html  reader.html
    ├── css/app.css
    ├── js/
    │   ├── common.js         loading, OSIS parsing, tooltips, nav shell
    │   └── timeline.js  atlas.js  network.js  quotations.js
    │       genealogy.js  reader.js
    └── data/                 generated (gitignored)
```

---

## Known limits

- **The chronology is one reading among several.** Dates before the monarchy are
  traditional by construction; the regnal dates follow Thiele, whose harmonisation
  of the synchronisms is standard but not unanimous. The certainty colours are
  there so you can see which is which, not to settle anything.
- **Book composition dates follow mainstream critical scholarship**, which many
  readers reject on principle. They are shown as ranges, in their own togglable
  row, and are used nowhere else.
- **Journey routes are reconstructions.** Numbers 33 lists 42 stages of the
  wilderness itinerary; most cannot be located, and the atlas draws only the
  identifiable points. The line between two stops is a straight line, not a road.
- **Cross-references are crowd-sourced**, from OpenBible's users. Vote counts are
  exposed everywhere so you can weigh them. 1,242 links carry negative votes;
  they are kept, because "readers rejected this link" is itself information.
- **The gazetteer is Protestant-canon only.** Deuterocanonical places, and places
  named only in 1 Maccabees (Modein, for instance), are absent unless added to
  `extra_places.json` by hand.
- **The atlas uses OpenStreetMap's public tile servers.** Their [tile usage
  policy](https://operations.osmfoundation.org/policies/tiles/) discourages
  third-party apps at volume. At personal traffic this is unremarkable, but if
  this ever drew real traffic the fix is a provider that permits it, or
  self-hosted tiles.
- **Verified headless, not by hand.** Every page was rendered in headless
  Chromium during development and checked for JS errors and expected output
  (257 timeline items, 1,278 atlas markers plus 73 route stops, 181,533 arcs,
  Genesis 1 with its 426 outgoing references). Nobody has clicked through it
  interactively — zoom, drag, hover and the map's tile loading are unexercised.
  Report anything that looks wrong.

## Ideas not yet built

- **Verse-level geometry**: shapes are attached to places, not to the verses that
  name them, so the atlas cannot yet shade "everywhere Amos mentions".
- **Hebrew and Greek**: every text here is English. Quotation scoring in
  particular would be far better against the Septuagint and the Masoretic Text
  than against two English translations of them.
- **Deuterocanon**: the gazetteer, cross-references and canon table are all
  Protestant-canon only. Adding the deuterocanonical books would touch every
  builder.
- **Chronological uncertainty as a distribution** rather than a label: an event
  dated "somewhere between 1446 and 1260" could be drawn as a gradient instead
  of two discrete bars.

## Licensing

This repository is split, because it holds two different kinds of thing:

- **Code** — `scripts/`, `web/js/`, `web/css/`, the HTML, the Makefile and the
  workflow: **MIT**, see `LICENSE`.
- **Curated data** — everything under `data/curated/`: the canon table, eras,
  events, people, journeys, genealogy and supplemental coordinates:
  **CC-BY-4.0**, see `LICENSE-DATA`. It is editorial content rather than code,
  and attribution is the point of it.
- **Downloaded sources** — whatever `scripts/fetch_sources.py` pulls into
  `data/raw/`: each keeps its own licence and none of it is redistributed here.
  See *Data sources* above. In short: OpenBible.info's cross-references and
  geocoding data are CC-BY-4.0 (their geometry incorporates OpenStreetMap under
  ODbL-1.0), and the six translations are public domain.

`LICENSE` deliberately contains the MIT text and nothing else, with no
explanatory preamble — GitHub's licence detector gives up on a file that carries
extra prose, and having the repo plainly labelled MIT is worth more than a note
that only someone opening the file would read. This paragraph is that note.
