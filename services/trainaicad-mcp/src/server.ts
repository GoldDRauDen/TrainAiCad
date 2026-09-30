import { McpServer, type CallToolResult } from "@modelcontextprotocol/server";
import * as z from "zod/v4";
import {
  CadEvidenceV1,
  JobModeRequested,
  SourceDescriptor
} from "./model.js";
import {
  jobStore,
  publicJob,
  recordSourceViewReceipt,
  routeJob
} from "./core.js";
import { downloadUri, storeSource } from "./ingest.js";
import { GeometrySourceV1 } from "./geometry.js";
import { renderSourcePage, sourcePageCount } from "./source-view.js";
import { harvestBoundDataDxf, readBoundDataDxfLedger } from "./source-dxf.js";

const BASE64 = /^[A-Za-z0-9+/\s]*={0,2}$/;
const NormalizedRegion = z.tuple([z.number().min(0).max(1), z.number().min(0).max(1), z.number().min(0).max(1), z.number().min(0).max(1)])
  .superRefine(([x0, y0, x1, y1], ctx) => {
    if (x0 >= x1 || y0 >= y1) ctx.addIssue({ code: "custom", message: "region must have positive width and height" });
  });

function json(value: unknown) {
  return {
    content: [{ type: "text" as const, text: JSON.stringify(value, null, 2) }]
  };
}

export function buildServer(): McpServer {
  const server = new McpServer(
    { name: "TrainAiCad", version: "0.3.0" },
    { capabilities: { tools: {} } }
  );

  server.registerTool(
    "process_cad_job",
    {
      description:
        "High-level production controller. Pins the current rules, returns actual source page images for vision, and advances deterministic stages when possible. It never asks the caller for coordinates or QA claims; unsupported engine stages return explicit blockers.",
      inputSchema: z.object({ jobId: z.string().min(1) })
    },
    async ({ jobId }) => orchestrate(jobId)
  );

  server.registerTool(
    "advance_cad_job",
    {
      description:
        "Advance a production job after ChatGPT inspects the returned source images. Accepts semantic CAD_EVIDENCE_V1 only, then routes automatically and returns the pinned route rules. Does not accept geometry coordinates or QA PASS claims.",
      inputSchema: z.object({ jobId: z.string().min(1), evidence: z.array(CadEvidenceV1).min(1).optional() })
    },
    async ({ jobId, evidence }) => orchestrate(jobId, evidence)
  );

  server.registerTool(
    "open_cad_job",
    {
      description:
        "Open a TrainAiCad MCP job using the live production release pin. Exact previously ingested source hashes are verified automatically; descriptor-only jobs stay unverified and cannot export.",
      inputSchema: z.object({
        drawing: SourceDescriptor,
        dxf: SourceDescriptor.optional(),
        referenceDxf: SourceDescriptor.optional(),
        mode: JobModeRequested.default("AUTO")
      })
    },
    async ({ drawing, dxf, referenceDxf, mode }) => {
      if (dxf && referenceDxf) throw new Error("PROVIDE_ONLY_ONE_OF_DXF_OR_REFERENCEDXF");
      const attachedDxf = dxf ?? referenceDxf;
      let job;
      try {
        job = jobStore.createFromIngestedSources(drawing, attachedDxf, mode, Boolean(referenceDxf));
      } catch (error) {
        if (!(error instanceof Error) || !error.message.startsWith("SOURCE_NOT_INGESTED:")) throw error;
        // Preserve non-production classification-only jobs for clients that have
        // not uploaded bytes yet; they remain unverified and cannot export.
        job = jobStore.create(drawing, attachedDxf, mode, Boolean(referenceDxf));
      }
      return json(publicJob(job));
    }
  );

  server.registerTool(
    "get_cad_rule_bundle",
    {
      description:
        "Read this job's immutable AI_ENTRYPOINT/CURRENT and mandatory/routed rule files. The tool returns each exact file body and SHA-256; read it before source inspection and again after routing adds mode/feature rules.",
      inputSchema: z.object({ jobId: z.string().min(1) })
    },
    async ({ jobId }) => json(jobStore.getRuleBundle(jobId))
  );

  server.registerTool(
    "submit_cad_evidence",
    {
      description:
        "Validate and store CAD_EVIDENCE_V1 produced from source inspection. DERIVED values require derivedFrom[] and rule; bent evidence may include faceCount, bend axis and signed fold direction.",
      inputSchema: z.object({
        jobId: z.string().min(1),
        evidence: z.array(CadEvidenceV1).min(1)
      })
    },
    async ({ jobId, evidence }) => {
      const job = jobStore.submitEvidence(jobId, evidence);
      return json(publicJob(job));
    }
  );

  server.registerTool(
    "route_cad_parts",
    {
      description:
        "Run deterministic routing against the live CURRENT rule set. Loads source classification, mechanical classifier, source-DATA preservation, feature modules and FACE_GRAPH for bent/multi-face parts. Jev remains advisory.",
      inputSchema: z.object({ jobId: z.string().min(1) })
    },
    async ({ jobId }) => json(publicJob(routeJob(jobId)))
  );

  server.registerTool(
    "build_canonical_geometry",
    {
      description:
        "DEBUG ONLY: accepts low-level GEOMETRY_SOURCE_V1 to test the experimental serializer. Do not use for production jobs; process_cad_job/advance_cad_job never request these caller-supplied coordinates. Production geometry must come from the not-yet-implemented deterministic PDF solver or DATA DXF harvester.",
      inputSchema: z.object({
        jobId: z.string().min(1),
        geometrySources: z.array(GeometrySourceV1).min(1)
      })
    },
    async ({ jobId, geometrySources }) => {
      if (jobStore.get(jobId).sourceVerified) jobStore.assertRuleBundleRead(jobId);
      return json(publicJob(jobStore.buildGeometry(jobId, geometrySources)));
    }
  );

  server.registerTool(
    "get_cad_source_view",
    {
      description:
        "Render a page or normalized crop from the hash-verified source with requested rotation. Returns cached PNG bytes and a receipt bound to source/page/region/rotation/DPI/image hash.",
      inputSchema: z.object({
        jobId: z.string().min(1), page: z.number().int().positive(), dpi: z.number().int().min(72).max(300).default(150),
        region: NormalizedRegion.optional(), rotation: z.union([z.literal(0), z.literal(90), z.literal(180), z.literal(270)]).default(0)
      })
    },
    async ({ jobId, page, dpi, region, rotation }) => {
      jobStore.assertRuleBundleRead(jobId);
      const job = jobStore.get(jobId);
      const rendered = renderSourcePage(job, page, dpi, region, rotation);
      recordSourceViewReceipt(jobId, rendered.receipt);
      return {
        content: [
          { type: "text" as const, text: JSON.stringify(rendered.receipt, null, 2) },
          { type: "image" as const, data: rendered.png.toString("base64"), mimeType: "image/png" }
        ]
      };
    }
  );

  server.registerTool(
    "harvest_data_dxf",
    {
      description:
        "Parse the exact job-bound PDF_DATA_RAW DATA_DXF into a source-handle/entity/transformation ledger. Preserves LINE/ARC/CIRCLE/LWPOLYLINE/POLYLINE/POINT/SPLINE/ELLIPSE and nested INSERT provenance; unsupported entities are retained as blocking flags. Never refits semantics or trusts INSUNITS as physical scale proof; the result always remains REVIEW_REQUIRED until scale and PDF correspondence are proved.",
      inputSchema: z.object({ jobId: z.string().min(1) })
    },
    async ({ jobId }) => {
      const harvested = harvestBoundDataDxf(jobId);
      return {
        content: [
          { type: "text" as const, text: JSON.stringify({
            phase: "SOURCE_GEOMETRY_HARVESTED_REVIEW_REQUIRED",
            jobId,
            ledgerUri: harvested.uri,
            fileName: harvested.fileName,
            ...harvested.summary
          }, null, 2) },
          { type: "resource" as const, resource: {
            uri: harvested.uri,
            mimeType: "application/json",
            blob: harvested.ledgerBytes.toString("base64")
          } }
        ]
      };
    }
  );

  server.registerTool(
    "get_source_geometry_ledger",
    {
      description:
        "Read the exact persisted source geometry ledger for the job's currently bound DATA_DXF. Requires the current ledger SHA-256 and rechecks the bound source and stored ledger hashes before returning its MCP resource.",
      inputSchema: z.object({ jobId: z.string().min(1), ledgerSha256: z.string().regex(/^[a-f0-9]{64}$/) })
    },
    async ({ jobId, ledgerSha256 }) => {
      const ledger = readBoundDataDxfLedger(jobId, ledgerSha256);
      return {
        content: [
          { type: "text" as const, text: JSON.stringify({ jobId, uri: ledger.uri, ledgerSha256, fileName: ledger.fileName, status: ledger.summary.status }) },
          { type: "resource" as const, resource: { uri: ledger.uri, mimeType: "application/json", blob: ledger.ledgerBytes.toString("base64") } }
        ]
      };
    }
  );

  server.registerTool(
    "run_cad_qa",
    {
      description:
        "Run server-computed manufacturing checks on canonical geometry. Checks the server cannot prove remain N/A and block production export.",
      inputSchema: z.object({ jobId: z.string().min(1) })
    },
    async ({ jobId }) => json(jobStore.runManufacturingQa(jobId))
  );

  server.registerTool(
    "export_dxf",
    {
      description:
        "Serialize canonical geometry only when server-computed manufacturing QA proves every required check. Caller-supplied QA cannot authorize export.",
      inputSchema: z.object({ jobId: z.string().min(1) })
    },
    async ({ jobId }) => json(publicJob(jobStore.exportDxf(jobId, [])))
  );

  server.registerTool(
    "audit_dxf",
    {
      description:
        "Re-open and independently audit the DXF written by export_dxf. Only a clean read-back advances DXF_READBACK -> QA_COMPLETE -> PRODUCTION_PASS.",
      inputSchema: z.object({ jobId: z.string().min(1) })
    },
    async ({ jobId }) => json(publicJob(jobStore.auditDxf(jobId)))
  );

  server.registerTool(
    "get_cad_job",
    {
      description:
        "Read current experimental job state, release pin, source policy, routes, canonical geometry and flags. V0.3 exposes DXF output/read-back status; PRODUCTION_PASS is reachable only after export + independent audit.",
      inputSchema: z.object({ jobId: z.string().min(1) })
    },
    async ({ jobId }) => json(publicJob(jobStore.get(jobId)))
  );

  server.registerTool(
    "get_cad_artifact",
    {
      description:
        "Return the exact saved and audited production DXF as an embedded MCP binary resource. The response contains file bytes, SHA-256 and a content-addressed trainaicad:// URI; local filesystem paths are never exposed.",
      inputSchema: z.object({ jobId: z.string().min(1) })
    },
    async ({ jobId }) => {
      const artifact = jobStore.readDxfArtifact(jobId);
      return {
        content: [
          { type: "text" as const, text: JSON.stringify({ uri: artifact.uri, fileName: artifact.fileName, mimeType: "image/vnd.dxf", sha256: artifact.sha256, bytes: artifact.bytes.length }) },
          { type: "resource" as const, resource: { uri: artifact.uri, mimeType: "image/vnd.dxf", blob: artifact.bytes.toString("base64") } }
        ]
      };
    }
  );

  server.registerTool(
    "ingest_cad_file",
    {
      description:
        "Ingest one PDF/image/DXF source: inline base64 data or downloadable http(s) URI. Supports DRAWING, DATA_DXF, REFERENCE_DXF and AI_DXF roles with immutable content-addressed storage.",
      inputSchema: z.object({
        fileName: z.string().min(1),
        role: z.enum(["DRAWING", "DATA_DXF", "REFERENCE_DXF", "AI_DXF"]).default("DRAWING"),
        data: z.string().min(1).optional(),
        uri: z.string().min(1).optional(),
        mimeType: z.string().min(1).optional(),
        jobId: z.string().min(1).optional()
      })
    },
    async ({ fileName, role, data, uri, mimeType, jobId }) => {
      if (Boolean(data) === Boolean(uri)) {
        throw new Error("PROVIDE_EXACTLY_ONE_OF_DATA_OR_URI");
      }
      let bytes: Buffer;
      if (data) {
        if (!BASE64.test(data)) throw new Error("INVALID_BASE64");
        bytes = Buffer.from(data.replace(/\s+/g, ""), "base64");
      } else {
        bytes = await downloadUri(uri as string);
      }

      const stored = storeSource({ fileName, bytes, mimeType }, role);
      let bound: Record<string, unknown> | null = null;
      let jobMode: string | null = null;
      if (jobId) {
        const result = jobStore.bindSource(jobId, role, stored); // reclassifies or rejects before writing
        bound = result.bound;
        jobMode = result.job.mode;
      }
      return json({
        role,
        kind: stored.kind,
        bytes: stored.bytes,
        source: {
          fileName: stored.fileName,
          sha256: stored.sha256,
          mimeType: stored.mimeType
        },
        storedPath: `sources/${role}/${stored.sha256.slice(0, 2)}/${stored.sha256}${stored.fileName.match(/\.[^.]+$/)?.[0] ?? ""}`,
        boundToJob: jobId ?? null,
        jobMode,
        boundSources: bound
      });
    }
  );

  return server;
}

async function orchestrate(jobId: string, evidence?: unknown[]): Promise<CallToolResult> {
  let job = jobStore.get(jobId);
  if (!job.sourceVerified) {
    return json({ phase: "SOURCE_REQUIRED", jobId, state: job.state, flags: ["SOURCE_BYTES_NOT_VERIFIED"], next: "Bind exact ingested DRAWING bytes before production processing." });
  }

  if (evidence?.length) job = jobStore.submitEvidence(jobId, evidence);

  if (job.state === "SOURCE_READY" && !job.evidence.length) {
    const initialRules = jobStore.getRuleBundle(jobId);
    const current = jobStore.get(jobId);
    const pageCount = sourcePageCount(current);
    const content: CallToolResult["content"] = [{
      type: "text",
      text: JSON.stringify({
        phase: "NEED_VISION",
        jobId,
        sourceManifest: current.sourceManifest,
        ruleSnapshotSha256: initialRules.snapshotSha256,
        pinnedRules: initialRules.files,
        pageCount,
        instruction: "Inspect the actual page images, map every drawing code to its source page, and submit semantic evidence. Do not invent geometry coordinates."
      }, null, 2)
    }];
    for (let page = 1; page <= pageCount; page += 1) {
      const view = renderSourcePage(current, page, 120);
      recordSourceViewReceipt(jobId, view.receipt);
      content.push({ type: "text", text: `SOURCE_VIEW_RECEIPT ${view.receipt.receiptId} ${JSON.stringify({ page, sourceSha256: view.receipt.sourceSha256, imageSha256: view.receipt.imageSha256, region: view.receipt.region, dpi: view.receipt.dpi })}` });
      content.push({ type: "image", data: view.png.toString("base64"), mimeType: "image/png" });
    }
    return { content };
  }

  if (job.state === "EVIDENCE_READY") {
    job = routeJob(jobId);
    const routedRules = jobStore.getRuleBundle(jobId);
    if (job.mode === "PDF_DATA_RAW") {
      const harvested = harvestBoundDataDxf(jobId);
      const current = jobStore.get(jobId);
      return {
        content: [
          { type: "text" as const, text: JSON.stringify({
            phase: "SOURCE_GEOMETRY_HARVESTED_REVIEW_REQUIRED",
            job: publicJob(current),
            routeRuleSnapshotSha256: routedRules.snapshotSha256,
            pinnedRouteRules: routedRules.files,
            ledgerUri: harvested.uri,
            ledgerSha256: harvested.ledgerSha256,
            blockers: [
              "DATA_DXF_PHYSICAL_SCALE_UNPROVED",
              "PDF_DATA_GEOMETRY_CORRESPONDENCE_NOT_PROVED",
              "DATA_DXF_CANONICAL_GEOMETRY_ENGINE_NOT_IMPLEMENTED"
            ],
            next: "Prove physical scale and PDF-to-DATA correspondence from source evidence. Geometry remains review-only until deterministic canonical construction and manufacturing QA consume the ledger."
          }, null, 2) },
          { type: "resource" as const, resource: {
            uri: harvested.uri,
            mimeType: "application/json",
            blob: harvested.ledgerBytes.toString("base64")
          } }
        ]
      };
    }
    if (job.state === "REVIEW_REQUIRED") {
      return json({ phase: "NEED_VISION", job: publicJob(job), routeRuleSnapshotSha256: routedRules.snapshotSha256, pinnedRouteRules: routedRules.files });
    }
    return json({
      phase: "ROUTED",
      job: publicJob(job),
      routeRuleSnapshotSha256: routedRules.snapshotSha256,
      pinnedRouteRules: routedRules.files,
      blocker: "PDF_ONLY_DETERMINISTIC_SOLVER_NOT_IMPLEMENTED",
      next: "The MCP has no production PDF-only source-geometry engine for this route yet; it will not request caller-generated GEOMETRY_SOURCE_V1."
    });
  }

  if (job.state === "PRODUCTION_PASS") {
    const artifact = jobStore.readDxfArtifact(jobId);
    return {
      content: [
        { type: "text" as const, text: JSON.stringify({ phase: "PRODUCTION_PASS", uri: artifact.uri, fileName: artifact.fileName, mimeType: "image/vnd.dxf", sha256: artifact.sha256, bytes: artifact.bytes.length }) },
        { type: "resource" as const, resource: { uri: artifact.uri, mimeType: "image/vnd.dxf", blob: artifact.bytes.toString("base64") } }
      ]
    };
  }

  return json({ phase: job.state === "ROUTED" ? "ROUTED" : job.state, job: publicJob(job), next: "No additional deterministic stage is available in this experimental engine state." });
}
