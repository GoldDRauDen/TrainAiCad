# LISPCAD Core — CAD Output & Response Contract

Source: approved V4.3 production baseline.

## 8. CAD Architecture & AutoLISP Schema

### 8.1 Units & Header Setup (NEW — mandatory first step in code generation)
Before emitting any geometry, the generated `.lsp` script MUST initialize drawing units to prevent scale corruption:
```lisp
(setvar "INSUNITS" 4)   ; 4 = Millimeters
(setvar "LUNITS" 2)     ; 2 = Decimal
(setvar "LUPREC" 2)     ; 2 decimal places precision
```
All coordinate values in `*parts*` (Section 8.4) are assumed to be in millimeters; this header block guarantees the AutoCAD session interprets them correctly regardless of the user's template default.

### 8.2 Layer, Linetype & Color Specifications
All entities exist strictly on Layer `"0"`. Attribute properties are assigned via explicit DXF Group Codes:

| Geometry Feature | Linetype (Group 6) | Color Code (Group 62) | Execution Method |
| :--- | :--- | :--- | :--- |
| **Outer / Inner Boundary** | ByLayer | ByLayer (7 / White) | Closed `LWPOLYLINE` |
| **Bend Lines** | `"DASHED"` | ByLayer | Double parallel lines |
| **Kegaki / Formed Lines** | ByLayer | `1` (Red) | `LINE` or `LWPOLYLINE` |
| **Ordinary PIERCING / capacity POINT** | ByLayer | ByLayer | actual `POINT`, NOT `CIRCLE` |
| **PIERCING + THROUGH HOLE POINT** | ByLayer | `3` (Green) | actual `POINT` |
| **Relief slit (LINE-specific)** | ByLayer | `3` (Green) only when specified | `LINE` |
| **Ambiguous Features** | ByLayer | `6` (Magenta) | Estimated geometry entities |
| **Adjacent Text Notes** | ByLayer | `6` (Magenta) | `TEXT` entity next to feature |

### 8.3 Interactive Dynamic DCL Command Structure
The primary AutoLISP command MUST be **`c:DRAW`**. It constructs a dynamic DCL selection dialog at runtime:
1. Writes a temporary `.dcl` file to `(getvar "TEMPPREFIX")`.
2. Populates a `list_box` (`multiple_select = true;`) with part codes from global variable `*parts*`.
3. On accept, prompts user for insertion point `(getpoint)` and draws selected flat patterns.

### 8.4 `*parts*` LISP Data Structure
```lisp
(setq *parts*
  '(
    (
      "DRAWING_CODE"      ; String: e.g. "041919"
      "MATERIAL"          ; String: e.g. "SUS304"
      THICKNESS           ; Real: e.g. 3.0
      OUTLINE             ; List: ((x y bulge_or_nil) ...)
      OUTER_FILLETS       ; List: ((x y radius) ...)
      CHAMFERS            ; List: ((x y size) ...)
      BEND_LINES          ; List: (((x1 y1) (x2 y2) is_flagged) ...)
      CORNER_RELIEFS      ; List: ((x y offset) ...)     ; see Section 4.10 for calc rule
      INTERNAL_FILLETS    ; List: ((x y radius) ...)
      HOLES               ; List: ((x y diameter_or_slot_spec [is_flagged]) ...): unproved type can be CIRCLE Color 6
      KEGAKI_LINES        ; List: (((x1 y1) (x2 y2)) ...)
      PIASUS              ; List: ((x y is_through) ...): is_through TRUE only when PDF explicitly says PIERCING + THROUGH HOLE; metadata Ø/M in REPORT only
    )
  )
)
```


Slot-specific storage semantics are canonical in `../features/SLOTS.md`; do not duplicate them here.

## 9. Output Contract & Response Structure

For normal drawing-to-Lisp production work, output strictly in **COMPACT DUAL-STAGE FORMAT**. Accuracy and the Lisp geometry are primary; commentary is secondary.

### Stage 1: Compact Production Report
Keep Stage 1 short. Default target is approximately **4–12 lines plus a small part table**, unless a failure requires more explanation.

Required content:

1. **Part Summary** — one compact table with only:
   - Barcode / Drawing Code
   - Material
   - Thickness
   - Calculated flat blank size, when fully proven

2. **Applied Adjustments** — only values that materially affect geometry:
   - handwritten correction / handwritten Nobi used;
   - Mid-Tolerance adjustment used;
   - ID→OD conversion used;
   - Nobi table row / conservative round-up used.
   Omit this subsection if none apply.

3. **Validation Result**:
   - If all mandatory checks required for the part pass: write one concise line such as `Validation: PASS — contour, datum, feature count, unfold, containment checked.`
   - Do **not** print the full PASS checklist by default.
   - If any check is `FAIL`, `FLAGGED`, `WARN`, or `N/A` in a way that affects production interpretation, list only those exceptions with a short reason.

4. **Questions / Ambiguity**:
   - If topology/feature identity/bend order cannot be uniquely established, STOP and ask. If only dimensions or coordinates remain missing, and the user requires an output preview, create only the already-known topology with Magenta integer-rounded estimated parts and a prominent non-production FLAG; do not call it production-safe.
   - Do not generate guessed Lisp merely to complete the response.

**Report discipline:** Do not discuss irrelevant title-block fields, broad theory, calibration history, or lengthy reasoning unless explicitly requested.

### Stage 2: Ready-to-Run AutoLISP Code Block
When Stage 1 has no unresolved blocker, follow immediately with **exactly ONE** standard code block containing the complete AutoLISP script (`.lsp`), beginning with the Units & Header Setup block in Section 8.1.

If the blocker changes topology, feature identity, bend sequence, or critical material/datum, do not invent Stage 2 geometry. If the user expressly requests complete output and the only unresolved fields are numeric values on proven topology, emit a visibly FLAGGED Magenta **non-production preview** as in Section 4.4, with a Stage 1 list of all estimated fields. Never claim PASS for estimated parts.
