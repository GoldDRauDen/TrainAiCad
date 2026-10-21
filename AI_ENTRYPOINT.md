# AI ENTRYPOINT — TrainAiCad repo-direct production

Current production release is **V4.34**.

This file is the production routing authority. New jobs use `TrainAiCad-CANONICAL-V4.34` with `tools/CANONICAL_INPUT_SCHEMA_V434.md`; preexisting V4.31 fixtures stay supported. Normal CAD jobs use **repo-direct modular routing**; never load the complete portable skill by default. `JOB_CARD.md` is the short card to re-read at every stage; it summarizes, it does not override.

## Invocation contract

When the user supplies CAD source and says `E2E`, `read TrainAiCad and do E2E`, or equivalent, execute the complete current repo-direct production flow below to its executable limit. Do not require the user to restate census, routing, canonical, export, read-back or QA steps. `AI_BOOTSTRAP.md` is the release-independent discovery layer; this file remains the production engineering authority.

## 1. Normal production flow

Mandatory router files: `skills/lispcad/router/FEATURE_CENSUS.md` and `skills/lispcad/router/ROUTER.yaml`. `skills/lispcad/router/RULE_COVERAGE.yaml` is for repository QA and bundle audits, not job retrieval. Always-on files are the Router `default_load`; do not invent another core set from memory.

1. **Source (L1):** runtime authority guard → source classification → physical-curve decode of any customer DXF → source manufacturing-note census → source feature-group / reference-parameter closure → part identity graph and assembly-datum candidates when multi-code/assembly is not proven absent → feature census → `tools/resolve_rules.py`. Defer any calibration sample until the `SOURCE_ONLY_SNAPSHOT` is frozen.
2. **Geometry (L2):** routed mode/feature/reference modules; for bends the attachment-edge lock, formed-profile OD, bend-edge / 90° bend-end relief; dimension/witness graph; table values from `python tools/lookup.py`; first source-only solve.
3. **Validate/export (L3):** cross-feature validation → source group + member ledger → holistic engineering challenge (re-open source on any anomaly) → local FLAG or complete VIEWS_ONLY fallback → final engineering sanity review → canonical member model → `PROVED SOURCE MEMBERS == PROVED CANONICAL MEMBERS` → canonical entities → `tools/export_canonical_dxf.py` → `SAVED DXF ENTITY IDs == CANONICAL ENTITY IDs` → saved-DXF read-back and applicable source reprojection.

Per-code rules:
- Process codes independently; store proved work by code so a failed part never forces rebuilding a verified one. Pair/対称 codes are cross-checked with `tools/pair_consistency.py`.
- Actually read the selected rule files; a selected path is not proof its contents were loaded.
- Reroute any code whose feature classification changes after zoom/DATA audit.
- Unresolved after source exhaustion: draw it anyway under `references/REVIEW_PREVIEW_POLICY.md` (Magenta + Vietnamese FLAG, REVIEW); never invent dimensions, never stop the job, never drop a code.
- No PASS from bbox, entity count or a plausible contour. Only an independently verified part is PASS; a local flag never silently becomes an approved CUT.

## 2. Hard gates and their owners

| Gate | Owner (load point) |
|---|---|
| Runtime authority, legacy wording, portable/history boundary | `references/RUNTIME_AUTHORITY_GUARD.md` (first) |
| Source class `PDF_ONLY` / `PDF_DATA_RAW` / `TRAIN_REFERENCE` / `DIRECT_EXISTING_DXF_AUDIT` | `references/SOURCE_DATA_CLASSIFICATION.md`; mode loads in Router `source_routes` |
| Physical-curve decode whenever DXF geometry participates | `references/DXF_PHYSICAL_CURVE_DECODING.md` (before census) |
| Source manufacturing notes; feature groups | `SOURCE_MANUFACTURING_NOTE_CENSUS.md`, `SOURCE_FEATURE_GROUP_CLOSURE.md` (before census) |
| Weld cue `REVERSED_E_ABOVE_BARCODE -> WELD_REQUIRED_CUE`; KH851 weld-site KEGAKI | `FEATURE_CENSUS.md`; `references/WELD_SITE_KEGAKI_CLOSURE.md` + `tools/weld_kegaki_guard.py` |
| Face creation for BEND/MULTI_FACE/UNKNOWN candidates | `references/FACE_CREATION_BEND_EVIDENCE.md` |
| `BEND_ATTACHMENT_EDGE_LOCKED`, `OD_actual` ownership, `THICKNESS_SINGLE_USE` | `BEND_ATTACHMENT_EDGE_OWNERSHIP.md`, `FORMED_PROFILE_OD_MEASUREMENT.md`, `BEND_UNFOLD.md` |
| Material aliases (SECC=ボンデ → SS), HL grain vector, typed witness graph, slot anchors | `MATERIAL_ALIASES.yaml`, `VALIDATION.md`, `DATUM_DIMENSION.md` |
| Canonical completeness, `NO_DIRECT_DXF_FROM_INTERPRETATION` | `references/CANONICAL_MEMBER_COMPLETENESS.md` (before final census) |
| Holistic challenge, `FINAL_ENGINEERING_SANITY_REVIEW` | `references/HOLISTIC_ENGINEERING_CHALLENGE.md` (L3) |
| Reference firewall (`REFERENCE_ASSISTED_UNDERSTANDING`, `CUSTOMER_CONFIRMATION_PENDING`) | `references/REFERENCE_EXPOSURE_FIREWALL.md` (only when a sample is present/unknown) |

**NO_DIRECT_DXF_FROM_INTERPRETATION:** never write a hand-picked subset from interpretation straight into `ezdxf.modelspace()`; persist source groups/members and canonical members, then serialize with `tools/export_canonical_dxf.py`. `tools/export_dxf.py` is a packaging component, not evidence of completeness. Hard-fail before serialization unless `PROVED SOURCE MEMBERS == PROVED SOURCE-BACKED CANONICAL MEMBERS`, and after saving unless `SAVED DXF ENTITY IDs == CANONICAL ENTITY IDs`.

## 3. Packaging

`skills/lispcad/core/CAD_OUTPUT.md` §1 owns it: by default one `<JOB>_ALL.dxf` or `<JOB>_ALL_REVIEW_ONLY.dxf`, no JSON output; individual PASS cuts only with `--individual-dxf`, named by the slip work number (e.g. `26-056522`). Lower-level `export_dxf.py` modes never override it.

## 4. Census before specialized rules

Inspect the actual source before selecting specialized modules. Census states are only `YES`, `NO`, `UNKNOWN`. **UNKNOWN != NO**: every `YES` and `UNKNOWN` family loads its route; after routed modules are loaded, re-check the source and close the final census. A family is never NO merely because OCR did not find its keyword: inspect geometry, leaders, witnesses, notes, revisions, sections/details, barcode/process cues and customer DATA.

## 5. Bent / multi-face parts

Every bent or multi-face part loads the Router `mode_routes` set (`BEND_UNFOLD.md`, `references/FACE_GRAPH_UNFOLD_PROTOCOL.md`, `FACE_CREATION_BEND_EVIDENCE.md`, `BEND_ATTACHMENT_EDGE_OWNERSHIP.md`, `FORMED_PROFILE_OD_MEASUREMENT.md`, `BEND_EDGE_RELIEF_90.md`, …). Before unfold close the `*_LOCKED` set, `OD_actual` ownership and the bend-edge length from the real shared edge. `NEAREST_VIEW_EDGE`, paper proximity and visual symmetry are not evidence; a formed/profile view is a measurement view, not CUT geometry. Nobi and its missing-Nobi fallback (`SPLIT_FLANGE_10MM`) follow `BEND_UNFOLD.md` §4.7.

## 6. Source and mode routing

Classify exactly one source relationship per `references/SOURCE_DATA_CLASSIFICATION.md` (default-loaded); mode loads come from `ROUTER.yaml` `source_routes`.

## 7. Release wiring index

Moved to `docs/RELEASE_WIRING_INDEX.md`. It is a QA/audit index, not a load list: load only the regressions relevant to the routed family or an explicit audit.

## 8. Production completeness

Before PASS or REVIEW_ONLY delivery close every step of §1 and every Router `post_route_checks` item. A correct bbox, entity count, valid DXF syntax or generic read-back cannot compensate for a missing note/group/member/family, false parameter comparison, wrong attachment edge, wrong bend domain or missing/extra relief. A source-supported family with no route stops that family with `ROUTING_COVERAGE_GAP`; never map it silently to generic CUT.

## 9. Portable and history policy

Snapshots and `docs/history/**` are outside normal retrieval (Router `history_policy`, `portable_compatibility`). After a `ROUTING_COVERAGE_GAP`, never continue production from snapshot text.

## 10. Regression and output

Load only regressions relevant to the routed family or an explicit audit; regression geometry is evidence, never a source of missing dimensions. Use current `VALIDATION.md` and `CAD_OUTPUT.md`; reprojection QA rules: `references/DXF_PHYSICAL_CURVE_DECODING.md` §6.

## 11. MCP boundary

**MCP is research-only and is NOT part of the production CAD pipeline.** Default CAD behavior remains repo-direct. Do not route through MCP for ordinary CAD production unless the user explicitly asks to work on MCP.
