import test from "node:test";
import assert from "node:assert/strict";
import { createHash, randomUUID } from "node:crypto";
import { mkdirSync, mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { jobStore, publicJob, resolveRepoRoot, routeJob } from "../src/core.js";
import { auditWithBridge, createExportPayload, exportWithBridge } from "../src/dxf.js";

process.env.TRAINAICAD_MCP_DATA = mkdtempSync(join(tmpdir(), "trainaicad-mcp-v03-"));

const SHA = "a".repeat(64);
const source = { fileName: "drawing.pdf", sha256: SHA, sourceId: SHA };

function n(value: number, unit: "mm" | "deg" = "mm") {
  return { value, unit, origin: "PRINTED" as const };
}

function readyJob() {
  const job = jobStore.create(source, undefined, "AUTO");
  jobStore.submitEvidence(job.jobId, [{
    schema: "CAD_EVIDENCE_V1",
    jobId: job.jobId,
    code: "P1",
    source: { sourceId: SHA, page: 1 },
    material: { printed: "SS400", family: "SS", thickness: n(2) },
    views: [{ id: "A", type: "FLAT" }],
    contour: { topology: "PLATE", status: "PROVED", overallX: n(50), overallY: n(30) },
    features: [{ id: "H1", family: "HOLE", quantity: 1, diameter: n(6), status: "PROVED" }],
    bends: [],
    markings: [],
    handwriting: [],
    uncertainties: []
  }]);
  routeJob(job.jobId);
  return jobStore.buildGeometry(job.jobId, [{
    schema: "GEOMETRY_SOURCE_V1",
    jobId: job.jobId,
    code: "P1",
    sourceSha256: SHA,
    origin: "PDF_SOURCE",
    buildKind: "FLAT_SINGLE_FACE",
    faces: [{
      faceId: "F1",
      sourceView: "A",
      contour: [{x:0,y:0},{x:50,y:0},{x:50,y:30},{x:0,y:30}]
    }],
    faceOrder: ["F1"],
    bends: [],
    features: [{
      featureId: "H1",
      family: "HOLE",
      hostFace: "F1",
      geometries: [{ kind: "CIRCLE", center: {x:25,y:15}, diameter: 6 }]
    }],
    proofs: {}
  }]);
}

function qa(jobId: string) {
  return [{
    schema: "MANUFACTURING_QA_V1",
    jobId,
    code: "P1",
    checks: {
      contour_topology: "PASS",
      datum: "PASS",
      feature_count: "PASS",
      unfold: "N/A",
      containment: "PASS",
      bend_domain: "N/A",
      material_rules: "PASS",
      slot_semantics: "N/A"
    },
    foldBack: "N/A",
    approvedForExport: true
  }];
}

test("serializer payload is production-shaped and preserves hole geometry", () => {
  const job = readyJob();
  assert.equal(job.state, "GEOMETRY_READY");
  const payload = createExportPayload(job, qa(job.jobId));
  assert.equal(payload.parts.length, 1);
  assert.equal(payload.parts[0]?.status, "PASS");
  assert.equal(payload.parts[0]?.entities[0]?.role, "outer");
  assert.equal(payload.parts[0]?.entities[1]?.type, "CIRCLE");
  assert.equal(payload.parts[0]?.entities[1]?.radius, 3);
});

test("critical QA cannot be N/A", () => {
  const job = readyJob();
  const bad = qa(job.jobId);
  (bad[0]!.checks as any).datum = "N/A";
  assert.throws(() => createExportPayload(job, bad), /DXF_CRITICAL_QA_NOT_PASS/);
});

test("bent production export requires full fold-back PASS", () => {
  const job = readyJob();
  job.geometry[0]!.bendZones = [{
    bendId: "B1", x1: 10, x2: 12, yMin: 0, yMax: 30,
    sign: "POSITIVE", angleDeg: 90, nobi: 2
  }];
  const bad = qa(job.jobId);
  assert.throws(() => createExportPayload(job, bad), /DXF_BENT_QA_NOT_PASS/);
});

test("saved composite DXF is physically read back against locked canonical serializer input", () => {
  const job = readyJob();
  const exported = exportWithBridge(job, qa(job.jobId), resolveRepoRoot());
  const audit = auditWithBridge(exported.output, resolveRepoRoot());
  assert.equal(audit.physicalGeometryMatch, true);
  assert.equal(audit.codeOrderMatch, true);
  assert.equal(audit.comparedEntityCount, audit.entityCount);
});

test("caller-forged QA cannot export an unverified source job", () => {
  const job = readyJob();
  assert.throws(() => jobStore.exportDxf(job.jobId, qa(job.jobId)), /PRODUCTION_SOURCE_UNVERIFIED/);
});

test("read-back rejects a DXF changed after export", () => {
  const file = join(process.env.TRAINAICAD_MCP_DATA!, "tampered.dxf");
  writeFileSync(file, "original DXF bytes");
  const record = {
    fileName: "tampered.dxf", relativePath: "tampered.dxf", absolutePath: file,
    manifestPath: "", serializerContract: "test", codeOrder: ["P1"],
    fileSha256: "0".repeat(64), serializerInputSha256: "0".repeat(64), manifestSha256: "0".repeat(64), writtenAt: new Date().toISOString()
  };
  assert.throws(() => auditWithBridge(record, process.cwd()), /DXF_READBACK_FILE_CHANGED_AFTER_EXPORT/);
});

test("artifact response serves exact audited DXF bytes without leaking local paths", () => {
  const job = jobStore.create(source, undefined, "AUTO");
  jobStore.getRuleBundle(job.jobId);
  const outputDir = join(process.env.TRAINAICAD_MCP_DATA!, "outputs", job.jobId);
  mkdirSync(outputDir, { recursive: true });
  const file = join(outputDir, "TEST_ALL.dxf");
  const bytes = Buffer.from("0\nSECTION\n2\nENTITIES\n0\nENDSEC\n0\nEOF\n", "ascii");
  writeFileSync(file, bytes);
  const digest = createHash("sha256").update(bytes).digest("hex");
  const serializerInputPath = join(outputDir, "serializer_input.json");
  const manifestPath = join(outputDir, "manifest.json");
  writeFileSync(serializerInputPath, "{}\n");
  writeFileSync(manifestPath, "{}\n");
  job.state = "PRODUCTION_PASS";
  job.sourceBindings.DRAWING = {
    role: "DRAWING", fileName: "drawing.pdf", sha256: SHA, mimeType: "application/pdf", storedPath: "C:\\private\\drawing.pdf"
  };
  job.dxfOutput = {
    fileName: "TEST_ALL.dxf", relativePath: "outputs/TEST_ALL.dxf", absolutePath: file,
    manifestPath, serializerContract: "test", codeOrder: ["P1"],
    fileSha256: digest,
    serializerInputSha256: createHash("sha256").update(readFileSync(serializerInputPath)).digest("hex"),
    manifestSha256: createHash("sha256").update(readFileSync(manifestPath)).digest("hex"),
    writtenAt: new Date().toISOString()
  };
  job.dxfAudit = { ok: true } as any;

  const artifact = jobStore.readDxfArtifact(job.jobId);
  assert.equal(artifact.uri, `trainaicad://jobs/${job.jobId}/artifacts/${digest}`);
  assert.deepEqual(artifact.bytes, bytes);
  const response = publicJob(job) as any;
  assert.equal(response.dxfOutput.artifactUri, artifact.uri);
  assert.equal("absolutePath" in response.dxfOutput, false);
  assert.equal("manifestPath" in response.dxfOutput, false);
  assert.equal("storedPath" in (Object.values(response.sourceBindings)[0] as any), false);
});

test("artifact retrieval rejects a post-audit byte change", () => {
  const job = jobStore.create(source, undefined, "AUTO");
  jobStore.getRuleBundle(job.jobId);
  const outputDir = join(process.env.TRAINAICAD_MCP_DATA!, "outputs", job.jobId);
  mkdirSync(outputDir, { recursive: true });
  const file = join(outputDir, "TEST_ALL.dxf");
  writeFileSync(file, "original");
  job.state = "PRODUCTION_PASS";
  job.dxfOutput = {
    fileName: "TEST_ALL.dxf", relativePath: "outputs/TEST_ALL.dxf", absolutePath: file,
    manifestPath: "", serializerContract: "test", codeOrder: ["P1"],
    fileSha256: "0".repeat(64), serializerInputSha256: "0".repeat(64), manifestSha256: "0".repeat(64), writtenAt: new Date().toISOString()
  };
  job.dxfAudit = { ok: true } as any;
  assert.throws(() => jobStore.readDxfArtifact(job.jobId), /DXF_ARTIFACT_HASH_MISMATCH/);
});

test("legacy production PASS without immutable rule and physical readback pins is demoted", () => {
  const seed = jobStore.create(source, undefined, "AUTO");
  const jobId = `cad_${randomUUID().replaceAll("-", "").slice(0, 16)}`;
  const legacy = {
    ...seed,
    jobId,
    state: "PRODUCTION_PASS",
    sourceVerified: true,
    production: { ...seed.production, ruleFiles: [], ruleSnapshotSha256: undefined },
    dxfOutput: { fileName: "old_ALL.dxf", fileSha256: "a".repeat(64), absolutePath: "C:\\old_ALL.dxf" },
    dxfAudit: { ok: true },
    manufacturingQa: [{ schema: "MANUFACTURING_QA_V1", jobId, code: "P1", checks: {}, foldBack: "PASS", approvedForExport: true }],
    flags: []
  };
  const jobsDir = join(process.env.TRAINAICAD_MCP_DATA!, "jobs");
  mkdirSync(jobsDir, { recursive: true });
  writeFileSync(join(jobsDir, `${jobId}.json`), JSON.stringify(legacy));
  const migrated = jobStore.get(jobId);
  assert.equal(migrated.state, "REVIEW_REQUIRED");
  assert.equal(migrated.sourceVerified, false);
  assert.equal(migrated.dxfOutput, undefined);
  assert.equal(migrated.dxfAudit, undefined);
  assert.ok(migrated.flags.includes("LEGACY_READBACK_BASIS_UNVERIFIED"));
  assert.equal(migrated.manufacturingQa[0]?.approvedForExport, false);
});
