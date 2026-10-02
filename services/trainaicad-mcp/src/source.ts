import { createHash } from "node:crypto";
import { readFileSync, existsSync, writeFileSync, mkdirSync } from "node:fs";
import { join, extname } from "node:path";
import { execFile } from "node:child_process";
import { promisify } from "node:util";
import { dataRoot } from "./ingest.js";
import type { CadJob } from "./model.js";
const run = promisify(execFile);
export const sha256 = (data: Buffer | string) =>
  createHash("sha256").update(data).digest("hex");
export type SourceImage = {
  imageId: string;
  page: number;
  roi: number[];
  dpi: number;
  sha256: string;
};
export type SourceManifest = {
  sourceSha256: string;
  pageCount: number;
  pages: {
    page: number;
    widthPt: number;
    heightPt: number;
    rotation: number;
    text: string;
    embeddedImages: number;
  }[];
  images: SourceImage[];
};
export function sourcePath(job: CadJob) {
  const ext = extname(job.source.fileName).toLowerCase();
  if (!/\.(pdf|png|jpg|jpeg|tif|tiff|bmp|webp)$/.test(ext))
    throw new Error("SOURCE_TYPE_NOT_RENDERABLE");
  const path = join(
    dataRoot(),
    "sources",
    "DRAWING",
    job.source.sha256.slice(0, 2),
    job.source.sha256 + ext,
  );
  if (!existsSync(path))
    throw new Error("SOURCE_UNAVAILABLE: ingest actual bytes first");
  if (sha256(readFileSync(path)) !== job.source.sha256)
    throw new Error("SOURCE_BYTES_SHA_MISMATCH");
  return path;
}
export const imageDirectory = (job: CadJob) =>
  join(dataRoot(), "images", job.source.sha256);
const rendering = new Map<string, Promise<SourceManifest>>();
export async function prepareSource(
  job: CadJob,
  root: string,
  options: unknown,
): Promise<SourceManifest> {
  const previous = rendering.get(job.source.sha256);
  const task = (async () => {
    if (previous) await previous.catch(() => undefined);
    const { stdout } = await run(
      process.env.TRAINAICAD_PYTHON ?? "python3",
      [
        join(root, "services/trainaicad-mcp/bridge/source_bridge.py"),
        sourcePath(job),
        imageDirectory(job),
        JSON.stringify(options),
      ],
      { timeout: 60_000, maxBuffer: 16 * 1024 * 1024 },
    );
    return JSON.parse(stdout) as SourceManifest;
  })();
  rendering.set(job.source.sha256, task);
  try {
    return await task;
  } finally {
    if (rendering.get(job.source.sha256) === task)
      rendering.delete(job.source.sha256);
  }
}
export function readSourceManifest(job: CadJob): SourceManifest {
  return JSON.parse(
    readFileSync(join(imageDirectory(job), "manifest.json"), "utf8"),
  );
}
const receipts = (job: CadJob) => join(dataRoot(), "receipts", job.jobId);
export function sourceImage(job: CadJob, imageId: string) {
  if (!/^[a-f0-9]{64}$/.test(imageId)) throw new Error("INVALID_IMAGE_ID");
  const im = readSourceManifest(job).images.find((x) => x.imageId === imageId);
  if (!im) throw new Error("SOURCE_IMAGE_NOT_FOUND");
  const bytes = readFileSync(join(imageDirectory(job), imageId + ".png"));
  if (sha256(bytes) !== im.sha256) throw new Error("SOURCE_IMAGE_TAMPERED");
  mkdirSync(receipts(job), { recursive: true });
  writeFileSync(
    join(receipts(job), imageId + ".json"),
    JSON.stringify({
      sourceSha256: job.source.sha256,
      imageSha256: im.sha256,
      deliveredAt: new Date().toISOString(),
    }),
  );
  return {
    metadata: { ...im, jobId: job.jobId, sourceSha256: job.source.sha256 },
    bytes,
  };
}
export function deliveredImages(job: CadJob) {
  return readSourceManifest(job).images.filter((im) =>
    existsSync(join(receipts(job), im.imageId + ".json")),
  );
}
