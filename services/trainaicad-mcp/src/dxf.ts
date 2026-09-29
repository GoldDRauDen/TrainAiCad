import { createHash } from "node:crypto";
import { execFileSync } from "node:child_process";
import {
  existsSync,
  mkdirSync,
  readFileSync,
  statSync,
  writeFileSync
} from "node:fs";
import { basename, join } from "node:path";
import { dataRoot } from "./ingest.js";
import { type CanonicalFeature, type CanonicalGeometryV1, type PolyVertex } from "./geometry.js";
import type { CadEvidenceV1, CadJob, DxfArtifact, DxfQaFamilies } from "./model.js";

type DxfEntity =
  | { type: "LWPOLYLINE"; role: string; closed: boolean; vertices: [number, number, number][]; color?: number; linetype?: string }
  | { type: "CIRCLE"; role: string; center: [number, number]; radius: number; color?: number; linetype?: string }
  | { type: "LINE"; role: string; start: [number, number]; end: [number, number]; color?: number; linetype?: string }
  | { type: "ARC"; role: string; center: [number, number]; radius: number; start_angle: number; end_angle: number; color?: number; linetype?: string }
  | { type: "POINT"; role: string; point: [number, number]; color?: number; linetype?: string };

type ExportPart = {
  code: string;
  material: string;
  thickness_mm: number;
  status: "PASS";
  checks: CanonicalGeometryV1["qa"]["checks"];
  entities: DxfEntity[];
};

type ExportPayload = {
  job_id: string;
  parts: ExportPart[];
};

type ExportManifest = {
  contract: string;
  job_id: string;
  coordinate_units: string;
  status: "PASS" | "REVIEW_ONLY";
  filename: string;
  parts: Array<{
    code: string;
    entity_count: number;
    checks: Record<string, string>;
  }>;
  positions: Array<{
    code: string;
    translation_mm: [number, number];
    entity_count: number;
  }>;
};

type ReadbackEntity = {
  type: string;
  layer: string;
  color: number;
  linetype: string;
  [key: string]: unknown;
};

type Readback = {
  audit_errors: number;
  insunits: number;
  measurement: number;
  entity_count: number;
  layer_counts: Record<string, number>;
  type_counts: Record<string, number>;
  layer0: ReadbackEntity[];
  meta: ReadbackEntity[];
};

function round(value: number, digits = 6): number {
  const factor = 10 ** digits;
  return Math.round(value * factor) / factor;
}

function sha256File(path: string): string {
  return createHash("sha256").update(readFileSync(path)).digest("hex");
}

function reverseBulged(vertices: PolyVertex[]): PolyVertex[] {
  const reversed = [...vertices].reverse();
  return reversed.map((v, i) => {
    const next = reversed[(i + 1) % reversed.length]!;
    return { x: v.x, y: v.y, bulge: -next.bulge };
  });
}

function sampledArea(vertices: PolyVertex[]): number {
  let area = 0;
  for (let i = 0; i < vertices.length; i++) {
    const a = vertices[i]!;
    const b = vertices[(i + 1) % vertices.length]!;
    area += (a.x * b.y - b.x * a.y) / 2;
    if (a.bulge) {
      const chord = Math.hypot(b.x - a.x, b.y - a.y);
      const theta = 4 * Math.atan(a.bulge);
      const radius = chord / (2 * Math.abs(Math.sin(theta / 2)));
      area += radius * radius * (theta - Math.sin(theta)) / 2;
    }
  }
  return area;
}

function orientVertices(vertices: PolyVertex[], ccw: boolean): PolyVertex[] {
  const area = sampledArea(vertices);
  if (Math.abs(area) <= 1e-12) return vertices;
  return (area > 0) === ccw ? vertices : reverseBulged(vertices);
}

function lwpolyline(role: string, vertices: PolyVertex[], closed: boolean, ccw?: boolean, color?: number): DxfEntity {
  const ordered = ccw === undefined ? vertices : orientVertices(vertices, ccw);
  return {
    type: "LWPOLYLINE",
    role,
    closed,
    vertices: ordered.map((v) => [v.x, v.y, v.bulge ?? 0]),
    ...(color && color !== 256 ? { color } : {})
  };
}

function slotVertices(feature: Extract<CanonicalFeature["geometry"], { kind: "SLOT" }>): PolyVertex[] {
  const r = feature.width / 2;
  const halfStraight = (feature.overallLength - feature.width) / 2;
  const local = [
    { x: -halfStraight, y: r, bulge: 0 },
    { x: halfStraight, y: r, bulge: -1 },
    { x: halfStraight, y: -r, bulge: 0 },
    { x: -halfStraight, y: -r, bulge: -1 }
  ];
  const a = feature.angleDeg * Math.PI / 180;
  const ca = Math.cos(a);
  const sa = Math.sin(a);
  return local.map((v) => ({
    x: feature.center.x + v.x * ca - v.y * sa,
    y: feature.center.y + v.x * sa + v.y * ca,
    bulge: v.bulge
  }));
}

function featureEntity(feature: CanonicalFeature): DxfEntity {
  const g = feature.geometry;
  const green = feature.style === "THROUGH_PIERCING_GREEN" || feature.style === "RELIEF_GREEN";

  if (feature.family === "RIB") {
    throw new Error(`RIB_MUST_BE_INDEPENDENT_PART:${feature.featureId}`);
  }
  if (feature.family === "CHAMFER" || feature.family === "RADIUS") {
    throw new Error(`RC_MUST_BE_BAKED_INTO_CANONICAL_CONTOUR:${feature.featureId}`);
  }
  if (feature.family === "OTHER") {
    throw new Error(`UNSUPPORTED_PRODUCTION_FEATURE_FAMILY:${feature.featureId}`);
  }

  if (feature.family === "HOLE" || feature.family === "TAP") {
    if (g.kind !== "CIRCLE") throw new Error(`ROUND_HOLE_REQUIRES_CIRCLE:${feature.featureId}`);
    return {
      type: "CIRCLE",
      role: "hole",
      center: [g.center.x, g.center.y],
      radius: g.diameter / 2
    };
  }

  if (feature.family === "SLOT") {
    if (g.kind !== "SLOT") throw new Error(`STRAIGHT_SLOT_REQUIRES_SLOT_GEOMETRY:${feature.featureId}`);
    return lwpolyline("slot", slotVertices(g), true, false);
  }

  if (feature.family === "CURVED_SLOT") {
    if (g.kind !== "POLYLINE" || !g.closed) {
      throw new Error(`CURVED_SLOT_REQUIRES_ONE_CLOSED_BULGED_POLYLINE:${feature.featureId}`);
    }
    return lwpolyline("slot", g.vertices, true, false);
  }

  if (feature.family === "CUTOUT") {
    if (g.kind !== "POLYLINE" || !g.closed) {
      throw new Error(`CUTOUT_REQUIRES_CLOSED_POLYLINE:${feature.featureId}`);
    }
    return lwpolyline("cutout", g.vertices, true, false);
  }

  if (feature.family === "PIASU") {
    if (g.kind !== "POINT") throw new Error(`PIASU_REQUIRES_POINT:${feature.featureId}`);
    return {
      type: "POINT",
      role: feature.style === "THROUGH_PIERCING_GREEN" ? "through_piercing" : "ordinary_point",
      point: [g.point.x, g.point.y],
      ...(feature.style === "THROUGH_PIERCING_GREEN" ? { color: 3 } : {})
    };
  }

  const role = feature.family === "KEGAKI"
    ? "kegaki"
    : feature.family === "SLIT_RELIEF"
      ? "relief"
      : feature.family === "FORMING"
        ? "forming"
        : feature.family.toLowerCase();
  const color = feature.family === "KEGAKI" ? 1 : green ? 3 : undefined;

  if (g.kind === "LINE") {
    return {
      type: "LINE",
      role,
      start: [g.start.x, g.start.y],
      end: [g.end.x, g.end.y],
      ...(color ? { color } : {})
    };
  }
  if (g.kind === "ARC") {
    return {
      type: "ARC",
      role,
      center: [g.center.x, g.center.y],
      radius: g.radius,
      start_angle: g.startAngleDeg,
      end_angle: g.endAngleDeg,
      ...(color ? { color } : {})
    };
  }
  if (g.kind === "POLYLINE") {
    return lwpolyline(role, g.vertices, g.closed, undefined, color);
  }
  if (g.kind === "POINT") {
    return {
      type: "POINT",
      role,
      point: [g.point.x, g.point.y],
      ...(color ? { color } : {})
    };
  }
  throw new Error(`FEATURE_GEOMETRY_NOT_SERIALIZABLE:${feature.featureId}:${g.kind}`);
}

function geometryEntities(geometry: CanonicalGeometryV1): DxfEntity[] {
  if (geometry.outerContours.length !== 1) {
    throw new Error(`EXACTLY_ONE_OUTER_CONTOUR_REQUIRED:${geometry.code}`);
  }
  const entities: DxfEntity[] = [
    lwpolyline("outer", geometry.outerContours[0]!, true, true)
  ];
  for (const feature of geometry.features) entities.push(featureEntity(feature));
  for (const bend of geometry.bendZones) {
    entities.push({
      type: "LINE",
      role: "bend",
      start: [bend.line1.start.x, bend.line1.start.y],
      end: [bend.line1.end.x, bend.line1.end.y],
      linetype: "DASHED"
    });
    entities.push({
      type: "LINE",
      role: "bend",
      start: [bend.line2.start.x, bend.line2.start.y],
      end: [bend.line2.end.x, bend.line2.end.y],
      linetype: "DASHED"
    });
  }
  return entities;
}

function evidenceFor(job: CadJob, code: string): CadEvidenceV1 {
  const evidence = job.evidence.find((e) => e.code === code);
  if (!evidence) throw new Error(`DXF_EVIDENCE_MISSING:${code}`);
  return evidence;
}

export function buildExportPayload(job: CadJob): ExportPayload {
  if (job.state !== "GEOMETRY_READY") throw new Error(`DXF_EXPORT_NOT_ALLOWED_IN_STATE:${job.state}`);
  if (job.flags.length) throw new Error("DXF_EXPORT_BLOCKED_BY_FLAGS");
  if (job.geometry.length !== job.evidence.length) throw new Error("DXF_GEOMETRY_CODE_COUNT_MISMATCH");

  const byCode = new Map(job.geometry.map((g) => [g.code, g] as const));
  const parts: ExportPart[] = [];
  for (const evidence of job.evidence) {
    const geometry = byCode.get(evidence.code);
    if (!geometry) throw new Error(`DXF_GEOMETRY_MISSING:${evidence.code}`);
    if (geometry.flags.length) throw new Error(`DXF_GEOMETRY_FLAGGED:${evidence.code}`);
    if (geometry.qa.foldBack !== "PASS" && geometry.qa.foldBack !== "NOT_APPLICABLE") {
      throw new Error(`DXF_FOLDBACK_NOT_PASS:${evidence.code}`);
    }
    const material = evidence.material.printed ?? evidence.material.family;
    const thickness = evidence.material.thickness?.value;
    if (!material) throw new Error(`DXF_MATERIAL_MISSING:${evidence.code}`);
    if (!(thickness && thickness > 0)) throw new Error(`DXF_THICKNESS_MISSING:${evidence.code}`);
    parts.push({
      code: evidence.code,
      material,
      thickness_mm: thickness,
      status: "PASS",
      checks: geometry.qa.checks,
      entities: geometryEntities(geometry)
    });
  }
  return { job_id: job.jobId, parts };
}

function pythonBin(): string {
  if (process.env.TRAINAICAD_PYTHON) return process.env.TRAINAICAD_PYTHON;
  return process.platform === "win32" ? "python" : "python3";
}

function normalizeNumber(value: number, digits = 6): number {
  return round(value, digits);
}

function translatedEntity(entity: DxfEntity, dx: number, dy: number): ReadbackEntity {
  const base = {
    type: entity.type,
    layer: "0",
    color: entity.color ?? 256,
    linetype: entity.linetype ?? "BYLAYER"
  };
  if (entity.type === "LWPOLYLINE") {
    return {
      ...base,
      closed: entity.closed,
      vertices: entity.vertices.map(([x, y, bulge]) => [
        normalizeNumber(x + dx),
        normalizeNumber(y + dy),
        round(bulge, 8)
      ])
    };
  }
  if (entity.type === "CIRCLE") {
    return {
      ...base,
      center: [normalizeNumber(entity.center[0] + dx), normalizeNumber(entity.center[1] + dy)],
      radius: normalizeNumber(entity.radius)
    };
  }
  if (entity.type === "LINE") {
    return {
      ...base,
      start: [normalizeNumber(entity.start[0] + dx), normalizeNumber(entity.start[1] + dy)],
      end: [normalizeNumber(entity.end[0] + dx), normalizeNumber(entity.end[1] + dy)]
    };
  }
  if (entity.type === "ARC") {
    return {
      ...base,
      center: [normalizeNumber(entity.center[0] + dx), normalizeNumber(entity.center[1] + dy)],
      radius: normalizeNumber(entity.radius),
      start_angle: normalizeNumber(entity.start_angle),
      end_angle: normalizeNumber(entity.end_angle)
    };
  }
  return {
    ...base,
    point: [normalizeNumber(entity.point[0] + dx), normalizeNumber(entity.point[1] + dy)]
  };
}

function expectedReadback(payload: ExportPayload, manifest: ExportManifest): ReadbackEntity[] {
  const byCode = new Map(payload.parts.map((p) => [p.code, p] as const));
  return manifest.positions.flatMap((position) => {
    const part = byCode.get(position.code);
    if (!part) throw new Error(`DXF_MANIFEST_UNKNOWN_CODE:${position.code}`);
    const [dx, dy] = position.translation_mm;
    return part.entities.map((entity) => translatedEntity(entity, dx, dy));
  });
}

function roleCounts(payload: ExportPayload): Record<string, number> {
  const counts: Record<string, number> = {};
  for (const part of payload.parts) {
    for (const entity of part.entities) {
      counts[entity.role] = (counts[entity.role] ?? 0) + 1;
    }
  }
  return counts;
}

function qaFamilies(payload: ExportPayload, job: CadJob): DxfQaFamilies {
  const counts = roleCounts(payload);
  const ribParts = job.evidence.filter((e) => e.partRole === "RIB").length;
  return {
    CUT: { status: "PASS", entities: (counts.outer ?? 0) + (counts.cutout ?? 0) },
    HOLE_SLOT: { status: (counts.hole ?? 0) + (counts.slot ?? 0) ? "PASS" : "N/A", entities: (counts.hole ?? 0) + (counts.slot ?? 0) },
    BEND: { status: counts.bend ? "PASS" : "N/A", entities: counts.bend ?? 0 },
    KEGAKI: { status: counts.kegaki ? "PASS" : "N/A", entities: counts.kegaki ?? 0 },
    RIB: { status: ribParts ? "PASS" : "N/A", entities: ribParts },
    PIASU_SLIT_FORMING: {
      status: (counts.through_piercing ?? 0) + (counts.ordinary_point ?? 0) + (counts.relief ?? 0) + (counts.forming ?? 0) ? "PASS" : "N/A",
      entities: (counts.through_piercing ?? 0) + (counts.ordinary_point ?? 0) + (counts.relief ?? 0) + (counts.forming ?? 0)
    }
  };
}


export function exportDxf(job: CadJob, repoRoot: string): DxfArtifact {
  const payload = buildExportPayload(job);
  const root = join(dataRoot(), "outputs", job.jobId);
  const outDir = join(root, "dxf");
  mkdirSync(outDir, { recursive: true });
  const input = join(root, "canonical_job.json");
  writeFileSync(input, JSON.stringify(payload, null, 2));

  const exporter = join(repoRoot, "tools", "export_dxf.py");
  const stdout = execFileSync(
    pythonBin(),
    [exporter, input, outDir, "--write-manifest"],
    { cwd: repoRoot, encoding: "utf8", stdio: ["ignore", "pipe", "pipe"] }
  ).trim();
  const lines = stdout.split(/\r?\n/).filter(Boolean);
  const result = JSON.parse(lines.at(-1) ?? "{}") as { files?: string[] };
  const dxfName = result.files?.find((f) => f.toLowerCase().endsWith(".dxf"));
  if (!dxfName) throw new Error("DXF_EXPORTER_RETURNED_NO_DXF");
  const dxfPath = join(outDir, basename(dxfName));
  const manifestPath = join(outDir, `${job.jobId}_MANIFEST.json`);
  if (!existsSync(dxfPath) || !existsSync(manifestPath)) throw new Error("DXF_EXPORT_OUTPUT_MISSING");

  const manifest = JSON.parse(readFileSync(manifestPath, "utf8")) as ExportManifest;
  if (manifest.status !== "PASS") throw new Error("DXF_EXPORT_UNEXPECTED_REVIEW_ONLY");

  return {
    filename: basename(dxfPath),
    relativePath: join("outputs", job.jobId, "dxf", basename(dxfPath)).replaceAll("\\", "/"),
    sha256: sha256File(dxfPath),
    bytes: statSync(dxfPath).size,
    units: "mm",
    manifestRelativePath: join("outputs", job.jobId, "dxf", basename(manifestPath)).replaceAll("\\", "/")
  };
}

export function auditDxf(job: CadJob, repoRoot: string): DxfArtifact {
  if (!job.output) throw new Error("DXF_ARTIFACT_MISSING");
  const payload = buildExportPayload({ ...job, state: "GEOMETRY_READY" });
  const dxfPath = join(dataRoot(), job.output.relativePath);
  const manifestPath = join(dataRoot(), job.output.manifestRelativePath);
  if (!existsSync(dxfPath) || !existsSync(manifestPath)) throw new Error("DXF_AUDIT_INPUT_MISSING");
  if (sha256File(dxfPath) !== job.output.sha256) throw new Error("DXF_ARTIFACT_SHA_CHANGED");

  const manifest = JSON.parse(readFileSync(manifestPath, "utf8")) as ExportManifest;
  const readbackScript = join(repoRoot, "services", "trainaicad-mcp", "python", "readback_dxf.py");
  const readbackStdout = execFileSync(
    pythonBin(),
    [readbackScript, dxfPath],
    { cwd: repoRoot, encoding: "utf8", stdio: ["ignore", "pipe", "pipe"] }
  ).trim();
  const readback = JSON.parse(readbackStdout) as Readback;

  if (readback.audit_errors !== 0) throw new Error("DXF_READBACK_AUDIT_ERRORS");
  if (readback.insunits !== 4 || readback.measurement !== 1) throw new Error("DXF_READBACK_UNIT_FAILURE");

  const expected = expectedReadback(payload, manifest);
  if (JSON.stringify(readback.layer0) !== JSON.stringify(expected)) {
    throw new Error("DXF_READBACK_CANONICAL_MISMATCH");
  }

  const expectedLabels = payload.parts.map((p) => p.code);
  const actualLabels = readback.meta
    .filter((e) => e.type === "TEXT")
    .map((e) => String(e.text ?? ""))
    .filter((text) => expectedLabels.includes(text));
  if (JSON.stringify(actualLabels) !== JSON.stringify(expectedLabels)) {
    throw new Error("DXF_READBACK_CODE_MAPPING_FAILURE");
  }

  return {
    ...job.output,
    readback: {
      auditErrors: readback.audit_errors,
      layer0Entities: readback.layer0.length,
      metaEntities: readback.meta.length,
      canonicalMatch: true,
      codeOrderMatch: true,
      unitsMatch: true
    },
    families: qaFamilies(payload, job)
  };
}
