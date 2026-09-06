// Direct quotation vs. loose allusion, measured rather than asserted: the
// longest run of words a New Testament verse shares with the Old Testament one
// it references. See scripts/build_quotations.py for what this does and does
// not mean.
import { load, shell, esc, books, verseText, readable } from "./common.js";
import { reEscape } from "./lib/osis.js";

shell("Quotations");

const CLASSES = {
  "quotation":   { c: "#5eb87a", label: "Quotation",   hint: "Six or more shared words, at least three of them distinctive." },
  "strong echo": { c: "#6d9fe0", label: "Strong echo", hint: "Four or five shared words with distinctive vocabulary." },
  "echo":        { c: "#e0a458", label: "Echo",        hint: "Three shared words, or a third of the distinctive vocabulary in common." },
};

document.body.insertAdjacentHTML("beforeend", `
  <main>
    <aside>
      <h2>Strength of overlap</h2>
      <div class="checks" id="cls"></div>
      <p class="hint" id="clshint"></p>
      <h2>Filter</h2>
      <div class="control">
        <label for="ntBook">New Testament book</label>
        <select id="ntBook"><option value="">any</option></select>
      </div>
      <div class="control">
        <label for="otBook">Old Testament book</label>
        <select id="otBook"><option value="">any</option></select>
      </div>
      <div class="control">
        <label for="q">Shared wording contains</label>
        <input type="search" id="q" placeholder="covenant, shepherd, stone...">
      </div>
      <h2>What this measures</h2>
      <p class="note">Word overlap in the KJV, not authorial intent. The KJV
        translators harmonised New Testament quotations with their own Old
        Testament wording, which inflates the score; and the New Testament
        usually quotes the Greek Septuagint, whose wording can differ from the
        Hebrew behind the English Old Testament, which deflates it.</p>
      <p class="hint" id="counts"></p>
    </aside>
    <div class="stage" style="overflow-y:auto">
      <div id="list" style="max-width:900px;margin:0 auto;padding:22px 28px 90px"></div>
    </div>
    <aside class="right" id="detail">
      <h2>Which books</h2>
      <div id="matrix" style="font-size:12px;line-height:1.75"></div>
    </aside>
  </main>`);

const [data, BOOKS] = await Promise.all([load("quotations.json"), books()]);
const S = { cls: new Set(Object.keys(CLASSES)), nt: "", ot: "", q: "" };

document.getElementById("cls").innerHTML = Object.entries(CLASSES).map(([k, v]) => {
  const n = data.pairs.filter((p) => p.cls === k).length;
  return `<label title="${esc(v.hint)}"><input type="checkbox" data-k="${k}" checked>
    <span class="swatch" style="--c:${v.c}"></span>${v.label}
    <span class="count">${n.toLocaleString()}</span></label>`;
}).join("");
document.getElementById("cls").addEventListener("change", (e) => {
  e.target.checked ? S.cls.add(e.target.dataset.k) : S.cls.delete(e.target.dataset.k);
  render();
});
document.getElementById("cls").addEventListener("mouseover", (e) => {
  const l = e.target.closest("label");
  if (l) document.getElementById("clshint").textContent = l.title;
});

const osisOf = (ref) => ref.split(".")[0];
const bookOf = (ref) => BOOKS.byOsis[osisOf(ref)];

document.getElementById("ntBook").innerHTML +=
  BOOKS.filter((b) => b.testament === "NT")
    .map((b) => `<option value="${b.osis}">${esc(b.name)}</option>`).join("");
document.getElementById("otBook").innerHTML +=
  BOOKS.filter((b) => b.testament === "OT")
    .map((b) => `<option value="${b.osis}">${esc(b.name)}</option>`).join("");
document.getElementById("ntBook").addEventListener("change", (e) => { S.nt = e.target.value; render(); });
document.getElementById("otBook").addEventListener("change", (e) => { S.ot = e.target.value; render(); });
document.getElementById("q").addEventListener("input", (e) => {
  S.q = e.target.value.trim().toLowerCase(); render();
});

const allusions = (data.classes.find(([k]) => k === "allusion") ?? [, 0])[1];
document.getElementById("counts").textContent =
  `${data.scanned.toLocaleString()} cross-testament references scanned. ` +
  `${allusions.toLocaleString()} scored as bare allusion and are not listed.`;

// --- which books quote which -------------------------------------------------
document.getElementById("matrix").innerHTML = data.matrix.slice(0, 26).map(([a, b, n]) => `
  <div style="display:flex;gap:8px;align-items:baseline;padding:2px 0">
    <span style="flex:1 1 auto">${esc(BOOKS[a].name)}
      <span style="color:var(--faint)">&larr;</span> ${esc(BOOKS[b].name)}</span>
    <span style="color:var(--accent);font:11px var(--mono)">${n}</span>
  </div>`).join("");

// --- the list ----------------------------------------------------------------
function visible() {
  return data.pairs.filter((p) =>
    S.cls.has(p.cls) &&
    (!S.nt || osisOf(p.nt) === S.nt) &&
    (!S.ot || osisOf(p.ot) === S.ot) &&
    (!S.q || p.shared.includes(S.q)));
}

// Wrap the shared run in <mark> wherever it appears in the verse.
function highlight(text, shared) {
  if (!shared) return text;
  const plain = text.replace(/<[^>]+>/g, "");
  const words = shared.split(" ");
  // Rebuild the run as a loose regex so punctuation between words does not
  // break the match.
  const re = new RegExp(words.map(reEscape).join("[^a-zA-Z]+"), "i");
  const m = re.exec(plain);
  if (!m) return text;
  return esc(plain.slice(0, m.index)) +
    `<mark>${esc(m[0])}</mark>` + esc(plain.slice(m.index + m[0].length));
}

let shown = 60;
async function render(more = false) {
  if (!more) shown = 60;
  const vis = visible();
  const list = document.getElementById("list");
  list.innerHTML = `<div style="color:var(--faint);font-size:12.5px;margin-bottom:18px">
    ${vis.length.toLocaleString()} pair${vis.length === 1 ? "" : "s"}, strongest first.
    Highlighted text is the shared run.</div>`;

  for (const p of vis.slice(0, shown)) {
    const c = CLASSES[p.cls];
    const [ntText, otText] = await Promise.all([verseText(p.nt), verseText(p.ot)]);
    list.insertAdjacentHTML("beforeend", `
      <div style="border:1px solid var(--line);border-radius:8px;padding:14px 16px;
                  margin-bottom:12px;background:var(--panel)">
        <div style="display:flex;align-items:baseline;gap:10px;margin-bottom:9px">
          <span class="pill" style="color:${c.c}">${c.label}</span>
          <span style="color:var(--faint);font:11px var(--mono)">
            ${p.run} shared words, ${p.distinct} distinctive</span>
          <span style="margin-left:auto;color:var(--faint);font:11px var(--mono)"
                title="OpenBible reader votes for this link">${p.votes} votes</span>
        </div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">
          <div>
            <a class="ref" href="reader.html#${p.nt}">${esc(readable(p.nt, BOOKS))}</a>
            <div class="verse-text" style="font-size:13.5px;margin-top:3px">
              ${highlight(ntText ?? "", p.shared)}</div>
          </div>
          <div style="border-left:1px solid var(--line);padding-left:16px">
            <a class="ref" href="reader.html#${p.ot}">${esc(readable(p.ot, BOOKS))}</a>
            <div class="verse-text" style="font-size:13.5px;margin-top:3px">
              ${highlight(otText ?? "", p.shared)}</div>
          </div>
        </div>
      </div>`);
  }
  if (vis.length > shown)
    list.insertAdjacentHTML("beforeend",
      `<button id="more" style="max-width:260px">Show ${Math.min(60, vis.length - shown)} more
        (${(vis.length - shown).toLocaleString()} remaining)</button>`);
  document.getElementById("more")?.addEventListener("click", () => {
    shown += 60; render(true);
  });
}

render();
