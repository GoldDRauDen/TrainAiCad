import { createHash, randomUUID } from "node:crypto";
import { existsSync, readFileSync, realpathSync } from "node:fs";
import { dirname, isAbsolute, join, relative, resolve } from "node:path";
import { atomicWriteJson, bindSourceToJob, dataRoot, verifiedSource, type IngestResult, type SourceRole } from "./ingest.js";
import { jevStatus } from "./jev.js";
import { buildJobGeometry, GeometrySourceV1 } from "./geometry.js";
import { exportWithBridge, auditWithBridge, type ManufacturingQaV1 } from "./dxf.js";
import { createRuleSnapshot, extendRuleSnapshot, readPinnedRuleBundle, verifyRuleSnapshot } from "./rules.js";
import {
  CadEvidenceV1,
  type CadEvidenceV1 as Evidence,
  type CadJob,
  type DxfRole,
  type JobMode,
  type JobModeRequested,
  type JobState,
  type PartClass,
  type ReleasePin,
  type SourceViewReceipt,
  type RouteResult,
  type SourceManifestV2,
  type SourceDescriptor,
  type SourcePolicy
} from "./model.js";

function sha256(text: string): string {
  return createHash("sha256").update(text).digest("hex");
}

export function resolveRepoRoot(start = process.env.TRAINAICAD_REPO_ROOT ?? process.cwd()): string {
  let current = resolve(start);
  for (;;) {
    const entry = join(current, "AI_ENTRYPOINT.md");
    const skill = join(current, "skills/lispcad/portable/SKILL_LISPCAD_CURRENT.md");
    if (existsSync(entry) && existsSync(skill)) return current;
    const parent = dirname(current);
    if (parent === current) throw new Error("SKILL_FRESHNESS_UNVERIFIED: TrainAiCad repo root not found");
    current = parent;
  }
}

export function readReleasePin(repoRoot = resolveRepoRoot()): ReleasePin {
  const entrypoint = readFileSync(join(repoRoot, "AI_ENTRYPOINT.md"), "utf8");
  const currentSkill = readFileSync(
    join(repoRoot, "skills/lispcad/portable/SKILL_LISPCAD_CURRENT.md"),
    "utf8"
  );

  const entryMatch = entrypoint.match(/Current production release is \*\*(V\d+\.\d+)\*\*/);
  const skillMatch = currentSkill.match(/^# SKILL_LISPCAD (V\d+\.\d+) PORTABLE/m);
  if (!entryMatch?.[1] || !skillMatch?.[1] || entryMatch[1] !== skillMatch[1]) {
    throw new Error("SKILL_FRESHNESS_UNVERIFIED: AI_ENTRYPOINT and CURRENT disagree");
  }

  return {
    release: entryMatch[1],
    entrypointSha256: sha256(entrypoint),
    currentSkillSha256: sha256(currentSkill),
    ...(() => {
      const rules = createRuleSnapshot(repoRoot);
      return { ruleFiles: rules.files, ruleSnapshotSha256: rules.sha256 };
    })()
  };
}

export const allowedTransitions: Readonly<Record<JobState, readonly JobState[]>> = {
  CREATED: ["SOURCE_READY"],
  SOURCE_READY: ["EVIDENCE_READY"],
  EVIDENCE_READY: ["ROUTED", "REVIEW_REQUIRED"],
  ROUTED: ["EVIDENCE_READY", "GEOMETRY_READY", "REVIEW_REQUIRED"],
  REVIEW_REQUIRED: ["EVIDENCE_READY", "GEOMETRY_READY"],
  GEOMETRY_READY: ["DXF_WRITTEN"],
  DXF_WRITTEN: ["DXF_READBACK"],
  DXF_READBACK: ["QA_COMPLETE"],
  QA_COMPLETE: ["PRODUCTION_PASS"],
  PRODUCTION_PASS: [],
  REVIEW_ONLY: [],
  VIEWS_ONLY: [],
  SOURCE_CONFLICT: []
};

export function assertTransition(from: JobState, to: JobState): void {
  if (!allowedTransitions[from].includes(to)) {
    throw new Error(`INVALID_JOB_TRANSITION: ${from} -> ${to}`);
  }
}

export function resolveJobMode(
  requested: JobModeRequested,
  hasDxf: boolean,
  declaredReference = false
): JobMode {
  if (requested === "AUTO") {
    if (declaredReference) {
      if (!hasDxf) throw new Error("TRAIN_REFERENCE requires DXF");
      return "TRAIN_REFERENCE";
    }
    return hasDxf ? "PDF_DATA_RAW" : "PDF_ONLY";
  }

  if (requested === "PDF_ONLY") {
    if (hasDxf) throw new Error("PDF_ONLY cannot include DXF; use AUTO/PDF_DATA_RAW/TRAIN_REFERENCE");
    return requested;
  }

  if (requested === "PDF_DATA_RAW") {
    if (!hasDxf) throw new Error("PDF_DATA_RAW requires DXF");
    if (declaredReference) throw new Error("PDF_DATA_RAW cannot use an explicitly declared reference DXF");
    return requested;
  }

  if (requested === "TRAIN_REFERENCE") {
    if (!hasDxf) throw new Error("TRAIN_REFERENCE requires DXF");
    return requested;
  }

  if (!hasDxf) throw new Error("DIRECT_EXISTING_DXF_AUDIT requires approved reference DXF");
  return "DIRECT_EXISTING_DXF_AUDIT";
}

export function sourcePolicyForMode(mode: JobMode): SourcePolicy {
  switch (mode) {
    case "PDF_ONLY":
      return {
        geometryAuthority: "PDF_OR_IMAGE",
        semanticAuthority: "PDF_OR_IMAGE",
        dxfUse: "NONE"
      };
    case "PDF_DATA_RAW":
      return {
        geometryAuthority: "DATA_DXF",
        semanticAuthority: "PDF_OR_IMAGE_CONTROL",
        dxfUse: "RAW_GEOMETRY"
      };
    case "TRAIN_REFERENCE":
      return {
        geometryAuthority: "PDF_OR_IMAGE_INDEPENDENT",
        semanticAuthority: "PDF_OR_IMAGE_INDEPENDENT",
        dxfUse: "AUDIT_ONLY"
      };
    case "DIRECT_EXISTING_DXF_AUDIT":
      return {
        geometryAuthority: "AI_DXF_VS_APPROVED_REFERENCE",
        semanticAuthority: "AUDIT_PAIR_FIRST_THEN_SOURCE",
        dxfUse: "GROUND_TRUTH_AUDIT"
      };
  }
}

function dxfRoleForMode(mode: JobMode): DxfRole | undefined {
  if (mode === "PDF_DATA_RAW") return "DATA_DXF";
  if (mode === "TRAIN_REFERENCE") return "TRAIN_REFERENCE";
  if (mode === "DIRECT_EXISTING_DXF_AUDIT") return "APPROVED_REFERENCE";
  return undefined;
}

/**
 * Source-mode invariant: a bound DXF source must be reflected by the job mode,
 * and `PDF_ONLY` may never coexist with a bound DXF. Returns the mode after the
 * binding (unchanged when the binding needs no reclassification) or throws.
 * Mode is reclassifiable only while the job is still SOURCE_READY; after
 * evidence is submitted the mode is locked and a mode-changing binding is
 * rejected instead.
 */
export function modeAfterBinding(mode: JobMode, state: JobState, role: SourceRole): JobMode {
  if (role === "DRAWING") return mode;

  let next: JobMode;
  if (role === "DATA_DXF") {
    if (mode === "PDF_ONLY") next = "PDF_DATA_RAW";
    else if (mode === "PDF_DATA_RAW") return mode;
    else throw new Error(`SOURCE_CONFLICT: DATA_DXF cannot bind to ${mode}`);
  } else if (role === "REFERENCE_DXF") {
    if (mode === "PDF_ONLY") next = "TRAIN_REFERENCE";
    else if (mode === "TRAIN_REFERENCE" || mode === "DIRECT_EXISTING_DXF_AUDIT") return mode;
    else throw new Error(`SOURCE_CONFLICT: REFERENCE_DXF cannot bind to ${mode}`);
  } else {
    // AI_DXF: fail-closed, only the direct audit mode accepts an AI-exported DXF
    if (mode === "DIRECT_EXISTING_DXF_AUDIT") return mode;
    throw new Error(`AI_DXF_NOT_ALLOWED_IN_${mode}`);
  }

  if (state !== "SOURCE_READY") throw new Error(`SOURCE_MODE_LOCKED: ${state}`);
  return next;
}

class JobStore {
  private jobs = new Map<string, CadJob>();

  private file(jobId: string): string {
    return join(dataRoot(), "jobs", `${jobId}.json`);
  }

  private persist(job: CadJob): void {
    atomicWriteJson(this.file(job.jobId), job);
  }

  private refreshSourceManifest(job: CadJob): void {
    const verified = Object.values(job.sourceBindings);
    const sources: SourceManifestV2["sources"] = verified.length
      ? verified.map((source) => ({
          role: source.role as SourceManifestV2["sources"][number]["role"],
          fileName: source.fileName,
          sha256: source.sha256,
          mimeType: source.mimeType,
          verified: true
        }))
      : [{
          role: "DRAWING",
          fileName: job.source.fileName,
          sha256: job.source.sha256,
          mimeType: job.source.mimeType ?? "application/pdf",
          verified: false
        }];
    const previous = job.sourceManifest;
    job.sourceManifest = {
      schema: "SOURCE_MANIFEST_V2",
      revision: (previous?.revision ?? 0) + 1,
      sources,
      pageCodeMap: job.evidence.map((evidence) => ({
        code: evidence.code,
        sourceSha256: evidence.source.sourceId,
        page: evidence.source.page,
        visualReceiptIds: [...evidence.source.visualReceiptIds],
        ...(evidence.source.revision !== undefined ? { revision: evidence.source.revision } : {})
      })),
      updatedAt: new Date().toISOString()
    };
  }

  private normalizePersisted(raw: unknown): CadJob {
    const legacy = raw as Omit<CadJob, "mode"> & {
      mode: JobMode | "NEW_PDF_TO_DXF";
      referenceDxf?: SourceDescriptor;
      sourcePolicy?: SourcePolicy;
    };

    if (legacy.mode === "NEW_PDF_TO_DXF") {
      const oldReference = legacy.referenceDxf;
      legacy.mode = oldReference ? "TRAIN_REFERENCE" : "PDF_ONLY";
      legacy.dxf = legacy.dxf ?? oldReference;
      legacy.dxfRole = oldReference ? "TRAIN_REFERENCE" : undefined;
      delete legacy.referenceDxf;
    }

    legacy.sourcePolicy = legacy.sourcePolicy ?? sourcePolicyForMode(legacy.mode as JobMode);
    const hasPinnedRuleFiles = Array.isArray(legacy.production.ruleFiles) && legacy.production.ruleFiles.length > 0;
    legacy.sourceVerified = hasPinnedRuleFiles ? (legacy.sourceVerified ?? false) : false;
    legacy.sourceBindings = legacy.sourceBindings ?? {};
    legacy.sourceManifest = legacy.sourceManifest ?? {
      schema: "SOURCE_MANIFEST_V2",
      revision: 0,
      sources: [],
      pageCodeMap: [],
      updatedAt: legacy.updatedAt
    };
    legacy.sourceViewReceipts = legacy.sourceViewReceipts ?? [];
    legacy.production.ruleFiles = legacy.production.ruleFiles ?? [];
    legacy.production.ruleSnapshotSha256 = legacy.production.ruleSnapshotSha256 ?? sha256(JSON.stringify([]));
    legacy.geometrySources = legacy.geometrySources ?? [];
    legacy.geometry = legacy.geometry ?? [];
    legacy.manufacturingQa = legacy.manufacturingQa ?? [];
    const expectedGeometryPinned = Boolean(legacy.dxfOutput?.serializerInputSha256 && legacy.dxfOutput?.manifestSha256);
    if ((legacy.state === "PRODUCTION_PASS" && !hasPinnedRuleFiles) || (legacy.dxfOutput && !expectedGeometryPinned)) {
      legacy.state = "REVIEW_REQUIRED";
      legacy.flags = [...new Set([...(legacy.flags ?? []), "LEGACY_READBACK_BASIS_UNVERIFIED"] )];
      legacy.dxfAudit = undefined;
      legacy.dxfOutput = undefined;
      legacy.manufacturingQa = legacy.manufacturingQa.map((qa) => ({ ...qa, approvedForExport: false }));
    }
    return legacy as CadJob;
  }

  create(
    source: SourceDescriptor,
    dxf: SourceDescriptor | undefined,
    requested: JobModeRequested,
    declaredReference = false
  ): CadJob {
    const now = new Date().toISOString();
    const mode = resolveJobMode(requested, Boolean(dxf), declaredReference);
    const job: CadJob = {
      jobId: `cad_${randomUUID().replaceAll("-", "").slice(0, 16)}`,
      mode,
      sourcePolicy: sourcePolicyForMode(mode),
      state: "CREATED",
      production: readReleasePin(),
      source,
      sourceVerified: false,
      sourceBindings: {},
      sourceManifest: {
        schema: "SOURCE_MANIFEST_V2",
        revision: 1,
        sources: [{ role: "DRAWING", fileName: source.fileName, sha256: source.sha256, mimeType: source.mimeType ?? "application/pdf", verified: false }],
        pageCodeMap: [],
        updatedAt: now
      },
      sourceViewReceipts: [],
      dxf,
      dxfRole: dxfRoleForMode(mode),
      evidence: [],
      routes: [],
      geometrySources: [],
      geometry: [],
      manufacturingQa: [],
      flags: [],
      createdAt: now,
      updatedAt: now
    };
    this.jobs.set(job.jobId, job);
    this.persist(job);
    return this.transition(job.jobId, "SOURCE_READY");
  }

  createFromIngestedSources(
    drawing: Pick<IngestResult, "fileName" | "sha256"> & { mimeType?: string },
    dxf: (Pick<IngestResult, "fileName" | "sha256"> & { mimeType?: string }) | undefined,
    requested: JobModeRequested,
    declaredReference = false
  ): CadJob {
    const drawingBytes = verifiedSource("DRAWING", drawing.fileName, drawing.sha256);
    const dxfRole: SourceRole | undefined = dxf ? (declaredReference ? "REFERENCE_DXF" : "DATA_DXF") : undefined;
    const dxfBytes = dxf && dxfRole ? verifiedSource(dxfRole, dxf.fileName, dxf.sha256) : undefined;
    const job = this.create(
      { fileName: drawingBytes.fileName, sha256: drawingBytes.sha256, sourceId: drawingBytes.sha256, mimeType: drawingBytes.mimeType },
      dxfBytes ? { fileName: dxfBytes.fileName, sha256: dxfBytes.sha256, mimeType: dxfBytes.mimeType } : undefined,
      requested,
      declaredReference
    );
    job.sourceVerified = true;
    job.sourceBindings.DRAWING = sourceSnapshot("DRAWING", drawingBytes);
    if (dxfBytes && dxfRole) job.sourceBindings[dxfRole] = sourceSnapshot(dxfRole, dxfBytes);
    this.refreshSourceManifest(job);
    this.persist(job);
    return job;
  }

  get(jobId: string): CadJob {
    if (!/^cad_[a-f0-9]{16}$/.test(jobId)) throw new Error(`INVALID_JOB_ID: ${jobId}`);
    let job = this.jobs.get(jobId);
    if (!job) {
      const file = this.file(jobId);
      if (existsSync(file)) {
        job = this.normalizePersisted(JSON.parse(readFileSync(file, "utf8")));
        this.jobs.set(jobId, job);
        this.persist(job);
      }
    }
    if (!job) throw new Error(`JOB_NOT_FOUND: ${jobId}`);
    return job;
  }

  transition(jobId: string, next: JobState): CadJob {
    const job = this.get(jobId);
    assertTransition(job.state, next);
    job.state = next;
    job.updatedAt = new Date().toISOString();
    this.persist(job);
    return job;
  }

  submitEvidence(jobId: string, raw: unknown[]): CadJob {
    const job = this.get(jobId);
    if (!["SOURCE_READY", "ROUTED", "REVIEW_REQUIRED"].includes(job.state)) {
      throw new Error(`EVIDENCE_NOT_ACCEPTED_IN_STATE: ${job.state}`);
    }
    const parsed = raw.map((item) => CadEvidenceV1.parse(item));
    for (const item of parsed) {
      if (item.jobId !== jobId) throw new Error(`EVIDENCE_JOB_MISMATCH: ${item.jobId}`);
      if (item.source.sourceId !== (job.source.sourceId ?? job.source.sha256)) {
        throw new Error(`EVIDENCE_SOURCE_MISMATCH: ${item.code}`);
      }
      if (job.sourceVerified) {
        const validReceipts = new Set(job.sourceViewReceipts.filter((r) => r.page === item.source.page).map((r) => r.receiptId));
        if (!item.source.visualReceiptIds.length || item.source.visualReceiptIds.some((id) => !validReceipts.has(id))) {
          throw new Error(`SOURCE_IMAGE_NOT_INSPECTED:${item.code}:PAGE_${item.source.page}`);
        }
      }
    }
    const seen = new Set<string>();
    for (const item of parsed) {
      if (seen.has(item.code)) throw new Error(`DUPLICATE_CODE: ${item.code}`);
      seen.add(item.code);
    }
    job.evidence = parsed;
    job.routes = [];
    job.geometrySources = [];
    job.geometry = [];
    job.manufacturingQa = [];
    job.dxfOutput = undefined;
    job.dxfAudit = undefined;
    job.flags = [];
    this.refreshSourceManifest(job);
    if (job.state === "SOURCE_READY") return this.transition(jobId, "EVIDENCE_READY");
    job.state = "EVIDENCE_READY";
    job.updatedAt = new Date().toISOString();
    this.persist(job);
    return job;
  }

  setRoutes(jobId: string, routes: RouteResult[]): CadJob {
    const job = this.get(jobId);
    if (job.state !== "EVIDENCE_READY") {
      throw new Error(`ROUTING_NOT_ALLOWED_IN_STATE: ${job.state}`);
    }
    job.routes = routes;
    job.geometrySources = [];
    job.geometry = [];
    job.manufacturingQa = [];
    job.dxfOutput = undefined;
    job.dxfAudit = undefined;
    const harvestFlags = job.sourceGeometryHarvest
      ? ["DATA_DXF_HARVEST_REVIEW_REQUIRED", ...job.sourceGeometryHarvest.flags.map((flag) => `DATA_DXF:${flag}`)]
      : [];
    job.flags = [...new Set([
      ...routes.flatMap((r) => r.flags.map((flag) => `${r.code}:${flag}`)),
      ...harvestFlags
    ])];
    if (!job.flags.length) {
      job.flags = routes
        .filter((r) => r.status === "REVIEW_REQUIRED")
        .map((r) => `${r.code}:ROUTING_REVIEW_REQUIRED`);
    }
    return this.transition(jobId, job.flags.length ? "REVIEW_REQUIRED" : "ROUTED");
  }

  recordSourceGeometryHarvest(jobId: string, harvest: CadJob["sourceGeometryHarvest"]): CadJob {
    const job = this.get(jobId);
    if (!harvest) throw new Error("DATA_DXF_HARVEST_RESULT_MISSING");
    if (job.mode !== "PDF_DATA_RAW") throw new Error(`DATA_DXF_HARVEST_NOT_ALLOWED_IN_${job.mode}`);
    if (!job.sourceBindings.DATA_DXF || job.sourceBindings.DATA_DXF.sha256 !== harvest?.sourceSha256) {
      throw new Error("DATA_DXF_HARVEST_SOURCE_MISMATCH");
    }
    if (["REVIEW_ONLY", "VIEWS_ONLY", "SOURCE_CONFLICT"].includes(job.state)) {
      throw new Error(`DATA_DXF_HARVEST_NOT_ALLOWED_IN_STATE:${job.state}`);
    }
    const changed = job.sourceGeometryHarvest?.ledgerSha256 !== harvest.ledgerSha256;
    job.sourceGeometryHarvest = harvest;
    job.flags = [...new Set([
      ...job.flags,
      "DATA_DXF_HARVEST_REVIEW_REQUIRED",
      ...harvest.flags.map((flag) => `DATA_DXF:${flag}`)
    ])];
    job.geometrySources = [];
    job.geometry = [];
    job.manufacturingQa = [];
    job.dxfOutput = undefined;
    job.dxfAudit = undefined;
    if (changed) job.flags = [...new Set([...job.flags, "SOURCE_GEOMETRY_LEDGER_CHANGED_REQUIRES_REVIEW"])];
    job.state = "REVIEW_REQUIRED";
    job.updatedAt = new Date().toISOString();
    this.persist(job);
    return job;
  }

  buildGeometry(jobId: string, rawSources: unknown[]): CadJob {
    const job = this.get(jobId);
    if (job.sourceVerified) this.assertRuleBundleRead(jobId);
    const parsed = rawSources.map((raw) => GeometrySourceV1.parse(raw));
    const built = buildJobGeometry(job, parsed);

    job.geometrySources = parsed;
    job.geometry = built.ready;
    job.manufacturingQa = [];
    job.dxfOutput = undefined;
    job.dxfAudit = undefined;
    job.flags = built.flags;
    job.updatedAt = new Date().toISOString();
    this.persist(job);

    if (built.flags.length) {
      if (job.state === "REVIEW_REQUIRED") return job;
      return this.transition(jobId, "REVIEW_REQUIRED");
    }
    return this.transition(jobId, "GEOMETRY_READY");
  }

  exportDxf(jobId: string, rawQa: unknown[]): CadJob {
    const job = this.get(jobId);
    if (!job.sourceVerified) throw new Error("PRODUCTION_SOURCE_UNVERIFIED");
    const machineQa = this.runManufacturingQa(jobId);
    const requiredKeys = ["contour_topology", "datum", "feature_count", "containment", "material_rules"] as const;
    if (machineQa.some((q) => !q.approvedForExport || requiredKeys.some((key) => q.checks[key] !== "PASS"))) {
      throw new Error(`PRODUCTION_QA_FAILED:${machineQa.map((q) => `${q.code}:${Object.entries(q.checks).filter(([k, v]) => requiredKeys.includes(k as typeof requiredKeys[number]) && v !== "PASS").map(([k, v]) => `${k}=${v}`).join(",")}`).join(";")}`);
    }
    // Kept in the method signature during the client migration; caller-supplied checks never authorize export.
    void rawQa;
    const exported = exportWithBridge(job, machineQa, resolveRepoRoot());
    job.manufacturingQa = exported.qa;
    job.dxfOutput = exported.output;
    job.dxfAudit = undefined;
    job.flags = [];
    job.updatedAt = new Date().toISOString();
    this.persist(job);
    return this.transition(jobId, "DXF_WRITTEN");
  }

  runManufacturingQa(jobId: string): ManufacturingQaV1[] {
    const job = this.get(jobId);
    if (!job.sourceVerified) throw new Error("PRODUCTION_SOURCE_UNVERIFIED");
    if (!job.geometry.length) throw new Error("QA_GEOMETRY_MISSING");
    const qa = evaluateManufacturingQa(job);
    job.manufacturingQa = qa;
    job.updatedAt = new Date().toISOString();
    this.persist(job);
    return qa;
  }

  getRuleBundle(jobId: string) {
    const job = this.get(jobId);
    const snapshot = {
      files: job.production.ruleFiles ?? [],
      sha256: job.production.ruleSnapshotSha256 ?? ""
    };
    const bundle = readPinnedRuleBundle(resolveRepoRoot(), snapshot);
    job.ruleBundleReadSha256 = bundle.snapshotSha256;
    job.updatedAt = new Date().toISOString();
    this.persist(job);
    return bundle;
  }

  assertRuleBundleRead(jobId: string): void {
    const job = this.get(jobId);
    const snapshot = {
      files: job.production.ruleFiles ?? [],
      sha256: job.production.ruleSnapshotSha256 ?? ""
    };
    verifyRuleSnapshot(resolveRepoRoot(), snapshot);
    if (!job.ruleBundleReadSha256 || job.ruleBundleReadSha256 !== snapshot.sha256) {
      throw new Error("JOB_RULE_BUNDLE_NOT_READ_OR_STALE");
    }
  }

  auditDxf(jobId: string): CadJob {
    const job = this.get(jobId);
    if (job.sourceVerified) this.assertRuleBundleRead(jobId);
    if (job.state !== "DXF_WRITTEN") {
      throw new Error(`DXF_AUDIT_NOT_ALLOWED_IN_STATE: ${job.state}`);
    }
    if (!job.dxfOutput) throw new Error("DXF_AUDIT_NO_OUTPUT");
    job.dxfAudit = auditWithBridge(job.dxfOutput, resolveRepoRoot());
    job.updatedAt = new Date().toISOString();
    this.persist(job);
    this.transition(jobId, "DXF_READBACK");
    this.transition(jobId, "QA_COMPLETE");
    if (!job.sourceVerified || !job.manufacturingQa.length || !job.manufacturingQa.every((q) => q.approvedForExport)) {
      throw new Error("PRODUCTION_ACCEPTANCE_EVIDENCE_MISSING");
    }
    return this.transition(jobId, "PRODUCTION_PASS");
  }

  readDxfArtifact(jobId: string): { uri: string; fileName: string; sha256: string; bytes: Buffer } {
    const job = this.get(jobId);
    if (job.state !== "PRODUCTION_PASS" || !job.dxfOutput || !job.dxfAudit?.ok) {
      throw new Error("DXF_ARTIFACT_NOT_PRODUCTION_READY");
    }
    this.assertRuleBundleRead(jobId);
    const allowedDir = realpathSync(join(dataRoot(), "outputs", jobId));
    const actualPath = realpathSync(job.dxfOutput.absolutePath);
    const pathFromJobDir = relative(allowedDir, actualPath);
    if (!pathFromJobDir || pathFromJobDir === ".." || pathFromJobDir.startsWith(`..${process.platform === "win32" ? "\\" : "/"}`) || isAbsolute(pathFromJobDir)) {
      throw new Error("DXF_ARTIFACT_OUTSIDE_JOB_OUTPUT");
    }
    const bytes = readFileSync(actualPath);
    const actualSha256 = createHash("sha256").update(bytes).digest("hex");
    if (actualSha256 !== job.dxfOutput.fileSha256) throw new Error("DXF_ARTIFACT_HASH_MISMATCH");
    const serializerInput = join(allowedDir, "serializer_input.json");
    const manifest = job.dxfOutput.manifestPath;
    if (!existsSync(serializerInput) || !existsSync(manifest) ||
        createHash("sha256").update(readFileSync(serializerInput)).digest("hex") !== job.dxfOutput.serializerInputSha256 ||
        createHash("sha256").update(readFileSync(manifest)).digest("hex") !== job.dxfOutput.manifestSha256) {
      throw new Error("DXF_ARTIFACT_AUDIT_BASIS_CHANGED");
    }
    return {
      uri: `trainaicad://jobs/${jobId}/artifacts/${actualSha256}`,
      fileName: job.dxfOutput.fileName,
      sha256: actualSha256,
      bytes
    };
  }

  /**
   * Bind an ingested source and keep the source-mode invariant: the job mode,
   * source policy and dxf descriptor are reclassified (or the binding is
   * rejected) so `PDF_ONLY` can never carry a DXF source. Rejects before any
   * write, so a refused binding leaves both the job and the binding file alone.
   */
  bindSource(jobId: string, role: SourceRole, source: IngestResult): { job: CadJob; bound: Record<string, IngestResult> } {
    const job = this.get(jobId);
    const next = modeAfterBinding(job.mode, job.state, role);
    if (role === "DRAWING" && source.sha256 !== job.source.sha256) {
      throw new Error(`SOURCE_DESCRIPTOR_MISMATCH:DRAWING:${job.source.sha256}->${source.sha256}`);
    }
    const bound = bindSourceToJob(jobId, role, source);
    if (next !== job.mode) {
      job.mode = next;
      job.sourcePolicy = sourcePolicyForMode(next);
      job.dxf = {
        fileName: source.fileName,
        sha256: source.sha256,
        mimeType: source.mimeType
      };
      job.dxfRole = dxfRoleForMode(next);
      job.updatedAt = new Date().toISOString();
      this.persist(job);
    }
    job.sourceBindings[role] = sourceSnapshot(role, source);
    if (role === "DRAWING") job.sourceVerified = true;
    this.refreshSourceManifest(job);
    job.updatedAt = new Date().toISOString();
    this.persist(job);
    return { job, bound };
  }
}

export const jobStore = new JobStore();

function sourceSnapshot(role: SourceRole, source: IngestResult) {
  return { role, fileName: source.fileName, sha256: source.sha256, mimeType: source.mimeType, storedPath: source.storedPath };
}

export function recordSourceViewReceipt(jobId: string, receipt: SourceViewReceipt): CadJob {
  const job = jobStore.get(jobId);
  if (!job.sourceVerified || receipt.sourceSha256 !== job.source.sha256) throw new Error("SOURCE_VIEW_SOURCE_MISMATCH");
  if (!Number.isInteger(receipt.page) || receipt.page < 1 || !Number.isFinite(receipt.dpi)) throw new Error("SOURCE_VIEW_METADATA_INVALID");
  const [x0, y0, x1, y1] = receipt.region;
  if ([x0, y0, x1, y1].some((n) => !Number.isFinite(n) || n < 0 || n > 1) || x0 >= x1 || y0 >= y1) throw new Error("SOURCE_VIEW_REGION_INVALID");
  if (![0, 90, 180, 270].includes(receipt.rotation ?? 0)) throw new Error("SOURCE_VIEW_ROTATION_INVALID");
  if (!/^[a-f0-9]{64}$/i.test(receipt.imageSha256)) throw new Error("SOURCE_VIEW_IMAGE_HASH_INVALID");
  if (!job.sourceViewReceipts.some((r) => r.receiptId === receipt.receiptId)) job.sourceViewReceipts.push(receipt);
  job.updatedAt = new Date().toISOString();
  // Persist through the public transition API without changing job state.
  saveJob(job);
  return job;
}

function saveJob(job: CadJob): void {
  atomicWriteJson(join(dataRoot(), "jobs", `${job.jobId}.json`), job);
}

function evaluateManufacturingQa(job: CadJob): import("./dxf.js").ManufacturingQaV1[] {
  return job.geometry.map((g) => {
    const evidence = job.evidence.find((e) => e.code === g.code)!;
    const inventoryOk = featureInventoryMatches(evidence, g.features);
    const hasFeatures = evidence.features.length > 0 || evidence.markings.length > 0;
    const datumOk = evidence.features.every((f) => Boolean(f.datum?.axis && f.datum.target === "FEATURE_CENTER"));
    const spans = g.outerContours[0]?.length ? {
      x: Math.max(...g.outerContours[0]!.map((p) => p.x)) - Math.min(...g.outerContours[0]!.map((p) => p.x)),
      y: Math.max(...g.outerContours[0]!.map((p) => p.y)) - Math.min(...g.outerContours[0]!.map((p) => p.y))
    } : undefined;
    const contourMatches = Boolean(spans &&
      (evidence.contour.overallX === undefined || Math.abs(spans.x - evidence.contour.overallX.value) <= 1e-6) &&
      (evidence.contour.overallY === undefined || Math.abs(spans.y - evidence.contour.overallY.value) <= 1e-6));
    const noBends = g.bendZones.length === 0;
    const check = (ok: boolean): "PASS" | "N/A" => ok ? "PASS" : "N/A";
    const checks: ManufacturingQaV1["checks"] = {
      contour_topology: check(g.outerContours.length === 1 && g.qa.topologyClosed && contourMatches),
      datum: hasFeatures ? check(datumOk) : "N/A",
      feature_count: check(inventoryOk),
      unfold: "N/A",
      containment: "N/A",
      bend_domain: "N/A",
      material_rules: "N/A",
      slot_semantics: "N/A"
    };
    const requiredKeys = ["contour_topology", "datum", "feature_count", "containment", "material_rules"] as const;
    return {
      schema: "MANUFACTURING_QA_V1" as const,
      jobId: job.jobId,
      code: g.code,
      checks,
      foldBack: noBends ? "N/A" : "N/A",
      approvedForExport: requiredKeys.every((key) => checks[key] === "PASS")
    };
  });
}

function featureInventoryMatches(evidence: Evidence, features: CadJob["geometry"][number]["features"]): boolean {
  const ids = new Set<string>();
  for (const item of evidence.features) {
    if (ids.has(item.id)) return false;
    ids.add(item.id);
    const instances = features.filter((f) => f.featureId === item.id);
    if (instances.length !== item.quantity || instances.some((f) => f.family !== item.family)) return false;
    if (item.diameter !== undefined && instances.some((f) => f.geometry.kind !== "CIRCLE" || Math.abs(f.geometry.diameter - item.diameter!.value) > 1e-6)) return false;
    if (item.width !== undefined && instances.some((f) => f.geometry.kind !== "SLOT" || Math.abs(f.geometry.width - item.width!.value) > 1e-6)) return false;
  }

  for (const marking of evidence.markings) {
    if (!new Set(["KEGAKI", "RIB"]).has(marking.family)) continue;
    const instances = features.filter((f) => f.featureId === marking.id && f.family === marking.family);
    if (instances.length !== marking.quantity) return false;
    ids.add(marking.id);
  }
  return features.every((f) => ids.has(f.featureId));
}

const topologyModule: Partial<Record<Evidence["contour"]["topology"], string>> = {
  L_PROFILE: "skills/lispcad/topology/L_PROFILE.md",
  U_PROFILE: "skills/lispcad/topology/U_PROFILE.md",
  MULTI_FACE: "skills/lispcad/topology/MULTI_FACE_PROFILE.md",
  STEPPED_PROFILE: "skills/lispcad/topology/STEPPED_PROFILE.md"
};

const featureModules: Partial<Record<Evidence["features"][number]["family"], readonly string[]>> = {
  SLOT: ["skills/lispcad/features/SLOTS.md"],
  CURVED_SLOT: ["skills/lispcad/features/CURVED_SLOT.md"],
  HOLE: ["skills/lispcad/features/HOLES_TAPS.md"],
  TAP: ["skills/lispcad/features/HOLES_TAPS.md"],
  CHAMFER: ["skills/lispcad/features/CHAMFER_RADIUS.md"],
  RADIUS: ["skills/lispcad/features/CHAMFER_RADIUS.md"],
  FORMING: ["skills/lispcad/features/FORMING_FEATURES.md"],
  PIASU: [
    "skills/lispcad/features/HOLES_TAPS.md",
    "skills/lispcad/features/FORMING_FEATURES.md"
  ],
  SLIT_RELIEF: ["skills/lispcad/features/SLIT_RELIEF.md"],
  RIB: ["skills/lispcad/features/RIB.md"]
};

const structurallyBentTopologies = new Set<Evidence["contour"]["topology"]>([
  "L_PROFILE",
  "U_PROFILE",
  "MULTI_FACE",
  "STEPPED_PROFILE",
  "BOXMET"
]);

function unique(values: string[]): string[] {
  return [...new Set(values)];
}

function inferredFaceCount(evidence: Evidence): number | null {
  if (evidence.faceCount) return evidence.faceCount;
  switch (evidence.contour.topology) {
    case "PLATE": return 1;
    case "L_PROFILE": return 2;
    case "U_PROFILE": return 3;
    case "BOXMET": return 5;
    default: return null;
  }
}

function minimumBends(evidence: Evidence): number {
  switch (evidence.contour.topology) {
    case "L_PROFILE": return 1;
    case "U_PROFILE": return 2;
    case "BOXMET": return 4;
    case "MULTI_FACE":
    case "STEPPED_PROFILE":
      return 1;
    default:
      return 0;
  }
}

function classifyPart(evidence: Evidence, structurallyBent: boolean): PartClass {
  if (evidence.partClassHint) return evidence.partClassHint;
  if (!structurallyBent) return "FLAT_NO_BEND";
  switch (evidence.contour.topology) {
    case "L_PROFILE": return "SINGLE_BEND_L";
    case "U_PROFILE": return "DOUBLE_BEND_U";
    case "MULTI_FACE": return "MULTI_FACE_ORTHOGONAL";
    case "STEPPED_PROFILE": return "STEPPED_BENT";
    case "BOXMET": return "BOX_4_FLANGE";
    default: return "OTHER_PROVED_TOPOLOGY";
  }
}

function inventory(evidence: Evidence, structurallyBent: boolean): string[] {
  const values = ["CUT"];
  if (structurallyBent) values.push("BEND");
  for (const feature of evidence.features) {
    switch (feature.family) {
      case "HOLE":
      case "TAP":
        values.push("HOLE_TAP");
        break;
      case "SLOT":
        values.push("STRAIGHT_SLOT");
        break;
      case "CURVED_SLOT":
        values.push("CURVED_SLOT");
        break;
      case "PIASU":
        values.push("PIASU_PIERCING");
        break;
      case "SLIT_RELIEF":
        values.push("SLIT_RELIEF");
        break;
      case "RIB":
        values.push("RIB");
        break;
      case "CHAMFER":
      case "RADIUS":
        values.push("R_C_CHAMFER");
        break;
      case "FORMING":
        values.push("FORMING");
        break;
      case "CUTOUT":
        values.push("INNER_CUT");
        break;
      default:
        values.push("OTHER");
    }
  }
  for (const marking of evidence.markings) {
    if (marking.family === "KEGAKI") values.push("KEGAKI");
    if (marking.family === "RIB") values.push("RIB");
  }
  return unique(values);
}

export function routeEvidence(evidence: Evidence, sourceMode: JobMode = "PDF_ONLY"): RouteResult {
  const structurallyBent =
    evidence.bends.length > 0 ||
    structurallyBentTopologies.has(evidence.contour.topology);

  const faceCount = inferredFaceCount(evidence);
  const requiredBends = minimumBends(evidence);
  const missingFaceCount =
    ["MULTI_FACE", "STEPPED_PROFILE"].includes(evidence.contour.topology) &&
    faceCount === null;
  const missingBendProof =
    structurallyBent && (
      evidence.bends.length < requiredBends ||
      evidence.bends.some((bend) =>
        !bend.axis || !bend.sign || bend.sign === "UNKNOWN"
      )
    );

  const blocked =
    evidence.contour.status === "UNCERTAIN" ||
    evidence.features.some((f) => f.status === "UNCERTAIN") ||
    evidence.bends.some((b) => b.status === "UNCERTAIN") ||
    evidence.markings.some((m) => m.status === "UNCERTAIN") ||
    evidence.uncertainties.some((u) => u.blocking) ||
    missingFaceCount ||
    missingBendProof;

  const mode: RouteResult["mode"] = blocked
    ? "UNRESOLVED"
    : structurallyBent
      ? "BEND_UNFOLD"
      : "FLAT_NO_BEND";

  const modules = [
    "references/SOURCE_DATA_CLASSIFICATION.md",
    "references/MECHANICAL_CLASSIFIER.md",
    "skills/lispcad/core/DRAWING_READING.md",
    "skills/lispcad/core/DATUM_DIMENSION.md",
    "skills/lispcad/core/VALIDATION.md",
    "skills/lispcad/core/CAD_OUTPUT.md",
    structurallyBent
      ? "skills/lispcad/modes/BEND_UNFOLD.md"
      : "skills/lispcad/modes/FLAT_NO_BEND.md"
  ];
  if (sourceMode === "PDF_DATA_RAW") modules.push("references/PDF_DATA_RAW_GEOMETRY_PRESERVATION.md");

  const topology = topologyModule[evidence.contour.topology];
  if (topology) modules.push(topology);

  for (const feature of evidence.features) {
    const selected = featureModules[feature.family];
    if (selected) modules.push(...selected);
  }
  for (const marking of evidence.markings) {
    if (marking.family === "KEGAKI") modules.push("skills/lispcad/features/KEGAKI.md");
    if (marking.family === "RIB") modules.push("skills/lispcad/features/RIB.md");
  }

  const specialRules: string[] = [];
  if (structurallyBent) {
    specialRules.push("references/FACE_GRAPH_UNFOLD_PROTOCOL.md");
  }
  const acute = evidence.bends.some(
    (bend) => bend.status === "PROVED" && bend.angle.value < 85
  );
  if (acute) {
    specialRules.push(
      "references/ACUTE_BEND_LT85_METHOD.md",
      "references/ACUTE_BEND_LT85_FROM_SOURCE.md"
    );
  }
  if (evidence.contour.topology === "BOXMET") {
    specialRules.push("references/BOXMET_SLIT_RELIEF.md");
  }

  const loadedModules = unique([...modules, ...specialRules]);
  const partClass = classifyPart(evidence, structurallyBent);

  return {
    code: evidence.code,
    mode,
    topology: evidence.contour.topology,
    modules: unique(modules),
    specialRules: unique(specialRules),
    flags: [],
    status: blocked ? "REVIEW_REQUIRED" : "ROUTED",
    mechanical: {
      sourceMode,
      partClass,
      faceCount,
      bendAxes: evidence.bends.map((bend) => ({
        bendId: bend.id,
        axis: bend.axis ?? "UNPROVED"
      })),
      bendAnglesAndSigns: evidence.bends.map((bend) => ({
        bendId: bend.id,
        angleDeg: bend.angle.value,
        sign: bend.sign ?? "UNPROVED"
      })),
      featureInventory: inventory(evidence, structurallyBent),
      evidenceStatus: blocked ? "REVIEW_REQUIRED" : "PROVED",
      loadedModules
    },
    jev: jevStatus()
  };
}

export function routeJob(jobId: string): CadJob {
  const job = jobStore.get(jobId);
  if (job.state !== "EVIDENCE_READY") {
    throw new Error(`ROUTING_NOT_ALLOWED_IN_STATE: ${job.state}`);
  }
  if (!job.evidence.length) throw new Error("NO_EVIDENCE");
  const routes = job.evidence.map((evidence) => {
    const route = routeEvidence(evidence, job.mode);
    const code = evidence.code.replace(/\D/g, "");
    if (code.includes("646") && !job.sourceBindings.DATA_DXF) {
      return { ...route, mode: "UNRESOLVED" as const, status: "REVIEW_REQUIRED" as const, flags: ["DATA_REQUIRED_MISSING"] };
    }
    return route;
  });
  const routeRulePaths = routes.flatMap((route) => [...route.modules, ...route.specialRules]);
  const pinned = extendRuleSnapshot(resolveRepoRoot(), {
    files: job.production.ruleFiles ?? [],
    sha256: job.production.ruleSnapshotSha256 ?? ""
  }, routeRulePaths);
  job.production.ruleFiles = pinned.files;
  job.production.ruleSnapshotSha256 = pinned.sha256;
  job.ruleBundleReadSha256 = undefined;
  return jobStore.setRoutes(jobId, routes);
}

export function publicJob(
  job: CadJob
): Omit<CadJob, "evidence" | "geometrySources" | "sourceBindings" | "dxfOutput"> & {
  evidenceCount: number;
  geometrySourceCount: number;
  sourceBindings: Record<string, Omit<CadJob["sourceBindings"][string], "storedPath">>;
  dxfOutput?: Omit<NonNullable<CadJob["dxfOutput"]>, "absolutePath" | "manifestPath" | "relativePath"> & { artifactUri: string };
} {
  const { evidence, geometrySources, ...rest } = job;
  return {
    ...rest,
    sourceBindings: Object.fromEntries(Object.entries(job.sourceBindings).map(([role, binding]) => {
      const { storedPath: _storedPath, ...publicBinding } = binding;
      return [role, publicBinding];
    })),
    dxfOutput: job.dxfOutput ? {
      fileName: job.dxfOutput.fileName,
      serializerContract: job.dxfOutput.serializerContract,
      codeOrder: job.dxfOutput.codeOrder,
      fileSha256: job.dxfOutput.fileSha256,
      serializerInputSha256: job.dxfOutput.serializerInputSha256,
      manifestSha256: job.dxfOutput.manifestSha256,
      writtenAt: job.dxfOutput.writtenAt,
      artifactUri: `trainaicad://jobs/${job.jobId}/artifacts/${job.dxfOutput.fileSha256}`
    } : undefined,
    evidenceCount: evidence.length,
    geometrySourceCount: geometrySources.length
  };
}
