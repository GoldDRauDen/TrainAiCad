# 521027-26 — customer DATA was hand-patched to make the chain close

FACT: 26-063852 / 26-063856 (SS400 t16 bars, one DATA sheet U09-06-Z0.dxf). Four SPLINE R20/R10 fillets were replaced by
ARCs through their 3 fit points (R20.065 / R10.033); six LINEs were merged or split (gaps 0.0003-0.003 mm, a bar end drawn over
the neighbouring plate's rectangle = T-junction). The shim 26-063851 (full circle Ø119) was built from typed spec numbers and its
witness datum entity was patched in the canonical JSON. 26-063852 was reported PASS.

ROOT_CAUSE: `dxf_assemble` needed endpoint-to-endpoint closure within 1e-4 mm and had no T-junction or round-blank route, so the
AI wrote a patched digest; `source_sha256` was optional, so the invariance check compared the output with the patched digest
(self-referential PASS). `data_part` needed >= 3 corners and a straight datum edge, and ignored the J/LJ 180 deg turn in its roundtrip.

LESSON: DATA is copied 100%. The digest is sealed (`pieces_sha256`); noise <= 1e-3 mm, T-junction cuts (overhang dropped), the
translation to the flat origin, round blanks (datum = tangent edge c - r) and the J/LJ turn are tool routes with ledger rows
(`CLOSURE_NOISE`, `T_SPLIT`, `T_SPUR`, `TRANSLATE_TO_ORIGIN`). An ELLIPSE/SPLINE in a contour is FLAG, never an arc.
Tests: `tests/test_data_fidelity.py`.
