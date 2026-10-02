/** Test certificates and private-host allowance are confined to this loopback canary. */
import { execFile } from "node:child_process";
import { promisify } from "node:util";
import { mkdtempSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { createServer } from "node:https";
import { once } from "node:events";
const [pdf, fixture, output] = process.argv.slice(2);
if (!pdf || !fixture || !output)
  throw new Error(
    "usage: smoke:native source.pdf independently-read-fixture.json report.json",
  );
const run = promisify(execFile),
  dir = mkdtempSync(join(tmpdir(), "cad-loopback-tls-"));
let server: ReturnType<typeof createServer> | undefined;
try {
  await run(
    "openssl",
    [
      "req",
      "-x509",
      "-newkey",
      "rsa:2048",
      "-nodes",
      "-keyout",
      join(dir, "key.pem"),
      "-out",
      join(dir, "cert.pem"),
      "-days",
      "1",
      "-subj",
      "/CN=127.0.0.1",
      "-addext",
      "subjectAltName=IP:127.0.0.1",
      "-addext",
      "basicConstraints=critical,CA:TRUE",
    ],
    { timeout: 15000 },
  );
  const bytes = readFileSync(resolve(pdf));
  server = createServer(
    {
      key: readFileSync(join(dir, "key.pem")),
      cert: readFileSync(join(dir, "cert.pem")),
    },
    (req, res) => {
      if (req.method !== "GET" || req.url !== "/source.pdf") {
        res.writeHead(404);
        res.end();
        return;
      }
      res.writeHead(200, {
        "content-type": "application/pdf",
        "content-length": bytes.length,
      });
      res.end(bytes);
    },
  );
  server.listen(0, "127.0.0.1");
  await once(server, "listening");
  const result = await run(
    process.execPath,
    [
      "--import",
      "tsx",
      "scripts/smoke_pdf.ts",
      resolve(pdf),
      resolve(fixture),
      resolve(output),
    ],
    {
      env: {
        ...process.env,
        NODE_EXTRA_CA_CERTS: join(dir, "cert.pem"),
        TRAINAICAD_ALLOW_PRIVATE_URL: "1",
        TRAINAICAD_SMOKE_NETWORK: "1",
        TRAINAICAD_SMOKE_SOURCE_URL: `https://127.0.0.1:${(server.address() as any).port}/source.pdf`,
      },
      timeout: 120000,
      maxBuffer: 2 * 1024 * 1024,
    },
  );
  process.stdout.write(result.stdout);
  process.stderr.write(result.stderr);
} finally {
  if (server) {
    server.closeAllConnections();
    await new Promise<void>((r) => server!.close(() => r()));
  }
  rmSync(dir, { recursive: true, force: true });
}
