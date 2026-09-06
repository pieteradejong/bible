// Shared helpers: data loading, tooltips, nav shell.
//
// The pure reference/formatting helpers live in lib/osis.js so they can be unit
// tested without a DOM; they are re-exported here so views keep one import.
export { parseOsis, readable, year, span, esc } from "./lib/osis.js";
// A re-export does not create a local binding, so anything used *inside* this
// module has to be imported as well.
import { parseOsis, esc } from "./lib/osis.js";

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


let BOOKS = null;
export async function books() {
  if (!BOOKS) {
    const t = await load("timeline.json");
    BOOKS = t.books;
    BOOKS.byOsis = Object.fromEntries(t.books.map((b) => [b.osis, b]));
  }
  return BOOKS;
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

// --- misc ---------------------------------------------------------------

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
        <a href="footprint.html">Footprint</a>
        <a href="network.html">Cross-references</a>
        <a href="quotations.html">Quotations</a>
        <a href="genealogy.html">Genealogy</a>
        <a href="reader.html">Reader</a>
        <a href="index.html">About</a>
      </nav>
    </header>`);
  markNav();
}
