// The text itself, with its links made walkable: every verse carries the
// references readers have drawn from it, and every place name is a map pin.
import { load, shell, esc, books, readable, parseOsis } from "./common.js";

shell("Reader");

document.body.insertAdjacentHTML("beforeend", `
  <main>
    <aside>
      <div class="control">
        <label for="book">Book</label>
        <select id="book"></select>
      </div>
      <div class="control">
        <label for="chapter">Chapter</label>
        <select id="chapter"></select>
      </div>
      <h2>Show</h2>
      <div class="checks">
        <label><input type="checkbox" id="showRefs" checked> Cross-references</label>
        <label><input type="checkbox" id="showPlaces" checked> Places on the map</label>
      </div>
      <h2>Compare translations</h2>
      <div class="checks" id="editions"></div>
      <p class="hint" id="edhint">Pick any and the same verse appears in each,
        under the KJV.</p>
      <div class="control" style="margin-top:12px">
        <label>At most <b id="topLabel">6</b> references per verse</label>
        <input type="range" id="top" min="1" max="20" value="6">
      </div>
      <h2>This chapter</h2>
      <p class="hint" id="chapstats"></p>
      <h2>Places here</h2>
      <div id="places" style="font-size:12.5px;line-height:1.8"></div>
      <p class="hint">Text: King James Version (public domain).
        References: OpenBible.info, ranked by reader votes.</p>
    </aside>
    <div class="stage" style="overflow-y:auto">
      <div id="text" style="max-width:760px;margin:0 auto;padding:26px 32px 80px"></div>
    </div>
    <aside class="right" id="peek">
      <h2>Linked verse</h2>
      <p class="note">Hover or click any reference in the margin to read it here
        without losing your place.</p>
    </aside>
  </main>`);

const [BOOKS, placeVerses, places, EDITIONS] = await Promise.all([
  books(), load("places_verses.json"), load("places.json"),
  load("translations.json"),
]);
// The KJV is the base text every view already renders; the rest are comparisons.
const COMPARE = EDITIONS.filter((e) => e.code !== "KJV");

// osis verse -> place records mentioned in it
const placesAt = new Map();
const placeById = new Map(places.map((p) => [p.id, p]));
for (const [pid, refs] of Object.entries(placeVerses))
  for (const r of refs) {
    if (!placesAt.has(r)) placesAt.set(r, []);
    placesAt.get(r).push(placeById.get(pid));
  }

const S = { book: "Gen", chapter: 1, refs: true, places: true, top: 6,
            editions: new Set() };

document.getElementById("editions").innerHTML = COMPARE.map((e) => `
  <label title="${esc(e.note)}"><input type="checkbox" data-e="${e.code}">
    ${esc(e.code)} <span class="count">${e.year}</span></label>`).join("");
document.getElementById("editions").addEventListener("change", (ev) => {
  const c = ev.target.dataset.e;
  ev.target.checked ? S.editions.add(c) : S.editions.delete(c);
  render();
});
document.getElementById("editions").addEventListener("mouseover", (ev) => {
  const l = ev.target.closest("label");
  if (l) document.getElementById("edhint").textContent = l.title;
});

// Load the selected editions for the current book; a translation that never
// covered this book simply resolves to null and renders as a stated gap.
async function loadEditions(osis) {
  const wanted = COMPARE.filter((e) => S.editions.has(e.code));
  const got = await Promise.all(wanted.map((e) =>
    load(`${e.path}/${osis}.json`).then((d) => ({ ...e, data: d }))
                                 .catch(() => ({ ...e, data: null }))));
  return got;
}

const bookSel = document.getElementById("book");
bookSel.innerHTML = BOOKS.map((b) =>
  `<option value="${b.osis}">${esc(b.name)}</option>`).join("");

function fillChapters() {
  const b = BOOKS.byOsis[S.book];
  document.getElementById("chapter").innerHTML =
    Array.from({ length: b.chapters }, (_, i) =>
      `<option value="${i + 1}"${i + 1 === S.chapter ? " selected" : ""}>${i + 1}</option>`).join("");
}

bookSel.addEventListener("change", (e) => {
  S.book = e.target.value; S.chapter = 1; fillChapters(); render();
});
document.getElementById("chapter").addEventListener("change", (e) => {
  S.chapter = +e.target.value; render();
});
document.getElementById("showRefs").addEventListener("change", (e) => {
  S.refs = e.target.checked; render();
});
document.getElementById("showPlaces").addEventListener("change", (e) => {
  S.places = e.target.checked; render();
});
document.getElementById("top").addEventListener("input", (e) => {
  S.top = +e.target.value;
  document.getElementById("topLabel").textContent = S.top;
  render();
});

async function render() {
  bookSel.value = S.book;
  fillChapters();
  location.hash = `${S.book}.${S.chapter}.1`;

  const b = BOOKS.byOsis[S.book];
  const [text, xref, editions] = await Promise.all([
    load(`text/${S.book}.json`),
    load(`xref/${S.book}.json`).catch(() => ({ refs: {} })),
    loadEditions(S.book),
  ]);
  const verses = text.chapters[S.chapter - 1] ?? [];

  const here = new Map();
  let refCount = 0;
  const out = [`<h2 style="font:600 24px/1.2 var(--serif);margin:0 0 4px;
      letter-spacing:.01em">${esc(b.name)} ${S.chapter}</h2>
    <div style="color:var(--faint);font-size:12px;margin-bottom:22px">
      ${esc(b.division)} &middot; ${b.testament === "OT" ? "Old" : "New"} Testament
      &middot; ${verses.length} verses</div>`];

  verses.forEach((vt, i) => {
    const n = i + 1;
    const osis = `${S.book}.${S.chapter}.${n}`;
    const links = (xref.refs[`${S.chapter}.${n}`] ?? []).slice(0, S.top);
    refCount += (xref.refs[`${S.chapter}.${n}`] ?? []).length;
    for (const p of placesAt.get(osis) ?? []) if (p) here.set(p.id, p);

    const gutter = S.refs && links.length
      ? `<div style="flex:0 0 168px;font-size:11px;line-height:1.75;padding-top:3px">
          ${links.map((r) => {
            const t = `${BOOKS[r[0]].osis}.${r[1]}.${r[2]}`;
            return `<a class="ref" data-peek="${t}" href="#${t}"
              title="${r[4]} reader votes">${esc(BOOKS[r[0]].name)} ${r[1]}:${r[2]}</a>`;
          }).join("<br>")}
         </div>`
      : `<div style="flex:0 0 ${S.refs ? 168 : 0}px"></div>`;

    const others = editions.map((e) => {
      const alt = e.data?.chapters?.[S.chapter - 1]?.[n - 1];
      return `<div style="display:flex;gap:10px;margin-top:5px">
        <span style="flex:0 0 62px;color:var(--faint);font:10.5px var(--mono);
                     padding-top:2px">${esc(e.code)}</span>
        <span class="verse-text" style="font-size:13px;color:${alt ? "var(--muted)" : "var(--faint)"}">
          ${alt ? esc(alt) : `<em>no verse here in ${esc(e.code)}</em>`}</span>
      </div>`;
    }).join("");

    out.push(`<div class="v" id="v${n}" style="display:flex;gap:18px;
        align-items:flex-start;padding:5px 0;border-radius:4px">
        <div style="flex:1 1 auto">
          <sup style="color:var(--faint);font:11px var(--mono);margin-right:6px">${n}</sup>
          <span class="verse-text">${vt}</span>
          ${others ? `<div style="margin:6px 0 4px;padding-left:2px;
            border-left:2px solid var(--line)">${others}</div>` : ""}
        </div>${gutter}
      </div>`);
  });

  document.getElementById("text").innerHTML = out.join("");
  document.getElementById("chapstats").textContent =
    `${refCount.toLocaleString()} cross-references leave this chapter.`;

  const list = [...here.values()].sort((a, c) => c.n - a.n);
  document.getElementById("places").innerHTML = S.places && list.length
    ? list.map((p) => `<a href="atlas.html#place=${encodeURIComponent(p.name)}"
        title="${esc(p.type)}, mentioned ${p.n} times in all">${esc(p.disp)}</a>`).join(" &middot; ")
    : `<span style="color:var(--faint)">${S.places ? "none named here" : "hidden"}</span>`;
}

// --- peek at a linked verse without navigating -------------------------------
const peek = document.getElementById("peek");
document.getElementById("text").addEventListener("mouseover", (e) => {
  const a = e.target.closest("a[data-peek]");
  if (a) showPeek(a.dataset.peek);
});
document.getElementById("text").addEventListener("click", (e) => {
  const a = e.target.closest("a[data-peek]");
  if (!a) return;
  e.preventDefault();
  const p = parseOsis(a.dataset.peek);
  S.book = p.book; S.chapter = p.chapter;
  render().then(() => document.getElementById(`v${p.verse}`)
    ?.scrollIntoView({ block: "center", behavior: "smooth" }));
});

let peekToken = 0;
async function showPeek(osis) {
  const mine = ++peekToken;
  const p = parseOsis(osis);
  const b = BOOKS.byOsis[p.book];
  const text = await load(`text/${p.book}.json`);
  if (mine !== peekToken) return;
  const vt = text.chapters[p.chapter - 1]?.[p.verse - 1] ?? "";
  const around = (text.chapters[p.chapter - 1] ?? []).slice(
    Math.max(0, p.verse - 2), p.verse + 1);
  peek.innerHTML = `<h2>Linked verse</h2>
    <div style="font:600 15px/1.3 var(--serif)">${esc(b.name)} ${p.chapter}:${p.verse}</div>
    <div style="color:var(--faint);font-size:12px;margin-bottom:10px">
      ${esc(b.division)} &middot; ${b.testament === "OT" ? "Old" : "New"} Testament</div>
    <div class="verse-text" style="font-size:14px">${vt}</div>
    <h2>In context</h2>
    <div class="verse-text" style="font-size:12.5px;color:var(--muted)">
      ${around.map((t, i) => {
        const num = Math.max(1, p.verse - 1) + i;
        return `<sup style="font:10px var(--mono)">${num}</sup> ${
          num === p.verse ? `<span style="color:var(--ink)">${t}</span>` : t}`;
      }).join(" ")}
    </div>
    <div style="margin-top:14px"><button data-go="${osis}">Read this chapter</button></div>`;
  peek.querySelector("[data-go]").onclick = () => {
    S.book = p.book; S.chapter = p.chapter;
    render().then(() => document.getElementById(`v${p.verse}`)
      ?.scrollIntoView({ block: "center" }));
  };
}

// deep link: reader.html#Rom.5.12
function fromHash() {
  const p = parseOsis(location.hash.slice(1));
  if (p && BOOKS.byOsis[p.book]) { S.book = p.book; S.chapter = p.chapter; return p.verse; }
  return null;
}
const v = fromHash();
await render();
if (v) document.getElementById(`v${v}`)?.scrollIntoView({ block: "center" });
