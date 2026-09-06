// Reference parsing and formatting. Run with `node --test tests/js/`.
import test from "node:test";
import assert from "node:assert/strict";
import {
  parseOsis, readable, year, span, esc, reEscape,
} from "../../web/js/lib/osis.js";

test("parseOsis reads well-formed references", () => {
  assert.deepEqual(parseOsis("Gen.1.1"), { book: "Gen", chapter: 1, verse: 1 });
  assert.deepEqual(parseOsis("1John.5.7"), { book: "1John", chapter: 5, verse: 7 });
  assert.deepEqual(parseOsis("Rev.22.21"), { book: "Rev", chapter: 22, verse: 21 });
});

test("parseOsis rejects anything malformed rather than guessing", () => {
  for (const bad of ["Gen.1", "Gen", "Gen.1.1.1", "", "Gen..1", "Gen.a.1",
                     null, undefined, "Gen 1:1"]) {
    assert.equal(parseOsis(bad), null, `should reject ${JSON.stringify(bad)}`);
  }
});

test("readable accepts the canon table in either shape", () => {
  const arr = [{ osis: "Gen", name: "Genesis" }];
  assert.equal(readable("Gen.1.1", arr), "Genesis 1:1");
  const idx = { byOsis: { Gen: { name: "Genesis" } } };
  assert.equal(readable("Gen.1.1", idx), "Genesis 1:1");
});

test("readable falls back to the raw OSIS for an unknown book", () => {
  assert.equal(readable("Nope.1.1", []), "Nope 1:1");
  assert.equal(readable("garbage", []), "garbage");
});

test("year labels the eras, and says so where the calendar has no zero", () => {
  assert.equal(year(-722), "722 BCE");
  assert.equal(year(70), "70 CE");
  assert.equal(year(0), "1 BCE/CE");
});

test("span collapses the era label when both ends share it", () => {
  assert.equal(span(-1050, -1010), "1050-1010 BCE");
  assert.equal(span(30, 95), "30-95 CE");
});

test("span spells out both eras when it crosses the epoch", () => {
  assert.equal(span(-5, 33), "5 BCE - 33 CE");
});

test("span of a single instant is just the year", () => {
  assert.equal(span(-586, null), "586 BCE");
  assert.equal(span(-586, -586), "586 BCE");
});

test("esc neutralises the characters that would break out of HTML", () => {
  assert.equal(esc('<script>&"'), "&lt;script&gt;&amp;&quot;");
  assert.equal(esc(""), "");
  assert.equal(esc(42), "42");
});

test("reEscape makes a string safe to embed in a RegExp", () => {
  // A shared quotation run containing "." or "*" must not become a wildcard.
  const literal = "a.b*c";
  assert.ok(new RegExp(reEscape(literal)).test("a.b*c"));
  assert.ok(!new RegExp(reEscape(literal)).test("axbxc"));
});
