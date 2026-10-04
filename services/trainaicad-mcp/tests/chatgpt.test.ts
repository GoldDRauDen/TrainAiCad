import test from "node:test";
import assert from "node:assert/strict";
import { generateKeyPair, SignJWT, exportJWK, createLocalJWKSet } from "jose";
import { mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { tmpdir } from "node:os";
import { createServer } from "node:http";
import { once } from "node:events";
import { toNodeHandler } from "@modelcontextprotocol/node";
import { Authentication, authConfig, type AuthConfig } from "../src/auth.js";
import { createApp, MAX_HTTP_BODY } from "../src/app.js";
import { ChatGptFile, ingestChatGptFile } from "../src/chatgpt-file.js";
import { downloadUri, storeSource } from "../src/ingest.js";
process.env.TRAINAICAD_MCP_DATA = mkdtempSync(join(tmpdir(), "cad-chatgpt-"));
const config: AuthConfig = {
  mode: "supabase",
  publicUrl: "https://cad.example.test",
  issuer: "https://project.supabase.co/auth/v1",
  ownerId: "00000000-0000-0000-0000-000000000001",
  clientId: "cad-client",
  publishableKey: "sb_publishable_unit",
  redirects: ["https://chatgpt.com/connector_platform_oauth_redirect"],
};
const keys = await generateKeyPair("ES256"),
  jwk = await exportJWK(keys.publicKey);
jwk.kid = "test";
const auth = new Authentication(config, createLocalJWKSet({ keys: [jwk] }));
const token = (claims: Record<string, any> = {}, key = keys.privateKey) =>
  new SignJWT({
    role: "authenticated",
    client_id: config.clientId,
    scope: "openid",
    trainaicad_access: true,
    is_anonymous: false,
    ...claims,
  })
    .setProtectedHeader({ alg: "ES256", kid: "test" })
    .setIssuer(claims.iss ?? config.issuer!)
    .setSubject(claims.sub ?? config.ownerId!)
    .setAudience(claims.aud ?? config.publicUrl! + "/mcp")
    .setIssuedAt()
    .setExpirationTime(claims.exp ?? "1h")
    .sign(key);

test("OAuth verifies signature, owner, client, audience, issuer, expiry and scope", async () => {
  assert.equal(
    (await auth.authorize("Bearer " + (await token())))?.clientId,
    config.clientId,
  );
  for (const claims of [
    { sub: "someone-else" },
    { client_id: "other-client" },
    { aud: "authenticated" },
    { iss: "https://evil.test" },
    { exp: 1 },
    { scope: "profile" },
    { trainaicad_access: false },
    { role: "service_role" },
    { is_anonymous: true },
  ])
    await assert.rejects(auth.authorize("Bearer " + (await token(claims))));
  await assert.rejects(
    auth.authorize(
      "Bearer " +
        (await token({}, (await generateKeyPair("ES256")).privateKey)),
    ),
  );
  await assert.rejects(auth.authorize(null));
  await assert.rejects(auth.authorize("Bearer opaque"));
});
test("public server fails closed without owner config and rejects leaked service keys", () => {
  assert.throws(
    () =>
      authConfig({
        TRAINAICAD_MCP_HOST: "0.0.0.0",
        TRAINAICAD_AUTH_MODE: "local",
      }),
    /PUBLIC_MCP_AUTH_REQUIRED/,
  );
  const env = {
    TRAINAICAD_AUTH_MODE: "supabase",
    SUPABASE_URL: "https://project.supabase.co",
    TRAINAICAD_PUBLIC_URL: config.publicUrl,
    TRAINAICAD_OWNER_ID: config.ownerId,
    TRAINAICAD_OAUTH_CLIENT_ID: config.clientId,
    SUPABASE_PUBLISHABLE_KEY: config.publishableKey,
    TRAINAICAD_OAUTH_REDIRECT_URIS: config.redirects!.join(","),
  };
  assert.equal(authConfig(env).issuer, config.issuer);
  assert.throws(
    () => authConfig({ ...env, TRAINAICAD_OWNER_ID: "" }),
    /OWNER_AND_CLIENT/,
  );
  assert.throws(
    () => authConfig({ ...env, TRAINAICAD_PUBLIC_URL: "http://cad.test" }),
    /PUBLIC_URL/,
  );
  assert.throws(
    () =>
      authConfig({
        ...env,
        TRAINAICAD_OAUTH_REDIRECT_URIS: "https://evil.test/callback",
      }),
    /REDIRECT/,
  );
  const serviceKey =
    "eyJhbGciOiJIUzI1NiJ9." +
    Buffer.from('{"role":"service_role"}').toString("base64url") +
    ".signature";
  assert.throws(
    () => authConfig({ ...env, SUPABASE_PUBLISHABLE_KEY: serviceKey }),
    /PUBLIC_KEY_MUST_BE_ANON/,
  );
});
test("OAuth discovery and consent pages are public; all CAD requests require a valid owner token", async () => {
  const app = createApp(config, auth);
  try {
    const response = await app.fetch(
      new Request(config.publicUrl + "/mcp", { method: "POST" }),
    );
    assert.equal(response.status, 401);
    assert.match(
      response.headers.get("www-authenticate")!,
      /oauth-protected-resource\/mcp/,
    );
    const metadata = await app.fetch(
      new Request(
        config.publicUrl + "/.well-known/oauth-protected-resource/mcp",
      ),
    );
    assert.equal((await metadata.json()).resource, config.publicUrl + "/mcp");
    const consent = await app.fetch(
      new Request(config.publicUrl + "/oauth/consent"),
    );
    assert.match(
      consent.headers.get("content-security-policy")!,
      /frame-ancestors 'none'/,
    );
    const html = await consent.text();
    assert.ok(html.includes(config.publishableKey!));
    assert.ok(!html.includes("service_role"));
    assert.ok(html.includes("persistSession:false"));
    const script = await app.fetch(
      new Request(config.publicUrl + "/oauth/supabase.js"),
    );
    assert.equal(script.status, 200);
    assert.ok((await script.text()).includes("getAuthorizationDetails"));
    assert.equal(
      (
        await app.fetch(
          new Request(config.publicUrl + "/oauth/consent", { method: "POST" }),
        )
      ).status,
      405,
    );
    const good = await app.fetch(
      new Request(config.publicUrl + "/mcp", {
        method: "POST",
        headers: {
          authorization: "Bearer " + (await token()),
          "content-type": "application/json",
          accept: "application/json, text/event-stream",
        },
        body: JSON.stringify({
          jsonrpc: "2.0",
          id: 1,
          method: "initialize",
          params: {
            protocolVersion: "2025-03-26",
            capabilities: {},
            clientInfo: { name: "test", version: "1" },
          },
        }),
      }),
    );
    assert.equal(good.status, 200);
  } finally {
    await app.close();
  }
});
test("host file object accepts missing optional metadata, infers actual binary kind and hides capability URL", async () => {
  const file = ChatGptFile.parse({
    download_url: "https://files.example.test/private?signature=secret",
    file_id: "file-unit",
  });
  const bytes = Buffer.from("%PDF-1.4\nunit"),
    received = await ingestChatGptFile(file, "DRAWING", async () => bytes);
  assert.equal(received.stored.fileName, "drawing.pdf");
  assert.deepEqual(readFileSync(received.stored.storedPath), bytes);
  assert.ok(!JSON.stringify(received).includes("signature"));
  await assert.rejects(
    ingestChatGptFile(
      { ...file, download_url: "http://files.test/f" },
      "DRAWING",
      async () => bytes,
    ),
    /HTTPS/,
  );
  await assert.rejects(
    ingestChatGptFile(
      { ...file, file_name: "bad.dxf" },
      "DRAWING",
      async () => bytes,
    ),
    /MISMATCH/,
  );
  await assert.rejects(
    ingestChatGptFile(file, "DATA_DXF", async () => bytes),
    /ROLE_KIND_MISMATCH/,
  );
});
test("native file tool advertises the exact four-property ChatGPT schema", async () => {
  const app = createApp({ mode: "local" });
  try {
    const response = await app.fetch(
      new Request("http://localhost/mcp", {
        method: "POST",
        headers: {
          "content-type": "application/json",
          accept: "application/json, text/event-stream",
          "mcp-protocol-version": "2025-03-26",
        },
        body: JSON.stringify({
          jsonrpc: "2.0",
          id: 1,
          method: "tools/list",
          params: {},
        }),
      }),
    );
    const text = await response.text(),
      line = text.split("\n").find((l) => l.startsWith("data:"));
    const tool = JSON.parse(line ? line.slice(5) : text).result.tools.find(
      (t: any) => t.name === "open_chatgpt_cad_job",
    );
    assert.deepEqual(tool._meta["openai/fileParams"], [
      "drawing",
      "dataDxf",
      "referenceDxf",
    ]);
    for (const name of tool._meta["openai/fileParams"]) {
      const schema = tool.inputSchema.properties[name];
      assert.deepEqual(Object.keys(schema.properties).sort(), [
        "download_url",
        "file_id",
        "file_name",
        "mime_type",
      ]);
      assert.deepEqual(schema.required.sort(), ["download_url", "file_id"]);
    }
  } finally {
    await app.close();
  }
});
test("actual Node TCP adapter accepts a body over 4 MiB", async () => {
  const app = createApp({ mode: "bearer", token: "t".repeat(40) }),
    serve = toNodeHandler(app, { maxRequestBodySize: MAX_HTTP_BODY });
  const server = createServer((req, res) => {
    void serve(req, res);
  });
  server.listen(0, "127.0.0.1");
  await once(server, "listening");
  const port = (server.address() as any).port;
  try {
    const bytes = Buffer.concat([
      Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]),
      Buffer.alloc(4 * 1024 * 1024),
    ]);
    const response = await fetch(`http://127.0.0.1:${port}/mcp`, {
      method: "POST",
      headers: {
        authorization: "Bearer " + "t".repeat(40),
        "content-type": "application/json",
        accept: "application/json, text/event-stream",
        "mcp-protocol-version": "2025-03-26",
      },
      body: JSON.stringify({
        jsonrpc: "2.0",
        id: 1,
        method: "tools/call",
        params: {
          name: "ingest_cad_file",
          arguments: { fileName: "large.png", data: bytes.toString("base64") },
        },
      }),
    });
    assert.equal(response.status, 200);
    const text = await response.text(),
      packet = JSON.parse(
        text
          .split("\n")
          .find((l) => l.startsWith("data:"))!
          .slice(5),
      );
    assert.equal(packet.result.isError, undefined);
    assert.equal(JSON.parse(packet.result.content[0].text).bytes, bytes.length);
  } finally {
    await app.close();
    server.closeAllConnections();
    await new Promise<void>((resolve) => server.close(() => resolve()));
  }
});
test("downloads reject private mapped IPv6, credential URLs and redirects to private addresses", async () => {
  for (const url of [
    "http://[::ffff:127.0.0.1]/source.pdf",
    "http://[::ffff:7f00:1]/source.pdf",
    "http://[::1]/source.pdf",
  ])
    await assert.rejects(downloadUri(url), /PRIVATE_ADDRESS/);
  await assert.rejects(
    downloadUri("https://user:password@example.test/f"),
    /CREDENTIALS/,
  );
});
test("content-addressed ingest rejects previously tampered source bytes", () => {
  const bytes = Buffer.from("%PDF-1.4\nunique-tamper-unit");
  const first = storeSource({ fileName: "source.pdf", bytes }, "DRAWING");
  writeFileSync(first.storedPath, "corrupted");
  assert.throws(
    () => storeSource({ fileName: "source.pdf", bytes }, "DRAWING"),
    /HASH_MISMATCH/,
  );
});

test("bootstrap discovery never opens CAD access before OAuth setup is complete", async () => {
  const setup = authConfig({
    TRAINAICAD_MCP_HOST: "0.0.0.0",
    TRAINAICAD_AUTH_MODE: "setup",
    SUPABASE_URL: "https://project.supabase.co",
    TRAINAICAD_PUBLIC_URL: "https://cad.example.test",
  });
  const app = createApp(setup);
  try {
    assert.equal(
      (
        await app.fetch(
          new Request(
            "https://cad.example.test/.well-known/oauth-protected-resource/mcp",
          ),
        )
      ).status,
      200,
    );
    assert.equal(
      (
        await app.fetch(
          new Request("https://cad.example.test/mcp", {
            method: "POST",
            headers: { authorization: "Bearer anything" },
          }),
        )
      ).status,
      401,
    );
    assert.equal(
      (await app.fetch(new Request("https://cad.example.test/oauth/consent")))
        .status,
      503,
    );
  } finally {
    await app.close();
  }
});
