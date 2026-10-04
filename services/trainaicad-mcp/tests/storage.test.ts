import test from "node:test";
import assert from "node:assert/strict";
import {
  mkdtempSync,
  mkdirSync,
  readFileSync,
  writeFileSync,
  existsSync,
} from "node:fs";
import { tmpdir } from "node:os";
import { join, dirname } from "node:path";
import { CheckpointStore, type ObjectStore } from "../src/storage.js";
function remote() {
  const files = new Map<string, Buffer>(),
    puts: string[] = [];
  const store: ObjectStore = {
    get: async (k) => files.get(k) ?? null,
    put: async (k, b) => {
      puts.push(k);
      files.set(k, Buffer.from(b));
    },
  };
  return { store, files, puts };
}
test("cold restart restores exact source, rule, image, job and DXF bytes", async () => {
  const src = mkdtempSync(join(tmpdir(), "cad-store-")),
    dst = mkdtempSync(join(tmpdir(), "cad-restored-")),
    r = remote();
  for (const p of [
    "jobs/cad.json",
    "sources/DRAWING/source.pdf",
    "rules/frozen/core.md",
    "images/view.png",
    "outputs/job/all.dxf",
  ]) {
    mkdirSync(dirname(join(src, p)), { recursive: true });
    writeFileSync(join(src, p), p);
  }
  const writer = new CheckpointStore(src, r.store);
  await writer.checkpoint();
  assert.equal(r.puts.at(-1), "index.json");
  const count = r.puts.length;
  await writer.checkpoint();
  assert.equal(r.puts.length, count);
  await new CheckpointStore(dst, r.store).restore();
  assert.equal(
    readFileSync(join(dst, "sources/DRAWING/source.pdf"), "utf8"),
    "sources/DRAWING/source.pdf",
  );
  assert.equal(
    readFileSync(join(dst, "outputs/job/all.dxf"), "utf8"),
    "outputs/job/all.dxf",
  );
});
test("failed blob upload cannot commit an index referencing missing bytes", async () => {
  const src = mkdtempSync(join(tmpdir(), "cad-failed-store-")),
    r = remote();
  writeFileSync(join(src, "job.json"), "first");
  const writer = new CheckpointStore(src, r.store);
  await writer.checkpoint();
  const before = Buffer.from(r.files.get("index.json")!);
  writeFileSync(join(src, "job.json"), "second");
  r.store.put = async () => {
    throw new Error("offline");
  };
  await assert.rejects(writer.checkpoint(), /offline/);
  assert.deepEqual(r.files.get("index.json"), before);
});
test("restore rejects corrupted blobs and traversal", async () => {
  const dst = mkdtempSync(join(tmpdir(), "cad-corrupt-")),
    r = remote(),
    hash = "a".repeat(64);
  r.files.set(
    "index.json",
    Buffer.from(JSON.stringify({ schema: 1, files: { "job.json": hash } })),
  );
  r.files.set("blobs/" + hash, Buffer.from("bad"));
  await assert.rejects(
    new CheckpointStore(dst, r.store).restore(),
    /HASH_MISMATCH/,
  );
  assert.equal(existsSync(join(dst, "job.json")), false);
  r.files.set(
    "index.json",
    Buffer.from(
      JSON.stringify({ schema: 1, files: { "../escape.json": hash } }),
    ),
  );
  await assert.rejects(
    new CheckpointStore(dst, r.store).restore(),
    /UNSAFE_PATH/,
  );
});
