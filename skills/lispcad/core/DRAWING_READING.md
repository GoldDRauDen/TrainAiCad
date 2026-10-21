# Drawing reading and source interpretation

Use the current pinned repository and its routed rules. Read the drawing itself; OCR, filenames, entity counts, bbox, symmetry and familiar part shapes are search aids, not proof. Keep source facts, interpretations and unresolved items distinct.

## Read sequence

1. Map code(s), pages and views. Record only the material, thickness, revision and source notes that affect the part.
2. Trace the actual outside contour, openings, steps, notches, corner radii/chamfers and feature families before assigning coordinates. Do not begin from a bounding rectangle. Census every notch/cut-out and dimensioned rectangle: each ends as built, user-cancelled (reason recorded) or a local FLAG with coordinates; never drop one silently.
3. For every used dimension, identify both physical witness endpoints, its semantic meaning, datum, axis signs and owner. A printed top-left origin overrides a customary CAD origin; unresolved source frame blocks production coordinates. See `DATUM_DIMENSION.md`.
4. Link features shown in multiple views to one source member, using the controlling view/detail and face.
5. Apply handwritten corrections or Nobi only to the member/bend the leader or source context identifies. Unclear scope remains local FLAG/REVIEW.
6. Lock code, material and thickness before resolving material, thread-pilot, Nobi or feasibility rules.

Inspect orthographic, section, detail, assembly, mirror and development views as applicable. Compare corresponding sibling views before deciding an inner/outer face. Read the projection method from the title block (`三角法` = third angle): top/bottom views sit above/below the main view and their edge nearest the main view is the part's FRONT; a web edge-on at the rear with flanges toward the viewer means the main view shows the INNER face (`CAD_OUTPUT.md` 5d). Take an end tab's side from the thick edge-on line at the end of the top/bottom view; a rotated section cannot give left/right. Unreadable -> local FLAG. Reflect a symmetric partner only when the source/user establishes its code, axis and scope; reflect all proved features/bends/marks, then revalidate. A mirrored inside view alone does not establish a new code, and symmetry does not make every bent part a mirror.

## Multi-page and clustered DATA

When summary and detailed pages conflict for the same code, first apply the source authority and revision rules. The V4.18 DETAILED_SOURCE_BUNDLE may resolve a contradictory summary only when the detailed page independently closes code identity, explicit material/thickness, dimension-witnessed formed geometry and applicable Nobi/flat arithmetic, with no higher-authority revision, correction or cancellation. Record the conflict and closure. An incomplete bundle remains FLAGGED; this does not mean the barcode page always wins. A reference DXF cannot supply missing source facts.

For a merged multi-part DXF, use only a user-declared or source-proved code-to-cluster mapping. If top-to-bottom order is explicitly given, order by descending global Y. An ambiguous row/overlap needs resolution; do not invent a left-right tie-breaker.

## Reading protocol (tools/pdf_views.py)

1. `python tools/pdf_views.py info <pdf>`: page count, rotation, `VECTOR` vs `SCANNED_IMAGE`.
2. `render --page N --out pN.png` (10×10 grid A1–J10): orientation, views, title block, where each code/view sits. Ignore administrative title-block text unless it resolves identity or a production conflict.
3. Vector page: `text --page N --dims [--cells C3:E5]` gives the exact printed strings (dimensions, `n-Ø`, `M`, `R`, `C`, `t`) with their cells. Take values from this text, never retype them from the image; OCR swaps (`B/8`, `O/0`, `S/5`, `Ø/O`, `M6/MG`) cannot occur there. Scanned page: read each value from a 600-dpi `crop` twice (two different crops or zooms); OCR output is only a candidate, and plausibility or a standard table never silently corrects an ambiguous glyph.
4. `crop --cells ... --dpi 600` every region whose witness lines, leaders, arrows or handwriting decide meaning; the image decides which geometry a value belongs to, the text decides the value.
5. Fill the dimension ledger (`JOB_CARD.md` item 2) before any arithmetic; every used value cites its crop/cell. A printed value with no ledger row is not used; a ledger row with no witness endpoints is FLAG.

## Manufacturing interpretation

Use the routed feature/material rule for Japanese terminology and geometry. For an eligible uncalled outside corner, apply the active material/thickness Laser-R table; an explicit PDF R/C at that corner controls. Never apply an automatic outside-corner radius to an inner hole/slot, flatten a relief into a fillet, or change explicit PDF geometry without its controlling rule. Treat source `加工不可` / unmachinable conditions as a production blocker, not an omission instruction. Keep slot-anchor, cancellation, bend-face and other specialized procedures in their routed owner files.
