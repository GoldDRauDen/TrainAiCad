import test from "node:test";
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { mkdtempSync, readFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { storeSource } from "../src/ingest.js";
import { jobStore } from "../src/core.js";

process.env.TRAINAICAD_MCP_DATA = mkdtempSync(join(tmpdir(), "trainaicad-direct-audit-"));

function pythonBin(): string {
  return process.env.TRAINAICAD_PYTHON ?? (process.platform === "win32" ? "python" : "python3");
}

function fixtures() {
  const dir = mkdtempSync(join(tmpdir(), "trainaicad-direct-fixture-"));
  const ai = join(dir, "ai.dxf");
  const ref = join(dir, "ref.dxf");
  const script = [
    "import ezdxf,sys",
    "ai,ref=sys.argv[1],sys.argv[2]",
    "d=ezdxf.new('R2010'); d.header['$INSUNITS']=4; m=d.modelspace()",
    "m.add_lwpolyline([(0,0,0),(10,0,1)],format='xyb',close=True)",
    "d.saveas(ai)",
    "r=ezdxf.new('R2010'); r.header['$INSUNITS']=1; q=r.modelspace()",
    "q.add_line((100,200),(110,200))",
    "q.add_arc((105,200),5,0,180)",
    "r.saveas(ref)"
  ].join("; ");
  execFileSync(pythonBin(), ["-c", script, ai, ref]);
  return { ai, ref };
}

function makeJob() {
  const fixture = fixtures();
  const ai = storeSource({ fileName: "ai.dxf", bytes: readFileSync(fixture.ai) }, "AI_DXF");
  const ref = storeSource({ fileName: "approved.dxf", bytes: readFileSync(fixture.ref) }, "REFERENCE_DXF");
  const job = jobStore.create(
    { fileName: ai.fileName, sha256: ai.sha256, sourceId: ai.sha256 },
    { fileName: ref.fileName, sha256: ref.sha256 },
    "DIRECT_EXISTING_DXF_AUDIT"
  );
  return job;
}

function config(referenceMmPerUnit = 1) {
  return {
    aiMmPerUnit: 1,
    referenceMmPerUnit,
    aiUnitProofRefs: ["source/user:AI actual mm"],
    referenceUnitProofRefs: ["source/user:reference actual mm despite header"],
    curveToleranceMm: 0.001,
    toleranceProofRefs: ["exact physical-curve comparison contract"],
    parts: [{
      code: "D01",
      mappingProofRefs: ["user/source maps both whole drawings to D01"],
      aiTransform: {},
      referenceTransform: {}
    }]
  };
}

test("direct audit treats bulged polyline and exact LINE+ARC as physical MATCH after layout translation", () => {
  const job = makeJob();
  const audited = jobStore.auditExistingDxf(job.jobId, config());
  assert.equal(audited.state, "AUDIT_COMPLETE");
  assert.equal(audited.directAudit?.parts[0]?.status, "MATCH");
  assert.ok(Math.abs(audited.directAudit?.parts[0]?.translationRemovedMm?.[0] ?? 0) > 90);
  assert.equal(audited.directAudit?.referenceMmPerUnit, 1);
});

test("direct audit does not trust DXF INSUNITS metadata and obeys explicit physical scale", () => {
  const job = makeJob();
  const audited = jobStore.auditExistingDxf(job.jobId, config(1.1));
  assert.equal(audited.state, "AUDIT_COMPLETE");
  assert.equal(audited.directAudit?.parts[0]?.status, "DIFF");
});

test("rotation or mirror cannot be introduced without proof refs", () => {
  const job = makeJob();
  const bad = config();
  bad.parts[0]!.aiTransform = { rotationDeg: 90 };
  assert.throws(() => jobStore.auditExistingDxf(job.jobId, bad), /rotation\/mirror requires proofRefs/);
});
