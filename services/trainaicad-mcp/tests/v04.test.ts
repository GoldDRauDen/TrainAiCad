import test from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, mkdirSync, writeFileSync, readFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { createMcpHandler } from "@modelcontextprotocol/server";
import { buildServer } from "../src/server.js";
import { jobStore, routeJob } from "../src/core.js";
import { storeSource } from "../src/ingest.js";
import { readSnapshot, rulesBundle, snapshotRoot } from "../src/snapshot.js";
import {
  imageDirectory,
  sourceImage,
  sha256,
  deliveredImages,
} from "../src/source.js";
import { artifact, downloadArtifact } from "../src/artifact.js";
process.env.TRAINAICAD_MCP_DATA = mkdtempSync(join(tmpdir(), "cad-v04-"));
// Synthetic transport/QA fixtures only; never source evidence or customer coordinates.
const PNG = Buffer.from(
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jY9kAAAAASUVORK5CYII=",
  "base64",
);
const input = storeSource({ fileName: "unit.png", bytes: PNG }, "DRAWING"),
  n = (value: number) => ({ value, unit: "mm", origin: "PRINTED" });
function ready() {
  const job = jobStore.create(input, undefined, "PDF_ONLY"),
    census = Object.fromEntries(
      Object.keys(readSnapshot(job.production).router.feature_routes).map(
        (k) => [
          k,
          {
            state: k === "HOLE" || k === "MATERIAL_RULES" ? "YES" : "NO",
            evidence: ["synthetic source fixture: " + k],
          },
        ],
      ),
    );
  jobStore.submitEvidence(job.jobId, [
    {
      schema: "CAD_EVIDENCE_V1",
      jobId: job.jobId,
      code: "UNIT",
      source: { sourceId: input.sha256, page: 1 },
      census,
      material: { printed: "SS400", family: "SS", thickness: n(2) },
      views: [{ id: "A", type: "FLAT" }],
      contour: {
        topology: "PLATE",
        status: "PROVED",
        overallX: n(40),
        overallY: n(20),
      },
      features: [
        {
          id: "H",
          family: "HOLE",
          quantity: 2,
          diameter: n(4),
          status: "PROVED",
        },
      ],
      bends: [],
      markings: [],
      handwriting: [],
      uncertainties: [],
    },
  ]);
  routeJob(job.jobId);
  jobStore.buildGeometry(job.jobId, [
    {
      schema: "GEOMETRY_SOURCE_V1",
      jobId: job.jobId,
      code: "UNIT",
      sourceSha256: input.sha256,
      origin: "PDF_SOURCE",
      buildKind: "FLAT_SINGLE_FACE",
      faces: [
        {
          faceId: "F",
          sourceView: "A",
          contour: [
            { x: 0, y: 0 },
            { x: 40, y: 0 },
            { x: 40, y: 20 },
            { x: 0, y: 20 },
          ],
        },
      ],
      faceOrder: ["F"],
      bends: [],
      features: [
        {
          featureId: "H",
          family: "HOLE",
          hostFace: "F",
          geometries: [
            { kind: "CIRCLE", center: { x: 10, y: 10 }, diameter: 4 },
            { kind: "CIRCLE", center: { x: 30, y: 10 }, diameter: 4 },
          ],
        },
      ],
      proofs: {},
    },
  ]);
  const dir = imageDirectory(job),
    imageId = sha256("synthetic-image-key");
  mkdirSync(dir, { recursive: true });
  writeFileSync(join(dir, imageId + ".png"), PNG);
  writeFileSync(
    join(dir, "manifest.json"),
    JSON.stringify({
      sourceSha256: input.sha256,
      pageCount: 1,
      pages: [],
      images: [
        { imageId, page: 1, roi: [0, 0, 1, 1], dpi: 110, sha256: sha256(PNG) },
      ],
    }),
  );
  sourceImage(job, imageId);
  const witnesses = [
    {
      id: "O",
      faceId: "F",
      contourVertex: 0,
      sourceIdentity: "synthetic bottom left",
    },
    ...[1, 2].map((i) => ({
      id: "P" + i,
      featureId: "H",
      instance: i,
      sourceIdentity: "synthetic hole " + i,
    })),
  ];
  const d = (
    id: string,
    from: string,
    to: string,
    axis: string,
    value: number,
  ) => ({
    id,
    imageId,
    printedText: String(value),
    from,
    to,
    axis,
    semantic: "BASELINE",
    value: n(value),
  });
  return {
    job: jobStore.get(job.jobId),
    checks: {
      code: "UNIT",
      witnesses,
      dimensions: [
        d("X1", "O", "P1", "X", 10),
        d("X2", "P1", "P2", "X", 20),
        d("Y1", "O", "P1", "Y", 10),
        d("Y2", "O", "P2", "Y", 10),
      ],
    },
  };
}
test("QA measures linked datums and actual DXF read-back remains research only", () => {
  const { job, checks } = ready();
  const q = jobStore.verify(job.jobId, [checks]);
  assert.equal(q.computedQa?.[0]?.status, "RESEARCH_GEOMETRY_CHECKED");
  assert.ok(
    q.computedQa?.[0]?.dimensionResiduals.every((x) => x.residualMm === 0),
  );
  jobStore.exportDxf(job.jobId);
  const done = jobStore.auditDxf(job.jobId);
  assert.equal(done.state, "QA_COMPLETE");
  assert.equal(done.dxfAudit?.entityTypes.CIRCLE, 2);
  assert.ok(
    done.dxfAudit?.labels.some((l) => l.startsWith("REVIEW ONLY - NO CUT")),
  );
  assert.ok(artifact(done).bytes.length > 0);
});
test("bad printed dimension, diameter or outside hole cannot be exported", () => {
  for (const defect of ["dimension", "diameter", "outside"]) {
    const { job, checks } = ready();
    if (defect === "dimension") checks.dimensions[0]!.value = n(11);
    if (
      defect === "diameter" &&
      job.geometry[0]!.features[0]!.geometry.kind === "CIRCLE"
    )
      job.geometry[0]!.features[0]!.geometry.diameter = 5;
    if (
      defect === "outside" &&
      job.geometry[0]!.features[0]!.geometry.kind === "CIRCLE"
    )
      job.geometry[0]!.features[0]!.geometry.center.x = 0;
    assert.equal(
      jobStore.verify(job.jobId, [checks]).computedQa?.[0]?.status,
      "REVIEW_REQUIRED",
    );
    assert.throws(() => jobStore.exportDxf(job.jobId), /COMPUTED_QA_FAILED/);
  }
});
test("disconnected chains cannot masquerade as an anchored datum", () => {
  const { job, checks } = ready();
  checks.dimensions = checks.dimensions.filter(
    (d) => d.axis !== "X" || d.id === "X2",
  );
  assert.ok(
    jobStore
      .verify(job.jobId, [checks])
      .computedQa?.[0]?.flags.some((f) => f.includes("DATUM_PATH_UNPROVED")),
  );
  assert.throws(() => jobStore.exportDxf(job.jobId), /COMPUTED_QA_FAILED/);
});
test("image receipt belongs to each job, even for identical bytes", () => {
  const { job, checks } = ready();
  const other = jobStore.create(input, undefined, "PDF_ONLY");
  assert.equal(deliveredImages(other).length, 0);
  checks.dimensions[0]!.imageId = "f".repeat(64);
  assert.ok(
    jobStore
      .verify(job.jobId, [checks])
      .computedQa?.[0]?.flags.some((f) => f.includes("NOT_DELIVERED")),
  );
  assert.throws(() => jobStore.exportDxf(job.jobId), /COMPUTED_QA_FAILED/);
});
test("export requires computed QA and rejects changed geometry", () => {
  const { job, checks } = ready();
  assert.throws(
    () => jobStore.exportDxf(job.jobId),
    /COMPUTED_QA_MISSING_OR_STALE/,
  );
  jobStore.verify(job.jobId, [checks]);
  job.geometry[0]!.outerContours[0]![1]!.x = 41;
  assert.throws(
    () => jobStore.exportDxf(job.jobId),
    /COMPUTED_QA_MISSING_OR_STALE/,
  );
});
test("changed saved DXF cannot be audited or delivered", () => {
  const { job, checks } = ready();
  jobStore.verify(job.jobId, [checks]);
  jobStore.exportDxf(job.jobId);
  writeFileSync(job.dxfOutput!.absolutePath, "changed");
  assert.throws(
    () => jobStore.auditDxf(job.jobId),
    /DXF_OUTPUT_CONTENT_CHANGED/,
  );
  assert.throws(() => artifact(job), /DXF_ARTIFACT_CONTENT_CHANGED/);
});
test("job IDs cannot traverse the filesystem", () => {
  assert.throws(() => jobStore.get("../../package"), /INVALID_JOB_ID/);
});
test("tampered frozen rules are rejected without changing production files", () => {
  const { job } = ready(),
    p = "skills/lispcad/core/DATUM_DIMENSION.md",
    file = join(snapshotRoot(job.production), p),
    original = readFileSync(file);
  try {
    writeFileSync(file, "modified");
    assert.throws(
      () => rulesBundle(job.production, [p]),
      /RULE_SNAPSHOT_TAMPERED/,
    );
  } finally {
    writeFileSync(file, original);
  }
});
test("signed artifacts reject query tampering and changed bytes", () => {
  const { job, checks } = ready();
  jobStore.verify(job.jobId, [checks]);
  jobStore.exportDxf(job.jobId);
  jobStore.auditDxf(job.jobId);
  process.env.TRAINAICAD_PUBLIC_URL = "https://cad.example.test";
  process.env.TRAINAICAD_ARTIFACT_SECRET = "x".repeat(40);
  try {
    const file = artifact(job),
      url = new URL(file.url!);
    assert.deepEqual(downloadArtifact(job, url).bytes, file.bytes);
    const bad = new URL(url);
    bad.searchParams.set("sha256", "0".repeat(64));
    assert.throws(() => downloadArtifact(job, bad), /SIGNATURE_INVALID/);
    writeFileSync(job.dxfOutput!.absolutePath, "changed");
    assert.throws(() => downloadArtifact(job, url), /CONTENT_CHANGED/);
  } finally {
    delete process.env.TRAINAICAD_PUBLIC_URL;
    delete process.env.TRAINAICAD_ARTIFACT_SECRET;
  }
});
test("SDK HTTP lists 14 tools and accepts a real body exceeding the old 4 MiB limit", async () => {
  const handler = createMcpHandler(buildServer, {
    maxRequestBodySize: 36 * 1024 * 1024,
  });
  let id = 0;
  const call = async (method: string, params: unknown) => {
    const r = await handler.fetch(
      new Request("http://localhost/mcp", {
        method: "POST",
        headers: {
          "content-type": "application/json",
          accept: "application/json, text/event-stream",
          "mcp-protocol-version": "2025-03-26",
        },
        body: JSON.stringify({ jsonrpc: "2.0", id: ++id, method, params }),
      }),
    );
    const text = await r.text(),
      line = text.split("\n").find((l) => l.startsWith("data:")),
      packet = JSON.parse(line ? line.slice(5) : text);
    assert.equal(r.status, 200);
    assert.equal(packet.error, undefined);
    assert.notEqual(packet.result?.isError, true);
    return packet.result;
  };
  try {
    await call("initialize", {
      protocolVersion: "2025-03-26",
      capabilities: {},
      clientInfo: { name: "unit", version: "1" },
    });
    assert.equal((await call("tools/list", {})).tools.length, 14);
    const large = Buffer.concat([PNG, Buffer.alloc(4 * 1024 * 1024)]),
      result = await call("tools/call", {
        name: "ingest_cad_file",
        arguments: { fileName: "large.png", data: large.toString("base64") },
      });
    assert.equal(JSON.parse(result.content[0].text).bytes, large.length);
  } finally {
    await handler.close();
  }
});
