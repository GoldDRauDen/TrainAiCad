# V4.33 holistic re-solve and complete source-view fallback

Before accepting `VIEWS_ONLY`, run `references/HOLISTIC_ENGINEERING_CHALLENGE.md`. A first failed interpretation is not source exhaustion. Re-open all relevant PDF views, DATA physical curves, witness chains, handwritten flat/Nobi arithmetic, part identity and candidate FACE_GRAPH relationships, then record the specific unresolved degree of freedom.

For multi-barcode / ①② / welded constituent drawings, build the routed `PART_IDENTITY_GRAPH` before assigning source views or DATA clusters to manufacturing codes.

# LISPCAD Core — Drawing Reading & Execution Contract

## V4.19 FACE_GRAPH_CAPTURE — mandatory source representation for bent/multi-face parts

Before Nobi arithmetic or global-flat coordinates, create an evidence-equivalent FACE_GRAPH as defined in `../../../references/FACE_GRAPH_UNFOLD_PROTOCOL.md`. Every used dimension must record both physical witness endpoints, semantic family and owner face/bend; every feature must record its host face/local datum; every bend must record both adjacent faces, shared edge, signed orientation and material domain. Shape labels (U/Z/box/etc.) may propose a graph but never prove it.

Do not proceed to production unfold while an ownership field is unresolved or while two materially different graphs satisfy the same source evidence.

## Mirror scope and slot witnesses

**Each code is independently declared; MIRROR is source scoped:** Only construct a reflected partner when the drawing/user establishes original and target codes, axis/orientation and the exact reflection scope. Reflect the complete proven geometry including contour, distinct hole families, slots, R/C, bends and markings; then revalidate the partner. If only the original is requested, do not invent a second code. A mirror of INSIDE views within one part does not create an undeclared part code.

**Slot witnesses:** exhaust whole slot dimension strings and verify END-CENTER versus OUTSIDE-TIP witnesses before asking; do not ask routine shop-spacing approval questions (`VALIDATION.md` §5.2).

## Material designation and exhaustion before asking

For sheet-metal designation families, recognize case-insensitive `SUS…→SUS`, `SP…/SS…→SS`, `A…→AL`, while preserving the full printed grade, thickness and the approved SUS430 SS-Nobi/SUS-laser split. A family match does not assert that distinct source grades are chemically identical.

Before asking, exhaust explicit witness lines, handwritten Nobi, width-derived slot-end radius and local-face transforms; then apply `references/REVIEW_PREVIEW_POLICY.md` for anything still unproved.

## V4.8 approved hole-family cancellation — active override

When an entire hole callout is clearly struck out and its leader clearly identifies a complete family, omit the whole family from DXF regardless of remaining legacy drawn circles. Log canceled source quantity and prove zero output entities; active nearby groups are unchanged. If only a tolerance/finish fragment is crossed or target/revision scope is unclear, DO NOT delete holes; ask.

## 0. Repo-Direct Execution Contract — Mandatory for Every Run

### 0.1 Session-Independent Execution
- Rules come from the repository at the pinned revision, never from chat history, hidden memory or model state.
- Before processing a drawing, load the modules the Router selects for the census. Every routed rule file is a mandatory execution rule.
- Do not assume a lesson from a previous chat exists unless a routed file, or a regression file it names, encodes it.
- Training/calibration means: validate an interpretation against user-approved reference data, extract a generalizable rule, and write it into the routed rule files after explicit approval. It does not mean silent model changes.
- A rule counts as portable only when it is stated explicitly enough that another AI can reproduce the same decision from the same inputs.

### 0.2 Authority Hierarchy
1. The user's current explicit instruction for the current job.
2. `AI_BOOTSTRAP.md` → `AI_ENTRYPOINT.md` → `skills/lispcad/router/ROUTER.yaml` → routed modules (this file is one of them).
3. Explicit drawing evidence, read per Section 2.2.1.
4. General CAD/manufacturing knowledge only where a routed rule allows it.

If a current user instruction conflicts with a safety or anti-error rule (for example, guessing an unreadable dimension from a bounding box), STOP and report the conflict instead of silently weakening the rule.

### 0.4 No Hidden Dependency on Conversation Context
- Case IDs such as `054615` or `054621` are **regression examples** under `regression/`, not required external knowledge. The rule being tested must be understandable from the routed rule text.
- If a future version depends on a table, formula, exception, or workflow, it MUST be included directly in a routed rule file or in a named companion file that the Router loads.
- Never write rules such as "as discussed earlier", "as the user said before", or "use the previous chat". Replace them with explicit, self-contained instructions.

### 0.5 Versioning and Update Discipline
- Major behavior changes are a new release listed in `docs/RELEASE_WIRING_INDEX.md`; keep the previous release reachable.
- Every validated correction must be checked for whether it is:
  - **Universal rule** → merge into the relevant main section.
  - **Regression example** → add under `regression/`.
  - **Job-specific exception** → keep in the job report only; do not promote to a universal rule without explicit confirmation.
- Routed rule files must remain internally consistent. If a new rule conflicts with an older rule, revise the older rule and document the resolution instead of leaving both active.

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
➔ [Reference calibration/audit: `references/REFERENCE_CALIBRATION_AUDIT.md`, only if a reference exists]
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
   - If the same part has conflicting material, thickness, dimension, or handwritten correction across pages, first apply the authority hierarchy in Section 0.2. For a Page-1/job-list summary conflicting with the same-code detailed drawing page, also apply the V4.18 **DETAILED_SOURCE_BUNDLE** rule below.
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

### 2.2.2 Read-Cost Protocol — cheaper reading, never lower accuracy
This protocol reduces image and context cost only. It does not relax any dimension, witness, or topology check.
- Extract the text layer first (for example `pdftotext -layout`). Use it to index title block, barcode, material, thickness, and dimension strings. Do not treat OCR text as the geometry source.
- Check page orientation on a thumbnail at 50 dpi or less. If the sheet is rotated 90°, rotate it at render time, not afterwards.
- Crop to the geometry region and render each needed region once at 200 dpi or more, then read it. Dimensions and witness endpoints are read only from a render at that resolution. If a render was low-dpi or unrotated, re-render it; do not guess from it.
- Customer and job-list pages need 100 dpi or less and only the row for the current code.
- Load customer rules, material rows, and thread or Nobi table rows for the single matching key (code, material, thickness). Do not load whole tables into context.
- Re-open an already-read region only when a new witness, leader, or handwritten-note question requires it.

### 2.3 OCR Error Correction & Context Engine
Correct optical character recognition errors using engineering context rules:
- `B` ↔ `8` | `O` ↔ `0` | `S` ↔ `5` | `M6` ↔ `MG` | `Ø` ↔ `O` | `0.5` ↔ `O.5`
- Validate dimensions against material thickness $t$ and standard hole lookup tables.

### 2.4 Material-table Laser R takes precedence over the old DXF-only R0.5 exception

The V4.3 unconditional rule to omit uncalled-out DXF-only R0.5 is superseded. Read the approved `references/MATERIAL_RULES.md` and apply automatic Laser R0.5, R2 and R3 to **eligible, uncalled-out** corners according to material/thickness and corner class. Explicit PDF R or C at a corner always overrides its material-table auto R. A shop-added R not prescribed by the PDF or approved table may be omitted only with direct user confirmation or an approved shop specification; otherwise FLAG a source conflict. This rule never authorizes inventing contour topology, flattening a relief into a fillet, or silently adjusting explicitly dimensioned PDF geometry.

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
