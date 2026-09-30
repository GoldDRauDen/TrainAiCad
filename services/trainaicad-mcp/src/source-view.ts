import { spawnSync } from "node:child_process";
import { createHash, randomUUID } from "node:crypto";
import { readFileSync } from "node:fs";
import { extname } from "node:path";
import type { CadJob, SourceViewReceipt } from "./model.js";
import { verifiedSource } from "./ingest.js";

export function renderSourcePage(job: CadJob, page: number, dpi: number): {
  receipt: SourceViewReceipt;
  png: Buffer;
} {
  if (!job.sourceVerified || !job.sourceBindings.DRAWING) throw new Error("SOURCE_NOT_VERIFIED");
  if (!Number.isInteger(page) || page < 1) throw new Error("SOURCE_PAGE_INVALID");
  if (!Number.isInteger(dpi) || dpi < 72 || dpi > 300) throw new Error("SOURCE_DPI_OUT_OF_RANGE");
  const drawing = verifiedSource("DRAWING", job.source.fileName, job.source.sha256);
  const isPdf = drawing.kind === "PDF";
  if (!isPdf && page !== 1) throw new Error("IMAGE_SOURCE_HAS_ONLY_PAGE_1");
  const script = [
    "import sys, pymupdf as fitz",
    "raw=sys.stdin.buffer.read()",
    `doc=fitz.open(stream=raw, filetype=${JSON.stringify(extname(drawing.fileName).slice(1).toLowerCase())})`,
    `page_no=${page - 1}`,
    "if page_no < 0 or page_no >= len(doc): raise ValueError('SOURCE_PAGE_OUT_OF_RANGE')",
    `pix=doc.load_page(page_no).get_pixmap(matrix=fitz.Matrix(${dpi}/72, ${dpi}/72), alpha=False)`,
    "sys.stdout.buffer.write(pix.tobytes('png'))"
  ].join("\n");
  const python = process.env.TRAINAICAD_PYTHON ?? (process.platform === "win32" ? "python" : "python3");
  const rendered = spawnSync(python, ["-c", script], { input: readFileSync(drawing.storedPath), maxBuffer: 32 * 1024 * 1024 });
  if (rendered.error) throw new Error(`SOURCE_RENDER_FAILED:${rendered.error.message}`);
  if (rendered.status !== 0 || !rendered.stdout?.length) {
    const detail = rendered.stderr?.toString("utf8").trim() || "unknown render error";
    throw new Error(`SOURCE_RENDER_FAILED:${detail}`);
  }
  const png = Buffer.from(rendered.stdout);
  if (png.length < 8 || png.subarray(0, 8).toString("hex") !== "89504e470d0a1a0a") throw new Error("SOURCE_RENDER_INVALID_PNG");
  const receipt: SourceViewReceipt = {
    receiptId: randomUUID(),
    sourceSha256: drawing.sha256,
    page,
    imageSha256: createHash("sha256").update(png).digest("hex"),
    region: [0, 0, 1, 1],
    dpi,
    storedAt: new Date().toISOString()
  };
  return { receipt, png };
}
