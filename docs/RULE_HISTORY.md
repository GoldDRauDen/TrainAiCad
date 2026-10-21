# Rule History (archived, not routed)

Verbatim archive of rule blocks removed from routed files. The Router does NOT load this file, and it is NOT production authority. It keeps provenance only. Restoring any block into a routed file requires explicit user approval (`DUYỆT`), per `AGENTS.md`.

## Superseded bend-intersection shorthand

Superseded from `skills/lispcad/features/SLIT_RELIEF.md`: "only when two perpendicular bend lines cross" and "When two outer edges fold in different directions and both outside dimensions must remain unchanged, create an R=t escape relief at their intersection". The owner now requires a source-proved physical intersection after step and bend-domain closure. Positive-step formulas are unchanged; evidence stays in regression/qa.

## Archived from skills/lispcad/core/DRAWING_READING.md

## V4.7 DXF-first output mode (approved 2026-09-26)
After executing ALL approved V4.6 drawing/material rules and real geometric verification, build ONE checked canonical part-local model. The same coordinates generate direct individual and combined DXFs and optional request-only Lisp; never independently recalculate for either. See `CAD_OUTPUT.md`. Critical missing source evidence blocks production; numeric-only uncertainty on proved topology can be Magenta non-production PREVIEW only on request. No V4.6 engineering lesson is changed by this output migration.

## Archived from skills/lispcad/core/VALIDATION.md

## Historical V4.7 saved-DXF dual-export audit (explicit-request legacy only)
Before declaring the canonical model PASS, actually execute every preceding V4.6 PDF-semantic, source/material, true contour topology, datum, feature-count, containment and bend-domain check. A serializer's structural validations cannot prove these engineering facts.
Under explicit-request **legacy V4.7 dual export** only, for EACH individual and combined DXF reopen the SAVED file and audit: real mm DXF, Layer 0 only, correct V4.6 entity/linetype/color/POINT/CIRCLE and bulges, geometry/count against the canonical source, no extra code-label TEXT. Combined drawing MUST contain exactly one translated copy of each production-PASS part, in explicitly declared code order descending Y, separated by at least 10 mm layout-only bbox clearance; record/check all offsets in the manifest. Keep numeric-only user-requested Magenta _PREVIEW outside production _ALL.dxf and do not mark preview PASS. Unknown topology/type/bend/material/datum blocks export. Count the `055958` Green LINE+ARC+LINE as ONE slit operation, not three.

## Archived 2026-10-15 (rule-load slimming; user DUYET) — verbatim, not routed

Each block was either a duplicate of text kept in a routed file, a superseded wording, or a case note whose rule remains in the routed file. Moved-not-removed content lives in `references/BEND_DATUM_MAPPING.md`, `references/ASSEMBLY_DATUM_CLOSURE.md`, `references/REFERENCE_CALIBRATION_AUDIT.md`, `references/REVIEW_PREVIEW_POLICY.md` and `regression/qa/*`.

### DATUM_DIMENSION.md V4.8 regression paragraph

## V4.8 approved datum/feature-family regression

Regression 520709-07: for 039915, OD 30 minus local step 5 gives the external step at **25**, NOT 27.36 (Nobi-adjusted bend datum) minus 5 = 22.36; the bend zone still retains Nobi 2.64. For 039918 and PDF-mirrored 039919, printed diagonal 50 (not 100) is measured to the theoretical sharp point before R10; independently identify 2-M4 and 3-Ø5 hole families by source leaders. The correct original 039918 flattened local centers (173.2,110) and (224.2,54) are respectively M4→Ø3.3 and Ø5. These examples reinforce existing dimension-endpoint and family-isolation rules; they do not create new general coordinates.

### DATUM_DIMENSION.md §4.2.7.2

User-approved 010420 Q03 documents this priority.

### DATUM_DIMENSION.md V4.34 witness

521013-21/059759 negative regression: taking 265 from the external RIGHT_EDGE rather than the RIGHT_HOLE_CENTER adds 10 mm to the group; sample/reference geometry cannot supply a missing witness.

### DATUM_DIMENSION.md §4.2.2a

- Approved 044812/044813 regression: `25` is the center distance of two `9.5×R1.75` long holes on the `28×41` face; use `28 + 21 - 3.68 = 45.32` for the proved two-face flat contribution, not `25-3.68` as a contour/bend coordinate.

### DATUM_DIMENSION.md §4.2.4

- Example pattern: if vertical dimensions `389` and `404` terminate respectively at a hole center and a step ledge, they define two different Y nodes; they are not interchangeable.

### DRAWING_READING.md top V4.18 (duplicate of §2.1.3 item 4)

## V4.18 approved 520929-18 — detailed-source bundle authority hardening

**V4.18 DETAILED_SOURCE_BUNDLE:** A Page-1/job-list row is a summary/mapping source, not an automatic override of the detailed drawing page. For the same barcode/code, when the detailed page contains a mutually consistent bundle of (a) matching code identity, (b) explicit material/thickness, (c) dimension-witnessed formed geometry, and (d) handwritten/printed Nobi or flat arithmetic that closes those dimensions, and there is no later revision/red correction/cancellation with higher authority, use that detailed bundle to resolve a contradictory summary row without asking. This is NOT a rule that “barcode page always wins”: if the detailed evidence does not close, identity is uncertain, or a higher-authority revision conflicts, FLAG/ask. In NEW_PDF_TO_DXF, a later reference DXF may verify the resolution but must not supply missing construction dimensions.

Source: inherited from the approved V4.3 baseline. Current production authority is `AI_ENTRYPOINT.md` plus the Router. This file holds drawing-reading rules, the execution pipeline and Japanese terminology.

### DRAWING_READING.md V4.13 'Already-approved rules' case refs

**Already-approved rules:** Exhaust whole slot dimension strings and verify END-CENTER versus OUTSIDE-TIP witnesses before asking; do not reintroduce routine shop-spacing approval questions (existing V4.12 §5.2). See new examples 018295/018304 and case 018297 in regression/qa/520315-18_V4_13_APPROVED.md.

### DRAWING_READING.md V4.12 para 2 (moved into REVIEW_PREVIEW_POLICY)

Before asking, exhaust explicit witness lines, handwritten Nobi, width-derived slot-end radius and local-face transforms. If the flat is independently proved, draw it even if an unrelated round-hole Ø/center is still uncertain; isolate that feature as Magenta `CIRCLE Ø?` / coordinate FLAG instead of changing its unknown Ø to POINT. Reuse existing V4.11 VIEWS_ONLY only when the actual unfold is not supportable. Do not require sample DXF for a clearly marked preview or ask for routine PDF-conforming shop-spacing acceptance. See approved regression `520217-27`.

### DRAWING_READING.md V4.11 preview-first (moved into REVIEW_PREVIEW_POLICY)

## V4.11 approved preview-first override — active

**DRAW → FLAG → CONFIRM:** If actual PDF evidence supports a recognizable approximation but a dimension, feature type or topology remains unproved, render the provisional portion Magenta (Layer 0, DXF 62=6), add an adjacent explicit assumption/FLAG and ask the user AFTER showing it. Keep every independently proved entity exact. If a defensible flat is not available, render independently proved orthographic/source views separately and label the code `VIEWS_ONLY`. The default combined DXF is `*_ALL_REVIEW_ONLY.dxf` with global **NO CUT** whenever any FLAG remains. Only absent identifiable source views or ambiguous part-code identity stops all drawing. This V4.11 preview rule overrides the inherited V4.3/V4.10 blanket STOP-before-any-drawing wording for **review-only** output; it never weakens Section 5 production PASS or allows silent geometry invention. See [QA regression](../../../regression/qa/520625-15_V4_11_APPROVED.md).

### DRAWING_READING.md V4.8

Case 040006 on 520709-07 deletes both 2-Ø8H7 while retaining 6-M8 and 4-Ø9.

### DRAWING_READING.md §0.3 (moved verbatim to REFERENCE_CALIBRATION_AUDIT)

### 0.3 Calibration / Regression Learning Protocol
When the user supplies a reference DXF or corrected CAD for PDF-interpretation calibration (NOT a specifically requested direct audit of an already created AI DXF):
1. **Interpret the PDF first** without using DXF coordinates to fill missing information.
2. Compare the independently derived geometry against the user-approved reference.
3. Classify each mismatch by semantic cause: datum, dimension-chain type, step/local dimension, feature type, C/R topology, tolerance/Nobi, or source conflict.
4. Convert only the **generalizable semantic cause** into a rule or regression test.
5. Do not encode one-off coordinates as generic rules.
6. Store validated examples as regression tests under `regression/` when they materially prevent recurrence.
7. Any future run must be able to apply those rules even when no DXF is supplied.

### VALIDATION.md duplicate of '2026-10-12 production validation precedence'

2026-10-12 CUSTOMER CAD OVERRIDE: correct source geometry can PASS with nonblocking WARN for machine L/Z/reach; customer-authorized DATA_NO_DIM_COMPARE waives only PDF/DATA dimension-only conflict, never missing or mismatched holes, topology, count or physical DATA audit. SS>=19 R3 is exterior-perimeter-only (outer contour may contain concave corners). A legible handwritten Nobi/table discrepancy is logged as audit, not a blocking FLAG.

### VALIDATION.md V4.23 reference anomaly (now in REFERENCE_CALIBRATION_AUDIT)

When a user-approved sample contains exact coincident duplicates, normalize them for physical comparison and report `REFERENCE_ANOMALY`; never promote duplicate entity count into physical feature quantity.

### VALIDATION.md V4.13 independent checks (units/tolerance -> REFERENCE_CALIBRATION_AUDIT; mirror/Nobi duplicated in DRAWING_READING and §2026-10-12)

## V4.13 approved 520315-18 independent checks

- Before comparing a reference DXF, reconcile $INSUNITS metadata with independently established PDF/user-confirmed actual numeric units. If contradictory and unresolved, FLAG SOURCE_UNIT_CONFLICT; do not automatically scale by 25.4. Output DXF remains mm, $INSUNITS=4.
- Treat original and mirrored drawing CODES as separate records. A mirror requires an established original/target relation, axis and feature scope, including actual holes/slots/R/C/bends, then independent count/containment validation. When inner formed faces are shown, assemble the proved INSIDE_VIEW first, apply only the evidenced reflection and compare hole family/center only in a shared final frame.
- If bend J, legible handwritten Nobi and a genuinely comparable table row ALL exist, draw with N_hand and record HANDWRITTEN_NOBI_DIFFERS_FROM_TABLE as a nonblocking audit note when the prescribed values disagree. Comparing a 165° note to a 90° table is an invalid conflict; no compatible row does not override handwriting.
- EXACT printed PDF inputs never receive a comparison tolerance. Only absolute differences strictly <0.01 mm caused by internal precision/rounding in an already-correct DERIVED result can pass an arithmetic-only comparison with reference DXF. Exactly 0.01 fails this test. This does not waive feature/datum/topology/bend/manufacturing checks. V4.12 already prohibits routine shop-spacing customer approval questions; do not duplicate that rule.


Source: approved V4.3 production baseline.

### VALIDATION.md V4.11 PREVIEW (now REVIEW_PREVIEW_POLICY)

## V4.11 PREVIEW vs production validation — active

The user approved **DRAW → FLAG → CONFIRM**: draw a reasonable PDF-supported provisional shape in Magenta with adjacent assumptions, or separate independently proved source/orthographic views when no defensible flat is possible; ask targeted questions after drawing. Record uncertain type/topology/size/datum as `FLAGGED` and mark such parts `PREVIEW` or `VIEWS_ONLY`, never `PASS`. Any such part makes the entire default composite `*_ALL_REVIEW_ONLY.dxf` / **NO CUT**. A previous user QA PASS on a delivered file does not certify any later changed file. The original Section 5 geometry, datum, counts, containment, material and bend-domain production gates remain fully mandatory once uncertainties are resolved. The earlier 'numeric-only Magenta' restriction is historical for previews but remains superseded by this user-approved review-only rule. See [approved regression](../../../regression/qa/520625-15_V4_11_APPROVED.md).

### VALIDATION.md V4.8 case sentence

Apply approved regression/datum/520709-07_APPROVED.md for 039915 external-step datum, 039918/039919 diagonal/hole family and full reflection, and 040006 deletion of the complete 2-Ø8H7 family with active 6-M8 and 4-Ø9 retained.

### VALIDATION.md DETAILED_SOURCE_BUNDLE check (duplicate of DRAWING_READING §2.1)

- **V4.18 DETAILED_SOURCE_BUNDLE conflict check:** When a job-list/summary row conflicts with the same-code detailed page, record whether the detailed page independently closes identity, explicit material/thickness, dimension-witnessed geometry, and Nobi/flat arithmetic, and verify there is no higher-authority revision/red correction/cancellation. Only a closed bundle resolves the summary conflict automatically; otherwise FLAG/ask. A reference DXF cannot be used as the missing input in NEW_PDF_TO_DXF.

### VALIDATION.md Reference DXF Comparison Check (now REFERENCE_CALIBRATION_AUDIT)

- **Reference DXF Comparison Check**: When `DRAWING_READING.md` §2.4 is active, compare feature coordinates and topology against the master DXF after PDF interpretation. First apply the approved material-table automatic Laser R rule for eligible corners; do not exclude matching DXF-only R0.5/R2 simply because PDF omitted the callout. Only explicitly approved downstream shop-only differences may be excluded.

### VALIDATION.md 055958 bullet

- **Connected primitives are not separate manufacturing features (approved `055958` regression)**: Count by proved topology, actual manufacturing operation, and endpoint connectivity, **not** by the number of same-colored DXF LINE/ARC entities. One approved `055958` `BEND_UNFOLD.md` §4.10 slit contains Green `LINE 55A` + `ARC 55B R0.5` + `LINE 55C`, which meet at their endpoints: feature count **1**, constituent entity count **3**. Common color alone does not prove that unrelated entities form one feature. The local R0.5 in this specific case is not a universal requirement of all slit reliefs. Remove only this slit method/count FLAG; independently uncertain customer sizes/datum still FLAG.

### VALIDATION.md V4.9/V4.10 output precedence + V4.14 direct audit (superseded/duplicated; audit now in REFERENCE_CALIBRATION_AUDIT)

## V4.9/V4.10 current output precedence

Default output is **ONE** top-to-bottom code-labeled composite, or `_ALL_REVIEW_ONLY.dxf` with all source-view groups/FLAGs and global NO CUT when any code is not independently production PASS. Exclude `AI_META` non-cut labels from the Layer-0 manufacturing audit. The historical V4.7 dual-export section above does NOT require default individual DXFs or manifest. The V4.10 source-origin/axis check in Section 5.1 is mandatory upstream BEFORE a production PASS or composite entity serialization.

### V4.14 direct existing-output audit and overlapping-cut QA

When explicitly asked to compare a PREVIOUSLY EXPORTED AI DXF with a user-approved reference, compare **AI DXF vs reference DXF FIRST**, not PDF vs sample. Normalize only independently proved source-unit interpretation, source orientation and layout translations; compare actual machining curves, typed hole/slot families and original source-callout counts, cut unions, complete unfold coordinates, all bend-pair coordinates and bend-line clipping to material. Geometric identity accepts ARC+LINE versus equivalent exact closed LWPOLYLINE/bulge; raw entity counts are not semantic feature counts. A partial source/orthographic view does not pass against a reference completed flat. Classify MATCH/PARTIAL/DIFF per code and test originally matched codes again after any rebuild. THEN inspect PDF to diagnose mismatches; independent PDF-FIRST interpretation remains the creation procedure. For truly overlapping cut holes require one non-self-intersecting Boolean-union contour and separate family quantity closure, rather than several overlapping interior cut circles. Strict `<0.01 mm` arithmetic residual is permitted ONLY for already-correct derived values per existing V4.13; every PRINTED source number remains exact. Six-code test: `regression/qa/520217-26_V4_14_APPROVED.md`.

### VALIDATION.md V4.17

The 520929-10 regression specifically fails W10/R5 where source/sample proves W9/R4.5.

### VALIDATION.md V4.17

Regression: H32 and top-edge-to-center 10 => bottom-origin Y22.

### VALIDATION.md REFERENCE_METADATA_NONBLOCKING (now REFERENCE_CALIBRATION_AUDIT)

- **REFERENCE_METADATA_NONBLOCKING:** for approved-reference audits, a conflicting `$INSUNITS` header does not by itself fail physical geometry once actual numeric units are independently proved from source/user/reference scale. Do not apply 25.4 scaling from metadata alone. Production exports still follow the normal mm metadata rule.

### CAD_OUTPUT.md V4.33 VIEWS_ONLY output gate (now REVIEW_PREVIEW_POLICY)

# V4.33 VIEWS_ONLY completeness / reference provenance output gate

When a flat truly remains unresolved after source exhaustion and `HOLISTIC_ENGINEERING_CHALLENGE`, `VIEWS_ONLY` is an executable review output, not a report-only status. Preserve all independently proved source/orthographic view members as separate labeled subgroups under the correct code. For customer DATA, preserve the physical source curves unless an approved manufacturing canonicalization explicitly changes them. Missing proved source-view members is `VIEWS_ONLY_SOURCE_VIEW_COMPLETENESS` FAIL.

A local unresolved feature does not erase an independently proved flat; output the proved flat and isolate the local FLAG/PREVIEW.

If a sample/reference is introduced later, output/audit reporting must preserve the frozen source-only status. Sample FLAG/Magenta geometry declared pending is `CUSTOMER_CONFIRMATION_PENDING`, not approved manufacturing geometry.

### CAD_OUTPUT.md V4.12 local-FLAG / V4.11 provisional clusters / V4.9 packaging / V4.8 gate (now REVIEW_PREVIEW_POLICY and packaging section)

## V4.12 approved local-FLAG precedence

Keep a source-proved flat even when a separate round-hole Ø or center awaits confirmation: represent only the unresolved hole dimension/position with Magenta `CIRCLE` and adjacent `Ø?`/coordinate FLAG. Never make an unknown Ø a guessed capacity POINT. Use the existing V4.11 separate labeled source views only if no defensible flat/unfold order exists. No PREVIEW can be called production PASS; the entire mixed-confidence composite stays `REVIEW ONLY — NO CUT`. Routine shop bridge/spacing/bend-proximity acceptance questions are suppressed, without weakening actual geometric containment, source tracing or material-capacity checks.

## V4.11 approved non-production provisional clusters

The default remains exactly ONE top-to-bottom code-labeled DXF. When a drawing supports a plausible but not fully proved shape, retain exact confirmed geometry and include the assumed portion in **Magenta Layer-0** with an adjacent Magenta explanatory FLAG; label the code `PREVIEW`. Truly estimated numeric values are integer-rounded. If the flat shape or bend sequence cannot be inferred responsibly, include independently proved source/orthographic views as **separate labeled subgroups** under that code and mark `VIEWS_ONLY`; do not silently omit it. Any estimate or unresolved view makes the entire combined file `*_ALL_REVIEW_ONLY.dxf` with **NO CUT**. Explicit user QA confirmation closes only its specific resolved question, and later changes require full Section 5 and saved-DXF validation. This V4.11 approval supersedes previous **numeric-only preview** constraints for non-production output, not production shape/type/datum requirements. See portable §4.4.1 and [520625-15 approved regression](../../../regression/qa/520625-15_V4_11_APPROVED.md).

**Current V4.9 user-approved packaging:** ONE top-to-bottom composite DXF, with exact code labels outside each nonoverlapping part cluster; per-code files and manifest only by explicit request. Incomplete flats remain source-view groups under the correct code; any FLAG makes the entire combined file `REVIEW_ONLY - NO CUT`. This changes only packaging, not the V4.8-approved or earlier manufacturing rules. AutoLISP remains explicit-request only.

**V4.8 upstream gate:** Write canceled source-family provenance and effective zero-count into canonical job trace, omit all deleted hole entities, and verify that the deleted group is also absent in the translated composite. No CAD serialization or DXF schema change; only user-confirmed PDF reading, counts and regression cases were approved.

### CAD_OUTPUT.md 8.3 (review text now REVIEW_PREVIEW_POLICY; layout in rule 6)

## 8.3 V4.9 mandatory single composite

Default **one DXF only**: `<JOB>_ALL.dxf` if every code has independent manufacturing PASS; otherwise `<JOB>_ALL_REVIEW_ONLY.dxf` including all codes and visible **NO CUT** annotation. Individual DXFs/manifest are NOT default and require explicit request. Preserve Stage 1 per-code status/report without delivering unnecessary individual CAD files.

Use the declared page-1 code order strictly top-to-bottom, with >=10 mm **layout-only** clearance between part/view-group geometry bboxes, no overlaps and no geometric rescaling. Every code appears exactly once beside its own cluster as generated `TEXT` on non-plot `AI_META`, not as a Layer-0 cut path. Internally record code, status, bbox, XY translation, flags and per-code machining entity counts even when the user did not request an external manifest.

For known-topology numeric-only uncertainty: preserve all proved sizes and positions, isolate an integer-rounded Magenta estimate plus adjacent Magenta FLAG note. For unknown unfold dimensions/order: output only independently proved orthographic/source views, grouped and labeled by source view under the correct code (`VIEWS_ONLY`), never a fabricated flat. If a temporary Ø is user-authorized, label it `Ø?` and treat it as review-only, not a verified hole. If there is not enough evidence even to draw a source view or assign the correct code, STOP and ask.

A single unresolved `PREVIEW`/`VIEWS_ONLY`/FLAG invalidates *production use of the entire composite*, even if other part clusters are individually correct. An explicitly requested legacy dual export may be supplied for compatible jobs but never silently substituted for the V4.9 default.

### CAD_OUTPUT.md V4.14 equivalence (duplicate of REFERENCE_CALIBRATION_AUDIT §2.4.2b)

### V4.14 physical-geometry equivalence when auditing user DXF

An audit of already generated AI CAD against a declared customer-reference CAD compares actual manufactured curves after verified unit/part-local-frame normalization; equivalent LINE+ARC versus closed LWPOLYLINE with true bulges need NOT have identical entity types or raw entity totals. However, prove exactly matching contour topology, source family membership/counts and positions, radius/chamfer geometry, the complete unfolded part and each true bend pair clipped to material. Regression-match parts remain invariant before/after repacking and any corrections elsewhere. For NEW production DXF, the current canonical Layer-0 export contract and mandatory independent PDF/validation checks remain unchanged.


## Completed consolidation decisions

The completed SLIM_MAPPING and GATE_REVIEW records are retained at baseline commit `65bf258bed380a4389aa91fe6f91f28cf2242ff4` under `docs/SLIM_MAPPING.md` and `docs/GATE_REVIEW.md`. They are historical evidence, not pending approval or production authority.

- Slimming was applied on 2026-10-14: AI_ENTRYPOINT 20,864→13,290 bytes and SKILL 8,523→5,991 bytes at that checkpoint; do not report these old reductions as a new result. Rule ownership was checked sentence by sentence before replacing prose with pointers.
- Approved gate classification: Group A plus NEAREST_VIEW_EDGE are gates; THICKNESS_SINGLE_USE, RAW_DATA_SNAPSHOT, PHYSICAL_DATA_BASELINE and DATA_PDF_DIM_DIFF are gates. Use full FOLD_BACK_SOURCE_REPROJECTION instead of FOLD_BACK. DATA_NO_DIM_COMPARE stays a customer policy, not a gate. Groups B/C are non-gate statuses/geometry/mechanisms/files. The executable classified lists remain in tools/build_gate_index.py.
- Identifier overlap was only a discovery filter, never proof of semantic parity.

## Superseded 2026-10-21 — Nobi fallback (user decision: split flange 10 mm; t not tabulated = FLAG)

Replaced by `BEND_UNFOLD.md` §4.7 and `tools/lookup.py nobi`. Old OD-fallback, separate-views fallback for non-90° bends and next-higher-thickness rule are no longer active.

### 4.7 Nobi (Bend Allowance) Lookup Priority & Sequential Formulas

**2026-10-12 clarification:** If no defensible Nobi exists for a non-90° bend, preserve separate source/orthographic views under local REVIEW so the operator can assemble after customer confirmation. Never insert a 90° table value. KH646 is its own numeric customer-code route. Legible handwritten PDF Nobi overrides a differing table number with a nonblocking audit record.


1. **Handwritten Nobi on Drawing**: Highest priority. Use directly (e.g., `-4.8`, `135° -1.71`) regardless of J-symbol.
2. **No Handwritten Nobi + J-Symbol Present**: Look up Nobi from standard tables (Section 7.3) by Material, Thickness, Bend Length, and Angle — applying the Interpolation Rule in Section 4.8 when the exact value is not tabulated.
3. **No Handwritten Nobi + J-Symbol Absent**: Draw the affected flange as a separate piece detached from the main body, offset by a fixed `10 mm` gap for downstream reassembly. Set `is_flagged = true`.
4. **J-Symbol Present + No Table Match** (including out-of-range per Section 4.8): Maintain flat blank at Outside Dimension (OD) and draw bend line at OD design position. Set `is_flagged = true`.

#### 4.8 Nobi Table Interpolation Rule (NEW — Conservative Round-Up, Shop-Practice Standard)
When the actual Thickness (`t`) or Bend Length (`L`) does **not** exactly match a row in Section 7.3, do **NOT** interpolate numerically. Instead:
- **Thickness mismatch**: Select the row with the **next higher tabulated t** (never round down). Rounding down risks selecting an undersized V-die opening for the actual material, risking cracking or improper die seating.
- **Bend Length mismatch**: Within the selected `t` row group, select the **next higher L bracket** (next larger V-die). This yields a conservative (larger) Nobi deduction, which errs toward tooling safety.
- **Out-of-Range**: If `t` or `L` exceeds the largest tabulated value for that material, do not guess. Set `is_flagged = true` and annotate `"OUT OF TABLE RANGE - CONFIRM NOBI WITH SHOP"` in Magenta (Color 6) per Section 4.4.
- This rule applies uniformly across all four material tables in Section 7.3.


**Handwritten/J mismatch audit:** Existing Rule 1 always draws with scoped legible N_hand, including bends marked J. Only if the approved table supplies a genuinely compatible N_table for the SAME material, thickness, bend length, angle and applicable surface state, record both and retain HANDWRITTEN_NOBI_DIFFERS_FROM_TABLE only as a nonblocking audit note if prescribed values differ. Do not borrow a 90° table row for a 165° bend; if the table has no match, never replace a proved handwritten Nobi with an OD fallback.

