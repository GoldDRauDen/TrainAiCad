import test from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { tmpdir } from "node:os";
import { CheckpointStore, type ObjectStore } from "../src/storage.js";

test("checkpoint publishes human-readable latest/job/code catalog alongside blobs", async () => {
  const root = mkdtempSync(join(tmpdir(), "cad-storage-catalog-"));
  const jobs = join(root, "jobs");
  mkdirSync(jobs, { recursive: true });
  const jobId = "cad_0123456789abcdef";
  writeFileSync(
    join(jobs, `${jobId}.json`),
    JSON.stringify({
      jobId,
      state: "QA_COMPLETE",
      mode: "PDF_ONLY",
      createdAt: "2026-10-03T07:00:00.000Z",
      updatedAt: "2026-10-03T07:24:00.000Z",
      source: {
        fileName: "520625-01.pdf",
        sha256: "a".repeat(64),
        mimeType: "application/pdf",
      },
      evidence: [{ code: "035742" }, { code: "035770" }],
      routes: [
        { code: "035742", status: "ROUTED", mode: "FLAT", mechanical: { partClass: "FLAT_NO_BEND" } },
        { code: "035770", status: "ROUTED", mode: "FLAT", mechanical: { partClass: "FLAT_NO_BEND" } },
      ],
      dxfOutput: {
        fileName: `${jobId}_ALL.dxf`,
        sha256: "b".repeat(64),
        serializerContract: "TrainAiCad-DXF-V4.9",
        writtenAt: "2026-10-03T07:23:00.000Z",
        codeOrder: ["035742", "035770"],
      },
      dxfAudit: {
        ok: true,
        auditErrorCount: 0,
        entityCount: 10,
        auditedAt: "2026-10-03T07:24:00.000Z",
      },
      flags: [],
    }),
  );

  const objects = new Map<string, Buffer>();
  const remote: ObjectStore = {
    get: async (key) => objects.get(key) ?? null,
    put: async (key, bytes) => {
      objects.set(key, Buffer.from(bytes));
    },
  };

  const store = new CheckpointStore(root, remote);
  await store.checkpoint();

  assert.ok(objects.has("index.json"));
  assert.ok([...objects.keys()].some((key) => key.startsWith("blobs/")));
  assert.ok(objects.has("catalog/latest.json"));
  assert.ok(objects.has(`catalog/jobs/${jobId}.json`));
  assert.ok(objects.has(`catalog/codes/035742/${jobId}.json`));
  assert.ok(objects.has("catalog/codes/035742/latest.json"));
  assert.ok(objects.has(`catalog/codes/035770/${jobId}.json`));

  const latest = JSON.parse(objects.get("catalog/latest.json")!.toString());
  assert.equal(latest.jobId, jobId);
  assert.deepEqual(latest.codes, ["035742", "035770"]);
  assert.equal(latest.output.fileName, `${jobId}_ALL.dxf`);
  assert.equal(latest.dxfAudit.ok, true);
});
