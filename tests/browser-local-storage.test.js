"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const code = fs.readFileSync("privacy-storage.js", "utf8");
function setup({blocked = false, quota = false} = {}) {
  const values = new Map([["unrelated-key", "do-not-touch"]]);
  const storage = {
    getItem(key) { if (blocked) throw Error("blocked"); return values.has(key) ? values.get(key) : null; },
    setItem(key, value) { if (blocked || quota) throw Error("quota"); values.set(key, value); },
    removeItem(key) { if (blocked) throw Error("blocked"); values.delete(key); }
  };
  const context = {window: {localStorage: storage}};
  vm.runInNewContext(code, context, {timeout: 1000});
  return {api: context.window.HojokinLocalStore, values};
}
{
  const {api, values} = setup();
  assert.equal(api.available, true);
  assert.equal(api.write(api.KEYS.individualFilters, {region:"東京都", keyword:"住宅"}), true);
  assert.equal(api.filters().region, "東京都");
  assert.equal(api.write(api.KEYS.individualFavorites, ["a", "a", "", 1, "b"]), true);
  assert.deepEqual(Array.from(api.favorites()), ["a", "b"]);
  assert.equal(api.write("unapproved-key", "secret"), false);
  assert.equal(api.read("unapproved-key", "fallback"), "fallback");
  values.set(api.KEYS.individualFilters, "{invalid");
  assert.deepEqual(Object.keys(api.filters()), []);
  api.clear();
  assert.equal(values.get("unrelated-key"), "do-not-touch");
  assert.equal(values.has(api.KEYS.individualFavorites), false);
  assert.equal(values.has(api.KEYS.businessFavorites), false);
}
{
  const {api} = setup({blocked: true});
  assert.equal(api.available, false);
  assert.equal(api.write(api.KEYS.individualFilters, {region:"東京都"}), false);
  assert.equal(api.read(api.KEYS.individualFilters, "fallback"), "fallback");
  assert.deepEqual(Array.from(api.favorites()), []);
  assert.doesNotThrow(() => api.clear());
}
{
  const {api} = setup({quota: true});
  assert.equal(api.available, false);
  assert.equal(api.write(api.KEYS.individualFavorites, ["x"]), false);
}
const individual = fs.readFileSync("individual.html", "utf8");
const business = fs.readFileSync("search.html", "utf8");
for (const html of [individual, business]) {
  assert.ok(html.includes('src="./privacy-storage.js"'));
  assert.ok(html.includes('id="clearLocal"'));
  assert.ok(!/<form[^>]*action=/.test(html), "Unexpected form submission");
}
assert.ok(individual.includes("favoriteKey"));
assert.ok(individual.includes("savedOnly"));
assert.ok(business.includes("persistBusinessFilters"));
console.log("Browser-only storage contract tests passed");
