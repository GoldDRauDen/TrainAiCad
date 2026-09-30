import { spawn } from "node:child_process";
import { existsSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

const packageRoot = fileURLToPath(new URL("..", import.meta.url));
const repositoryRoot = fileURLToPath(new URL("../../../", import.meta.url));
const tsxCli = join(packageRoot, "node_modules", "tsx", "dist", "cli.mjs");
const inspectorScript = join(packageRoot, "scripts", "e2e_inspector.sh");
const bash = resolveBash();

if (!existsSync(tsxCli)) throw new Error("tsx CLI missing; run npm ci first");
if (!existsSync(inspectorScript)) throw new Error("MCP Inspector E2E script is missing");

const server = spawn(process.execPath, [tsxCli, "src/http.ts"], {
  cwd: packageRoot,
  stdio: ["ignore", "inherit", "inherit"],
  env: process.env
});
let stopping = false;
server.on("exit", (code, signal) => {
  if (!stopping && code !== 0) console.error(`MCP server exited early: code=${code} signal=${signal}`);
});

try {
  await waitForServer(server);
  const e2e = spawn(bash, [inspectorScript], {
    cwd: packageRoot,
    stdio: "inherit",
    env: { ...process.env, TRAINAICAD_REPO_ROOT: repositoryRoot }
  });
  const exitCode = await new Promise((resolve, reject) => {
    e2e.once("error", reject);
    e2e.once("exit", (code, signal) => resolve(code ?? (signal ? 1 : 0)));
  });
  if (exitCode !== 0) process.exitCode = Number(exitCode);
} finally {
  stopping = true;
  server.kill("SIGTERM");
}

function resolveBash() {
  const candidates = process.platform === "win32"
    ? [process.env.TRAINAICAD_BASH, "C:\\Program Files\\Git\\bin\\bash.exe", "C:\\Program Files (x86)\\Git\\bin\\bash.exe"]
    : [process.env.TRAINAICAD_BASH, "bash"];
  return candidates.find((candidate) => candidate && (candidate === "bash" || existsSync(candidate))) ?? "bash";
}

async function waitForServer(child) {
  const deadline = Date.now() + 30_000;
  let lastError;
  while (Date.now() < deadline) {
    if (child.exitCode !== null) throw new Error(`MCP server exited before readiness (${child.exitCode})`);
    try {
      const response = await fetch("http://127.0.0.1:8787/mcp", { signal: AbortSignal.timeout(750) });
      if (response.status !== 404) return;
    } catch (error) {
      lastError = error;
    }
    await new Promise((resolve) => setTimeout(resolve, 250));
  }
  throw new Error(`Timed out waiting for MCP HTTP server: ${lastError?.message ?? "not ready"}`);
}
