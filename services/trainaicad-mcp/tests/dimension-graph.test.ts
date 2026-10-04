import assert from "node:assert/strict";
import test from "node:test";
import { solveDimensionGraph, type DimensionGraphV1 } from "../src/dimension-graph.js";

const sourceSha256 = "a".repeat(64);
const receipt = "receipt-page-1";
const trustedReceipts = new Map([[receipt, { sourceSha256, page: 1 }]]);

function graph(dimensions: DimensionGraphV1["dimensions"]): DimensionGraphV1 {
  return {
    schema: "CAD_DIMENSION_GRAPH_V1",
    jobId: "cad_test",
    code: "P-1",
    sourceSha256,
    page: 1,
    datumNodeId: "A",
    requiredNodeIds: ["A", "B", "C", "D"],
    dimensions
  };
}

test("dimension graph deterministically derives baseline, chain and orthogonal coordinates", () => {
  const result = solveDimensionGraph(graph([
    { id: "d1", startWitnessId: "A", endWitnessId: "B", axis: "X", positiveDirection: 1, valueMm: 20, printedText: "20", dimensionClass: "BASELINE", sourceReceiptId: receipt },
    { id: "d2", startWitnessId: "B", endWitnessId: "C", axis: "X", positiveDirection: 1, valueMm: 15, printedText: "15", dimensionClass: "CHAIN", sourceReceiptId: receipt },
    { id: "d3", startWitnessId: "A", endWitnessId: "C", axis: "Y", positiveDirection: -1, valueMm: 30, printedText: "30", dimensionClass: "ORDINATE", sourceReceiptId: receipt },
    { id: "d4", startWitnessId: "C", endWitnessId: "D", axis: "X", positiveDirection: -1, valueMm: 5, printedText: "5", dimensionClass: "LOCAL", sourceReceiptId: receipt },
    { id: "d5", startWitnessId: "B", endWitnessId: "D", axis: "Y", positiveDirection: -1, valueMm: 10, printedText: "10", dimensionClass: "CHAIN", sourceReceiptId: receipt },
    { id: "d6", startWitnessId: "A", endWitnessId: "B", axis: "Y", positiveDirection: 1, valueMm: 10, printedText: "10", dimensionClass: "ORDINATE", sourceReceiptId: receipt },
    { id: "d7", startWitnessId: "C", endWitnessId: "D", axis: "Y", positiveDirection: 1, valueMm: 30, printedText: "30", dimensionClass: "LOCAL", sourceReceiptId: receipt }
  ]), { jobId: "cad_test", sourceSha256, receipts: trustedReceipts });

  assert.equal(result.status, "SOLVED");
  assert.deepEqual(result.nodes, [
    { nodeId: "A", xMm: 0, yMm: 0, xDerivedFrom: [], yDerivedFrom: [] },
    { nodeId: "B", xMm: 20, yMm: 10, xDerivedFrom: ["d1"], yDerivedFrom: ["d6"] },
    { nodeId: "C", xMm: 35, yMm: -30, xDerivedFrom: ["d1", "d2"], yDerivedFrom: ["d3"] },
    { nodeId: "D", xMm: 30, yMm: 0, xDerivedFrom: ["d1", "d2", "d4"], yDerivedFrom: ["d3", "d7"] }
  ]);
  assert.equal(result.derivations[1]?.expression, "C = B + 15");
});

test("inconsistent dimension cycles and disconnected datum components require review", () => {
  const result = solveDimensionGraph(graph([
    { id: "d1", startWitnessId: "A", endWitnessId: "B", axis: "X", positiveDirection: 1, valueMm: 20, printedText: "20", dimensionClass: "BASELINE", sourceReceiptId: receipt },
    { id: "d2", startWitnessId: "A", endWitnessId: "B", axis: "X", positiveDirection: 1, valueMm: 21, printedText: "21", dimensionClass: "OVERALL", sourceReceiptId: receipt },
    { id: "d3", startWitnessId: "C", endWitnessId: "D", axis: "X", positiveDirection: 1, valueMm: 5, printedText: "5", dimensionClass: "CHAIN", sourceReceiptId: receipt }
  ]), { jobId: "cad_test", sourceSha256, receipts: trustedReceipts });

  assert.equal(result.status, "REVIEW_REQUIRED");
  assert.ok(result.flags.includes("DIMENSION_GRAPH_INCONSISTENT:X:d2"));
  assert.ok(result.flags.includes("DIMENSION_X_UNRESOLVED:C"));
  assert.ok(result.flags.includes("DIMENSION_Y_UNRESOLVED:B"));
});

test("unbound visual receipts and source hashes cannot yield a solved graph", () => {
  const raw = graph([
    { id: "d1", startWitnessId: "A", endWitnessId: "B", axis: "X", positiveDirection: 1, valueMm: 10, printedText: "10", dimensionClass: "BASELINE", sourceReceiptId: receipt },
    { id: "d2", startWitnessId: "A", endWitnessId: "B", axis: "Y", positiveDirection: 1, valueMm: 10, printedText: "10", dimensionClass: "BASELINE", sourceReceiptId: receipt },
    { id: "d3", startWitnessId: "A", endWitnessId: "C", axis: "X", positiveDirection: 1, valueMm: 15, printedText: "15", dimensionClass: "BASELINE", sourceReceiptId: "forged" },
    { id: "d4", startWitnessId: "A", endWitnessId: "C", axis: "Y", positiveDirection: 1, valueMm: 15, printedText: "15", dimensionClass: "BASELINE", sourceReceiptId: "forged" },
    { id: "d5", startWitnessId: "A", endWitnessId: "D", axis: "X", positiveDirection: 1, valueMm: 25, printedText: "25", dimensionClass: "BASELINE", sourceReceiptId: receipt },
    { id: "d6", startWitnessId: "A", endWitnessId: "D", axis: "Y", positiveDirection: 1, valueMm: 25, printedText: "25", dimensionClass: "BASELINE", sourceReceiptId: receipt }
  ]);
  const result = solveDimensionGraph(raw, {
    jobId: "cad_test", sourceSha256: "b".repeat(64), receipts: trustedReceipts
  });
  assert.equal(result.status, "REVIEW_REQUIRED");
  assert.ok(result.flags.includes("DIMENSION_GRAPH_SOURCE_MISMATCH"));
  assert.ok(result.flags.includes("DIMENSION_SOURCE_RECEIPT_UNVERIFIED:d3"));
});
