/** Read-only live deployment checks. Never prints tokens or signed source URLs. */
const [raw] = process.argv.slice(2);
if (!raw)
  throw new Error("usage: npm run check:remote -- https://YOUR.onrender.com");
const base = new URL(raw);
if (
  base.protocol !== "https:" ||
  base.pathname !== "/" ||
  base.search ||
  base.hash
)
  throw new Error("Provide an HTTPS origin");
const request = async (path: string, init?: RequestInit) =>
  fetch(new URL(path, base), {
    ...init,
    redirect: "error",
    signal: AbortSignal.timeout(15000),
  });
const health = await request("/health");
if (health.status !== 200 || (await health.text()) !== "ok")
  throw new Error("HEALTH_FAILED");
const meta = await request("/.well-known/oauth-protected-resource/mcp");
if (meta.status !== 200) throw new Error("PROTECTED_RESOURCE_METADATA_FAILED");
const info = await meta.json();
if (
  info.resource !== base.origin + "/mcp" ||
  info.authorization_servers.length !== 1
)
  throw new Error("RESOURCE_AUDIENCE_MISMATCH");
const issuer = new URL(info.authorization_servers[0]);
if (
  issuer.protocol !== "https:" ||
  !issuer.hostname.endsWith(".supabase.co") ||
  issuer.pathname !== "/auth/v1"
)
  throw new Error("ISSUER_INVALID");
const discovery = await fetch(
  `${issuer.origin}/.well-known/oauth-authorization-server/auth/v1`,
  { redirect: "error", signal: AbortSignal.timeout(15000) },
);
if (discovery.status !== 200) throw new Error("SUPABASE_OAUTH_NOT_ENABLED");
const oauth = await discovery.json();
if (
  oauth.issuer !== issuer.href ||
  !oauth.code_challenge_methods_supported?.includes("S256")
)
  throw new Error("OAUTH_DISCOVERY_OR_PKCE_FAILED");
const denied = await request("/mcp", {
  method: "POST",
  headers: {
    "content-type": "application/json",
    accept: "application/json, text/event-stream",
  },
  body: "{}",
});
if (
  denied.status !== 401 ||
  !denied.headers.get("www-authenticate")?.includes("resource_metadata")
)
  throw new Error("UNAUTHENTICATED_ACCESS_OR_CHALLENGE_FAILED");
const jwks = await fetch(`${issuer.href}/.well-known/jwks.json`, {
  redirect: "error",
  signal: AbortSignal.timeout(15000),
});
const keys = await jwks.json();
if (!keys.keys?.some((k: any) => k.kty === "EC" || k.kty === "RSA"))
  throw new Error("ASYMMETRIC_SIGNING_KEY_REQUIRED");
const page = await request("/oauth/consent");
if (page.status !== 200 || !page.headers.get("content-security-policy"))
  throw new Error("CONSENT_PAGE_FAILED");
console.log(
  "PASS: health, OAuth metadata/PKCE/JWKS, auth gate, consent page. Still test owner login + actual ChatGPT file delivery/download in the host.",
);
export {};
