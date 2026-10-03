import test from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync } from "node:fs";
import { join } from "node:path";
import { tmpdir } from "node:os";
import { jobStore, routeJob } from "../src/core.js";
import { exportRepoDirectDxf } from "../src/repo-direct.js";

process.env.TRAINAICAD_MCP_DATA = mkdtempSync(join(tmpdir(), "cad-repo-direct-"));
process.env.TRAINAICAD_ARTIFACT_SECRET = "x".repeat(64);
process.env.TRAINAICAD_PUBLIC_URL = "https://cad.example.test";
process.env.TRAINAICAD_SOURCE_COMMIT = "repo-direct-unit";

const sourceSha = "a".repeat(64);
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

function census() {
  return Object.fromEntries(
    censusNames.map((name) => [
      name,
      {
        state: ["TAP", "MATERIAL_RULES", "NOBI"].includes(name)
          ? "YES"
          : "NO",
        evidence: [`unit:${name}`],
      },
    ]),
  );
}

function tn(value: number, unit: "mm" | "deg" = "mm") {
  return { value, unit, origin: "PRINTED" as const, page: 1 };
}

test("repo-direct path exports a U-profile with Y-axis bend and bent-face features without V0.2 blockers", () => {
  const created = jobStore.create(
    {
      fileName: "036339.pdf",
      sha256: sourceSha,
      mimeType: "application/pdf",
      sourceId: sourceSha,
    },
    undefined,
    "PDF_ONLY",
  );

  jobStore.submitEvidence(created.jobId, [
    {
      schema: "CAD_EVIDENCE_V1",
      jobId: created.jobId,
      code: "036339",
      source: { sourceId: sourceSha, page: 1 },
      census: census(),
      material: {
        printed: "SUS304",
        family: "SUS304",
        thickness: tn(3),
      },
      views: [{ id: "FORMED", type: "FORMED" }],
      contour: {
        topology: "U_PROFILE",
        status: "PROVED",
        overallX: tn(200.4),
        overallY: tn(50),
      },
      faceCount: 3,
      partClassHint: "DOUBLE_BEND_U",
      features: [
        {
          id: "M4",
          family: "TAP",
          quantity: 4,
          diameter: tn(3.3),
          callout: "4-M4",
          status: "PROVED",
        },
        {
          id: "SQ",
          family: "CUTOUT",
          quantity: 2,
          callout: "2-SQUARE",
          status: "PROVED",
        },
      ],
      bends: [
        {
          id: "B1",
          angle: tn(90, "deg"),
          axis: "X",
          sign: "POSITIVE",
          nobi: tn(4.8),
          status: "PROVED",
        },
        {
          id: "B2",
          angle: tn(90, "deg"),
          axis: "Y",
          sign: "NEGATIVE",
          nobi: tn(4.8),
          status: "PROVED",
        },
      ],
      markings: [],
      handwriting: [],
      uncertainties: [],
    },
  ]);

  const routed = routeJob(created.jobId);
  assert.equal(routed.routes[0]?.status, "ROUTED");
  assert.equal(routed.routes[0]?.mechanical.partClass, "DOUBLE_BEND_U");

  const result = exportRepoDirectDxf({
    schema: "REPO_DIRECT_DXF_V1",
    jobId: created.jobId,
    sourceSha256: sourceSha,
    ruleSnapshotId: routed.production.snapshotId,
    parts: [
      {
        code: "036339",
        material: "SUS304",
        thickness_mm: 3,
        status: "PASS",
        flags: [],
        checks: {
          contour_topology: "PASS",
          datum: "PASS",
          feature_count: "PASS",
          unfold: "PASS",
          containment: "PASS",
          bend_domain: "PASS",
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
              [200.4, 0, 0],
              [200.4, 50, 0],
              [0, 50, 0],
            ],
          },
          { type: "CIRCLE", role: "hole", center: [25, 15], radius: 1.65 },
          { type: "CIRCLE", role: "hole", center: [25, 35], radius: 1.65 },
          { type: "CIRCLE", role: "hole", center: [175, 15], radius: 1.65 },
          { type: "CIRCLE", role: "hole", center: [175, 35], radius: 1.65 },
          {
            type: "LWPOLYLINE",
            role: "cutout",
            closed: true,
            vertices: [
              [77.5, 17.5, 0],
              [77.5, 22.5, 0],
              [82.5, 22.5, 0],
              [82.5, 17.5, 0],
            ],
          },
          {
            type: "LWPOLYLINE",
            role: "cutout",
            closed: true,
            vertices: [
              [117.5, 27.5, 0],
              [117.5, 32.5, 0],
              [122.5, 32.5, 0],
              [122.5, 27.5, 0],
            ],
          },
          {
            type: "LINE",
            role: "bend",
            linetype: "DASHED",
            start: [45, 0],
            end: [45, 50],
          },
          {
            type: "LINE",
            role: "bend",
            linetype: "DASHED",
            start: [48, 0],
            end: [48, 50],
          },
          {
            type: "LINE",
            role: "bend",
            linetype: "DASHED",
            start: [152.4, 0],
            end: [152.4, 50],
          },
          {
            type: "LINE",
            role: "bend",
            linetype: "DASHED",
            start: [155.4, 0],
            end: [155.4, 50],
          },
        ],
      },
    ],
    gates: [
      {
        code: "036339",
        finalCensusClosed: true,
        sourceFeatureCompleteness: true,
        crossFeatureValidation: true,
        constraintsClosed: true,
        localFaceTransforms: "PASS",
        foldBackSourceReprojection: "PASS",
        rawDataSnapshot: "N/A",
        sameParameterGate: "N/A",
        manufacturingChangeLedger: "N/A",
        untouchedDataInvariance: "N/A",
        sourceReprojection: "N/A",
        sourceActiveFamilies: ["CUT", "BEND", "HOLE_TAP", "INNER_CUT"],
        canonicalFamilies: ["CUT", "BEND", "HOLE_TAP", "INNER_CUT"],
        serializedFamilies: ["CUT", "BEND", "HOLE_TAP", "INNER_CUT"],
        evidenceRefs: ["unit:036339:p1"],
      },
    ],
  });

  assert.equal(result.job.state, "QA_COMPLETE");
  assert.match(result.artifact.fileName, /_ALL\.dxf$/);
  assert.equal(result.job.dxfAudit?.ok, true);
  assert.equal(result.job.dxfAudit?.insunits, 4);
  assert.ok(!result.job.flags.some((flag) => flag.includes("V02_")));
});
