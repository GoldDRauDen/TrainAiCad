# AI ENTRYPOINT — TrainAiCad repo-direct production

Current approved production release: **V4.23**.

This file is the production routing authority. Normal CAD jobs use **repo-direct modular routing**. Do not load the complete portable skill by default.

## 1. Normal production flow

```text
SOURCE
  -> always-on CORE
  -> SOURCE CLASSIFICATION
  -> FEATURE CENSUS
  -> ROUTER
  -> selected mode / feature / reference modules
  -> CROSS-FEATURE VALIDATION
  -> canonical geometry
  -> DXF
  -> saved-DXF read-back / applicable source reprojection
```

Mandatory router files:

- `skills/lispcad/router/FEATURE_CENSUS.md`
- `skills/lispcad/router/ROUTER.yaml`
- `skills/lispcad/router/RULE_COVERAGE.yaml`

Always-on core is declared in `ROUTER.yaml`. Do not invent a different core set from memory.

## 2. Census before specialized rules

Inspect the actual source before selecting specialized modules. Build the preliminary census with only:

- `YES`
- `NO`
- `UNKNOWN`

**UNKNOWN != NO.** Every `YES` and `UNKNOWN` family loads its route. After routed modules are loaded, re-check the source and close the final census.

Do not mark a feature absent merely because OCR did not find its keyword. Inspect geometry, leaders, witnesses, notes, revisions, sections/details and supplied customer DATA as applicable.

## 3. Source routing

Classify exactly one source relationship using `references/SOURCE_DATA_CLASSIFICATION.md`:

- `PDF_ONLY`
- `PDF_DATA_RAW`
- `TRAIN_REFERENCE`
- `DIRECT_EXISTING_DXF_AUDIT`

For `PDF_DATA_RAW`, the router loads the current DATA-geometry-preservation and physical-census/bidirectional-QA references. Customer DATA supplies physical geometry; PDF controls semantics, dimensions, revisions and manufacturing meaning under the approved rules.

For every bent or multi-face part, the router loads `modes/BEND_UNFOLD.md` and `references/FACE_GRAPH_UNFOLD_PROTOCOL.md`.

## 4. Current hard gates retained by the modular route

The modular route does not weaken any approved rule. In particular:

- V4.23 per-bend witness ledger and thickness-single-use checks remain active.
- V4.22 source exhaustion and source-family completeness remain active.
- V4.21 customer-DATA geometry preservation and source reprojection remain active.
- V4.20 source/mechanical classification and independent KEGAKI / SLIT-RELIEF / RIB / CURVED_SLOT routing remain active.
- V4.19 constraint-closed signed FACE_GRAPH and fold-back remain active for bent/multi-face work.
- Existing datum, source-witness, R/C, material, Nobi, thread-pilot, cancellation, preview, output and saved-DXF QA rules remain active through their routed modules.

The audit mapping from approved release families to active modular files is `skills/lispcad/router/RULE_COVERAGE.yaml`.

## 5. Production completeness

Before production PASS, close:

```text
SOURCE ACTIVE FAMILIES
  -> FINAL FEATURE CENSUS
  -> LOADED ROUTES
  -> CANONICAL GEOMETRY
  -> SERIALIZED OUTPUT
```

Then run the active validation and output contract. A correct bbox, entity count, syntactically valid DXF or successful read-back cannot compensate for a missing source manufacturing family.

If a source-supported feature has no route, stop with `ROUTING_COVERAGE_GAP`. Do not silently map it to generic CUT.

## 6. Portable and history policy

`skills/lispcad/portable/SKILL_LISPCAD_CURRENT.md` is retained as the complete V4.23 compatibility/audit snapshot so no approved rule text is destroyed by this migration.

It is **NOT part of the normal repo-direct load path**.

It may be read only to diagnose a `ROUTING_COVERAGE_GAP`, audit historical coverage, or perform an explicitly requested portability check. After a gap is found, do not silently continue production from the portable file; fix/approve the missing route first.

Normal production retrieval must exclude:

- `skills/lispcad/versions/**`
- `docs/history/**`

Historical snapshots never override active modular rules.

## 7. Regression and output

Load only regressions relevant to the routed rule/family or an explicit audit. Regression geometry is evidence/tests, not a source of missing dimensions for a new drawing.

Use the current core `VALIDATION.md` and `CAD_OUTPUT.md` contract plus applicable routed modules. Read back the actual saved DXF before calling production complete.

## 8. MCP boundary

Normal production is repo-direct. Experimental code under `services/trainaicad-mcp/` is outside this routing path and has no production authority unless the user explicitly asks to work on MCP.
