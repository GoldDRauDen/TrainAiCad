# 521023-16 — FLAG noise, J/LJ edge, misread slope, slow flat job (user-approved 2026-10-23, DUYỆT)

Source: 521023-16.pdf (slip + 4 drawings, scanned). User review of the first delivered `521023-16_ALL_REVIEW_ONLY.dxf`.

| # | FACT | ROOT_CAUSE | LESSON (owner file) |
|---|---|---|---|
| 1 | 26-062954 (SUS304 t2): note 「指示無き角部はC0.5程度の面取りのこと」 was FLAGGED against the Laser R table. User: the general note IS the Laser R; draw R0.5, no FLAG. | General corner note read as a competing explicit C callout. | Note for uncalled corners → AUTO_R, no FLAG (`CHAMFER_RADIUS.md`). |
| 2 | 26-062954: `C1` leader at slot 1 mouth only; slot 2 drawn identically; FLAGGED. User: obvious, C1 applies to both. | "Drawn R/C without callout → FLAG" applied to a sibling of a called `2-` family. | Sibling of a called `n-` family is CALLED (`CHAMFER_RADIUS.md`). |
| 3 | 26-062954: bare `R` leader on the semicircular end, width `2-8.5`; FLAGGED "R unvalued". User: R only marks the arc; R=8.5/2=4.25. | Bare R read as a missing value. | Bare R on width-dimensioned slot/notch end = W/2 (`SLOTS.md`). |
| 4 | 26-062954: "no SUS front-side label found (customer 843)" FLAGGED. User: not needed. | Customer note read as a mandatory label. | Respect a printed label; no label is not a FLAG (`CUSTOMER_CAD_RULES.yaml` 843). |
| 5 | 26-062961 (A2017 t5, 1720×70, 8 V-notches): drawn 70 at the left end sloping DOWN to 65 at x=100. Drawing: left end 65 (extension line of 65 meets the left edge), slope UP to 70 at x=100, flats at 70, V bottoms at 45. | Slope read from a low-zoom view; the 70 extension line taken as the corner. | Close same-axis dims (70/65): crop ≥900 dpi, name the edge each extension line touches; overlay the built part on the crop, ≥3 anchors ≤1 mm (`DRAWING_READING.md`, `JOB_CARD.md`, `tools/overlay_check.py`). Overlay of the wrong model gave 2.39 mm, the corrected one 0.22 mm. |
| 6 | J/LJ: 26-062961 turned 180° so J,J,LJ sit on the straight edge (user OK); 26-062960 (1500×70, same V-notch family) was left with marks on the notched top edge. User: why not turn 062960 too. | "Top edge" read literally as the drawing's max-Y edge; siblings not kept consistent. | J/LJ on the long straight edge; turn 180° when only the bottom edge is straight; same for sibling codes (`CAD_OUTPUT.md`, `tools/build_canonical.py`). |
| 7 | Status name: rules said "status REVIEW", exporter accepts REVIEW only for HL; flagged parts must be `PREVIEW`. | Two names for one state. | `REVIEW_PREVIEW_POLICY.md` item 0, `JOB_CARD.md` item 5. |
| 8 | Easy flat job took ~19 min; most time reading validator sources to learn the JSON contract and hand-writing fillet/chamfer/witness/J-LJ code; context compaction lost the per-code geometry. | No compact builder, no minimal example, ledger not on disk. | `tools/build_canonical.py` + `tools/run_job.py` + `examples/flat_minimal.yaml`; write ledger/spec per code to a file at once (`JOB_CARD.md` item 2); `resolve_rules.py --bundle`. |
| 9 | REVIEW banner overlapped the first code label in the composite. | Banner at stack top +12 while the label occupies +10..+20. | Banner above the label reserve (`tools/export_dxf.py`, test). |

Regression assertions (coordinates only here):
- 26-062961 corrected outline before turning: (0,0) (1720,0) (1720,70) V×8 at x=1680…280 (depth 25, 90°) (100,70) (0,65); Laser R0.5 at 3 corners; (0,65) is 92.86° → no automatic R. Turned 180°: J 30.5 / 860 / LJ 1689.5 on y=70.
- 26-062960: turned 180°, J 30.5, LJ 1469.5.
- 26-062954: 5 × R0.5 AUTO_R, 4 × C1 CALLED, 2 × R4.25 notch ends, status PASS, no FLAG.
- Spec of the corrected job builds and exports `521023-16_ALL.dxf` with all four codes PASS (`tools/run_job.py`, 0.7 s).
