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
        "Preferred current-repo path. CALL ONCE PER JOB after routing; for multi-code jobs omit code so all routed codes/rules are returned in one response. Do not call once per part. Reuse this contract for retries. The legacy build_canonical_geometry tool is V0.2 research-only and must NOT be inserted into the repo-direct path. Do not open a replacement job merely because export validation fails; fix/reuse the same job. IMPORTANT: do NOT ask the user merely because a route, census, semantic check, material/check gate or other reviewable validation is uncertain while usable geometry can still be constructed from the source. Submit the best source-supported canonical geometry on the same job; export_repo_direct_dxf will automatically downgrade affected parts to FLAG/PREVIEW and emit one REVIEW_ONLY - NO CUT composite DXF. Ask the user only for a genuine hard blocker where meaningful geometry cannot be constructed/resolved from the available authority, the source is missing/unreadable/conflicting, integrity binding fails, or an explicit user choice is required.",
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
          reviewableAmbiguity: "AUTO_FLAG_AND_CONTINUE",
          userQuestionPolicy: "ONLY_FOR_HARD_BLOCKERS",
          reviewOutput: "ONE_COMPOSITE_ALL_REVIEW_ONLY_NO_CUT",
          hardBlockers: [
            "meaningful_geometry_cannot_be_constructed_from_available_source_authority",
            "source_missing_or_unreadable",
            "source_authority_conflict_that_changes_geometry",
            "immutable_source_or_rule_hash_binding_failure",
            "malformed_or_structurally_unsafe_geometry",
            "explicit_user_choice_required_to_resolve_two_or_more_valid_geometries",
          ],
        },
        requiredFlow: [
          "inspect_source",
          "submit_cad_evidence_once",
          "route_cad_parts_once",
          "get_repo_direct_contract_once_for_the_job",
          "construct_one_canonical_entity_model_per_code_from_best_source_supported_interpretation",
          "execute_current_validation_gates",
          "auto_flag_reviewable_ambiguity_without_asking_user",
          "export_repo_direct_dxf_on_the_same_job",
          "automatic_saved_dxf_readback",
          "get_repo_direct_artifact",
        ],
        productionGate: {
          passRequires: {
            finalCensusClosed: true,
            sourceFeatureCompleteness: true,
            crossFeatureValidation: true,
            constraintsClosed: true,
          },
          reviewableFailureBehavior:
            "DOWNGRADE_AFFECTED_PART_TO_FLAGGED_PREVIEW_AND_EXPORT_GLOBAL_REVIEW_ONLY_NO_CUT_COMPOSITE",
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
        "PREFERRED E2E export path. Use directly after repo-direct construction; NEVER call legacy build_canonical_geometry first and NEVER fall back to ad-hoc ezdxf/Python output. The server binds source/DATA hashes and pinned rule snapshot from jobId. It enforces one composite DXF, reopens/audits it, and returns the signed artifact. REVIEWABLE ambiguity is NOT a reason to ask the user or abort: if canonical geometry is still constructable, the server auto-flags/downgrades affected parts to PREVIEW and returns one *_ALL_REVIEW_ONLY.dxf containing all requested codes with REVIEW ONLY - NO CUT annotations. Only hard integrity/source/structural failures that prevent meaningful geometry remain blocking. Individual per-code DXFs are never produced by this path.",
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
      const reviewOnly = result.job.flags.some((flag) =>
        flag !== "MCP_REPO_DIRECT_PARITY_NON_AUTHORITY",
      );
      return json({
        ...publicJob(result.job),
        repoDirect: {
          path: "REPO_DIRECT_V4_25_PARITY",
          outputPolicy: "ONE_COMPOSITE_DXF_ONLY",
          reviewPolicy: "AUTO_FLAG_REVIEWABLE_AMBIGUITY_NO_USER_QUESTION",
          deliveryState: reviewOnly ? "REVIEW_ONLY_NO_CUT" : "PASS_GEOMETRY_AUDITED",
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
        "Return the signed URL and hash for the single repo-direct composite DXF after export/read-back. A flagged job may legitimately return an *_ALL_REVIEW_ONLY.dxf artifact; that is the expected no-cut review output, not a reason to ask the user before delivery.",
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
