# 520702-08 — customer DATA is a whole drawing sheet: digest by id, assemble without retyping

## FACT
- Job 520702-08 shipped 7 DXF DATA files for 3 customers; every one is a drawing sheet (frame, title block, several views, an iso view), none is a flat part.
- KH646 (`RAX00261A`, `SX-4A69433-C1A-05`): CATIA export, one layer `0`, `$INSUNITS` 0, dimensions and text exploded into 80-83% sub-2 mm LINEs, 101 ELLIPSE in the iso view, per-view scale (1:2, 1:3, iso 1:6) proved only by thread pairs (Ø1.081/Ø1.333 ×3 = M4 minor/nominal; Ø2.458/Ø3 ×2 = M6).
- Other customers: layered AutoCAD sheets with real DIMENSION entities (some measurement 0.0) and geometry inside INSERT blocks (holes of `24721-71QJ0-133` exist only inside `BLKF015`).
- The old census merged frame + dimensions + views into one 269×181 cluster.

## ROOT_CAUSE
`TOOL_GAP`. Nothing gave each DATA primitive a stable id and a single home, so the AI had to retype coordinates from a summary and could drop or alter members without a gate.

## LESSON
- `tools/dxf_digest.py` gives every primitive an id and exactly one home (view or bucket); unsupported curves, noise candidates, duplicates and annotations are listed, never silently dropped.
- `tools/dxf_assemble.py` takes ids plus a declared rigid transform; only layer/colour/linetype change, every piece must be used or excluded with a reason code, and the output is re-decoded and matched to the source in both directions before it is returned.
- Layers/colours/linetypes of an unknown customer are hints only; KH646 is always a CATIA sheet (profile auto-detected from the exploded-glyph share).
