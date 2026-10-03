import { McpServer } from "@modelcontextprotocol/server";
import * as z from "zod/v4";
import { artifact } from "./artifact.js";
import { checkpoint } from "./storage.js";
import { buildServer } from "./server.js";
import { jobStore, publicJob } from "./core.js";
import { rulesBundle, selectRules } from "./snapshot.js";
import { RepoDirectToolInput } from "./repo-direct-tool-schema.js";
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
        "Preferred current-repo path. CALL ONCE PER JOB after routing; for multi-code jobs omit code so all routed codes/rules are returned in one response. Do not call once per part. Reuse this contract for retries. The legacy build_canonical_geometry tool is V0.2 research-only and must NOT be inserted into the repo-direct path. Do not open a replacement job merely because export validation fails; fix the same job/submission and retry.",
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
        workflowPolicy: {
          oneJobPerUserRequest: true,
          reuseSameJobIdOnRetry: true,
          contractCallsPerJob: 1,
          doNotCallLegacyCanonicalBuilder: true,
          doNotFallbackToExternalEzdxfOrAdHocSerializer: true,
          output: "ONE_COMPOSITE_DXF_ONLY",
          individualDxf: "FORBIDDEN_UNLESS_USER_EXPLICITLY_REQUESTS_A_SEPARATE_LEGACY_FLOW",
          callerMustEchoSourceHashes: false,
          callerMustEchoRuleSnapshot: false,
        },
        requiredFlow: [
          "inspect_source",
          "submit_cad_evidence_once",
          "route_cad_parts_once",
          "get_repo_direct_contract_once_for_the_job",
          "construct_one_canonical_entity_model_per_code",
          "execute_current_validation_gates",
          "export_repo_direct_dxf_on_the_same_job",
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
        "PREFERRED E2E export path. Use this directly after repo-direct construction; NEVER call legacy build_canonical_geometry first and NEVER fall back to ad-hoc ezdxf/Python output. The server binds source/DATA hashes and the pinned rule snapshot from jobId, so callers do not need to copy hashes. It verifies route/census/material/count/gate closure, calls repo tools/export_dxf.py in V4.9 SINGLE mode, deletes stale DXFs from prior retries, enforces exactly ONE *_ALL*.dxf composite artifact for the whole requested code set, reopens/audits it, and returns the signed artifact. Individual per-code DXFs are not produced by this path.",
      inputSchema: RepoDirectToolInput,
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
          outputPolicy: "ONE_COMPOSITE_DXF_ONLY",
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
        "Return the signed URL and hash for the single repo-direct composite DXF after export/read-back.",
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
        outputPolicy: "ONE_COMPOSITE_DXF_ONLY",
        fileName: file.fileName,
        sha256: file.sha256,
        url: file.url,
      });
    },
  );

  return server;
}
