#!/usr/bin/env bash
# Full E2E for TrainAiCad MCP V1.0 via MCP Inspector CLI (HTTP transport).
set -u
cd "$(dirname "$0")/.." || exit 1
INS="npx -y @modelcontextprotocol/inspector@2.8.0 --cli --server-url http://127.0.0.1:8787/mcp --transport http"
PASS=0; FAIL=0
ok()   { echo "PASS: $1"; PASS=$((PASS+1)); }
bad()  { echo "FAIL: $1"; FAIL=$((FAIL+1)); }

# unescape the JSON text payload so greps read like plain JSON
call() {
  local tool="$1"; shift
  local cmd="$INS --method tools/call --tool-name $tool"
  while [ $# -gt 0 ]; do cmd="$cmd --tool-arg '$1'"; shift; done
  eval "$cmd" 2>&1 | sed 's/\\"/"/g'
}

SHA_A=$(printf 'a%.0s' {1..64})
SHA_B=$(printf 'b%.0s' {1..64})
# expected production release read from the live entrypoint (never hard-coded)
EXPECT=$(grep -o 'Current production release is \*\*V[0-9.]*\*\*' ../../AI_ENTRYPOINT.md | grep -o 'V[0-9.]*')
[ -n "$EXPECT" ] || { echo "FAIL: cannot resolve release from AI_ENTRYPOINT.md"; exit 1; }
echo "expected release pin: $EXPECT"

LIST=$($INS --method tools/list 2>/dev/null)
for t in open_cad_job submit_cad_evidence route_cad_parts build_canonical_geometry export_dxf audit_dxf export_review_dxf audit_existing_dxf get_cad_job ingest_cad_file; do
  echo "$LIST" | grep -q "\"name\": \"$t\"" && ok "tool listed: $t" || bad "tool listed: $t"
done

# 1. V4.20 source classification
OUT=$(call open_cad_job "drawing={\"fileName\":\"sample.pdf\",\"sha256\":\"$SHA_A\"}" "mode=AUTO")
echo "$OUT" | grep -q '"mode": "PDF_ONLY"' && ok "AUTO PDF-only => PDF_ONLY" || bad "PDF_ONLY: $OUT"
JOB=$(echo "$OUT" | grep -o 'cad_[0-9a-f]\{16\}' | head -1)
[ -n "$JOB" ] && ok "jobId=$JOB" || bad "jobId missing"

OUT=$(call open_cad_job "drawing={\"fileName\":\"sample.pdf\",\"sha256\":\"$SHA_A\"}" \
  "dxf={\"fileName\":\"data.dxf\",\"sha256\":\"$SHA_B\"}" "mode=AUTO")
echo "$OUT" | grep -q '"mode": "PDF_DATA_RAW"' && ok "AUTO+generic DXF => PDF_DATA_RAW" || bad "PDF_DATA_RAW: $OUT"

OUT=$(call open_cad_job "drawing={\"fileName\":\"sample.pdf\",\"sha256\":\"$SHA_A\"}" \
  "referenceDxf={\"fileName\":\"approved.dxf\",\"sha256\":\"$SHA_B\"}" "mode=AUTO")
echo "$OUT" | grep -q '"mode": "TRAIN_REFERENCE"' && ok "AUTO+explicit reference => TRAIN_REFERENCE" || bad "TRAIN_REFERENCE: $OUT"

# 2. DIRECT audit without approved reference must FAIL
ERR=$(call open_cad_job "drawing={\"fileName\":\"ai.dxf\",\"sha256\":\"$SHA_A\"}" \
  "mode=DIRECT_EXISTING_DXF_AUDIT")
echo "$ERR" | grep -q 'approved reference DXF' && ok "direct audit w/o reference FAILs" || bad "direct audit: $ERR"

# 2b. DIRECT existing DXF physical audit: bulged polyline vs LINE+ARC, translation-only normalization
TMP_AUDIT=$(mktemp -d)
python - "$TMP_AUDIT/ai.dxf" "$TMP_AUDIT/ref.dxf" <<'PY'
import ezdxf,sys
ai,ref=sys.argv[1],sys.argv[2]
d=ezdxf.new("R2010"); d.header["$INSUNITS"]=4; m=d.modelspace()
m.add_lwpolyline([(0,0,0),(10,0,1)],format="xyb",close=True); d.saveas(ai)
r=ezdxf.new("R2010"); r.header["$INSUNITS"]=1; q=r.modelspace()
q.add_line((100,200),(110,200)); q.add_arc((105,200),5,0,180); r.saveas(ref)
PY
AI_AUDIT_B64=$(base64 -w0 "$TMP_AUDIT/ai.dxf")
REF_AUDIT_B64=$(base64 -w0 "$TMP_AUDIT/ref.dxf")
OUT=$(call ingest_cad_file "fileName=ai.dxf" "role=AI_DXF" "data=$AI_AUDIT_B64")
AI_AUDIT_SHA=$(echo "$OUT" | grep -o '"sha256": "[0-9a-f]\{64\}"' | head -1 | grep -o '[0-9a-f]\{64\}')
OUT=$(call ingest_cad_file "fileName=approved.dxf" "role=REFERENCE_DXF" "data=$REF_AUDIT_B64")
REF_AUDIT_SHA=$(echo "$OUT" | grep -o '"sha256": "[0-9a-f]\{64\}"' | head -1 | grep -o '[0-9a-f]\{64\}')
OUT=$(call open_cad_job "drawing={\"fileName\":\"ai.dxf\",\"sha256\":\"$AI_AUDIT_SHA\",\"sourceId\":\"$AI_AUDIT_SHA\"}" \
  "referenceDxf={\"fileName\":\"approved.dxf\",\"sha256\":\"$REF_AUDIT_SHA\"}" "mode=DIRECT_EXISTING_DXF_AUDIT")
AUDIT_JOB=$(echo "$OUT" | grep -o 'cad_[0-9a-f]\{16\}' | head -1)
DAC='{"aiMmPerUnit":1,"referenceMmPerUnit":1,"aiUnitProofRefs":["source/user:mm"],"referenceUnitProofRefs":["source/user:mm despite header"],"curveToleranceMm":0.001,"toleranceProofRefs":["physical curve contract"],"parts":[{"code":"D01","mappingProofRefs":["whole drawing D01"],"aiTransform":{},"referenceTransform":{}}]}'
OUT=$(call audit_existing_dxf "jobId=$AUDIT_JOB" "config=$DAC")
echo "$OUT" | grep -q '"state": "AUDIT_COMPLETE"' && ok "direct audit => AUDIT_COMPLETE" || bad "direct audit state: $OUT"
echo "$OUT" | grep -q '"status": "MATCH"' && ok "ARC+LINE equals exact bulged polyline physically" || bad "direct audit geometry: $OUT"
echo "$OUT" | grep -q '"referenceMmPerUnit": 1' && ok "direct audit uses explicit physical unit scale" || bad "direct audit unit: $OUT"
rm -rf "$TMP_AUDIT"

# 3. submit evidence
EV='{"schema":"CAD_EVIDENCE_V1","jobId":"'"$JOB"'","code":"056648","source":{"sourceId":"'"$SHA_A"'","page":1},"material":{"printed":"SS400","family":"SS","thickness":{"value":3,"unit":"mm","origin":"PRINTED"}},"views":[{"id":"A","type":"FLAT"}],"contour":{"topology":"PLATE","status":"PROVED","overallX":{"value":50,"unit":"mm","origin":"PRINTED"},"overallY":{"value":32,"unit":"mm","origin":"PRINTED"}},"features":[{"id":"S1","family":"SLOT","quantity":1,"width":{"value":10,"unit":"mm","origin":"PRINTED"}}],"bends":[],"markings":[],"handwriting":[],"uncertainties":[]}'
OUT=$(call submit_cad_evidence "jobId=$JOB" "evidence=[$EV]")
echo "$OUT" | grep -q '"state": "EVIDENCE_READY"' && ok "submit_cad_evidence => EVIDENCE_READY" || bad "submit: $OUT"

# 4. route
OUT=$(call route_cad_parts "jobId=$JOB")
echo "$OUT" | grep -q '"mode": "FLAT_NO_BEND"' && ok "route => FLAT_NO_BEND" || bad "route: $OUT"
echo "$OUT" | grep -q 'SLOTS.md' && ok "route loads SLOTS module" || bad "route modules: $OUT"

# 4b. V0.2 canonical geometry through MCP
GS='{"schema":"GEOMETRY_SOURCE_V1","jobId":"'"$JOB"'","code":"056648","sourceSha256":"'"$SHA_A"'","origin":"PDF_SOURCE","buildKind":"FLAT_SINGLE_FACE","faces":[{"faceId":"F1","sourceView":"A","contour":[{"x":0,"y":0},{"x":50,"y":0},{"x":50,"y":32},{"x":0,"y":32}]}],"faceOrder":["F1"],"bends":[],"features":[{"featureId":"S1","family":"SLOT","hostFace":"F1","geometries":[{"kind":"SLOT","center":{"x":25,"y":22},"overallLength":20,"width":10,"angleDeg":0}]}],"proofs":{"topologyLocked":{"evidenceRefs":["page:1"]},"dimensionWitnessLocked":{"evidenceRefs":["page:1"]},"featureOwnershipLocked":{"evidenceRefs":["page:1"]},"constraintsClosed":{"evidenceRefs":["page:1"]},"materialRules":{"evidenceRefs":["page:1"]},"slotSemantics":{"evidenceRefs":["page:1"]}}}'
OUT=$(call build_canonical_geometry "jobId=$JOB" "geometrySources=[$GS]")
echo "$OUT" | grep -q '"state": "GEOMETRY_READY"' && ok "V1 build => GEOMETRY_READY" || bad "geometry state: $OUT"
echo "$OUT" | grep -q '"schema": "CANONICAL_GEOMETRY_V1"' && ok "canonical schema returned" || bad "geometry schema: $OUT"
echo "$OUT" | grep -q '"instance": 1' && ok "feature instance preserved" || bad "geometry feature: $OUT"

# 4c. production path: write DXF, then independent read-back audit
OUT=$(call export_dxf "jobId=$JOB")
echo "$OUT" | grep -q '"state": "DXF_WRITTEN"' && ok "export_dxf => DXF_WRITTEN" || bad "export: $OUT"
echo "$OUT" | grep -q '"filename": "cad_.*_ALL.dxf"' && ok "production composite DXF created" || bad "filename: $OUT"
echo "$OUT" | grep -q '"readback"' && bad "export granted readback prematurely" || ok "export alone does not grant readback"

OUT=$(call audit_dxf "jobId=$JOB")
echo "$OUT" | grep -q '"state": "PRODUCTION_PASS"' && ok "audit_dxf => PRODUCTION_PASS" || bad "audit: $OUT"
echo "$OUT" | grep -q '"canonicalMatch": true' && ok "saved DXF matches canonical geometry" || bad "canonical readback: $OUT"
echo "$OUT" | grep -q '"codeOrderMatch": true' && ok "saved DXF code mapping/order matches" || bad "code order: $OUT"
echo "$OUT" | grep -q '"HOLE_SLOT": {' && ok "independent family QA present" || bad "family qa: $OUT"

# 5. get
OUT=$(call get_cad_job "jobId=$JOB")
echo "$OUT" | grep -q "\"release\": \"$EXPECT\"" && ok "release pin $EXPECT" || bad "release pin ($EXPECT): $OUT"
echo "$OUT" | grep -q '"state": "PRODUCTION_PASS"' && ok "get_cad_job persists audited PRODUCTION_PASS" || bad "production state missing: $OUT"

# 5b. unresolved source => explicit REVIEW_ONLY / NO CUT path
OUT=$(call open_cad_job "drawing={\"fileName\":\"review.pdf\",\"sha256\":\"$SHA_A\",\"sourceId\":\"$SHA_A\"}" "mode=AUTO")
RV_JOB=$(echo "$OUT" | grep -o 'cad_[0-9a-f]\{16\}' | head -1)
RV_EV='{"schema":"CAD_EVIDENCE_V1","jobId":"'"$RV_JOB"'","code":"RV01","source":{"sourceId":"'"$SHA_A"'","page":1},"material":{"printed":"SS400","family":"SS","thickness":{"value":2,"unit":"mm","origin":"PRINTED"}},"views":[{"id":"FRONT","type":"FRONT"}],"contour":{"topology":"UNKNOWN","status":"UNCERTAIN"},"features":[],"bends":[],"markings":[],"handwriting":[],"uncertainties":[{"code":"TOPOLOGY","evidence":"flat topology unresolved","blocking":true}]}'
call submit_cad_evidence "jobId=$RV_JOB" "evidence=[$RV_EV]" >/dev/null
OUT=$(call route_cad_parts "jobId=$RV_JOB")
echo "$OUT" | grep -q '"state": "REVIEW_REQUIRED"' && ok "uncertain source => REVIEW_REQUIRED" || bad "review route: $OUT"
RV='{"schema":"REVIEW_OUTPUT_V1","parts":[{"code":"RV01","status":"VIEWS_ONLY","preview_reason":"separate_source_views","flags":["TOPOLOGY unresolved"],"checks":{"contour_topology":"FLAGGED","datum":"PASS","feature_count":"PASS","unfold":"FLAGGED","containment":"FLAGGED","bend_domain":"N/A","material_rules":"PASS","slot_semantics":"N/A"},"entities":[{"type":"LINE","role":"source_view","view_id":"FRONT","start":[0,0],"end":[40,0],"evidenceRefs":["page:1 FRONT"]},{"type":"LINE","role":"source_view","view_id":"FRONT","start":[40,0],"end":[40,20],"evidenceRefs":["page:1 FRONT"]}]}]}'
OUT=$(call export_review_dxf "jobId=$RV_JOB" "review=$RV")
echo "$OUT" | grep -q '"state": "REVIEW_ONLY"' && ok "review export => REVIEW_ONLY" || bad "review export state: $OUT"
echo "$OUT" | grep -q '_ALL_REVIEW_ONLY.dxf' && ok "review filename is NO-CUT composite" || bad "review filename: $OUT"
echo "$OUT" | grep -q '"reviewOnly": true' && ok "review artifact cannot masquerade as production" || bad "review marker: $OUT"
ERR=$(call audit_dxf "jobId=$RV_JOB")
echo "$ERR" | grep -q 'DXF_AUDIT_NOT_ALLOWED_IN_STATE' && ok "review output cannot enter production audit" || bad "review production guard: $ERR"

# 6. ingest drawing PDF (base64) bound to job
PDF_B64=$(printf '%%PDF-1.7\n1 0 obj\n<<>>\nendobj\ntrailer\n%%%%EOF\n' | base64 -w0)
OUT=$(call ingest_cad_file "fileName=../../evil sample.pdf" "role=DRAWING" "data=$PDF_B64" "jobId=$JOB")
echo "$OUT" | grep -q '"kind": "PDF"' && ok "ingest PDF (base64) => kind PDF" || bad "ingest pdf: $OUT"
echo "$OUT" | grep -q '"fileName": "evil sample.pdf"' && ok "filename sanitized" || bad "filename: $OUT"
echo "$OUT" | grep -q "sources/DRAWING/" && ok "drawing stored under DRAWING/" || bad "path: $OUT"
DRAW_SHA=$(echo "$OUT" | grep -o '"sha256": "[0-9a-f]\{64\}"' | head -1 | grep -o '[0-9a-f]\{64\}')

# 7. PDF + explicit reference (matrix C/F): fresh PDF_ONLY job, then bind REFERENCE_DXF
DXF_B64=$(printf '0\nSECTION\n2\nENTITIES\n0\nENDSEC\n0\nEOF\n' | base64 -w0)
OUT=$(call open_cad_job "drawing={\"fileName\":\"sample.pdf\",\"sha256\":\"$SHA_A\"}" "mode=AUTO")
REF_JOB=$(echo "$OUT" | grep -o 'cad_[0-9a-f]\{16\}' | head -1)
echo "$OUT" | grep -q '"mode": "PDF_ONLY"' && ok "fresh job => PDF_ONLY" || bad "fresh: $OUT"
OUT=$(call ingest_cad_file "fileName=ref.dxf" "role=REFERENCE_DXF" "data=$DXF_B64" "jobId=$REF_JOB")
echo "$OUT" | grep -q '"kind": "DXF"' && ok "ingest DXF => kind DXF" || bad "ingest dxf: $OUT"
echo "$OUT" | grep -q "sources/REFERENCE_DXF/" && ok "reference stored under REFERENCE_DXF/" || bad "ref path: $OUT"
echo "$OUT" | grep -q '"jobMode": "TRAIN_REFERENCE"' && ok "F: PDF_ONLY + REFERENCE_DXF => TRAIN_REFERENCE" || bad "reclassify ref: $OUT"
OUT=$(call get_cad_job "jobId=$REF_JOB")
echo "$OUT" | grep -q '"mode": "TRAIN_REFERENCE"' && ok "F: job mode persisted as TRAIN_REFERENCE" || bad "ref mode: $OUT"
echo "$OUT" | grep -q '"dxfUse": "AUDIT_ONLY"' && ok "F: reference is audit-only" || bad "ref policy: $OUT"
REF_SHA=$(echo "$OUT" | grep -o '"sha256": "[0-9a-f]\{64\}"' | tail -1 | grep -o '[0-9a-f]\{64\}')
[ -n "$DRAW_SHA" ] && [ -n "$REF_SHA" ] && [ "$DRAW_SHA" != "$REF_SHA" ] \
  && ok "drawing and reference are distinct sources" || bad "sha draw=$DRAW_SHA ref=$REF_SHA"

# 7b. mode is locked after evidence: no DXF may attach to the routed PDF_ONLY job
ERR=$(call ingest_cad_file "fileName=late.dxf" "role=REFERENCE_DXF" "data=$DXF_B64" "jobId=$JOB")
echo "$ERR" | grep -q 'SOURCE_MODE_LOCKED' && ok "locked mode rejects late DXF binding" || bad "lock: $ERR"
OUT=$(call get_cad_job "jobId=$JOB")
echo "$OUT" | grep -q '"mode": "PDF_ONLY"' && ok "locked job still PDF_ONLY" || bad "locked mode: $OUT"

# 8. rejected inputs
ERR=$(call ingest_cad_file "fileName=payload.exe" "role=DRAWING" "data=$PDF_B64")
echo "$ERR" | grep -q 'UNSUPPORTED_FILE_TYPE' && ok "extension whitelist rejects .exe" || bad "exe: $ERR"
ERR=$(call ingest_cad_file "fileName=a.pdf" "role=DRAWING")
echo "$ERR" | grep -q 'PROVIDE_EXACTLY_ONE_OF_DATA_OR_URI' && ok "data/uri exclusivity enforced" || bad "exclusivity: $ERR"
ERR=$(call ingest_cad_file "fileName=a.pdf" "uri=file:///etc/passwd" "role=DRAWING")
echo "$ERR" | grep -q 'UNSUPPORTED_URI_SCHEME' && ok "file:// URI rejected" || bad "scheme: $ERR"
ERR=$(call ingest_cad_file "fileName=a.pdf" "uri=http://127.0.0.1:9/a.pdf" "role=DRAWING")
echo "$ERR" | grep -q 'PRIVATE_ADDRESS_BLOCKED' && ok "private address blocked" || bad "ssrf: $ERR"

# 9. DRAWING binding is immutable per job: new valid PDF content must be refused
PDF2_B64=$(printf '%%PDF-1.7\nother content\ntrailer\n%%%%EOF\n' | base64 -w0)
ERR=$(call ingest_cad_file "fileName=other.pdf" "role=DRAWING" "data=$PDF2_B64" "jobId=$JOB")
echo "$ERR" | grep -q 'SOURCE_ALREADY_BOUND' && ok "DRAWING binding immutable" || bad "rebind: $ERR"

# 10. unknown job cannot be bound
ERR=$(call ingest_cad_file "fileName=a.pdf" "role=DRAWING" "data=$PDF_B64" "jobId=cad_0000000000000000")
echo "$ERR" | grep -q 'JOB_NOT_FOUND' && ok "binding unknown job fails closed" || bad "unknown job: $ERR"

# 11. matrix E: PDF_ONLY + DATA_DXF => PDF_DATA_RAW (reclassify while SOURCE_READY)
OUT=$(call open_cad_job "drawing={\"fileName\":\"sample.pdf\",\"sha256\":\"$SHA_A\"}" "mode=AUTO")
E_JOB=$(echo "$OUT" | grep -o 'cad_[0-9a-f]\{16\}' | head -1)
echo "$OUT" | grep -q '"mode": "PDF_ONLY"' && ok "E setup: fresh job PDF_ONLY" || bad "E setup: $OUT"
OUT=$(call ingest_cad_file "fileName=data.dxf" "role=DATA_DXF" "data=$DXF_B64" "jobId=$E_JOB")
echo "$OUT" | grep -q '"jobMode": "PDF_DATA_RAW"' && ok "E: PDF_ONLY + DATA_DXF => PDF_DATA_RAW" || bad "E reclassify: $OUT"
OUT=$(call get_cad_job "jobId=$E_JOB")
echo "$OUT" | grep -q '"mode": "PDF_DATA_RAW"' && ok "E: job mode persisted as PDF_DATA_RAW" || bad "E mode: $OUT"
echo "$OUT" | grep -q '"geometryAuthority": "DATA_DXF"' && ok "E: DATA_DXF is geometry authority" || bad "E authority: $OUT"
echo "$OUT" | grep -q '"semanticAuthority": "PDF_OR_IMAGE_CONTROL"' && ok "E: PDF stays semantic/control authority" || bad "E semantic: $OUT"

# 12. AI_DXF is fail-closed outside the direct audit mode
ERR=$(call ingest_cad_file "fileName=ai.dxf" "role=AI_DXF" "data=$DXF_B64" "jobId=$JOB")
echo "$ERR" | grep -q 'AI_DXF_NOT_ALLOWED_IN_PDF_ONLY' && ok "AI_DXF rejected in PDF_ONLY" || bad "AI_DXF: $ERR"

# 13. persisted job files hold the same classification (restart-safe state)
grep -q '"mode": "PDF_DATA_RAW"' "data/jobs/$E_JOB.json" && ok "E: mode persisted on disk" || bad "E file: $E_JOB"
grep -q '"mode": "TRAIN_REFERENCE"' "data/jobs/$REF_JOB.json" && ok "F: mode persisted on disk" || bad "F file: $REF_JOB"
grep -q '"mode": "PDF_ONLY"' "data/jobs/$JOB.json" && ok "locked job persisted PDF_ONLY" || bad "lock file: $JOB"
grep -q '"dxf"' "data/jobs/$JOB.json" && bad "PDF_ONLY job carries a DXF descriptor" || ok "PDF_ONLY job has no DXF"

echo "---- inspector e2e: $PASS passed, $FAIL failed ----"
echo "JOB_ID=$JOB"
echo "REF_JOB_ID=$REF_JOB"
echo "E_JOB_ID=$E_JOB"
[ "$FAIL" -eq 0 ]
