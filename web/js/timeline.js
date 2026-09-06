// Zoomable chronology. Rows are packed greedily; colour encodes how firmly the
// date is known, because that is the honest variable in a biblical timeline.
import { load, shell, showTip, moveTip, hideTip, CERTAINTY, span, esc, readable, verseText } from "./common.js";
import { packRows } from "./lib/layout.js";

shell("Timeline");

const S = { certainty: new Set(Object.keys(CERTAINTY)), groups: new Set(), q: "" };

const GROUPS = [
  { id: "eras",      label: "Eras",              kind: "era" },
  { id: "narrative", label: "Narrative events",  kind: "event", lanes: ["narrative"] },
  { id: "patriarch", label: "Patriarchs",        kind: "person", lanes: ["patriarch"] },
  { id: "kings",     label: "Kings",             kind: "person", lanes: ["united", "judah", "israel"] },
  { id: "prophets",  label: "Prophets & scribes", kind: "person", lanes: ["prophet"] },
  { id: "israel",    label: "Israel & Judah",    kind: "event", lanes: ["israel", "exile"] },
  { id: "rulers",    label: "Foreign rulers",    kind: "person", lanes: ["empire"] },
  { id: "empires",   label: "Empires & wars",    kind: "event", lanes: ["empires"] },
  { id: "church",    label: "Jesus & the church", kind: "both", lanes: ["church"] },
  { id: "text",      label: "Text & canon",      kind: "event", lanes: ["text"] },
  { id: "books",     label: "Books written",     kind: "book" },
];
GROUPS.forEach((g) => S.groups.add(g.id));

const data = await load("timeline.json");

// One flat list of drawable items, each with a group, a span, and a certainty.
const items = [];
for (const e of data.eras)
  items.push({ g: "eras", label: e.label, a: e.start, b: e.end, c: e.certainty, kind: "era", raw: e });
for (const e of data.events) {
  const g = GROUPS.find((x) => x.kind !== "person" && x.lanes?.includes(e.lane));
  items.push({ g: g ? g.id : "narrative", label: e.label, a: e.start, b: e.end ?? null,
               c: e.certainty, kind: "event", raw: e });
}
for (const p of data.people) {
  const g = GROUPS.find((x) => (x.kind === "person" || x.kind === "both") && x.lanes?.includes(p.lane));
  if (g) items.push({ g: g.id, label: p.name, a: p.start, b: p.end, c: p.certainty, kind: "person", raw: p });
}
for (const b of data.books)
  items.push({ g: "books", label: b.name, a: b.composed[0], b: b.composed[1],
               c: "conventional", kind: "book", raw: b });

// ---------------------------------------------------------------- side panel
document.body.insertAdjacentHTML("beforeend", `
  <main>
    <aside>
      <div class="control">
        <label for="q">Find</label>
        <input type="search" id="q" placeholder="Josiah, Carchemish, Romans...">
      </div>
      <h2>How firm is the date?</h2>
      <div class="checks" id="certainty"></div>
      <p class="hint" id="certhint"></p>
      <h2>Rows</h2>
      <div class="checks" id="groups"></div>
      <h2>View</h2>
      <div class="control"><button id="fit">Fit everything (4004 BCE - 1611 CE)</button></div>
      <div class="control"><button id="focus">Focus 1200 BCE - 150 CE</button></div>
      <p class="hint">Scroll to move down the chart; hold &#8984; or Ctrl and scroll
        to zoom the time axis; drag to pan. Click any bar for its scripture
        references.</p>
    </aside>
    <div class="stage">
      <svg id="axis" style="position:absolute;top:0;left:0;right:0;z-index:2;
           background:var(--bg);border-bottom:1px solid var(--line)"></svg>
      <div id="scroll" style="position:absolute;top:26px;left:0;right:0;bottom:0;
           overflow-y:auto;overflow-x:hidden"><svg id="chart"></svg></div>
    </div>
    <aside class="right" id="detail"><h2>Selection</h2>
      <p class="note">Click anything on the chart.</p></aside>
  </main>`);

const certBox = document.getElementById("certainty");
certBox.innerHTML = Object.entries(CERTAINTY).map(([k, v]) => `
  <label title="${esc(v.hint)}"><input type="checkbox" data-c="${k}" checked>
  <span class="swatch" style="--c:${v.color}"></span>${v.label}
  <span class="count" id="cnt-${k}"></span></label>`).join("");
certBox.addEventListener("change", (e) => {
  const k = e.target.dataset.c;
  e.target.checked ? S.certainty.add(k) : S.certainty.delete(k);
  draw();
});
certBox.addEventListener("mouseover", (e) => {
  const l = e.target.closest("label");
  if (l) document.getElementById("certhint").textContent = l.title;
});

const groupBox = document.getElementById("groups");
groupBox.innerHTML = GROUPS.map((g) => `
  <label><input type="checkbox" data-g="${g.id}" checked>${g.label}
  <span class="count">${items.filter((i) => i.g === g.id).length}</span></label>`).join("");
groupBox.addEventListener("change", (e) => {
  const k = e.target.dataset.g;
  e.target.checked ? S.groups.add(k) : S.groups.delete(k);
  draw();
});
document.getElementById("q").addEventListener("input", (e) => {
  S.q = e.target.value.trim().toLowerCase(); draw();
});

for (const [k] of Object.entries(CERTAINTY))
  document.getElementById(`cnt-${k}`).textContent = items.filter((i) => i.c === k).length;

// -------------------------------------------------------------------- chart
const svg = d3.select("#chart");
const axisSvg = d3.select("#axis");
const scroller = document.getElementById("scroll");
const stage = document.querySelector(".stage");
const M = { top: 4, right: 24, bottom: 8, left: 168 };
const AXIS_H = 26;
const ROW = 17, GAP = 13, PAD_PX = 12;

const x0 = d3.scaleLinear().domain([-1200, 150]);
let x = x0.copy();

const gAxis = axisSvg.append("g").attr("class", "axis");
const gRows = svg.append("g");
const gGrid = svg.append("g");

const zoom = d3.zoom().scaleExtent([0.02, 400])
  .on("zoom", (ev) => { x = ev.transform.rescaleX(x0); draw(); });
// Zoom is driven from the scroll container so the whole tall chart responds.
d3.select(scroller).call(zoom).on("wheel.zoom", function (ev) {
  // Plain wheel scrolls the tall chart; hold a modifier (or pinch) to zoom.
  if (!ev.ctrlKey && !ev.metaKey && !ev.altKey) return;
  ev.preventDefault();
  const t = d3.zoomTransform(this);
  const p = d3.pointer(ev, this);
  const k = t.k * Math.pow(2, -ev.deltaY * 0.002);
  d3.select(this).call(zoom.transform,
    d3.zoomIdentity.translate(p[0] - (p[0] - t.x) * (k / t.k), 0).scale(k));
});

let W = 0, H = 0;
function resize() {
  W = stage.clientWidth; H = stage.clientHeight;
  axisSvg.attr("width", W).attr("height", AXIS_H);
  x0.range([M.left, W - M.right]);
  x = d3.zoomTransform(scroller).rescaleX(x0);
  draw();
}
new ResizeObserver(resize).observe(stage);

// Greedy row packing. It has to run at render time, not once: a label needs a
// fixed number of *pixels*, which is a different number of years at every zoom
// level, and packing in year units makes labels collide everywhere but one
// zoom. Repacking ~260 items per frame is cheap.
let layout = [], contentHeight = 0;

function shownItems() {
  return items.filter((i) =>
    S.groups.has(i.g) && S.certainty.has(i.c) &&
    (!S.q || i.label.toLowerCase().includes(S.q)));
}

function pack() {
  const shown = shownItems();
  const ppy = x(1) - x(0);          // pixels per year at the current zoom

  layout = [];
  let y = M.top + 14;
  for (const g of GROUPS) {
    if (!S.groups.has(g.id)) continue;
    const mine = shown.filter((i) => i.g === g.id);
    if (!mine.length) continue;
    const { placed, rows } = packRows(mine, { pixelsPerUnit: ppy, gapPx: PAD_PX });
    for (const { item, row } of placed) {
      item._y = y + row * ROW;
      layout.push(item);
    }
    layout.push({ _group: { label: g.label, y, rows } });
    y += rows * ROW + GAP;
  }
  contentHeight = y + 20;
}

function draw() { pack(); render(); }

function render() {
  if (!W) return;
  svg.attr("width", W).attr("height", contentHeight);
  const [lo, hi] = x.domain();

  // axis: adaptive tick step so labels never crowd
  const target = Math.max(3, Math.floor((W - M.left) / 110));
  const raw = (hi - lo) / target;
  const step = [1, 2, 5, 10, 25, 50, 100, 250, 500, 1000, 2500]
    .find((s) => s >= raw) ?? 5000;
  const ticks = d3.range(Math.ceil(lo / step) * step, hi, step);

  const t = gAxis.selectAll("g.t").data(ticks, (d) => d);
  const te = t.enter().append("g").attr("class", "t");
  te.append("line").attr("y1", AXIS_H - 9).attr("y2", AXIS_H).attr("stroke", "var(--line)");
  te.append("text").attr("y", AXIS_H - 14).attr("text-anchor", "middle")
    .attr("fill", "var(--faint)").attr("font-size", 10.5);
  t.exit().remove();
  gAxis.selectAll("g.t").attr("transform", (d) => `translate(${x(d)},0)`);
  gAxis.selectAll("g.t").select("text")
    .text((d) => (d < 0 ? `${-d} BC` : d === 0 ? "1" : `${d} AD`));

  // vertical guides down the scrolling chart, plus the year-zero marker
  const gr = gGrid.selectAll("line.tick").data(ticks, (d) => d);
  gr.enter().append("line").attr("class", "tick")
    .attr("stroke", "var(--line)").attr("stroke-opacity", .45)
    .merge(gr)
    .attr("x1", (d) => x(d)).attr("x2", (d) => x(d))
    .attr("y1", 0).attr("y2", contentHeight);
  gr.exit().remove();
  gGrid.selectAll("line.zero").data([0]).join("line").attr("class", "zero")
    .attr("x1", x(0)).attr("x2", x(0)).attr("y1", 0).attr("y2", contentHeight)
    .attr("stroke", "var(--accent)").attr("stroke-opacity", 0.35)
    .attr("stroke-dasharray", "3 4");

  const groups = layout.filter((d) => d._group).map((d) => d._group);
  const gl = gRows.selectAll("g.glabel").data(groups, (d) => d.label);
  const gle = gl.enter().append("g").attr("class", "glabel");
  gle.append("text").attr("x", M.left - 12).attr("text-anchor", "end")
    .attr("fill", "var(--faint)").attr("font-size", 10.5)
    .attr("font-weight", 600).attr("letter-spacing", ".08em");
  gle.append("line").attr("x1", 0).attr("stroke", "var(--line)").attr("stroke-opacity", .6);
  gl.exit().remove();
  gRows.selectAll("g.glabel").select("text")
    .attr("y", (d) => d.y + 9).text((d) => d.label.toUpperCase());
  gRows.selectAll("g.glabel").select("line")
    .attr("x1", M.left - 8).attr("x2", W).attr("y1", (d) => d.y - 7).attr("y2", (d) => d.y - 7);

  const bars = layout.filter((d) => !d._group);
  const sel = gRows.selectAll("g.item").data(bars, (d) => d.g + d.label + d.a);
  const en = sel.enter().append("g").attr("class", "item").style("cursor", "pointer");
  en.append("rect").attr("class", "bg").attr("rx", 2.5);
  en.append("text").attr("class", "lab").attr("dy", "0.32em")
    .attr("font-size", 10.5).attr("fill", "var(--ink)");
  en.on("mousemove", (ev, d) => { moveTip(ev); })
    .on("mouseenter", (ev, d) => showTip(ev, tipHtml(d)))
    .on("mouseleave", hideTip)
    .on("click", (ev, d) => detail(d));
  sel.exit().remove();

  // Clamp to a little beyond the viewport: zoomed in far enough, a millennium-long
  // era is millions of pixels wide, and only the visible slice matters.
  const clamp = (v) => Math.max(M.left, Math.min(v, W + 60));
  const x1 = (d) => clamp(x(d.a));
  const x2 = (d) => clamp(d.b == null ? x(d.a) + 3 : x(d.b));

  const all = gRows.selectAll("g.item");
  // An item entirely off-screen would otherwise clamp to a 3px stub at the clip
  // edge, which reads as a real event that happens to have no label.
  all.attr("display", (d) =>
    (x(d.b ?? d.a) < M.left - 2 || x(d.a) > W + 2 ? "none" : null));
  all.select("rect.bg")
    .attr("x", x1)
    .attr("y", (d) => d._y)
    .attr("width", (d) => Math.max(x2(d) - x1(d), 3))
    .attr("height", ROW - 5)
    .attr("fill", (d) => CERTAINTY[d.c].color)
    .attr("fill-opacity", (d) => (d.kind === "era" ? 0.28 : d.b == null ? 0.95 : 0.55))
    .attr("stroke", (d) => CERTAINTY[d.c].color)
    .attr("stroke-opacity", (d) => (d.kind === "era" ? 0.7 : 0.9));
  const labelPx = (d) => d.label.length * 5.7;
  const inside = (d) => x2(d) - x1(d) > labelPx(d) + 14;
  all.select("text.lab")
    .attr("x", (d) => (inside(d) ? x1(d) + 6 : x2(d) + 5))
    .attr("y", (d) => d._y + (ROW - 5) / 2)
    .attr("fill", (d) => (inside(d) ? "#12100e" : "var(--ink)"))
    .attr("font-weight", (d) => (inside(d) ? 600 : 400))
    .attr("opacity", (d) => (x2(d) <= M.left || x1(d) > W - 4 ? 0 : 1))
    .text((d) => d.label);
}

function tipHtml(d) {
  const c = CERTAINTY[d.c];
  const r = d.raw;
  const refs = (r.refs || []).slice(0, 4).map((x) => x.label).join(" &middot; ");
  return `<b>${esc(d.label)}</b>
    <div class="meta">${span(d.a, d.b)} &middot;
      <span style="color:${c.color}">${c.label}</span>
      ${r.role ? ` &middot; ${esc(r.role)}` : ""}</div>
    ${r.note ? `<div style="margin-top:6px">${esc(r.note)}</div>` : ""}
    ${refs ? `<div class="meta" style="margin-top:6px">${refs}</div>` : ""}`;
}

async function detail(d) {
  const r = d.raw, c = CERTAINTY[d.c];
  const box = document.getElementById("detail");
  box.innerHTML = `<h2>Selection</h2>
    <div style="font:600 16px/1.3 var(--serif);margin-bottom:4px">${esc(d.label)}</div>
    <div style="color:var(--muted);font-size:12.5px">${span(d.a, d.b)}${r.role ? " &middot; " + esc(r.role) : ""}</div>
    <div style="margin:8px 0"><span class="pill" style="color:${c.color}">${c.label}</span></div>
    <p class="note">${esc(c.hint)}</p>
    ${r.note ? `<p style="font-size:13px;color:var(--ink)">${esc(r.note)}</p>` : ""}
    ${r.places?.length ? `<h2>Places</h2><div style="font-size:12.5px">${
      r.places.map((p) => `<a href="atlas.html#place=${encodeURIComponent(p.name)}">${esc(p.name)}</a>`).join(", ")}</div>` : ""}
    ${r.refs?.length ? `<h2>References</h2><div id="refs"></div>` : ""}`;
  const holder = box.querySelector("#refs");
  if (!holder) return;
  for (const ref of r.refs) {
    const txt = await verseText(ref.osis);
    holder.insertAdjacentHTML("beforeend", `
      <div style="margin-bottom:11px">
        <a class="ref" href="reader.html#${ref.osis}">${esc(ref.label)}</a>
        <div class="verse-text" style="font-size:13px;margin-top:2px">${txt ?? ""}</div>
      </div>`);
  }
}

document.getElementById("fit").onclick = () => setDomain(-4100, 1700);
document.getElementById("focus").onclick = () => setDomain(-1200, 150);
function setDomain(a, b) {
  const k = (x0.domain()[1] - x0.domain()[0]) / (b - a);
  const tx = x0.range()[0] - x0(a) * k;
  d3.select(scroller).transition().duration(650)
    .call(zoom.transform, d3.zoomIdentity.translate(tx, 0).scale(k));
}

resize();
