import { createRemoteJWKSet, jwtVerify, type JWTVerifyGetKey } from "jose";
import { createHash, timingSafeEqual } from "node:crypto";
import type { AuthInfo } from "@modelcontextprotocol/server";

export type AuthConfig = {
  mode: "local" | "bearer" | "supabase" | "setup" | "auth0";
  publicUrl?: string;
  token?: string;
  issuer?: string;
  audience?: string;
  ownerSub?: string;
  publishableKey?: string;
  ownerId?: string;
  clientId?: string;
  redirects?: string[];
};

function publicOrigin(env: NodeJS.ProcessEnv) {
  const publicUrl = new URL(env.TRAINAICAD_PUBLIC_URL ?? "invalid:");
  if (
    publicUrl.protocol !== "https:" ||
    publicUrl.pathname !== "/" ||
    publicUrl.search ||
    publicUrl.hash ||
    publicUrl.username ||
    publicUrl.password
  )
    throw new Error("AUTH_PUBLIC_URL_INVALID");
  return publicUrl.origin;
}

export function authConfig(env = process.env): AuthConfig {
  const publicBind = (env.TRAINAICAD_MCP_HOST ?? "127.0.0.1") !== "127.0.0.1";
  const mode = env.TRAINAICAD_AUTH_MODE ?? (publicBind ? "bearer" : "local");
  if (!["local", "bearer", "supabase", "setup", "auth0"].includes(mode))
    throw new Error("AUTH_MODE_INVALID");
  if (mode === "local") {
    if (publicBind) throw new Error("PUBLIC_MCP_AUTH_REQUIRED");
    return { mode, token: env.TRAINAICAD_MCP_AUTH_TOKEN };
  }
  if (mode === "bearer") {
    const token = env.TRAINAICAD_MCP_AUTH_TOKEN;
    if (!token || token.length < 32)
      throw new Error("PUBLIC_MCP_AUTH_REQUIRED");
    return { mode, token };
  }

  const publicUrl = publicOrigin(env);

  if (mode === "auth0") {
    const rawIssuer = new URL(env.TRAINAICAD_AUTH0_ISSUER ?? "invalid:");
    if (
      rawIssuer.protocol !== "https:" ||
      rawIssuer.pathname !== "/" ||
      rawIssuer.search ||
      rawIssuer.hash ||
      rawIssuer.username ||
      rawIssuer.password
    )
      throw new Error("AUTH0_ISSUER_INVALID");
    const issuer = rawIssuer.origin + "/",
      audience = env.TRAINAICAD_AUTH0_AUDIENCE,
      ownerSub = env.TRAINAICAD_AUTH0_OWNER_SUB;
    if (audience !== publicUrl + "/mcp")
      throw new Error("AUTH0_AUDIENCE_INVALID");
    if (!ownerSub || !/^[^\s]{1,256}$/.test(ownerSub))
      throw new Error("AUTH0_OWNER_SUB_REQUIRED");
    return { mode, publicUrl, issuer, audience, ownerSub };
  }

  const project = new URL(env.SUPABASE_URL ?? "invalid:");
  if (
    project.protocol !== "https:" ||
    !project.hostname.endsWith(".supabase.co") ||
    project.pathname !== "/" ||
    project.search ||
    project.hash ||
    project.username ||
    project.password
  )
    throw new Error("AUTH_SUPABASE_URL_INVALID");
  // Bootstrap only exposes discovery so the owner can obtain the exact host callback.
  if (mode === "setup")
    return {
      mode,
      publicUrl,
      issuer: project.origin + "/auth/v1",
    };
  const ownerId = env.TRAINAICAD_OWNER_ID,
    clientId = env.TRAINAICAD_OAUTH_CLIENT_ID;
  if (
    !ownerId ||
    !/^[a-f0-9-]{36}$/i.test(ownerId) ||
    !clientId ||
    !/^[a-zA-Z0-9_-]{8,128}$/.test(clientId)
  )
    throw new Error("AUTH_OWNER_AND_CLIENT_REQUIRED");
  const publishableKey = env.SUPABASE_PUBLISHABLE_KEY;
  if (
    !publishableKey ||
    (!publishableKey.startsWith("sb_publishable_") &&
      !publishableKey.startsWith("eyJ"))
  )
    throw new Error("AUTH_PUBLISHABLE_KEY_REQUIRED");
  // Refuse legacy service-role JWTs in the public page, even if misconfigured.
  if (publishableKey.startsWith("eyJ")) {
    const claims = JSON.parse(
      Buffer.from(publishableKey.split(".")[1] ?? "", "base64url").toString(),
    );
    if (claims.role !== "anon") throw new Error("AUTH_PUBLIC_KEY_MUST_BE_ANON");
  }
  const redirects = (env.TRAINAICAD_OAUTH_REDIRECT_URIS ?? "")
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
  if (
    !redirects.length ||
    redirects.some((uri) => {
      const u = new URL(uri);
      return (
        u.protocol !== "https:" ||
        u.username ||
        u.password ||
        u.hash ||
        u.search ||
        !["chatgpt.com", "chat.openai.com"].includes(u.hostname)
      );
    })
  )
    throw new Error("AUTH_EXACT_CHATGPT_REDIRECT_REQUIRED");
  return {
    mode: "supabase",
    publicUrl,
    issuer: project.origin + "/auth/v1",
    publishableKey,
    ownerId,
    clientId,
    redirects,
  };
}

const digest = (s: string) => createHash("sha256").update(s).digest();
export class Authentication {
  private keys?: JWTVerifyGetKey;
  constructor(
    readonly config: AuthConfig,
    keys?: JWTVerifyGetKey,
  ) {
    if (config.mode === "supabase")
      this.keys =
        keys ??
        createRemoteJWKSet(new URL(config.issuer + "/.well-known/jwks.json"), {
          timeoutDuration: 5000,
        });
    if (config.mode === "auth0")
      this.keys =
        keys ??
        createRemoteJWKSet(new URL(config.issuer + ".well-known/jwks.json"), {
          timeoutDuration: 5000,
        });
  }
  metadata() {
    return {
      resource: this.config.publicUrl + "/mcp",
      authorization_servers: [this.config.issuer],
      scopes_supported:
        this.config.mode === "auth0"
          ? ["openid", "email", "offline_access"]
          : ["openid"],
      bearer_methods_supported: ["header"],
    };
  }
  async authorize(header: string | null): Promise<AuthInfo | null> {
    const cfg = this.config;
    if (cfg.mode === "setup") throw new Error("OAUTH_SETUP_NOT_COMPLETE");
    if (cfg.mode === "local" && !cfg.token) return null;
    if (!header || header.length > 16384 || !/^Bearer [^\s]+$/i.test(header))
      throw new Error("INVALID_TOKEN");
    const token = header.slice(7);
    if (cfg.mode === "bearer") {
      if (!cfg.token || !timingSafeEqual(digest(token), digest(cfg.token)))
        throw new Error("INVALID_TOKEN");
      return null;
    }
    if (cfg.mode === "auth0") {
      const { payload } = await jwtVerify(token, this.keys!, {
        issuer: cfg.issuer,
        audience: cfg.audience,
        algorithms: ["RS256"],
        requiredClaims: ["sub", "exp", "iat"],
      });
      if (payload.sub !== cfg.ownerSub)
        throw new Error("OWNER_ACCESS_DENIED");
      const scopes =
        typeof payload.scope === "string"
          ? payload.scope.split(" ").filter(Boolean)
          : [];
      return {
        token,
        clientId:
          typeof payload.azp === "string"
            ? payload.azp
            : typeof payload.client_id === "string"
              ? payload.client_id
              : "auth0",
        scopes,
        expiresAt: payload.exp!,
        extra: { ownerId: payload.sub },
      };
    }
    if (cfg.mode !== "supabase") {
      if (!cfg.token || !timingSafeEqual(digest(token), digest(cfg.token)))
        throw new Error("INVALID_TOKEN");
      return null;
    }
    const { payload } = await jwtVerify(token, this.keys!, {
      issuer: cfg.issuer,
      audience: cfg.publicUrl + "/mcp",
      algorithms: ["ES256", "RS256"],
      requiredClaims: ["sub", "exp", "iat", "client_id", "role", "scope"],
    });
    if (
      payload.sub !== cfg.ownerId ||
      payload.client_id !== cfg.clientId ||
      payload.role !== "authenticated" ||
      payload.is_anonymous === true ||
      typeof payload.scope !== "string" ||
      !payload.scope.split(" ").includes("openid") ||
      payload.trainaicad_access !== true
    )
      throw new Error("OWNER_OR_CLIENT_ACCESS_DENIED");
    return {
      token,
      clientId: cfg.clientId!,
      scopes: ["openid"],
      expiresAt: payload.exp!,
      extra: { ownerId: payload.sub },
    };
  }
  challenge() {
    return ["supabase", "setup", "auth0"].includes(this.config.mode)
      ? `Bearer resource_metadata="${this.config.publicUrl}/.well-known/oauth-protected-resource/mcp", scope="openid"`
      : 'Bearer realm="TrainAiCad developer staging"';
  }
}
