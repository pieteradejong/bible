// Layout maths pulled out of the views. Run with `node --test tests/js/`.
import test from "node:test";
import assert from "node:assert/strict";
import {
  alphaFor, packRows, generationDepths, barycentre,
} from "../../web/js/lib/layout.js";

// --- alphaFor ---------------------------------------------------------------

test("alphaFor always returns two hex digits", () => {
  for (const n of [0, 1, 100, 1e4, 1e6]) {
    const a = alphaFor(n);
    assert.match(a, /^[0-9a-f]{2}$/, `n=${n} gave ${a}`);
  }
});

test("alphaFor fades as the number of arcs grows", () => {
  const counts = [10, 100, 1000, 20000, 190000];
  const alphas = counts.map((n) => parseInt(alphaFor(n), 16));
  for (let i = 1; i < alphas.length; i++) {
    assert.ok(alphas[i] <= alphas[i - 1],
      `alpha rose from ${alphas[i - 1]} to ${alphas[i]} between ` +
      `${counts[i - 1]} and ${counts[i]} arcs`);
  }
  // <= alone is satisfied by a constant, which is exactly the bug that shipped:
  // a fixed alpha whited out the canvas at 190,000 arcs. Require it to respond.
  assert.ok(alphas.at(-1) < alphas[0] / 2,
    `alpha barely responds to arc count: ${alphas[0]} -> ${alphas.at(-1)}`);
});

test("alphaFor stays visible at the extremes", () => {
  // REGRESSION: a fixed alpha of 0x1a saturated 190,000 additive arcs to solid
  // white. The floor keeps arcs visible; the ceiling keeps them from blowing out.
  assert.ok(parseInt(alphaFor(1e7), 16) >= 2, "faded to invisible");
  assert.ok(parseInt(alphaFor(1), 16) <= 0x56, "blew past the ceiling");
});

// --- packRows ---------------------------------------------------------------

const overlaps = (a, b) => {
  const ax2 = Math.max(a.b ?? a.a, a.a), bx2 = Math.max(b.b ?? b.a, b.a);
  return a.a < bx2 && b.a < ax2;
};

test("packRows never puts two overlapping bars on the same row", () => {
  const items = [
    { a: 0, b: 100, label: "one" },
    { a: 50, b: 150, label: "two" },
    { a: 120, b: 200, label: "three" },
    { a: 400, b: 500, label: "four" },
  ];
  const { placed } = packRows(items, { pixelsPerUnit: 1 });
  const byRow = new Map();
  for (const { item, row } of placed) {
    for (const other of byRow.get(row) ?? []) {
      assert.ok(!overlaps(item, other),
        `${item.label} and ${other.label} share row ${row}`);
    }
    byRow.set(row, [...(byRow.get(row) ?? []), item]);
  }
});

test("packRows leaves room for labels, so rows grow as you zoom out", () => {
  // REGRESSION: packing reserved label space in data units, so labels collided
  // at every zoom level but the one it was tuned for. Fewer pixels per unit
  // means a label costs more units, which means more rows.
  const items = Array.from({ length: 8 }, (_, i) => ({
    a: i * 10, b: i * 10 + 5, label: "a fairly long label here",
  }));
  const zoomedIn = packRows(items, { pixelsPerUnit: 20 }).rows;
  const zoomedOut = packRows(items, { pixelsPerUnit: 0.2 }).rows;
  assert.ok(zoomedOut > zoomedIn,
    `expected more rows when zoomed out, got ${zoomedOut} vs ${zoomedIn}`);
});

test("packRows places every item exactly once", () => {
  const items = Array.from({ length: 40 }, (_, i) => ({
    a: (i * 37) % 500, b: ((i * 37) % 500) + 20, label: `item ${i}`,
  }));
  const { placed } = packRows(items, { pixelsPerUnit: 2 });
  assert.equal(placed.length, items.length);
  assert.equal(new Set(placed.map((p) => p.item)).size, items.length);
});

test("packRows uses one row for items that cannot collide", () => {
  const items = Array.from({ length: 5 }, (_, i) => ({
    a: i * 1000, b: i * 1000 + 10, label: "x",
  }));
  assert.equal(packRows(items, { pixelsPerUnit: 1 }).rows, 1);
});

test("packRows copes with instants, zero scale and no items", () => {
  assert.equal(packRows([], { pixelsPerUnit: 1 }).rows, 0);
  assert.equal(packRows([{ a: 5, b: null, label: "point" }],
                        { pixelsPerUnit: 1 }).placed.length, 1);
  assert.doesNotThrow(() => packRows([{ a: 0, b: 1, label: "x" }],
                                     { pixelsPerUnit: 0 }));
});

test("packRows does not mutate the caller's array order", () => {
  const items = [{ a: 30, b: 40, label: "b" }, { a: 0, b: 10, label: "a" }];
  packRows(items, { pixelsPerUnit: 1 });
  assert.deepEqual(items.map((i) => i.label), ["b", "a"]);
});

// --- generationDepths -------------------------------------------------------

const parentsFrom = (edges) => {
  const m = new Map();
  for (const [p, c] of edges) m.set(c, [...(m.get(c) ?? []), p]);
  return (id) => m.get(id);
};

test("generationDepths numbers a simple chain", () => {
  const d = generationDepths(["a", "b", "c"],
                             parentsFrom([["a", "b"], ["b", "c"]]));
  assert.equal(d.get("a"), 0);
  assert.equal(d.get("b"), 1);
  assert.equal(d.get("c"), 2);
});

test("generationDepths takes the LONGEST path when parents disagree", () => {
  // Joseph has two fathers -- Jacob in Matthew, Heli in Luke -- reached by
  // chains of different lengths. Taking the longest keeps both lines legible;
  // taking the shortest would collapse one onto the other.
  const edges = [
    ["david", "solomon"], ["solomon", "joseph_line_a"],
    ["david", "nathan"], ["nathan", "x1"], ["x1", "x2"], ["x2", "joseph_line_a"],
  ];
  const ids = ["david", "solomon", "nathan", "x1", "x2", "joseph_line_a"];
  const d = generationDepths(ids, parentsFrom(edges));
  assert.equal(d.get("joseph_line_a"), 4, "did not take the longer line");
});

test("generationDepths gives every root zero", () => {
  const d = generationDepths(["r1", "r2", "kid"], parentsFrom([["r1", "kid"]]));
  assert.equal(d.get("r1"), 0);
  assert.equal(d.get("r2"), 0);
});

test("generationDepths terminates on a cycle instead of hanging", () => {
  const d = generationDepths(["a", "b"], parentsFrom([["a", "b"], ["b", "a"]]));
  assert.ok(Number.isFinite(d.get("a")));
  assert.ok(Number.isFinite(d.get("b")));
});

test("generationDepths covers every id it is given", () => {
  const ids = ["a", "b", "c", "orphan"];
  const d = generationDepths(ids, parentsFrom([["a", "b"], ["b", "c"]]));
  for (const id of ids) assert.ok(d.has(id), `${id} was not assigned a depth`);
});

// --- barycentre -------------------------------------------------------------

test("barycentre averages the neighbours it can see", () => {
  const pos = new Map([["a", 2], ["b", 6]]);
  assert.equal(barycentre(["a", "b"], (k) => pos.get(k), 0), 4);
});

test("barycentre falls back when there are no neighbours", () => {
  assert.equal(barycentre([], () => 1, 99), 99);
  assert.equal(barycentre(undefined, () => 1, 7), 7);
});
