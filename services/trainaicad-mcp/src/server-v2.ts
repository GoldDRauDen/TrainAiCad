import { McpServer } from "@modelcontextprotocol/server";
import * as z from "zod/v4";
import { artifact } from "./artifact.js";
import { checkpoint } from "./storage.js";
import { buildServer } from "./server.js";
import { jobStore, publicJob } from "./core.js";
import { rulesBundle, selectRules } from "./snapshot.js";
import { RepoDirectSubmissionV1 } from "./repo-direct.js";
import { exportRepoDirectE2E } from "./repo-direct-e2e.js";

async function json(value: unknown) {
  await checkpoint();
  return {
    content: [{ type: "text" as const, text: JSON.stringify(value, null, 2) }],
  };
}

function oauthMeta() {
  return ["auth0", "supabase"].includes(process.env.TRAINAICAD_AUTH_MODE ?? "")
    ? { securitySchemes: [{ type: "oauth2", scopes: ["openid"] }] }
    : undefined;
}

export function buildServerV2(): McpServer {
  const server = buildServer();

  server.registerTool(
    "get_repo_direct_contract",
    {
      title: "Đọc contract repo-direct hiện hành",
      description:
        "Preferred current-repo path. Return the pinned V4.25 repo-direct flow, routed rule paths, source policy and serializer/gate contract for one job/code. Use this before final DXF construction. The legacy build_canonical_geometry tool is V0.2 research-only and is NOT required by this path.",
      inputSchema: z.object({
        jobId: z.string().min(1),
        code: z.string().min(1).optional(),
      }),
      annotations: {
        readOnlyHint: true,
        destructiveHint: false,
        openWorldHint: false,
      },
      _meta: oauthMeta(),
    },
    async ({ jobId, code }) => {
      const job = jobStore.get(jobId);
      const selectedEvidence = code
        ? job.evidence.filter((e) => e.code === code)
        : job.evidence;
      if (code && !selectedEvidence.length)
        throw new Error("EVIDENCE_CODE_NOT_FOUND");
      const routed = selectedEvidence.map((evidence) => ({
        code: evidence.code,
        selectedPaths: [
          "AI_ENTRYPOINT.md",
          ...selectRules(job.production, job.mode, evidence),
        ],
        route: job.routes.find((route) => route.code === evidence.code) ?? null,
      }));
      const uniquePaths = [...new Set(routed.flatMap((item) => item.selectedPaths))];
      return json({
        preferredPath: "REPO_DIRECT_V4_25_PARITY",
        legacyResearchBuilder: "DO_NOT_USE_FOR_REPO_DIRECT_PARITY",
        release: job.production.release,
        snapshotId: job.production.snapshotId,
        sourceMode: job.mode,
        sourcePolicy: job.sourcePolicy,
        routed,
        rules: rulesBundle(job.production, uniquePaths),
        requiredFlow: [
          "inspect_source",
          "submit_cad_evidence",
          "route_cad_parts",
          "get_cad_rules/get_repo_direct_contract",
          "construct_one_canonical_entity_model_per_code",
          "execute_current_validation_gates",
          "export_repo_direct_dxf",
          "automatic_saved_dxf_readback",
          "get_repo_direct_artifact",
        ],
        productionGate: {
          finalCensusClosed: true,
          sourceFeatureCompleteness: true,
          crossFeatureValidation: true,
          constraintsClosed: true,
          bentPartsRequire: [
            "localFaceTransforms=PASS",
            "foldBackSourceReprojection=PASS",
            "checks.unfold=PASS",
            "checks.bend_domain=PASS",
          ],
          pdfDataRawAlsoRequires: [
            "rawDataSnapshot=PASS",
            "sameParameterGate=PASS",
            "manufacturingChangeLedger=PASS",
            "untouchedDataInvariance=PASS",
            "sourceReprojection=PASS",
          ],
          savedDxfReadback: "executed automatically by export_repo_direct_dxf",
        },
      });
    },
  );

  server.registerTool(
    "export_repo_direct_dxf",
    {
      title: "Xuất DXF theo repo hiện hành",
      description:
        "PREFERRED E2E export path that mirrors the current repo-direct production workflow instead of the limited V0.2 TypeScript canonical builder. Submit the independently interpreted canonical DXF entities plus explicit current-rule validation gates. The server binds source/DATA hashes + rule snapshot, verifies route/census/material/count/gate closure, calls the repo-approved tools/export_dxf.py serializer, reopens/audits the saved DXF with PASS/review-aware label checks, and returns a signed artifact URL. Supports bent/multi-face parts and features without V02_BENT_FEATURE_TRANSFORM_NOT_IMPLEMENTED or V02_LINEAR_CHAIN_AXIS_UNSUPPORTED because local-face transforms are solved upstream under the active repo rules, exactly as repo-direct production does.",
      inputSchema: RepoDirectSubmissionV1,
      annotations: {
        readOnlyHint: false,
        destructiveHint: false,
        openWorldHint: false,
      },
      _meta: oauthMeta(),
    },
    async (submission) => {
      const result = exportRepoDirectE2E(submission);
      return json({
        ...publicJob(result.job),
        repoDirect: {
          path: "REPO_DIRECT_V4_25_PARITY",
          submissionSha256: result.submissionSha256,
          savedDxfReadback: result.job.dxfAudit,
        },
        artifact: result.artifact,
      });
    },
  );

  server.registerTool(
    "get_repo_direct_artifact",
    {
      title: "Lấy DXF repo-direct",
      description:
        "Return the signed URL and hash for a repo-direct DXF after export/read-back.",
      inputSchema: z.object({ jobId: z.string().min(1) }),
      annotations: {
        readOnlyHint: true,
        destructiveHint: false,
        openWorldHint: false,
      },
      _meta: oauthMeta(),
    },
    async ({ jobId }) => {
      const job = jobStore.get(jobId);
      const file = artifact(job);
      return json({
        jobId,
        state: job.state,
        fileName: file.fileName,
        sha256: file.sha256,
        url: file.url,
      });
    },
  );

  return server;
}
