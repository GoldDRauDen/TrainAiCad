# Drawing reading and source interpretation

Use the current pinned repository and its routed rules. Read the drawing itself; OCR, filenames, entity counts, bbox, symmetry and familiar part shapes are search aids, not proof. Keep source facts, interpretations and unresolved items distinct.

## Read sequence

1. Map code(s), pages and views. Record only the material, thickness, revision and source notes that affect the part.
2. Trace the actual outside contour, openings, steps, notches, corner radii/chamfers and feature families before assigning coordinates. Do not begin from a bounding rectangle.
3. For every used dimension, identify both physical witness endpoints, its semantic meaning, datum, axis signs and owner. A printed top-left origin overrides a customary CAD origin; unresolved source frame blocks production coordinates. See `DATUM_DIMENSION.md`.
4. Link features shown in multiple views to one source member, using the controlling view/detail and face.
5. Apply handwritten corrections or Nobi only to the member/bend the leader or source context identifies. Unclear scope remains local FLAG/REVIEW.
6. Lock code, material and thickness before resolving material, thread-pilot, Nobi or feasibility rules.

Inspect orthographic, section, detail, assembly, mirror and development views as applicable. Compare corresponding sibling views before deciding an inner/outer face. Reflect a symmetric partner only when the source/user establishes its code, axis and scope; reflect all proved features/bends/marks, then revalidate. A mirrored inside view alone does not establish a new code, and symmetry does not make every bent part a mirror.

## Multi-page and clustered DATA

When summary and detailed pages conflict for the same code, first apply the source authority and revision rules. The V4.18 DETAILED_SOURCE_BUNDLE may resolve a contradictory summary only when the detailed page independently closes code identity, explicit material/thickness, dimension-witnessed formed geometry and applicable Nobi/flat arithmetic, with no higher-authority revision, correction or cancellation. Record the conflict and closure. An incomplete bundle remains FLAGGED; this does not mean the barcode page always wins. A reference DXF cannot supply missing source facts.

For a merged multi-part DXF, use only a user-declared or source-proved code-to-cluster mapping. If top-to-bottom order is explicitly given, order by descending global Y. An ambiguous row/overlap needs resolution; do not invent a left-right tie-breaker.

## Read cost and OCR

Use text extraction to find candidate metadata and dimensions, then inspect the source image for semantics and geometry. Check orientation on a thumbnail; render only relevant geometry crops at a readable resolution, and reopen a crop only when a new witness, leader or handwritten-note question requires it. Administrative title-block text is ignored unless it resolves identity or a production conflict.

Treat common OCR swaps (`B/8`, `O/0`, `S/5`, `Ø/O`, `M6/MG`) as candidates only. Verify the glyph on the drawing; manufacturing plausibility or a standard table cannot silently correct an ambiguous printed value.

## Manufacturing interpretation

Use the routed feature/material rule for Japanese terminology and geometry. For an eligible uncalled outside corner, apply the active material/thickness Laser-R table; an explicit PDF R/C at that corner controls. Never apply an automatic outside-corner radius to an inner hole/slot, flatten a relief into a fillet, or change explicit PDF geometry without its controlling rule. Treat source `加工不可` / unmachinable conditions as a production blocker, not an omission instruction. Keep slot-anchor, cancellation, bend-face and other specialized procedures in their routed owner files.
