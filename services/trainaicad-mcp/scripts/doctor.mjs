import { spawnSync } from "node:child_process";
import { existsSync, readFileSync } from "node:fs";
import { isAbsolute, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const repo = fileURLToPath(new URL("../../../", import.meta.url));
const python = process.env.TRAINAICAD_PYTHON ?? (process.platform === "win32" ? "python" : "python3");
const nodeMajor = Number(process.versions.node.split(".")[0]);
const py = spawnSync(python, ["-c", "import sys,ezdxf,pymupdf; print(sys.version.split()[0])"], { encoding: "utf8" });
const entrypoint = readFileSync(`${repo}AI_ENTRYPOINT.md`, "utf8");
const release = entrypoint.match(/Current production release is \*\*(V[0-9.]+)\*\*/)?.[1] ?? "UNRESOLVED";
const required = JSON.parse(readFileSync(`${repo}regression/production-e2e/acceptance-set.json`, "utf8"));
const missing = [];
for (const testCase of required.cases) {
  for (const role of testCase.requiredRoles) {
    const path = testCase.sources?.[role];
    if (!path) {
      missing.push(`${testCase.id}:${role}: fixture path not declared`);
      continue;
    }
    const absolutePath = resolve(repo, path);
    const fromRoot = relative(repo, absolutePath);
    if (!fromRoot || fromRoot === ".." || fromRoot.startsWith(`..${process.platform === "win32" ? "\\" : "/"}`) || isAbsolute(fromRoot)) {
      missing.push(`${testCase.id}:${role}: path escapes repository`);
    } else if (!existsSync(absolutePath)) {
      missing.push(`${testCase.id}:${role}: ${path}`);
    }
  }
}

console.log(`TrainAiCad MCP doctor`);
console.log(`repository=${repo}`);
console.log(`productionRelease=${release}`);
console.log(`node=${process.versions.node} ${nodeMajor >= 22 ? "PASS" : "FAIL (need >=22)"}`);
console.log(`python=${py.status === 0 ? py.stdout.trim() : "UNAVAILABLE"} ${py.status === 0 ? "PASS" : "FAIL (need ezdxf and PyMuPDF)"}`);
console.log(`productionSourceAcceptance=${missing.length ? `BLOCKED (${missing.length} SOURCE_UNAVAILABLE)` : "FIXTURE_PATHS_DECLARED; run npm run test:e2e"}`);
for (const item of missing) console.log(`SOURCE_UNAVAILABLE ${item}`);
if (nodeMajor < 22 || py.status !== 0) process.exitCode = 1;
