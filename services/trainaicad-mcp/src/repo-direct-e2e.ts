import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { join, resolve } from "node:path";
import { spawnSync } from "node:child_process";
import { artifact } from "./artifact.js";
import { jobStore, resolveRepoRoot } from "./core.js";
import { dataRoot } from "./ingest.js";
import type { CadJob } from "./model.js";
import { snapshotRoot } from "./snapshot.js";
import { sha256 } from "./source.js";
import {
  validateRepoDirectSubmission,
  type RepoDirectSubmissionV1,
} from "./repo-direct.js";

function pythonExe() {
  return (
    process.env.TRAINAICAD_PYTHON ??
    (process.platform === "win32" ? "python" : "python3")
  );
}

function bridgePath() {
  return join(
    resolveRepoRoot(),
    "services",
    "trainaicad-mcp",
    "bridge",
    "dxf_bridge.py",
  );
}

function runBridge(job: CadJob, args: string[]) {
  const proc = spawnSync(pythonExe(), [bridgePath(), ...args], {
    cwd: resolveRepoRoot(),
    encoding: "utf8",
    timeout: 60_000,
    env: {
      ...process.env,
      TRAINAICAD_RULE_SNAPSHOT: snapshotRoot(job.production),
    },
    maxBuffer: 16 * 1024 * 1024,
  });
  if (proc.error) throw proc.error;
  if (proc.status !== 0)
    throw new Error(
      `REPO_DIRECT_DXF_BRIDGE_FAILED:${(proc.stderr || proc.stdout || "").trim()}`,
    );
  const lines = (proc.stdout || "").trim().split(/\r?\n/).filter(Boolean);
  if (!lines.length) throw new Error("REPO_DIRECT_DXF_BRIDGE_EMPTY_OUTPUT");
  return JSON.parse(lines.at(-1)!);
}

function expectedCodeLabels(submission: RepoDirectSubmissionV1) {
  return submission.parts.map((part) => {
    if (part.status === "PASS") return part.code;
    if (part.status === "VIEWS_ONLY") return `${part.code} [VIEWS_ONLY - FLAG]`;
    return `${part.code} [FLAG]`;
  });
}

function auditSavedDxf(job: CadJob, submission: RepoDirectSubmissionV1) {
  if (!job.dxfOutput) throw new Error("REPO_DIRECT_AUDIT_NO_OUTPUT");
  const result = runBridge(job, ["audit", job.dxfOutput.absolutePath]);
  const audit = {
    ok: Boolean(result.ok),
    auditErrorCount: Number(result.audit_error_count ?? -1),
    auditFixCount: Number(result.audit_fix_count ?? -1),
    insunits: Number(result.insunits ?? 0),
    entityCount: Number(result.entity_count ?? 0),
    layers: (result.layers ?? {}) as Record<string, number>,
    entityTypes: (result.entity_types ?? {}) as Record<string, number>,
    labels: Array.isArray(result.labels)
      ? result.labels.map((value: unknown) => String(value))
      : [],
    aiMetaPlot:
      result.ai_meta_plot === null || result.ai_meta_plot === undefined
        ? null
        : Number(result.ai_meta_plot),
    auditedAt: new Date().toISOString(),
  };

  if (!audit.ok || audit.auditErrorCount !== 0)
    throw new Error("REPO_DIRECT_READBACK_AUDIT_FAILED");
  if (audit.insunits !== 4)
    throw new Error("REPO_DIRECT_READBACK_UNITS_NOT_MM");
  if (audit.aiMetaPlot !== 0)
    throw new Error("REPO_DIRECT_READBACK_AI_META_PLOT_ENABLED");
  if (!audit.layers["0"])
    throw new Error("REPO_DIRECT_READBACK_NO_MANUFACTURING_GEOMETRY");

  const expected = expectedCodeLabels(submission);
  const expectedSet = new Set(expected);
  const actualCodeLabels = audit.labels.filter((label) => expectedSet.has(label));
  if (actualCodeLabels.join("|") !== expected.join("|"))
    throw new Error("REPO_DIRECT_READBACK_CODE_ORDER_MISMATCH");

  const reviewOnly = submission.parts.some(
    (part) => part.status !== "PASS" || part.flags.length > 0,
  );
  const hasNoCut = audit.labels.some((label) =>
    label.startsWith("REVIEW ONLY - NO CUT"),
  );
  if (reviewOnly && !hasNoCut)
    throw new Error("REPO_DIRECT_READBACK_NO_CUT_LABEL_MISSING");
  if (!reviewOnly && hasNoCut)
    throw new Error("REPO_DIRECT_PASS_UNEXPECTED_NO_CUT_LABEL");

  return audit;
}

export function exportRepoDirectE2E(raw: unknown): {
  job: CadJob;
  submissionSha256: string;
  artifact: { fileName: string; sha256: string; url: string | null };
} {
  const { job, submission, submissionSha256 } =
    validateRepoDirectSubmission(raw);

  job.geometrySources = [];
  job.geometry = [];
  job.manufacturingQa = [];
  job.computedQa = undefined;
  job.sourceChecks = undefined;
  job.dxfOutput = undefined;
  job.dxfAudit = undefined;
  job.flags = [];
  if (job.state !== "GEOMETRY_READY")
    jobStore.transition(job.jobId, "GEOMETRY_READY");

  const outDir = join(dataRoot(), "outputs", job.jobId);
  mkdirSync(outDir, { recursive: true });
  const payload = { job_id: job.jobId, parts: submission.parts };
  const inputPath = join(outDir, "repo_direct_serializer_input.json");
  writeFileSync(inputPath, JSON.stringify(payload, null, 2));
  writeFileSync(
    join(outDir, "repo_direct_trace.json"),
    JSON.stringify(
      {
        schema: submission.schema,
        submissionSha256,
        sourceSha256: submission.sourceSha256,
        dxfSha256: submission.dxfSha256 ?? null,
        ruleSnapshotId: submission.ruleSnapshotId,
        gates: submission.gates,
      },
      null,
      2,
    ),
  );

  const result = runBridge(job, ["export", inputPath, outDir]);
  if (
    !result?.ok ||
    !result?.manifest?.filename ||
    !result?.dxf_path ||
    !result?.manifest_path
  )
    throw new Error("REPO_DIRECT_DXF_BRIDGE_INVALID_RESULT");
  const abs = resolve(result.dxf_path);
  if (!existsSync(abs)) throw new Error("REPO_DIRECT_DXF_FILE_MISSING");

  const codeLabels = expectedCodeLabels(submission);
  job.dxfOutput = {
    sha256: sha256(readFileSync(abs)),
    fileName: result.manifest.filename,
    relativePath: join("outputs", job.jobId, result.manifest.filename),
    absolutePath: abs,
    manifestPath: resolve(result.manifest_path),
    serializerContract: result.manifest.contract,
    codeOrder: codeLabels,
    writtenAt: new Date().toISOString(),
  };
  jobStore.transition(job.jobId, "DXF_WRITTEN");

  job.dxfAudit = auditSavedDxf(job, submission);
  job.flags = ["MCP_REPO_DIRECT_PARITY_NON_AUTHORITY"];
  jobStore.transition(job.jobId, "DXF_READBACK");
  jobStore.transition(job.jobId, "QA_COMPLETE");

  const file = artifact(job);
  return {
    job,
    submissionSha256,
    artifact: { fileName: file.fileName, sha256: file.sha256, url: file.url },
  };
}
