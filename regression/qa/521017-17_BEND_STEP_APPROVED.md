# 521017-17 / 061099 positive bend-end steps

Approved by user on 2026-10-17. Source: `521017-17.pdf`, page 6, SHA-256
`ef18f1eeaee9bae29cf3b1063d7122f3079768550537710e7edc140a8cc8c321`.

**FACT:** User confirmed both junctions protrude by sheet thickness t2: join
the bends normally; no slit or R=t corner escape is required. The part has
five faces, four bends, eight diameter7 holes, and six C5 corners.

**ROOT_CAUSE:** The source solve did not close the positive step from the
40-wide web and44OD upper channel, then confused different fold directions
with a physical opposite-fold intersection. A correct scalar S helper and
self-consistent source/canonical ledgers could not detect that wrong choice.

**LESSON:** Resolve each actual edge and signed local step independently
before selecting a relief mechanism. Positive S (including S=t) in the
90-degree bend-end mechanism needs no added relief. A change of fold sign
or overlapping virtual-sharp dashed lines does not prove physical crossing.

## Hand-checked source and unfold closure

- Main chain: 50 + (62+2) + (120+2) -2x3.68 =228.64.
- Channel chain: 15 +44 +15 -2x3.68 =66.64.
- Both junctions: S=+2, with the positive direction reversed at the upper site.
- Main bend pairs X46.32/50 and106.64/110.32 span the40-wide web.
- Lip bend pairs Y11.32/15 and51.64/55.32 span X108.64..228.64.
- Web side edges Y13.32 and53.32 remain inset2 from the corresponding
  channel outside virtual lines. Lip roots start2 beyond X106.64.

Fixture `regression/bend/521017-17_061099_positive_step.json` retains the
V4.34 canonical source model and separate formed-view edge witnesses.
`tests/test_bend_end_step_guard.py` checks wrong S, spurious R=t, missing
site/edge/direction proof, rotation/reflection, and actual saved DXF
(30 manufacturing entities,8 CIRCLE,8 DASHED LINE; no Green/Magenta relief).
Flush/recessed and separately scoped mechanism controls retain prior rules.
Negative controls reject an unrelated contour/hole as relief, unscoped non90
relief, oblique crossing domains, wrong actual-edge identity, incorrect depth
and disconnected slit geometry before a DXF is saved.
The numerical fixture values are evidence for this case, not production defaults.
