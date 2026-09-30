import test from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, mkdirSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { createRuleSnapshot, extendRuleSnapshot, readPinnedRuleBundle, verifyRuleSnapshot } from "../src/rules.js";

test("rule snapshot includes entrypoint core and mandatory files, then freezes routed modules", () => {
  const root = mkdtempSync(join(tmpdir(), "trainaicad-rules-"));
  mkdirSync(join(root, "skills/lispcad/core"), { recursive: true });
  mkdirSync(join(root, "references"), { recursive: true });
  mkdirSync(join(root, "skills/lispcad/modes"), { recursive: true });
  writeFileSync(join(root, "AI_ENTRYPOINT.md"), [
    "Current production release is **V9.1**.",
    "## Mandatory load order",
    "Read `references/BASE.md` before source interpretation.",
    "## End"
  ].join("\n"));
  mkdirSync(join(root, "skills/lispcad/portable"), { recursive: true });
  writeFileSync(join(root, "skills/lispcad/portable/SKILL_LISPCAD_CURRENT.md"), "# SKILL_LISPCAD V9.1 PORTABLE\n");
  writeFileSync(join(root, "skills/lispcad/core/DRAWING_READING.md"), "core\n");
  writeFileSync(join(root, "references/BASE.md"), "base rule\n");
  writeFileSync(join(root, "skills/lispcad/modes/FLAT_NO_BEND.md"), "flat rule\n");

  const base = createRuleSnapshot(root);
  assert.ok(base.files.some((f) => f.path === "AI_ENTRYPOINT.md"));
  assert.ok(base.files.some((f) => f.path.endsWith("SKILL_LISPCAD_CURRENT.md")));
  assert.ok(base.files.some((f) => f.path === "skills/lispcad/core/DRAWING_READING.md"));
  verifyRuleSnapshot(root, base);

  const routed = extendRuleSnapshot(root, base, ["skills/lispcad/modes/FLAT_NO_BEND.md"]);
  assert.notEqual(routed.sha256, base.sha256);
  const bundle = readPinnedRuleBundle(root, routed);
  assert.ok(bundle.files.find((f) => f.path.endsWith("FLAT_NO_BEND.md"))?.content.includes("flat rule"));
  writeFileSync(join(root, "skills/lispcad/modes/FLAT_NO_BEND.md"), "changed\n");
  assert.throws(() => verifyRuleSnapshot(root, routed), /JOB_RULE_SNAPSHOT_STALE/);
});
