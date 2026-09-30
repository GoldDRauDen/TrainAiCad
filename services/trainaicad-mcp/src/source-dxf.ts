import { createHash } from "node:crypto";
import { existsSync, mkdirSync, readFileSync, realpathSync } from "node:fs";
import { join } from "node:path";
import { spawnSync } from "node:child_process";
import { jobStore, resolveRepoRoot } from "./core.js";
import { atomicWriteBytes, dataRoot, verifiedSource } from "./ingest.js";
import type { SourceGeometryHarvestV1 } from "./model.js";

const LEDGER_MAX_BYTES = 64 * 1024 * 1024;

function pythonExe(): string {
  return process.env.TRAINAICAD_PYTHON ?? (process.platform === "win32" ? "python" : "python3");
}

export type HarvestedSourceGeometry = {
  uri: string;
  fileName: string;
  ledgerSha256: string;
  ledgerBytes: Buffer;
  summary: SourceGeometryHarvestV1;
};

export function harvestBoundDataDxf(jobId: string): HarvestedSourceGeometry {
  const job = jobStore.get(jobId);
  if (job.mode !== "PDF_DATA_RAW") throw new Error(`DATA_DXF_HARVEST_NOT_ALLOWED_IN_${job.mode}`);
  const binding = job.sourceBindings.DATA_DXF;
  if (!binding) throw new Error("DATA_DXF_HARVEST_SOURCE_MISSING");
  const source = verifiedSource("DATA_DXF", binding.fileName, binding.sha256);
  if (realpathSync(source.storedPath) !== realpathSync(binding.storedPath)) {
    throw new Error("DATA_DXF_HARVEST_BOUND_PATH_MISMATCH");
  }

  const repoRoot = resolveRepoRoot();
  const bridge = join(repoRoot, "services", "trainaicad-mcp", "bridge", "dxf_bridge.py");
  const proc = spawnSync(pythonExe(), [bridge, "harvest", source.storedPath], {
    cwd: repoRoot,
    encoding: "utf8",
    maxBuffer: LEDGER_MAX_BYTES
  });
  if (proc.error) throw proc.error;
  if (proc.status !== 0) throw new Error(`DATA_DXF_HARVEST_FAILED:${(proc.stderr || proc.stdout || "").trim()}`);
  const line = (proc.stdout || "").trim().split(/\r?\n/).filter(Boolean).at(-1);
  if (!line) throw new Error("DATA_DXF_HARVEST_EMPTY_RESULT");
  const ledgerBytes = Buffer.from(line, "utf8");
  if (ledgerBytes.length > LEDGER_MAX_BYTES) throw new Error("SOURCE_GEOMETRY_LEDGER_TOO_LARGE");
  const ledger = JSON.parse(line) as Record<string, any>;
  if (ledger.schema !== "TRAINSOURCE_GEOMETRY_LEDGER_V1" || ledger.sourceSha256 !== source.sha256 ||
      !Array.isArray(ledger.entities) || !Array.isArray(ledger.flags)) {
    throw new Error("DATA_DXF_HARVEST_RESULT_INVALID");
  }
  const ledgerSha256 = createHash("sha256").update(ledgerBytes).digest("hex");
  const summary: SourceGeometryHarvestV1 = {
    schema: "TRAINSOURCE_GEOMETRY_LEDGER_V1",
    sourceSha256: source.sha256,
    ledgerSha256,
    entityCount: ledger.entities.length,
    unsupportedCount: ledger.unsupportedEntities?.length ?? 0,
    flags: ledger.flags,
    scaleStatus: "UNPROVED",
    status: "REVIEW_REQUIRED",
    updatedAt: new Date().toISOString()
  };
  const ledgerDir = join(dataRoot(), "jobs", jobId, "source-geometry", source.sha256);
  const ledgerPath = join(ledgerDir, `${ledgerSha256}.json`);
  mkdirSync(ledgerDir, { recursive: true });
  if (existsSync(ledgerPath)) {
    const previous = readFileSync(ledgerPath);
    const previousSha = createHash("sha256").update(previous).digest("hex");
    if (previousSha !== ledgerSha256) throw new Error("SOURCE_GEOMETRY_LEDGER_CONTENT_ADDRESS_MISMATCH");
  } else {
    atomicWriteBytes(ledgerPath, ledgerBytes);
  }
  jobStore.recordSourceGeometryHarvest(jobId, summary);
  return {
    uri: `trainaicad://jobs/${jobId}/source-geometry/${ledgerSha256}`,
    fileName: source.fileName,
    ledgerSha256,
    ledgerBytes,
    summary
  };
}

export function readBoundDataDxfLedger(jobId: string, ledgerSha256: string): HarvestedSourceGeometry {
  if (!/^[a-f0-9]{64}$/.test(ledgerSha256)) throw new Error("INVALID_LEDGER_SHA256");
  const job = jobStore.get(jobId);
  if (job.mode !== "PDF_DATA_RAW") throw new Error(`DATA_DXF_LEDGER_NOT_ALLOWED_IN_${job.mode}`);
  const binding = job.sourceBindings.DATA_DXF;
  const summary = job.sourceGeometryHarvest;
  if (!binding || !summary || summary.sourceSha256 !== binding.sha256 || summary.ledgerSha256 !== ledgerSha256) {
    throw new Error("SOURCE_GEOMETRY_LEDGER_NOT_CURRENT");
  }
  verifiedSource("DATA_DXF", binding.fileName, binding.sha256);
  const path = join(dataRoot(), "jobs", jobId, "source-geometry", binding.sha256, `${ledgerSha256}.json`);
  if (!existsSync(path)) throw new Error("SOURCE_GEOMETRY_LEDGER_MISSING");
  const ledgerBytes = readFileSync(path);
  const actualSha = createHash("sha256").update(ledgerBytes).digest("hex");
  if (actualSha !== ledgerSha256) throw new Error("SOURCE_GEOMETRY_LEDGER_HASH_MISMATCH");
  const ledger = JSON.parse(ledgerBytes.toString("utf8")) as Record<string, any>;
  if (ledger.schema !== summary.schema || ledger.sourceSha256 !== binding.sha256) {
    throw new Error("SOURCE_GEOMETRY_LEDGER_BINDING_MISMATCH");
  }
  return {
    uri: `trainaicad://jobs/${jobId}/source-geometry/${ledgerSha256}`,
    fileName: binding.fileName,
    ledgerSha256,
    ledgerBytes,
    summary
  };
}
