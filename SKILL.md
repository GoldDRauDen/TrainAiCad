---
name: trainaicad-e2e
description: Source-grounded mechanical sheet-metal CAD from PDF, images and customer DXF DATA through canonical Geometry JSON, validation, export and saved-DXF QA.
---

# TrainAiCad — Universal CAD E2E Skill

**This is the only cross-agent workflow entry point. It is not a second engineering
rule source.** Read this file first, then `JOB_CARD.md` (re-read it at the start of
every stage), then resolve current engineering authority from the same repository
revision. Repository: `GoldDRauDen/TrainAiCad`.

## 0. Compatibility and tool gate

An agent may be ChatGPT, Codex, Claude, Gemini or another model; brands do
not determine whether CAD execution is available. It must have:

- Access to the actual current repository snapshot and user-provided source.
- Capability to inspect PDF pages/regions and images visually, including
  cropping and magnification when source evidence requires it.
- For customer DATA: a way to inspect/decode DXF entity types, transforms,
  arcs, bulges, layers and units without losing physical curves.
- A runtime with filesystem, Python and the repository dependencies (or
  equivalent verified CAD tooling) to build JSON, execute deterministic
  geometry checks, save DXF and reopen the exact saved DXF.

If a capability is absent, report the precise blocked stage and preserve proved
work. Do not claim source inspected, geometry proved, PASS or DXF exported
without the corresponding actual work.

## 1. Production authority and single source of truth

`current user task -> AI_BOOTSTRAP.md -> AI_ENTRYPOINT.md -> FEATURE_CENSUS.md
-> ROUTER.yaml -> routed modules/references -> canonical/export tools`.

Pin one commit SHA and routing release for a job. Source drawings and customer
production notes govern its facts and dimensions. User-approved engineering
rules are sourced only from the current repo-direct path. `SKILL.md` specifies
the E2E workflow, never overrides engineering values or release-specific gates.
Current release is discovered from `AI_ENTRYPOINT.md` and `ROUTER.yaml`;
do not hardcode it from this file.

Default retrieval **excludes** `skills/lispcad/versions/`,
`skills/lispcad/portable/`, `docs/history/`, and `regression/`.
Regression documents are QA evidence, never new customer dimensional inputs.
MCP is research-only, not the default engine.

## 2. Trigger and per-code workflow

A CAD source plus `E2E` or `Read TrainAiCad and do E2E` starts the full
executable job, not only a textual interpretation. Follow the order in
`AI_ENTRYPOINT.md` §1 and its per-code rules:

1. **Job/source census:** all codes and source views; link barcode, material,
   thickness, notes, revisions and customer DATA to their parts. Keep
   forbidden/user-excluded files closed.
2. **Read/exhaust source:** every relevant view and detail; zoom/crop unclear
   regions; trace witnesses; keep raw DATA physical curves; separate
   sample/reference evidence from production source.
3. **Feature routing:** FEATURE_CENSUS per code (`skills/lispcad/router/FEATURE_CENSUS.md`),
   each family YES/NO/UNKNOWN, UNKNOWN loads its rule. Resolver:
   `python tools/resolve_rules.py census.json` when Python is available. All
   four stages (L0 bootstrap, L1 census, L2 selected rules, L3 validation/export/QA)
   are mandatory.
4. **Engineering geometry:** part identity, datum, witness graph, member
   inventory, families and, when applicable, FACE_GRAPH and bend terms. Build
   per-code canonical Geometry JSON per `tools/CANONICAL_INPUT_SCHEMA_V434.md`
   for new jobs (V4.31 inputs stay readable).
5. **Independent validation:** run all Router and `VALIDATION.md` checks,
   including source-to-canonical completeness. Unresolved after source
   exhaustion means REVIEW semantics, not invented dimensions.
6. **Deterministic export:** `tools/export_canonical_dxf.py` for supported jobs.
7. **Saved-DXF QA:** reopen the emitted DXF; validate geometry and canonical
   Entity IDs/XDATA against source and permitted reference evidence.
8. **Deliver/report:** verified files; per-code PASS/REVIEW with unresolved
   dimensions/features and source references.

## 3. Canonical status and artifact contracts

Output packaging, XDATA entity IDs and CUT-file contents are defined in
`skills/lispcad/core/CAD_OUTPUT.md` and `tools/DXF_INPUT_SCHEMA.md`.

**Implemented canonical production artifact contract** (after upstream
source/engineering QA and composite canonical read-back):

```text
<JOB>/
  parts_dxf/<slip-no>.dxf        # ONLY on explicit request (--individual-dxf); QA PASS only; LINE/ARC/CIRCLE CUT only; slip-no = slip work no., e.g. 26-056522
  <JOB>_ALL.dxf                    # if all PASS
  <JOB>_ALL_REVIEW_ONLY.dxf        # otherwise all codes, warnings intact
```

REVIEW_ONLY output is not safe to manufacture. Do not fabricate a claim of
customer-drawing correctness merely because the structural export tests pass;
full source-grounded acceptance remains necessary for manufacturing PASS.

## 4. Execution and QA rules

- No fabricated geometry, dimensions, source examination or PASS.
- No promotion of a user-supplied reference/sample into source authority.
- Preserve unresolved feature provenance and never conceal it within CUT.
- Preserve all source-proved groups/members; FAIL an empty/subset ledger that
  misrepresents source completeness.
- Respect user-forbidden files: never open/read/copy/use.
- Do not modify user-approved rules while processing a normal E2E job.
  Proposed lessons become production rules only after explicit approval,
  with regression and saved-output QA.

## 5. Portable one-file use

When multi-file repository ingestion is unavailable, a code-capable executor
can run `python tools/build_rule_bundle.py --output
../TrainAiCad_E2E_RULEPACK.md` and pass the resulting single generated document
to another model. The build collects current Router-approved modules, **not**
obsolete portable snapshots. That document has a build manifest, content hash,
and snapshot context. It is a read-only handoff, not a runtime/CAD engine.
