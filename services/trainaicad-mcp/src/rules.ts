import { createHash } from "node:crypto";
import { existsSync, readFileSync, readdirSync } from "node:fs";
import { join, resolve } from "node:path";

export type RuleFilePin = { path: string; sha256: string };
export type RuleSnapshot = { files: RuleFilePin[]; sha256: string };

const hash = (bytes: string | Buffer) => createHash("sha256").update(bytes).digest("hex");

export function createRuleSnapshot(repoRoot: string): RuleSnapshot {
  const entryPath = "AI_ENTRYPOINT.md";
  const entry = readRuleText(repoRoot, entryPath);
  const section = entry.split("## Mandatory load order", 2)[1]?.split("\n## ", 1)[0];
  if (!section) throw new Error("RULE_SNAPSHOT_MANDATORY_LOAD_ORDER_MISSING");

  const paths = new Set<string>([entryPath, "skills/lispcad/portable/SKILL_LISPCAD_CURRENT.md"]);
  const coreDir = join(repoRoot, "skills/lispcad/core");
  if (!existsSync(coreDir)) throw new Error("RULE_SNAPSHOT_CORE_DIRECTORY_MISSING");
  for (const name of readdirSync(coreDir).filter((n) => n.toLowerCase().endsWith(".md"))) {
    paths.add(`skills/lispcad/core/${name}`);
  }
  for (const match of section.matchAll(/(?:references|regression|tools)\/[A-Za-z0-9_./-]+\.md/g)) {
    paths.add(match[0]);
  }
  return snapshot(repoRoot, [...paths]);
}

export function extendRuleSnapshot(repoRoot: string, current: RuleSnapshot, paths: string[]): RuleSnapshot {
  verifyRuleSnapshot(repoRoot, current);
  return snapshot(repoRoot, [...current.files.map((f) => f.path), ...paths]);
}

export function verifyRuleSnapshot(repoRoot: string, current: RuleSnapshot): void {
  for (const pin of current.files) {
    const actual = hash(readRuleText(repoRoot, pin.path));
    if (actual !== pin.sha256) throw new Error(`JOB_RULE_SNAPSHOT_STALE:${pin.path}`);
  }
  const digest = hash(JSON.stringify(current.files));
  if (digest !== current.sha256) throw new Error("JOB_RULE_SNAPSHOT_CORRUPTED");
}

export function readPinnedRuleBundle(repoRoot: string, current: RuleSnapshot) {
  verifyRuleSnapshot(repoRoot, current);
  return {
    snapshotSha256: current.sha256,
    files: current.files.map((pin) => ({ ...pin, content: readRuleText(repoRoot, pin.path) }))
  };
}

function snapshot(repoRoot: string, rawPaths: string[]): RuleSnapshot {
  const paths = [...new Set(rawPaths)].sort();
  const files = paths.map((path) => ({ path, sha256: hash(readRuleText(repoRoot, path)) }));
  return { files, sha256: hash(JSON.stringify(files)) };
}

function readRuleText(repoRoot: string, path: string): string {
  if (path.includes("..") || path.startsWith("/") || path.includes("\\")) throw new Error(`RULE_PATH_INVALID:${path}`);
  const absolute = resolve(repoRoot, path);
  if (!absolute.startsWith(resolve(repoRoot) + "\\") && !absolute.startsWith(resolve(repoRoot) + "/")) {
    throw new Error(`RULE_PATH_OUTSIDE_REPO:${path}`);
  }
  if (!existsSync(absolute)) throw new Error(`RULE_SNAPSHOT_FILE_MISSING:${path}`);
  return readFileSync(absolute, "utf8");
}
