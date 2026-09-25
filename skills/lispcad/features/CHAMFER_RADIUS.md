# LISPCAD Feature — Chamfer / Radius / Automatic Laser R

Approved calibration 520924-19, 2026-09-25. Governing table: `../../../references/MATERIAL_RULES.md`. The old V4.3 unconditional DXF-only R0.5 exclusion is SUPERSEDED when this approved table prescribes a radius.

### 4.5 Corner Filleting & Chamfer Baking

- **No global FILLET command** or global outline fillet pass: trace real topology before arithmetic.
- Classify each target by **material interior angle**: convex/outside `<180°`; concave/re-entrant `>180°`. The term `outside corner ≤90°` in the workbook describes a convex exterior corner of the stated angle; do not apply the rule to similarly drawn inner corners.
- **Order of authority per CORNER**: drawing-specific revision/red correction → explicit PDF R/C callout (with applicable quantity) → approved workbook automatic Laser R (if the PDF has NO R/C instruction for that corner). A PDF C remains a straight chamfer and must never silently become R2/R0.5. Where a PDF R/C overrides a material table at one corner, still use automatic Laser R at other eligible uncalled-out corners.
- Workbook automatic laser radii: SS up to t5 as tabulated R0.5 for exterior ≤90°; SS t6–9 R2; SUS/other or AL rows with R0.5 for exterior ≤90°; Cu/Brass t≤5 R0.5 exterior ≤90°; SS t≥19 R3 at stated inside/outside corner class including the sheet's chamfer-language **only when there is no conflicting PDF-specific R/C**. Honor exact row/range lookup, and `無` means no automatic radius. A blank R is UNKNOWN, not automatically R0. Ignore unexplained `※3` annotation but do use the workbook's R3.
- **Two R2 of part `055955` are required in generated geometry** under the SS t9 material-table rule; this explicitly reverses the earlier hypothesis to omit them as downstream shop additions. Never treat the old DXF-only R0.5 omission as a reason to omit a radius required by the current approved table.
- **DXF-only shop radius beyond the table:** a PDF-unmarked radius that does **not** follow an approved material rule may be omitted as a separate later shop operation only with direct user approval or an approved shop specification. Otherwise source conflict/FLAG. Do not infer an arbitrary R from thickness.
- **Callout topology and count:** a leader is evidence of target corner class, not global scope; identify the candidate equivalent corners by their material topology and count (`6-C5`, `2-C10`, `4-R5` etc). Distinct R and C families MUST match their own n-calls.
- **Geometry:** bake an explicit R into polyline tangent points/bulges (for a CCW 90° arc, `bulge=tan(90°/4)=0.41421356` with sign from actual sweep). A straight C replaces the corner with two tangent-offset vertices and bulge 0. A sharp interior U-notch stays sharp unless the PDF explicitly requires an interior R or an approved material rule for that particular class applies.
- **Relief is not Laser R:** an `R=t` relief at two oppositely folding edges whose outside extents must remain unchanged is a manufacturing clearance with distinct topology. Do not spread Laser R to reliefs and do not infer three special reliefs of `055958` (method pending).

### Material-table validation
Record source material, thickness, chosen worksheet row, eligible corner class, R/C overrides, and each generated automatic radius; compare PDF and ground-truth DXF *after* this classification. A DXF R0.5 that matches the approved material table is expected and must not be excluded from regression comparisons.
