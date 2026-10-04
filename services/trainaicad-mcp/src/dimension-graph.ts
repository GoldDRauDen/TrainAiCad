import * as z from "zod/v4";

const DimensionClass = z.enum([
  "BASELINE", "CHAIN", "LOCAL", "OVERALL", "ORDINATE",
  "EDGE_CENTER", "CENTER_CENTER"
]);

export const DimensionGraphV1 = z.object({
  schema: z.literal("CAD_DIMENSION_GRAPH_V1"),
  jobId: z.string().min(1),
  code: z.string().min(1),
  sourceSha256: z.string().regex(/^[a-f0-9]{64}$/),
  page: z.number().int().positive(),
  datumNodeId: z.string().min(1),
  requiredNodeIds: z.array(z.string().min(1)).min(1),
  dimensions: z.array(z.object({
    id: z.string().min(1),
    startWitnessId: z.string().min(1),
    endWitnessId: z.string().min(1),
    axis: z.enum(["X", "Y"]),
    positiveDirection: z.union([z.literal(-1), z.literal(1)]),
    valueMm: z.number().finite().positive(),
    printedText: z.string().min(1),
    dimensionClass: DimensionClass,
    sourceReceiptId: z.string().min(1)
  })).min(1)
});
export type DimensionGraphV1 = z.infer<typeof DimensionGraphV1>;

export type DimensionGraphSolutionV1 = {
  schema: "CAD_DIMENSION_SOLUTION_V1";
  jobId: string;
  code: string;
  sourceSha256: string;
  page: number;
  datumNodeId: string;
  status: "SOLVED" | "REVIEW_REQUIRED";
  nodes: Array<{
    nodeId: string;
    xMm: number | null;
    yMm: number | null;
    xDerivedFrom: string[];
    yDerivedFrom: string[];
  }>;
  derivations: Array<{
    dimensionId: string;
    axis: "X" | "Y";
    startWitnessId: string;
    endWitnessId: string;
    expression: string;
    valueMm: number;
    sourceReceiptId: string;
  }>;
  flags: string[];
};

type AxisSolution = {
  values: Map<string, number>;
  derivations: Map<string, Set<string>>;
  flags: string[];
};

function solveAxis(graph: DimensionGraphV1, axis: "X" | "Y"): AxisSolution {
  const edges = graph.dimensions.filter((dimension) => dimension.axis === axis);
  const adjacency = new Map<string, Array<{ node: string; delta: number; id: string }>>();
  for (const edge of edges) {
    const forward = adjacency.get(edge.startWitnessId) ?? [];
    forward.push({ node: edge.endWitnessId, delta: edge.positiveDirection * edge.valueMm, id: edge.id });
    adjacency.set(edge.startWitnessId, forward);
    const reverse = adjacency.get(edge.endWitnessId) ?? [];
    reverse.push({ node: edge.startWitnessId, delta: -edge.positiveDirection * edge.valueMm, id: edge.id });
    adjacency.set(edge.endWitnessId, reverse);
  }

  const values = new Map<string, number>([[graph.datumNodeId, 0]]);
  const derivations = new Map<string, Set<string>>([[graph.datumNodeId, new Set()]]);
  const queue = [graph.datumNodeId];
  const flags: string[] = [];
  for (let index = 0; index < queue.length; index++) {
    const from = queue[index]!;
    for (const edge of adjacency.get(from) ?? []) {
      const candidate = values.get(from)! + edge.delta;
      const path = new Set(derivations.get(from));
      path.add(edge.id);
      if (!values.has(edge.node)) {
        values.set(edge.node, candidate);
        derivations.set(edge.node, path);
        queue.push(edge.node);
      } else if (Math.abs(values.get(edge.node)! - candidate) > 1e-9) {
        flags.push(`DIMENSION_GRAPH_INCONSISTENT:${axis}:${edge.id}`);
      }
    }
  }
  return { values, derivations, flags };
}

export function solveDimensionGraph(
  raw: unknown,
  trusted: { jobId: string; sourceSha256: string; receipts: Map<string, { sourceSha256: string; page: number }> }
): DimensionGraphSolutionV1 {
  const graph = DimensionGraphV1.parse(raw);
  const flags: string[] = [];
  if (graph.jobId !== trusted.jobId) flags.push("DIMENSION_GRAPH_JOB_MISMATCH");
  if (graph.sourceSha256 !== trusted.sourceSha256) flags.push("DIMENSION_GRAPH_SOURCE_MISMATCH");

  const ids = new Set<string>();
  for (const dimension of graph.dimensions) {
    if (ids.has(dimension.id)) flags.push(`DIMENSION_ID_DUPLICATE:${dimension.id}`);
    ids.add(dimension.id);
    if (dimension.startWitnessId === dimension.endWitnessId) {
      flags.push(`DIMENSION_WITNESSES_IDENTICAL:${dimension.id}`);
    }
    const receipt = trusted.receipts.get(dimension.sourceReceiptId);
    if (!receipt || receipt.sourceSha256 !== graph.sourceSha256 || receipt.page !== graph.page) {
      flags.push(`DIMENSION_SOURCE_RECEIPT_UNVERIFIED:${dimension.id}`);
    }
  }

  const x = solveAxis(graph, "X");
  const y = solveAxis(graph, "Y");
  flags.push(...x.flags, ...y.flags);
  for (const nodeId of graph.requiredNodeIds) {
    if (!x.values.has(nodeId)) flags.push(`DIMENSION_X_UNRESOLVED:${nodeId}`);
    if (!y.values.has(nodeId)) flags.push(`DIMENSION_Y_UNRESOLVED:${nodeId}`);
  }

  return {
    schema: "CAD_DIMENSION_SOLUTION_V1",
    jobId: graph.jobId,
    code: graph.code,
    sourceSha256: graph.sourceSha256,
    page: graph.page,
    datumNodeId: graph.datumNodeId,
    status: flags.length ? "REVIEW_REQUIRED" : "SOLVED",
    nodes: [...new Set([graph.datumNodeId, ...graph.requiredNodeIds,
      ...graph.dimensions.flatMap((d) => [d.startWitnessId, d.endWitnessId])])]
      .sort().map((nodeId) => ({
        nodeId,
        xMm: x.values.get(nodeId) ?? null,
        yMm: y.values.get(nodeId) ?? null,
        xDerivedFrom: [...(x.derivations.get(nodeId) ?? [])].sort(),
        yDerivedFrom: [...(y.derivations.get(nodeId) ?? [])].sort()
      })),
    derivations: graph.dimensions.map((dimension) => ({
      dimensionId: dimension.id,
      axis: dimension.axis,
      startWitnessId: dimension.startWitnessId,
      endWitnessId: dimension.endWitnessId,
      expression: `${dimension.endWitnessId} = ${dimension.startWitnessId} ${dimension.positiveDirection === 1 ? "+" : "-"} ${dimension.valueMm}`,
      valueMm: dimension.valueMm,
      sourceReceiptId: dimension.sourceReceiptId
    })),
    flags: [...new Set(flags)]
  };
}
