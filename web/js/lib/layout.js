// Layout maths shared by the views: nothing here touches the DOM, so it can be
// unit tested. Each function is pulled out of the view that used to own it.

/**
 * Per-arc alpha for the cross-reference canvas, as a two-hex-digit string.
 *
 * Arcs are drawn with additive blending, so an alpha that reads well for a
 * thousand arcs is a white-out at a hundred thousand. Scale it to the number
 * actually being drawn.
 */
export function alphaFor(n) {
  const a = Math.max(2, Math.min(56, Math.round(2400 / Math.sqrt(Math.max(n, 1)))));
  return a.toString(16).padStart(2, "0");
}

/**
 * Greedily pack items into non-overlapping rows.
 *
 * Each item needs its bar plus room for its label, and a label costs a fixed
 * number of *pixels* -- which is a different number of years at every zoom
 * level. So this takes pixelsPerUnit and is re-run on each render; packing in
 * data units instead is what made timeline labels collide at every zoom but one.
 *
 * items: [{a, b, label}] where a/b are start/end in data units (b may be null).
 * Returns [{item, row}] plus the row count.
 */
export function packRows(items, { pixelsPerUnit = 1, charPx = 5.7, gapPx = 12 } = {}) {
  const toUnits = (px) => (pixelsPerUnit > 0 ? px / pixelsPerUnit : px);
  const rowEnds = [];
  const placed = [];
  for (const item of [...items].sort((x, y) => x.a - y.a ||
                                      (x.b ?? x.a) - (y.b ?? y.a))) {
    const barEnd = Math.max(item.b ?? item.a, item.a);
    const labelPx = String(item.label ?? "").length * charPx;
    const barPx = Math.max((barEnd - item.a) * pixelsPerUnit, 3);
    // A bar wide enough to carry its label inside needs only the gap after it.
    const need = toUnits(barPx > labelPx + 14 ? gapPx : labelPx + gapPx);
    let row = rowEnds.findIndex((end) => item.a > end);
    if (row < 0) { row = rowEnds.length; rowEnds.push(-Infinity); }
    rowEnds[row] = barEnd + need;
    placed.push({ item, row });
  }
  return { placed, rows: rowEnds.length };
}

/**
 * Generation number for every node: the longest path from any root.
 *
 * Longest rather than shortest is deliberate. Joseph has two fathers in the
 * genealogy -- Jacob in Matthew, Heli in Luke -- and taking the longest path
 * keeps both lines readable instead of collapsing one onto the other.
 */
export function generationDepths(ids, parentsOf) {
  const depth = new Map();
  const visit = (id, stack) => {
    if (depth.has(id)) return depth.get(id);
    if (stack.has(id)) return 0;          // defensive: cycles are not expected
    stack.add(id);
    const ps = parentsOf(id) ?? [];
    const d = ps.length ? Math.max(...ps.map((p) => visit(p, stack))) + 1 : 0;
    stack.delete(id);
    depth.set(id, d);
    return d;
  };
  for (const id of ids) visit(id, new Set());
  return depth;
}

/** Mean position of a node's neighbours, for barycentre crossing reduction. */
export function barycentre(neighbours, positionOf, fallback) {
  const xs = (neighbours ?? []).map(positionOf).filter((v) => v != null);
  return xs.length ? xs.reduce((a, b) => a + b, 0) / xs.length : fallback;
}
