# AGENTS.md — TrainAiCad orchestration policy

This root file is for agents that read repository instructions automatically. It is **orchestration only**: it holds no engineering formulas and no pinned release.

## 1. Bootstrap and authority
Follow `AI_BOOTSTRAP.md` for the bootstrap sequence and authority order, and `AI_ENTRYPOINT.md` for the current production release. Load routed modules through `skills/lispcad/router/FEATURE_CENSUS.md` and `skills/lispcad/router/ROUTER.yaml`, not by reading a portable snapshot. Pin one repository snapshot per job and do not change engineering authority halfway through an unfinished DXF. If freshness or access cannot be established, report the precise blocker. Never claim the current TrainAiCad repo was used when it was not actually read.

## 2. Source and tool execution
Actually inspect the supplied PDF/image/DXF source with the available vision, file and CAD tools. A filename, OCR fragment, bbox or entity count is not proof that the drawing was visually or semantically inspected. Use deterministic code for arithmetic, geometry checks, canonical export and DXF read-back where the repo requires them. Use model reasoning for source semantics, witness/leader scope, topology, ownership and ambiguity. Execute each stage the current repo requires; do not replace it with prose.

## 3. No-progress behavior
If the pipeline is producing placeholders, empty ledgers, representative rectangles, or otherwise making no real geometry progress, do not scale that failure to more codes. Identify the failing stage, preserve proved work, follow current repo fallback/FLAG behavior, and continue any unaffected executable work.

Never solve a no-progress condition by inventing dimensions, topology, source members or PASS status.

## 4. Reference and calibration
Follow `AI_BOOTSTRAP.md` §5. Do not reverse-fit source geometry from a sample, and do not promote sample-pending or FLAG geometry into production authority without source or user confirmation.

## 5. Repository-change boundary
A normal E2E request does not authorize repository changes.

Only modify or push production rules after explicit user approval such as `DUYỆT` or `PUSH`. Apply the current repo calibration and update discipline, add relevant executable regression tests, run required QA, and merge only after all required checks pass. Do not edit portable or history files as a shortcut around modular production authority.

## 6. Language of notes inside the DXF
Every note written into the combined DXF is Vietnamese (tiếng Việt, with diacritics; the template font is Arial TrueType): the `FLAG: ...` lines (no repeated work code; Vietnamese only, never English), Magenta preview/estimate notes and the global review banner. Keep identifiers verbatim: work codes, entity IDs, file names, rule names, coordinates and Japanese source text. No language is mandated for chat replies or Project job notes. Approved by the user (`DUYỆT`) on 2026-10-20.
