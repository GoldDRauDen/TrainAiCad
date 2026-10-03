import test from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync } from "node:fs";
import { join } from "node:path";
import { tmpdir } from "node:os";
import { jobStore, routeJob } from "../src/core.js";
import { exportRepoDirectE2E } from "../src/repo-direct-e2e.js";

process.env.TRAINAICAD_MCP_DATA = mkdtempSync(join(tmpdir(), "cad-repo-review-"));
process.env.TRAINAICAD_ARTIFACT_SECRET = "x".repeat(64);
process.env.TRAINAICAD_PUBLIC_URL = "https://cad.example.test";
process.env.TRAINAICAD_SOURCE_COMMIT = "repo-review-unit";

const sourceSha = "c".repeat(64);
const censusNames = [
  "HOLE",
  "TAP",
  "SLOT_STRAIGHT",
  "CURVED_SLOT",
  "KEGAKI",
  "PIASU",
  "SLIT_RELIEF",
  "RIB",
  "CHAMFER_FILLET",
  "HEMMING",
  "Z_BEND",
  "ACUTE_BEND_LT85",
  "BOXMET",
  "MATERIAL_RULES",
  "NOBI",
  "REVISION_CANCELLATION",
];

function tn(value: number) {
  return { value, unit: "mm" as const, origin: "PRINTED" as const, page: 1 };
}

test("repo-direct flags reviewable ambiguity and still exports one REVIEW_ONLY composite", () => {
  const created = jobStore.create(
    {
      fileName: "review.pdf",
      sha256: sourceSha,
      mimeType: "application/pdf",
      sourceId: sourceSha,
    },
    undefined,
    "PDF_ONLY",
  );

  const census = Object.fromEntries(
    censusNames.map((name) => [
      name,
      name === "TAP"
        ? { state: "UNKNOWN", evidence: [] }
        : { state: "NO", evidence: [] },
    ]),
  );

  jobStore.submitEvidence(created.jobId, [
    {
      schema: "CAD_EVIDENCE_V1",
      jobId: created.jobId,
      code: "26-TEST-001",
      source: { sourceId: sourceSha, page: 1 },
      census,
      material: { printed: "SUS304", family: "SUS304", thickness: tn(2) },
      views: [{ id: "FLAT", type: "FLAT" }],
      contour: {
        topology: "PLATE",
        status: "PROVED",
        overallX: tn(100),
        overallY: tn(50),
      },
      faceCount: 1,
      partClassHint: "FLAT_NO_BEND",
      features: [],
      bends: [],
      markings: [],
      handwriting: [],
      uncertainties: [
        {
          code: "TAP_SEMANTIC_UNCLEAR",
          evidence: "source callout is unresolved but outer geometry is known",
          blocking: true,
        },
      ],
    },
  ]);

  const routed = routeJob(created.jobId);
  assert.equal(routed.state, "REVIEW_REQUIRED");

  const result = exportRepoDirectE2E({
    schema: "REPO_DIRECT_DXF_V1",
    jobId: created.jobId,
    parts: [
      {
        code: "26-TEST-001",
        material: "SUS304",
        thickness_mm: 2,
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
          slot_semantics: "N/A",
        },
        entities: [
          {
            type: "LWPOLYLINE",
            role: "outer",
            closed: true,
            vertices: [
              [0, 0, 0],
              [100, 0, 0],
              [100, 50, 0],
              [0, 50, 0],
            ],
          },
        ],
      },
    ],
    gates: [
      {
        code: "26-TEST-001",
        finalCensusClosed: false,
        sourceFeatureCompleteness: false,
        crossFeatureValidation: true,
        constraintsClosed: true,
        localFaceTransforms: "N/A",
        foldBackSourceReprojection: "N/A",
        rawDataSnapshot: "N/A",
        sameParameterGate: "N/A",
        manufacturingChangeLedger: "N/A",
        untouchedDataInvariance: "N/A",
        sourceReprojection: "N/A",
        sourceActiveFamilies: ["CUT"],
        canonicalFamilies: ["CUT"],
        serializedFamilies: ["CUT"],
        evidenceRefs: ["p1:outer"],
      },
    ],
  });

  assert.equal(result.job.state, "QA_COMPLETE");
  assert.match(result.artifact.fileName, /_ALL_REVIEW_ONLY\.dxf$/);
  assert.equal(result.job.dxfAudit?.ok, true);
  assert.ok(result.job.dxfAudit?.labels.includes("26-TEST-001 [FLAG]"));
  assert.ok(
    result.job.dxfAudit?.labels.some((label) =>
      label.startsWith("REVIEW ONLY - NO CUT"),
    ),
  );
});
