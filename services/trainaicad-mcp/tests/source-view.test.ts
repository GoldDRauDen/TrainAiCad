import test from "node:test";
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { jobStore, recordSourceViewReceipt } from "../src/core.js";
import { storeSource } from "../src/ingest.js";
import { renderSourcePage } from "../src/source-view.js";

process.env.TRAINAICAD_MCP_DATA = mkdtempSync(join(tmpdir(), "trainaicad-source-view-"));

test("verified PDF source renders a real PNG and receipt gates evidence by page", () => {
  const python = process.env.TRAINAICAD_PYTHON ?? (process.platform === "win32" ? "python" : "python3");
  const generated = spawnSync(python, ["-c", "import pymupdf,sys; d=pymupdf.open(); p=d.new_page(); p.insert_text((72,72),'TrainAiCad E2E'); sys.stdout.buffer.write(d.tobytes())"], { maxBuffer: 8 * 1024 * 1024 });
  assert.equal(generated.status, 0, generated.stderr?.toString());
  assert.equal(generated.stdout.subarray(0, 5).toString("ascii"), "%PDF-", `unexpected PDF bytes: ${generated.stdout.subarray(0, 24).toString("hex")}`);
  const source = storeSource({ fileName: "source.pdf", bytes: generated.stdout }, "DRAWING");
  const job = jobStore.create({ fileName: source.fileName, sha256: source.sha256 }, undefined, "AUTO");
  jobStore.bindSource(job.jobId, "DRAWING", source);

  assert.throws(() => jobStore.submitEvidence(job.jobId, [evidence(job.jobId, source.sha256, [])]), /SOURCE_IMAGE_NOT_INSPECTED/);
  const rendered = renderSourcePage(jobStore.get(job.jobId), 1, 100);
  assert.equal(rendered.png.subarray(0, 8).toString("hex"), "89504e470d0a1a0a");
  assert.equal(rendered.receipt.sourceSha256, source.sha256);
  recordSourceViewReceipt(job.jobId, rendered.receipt);
  const accepted = jobStore.submitEvidence(job.jobId, [evidence(job.jobId, source.sha256, [rendered.receipt.receiptId])]);
  assert.equal(accepted.state, "EVIDENCE_READY");
});

function evidence(jobId: string, sha: string, visualReceiptIds: string[]) {
  return {
    schema: "CAD_EVIDENCE_V1",
    jobId,
    code: "VIEW001",
    source: { sourceId: sha, page: 1, visualReceiptIds },
    material: { printed: "SS400", family: "SS", thickness: { value: 2, unit: "mm", origin: "PRINTED" } },
    views: [{ id: "A", type: "FLAT" }],
    contour: { topology: "PLATE", status: "PROVED", overallX: { value: 20, unit: "mm", origin: "PRINTED" }, overallY: { value: 10, unit: "mm", origin: "PRINTED" } },
    features: [], bends: [], markings: [], handwriting: [], uncertainties: []
  };
}
