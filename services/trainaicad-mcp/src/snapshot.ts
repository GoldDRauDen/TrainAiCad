import { createHash } from "node:crypto";
import {
  existsSync,
  mkdirSync,
  readFileSync,
  writeFileSync,
  renameSync,
} from "node:fs";
import { join, dirname } from "node:path";
import { spawnSync } from "node:child_process";
import { dataRoot } from "./ingest.js";
import type { ReleasePin, CadEvidenceV1, JobMode } from "./model.js";
const hash = (b: string | Buffer) =>
  createHash("sha256").update(b).digest("hex");
type Rule = { load: string[]; depends_on?: string[] };
type Router = {
  release: string;
  default_load: string[];
  source_routes: Record<string, Rule>;
  mode_routes: Record<string, Rule>;
  feature_routes: Record<string, Rule>;
  dependency_aliases: Record<
    string,
    { route_group: "mode_routes"; route_id: string }
  >;
};
type Snapshot = ReleasePin & { router: Router; files: Record<string, string> };
function safe(path: string) {
  if (
    path.includes("..") ||
    path.startsWith("/") ||
    path.includes("\\") ||
    /^(skills\/lispcad\/(versions|portable)\/|docs\/history\/)/.test(path)
  )
    throw new Error(`ROUTING_COVERAGE_GAP:${path}`);
}
export function pinRules(root: string): ReleasePin {
  try {
    const entry = readFileSync(join(root, "AI_ENTRYPOINT.md"), "utf8");
    const proc = spawnSync(
      process.env.TRAINAICAD_PYTHON ?? "python3",
      [join(root, "services/trainaicad-mcp/bridge/rules_bridge.py"), root],
      { encoding: "utf8", timeout: 30_000 },
    );
    if (proc.status !== 0)
      throw new Error(proc.stderr || "router bridge failed");
    const { router, coverageRelease } = JSON.parse(proc.stdout) as {
      router: Router;
      coverageRelease: string;
    };
    const release = entry.match(
      /Current production release is \*\*(V\d+\.\d+)\*\*/,
    )?.[1];
    if (!release || router.release !== release || coverageRelease !== release)
      throw new Error("entrypoint/router/coverage disagree");
    const paths = new Set([
      "AI_ENTRYPOINT.md",
      "skills/lispcad/router/ROUTER.yaml",
      "skills/lispcad/router/FEATURE_CENSUS.md",
      "skills/lispcad/router/RULE_COVERAGE.yaml",
      "tools/export_dxf.py",
      ...router.default_load,
    ]);
    for (const routes of [
      router.source_routes,
      router.mode_routes,
      router.feature_routes,
    ])
      for (const r of Object.values(routes))
        for (const p of r.load) paths.add(p);
    const files: Record<string, string> = {},
      moduleHashes: Record<string, string> = {};
    for (const p of [...paths].sort()) {
      safe(p);
      files[p] = readFileSync(join(root, p), "utf8");
      moduleHashes[p] = hash(files[p]!);
    }
    const snapshotId = hash(JSON.stringify(moduleHashes));
    const pin: ReleasePin = {
      release,
      snapshotId,
      entrypointSha256: moduleHashes["AI_ENTRYPOINT.md"]!,
      routerSha256: moduleHashes["skills/lispcad/router/ROUTER.yaml"]!,
      routerDataSha256: hash(JSON.stringify(router)),
      censusSha256: moduleHashes["skills/lispcad/router/FEATURE_CENSUS.md"]!,
      coverageSha256: moduleHashes["skills/lispcad/router/RULE_COVERAGE.yaml"]!,
      moduleHashes,
      repositoryCommit: process.env.TRAINAICAD_SOURCE_COMMIT ?? null,
    };
    const dir = join(dataRoot(), "rules", snapshotId);
    mkdirSync(dir, { recursive: true });
    for (const [p, text] of Object.entries(files)) {
      const dest = join(dir, p);
      mkdirSync(dirname(dest), { recursive: true });
      if (!existsSync(dest)) writeFileSync(dest, text, { flag: "wx" });
      if (hash(readFileSync(dest)) !== moduleHashes[p])
        throw new Error(`snapshot tampered:${p}`);
    }
    const manifest = join(dir, "manifest.json");
    if (!existsSync(manifest)) {
      writeFileSync(
        manifest + ".tmp",
        JSON.stringify({ ...pin, router, files }),
      );
      renameSync(manifest + ".tmp", manifest);
    }
    return pin;
  } catch (e) {
    throw new Error(`SKILL_FRESHNESS_UNVERIFIED:${String(e)}`);
  }
}
export const snapshotRoot = (pin: ReleasePin) =>
  join(dataRoot(), "rules", pin.snapshotId);
export function readSnapshot(pin: ReleasePin): Snapshot {
  const snap = JSON.parse(
    readFileSync(join(snapshotRoot(pin), "manifest.json"), "utf8"),
  ) as Snapshot;
  if (
    hash(JSON.stringify(snap.moduleHashes)) !== pin.snapshotId ||
    hash(JSON.stringify(snap.router)) !== pin.routerDataSha256
  )
    throw new Error("RULE_SNAPSHOT_TAMPERED");
  for (const [p, h] of Object.entries(pin.moduleHashes)) {
    safe(p);
    if (
      hash(readFileSync(join(snapshotRoot(pin), p))) !== h ||
      hash(snap.files[p]!) !== h
    )
      throw new Error(`RULE_SNAPSHOT_TAMPERED:${p}`);
  }
  return snap;
}
export function selectRules(
  pin: ReleasePin,
  mode: JobMode,
  evidence?: CadEvidenceV1,
): string[] {
  const r = readSnapshot(pin).router,
    selected = new Set([...r.default_load, ...r.source_routes[mode]!.load]);
  if (!evidence) return [...selected];
  const bent =
    evidence.bends.length > 0 || evidence.contour.topology !== "PLATE";
  for (const p of r.mode_routes[
    evidence.contour.topology === "UNKNOWN"
      ? "UNKNOWN"
      : bent
        ? "BEND"
        : "FLAT_NO_BEND"
  ]!.load)
    selected.add(p);
  const present = new Set(["MATERIAL_RULES"]),
    aliases: Record<string, string> = {
      SLOT: "SLOT_STRAIGHT",
      CHAMFER: "CHAMFER_FILLET",
      RADIUS: "CHAMFER_FILLET",
    };
  for (const f of evidence.features) {
    if (f.family === "CUTOUT") continue;
    const name = aliases[f.family] ?? f.family;
    if (!r.feature_routes[name])
      throw new Error(`ROUTING_COVERAGE_GAP:${f.family}`);
    present.add(name);
  }
  for (const m of evidence.markings) present.add(m.family);
  if (bent) present.add("NOBI");
  if (evidence.contour.topology === "BOXMET") present.add("BOXMET");
  if (evidence.bends.some((b) => b.angle.value < 85))
    present.add("ACUTE_BEND_LT85");
  const visited = new Set<string>();
  const load = (name: string) => {
    if (visited.has(name)) return;
    visited.add(name);
    const a = r.dependency_aliases[name],
      route = a ? r[a.route_group][a.route_id] : r.feature_routes[name];
    if (!route) throw new Error(`ROUTING_COVERAGE_GAP:${name}`);
    for (const p of route.load) selected.add(p);
    for (const dep of route.depends_on ?? []) load(dep);
  };
  for (const name of Object.keys(r.feature_routes)) {
    const state = evidence.census?.[name]?.state ?? "UNKNOWN";
    if (present.has(name) && state === "NO")
      throw new Error(`CENSUS_CONTRADICTION:${name}`);
    if (present.has(name) || state !== "NO") load(name);
  }
  return [...selected];
}
export function rulesBundle(pin: ReleasePin, paths: string[]) {
  const snap = readSnapshot(pin);
  return paths.map((path) => {
    if (!snap.files[path]) throw new Error(`RULE_NOT_IN_SNAPSHOT:${path}`);
    return { path, sha256: pin.moduleHashes[path], content: snap.files[path] };
  });
}
