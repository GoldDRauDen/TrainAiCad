# CENSUS — what is on the drawing → which cards to read (L1, always)

One `census_<code>.json` per code via `python tools/job.py census <code> --set HOLE=YES:<ev> --rest NO ..` (all codes: `--from census.yaml`); it prints the cards per stage and the customer's notes. States: `YES | NO | UNKNOWN`. **UNKNOWN ≠ NO**: YES and UNKNOWN both load. NO needs evidence (geometry, leaders, notes, revisions, sections, barcode cues, DATA) — a missing OCR keyword is not evidence. Re-run the resolver whenever a state changes.

## Trigger index
| Family | Look for | Card |
|---|---|---|
| HOLE | `Ø`, `n-Ø`, `穴`, `キリ`, circles | HOLE_TAP |
| TAP | `M6`, `M8x1`, `タップ`, `ネジ` | HOLE_TAP |
| PIASU | `ピアス`, `PIERCING`, `THROUGH HOLE`, `白ピアス`, points | HOLE_TAP |
| SLOT_STRAIGHT / CURVED_SLOT | `長穴`, stadium/arc slots | SLOT |
| KEGAKI | `ケガキ`, reversed-e above barcode, welded child, assembly A/B/C, customer 851 | KEGAKI |
| RIB / FORMING_FEATURES | rib/gusset part, louver, emboss, dimple, half shear, curl, lance | KEGAKI |
| SLIT_RELIEF | `スリット`, `SLIT`, Green lines at bend ends, box corners | SLIT_RELIEF |
| part_mode BEND / MULTI_FACE / UNKNOWN (L, U, Z, hem, box, Nobi) | `曲げ`, `ノビ`, double dashed lines, side/section views, `J` | BEND + SLIT_RELIEF |
| ACUTE_BEND_LT85 | included angle ≤85° | BEND_ACUTE |
| BOXMET | base + four flanges, corners drawn sharp | SLIT_RELIEF |
| source_mode PDF_DATA_RAW | customer DXF with the PDF | DATA_DXF |
| reference_present YES/UNKNOWN | sample / approved DXF | REFERENCE |
| multi_code_or_assembly YES/UNKNOWN | several codes/constituents/weld relations | MULTI_PART |

Always: READ_SOURCE + CENSUS (L1; revisions/cancellation in READ_SOURCE §5), DATUM + CORNER_RC (L2; every corner, R/C callouts, Laser R), VALIDATE + OUTPUT (L3). Stepped/notched contours: DATUM §3 (flat) or BEND §7 (flange).

## census fields (`job.py census` flags / `--from` keys)
`source_mode` PDF_ONLY | PDF_DATA_RAW | TRAIN_REFERENCE | DIRECT_EXISTING_DXF_AUDIT; `part_mode` FLAT_NO_BEND | BEND | MULTI_FACE | UNKNOWN; `reference_present`, `multi_code_or_assembly` YES | NO | UNKNOWN; `customer_code` numeric (JOB STATISTICS) or null; notes `{note_text, code_scope, candidate_family, resolution}`; `features`: every template key `{state, evidence: [page/view/region or DATA ids]}`; `material_and_grain` {printed_grade, alias_resolved, hairline_HL: {state, grain_vector_part_relative: PROVED|UNPROVED|NOT_APPLICABLE}}; KH851 / weld evidence: `source_assembly_view_ids`, `source_weld_site_ids`, `weld_site_census` (KEGAKI.md §2).
Material/HL fields are not feature families. HL with grain `UNPROVED` forces REVIEW.

## Hard stops (drawing still happens, PASS does not)
- A source-supported family with no route → `ROUTING_COVERAGE_GAP` (never silently generic CUT).
- A DXF segment with bulge not decoded → census incomplete.
- A note `UNRESOLVED` while its family is NO → census invalid; route it UNKNOWN.
- Final closure: `NOTES → ACTIVE FAMILIES → FINAL CENSUS → LOADED CARDS → CANONICAL FAMILIES → DXF` with nothing unexplained.
