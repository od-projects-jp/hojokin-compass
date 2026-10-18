/* Hojokin Compass: browser-only preferences. No cookies, accounts or network requests. */
(function (root) {
  "use strict";
  const KEYS = Object.freeze({
    individualFilters: "hojokin-individual-filters-v1",
    individualFavorites: "hojokin-individual-favorites-v1",
    businessFilters: "hojokin-business-filters-v1"
  });
  function safeStorage() {
    try {
      const storage = root.localStorage;
      const key = "__hojokin_storage_probe__";
      storage.setItem(key, "1");
      storage.removeItem(key);
      return storage;
    } catch (_) {
      return null;
    }
  }
  const storage = safeStorage();
  function read(key, fallback) {
    if (!Object.values(KEYS).includes(key) || !storage) return fallback;
    try {
      const raw = storage.getItem(key);
      return raw === null ? fallback : JSON.parse(raw);
    } catch (_) {
      return fallback;
    }
  }
  function write(key, value) {
    if (!Object.values(KEYS).includes(key) || !storage) return false;
    try {
      storage.setItem(key, JSON.stringify(value));
      return true;
    } catch (_) {
      return false;
    }
  }
  function remove(key) {
    if (!Object.values(KEYS).includes(key) || !storage) return false;
    try {
      storage.removeItem(key);
      return true;
    } catch (_) {
      return false;
    }
  }
  function clear() {
    // Never clear the entire origin: other apps on github.io may share storage.
    Object.values(KEYS).forEach(remove);
  }
  function favorites() {
    const value = read(KEYS.individualFavorites, []);
    return Array.isArray(value) ? [...new Set(value.filter(
      x => typeof x === "string" && x.length > 0 && x.length < 600
    ))].slice(0, 500) : [];
  }
  function filters() {
    const value = read(KEYS.individualFilters, {});
    if (!value || typeof value !== "object" || Array.isArray(value)) return {};
    const clean = {};
    for (const key of ["region", "municipality", "keyword", "topic", "savedOnly"]) {
      if (key === "savedOnly") {
        if (typeof value[key] === "boolean") clean[key] = value[key];
      } else if (typeof value[key] === "string") {
        clean[key] = value[key].slice(0, 120);
      }
    }
    return clean;
  }
  root.HojokinLocalStore = Object.freeze({
    KEYS, available: !!storage, read, write, remove, clear, favorites, filters
  });
})(typeof window !== "undefined" ? window : globalThis);
