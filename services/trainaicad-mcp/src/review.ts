import { createHash } from "node:crypto";
import { execFileSync } from "node:child_process";
import { existsSync, mkdirSync, readFileSync, statSync, writeFileSync } from "node:fs";
import { basename, join } from "node:path";
import * as z from "zod/v4";
import { dataRoot } from "./ingest.js";
import type { CadJob, DxfArtifact } from "./model.js";

const Vec2 = z.tuple([z.number().finite(), z.number().finite()]);
const Vertex = z.tuple([z.number().finite(), z.number().finite(), z.number().finite()]);
const ProofRefs = z.array(z.string().min(1)).min(1);

const Common = {
  role: z.string().min(1),
  color: z.union([z.literal(1), z.literal(3), z.literal(6), z.literal(256)]).optional(),
  linetype: z.string().min(1).optional(),
  view_id: z.string().min(1).optional(),
  evidenceRefs: ProofRefs
};

const ReviewEntity = z.discriminatedUnion("type", [
  z.object({
    type: z.literal("LWPOLYLINE"),
    ...Common,
    closed: z.boolean(),
    vertices: z.array(Vertex).min(2)
  }),
  z.object({ type: z.literal("CIRCLE"), ...Common, center: Vec2, radius: z.number().positive() }),
  z.object({ type: z.literal("LINE"), ...Common, start: Vec2, end: Vec2 }),
  z.object({
    type: z.literal("ARC"),
    ...Common,
    center: Vec2,
    radius: z.number().positive(),
    start_angle: z.number().finite(),
    end_angle: z.number().finite()
  }),
  z.object({ type: z.literal("POINT"), ...Common, point: Vec2 }),
  z.object({
    type: z.literal("TEXT"),
    ...Common,
    insert: Vec2,
    text: z.string().min(1),
    height: z.number().positive().default(2.5)
  })
]);

const Check = z.enum(["PASS", "N/A", "FLAGGED"]);
const Checks = z.object({
  contour_topology: Check,
  datum: Check,
  feature_count: Check,
  unfold: Check,
  containment: Check,
  bend_domain: Check,
  material_rules: Check,
  slot_semantics: Check
});

const ReviewPart = z.object({
  code: z.string().min(1),
  status: z.enum(["PASS", "PREVIEW", "VIEWS_ONLY"]),
  checks: Checks,
  flags: z.array(z.string().min(1)).default([]),
  preview_reason: z.enum(["numeric_only_known_topology", "separate_source_views"]).optional(),
  entities: z.array(ReviewEntity).min(1)
});

export const ReviewOutputV1 = z.object({
  schema: z.literal("REVIEW_OUTPUT_V1"),
  parts: z.array(ReviewPart).min(1)
}).superRefine((v, ctx) => {
  if (!v.parts.some((p) => p.status !== "PASS")) {
    ctx.addIssue({ code: "custom", message: "review export requires at least one PREVIEW or VIEWS_ONLY part" });
  }
  for (const [index, part] of v.parts.entries()) {
    if (part.status === "PREVIEW" && part.preview_reason !== "numeric_only_known_topology") {
      ctx.addIssue({ code: "custom", path: ["parts", index], message: "PREVIEW requires numeric_only_known_topology" });
    }
    if (part.status === "VIEWS_ONLY" && part.preview_reason !== "separate_source_views") {
      ctx.addIssue({ code: "custom", path: ["parts", index], message: "VIEWS_ONLY requires separate_source_views" });
    }
  }
});
export type ReviewOutputV1 = z.infer<typeof ReviewOutputV1>;

function pythonBin(): string {
  if (process.env.TRAINAICAD_PYTHON) return process.env.TRAINAICAD_PYTHON;
  return process.platform === "win32" ? "python" : "python3";
}

function sha256File(path: string): string {
  return createHash("sha256").update(readFileSync(path)).digest("hex");
}

function stripProofs(entity: z.infer<typeof ReviewEntity>) {
  const { evidenceRefs: _proofs, ...rest } = entity;
  return rest;
}

export function exportReviewOnly(job: CadJob, repoRoot: string, raw: unknown): DxfArtifact {
  if (!["REVIEW_REQUIRED", "SOURCE_CONFLICT"].includes(job.state)) {
    throw new Error(`REVIEW_EXPORT_NOT_ALLOWED_IN_STATE:${job.state}`);
  }
  if (job.mode === "DIRECT_EXISTING_DXF_AUDIT") {
    throw new Error("REVIEW_EXPORT_NOT_APPLICABLE_TO_DIRECT_AUDIT");
  }

  const review = ReviewOutputV1.parse(raw);
  const expectedCodes = job.evidence.map((e) => e.code);
  const actualCodes = review.parts.map((p) => p.code);
  if (JSON.stringify(actualCodes) !== JSON.stringify(expectedCodes)) {
    throw new Error("REVIEW_EXPORT_CODE_ORDER_MISMATCH");
  }

  const evidenceByCode = new Map(job.evidence.map((e) => [e.code, e] as const));
  const parts = review.parts.map((part) => {
    const evidence = evidenceByCode.get(part.code)!;
    const material = evidence.material.printed ?? evidence.material.family;
    const thickness = evidence.material.thickness?.value;
    if (!material) throw new Error(`REVIEW_MATERIAL_MISSING:${part.code}`);
    if (!(thickness && thickness > 0)) throw new Error(`REVIEW_THICKNESS_MISSING:${part.code}`);
    return {
      code: part.code,
      material,
      thickness_mm: thickness,
      status: part.status,
      checks: part.checks,
      flags: part.flags,
      ...(part.preview_reason ? { preview_reason: part.preview_reason } : {}),
      entities: part.entities.map(stripProofs)
    };
  });

  const root = join(dataRoot(), "outputs", job.jobId);
  const outDir = join(root, "review");
  mkdirSync(outDir, { recursive: true });
  const input = join(root, "review_job.json");
  writeFileSync(input, JSON.stringify({ job_id: job.jobId, parts }, null, 2));

  const exporter = join(repoRoot, "tools", "export_dxf.py");
  const stdout = execFileSync(
    pythonBin(),
    [exporter, input, outDir, "--write-manifest"],
    { cwd: repoRoot, encoding: "utf8", stdio: ["ignore", "pipe", "pipe"] }
  ).trim();
  const result = JSON.parse(stdout.split(/\r?\n/).filter(Boolean).at(-1) ?? "{}") as { files?: string[] };
  const dxfName = result.files?.find((f) => f.endsWith("_ALL_REVIEW_ONLY.dxf"));
  if (!dxfName) throw new Error("REVIEW_EXPORTER_RETURNED_NO_REVIEW_DXF");
  const dxfPath = join(outDir, basename(dxfName));
  const manifestPath = join(outDir, `${job.jobId}_MANIFEST.json`);
  if (!existsSync(dxfPath) || !existsSync(manifestPath)) throw new Error("REVIEW_EXPORT_OUTPUT_MISSING");
  const manifest = JSON.parse(readFileSync(manifestPath, "utf8")) as { status?: string };
  if (manifest.status !== "REVIEW_ONLY") throw new Error("REVIEW_EXPORT_STATUS_FAILURE");

  return {
    filename: basename(dxfPath),
    relativePath: join("outputs", job.jobId, "review", basename(dxfPath)).replaceAll("\\", "/"),
    sha256: sha256File(dxfPath),
    bytes: statSync(dxfPath).size,
    units: "mm",
    manifestRelativePath: join("outputs", job.jobId, "review", basename(manifestPath)).replaceAll("\\", "/"),
    reviewOnly: true
  };
}
