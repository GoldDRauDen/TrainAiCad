import { createHash } from "node:crypto";
import * as z from "zod/v4";
import {
  Provenance,
  TechnicalNumber,
  type CadEvidenceV1,
  type CadJob,
  type JobMode
} from "./model.js";

export const Point2 = z.object({
  x: z.number().finite(),
  y: z.number().finite()
});
export type Point2 = z.infer<typeof Point2>;

export const PolyVertex = Point2.extend({
  bulge: z.number().finite().default(0)
});
export type PolyVertex = z.infer<typeof PolyVertex>;

export const Segment2 = z.object({
  start: Point2,
  end: Point2
});
export type Segment2 = z.infer<typeof Segment2>;

export const Affine2 = z.object({
  m00: z.number().finite(),
  m01: z.number().finite(),
  m10: z.number().finite(),
  m11: z.number().finite(),
  tx: z.number().finite(),
  ty: z.number().finite()
});
export type Affine2 = z.infer<typeof Affine2>;

const GateProof = z.object({
  evidenceRefs: z.array(z.string().min(1)).min(1)
});

const FoldBackNumericCheck = z.object({
  id: z.string().min(1),
  expected: z.number().finite(),
  actual: z.number().finite(),
  origin: Provenance
});

const FoldBackProof = z.object({
  evidenceRefs: z.array(z.string().min(1)).min(1),
  topologyMatch: z.literal(true),
  adjacencyMatch: z.literal(true),
  bendSignMatch: z.literal(true),
  featureOwnershipMatch: z.literal(true),
  bendDomainMatch: z.literal(true),
  numericChecks: z.array(FoldBackNumericCheck).default([])
});

const FaceGraphProofs = z.object({
  topologyLocked: GateProof.optional(),
  dimensionWitnessLocked: GateProof.optional(),
  featureOwnershipLocked: GateProof.optional(),
  faceOrderLocked: GateProof.optional(),
  bendSignLocked: GateProof.optional(),
  bendDomainLocked: GateProof.optional(),
  constraintsClosed: GateProof.optional(),
  foldBackMatch: FoldBackProof.optional(),
  materialRules: GateProof.optional(),
  slotSemantics: GateProof.optional()
});

const CircleGeometry = z.object({
  kind: z.literal("CIRCLE"),
  center: Point2,
  diameter: z.number().positive()
});

const PointGeometry = z.object({
  kind: z.literal("POINT"),
  point: Point2
});

const SlotGeometry = z.object({
  kind: z.literal("SLOT"),
  center: Point2,
  overallLength: z.number().positive(),
  width: z.number().positive(),
  angleDeg: z.number().finite().default(0)
}).superRefine((v, ctx) => {
  if (v.overallLength < v.width) {
    ctx.addIssue({ code: "custom", message: "SLOT overallLength must be >= width" });
  }
});

const PolylineGeometry = z.object({
  kind: z.literal("POLYLINE"),
  closed: z.boolean(),
  vertices: z.array(PolyVertex).min(2)
});

const LineGeometry = z.object({
  kind: z.literal("LINE"),
  start: Point2,
  end: Point2
});

const ArcGeometry = z.object({
  kind: z.literal("ARC"),
  center: Point2,
  radius: z.number().positive(),
  startAngleDeg: z.number().finite(),
  endAngleDeg: z.number().finite()
});

export const LocalFeatureGeometry = z.discriminatedUnion("kind", [
  CircleGeometry,
  PointGeometry,
  SlotGeometry,
  PolylineGeometry,
  LineGeometry,
  ArcGeometry
]);
export type LocalFeatureGeometry = z.infer<typeof LocalFeatureGeometry>;

const GeometryFeatureSource = z.object({
  featureId: z.string().min(1),
  family: z.enum([
    "SLOT",
    "CURVED_SLOT",
    "HOLE",
    "TAP",
    "CHAMFER",
    "RADIUS",
    "FORMING",
    "CUTOUT",
    "PIASU",
    "SLIT_RELIEF",
    "RIB",
    "KEGAKI",
    "OTHER"
  ]),
  hostFace: z.string().min(1),
  style: z.enum(["BYLAYER", "THROUGH_PIERCING_GREEN", "RELIEF_GREEN"]).default("BYLAYER"),
  styleProofRefs: z.array(z.string().min(1)).optional(),
  geometries: z.array(LocalFeatureGeometry).min(1)
}).superRefine((v, ctx) => {
  if (v.style !== "BYLAYER" && !v.styleProofRefs?.length) {
    ctx.addIssue({ code: "custom", message: "Non-default manufacturing style requires styleProofRefs" });
  }
});

const GeometryFaceSource = z.object({
  faceId: z.string().min(1),
  sourceView: z.string().min(1),
  contour: z.array(PolyVertex).min(3),
  outsideLength: TechnicalNumber.optional(),
  transverseWidth: TechnicalNumber.optional(),
  unfoldDirection: z.enum(["FORWARD", "REVERSE"]).default("FORWARD"),
  transverseFlip: z.boolean().default(false),
  flatTransform: Affine2.optional(),
  transformProofRefs: z.array(z.string().min(1)).optional()
});

const BendFlatLines = z.object({
  line1: Segment2,
  line2: Segment2,
  proofRefs: z.array(z.string().min(1)).min(1)
});

const GeometryBendSource = z.object({
  bendId: z.string().min(1),
  faceA: z.string().min(1),
  faceB: z.string().min(1),
  axis: z.enum(["X", "Y", "OTHER"]),
  sign: z.enum(["POSITIVE", "NEGATIVE"]),
  angleDeg: TechnicalNumber,
  nobi: TechnicalNumber,
  flatLines: BendFlatLines.optional()
});

export const GeometrySourceV1 = z.object({
  schema: z.literal("GEOMETRY_SOURCE_V1"),
  jobId: z.string().min(1),
  code: z.string().min(1),
  sourceSha256: z.string().regex(/^[a-fA-F0-9]{64}$/),
  origin: z.enum(["PDF_SOURCE", "DATA_DXF"]),
  buildKind: z.enum(["FLAT_SINGLE_FACE", "LINEAR_CHAIN", "FACE_GRAPH_FLAT"]),
  faces: z.array(GeometryFaceSource).min(1),
  faceOrder: z.array(z.string().min(1)).min(1),
  bends: z.array(GeometryBendSource).default([]),
  features: z.array(GeometryFeatureSource).default([]),
  flatOuterContour: z.array(PolyVertex).min(3).optional(),
  flatOuterProofRefs: z.array(z.string().min(1)).optional(),
  proofs: FaceGraphProofs.default({})
});
export type GeometrySourceV1 = z.infer<typeof GeometrySourceV1>;

export type CanonicalFeature = {
  featureId: string;
  family: string;
  hostFace: string;
  instance: number;
  style: "BYLAYER" | "THROUGH_PIERCING_GREEN" | "RELIEF_GREEN";
  geometry: LocalFeatureGeometry;
};

export type CanonicalBendZone = {
  bendId: string;
  line1: Segment2;
  line2: Segment2;
  sign: "POSITIVE" | "NEGATIVE";
  angleDeg: number;
  nobi: number;
};

export type CanonicalGeometryV1 = {
  schema: "CANONICAL_GEOMETRY_V1";
  geometryId: string;
  jobId: string;
  code: string;
  units: "mm";
  buildKind: "FLAT_SINGLE_FACE" | "LINEAR_CHAIN" | "FACE_GRAPH_FLAT";
  sourceMode: JobMode;
  sourceSha256: string;
  outerContours: PolyVertex[][];
  features: CanonicalFeature[];
  bendZones: CanonicalBendZone[];
  faceMap: Array<{
    faceId: string;
    flatStartX?: number;
    flatEndX?: number;
    transform?: Affine2;
  }>;
  qa: {
    polygonClosed: boolean;
    topologyClosed: boolean;
    faceGraphG1toG7: "NOT_APPLICABLE" | "PASS";
    foldBack: "NOT_APPLICABLE" | "PASS";
    numericResidualMaxMm: number;
    checks: {
      contour_topology: "PASS";
      datum: "PASS";
      feature_count: "PASS";
      unfold: "PASS" | "N/A";
      containment: "PASS";
      bend_domain: "PASS" | "N/A";
      material_rules: "PASS";
      slot_semantics: "PASS" | "N/A";
    };
  };
  flags: string[];
};

export type GeometryBuildResult = {
  code: string;
  status: "READY" | "REVIEW_REQUIRED";
  geometry?: CanonicalGeometryV1;
  flags: string[];
};

function hashId(value: unknown): string {
  return createHash("sha256").update(JSON.stringify(value)).digest("hex").slice(0, 20);
}

function unique(values: string[]): string[] {
  return [...new Set(values)];
}

function samePoint(a: Point2, b: Point2, eps = 1e-9): boolean {
  return Math.abs(a.x - b.x) <= eps && Math.abs(a.y - b.y) <= eps;
}

function orient(a: Point2, b: Point2, c: Point2): number {
  return (b.x - a.x) * (c.y - a.y) - (b.y - a.y) * (c.x - a.x);
}

function onSegment(a: Point2, b: Point2, p: Point2, eps = 1e-9): boolean {
  return Math.min(a.x, b.x) - eps <= p.x && p.x <= Math.max(a.x, b.x) + eps &&
    Math.min(a.y, b.y) - eps <= p.y && p.y <= Math.max(a.y, b.y) + eps &&
    Math.abs(orient(a, b, p)) <= eps;
}

function segmentsIntersect(a: Point2, b: Point2, c: Point2, d: Point2): boolean {
  const o1 = orient(a, b, c);
  const o2 = orient(a, b, d);
  const o3 = orient(c, d, a);
  const o4 = orient(c, d, b);
  const eps = 1e-9;

  if (((o1 > eps && o2 < -eps) || (o1 < -eps && o2 > eps)) &&
      ((o3 > eps && o4 < -eps) || (o3 < -eps && o4 > eps))) return true;

  return Math.abs(o1) <= eps && onSegment(a, b, c) ||
    Math.abs(o2) <= eps && onSegment(a, b, d) ||
    Math.abs(o3) <= eps && onSegment(c, d, a) ||
    Math.abs(o4) <= eps && onSegment(c, d, b);
}

function flattenBulged(vertices: PolyVertex[], stepDeg = 5): Point2[] {
  const out: Point2[] = [];
  for (let i = 0; i < vertices.length; i++) {
    const a = vertices[i]!;
    const b = vertices[(i + 1) % vertices.length]!;
    out.push({ x: a.x, y: a.y });
    if (!a.bulge) continue;
    const theta = 4 * Math.atan(a.bulge);
    const chord = Math.hypot(b.x - a.x, b.y - a.y);
    if (chord <= 1e-12 || Math.abs(theta) <= 1e-12) continue;
    const radius = chord / (2 * Math.abs(Math.sin(theta / 2)));
    const mid = { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 };
    const ux = (b.x - a.x) / chord;
    const uy = (b.y - a.y) / chord;
    const nx = -uy;
    const ny = ux;
    const h = radius * Math.cos(Math.abs(theta) / 2);
    const sign = Math.sign(theta);
    const center = { x: mid.x + sign * nx * h, y: mid.y + sign * ny * h };
    const start = Math.atan2(a.y - center.y, a.x - center.x);
    const segments = Math.max(2, Math.ceil(Math.abs(theta) / (stepDeg * Math.PI / 180)));
    for (let k = 1; k < segments; k++) {
      const ang = start + theta * k / segments;
      out.push({ x: center.x + radius * Math.cos(ang), y: center.y + radius * Math.sin(ang) });
    }
  }
  return out;
}

export function polygonArea(points: Point2[]): number {
  let area = 0;
  for (let i = 0; i < points.length; i++) {
    const a = points[i]!;
    const b = points[(i + 1) % points.length]!;
    area += a.x * b.y - b.x * a.y;
  }
  return area / 2;
}

function ensureCcw(vertices: PolyVertex[]): PolyVertex[] {
  if (polygonArea(flattenBulged(vertices)) >= 0) return vertices;
  const reversed = [...vertices].reverse();
  return reversed.map((v, i) => {
    const nextReversed = reversed[(i + 1) % reversed.length]!;
    return { x: v.x, y: v.y, bulge: -nextReversed.bulge };
  });
}

function validateSimplePolygon(vertices: PolyVertex[]): string[] {
  const points = flattenBulged(vertices);
  const flags: string[] = [];
  if (points.length < 3) return ["CONTOUR_TOO_FEW_POINTS"];
  if (Math.abs(polygonArea(points)) <= 1e-9) flags.push("CONTOUR_ZERO_AREA");

  for (let i = 0; i < points.length; i++) {
    const a = points[i]!;
    const b = points[(i + 1) % points.length]!;
    if (samePoint(a, b)) flags.push("CONTOUR_ZERO_LENGTH_EDGE");
  }

  for (let i = 0; i < points.length; i++) {
    const a1 = points[i]!;
    const a2 = points[(i + 1) % points.length]!;
    for (let j = i + 1; j < points.length; j++) {
      const adjacent =
        j === i ||
        j === (i + 1) % points.length ||
        i === (j + 1) % points.length;
      if (adjacent) continue;
      if (i === 0 && j === points.length - 1) continue;
      const b1 = points[j]!;
      const b2 = points[(j + 1) % points.length]!;
      if (segmentsIntersect(a1, a2, b1, b2)) flags.push("CONTOUR_SELF_INTERSECTION");
    }
  }
  return unique(flags);
}

function pointInPolygon(point: Point2, polygon: Point2[], inclusive = true): boolean {
  for (let i = 0; i < polygon.length; i++) {
    if (onSegment(polygon[i]!, polygon[(i + 1) % polygon.length]!, point)) return inclusive;
  }
  let inside = false;
  for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
    const a = polygon[i]!;
    const b = polygon[j]!;
    const intersects =
      (a.y > point.y) !== (b.y > point.y) &&
      point.x < ((b.x - a.x) * (point.y - a.y)) / ((b.y - a.y) || Number.EPSILON) + a.x;
    if (intersects) inside = !inside;
  }
  return inside;
}

function expectedGeometryAuthority(job: CadJob): {
  origin: "PDF_SOURCE" | "DATA_DXF";
  sha256: string;
} {
  if (job.mode === "PDF_DATA_RAW") {
    if (!job.dxf) throw new Error("GEOMETRY_AUTHORITY_MISSING_DATA_DXF");
    return { origin: "DATA_DXF", sha256: job.dxf.sha256 };
  }
  if (job.mode === "DIRECT_EXISTING_DXF_AUDIT") {
    throw new Error("GEOMETRY_BUILD_NOT_APPLICABLE_TO_DIRECT_AUDIT");
  }
  return { origin: "PDF_SOURCE", sha256: job.source.sha256 };
}

function evidenceForCode(job: CadJob, code: string): CadEvidenceV1 {
  const evidence = job.evidence.find((item) => item.code === code);
  if (!evidence) throw new Error(`GEOMETRY_EVIDENCE_NOT_FOUND: ${code}`);
  return evidence;
}

function routeForCode(job: CadJob, code: string) {
  const route = job.routes.find((item) => item.code === code);
  if (!route) throw new Error(`GEOMETRY_ROUTE_NOT_FOUND: ${code}`);
  return route;
}

function validateSourceIdentity(job: CadJob, source: GeometrySourceV1): string[] {
  const flags: string[] = [];
  const expected = expectedGeometryAuthority(job);
  if (source.origin !== expected.origin) {
    flags.push(`GEOMETRY_AUTHORITY_ORIGIN_MISMATCH:${source.origin}->${expected.origin}`);
  }
  if (source.sourceSha256.toLowerCase() !== expected.sha256.toLowerCase()) {
    flags.push("GEOMETRY_AUTHORITY_SHA_MISMATCH");
  }
  return flags;
}

function validateFaceIds(source: GeometrySourceV1): string[] {
  const flags: string[] = [];
  const ids = source.faces.map((f) => f.faceId);
  if (new Set(ids).size !== ids.length) flags.push("DUPLICATE_FACE_ID");
  if (new Set(source.faceOrder).size !== source.faceOrder.length) flags.push("DUPLICATE_FACE_ORDER_ID");
  if (source.faceOrder.length !== ids.length) flags.push("FACE_ORDER_COUNT_MISMATCH");
  if ([...ids].sort().join("|") !== [...source.faceOrder].sort().join("|")) {
    flags.push("FACE_ORDER_MEMBERSHIP_MISMATCH");
  }
  for (const feature of source.features) {
    if (!ids.includes(feature.hostFace)) flags.push(`FEATURE_HOST_FACE_UNKNOWN:${feature.featureId}`);
  }
  for (const bend of source.bends) {
    if (!ids.includes(bend.faceA) || !ids.includes(bend.faceB) || bend.faceA === bend.faceB) {
      flags.push(`BEND_FACE_REFERENCE_INVALID:${bend.bendId}`);
    }
  }
  return flags;
}

function validateEvidenceFeatureOwnership(job: CadJob, source: GeometrySourceV1): string[] {
  const evidence = evidenceForCode(job, source.code);
  const flags: string[] = [];
  const byId = new Map(source.features.map((f) => [f.featureId, f] as const));
  for (const feature of evidence.features) {
    const sourceFeature = byId.get(feature.id);
    if (!sourceFeature) {
      flags.push(`FEATURE_GEOMETRY_MISSING:${feature.id}`);
      continue;
    }
    if (sourceFeature.family !== feature.family) flags.push(`FEATURE_FAMILY_MISMATCH:${feature.id}`);
    if (sourceFeature.geometries.length !== feature.quantity) {
      flags.push(`FEATURE_QUANTITY_MISMATCH:${feature.id}`);
    }
    if (feature.family === "RIB") {
      flags.push(`RIB_MUST_BE_INDEPENDENT_PART:${feature.id}`);
    }
    if (feature.family === "PIASU" && sourceFeature.style === "RELIEF_GREEN") {
      flags.push(`PIASU_STYLE_INVALID:${feature.id}`);
    }
    if (feature.family === "SLIT_RELIEF" && sourceFeature.style === "THROUGH_PIERCING_GREEN") {
      flags.push(`SLIT_STYLE_INVALID:${feature.id}`);
    }
  }
  for (const marking of evidence.markings) {
    if (marking.family === "KEGAKI" || marking.family === "RIB") {
      const sourceFeature = byId.get(marking.id);
      if (!sourceFeature) {
        flags.push(`MARKING_GEOMETRY_MISSING:${marking.id}`);
        continue;
      }
      if (sourceFeature.family !== marking.family) flags.push(`MARKING_FAMILY_MISMATCH:${marking.id}`);
      if (sourceFeature.geometries.length !== marking.quantity) {
        flags.push(`MARKING_QUANTITY_MISMATCH:${marking.id}`);
      }
    }
  }
  return flags;
}

function hasSlots(source: GeometrySourceV1): boolean {
  return source.features.some((f) => f.family === "SLOT" || f.family === "CURVED_SLOT");
}

function requiredBaseProofFlags(source: GeometrySourceV1): string[] {
  const flags: string[] = [];
  for (const [key, value] of [
    ["TOPOLOGY_LOCKED", source.proofs.topologyLocked],
    ["DIMENSION_WITNESS_LOCKED", source.proofs.dimensionWitnessLocked],
    ["FEATURE_OWNERSHIP_LOCKED", source.proofs.featureOwnershipLocked],
    ["CONSTRAINTS_CLOSED", source.proofs.constraintsClosed],
    ["MATERIAL_RULES_UNPROVED", source.proofs.materialRules]
  ] as const) {
    if (!value) flags.push(key);
  }
  if (hasSlots(source) && !source.proofs.slotSemantics) flags.push("SLOT_SEMANTICS_UNPROVED");
  return flags;
}

function requiredBentProofFlags(source: GeometrySourceV1): string[] {
  const flags = requiredBaseProofFlags(source);
  for (const [key, value] of [
    ["FACE_ORDER_LOCKED", source.proofs.faceOrderLocked],
    ["BEND_SIGN_LOCKED", source.proofs.bendSignLocked],
    ["BEND_DOMAIN_LOCKED", source.proofs.bendDomainLocked],
    ["FOLD_BACK_MATCH_MISSING", source.proofs.foldBackMatch]
  ] as const) {
    if (!value) flags.push(key);
  }
  return flags;
}

function foldBackResidual(source: GeometrySourceV1): { flags: string[]; max: number } {
  const proof = source.proofs.foldBackMatch;
  if (!proof) return { flags: ["FOLD_BACK_MATCH_MISSING"], max: Infinity };
  const flags: string[] = [];
  let max = 0;
  for (const check of proof.numericChecks) {
    const residual = Number(Math.abs(check.expected - check.actual).toFixed(12));
    max = Math.max(max, residual);
    if (check.origin === "DERIVED") {
      if (residual >= 0.01) flags.push(`FOLD_BACK_DERIVED_RESIDUAL:${check.id}`);
    } else if (residual > 1e-9) {
      flags.push(`FOLD_BACK_EXACT_SOURCE_MISMATCH:${check.id}`);
    }
  }
  return { flags, max };
}

function rigidTransformFlags(transform: Affine2, faceId: string): string[] {
  const flags: string[] = [];
  const c0 = Math.hypot(transform.m00, transform.m10);
  const c1 = Math.hypot(transform.m01, transform.m11);
  const dot = transform.m00 * transform.m01 + transform.m10 * transform.m11;
  const det = transform.m00 * transform.m11 - transform.m01 * transform.m10;
  if (Math.abs(c0 - 1) > 1e-9 || Math.abs(c1 - 1) > 1e-9 || Math.abs(dot) > 1e-9) {
    flags.push(`FACE_TRANSFORM_NOT_RIGID:${faceId}`);
  }
  if (Math.abs(Math.abs(det) - 1) > 1e-9) flags.push(`FACE_TRANSFORM_BAD_DETERMINANT:${faceId}`);
  return flags;
}

function transformPoint(point: Point2, t: Affine2): Point2 {
  return {
    x: t.m00 * point.x + t.m01 * point.y + t.tx,
    y: t.m10 * point.x + t.m11 * point.y + t.ty
  };
}

function transformAngle(angleDeg: number, t: Affine2): number {
  const r = angleDeg * Math.PI / 180;
  const vx = Math.cos(r);
  const vy = Math.sin(r);
  const x = t.m00 * vx + t.m01 * vy;
  const y = t.m10 * vx + t.m11 * vy;
  let deg = Math.atan2(y, x) * 180 / Math.PI;
  while (deg < 0) deg += 360;
  while (deg >= 360) deg -= 360;
  return deg;
}

function transformGeometry(geometry: LocalFeatureGeometry, t: Affine2): LocalFeatureGeometry {
  if (geometry.kind === "CIRCLE") {
    return { ...geometry, center: transformPoint(geometry.center, t) };
  }
  if (geometry.kind === "POINT") {
    return { ...geometry, point: transformPoint(geometry.point, t) };
  }
  if (geometry.kind === "SLOT") {
    return {
      ...geometry,
      center: transformPoint(geometry.center, t),
      angleDeg: transformAngle(geometry.angleDeg, t)
    };
  }
  if (geometry.kind === "POLYLINE") {
    const det = t.m00 * t.m11 - t.m01 * t.m10;
    return {
      ...geometry,
      vertices: geometry.vertices.map((v) => ({
        ...transformPoint(v, t),
        bulge: det >= 0 ? v.bulge : -v.bulge
      }))
    };
  }
  if (geometry.kind === "LINE") {
    return {
      ...geometry,
      start: transformPoint(geometry.start, t),
      end: transformPoint(geometry.end, t)
    };
  }
  const det = t.m00 * t.m11 - t.m01 * t.m10;
  const start = transformAngle(geometry.startAngleDeg, t);
  const end = transformAngle(geometry.endAngleDeg, t);
  return {
    ...geometry,
    center: transformPoint(geometry.center, t),
    startAngleDeg: det >= 0 ? start : end,
    endAngleDeg: det >= 0 ? end : start
  };
}

function geometrySamplePoints(geometry: LocalFeatureGeometry): Point2[] {
  if (geometry.kind === "POINT") return [geometry.point];
  if (geometry.kind === "CIRCLE") {
    const r = geometry.diameter / 2;
    const pts = [geometry.center];
    for (let i = 0; i < 24; i++) {
      const a = 2 * Math.PI * i / 24;
      pts.push({ x: geometry.center.x + r * Math.cos(a), y: geometry.center.y + r * Math.sin(a) });
    }
    return pts;
  }
  if (geometry.kind === "SLOT") {
    const r = geometry.width / 2;
    const halfStraight = (geometry.overallLength - geometry.width) / 2;
    const theta = geometry.angleDeg * Math.PI / 180;
    const ux = Math.cos(theta);
    const uy = Math.sin(theta);
    const nx = -uy;
    const ny = ux;
    const c1 = { x: geometry.center.x - halfStraight * ux, y: geometry.center.y - halfStraight * uy };
    const c2 = { x: geometry.center.x + halfStraight * ux, y: geometry.center.y + halfStraight * uy };
    const pts = [geometry.center];
    for (const center of [c1, c2]) {
      for (let i = 0; i < 16; i++) {
        const a = 2 * Math.PI * i / 16;
        pts.push({ x: center.x + r * (Math.cos(a) * ux + Math.sin(a) * nx),
          y: center.y + r * (Math.cos(a) * uy + Math.sin(a) * ny) });
      }
    }
    return pts;
  }
  if (geometry.kind === "POLYLINE") {
    return flattenBulged(geometry.vertices);
  }
  if (geometry.kind === "LINE") {
    return [
      geometry.start,
      geometry.end,
      { x: (geometry.start.x + geometry.end.x) / 2, y: (geometry.start.y + geometry.end.y) / 2 }
    ];
  }
  const points: Point2[] = [geometry.center];
  let start = geometry.startAngleDeg;
  let end = geometry.endAngleDeg;
  while (end < start) end += 360;
  for (let i = 0; i <= 16; i++) {
    const deg = start + (end - start) * i / 16;
    const a = deg * Math.PI / 180;
    points.push({ x: geometry.center.x + geometry.radius * Math.cos(a),
      y: geometry.center.y + geometry.radius * Math.sin(a) });
  }
  return points;
}

function pointInsideSlot(p: Point2, slot: Extract<LocalFeatureGeometry, { kind: "SLOT" }>): boolean {
  const theta = -slot.angleDeg * Math.PI / 180;
  const dx = p.x - slot.center.x;
  const dy = p.y - slot.center.y;
  const x = dx * Math.cos(theta) - dy * Math.sin(theta);
  const y = dx * Math.sin(theta) + dy * Math.cos(theta);
  const r = slot.width / 2;
  const halfStraight = (slot.overallLength - slot.width) / 2;
  if (Math.abs(x) <= halfStraight && Math.abs(y) <= r) return true;
  const cx = x < 0 ? -halfStraight : halfStraight;
  return Math.hypot(x - cx, y) <= r + 1e-9;
}

function pointInsideVoid(p: Point2, features: CanonicalFeature[]): boolean {
  for (const feature of features) {
    if (!["HOLE", "TAP", "SLOT", "CURVED_SLOT", "CUTOUT"].includes(feature.family)) continue;
    const g = feature.geometry;
    if (g.kind === "CIRCLE" && Math.hypot(p.x - g.center.x, p.y - g.center.y) < g.diameter / 2 - 1e-9) {
      return true;
    }
    if (g.kind === "SLOT" && pointInsideSlot(p, g)) return true;
    if (g.kind === "POLYLINE" && g.closed && pointInPolygon(p, flattenBulged(g.vertices), false)) return true;
  }
  return false;
}

function validateFeatureContainment(outer: Point2[], features: CanonicalFeature[]): string[] {
  const flags: string[] = [];
  for (const feature of features) {
    for (const p of geometrySamplePoints(feature.geometry)) {
      if (!pointInPolygon(p, outer, true)) {
        flags.push(`FEATURE_OUTSIDE_MATERIAL:${feature.featureId}:${feature.instance}`);
        break;
      }
    }
  }
  return unique(flags);
}

function validateBendMaterial(outer: Point2[], features: CanonicalFeature[], bends: CanonicalBendZone[]): string[] {
  const flags: string[] = [];
  for (const bend of bends) {
    for (const [name, line] of [["L1", bend.line1], ["L2", bend.line2]] as const) {
      for (let i = 0; i <= 100; i++) {
        const t = i / 100;
        const p = {
          x: line.start.x + (line.end.x - line.start.x) * t,
          y: line.start.y + (line.end.y - line.start.y) * t
        };
        if (!pointInPolygon(p, outer, true) || pointInsideVoid(p, features)) {
          flags.push(`BEND_DOMAIN_NOT_MATERIAL:${bend.bendId}:${name}`);
          break;
        }
      }
    }
  }
  return unique(flags);
}

function canonicalizeFeatures(
  source: GeometrySourceV1,
  transforms: Map<string, Affine2>
): CanonicalFeature[] {
  return source.features.flatMap((feature) => {
    const transform = transforms.get(feature.hostFace);
    if (!transform) throw new Error(`FACE_TRANSFORM_MISSING:${feature.hostFace}`);
    return feature.geometries.map((geometry, index) => ({
      featureId: feature.featureId,
      family: feature.family,
      hostFace: feature.hostFace,
      instance: index + 1,
      style: feature.style,
      geometry: transformGeometry(geometry, transform)
    }));
  });
}

function checksFor(source: GeometrySourceV1, bent: boolean): CanonicalGeometryV1["qa"]["checks"] {
  return {
    contour_topology: "PASS",
    datum: "PASS",
    feature_count: "PASS",
    unfold: bent ? "PASS" : "N/A",
    containment: "PASS",
    bend_domain: bent ? "PASS" : "N/A",
    material_rules: "PASS",
    slot_semantics: hasSlots(source) ? "PASS" : "N/A"
  };
}

function buildFlat(job: CadJob, source: GeometrySourceV1): GeometryBuildResult {
  const flags = [
    ...validateSourceIdentity(job, source),
    ...validateFaceIds(source),
    ...requiredBaseProofFlags(source)
  ];
  const route = routeForCode(job, source.code);
  if (route.mode !== "FLAT_NO_BEND") flags.push("FLAT_SOURCE_ON_NONFLAT_ROUTE");
  if (source.faces.length !== 1 || source.faceOrder.length !== 1) flags.push("FLAT_REQUIRES_ONE_FACE");
  if (source.bends.length) flags.push("FLAT_CANNOT_HAVE_BENDS");
  flags.push(...validateEvidenceFeatureOwnership(job, source));

  const face = source.faces[0];
  if (!face) flags.push("FLAT_FACE_MISSING");
  else flags.push(...validateSimplePolygon(face.contour));
  if (flags.length) return { code: source.code, status: "REVIEW_REQUIRED", flags: unique(flags) };

  const transform: Affine2 = { m00: 1, m01: 0, m10: 0, m11: 1, tx: 0, ty: 0 };
  const features = canonicalizeFeatures(source, new Map([[face!.faceId, transform]]));
  const outer = ensureCcw(face!.contour);
  const containment = validateFeatureContainment(flattenBulged(outer), features);
  if (containment.length) return { code: source.code, status: "REVIEW_REQUIRED", flags: containment };

  const geometry: CanonicalGeometryV1 = {
    schema: "CANONICAL_GEOMETRY_V1",
    geometryId: `geo_${hashId(source)}`,
    jobId: job.jobId,
    code: source.code,
    units: "mm",
    buildKind: "FLAT_SINGLE_FACE",
    sourceMode: job.mode,
    sourceSha256: source.sourceSha256,
    outerContours: [outer],
    features,
    bendZones: [],
    faceMap: [{ faceId: face!.faceId, transform }],
    qa: {
      polygonClosed: true,
      topologyClosed: true,
      faceGraphG1toG7: "NOT_APPLICABLE",
      foldBack: "NOT_APPLICABLE",
      numericResidualMaxMm: 0,
      checks: checksFor(source, false)
    },
    flags: []
  };
  return { code: source.code, status: "READY", geometry, flags: [] };
}

function buildLinearChain(job: CadJob, source: GeometrySourceV1): GeometryBuildResult {
  const flags = [
    ...validateSourceIdentity(job, source),
    ...validateFaceIds(source),
    ...requiredBentProofFlags(source),
    ...validateEvidenceFeatureOwnership(job, source)
  ];
  const route = routeForCode(job, source.code);
  if (route.mode !== "BEND_UNFOLD") flags.push("LINEAR_CHAIN_REQUIRES_BEND_UNFOLD_ROUTE");
  if (source.faces.length < 2) flags.push("LINEAR_CHAIN_REQUIRES_AT_LEAST_TWO_FACES");
  if (source.bends.length !== Math.max(0, source.faces.length - 1)) flags.push("BEND_COUNT_NOT_CHAIN_CLOSED");

  const ordered = source.faceOrder
    .map((id) => source.faces.find((f) => f.faceId === id))
    .filter((f): f is NonNullable<typeof f> => Boolean(f));
  const lengths = ordered.map((f) => f.outsideLength?.value);
  const widths = ordered.map((f) => f.transverseWidth?.value);
  if (lengths.some((v) => v === undefined || v <= 0)) flags.push("FACE_OUTSIDE_LENGTH_MISSING");
  if (widths.some((v) => v === undefined || v <= 0)) flags.push("FACE_TRANSVERSE_WIDTH_MISSING");
  const width0 = widths[0];
  if (width0 !== undefined && widths.some((v) => v !== undefined && Math.abs(v - width0) > 1e-9)) {
    flags.push("LINEAR_CHAIN_VARIABLE_WIDTH_USE_FACE_GRAPH_FLAT");
  }

  const bendByPair = new Map<string, GeometrySourceV1["bends"][number]>();
  for (const bend of source.bends) {
    if (bend.axis !== "X") flags.push(`LINEAR_CHAIN_NON_X_USE_FACE_GRAPH_FLAT:${bend.bendId}`);
    if (bend.nobi.value < 0) flags.push(`NEGATIVE_NOBI:${bend.bendId}`);
    const key1 = `${bend.faceA}|${bend.faceB}`;
    const key2 = `${bend.faceB}|${bend.faceA}`;
    if (bendByPair.has(key1) || bendByPair.has(key2)) flags.push(`DUPLICATE_BEND_PAIR:${bend.bendId}`);
    bendByPair.set(key1, bend);
  }
  for (let i = 0; i < source.faceOrder.length - 1; i++) {
    const a = source.faceOrder[i]!;
    const b = source.faceOrder[i + 1]!;
    if (!bendByPair.has(`${a}|${b}`) && !bendByPair.has(`${b}|${a}`)) {
      flags.push(`CHAIN_ADJACENCY_BEND_MISSING:${a}->${b}`);
    }
  }

  const fold = foldBackResidual(source);
  flags.push(...fold.flags);
  if (flags.length) return { code: source.code, status: "REVIEW_REQUIRED", flags: unique(flags) };

  const numericLengths = lengths as number[];
  const width = width0 as number;
  const bendZones: CanonicalBendZone[] = [];
  const faceMap: CanonicalGeometryV1["faceMap"] = [];
  const transforms = new Map<string, Affine2>();
  let cumulativeOutside = 0;
  let cumulativeNobi = 0;

  for (let i = 0; i < ordered.length; i++) {
    const face = ordered[i]!;
    const start = i === 0 ? 0 : cumulativeOutside - cumulativeNobi;
    cumulativeOutside += numericLengths[i]!;
    const end = cumulativeOutside - cumulativeNobi;
    const reverse = face.unfoldDirection === "REVERSE";
    const flipY = face.transverseFlip;
    const transform: Affine2 = reverse
      ? { m00: -1, m01: 0, m10: 0, m11: flipY ? -1 : 1, tx: end, ty: flipY ? width : 0 }
      : { m00: 1, m01: 0, m10: 0, m11: flipY ? -1 : 1, tx: start, ty: flipY ? width : 0 };
    transforms.set(face.faceId, transform);
    faceMap.push({ faceId: face.faceId, flatStartX: start, flatEndX: end, transform });

    if (i < ordered.length - 1) {
      const next = ordered[i + 1]!;
      const bend = bendByPair.get(`${face.faceId}|${next.faceId}`) ??
        bendByPair.get(`${next.faceId}|${face.faceId}`)!;
      const nobi = bend.nobi.value;
      const x2 = end;
      const x1 = x2 - nobi;
      bendZones.push({
        bendId: bend.bendId,
        line1: { start: { x: x1, y: 0 }, end: { x: x1, y: width } },
        line2: { start: { x: x2, y: 0 }, end: { x: x2, y: width } },
        sign: bend.sign,
        angleDeg: bend.angleDeg.value,
        nobi
      });
      cumulativeNobi += nobi;
    }
  }

  const flatLength = cumulativeOutside - cumulativeNobi;
  if (!(flatLength > 0)) {
    return { code: source.code, status: "REVIEW_REQUIRED", flags: ["NONPOSITIVE_FLAT_LENGTH"] };
  }
  const outer = ensureCcw(source.flatOuterContour ?? [
    { x: 0, y: 0, bulge: 0 },
    { x: flatLength, y: 0, bulge: 0 },
    { x: flatLength, y: width, bulge: 0 },
    { x: 0, y: width, bulge: 0 }
  ]);
  const outerFlags = validateSimplePolygon(outer);
  if (outerFlags.length) return { code: source.code, status: "REVIEW_REQUIRED", flags: outerFlags };

  const features = canonicalizeFeatures(source, transforms);
  const materialFlags = [
    ...validateFeatureContainment(flattenBulged(outer), features),
    ...validateBendMaterial(flattenBulged(outer), features, bendZones)
  ];
  if (materialFlags.length) return { code: source.code, status: "REVIEW_REQUIRED", flags: unique(materialFlags) };

  const geometry: CanonicalGeometryV1 = {
    schema: "CANONICAL_GEOMETRY_V1",
    geometryId: `geo_${hashId(source)}`,
    jobId: job.jobId,
    code: source.code,
    units: "mm",
    buildKind: "LINEAR_CHAIN",
    sourceMode: job.mode,
    sourceSha256: source.sourceSha256,
    outerContours: [outer],
    features,
    bendZones,
    faceMap,
    qa: {
      polygonClosed: true,
      topologyClosed: true,
      faceGraphG1toG7: "PASS",
      foldBack: "PASS",
      numericResidualMaxMm: fold.max,
      checks: checksFor(source, true)
    },
    flags: []
  };
  return { code: source.code, status: "READY", geometry, flags: [] };
}

function buildFaceGraphFlat(job: CadJob, source: GeometrySourceV1): GeometryBuildResult {
  const flags = [
    ...validateSourceIdentity(job, source),
    ...validateFaceIds(source),
    ...requiredBentProofFlags(source),
    ...validateEvidenceFeatureOwnership(job, source)
  ];
  const route = routeForCode(job, source.code);
  if (route.mode !== "BEND_UNFOLD") flags.push("FACE_GRAPH_FLAT_REQUIRES_BEND_UNFOLD_ROUTE");
  if (!source.flatOuterContour || !source.flatOuterProofRefs?.length) {
    flags.push("FLAT_OUTER_CONTOUR_PROOF_MISSING");
  }

  const transforms = new Map<string, Affine2>();
  for (const face of source.faces) {
    if (!face.flatTransform || !face.transformProofRefs?.length) {
      flags.push(`FACE_FLAT_TRANSFORM_PROOF_MISSING:${face.faceId}`);
      continue;
    }
    flags.push(...rigidTransformFlags(face.flatTransform, face.faceId));
    transforms.set(face.faceId, face.flatTransform);
  }

  const bendIds = new Set<string>();
  for (const bend of source.bends) {
    if (bendIds.has(bend.bendId)) flags.push(`DUPLICATE_BEND_ID:${bend.bendId}`);
    bendIds.add(bend.bendId);
    if (!bend.flatLines) flags.push(`BEND_FLAT_DOMAIN_MISSING:${bend.bendId}`);
    if (bend.nobi.value < 0) flags.push(`NEGATIVE_NOBI:${bend.bendId}`);
  }
  const fold = foldBackResidual(source);
  flags.push(...fold.flags);

  if (flags.length) return { code: source.code, status: "REVIEW_REQUIRED", flags: unique(flags) };

  const outer = ensureCcw(source.flatOuterContour!);
  const outerFlags = validateSimplePolygon(outer);
  if (outerFlags.length) return { code: source.code, status: "REVIEW_REQUIRED", flags: outerFlags };

  for (const face of source.faces) {
    const t = transforms.get(face.faceId)!;
    const det = t.m00 * t.m11 - t.m01 * t.m10;
    const flatFace = face.contour.map((v) => ({
      ...transformPoint(v, t),
      bulge: det >= 0 ? v.bulge : -v.bulge
    }));
    for (const p of flattenBulged(flatFace)) {
      if (!pointInPolygon(p, flattenBulged(outer), true)) {
        flags.push(`TRANSFORMED_FACE_OUTSIDE_FLAT:${face.faceId}`);
        break;
      }
    }
  }

  const features = canonicalizeFeatures(source, transforms);
  const bendZones: CanonicalBendZone[] = source.bends.map((bend) => ({
    bendId: bend.bendId,
    line1: bend.flatLines!.line1,
    line2: bend.flatLines!.line2,
    sign: bend.sign,
    angleDeg: bend.angleDeg.value,
    nobi: bend.nobi.value
  }));
  flags.push(...validateFeatureContainment(flattenBulged(outer), features));
  flags.push(...validateBendMaterial(flattenBulged(outer), features, bendZones));
  if (flags.length) return { code: source.code, status: "REVIEW_REQUIRED", flags: unique(flags) };

  const geometry: CanonicalGeometryV1 = {
    schema: "CANONICAL_GEOMETRY_V1",
    geometryId: `geo_${hashId(source)}`,
    jobId: job.jobId,
    code: source.code,
    units: "mm",
    buildKind: "FACE_GRAPH_FLAT",
    sourceMode: job.mode,
    sourceSha256: source.sourceSha256,
    outerContours: [outer],
    features,
    bendZones,
    faceMap: source.faceOrder.map((faceId) => ({ faceId, transform: transforms.get(faceId)! })),
    qa: {
      polygonClosed: true,
      topologyClosed: true,
      faceGraphG1toG7: "PASS",
      foldBack: "PASS",
      numericResidualMaxMm: fold.max,
      checks: checksFor(source, true)
    },
    flags: []
  };
  return { code: source.code, status: "READY", geometry, flags: [] };
}

export function buildGeometrySource(job: CadJob, raw: unknown): GeometryBuildResult {
  const source = GeometrySourceV1.parse(raw);
  if (source.jobId !== job.jobId) {
    return { code: source.code, status: "REVIEW_REQUIRED", flags: ["GEOMETRY_JOB_MISMATCH"] };
  }
  evidenceForCode(job, source.code);
  routeForCode(job, source.code);

  if (source.buildKind === "FLAT_SINGLE_FACE") return buildFlat(job, source);
  if (source.buildKind === "LINEAR_CHAIN") return buildLinearChain(job, source);
  return buildFaceGraphFlat(job, source);
}

export function buildJobGeometry(job: CadJob, rawSources: unknown[]): {
  results: GeometryBuildResult[];
  ready: CanonicalGeometryV1[];
  flags: string[];
} {
  if (job.mode === "DIRECT_EXISTING_DXF_AUDIT") {
    throw new Error("GEOMETRY_BUILD_NOT_APPLICABLE_TO_DIRECT_AUDIT");
  }
  if (!["ROUTED", "REVIEW_REQUIRED"].includes(job.state)) {
    throw new Error(`GEOMETRY_BUILD_NOT_ALLOWED_IN_STATE: ${job.state}`);
  }
  if (job.routes.some((route) => route.status !== "ROUTED")) {
    throw new Error("GEOMETRY_BUILD_BLOCKED_BY_ROUTING_REVIEW");
  }

  const parsed = rawSources.map((raw) => GeometrySourceV1.parse(raw));
  const codes = job.routes.map((r) => r.code).sort();
  const inputCodes = parsed.map((s) => s.code).sort();
  if (new Set(inputCodes).size !== inputCodes.length) throw new Error("DUPLICATE_GEOMETRY_CODE");
  if (codes.join("|") !== inputCodes.join("|")) throw new Error("GEOMETRY_CODE_SET_MISMATCH");

  const results = parsed.map((source) => buildGeometrySource(job, source));
  const ready = results.flatMap((r) => r.geometry ? [r.geometry] : []);
  const flags = results.flatMap((r) => r.flags.map((flag) => `${r.code}:${flag}`));
  return { results, ready, flags };
}
