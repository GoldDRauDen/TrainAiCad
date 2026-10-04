import { ChatGptFile, ingestChatGptFile } from "./chatgpt-file.js";
import { rulesBundle, selectRules } from "./snapshot.js";
import { prepareSource, sourceImage } from "./source.js";
import { SourceChecks } from "./qa.js";
import { artifact } from "./artifact.js";
import { checkpoint } from "./storage.js";
import { McpServer } from "@modelcontextprotocol/server";
import * as z from "zod/v4";
import { CadEvidenceV1, JobModeRequested, SourceDescriptor } from "./model.js";
import { jobStore, publicJob, routeJob, resolveRepoRoot } from "./core.js";
import { downloadUri, storeSource, maxSourceBytes } from "./ingest.js";
import { GeometrySourceV1 } from "./geometry.js";

const BASE64 = /^[A-Za-z0-9+/\s]*={0,2}$/;

async function json(value: unknown) {
  await checkpoint();
  return {
    content: [{ type: "text" as const, text: JSON.stringify(value, null, 2) }],
  };
}

export function buildServer(): McpServer {
  const server = new McpServer(
    { name: "TrainAiCad", version: "0.5.0" },
    { capabilities: { tools: {} } },
  );

  server.registerTool(
    "open_chatgpt_cad_job",
    {
      title: "Nhận bản vẽ PDF / ảnh từ ChatGPT",
      description:
        "Start a CAD job from host-authorized file attachments. Fetch binary bytes directly using file params; never manufacture download URLs or send PDF base64. Without DATA DXF uses PDF_ONLY. Optional referenceDxf is TRAIN_REFERENCE, not raw DATA.",
      inputSchema: z.object({
        drawing: ChatGptFile,
        dataDxf: ChatGptFile.optional(),
        referenceDxf: ChatGptFile.optional(),
      }),
      annotations: {
        readOnlyHint: false,
        destructiveHint: false,
        openWorldHint: true,
      },
      _meta: {
        "openai/fileParams": ["drawing", "dataDxf", "referenceDxf"],
        ...(process.env.TRAINAICAD_AUTH_MODE === "supabase"
          ? { securitySchemes: [{ type: "oauth2", scopes: ["openid"] }] }
          : {}),
      },
    },
    async ({ drawing, dataDxf, referenceDxf }) => {
      if (dataDxf && referenceDxf)
        throw new Error("PROVIDE_ONLY_ONE_OF_DATA_OR_REFERENCE_DXF");
      const input = await ingestChatGptFile(drawing, "DRAWING");
      const dxf =
        dataDxf || referenceDxf
          ? await ingestChatGptFile(
              (dataDxf ?? referenceDxf)!,
              dataDxf ? "DATA_DXF" : "REFERENCE_DXF",
            )
          : undefined;
      const source = (s: typeof input.stored) => ({
        fileName: s.fileName,
        sha256: s.sha256,
        mimeType: s.mimeType,
      });
      const job = jobStore.create(
        source(input.stored),
        dxf ? source(dxf.stored) : undefined,
        "AUTO",
        Boolean(referenceDxf),
      );
      return json({
        ...publicJob(job),
        receivedFiles: [
          {
            fileId: input.fileId,
            ...source(input.stored),
            bytes: input.stored.bytes,
          },
          ...(dxf
            ? [
                {
                  fileId: dxf.fileId,
                  ...source(dxf.stored),
                  bytes: dxf.stored.bytes,
                },
              ]
            : []),
        ],
      });
    },
  );

  server.registerTool(
    "open_cad_job",
    {
      annotations: {
        readOnlyHint: false,
        destructiveHint: false,
        openWorldHint: false,
      },
      _meta:
        process.env.TRAINAICAD_AUTH_MODE === "supabase"
          ? { securitySchemes: [{ type: "oauth2", scopes: ["openid"] }] }
          : undefined,
      description:
        "Open a research job using the active modular source-classification rules. AUTO+generic dxf => PDF_DATA_RAW; AUTO+explicit referenceDxf => TRAIN_REFERENCE; no DXF => PDF_ONLY.",
      inputSchema: z.object({
        drawing: SourceDescriptor,
        dxf: SourceDescriptor.optional(),
        referenceDxf: SourceDescriptor.optional(),
        mode: JobModeRequested.default("AUTO"),
      }),
    },
    async ({ drawing, dxf, referenceDxf, mode }) => {
      if (dxf && referenceDxf)
        throw new Error("PROVIDE_ONLY_ONE_OF_DXF_OR_REFERENCEDXF");
      const attachedDxf = dxf ?? referenceDxf;
      const job = jobStore.create(
        drawing,
        attachedDxf,
        mode,
        Boolean(referenceDxf),
      );
      return json(publicJob(job));
    },
  );

  server.registerTool(
    "submit_cad_evidence",
    {
      annotations: {
        readOnlyHint: false,
        destructiveHint: false,
        openWorldHint: false,
      },
      _meta:
        process.env.TRAINAICAD_AUTH_MODE === "supabase"
          ? { securitySchemes: [{ type: "oauth2", scopes: ["openid"] }] }
          : undefined,
      description:
        "Validate and store CAD_EVIDENCE_V1 produced from source inspection. DERIVED values require derivedFrom[] and rule; bent evidence may include faceCount, bend axis and signed fold direction.",
      inputSchema: z.object({
        jobId: z.string().min(1),
        evidence: z.array(CadEvidenceV1).min(1),
      }),
    },
    async ({ jobId, evidence }) => {
      const job = jobStore.submitEvidence(jobId, evidence);
      return json(publicJob(job));
    },
  );

  server.registerTool(
    "route_cad_parts",
    {
      annotations: {
        readOnlyHint: false,
        destructiveHint: false,
        openWorldHint: false,
      },
      _meta:
        process.env.TRAINAICAD_AUTH_MODE === "supabase"
          ? { securitySchemes: [{ type: "oauth2", scopes: ["openid"] }] }
          : undefined,
      description:
        "Run pinned active modular source/mechanical routing. Loads source classification, mechanical classifier, feature modules and FACE_GRAPH for bent/multi-face parts. Jev remains advisory.",
      inputSchema: z.object({ jobId: z.string().min(1) }),
    },
    async ({ jobId }) => json(publicJob(routeJob(jobId))),
  );

  server.registerTool(
    "build_canonical_geometry",
    {
      annotations: {
        readOnlyHint: false,
        destructiveHint: false,
        openWorldHint: false,
      },
      _meta:
        process.env.TRAINAICAD_AUTH_MODE === "supabase"
          ? { securitySchemes: [{ type: "oauth2", scopes: ["openid"] }] }
          : undefined,
      description:
        "Build deterministic CANONICAL_GEOMETRY_V1 from source-authorized GEOMETRY_SOURCE_V1. V0.2 supports proved flat single-face geometry and proved constant-width linear bend chains; unsupported/missing constraints fail to REVIEW_REQUIRED.",
      inputSchema: z.object({
        jobId: z.string().min(1),
        geometrySources: z.array(GeometrySourceV1).min(1),
      }),
    },
    async ({ jobId, geometrySources }) =>
      json(publicJob(jobStore.buildGeometry(jobId, geometrySources))),
  );

  server.registerTool(
    "export_dxf",
    {
      annotations: {
        readOnlyHint: false,
        destructiveHint: false,
        openWorldHint: false,
      },
      _meta:
        process.env.TRAINAICAD_AUTH_MODE === "supabase"
          ? { securitySchemes: [{ type: "oauth2", scopes: ["openid"] }] }
          : undefined,
      description:
        "Export hash-bound checked source-view geometry as REVIEW ONLY / NO CUT. Caller PASS claims cannot certify production.",
      inputSchema: z.object({ jobId: z.string().min(1) }),
    },
    async ({ jobId }) => json(publicJob(jobStore.exportDxf(jobId))),
  );

  server.registerTool(
    "audit_dxf",
    {
      annotations: {
        readOnlyHint: false,
        destructiveHint: false,
        openWorldHint: false,
      },
      _meta:
        process.env.TRAINAICAD_AUTH_MODE === "supabase"
          ? { securitySchemes: [{ type: "oauth2", scopes: ["openid"] }] }
          : undefined,
      description:
        "Re-open and independently audit the DXF written by export_dxf. A clean read-back advances to research QA_COMPLETE; never PRODUCTION_PASS.",
      inputSchema: z.object({ jobId: z.string().min(1) }),
    },
    async ({ jobId }) => json(publicJob(jobStore.auditDxf(jobId))),
  );

  server.registerTool(
    "get_cad_job",
    {
      annotations: {
        readOnlyHint: true,
        destructiveHint: false,
        openWorldHint: false,
      },
      _meta:
        process.env.TRAINAICAD_AUTH_MODE === "supabase"
          ? { securitySchemes: [{ type: "oauth2", scopes: ["openid"] }] }
          : undefined,
      description:
        "Read current experimental job state, release pin, source policy, routes, canonical geometry and flags. Exposes DXF output/read-back status; QA_COMPLETE is research only and never PRODUCTION_PASS.",
      inputSchema: z.object({ jobId: z.string().min(1) }),
    },
    async ({ jobId }) => json(publicJob(jobStore.get(jobId))),
  );

  server.registerTool(
    "ingest_cad_file",
    {
      annotations: {
        readOnlyHint: false,
        destructiveHint: false,
        openWorldHint: true,
      },
      _meta:
        process.env.TRAINAICAD_AUTH_MODE === "supabase"
          ? { securitySchemes: [{ type: "oauth2", scopes: ["openid"] }] }
          : undefined,
      description:
        "Ingest one PDF/image/DXF source: inline base64 data or downloadable http(s) URI. Supports DRAWING, DATA_DXF, REFERENCE_DXF and AI_DXF roles with immutable content-addressed storage.",
      inputSchema: z.object({
        fileName: z.string().min(1),
        role: z
          .enum(["DRAWING", "DATA_DXF", "REFERENCE_DXF", "AI_DXF"])
          .default("DRAWING"),
        data: z.string().min(1).optional(),
        uri: z.string().min(1).optional(),
        mimeType: z.string().min(1).optional(),
        jobId: z.string().min(1).optional(),
      }),
    },
    async ({ fileName, role, data, uri, mimeType, jobId }) => {
      if (Boolean(data) === Boolean(uri)) {
        throw new Error("PROVIDE_EXACTLY_ONE_OF_DATA_OR_URI");
      }
      let bytes: Buffer;
      if (data) {
        if (data.length > Math.ceil(maxSourceBytes() / 3) * 4 + 1024)
          throw new Error("SOURCE_TOO_LARGE");
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
          mimeType: stored.mimeType,
        },
        storedPath: `sources/${role}/${stored.sha256.slice(0, 2)}/${stored.sha256}${stored.fileName.match(/\.[^.]+$/)?.[0] ?? ""}`,
        boundToJob: jobId ?? null,
        jobMode,
        boundSources: bound,
      });
    },
  );

  server.registerTool(
    "get_cad_rules",
    {
      annotations: {
        readOnlyHint: true,
        destructiveHint: false,
        openWorldHint: false,
      },
      _meta:
        process.env.TRAINAICAD_AUTH_MODE === "supabase"
          ? { securitySchemes: [{ type: "oauth2", scopes: ["openid"] }] }
          : undefined,
      description:
        "Read actual immutable modular rule text, by selected code and optional path subset. Without code returns entrypoint and always-on core.",
      inputSchema: z.object({
        jobId: z.string(),
        code: z.string().optional(),
        paths: z.array(z.string()).optional(),
      }),
    },
    async ({ jobId, code, paths }) => {
      const job = jobStore.get(jobId),
        e = code ? job.evidence.find((e) => e.code === code) : undefined;
      if (code && !e) throw new Error("EVIDENCE_CODE_NOT_FOUND");
      const selected = [
        "AI_ENTRYPOINT.md",
        ...selectRules(job.production, job.mode, e),
      ];
      if (paths?.some((p) => !selected.includes(p)))
        throw new Error("RULE_NOT_IN_SELECTED_ROUTE");
      return json({
        snapshotId: job.production.snapshotId,
        release: job.production.release,
        selectedPaths: selected,
        rules: rulesBundle(job.production, paths ?? selected),
      });
    },
  );
  server.registerTool(
    "prepare_cad_source",
    {
      annotations: {
        readOnlyHint: false,
        destructiveHint: false,
        openWorldHint: false,
      },
      _meta:
        process.env.TRAINAICAD_AUTH_MODE === "supabase"
          ? { securitySchemes: [{ type: "oauth2", scopes: ["openid"] }] }
          : undefined,
      description:
        "Read actual bytes and cache page overviews or normalized ROI crops [left,top,right,bottom]. Metadata alone is not vision evidence.",
      inputSchema: z.object({
        jobId: z.string(),
        pages: z.array(z.number().int().positive()).optional(),
        dpi: z.number().int().min(72).max(300).default(110),
        crops: z
          .array(
            z.object({
              page: z.number().int().positive(),
              roi: z.tuple([z.number(), z.number(), z.number(), z.number()]),
            }),
          )
          .default([]),
      }),
    },
    async ({ jobId, ...options }) =>
      json(
        await prepareSource(jobStore.get(jobId), resolveRepoRoot(), options),
      ),
  );
  server.registerTool(
    "get_cad_source_image",
    {
      annotations: {
        readOnlyHint: false,
        destructiveHint: false,
        openWorldHint: false,
      },
      _meta:
        process.env.TRAINAICAD_AUTH_MODE === "supabase"
          ? { securitySchemes: [{ type: "oauth2", scopes: ["openid"] }] }
          : undefined,
      description:
        "Deliver actual page/crop image bytes, source/page/ROI/image hashes. Receipt does not prove correct interpretation.",
      inputSchema: z.object({ jobId: z.string(), imageId: z.string() }),
    },
    async ({ jobId, imageId }) => {
      const im = sourceImage(jobStore.get(jobId), imageId);
      await checkpoint();
      return {
        content: [
          { type: "text" as const, text: JSON.stringify(im.metadata) },
          {
            type: "image" as const,
            mimeType: "image/png",
            data: im.bytes.toString("base64"),
          },
        ],
      };
    },
  );
  server.registerTool(
    "verify_cad_geometry",
    {
      annotations: {
        readOnlyHint: false,
        destructiveHint: false,
        openWorldHint: false,
      },
      _meta:
        process.env.TRAINAICAD_AUTH_MODE === "supabase"
          ? { securitySchemes: [{ type: "oauth2", scopes: ["openid"] }] }
          : undefined,
      description:
        "Measure identified dimension witnesses, anchored datums, overall sizes and circle fidelity/containment. Bind computed research QA to geometry/source/rule hashes; no production certification.",
      inputSchema: z.object({
        jobId: z.string(),
        checks: z.array(SourceChecks).min(1),
      }),
    },
    async ({ jobId, checks }) =>
      json(publicJob(jobStore.verify(jobId, checks))),
  );
  server.registerTool(
    "get_cad_artifact",
    {
      annotations: {
        readOnlyHint: true,
        destructiveHint: false,
        openWorldHint: false,
      },
      _meta:
        process.env.TRAINAICAD_AUTH_MODE === "supabase"
          ? { securitySchemes: [{ type: "oauth2", scopes: ["openid"] }] }
          : undefined,
      description:
        "Return actual review DXF bytes or an expiring signed download with exact SHA256.",
      inputSchema: z.object({ jobId: z.string() }),
    },
    async ({ jobId }) => {
      const file = artifact(jobStore.get(jobId)),
        info = {
          fileName: file.fileName,
          sha256: file.sha256,
          bytes: file.bytes.length,
          url: file.url,
          status: "REVIEW_ONLY_NO_CUT",
        };
      if (file.url)
        return {
          content: [
            { type: "text" as const, text: JSON.stringify(info) },
            {
              type: "text" as const,
              text: `[Tải ${file.fileName}](${file.url}) — REVIEW ONLY / NO CUT`,
            },
            {
              type: "resource_link" as const,
              uri: file.url,
              name: file.fileName,
              mimeType: "application/dxf",
            },
          ],
        };
      return {
        content: [
          { type: "text" as const, text: JSON.stringify(info) },
          {
            type: "resource" as const,
            resource: {
              uri: `cad-artifact://${jobId}/dxf`,
              mimeType: "application/dxf",
              blob: file.bytes.toString("base64"),
            },
          },
        ],
      };
    },
  );

  return server;
}
