// Quick logic tests (no browser, no install): `npm test`
import test from "node:test";
import assert from "node:assert/strict";
import { STRING_KEYS, STRING_TABLE, getLang, setLangState, t } from "./strings.js";
import { fmtArea, fmtDate, mapsEmbedUrl, num, parseLatLng, parseQr, validLatLng } from "./utils.js";
import { readFileSync, readdirSync } from "node:fs";

test("every string has both Bangla and English text", () => {
  for (const k of STRING_KEYS) {
    const [bn, en] = STRING_TABLE[k];
    assert.ok(bn && en, `missing translation: ${k}`);
  }
});

test("language switch changes text and digits", () => {
  setLangState("bn");
  assert.equal(num(412), "৪১২");
  assert.equal(fmtDate("2026-10-17"), "১৭/১০/২০২৬");
  assert.equal(t("nav.verify"), "দলিল যাচাই");
  setLangState("en");
  assert.equal(getLang(), "en");
  assert.equal(num(412), "412");
  assert.equal(fmtArea(6.5), "6.5");
  assert.equal(t("reg.done", { n: "D-0001" }), "Deed D-0001 registered");
  assert.equal(t("no.such.key"), "no.such.key");
});

test("every t('...') key used in source exists", () => {
  const files = [];
  const walk = (d) => readdirSync(d, { withFileTypes: true }).forEach((e) => (e.isDirectory() ? walk(`${d}/${e.name}`) : files.push(`${d}/${e.name}`)));
  walk(new URL(".", import.meta.url).pathname);
  const used = new Set();
  for (const f of files.filter((x) => /\.(jsx?|mjs)$/.test(x) && !x.endsWith("app.test.mjs") && !x.endsWith("strings.js"))) {
    for (const m of readFileSync(f, "utf8").matchAll(/\bt\(\s*["'`]([\w.]+)["'`]/g)) used.add(m[1]);
    for (const m of readFileSync(f, "utf8").matchAll(/["']((?:nav|chat|home|plot|map|reg|flag|verify|ai|scan|theme|lang|footer|f|ph|sketch|status|mut|err)\.[\w.]+)["']/g)) used.add(m[1]);
  }
  for (const k of used) if (!STRING_KEYS.includes(k) && !/^(status|mut)\.$/.test(k)) assert.fail(`unknown string key: ${k}`);
});

test("Google Maps coordinates are parsed from links and text", () => {
  assert.deepEqual(parseLatLng("23.8103, 90.4125"), { lat: 23.8103, lng: 90.4125 });
  assert.deepEqual(parseLatLng("https://www.google.com/maps/@23.8103,90.4125,17z"), { lat: 23.8103, lng: 90.4125 });
  assert.deepEqual(parseLatLng("https://www.google.com/maps?q=24.5,91.25"), { lat: 24.5, lng: 91.25 });
  assert.deepEqual(parseLatLng("https://www.google.com/maps/place/X/data=!3d23.7!4d90.3"), { lat: 23.7, lng: 90.3 });
  assert.equal(parseLatLng("hello"), null);
  assert.equal(parseLatLng("123, 90"), null);
  assert.equal(validLatLng(91, 0), false);
  assert.ok(mapsEmbedUrl(23.8, 90.4).includes("output=embed"));
});

test("QR payloads are understood", () => {
  assert.deepEqual(parseQr("https://x.test/verify?deed=d-0003&hash=abc"), { deed: "D-0003", hash: "abc" });
  assert.deepEqual(parseQr("d-0002"), { deed: "D-0002", hash: "" });
  assert.equal(parseQr("nonsense"), null);
});
