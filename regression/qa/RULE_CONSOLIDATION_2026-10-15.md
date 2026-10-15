# Approved rule-owner consolidation — implementation evidence

User approved the proposal on 2026-10-15. Baseline main:
`65bf258bed380a4389aa91fe6f91f28cf2242ff4`. Production stays V4.34;
new input V4.34 and compatible V4.31 reader remain supported.
This record is audit evidence, not a production load list or a new versioned rule.

## Fact, cause and lesson

**FACT:** DATA preservation/census/manufacturing prose overlapped across four
references; acute construction had two co-routed files; bend relief lived in
the bend mode as well as feature references. Some older schema, JSON delivery,
DXF gap/curve and R3 instructions competed with their approved overrides.

**ROOT_CAUSE:** cumulative release supplements and copied rule descriptions
made ownership unclear. Exact paragraph deduplication did not find semantic
copies. The bootstrap release detector also matched escaped backslashes
instead of a release number.

**LESSON:** one scoped owner per decision, explicit route dependencies and
actual negative/regression checks. Moving inline bend relief requires loading
its new owner before a preliminary NO can discard it. No formula/table or
production Python AST is changed.

**Audit correction:** AGENTS.md already was release-independent. The V4.34
supplement described in finding F04 belongs to the start of AI_ENTRYPOINT.md,
not the end of AGENTS.md (a concatenated file read obscured the boundary).
AGENTS needs no edit; the release regex defect is real and has a negative
control. Historical CURRENT remains pinned V4.24, not current production.

## Clause ownership migration

Source headings below refer to baseline files, which remain inspectable at the
pinned commit. Each row preserves a decision or restriction, not merely a shared
uppercase identifier. Deleted documents' unique clauses are retained at the
listed owner. Regression fixtures remain separate from construction authority.

| Baseline source/section | Current owner/section | Preserved scope and verification |
|---|---|---|
| PDF_DATA_RAW_GEOMETRY_PRESERVATION: Scope/Geometry-preservation | DATA_RAW_TO_MANUFACTURING_CONTRACT: Authority/Complete harvest | Customer DATA geometry; PDF semantics; no PDF redraw, complete harvest before changing geometry; test_v421 |
| Preservation: Scale | DATA contract: Complete harvest | Per-view proved physical scale, not a job-wide inferred scale; no forced scale to close numbers |
| Preservation: RAW freeze; physical census §1–2 | DATA contract: Complete harvest | Immutable raw snapshot; classify every primitive; thickness-only/helpers excluded only after semantic accounting; check_v423 |
| Preservation: assembly steps 4–6 | DATA contract: Complete harvest | Preserve local face curves, proved rigid/reflection/scale transforms; Nobi changes inter-face placement, not a redraw |
| Classification: numeric customer exception; raw contract §3 | CAD_CUSTOMER_POLICY + DATA contract: Same physical parameter | Numeric JOB STATISTICS ID, no-code general; DATA_NO_DIM_COMPARE numeric scope only; KH433 1.0 and general 0.1 strict boundary; tests customer policy/v420 |
| Raw contract §3; physical census SAME_PARAMETER_GATE | DATA contract: Same physical parameter | Same code/view/member/datum/unit parameter; < threshold is not snap permission; ≥ threshold local FLAG without forced correction |
| Raw contract §4; physical census manufacturing ledger | DATA contract: Rule-scoped manufacturing canonicalization | Active rule and local changed_scope for every intentional physical change; source/host/gate/value/rule/canonical/serialized fields |
| Physical census V4.24; preservation canonicalization | DATA contract: DATA_TAP_NOMINAL_VALIDATION | Every proved M*, nominal-reference vs pilot identity; nominal non-cut, one effective pilot, quantity/center/face unchanged; check_v424/v425 |
| Physical census DATA_AUTO_R; preservation automatic R | DATA contract: DATA_AUTO_R_CANONICALIZATION | Sharp DATA does not suppress material R; local tangent replacement/provenance; explicit R/C and current R3 conflict scope preserved |
| Raw contract §5–6; preservation QA; physical census invariance | DATA contract: Untouched invariance | Unchanged physical curves survive canonical and saved-DXF inverse read-back; no 0.1 redraw allowance; exact representation equivalence; UNTOUCHED_DATA_INVARIANCE_FAIL |
| Physical census §3–4 | DATA contract: Independent completeness | Both source→canonical and canonical→source; no missing family, no extra curve, no self-selected subset equality |
| Physical census §5 | DATA contract: Independent completeness + FACE_GRAPH | Per-bend witness fields, THICKNESS_SINGLE_USE, ±t diagnostic only; bend domain/fold-back retained |
| Physical census §6 | DATA contract: Independent completeness | Reference/direct audit only: normalize coincident/reversed duplicates, report REFERENCE_ANOMALY, never mutate sample |
| Raw contract §7 | regression/qa/521001-20_V4_25_APPROVED.md | Existing approved 855→854.75, 600→599.75, Ø4.134→Ø4.2, untouched 60.000709679 assertions remain; never new-job inputs |
| Raw contract §8; physical census §7 | DATA contract: PASS boundary | All raw/baseline/gate/ledger/invariance/bidirectional/reprojection/saved-readback gates remain mandatory |
| Classification job-family 646; preservation Scope | SOURCE_DATA_CLASSIFICATION: 646 DATA-required | DATA_REQUIRED_MISSING; do not silently downgrade to PDF_ONLY; independent of numeric customer 646 |
| Classification reference ordering | SOURCE_DATA_CLASSIFICATION + REFERENCE_EXPOSURE_FIREWALL | Source-only freeze before sample decoding/exposure; direct audit exception does not rewrite source-only history |
| ACUTE_BEND_LT85_METHOD §0–3 | ACUTE_BEND_LT85_FROM_SOURCE: Trigger and precedence + construction | Included ≤85° inclusive, proved radius/free edges/faces, real-radius OD envelope, exact printed inputs; generic tangent method cannot replace acute construction |
| Acute METHOD §4–6; FROM_SOURCE §7–9 | FROM_SOURCE regression assertions + existing acute regression/assets | Numeric outputs are assertions only; no reverse-fit radius/normal/sign, no proof-DXF input; actual fixture filenames, source hashes retained |
| BEND_UNFOLD attachment block and FACE_GRAPH gate list | BEND_UNFOLD pointer → FACE_GRAPH + attachment owner | Exact physical shared edges, not nearest paper edge; G1–G7/G8 unchanged; tests_v432/v433 and check_v432 |
| BEND_UNFOLD §4.10 crossing-bend/opposite-fold | features/SLIT_RELIEF: Generic construction | Perpendicular crossing trigger; retreat longer by t, depth t+0.2, diagonal to intersection; opposite-fold R=t keeps both outside extents; not auto Laser R |
| BEND_UNFOLD §4.10.1 | SLIT_RELIEF: BOXMET routing → BOXMET_SLIT_RELIEF | Four flanges, L/W retreat, signed rays, LINE+ARC+LINE, real intersection trimming; no application to ordinary L/U/Z/free edges |
| Relief classification/dependencies | ROUTER BEND/MULTI_FACE/UNKNOWN and feature routes | Load moved inline relief before final NO; custom slit remains independently available for flat parts; test_rule_owner_consolidation |
| BEND_EDGE_RELIEF_90 §7 | Same owner, linked from SLIT_RELIEF | Source/revision→specific→signed S→generic priority, no double relief; S>0 no slit, S≤0 t+0.2 from actual edge; check_v430 |
| CAD_OUTPUT approved top override + older §8.4 | CAD_OUTPUT: current geometry + executed verification | Exploded pieces, template/mm, approved composite POINT/review content, standalone CUT only, no DIM, 150 mm clusters, AI_META non-cut, exact piece-owner read-back |
| CAD_OUTPUT + V434 schema + RULE_BRAIN packaging | CAD_OUTPUT current packaging; others point/agree | One combined default, no JSON delivery, individual PASS only explicit, optional debug manifest only explicit, mixed REVIEW filename |
| MATERIAL_RULES approved R3 override + older table algorithm | MATERIAL_RULES: SS t>=19 decision table | Outer perimeter incl concave, no inner hole/slot; customer sharp/pin conflict FLAG, explicit R/C semantics retained |
| CHAMFER_RADIUS copied material lists | MATERIAL_RULES owner; CHAMFER geometry/count remains | SUS430 process split, Cu/Brass L09/L10 and table values unchanged; no duplicated numeric/process table |
| SLIM_MAPPING/GATE_REVIEW completed decisions | docs/RULE_HISTORY: Completed consolidation decisions | Accepted decisions, baseline provenance and earlier measured savings retained; stale approval questions removed |
| mcp-research workflow with missing service | Removed workflow; test_workflow_separation | Research remains outside CAD; no dispatch into absent working-directory; production CI adds templates paths |

## Boundaries and identifiers

- `DATA_PHYSICAL_CENSUS_AND_BIDIRECTIONAL_QA` was also indexed as a gate because
  its **filename** ended in QA. The file is retired; its actual independent
  gates remain in the DATA owner. It is not an executable predicate to drop.
- `UNTOUCHED_DATA_INVARIANCE_FAIL` retains its diagnostic spelling.
- GATE_INDEX is regenerated; no approved gate classification is added or removed.
- No budget cap is raised. The version/date heading allowlist is tightened by
  removing deleted/unused headings, not expanded or redirected to another owner.
- General/customer Nobi, coarse/fine thread, KEGAKI/weld-site completeness,
  topology candidates, review/reference policies and all numerical tables stay
  distinct. The 23 archived snapshots and their hashes are unchanged.
- Full source PDF/DATA replay is not claimed: this maintenance request supplies
  no new drawing set. Synthetic export, physical fixture and ledger tests do not
  prove an AI's source witness or manufacturing interpretation is correct.

## Validation

Results and measured before/after bytes are recorded below after executing the
same baseline and candidate scenarios. CI must run on the actual pushed commit.


- Full suite: **286 passed** (275 baseline tests preserved, 11 added cases).
- All **18** original `regression/tools/check_*.py` scripts pass.
- Coverage **51/51** active Markdown modules, previously 54/54. No unrouted module.
- Exact normalized cross-module paragraph duplicate scan: **0** (not a semantic proof).
- **2,064** routing cases match after explicit old→new owner mapping and the
  moved inline-relief dependency. This covers all four source/part modes,
  each feature YES/UNKNOWN, general/KH433/KH646 customer policies, stage-specific
  path sets and all post-route checks. Missing feature census remains rejected.
  KH851 source/weld completeness stays covered by its independent positive and
  negative executable tests; no empty-site bypass is added to the route matrix.
- **10 export scenarios / 16 actual saved DXFs** match baseline physical/attribute
  signatures and TRAINAICAD XDATA. Scenarios include V4.31 flat/bend/relief/slot,
  mixed review, V4.34, proved/unproved HL, mirror/dx, KH851 RED marks, POINTs and
  compatibility source-view fallback. These are synthetic/approved-fixture cases.
- All **23** archive snapshot hashes match and the pinned commit remains reachable.
- AST of every existing `tools/*.py` matches baseline (the gate-index edit is a comment).
  Material/customer/Nobi/thread numeric tables and the CAD template are unchanged.
- Rulepack: **400,527 → 375,247 bytes** at this checkpoint; generated index/bundle
  live outside the working tree. Budget caps unchanged; heading allowlist 97→72.

| Scenario | L0+L1 before | L0+L1 after | All stages before | All stages after | Full-job byte reduction |
|---|---:|---:|---:|---:|---:|
| flat | 79,973 | 73,837 | 152,905 | 147,108 | 3.79% |
| flat_tap | 79,973 | 73,837 | 178,617 | 172,828 | 3.24% |
| bend_nobi | 79,973 | 73,837 | 235,859 | 233,037 | 1.20% |
| data_holes | 108,289 | 88,363 | 202,673 | 183,094 | 9.66% |
| unknown_complex | 122,757 | 102,831 | 333,080 | 309,032 | 7.22% |

Bytes are UTF-8 file bytes, not model tokens. No startup percentage is presented
as full-job savings. Flat jobs do not acquire the DATA or bend-specific owner.

### Reproduce the before/after maintenance check

Use a full-history checkout (snapshots require the pinned commit). Add a detached
baseline worktree at the commit above, then invoke
`regression/tools/compare_rule_consolidation.py BASELINE_ROOT /tmp/before` and
`regression/tools/compare_rule_consolidation.py CANDIDATE_ROOT /tmp/after` in
separate processes with fresh output directories. Compare parsed `summary.json`
and `routes.json` for exact equality. The former contains physical signatures,
member/piece XDATA, statuses, filenames and archive hashes; the latter normalizes
only the explicitly documented owner moves. `benchmark.json` records measured
bytes per checkout. DXF timestamps/handles are deliberately excluded; the
exporter independently performs saved-file read-back and physical/provenance QA.

After this record was written, GitHub CI still must validate the pushed commit.
No new source-PDF production certification is claimed.
