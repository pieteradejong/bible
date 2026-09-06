// Reference parsing and formatting. No DOM, no fetch -- so it can be unit
// tested under node:test, and so common.js stays a thin shell over it.

const REF = /^(\w+)\.(\d+)\.(\d+)$/;

/** "Gen.1.1" -> {book:"Gen", chapter:1, verse:1}; null if it is not a reference. */
export function parseOsis(ref) {
  const m = REF.exec(String(ref ?? ""));
  return m ? { book: m[1], chapter: +m[2], verse: +m[3] } : null;
}

/** "Gen.1.1" -> "Genesis 1:1", given the canon table in either shape. */
export function readable(ref, books) {
  const p = parseOsis(ref);
  if (!p) return String(ref);
  const b = books?.byOsis
    ? books.byOsis[p.book]
    : Array.isArray(books) ? books.find((x) => x.osis === p.book) : null;
  return `${b ? b.name : p.book} ${p.chapter}:${p.verse}`;
}

/** Negative years are BCE. There is no year zero, so 0 is labelled explicitly. */
export function year(y) {
  return y < 0 ? `${-y} BCE` : y === 0 ? "1 BCE/CE" : `${y} CE`;
}

/** A span, collapsed to one era label when both ends share it. */
export function span(a, b) {
  if (b == null || b === a) return year(a);
  return a < 0 && b < 0 ? `${-a}-${-b} BCE`
       : a > 0 && b > 0 ? `${a}-${b} CE`
       : `${year(a)} - ${year(b)}`;
}

export const esc = (s) =>
  String(s).replace(/[&<>"]/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

/** Escape a string for literal use inside a RegExp. */
export const reEscape = (s) => String(s).replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
