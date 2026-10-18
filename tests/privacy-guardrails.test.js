"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");

const pages = ["index.html", "individual.html", "search.html", "individual-directory.html", "privacy.html"];
for (const page of pages) {
  const html = fs.readFileSync(page, "utf8");
  // External scripts can collect visitor data. Require an explicit review before adding them.
  const scripts = [...html.matchAll(/<script\b[^>]*\bsrc\s*=\s*["']([^"']+)["']/gi)];
  for (const match of scripts) {
    assert.ok(match[1].startsWith("./"), `${page}: external script requires privacy review: ${match[1]}`);
  }
  assert.ok(!/<input\b[^>]*type\s*=\s*["'](?:email|password|tel)["']/i.test(html),
    `${page}: user credentials/contact fields violate no-account policy`);
  assert.ok(!/\b(?:sendBeacon|gtag\s*\(|fbq\s*\(|dataLayer\.push)\b/.test(html),
    `${page}: tracking call requires privacy review`);
}
const individual = fs.readFileSync("individual.html", "utf8");
const business = fs.readFileSync("search.html", "utf8");
assert.ok(!/\blocalStorage\b/.test(individual), "Individual UI must use shared storage helper");
assert.ok(!/\blocalStorage\b/.test(business), "Business UI must use shared storage helper");
for (const page of ["individual.html", "search.html", "privacy.html"]) {
  const html = fs.readFileSync(page, "utf8");
  assert.ok(html.includes('src="./privacy-storage.js"'), `${page}: missing local-only storage helper`);
  assert.ok(html.includes('id="clearLocal"') || html.includes('id="deleteBrowserData"'),
    `${page}: no delete-data control`);
}
console.log("Privacy guardrails: no account inputs, third-party scripts, or tracking calls");
