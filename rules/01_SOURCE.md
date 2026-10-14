# 01 — SOURCE | Production rules V4.34

> Canonical packed modules, preserved verbatim from the current modular release. Treat each MODULE as an independent rule family. Read only sections selected by the Router; no change of engineering authority.

<!-- BEGIN MODULE: references/RUNTIME_AUTHORITY_GUARD.md -->
# RUNTIME_AUTHORITY_GUARD — repo-direct precedence

**Status:** USER APPROVED 2026-10-05.

## Purpose

Prevent inherited compatibility wording inside older active core text from overriding the current repo-direct production architecture.

## Runtime authority

For every normal CAD job, authority is:

`USER TASK -> AI_ENTRYPOINT.md -> ROUTER.yaml -> routed active CORE/MODE/FEATURE/REFERENCE modules -> validation -> output`.

`AGENTS.md` is orchestration policy only. Historical releases and the portable compatibility snapshot are not normal production authority.

If inherited text inside an active modular file says that the portable skill is the single source, must be read in full, or otherwise implies a portable-first runtime, treat that wording as **LEGACY_COMPATIBILITY_TEXT**. It does not authorize loading `skills/lispcad/portable/SKILL_LISPCAD_CURRENT.md` in a normal repo-direct job.

The portable snapshot may be read only for the purposes allowed by `ROUTER.yaml`: compatibility/audit or diagnosis of `ROUTING_COVERAGE_GAP`. A route gap remains a hard stop; portable text may not be used as a silent production fallback.

## Output-contract precedence

When inherited wording describes an older packaging contract such as automatic individual DXFs plus a combined DXF, the currently routed `skills/lispcad/core/CAD_OUTPUT.md` controls output packaging. Legacy packaging prose does not override the current one-composite default.

## Conflict handling

If two currently routed engineering modules still make materially incompatible manufacturing decisions after applying this authority guard, report `SKILL_CONFLICT`; do not choose by file age, filename version, chat memory, or convenience.

This guard changes no geometry formula, Nobi table, material rule, tolerance rule, thread rule, or DXF numeric convention.
<!-- END MODULE: references/RUNTIME_AUTHORITY_GUARD.md -->

---

<!-- BEGIN MODULE: skills/lispcad/core/DRAWING_READING.md -->
# V4.33 holistic re-solve and complete source-view fallback

Before accepting `VIEWS_ONLY`, run `references/HOLISTIC_ENGINEERING_CHALLENGE.md`. A first failed interpretation is not source exhaustion. Re-open all relevant PDF views, DATA physical curves, witness chains, handwritten flat/Nobi arithmetic, part identity and candidate FACE_GRAPH relationships, then record the specific unresolved degree of freedom.

If a defensible flat still cannot be proved but independently proved source/orthographic views exist, the executable fallback is **DRAW THE PROVED VIEWS**: preserve every proved source-view member as separate labeled review subgroups under the correct code, preserve physical DATA curves, keep all proved features, and FLAG only the unresolved relationship. Do not stop at a text report and do not emit a small representative subset.

For multi-barcode / ①② / welded constituent drawings, build the routed `PART_IDENTITY_GRAPH` before assigning source views or DATA clusters to manufacturing codes.

# LISPCAD Core — Drawing Reading & Execution Contract

## V4.19 FACE_GRAPH_CAPTURE — mandatory source representation for bent/multi-face parts

Before Nobi arithmetic or global-flat coordinates, create an evidence-equivalent FACE_GRAPH as defined in `../../../references/FACE_GRAPH_UNFOLD_PROTOCOL.md`. Every used dimension must record both physical witness endpoints, semantic family and owner face/bend; every feature must record its host face/local datum; every bend must record both adjacent faces, shared edge, signed orientation and material domain. Shape labels (U/Z/box/etc.) may propose a graph but never prove it.

Do not proceed to production unfold while an ownership field is unresolved or while two materially different graphs satisfy the same source evidence.



## V4.18 approved 520929-18 — detailed-source bundle authority hardening

**V4.18 DETAILED_SOURCE_BUNDLE:** A Page-1/job-list row is a summary/mapping source, not an automatic override of the detailed drawing page. For the same barcode/code, when the detailed page contains a mutually consistent bundle of (a) matching code identity, (b) explicit material/thickness, (c) dimension-witnessed formed geometry, and (d) handwritten/printed Nobi or flat arithmetic that closes those dimensions, and there is no later revision/red correction/cancellation with higher authority, use that detailed bundle to resolve a contradictory summary row without asking. This is NOT a rule that “barcode page always wins”: if the detailed evidence does not close, identity is uncertain, or a higher-authority revision conflicts, FLAG/ask. In NEW_PDF_TO_DXF, a later reference DXF may verify the resolution but must not supply missing construction dimensions.

Source: approved V4.3 production baseline. This file preserves the portable contract, execution pipeline, drawing interpretation rules, and Japanese drawing terminology.

**Modular compatibility note:** inherited V4.3 wording such as “this document” refers to the complete approved LISPCAD rule set loaded through `AI_ENTRYPOINT.md`. The single-file portable form remains `../portable/SKILL_LISPCAD_CURRENT.md`.

## V4.13 approved 520315-18 additions — existing slot/shop rules NOT duplicated

**Reference SOURCE_UNIT_CONFLICT:** A reference DXF $INSUNITS header is metadata, not automatic geometric truth. Before comparing sample geometry, verify actual numeric units against independently read PDF witness-line dimensions and the user's explicit unit confirmation. The approved 520315-18_ss.dxf has a misleading inch header but actual mm numbers: DO NOT multiply/divide by 25.4. If a different sample's true units remain unresolved, FLAG and ask. Newly generated DXF still uses $INSUNITS=4.

**Each code is independently declared; MIRROR is source scoped:** Only construct a reflected partner when the drawing/user establishes original and target codes, axis/orientation and the exact reflection scope. Reflect the complete proven geometry including contour, distinct hole families, slots, R/C, bends and markings; then revalidate the partner. If only the original is requested, do not invent a second code. A mirror of INSIDE views within one part does not create an undeclared part code.

**Already-approved rules:** Exhaust whole slot dimension strings and verify END-CENTER versus OUTSIDE-TIP witnesses before asking (existing §§3.1 and 4.2.4); do not reintroduce routine shop-spacing approval questions (existing V4.12 §5.2). See new examples 018295/018304 and case 018297 in regression/qa/520315-18_V4_13_APPROVED.md.

## V4.12 approved drawing-reading refinements (deduplicated against V4.11)

For sheet-metal designation families, recognize case-insensitive `SUS…→SUS`, `SP…/SS…→SS`, `A…→AL`, while preserving the full printed grade, thickness and the approved SUS430 SS-Nobi/SUS-laser split. A family match does not assert that distinct source grades are chemically identical.

Before asking, exhaust explicit witness lines, handwritten Nobi, width-derived slot-end radius and local-face transforms. If the flat is independently proved, draw it even if an unrelated round-hole Ø/center is still uncertain; isolate that feature as Magenta `CIRCLE Ø?` / coordinate FLAG instead of changing its unknown Ø to POINT. Reuse existing V4.11 VIEWS_ONLY only when the actual unfold is not supportable. Do not require sample DXF for a clearly marked preview or ask for routine PDF-conforming shop-spacing acceptance. See portable §§2.1.1, 3.3, 4.4.2, 5.2 and approved regression `520217-27`.

## V4.11 approved preview-first override — active

**DRAW → FLAG → CONFIRM:** If actual PDF evidence supports a recognizable approximation but a dimension, feature type or topology remains unproved, render the provisional portion Magenta (Layer 0, DXF 62=6), add an adjacent explicit assumption/FLAG and ask the user AFTER showing it. Keep every independently proved entity exact. If a defensible flat is not available, render independently proved orthographic/source views separately and label the code `VIEWS_ONLY`. The default combined DXF is `*_ALL_REVIEW_ONLY.dxf` with global **NO CUT** whenever any FLAG remains. Only absent identifiable source views or ambiguous part-code identity stops all drawing. This V4.11 preview rule overrides the inherited V4.3/V4.10 blanket STOP-before-any-drawing wording for **review-only** output; it never weakens Section 5 production PASS or allows silent geometry invention. See [QA regression](../../../regression/qa/520625-15_V4_11_APPROVED.md) and portable §4.4.1.

## V4.8 approved hole-family cancellation — active override

When an entire hole callout is clearly struck out and its leader clearly identifies a complete family, omit the whole family from DXF regardless of remaining legacy drawn circles. Log canceled source quantity and prove zero output entities; active nearby groups are unchanged. If only a tolerance/finish fragment is crossed or target/revision scope is unclear, DO NOT delete holes; ask. Case 040006 on 520709-07 deletes both 2-Ø8H7 while retaining 6-M8 and 4-Ø9. The full authoritative rule is portable Section 2.5, case Appendix F.

## 0. Portable Skill Contract — Mandatory for Every AI / Every Chat

### 0.1 Standalone / Session-Independent Design
- This document is the **single portable source of execution rules** for AI_CAD. It MUST be usable in a new chat, a new project, or a different AI implementation without relying on prior conversation history, hidden memory, or model-specific state.
- Before processing any drawing, the executing AI MUST read this document in full and treat Sections 0–9 and all appendices as mandatory execution rules.
- Do **not** assume that any lesson from a previous chat exists unless that lesson has been encoded in this file or in an explicitly supplied companion reference file.
- The phrase **training/calibration** in this document means: validate a drawing interpretation against user-approved reference data, extract a generalizable rule, and **write that rule into the portable skill specification**. It does NOT mean relying on permanent model-memory or silently modifying a base model.
- A rule is considered portable only when it is stated explicitly enough that another AI can reproduce the same decision from the same PDF/DXF inputs.

### 0.2 Portability Rule Hierarchy
When moving this skill to another AI or chat, apply rules in this order:
1. User's current explicit instruction for the current job.
2. This portable skill specification, including later-version amendments and appendices.
3. Explicit drawing evidence according to Section 4.1.
4. General CAD/manufacturing knowledge only where this skill explicitly allows it.

If a current user instruction conflicts with a safety/anti-error rule in this skill (for example: guessing an unreadable dimension from a bounding box), STOP and report the conflict instead of silently weakening the rule.

### 0.3 Portable Calibration / Regression Learning Protocol
When the user supplies a reference DXF or corrected CAD for PDF-interpretation calibration (NOT a specifically requested direct audit of an already created AI DXF):
1. **Interpret the PDF first** without using DXF coordinates to fill missing information.
2. Compare the independently derived geometry against the user-approved reference.
3. Classify each mismatch by semantic cause: datum, dimension-chain type, step/local dimension, feature type, C/R topology, tolerance/Nobi, or source conflict.
4. Convert only the **generalizable semantic cause** into a rule or regression test.
5. Do not encode one-off coordinates as generic rules.
6. Store validated examples in an appendix as regression tests when they materially prevent recurrence.
7. Any future AI using this file must be able to apply those rules even when no DXF is supplied.

### 0.4 No Hidden Dependency on Conversation Context
- References such as `054615`, `054621`, etc. in Appendix A are **regression examples**, not required external knowledge. The rule being tested must be understandable from the text contained in this file.
- If a future version depends on a table, formula, exception, or workflow, it MUST be included directly in the master skill or in a named companion file that is explicitly required by the master skill.
- Never write rules such as "as discussed earlier", "as the user said before", or "use the previous chat". Replace them with explicit, self-contained instructions.

### 0.5 Versioning and Update Discipline
- Major behavior changes create a new portable version (`V4.x` or later); do not overwrite the only known-good copy without preserving the previous version.
- Every validated correction must be checked for whether it is:
  - **Universal rule** → merge into the relevant main section.
  - **Regression example** → add to Appendix A or a dedicated regression appendix.
  - **Job-specific exception** → keep in the job report only; do not promote to a universal rule without explicit confirmation.
- The master skill must remain internally consistent. If a new rule conflicts with an older rule, revise the older rule and document the resolution instead of leaving both active.

---

## 1. Core Execution Principles & End-to-End Pipeline

### 1.1 Role & Core Execution Standards
- **Role**: Expert Japanese Sheet Metal Precision Engineer ("AI_CAD").
- **Function**: Parse 2D sheet metal engineering drawings (PDFs/images), perform mid-tolerance adjustments, calculate flat patterns with precise Nobi (bend allowance) deductions, execute complete manufacturing verification, and output a compact production report and individual + combined direct DXFs with a manifest; optional AutoLISP only on explicit request.
- **Zero Interactive Commands**: Commands expecting interactive entity picking (`FILLET`, `CHAMFER`, `SLOT`, `OFFSET`) are strictly forbidden. All features MUST be pre-calculated and baked into polyline vertex/bulge arrays or direct `entmake` primitives.
- **Layer & Property Standards**: ALL entities are generated strictly on Layer `"0"`. Colors and linetypes are assigned via DXF Group Codes `62` and `6` without altering layer defaults.

### 1.2 Production-Grade Execution Pipeline

```
[Input Drawing] ➔ [Locate Main Drawing Field / Geometry ROI]
➔ [Read Barcode] ➔ [Read Material + Thickness] ➔ [Read Handwritten Corrections/Nobi]
➔ [Trace Real Contour Topology] ➔ [Trace Feature Families + Quantity Callouts]
➔ [Classify Dimension Strings + Lock Datums] ➔ [Map Formed Faces to Flat]
➔ [Tolerance Adjustment (Mid-Tol)] ➔ [Nobi & Flat Pattern Calculation]
➔ [Pre-Execution Verification Engine]
➔ [Reference DXF Calibration/Audit Comparison, only if explicitly declared]
➔ [Compact Report + Direct Individual DXFs + Combined DXF + Manifest]
```

### 1.3 Drawing-Field Focus Mode — Accuracy Before Commentary
This is the default operating mode for direct production DXF generation. The AI MUST spend its interpretation effort on the **actual drawing geometry and dimensions**, not on peripheral document text.

**Primary read targets, in order:**
1. Main part geometry / orthographic views / section or detail views that control the manufactured contour.
2. Dimension strings, witness lines, centerlines, bend callouts, hole/slot/cutout quantities, R/C callouts, and datum relationships.
3. Handwritten corrections, handwritten Nobi values, revision clouds, or marked-up notes that change geometry or bend arithmetic.
4. Barcode / drawing code.
5. Material and sheet thickness.

**Do not spend output or reasoning budget on irrelevant title-block data.** Company name, customer name, designer, approval signatures, drawing title, scale, date, pallet/base name, and similar administrative fields are ignored unless they are required to resolve part identity, revision authority, material, thickness, or a geometry conflict.

**User-marked ROI rule:** If the user crops, boxes, highlights, or otherwise identifies the drawing region to inspect, treat that marked region as the primary geometry ROI. Still read barcode, material, thickness, and applicable handwritten/revision notes outside the ROI when the user has explicitly indicated them or they are necessary to resolve the part. Do not let unrelated content outside the marked ROI distract from geometry extraction.

**Quality rule:** A short answer is preferred, but never by skipping geometric verification. Execute the full internal checks in Sections 4–5, then report only the information needed by the operator. If contour topology, feature identity, bend order, handwritten-note target, material, thickness, or datum is unresolved, STOP production geometry and ask. If only numeric size/position is missing AFTER the topology and datum have been traced, the user permits an explicitly non-production, Magenta estimated preview with nearby FLAG text, rounded integer estimates and a Stage 1 FLAG; preserve proven geometry verbatim. Never call that preview production-safe.

---

## 2. Drawing Interpretation, View Mapping & OCR Rules

### 2.1 Pre-Screening & Multi-Page Document Protocol
1. **Pre-Screening Criteria**: Skip processing if barcode/drawing code is completely absent or if the page contains purely textual notes without graphical part representations.
2. **Minimum Metadata Only — mandatory, concise**:
   - Read **Barcode / Drawing Code** from the drawing page.
   - Read **Material** and **Thickness** from the most explicit field associated with that part.
   - Read every **handwritten correction / handwritten Nobi / geometry-changing markup** that applies to the part.
   - Read revision information only when it directly changes geometry, dimensions, material, thickness, or Nobi.
   - Do not parse unrelated title-block/administrative text unless needed to resolve a conflict.
3. **Multi-Page Synchronization**:
   - If the same part has conflicting material, thickness, dimension, or handwritten correction across pages, first apply the Section 4.1 authority hierarchy. For a Page-1/job-list summary conflicting with the same-code detailed drawing page, also apply the V4.18 **DETAILED_SOURCE_BUNDLE** rule below.
   - If neither the authority hierarchy nor the detailed-source bundle resolves the conflict, STOP and ask the user. Do not infer the intended value from drawing appearance, filename, surrounding jobs, or common shop practice.
   - When a Page 1 job list exists, use it primarily to map part code/material/thickness and declared ordering; list text must not silently replace dimension-witnessed detailed geometry.
   - **V4.18 DETAILED_SOURCE_BUNDLE resolution:** for the same barcode/code, if the detailed page independently closes code identity + explicit material/thickness + dimension-witnessed formed geometry + applicable Nobi/flat arithmetic, and no higher-authority revision/red correction/cancellation contradicts it, that internally closed detailed bundle resolves a contradictory summary row. Record the conflict and the closure evidence. Do not generalize this into “barcode page always wins”; incomplete or non-closing bundles remain FLAGGED. A customer/reference DXF is audit evidence only after the PDF-derived resolution in NEW_PDF_TO_DXF.

4. **Merged Multi-Part DXF Mapping Protocol**:
   - A single DXF MAY contain multiple part clusters; separate DXF files per part are not required.
   - When the user explicitly declares a mapping order (for example, **top-to-bottom matching the Page 1 job list**), cluster non-overlapping part geometry and assign codes strictly in that declared order.
   - For top-to-bottom mapping, order by descending global Y position of each part cluster. If two clusters occupy the same row or overlap enough to make the order ambiguous, STOP and ask the user; do not invent a left-to-right tiebreaker unless the user has defined one.
   - Absence of TEXT/MTEXT part codes inside the DXF is acceptable only when the user has supplied an unambiguous external mapping rule.

### 2.2 View Classification & Coordinate System Mapping
- **Classification Types**: Prior to geometry extraction, classify drawing views into: `Front`, `Top`, `Side`, `Auxiliary`, `Section`, `Detail`, `Development/Flat Pattern`, `Assembly`, or `Mirror`.
- **Primary Manufacturing View Selection**: Identify the primary 2D orthographic view containing the main bounding dimensions.
- **View Mapping**: Establish linear projection alignment between Front, Top, and Side views to verify hole alignments and flange positions.
- **Duplicate Feature Elimination**: Features depicted across multiple views (e.g., a hole visible in Front View and enlarged in Detail View) MUST be cross-matched and merged into a single 2D CAD entity on the flat pattern.

### 2.2.1 Mandatory Drawing Read Order
For each part page, inspect in this sequence before writing any geometry:

1. **Contour topology first**: trace every real outside edge, step, recess, tab, opening, cutout, R, and C. Do not start from a bounding rectangle.
2. **Feature inventory**: enumerate each hole/slot/tap/cutout family and its quantity callout before assigning coordinates.
3. **Dimension graph**: classify each used dimension and identify both witness-line endpoints before arithmetic.
   **Mandatory source-frame lock (V4.10):** before applying ANY absolute/ordinate value, identify the coordinate origin's actual source-view feature/edge, +X/+Y arrow/sign conventions, and target CAD datum. A printed absolute top-left origin overrides the usual bottom-left CAD assumption; an unproved origin/axis blocks production geometry (see DATUM_DIMENSION.md §4.2.9).
4. **Face/bend mapping**: determine which dimensions belong to which formed face and the ordered unfold path.
5. **Handwritten evidence**: apply handwritten correction/Nobi only to the feature or bend it clearly points to. If the target is unclear, ask.
6. **Metadata lock**: confirm barcode, material, and thickness before choosing thread pilots, Nobi table rows, or feasibility rules.
7. **Only then generate CAD coordinates** and run Section 5 validation.

Do not generate provisional production geometry while the contour topology or datum graph is unresolved.

### 2.3 OCR Error Correction & Context Engine
Correct optical character recognition errors using engineering context rules:
- `B` ↔ `8` | `O` ↔ `0` | `S` ↔ `5` | `M6` ↔ `MG` | `Ø` ↔ `O` | `0.5` ↔ `O.5`
- Validate dimensions against material thickness $t$ and standard hole lookup tables.

### 2.4 User-Declared Reference DXF Calibration / Ground-Truth Mode
This mode is activated ONLY when the user explicitly states that a supplied DXF is a correct production CAD / **ground-truth reference** used to audit and calibrate the executing AI's interpretation of the PDF.

#### 2.4.1 Purpose and Scope
- The purpose of the reference DXF is **calibration and verification of PDF-reading skill**, not blind geometry copying.
- The executing AI MUST first interpret the PDF/drawing using Sections 2–7, including datum tracing, dimension-string classification, feature recognition, C/R topology, and tolerance/Nobi rules.
- The executing AI then compares that independently-derived result with the reference DXF and identifies why any mismatch occurred.
- Learn **generalizable interpretation rules** from the comparison (datum origin, chain-vs-baseline distinction, step dimensions, convex/concave C/R mapping, feature-count logic). Do NOT learn or memorize raw coordinates as a substitute for drawing interpretation.
- A reference DXF may be used to confirm that a particular PDF interpretation is correct. It MUST NOT be used as a hidden bounding-box ruler to invent a dimension that cannot be traced on the PDF.

#### 2.4.2 Ground-Truth Comparison Rules
- Compare: feature position, feature size, contour topology, hole/slot locations, chamfer geometry, explicitly specified radii, and part-to-code mapping.
- When a mismatch is found, classify the root cause explicitly as one of: `DATUM ERROR`, `CHAIN/BASELINE ERROR`, `STEP DIMENSION ERROR`, `FEATURE TYPE ERROR`, `FEATURE-COUNT ERROR`, `C/R TOPOLOGY ERROR`, `REFERENCE/FORMED-DIMENSION ERROR`, `UNFOLD TRANSFORM ERROR`, `BEND-SEQUENCE ERROR`, `CONTAINMENT ERROR`, `CODE/SCHEMA SEMANTICS ERROR`, `MISSING/AMBIGUOUS PDF DIMENSION`, or `DXF-ONLY SHOP FEATURE`.
- If the DXF and PDF differ but the mismatch can be explained by a PDF dimension string that was previously misread, correct the PDF interpretation and record the anti-regression rule in the portable skill when validated.
- If the DXF differs from the PDF in a way that **cannot** be supported by the PDF dimensions/callouts, do NOT silently teach that difference as a general rule. Report it as a production-CAD adjustment or source conflict and ask the user when it materially changes the part.
- A newer visible revision note / red correction on the PDF must still be reported if it conflicts with the supplied DXF; ground-truth calibration does not erase revision chronology.

#### 2.4.2b V4.14 approved DIRECT AUDIT of pre-existing AI DXF against a reference

If the user's objective is to evaluate **the AI's already-exported DXF** against a customer-approved reference DXF, compare **those TWO DXFs FIRST**, matching only proved drawing-code clusters and actual user/PDF-confirmed coordinate units, then normalizing layout-only translation and any independently proved orientation. Audit full physical outer/inner boundaries, each hole/slot/cutout family (type, diameter, original quantity and coordinates), true R/C, complete unfolded extent, each double-line bend-pair coordinate and its clipping to real material. ARC+LINE in the reference and exact, closed LWPOLYLINE/bulge in the AI output are geometrically equivalent; raw entity counts alone are not a failure. A source/orthographic face is only PARTIAL if the reference has a complete flat, irrespective of its locally correct holes. Report MATCH/PARTIAL/DIFF **per code**, protect MATCHed parts from later edits, and **only THEN** revisit the PDF to identify why the AI made each error. This is distinct from creating a NEW PDF-based drawing: existing PDF-FIRST rules are unchanged, and sample DXF is never a hidden replacement for an unproved PDF dimension. Approved case: `regression/qa/520217-26_V4_14_APPROVED.md`.

#### 2.4.3 Approved material-table Laser R takes precedence over old DXF-only R0.5 exception

The V4.3 unconditional rule to omit uncalled-out DXF-only R0.5 is superseded. Read the approved `references/MATERIAL_RULES.md` and apply automatic Laser R0.5, R2 and R3 to **eligible, uncalled-out** corners according to material/thickness and corner class. Explicit PDF R or C at a corner always overrides its material-table auto R. A shop-added R not prescribed by the PDF or approved table may be omitted only with direct user confirmation or an approved shop specification; otherwise FLAG a source conflict. This rule never authorizes inventing contour topology, flattening a relief into a fillet, or silently adjusting explicitly dimensioned PDF geometry.

#### 2.4.4 Calibration / Portable Learning Discipline
- Every reference-DXF comparison is an **anti-regression calibration case**: record the semantic reason for each corrected mismatch, not merely the corrected coordinate. Validated general rules belong in this portable skill file.
- Future PDF-only jobs, including in unrelated chats or on another AI, must apply those semantic rules from this file without requiring a DXF.
- Do not generalize one-off production edits from a single DXF into universal rules unless the user explicitly confirms they are standard practice.
- Do not rely on conversational memory for this learning. If the lesson must survive across chats/AIs, encode it in this master skill or a required companion regression file.

---

## 6. Japanese Manufacturing Knowledge Base

| Japanese Term | Kanji / Kana | Manufacturing Meaning | CAD Layer / Action |
| :--- | :--- | :--- | :--- |
| **Kegaki** | ケガキ / 罫書 | Marking / Scribe Line | Layer 0, Color 1 (Red) |
| **Burring** | バーリング | Extruded / Tapped Flange Hole | Draw Pilot Hole, Color 3 Center Point |
| **Burring Pilot** | バーリング下穴 | Pre-hole for Burring Operation | Draw exact pilot diameter |
| **Countersink** | 皿 / 皿揉み | Countersunk Hole | Draw inner through-hole diameter |
| **Counterbore** | ザグリ | Counterbored Hole | Draw inner through-hole diameter |
| **Half Shear** | ハーフシャー / 半切 | Positioning Pin / Half Cut | Draw center Piasu point (Green) |
| **Bending** | 曲げ / L曲げ / Z曲げ | Press Brake Bending Operation | Double DASHED lines on Layer 0 |
| **Unfolded** | 展開 / 展開図 | Flat Pattern Drawing | Extract as primary flat geometry |
| **Unmachinable** | 加工不可 | Feature impossible to laser cut | Flag error in report |
| **Reference** | 参考 / 参考寸法 | Reference Dimension (No Tol) | Do not apply tolerance adjustments |
| **Tap** | タップ / ネジ | Threaded Tapped Hole | Convert to pilot hole diameter |
| **Chamfer** | 面取り | Corner Chamfer (C) | Bake into polyline vertices |
| **Radius** | R加工 / R | Corner Fillet Radius (R) | Bake into polyline bulges |
| **Slot** | 長穴 | Elongated / Stadium Slot | Closed LWPOLYLINE with bulges |
| **Nobi** | ノビ / 伸び | Bend Allowance Deduction | Subtract from bend zone |
| **Piercing** | ピアス / ピアシング | Laser Piercing Point | Layer 0, Color 3 (Green) |
| **Bend Datum** | 曲げ基準 | Reference Edge for Bending | Align datum bend line |

---


## V4.7 DXF-first output mode (approved 2026-09-26)
After executing ALL approved V4.6 drawing/material rules and real geometric verification, build ONE checked canonical part-local model. The same coordinates generate direct individual and combined DXFs and optional request-only Lisp; never independently recalculate for either. See `CAD_OUTPUT.md`. Critical missing source evidence blocks production; numeric-only uncertainty on proved topology can be Magenta non-production PREVIEW only on request. No V4.6 engineering lesson is changed by this output migration.
<!-- END MODULE: skills/lispcad/core/DRAWING_READING.md -->

---

<!-- BEGIN MODULE: references/SOURCE_DATA_CLASSIFICATION.md -->
# SOURCE_DATA_CLASSIFICATION — V4.25 repo-direct source routing

## 2026-10-12 numeric customer-code dimensional authority exception
The selected `references/CUSTOMER_CAD_RULES.yaml` record is authoritative for per-customer DATA/PDF dimensional comparison, only when a numeric **customer_code** was independently identified on the job statistics sheet. `DATA_NO_DIM_COMPARE` waives generic numerical PDF-vs-DATA discrepancy flags for that customer's DATA-derived parameters, never missing/mismatched holes, nominal M identity, source family/member completeness, dimensional witnesses belonging to an absent member, topology, revisions, unchanged DATA geometry, or DXF saved read-back. `PDF_PRIORITY` uses proved PDF dimensions with DATA provenance. `CONFIRM_CONFLICT` locally REVIEWs true same-parameter disagreement. With no customer_code use general existing thresholds. The historical job-family 646 DATA-required rule below is independent of numeric customer code 646.

## V4.25 DATA-first / manufacturing-second clarification

For every `PDF_DATA_RAW` job, **DATA geometry must be harvested/preserved before manufacturing canonicalization**. Load `DATA_RAW_TO_MANUFACTURING_CONTRACT.md` in addition to the existing V4.21/V4.24 preservation and physical-census references.

Freeze/account the complete DATA source first as `RAW_DATA_SNAPSHOT`, classify `PHYSICAL_DATA_BASELINE`, then compare PDF/DATA only by the same physical parameter. The DATA<->PDF threshold is a conflict gate, **not a redraw tolerance** and not automatic permission to snap DATA to the PDF nominal.

- If the same parameter has `Delta < 0.1 mm` under the general customer rule, the comparison passes. If no active routed manufacturing rule controls that parameter, retain the DATA physical geometry unchanged.
- If the same parameter has `Delta >= 0.1 mm`, FLAG `DATA_PDF_DIM_DIFF`, retain the conflicting DATA parameter locally, and do not automatically force it to PDF. Continue unrelated proved families under the normal local-uncertainty rules.
- Any production geometry intentionally changed after DATA harvest requires an active controlling manufacturing rule and `MANUFACTURING_CHANGE_LEDGER` scope. Examples include a source tolerance/mid-tolerance conversion, M* pilot conversion, explicit R/C, material-table automatic R, and proved Nobi/bend placement.
- All physical DATA outside approved changed scopes must pass `UNTOUCHED_DATA_INVARIANCE_CHECK`. Entity representation may change only when the physical curves/topology are exactly equivalent within CAD numerical precision.

## V4.24 manufacturing-canonicalization clarification

The existing `PDF_DATA_RAW` authority split remains: DATA supplies source geometry/provenance and PDF supplies semantics/control. After source extraction, an active manufacturing rule may intentionally replace/add the production representation of a proved source feature. Examples are material-table automatic Laser R and `M*` thread-pilot conversion. Record such changes as explicit manufacturing canonicalizations; they are not permission to redraw unrelated DATA geometry.

The numeric DATA<->PDF gate compares the **same physical parameter**. For a proved `M<n>` tap, compare an identifiable DATA **nominal thread reference** diameter against nominal `n`; do not compare the raw pre-hole/pilot diameter against nominal `n`. The final laser CUT may then be canonicalized to the approved thread-pilot diameter under `HOLES_TAPS.md` / `THREAD_PILOT_TABLE.md`.

**Status:** USER APPROVED V4.20 2026-09-29; V4.21 geometry-preservation hardening approved 2026-09-30; V4.25 sequencing/scope hardening approved 2026-10-02.

**V4.21 hard gate:** for every PDF + customer DXF DATA job, existing DATA geometry must be harvested/preserved and assembled by proved transforms; do not redraw the same geometry from PDF dimensions. Load `references/PDF_DATA_RAW_GEOMETRY_PRESERVATION.md`. Job family `646` is DATA-required by default: if its customer DATA is absent, report `DATA_REQUIRED_MISSING` and ask for it instead of silently using PDF_ONLY.

## 1. Four source relationships

### PDF_ONLY
PDF/image is the source geometry. During explicit training/calibration workflows, absence of an unprovided DATA DXF is not a reason to ask whether one exists; continue from PDF. In ordinary production, if a page visibly carries a boxed/stamped `DATA` mark but its CAD DATA is absent, report `DATA_EXPECTED_MISSING` when the current task requires that DATA.

### PDF_DATA_RAW
Use when customer CAD/DXF is supplied together with the corresponding PDF/page. A boxed/stamped `DATA` mark on the PDF is evidence that CAD DATA exists for that page. PDF + DXF supplied together defaults to `PDF_DATA_RAW` unless the user explicitly declares the DXF to be a clean/sample/approved/training reference.

Authority split:
- **DATA supplies source geometry 100%**: source lines/arcs/curves, face/view outlines, hole/slot geometry and locations.
- **PDF supplies semantics/control**: code, material, thickness, printed dimensions/witnesses, Nobi, revision/handwriting, feature identity/count and BEND/KEGAKI/RIB/PIASU meaning.

Pipeline:
`PDF mapping/semantic lock -> RAW DATA geometry extraction/freeze -> classify views/faces and physical roles -> remove text/dimension/hidden/construction/thickness-only duplicates -> map feature ownership -> SAME_PARAMETER_GATE -> apply only proved manufacturing rules with MANUFACTURING_CHANGE_LEDGER -> assemble/unfold -> UNTOUCHED_DATA_INVARIANCE_CHECK -> QA DATA<->PDF/source reprojection -> export/read-back`.

Do not redraw the whole part, face contour, radius/relief, hole/slot center, or other existing physical geometry from PDF dimensions/picture approximation when that geometry exists in customer DATA. Harvest it, clean it and preserve it. Use proved transforms to assemble/unfold. Nobi changes placement between preserved faces; it is not permission to recreate those faces.

Before PASS, inverse-transform/reproject every non-canonicalized unfolded face/feature to its extracted DATA source. Any measurable redraw drift beyond CAD serialization/numerical precision is FAIL. The DATA<->PDF numeric gate below is not a redraw tolerance.

### TRAIN_REFERENCE
User explicitly declares the DXF as sample, clean/extracted drawing, approved/ground-truth CAD or training comparison artifact. It is audit/calibration evidence, not raw DATA for direct extraction. For NEW construction, interpret source independently first.

### DIRECT_EXISTING_DXF_AUDIT
When evaluating an already-exported AI DXF against an approved reference, compare those two DXFs first in proved physical units/orientation, report MATCH/PARTIAL/DIFF per code, then use PDF/source to diagnose causes.

## 2. DATA <-> PDF numeric gate

Compare only the same physical parameter after correct code/view/feature/datum/unit mapping.

For every customer except KH433:
- `Delta < 0.1 mm` -> NO FLAG.
- `Delta >= 0.1 mm` -> FLAG `DATA_PDF_DIM_DIFF`.

Exactly 0.1 mm FLAGS.

For KH433, only when explicitly identified as that customer:
- `Delta < 1.0 mm` -> accepted DATA noise if topology and feature identity/count are unchanged.
- `Delta >= 1.0 mm` -> FLAG.

Numeric allowance never waives topology, feature family/count, bend order, revision/cancellation, unit, mirror, KEGAKI/PIASU/SLIT/RIB identity, self-intersection or duplicate-toolpath errors.

## 3. Canonicalization

Canonicalization occurs **only after complete DATA harvest/accounting**.

1. First run the same-parameter DATA<->PDF gate.
2. A passing gate does not by itself authorize changing DATA to the PDF nominal. With no active manufacturing rule controlling that parameter, keep the cleaned DATA physical geometry unchanged.
3. If an active routed manufacturing rule controls the parameter and the relevant source identity/scope is proved, apply that rule and record the exact local change in `MANUFACTURING_CHANGE_LEDGER`. Examples include mid-tolerance, thread-pilot conversion, explicit R/C, automatic material R and Nobi/bend placement.
4. At or above the applicable DATA<->PDF threshold, report both same-parameter values and FLAG instead of silently forcing agreement. Do not automatically canonicalize the conflicting parameter until the conflict is resolved by higher-authority source/user evidence.
5. Geometry not inside an approved changed scope remains DATA-derived and must pass `UNTOUCHED_DATA_INVARIANCE_CHECK`; do not invent rounded values or refit it merely for cleaner output.

## 4. V4.21 646 DATA-required routing
For production job family `646`, corresponding customer DATA is expected by default. If it is absent: status `DATA_REQUIRED_MISSING`; ask for DATA; do not silently downgrade to `PDF_ONLY`; do not generate production geometry until resolved. Once DATA is present, the same universal PDF_DATA_RAW geometry-preservation rules apply as for every other job.
<!-- END MODULE: references/SOURCE_DATA_CLASSIFICATION.md -->

---

<!-- BEGIN MODULE: references/DXF_PHYSICAL_CURVE_DECODING.md -->
# DXF_PHYSICAL_CURVE_DECODING — V4.26

**Status:** USER APPROVED 2026-10-03 from job 521001-19 / codes 057688-113 and 057689-114.  
**Scope:** every production/audit workflow that reads DXF geometry as source evidence, including `PDF_DATA_RAW`, `TRAIN_REFERENCE`, and `DIRECT_EXISTING_DXF_AUDIT`. This reference adds no Nobi, material, thread, tolerance, or R/C value.

## 1. FACT / failure mechanism

A DXF `POLYLINE` or `LWPOLYLINE` vertex list is not, by itself, the physical curve topology. A segment whose start vertex has nonzero **bulge** is an ARC, not the straight chord between its endpoint vertices.

Approved 521001-19 diagnosis: customer DATA for 057688/113 and 057689/114 contains quarter-circle bulged segments corresponding to the PDF `2-R3` and `2-R1`. Reading endpoint coordinates while ignoring bulge incorrectly converts those source radii into apparent 45-degree chamfers.

## 2. Mandatory decode before geometry/feature classification

When any source DXF is present, decode the complete physical curve representation **before** contour topology, R/C identity, Feature Census, physical-family inventory, bbox comparison, canonicalization, or reference comparison.

For every relevant entity:

- `LINE` -> physical straight segment.
- `ARC` -> physical circular arc using center/radius/start/end/sweep.
- `CIRCLE` -> physical full circle.
- `LWPOLYLINE` -> evaluate every segment from each vertex to the next using that **start vertex's bulge**.
- old-style `POLYLINE` / `VERTEX` -> evaluate every 2D polyline segment using the `VERTEX` bulge (DXF group 42) belonging to the segment start vertex.
- closed `POLYLINE` / `LWPOLYLINE` -> also evaluate the final-vertex -> first-vertex closing segment, including the final vertex's bulge.
- nested/block geometry -> apply the proved INSERT/block transform before physical comparison; do not classify transformed arc endpoints as a chord.
- unsupported/non-planar curve forms -> retain `UNKNOWN`/FLAG and do not simplify them into LINE merely to continue production.

## 3. Bulge semantics

For endpoints `P0`, `P1` and start-vertex bulge `b`:

- `b = 0` -> LINE from `P0` to `P1`.
- `b != 0` -> circular ARC.
- signed included angle: `theta = 4 * atan(b)`.
- chord length: `c = |P1 - P0|`.
- radius magnitude: `R = c * (1 + b^2) / (4 * |b|)`.
- bulge sign controls sweep orientation; preserve it rather than replacing the arc with its chord.

For a 90-degree quarter circle, `|b| = tan(90°/4) = 0.41421356237...`. Therefore endpoint deltas that visually resemble `3 x 3` or `1 x 1` are not evidence of `C3` or `C1` when the controlling segment carries this bulge; the decoded physical curves are R3 or R1 respectively when the radius calculation closes.

Use a CAD/DXF library's exact virtual/arc geometry when available. The formulas above are an independent audit definition, not permission to refit source curves.

## 4. PHYSICAL_CURVE_CENSUS

Before semantic feature classification, retain an evidence-equivalent census for every relevant source curve:

`source_entity, source_vertex_or_segment, curve_type, endpoints, bulge_if_any, center_if_arc, radius_if_arc, signed_sweep_if_arc, closed_segment_status, transform, physical_role`.

`curve_type` must reflect decoded physical geometry (`LINE`, `ARC`, `CIRCLE`, other proved curve), not entity-container appearance.

A `POLYLINE` container may therefore contribute a mixture of LINE and ARC physical segments.

## 5. R/C semantic interaction

DXF physical decoding answers **what physical curve exists in DATA/reference**. PDF/source callouts still control manufacturing semantics according to the active source-mode authority rules.

- Never classify `C` merely because two adjacent polyline vertices have equal X/Y offsets.
- Never classify `R` merely because a callout says R while DATA was not physically decoded.
- First decode DATA physical curves; then compare the decoded result with PDF/source R/C semantics and quantity/scope.
- A true DATA arc may be represented later as ARC or exact bulged LWPOLYLINE; representation change is acceptable only when the physical curve is invariant or an explicit manufacturing rule records the changed scope.

## 6. Hard QA gates

### DXF_SOURCE_BULGE_DECODE_COMPLETE
For every relevant source `POLYLINE`/`LWPOLYLINE`, account for every segment and bulge, including the closed final->first segment.

### BULGE_ARC_NOT_CHORD
If any relevant segment has `|bulge| > CAD numerical zero`, its physical source type is ARC. Production FAIL if the source physical census or unchanged canonical geometry treats that segment as a straight chord.

### PHYSICAL_CURVE_REPROJECTION
Source reprojection/reference comparison must compare physical LINE/ARC/CIRCLE geometry: endpoints plus center/radius/sweep for arcs. Vertex equality, bbox equality, chord equality, raw entity count, or a visually similar polyline is insufficient.

### R_C_SOURCE_CLOSURE
When PDF/source declares R/C, compare the callout family/value/count against the decoded physical DATA/reference curve family. Do not report `SOURCE_CONFLICT` until both sides have been decoded/classified correctly.

No production PASS is permitted when a relevant bulged source segment is unaccounted, flattened to a chord, or omitted from physical-curve QA.

## 7. Relationship to V4.25

V4.25 requires `RAW_DATA_SNAPSHOT`, physical baseline, representation-equivalent geometry and untouched-DATA invariance. V4.26 clarifies that the raw/physical baseline itself must contain **decoded physical curves**. Preserving only polyline endpoint vertices while dropping bulge is not 100% DATA harvest and is not representation equivalence.

This change does not modify numeric manufacturing tables or the DATA<->PDF threshold.
<!-- END MODULE: references/DXF_PHYSICAL_CURVE_DECODING.md -->

---

<!-- BEGIN MODULE: references/MECHANICAL_CLASSIFIER.md -->
# MECHANICAL_CLASSIFIER — V4.33 identity/challenge hardening over V4.23/V4.20

## V4.33 required identity/challenge fields

Extend the mechanical record with:
`part_identity_graph_status, source_utilization_status, first_solve_status, holistic_challenge_status, unresolved_blocker_class, final_engineering_sanity_status`.

When multiple barcodes/codes, constituent marks, weld relationships or candidate child parts share a drawing/detail/DATA cluster, load `references/PART_IDENTITY_GRAPH.md` and close ownership before manufacturing geometry is assigned.

A high-evidence part that the current solver cannot close is `AI_INTERPRETATION_GAP` until source exhaustion proves a true ambiguity; do not silently convert solver difficulty into customer missing-data status.

## V4.23 required source-census fields

Extend the preliminary mechanical record with:
`source_entity_census, source_physical_inventory, drawing_only_inventory, canonicalized_inventory, bidirectional_diff_status, per_bend_witness_ledger_status`.

Every relevant DATA primitive must receive a semantic role before it is eligible for manufacturing canonical geometry. `THICKNESS_REPRESENTATION`, hidden/projection-only, dimension-helper/construction and duplicate/coincident entities do not become CUT by default. Every active physical family must still receive its normal manufacturing-family classification and host/status.


**Status:** USER APPROVED 2026-09-29.

Before production geometry, create a mechanical classification record. It routes modules; it never substitutes for V4.19 FACE_GRAPH proof.

Required fields:
`source_mode, part_class, face_count, bend_axes, bend_angles_and_signs, feature_inventory, evidence_status, loaded_modules`.

Part classes include:
`FLAT_NO_BEND, SINGLE_BEND_L, DOUBLE_BEND_U, OFFSET_Z_JOG, MULTI_FACE_ORTHOGONAL, STEPPED_BENT, BOX_4_FLANGE, INSIDE_VIEW_ASSEMBLY, MIRROR_PART, OTHER_PROVED_TOPOLOGY`.

Feature inventory is independent:
- outer/inner CUT;
- round hole/tap;
- straight slot;
- curved/circular-arc slot;
- BEND;
- KEGAKI;
- PIASU/PIERCING POINT;
- SLIT/RELIEF;
- RIB;
- R/C/chamfer;
- other forming feature.

Do not classify from color alone. Use entity type, connectivity/topology, source callout/leader, host face and manufacturing function.

Routing:
- flat -> FLAT_NO_BEND;
- any bent/multi-face -> BEND_UNFOLD + FACE_GRAPH protocol;
- curved slot -> `features/CURVED_SLOT.md`;
- KEGAKI -> `features/KEGAKI.md`;
- SLIT/RELIEF -> `features/SLIT_RELIEF.md`;
- RIB -> `features/RIB.md`;
- PIASU/PIERCING -> existing HOLES_TAPS/forming rules.

No code receives production PASS until every detected/required manufacturing family has an explicit status.
<!-- END MODULE: references/MECHANICAL_CLASSIFIER.md -->

---

<!-- BEGIN MODULE: references/PDF_DATA_RAW_GEOMETRY_PRESERVATION.md -->
# PDF_DATA_RAW_GEOMETRY_PRESERVATION — V4.25 DATA-first hardening over V4.24

## V4.25 RAW DATA freeze before manufacturing canonicalization

For every `PDF_DATA_RAW` job, load `DATA_RAW_TO_MANUFACTURING_CONTRACT.md` and enforce this order before any production geometry is called complete:

`RAW_DATA_SNAPSHOT -> PHYSICAL_DATA_BASELINE -> SAME_PARAMETER_GATE -> MANUFACTURING_CHANGE_LEDGER -> MANUFACTURING_CANONICAL -> UNTOUCHED_DATA_INVARIANCE_CHECK`.

- **Freeze/account first:** harvest and classify the complete relevant customer DATA before tolerance, M* pilot, R/C, Nobi or another manufacturing adjustment is applied. `100% DATA` means complete source geometry/provenance accounting before manufacturing; drawing-only text/dimensions/hidden helpers/thickness-representation-only edges may still be excluded by proved semantic role.
- **No-rule low delta stays DATA:** a DATA<->PDF same-parameter difference below the applicable threshold is not permission to snap the DATA geometry to the PDF nominal. If no active manufacturing rule controls that parameter, retain the physical DATA value/curve unchanged.
- **Rule-scoped change only:** every intentional change after the freeze must have a proved controlling rule and local `MANUFACTURING_CHANGE_LEDGER` entry. Valid examples include source tolerance/mid-tolerance, M* pilot conversion, explicit R/C, material-table automatic Laser R and Nobi/bend placement.
- **Conflict does not self-correct:** a same-parameter difference at/above the threshold is `DATA_PDF_DIM_DIFF`; retain/flag the conflicting DATA parameter instead of silently forcing it to PDF. Continue unrelated proved geometry under normal local-uncertainty policy.
- **Untouched means physically invariant:** outside approved changed scopes, source endpoints, centers, radii, sweeps and curve geometry must survive within CAD numerical/serialization precision. The threshold is not a redraw tolerance.
- **Representation-neutral:** LINE/ARC/CIRCLE may be re-encoded as an exactly equivalent LWPOLYLINE/bulge representation, or vice versa, when physical curves/topology do not change. Prefer direct source primitives when they are simpler/safer. Raw entity count and AutoCAD `OVERKILL` are not acceptance criteria.

521001-20 approved examples: tolerance may legitimately produce `855 -> 854.75` and `600 -> 599.75`; proved M5 may produce raw pre-hole `Ø4.134 -> Ø4.2` through the thread-pilot rule; an otherwise uncontrolled DATA height `60.000709679` versus PDF `60` must remain `60.000709679` because the sub-threshold comparison alone does not authorize snapping.

## V4.24 manufacturing canonicalization after 100% DATA harvest

Customer DATA remains the source geometry/provenance authority, but `100% DATA` is a source-harvest rule, not a blanket instruction to serialize every raw DATA parameter unchanged. After source roles, host faces and feature identity are locked, apply every active manufacturing rule that explicitly controls production geometry.

- **Automatic Laser R:** an otherwise uncalled eligible outside corner `<=90°` must receive the active material/thickness Laser R from `MATERIAL_RULES.md` even when the harvested DATA corner is sharp. Record the local sharp-vertex -> tangent-R replacement as `DATA_AUTO_R_CANONICALIZATION`. Explicit source R/C still wins at its own corner.
- **Tapped M* holes:** preserve DATA center, quantity, host face and source role. Nominal-reference geometry and raw pre-hole geometry are evidence, not automatically final CUT geometry. Final pilot representation follows `HOLES_TAPS.md` + `THREAD_PILOT_TABLE.md` unless the PDF explicitly controls another effective hole diameter.
- A canonicalized R/pilot is allowed in `CANONICAL_TO_SOURCE_PHYSICAL` only with an explicit rule/provenance record. Every unchanged neighboring DATA segment/feature still must inverse-reproject to source within CAD numerical/serialization precision.
- FAIL if an implementation cites `DATA 100%` as the reason to omit required automatic R, preserve a raw tap pre-hole instead of the controlled pilot, or serialize a tap nominal-reference circle as an extra production cut.

## V4.23 physical DATA census and bidirectional closure

Before canonical geometry, classify every relevant harvested DATA primitive as one of:
- `PHYSICAL_CUT_OR_FACE_EDGE`
- `PHYSICAL_HOLE_SLOT_OR_FEATURE`
- `BEND_SUPPORT`
- `THICKNESS_REPRESENTATION`
- `HIDDEN_OR_PROJECTION_ONLY`
- `DIMENSION_HELPER_OR_CONSTRUCTION`
- `DUPLICATE_COINCIDENT`
- another explicitly proved physical/nonphysical role.

A DATA primitive is not automatically manufacturing geometry merely because it is present in customer CAD. Paired edges shown only to represent sheet thickness in Side/Section views remain `THICKNESS_REPRESENTATION` unless source semantics independently prove that edge is an actual cut boundary.

After unfold/canonicalization, run both `SOURCE_PHYSICAL_TO_CANONICAL` and `CANONICAL_TO_SOURCE_PHYSICAL`. Passing inverse reprojection for only the subset selected by the AI is insufficient. Missing physical source geometry and extra manufacturing geometry are both production FAIL. Load `DATA_PHYSICAL_CENSUS_AND_BIDIRECTIONAL_QA.md`.


**Status:** USER APPROVED 2026-09-30; V4.25 hardening approved 2026-10-02.

## Scope
Applies to every job where the customer supplies a PDF/image together with corresponding customer CAD/DXF DATA.

- Customer DATA is the **geometry authority** and authoritative geometry source.
- PDF is the semantic/control source for code, material, thickness, view/face meaning, dimension witnesses/datums, drawing scale, revision/handwriting, Nobi, BEND, KEGAKI, RIB, PIASU, feature identity/count and manufacturing semantics.
- Job family `646` is DATA-required by default. If a 646 production job arrives without its corresponding customer DATA, report `DATA_REQUIRED_MISSING`, ask for the DATA, and do not silently fall back to PDF_ONLY.

## Geometry-preservation hard gate
When the same physical geometry exists in customer DATA, do not reconstruct/redraw it from PDF dimensions, bbox, screenshots or visual approximation.

Required flow:
1. Read PDF to lock code/page mapping, semantics, witnesses, scale and formed-face meaning.
2. Extract the actual DATA primitives/curves for the relevant views/faces and freeze/account them before manufacturing adjustment.
3. Remove drawing-only entities: frame, title block, dimensions, text, hidden/construction lines, duplicated thickness edges and unrelated views only after role classification.
4. Preserve retained source geometry in its local face/view coordinate system.
5. Assemble/unfold using only proved transforms: translation, rotation, source-proved reflection and source-proved uniform drawing-scale conversion.
6. Apply Nobi/bend rules to placement between faces, not by redrawing face geometry.
7. Canonicalize only when an active PDF/manufacturing rule explicitly controls that parameter; record each canonicalized element separately and preserve all geometry outside its changed scope.

## Scale
Prove physical scale per corresponding PDF page/view. Never apply one common scale to all DATA files merely because they belong to one job. A proved 1:2 source view is converted to physical geometry by x2 before assembly; this is a source transform, not permission to redraw.

## QA / source reprojection
Before production PASS:
- inverse-transform/reproject every non-canonicalized unfolded face/feature back to its extracted DATA source geometry;
- residual may only reflect CAD serialization/numerical precision;
- any visible or measurable redraw drift is FAIL;
- DATA<->PDF dimension thresholds are not redraw tolerances;
- audit CUT, HOLE/SLOT, BEND, KEGAKI and RIB independently;
- bbox/flat-size closure alone is insufficient.

## Forbidden shortcuts
FAIL if existing DATA geometry is rebuilt from printed dimensions; endpoints/radii/centers are rounded without an explicit canonicalization rule; bbox resemblance substitutes for face ownership; scale is forced to make dimensions match; mirror/rotation is inferred without evidence; or small redraw drift is accepted under shop/customer delta thresholds.

## Relationship to V4.20
V4.20 already stated that DATA supplies source geometry 100%. V4.21 made that statement executable through mandatory geometry harvesting/preservation, transform-only assembly, source reprojection, and the 646 missing-DATA gate. V4.25 further makes the pre-manufacturing DATA snapshot and local change scope explicit so valid production canonicalization cannot leak into unrelated DATA geometry.
<!-- END MODULE: references/PDF_DATA_RAW_GEOMETRY_PRESERVATION.md -->

---

<!-- BEGIN MODULE: references/DATA_PHYSICAL_CENSUS_AND_BIDIRECTIONAL_QA.md -->
# DATA_PHYSICAL_CENSUS_AND_BIDIRECTIONAL_QA — V4.25

**Status:** USER APPROVED 2026-10-01 from 521001-03 direct audit; V4.25 sequencing/invariance hardening approved 2026-10-02 from 521001-20 direct audit.
**Scope:** every `PDF_DATA_RAW` job. This reference adds no Nobi/material formula.

## V4.25 RAW baseline + manufacturing-scope QA

Before any production canonicalization, freeze/account the complete relevant customer DATA as `RAW_DATA_SNAPSHOT`, then classify `PHYSICAL_DATA_BASELINE`. Load `DATA_RAW_TO_MANUFACTURING_CONTRACT.md`.

### RAW_DATA_SNAPSHOT_COMPLETE
Every relevant DATA primitive/view/face must be harvested before manufacturing adjustment and assigned a semantic role. Drawing-only exclusion is allowed only after role classification; it must not be used to hide unaccounted physical geometry.

### PHYSICAL_DATA_BASELINE_COMPLETE
Build the physical manufacturing baseline from the source-supported CUT/face edges, holes/slots/features, bend support and other proved physical families. Keep source coordinates/curves/provenance before any tolerance, tap-pilot, R/C, Nobi or other manufacturing change.

### SAME_PARAMETER_GATE
Run DATA<->PDF delta checks only on the same physical parameter after code/view/feature/datum/unit mapping. A passing low-delta comparison does not authorize snapping DATA to the PDF nominal. At/above the applicable threshold, FLAG `DATA_PDF_DIM_DIFF` and do not automatically canonicalize that conflicting parameter.

### MANUFACTURING_CHANGE_LEDGER
Extend the V4.24 canonicalization ledger. Every physical member that differs between `PHYSICAL_DATA_BASELINE` and manufacturing canonical geometry must retain:

`source_members, host_face, source_geometry_or_value, same_parameter_gate_status, controlling_rule, changed_scope, canonical_geometry_or_value, serialized_members`.

A rule applies only within its proved `changed_scope`; unchanged neighboring DATA geometry remains independently auditable.

### UNTOUCHED_DATA_INVARIANCE_CHECK
For every physical DATA member outside all approved changed scopes, compare the source physical curve with canonical and saved-DXF read-back geometry after reversing only proved layout/source transforms. PASS requires identical physical geometry within CAD numerical/serialization precision. The DATA<->PDF customer threshold is not an allowed redraw tolerance.

Equivalent representation is permitted: LINE/ARC/CIRCLE versus an exact LWPOLYLINE/bulge encoding is physically acceptable when endpoints, centers/radii/sweeps and topology represent the same curves. Raw entity count and AutoCAD `OVERKILL` are not physical-geometry QA.

521001-20 regression: `855 -> 854.75`, `600 -> 599.75`, and M5 raw pre-hole `Ø4.134 -> Ø4.2` are approved rule-scoped manufacturing changes. An otherwise uncontrolled source height `60.000709679` must remain unchanged; snapping it to PDF nominal `60` is `UNTOUCHED_DATA_INVARIANCE_FAIL`.

## V4.24 manufacturing-canonicalization ledger

For `PDF_DATA_RAW`, extend source-role classification with these roles when proved:
- `THREAD_NOMINAL_REFERENCE`: a nominal-diameter circle/ring that identifies the M* thread size; semantic evidence, not a production cut.
- `THREAD_PREHOLE_SOURCE`: the inner/raw pre-hole geometry associated with the same tap feature.
- `MANUFACTURING_CANONICALIZED`: canonical geometry intentionally produced by an active rule from proved source provenance, such as an automatic material Laser R or a standard thread pilot.

For every canonicalized member retain `source_members, host_face, controlling_rule, source_value_or_geometry, canonical_value_or_geometry, serialized_members`.

### DATA_TAP_NOMINAL_VALIDATION
Applies to **every proved `M<n>`**. When the corresponding DATA contains an identifiable nominal-reference diameter, compare `abs(D_DATA_NOMINAL - n)` using the general customer threshold: `Delta < 0.1 mm` passes; `Delta >= 0.1 mm` => `DATA_PDF_DIM_DIFF`. Exactly 0.1 mm flags. Do not use the raw pre-hole/pilot diameter for this nominal-identity comparison.

After identity is locked, the nominal-reference geometry remains non-cut. The raw pre-hole stays as provenance, while the final production hole is the approved M* pilot from `THREAD_PILOT_TABLE.md` unless the PDF explicitly specifies another effective hole diameter. Example only: M6 + nominal DATA Ø6 + inner DATA Ø5.1 -> one production Ø5.0 pilot.

### DATA_AUTO_R_CANONICALIZATION
A sharp DATA vertex does not suppress an active material-table auto-R. If `MATERIAL_RULES.md` requires R at an otherwise uncalled eligible outside corner `<=90°`, canonicalize that local corner to the required tangent R and record the controlling material/thickness row. Explicit source R/C takes precedence. Surrounding unchanged DATA geometry remains subject to exact source reprojection.

These recorded manufacturing canonicalizations satisfy `CANONICAL_TO_SOURCE_PHYSICAL` through explicit rule provenance; unrecorded extra arcs/holes remain FAIL.

## 1. Complete DATA entity census
Before canonical geometry, harvest every relevant DATA primitive/view/face and assign a semantic role: `PHYSICAL_CUT_OR_FACE_EDGE`, `PHYSICAL_HOLE_SLOT_OR_FEATURE`, `BEND_SUPPORT`, `THICKNESS_REPRESENTATION`, `HIDDEN_OR_PROJECTION_ONLY`, `DIMENSION_HELPER_OR_CONSTRUCTION`, `DUPLICATE_COINCIDENT`, or another explicitly documented role. Presence in customer DXF proves provenance, not manufacturing meaning.

## 2. Drawing-only thickness representation
Paired/projection edges whose purpose is only to show sheet thickness may support face/thickness/witness interpretation but MUST NOT enter manufacturing CUT unless independent source evidence proves that exact edge is a real blank boundary.

## 3. Bidirectional source/canonical QA
### SOURCE_PHYSICAL_TO_CANONICAL
Every active physical source family/curve must have host face/transform, retained/canonicalized/canceled status, quantity/value where applicable, and canonical/serialized presence. Any unaccounted active physical geometry is FAIL.

### CANONICAL_TO_SOURCE_PHYSICAL
Every manufacturing canonical/output primitive must map to physical source evidence or an explicit recorded canonicalization. Any extra manufacturing primitive without provenance is FAIL.

Inverse reprojection of only the AI-selected subset does not satisfy these gates.

## 4. Feature-family closure
Retain `family, value/size, quantity, host_face, source members, canonical members, serialized members, cancellation/canonicalization status`. Missing a family member remains FAIL even if the rest of the contour reprojects.

## 5. PER_BEND_WITNESS_LEDGER
Each bend requires `bend_id, face_A, face_B, witnesses, ID_OD_semantics, thickness_terms_and_owners, Nobi, face_order, fold_sign, material_domain, pair_coordinates, fold_back_status`.

### THICKNESS_SINGLE_USE
Every thickness contribution has exactly one owned use. A residual exactly equal to `±t` is a diagnostic pattern for witness/thickness ownership review, not a universal correction formula.

## 6. Reference duplicate normalization
In reference/direct-audit mode, exact coincident/reversed duplicate curves are normalized before physical quantity comparison and reported as `REFERENCE_ANOMALY`. Do not teach duplicate entity count as manufacturing quantity and do not mutate the sample.

## 7. PASS boundary
Production eligibility requires `RAW_DATA_SNAPSHOT -> PHYSICAL_DATA_BASELINE -> SOURCE CENSUS -> ROLE CLASSIFICATION -> FAMILY INVENTORY -> FACE_GRAPH -> PER_BEND_WITNESS_LEDGER -> SAME_PARAMETER_GATE -> MANUFACTURING_CHANGE_LEDGER -> UNFOLD/CANONICALIZATION -> UNTOUCHED_DATA_INVARIANCE_CHECK -> SOURCE_PHYSICAL_TO_CANONICAL -> CANONICAL_TO_SOURCE_PHYSICAL -> FAMILY/BEND DOMAIN QA -> FOLD_BACK/REPROJECTION -> DXF SAVE -> READ-BACK`. Downstream read-back cannot override an upstream census/semantic/invariance failure.
<!-- END MODULE: references/DATA_PHYSICAL_CENSUS_AND_BIDIRECTIONAL_QA.md -->

---

<!-- BEGIN MODULE: references/DATA_RAW_TO_MANUFACTURING_CONTRACT.md -->
# DATA_RAW_TO_MANUFACTURING_CONTRACT — V4.25

**Status:** USER APPROVED 2026-10-02 from 521001-20 direct audit.
**Scope:** every `PDF_DATA_RAW` production job.

## 1. Core sequencing — DATA first, manufacturing second

`PDF_DATA_RAW` means:

`RAW_DATA_SNAPSHOT -> PHYSICAL_DATA_BASELINE -> PDF semantic lock -> SAME_PARAMETER_GATE -> MANUFACTURING_CHANGE_LEDGER -> MANUFACTURING_CANONICAL -> UNTOUCHED_DATA_INVARIANCE_CHECK -> source reprojection -> DXF save/read-back`.

The customer DXF DATA is the geometry source. The PDF is the semantic/manufacturing control source. Do not use PDF dimensions to recreate geometry that already exists in DATA.

## 2. RAW_DATA_SNAPSHOT and PHYSICAL_DATA_BASELINE

Before any tolerance, Nobi, thread-pilot, R/C or other manufacturing adjustment:

1. Harvest every relevant DATA primitive/view/face.
2. Freeze an immutable `RAW_DATA_SNAPSHOT` containing the source geometry/provenance.
3. Classify every harvested primitive by semantic role.
4. Build `PHYSICAL_DATA_BASELINE` from the source-supported physical manufacturing geometry after excluding drawing-only text/dimensions, hidden/projection-only helpers, thickness-representation-only edges and proved duplicates.

`100% DATA` means **100% source harvest/accounting before manufacturing**, not that title blocks or drawing-only entities must be serialized, and not that active manufacturing rules are disabled.

## 3. SAME_PARAMETER_GATE before canonicalization

**2026-10-12 override:** first check the explicit numeric customer-code policy from `CUSTOMER_CAD_RULES.yaml`. `DATA_NO_DIM_COMPARE` bypasses ONLY the PDF-vs-DATA numeric discrepancy test. Full M/Ø/hole count/location/identity, source membership, topology, provenance and read-back remain mandatory; discrepancies require local REVIEW. No matching customer-code record => general gate below. Do not confuse job-family 646 with customer-code 646.


The DATA<->PDF threshold is evaluated only between the **same physical parameter** after code/view/feature/datum/unit mapping.

For the normal customer threshold:
- `Delta < 0.1 mm` -> same-parameter gate passes.
- `Delta >= 0.1 mm` -> `DATA_PDF_DIM_DIFF`; exactly `0.1 mm` flags.

A passed gate **does not by itself authorize changing DATA to the PDF nominal**. If no active manufacturing rule controls that parameter, retain the DATA physical geometry unchanged even when the PDF nominal differs by less than the threshold.

A failed gate blocks automatic canonicalization of that conflicting parameter. Keep the DATA value/geometry, FLAG the local conflict, and continue unrelated proved families under the normal local-uncertainty rules.

Different physical parameters must never be compared through this gate. Example: a DATA `THREAD_PREHOLE_SOURCE` diameter is not the same parameter as PDF `M<n>` nominal thread diameter. An identifiable `THREAD_NOMINAL_REFERENCE` is the comparable parameter.

## 4. MANUFACTURING_CHANGE_LEDGER

Any intentional physical change from `PHYSICAL_DATA_BASELINE` to production geometry requires one ledger record:

`source_members, host_face, source_geometry_or_value, same_parameter_gate_status, controlling_rule, changed_scope, canonical_geometry_or_value, serialized_members`.

Allowed changes are only those caused by an active routed manufacturing rule with proved scope, including as applicable:
- mid-tolerance / limit-dimension conversion;
- M* thread-pilot conversion;
- explicit PDF R/C;
- material-table automatic Laser R;
- Nobi / bend placement between preserved faces;
- another explicitly routed production rule.

The ledger is local. A rule that changes one edge, corner, hole diameter or face placement does not authorize refitting, rounding or simplifying neighboring DATA geometry.

## 5. UNTOUCHED_DATA_INVARIANCE_CHECK

Every physical DATA member outside all approved `changed_scope` regions must remain physically identical after canonicalization and final serialization, modulo proved rigid/uniform source transforms and normal CAD floating-point serialization precision.

Production FAIL if an untouched endpoint, center, radius, sweep, straight/curved boundary, slot/hole location or other physical curve drifts because of:
- PDF redraw;
- rounding/snapping;
- analytic refit/simplification;
- bbox reconstruction;
- arbitrary tangent rebuilding;
- tolerance used as a redraw allowance.

The `0.1 mm` DATA<->PDF threshold is **not** an allowed geometry-drift tolerance.

## 6. Representation equivalence

Entity type identity is not required when physical geometry is unchanged. Exact LINE/ARC/CIRCLE geometry may be serialized as an equivalent LWPOLYLINE/bulge representation, and vice versa, if the represented physical curves are identical within CAD numerical precision and topology/feature semantics remain unchanged.

Therefore AutoCAD `OVERKILL` behavior or raw entity count is not a production acceptance criterion. Prefer retaining source primitives when that is simpler and less error-prone; re-encoding is acceptable only after exact physical-equivalence QA.

## 7. 521001-20 approved examples

- DATA nominal `855` matching PDF nominal `855`, followed by the applicable source tolerance, may become manufacturing `854.75`; the change is a tolerance canonicalization, not PDF redraw.
- DATA nominal `600` matching PDF nominal `600`, followed by the applicable source tolerance, may become manufacturing `599.75`.
- PDF M5 + DATA nominal-reference `Ø5` + raw pre-hole `Ø4.134` locks M5 identity from the nominal-reference comparison; final laser pilot is `Ø4.2` under the active thread-pilot rule. The raw pre-hole is provenance, not a nominal-thread delta input.
- DATA physical height `60.000709679` versus PDF nominal `60` is below the general threshold. If no manufacturing rule controls that height, retain `60.000709679`; do not snap it to `60.000` merely because the PDF prints 60.

## 8. PASS boundary

For `PDF_DATA_RAW`, production PASS requires all of:

`RAW_DATA_SNAPSHOT_COMPLETE`
`PHYSICAL_DATA_BASELINE_COMPLETE`
`SAME_PARAMETER_GATE_CLOSED`
`MANUFACTURING_CHANGE_LEDGER_COMPLETE`
`UNTOUCHED_DATA_INVARIANCE_PASS`
`SOURCE_PHYSICAL_TO_CANONICAL_PASS`
`CANONICAL_TO_SOURCE_PHYSICAL_PASS`
`SOURCE_REPROJECTION_PASS`
`SAVED_DXF_READBACK_PASS`.

A valid DXF, matching bbox, successful OVERKILL, or reference/sample resemblance cannot compensate for a missing source member, unlogged manufacturing change or untouched-DATA drift.
<!-- END MODULE: references/DATA_RAW_TO_MANUFACTURING_CONTRACT.md -->

---

<!-- BEGIN MODULE: references/REFERENCE_EXPOSURE_FIREWALL.md -->
# REFERENCE_EXPOSURE_FIREWALL — V4.33

**Status:** USER APPROVED / PUSH 2026-10-07.

## 1. Purpose

Prevent hindsight/reverse-fit after a sample/reference DXF becomes visible.

The failure this gate prevents is:

`source unresolved -> inspect sample -> learn the answer -> rewrite history as "source was already clear"`.

A reference can diagnose, verify or teach a general lesson. It cannot retroactively change what the source-only solver had actually established.

## 2. Source-only freeze

Before a reference/sample is opened for calibration or comparison, persist an immutable `SOURCE_ONLY_SNAPSHOT` containing, at minimum:

- source file identities/hashes when available;
- code/part identity state;
- preliminary/final feature census;
- source groups and source members;
- part-identity graph when applicable;
- FACE_GRAPH / candidate topology state;
- dimension/witness ownership;
- current canonical/provisional output status;
- unresolved objects and blocker classes;
- claims with evidence provenance.

The snapshot must exist before `REFERENCE_EXPOSED=true`.

## 3. Post-reference statuses

Use these explicit states:

- `SOURCE_ONLY_SOLVED`
- `SOURCE_ONLY_UNRESOLVED`
- `REFERENCE_ASSISTED_UNDERSTANDING`
- `REFERENCE_CONFLICT`
- `CUSTOMER_CONFIRMATION_PENDING`

A claim that was unresolved before reference exposure does not become source-proved merely because the reference reveals a plausible answer.

## 4. Provenance immutability

After reference exposure:

- reference/sample evidence remains `APPROVED_REFERENCE` or `REFERENCE`, never silently rewritten as PRINTED/CUSTOMER_DATA;
- an unresolved pre-reference claim may be upgraded to source-proved only when new non-reference evidence is identified and recorded;
- job-specific reference coordinates must not be copied into a new source interpretation;
- a general lesson may be promoted only through the normal FACT -> ROOT_CAUSE -> PROPOSED_LESSON -> REGRESSION_CASE -> APPROVAL process.

If a session has already seen the sample, that same session cannot prove a truly blind source-only solve by re-reading the source.

## 5. Sample FLAG boundary

When the operator declares sample FLAG/Magenta geometry to be pending customer confirmation:

`SAMPLE_FLAGGED_GEOMETRY -> CUSTOMER_CONFIRMATION_PENDING`.

Such geometry is not approved-reference authority. It must not:

- fill a missing source dimension;
- resolve a source topology;
- become production geometry merely because it is present in the sample;
- be promoted into a universal rule.

It may be compared and reported as pending. Only independent source evidence or explicit user/customer confirmation may close it.

## 6. Blind regression requirement

For calibration cases intended to prove future source-only capability:

1. withhold the sample/reference from the solver;
2. run the full source-only pipeline;
3. persist/freeze the source-only result;
4. only then expose the sample to the comparator;
5. classify mismatches without changing the frozen provenance.

A regression that lets the solver see the expected sample before source-only freeze is not evidence that the AI can solve the drawing independently.

## 7. Audit rule

When a pre-reference field changes from unresolved/FLAGGED to PROVED after sample exposure, require one of:

- new PRINTED/HANDWRITTEN-REVISION/CUSTOMER_DATA/USER_CONFIRMED evidence not available in the frozen snapshot; or
- keep the result as `REFERENCE_ASSISTED_UNDERSTANDING`.

Otherwise fail `POST_REFERENCE_SOURCE_REWRITE`.

## 8. Non-generalization

This firewall does not make a sample untrustworthy. Approved reference geometry remains valuable audit evidence. The rule only preserves chronology and provenance so the AI cannot claim prior understanding that did not actually exist.
<!-- END MODULE: references/REFERENCE_EXPOSURE_FIREWALL.md -->
