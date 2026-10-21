# JOB_CARD — TrainAiCad CAD job (read at job start AND again at the start of every stage)

Thẻ việc ngắn: 12 điều không được quên + thứ tự bước + lệnh tool. Detailed rules live in the routed files; this card never overrides them, it keeps them from being forgotten.

## 12 non-negotiables

1. **Look at the source yourself.** `tools/pdf_views.py`: render every page with the grid, take vector text for exact values, crop at 600 dpi every view, detail, note and title block that decides meaning. OCR, filename, bbox, entity count and familiar shapes are search hints, never proof.
2. **Dimension ledger before arithmetic.** Every number you use gets one row: `code | view | value | from-node | to-node | datum | kind (baseline/chain/overall/ordinate/reference) | crop ref`. Read each value twice (two different crops or zoom levels); OCR swaps `B/8 O/0 S/5 Ø/O M6/MG` are only candidates until the glyph is checked.
3. **UNKNOWN ≠ NO.** A feature family is NO only with evidence; YES and UNKNOWN both load their rule (`FEATURE_CENSUS.md`).
4. **Tables by tool, never by eye.** Nobi, Laser R, hole POINT/CIRCLE, thread pilot, ID→OD and unfold arithmetic come from `python tools/lookup.py` (commands below). Corner class and feature identity remain your engineering decision.
5. **Always draw, never stop.** Every code is drawn. Uncertain items: best source-supported estimate in Magenta + Vietnamese `FLAG:` + status REVIEW. Unknown hole → Magenta circle + FLAG, never omitted. Questions go in the report after the DXF (`REVIEW_PREVIEW_POLICY.md`).
6. **Missing Nobi → `SPLIT_FLANGE_10MM`** (flange drawn as a separate piece 10 mm away, FLAG). Non-90° without handwritten Nobi, no J, t not tabulated, L out of table: all split (`BEND_UNFOLD.md` §4.7).
7. **No invention.** No bounding-rectangle placeholder, no dimension borrowed from a neighbor, no coordinate reverse-fitted from a sample/reference DXF, no mirror without proof of partner, axis and scope.
8. **Geometry goes canonical JSON → `tools/export_canonical_dxf.py` → reopen the saved DXF.** Never write DXF by hand with ezdxf.
9. **PASS only for checks actually executed.** A check you could not run is FLAG/WARN, not PASS.
10. **DXF notes are Vietnamese** (`FLAG: ...`, Magenta notes, review banner); identifiers and Japanese source text verbatim.
11. **Pair codes agree.** Codes marked 対称 or drawn as a pair: run `python tools/pair_consistency.py` before export; any mismatch is re-read from the source.
12. **A job never edits repo rules.** Lessons are proposed in the report; production rules change only after the user says `DUYỆT`/`PUSH`.

## Stages (read rules only when the stage starts; re-read this card first)

| Stage | Do | Read | Output |
|---|---|---|---|
| L0 | Pin repo commit; list every code from the slip (作業No) and every source file | this card, `AI_ENTRYPOINT.md` | job list |
| L1 | Per code: inspect source, notes census, feature census YES/NO/UNKNOWN; `python tools/resolve_rules.py census.json` | `FEATURE_CENSUS.md` + Router `default_load` | `census.json`, dimension ledger, rule list per stage |
| L2 | Per code: identity, datum, witness graph, members, faces/bends; lookups; canonical JSON | L2 paths from the resolver | canonical part JSON |
| L3 | Validate, holistic challenge, pair check, export, saved-DXF read-back | L3 paths from the resolver | `<JOB>_ALL.dxf` or `<JOB>_ALL_REVIEW_ONLY.dxf` |
| Report | Per-code table, corrections, every FLAG, questions for the customer | `CAD_OUTPUT.md` §11 | chat report + DXF |

Work one code at a time and keep proved work per code; a failure in one code never forces redoing another. If a census value changes later, rerun the resolver.

## Tool commands

```sh
python tools/pdf_views.py info drawing.pdf
python tools/pdf_views.py render drawing.pdf --page 1 --out p1.png
python tools/pdf_views.py text drawing.pdf --page 1 --dims [--cells C3:E5]
python tools/pdf_views.py crop drawing.pdf --page 1 --cells C3:E5 --out c.png
python tools/lookup.py nobi --material SPCC --t 1.6 --L 900 [--angle 135] [--surface "#1"] [--handwritten 0.36] [--no-j] [--customer 646]
python tools/lookup.py laser-r --material SS400 --t 9
python tools/lookup.py hole --material SS400 --t 9 --dia 4.2 [--piercing] [--through]
python tools/lookup.py pilot --thread M8x1
python tools/lookup.py idod --t 3 --angle 165
python tools/lookup.py unfold --od 410.8 20.8 175 --nobi 1.68 0.36
python tools/resolve_rules.py census.json
python tools/pair_consistency.py job.json CODE_A CODE_B [--mirror x|y|none]
python tools/export_canonical_dxf.py job.json OUT/
```

A tool result with `status: FLAG` gives the `action` to draw and the Vietnamese `flag_vi` text to copy into the FLAG line.
