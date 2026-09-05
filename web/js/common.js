// Shared helpers: data loading, OSIS parsing, tooltips, nav.
export const DATA = "data";

const cache = new Map();
export async function load(path) {
  if (!cache.has(path)) {
    cache.set(path, fetch(`${DATA}/${path}`).then((r) => {
      if (!r.ok) throw new Error(`${path}: ${r.status} - run \`make data\` first`);
      return r.json();
    }));
  }
  return cache.get(path);
}

export const CERTAINTY = {
  attested:     { color: "var(--attested)",     label: "Attested",     hint: "Fixed by a source outside the Bible - an inscription, a chronicle, a datable reign." },
  conventional: { color: "var(--conventional)", label: "Conventional", hint: "The date most scholars work with, inferred rather than documented." },
  traditional:  { color: "var(--traditional)",  label: "Traditional",  hint: "Derived from the Bible's own internal chronology, with no external anchor." },
  disputed:     { color: "var(--disputed)",     label: "Disputed",     hint: "Serious competing proposals exist; the timeline shows one and names the others." },
  unknown:      { color: "var(--unknown)",      label: "Unstated",     hint: "No confidence recorded in the source data." },
};

export const LANES = {
  narrative: "Narrative", israel: "Israel and Judah", empires: "Empires",
  exile: "Exile", church: "Church", text: "Text and canon",
};

// --- references -------------------------------------------------------------
export function parseOsis(ref) {
  const m = /^(\w+)\.(\d+)\.(\d+)$/.exec(ref);
  return m ? { book: m[1], chapter: +m[2], verse: +m[3] } : null;
}

let BOOKS = null;
export async function books() {
  if (!BOOKS) {
    const t = await load("timeline.json");
    BOOKS = t.books;
    BOOKS.byOsis = Object.fromEntries(t.books.map((b) => [b.osis, b]));
  }
  return BOOKS;
}

export function readable(ref, bks) {
  const p = parseOsis(ref);
  if (!p) return ref;
  const b = bks.byOsis ? bks.byOsis[p.book] : bks.find((x) => x.osis === p.book);
  return `${b ? b.name : p.book} ${p.chapter}:${p.verse}`;
}

// Fetch a single verse's text, loading (and caching) that book's file.
export async function verseText(ref) {
  const p = parseOsis(ref);
  if (!p) return null;
  try {
    const t = await load(`text/${p.book}.json`);
    return t.chapters[p.chapter - 1]?.[p.verse - 1] ?? null;
  } catch { return null; }
}

// --- tooltip ----------------------------------------------------------------
const tip = document.createElement("div");
tip.className = "tip";
document.body.appendChild(tip);

export function showTip(evt, html) {
  tip.innerHTML = html;
  tip.classList.add("on");
  moveTip(evt);
}
export function moveTip(evt) {
  const pad = 14, r = tip.getBoundingClientRect();
  let x = evt.clientX + pad, y = evt.clientY + pad;
  if (x + r.width > innerWidth - 8) x = evt.clientX - r.width - pad;
  if (y + r.height > innerHeight - 8) y = evt.clientY - r.height - pad;
  tip.style.left = `${Math.max(8, x)}px`;
  tip.style.top = `${Math.max(8, y)}px`;
}
export function hideTip() { tip.classList.remove("on"); }

// --- misc -------------------------------------------------------------------
export function year(y) {
  return y < 0 ? `${-y} BCE` : y === 0 ? "1 BCE/CE" : `${y} CE`;
}
export function span(a, b) {
  if (b == null || b === a) return year(a);
  return a < 0 && b < 0 ? `${-a}-${-b} BCE`
       : a > 0 && b > 0 ? `${a}-${b} CE`
       : `${year(a)} - ${year(b)}`;
}
export const esc = (s) =>
  String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

export function markNav() {
  const here = location.pathname.split("/").pop() || "index.html";
  document.querySelectorAll("nav.views a").forEach((a) => {
    if (a.getAttribute("href") === here) a.setAttribute("aria-current", "page");
  });
}

export function shell(title) {
  document.body.insertAdjacentHTML("afterbegin", `
    <header class="bar">
      <h1><a href="index.html">Visualising the Bible</a></h1>
      <span style="color:var(--faint);font-size:12.5px">${esc(title)}</span>
      <nav class="views">
        <a href="timeline.html">Timeline</a>
        <a href="atlas.html">Atlas</a>
        <a href="network.html">Cross-references</a>
        <a href="quotations.html">Quotations</a>
        <a href="genealogy.html">Genealogy</a>
        <a href="reader.html">Reader</a>
        <a href="index.html">About</a>
      </nav>
    </header>`);
  markNav();
}
