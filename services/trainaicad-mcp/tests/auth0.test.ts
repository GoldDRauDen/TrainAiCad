import test from "node:test";
import assert from "node:assert/strict";
import {
  createLocalJWKSet,
  exportJWK,
  generateKeyPair,
  SignJWT,
} from "jose";
import { Authentication, authConfig, type AuthConfig } from "../src/auth.js";
import { createApp } from "../src/app.js";

const config: AuthConfig = {
  mode: "auth0",
  publicUrl: "https://cad.example.test",
  issuer: "https://tenant.example.auth0.com/",
  audience: "https://cad.example.test/mcp",
  ownerSub: "auth0|owner-unit",
};

const keys = await generateKeyPair("RS256"),
  jwk = await exportJWK(keys.publicKey);
jwk.kid = "auth0-unit";
const auth = new Authentication(config, createLocalJWKSet({ keys: [jwk] }));
const token = (claims: Record<string, any> = {}) =>
  new SignJWT({ scope: "openid email offline_access", azp: "chatgpt-unit", ...claims })
    .setProtectedHeader({ alg: "RS256", kid: "auth0-unit" })
    .setIssuer(claims.iss ?? config.issuer!)
    .setSubject(claims.sub ?? config.ownerSub!)
    .setAudience(claims.aud ?? config.audience!)
    .setIssuedAt()
    .setExpirationTime(claims.exp ?? "1h")
    .sign(keys.privateKey);

test("auth0 config validates canonical issuer, audience and owner", () => {
  const env = {
    TRAINAICAD_AUTH_MODE: "auth0",
    TRAINAICAD_PUBLIC_URL: config.publicUrl,
    TRAINAICAD_AUTH0_ISSUER: config.issuer,
    TRAINAICAD_AUTH0_AUDIENCE: config.audience,
    TRAINAICAD_AUTH0_OWNER_SUB: config.ownerSub,
  };
  assert.deepEqual(authConfig(env), config);
  assert.throws(
    () => authConfig({ ...env, TRAINAICAD_AUTH0_AUDIENCE: "https://wrong.test/mcp" }),
    /AUTH0_AUDIENCE_INVALID/,
  );
  assert.throws(
    () => authConfig({ ...env, TRAINAICAD_AUTH0_OWNER_SUB: "" }),
    /AUTH0_OWNER_SUB_REQUIRED/,
  );
  assert.throws(
    () => authConfig({ ...env, TRAINAICAD_AUTH0_ISSUER: "http://tenant.test/" }),
    /AUTH0_ISSUER_INVALID/,
  );
});

test("auth0 verifies RS256 issuer audience expiry and owner sub", async () => {
  const info = await auth.authorize("Bearer " + (await token()));
  assert.equal(info?.clientId, "chatgpt-unit");
  assert.equal(info?.extra?.ownerId, config.ownerSub);
  for (const claims of [
    { sub: "auth0|other" },
    { aud: "https://wrong.test/mcp" },
    { iss: "https://wrong.example/" },
    { exp: 1 },
  ])
    await assert.rejects(auth.authorize("Bearer " + (await token(claims))));
  await assert.rejects(auth.authorize(null));
});

test("auth0 discovery advertises Auth0 and does not expose Supabase consent", async () => {
  const app = createApp(config, auth);
  try {
    const metadata = await app.fetch(
      new Request(
        config.publicUrl + "/.well-known/oauth-protected-resource/mcp",
      ),
    );
    assert.equal(metadata.status, 200);
    assert.deepEqual(await metadata.json(), {
      resource: config.publicUrl + "/mcp",
      authorization_servers: [config.issuer],
      scopes_supported: ["openid", "email", "offline_access"],
      bearer_methods_supported: ["header"],
    });
    assert.equal(
      (await app.fetch(new Request(config.publicUrl + "/oauth/consent"))).status,
      404,
    );
    const denied = await app.fetch(
      new Request(config.publicUrl + "/mcp", { method: "POST" }),
    );
    assert.equal(denied.status, 401);
    assert.match(
      denied.headers.get("www-authenticate")!,
      /oauth-protected-resource\/mcp/,
    );
  } finally {
    await app.close();
  }
});
