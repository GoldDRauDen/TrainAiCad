import { createHmac, timingSafeEqual } from "node:crypto";
import { readFileSync } from "node:fs";
import { sha256 } from "./source.js";
import type { CadJob } from "./model.js";
function key() {
  const key = process.env.TRAINAICAD_ARTIFACT_SECRET;
  if (!key || key.length < 32)
    throw new Error("ARTIFACT_SIGNING_SECRET_REQUIRED");
  return key;
}
const sign = (id: string, expires: string, hash: string) =>
  createHmac("sha256", key())
    .update(`${id}\n${expires}\n${hash}`)
    .digest("hex");
export function artifact(job: CadJob) {
  if (!job.dxfOutput || !["DXF_WRITTEN", "QA_COMPLETE"].includes(job.state))
    throw new Error("DXF_ARTIFACT_NOT_READY");
  const bytes = readFileSync(job.dxfOutput.absolutePath),
    hash = sha256(bytes);
  if (hash !== job.dxfOutput.sha256)
    throw new Error("DXF_ARTIFACT_CONTENT_CHANGED");
  let url: string | null = null;
  const base = process.env.TRAINAICAD_PUBLIC_URL;
  if (base) {
    const expires = String(Math.floor(Date.now() / 1000) + 600);
    url =
      new URL(`/artifacts/${job.jobId}.dxf`, base).toString() +
      `?expires=${expires}&sha256=${hash}&signature=${sign(job.jobId, expires, hash)}`;
  }
  return { fileName: job.dxfOutput.fileName, sha256: hash, bytes, url };
}
export function downloadArtifact(job: CadJob, url: URL) {
  const exp = url.searchParams.get("expires") ?? "",
    hash = url.searchParams.get("sha256") ?? "",
    sig = url.searchParams.get("signature") ?? "",
    now = Math.floor(Date.now() / 1000);
  if (
    !/^\d+$/.test(exp) ||
    Number(exp) < now ||
    Number(exp) > now + 600 ||
    !/^[a-f0-9]{64}$/.test(hash) ||
    !/^[a-f0-9]{64}$/.test(sig)
  )
    throw new Error("ARTIFACT_LINK_INVALID_OR_EXPIRED");
  if (
    !timingSafeEqual(
      Buffer.from(sig, "hex"),
      Buffer.from(sign(job.jobId, exp, hash), "hex"),
    )
  )
    throw new Error("ARTIFACT_SIGNATURE_INVALID");
  const file = artifact(job);
  if (file.sha256 !== hash) throw new Error("ARTIFACT_CONTENT_CHANGED");
  return file;
}
