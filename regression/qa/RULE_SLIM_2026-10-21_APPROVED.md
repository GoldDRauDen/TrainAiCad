# Rule slim + lookup tools — approved 2026-10-21 (user: DUYỆT)

## FACT
- Job 520925-07 (2026-10-18 E2E report): ~285 KB of rules per job, 125–200k tokens of context per turn, 29 model calls, 23.6 min; 1 MATCH / 1 PARTIAL / 2 DIFF. Two codes ended VIEWS_ONLY although `161+41-9.78=192.22` was already verified; pair 056159/056160 disagreed on a slot by 10 mm.
- Audit of the rules found direct contradictions: three different missing-Nobi fallbacks; English DXF note examples against the Vietnamese-only rule; "STOP and ask" against "execute to the limit / never stop at text"; schema V431 in SKILL vs V434 elsewhere; DATA authority vs "implied DXF geometry" rank 7; feasibility table "Flag" vs advisory-only text; dead section references (`BEND_UNFOLD §4.10`, `DRAWING_READING §2.1/§2.4/§0.3`, `Section 6`, `Section 7.3`, `services/trainaicad-mcp/`).
- Table lookups (Nobi, Laser R, hole POINT/CIRCLE, thread pilot) existed only as prose for the model to read by eye.

## ROOT_CAUSE
Rules were written for the model to remember and obey; every lesson added prose, so context grew, contradictions accumulated, and the safest status (REVIEW/VIEWS_ONLY) won when rules conflicted.

## USER DECISIONS (2026-10-21)
1. Runtime: Claude web.
2. Missing Nobi → **split the flange 10 mm + FLAG**, distinguishing 90° (table allowed) from non-90° (never a 90° row).
3. Thickness not in the Nobi table → **FLAG** (no next-higher row).
4. Ambiguity → **REVIEW but always draw everything**; e.g. a hole with missing data is drawn approximately in Magenta with a FLAG, never omitted; the job never stops to ask.
5. SUS: 2B by default, #1 when the source states #1; rows where #1 > 2B are genuine.

## LESSON (implemented)
- `tools/lookup.py` (parses the owning Markdown tables) + `tests/test_lookup.py` reproduce every approved table regression.
- `JOB_CARD.md` (≤6 KB) is the first L0 file and is re-read at every stage.
- `tools/pdf_views.py` gives exact vector dimension text with grid cells and 600-dpi crops; `tools/pair_consistency.py` cross-checks pair codes.
- Contradictions resolved in their owning files; `REVIEW_PREVIEW_POLICY.md` §0 "always draw, never stop".
- `AI_ENTRYPOINT` 13.6→8.3 KB, `VALIDATION` 20.2→13.0 KB, `CAD_OUTPUT` 16.5→12.2 KB, `MATERIAL_RULES` 12.8→8.5 KB; budgets tightened in `tests/test_rule_load_budget.py`; `tests/test_cross_references.py` blocks dead references.

## REGRESSION_CASE
`tests/test_lookup.py`, `tests/test_pair_consistency.py`, `tests/test_pdf_views.py`, `tests/test_job_card.py`, `tests/test_cross_references.py`. Superseded text: `docs/RULE_HISTORY.md` (2026-10-21 sections).
