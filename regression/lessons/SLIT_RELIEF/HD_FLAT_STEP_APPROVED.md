# HD flat step sample — S measured in the flat, slit length T + 0.2 − S (approved 2026-10-25)

Rule: `rules/SLIT_RELIEF.md` §3/§5. Tool: `tools/bend_corner.py`. Test: `tests/test_bend_corner_samples.py`.
Sources (user, local only): `template/HD/slit-relief-HD.dxf` (SUS t2), `template/061247,061248/061247,061248.dxf` (SS t3.2).

**FACT:** the HD sheet draws one part three times (web, narrower bottom flange, two side tabs; Nobi 3.68, lead 6) with
the bottom bend lines moved: flange-side line at the web edge (S 0), 2 mm past it (S −2), 6 mm short of it (S +6).
S 0 → Green slit 2.2 from the corner B; S −2 → 4.2 from B (DIM 4.2), lead and R0.5 still at B; S +6 → no slit.
061248: the retreated right flange end has S 0 in the flat → slit 3.4 (t3.2 + 0.2), lead 3; the full top flange end
S +3.2 → none; bend lines stop at the other bend's web-side line. 061247: opposite folds → R3.2 relief + two R0.5 at
the flange-side line intersection, lines meet line by line.

**ROOT_CAUSE:** the card defined S in the formed source frame ("flush reference", "actual recessed edge"), and
`bend_end_guard` rebuilt every slit with length T + 0.2 from B, so a correct S −2 slit (4.2) failed and a wrong 2.2
one passed. Bend-end junctions were drawn by hand.

**LESSON:** measure in the flat: B = flange side edge ∩ web edge, S = B − flange-side bend line, positive toward the
web; S > 0 no slit; S ≤ 0 slit from B, length T + 0.2 − S (ends T + 0.2 past the flange-side line). The tool derives
S, the slit, the bend domains and the R = t relief from the proved outline; the guard checks T + 0.2 − S.
