import {
  createMcpHandler,
  type McpHandlerRequestOptions,
} from "@modelcontextprotocol/server";
import { Authentication, authConfig, type AuthConfig } from "./auth.js";
import { buildServer } from "./server.js";
import { consentPage, supabaseBrowserScript } from "./consent.js";
import { downloadArtifact } from "./artifact.js";
import { jobStore } from "./core.js";
export const MAX_HTTP_BODY = 36 * 1024 * 1024;
export function createApp(
  config: AuthConfig = authConfig(),
  authentication = new Authentication(config),
) {
  const mcp = createMcpHandler(buildServer, {
    maxRequestBodySize: MAX_HTTP_BODY,
  });
  return {
    close: () => mcp.close(),
    async fetch(
      request: Request,
      options?: McpHandlerRequestOptions,
    ): Promise<Response> {
      const url = new URL(request.url),
        path = url.pathname;
      const getOnly =
        path === "/health" ||
        path.startsWith("/.well-known/") ||
        path.startsWith("/oauth/") ||
        path.startsWith("/artifacts/");
      if (getOnly && request.method !== "GET")
        return new Response("Method Not Allowed", {
          status: 405,
          headers: { allow: "GET" },
        });
      if (path === "/health") return new Response("ok");
      if (
        ["supabase", "setup", "auth0"].includes(config.mode) &&
        [
          "/.well-known/oauth-protected-resource",
          "/.well-known/oauth-protected-resource/mcp",
        ].includes(path)
      )
        return Response.json(authentication.metadata(), {
          headers: { "cache-control": "no-store" },
        });
      if (["supabase", "setup"].includes(config.mode)) {
        if (path === "/oauth/consent")
          return config.mode === "supabase"
            ? consentPage(config)
            : new Response("OAuth setup pending", { status: 503 });
        if (config.mode === "supabase" && path === "/oauth/supabase.js")
          return new Response(new Uint8Array(supabaseBrowserScript()), {
            headers: {
              "content-type": "text/javascript; charset=utf-8",
              "x-content-type-options": "nosniff",
              "cache-control": "public,max-age=3600",
            },
          });
      }
      if (path.startsWith("/artifacts/")) {
        try {
          const id = path.match(/^\/artifacts\/(cad_[a-f0-9]{16})\.dxf$/)?.[1];
          if (!id) throw new Error("INVALID_ARTIFACT");
          const file = downloadArtifact(jobStore.get(id), url);
          return new Response(new Uint8Array(file.bytes), {
            headers: {
              "content-type": "application/dxf",
              "content-disposition": `attachment; filename="${file.fileName}"`,
              "cache-control": "private, no-store",
              "x-content-type-options": "nosniff",
            },
          });
        } catch {
          return new Response("Forbidden", { status: 403 });
        }
      }
      if (path !== "/mcp") return new Response("Not Found", { status: 404 });
      let authInfo;
      try {
        authInfo = await authentication.authorize(
          request.headers.get("authorization"),
        );
      } catch {
        return Response.json(
          { error: "invalid_token" },
          {
            status: 401,
            headers: {
              "www-authenticate": authentication.challenge(),
              "cache-control": "no-store",
            },
          },
        );
      }
      return mcp.fetch(request, {
        ...options,
        authInfo: authInfo ?? undefined,
      });
    },
  };
}
