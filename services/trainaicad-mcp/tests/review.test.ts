import test from "node:test";
import assert from "node:assert/strict";
import { existsSync, mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { jobStore, routeJob } from "../src/core.js";
import { dataRoot } from "../src/ingest.js";

process.env.TRAINAICAD_MCP_DATA = mkdtempSync(join(tmpdir(), "trainaicad-review-"));

function n(value: number) {
  return { value, unit: "mm", origin: "PRINTED" };
}

function reviewJob() {
  const source = { fileName: "drawing.pdf", sha256: "9".repeat(64), sourceId: "source-review" };
  const job = jobStore.create(source, undefined, "AUTO");
  jobStore.submitEvidence(job.jobId, [{
    schema: "CAD_EVIDENCE_V1",
    jobId: job.jobId,
    code: "RV01",
    source: { sourceId: "source-review", page: 1 },
    material: { printed: "SS400", family: "SS", thickness: n(2) },
    views: [{ id: "FRONT", type: "FRONT" }],
    contour: { topology: "UNKNOWN", status: "UNCERTAIN" },
    features: [],
    bends: [],
    markings: [],
    handwriting: [],
    uncertainties: [{ code: "TOPOLOGY", evidence: "source does not close a trustworthy flat", blocking: true }]
  }]);
  return routeJob(job.jobId);
}

test("VIEWS_ONLY produces only REVIEW_ONLY / NO CUT output and cannot enter production audit", () => {
  const job = reviewJob();
  assert.equal(job.state, "REVIEW_REQUIRED");
  const review = {
    schema: "REVIEW_OUTPUT_V1",
    parts: [{
      code: "RV01",
      status: "VIEWS_ONLY",
      preview_reason: "separate_source_views",
      flags: ["TOPOLOGY unresolved — independently proved FRONT view only"],
      checks: {
        contour_topology: "FLAGGED",
        datum: "PASS",
        feature_count: "PASS",
        unfold: "FLAGGED",
        containment: "FLAGGED",
        bend_domain: "N/A",
        material_rules: "PASS",
        slot_semantics: "N/A"
      },
      entities: [
        {
          type: "LINE",
          role: "source_view",
          view_id: "FRONT",
          start: [0, 0],
          end: [40, 0],
          evidenceRefs: ["page:1 FRONT bottom edge"]
        },
        {
          type: "LINE",
          role: "source_view",
          view_id: "FRONT",
          start: [40, 0],
          end: [40, 20],
          evidenceRefs: ["page:1 FRONT right edge"]
        }
      ]
    }]
  };
  const out = jobStore.exportReviewDxf(job.jobId, review);
  assert.equal(out.state, "REVIEW_ONLY");
  assert.equal(out.output?.reviewOnly, true);
  assert.ok(out.output?.filename.endsWith("_ALL_REVIEW_ONLY.dxf"));
  assert.ok(existsSync(join(dataRoot(), out.output!.relativePath)));
  assert.throws(() => jobStore.auditDxf(job.jobId), /DXF_AUDIT_NOT_ALLOWED_IN_STATE/);
});

test("review exporter rejects a payload containing only PASS parts", () => {
  const job = reviewJob();
  const invalid = {
    schema: "REVIEW_OUTPUT_V1",
    parts: [{
      code: "RV01",
      status: "PASS",
      flags: [],
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
      entities: [{
        type: "LWPOLYLINE",
        role: "outer",
        closed: true,
        vertices: [[0,0,0],[40,0,0],[40,20,0],[0,20,0]],
        evidenceRefs: ["page:1"]
      }]
    }]
  };
  assert.throws(() => jobStore.exportReviewDxf(job.jobId, invalid), /review export requires at least one PREVIEW or VIEWS_ONLY part/);
});
