import { spawnSync } from "node:child_process";
import { createHash, randomUUID } from "node:crypto";
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { extname, join } from "node:path";
import type { CadJob, SourceViewReceipt } from "./model.js";
import { dataRoot, verifiedSource } from "./ingest.js";

export type NormalizedRegion = [number, number, number, number];

export function sourcePageCount(job: CadJob): number {
  if (!job.sourceVerified || !job.sourceBindings.DRAWING) throw new Error("SOURCE_NOT_VERIFIED");
  const drawing = verifiedSource("DRAWING", job.source.fileName, job.source.sha256);
  if (drawing.kind !== "PDF") return 1;
  const script = [
    "import sys, pymupdf as fitz",
    "raw=sys.stdin.buffer.read()",
    "doc=fitz.open(stream=raw, filetype='pdf')",
    "print(len(doc))"
  ].join("\n");
  const python = process.env.TRAINAICAD_PYTHON ?? (process.platform === "win32" ? "python" : "python3");
  const result = spawnSync(python, ["-c", script], { input: readFileSync(drawing.storedPath), encoding: "utf8", maxBuffer: 1024 * 1024 });
  if (result.error) throw new Error(`SOURCE_PAGE_COUNT_FAILED:${result.error.message}`);
  if (result.status !== 0) throw new Error(`SOURCE_PAGE_COUNT_FAILED:${result.stderr.trim()}`);
  const count = Number.parseInt(result.stdout.trim(), 10);
  if (!Number.isInteger(count) || count < 1) throw new Error("SOURCE_PAGE_COUNT_INVALID");
  return count;
}

export function renderSourcePage(job: CadJob, page: number, dpi: number, region: NormalizedRegion = [0, 0, 1, 1], rotation: 0 | 90 | 180 | 270 = 0): {
  receipt: SourceViewReceipt;
  png: Buffer;
} {
  if (!job.sourceVerified || !job.sourceBindings.DRAWING) throw new Error("SOURCE_NOT_VERIFIED");
  if (!Number.isInteger(page) || page < 1) throw new Error("SOURCE_PAGE_INVALID");
  if (!Number.isInteger(dpi) || dpi < 72 || dpi > 300) throw new Error("SOURCE_DPI_OUT_OF_RANGE");
  if (region.some((n) => !Number.isFinite(n) || n < 0 || n > 1) || region[0] >= region[2] || region[1] >= region[3]) throw new Error("SOURCE_REGION_INVALID");
  if (![0, 90, 180, 270].includes(rotation)) throw new Error("SOURCE_ROTATION_INVALID");
  const drawing = verifiedSource("DRAWING", job.source.fileName, job.source.sha256);
  const isPdf = drawing.kind === "PDF";
  if (!isPdf && page !== 1) throw new Error("IMAGE_SOURCE_HAS_ONLY_PAGE_1");
  const regionKey = region.map((n) => Math.round(n * 1_000_000)).join("-");
  const cachePath = join(dataRoot(), "cache", "source-views", drawing.sha256, `page-${page}-region-${regionKey}-dpi-${dpi}-rotation-${rotation}.png`);
  if (existsSync(cachePath)) {
    const png = readFileSync(cachePath);
    if (png.length < 8 || png.subarray(0, 8).toString("hex") !== "89504e470d0a1a0a") throw new Error("SOURCE_VIEW_CACHE_CORRUPTED");
    const imageSha256 = createHash("sha256").update(png).digest("hex");
    const receipt = job.sourceViewReceipts.find((r) => r.sourceSha256 === drawing.sha256 && r.page === page && r.dpi === dpi && (r.rotation ?? 0) === rotation && JSON.stringify(r.region) === JSON.stringify(region) && r.imageSha256 === imageSha256);
    if (receipt) return { receipt, png };
    return { receipt: makeReceipt(drawing.sha256, page, dpi, imageSha256, region, rotation), png };
  }
  const script = [
    "import sys, pymupdf as fitz",
    "raw=sys.stdin.buffer.read()",
    `doc=fitz.open(stream=raw, filetype=${JSON.stringify(extname(drawing.fileName).slice(1).toLowerCase())})`,
    `page_no=${page - 1}`,
    "if page_no < 0 or page_no >= len(doc): raise ValueError('SOURCE_PAGE_OUT_OF_RANGE')",
    `page=doc.load_page(page_no); page.set_rotation((page.rotation+${rotation})%360); rect=page.rect`,
    `clip=fitz.Rect(rect.x0+rect.width*${region[0]}, rect.y0+rect.height*${region[1]}, rect.x0+rect.width*${region[2]}, rect.y0+rect.height*${region[3]})`,
    `pix=page.get_pixmap(matrix=fitz.Matrix(${dpi}/72, ${dpi}/72), clip=clip, alpha=False)`,
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
  const imageSha256 = createHash("sha256").update(png).digest("hex");
  mkdirSync(join(dataRoot(), "cache", "source-views", drawing.sha256), { recursive: true });
  writeFileSync(cachePath, png, { flag: "wx" });
  const receipt = makeReceipt(drawing.sha256, page, dpi, imageSha256, region, rotation);
  return { receipt, png };
}

function makeReceipt(sourceSha256: string, page: number, dpi: number, imageSha256: string, region: NormalizedRegion, rotation: 0 | 90 | 180 | 270): SourceViewReceipt {
  return {
    receiptId: randomUUID(), sourceSha256, page, imageSha256,
    region, rotation, dpi, storedAt: new Date().toISOString()
  };
}
