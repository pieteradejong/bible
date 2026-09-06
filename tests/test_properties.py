"""Property tests: invariants that must hold for *any* input, not just examples.

Hand-rolled on seeded `random` rather than Hypothesis, to keep the repo
dependency-free. That costs us shrinking, so when a property fails the harness
prints the seed and the offending input -- paste those into a unit test in
test_transforms.py to pin the case permanently.

Seeds are fixed, so a failure here is reproducible rather than a flake.
"""
import random
import string
import unittest

from tests.helpers import builder

SEEDS = (1, 7, 42, 1611, 20260906)
CASES = 200


def rng(seed):
    return random.Random(seed)


class PropertyCase(unittest.TestCase):
    """Adds a failure message that always carries the seed and the input."""

    def check(self, seed, value, condition, why):
        if not condition:
            self.fail(f"property failed [seed={seed}]\n  input: {value!r}\n  {why}")


class TestSimplifyProperties(PropertyCase):
    """Ramer-Douglas-Peucker must never invent or reorder geometry."""

    def setUp(self):
        self.mod = builder("build_geometry")

    def path(self, r, n=None):
        n = n or r.randint(3, 60)
        return [(round(r.uniform(-180, 180), 5), round(r.uniform(-85, 85), 5))
                for _ in range(n)]

    def test_output_is_a_subsequence_of_the_input(self):
        # The strongest guarantee: simplification only ever *removes* points.
        for seed in SEEDS:
            r = rng(seed)
            for _ in range(CASES):
                pts = self.path(r)
                out = self.mod.simplify(pts, tol=r.choice([0.0001, 0.01, 1, 10]))
                it = iter(pts)
                self.check(seed, pts, all(p in it for p in out),
                           "output is not a subsequence of the input")

    def test_endpoints_always_survive(self):
        for seed in SEEDS:
            r = rng(seed)
            for _ in range(CASES):
                pts = self.path(r)
                out = self.mod.simplify(pts, tol=r.uniform(0, 20))
                self.check(seed, pts, out[0] == pts[0] and out[-1] == pts[-1],
                           f"endpoints changed: {out[0]} .. {out[-1]}")

    def test_never_grows(self):
        for seed in SEEDS:
            r = rng(seed)
            for _ in range(CASES):
                pts = self.path(r)
                out = self.mod.simplify(pts, tol=r.uniform(0, 20))
                self.check(seed, pts, len(out) <= len(pts),
                           f"grew from {len(pts)} to {len(out)} points")

    def test_is_stable_under_reapplication(self):
        # Simplifying an already-simplified path at the same tolerance is a no-op.
        for seed in SEEDS:
            r = rng(seed)
            for _ in range(CASES // 2):
                pts, tol = self.path(r), r.choice([0.01, 0.5, 5])
                once = self.mod.simplify(pts, tol=tol)
                self.check(seed, pts, self.mod.simplify(once, tol=tol) == once,
                           "second pass changed the result")

    def test_zero_tolerance_keeps_every_corner(self):
        # At tolerance 0 only exactly-collinear points may be dropped, and random
        # coordinates are never exactly collinear -- so nothing should be lost.
        for seed in SEEDS:
            r = rng(seed)
            for _ in range(50):
                pts = self.path(r, n=r.randint(3, 25))
                if len(set(pts)) != len(pts):
                    continue                 # duplicates are legitimately droppable
                out = self.mod.simplify(pts, tol=0.0)
                self.check(seed, pts, len(out) == len(pts),
                           f"zero tolerance dropped {len(pts) - len(out)} genuine "
                           f"corner(s): {len(pts)} -> {len(out)}")

    def test_never_raises_on_degenerate_paths(self):
        degenerate = [
            [], [(0, 0)], [(0, 0), (0, 0)], [(0, 0)] * 40,
            [(1e-9, 1e-9), (0, 0), (1e-9, 0)],
            [(180, 85), (-180, -85)] * 5,
        ]
        for pts in degenerate:
            with self.subTest(pts=pts[:3]):
                self.mod.simplify(pts)


class TestCleanProperties(PropertyCase):
    """No input should let brace markup or a marginal note reach the reader."""

    def setUp(self):
        self.clean = builder("build_text").clean

    def text(self, r):
        words = ["the", "lord", "said", "unto", "moses", "was", "is", "and"]
        parts = []
        for _ in range(r.randint(1, 12)):
            roll = r.random()
            if roll < 0.2:                       # a supplied word
                parts.append("{" + r.choice(words) + "}")
            elif roll < 0.4:                     # a marginal note
                parts.append("{" + r.choice(words) + ": or, " + r.choice(words) + "}")
            else:
                parts.append(r.choice(words))
        return " ".join(parts)

    def test_never_leaks_braces_or_notes(self):
        for seed in SEEDS:
            r = rng(seed)
            for _ in range(CASES):
                s = self.text(r)
                out = self.clean(s)
                self.check(seed, s, "{" not in out and "}" not in out,
                           f"brace survived: {out!r}")
                self.check(seed, s, ": or," not in out,
                           f"marginal note survived: {out!r}")

    def test_never_leaves_double_spaces(self):
        for seed in SEEDS:
            r = rng(seed)
            for _ in range(CASES):
                s = self.text(r)
                self.check(seed, s, "  " not in self.clean(s), "double space left behind")

    def test_never_raises_on_arbitrary_text(self):
        r = rng(99)
        alphabet = string.printable
        for _ in range(400):
            s = "".join(r.choice(alphabet) for _ in range(r.randint(0, 60)))
            try:
                self.clean(s)
            except Exception as e:                       # noqa: BLE001
                self.fail(f"clean() raised {type(e).__name__} on {s!r}")


class TestParsingProperties(PropertyCase):
    """Reference parsing and book-name normalisation must be total and stable."""

    def setUp(self):
        self.xref = builder("build_crossrefs")
        self.tr = builder("build_translations")
        self.places = builder("build_places")

    def test_parse_round_trips_every_valid_reference(self):
        r = rng(3)
        osis = list(self.xref.IDX)
        for _ in range(600):
            book = r.choice(osis)
            ch, vs = r.randint(1, 150), r.randint(1, 176)
            got = self.xref.parse(f"{book}.{ch}.{vs}")
            self.check(3, f"{book}.{ch}.{vs}", got == (self.xref.IDX[book], ch, vs),
                       f"got {got}")

    def test_parse_never_raises(self):
        r = rng(11)
        for _ in range(600):
            s = "".join(r.choice(string.printable) for _ in range(r.randint(0, 24)))
            try:
                self.xref.parse(s)
            except Exception as e:                       # noqa: BLE001
                self.fail(f"parse() raised {type(e).__name__} on {s!r}")

    def test_canonical_never_raises_and_is_idempotent(self):
        r = rng(13)
        for _ in range(400):
            s = "".join(r.choice(string.printable) for _ in range(r.randint(0, 24)))
            try:
                got = self.tr.canonical(s)
            except Exception as e:                       # noqa: BLE001
                self.fail(f"canonical() raised {type(e).__name__} on {s!r}")
            if got is not None:
                self.check(13, s, self.tr.canonical(got["name"]) == got,
                           "not idempotent")

    def test_display_name_is_total_and_non_empty(self):
        r = rng(17)
        for _ in range(400):
            base = "".join(r.choice(string.ascii_letters + " -") for _ in range(r.randint(1, 15)))
            name = base + (f" {r.randint(1, 9)}" if r.random() < 0.5 else "")
            got = self.places.display_name(name)
            self.check(17, name, isinstance(got, str), "did not return a string")
            self.check(17, name, got.strip() != "" or name.strip() == "",
                       "returned empty for a non-empty name")


if __name__ == "__main__":
    unittest.main(verbosity=2)
