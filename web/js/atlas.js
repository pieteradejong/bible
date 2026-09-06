// Geography: every geolocatable place the Bible names, plus the routes.
// Marker colour is scholarly confidence in the identification, not importance,
// so the map shows where the ancient world is genuinely unlocated.
import { load, shell, esc, readable, books, verseText } from "./common.js";

shell("Atlas");

document.body.insertAdjacentHTML("beforeend", `
  <main>
    <aside>
      <div class="control">
        <label for="q">Find a place</label>
        <input type="search" id="q" placeholder="Capernaum, Nineveh, Tarshish...">
        <div id="results" style="margin-top:6px;font-size:12.5px"></div>
      </div>
      <h2>Where nobody knows</h2>
      <div class="checks">
        <label title="Places whose extent scholarship cannot fix">
          <input type="checkbox" id="uncertainty">
          Draw uncertainty fields
          <span class="count">${Object.keys(uncertainty).length}</span>
        </label>
      </div>
      <p class="hint">For places like Assyria, Amalek and Bashan the gazetteer
        ships nested confidence contours rather than a location. Drawn as a
        graded field, darkest where scholarship agrees.</p>
      <h2>Time</h2>
      <div class="control">
        <label><input type="checkbox" id="timeOn"> Filter by date</label>
        <input type="range" id="time" min="${TIME_MIN}" max="${TIME_MAX}"
               value="${TIME_MAX}" step="5" disabled>
        <div class="hint" id="timeLabel">off &mdash; showing every place</div>
      </div>
      <h2>Shapes</h2>
      <div class="checks" id="shapes"></div>
      <p class="hint">Drawn as areas and lines rather than points, simplified from
        the gazetteer's own geometry. Regions are off by default: many are
        low-confidence bounding areas and they overlap heavily.</p>
      <h2>Routes</h2>
      <div class="checks" id="journeys"></div>
      <h2>Where mentioned</h2>
      <div class="control">
        <select id="scope">
          <option value="all">Anywhere in the Bible</option>
          <option value="OT">Old Testament only</option>
          <option value="NT">New Testament only</option>
          <option value="both">Both testaments</option>
        </select>
      </div>
      <div class="control">
        <label for="book">In a particular book</label>
        <select id="book"><option value="">any book</option></select>
      </div>
      <h2>How sure is the location?</h2>
      <div class="checks" id="conf"></div>
      <label class="checks" style="margin-top:8px">
        <input type="checkbox" id="contested">
        Only places with rival sites
        <span class="count" id="contestedN"></span>
      </label>
      <h2>Kind of place</h2>
      <div class="control"><select id="type"><option value="">any kind</option></select></div>
      <div class="control">
        <label>Mentioned at least <b id="minLabel">1</b> time(s)</label>
        <input type="range" id="min" min="1" max="60" value="1">
      </div>
      <p class="hint" id="shown"></p>
    </aside>
    <div class="stage"><div id="map" style="position:absolute;inset:0"></div></div>
    <aside class="right" id="detail"><h2>Selection</h2>
      <p class="note">Click a marker, or a stop on a route.</p></aside>
  </main>`);

const [places, meta, journeys, verses, BOOKS, geometry, uncertainty, timeline] =
  await Promise.all([
    load("places.json"), load("places_meta.json"), load("journeys.json"),
    load("places_verses.json"), books(), load("geometry.json"),
    load("uncertainty.json"), load("timeline.json"),
  ]);

// Events that carry both a date and a resolved coordinate, for the time scrub.
const DATED = timeline.events
  .filter((e) => e.places?.length)
  .map((e) => ({ ...e, end: e.end ?? e.start }))
  .sort((a, b) => a.start - b.start);
const TIME_MIN = Math.min(...DATED.map((e) => e.start));
const TIME_MAX = Math.max(...DATED.map((e) => e.end));

const CONF = {
  certain:  { c: "#5eb87a", label: "Certain",   hint: "No substantial doubt among the sources." },
  likely:   { c: "#6d9fe0", label: "Likely",    hint: "The sources lean one way." },
  possible: { c: "#e0a458", label: "Possible",  hint: "Tentative; proposed by only some sources." },
  disputed: { c: "#d9736a", label: "Disputed",  hint: "The sources argue against the leading identification." },
  unknown:  { c: "#7b736c", label: "Unrecorded", hint: "The source data records no confidence vote." },
};

const S = {
  conf: new Set(Object.keys(CONF)), scope: "all", book: "", type: "",
  min: 1, contested: false, journeys: new Set(journeys.map((j) => j.id)),
  shapes: new Set(["river", "body of water"]),
  uncertainty: false,
  timeAt: null,          // null = time filter off
};

// Shapes worth drawing as shapes. A settlement is a dot; Judea is not.
const SHAPE_KINDS = {
  "river":         { c: "#58a8c4", label: "Rivers" },
  "body of water": { c: "#4e93b8", label: "Seas and lakes" },
  "region":        { c: "#a98bd6", label: "Regions" },
  "valley":        { c: "#8d8378", label: "Valleys and wadis" },
};

// ------------------------------------------------------------------ the map
const map = L.map("map", { zoomControl: true, worldCopyJump: false })
  .setView([32.0, 35.3], 6);
L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
  attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
  maxZoom: 14, className: "basemap",
}).addTo(map);

const fieldLayer = L.layerGroup().addTo(map);   // uncertainty, furthest back
const shapeLayer = L.layerGroup().addTo(map);
const eventLayer = L.layerGroup().addTo(map);
const placeLayer = L.layerGroup().addTo(map);
const routeLayer = L.layerGroup().addTo(map);
const byName = new Map(places.map((p) => [p.name, p]));
const byId = new Map(places.map((p) => [p.id, p]));

// ----------------------------------------------------------------- controls
document.getElementById("conf").innerHTML = Object.entries(CONF).map(([k, v]) => {
  const n = places.filter((p) => p.conf === k).length;
  return `<label title="${esc(v.hint)}"><input type="checkbox" data-k="${k}" checked>
    <span class="swatch" style="--c:${v.c}"></span>${v.label}
    <span class="count">${n}</span></label>`;
}).join("");
document.getElementById("conf").addEventListener("change", (e) => {
  e.target.checked ? S.conf.add(e.target.dataset.k) : S.conf.delete(e.target.dataset.k);
  refresh();
});

document.getElementById("type").innerHTML +=
  meta.types.filter(([, n]) => n >= 3)
    .map(([t, n]) => `<option value="${esc(t)}">${esc(t)} (${n})</option>`).join("");
document.getElementById("book").innerHTML +=
  BOOKS.map((b) => `<option value="${b.i}">${esc(b.name)}</option>`).join("");
document.getElementById("contestedN").textContent = meta.contested;

document.getElementById("uncertainty").addEventListener("change", (e) => {
  S.uncertainty = e.target.checked;
  drawFields();
});

const timeSlider = document.getElementById("time");
document.getElementById("timeOn").addEventListener("change", (e) => {
  timeSlider.disabled = !e.target.checked;
  S.timeAt = e.target.checked ? +timeSlider.value : null;
  drawEvents();
});
timeSlider.addEventListener("input", (e) => {
  S.timeAt = +e.target.value;
  drawEvents();
});

document.getElementById("shapes").innerHTML = Object.entries(SHAPE_KINDS).map(([k, v]) => {
  const n = Object.values(geometry).filter((x) => x.type === k).length;
  return `<label><input type="checkbox" data-s="${k}"${S.shapes.has(k) ? " checked" : ""}>
    <span class="swatch" style="--c:${v.c}"></span>${v.label}
    <span class="count">${n}</span></label>`;
}).join("");
document.getElementById("shapes").addEventListener("change", (e) => {
  const k = e.target.dataset.s;
  e.target.checked ? S.shapes.add(k) : S.shapes.delete(k);
  drawShapes();
});

document.getElementById("journeys").innerHTML = journeys.map((j) => `
  <label><input type="checkbox" data-j="${j.id}" checked>
    <span class="swatch" style="--c:${routeColor(j)}"></span>${esc(j.label)}
    <span class="count">${j.stops.length}</span></label>`).join("");
document.getElementById("journeys").addEventListener("change", (e) => {
  const id = e.target.dataset.j;
  e.target.checked ? S.journeys.add(id) : S.journeys.delete(id);
  drawRoutes();
});

const bind = (id, key, cast = (v) => v) =>
  document.getElementById(id).addEventListener("change", (e) => {
    S[key] = cast(e.target.type === "checkbox" ? e.target.checked : e.target.value);
    refresh();
  });
bind("scope", "scope"); bind("book", "book"); bind("type", "type");
bind("contested", "contested");
document.getElementById("min").addEventListener("input", (e) => {
  S.min = +e.target.value;
  document.getElementById("minLabel").textContent = S.min;
  refresh();
});

// ------------------------------------------------------------------ drawing
function visible() {
  return places.filter((p) => {
    if (!S.conf.has(p.conf)) return false;
    if (p.n < S.min) return false;
    if (S.contested && p.alts < 2) return false;
    if (S.type && p.type !== S.type) return false;
    if (S.book !== "" && !(S.book in p.books)) return false;
    if (S.scope === "OT" && p.t === "NT") return false;
    if (S.scope === "NT" && p.t === "OT") return false;
    if (S.scope === "both" && p.t !== "both") return false;
    return true;
  });
}

const radius = (n) => 3 + Math.sqrt(n) * 1.15;

function refresh(withShapes = true) {
  placeLayer.clearLayers();
  const vis = visible();
  for (const p of vis) {
    const m = L.circleMarker([p.lat, p.lon], {
      radius: radius(p.n), color: CONF[p.conf].c, weight: 1.2,
      fillColor: CONF[p.conf].c, fillOpacity: 0.32,
    });
    m.bindTooltip(`${esc(p.disp)} <span style="opacity:.6">${p.n}&times;</span>`,
                  { direction: "top", offset: [0, -4] });
    m.on("click", () => select(p));
    m.addTo(placeLayer);
  }
  if (withShapes && typeof drawShapes === "function") drawShapes();
  document.getElementById("shown").textContent =
    `${vis.length} of ${places.length} places shown; ` +
    `${meta.count} geolocated out of the ${meta.count + meta.ungeolocated} in the gazetteer.`;
}

function drawShapes() {
  shapeLayer.clearLayers();
  const allowed = new Set(visible().map((p) => p.id));
  for (const [id, sh] of Object.entries(geometry)) {
    if (!S.shapes.has(sh.type)) continue;
    if (!allowed.has(id)) continue;
    const style = SHAPE_KINDS[sh.type];
    const area = sh.kind === "area";
    const layer = area
      ? L.polygon(sh.rings, {
          color: style.c, weight: 0.8, opacity: 0.3,
          fillColor: style.c, fillOpacity: 0.035, interactive: true })
      : L.polyline(sh.rings, {
          color: style.c, weight: 1.6, opacity: 0.8, interactive: true });
    layer.bindTooltip(`${esc(sh.name)} <span style="opacity:.6">${esc(sh.type)}</span>`,
                      { sticky: true });
    const p = byId.get(id);
    if (p) layer.on("click", () => select(p));
    layer.addTo(shapeLayer);
  }
}

// Nested contours, broadest and faintest on the outside. The point is that the
// eye should read "somewhere around here", not "at this pin".
function drawFields() {
  fieldLayer.clearLayers();
  if (!S.uncertainty) return;
  for (const [id, u] of Object.entries(uncertainty)) {
    const span = Math.max(u.max - u.min, 1);
    for (const band of u.bands) {
      const t = (band.conf - u.min) / span;           // 0 outermost, 1 innermost
      L.polygon(band.ring, {
        stroke: false,
        fillColor: "#e0a458",
        fillOpacity: 0.045 + t * 0.10,
        interactive: t > 0.85,                        // only the core takes clicks
      }).bindTooltip(`<b>${esc(u.name)}</b><br>confidence ${band.conf} of ${u.max}`,
                     { sticky: true })
        .addTo(fieldLayer);
    }
  }
}

// Events dated at or before the slider position, so dragging it plays the
// narrative forward across the map.
function drawEvents() {
  eventLayer.clearLayers();
  const label = document.getElementById("timeLabel");
  if (S.timeAt == null) {
    label.textContent = "off — showing every place";
    placeLayer.addTo(map);
    return;
  }
  map.removeLayer(placeLayer);
  const y = S.timeAt;
  const shown = DATED.filter((e) => e.start <= y);
  for (const e of shown) {
    const age = Math.min((y - e.start) / 400, 1);      // fade with distance in time
    for (const pl of e.places) {
      L.circleMarker([pl.lat, pl.lon], {
        radius: 5 - age * 2, color: "#e0a458", weight: 1.2,
        fillColor: "#e0a458", fillOpacity: 0.55 - age * 0.4, opacity: 1 - age * 0.6,
      }).bindTooltip(`<b>${esc(e.label)}</b><br>${yearLabel(e.start)}`,
                     { direction: "top" })
        .addTo(eventLayer);
    }
  }
  const latest = shown.at(-1);
  label.innerHTML = `<b>${yearLabel(y)}</b> &mdash; ${shown.length} of ${DATED.length}
    dated events so far${latest ? `<br>latest: ${esc(latest.label)}` : ""}
    <br><span style="color:var(--faint)">only curated events carry dates, so this
    is sparser than the full atlas</span>`;
}

const yearLabel = (y) => (y < 0 ? `${-y} BCE` : `${y} CE`);

function routeColor(j) {
  return { amber: "#e0a458", red: "#d9736a", slate: "#8d8378", violet: "#a98bd6",
           blue: "#6d9fe0", green: "#5eb87a", teal: "#58b0b8", orange: "#d98c4a" }[j.color]
    ?? "#e0a458";
}

function drawRoutes() {
  routeLayer.clearLayers();
  for (const j of journeys) {
    if (!S.journeys.has(j.id)) continue;
    const c = routeColor(j);
    const pts = j.stops.map((s) => [s.lat, s.lon]);
    L.polyline(pts, { color: c, weight: 2.2, opacity: 0.8, dashArray: j.certainty === "disputed" ? "6 5" : null })
      .bindTooltip(`${esc(j.label)}`, { sticky: true }).addTo(routeLayer);
    j.stops.forEach((s, i) => {
      L.marker([s.lat, s.lon], {
        icon: L.divIcon({
          className: "", iconSize: [18, 18], iconAnchor: [9, 9],
          html: `<div style="width:18px;height:18px;border-radius:50%;background:${c};
            color:#12100e;font:600 10px/18px var(--sans);text-align:center;
            border:1.5px solid #12100e;box-shadow:0 1px 4px rgba(0,0,0,.6)">${i + 1}</div>`,
        }),
      }).bindTooltip(`<b>${i + 1}. ${esc(s.label)}</b><br>${esc(j.label)}`,
                     { direction: "top", offset: [0, -8] })
        .on("click", () => selectStop(j, s, i))
        .addTo(routeLayer);
    });
  }
}

// ----------------------------------------------------------------- selection
async function select(p) {
  const box = document.getElementById("detail");
  const refs = verses[p.id] ?? [];
  const perBook = Object.entries(p.books)
    .sort((a, b) => b[1] - a[1])
    .map(([i, n]) => `${esc(BOOKS[+i].name)} <span style="color:var(--faint)">${n}</span>`)
    .join(" &middot; ");
  box.innerHTML = `<h2>Place</h2>
    <div style="font:600 17px/1.3 var(--serif)">${esc(p.disp)}</div>
    <div style="color:var(--muted);font-size:12.5px;margin-top:2px">
      ${esc(p.type)}${p.kind ? ` &middot; ${esc(p.kind)}-made` : ""} &middot;
      ${p.lat.toFixed(3)}, ${p.lon.toFixed(3)}</div>
    <div style="margin:9px 0">
      <span class="pill" style="color:${CONF[p.conf].c}">${CONF[p.conf].label}</span>
      ${p.alts > 1 ? `<span class="pill" style="color:var(--disputed);margin-left:5px">${p.alts} rival sites</span>` : ""}
    </div>
    <p class="note">${esc(CONF[p.conf].hint)}${p.alts > 1
      ? ` Scholarship has proposed ${p.alts} different modern locations for this place; the leading one carries ${Math.round(p.share * 100)}% of the vote and is what the marker shows.`
      : ""}</p>
    ${geometry[p.id] ? `<p class="hint">Drawn on the map as
      ${geometry[p.id].kind === "area" ? "an area" : "a line"}, not just a point.</p>` : ""}
    <h2>Mentioned ${p.n} time${p.n === 1 ? "" : "s"}</h2>
    <div style="font-size:12.5px;line-height:1.7">${perBook}</div>
    <h2>First mention</h2>
    <div id="first"></div>
    <h2>All references</h2>
    <div style="font-size:11.5px;line-height:1.9;word-spacing:.1em">
      ${refs.map((r) => `<a class="ref" href="reader.html#${r}">${esc(readable(r, BOOKS))}</a>`).join(" ")}
    </div>`;
  const txt = await verseText(p.first);
  box.querySelector("#first").innerHTML = `
    <a class="ref" href="reader.html#${p.first}">${esc(readable(p.first, BOOKS))}</a>
    <div class="verse-text" style="font-size:13.5px;margin-top:3px">${txt ?? ""}</div>`;
  map.setView([p.lat, p.lon], Math.max(map.getZoom(), 8), { animate: true });
}

async function selectStop(j, s, i) {
  const box = document.getElementById("detail");
  const txt = await verseText(s.ref);
  box.innerHTML = `<h2>Route stop</h2>
    <div style="font:600 17px/1.3 var(--serif)">${i + 1}. ${esc(s.label)}</div>
    <div style="color:var(--muted);font-size:12.5px">${esc(j.label)}</div>
    <div style="margin:9px 0"><span class="pill" style="color:${routeColor(j)}">${esc(j.certainty)} route</span></div>
    <p class="note">${esc(j.note ?? "")}</p>
    <a class="ref" href="reader.html#${s.ref}">${esc(readable(s.ref, BOOKS))}</a>
    <div class="verse-text" style="font-size:13.5px;margin-top:4px">${txt ?? ""}</div>
    ${byName.has(s.place) ? `<div style="margin-top:12px"><button id="more">Show everything about ${esc(s.label)}</button></div>` : ""}`;
  box.querySelector("#more")?.addEventListener("click", () => select(byName.get(s.place)));
}

// -------------------------------------------------------------------- search
const q = document.getElementById("q"), results = document.getElementById("results");
q.addEventListener("input", () => {
  const v = q.value.trim().toLowerCase();
  if (v.length < 2) { results.innerHTML = ""; return; }
  const hits = places.filter((p) => p.disp.toLowerCase().includes(v))
    .sort((a, b) => b.n - a.n).slice(0, 12);
  results.innerHTML = hits.length
    ? hits.map((p) => `<a href="#" data-id="${p.id}">${esc(p.disp)}</a>
        <span style="color:var(--faint)">${p.n}</span><br>`).join("")
    : `<span style="color:var(--faint)">no match</span>`;
});
results.addEventListener("click", (e) => {
  const a = e.target.closest("a[data-id]");
  if (!a) return;
  e.preventDefault();
  const p = byId.get(a.dataset.id);
  if (p) select(p);
});

// deep link: atlas.html#place=Capernaum
const hash = decodeURIComponent(location.hash.replace(/^#place=/, ""));
if (hash && byName.has(hash)) select(byName.get(hash));

refresh();
drawRoutes();
drawFields();
