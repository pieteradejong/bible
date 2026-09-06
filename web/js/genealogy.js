// Descent lines as a graph. Laid out by generation left to right, which makes
// the thing worth seeing visible: Matthew and Luke split at David, run in
// parallel for twenty generations, touch again at Shealtiel and Zerubbabel,
// and give Joseph two different fathers.
import { load, shell, esc, books, verseText, readable, showTip, moveTip, hideTip } from "./common.js";
import { generationDepths, barycentre } from "./lib/layout.js";

shell("Genealogy");

const LINE = {
  primeval: { c: "#e0a458", label: "Adam to Abraham" },
  judah:    { c: "#d6b25c", label: "Perez to David" },
  matthew:  { c: "#6d9fe0", label: "Matthew 1 (via Solomon)" },
  luke:     { c: "#a98bd6", label: "Luke 3 (via Nathan)" },
  other:    { c: "#8d8378", label: "Other family ties" },
  spouse:   { c: "#d9736a", label: "Marriages" },
};

document.body.insertAdjacentHTML("beforeend", `
  <main>
    <aside>
      <h2>Lines</h2>
      <div class="checks" id="lines"></div>
      <h2>Show</h2>
      <div class="checks">
        <label><input type="checkbox" id="spouses" checked> Marriages</label>
        <label><input type="checkbox" id="ages" checked> Lifespans from Genesis 5 and 11</label>
      </div>
      <div class="control" style="margin-top:12px">
        <label for="q">Find</label>
        <input type="search" id="q" placeholder="Zerubbabel, Boaz, Enoch...">
      </div>
      <h2>The divergence</h2>
      <p class="note">Matthew traces Jesus through Solomon and the kings of
        Judah; Luke traces him through David's son Nathan. The two lists share
        only Shealtiel and Zerubbabel in between, and name different fathers for
        Joseph &mdash; Jacob in Matthew, Heli in Luke. Harmonising them has been
        argued over since the second century; this view just shows both.</p>
      <p class="hint" id="stats"></p>
      <div class="control"><button id="home">Back to the beginning</button></div>
      <div class="control"><button id="fit">Fit all 75 generations (small)</button></div>
      <p class="hint">Scroll to zoom, drag to pan. The chart is 75 generations
        wide, so it opens at readable size on Adam rather than fitted.</p>
    </aside>
    <div class="stage"><svg id="chart"></svg></div>
    <aside class="right" id="detail"><h2>Selection</h2>
      <p class="note">Click anyone.</p></aside>
  </main>`);

const [g, BOOKS] = await Promise.all([load("genealogy.json"), books()]);
const S = { lines: new Set(Object.keys(LINE)), spouses: true, ages: true, q: "" };

const byId = new Map(g.people.map((p) => [p.id, p]));
const descent = g.edges.filter((e) => e.kind !== "spouse");
const marriages = g.edges.filter((e) => e.kind === "spouse");

// --- layout: generation = longest path from a root --------------------------
const parents = new Map(), children = new Map();
const push = (map, key, val) => {
  if (!map.has(key)) map.set(key, []);
  map.get(key).push(val);
};
for (const e of descent) {
  if (!byId.has(e.p) || !byId.has(e.c)) continue;
  push(children, e.p, e.c);
  push(parents, e.c, e.p);
}

const depth = generationDepths(g.people.map((p) => p.id), (id) => parents.get(id));

// A person who appears only as somebody's spouse has no descent depth of her
// own; put her in the same generation as the person she married.
const spouseOf = new Map();
for (const m of marriages) {
  spouseOf.set(m.p, m.c);
  spouseOf.set(m.c, m.p);
}
for (const p of g.people) {
  const noLine = !(parents.get(p.id) ?? []).length && !(children.get(p.id) ?? []).length;
  const mate = spouseOf.get(p.id);
  if (noLine && mate && depth.has(mate)) depth.set(p.id, depth.get(mate));
}

const maxDepth = Math.max(...depth.values());
const layers = Array.from({ length: maxDepth + 1 }, () => []);
for (const p of g.people) layers[depth.get(p.id)].push(p.id);

// Order within each layer by the mean position of parents (barycentre), a few
// sweeps, so the Matthew and Luke tracks stay unbraided.
const pos = new Map();
layers.forEach((ids) => ids.forEach((id, i) => pos.set(id, i)));
for (let sweep = 0; sweep < 6; sweep++) {
  for (let d = 1; d <= maxDepth; d++) {
    layers[d].sort((a, b) => bary(a) - bary(b));
    layers[d].forEach((id, i) => pos.set(id, i));
  }
  for (let d = maxDepth - 1; d >= 0; d--) {
    layers[d].sort((a, b) => baryDown(a) - baryDown(b));
    layers[d].forEach((id, i) => pos.set(id, i));
  }
}
function bary(id) {
  const ps = (parents.get(id) ?? []).filter((p) => pos.has(p));
  if (ps.length) return barycentre(ps, (p) => pos.get(p), 0);
  // Nudge a spouse just below the person married, rather than leaving her
  // wherever the initial order happened to put her.
  const mate = spouseOf.get(id);
  if (mate && pos.has(mate)) return pos.get(mate) + 0.5;
  return pos.get(id) ?? 0;
}
function baryDown(id) {
  return barycentre((children.get(id) ?? []).filter((c) => pos.has(c)),
                    (c) => pos.get(c), pos.get(id) ?? 0);
}

const COL = 104, ROW = 30, PAD = 40;
const laneOf = (p) => (p.lines[0] ?? "other");
const xy = (id) => ({
  x: PAD + depth.get(id) * COL,
  y: PAD + 30 + pos.get(id) * ROW,
});

// --- controls ---------------------------------------------------------------
document.getElementById("lines").innerHTML = Object.entries(LINE).map(([k, v]) => {
  const n = k === "spouse" ? marriages.length
    : k === "other" ? g.people.filter((p) => !p.lines.length).length
    : g.people.filter((p) => p.lines.includes(k)).length;
  return `<label><input type="checkbox" data-k="${k}" checked>
    <span class="swatch" style="--c:${v.c}"></span>${v.label}
    <span class="count">${n}</span></label>`;
}).join("");
document.getElementById("lines").addEventListener("change", (e) => {
  e.target.checked ? S.lines.add(e.target.dataset.k) : S.lines.delete(e.target.dataset.k);
  draw();
});
document.getElementById("spouses").addEventListener("change", (e) => {
  S.spouses = e.target.checked; draw();
});
document.getElementById("ages").addEventListener("change", (e) => {
  S.ages = e.target.checked; draw();
});
document.getElementById("q").addEventListener("input", (e) => {
  S.q = e.target.value.trim().toLowerCase(); draw();
});
document.getElementById("stats").textContent =
  `${g.people.length} people, ${descent.length} parent-child links, ` +
  `${marriages.length} marriages, ${maxDepth + 1} generations.`;

// --- draw -------------------------------------------------------------------
const svg = d3.select("#chart");
const stage = document.querySelector(".stage");
const root = svg.append("g");
const gEdge = root.append("g"), gNode = root.append("g");

const zoom = d3.zoom().scaleExtent([0.12, 3])
  .on("zoom", (ev) => root.attr("transform", ev.transform));
svg.call(zoom);

let W = 0, H = 0, fitted = false;
function resize() {
  W = stage.clientWidth; H = stage.clientHeight;
  svg.attr("width", W).attr("height", H);
  draw();
  if (!fitted && W > 0 && H > 0) { fitted = true; home(0); }
}
new ResizeObserver(resize).observe(stage);

function visiblePerson(p) {
  return p.lines.some((l) => S.lines.has(l)) || (!p.lines.length && S.lines.has("other"));
}

function draw() {
  if (!W) return;
  const people = g.people.filter(visiblePerson);
  const ok = new Set(people.map((p) => p.id));
  const edges = [
    ...descent.filter((e) => ok.has(e.p) && ok.has(e.c) && S.lines.has(e.line)),
    ...(S.spouses && S.lines.has("spouse")
      ? marriages.filter((e) => ok.has(e.p) && ok.has(e.c)) : []),
  ];

  const es = gEdge.selectAll("path").data(edges, (e) => `${e.p}|${e.c}|${e.kind}`);
  es.exit().remove();
  es.enter().append("path").attr("fill", "none")
    .merge(es)
    .attr("stroke", (e) => LINE[e.line]?.c ?? "#8d8378")
    .attr("stroke-opacity", (e) => (e.kind === "spouse" ? 0.5 : 0.75))
    .attr("stroke-width", (e) => (e.kind === "spouse" ? 1 : 1.4))
    .attr("stroke-dasharray", (e) => (e.kind === "spouse" ? "3 3" : null))
    .attr("d", (e) => {
      const a = xy(e.p), b = xy(e.c);
      const mx = (a.x + b.x) / 2;
      return `M${a.x + 6},${a.y} C${mx},${a.y} ${mx},${b.y} ${b.x - 6},${b.y}`;
    });

  const ns = gNode.selectAll("g.p").data(people, (p) => p.id);
  ns.exit().remove();
  const en = ns.enter().append("g").attr("class", "p").style("cursor", "pointer");
  en.append("circle");
  en.append("text").attr("dy", "0.32em").attr("font-size", 10.5);
  en.on("mouseenter", (ev, p) => showTip(ev, tip(p)))
    .on("mousemove", moveTip).on("mouseleave", hideTip)
    .on("click", (ev, p) => detail(p));

  const all = gNode.selectAll("g.p")
    .attr("transform", (p) => { const c = xy(p.id); return `translate(${c.x},${c.y})`; })
    .attr("opacity", (p) => (!S.q || p.name.toLowerCase().includes(S.q) ? 1 : 0.16));
  all.select("circle")
    .attr("r", (p) => (S.ages && p.age ? 3 + Math.sqrt(p.age) / 4.2 : 4))
    .attr("fill", (p) => LINE[laneOf(p)]?.c ?? "#8d8378")
    .attr("fill-opacity", (p) => (p.sex === "f" ? 0.25 : 0.85))
    .attr("stroke", (p) => LINE[laneOf(p)]?.c ?? "#8d8378")
    .attr("stroke-width", 1.3);
  all.select("text")
    .attr("x", (p) => (S.ages && p.age ? 6 + Math.sqrt(p.age) / 4.2 : 9))
    .attr("fill", (p) => ((parents.get(p.id) ?? []).length > 1 ? "var(--accent)" : "var(--ink)"))
    .text((p) => p.name + (S.ages && p.age ? `  ${p.age}` : ""));
}

function tip(p) {
  const kids = (children.get(p.id) ?? []).length;
  return `<b>${esc(p.name)}</b>
    <div class="meta">generation ${depth.get(p.id) + 1}
      ${p.age ? ` &middot; lived ${p.age} years` : ""}
      ${kids ? ` &middot; ${kids} child${kids === 1 ? "" : "ren"} named` : ""}</div>
    ${p.kjv && p.kjv !== p.name ? `<div class="meta">KJV: ${esc(p.kjv)}</div>` : ""}
    <div class="meta" style="margin-top:5px">${p.lines.map((l) => LINE[l]?.label ?? l).join(" &middot; ")}</div>`;
}

async function detail(p) {
  const box = document.getElementById("detail");
  const ps = parents.get(p.id) ?? [], cs = children.get(p.id) ?? [];
  const spouse = marriages.filter((m) => m.p === p.id || m.c === p.id)
    .map((m) => (m.p === p.id ? m.c : m.p));
  const link = (id) => `<a href="#" data-go="${esc(id)}">${esc(byId.get(id)?.name ?? id)}</a>`;
  box.innerHTML = `<h2>Person</h2>
    <div style="font:600 17px/1.3 var(--serif)">${esc(p.name)}</div>
    <div style="color:var(--muted);font-size:12.5px">generation ${depth.get(p.id) + 1}
      ${p.age ? ` &middot; lived ${p.age} years` : ""}</div>
    ${p.kjv && p.kjv !== p.name
      ? `<p class="hint">Spelled &ldquo;${esc(p.kjv)}&rdquo; in the KJV.</p>` : ""}
    ${ps.length > 1
      ? `<p class="note" style="border-color:var(--accent)">Two different fathers are
         named for this person, by different books. Both are drawn.</p>` : ""}
    ${ps.length ? `<h2>Parent${ps.length > 1 ? "s" : ""}</h2><div>${ps.map(link).join(", ")}</div>` : ""}
    ${spouse.length ? `<h2>Married</h2><div>${spouse.map(link).join(", ")}</div>` : ""}
    ${cs.length ? `<h2>Children named</h2><div style="line-height:1.9">${cs.map(link).join(", ")}</div>` : ""}
    ${p.refs.length ? `<h2>References</h2><div id="refs"></div>` : ""}`;
  box.querySelectorAll("a[data-go]").forEach((a) =>
    a.addEventListener("click", (ev) => {
      ev.preventDefault();
      const t = byId.get(a.dataset.go);
      if (t) { detail(t); centre(t.id); }
    }));
  const holder = box.querySelector("#refs");
  if (!holder) return;
  const notes = descent.filter((e) => e.c === p.id && e.note).map((e) => e.note);
  if (notes.length)
    holder.insertAdjacentHTML("beforebegin", `<p class="note">${esc(notes[0])}</p>`);
  for (const ref of p.refs) {
    const txt = await verseText(ref);
    holder.insertAdjacentHTML("beforeend", `
      <div style="margin-bottom:10px">
        <a class="ref" href="reader.html#${ref}">${esc(readable(ref, BOOKS))}</a>
        <div class="verse-text" style="font-size:13px;margin-top:2px">${txt ?? ""}</div>
      </div>`);
  }
}

function centre(id) {
  const c = xy(id), k = d3.zoomTransform(svg.node()).k;
  svg.transition().duration(500).call(zoom.transform,
    d3.zoomIdentity.translate(W / 2 - c.x * k, H / 2 - c.y * k).scale(k));
}

// The graph is far wider than it is tall, so the useful default is full size,
// anchored at the first generation, rather than an unreadable overview.
function home(ms = 600) {
  if (!W || !H) return;
  d3.select(svg.node()).transition().duration(ms).call(zoom.transform,
    d3.zoomIdentity.translate(0, Math.max(20, (H - contentHeight()) / 2)).scale(1));
}

function contentHeight() {
  return PAD * 2 + Math.max(...layers.map((l) => l.length)) * ROW;
}

function fit(ms = 600) {
  if (!W || !H) return;
  const w = PAD * 2 + maxDepth * COL + 140;
  const h = PAD * 2 + Math.max(...layers.map((l) => l.length)) * ROW + 60;
  const k = Math.max(Math.min(W / w, H / h, 1), 0.12);
  d3.select(svg.node()).transition().duration(ms).call(zoom.transform,
    d3.zoomIdentity.translate((W - w * k) / 2, (H - h * k) / 2).scale(k));
}
document.getElementById("fit").onclick = () => fit();
document.getElementById("home").onclick = () => home();

resize();
