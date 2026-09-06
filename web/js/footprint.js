// Where each book's world sits, two ways.
//
//   drift      the mention-weighted centre of every book, connected in
//              canonical order: the biblical world's focus travelling from
//              Mesopotamia to Canaan, down to Egypt, and out to the Mediterranean
//   multiples  66 thumbnails on one shared extent, so they are comparable
//
// Both are drawn on a plain equirectangular projection rather than a slippy
// map: the point is comparison between books, not navigation.
import { load, shell, esc, showTip, moveTip, hideTip } from "./common.js";

shell("Footprint");

const DIV = {
  "Torah": "#e0a458", "History": "#c98a5e", "Wisdom": "#d6b25c",
  "Major Prophets": "#a98bd6", "Minor Prophets": "#8f79c4",
  "Gospels": "#5eb87a", "Acts": "#57b0a0", "Pauline": "#6d9fe0",
  "General": "#58a8c4", "Apocalyptic": "#d9736a",
};

document.body.insertAdjacentHTML("beforeend", `
  <main>
    <aside>
      <h2>View</h2>
      <div class="control">
        <select id="mode">
          <option value="drift">Drift &mdash; each book's centre of gravity</option>
          <option value="multiples">Small multiples &mdash; one map per book</option>
        </select>
      </div>
      <h2>Divisions</h2>
      <div class="checks" id="divs"></div>
      <div class="control" style="margin-top:12px">
        <label><input type="checkbox" id="line" checked> Connect in canonical order</label>
      </div>
      <p class="note" id="explain"></p>
      <h2>Widest and tightest</h2>
      <div id="spread" style="font-size:12px;line-height:1.8"></div>
      <p class="hint">Spread is the mention-weighted mean distance from a book's
        own centre &mdash; a book that stays in one valley against one that
        crosses an empire. Books naming fewer than three places are left out:
        their spread is near zero by definition, not by geography.</p>
    </aside>
    <div class="stage"><svg id="chart"></svg></div>
    <aside class="right" id="detail"><h2>Selection</h2>
      <p class="note">Hover or click a book.</p></aside>
  </main>`);

const geo = await load("geostats.json");
const located = geo.books.filter((b) => b.places > 0);
const S = { mode: "drift", divs: new Set(Object.keys(DIV)), line: true };

document.getElementById("divs").innerHTML = Object.keys(DIV).map((d) => {
  const n = geo.books.filter((b) => b.division === d).length;
  return `<label><input type="checkbox" data-d="${esc(d)}" checked>
    <span class="swatch" style="--c:${DIV[d]}"></span>${esc(d)}
    <span class="count">${n}</span></label>`;
}).join("");
document.getElementById("divs").addEventListener("change", (e) => {
  const d = e.target.dataset.d;
  e.target.checked ? S.divs.add(d) : S.divs.delete(d);
  draw();
});
document.getElementById("mode").addEventListener("change", (e) => {
  S.mode = e.target.value; draw();
});
document.getElementById("line").addEventListener("change", (e) => {
  S.line = e.target.checked; draw();
});

const bySpread = located.filter((b) => b.places >= 3)
  .sort((a, b) => b.spread - a.spread);
document.getElementById("spread").innerHTML =
  [...bySpread.slice(0, 4), null, ...bySpread.slice(-4)].map((b) => b === null
    ? `<div style="color:var(--faint);padding:3px 0">&middot; &middot; &middot;</div>`
    : `<div style="display:flex;gap:8px"><span style="flex:1 1 auto">${esc(b.name)}</span>
       <span style="color:var(--accent);font:11px var(--mono)">${Math.round(b.spread)} km</span></div>`
  ).join("");

// ---------------------------------------------------------------- projection
const svg = d3.select("#chart");
const stage = document.querySelector(".stage");
let W = 0, H = 0;

function resize() {
  W = stage.clientWidth; H = stage.clientHeight;
  svg.attr("width", W).attr("height", H);
  draw();
}
new ResizeObserver(resize).observe(stage);

/** Equirectangular fit of a [south, west, north, east] box into a w x h box. */
function projector(bounds, w, h, pad = 10) {
  const [s, west, n, e] = bounds;
  const sx = (w - pad * 2) / Math.max(e - west, 1e-6);
  const sy = (h - pad * 2) / Math.max(n - s, 1e-6);
  const k = Math.min(sx, sy);
  const ox = pad + ((w - pad * 2) - (e - west) * k) / 2;
  const oy = pad + ((h - pad * 2) - (n - s) * k) / 2;
  return (lat, lon) => [ox + (lon - west) * k, oy + (n - lat) * k];
}

function visible() {
  return located.filter((b) => S.divs.has(b.division));
}

function draw() {
  if (!W) return;
  svg.selectAll("*").remove();
  document.getElementById("explain").innerHTML = S.mode === "drift"
    ? "Each dot is one book, placed at the mention-weighted centre of every place it names, sized by how many places that is. Read the line in canonical order and the focus travels: Mesopotamia, Canaan, Egypt and Sinai, back to the Levant, then out across the Mediterranean."
    : "One thumbnail per book, all on the same extent and projection, so the sizes and positions are honestly comparable. The Old Testament clusters on the Levant; the New Testament spills across the Mediterranean.";
  S.mode === "drift" ? drawDrift() : drawMultiples();
}

// -------------------------------------------------------------------- drift
function drawDrift() {
  const shown = visible();
  if (!shown.length) return;
  // Fit to the centres plus a margin, not to every place in the Bible: the full
  // extent runs from Spain to Persia and squeezes all 61 centres into a dot.
  const pad = 1.2;
  const box = [
    Math.min(...shown.map((b) => b.lat)) - pad,
    Math.min(...shown.map((b) => b.lon)) - pad,
    Math.max(...shown.map((b) => b.lat)) + pad,
    Math.max(...shown.map((b) => b.lon)) + pad,
  ];
  const project = projector(box, W, H, 40);
  const g = svg.append("g");

  // A faint hint of every place, so the centres have context.
  const all = svg.insert("g", ":first-child");
  for (const b of located) {
    for (const [lat, lon] of (b.pts ?? []).slice(0, 80)) {
      if (lat < box[0] || lat > box[2] || lon < box[1] || lon > box[3]) continue;
      const [x, y] = project(lat, lon);
      all.append("circle").attr("cx", x).attr("cy", y).attr("r", 0.8)
        .attr("fill", "var(--faint)").attr("fill-opacity", 0.22);
    }
  }

  if (S.line) {
    const path = shown.map((b) => project(b.lat, b.lon));
    g.append("path")
      .attr("d", d3.line().curve(d3.curveCatmullRom.alpha(0.5))(path))
      .attr("fill", "none").attr("stroke", "var(--line)")
      .attr("stroke-width", 1.4).attr("stroke-opacity", 0.9);
  }

  const r = d3.scaleSqrt().domain([1, d3.max(located, (b) => b.places)]).range([3, 15]);
  g.selectAll("circle.book").data(shown).join("circle").attr("class", "book")
    .attr("cx", (b) => project(b.lat, b.lon)[0])
    .attr("cy", (b) => project(b.lat, b.lon)[1])
    .attr("r", (b) => r(b.places))
    .attr("fill", (b) => DIV[b.division] ?? "#8d8378")
    .attr("fill-opacity", 0.5)
    .attr("stroke", (b) => DIV[b.division] ?? "#8d8378")
    .style("cursor", "pointer")
    .on("mouseenter", (ev, b) => showTip(ev, tip(b)))
    .on("mousemove", moveTip).on("mouseleave", hideTip)
    .on("click", (ev, b) => detail(b));

  // Label only the books that anchor the story, or the chart becomes soup.
  // Label only the books that anchor the story, and push labels apart when the
  // centres crowd together -- which they do, badly, around Jerusalem.
  const anchors = ["Gen", "Exod", "Josh", "1Kgs", "Ezra", "Matt", "Acts", "Rev"];
  const labels = shown.filter((b) => anchors.includes(b.osis))
    .map((b) => {
      const [x, y] = project(b.lat, b.lon);
      return { b, x: x + r(b.places) + 5, y: y + 3 };
    })
    .sort((a, c) => a.y - c.y);
  const MIN_GAP = 13;
  for (let i = 1; i < labels.length; i++) {
    if (labels[i].y - labels[i - 1].y < MIN_GAP) {
      labels[i].y = labels[i - 1].y + MIN_GAP;
    }
  }
  const lg = g.append("g");
  for (const l of labels) {
    const [cx, cy] = project(l.b.lat, l.b.lon);
    lg.append("line").attr("x1", cx).attr("y1", cy)
      .attr("x2", l.x - 2).attr("y2", l.y - 3)
      .attr("stroke", "var(--line)").attr("stroke-width", 0.8);
    lg.append("text").attr("x", l.x).attr("y", l.y)
      .attr("font-size", 11).attr("fill", "var(--ink)")
      .text(l.b.name);
  }
}

// ---------------------------------------------------------------- multiples
function drawMultiples() {
  const shown = geo.books.filter((b) => S.divs.has(b.division));
  const cols = Math.max(4, Math.floor(W / 132));
  const cw = W / cols, ch = cw * 0.82;
  const g = svg.append("g");
  svg.attr("height", Math.max(H, Math.ceil(shown.length / cols) * ch + 20));

  shown.forEach((b, i) => {
    const gx = (i % cols) * cw, gy = Math.floor(i / cols) * ch;
    const cell = g.append("g").attr("transform", `translate(${gx},${gy})`)
      .style("cursor", "pointer")
      .on("mouseenter", (ev) => showTip(ev, tip(b)))
      .on("mousemove", moveTip).on("mouseleave", hideTip)
      .on("click", () => detail(b));

    cell.append("rect").attr("width", cw - 6).attr("height", ch - 22)
      .attr("rx", 4).attr("fill", "var(--panel)")
      .attr("stroke", "var(--line)");

    if (b.places) {
      // Same extent for every thumbnail, so they compare honestly.
      const project = projector(geo.bounds, cw - 6, ch - 22, 5);
      const colour = DIV[b.division] ?? "#8d8378";
      for (const [lat, lon, n] of b.pts ?? []) {
        const [x, y] = project(lat, lon);
        cell.append("circle").attr("cx", x).attr("cy", y)
          .attr("r", Math.min(1 + Math.sqrt(n) * 0.5, 4))
          .attr("fill", colour).attr("fill-opacity", 0.55);
      }
    } else {
      cell.append("text").attr("x", (cw - 6) / 2).attr("y", (ch - 22) / 2)
        .attr("text-anchor", "middle").attr("fill", "var(--faint)")
        .attr("font-size", 10).text("no places named");
    }

    cell.append("text").attr("x", 2).attr("y", ch - 8)
      .attr("font-size", 10).attr("fill", "var(--muted)")
      .text(`${b.name}${b.places ? ` ${b.places}` : ""}`);
  });
}

function tip(b) {
  return `<b>${esc(b.name)}</b>
    <div class="meta">${esc(b.division)} &middot;
      ${b.testament === "OT" ? "Old" : "New"} Testament</div>
    ${b.places
      ? `<div class="meta" style="margin-top:5px">${b.places} places,
         ${b.mentions} mentions &middot; spread ${Math.round(b.spread)} km</div>`
      : `<div class="meta" style="margin-top:5px">names no mappable place</div>`}`;
}

function detail(b) {
  document.getElementById("detail").innerHTML = `<h2>Book</h2>
    <div style="font:600 17px/1.3 var(--serif)">${esc(b.name)}</div>
    <div style="color:var(--muted);font-size:12.5px">${esc(b.division)} &middot;
      ${b.testament === "OT" ? "Old" : "New"} Testament</div>
    ${b.places ? `
      <h2>Geography</h2>
      <div style="font-size:13px;line-height:1.9">
        <div>${b.places} distinct places, named ${b.mentions} times</div>
        <div>centre ${b.lat.toFixed(2)}, ${b.lon.toFixed(2)}</div>
        <div>spread ${Math.round(b.spread)} km from that centre</div>
      </div>
      <div style="margin-top:14px">
        <a href="atlas.html">Open the atlas</a> &middot;
        <a href="reader.html#${b.osis}.1.1">Read ${esc(b.name)} 1</a>
      </div>`
      : `<p class="note">This book names no place that can be put on a map.</p>`}`;
}

resize();
