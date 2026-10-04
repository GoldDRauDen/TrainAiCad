import { readSnapshot } from "./snapshot.js";
import * as z from "zod/v4";
import type { CadJob } from "./model.js";
import { TechnicalNumber } from "./model.js";
import { deliveredImages, sha256 } from "./source.js";
export const SourceChecks = z.object({
  code: z.string().min(1),
  witnesses: z
    .array(
      z.object({
        id: z.string().min(1),
        faceId: z.string().optional(),
        contourVertex: z.number().int().nonnegative().optional(),
        featureId: z.string().optional(),
        instance: z.number().int().positive().optional(),
        sourceIdentity: z.string().min(1),
      }),
    )
    .min(1),
  dimensions: z
    .array(
      z.object({
        id: z.string().min(1),
        imageId: z.string().regex(/^[a-f0-9]{64}$/),
        printedText: z.string().min(1),
        from: z.string(),
        to: z.string(),
        axis: z.enum(["X", "Y"]),
        semantic: z.enum(["BASELINE", "CHAIN", "LOCAL", "OVERALL", "ORDINATE"]),
        value: TechnicalNumber,
      }),
    )
    .min(1),
});
export type SourceChecks = z.infer<typeof SourceChecks>;
export type QaReport = {
  code: string;
  geometryHash: string;
  ruleSnapshotId: string;
  sourceSha256: string;
  computedAt: string;
  dimensionResiduals: { id: string; residualMm: number }[];
  status: "RESEARCH_GEOMETRY_CHECKED" | "REVIEW_REQUIRED";
  flags: string[];
  limitation: string;
};
function inside(x: number, y: number, p: { x: number; y: number }[]) {
  let yes = false;
  for (let i = 0, j = p.length - 1; i < p.length; j = i++) {
    const a = p[i]!,
      b = p[j]!;
    if (
      a.y > y !== b.y > y &&
      x < ((b.x - a.x) * (y - a.y)) / (b.y - a.y) + a.x
    )
      yes = !yes;
  }
  return yes;
}
function distance(
  x: number,
  y: number,
  a: { x: number; y: number },
  b: { x: number; y: number },
) {
  const dx = b.x - a.x,
    dy = b.y - a.y,
    t = Math.max(
      0,
      Math.min(1, ((x - a.x) * dx + (y - a.y) * dy) / (dx * dx + dy * dy)),
    );
  return Math.hypot(x - a.x - t * dx, y - a.y - t * dy);
}
export function verifyGeometry(job: CadJob, raw: unknown[]): QaReport[] {
  if (job.state !== "GEOMETRY_READY")
    throw new Error("QA_REQUIRES_GEOMETRY_READY");
  const checks = raw.map((x) => SourceChecks.parse(x));
  if (
    new Set(checks.map((x) => x.code)).size !== checks.length ||
    checks.length !== job.geometry.length
  )
    throw new Error("QA_CODE_SET_MISMATCH");
  const images = deliveredImages(job);
  return job.geometry.map((g) => {
    const c = checks.find((x) => x.code === g.code);
    if (!c) throw new Error("QA_CODE_SET_MISMATCH");
    const e = job.evidence.find((x) => x.code === g.code)!,
      flags: string[] = [];
    if (
      new Set(c.witnesses.map((w) => w.id)).size !== c.witnesses.length ||
      new Set(c.dimensions.map((d) => d.id)).size !== c.dimensions.length
    )
      throw new Error("DUPLICATE_DIMENSION_OR_WITNESS_ID");
    if (job.mode !== "PDF_ONLY")
      flags.push("RAW_DATA_BIDIRECTIONAL_QA_NOT_IMPLEMENTED");
    if (g.buildKind !== "FLAT_SINGLE_FACE")
      flags.push("SIGNED_FOLD_BACK_NOT_IMPLEMENTED");
    if (g.outerBulges.some((b) => b.some((x) => x !== 0)))
      flags.push("CURVED_CONTAINMENT_NOT_IMPLEMENTED");
    if (
      !e.census ||
      Object.keys(readSnapshot(job.production).router.feature_routes).some(
        (k) =>
          !e.census?.[k] ||
          e.census[k]!.state === "UNKNOWN" ||
          !e.census[k]!.evidence.length,
      )
    )
      flags.push("FINAL_CENSUS_NOT_CLOSED");
    const resolve = (id: string) => {
      const w = c.witnesses.find((x) => x.id === id);
      if (!w) throw new Error(`DIMENSION_WITNESS_NOT_FOUND:${id}`);
      if (w.featureId) {
        const f = g.features.find(
          (x) =>
            x.featureId === w.featureId && x.instance === (w.instance ?? 1),
        );
        if (f?.geometry.kind !== "CIRCLE")
          throw new Error(`WITNESS_FEATURE_UNSUPPORTED:${id}`);
        return f.geometry.center;
      }
      if (w.faceId !== g.faceMap[0]?.faceId || w.contourVertex === undefined)
        throw new Error(`WITNESS_OWNER_UNPROVED:${id}`);
      const p = g.outerContours[0]?.[w.contourVertex];
      if (!p) throw new Error(`WITNESS_VERTEX_MISSING:${id}`);
      return p;
    };
    const residuals = c.dimensions.map((d) => {
      if (
        !images.some(
          (im) => im.imageId === d.imageId && im.page === e.source.page,
        )
      )
        flags.push(`SOURCE_IMAGE_NOT_DELIVERED:${d.id}`);
      if (
        d.value.unit !== "mm" ||
        !["PRINTED", "HANDWRITTEN", "DERIVED", "USER_CONFIRMED"].includes(
          d.value.origin,
        )
      )
        flags.push(`UNPROVED_DIMENSION:${d.id}`);
      const a = resolve(d.from),
        b = resolve(d.to),
        axis = d.axis.toLowerCase() as "x" | "y",
        residualMm = Math.abs(Math.abs(b[axis] - a[axis]) - d.value.value);
      if (residualMm > 1e-7) flags.push(`SOURCE_DIMENSION_MISMATCH:${d.id}`);
      return { id: d.id, residualMm };
    });
    for (const axis of ["X", "Y"] as const) {
      const connected = new Set(
        c.witnesses
          .filter(
            (w) =>
              w.faceId === g.faceMap[0]?.faceId &&
              w.contourVertex !== undefined,
          )
          .map((w) => w.id),
      );
      let changed = true;
      while (changed) {
        changed = false;
        for (const d of c.dimensions.filter((d) => d.axis === axis)) {
          if (connected.has(d.from) && !connected.has(d.to)) {
            connected.add(d.to);
            changed = true;
          }
          if (connected.has(d.to) && !connected.has(d.from)) {
            connected.add(d.from);
            changed = true;
          }
        }
      }
      for (const f of g.features)
        if (
          !c.witnesses.some(
            (w) =>
              w.featureId === f.featureId &&
              (w.instance ?? 1) === f.instance &&
              connected.has(w.id),
          )
        )
          flags.push(
            `FEATURE_DATUM_PATH_UNPROVED:${f.featureId}:${f.instance}:${axis}`,
          );
    }
    for (const [axis, d] of [
      ["x", e.contour.overallX],
      ["y", e.contour.overallY],
    ] as const) {
      const points = g.outerContours[0]!;
      if (
        d &&
        Math.abs(
          Math.max(...points.map((p) => p[axis])) -
            Math.min(...points.map((p) => p[axis])) -
            d.value,
        ) > 1e-7
      )
        flags.push(`CONTOUR_OVERALL_MISMATCH:${axis}`);
    }
    for (const f of g.features) {
      const s = e.features.find((x) => x.id === f.featureId);
      if (!s && !e.markings.some((x) => x.id === f.featureId))
        flags.push(`EXTRA_FEATURE:${f.featureId}`);
      if (f.geometry.kind !== "CIRCLE") {
        flags.push(`FEATURE_QA_NOT_IMPLEMENTED:${f.featureId}`);
        continue;
      }
      if (
        !s?.diameter ||
        s.diameter.unit !== "mm" ||
        Math.abs(s.diameter.value - f.geometry.diameter) > 1e-7
      )
        flags.push(`FEATURE_DIAMETER_MISMATCH:${f.featureId}`);
      const { x, y } = f.geometry.center,
        p = g.outerContours[0]!,
        r = f.geometry.diameter / 2;
      if (
        !inside(x, y, p) ||
        p.some((a, i) => distance(x, y, a, p[(i + 1) % p.length]!) < r - 1e-7)
      )
        flags.push(`FEATURE_OUTSIDE_MATERIAL:${f.featureId}:${f.instance}`);
    }
    for (let i = 0; i < g.features.length; i++)
      for (let j = i + 1; j < g.features.length; j++) {
        const a = g.features[i]!.geometry,
          b = g.features[j]!.geometry;
        if (
          a.kind === "CIRCLE" &&
          b.kind === "CIRCLE" &&
          Math.hypot(a.center.x - b.center.x, a.center.y - b.center.y) <
            (a.diameter + b.diameter) / 2 - 1e-7
        )
          flags.push("OVERLAPPING_CUT_NEEDS_PROVED_UNION");
      }
    return {
      code: g.code,
      geometryHash: sha256(JSON.stringify(g)),
      ruleSnapshotId: job.production.snapshotId,
      sourceSha256: job.source.sha256,
      computedAt: new Date().toISOString(),
      dimensionResiduals: residuals,
      status: flags.length ? "REVIEW_REQUIRED" : "RESEARCH_GEOMETRY_CHECKED",
      flags: [...new Set(flags)],
      limitation:
        "Witness identity and source interpretation remain model-supplied. Material/R/C rules and source-semantic QA are not certified by these numeric checks.",
    };
  });
}
