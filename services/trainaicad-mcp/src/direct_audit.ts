import { execFileSync } from "node:child_process";
import { existsSync, readFileSync, writeFileSync } from "node:fs";
import { extname, join } from "node:path";
import * as z from "zod/v4";
import { dataRoot } from "./ingest.js";
import type { CadJob, DirectAuditResult } from "./model.js";

const Window = z.tuple([
  z.number().finite(), z.number().finite(),
  z.number().finite(), z.number().finite()
]);

const ExplicitTransform = z.object({
  rotationDeg: z.number().finite().default(0),
  mirrorX: z.boolean().default(false),
  mirrorY: z.boolean().default(false),
  proofRefs: z.array(z.string().min(1)).optional()
}).superRefine((v, ctx) => {
  const nonIdentity = Math.abs(v.rotationDeg) > 1e-12 || v.mirrorX || v.mirrorY;
  if (nonIdentity && !v.proofRefs?.length) {
    ctx.addIssue({ code: "custom", message: "rotation/mirror requires proofRefs" });
  }
});

export const DirectAuditConfig = z.object({
  aiMmPerUnit: z.number().positive(),
  referenceMmPerUnit: z.number().positive(),
  aiUnitProofRefs: z.array(z.string().min(1)).min(1),
  referenceUnitProofRefs: z.array(z.string().min(1)).min(1),
  curveToleranceMm: z.number().positive().max(1),
  toleranceProofRefs: z.array(z.string().min(1)).min(1),
  parts: z.array(z.object({
    code: z.string().min(1),
    mappingProofRefs: z.array(z.string().min(1)).min(1),
    aiWindow: Window.optional(),
    referenceWindow: Window.optional(),
    aiTransform: ExplicitTransform.optional(),
    referenceTransform: ExplicitTransform.optional()
  })).min(1)
}).superRefine((v, ctx) => {
  if (v.parts.length > 1) {
    v.parts.forEach((part, index) => {
      if (!part.aiWindow || !part.referenceWindow) {
        ctx.addIssue({
          code: "custom",
          path: ["parts", index],
          message: "multi-part direct audit requires explicit aiWindow and referenceWindow per code"
        });
      }
    });
  }
});
export type DirectAuditConfig = z.infer<typeof DirectAuditConfig>;

function pythonBin(): string {
  if (process.env.TRAINAICAD_PYTHON) return process.env.TRAINAICAD_PYTHON;
  return process.platform === "win32" ? "python" : "python3";
}

function storedDxf(sha256: string, fileName: string, roles: string[]): string {
  const ext = extname(fileName).toLowerCase();
  if (ext !== ".dxf") throw new Error(`DIRECT_AUDIT_REQUIRES_DXF:${fileName}`);
  for (const role of roles) {
    const path = join(dataRoot(), "sources", role, sha256.slice(0, 2), `${sha256}.dxf`);
    if (existsSync(path)) return path;
  }
  throw new Error(`DIRECT_AUDIT_SOURCE_NOT_INGESTED:${fileName}`);
}

export function runDirectAudit(job: CadJob, repoRoot: string, rawConfig: unknown): DirectAuditResult {
  if (job.mode !== "DIRECT_EXISTING_DXF_AUDIT") {
    throw new Error(`DIRECT_AUDIT_WRONG_MODE:${job.mode}`);
  }
  if (!job.dxf) throw new Error("DIRECT_AUDIT_REFERENCE_MISSING");
  const config = DirectAuditConfig.parse(rawConfig);
  const aiPath = storedDxf(job.source.sha256, job.source.fileName, ["AI_DXF", "DRAWING"]);
  const referencePath = storedDxf(job.dxf.sha256, job.dxf.fileName, ["REFERENCE_DXF", "DATA_DXF"]);
  const configPath = join(dataRoot(), "jobs", `${job.jobId}.direct-audit.json`);
  writeFileSync(configPath, JSON.stringify(config, null, 2));

  const script = join(repoRoot, "services", "trainaicad-mcp", "python", "compare_dxf.py");
  const stdout = execFileSync(
    pythonBin(),
    [script, aiPath, referencePath, configPath],
    { cwd: repoRoot, encoding: "utf8", stdio: ["ignore", "pipe", "pipe"] }
  ).trim();
  const raw = JSON.parse(stdout) as { results?: DirectAuditResult["parts"] };
  if (!raw.results || raw.results.length !== config.parts.length) {
    throw new Error("DIRECT_AUDIT_RESULT_COUNT_MISMATCH");
  }

  const result: DirectAuditResult = {
    aiSha256: job.source.sha256,
    referenceSha256: job.dxf.sha256,
    aiMmPerUnit: config.aiMmPerUnit,
    referenceMmPerUnit: config.referenceMmPerUnit,
    curveToleranceMm: config.curveToleranceMm,
    parts: raw.results,
    boundary:
      "DXF-to-DXF physical comparison first. PDF/source diagnosis is a separate next step. Layout translation may be normalized; rotation/mirror only when explicitly proof-backed."
  };
  return result;
}
