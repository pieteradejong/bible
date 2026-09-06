"""End-to-end tests: run each builder as a subprocess over a synthetic corpus.

The unit tests cover the transforms; these cover the wiring around them --
argument handling, file layout, the cross-checks builders make against each
other. Builders are invoked exactly as build_all.py invokes them, so nothing
here depends on import tricks.

The fixture corpus is *generated*, not committed: it is derived from
data/curated/books.json, so it can never drift out of step with the canon
table, and it keeps the repo small.
"""
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
BOOKS = json.loads((ROOT / "data/curated/books.json").read_text())


# The curated chronology and genealogy cite verse numbers up to 67, and
# build_timeline.py checks every one against the built text -- so the fixture
# has to be at least that deep or the gate fires on the fixture itself.
VERSES_PER_CHAPTER = 67


def mini_kjv():
    """A structurally valid en_kjv.json: 66 books, real chapter counts.

    build_text.py refuses to run if the book or chapter counts disagree with the
    canon table, so a fixture that cuts corners here would not exercise the code.
    """
    return {"translation": "KJV: fixture", "books": [
        {"name": b["name"], "chapters": [
            {"chapter": c, "verses": [
                {"verse": v,
                 "text": f"{b['name']} {c}:{v} {{was}} written {{note: or, gloss}}"}
                for v in range(1, VERSES_PER_CHAPTER + 1)]}
            for c in range(1, b["chapters"] + 1)]}
        for b in BOOKS
    ]}


def mini_ancient():
    """Two ancient places in the real nested shape build_places.py expects."""
    def rec(pid, name, lon, lat, tags, extra_ident=False):
        idents = [{
            "class": "human",
            "description": name,
            "id": f"m{pid}",
            "id_source": "modern",
            "votes": {"tags": tags},
            "score": {"vote_total": 500, "vote_count": 1, "vote_average": 500},
            "types": ["settlement"],
            "resolutions": [{"class": "human", "land_or_water": "land",
                             "lonlat": f"{lon},{lat}", "type": "settlement"}],
        }]
        if extra_ident:                       # a rival site, so alts > 1
            idents.append({
                "class": "human", "description": "rival", "id": "mzzz",
                "id_source": "modern", "votes": {"tags": {"confidence_possible": 3}},
                "score": {"vote_total": 120, "vote_count": 3, "vote_average": 40},
                "types": ["settlement"],
                "resolutions": [{"class": "human", "land_or_water": "land",
                                 "lonlat": f"{lon + 0.5},{lat + 0.5}",
                                 "type": "settlement"}],
            })
        return {
            "id": pid, "friendly_id": name, "url_slug": name.lower(),
            "types": ["settlement"], "geojson_file": f"{pid}.geojson",
            "identifications": idents,
            "verses": [{"osis": "Gen.1.1"}, {"osis": "Matt.1.1"}],
        }
    return [rec("aaa111", "Testville 1", 35.2, 31.7, {"confidence_yes": 4}),
            rec("bbb222", "Doubtown", 36.0, 32.0, {"confidence_possible": 5}, True)]


def curated_gazetteer():
    """An ancient.jsonl covering every place the curated data actually names.

    build_timeline.py resolves each event place and journey stop against the
    built gazetteer, so the fixture has to contain them -- generated from the
    curated files themselves, so adding a journey stop can never silently
    invalidate this test.
    """
    curated = ROOT / "data/curated"
    names = set()
    for e in json.loads((curated / "events.json").read_text()):
        names.update(e.get("places", []))
    for j in json.loads((curated / "journeys.json").read_text()):
        names.update(s["place"] for s in j["stops"])

    out = []
    for i, name in enumerate(sorted(names)):
        lon, lat = 35.0 + (i % 40) * 0.1, 31.0 + (i % 40) * 0.1
        out.append({
            "id": f"gaz{i:04d}", "friendly_id": name, "url_slug": str(i),
            "types": ["settlement"], "geojson_file": f"gaz{i:04d}.geojson",
            "identifications": [{
                "class": "human", "description": name, "id": f"m{i}",
                "id_source": "modern",
                "votes": {"tags": {"confidence_likely": 2}},
                "score": {"vote_total": 300, "vote_count": 2, "vote_average": 150},
                "types": ["settlement"],
                "resolutions": [{"class": "human", "land_or_water": "land",
                                 "lonlat": f"{lon},{lat}", "type": "settlement"}],
            }],
            "verses": [{"osis": "Gen.1.1"}],
        })
    return out


class BuilderCase(unittest.TestCase):
    """Gives each test an isolated repo-shaped working directory."""

    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp(prefix="bible-test-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        shutil.copytree(ROOT / "scripts", self.tmp / "scripts")
        shutil.copytree(ROOT / "data/curated", self.tmp / "data/curated")
        (self.tmp / "data/raw").mkdir(parents=True)

    def raw(self, name, obj):
        p = self.tmp / "data/raw" / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(obj if isinstance(obj, str) else json.dumps(obj))
        return p

    def run_builder(self, name, expect_ok=True):
        r = subprocess.run([sys.executable, f"scripts/{name}.py"],
                           cwd=self.tmp, capture_output=True, text=True)
        if expect_ok and r.returncode != 0:
            self.fail(f"{name} failed ({r.returncode})\n"
                      f"stdout:\n{r.stdout}\nstderr:\n{r.stderr}")
        return r

    def out(self, rel):
        return json.loads((self.tmp / "web/data" / rel).read_text())


class TestBuildText(BuilderCase):
    def test_splits_into_per_book_files_and_applies_the_brace_rule(self):
        self.raw("en_kjv.json", mini_kjv())
        r = self.run_builder("build_text")
        self.assertIn("66 books", r.stdout)

        gen = self.out("text/Gen.json")
        self.assertEqual(len(gen["chapters"]), 50)
        verse = gen["chapters"][0][0]
        self.assertIn("<i>was</i>", verse)        # supplied word kept
        self.assertNotIn("note", verse)           # marginal note dropped
        self.assertNotIn("{", verse)

        # Every canon book must land, named by OSIS.
        for b in BOOKS:
            self.assertTrue((self.tmp / "web/data/text" / f"{b['osis']}.json").exists(),
                            f"missing {b['osis']}.json")

    def test_refuses_a_source_with_the_wrong_chapter_count(self):
        corpus = mini_kjv()
        corpus["books"][0]["chapters"] = corpus["books"][0]["chapters"][:10]
        self.raw("en_kjv.json", corpus)
        r = self.run_builder("build_text", expect_ok=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("chapters", r.stderr)

    def test_refuses_a_source_with_the_wrong_book_count(self):
        corpus = mini_kjv()
        corpus["books"] = corpus["books"][:40]
        self.raw("en_kjv.json", corpus)
        r = self.run_builder("build_text", expect_ok=False)
        self.assertNotEqual(r.returncode, 0)


class TestBuildCrossrefs(BuilderCase):
    HEADER = "From Verse\tTo Verse\tVotes\n"

    def setUp(self):
        # build_crossrefs validates every reference against the built text, so
        # the text has to exist first -- the same order build_all.py uses.
        super().setUp()
        self.raw("en_kjv.json", mini_kjv())
        self.run_builder("build_text")

    def test_matrix_edges_and_per_book_files(self):
        self.raw("cross_references.txt", self.HEADER + "\n".join([
            "Gen.1.1\tJohn.1.1\t100",
            "Gen.1.1\tPs.148.4-Ps.148.5\t50",      # a range
            "Gen.1.2\tIsa.45.18\t-9",              # a downvoted link
            "Matt.1.1\tGen.5.1\t20",
            "bogus\tGen.1.1\t5",                   # unparseable, must be skipped
            "Gen.1.1\tGen.1.999\t5",               # outside this versification
        ]))
        r = self.run_builder("build_crossrefs")
        self.assertIn("4 parsed", r.stdout)
        self.assertIn("1 unparseable", r.stdout)
        self.assertIn("1 outside this versification", r.stdout)

        mat = self.out("xref_books.json")
        self.assertEqual(mat["total"], 4)
        self.assertEqual(len(mat["counts"]), 66)
        gen, john = 0, 42
        self.assertEqual(mat["counts"][gen][john], 1)

        # A downvoted link is kept but must not add to the weighted total.
        isa = next(i for i, b in enumerate(BOOKS) if b["osis"] == "Isa")
        self.assertEqual(mat["counts"][gen][isa], 1)
        self.assertEqual(mat["weighted"][gen][isa], 0)

        refs = self.out("xref/Gen.json")["refs"]
        self.assertIn("1.1", refs)
        ranged = [x for x in refs["1.1"] if x[3]]          # end verse recorded
        self.assertTrue(ranged, "the verse range lost its end verse")
        self.assertEqual(ranged[0][3], 5)

    def test_references_are_sorted_by_votes(self):
        self.raw("cross_references.txt", self.HEADER + "\n".join([
            "Gen.1.1\tJohn.1.1\t10",
            "Gen.1.1\tPs.33.9\t900",
            "Gen.1.1\tHeb.11.3\t400",
        ]))
        self.run_builder("build_crossrefs")
        votes = [x[4] for x in self.out("xref/Gen.json")["refs"]["1.1"]]
        self.assertEqual(votes, sorted(votes, reverse=True))


class TestBuildPlaces(BuilderCase):
    def test_flattens_places_and_records_rival_sites(self):
        self.raw("ancient.jsonl",
                 "\n".join(json.dumps(r) for r in mini_ancient()) + "\n")
        r = self.run_builder("build_places")
        self.assertIn("2 geolocated", r.stdout)

        places = {p["name"]: p for p in self.out("places.json")}
        self.assertEqual(places["Testville 1"]["disp"], "Testville")
        self.assertEqual(places["Testville 1"]["conf"], "certain")
        self.assertEqual(places["Testville 1"]["alts"], 1)

        # The second place has a rival identification and must say so.
        self.assertEqual(places["Doubtown"]["alts"], 2)
        self.assertLess(places["Doubtown"]["share"], 1.0)
        self.assertEqual(places["Doubtown"]["conf"], "possible")

        # Mentioned in both testaments -> "both".
        self.assertEqual(places["Doubtown"]["t"], "both")
        self.assertEqual(places["Doubtown"]["n"], 2)

        meta = self.out("places_meta.json")
        self.assertEqual(meta["count"], 2)
        self.assertEqual(meta["contested"], 1)


class TestBuildQuotations(BuilderCase):
    def test_scores_only_cross_testament_links(self):
        self.raw("en_kjv.json", mini_kjv())
        self.run_builder("build_text")
        # Overwrite two verses so one pair shares a long distinctive run.
        for osis, ch, vs, text in [
            ("Matt", 1, 1, "the voice of one crying in the wilderness prepare ye the way"),
            ("Isa", 40, 3, "the voice of one crying in the wilderness prepare ye the way"),
        ]:
            p = self.tmp / "web/data/text" / f"{osis}.json"
            d = json.loads(p.read_text())
            d["chapters"][ch - 1][vs - 1] = text
            p.write_text(json.dumps(d))

        self.raw("cross_references.txt", "From Verse\tTo Verse\tVotes\n" + "\n".join([
            "Matt.1.1\tIsa.40.3\t300",     # cross-testament, near-identical
            "Gen.1.1\tExod.1.1\t100",      # same testament: must be ignored
        ]))
        r = self.run_builder("build_quotations")
        q = self.out("quotations.json")
        self.assertEqual(q["scanned"], 1, "same-testament link was not excluded")
        self.assertEqual(len(q["pairs"]), 1)
        pair = q["pairs"][0]
        self.assertEqual(pair["cls"], "quotation")
        self.assertEqual(pair["nt"], "Matt.1.1")
        self.assertEqual(pair["ot"], "Isa.40.3")
        self.assertGreaterEqual(pair["run"], 10)


class TestBuildTimelineValidation(BuilderCase):
    """The curated-data gate: it must refuse anything that does not resolve."""

    def prepare(self):
        self.raw("en_kjv.json", mini_kjv())
        self.run_builder("build_text")
        self.raw("ancient.jsonl",
                 "\n".join(json.dumps(r) for r in curated_gazetteer()) + "\n")
        self.run_builder("build_places")

    def test_accepts_the_real_curated_data(self):
        self.prepare()
        r = self.run_builder("build_timeline")
        self.assertIn("all refs and places resolved", r.stdout)
        self.assertTrue((self.tmp / "web/data/genealogy.json").exists())

    def test_rejects_a_verse_that_does_not_exist(self):
        self.prepare()
        p = self.tmp / "data/curated/events.json"
        p.write_text(p.read_text().replace('"refs":["Gen.1.1"]',
                                           '"refs":["Gen.1.999"]', 1))
        r = self.run_builder("build_timeline", expect_ok=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("Gen.1.999", r.stderr)
        self.assertFalse((self.tmp / "web/data/timeline.json").exists(),
                         "emitted output despite a validation failure")

    def test_rejects_an_unknown_place(self):
        self.prepare()
        p = self.tmp / "data/curated/journeys.json"
        p.write_text(p.read_text().replace('"place":"Haran"',
                                           '"place":"Atlantis"', 1))
        r = self.run_builder("build_timeline", expect_ok=False)
        self.assertIn("Atlantis", r.stderr)

    def test_rejects_a_genealogy_edge_naming_a_missing_person(self):
        self.prepare()
        p = self.tmp / "data/curated/genealogy.json"
        d = json.loads(p.read_text())
        d["edges"].append({"p": "Nobody", "c": "Adam", "ref": "Gen.5.3",
                           "kind": "son", "line": "other"})
        p.write_text(json.dumps(d))
        r = self.run_builder("build_timeline", expect_ok=False)
        self.assertIn("Nobody", r.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
