import * as z from "zod/v4";

const Finite = z.number().finite();
const XY = z.array(Finite).length(2);
const Vertex = z.array(Finite).length(3);
const CheckValue = z.enum(["PASS", "N/A", "FLAGGED"]);
const GateValue = z.enum(["PASS", "N/A"]);

// Deliberately portable tool-facing schema: avoid tuple/prefixItems/boolean-schema
// constructs that some MCP consumers reject. The server re-validates the same
// payload against the stricter RepoDirectSubmissionV1 before any write/export.
const PortableEntity = z.object({
  type: z.enum(["LWPOLYLINE", "CIRCLE", "POINT", "LINE", "ARC", "TEXT"]),
  role: z.string().min(1),
  color: z.number().int().optional(),
  linetype: z.string().min(1).optional(),
  view_id: z.string().min(1).optional(),
  closed: z.boolean().optional(),
  vertices: z.array(Vertex).min(2).optional(),
  center: XY.optional(),
  radius: z.number().positive().optional(),
  point: XY.optional(),
  start: XY.optional(),
  end: XY.optional(),
  start_angle: Finite.optional(),
  end_angle: Finite.optional(),
  insert: XY.optional(),
  text: z.string().min(1).optional(),
  height: z.number().positive().optional(),
});

const PortableChecks = z.object({
  contour_topology: CheckValue,
  datum: CheckValue,
  feature_count: CheckValue,
  unfold: CheckValue,
  containment: CheckValue,
  bend_domain: CheckValue,
  material_rules: CheckValue,
  slot_semantics: CheckValue,
});

const PortablePart = z.object({
  code: z.string().min(1),
  material: z.string().min(1),
  thickness_mm: z.number().positive(),
  status: z.enum(["PASS", "PREVIEW", "VIEWS_ONLY"]),
  preview_reason: z.string().min(1).optional(),
  flags: z.array(z.string().min(1)),
  checks: PortableChecks,
  entities: z.array(PortableEntity).min(1),
});

const PortableGate = z.object({
  code: z.string().min(1),
  finalCensusClosed: z.boolean(),
  sourceFeatureCompleteness: z.boolean(),
  crossFeatureValidation: z.boolean(),
  constraintsClosed: z.boolean(),
  localFaceTransforms: GateValue,
  foldBackSourceReprojection: GateValue,
  rawDataSnapshot: GateValue,
  sameParameterGate: GateValue,
  manufacturingChangeLedger: GateValue,
  untouchedDataInvariance: GateValue,
  sourceReprojection: GateValue,
  sourceActiveFamilies: z.array(z.string().min(1)).min(1),
  canonicalFamilies: z.array(z.string().min(1)).min(1),
  serializedFamilies: z.array(z.string().min(1)).min(1),
  evidenceRefs: z.array(z.string().min(1)).min(1),
});

export const RepoDirectToolInput = z.object({
  schema: z.literal("REPO_DIRECT_DXF_V1"),
  jobId: z.string().min(1),
  // Optional at the MCP boundary. The server authoritatively fills these from
  // the persisted job before strict RepoDirectSubmissionV1 validation. Keeping
  // them optional removes a common caller error (truncated/copied hashes)
  // without weakening the internal hash/snapshot binding.
  sourceSha256: z.string().length(64).optional(),
  dxfSha256: z.string().length(64).optional(),
  ruleSnapshotId: z.string().min(1).optional(),
  parts: z.array(PortablePart).min(1),
  gates: z.array(PortableGate).min(1),
});
