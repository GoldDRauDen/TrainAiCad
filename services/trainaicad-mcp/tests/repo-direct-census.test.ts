import test from "node:test";
import assert from "node:assert/strict";
import { isCensusItemClosed } from "../src/repo-direct.js";

test("repo-direct final census treats explicit NO as closed without synthetic evidence", () => {
  assert.equal(isCensusItemClosed({ state: "NO", evidence: [] }), true);
  assert.equal(isCensusItemClosed({ state: "NO", evidence: ["page-inspected"] }), true);
});

test("repo-direct final census still requires proof for YES and blocks UNKNOWN", () => {
  assert.equal(isCensusItemClosed({ state: "YES", evidence: [] }), false);
  assert.equal(isCensusItemClosed({ state: "YES", evidence: ["printed-callout"] }), true);
  assert.equal(isCensusItemClosed({ state: "UNKNOWN", evidence: [] }), false);
  assert.equal(isCensusItemClosed(undefined), false);
});
