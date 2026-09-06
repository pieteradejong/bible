"""Unit tests for the pure transforms every builder depends on.

These functions decide what the data *says*, as opposed to how much of it there
is. The existing invariant check counts verses; it cannot notice that all 31,100
of them have been quietly corrupted. Two of the functions below shipped exactly
that kind of bug during development, and both bugs are pinned here as tests.

Runs offline: the builders read only data/curated/books.json at import.
"""
import math
import unittest

from tests.helpers import builder


class TestKjvBraceRule(unittest.TestCase):
    """build_text.clean -- translator-supplied words vs. marginal notes.

    The KJV source marks both with braces. Supplied words are real text and must
    be kept in italics; marginal notes are apparatus and must go. The rule is
    that a note always carries a colon and a supplied word never does, verified
    across all 29,393 brace spans in the source.
    """

    def setUp(self):
        self.clean = builder("build_text").clean

    def test_supplied_words_are_kept_as_italics(self):
        self.assertEqual(self.clean("darkness {was} upon"), "darkness <i>was</i> upon")
        self.assertEqual(self.clean("that {it was} good"), "that <i>it was</i> good")

    def test_marginal_notes_are_dropped(self):
        # REGRESSION: 2,261 notes of this exact shape leaked into the verse text
        # and showed up mid-sentence in the quotations view.
        self.assertEqual(
            self.clean("they shall be to me a people {in: or, upon}"),
            "they shall be to me a people",
        )
        self.assertEqual(self.clean("the light {the light from...: Heb. between}"),
                         "the light")
        self.assertEqual(self.clean("a word {Cain: that is, Gotten, or, Acquired}"),
                         "a word")

    def test_hebrew_and_greek_glosses_are_dropped(self):
        for gloss in ("{name: Heb. called}", "{word: Gr. logos}", "{x: Chal. y}"):
            self.assertEqual(self.clean(f"text {gloss}"), "text")

    def test_output_never_retains_brace_markup(self):
        for s in ("{was}", "{a: b}", "plain", "{x} and {y: z}", "{}"):
            with self.subTest(s=s):
                out = self.clean(s)
                self.assertNotIn("{", out)
                self.assertNotIn("}", out)

    def test_whitespace_is_collapsed_not_doubled(self):
        # Removing a note must not leave the gap it occupied behind.
        self.assertEqual(self.clean("a {x: y} b"), "a b")
        self.assertNotIn("  ", self.clean("one {note: here} two"))

    def test_plain_text_is_untouched(self):
        s = "In the beginning God created the heaven and the earth."
        self.assertEqual(self.clean(s), s)


class TestTranslationBookNames(unittest.TestCase):
    """build_translations.canonical -- source book names to the canon table."""

    def setUp(self):
        self.canonical = builder("build_translations").canonical

    def test_roman_numerals_become_arabic(self):
        for src, want in [("I Samuel", "1 Samuel"), ("II Kings", "2 Kings"),
                          ("III John", "3 John"), ("I Chronicles", "1 Chronicles")]:
            with self.subTest(src=src):
                self.assertEqual(self.canonical(src)["name"], want)

    def test_aliases_resolve(self):
        # REGRESSION: "Revelation of John" matched nothing, so every translation
        # silently built 65 books instead of 66.
        self.assertEqual(self.canonical("Revelation of John")["name"], "Revelation")
        self.assertEqual(self.canonical("Song of Songs")["name"], "Song of Solomon")
        self.assertEqual(self.canonical("Acts of the Apostles")["name"], "Acts")

    def test_plain_names_pass_through(self):
        self.assertEqual(self.canonical("Genesis")["osis"], "Gen")
        self.assertEqual(self.canonical("  Malachi  ")["osis"], "Mal")

    def test_deuterocanon_and_junk_return_none(self):
        for src in ("Tobit", "1 Maccabees", "Bel and the Dragon", "", "???"):
            with self.subTest(src=src):
                self.assertIsNone(self.canonical(src))

    def test_every_canon_book_round_trips(self):
        mod = builder("build_translations")
        for b in mod.BOOKS:
            self.assertEqual(self.canonical(b["name"])["osis"], b["osis"])


class TestPlaceNames(unittest.TestCase):
    """build_places.display_name and confidence."""

    def setUp(self):
        self.mod = builder("build_places")

    def test_primary_homonym_loses_its_suffix(self):
        self.assertEqual(self.mod.display_name("Bethel 1"), "Bethel")
        self.assertEqual(self.mod.display_name("Ur 1"), "Ur")

    def test_later_homonyms_are_parenthesised(self):
        self.assertEqual(self.mod.display_name("Bethel 2"), "Bethel (2)")
        self.assertEqual(self.mod.display_name("Antioch 2"), "Antioch (2)")

    def test_unsuffixed_names_are_untouched(self):
        for n in ("Jerusalem", "Sea of Galilee", "En-gedi"):
            with self.subTest(n=n):
                self.assertEqual(self.mod.display_name(n), n)

    def test_display_name_is_idempotent(self):
        # "Bethel (2)" must not be re-parsed into something else.
        once = self.mod.display_name("Bethel 2")
        self.assertEqual(self.mod.display_name(once), once)

    def test_confidence_picks_the_strongest_backed_tag(self):
        c = self.mod.confidence
        self.assertEqual(c({"votes": {"tags": {"confidence_yes": 5}}}), "certain")
        self.assertEqual(c({"votes": {"tags": {"confidence_likely": 3}}}), "likely")
        self.assertEqual(c({"votes": {"tags": {"confidence_possible": 4}}}), "possible")
        self.assertEqual(c({"votes": {"tags": {"confidence_no": 2}}}), "disputed")

    def test_confidence_without_votes_is_unknown(self):
        for ident in ({}, {"votes": {}}, {"votes": {"tags": {}}}):
            with self.subTest(ident=ident):
                self.assertEqual(self.mod.confidence(ident), "unknown")

    def test_a_minority_tag_does_not_win(self):
        # One "yes" among many "possible" should not promote the whole place.
        got = self.mod.confidence(
            {"votes": {"tags": {"confidence_yes": 1, "confidence_possible": 9}}})
        self.assertEqual(got, "possible")


class TestOsisParsing(unittest.TestCase):
    """build_crossrefs.parse -- OSIS references to (book index, chapter, verse)."""

    def setUp(self):
        self.mod = builder("build_crossrefs")

    def test_valid_references(self):
        self.assertEqual(self.mod.parse("Gen.1.1"), (0, 1, 1))
        self.assertEqual(self.mod.parse("Rev.22.21"), (65, 22, 21))
        self.assertEqual(self.mod.parse("1John.5.7")[0], self.mod.IDX["1John"])

    def test_malformed_references_return_none(self):
        for bad in ("Gen.1", "Gen", "Gen.1.1.1", "", "Gen..1", "Gen.a.1",
                    "NotABook.1.1", "gen.1.1"):
            with self.subTest(bad=bad):
                self.assertIsNone(self.mod.parse(bad))

    def test_all_66_books_are_addressable(self):
        self.assertEqual(len(self.mod.IDX), 66)
        for osis, i in self.mod.IDX.items():
            self.assertEqual(self.mod.parse(f"{osis}.1.1"), (i, 1, 1))


class TestQuotationScoring(unittest.TestCase):
    """build_quotations.words and classify."""

    def setUp(self):
        self.mod = builder("build_quotations")

    def test_words_strips_markup_and_punctuation(self):
        self.assertEqual(self.mod.words("And <i>was</i> the light, indeed!"),
                         ["and", "was", "the", "light", "indeed"])

    def test_words_lowercases(self):
        self.assertEqual(self.mod.words("The LORD God"), ["the", "lord", "god"])

    def test_class_boundaries(self):
        c = self.mod.classify
        self.assertEqual(c(run=6, distinct=3, jaccard=0.0), "quotation")
        self.assertEqual(c(run=5, distinct=3, jaccard=0.0), "strong echo")
        self.assertEqual(c(run=4, distinct=2, jaccard=0.0), "strong echo")
        self.assertEqual(c(run=3, distinct=1, jaccard=0.0), "echo")
        self.assertEqual(c(run=1, distinct=0, jaccard=0.40), "echo")
        self.assertEqual(c(run=1, distinct=0, jaccard=0.0), "allusion")

    def test_a_long_run_of_common_words_is_not_a_quotation(self):
        # "and it came to pass that the" is six words of nothing in particular.
        self.assertNotEqual(self.mod.classify(run=6, distinct=0, jaccard=0.0),
                            "quotation")


class TestGeometry(unittest.TestCase):
    """build_geometry -- GeoJSON flattening and Ramer-Douglas-Peucker."""

    def setUp(self):
        self.mod = builder("build_geometry")

    def test_rings_of_handles_every_geometry_type(self):
        r = self.mod.rings_of
        self.assertEqual(r({"type": "LineString", "coordinates": [[0, 0], [1, 1]]}),
                         [[[0, 0], [1, 1]]])
        self.assertEqual(len(r({"type": "Polygon",
                                "coordinates": [[[0, 0], [1, 1], [0, 1], [0, 0]]]})), 1)
        self.assertEqual(len(r({"type": "MultiPolygon",
                                "coordinates": [[[[0, 0]]], [[[1, 1]]]]})), 2)
        self.assertEqual(len(r({"type": "MultiLineString",
                                "coordinates": [[[0, 0]], [[1, 1]]]})), 2)
        self.assertEqual(r({"type": "Point", "coordinates": [0, 0]}), [])
        self.assertEqual(r({}), [])

    def test_rings_of_recurses_into_geometry_collections(self):
        got = self.mod.rings_of({
            "type": "GeometryCollection",
            "geometries": [
                {"type": "LineString", "coordinates": [[0, 0], [1, 1]]},
                {"type": "LineString", "coordinates": [[2, 2], [3, 3]]},
            ]})
        self.assertEqual(len(got), 2)

    def test_first_geometry_unwraps_feature_shapes(self):
        f = self.mod.first_geometry
        geom = {"type": "LineString", "coordinates": [[0, 0]]}
        self.assertEqual(f({"type": "Feature", "geometry": geom}), geom)
        self.assertEqual(f({"type": "FeatureCollection",
                            "features": [{"geometry": geom}]}), geom)
        self.assertEqual(f(geom), geom)
        self.assertIsNone(f({"type": "FeatureCollection", "features": []}))

    def test_simplify_keeps_both_endpoints(self):
        pts = [(0, 0), (1, 0.001), (2, 0), (3, 0.001), (4, 0)]
        out = self.mod.simplify(pts)
        self.assertEqual(out[0], pts[0])
        self.assertEqual(out[-1], pts[-1])

    def test_simplify_drops_collinear_points(self):
        straight = [(x, 0.0) for x in range(20)]
        self.assertEqual(self.mod.simplify(straight), [(0.0, 0.0), (19, 0.0)])

    def test_simplify_preserves_a_real_corner(self):
        # A right angle is the whole point of the shape; it must survive.
        pts = [(0, 0), (1, 0), (2, 0), (2, 1), (2, 2)]
        out = self.mod.simplify(pts, tol=0.01)
        self.assertIn((2, 0), out)

    def test_simplify_is_a_noop_on_short_inputs(self):
        for pts in ([], [(0, 0)], [(0, 0), (1, 1)]):
            with self.subTest(pts=pts):
                self.assertEqual(self.mod.simplify(pts), pts)

    def test_perpendicular_distance(self):
        d = self.mod.perpendicular
        self.assertAlmostEqual(d((0, 1), (0, 0), (2, 0)), 1.0)
        self.assertAlmostEqual(d((1, 0), (0, 0), (2, 0)), 0.0)
        # Degenerate segment: falls back to point distance.
        self.assertAlmostEqual(d((3, 4), (0, 0), (0, 0)), 5.0)
        self.assertFalse(math.isnan(d((0, 0), (1, 1), (1, 1))))


if __name__ == "__main__":
    unittest.main(verbosity=2)
