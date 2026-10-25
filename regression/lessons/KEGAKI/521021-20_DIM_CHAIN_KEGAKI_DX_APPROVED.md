# 521021-20 — hole-family dimension chains, KEGAKI across the bend, dx on the back-face KEGAKI

**Status:** USER APPROVED / PUSH 2026-10-21 (customer sample `521021-20_mau.dxf` audited; sample is audit-only).

## FACT
Job 521021-20 (Meinan 851, codes 26-062288 ... 26-062295; bent t9 bracket + rib, U-bracket + plate, tube + 3 plates).

## ROOT_CAUSE (all `AI_SOURCE_SEMANTICS_ERROR`)
1. `CHAIN/BASELINE ERROR` 26-062294/062295: the 15 mm end offset of 2-M8 was applied to 4-M5; the M5 string is 204 + 13 (X = 13 and 217).
2. `FEATURE TYPE ERROR` 26-062288: a 6 mm strip (rib foot) was turned into a 6 x 65 slit cutout.
3. `KEGAKI FOOTPRINT ERROR` 26-062288: U open at the bend instead of one closed union rectangle across the bend (25 .. 84.38+9+150 = 243.38 flat, 6 wide); no chamfer at the rib foot.
4. `ORIENTATION` 26-062288 drawn rotated 90 deg instead of the plan-view frame.
5. `dx` omitted for 26-062292 / 26-062293 (KEGAKI on the back face of the drawn view).

## APPROVED LESSON (scoped)
- Each hole family traces its own dimension string and names the printed label on each witness step (`DATUM_DIMENSION.md` 4.2.4.0; the witness graph is self-consistent by construction, so the Reader names the printed dimension, e.g. "dim 204 between M5 axes", on each `proof.evidence_ref`; a row offset from another family is `DIMENSION_CHAIN_MISMATCH`).
- A thin strip in an assembly view is a child footprint, not a cutout; rib adjacent to the bend with no chamfer -> KEGAKI runs continuously across the bend line (`KEGAKI_FOOTPRINT_FROM_PDF.md` 2b, 8).
- Canonical flat frame follows the primary plan view (`BEND_UNFOLD.md`).
- KEGAKI on the drawn face -> no dx; KEGAKI on the back face of the drawn view -> `dx_label: true`, geometry unchanged (`DXF_INPUT_SCHEMA.md` dx_label; CAD_OUTPUT.md 5d unchanged: size budget). 521021-20: 26-062292 and 26-062293 carry dx; 26-062288/062294/062295 do not.
- User-confirmed reading rules: a child clearly centred in the view is centred; plate C top edge flush with the tube top is a usable chain origin (26-062295 y = 11).

## REGRESSION_CASE
`tests/test_521021_20_regression.py`.
