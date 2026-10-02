/** PDF canary: in-process SDK or actual loopback TCP plus native file transfer. */
import { readFileSync, writeFileSync } from "node:fs";
import { createServer } from "node:http";
import { once } from "node:events";
import { toNodeHandler } from "@modelcontextprotocol/node";
import { createApp, MAX_HTTP_BODY } from "../src/app.js";
import { jobStore } from "../src/core.js";
import { sha256 } from "../src/source.js";
const [pdf, fixture, output] = process.argv.slice(2);
if (!pdf || !fixture || !output)
  throw new Error(
    "usage: smoke_pdf.ts source.pdf independently-read-fixture.json summary.json",
  );
const spec = JSON.parse(readFileSync(fixture, "utf8")),
  bytes = readFileSync(pdf),
  hash = sha256(bytes),
  handler = createApp({ mode: "local" });
const network = process.env.TRAINAICAD_SMOKE_NETWORK === "1";
let endpoint = "http://localhost/mcp";
let tcpServer: ReturnType<typeof createServer> | undefined;
if (network) {
  const adapter = toNodeHandler(handler, { maxRequestBodySize: MAX_HTTP_BODY });
  tcpServer = createServer((req, res) => {
    void adapter(req, res);
  });
  tcpServer.listen(0, "127.0.0.1");
  await once(tcpServer, "listening");
  endpoint = `http://127.0.0.1:${(tcpServer.address() as any).port}/mcp`;
  process.env.TRAINAICAD_PUBLIC_URL = new URL(endpoint).origin;
  process.env.TRAINAICAD_ARTIFACT_SECRET =
    "loopback-smoke-key-not-a-deployment-secret";
}
let id = 0;
const timings: Record<string, number> = {};
async function rpc(method: string, params: unknown) {
  const before = performance.now(),
    response = await (network ? fetch : handler.fetch)(
      new Request(endpoint, {
        method: "POST",
        headers: {
          "content-type": "application/json",
          accept: "application/json, text/event-stream",
          "mcp-protocol-version": "2025-03-26",
        },
        body: JSON.stringify({ jsonrpc: "2.0", id: ++id, method, params }),
      }),
    );
  const text = await response.text(),
    line = text.split("\n").find((l) => l.startsWith("data:")),
    packet = JSON.parse(line ? line.slice(5) : text);
  if (!response.ok || packet.error || packet.result?.isError)
    throw new Error(`MCP ${method}: ${text.slice(0, 1000)}`);
  timings[`${method}:${(params as any)?.name ?? "request"}:${id}`] =
    performance.now() - before;
  return packet.result;
}
const tool = (name: string, args: unknown) =>
    rpc("tools/call", { name, arguments: args }),
  asJson = (r: any) =>
    JSON.parse(r.content.find((c: any) => c.type === "text").text);
try {
  await rpc("initialize", {
    protocolVersion: "2025-03-26",
    capabilities: {},
    clientInfo: { name: "real-PDF-smoke", version: "1" },
  });
  const inventory = await rpc("tools/list", {});
  const nativeUrl = process.env.TRAINAICAD_SMOKE_SOURCE_URL;
  const opened = nativeUrl
    ? asJson(
        await tool("open_chatgpt_cad_job", {
          drawing: {
            file_id: "local-canary-authorized-file",
            download_url: nativeUrl,
            file_name: pdf.split("/").at(-1),
            mime_type: "application/pdf",
          },
        }),
      )
    : await (async () => {
        await tool("ingest_cad_file", {
          fileName: pdf.split("/").at(-1),
          role: "DRAWING",
          data: bytes.toString("base64"),
          mimeType: "application/pdf",
        });
        return asJson(
          await tool("open_cad_job", {
            drawing: { fileName: pdf.split("/").at(-1), sha256: hash },
            mode: "PDF_ONLY",
          }),
        );
      })();
  const jobId = opened.jobId;
  const prepared = asJson(
      await tool("prepare_cad_source", {
        jobId,
        pages: [spec.page],
        dpi: 160,
        crops: spec.crops ?? [],
      }),
    ),
    im = prepared.images.find(
      (im: any) => im.page === spec.page && im.roi.join(",") === "0,0,1,1",
    );
  const imageResult = await tool("get_cad_source_image", {
    jobId,
    imageId: im.imageId,
  });
  writeFileSync(
    output.replace(/\.json$/, "_source.png"),
    Buffer.from(
      imageResult.content.find((c: any) => c.type === "image").data,
      "base64",
    ),
  );
  for (const extra of prepared.images.filter(
    (x: any) => x.imageId !== im.imageId,
  ))
    await tool("get_cad_source_image", { jobId, imageId: extra.imageId });
  const evidence = {
    ...spec.evidence,
    jobId,
    source: { sourceId: hash, page: spec.page },
  };
  await tool("submit_cad_evidence", { jobId, evidence: [evidence] });
  await tool("route_cad_parts", { jobId });
  await tool("get_cad_rules", {
    jobId,
    code: evidence.code,
    paths: spec.rulePaths,
  });
  await tool("build_canonical_geometry", {
    jobId,
    geometrySources: [{ ...spec.geometry, jobId, sourceSha256: hash }],
  });
  const checks = {
      ...spec.checks,
      dimensions: spec.checks.dimensions.map((d: any) => ({
        ...d,
        imageId: im.imageId,
      })),
    },
    verified = asJson(
      await tool("verify_cad_geometry", { jobId, checks: [checks] }),
    );
  await tool("export_dxf", { jobId });
  const audit = asJson(await tool("audit_dxf", { jobId })),
    file = await tool("get_cad_artifact", { jobId });
  const delivered = asJson(file);
  let downloadedSha256: string | null = null;
  if (delivered.url) {
    const download = await fetch(delivered.url);
    if (!download.ok) throw new Error("SIGNED_DXF_DOWNLOAD_FAILED");
    const returned = Buffer.from(await download.arrayBuffer());
    downloadedSha256 = sha256(returned);
    if (downloadedSha256 !== delivered.sha256)
      throw new Error("SIGNED_DXF_DOWNLOAD_HASH_MISMATCH");
    writeFileSync(output.replace(/\.json$/, "_returned.dxf"), returned);
  }
  const summary = {
    transport: network
      ? "Actual Node TCP HTTP + SDK; local canary, not public hosting"
      : "SDK HTTP Request/Response in-process; not a public deployment",
    inputTransfer: nativeUrl
      ? "Native fileParams; actual HTTPS binary download with trusted local test CA"
      : "Legacy inline base64",
    downloadedSha256,
    scope:
      "One independently interpreted source view, not the complete PDF. Timings exclude model reasoning, cloud hosting, cloud identity provider and real remote storage.",
    usage: "USAGE_UNAVAILABLE",
    jobId,
    sourceSha256: hash,
    pageCount: prepared.pageCount,
    testedPage: spec.page,
    code: evidence.code,
    toolCount: inventory.tools.length,
    geometry: jobStore.get(jobId).geometry,
    qa: verified.computedQa,
    state: audit.state,
    flags: audit.flags,
    dxfOutput: jobStore.get(jobId).dxfOutput,
    readback: jobStore.get(jobId).dxfAudit,
    artifact: {
      ...delivered,
      url: delivered.url ? "EXPIRING_LINK_OMITTED_FROM_REPORT" : null,
    },
    timingsMs: timings,
  };
  writeFileSync(output, JSON.stringify(summary, null, 2));
  console.log(
    JSON.stringify(
      {
        jobId,
        state: audit.state,
        toolCount: inventory.tools.length,
        file: summary.dxfOutput?.absolutePath,
        qa: summary.qa,
      },
      null,
      2,
    ),
  );
} finally {
  await handler.close();
  if (tcpServer) {
    tcpServer.closeAllConnections();
    await new Promise<void>((r) => tcpServer!.close(() => r()));
  }
}
