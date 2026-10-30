# JOB_CARD — TrainAiCad CAD job (read at job start and again at the start of every stage)

PDF / image / customer DXF DATA → canonical geometry JSON → verified DXF. `E2E` (or `Đọc repo TrainAiCad làm E2E`) with a source = run the whole job to the DXF. `QA` on an existing DXF = `rules/QA_REVERSE.md` instead. Unclear which → ask first.

## 12 non-negotiables
1. **Look yourself.** `tools/pdf_views.py`: grid render, vector `text --dims` for values, 600 dpi crops where witnesses/leaders decide. OCR, filenames, bbox, entity counts are hints, never proof.
2. **Ledger before arithmetic.** Each used number: `code | view | value | from-node | to-node | datum | kind | crop` — in the spec that is the witness step with its `ev`; `run_job.py` writes `ledger_<code>.md` from it. Scanned values read twice. Write the spec of each code to its file as soon as it is read.
3. **UNKNOWN ≠ NO.** NO needs evidence; YES and UNKNOWN load their card (`rules/CENSUS.md`).
4. **Tables by tool, never by eye:** `tools/lookup.py` (Nobi, Laser R, POINT/CIRCLE, pilot, ID→OD, unfold), `tools/acute_bend.py`, `tools/slit_geometry.py`.
5. **Always draw, never stop.** Every code drawn; an uncertain item = best source-supported estimate in Magenta + Vietnamese `FLAG:` + status PREVIEW. FLAG only real unknowns. Questions go in the report after the DXF.
6. **Missing Nobi → `SPLIT_FLANGE_10MM`** + FLAG (non-90° without handwriting, no J, t or L not in the table).
7. **No invention:** no bounding-rectangle placeholder, no borrowed neighbour dimension, no coordinate from a sample DXF, no mirror without proved partner/axis/scope.
8. **Spec / canonical JSON → `tools/run_job.py` (build → `export_canonical_dxf.py` → reopen the saved DXF).** Never write DXF with ezdxf yourself.
9. **PASS only for checks actually run.**
10. **DXF notes in Vietnamese** with diacritics; codes, entity IDs, file names and Japanese text verbatim.
11. **Pair codes (対称) agree:** `tools/pair_consistency.py` before export.
12. **A job never edits the repo.** Lessons are proposed in the report; rules change only after the user says `DUYỆT`/`PUSH`.

## Stages
| Stage | Do | Read | Write |
|---|---|---|---|
| L0 | list every code from the slip (作業No) and every source file; `job.py init` pins the commit | this card | `.work/<JOB>/job_state.json` |
| L1 | per code: inspect source, notes census, families YES/NO/UNKNOWN, `job.py census <code>` | `rules/READ_SOURCE.md`, `rules/CENSUS.md` + L1 cards it prints | `census_<code>.json`, `ledger_<code>.md` |
| L2 | identity, datum, witnesses, faces/bends, lookups, canonical | L2 cards from the resolver | `spec_<code>.yaml` or `job.json` part |
| L3 | validate, holistic challenge, pair check, export, read-back | `rules/VALIDATE.md`, `rules/OUTPUT.md` | `<JOB>_ALL.dxf` / `<JOB>_ALL_REVIEW_ONLY.dxf` → `job.py deliver` |
| Report | per-code table, corrections, every FLAG, customer questions, time | `rules/OUTPUT.md` §8 | chat |

One code at a time; keep proved work per code (a failure never forces redoing a proved code). After every code/stage run `job.py set <code> --stage .. --status .. [--flag ..] [--file key=path]`; after a compaction run `job.py status` and continue from the files. A census change → rerun `job.py census`. A job-local script = a tool gap: name it in the report.

## Commands
```sh
python tools/job.py init <JOB> [--source x.pdf]   # slip.py -> codes; then: status | set | census --set/--from | qa | deliver | deliver-code | clean
python tools/pdf_views.py info|render|text|crop|pairs drawing.pdf --page 1 [--dims] [--cells C3:E5] [--dpi 600] --out x.png
python tools/resolve_rules.py census.json [--bundle rules.md]  # cards per stage + customer notes (job.py census wraps it)
python tools/dxf_digest.py file.dxf [--out digest.json] [--png v.png]   # any DXF: views, holes by Ø, R, piece ids; `show` zooms
python tools/dxf_assemble.py digest.json plan.json --out assembled.json   # DATA pieces by id -> spec part `data: assembled.json`
python tools/lookup.py nobi --material SPCC --t 1.6 --L 900 [--angle 135] [--surface "#1"] [--handwritten 0.36] [--no-j] [--customer 646]
python tools/lookup.py laser-r --material SS400 --t 9 [--customer 768]
python tools/lookup.py hole --material SS400 --t 9 --dia 4.2 [--piercing] [--through] [--customer 859]
python tools/lookup.py pilot --thread M8x1        # also: countersink --thread M6, tooling --material SPCC --t 3
python tools/lookup.py idod --t 3 --angle 165
python tools/lookup.py leg --a 35 --b 65 --t 6 --angle 120 --nobi 4.92   # non-90° OD when the dims stop at the end faces
python tools/lookup.py slit --material SS400 --t 6 --S -2 --angle 120      # S gates the relief at every angle
python tools/lookup.py unfold --od 410.8 20.8 175 --nobi 1.68 0.36
python tools/acute_bend.py od --t 3 --angle 75 --rin 0.6 --inside 179.2 46.9
python tools/run_job.py spec_A.yaml spec_B.yaml [box.job.json] OUT/   # whole job: build -> export -> reopen -> report
python tools/boxmet_job.py --code 26-XXXXXX --L 200 --W 150 --H 30 30 30 30 --T 1.5 --material SS --N 2.54 --job-id <JOB> --out box.job.json
python tools/pair_consistency.py job.json CODE_A CODE_B [--mirror x|y|none]
python tools/overlay_check.py job.json CODE --image crop.png --anchor x,y=px,py (x3) --out ov.png
```
A tool result with `status: FLAG` gives the `action` to draw and the Vietnamese `flag_vi` to copy into the FLAG line.

Not production sources: `regression/` (evidence only, open a lesson only when a card points to it), `tests/`, git history.
