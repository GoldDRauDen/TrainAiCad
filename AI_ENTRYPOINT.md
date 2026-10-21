# AI ENTRYPOINT — TrainAiCad repo-direct production

Current production release is **V4.34**.

Production E2E for **new** jobs uses `TrainAiCad-CANONICAL-V4.34` plus `tools/CANONICAL_INPUT_SCHEMA_V434.md`; preexisting V4.31 fixtures remain supported. Load `references/MATERIAL_ALIASES.yaml` for material grades (SECC=ボンデ → SS), retain per-process exceptions, record PDF-grounded typed witness graphs for holes/slots, and explicit slot anchor source endpoints before PASS. All HL needs a proven part-relative grain vector; otherwise REVIEW regardless of Excel 横目. Individual CUT DXF orientation (X long unless HL→X) is downstream exporter-only; composite stays source-readable. Do not learn missing witnesses from sample DXF.

**KH851 weld-location KEGAKI completeness:** after reading numeric customer
code and before declaring KEGAKI=NO, follow
references/WELD_SITE_KEGAKI_CLOSURE.md. Independently enumerate every
assembly/weld site, then link each required marking to the appropriate
source/canonical KEGAKI member, or retain a scoped FLAG. Run
tools/weld_kegaki_guard.py through Router and canonical validation
before export. Do not claim PASS from a self-consistent incomplete
source-member census, DXF read-back or a copied reference mark.


This file is the production routing authority. Normal CAD jobs use **repo-direct modular routing**. Do not load the complete portable skill by default.

**Current packaging contract (supersedes inherited V4.9 one-composite-only
wording; retains V4.31 canonical input and all engineering/QA gates):** after
`tools/export_canonical_dxf.py` validates source/canonical completeness and
reopens the composite with verified `TRAINAICAD ENTITY_ID`, the same canonical
job writes no JSON output and, by default, only the combined DXF. Individual `parts_dxf/<PASS_CODE>.dxf` (PASS codes only; file name = delivery-slip work number, e.g. `26-056522`; slip `サイズ X/Y` is reference only) are produced **only on explicit user request** (`--individual-dxf`), and exactly one
`<JOB>_ALL.dxf` or `<JOB>_ALL_REVIEW_ONLY.dxf` at the output root.
Individual PASS DXFs are CUT-only LINE/ARC/CIRCLE and exclude bend/marking,
POINT, notes and every unproved entity; their derived provenance and physical
geometry are validated by actual saved-DXF read-back. One code's REVIEW
does not suppress other proved codes' PASS cut files, while it always makes
the combined DXF REVIEW_ONLY. Existing `tools/export_dxf.py` compatibility
modes do not override this canonical E2E contract.

## Invocation contract

When the user supplies CAD source and says `E2E`, `read TrainAiCad and do E2E`, or equivalent, treat that as an instruction to execute the complete current repo-direct production flow below to its executable limit. Do not require the user to restate census, routing, canonical, export, read-back or QA steps already defined by this repository.

`AI_BOOTSTRAP.md` is the release-independent discovery/bootstrap layer; this file remains the production engineering authority.

## 1. Normal production flow

```text
SOURCE
  -> RUNTIME AUTHORITY GUARD
  -> always-on CORE
  -> SOURCE CLASSIFICATION
  -> DXF PHYSICAL-CURVE DECODE for customer DATA when source-authoritative
  -> defer calibration/sample REFERENCE exposure until SOURCE_ONLY_SNAPSHOT freeze
  -> SOURCE MANUFACTURING NOTE CENSUS
  -> SOURCE FEATURE-GROUP / REFERENCE-PARAMETER CLOSURE
  -> PART IDENTITY GRAPH when multi-code / constituent / assembly evidence exists
  -> ASSEMBLY DATUM candidate census for indirectly dimensioned features, when applicable
  -> FEATURE CENSUS
  -> ROUTER
  -> selected mode / feature / reference modules
  -> BEND ATTACHMENT EDGE LOCK when applicable
  -> FORMED-PROFILE OD MEASUREMENT when applicable
  -> BEND-EDGE / 90-DEG BEND-END RELIEF GATE when applicable
  -> CROSS-FEATURE VALIDATION
  -> SOURCE GROUP + MEMBER LEDGER
  -> DIMENSION/WITNESS GRAPH
  -> FIRST SOURCE-ONLY SOLVE
  -> HOLISTIC ENGINEERING CHALLENGE
  -> local FLAG or COMPLETE VIEWS_ONLY fallback when still unresolved
  -> FINAL ENGINEERING SANITY REVIEW
  -> CANONICAL MEMBER MODEL
  -> PROVED SOURCE MEMBERS == PROVED CANONICAL MEMBERS
  -> CANONICAL ENTITIES
  -> tools/export_canonical_dxf.py
  -> SAVED DXF ENTITY IDs == CANONICAL ENTITY IDs
  -> saved-DXF read-back / applicable source reprojection
  -> SOURCE_ONLY_SNAPSHOT freeze before any later sample/reference calibration
```

Mandatory router files:
- `skills/lispcad/router/FEATURE_CENSUS.md`
- `skills/lispcad/router/ROUTER.yaml`

`skills/lispcad/router/RULE_COVERAGE.yaml` is used by repository QA and bundle audits, not ordinary job retrieval.

Always-on core/source-parsing references are declared in `ROUTER.yaml`. Do not invent a different core set from memory.

### Per-code workflow rules (moved from SKILL.md §2)

- Process codes independently where possible; store proved work by code so a failed part does not force geometry reconstruction of already-verified parts.
- Actually read the selected rule files; never treat a selected path as proof that its contents were loaded.
- Reroute any code whose source feature classification changes after zoom/DATA audit.
- If still unresolved after source exhaustion, retain proved geometry/source views with REVIEW semantics; do not invent missing dimensions or terminate unrelated codes.
- No PASS from bbox, entity count or visually plausible contour alone.
- Geometry JSON, not a manually repaired DXF, is the canonical model. The exporter reads canonical entities and must never infer geometry anew; do not bypass it by ad hoc `ezdxf` writing.
- Reopen the actual emitted DXF for saved-file QA. Only an independently verified part can be called PASS.
- A local flag cannot silently become an approved CUT.

## 2. V4.33 holistic engineering challenge / reference-exposure hard gate

Load `references/HOLISTIC_ENGINEERING_CHALLENGE.md` at L3 after the first source-only solve and before canonicalization. Load `PART_IDENTITY_GRAPH` only when multi-code/assembly is not proven absent; load `REFERENCE_EXPOSURE_FIREWALL` only when a sample/reference is present or unknown.

- After the first source-only solve and before canonicalization, run `HOLISTIC_ENGINEERING_CHALLENGE`; on an anomaly, re-open the source and re-solve. `VIEWS_ONLY` is only a complete executable fallback after source exhaustion, never a text-only stop.
- Before final canonical serialization, run `FINAL_ENGINEERING_SANITY_REVIEW`.
- For calibration/reference work, freeze `SOURCE_ONLY_SNAPSHOT` before reference exposure; later reclassification follows `REFERENCE_EXPOSURE_FIREWALL.md` (`REFERENCE_ASSISTED_UNDERSTANDING`, `CUSTOMER_CONFIRMATION_PENDING`).

## 2A. V4.32 bend attachment-edge / formed-profile OD hard gate

For every `BEND`, `MULTI_FACE`, or unresolved bend candidate the Router loads `references/BEND_ATTACHMENT_EDGE_OWNERSHIP.md` and, when outside face length must come from formed/profile geometry, `references/FORMED_PROFILE_OD_MEASUREMENT.md`, together with `BEND_UNFOLD.md`, `FACE_GRAPH_UNFOLD_PROTOCOL.md`, `FACE_CREATION_BEND_EVIDENCE.md` and the relief/Nobi rules (`ROUTER.yaml` `mode_routes`).

Before unfold, `BEND_ATTACHMENT_EDGE_LOCKED` must prove the exact physical material edge on both adjacent faces. `NEAREST_VIEW_EDGE`, paper proximity and visual symmetry are not evidence. A formed/profile view is a `MEASUREMENT_CONSTRUCTION_VIEW`, not CUT geometry. `THICKNESS_SINGLE_USE` remains mandatory. Regression: `regression/qa/521006-18_V4_32_APPROVED.md`.

## 2B. V4.31 E2E canonical completeness hard gate

Load `references/CANONICAL_MEMBER_COMPLETENESS.md` before final Feature Census and use `tools/CANONICAL_INPUT_SCHEMA_V434.md` for new output state (V4.31 reader compatibility remains supported).

**NO_DIRECT_DXF_FROM_INTERPRETATION:** never write a hand-picked subset from source interpretation straight into `ezdxf.modelspace()`; persist source groups/members and canonical members first, then serialize through `tools/export_canonical_dxf.py`. `tools/export_dxf.py` is a lower-level packaging component, not evidence of completeness.

Hard-fail before serialization unless `PROVED SOURCE MEMBERS == PROVED SOURCE-BACKED CANONICAL MEMBERS`, and after saving unless `SAVED DXF ENTITY IDs == CANONICAL ENTITY IDs`. Detail, member statuses and regression `521005-05_V4_31_APPROVED`: `CANONICAL_MEMBER_COMPLETENESS.md`.

## 3. V4.30 runtime-authority hardening

Load `references/RUNTIME_AUTHORITY_GUARD.md` before inherited core text. Repo-direct authority is:

`USER TASK -> AI_ENTRYPOINT -> ROUTER -> ROUTED MODULES/REFERENCES`.

Legacy compatibility wording, packaging precedence and the portable/history boundary are defined in that file. A route gap is `ROUTING_COVERAGE_GAP`; do not silently continue from portable/history.

## 4. Census before specialized rules

Inspect the actual source before selecting specialized modules. Build the preliminary census with only `YES`, `NO`, or `UNKNOWN`.

**UNKNOWN != NO.** Every `YES` and `UNKNOWN` family loads its route. After routed modules are loaded, re-check the source and close the final census.

Do not mark a feature absent merely because OCR did not find its keyword. Inspect geometry, leaders, witnesses, notes, revisions, sections/details, barcode/process cues and supplied customer DATA as applicable.

### Source gates before the final census

Each gate's rules live in its file; load it at the stated point.

- **V4.30 source feature-group gate:** `references/SOURCE_FEATURE_GROUP_CLOSURE.md`, before final preliminary Feature Census.
- **V4.29 source-manufacturing-note gate:** `references/SOURCE_MANUFACTURING_NOTE_CENSUS.md`, always-on source parsing before final preliminary Feature Census.
- **V4.28 face-creation gate:** for `BEND`, `MULTI_FACE`, or `UNKNOWN` mode candidates, `references/FACE_CREATION_BEND_EVIDENCE.md`, before final FACE_GRAPH closure.
- **V4.27 weld-cue gate:** `REVERSED_E_ABOVE_BARCODE -> WELD_REQUIRED_CUE`, scoped to its barcode/code cluster; rules in `skills/lispcad/router/FEATURE_CENSUS.md`.
- **V4.26 physical-curve gate:** whenever DXF geometry participates as customer DATA, reference, or direct-audit evidence, decode physical curves before Feature Census using `references/DXF_PHYSICAL_CURVE_DECODING.md`.

## 5. Bent / multi-face parts — V4.32 attachment / OD / bend-edge / relief gate

Every bent or multi-face part loads `skills/lispcad/modes/BEND_UNFOLD.md`, `references/FACE_GRAPH_UNFOLD_PROTOCOL.md`, `references/FACE_CREATION_BEND_EVIDENCE.md`, `references/BEND_ATTACHMENT_EDGE_OWNERSHIP.md`, `references/FORMED_PROFILE_OD_MEASUREMENT.md`, and `references/BEND_EDGE_RELIEF_90.md`.

Before production unfold/output close the `*_LOCKED` set in `BEND_UNFOLD.md` (including `BEND_ATTACHMENT_EDGE_LOCKED`), `OD_actual` ownership with `THICKNESS_SINGLE_USE`, and the bend-edge length from the actual shared edge. The `BEND_END_OFFSET_90` relief decision (signed `S`), mechanism precedence and no-duplicate-relief rule are in `BEND_EDGE_RELIEF_90.md`; fold-back identity checks are in `CROSS_FEATURE_VALIDATION.md`.

## 6. Source and mode routing

Classify exactly one source relationship (`PDF_ONLY`, `PDF_DATA_RAW`, `TRAIN_REFERENCE`, `DIRECT_EXISTING_DXF_AUDIT`) per the section "Source relationship classes and mode loads" in `references/SOURCE_DATA_CLASSIFICATION.md` (default-loaded). Mode loads: `ROUTER.yaml` `source_routes`.

## 7. Release wiring index

Moved to `docs/RELEASE_WIRING_INDEX.md`. It is a QA/audit index, not a load list: load only the regressions relevant to the routed family or an explicit audit.

## 8. Production completeness

Before production PASS or REVIEW_ONLY delivery, close every step of the §1 flow (notes -> groups -> members -> families -> census -> routes -> witness graph -> canonical members/entities -> serialized output -> saved entity-ID read-back) and every `ROUTER.yaml` `post_route_checks` item. For bent parts this includes FACE_GRAPH, `BEND_ATTACHMENT_EDGE_LOCKED`, `OD_actual` ownership, per-bend witness ledger, bend-edge material domain and any 90-degree bend-end relief decision (§5).

A correct bbox, raw entity count, syntactically valid DXF or successful generic read-back cannot compensate for a missing source note/group/member/family, false parameter comparison, wrong attachment edge, wrong bend domain, or missing/extra relief.

If a source-supported family has no route, stop with `ROUTING_COVERAGE_GAP`. Do not silently map it to generic CUT.

## 9. Portable and history policy

Snapshots and `docs/history/**` are outside normal production retrieval. Rules, pinned archive and read-only uses: `skills/lispcad/router/ROUTER.yaml` `history_policy` and `portable_compatibility`. After a `ROUTING_COVERAGE_GAP`, stop; do not silently continue production from snapshot text.

## 10. Regression and output

Load only regressions relevant to the routed rule/family or an explicit audit. Regression geometry is evidence/tests, not a source of missing dimensions for a new drawing.

Use current `VALIDATION.md` and `CAD_OUTPUT.md`. New CAD jobs follow the canonical contract in the top supplement: export through `tools/export_canonical_dxf.py`, then read back the actual saved DXF before calling production complete. Reprojection QA rules: `references/DXF_PHYSICAL_CURVE_DECODING.md` §6.

## 11. MCP boundary

**MCP is research-only and is NOT part of the production CAD pipeline.** Default CAD behavior remains repo-direct. Do not route through MCP for ordinary CAD production. Experimental MCP code has no production authority unless the user explicitly asks to work on MCP.
