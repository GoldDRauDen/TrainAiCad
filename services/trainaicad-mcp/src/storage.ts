/** Single-owner private checkpoints, one process/writer per namespace. */
import {
  mkdirSync,
  readdirSync,
  readFileSync,
  renameSync,
  writeFileSync,
  statSync,
} from "node:fs";
import { dirname, join } from "node:path";
import { dataRoot } from "./ingest.js";
import { sha256 } from "./source.js";
type Index = { schema: 1; files: Record<string, string> };
export interface ObjectStore {
  get(key: string): Promise<Buffer | null>;
  put(key: string, bytes: Buffer): Promise<void>;
}
function safe(path: string) {
  if (
    !/^[A-Za-z0-9_./-]+$/.test(path) ||
    path.startsWith("/") ||
    path.split("/").some((p) => !p || p === "." || p === "..")
  )
    throw new Error("STORAGE_UNSAFE_PATH");
}
export class CheckpointStore {
  private known: Index = { schema: 1, files: {} };
  private queue: Promise<void> = Promise.resolve();
  private stamps = new Map<string, { stamp: string; hash: string }>();
  constructor(
    private root: string,
    private remote: ObjectStore,
  ) {}
  async restore() {
    const bytes = await this.remote.get("index.json");
    if (!bytes) return;
    const index = JSON.parse(bytes.toString()) as Index;
    if (index.schema !== 1 || !index.files || typeof index.files !== "object")
      throw new Error("STORAGE_INDEX_INVALID");
    for (const [path, hash] of Object.entries(index.files)) {
      safe(path);
      if (!/^[a-f0-9]{64}$/.test(hash)) throw new Error("STORAGE_HASH_INVALID");
      const data = await this.remote.get(`blobs/${hash}`);
      if (!data || sha256(data) !== hash)
        throw new Error("STORAGE_RESTORE_HASH_MISMATCH");
      const dest = join(this.root, path);
      mkdirSync(dirname(dest), { recursive: true });
      writeFileSync(dest + ".tmp", data);
      renameSync(dest + ".tmp", dest);
      const stat = statSync(dest, { bigint: true });
      this.stamps.set(path, { stamp: `${stat.mtimeNs}:${stat.size}`, hash });
    }
    this.known = index;
  }
  checkpoint() {
    const task = this.queue
      .catch(() => undefined)
      .then(async () => {
        const index: Index = { schema: 1, files: {} },
          changed: { hash: string; data: Buffer }[] = [];
        const walk = (dir: string, prefix = "") => {
          for (const ent of readdirSync(dir, { withFileTypes: true })) {
            if (ent.name.endsWith(".tmp") || ent.name === "__pycache__")
              continue;
            const path = prefix + ent.name;
            safe(path);
            if (ent.isDirectory()) walk(join(dir, ent.name), path + "/");
            else if (ent.isFile()) {
              const file = join(dir, ent.name),
                stat = statSync(file, { bigint: true }),
                stamp = `${stat.mtimeNs}:${stat.size}`,
                old = this.stamps.get(path);
              if (old?.stamp === stamp && this.known.files[path] === old.hash)
                index.files[path] = old.hash;
              else {
                const data = readFileSync(file),
                  hash = sha256(data);
                index.files[path] = hash;
                this.stamps.set(path, { stamp, hash });
                if (this.known.files[path] !== hash)
                  changed.push({ hash, data });
              }
            }
          }
        };
        mkdirSync(this.root, { recursive: true });
        walk(this.root);
        const sent = new Set<string>();
        for (const f of changed)
          if (!sent.has(f.hash)) {
            await this.remote.put(`blobs/${f.hash}`, f.data);
            sent.add(f.hash);
          }
        if (JSON.stringify(index.files) !== JSON.stringify(this.known.files))
          await this.remote.put(
            "index.json",
            Buffer.from(JSON.stringify(index)),
          );
        this.known = index;
      });
    this.queue = task;
    return task;
  }
}
function supabaseStore(): ObjectStore | null {
  const base = process.env.SUPABASE_URL,
    key = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!base && !key) return null;
  if (!base || !key) throw new Error("STORAGE_CONFIG_INCOMPLETE");
  const url = new URL(base);
  if (
    url.protocol !== "https:" ||
    !url.hostname.endsWith(".supabase.co") ||
    url.pathname !== "/" ||
    url.search ||
    url.username ||
    url.password
  )
    throw new Error("STORAGE_URL_INVALID");
  const bucket = process.env.TRAINAICAD_STORAGE_BUCKET ?? "trainaicad-private",
    namespace = process.env.TRAINAICAD_STORAGE_NAMESPACE ?? "research-owner";
  if (!/^[A-Za-z0-9_-]+$/.test(bucket) || !/^[A-Za-z0-9_-]+$/.test(namespace))
    throw new Error("STORAGE_NAMESPACE_INVALID");
  const request = async (
    path: string,
    method: "GET" | "POST",
    bytes?: Buffer,
  ) => {
    safe(path);
    const res = await fetch(
      `${url.origin}/storage/v1/object/${bucket}/${namespace}/${path}`,
      {
        method,
        headers: {
          authorization: `Bearer ${key}`,
          apikey: key,
          "content-type": "application/octet-stream",
          "x-upsert": "true",
        },
        body: bytes ? new Uint8Array(bytes) : undefined,
        signal: AbortSignal.timeout(20_000),
        redirect: "error",
      },
    );
    if (!res.ok) {
      if (method === "GET" && res.status === 404) return null;
      if (method === "GET" && res.status === 400) {
        const body = await res.json().catch(() => null);
        if (String(body?.statusCode) === "404") return null;
      }
      throw new Error(`STORAGE_REQUEST_FAILED:${method}:${res.status}`);
    }
    return Buffer.from(await res.arrayBuffer());
  };
  return {
    get: (path) => request(path, "GET"),
    put: async (path, bytes) => {
      await request(path, "POST", bytes);
    },
  };
}
let durable: CheckpointStore | null = null;
export async function initializeStorage() {
  const remote = supabaseStore();
  if (!remote) {
    if (process.env.TRAINAICAD_REQUIRE_DURABLE === "1")
      throw new Error("DURABLE_STORAGE_REQUIRED");
    return;
  }
  durable = new CheckpointStore(dataRoot(), remote);
  await durable.restore();
}
export async function checkpoint() {
  if (durable) await durable.checkpoint();
}
