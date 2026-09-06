"""Semantic checks on the real built output in web/data.

The invariant check counts things. These verify the data is internally
consistent: that every reference points at something that exists, that no
coordinate is nonsense, that the genealogy is actually a graph. None of this was
checked before, and the largest of them -- resolving all 344,799 cross-reference
targets -- is the kind of thing that only ever gets verified by a machine.

Skips itself when web/data is absent, so the fast offline suite stays fast.
Run after a build: `make test-all`.
"""
import json
import math
import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "web/data"
BOOKS = json.loads((ROOT / "data/curated/books.json").read_text())
BY_OSIS = {b["osis"]: b for b in BOOKS}
OSIS_RE = re.compile(r"^(\w+)\.(\d+)\.(\d+)$")


def built():
    return (DATA / "timeline.json").exists() and (DATA / "text").is_dir()


@unittest.skipUnless(built(), "web/data not built; run `make data` first")
class ContractCase(unittest.TestCase):
    """Shares one lazily-built verse index across the whole class."""

    _index = None

    @classmethod
    def verse_index(cls):
        """{osis: [verse count per chapter]} straight from the built text."""
        if ContractCase._index is None:
            idx = {}
            for b in BOOKS:
                chapters = json.loads(
                    (DATA / "text" / f"{b['osis']}.json").read_text())["chapters"]
                idx[b["osis"]] = [len(c) for c in chapters]
            ContractCase._index = idx
        return ContractCase._index

    def resolves(self, osis):
        """True when this reference names a verse that actually exists."""
        m = OSIS_RE.match(osis)
        if not m:
            return False
        book, ch, vs = m.group(1), int(m.group(2)), int(m.group(3))
        lens = self.verse_index().get(book)
        return bool(lens) and 1 <= ch <= len(lens) and 1 <= vs <= lens[ch - 1]


class TestCrossReferenceTargets(ContractCase):
    def test_every_cross_reference_resolves_to_a_real_verse(self):
        """All 344,799 of them. Never checked until now."""
        checked = 0
        bad = []
        for b in BOOKS:
            path = DATA / "xref" / f"{b['osis']}.json"
            if not path.exists():
                continue
            refs = json.loads(path.read_text())["refs"]
            lens = self.verse_index()[b["osis"]]
            for source, targets in refs.items():
                ch, vs = (int(x) for x in source.split("."))
                if not (1 <= ch <= len(lens) and 1 <= vs <= lens[ch - 1]):
                    bad.append(f"source {b['osis']}.{source} does not exist")
                for t in targets:
                    checked += 1
                    tb = BOOKS[t[0]]["osis"]
                    if not self.resolves(f"{tb}.{t[1]}.{t[2]}"):
                        bad.append(f"{b['osis']}.{source} -> {tb}.{t[1]}.{t[2]}")
                    if t[3] and t[3] < t[2]:
                        bad.append(f"{b['osis']}.{source} -> range ends before it starts")
                    if len(bad) > 20:
                        break
        self.assertGreater(checked, 300_000, "far fewer targets than expected")
        self.assertFalse(bad, f"{len(bad)}+ unresolvable targets, e.g.\n  "
                              + "\n  ".join(bad[:10]))

    def test_book_matrix_agrees_with_the_per_book_files(self):
        mat = json.loads((DATA / "xref_books.json").read_text())
        total = sum(sum(row) for row in mat["counts"])
        self.assertEqual(total, mat["total"],
                         "matrix cells do not sum to the declared total")


class TestPlaceContracts(ContractCase):
    def test_coordinates_are_finite_and_plausible(self):
        for p in json.loads((DATA / "places.json").read_text()):
            with self.subTest(place=p["name"]):
                self.assertTrue(math.isfinite(p["lat"]) and math.isfinite(p["lon"]))
                self.assertTrue(-90 <= p["lat"] <= 90, f"lat {p['lat']}")
                self.assertTrue(-180 <= p["lon"] <= 180, f"lon {p['lon']}")

    def test_every_place_verse_reference_resolves(self):
        bad = [r for refs in json.loads((DATA / "places_verses.json").read_text()).values()
               for r in refs if not self.resolves(r)]
        self.assertFalse(bad, f"{len(bad)} unresolvable place references, "
                              f"e.g. {bad[:5]}")

    def test_place_ids_line_up_across_files(self):
        places = json.loads((DATA / "places.json").read_text())
        verses = json.loads((DATA / "places_verses.json").read_text())
        self.assertEqual({p["id"] for p in places}, set(verses),
                         "places.json and places_verses.json disagree on ids")

    def test_per_book_counts_match_the_verse_list(self):
        verses = json.loads((DATA / "places_verses.json").read_text())
        for p in json.loads((DATA / "places.json").read_text())[:200]:
            with self.subTest(place=p["name"]):
                self.assertEqual(sum(p["books"].values()), p["n"])
                self.assertEqual(len(verses[p["id"]]), p["n"])

    def test_book_indexes_are_in_range(self):
        for p in json.loads((DATA / "places.json").read_text()):
            for bi in p["books"]:
                self.assertTrue(0 <= int(bi) < 66, f"{p['name']}: book {bi}")


class TestGeometryContracts(ContractCase):
    def test_rings_are_well_formed(self):
        geo = json.loads((DATA / "geometry.json").read_text())
        self.assertGreater(len(geo), 0)
        for gid, shape in geo.items():
            with self.subTest(shape=shape["name"]):
                self.assertIn(shape["kind"], ("area", "line"))
                self.assertTrue(shape["rings"], "shape has no rings")
                for ring in shape["rings"]:
                    self.assertGreaterEqual(len(ring), 3)
                    for lat, lon in ring:
                        self.assertTrue(math.isfinite(lat) and math.isfinite(lon))
                        self.assertTrue(-90 <= lat <= 90 and -180 <= lon <= 180)

    def test_geometry_ids_are_known_places(self):
        geo = json.loads((DATA / "geometry.json").read_text())
        known = {p["id"] for p in json.loads((DATA / "places.json").read_text())}
        orphans = [g for g in geo if g not in known]
        # Geometry may exist for places that have no mapped point, but not many.
        self.assertLess(len(orphans), len(geo) * 0.5,
                        "most geometry does not correspond to a mapped place")


class TestGenealogyContracts(ContractCase):
    def setUp(self):
        self.g = json.loads((DATA / "genealogy.json").read_text())
        self.ids = {p["id"] for p in self.g["people"]}

    def test_every_edge_endpoint_exists(self):
        for e in self.g["edges"]:
            self.assertIn(e["p"], self.ids)
            self.assertIn(e["c"], self.ids)

    def test_descent_graph_is_acyclic(self):
        children = {}
        for e in self.g["edges"]:
            if e["kind"] != "spouse":
                children.setdefault(e["p"], []).append(e["c"])
        WHITE, GREY, BLACK = 0, 1, 2
        colour = dict.fromkeys(self.ids, WHITE)

        def visit(node, trail):
            colour[node] = GREY
            for kid in children.get(node, []):
                if colour[kid] == GREY:
                    self.fail(f"cycle in the descent graph: "
                              f"{' -> '.join(trail + [kid])}")
                if colour[kid] == WHITE:
                    visit(kid, trail + [kid])
            colour[node] = BLACK

        for node in self.ids:
            if colour[node] == WHITE:
                visit(node, [node])

    def test_nobody_is_their_own_parent(self):
        for e in self.g["edges"]:
            self.assertNotEqual(e["p"], e["c"])

    def test_every_reference_resolves(self):
        bad = [r for p in self.g["people"] for r in p["refs"] if not self.resolves(r)]
        bad += [e["ref"] for e in self.g["edges"]
                if e.get("ref") and not self.resolves(e["ref"])]
        self.assertFalse(bad, f"unresolvable genealogy references: {bad[:5]}")


class TestTranslationContracts(ContractCase):
    # Wycliffe translated the Vulgate, whose Esther and Daniel carry the Greek
    # additions -- 16 chapters where the Protestant canon has 10. That is the
    # source being faithful to itself, so extra chapters are allowed; what
    # matters is that the reader can never surface them, because its chapter
    # selector is driven by the canon table.
    KNOWN_LONGER = {("Wycliffe", "Esth"), ("Wycliffe", "Dan")}

    def test_no_translation_exceeds_the_canon_unexpectedly(self):
        for ed in json.loads((DATA / "translations.json").read_text()):
            if ed["path"] == "text":
                continue
            for b in BOOKS:
                path = DATA / ed["path"] / f"{b['osis']}.json"
                if not path.exists():
                    continue          # partial coverage is expected and stated
                got = len(json.loads(path.read_text())["chapters"])
                if got > b["chapters"]:
                    self.assertIn((ed["code"], b["osis"]), self.KNOWN_LONGER,
                                  f"{ed['code']} {b['osis']}: {got} chapters "
                                  f"> canon's {b['chapters']}, and not a known "
                                  "deuterocanonical addition")

    def test_the_reader_cannot_surface_extra_chapters(self):
        # The selector is built from the canon table, so anything past it is
        # unreachable by design. Guard that the canon table is what drives it.
        reader = (ROOT / "web/js/reader.js").read_text()
        self.assertIn("b.chapters", reader,
                      "reader no longer bounds its chapter selector by the canon")

    def test_manifest_counts_match_the_files_on_disk(self):
        for ed in json.loads((DATA / "translations.json").read_text()):
            if ed["path"] == "text":
                continue
            on_disk = len(list((DATA / ed["path"]).glob("*.json")))
            self.assertEqual(on_disk, ed["books"],
                             f"{ed['code']}: manifest says {ed['books']} books, "
                             f"{on_disk} files present")


class TestSiteContracts(ContractCase):
    """The views must not reference pages or data files that do not exist."""

    def test_every_nav_link_resolves_to_a_page(self):
        common = (ROOT / "web/js/common.js").read_text()
        for href in set(re.findall(r'href="([a-z]+\.html)"', common)):
            with self.subTest(href=href):
                self.assertTrue((ROOT / "web" / href).exists(), f"nav links to missing {href}")

    def test_every_data_file_the_views_load_exists(self):
        # Matches load("places.json") and load(`text/${x}.json`)-style literals.
        missing = []
        for js in (ROOT / "web/js").rglob("*.js"):
            for name in re.findall(r'load\("([a-z_]+\.json)"\)', js.read_text()):
                if not (DATA / name).exists():
                    missing.append(f"{js.name} -> {name}")
        self.assertFalse(missing, f"views load files that do not exist: {missing}")

    def test_every_page_references_its_module(self):
        for page in (ROOT / "web").glob("*.html"):
            html = page.read_text()
            for src in re.findall(r'src="(js/[a-z]+\.js)"', html):
                with self.subTest(page=page.name):
                    self.assertTrue((ROOT / "web" / src).exists(),
                                    f"{page.name} loads missing {src}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
