import { existsSync, readFileSync } from "node:fs";
import { isAbsolute, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const repo = fileURLToPath(new URL("../../../", import.meta.url));
const manifestPath = resolve(repo, "regression/production-e2e/acceptance-set.json");
const manifest = JSON.parse(readFileSync(manifestPath, "utf8"));
const missing = [];

for (const testCase of manifest.cases) {
  for (const role of testCase.requiredRoles) {
    const relativePath = testCase.sources?.[role];
    if (!relativePath) {
      missing.push(`${testCase.id}:${role}: fixture path not declared`);
      continue;
    }
    const absolutePath = resolve(repo, relativePath);
    const fromRoot = relative(repo, absolutePath);
    if (!fromRoot || fromRoot === ".." || fromRoot.startsWith(`..${process.platform === "win32" ? "\\" : "/"}`) || isAbsolute(fromRoot)) {
      missing.push(`${testCase.id}:${role}: path escapes repository`);
      continue;
    }
    if (!existsSync(absolutePath)) missing.push(`${testCase.id}:${role}: SOURCE_UNAVAILABLE ${relativePath}`);
  }
}

console.log(`Production source acceptance cases: ${manifest.cases.length}`);
if (missing.length) {
  for (const item of missing) console.error(`SOURCE_UNAVAILABLE ${item}`);
  console.error("BLOCKED: production PDF/DATA acceptance fixtures are not present; protocol smoke results do not certify production E2E.");
  process.exitCode = 2;
} else {
  console.error("BLOCKED: fixture paths exist, but full manufacturing-source acceptance has not been implemented by this experimental pipeline.");
  process.exitCode = 2;
}
console.error("BLOCKED: ChatGPT Web attachment upload/download acceptance requires the remote MCP app and Secure MCP Tunnel; this local runner cannot certify that UI path.");
