# CAD_OUTPUT_TEMPLATE.dxf sample layout (updated 2026-10-19)

`templates/CAD_OUTPUT_TEMPLATE.dxf` carries a sample drawing as the visual spec for output text style, sizes and placement.
`tools/export_dxf.py::new_doc()` deletes every modelspace entity, so none of it reaches production output.
`tests/test_cad_output_template.py` fails if the sample and the exporter constants drift apart.

Header: AC1021, `$PDMODE 3`, `$PDSIZE 5`, `$TEXTSIZE 10`, `$LTSCALE 15`, `$CHAMFERA/B 2`; layers `0`, `Defpoints`, `DIM`; text style `Standard`; linetype `DASHED`.

| Item | Sample (100x100 part at origin) | Exporter constant |
|---|---|---|
| Code label | TEXT h10, baseline 10 mm above outline top, x=0 | `CODE_LABEL_HEIGHT_MM=10`, `CODE_LABEL_OFFSET_MM=10` |
| `dx` | TEXT h20, right edge 23 mm left of outline, centred vertically | `DX_LABEL_HEIGHT_MM=20`, `DX_LABEL_CLEARANCE_MM=23` |
| FLAG | 3 lines TEXT h15, pitch 25 mm, x = outline right + 49 mm, first line at outline top | `FLAG_LABEL_HEIGHT_MM=15`, `FLAG_LINE_PITCH_MM=25`, `FLAG_LABEL_CLEARANCE_MM=49` |
| J/LJ (1650x80 part) | POINT + TEXT h10 at the top edge, first J = X1+30, LJ = X2-30, middle J evenly (X1/X2 = ends of the max-Y edge; sample has C5 left, C2 right, hence 35 / 32 from the blank ends); TEXT on layer 0, insert = POINT | `JLJ_TEXT_HEIGHT_MM=10`, `JLJ_INSET_MM=30` |

Owner decisions (2026-10-19):
- Generated labels (code, `dx`, FLAG) stay on non-plot `AI_META`; J/LJ POINT+TEXT stay on layer `0`.
- J/LJ: first J = X1+30, LJ = X2-30, X1/X2 = left/right ends of the max-Y edge; with more J (by length rule) they are spread evenly between those two points.
- The sample's POINT `angle=180` on LJ is not reproduced (no effect).
- Cluster gap stays 150 mm (a single code label sticking up is negligible).
