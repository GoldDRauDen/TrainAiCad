import { createHash } from "node:crypto";
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { join, resolve } from "node:path";
import { spawnSync } from "node:child_process";
import * as z from "zod/v4";
import { artifact } from "./artifact.js";
import { jobStore, resolveRepoRoot } from "./core.js";
import { dataRoot } from "./ingest.js";
import type { CadJob } from "./model.js";
import {
  censusContradictions,
  readSnapshot,
  selectRules,
  snapshotRoot,
} from "./snapshot.js";
import { sha256 } from "./source.js";

const Finite = z.number().finite();
const XY = z.tuple([Finite, Finite]);
const Vertex = z.tuple([Finite, Finite, Finite]);
const CheckValue = z.enum(["PASS", "N/A", "FLAGGED"]);
const GateValue = z.enum(["PASS", "N/A"]);

export const RepoDirectChecks = z.object({
  contour_topology: CheckValue,
  datum: CheckValue,
  feature_count: CheckValue,
  unfold: CheckValue,
  containment: CheckValue,
  bend_domain: CheckValue,
  material_rules: CheckValue,
  slot_semantics: CheckValue,
});

const CommonEntity = {
  role: z.string().min(1),
  color: z.number().int().optional(),
  linetype: z.string().min(1).optional(),
  view_id: z.string().min(1).optional(),
};

export const RepoDirectEntity = z.discriminatedUnion("type", [
  z.object({ ...CommonEntity, type: z.literal("LWPOLYLINE"), closed: z.boolean(), vertices: z.array(Vertex).min(2) }),
  z.object({ ...CommonEntity, type: z.literal("CIRCLE"), center: XY, radius: z.number().positive() }),
  z.object({ ...CommonEntity, type: z.literal("POINT"), point: XY }),
  z.object({ ...CommonEntity, type: z.literal("LINE"), start: XY, end: XY }),
  z.object({ ...CommonEntity, type: z.literal("ARC"), center: XY, radius: z.number().positive(), start_angle: Finite, end_angle: Finite }),
  z.object({ ...CommonEntity, type: z.literal("TEXT"), insert: XY, text: z.string().min(1), height: z.number().positive().optional() }),
]);

export const RepoDirectPart = z.object({
  code: z.string().regex(/^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$/),
  material: z.string().min(1),
  thickness_mm: z.number().positive(),
  status: z.enum(["PASS", "PREVIEW", "VIEWS_ONLY"]),
  preview_reason: z.string().min(1).optional(),
  flags: z.array(z.string().min(1)).default([]),
  checks: RepoDirectChecks,
  entities: z.array(RepoDirectEntity).min(1),
});

export const RepoDirectGate = z.object({
  code: z.string().min(1),
  finalCensusClosed: z.boolean(),
  sourceFeatureCompleteness: z.boolean(),
  crossFeatureValidation: z.boolean(),
  constraintsClosed: z.boolean(),
  localFaceTransforms: GateValue,
  foldBackSourceReprojection: GateValue,
  rawDataSnapshot: GateValue,
  sameParameterGate: GateValue,
  manufacturingChangeLedger: GateValue,
  untouchedDataInvariance: GateValue,
  sourceReprojection: GateValue,
  sourceActiveFamilies: z.array(z.string().min(1)).min(1),
  canonicalFamilies: z.array(z.string().min(1)).min(1),
  serializedFamilies: z.array(z.string().min(1)).min(1),
  evidenceRefs: z.array(z.string().min(1)).min(1),
});

export const RepoDirectSubmissionV1 = z.object({
  schema: z.literal("REPO_DIRECT_DXF_V1"),
  jobId: z.string().regex(/^cad_[a-f0-9]{16}$/),
  sourceSha256: z.string().regex(/^[a-fA-F0-9]{64}$/),
  dxfSha256: z.string().regex(/^[a-fA-F0-9]{64}$/).optional(),
  ruleSnapshotId: z.string().min(1),
  parts: z.array(RepoDirectPart).min(1),
  gates: z.array(RepoDirectGate).min(1),
});
export type RepoDirectSubmissionV1 = z.infer<typeof RepoDirectSubmissionV1>;

type RepoDirectPartValue = z.infer<typeof RepoDirectPart>;
type RepoDirectGateValue = z.infer<typeof RepoDirectGate>;

function unique(values: string[]) {
  return [...new Set(values)];
}

function sameSet(a: string[], b: string[]) {
  const aa = [...new Set(a)].sort();
  const bb = [...new Set(b)].sort();
  return aa.length === bb.length && aa.every((v, i) => v === bb[i]);
}

function missingSubset(required: string[], actual: string[]) {
  const have = new Set(actual);
  return unique(required).filter((v) => !have.has(v));
}

function countEntities(part: RepoDirectPartValue) {
  const count = (predicate: (entity: z.infer<typeof RepoDirectEntity>) => boolean) =>
    part.entities.filter(predicate).length;
  return {
    hole: count((e) => e.type === "CIRCLE" && e.role === "hole"),
    slot: count((e) => e.type === "LWPOLYLINE" && e.role === "slot"),
    cutout: count((e) => e.type === "LWPOLYLINE" && e.role === "cutout"),
    piasu: count((e) => e.type === "POINT" && ["through_piercing", "ordinary_point"].includes(e.role)),
    bend: count((e) => e.type === "LINE" && e.role === "bend"),
  };
}

export function isCensusItemClosed(
  item: { state: "YES" | "NO" | "UNKNOWN"; evidence: string[] } | undefined,
) {
  if (!item || item.state === "UNKNOWN") return false;
  if (item.state === "NO") return true;
  return item.evidence.length > 0;
}

function addReviewFlag(part: RepoDirectPartValue, flag: string) {
  if (!part.flags.includes(flag)) part.flags.push(flag);
  if (part.status === "PASS") part.status = "PREVIEW";
  if (part.status === "PREVIEW") part.preview_reason = "review_flag_known_geometry";
}

function validatePart(
  job: CadJob,
  part: RepoDirectPartValue,
  gate: RepoDirectGateValue,
) {
  const evidence = job.evidence.find((e) => e.code === part.code);
  if (!evidence) throw new Error(`REPO_DIRECT_EVIDENCE_NOT_FOUND:${part.code}`);
  const route = job.routes.find((r) => r.code === part.code);
  if (!route) throw new Error(`REPO_DIRECT_ROUTE_NOT_FOUND:${part.code}`);

  // Missing/tampered rule authority is a hard blocker. Evidence inconsistency
  // is not: load the applicable rules, then downgrade the affected part to a
  // review-only flag so the multi-code job can still complete.
  const router = readSnapshot(job.production).router;
  selectRules(job.production, job.mode, evidence);
  for (const family of censusContradictions(evidence))
    addReviewFlag(part, `CENSUS_CONTRADICTION:${family}`);

  for (const family of Object.keys(router.feature_routes)) {
    if (!isCensusItemClosed(evidence.census?.[family]))
      addReviewFlag(part, `FINAL_CENSUS_NOT_CLOSED:${family}`);
  }
  if (!gate.finalCensusClosed) addReviewFlag(part, "FINAL_CENSUS_GATE_NOT_CLOSED");
  if (!gate.sourceFeatureCompleteness) addReviewFlag(part, "SOURCE_FEATURE_COMPLETENESS_NOT_CLOSED");
  if (!gate.crossFeatureValidation) addReviewFlag(part, "CROSS_FEATURE_VALIDATION_NOT_CLOSED");
  if (!gate.constraintsClosed) addReviewFlag(part, "CONSTRAINTS_NOT_CLOSED");
  if (route.status !== "ROUTED") addReviewFlag(part, "ROUTING_REVIEW_REQUIRED");

  for (const uncertainty of evidence.uncertainties) {
    if (uncertainty.blocking)
      addReviewFlag(part, `SOURCE_UNCERTAINTY:${uncertainty.code}`);
  }

  const material = evidence.material.family ?? evidence.material.printed;
  const thickness = evidence.material.thickness?.value;
  if (!material || !thickness) {
    addReviewFlag(part, "MATERIAL_THICKNESS_UNPROVED");
  } else {
    if (part.material.trim().toUpperCase() !== material.trim().toUpperCase())
      addReviewFlag(part, `MATERIAL_MISMATCH:${part.material}!=${material}`);
    if (Math.abs(part.thickness_mm - thickness) > 1e-9)
      addReviewFlag(part, `THICKNESS_MISMATCH:${part.thickness_mm}!=${thickness}`);
  }

  const expectedFamilies = route.mechanical.featureInventory;
  if (!sameSet(expectedFamilies, gate.sourceActiveFamilies))
    addReviewFlag(part, "SOURCE_FAMILY_MISMATCH");
  const missingCanonical = missingSubset(expectedFamilies, gate.canonicalFamilies);
  if (missingCanonical.length)
    addReviewFlag(part, `CANONICAL_FAMILY_MISSING:${missingCanonical.join(",")}`);
  const missingSerialized = missingSubset(expectedFamilies, gate.serializedFamilies);
  if (missingSerialized.length)
    addReviewFlag(part, `SERIALIZED_FAMILY_MISSING:${missingSerialized.join(",")}`);

  const expected = {
    hole: evidence.features.filter((f) => f.family === "HOLE" || f.family === "TAP").reduce((sum, f) => sum + f.quantity, 0),
    slot: evidence.features.filter((f) => f.family === "SLOT" || f.family === "CURVED_SLOT").reduce((sum, f) => sum + f.quantity, 0),
    cutout: evidence.features.filter((f) => f.family === "CUTOUT").reduce((sum, f) => sum + f.quantity, 0),
    piasu: evidence.features.filter((f) => f.family === "PIASU").reduce((sum, f) => sum + f.quantity, 0),
  };
  const actual = countEntities(part);
  for (const key of ["hole", "slot", "cutout", "piasu"] as const) {
    if (actual[key] !== expected[key])
      addReviewFlag(part, `FEATURE_COUNT_MISMATCH:${key}:${actual[key]}!=${expected[key]}`);
  }

  const bent = evidence.bends.length > 0 || route.mode === "BEND_UNFOLD";
  if (bent && actual.bend < evidence.bends.length * 2)
    addReviewFlag(part, `BEND_LINES_INCOMPLETE:${actual.bend}<${evidence.bends.length * 2}`);

  for (const key of ["contour_topology", "datum", "feature_count", "containment", "material_rules"] as const) {
    if (part.checks[key] !== "PASS") addReviewFlag(part, `CHECK_NOT_PASS:${key}`);
  }
  if (expected.slot > 0 && part.checks.slot_semantics !== "PASS")
    addReviewFlag(part, "SLOT_SEMANTICS_NOT_PASS");

  if (bent) {
    if (part.checks.unfold !== "PASS") addReviewFlag(part, "UNFOLD_NOT_PASS");
    if (part.checks.bend_domain !== "PASS") addReviewFlag(part, "BEND_DOMAIN_NOT_PASS");
    if (gate.localFaceTransforms !== "PASS") addReviewFlag(part, "LOCAL_FACE_TRANSFORMS_NOT_PASS");
    if (gate.foldBackSourceReprojection !== "PASS") addReviewFlag(part, "FOLD_BACK_REPROJECTION_NOT_PASS");
  }

  if (job.mode === "PDF_DATA_RAW") {
    for (const [name, value] of Object.entries({
      rawDataSnapshot: gate.rawDataSnapshot,
      sameParameterGate: gate.sameParameterGate,
      manufacturingChangeLedger: gate.manufacturingChangeLedger,
      untouchedDataInvariance: gate.untouchedDataInvariance,
      sourceReprojection: gate.sourceReprojection,
    })) {
      if (value !== "PASS") addReviewFlag(part, `DATA_GATE_NOT_PASS:${name}`);
    }
  }

  if (part.status === "PREVIEW") {
    if (!part.flags.length) part.flags.push("CALLER_PREVIEW");
    part.preview_reason = part.preview_reason ?? "review_flag_known_geometry";
  }
  if (part.status === "VIEWS_ONLY") {
    if (!part.flags.length) part.flags.push("CALLER_VIEWS_ONLY");
    part.preview_reason = part.preview_reason ?? "separate_source_views";
  }
}

export function validateRepoDirectSubmission(raw: unknown): {
  job: CadJob;
  submission: RepoDirectSubmissionV1;
  submissionSha256: string;
} {
  const submission = RepoDirectSubmissionV1.parse(raw);
  const job = jobStore.get(submission.jobId);
  if (!["ROUTED", "REVIEW_REQUIRED", "GEOMETRY_READY"].includes(job.state))
    throw new Error(`REPO_DIRECT_NOT_ALLOWED_IN_STATE:${job.state}`);
  if (job.mode === "DIRECT_EXISTING_DXF_AUDIT")
    throw new Error("REPO_DIRECT_EXPORT_NOT_APPLICABLE_TO_DIRECT_AUDIT");
  if (submission.sourceSha256.toLowerCase() !== job.source.sha256.toLowerCase())
    throw new Error("REPO_DIRECT_SOURCE_SHA_MISMATCH");
  if (submission.ruleSnapshotId !== job.production.snapshotId)
    throw new Error("REPO_DIRECT_RULE_SNAPSHOT_MISMATCH");
  if (job.dxf) {
    if (!submission.dxfSha256 || submission.dxfSha256.toLowerCase() !== job.dxf.sha256.toLowerCase())
      throw new Error("REPO_DIRECT_DXF_SHA_MISMATCH");
  } else if (submission.dxfSha256) {
    throw new Error("REPO_DIRECT_UNEXPECTED_DXF_SHA");
  }

  readSnapshot(job.production);
  const expectedCodes = job.evidence.map((e) => e.code);
  const partCodes = submission.parts.map((p) => p.code);
  const gateCodes = submission.gates.map((g) => g.code);
  if (!sameSet(expectedCodes, partCodes) || !sameSet(expectedCodes, gateCodes) ||
      new Set(partCodes).size !== partCodes.length || new Set(gateCodes).size !== gateCodes.length)
    throw new Error("REPO_DIRECT_CODE_SET_MISMATCH");
  if (partCodes.some((code, i) => code !== expectedCodes[i]))
    throw new Error("REPO_DIRECT_CODE_ORDER_MISMATCH");

  for (const part of submission.parts) {
    const gate = submission.gates.find((g) => g.code === part.code)!;
    validatePart(job, part, gate);
  }

  const submissionSha256 = createHash("sha256").update(JSON.stringify(submission)).digest("hex");
  return { job, submission, submissionSha256 };
}

function pythonExe() {
  return process.env.TRAINAICAD_PYTHON ?? (process.platform === "win32" ? "python" : "python3");
}

function runBridge(job: CadJob, inputPath: string, outDir: string) {
  const repoRoot = resolveRepoRoot();
  const bridge = join(repoRoot, "services", "trainaicad-mcp", "bridge", "dxf_bridge.py");
  const proc = spawnSync(pythonExe(), [bridge, "export", inputPath, outDir], {
    cwd: repoRoot,
    encoding: "utf8",
    timeout: 60_000,
    env: { ...process.env, TRAINAICAD_RULE_SNAPSHOT: snapshotRoot(job.production) },
    maxBuffer: 16 * 1024 * 1024,
  });
  if (proc.error) throw proc.error;
  if (proc.status !== 0)
    throw new Error(`REPO_DIRECT_DXF_BRIDGE_FAILED:${(proc.stderr || proc.stdout || "").trim()}`);
  const lines = (proc.stdout || "").trim().split(/\r?\n/).filter(Boolean);
  if (!lines.length) throw new Error("REPO_DIRECT_DXF_BRIDGE_EMPTY_OUTPUT");
  return JSON.parse(lines.at(-1)!);
}

/** Legacy repo-direct export entry retained for compatibility. Preferred MCP path is repo-direct-e2e.ts. */
export function exportRepoDirectDxf(raw: unknown): {
  job: CadJob;
  submissionSha256: string;
  artifact: { fileName: string; sha256: string; url: string | null };
} {
  const { job, submission, submissionSha256 } = validateRepoDirectSubmission(raw);
  job.geometrySources = [];
  job.geometry = [];
  job.manufacturingQa = [];
  job.computedQa = undefined;
  job.sourceChecks = undefined;
  job.dxfOutput = undefined;
  job.dxfAudit = undefined;
  job.flags = [];

  if (job.state !== "GEOMETRY_READY") jobStore.transition(job.jobId, "GEOMETRY_READY");
  const outDir = join(dataRoot(), "outputs", job.jobId);
  mkdirSync(outDir, { recursive: true });
  const payload = { job_id: job.jobId, parts: submission.parts };
  const inputPath = join(outDir, "repo_direct_serializer_input.json");
  writeFileSync(inputPath, JSON.stringify(payload, null, 2));
  writeFileSync(join(outDir, "repo_direct_trace.json"), JSON.stringify({
    schema: submission.schema,
    submissionSha256,
    sourceSha256: submission.sourceSha256,
    dxfSha256: submission.dxfSha256 ?? null,
    ruleSnapshotId: submission.ruleSnapshotId,
    gates: submission.gates,
  }, null, 2));

  const result = runBridge(job, inputPath, outDir);
  if (!result?.ok || !result?.manifest?.filename || !result?.dxf_path || !result?.manifest_path)
    throw new Error("REPO_DIRECT_DXF_BRIDGE_INVALID_RESULT");
  const abs = resolve(result.dxf_path);
  if (!existsSync(abs)) throw new Error("REPO_DIRECT_DXF_FILE_MISSING");
  job.dxfOutput = {
    sha256: sha256(readFileSync(abs)),
    fileName: result.manifest.filename,
    relativePath: join("outputs", job.jobId, result.manifest.filename),
    absolutePath: abs,
    manifestPath: resolve(result.manifest_path),
    serializerContract: result.manifest.contract,
    codeOrder: Array.isArray(result.manifest.parts)
      ? result.manifest.parts.map((part: any) => String(part.code))
      : submission.parts.map((part) => part.code),
    writtenAt: new Date().toISOString(),
  };

  jobStore.transition(job.jobId, "DXF_WRITTEN");
  const audited = jobStore.auditDxf(job.jobId);
  const file = artifact(audited);
  return { job: audited, submissionSha256, artifact: { fileName: file.fileName, sha256: file.sha256, url: file.url } };
}
