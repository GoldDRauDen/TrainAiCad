import { spawnSync } from "node:child_process";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";

const repo = fileURLToPath(new URL("../../../", import.meta.url));
const python = process.env.TRAINAICAD_PYTHON ?? (process.platform === "win32" ? "python" : "python3");
const scripts = [
  "regression/tools/check_520801_04_v416.py",
  "regression/tools/check_520929_10_v417.py",
  "regression/tools/check_520929_18_v418.py",
  "regression/tools/check_520929_25_v419.py",
  "regression/tools/check_v420_source_mech.py",
  "regression/tools/check_520930_10_v422.py",
  "regression/tools/check_acute_bend_lt85.py"
];

let failed = false;
for (const script of scripts) {
  const result = spawnSync(python, [resolve(repo, script)], { cwd: repo, stdio: "inherit" });
  if (result.error) {
    console.error(`${script}: ${result.error.message}`);
    failed = true;
  } else if (result.status !== 0) {
    console.error(`${script}: exited ${result.status}`);
    failed = true;
  }
}
if (failed) process.exitCode = 1;
