import { initializeStorage, checkpoint } from "./storage.js";
import { createServer } from "node:http";
import {
  hostHeaderValidation,
  localhostHostValidation,
  localhostOriginValidation,
  toNodeHandler,
} from "@modelcontextprotocol/node";
import { readReleasePin } from "./core.js";
import { authConfig } from "./auth.js";
import { createApp, MAX_HTTP_BODY } from "./app.js";
const port = Number(
  process.env.PORT ?? process.env.TRAINAICAD_MCP_PORT ?? "8787",
);
if (!Number.isInteger(port) || port < 1 || port > 65535)
  throw new Error("Invalid MCP port");
const host = process.env.TRAINAICAD_MCP_HOST ?? "127.0.0.1";
const config = authConfig();
await initializeStorage();
const release = readReleasePin();
await checkpoint();
const app = createApp(config);
// The Node adapter has its own 4 MiB default, separate from the SDK handler.
const nodeHandler = toNodeHandler(app, { maxRequestBodySize: MAX_HTTP_BODY });
const hostGuard =
  host === "127.0.0.1"
    ? localhostHostValidation()
    : config.publicUrl
      ? hostHeaderValidation([new URL(config.publicUrl).hostname])
      : undefined;
const originGuard = localhostOriginValidation();
const server = createServer((req, res) => {
  if (hostGuard && !hostGuard(req, res)) return;
  if (host === "127.0.0.1" && !originGuard(req, res)) return;
  if (
    host !== "127.0.0.1" &&
    req.headers.origin &&
    req.headers.origin !== config.publicUrl
  ) {
    res.writeHead(403);
    res.end("Origin rejected");
    return;
  }
  void nodeHandler(req, res);
});
server.listen(port, host, () =>
  console.error(
    `[TrainAiCad MCP] research; release=${release.release}; auth=${config.mode}; listening ${host}:${port}`,
  ),
);
async function shutdown() {
  server.close();
  await app.close();
}
process.once("SIGTERM", () => {
  void shutdown();
});
process.once("SIGINT", () => {
  void shutdown();
});
