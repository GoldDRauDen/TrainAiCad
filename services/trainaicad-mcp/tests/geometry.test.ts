import test from "node:test";
import assert from "node:assert/strict";
import { existsSync, mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { dataRoot } from "../src/ingest.js";
import { jobStore, routeJob } from "../src/core.js";

process.env.TRAINAICAD_MCP_DATA = mkdtempSync(join(tmpdir(), "trainaicad-mcp-v1-"));

const PDF_SHA = "d".repeat(64);
const DATA_SHA = "e".repeat(64);
const REF_SHA = "f".repeat(64);

const drawing = {
  fileName: "drawing.pdf",
  sha256: PDF_SHA,
  sourceId: "drawing-source"
};

function number(value: number, unit: "mm" | "deg" = "mm", origin = "PRINTED") {
  return { value, unit, origin };
}

function baseProofs(slot = false) {
  const p = { evidenceRefs: ["page:1"] };
  return {
    topologyLocked: p,
    dimensionWitnessLocked: p,
    featureOwnershipLocked: p,
    constraintsClosed: p,
    materialRules: p,
    ...(slot ? { slotSemantics: p } : {})
  };
}

function bentProofs(numericChecks: unknown[] = []) {
  const p = { evidenceRefs: ["page:1"] };
  return {
    ...baseProofs(),
    faceOrderLocked: p,
    bendSignLocked: p,
    bendDomainLocked: p,
    foldBackMatch: {
      evidenceRefs: ["page:1", "formed-view:A"],
      topologyMatch: true,
      adjacencyMatch: true,
      bendSignMatch: true,
      featureOwnershipMatch: true,
      bendDomainMatch: true,
      numericChecks
    }
  };
}

function openRoutedFlat() {
  const job = jobStore.create(drawing, undefined, "AUTO");
  jobStore.submitEvidence(job.jobId, [{
    schema: "CAD_EVIDENCE_V1",
    jobId: job.jobId,
    code: "FLAT01",
    source: { sourceId: "drawing-source", page: 1 },
    material: { printed: "SS400", family: "SS", thickness: number(3) },
    views: [{ id: "A", type: "FLAT" }],
    contour: {
      topology: "PLATE",
      status: "PROVED",
      overallX: number(80),
      overallY: number(40)
    },
    features: [
      { id: "H1", family: "HOLE", quantity: 2, diameter: number(6), status: "PROVED" },
      { id: "S1", family: "SLOT", quantity: 1, width: number(10), status: "PROVED" }
    ],
    bends: [],
    markings: [{ id: "K1", family: "KEGAKI", quantity: 1, status: "PROVED" }],
    handwriting: [],
    uncertainties: []
  }]);
  return routeJob(job.jobId);
}

function flatGeometry(jobId: string, sha = PDF_SHA, origin: "PDF_SOURCE" | "DATA_DXF" = "PDF_SOURCE") {
  return {
    schema: "GEOMETRY_SOURCE_V1",
    jobId,
    code: "FLAT01",
    sourceSha256: sha,
    origin,
    buildKind: "FLAT_SINGLE_FACE",
    faces: [{
      faceId: "F1",
      sourceView: "A",
      contour: [
        { x: 0, y: 0, bulge: 0 },
        { x: 80, y: 0, bulge: 0 },
        { x: 80, y: 40, bulge: 0 },
        { x: 0, y: 40, bulge: 0 }
      ]
    }],
    faceOrder: ["F1"],
    bends: [],
    features: [
      {
        featureId: "H1",
        family: "HOLE",
        hostFace: "F1",
        geometries: [
          { kind: "CIRCLE", center: { x: 15, y: 20 }, diameter: 6 },
          { kind: "CIRCLE", center: { x: 65, y: 20 }, diameter: 6 }
        ]
      },
      {
        featureId: "S1",
        family: "SLOT",
        hostFace: "F1",
        geometries: [{ kind: "SLOT", center: { x: 40, y: 12 }, overallLength: 24, width: 10, angleDeg: 0 }]
      },
      {
        featureId: "K1",
        family: "KEGAKI",
        hostFace: "F1",
        geometries: [{ kind: "LINE", start: { x: 10, y: 30 }, end: { x: 70, y: 30 } }]
      }
    ],
    proofs: { ...baseProofs(true) }
  };
}

function openRoutedLinear(dxf = false) {
  const data = dxf ? { fileName: "data.dxf", sha256: DATA_SHA } : undefined;
  const job = jobStore.create(drawing, data, "AUTO");
  jobStore.submitEvidence(job.jobId, [{
    schema: "CAD_EVIDENCE_V1",
    jobId: job.jobId,
    code: "L01",
    source: { sourceId: "drawing-source", page: 1 },
    material: { printed: "SS400", family: "SS", thickness: number(3) },
    views: [{ id: "FORMED", type: "FORMED" }],
    contour: { topology: "L_PROFILE", status: "PROVED" },
    faceCount: 2,
    features: [{ id: "H1", family: "HOLE", quantity: 1, diameter: number(6), status: "PROVED" }],
    bends: [{
      id: "B1",
      angle: number(90, "deg"),
      axis: "X",
      sign: "POSITIVE",
      nobi: { value: 4.4, unit: "mm", origin: "HANDWRITTEN" },
      status: "PROVED"
    }],
    markings: [],
    handwriting: [],
    uncertainties: []
  }]);
  return routeJob(job.jobId);
}

function linearGeometry(
  jobId: string,
  sha = PDF_SHA,
  origin: "PDF_SOURCE" | "DATA_DXF" = "PDF_SOURCE",
  residual = 0.001
) {
  return {
    schema: "GEOMETRY_SOURCE_V1",
    jobId,
    code: "L01",
    sourceSha256: sha,
    origin,
    buildKind: "LINEAR_CHAIN",
    faces: [
      {
        faceId: "F1",
        sourceView: "FORMED",
        contour: [{ x: 0, y: 0 }, { x: 150, y: 0 }, { x: 150, y: 25 }, { x: 0, y: 25 }],
        outsideLength: number(150),
        transverseWidth: number(25)
      },
      {
        faceId: "F2",
        sourceView: "FORMED",
        contour: [{ x: 0, y: 0 }, { x: 23.2, y: 0 }, { x: 23.2, y: 25 }, { x: 0, y: 25 }],
        outsideLength: number(23.2),
        transverseWidth: number(25)
      }
    ],
    faceOrder: ["F1", "F2"],
    bends: [{
      bendId: "B1",
      faceA: "F1",
      faceB: "F2",
      axis: "X",
      sign: "POSITIVE",
      angleDeg: number(90, "deg"),
      nobi: { value: 4.4, unit: "mm", origin: "HANDWRITTEN" }
    }],
    features: [{
      featureId: "H1",
      family: "HOLE",
      hostFace: "F2",
      geometries: [{ kind: "CIRCLE", center: { x: 10, y: 12.5 }, diameter: 6 }]
    }],
    proofs: {
      ...bentProofs([{
        id: "flat-derived",
        expected: 168.8,
        actual: 168.8 + residual,
        origin: "DERIVED"
      }])
    }
  };
}

function openRoutedFaceGraph() {
  const job = jobStore.create(drawing, undefined, "AUTO");
  jobStore.submitEvidence(job.jobId, [{
    schema: "CAD_EVIDENCE_V1",
    jobId: job.jobId,
    code: "MIX01",
    source: { sourceId: "drawing-source", page: 1 },
    material: { printed: "SS400", family: "SS", thickness: number(2) },
    views: [{ id: "FORMED", type: "FORMED" }],
    contour: { topology: "MULTI_FACE", status: "PROVED" },
    faceCount: 3,
    features: [{ id: "H1", family: "HOLE", quantity: 1, diameter: number(8), status: "PROVED" }],
    bends: [
      { id: "B1", angle: number(90, "deg"), axis: "X", sign: "POSITIVE", nobi: number(2), status: "PROVED" },
      { id: "B2", angle: number(90, "deg"), axis: "Y", sign: "NEGATIVE", nobi: number(2), status: "PROVED" }
    ],
    markings: [],
    handwriting: [],
    uncertainties: []
  }]);
  return routeJob(job.jobId);
}

function faceGraphGeometry(jobId: string) {
  const t1 = { m00: 1, m01: 0, m10: 0, m11: 1, tx: 0, ty: 0 };
  const t2 = { m00: 1, m01: 0, m10: 0, m11: 1, tx: 100, ty: 0 };
  const t3 = { m00: 1, m01: 0, m10: 0, m11: 1, tx: 90, ty: 40 };
  return {
    schema: "GEOMETRY_SOURCE_V1",
    jobId,
    code: "MIX01",
    sourceSha256: PDF_SHA,
    origin: "PDF_SOURCE",
    buildKind: "FACE_GRAPH_FLAT",
    faces: [
      {
        faceId: "F1", sourceView: "FORMED",
        contour: [{ x: 0, y: 0 }, { x: 100, y: 0 }, { x: 100, y: 40 }, { x: 0, y: 40 }],
        flatTransform: t1, transformProofRefs: ["page:1:F1"]
      },
      {
        faceId: "F2", sourceView: "FORMED",
        contour: [{ x: 0, y: 0 }, { x: 20, y: 0 }, { x: 20, y: 40 }, { x: 0, y: 40 }],
        flatTransform: t2, transformProofRefs: ["page:1:F2"]
      },
      {
        faceId: "F3", sourceView: "FORMED",
        contour: [{ x: 0, y: 0 }, { x: 30, y: 0 }, { x: 30, y: 20 }, { x: 0, y: 20 }],
        flatTransform: t3, transformProofRefs: ["page:1:F3"]
      }
    ],
    faceOrder: ["F1", "F2", "F3"],
    bends: [
      {
        bendId: "B1", faceA: "F1", faceB: "F2", axis: "X", sign: "POSITIVE",
        angleDeg: number(90, "deg"), nobi: number(2),
        flatLines: {
          line1: { start: { x: 98, y: 0 }, end: { x: 98, y: 40 } },
          line2: { start: { x: 100, y: 0 }, end: { x: 100, y: 40 } },
          proofRefs: ["page:1:B1"]
        }
      },
      {
        bendId: "B2", faceA: "F2", faceB: "F3", axis: "Y", sign: "NEGATIVE",
        angleDeg: number(90, "deg"), nobi: number(2),
        flatLines: {
          line1: { start: { x: 90, y: 38 }, end: { x: 120, y: 38 } },
          line2: { start: { x: 90, y: 40 }, end: { x: 120, y: 40 } },
          proofRefs: ["page:1:B2"]
        }
      }
    ],
    features: [{
      featureId: "H1",
      family: "HOLE",
      hostFace: "F3",
      geometries: [{ kind: "CIRCLE", center: { x: 15, y: 10 }, diameter: 8 }]
    }],
    flatOuterContour: [
      { x: 0, y: 0 },
      { x: 120, y: 0 },
      { x: 120, y: 60 },
      { x: 90, y: 60 },
      { x: 90, y: 40 },
      { x: 0, y: 40 }
    ],
    flatOuterProofRefs: ["page:1:flat-outer"],
    proofs: {
      ...bentProofs([
        { id: "formed-X", expected: 120, actual: 120, origin: "PRINTED" },
        { id: "derived-check", expected: 60, actual: 60.009, origin: "DERIVED" }
      ])
    }
  };
}

test("full flat pipeline reaches PRODUCTION_PASS only after saved-DXF read-back", () => {
  const routed = openRoutedFlat();
  const built = jobStore.buildGeometry(routed.jobId, [flatGeometry(routed.jobId)]);
  assert.equal(built.state, "GEOMETRY_READY");
  assert.equal(built.geometry[0]?.features.length, 4);

  const written = jobStore.exportDxf(routed.jobId);
  assert.equal(written.state, "DXF_WRITTEN");
  assert.ok(written.output);
  assert.ok(existsSync(join(dataRoot(), written.output!.relativePath)));
  assert.equal(written.output?.readback, undefined);

  const passed = jobStore.auditDxf(routed.jobId);
  assert.equal(passed.state, "PRODUCTION_PASS");
  assert.equal(passed.output?.readback?.canonicalMatch, true);
  assert.equal(passed.output?.readback?.codeOrderMatch, true);
  assert.equal(passed.output?.families?.CUT.status, "PASS");
  assert.equal(passed.output?.families?.HOLE_SLOT.status, "PASS");
  assert.equal(passed.output?.families?.KEGAKI.status, "PASS");
  assert.equal(passed.output?.families?.BEND.status, "N/A");
});

test("linear chain computes 168.8 and transforms a hosted feature with G8 PASS", () => {
  const routed = openRoutedLinear(false);
  const built = jobStore.buildGeometry(routed.jobId, [linearGeometry(routed.jobId)]);
  assert.equal(built.state, "GEOMETRY_READY");
  const g = built.geometry[0]!;
  assert.equal(g.qa.foldBack, "PASS");
  assert.ok(g.qa.numericResidualMaxMm < 0.01);
  assert.equal(g.bendZones.length, 1);
  assert.equal(g.bendZones[0]?.line1.start.x, 145.6);
  assert.equal(g.bendZones[0]?.line2.start.x, 150);
  assert.equal(g.features[0]?.hostFace, "F2");
  assert.equal(g.features[0]?.geometry.kind, "CIRCLE");
  if (g.features[0]?.geometry.kind === "CIRCLE") {
    assert.equal(g.features[0].geometry.center.x, 155.6);
  }
});

test("DERIVED fold-back residual must be strictly below 0.01 mm", () => {
  const pass = openRoutedLinear(false);
  assert.equal(jobStore.buildGeometry(pass.jobId, [linearGeometry(pass.jobId, PDF_SHA, "PDF_SOURCE", 0.009)]).state, "GEOMETRY_READY");

  const fail = openRoutedLinear(false);
  const failed = jobStore.buildGeometry(fail.jobId, [linearGeometry(fail.jobId, PDF_SHA, "PDF_SOURCE", 0.01)]);
  assert.equal(failed.state, "REVIEW_REQUIRED");
  assert.ok(failed.flags.some((f) => f.includes("FOLD_BACK_DERIVED_RESIDUAL")));
});

test("PDF_DATA_RAW geometry authority is the bound DATA DXF SHA", () => {
  const routed = openRoutedLinear(true);
  const wrong = jobStore.buildGeometry(routed.jobId, [linearGeometry(routed.jobId, PDF_SHA, "PDF_SOURCE")]);
  assert.equal(wrong.state, "REVIEW_REQUIRED");
  assert.ok(wrong.flags.some((f) => f.includes("GEOMETRY_AUTHORITY_ORIGIN_MISMATCH")));

  const fixed = jobStore.buildGeometry(routed.jobId, [linearGeometry(routed.jobId, DATA_SHA, "DATA_DXF")]);
  assert.equal(fixed.state, "GEOMETRY_READY");
});

test("TRAIN_REFERENCE never authorizes reference DXF construction geometry", () => {
  const job = jobStore.create(drawing, { fileName: "ref.dxf", sha256: REF_SHA }, "AUTO", true);
  jobStore.submitEvidence(job.jobId, [{
    schema: "CAD_EVIDENCE_V1",
    jobId: job.jobId,
    code: "FLAT01",
    source: { sourceId: "drawing-source", page: 1 },
    material: { printed: "SS", thickness: number(1) },
    views: [{ id: "A", type: "FLAT" }],
    contour: { topology: "PLATE", status: "PROVED" },
    features: [
      { id: "H1", family: "HOLE", quantity: 2, status: "PROVED" },
      { id: "S1", family: "SLOT", quantity: 1, status: "PROVED" }
    ],
    bends: [],
    markings: [{ id: "K1", family: "KEGAKI", quantity: 1, status: "PROVED" }],
    handwriting: [],
    uncertainties: []
  }]);
  routeJob(job.jobId);
  const failed = jobStore.buildGeometry(job.jobId, [flatGeometry(job.jobId, REF_SHA, "DATA_DXF")]);
  assert.equal(failed.state, "REVIEW_REQUIRED");
  assert.ok(failed.flags.some((f) => f.includes("GEOMETRY_AUTHORITY_SHA_MISMATCH")));
});

test("FACE_GRAPH_FLAT supports mixed-axis transforms and full G1-G8 gate", () => {
  const routed = openRoutedFaceGraph();
  const built = jobStore.buildGeometry(routed.jobId, [faceGraphGeometry(routed.jobId)]);
  assert.equal(built.state, "GEOMETRY_READY");
  const g = built.geometry[0]!;
  assert.equal(g.buildKind, "FACE_GRAPH_FLAT");
  assert.equal(g.qa.faceGraphG1toG7, "PASS");
  assert.equal(g.qa.foldBack, "PASS");
  assert.equal(g.bendZones.length, 2);
  assert.equal(g.features[0]?.geometry.kind, "CIRCLE");
  if (g.features[0]?.geometry.kind === "CIRCLE") {
    assert.deepEqual(g.features[0].geometry.center, { x: 105, y: 50 });
  }
});

test("RIB is an independent part role and is audited separately", () => {
  const job = jobStore.create(drawing, undefined, "AUTO");
  jobStore.submitEvidence(job.jobId, [{
    schema: "CAD_EVIDENCE_V1",
    jobId: job.jobId,
    code: "RIB01",
    partRole: "RIB",
    source: { sourceId: "drawing-source", page: 1 },
    material: { printed: "SS", thickness: number(2) },
    views: [{ id: "A", type: "FLAT" }],
    contour: { topology: "PLATE", status: "PROVED" },
    features: [],
    bends: [],
    markings: [],
    handwriting: [],
    uncertainties: []
  }]);
  routeJob(job.jobId);
  const source = {
    schema: "GEOMETRY_SOURCE_V1",
    jobId: job.jobId,
    code: "RIB01",
    sourceSha256: PDF_SHA,
    origin: "PDF_SOURCE",
    buildKind: "FLAT_SINGLE_FACE",
    faces: [{
      faceId: "F1", sourceView: "A",
      contour: [{ x: 0, y: 0 }, { x: 30, y: 0 }, { x: 30, y: 8 }, { x: 0, y: 8 }]
    }],
    faceOrder: ["F1"],
    bends: [],
    features: [],
    proofs: baseProofs()
  };
  assert.equal(jobStore.buildGeometry(job.jobId, [source]).state, "GEOMETRY_READY");
  jobStore.exportDxf(job.jobId);
  const passed = jobStore.auditDxf(job.jobId);
  assert.equal(passed.output?.families?.RIB.status, "PASS");
});

test("DIRECT_EXISTING_DXF_AUDIT does not enter new-geometry construction path", () => {
  const job = jobStore.create(
    { fileName: "ai.dxf", sha256: PDF_SHA, sourceId: "drawing-source" },
    { fileName: "approved.dxf", sha256: REF_SHA },
    "DIRECT_EXISTING_DXF_AUDIT"
  );
  assert.throws(
    () => jobStore.buildGeometry(job.jobId, []),
    /GEOMETRY_BUILD_NOT_APPLICABLE_TO_DIRECT_AUDIT|GEOMETRY_BUILD_NOT_ALLOWED_IN_STATE/
  );
});
