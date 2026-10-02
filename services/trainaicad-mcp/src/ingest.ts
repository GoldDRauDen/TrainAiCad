import { createHash } from "node:crypto";
import { lookup } from "node:dns/promises";
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { isIP, BlockList } from "node:net";
import { request as httpRequest } from "node:http";
import { request as httpsRequest } from "node:https";
import { dirname, extname, join } from "node:path";
import { fileURLToPath } from "node:url";

export type SourceKind = "PDF" | "IMAGE" | "DXF";
export type SourceRole = "DRAWING" | "DATA_DXF" | "REFERENCE_DXF" | "AI_DXF";

const PACKAGE_ROOT = dirname(dirname(fileURLToPath(import.meta.url)));

/** Local data root (jobs + immutable sources). Override with TRAINAICAD_MCP_DATA. */
export function dataRoot(): string {
  return process.env.TRAINAICAD_MCP_DATA ?? join(PACKAGE_ROOT, "data");
}

export function maxSourceBytes(): number {
  const raw = Number.parseInt(
    process.env.TRAINAICAD_MAX_SOURCE_BYTES ?? "",
    10,
  );
  return Number.isInteger(raw) && raw > 0 ? raw : 25 * 1024 * 1024;
}

const ALLOWED_EXT: Record<string, SourceKind> = {
  ".pdf": "PDF",
  ".png": "IMAGE",
  ".jpg": "IMAGE",
  ".jpeg": "IMAGE",
  ".tif": "IMAGE",
  ".tiff": "IMAGE",
  ".bmp": "IMAGE",
  ".webp": "IMAGE",
  ".dxf": "DXF",
};

const KIND_MIME: Record<SourceKind, readonly string[]> = {
  PDF: ["application/pdf"],
  IMAGE: ["image/png", "image/jpeg", "image/tiff", "image/bmp", "image/webp"],
  DXF: [
    "image/vnd.dxf",
    "application/dxf",
    "application/x-dxf",
    "application/octet-stream",
  ],
};

/** Strip any path, control/illegal characters and reserved leading dots. */
export function sanitizeFileName(raw: string): string {
  const base = raw.split(/[\\/]/).pop() ?? "";
  const cleaned = base
    .replace(/[\u0000-\u001f\u007f<>:"|?*]/g, "")
    .replace(/^[.\s]+/, "")
    .trim()
    .slice(0, 120);
  if (
    !cleaned ||
    !/^[\p{L}\p{N} ._()-]+$/u.test(cleaned) ||
    cleaned.includes("..")
  ) {
    throw new Error(`INVALID_FILE_NAME: ${JSON.stringify(raw)}`);
  }
  const ext = extname(cleaned).toLowerCase();
  if (!ALLOWED_EXT[ext])
    throw new Error(`UNSUPPORTED_FILE_TYPE: ${ext || "(none)"}`);
  return cleaned;
}

function startsWith(bytes: Uint8Array, sig: number[], at = 0): boolean {
  if (bytes.length < at + sig.length) return false;
  return sig.every((b, i) => bytes[at + i] === b);
}

function ascii(bytes: Uint8Array, from = 0, to = bytes.length): string {
  return Buffer.from(bytes.subarray(from, to)).toString("latin1");
}

/** Magic-byte sniffing; declared MIME never decides the kind. */
export function sniffKind(bytes: Uint8Array): SourceKind | null {
  if (startsWith(bytes, [0x25, 0x50, 0x44, 0x46, 0x2d])) return "PDF";
  if (startsWith(bytes, [0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]))
    return "IMAGE";
  if (startsWith(bytes, [0xff, 0xd8, 0xff])) return "IMAGE";
  if (ascii(bytes, 0, 4) === "II*\u0000" || ascii(bytes, 0, 4) === "MM\u0000*")
    return "IMAGE";
  if (ascii(bytes, 0, 2) === "BM") return "IMAGE";
  if (ascii(bytes, 0, 4) === "RIFF" && ascii(bytes, 8, 12) === "WEBP")
    return "IMAGE";
  if (ascii(bytes, 0, 17) === "AutoCAD Binary DXF") return "DXF";

  const head = ascii(bytes, 0, Math.min(bytes.length, 2048)).replace(
    /^\uFEFF/,
    "",
  );
  if (
    /^\s*(0|999)\s*\r?\n/.test(head) &&
    /(SECTION|ENDSEC|ENTITIES|HEADER|TABLES)/.test(head)
  ) {
    return "DXF";
  }
  return null;
}

export type IngestResult = {
  kind: SourceKind;
  bytes: number;
  fileName: string;
  mimeType: string;
  sha256: string;
  storedPath: string;
};

/**
 * Validate bytes, hash them and store immutably under data/sources/<role>/.
 * Same content is idempotent; content is never rewritten.
 */
export function storeSource(
  raw: { fileName: string; bytes: Buffer; mimeType?: string },
  role: SourceRole,
): IngestResult {
  const fileName = sanitizeFileName(raw.fileName);
  if (raw.bytes.length === 0) throw new Error("EMPTY_SOURCE_FILE");
  if (raw.bytes.length > maxSourceBytes()) {
    throw new Error(
      `SOURCE_TOO_LARGE: ${raw.bytes.length} > ${maxSourceBytes()}`,
    );
  }

  const kind = sniffKind(raw.bytes);
  if (!kind) throw new Error("UNKNOWN_FILE_SIGNATURE");

  const ext = extname(fileName).toLowerCase();
  if (ALLOWED_EXT[ext] !== kind)
    throw new Error(`EXTENSION_SIGNATURE_MISMATCH: ${ext} is not ${kind}`);
  if (role !== "DRAWING" && kind !== "DXF") {
    throw new Error(`ROLE_KIND_MISMATCH: ${role} requires DXF`);
  }

  const declared = raw.mimeType?.split(";")[0]?.trim().toLowerCase();
  if (
    declared &&
    declared !== "application/octet-stream" &&
    !KIND_MIME[kind].includes(declared)
  ) {
    throw new Error(
      `MIME_SIGNATURE_MISMATCH: declared ${declared}, signature ${kind}`,
    );
  }

  const sha256 = createHash("sha256").update(raw.bytes).digest("hex");
  const dir = join(dataRoot(), "sources", role, sha256.slice(0, 2));
  const storedPath = join(dir, `${sha256}${ext}`);
  mkdirSync(dir, { recursive: true });
  try {
    writeFileSync(storedPath, raw.bytes, { flag: "wx" });
  } catch (error) {
    const code = (error as NodeJS.ErrnoException).code;
    if (code !== "EEXIST") throw error;
    if (!existsSync(storedPath)) throw error;
    if (
      createHash("sha256").update(readFileSync(storedPath)).digest("hex") !==
      sha256
    )
      throw new Error("STORED_SOURCE_HASH_MISMATCH");
  }

  return {
    kind,
    bytes: raw.bytes.length,
    fileName,
    mimeType: KIND_MIME[kind][0] ?? declared ?? "application/octet-stream",
    sha256,
    storedPath,
  };
}

const blocked = new BlockList();
for (const [address, prefix] of [
  ["0.0.0.0", 8],
  ["10.0.0.0", 8],
  ["127.0.0.0", 8],
  ["169.254.0.0", 16],
  ["172.16.0.0", 12],
  ["192.168.0.0", 16],
  ["100.64.0.0", 10],
  ["224.0.0.0", 4],
  ["240.0.0.0", 4],
] as const)
  blocked.addSubnet(address, prefix, "ipv4");
for (const [address, prefix] of [
  ["::", 128],
  ["::1", 128],
  ["fc00::", 7],
  ["fe80::", 10],
  ["ff00::", 8],
] as const)
  blocked.addSubnet(address, prefix, "ipv6");
async function resolvedHost(hostname: string, allowPrivate: boolean) {
  const host = hostname.replace(/^\[|\]$/g, "");
  const addresses = isIP(host)
    ? [{ address: host, family: isIP(host) }]
    : await lookup(host, { all: true });
  if (!addresses.length) throw new Error("DNS_FAILED");
  if (
    !allowPrivate &&
    addresses.some((r) =>
      blocked.check(r.address, r.family === 6 ? "ipv6" : "ipv4"),
    )
  )
    throw new Error("PRIVATE_ADDRESS_BLOCKED");
  return addresses[0]!;
}

export type DownloadOptions = {
  allowPrivate?: boolean;
  maxRedirects?: number;
  timeoutMs?: number;
};

/** SSRF-guarded fetch: http(s) only, bounded redirects, bounded size and time. */
export async function downloadUri(
  uri: string,
  options: DownloadOptions = {},
): Promise<Buffer> {
  const allowPrivate =
    options.allowPrivate ?? process.env.TRAINAICAD_ALLOW_PRIVATE_URL === "1";
  const redirects = options.maxRedirects ?? 3,
    timeout = options.timeoutMs ?? 15000,
    limit = maxSourceBytes();
  let current = uri;
  const deadline = Date.now() + timeout;
  for (let hop = 0; hop <= redirects; hop++) {
    const url = new URL(current);
    if (!["http:", "https:"].includes(url.protocol))
      throw new Error(`UNSUPPORTED_URI_SCHEME: ${url.protocol}`);
    if (url.username || url.password)
      throw new Error("URL_CREDENTIALS_FORBIDDEN");
    const address = await resolvedHost(url.hostname, allowPrivate);
    const remaining = deadline - Date.now();
    if (remaining <= 0) throw new Error("DOWNLOAD_TIMEOUT");
    const result = await new Promise<{ bytes?: Buffer; redirect?: string }>(
      (resolve, reject) => {
        const request = url.protocol === "https:" ? httpsRequest : httpRequest;
        // Connect to the already-validated address; DNS cannot change between validation and use.
        const req = request(
          url,
          {
            method: "GET",
            agent: false,
            family: address.family,
            lookup: ((
              _host: unknown,
              _opts: unknown,
              cb: (error: null, address: string, family: number) => void,
            ) => cb(null, address.address, address.family)) as any,
            headers: { accept: "application/pdf,image/*,application/dxf,*/*" },
          },
          async (res) => {
            if (
              res.statusCode &&
              res.statusCode >= 300 &&
              res.statusCode < 400
            ) {
              const location = res.headers.location;
              res.destroy();
              if (!location) reject(new Error("REDIRECT_WITHOUT_LOCATION"));
              else resolve({ redirect: new URL(location, url).toString() });
              return;
            }
            if (
              !res.statusCode ||
              res.statusCode < 200 ||
              res.statusCode >= 300
            ) {
              res.destroy();
              reject(new Error(`DOWNLOAD_FAILED:${res.statusCode}`));
              return;
            }
            if (Number(res.headers["content-length"]) > limit) {
              res.destroy();
              reject(new Error("SOURCE_TOO_LARGE"));
              return;
            }
            const chunks: Buffer[] = [];
            let total = 0;
            try {
              for await (const chunk of res) {
                total += chunk.length;
                if (total > limit) throw new Error("SOURCE_TOO_LARGE");
                chunks.push(Buffer.from(chunk));
              }
              resolve({ bytes: Buffer.concat(chunks) });
            } catch (e) {
              res.destroy();
              reject(e);
            }
          },
        );
        const timer = setTimeout(
          () => req.destroy(new Error("DOWNLOAD_TIMEOUT")),
          remaining,
        );
        req.on("error", reject);
        req.on("close", () => clearTimeout(timer));
        req.end();
      },
    );
    if (result.bytes) return result.bytes;
    const next = new URL(result.redirect!);
    if (url.protocol === "https:" && next.protocol !== "https:")
      throw new Error("DOWNLOAD_TLS_DOWNGRADE_BLOCKED");
    current = next.toString();
  }
  throw new Error("TOO_MANY_REDIRECTS");
}

/** Bind an ingested source to a job, immutably, per role. */
export function bindSourceToJob(
  jobId: string,
  role: SourceRole,
  source: IngestResult,
): Record<string, IngestResult> {
  if (!/^cad_[a-f0-9]{16}$/.test(jobId))
    throw new Error(`INVALID_JOB_ID: ${jobId}`);
  const dir = join(dataRoot(), "jobs");
  const file = join(dir, `${jobId}.sources.json`);
  if (!existsSync(join(dir, `${jobId}.json`)))
    throw new Error(`JOB_NOT_FOUND: ${jobId}`);
  mkdirSync(dir, { recursive: true });
  const current: Record<string, IngestResult> = existsSync(file)
    ? (JSON.parse(readFileSync(file, "utf8")) as Record<string, IngestResult>)
    : {};
  const bound = current[role];
  if (bound && bound.sha256 !== source.sha256) {
    throw new Error(`SOURCE_ALREADY_BOUND: ${role} is immutable for ${jobId}`);
  }
  current[role] = source;
  writeFileSync(file, JSON.stringify(current, null, 2));
  return current;
}
