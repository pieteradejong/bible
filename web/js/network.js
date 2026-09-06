// The 344,798 cross-references OpenBible's readers have voted on, drawn two ways:
// an arc diagram over all 1,189 chapters, and a 66x66 book matrix.
import { load, shell, esc, books, verseText, readable, showTip, moveTip, hideTip } from "./common.js";
import { alphaFor } from "./lib/layout.js";

shell("Cross-references");

document.body.insertAdjacentHTML("beforeend", `
  <main>
    <aside>
      <h2>View</h2>
      <div class="control">
        <select id="mode">
          <option value="arcs">Arc diagram - every chapter</option>
          <option value="matrix">Book matrix - who cites whom</option>
        </select>
      </div>
      <h2>Direction</h2>
      <div class="checks" id="dirs"></div>
      <div class="control" style="margin-top:12px">
        <label>Show links with at least <b id="minLabel">2</b> reference(s)</label>
        <input type="range" id="min" min="1" max="30" value="2">
        <p class="hint">127,297 of the 191,620 chapter pairs are linked just
          once. At 1 the picture is a solid wall; from 2 upward the structure
          appears.</p>
      </div>
      <h2>Colour</h2>
      <div class="control">
        <select id="colorBy">
          <option value="target">By book cited</option>
          <option value="direction">By direction across the testaments</option>
        </select>
      </div>
      <h2>Jump to a book</h2>
      <div class="control"><select id="book"><option value="">-</option></select></div>
      <p class="hint" id="stats"></p>
      <p class="note" id="explain"></p>
    </aside>
    <div class="stage">
      <canvas id="base" style="position:absolute;inset:0"></canvas>
      <canvas id="hi" style="position:absolute;inset:0"></canvas>
      <svg id="ui" style="position:absolute;inset:0"></svg>
    </div>
    <aside class="right" id="detail"><h2>Selection</h2>
      <p class="note">Hover the strip along the bottom to light up one chapter's
      references. Click to pin it and read them.</p></aside>
  </main>`);

const [BOOKS, mat, chapters] = await Promise.all([
  books(), load("xref_books.json"), load("xref_chapters.json"),
]);

const DIVCOLORS = {
  "Torah": "#e0a458", "History": "#c98a5e", "Wisdom": "#d6b25c",
  "Major Prophets": "#a98bd6", "Minor Prophets": "#8f79c4",
  "Gospels": "#5eb87a", "Acts": "#57b0a0", "Pauline": "#6d9fe0",
  "General": "#58a8c4", "Apocalyptic": "#d9736a",
};

const DIRS = {
  "OT>OT": { label: "Old to Old", c: "#e0a458" },
  "OT>NT": { label: "Old to New", c: "#5eb87a" },
  "NT>OT": { label: "New to Old", c: "#6d9fe0" },
  "NT>NT": { label: "New to New", c: "#a98bd6" },
};

const S = { mode: "arcs", min: 2, colorBy: "target", dirs: new Set(Object.keys(DIRS)) };

// chapter offsets: cumulative index of every chapter in canonical order
const offset = [], chaptersOf = [];
let total = 0;
for (const b of BOOKS) {
  offset[b.i] = total;
  chaptersOf[b.i] = b.chapters;
  total += b.chapters;
}
const gidx = (b, c) => offset[b] + c - 1;

const dirOf = (fb, tb) =>
  `${BOOKS[fb].testament}>${BOOKS[tb].testament}`;

// ------------------------------------------------------------------ controls
document.getElementById("dirs").innerHTML = Object.entries(DIRS).map(([k, v]) => {
  const n = chapters.edges.filter((e) => dirOf(e[0], e[2]) === k).length;
  return `<label><input type="checkbox" data-k="${k}" checked>
    <span class="swatch" style="--c:${v.c}"></span>${v.label}
    <span class="count">${n.toLocaleString()}</span></label>`;
}).join("");
document.getElementById("dirs").addEventListener("change", (e) => {
  e.target.checked ? S.dirs.add(e.target.dataset.k) : S.dirs.delete(e.target.dataset.k);
  redraw();
});
document.getElementById("book").innerHTML +=
  BOOKS.map((b) => `<option value="${b.i}">${esc(b.name)}</option>`).join("");
document.getElementById("book").addEventListener("change", (e) => {
  if (e.target.value !== "") pick(+e.target.value, 1);
});
document.getElementById("min").addEventListener("input", (e) => {
  S.min = +e.target.value;
  document.getElementById("minLabel").textContent = S.min;
  redraw();
});
document.getElementById("colorBy").addEventListener("change", (e) => {
  S.colorBy = e.target.value; redraw();
});
document.getElementById("mode").addEventListener("change", (e) => {
  S.mode = e.target.value; resize();
});

document.getElementById("stats").textContent =
  `${mat.total.toLocaleString()} verse-level cross-references, collapsing to ` +
  `${chapters.edges.length.toLocaleString()} chapter-to-chapter links.`;
document.getElementById("explain").innerHTML =
  "Every arc is a pair of chapters readers have linked. 54% of links stay inside " +
  "the Old Testament and 25% inside the New; the remaining 21% cross between " +
  "them. Isolate those with the direction filter and the long arcs that survive " +
  "are the seam between the testaments.";

// -------------------------------------------------------------------- canvas
const stage = document.querySelector(".stage");
const base = document.getElementById("base"), hi = document.getElementById("hi");
const ui = d3.select("#ui");
let W = 0, H = 0, DPR = Math.min(devicePixelRatio || 1, 2);
const STRIP = 26, PADX = 16;

function resize() {
  W = stage.clientWidth; H = stage.clientHeight;
  for (const c of [base, hi]) {
    c.width = W * DPR; c.height = H * DPR;
    c.style.width = `${W}px`; c.style.height = `${H}px`;
    c.getContext("2d").setTransform(DPR, 0, 0, DPR, 0, 0);
  }
  ui.attr("width", W).attr("height", H);
  redraw();
}
new ResizeObserver(resize).observe(stage);

const X = (g) => PADX + (g / (total - 1)) * (W - 2 * PADX);
const BASE_Y = () => H - STRIP - 26;

function keep(e) {
  return e[4] >= S.min && S.dirs.has(dirOf(e[0], e[2]));
}
function edgeColor(e, alpha) {
  const c = S.colorBy === "direction"
    ? DIRS[dirOf(e[0], e[2])].c
    : DIVCOLORS[BOOKS[e[2]].division] ?? "#8d8378";
  return c + alpha;
}

function redraw() {
  if (!W) return;
  const ctx = base.getContext("2d");
  ctx.clearRect(0, 0, W, H);
  hi.getContext("2d").clearRect(0, 0, W, H);
  ui.selectAll("*").remove();
  if (S.mode === "arcs") { drawArcs(ctx); drawStrip(); }
  else drawMatrix();
}

function drawArcs(ctx) {
  const y = BASE_Y();
  ctx.lineWidth = 0.42;
  ctx.globalCompositeOperation = "lighter";
  // One Path2D per colour rather than per arc: there are ~190k arcs and only a
  // handful of colours, and stroking each arc separately is what makes this
  // kind of diagram slow.
  const shown = chapters.edges.filter(keep);
  const alpha = alphaFor(shown.length);
  const paths = new Map();
  let drawn = 0;
  for (const e of shown) {
    const x1 = X(gidx(e[0], e[1])), x2 = X(gidx(e[2], e[3]));
    if (Math.abs(x2 - x1) < 0.6) continue;
    const r = Math.abs(x2 - x1) / 2, cx = (x1 + x2) / 2;
    const col = edgeColor(e, alpha);
    let p = paths.get(col);
    if (!p) paths.set(col, (p = new Path2D()));
    p.ellipse(cx, y, r, Math.min(r, y - 8), 0, Math.PI, 0);
    drawn++;
  }
  for (const [col, p] of paths) { ctx.strokeStyle = col; ctx.stroke(p); }
  ctx.globalCompositeOperation = "source-over";
  ui.append("text").attr("x", PADX).attr("y", 20)
    .attr("fill", "var(--faint)").attr("font-size", 11)
    .text(`${drawn.toLocaleString()} arcs drawn`);
}

function drawStrip() {
  const y = BASE_Y();
  const g = ui.append("g");
  for (const b of BOOKS) {
    const x1 = X(offset[b.i]), x2 = X(offset[b.i] + chaptersOf[b.i] - 1);
    g.append("rect")
      .attr("x", x1).attr("y", y + 5).attr("width", Math.max(x2 - x1, 1.5))
      .attr("height", 14).attr("rx", 1.5)
      .attr("fill", DIVCOLORS[b.division] ?? "#8d8378")
      .attr("fill-opacity", 0.65)
      .attr("data-book", b.i).style("cursor", "crosshair");
    if (x2 - x1 > 22)
      g.append("text").attr("x", (x1 + x2) / 2).attr("y", y + 34)
        .attr("text-anchor", "middle").attr("fill", "var(--faint)")
        .attr("font-size", 9.5).attr("pointer-events", "none")
        .text(b.osis);
  }
  // Testament divide
  const div = X(offset[39]) - 3;
  g.append("line").attr("x1", div).attr("x2", div).attr("y1", 30).attr("y2", y + 24)
    .attr("stroke", "var(--line)").attr("stroke-dasharray", "3 4");
  g.append("text").attr("x", div - 6).attr("y", 44).attr("text-anchor", "end")
    .attr("fill", "var(--faint)").attr("font-size", 10.5).text("Old Testament");
  g.append("text").attr("x", div + 6).attr("y", 44)
    .attr("fill", "var(--faint)").attr("font-size", 10.5).text("New Testament");

  // A transparent hit strip: maps mouse x back to a chapter.
  g.append("rect").attr("x", PADX).attr("y", y + 2).attr("width", W - 2 * PADX)
    .attr("height", 22).attr("fill", "transparent").style("cursor", "crosshair")
    .on("mousemove", (ev) => {
      const gi = Math.round(((d3.pointer(ev)[0] - PADX) / (W - 2 * PADX)) * (total - 1));
      const b = BOOKS.findLast((bb) => offset[bb.i] <= gi);
      if (!b) return;
      const c = gi - offset[b.i] + 1;
      highlight(b.i, Math.min(Math.max(c, 1), chaptersOf[b.i]));
      showTip(ev, `<b>${esc(b.name)} ${Math.min(Math.max(c, 1), chaptersOf[b.i])}</b>
        <div class="meta">${esc(b.division)}</div>`);
    })
    .on("mouseleave", () => { hideTip(); hi.getContext("2d").clearRect(0, 0, W, H); })
    .on("click", (ev) => {
      const gi = Math.round(((d3.pointer(ev)[0] - PADX) / (W - 2 * PADX)) * (total - 1));
      const b = BOOKS.findLast((bb) => offset[bb.i] <= gi);
      if (b) pick(b.i, Math.min(Math.max(gi - offset[b.i] + 1, 1), chaptersOf[b.i]));
    });
}

function highlight(bi, ci) {
  const ctx = hi.getContext("2d");
  ctx.clearRect(0, 0, W, H);
  if (S.mode !== "arcs") return;
  const y = BASE_Y();
  ctx.lineWidth = 1.1;
  for (const e of chapters.edges) {
    const from = e[0] === bi && e[1] === ci, to = e[2] === bi && e[3] === ci;
    if ((!from && !to) || !keep(e)) continue;
    const x1 = X(gidx(e[0], e[1])), x2 = X(gidx(e[2], e[3]));
    const r = Math.abs(x2 - x1) / 2, cx = (x1 + x2) / 2;
    ctx.beginPath();
    ctx.ellipse(cx, y, r, Math.min(r, y - 8), 0, Math.PI, 0);
    ctx.strokeStyle = from ? "#f5e6c8dd" : "#6d9fe0cc";
    ctx.stroke();
  }
}

// ------------------------------------------------------------------- matrix
function drawMatrix() {
  const n = BOOKS.length;
  const pad = { t: 96, l: 104, r: 20, b: 20 };
  const size = Math.min(W - pad.l - pad.r, H - pad.t - pad.b);
  const cell = size / n;
  const g = ui.append("g").attr("transform", `translate(${pad.l},${pad.t})`);

  const vals = [];
  for (let i = 0; i < n; i++) for (let j = 0; j < n; j++) vals.push(mat.counts[i][j]);
  const scale = d3.scaleSequentialLog(d3.interpolateYlOrBr)
    .domain([1, d3.max(vals)]).clamp(true);

  for (let i = 0; i < n; i++) {
    for (let j = 0; j < n; j++) {
      const v = mat.counts[i][j];
      if (!v || v < S.min) continue;
      if (!S.dirs.has(dirOf(i, j))) continue;
      g.append("rect")
        .attr("x", j * cell).attr("y", i * cell)
        .attr("width", cell - 0.5).attr("height", cell - 0.5)
        .attr("fill", scale(v)).attr("fill-opacity", 0.85)
        .style("cursor", "pointer")
        .on("mouseenter", (ev) => showTip(ev,
          `<b>${esc(BOOKS[i].name)} &rarr; ${esc(BOOKS[j].name)}</b>
           <div class="meta">${v.toLocaleString()} references</div>`))
        .on("mousemove", moveTip).on("mouseleave", hideTip)
        .on("click", () => pick(i, 1));
    }
  }
  BOOKS.forEach((b, i) => {
    g.append("text").attr("x", -6).attr("y", i * cell + cell * 0.78)
      .attr("text-anchor", "end").attr("font-size", Math.min(cell * 0.85, 10))
      .attr("fill", b.testament === "NT" ? "var(--conventional)" : "var(--faint)")
      .text(b.osis);
    g.append("text")
      .attr("transform", `translate(${i * cell + cell * 0.75},-6) rotate(-90)`)
      .attr("font-size", Math.min(cell * 0.85, 10))
      .attr("fill", b.testament === "NT" ? "var(--conventional)" : "var(--faint)")
      .text(b.osis);
  });
  ui.append("text").attr("x", pad.l).attr("y", 26).attr("fill", "var(--muted)")
    .attr("font-size", 11.5)
    .text("rows: the book doing the referring   →   columns: the book referred to");
}

// ----------------------------------------------------------------- selection
async function pick(bi, ci) {
  highlight(bi, ci);
  const b = BOOKS[bi];
  const box = document.getElementById("detail");
  box.innerHTML = `<h2>Chapter</h2>
    <div style="font:600 17px/1.3 var(--serif)">${esc(b.name)} ${ci}</div>
    <div style="color:var(--muted);font-size:12.5px">${esc(b.division)} &middot;
      ${b.testament === "OT" ? "Old" : "New"} Testament</div>
    <div class="loading" style="position:static;padding:16px 0">loading references...</div>`;

  const file = await load(`xref/${b.osis}.json`).catch(() => null);
  if (!file) { box.insertAdjacentHTML("beforeend", `<p class="note">No outgoing references.</p>`); return; }

  const rows = Object.entries(file.refs)
    .filter(([k]) => +k.split(".")[0] === ci)
    .sort((a, b2) => +a[0].split(".")[1] - +b2[0].split(".")[1]);

  const outgoing = rows.reduce((s, [, v]) => s + v.length, 0);
  box.querySelector(".loading").remove();
  box.insertAdjacentHTML("beforeend", `
    <p class="hint">${outgoing.toLocaleString()} references out of this chapter,
      across ${rows.length} verse${rows.length === 1 ? "" : "s"}.
      Sorted by how many readers voted for each link.</p>`);

  for (const [vkey, list] of rows.slice(0, 40)) {
    const v = vkey.split(".")[1];
    const osis = `${b.osis}.${ci}.${v}`;
    const txt = await verseText(osis);
    box.insertAdjacentHTML("beforeend", `
      <div style="margin:14px 0 0;padding-top:10px;border-top:1px solid var(--line)">
        <a class="ref" href="reader.html#${osis}">${esc(b.name)} ${ci}:${v}</a>
        <div class="verse-text" style="font-size:13px;margin:3px 0 6px">${txt ?? ""}</div>
        <div style="font-size:11.5px;line-height:1.9">
          ${list.slice(0, 12).map((r) => {
            const t = `${BOOKS[r[0]].osis}.${r[1]}.${r[2]}`;
            return `<a class="ref" href="reader.html#${t}" title="${r[4]} votes"
              >${esc(BOOKS[r[0]].name)} ${r[1]}:${r[2]}${r[3] ? `-${r[3]}` : ""}</a>`;
          }).join(" &middot; ")}
          ${list.length > 12 ? `<span style="color:var(--faint)"> +${list.length - 12} more</span>` : ""}
        </div>
      </div>`);
  }
}

resize();
