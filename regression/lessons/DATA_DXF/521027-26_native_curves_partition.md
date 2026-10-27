# 521027-26 — open SPLINE/ELLIPSE kept as that entity; members proposed from geometry

FACT: R20/R10 fillets of the bar outlines were SPLINEs; the digest listed them UNKNOWN and the AI replaced them by arcs. Splitting a
DATA sheet into outline / pockets / slots / holes was hand-written per job.

ROOT_CAUSE: no route for a native curve (digest -> assemble -> canonical -> exporter) and no geometry-based partition tool.

LESSON: `dxf_digest` decodes an open SPLINE/ELLIPSE (`curve`); `dxf_assemble` keeps it in an outer chain; the canonical outer polyline
carries `curves` (chord vertex, bulge 0) and the exporter writes the same entity; validation uses the curve, not its chord.
`dxf_partition.py` proposes members; anything not a simple loop is left to the AI. Tests: `tests/test_native_curves.py`, `tests/test_dxf_partition.py`.
