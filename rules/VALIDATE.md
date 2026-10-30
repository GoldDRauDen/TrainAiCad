# VALIDATE — checks before export (L3, always)

**PASS = executed and succeeded.** Not run → FLAG/WARN/N/A. FAIL blocks PASS; anything unresolved is still drawn (`OUTPUT.md` §5). Read-back proves serialization, never source meaning. The exporter runs the machine gates; this card is what only you can check.

## 1. Geometry
Outer closed, CCW, no self-intersection; cut-outs CW; every closed hole/slot inside material (open notches excepted); no placeholder rectangle (right bbox + wrong topology = FAIL); a "retain the piece" note never clones a second cut-out.

## 2. Source semantics (every used number)
- Origin/axis proved per view; datum path connected; dimension type classified; endpoint identity right; chain closes to the overall; reference dims keep their datum (`DATUM.md`).
- Every explicit R/C matches the source tuple family + value + qty + corner class (C drawn as R = FAIL).
- Slot length semantics and anchor (`SLOT.md`); each hole family counted and traced on its own.
- Material = the slip's (`tools/slip.py`): a different FAMILY (SS/SUS/AL/CU) on the drawing → FLAG + note; the same family is silent.
- `SLOT_WITNESS_FAIL` (a nearby number used as W/R/length) · `MIRROR_SCOPE_FAIL` (mirror without proof) · `DATUM_WITNESS_FAIL` (coordinate not from its proved datum) · `KEGAKI_SCOPE_FAIL` (CUT PASS never implies KEGAKI PASS) · `STALE_PREVIEW_FAIL` (resolved mark still Magenta).

## 3. Completeness
- Source-active families (CUT, HOLE/SLOT, BEND, KEGAKI, PIASU, SLIT/RELIEF, RIB, R/C, forming) vs canonical vs DXF: a family that vanished without cancellation is FAIL.
- Every explicit quantity (`n-Ø`, `n-M`, `n-R`, `n-C`, repeated notches) = produced count; tap→pilot changes Ø, not count. Count by topology, not colour: slit LINE+ARC+LINE = 1 feature, 3 entities. Truly overlapping holes = one union contour, quantities kept.
- Notes → families → routes → canonical → DXF closes (`READ_SOURCE.md` §3).

## 4. Bent parts
Local-face → flat transform for every feature; face order proved independently of the total; bend lines only over material; fold-back reproduces faces, attachment edges, signs, ODs, feature hosts/offsets; every bend has a Nobi source or `SPLIT_FLANGE_10MM`; never a 90° row on a non-90° bend (`BEND.md`).

## 5. Holistic challenge (`tools/holistic_engineering_guard.py`, run before canonical)
Raise `ENGINEERING_ANOMALY_DETECTED`, re-open the source and re-solve when:
- substantial DATA or several proved views but few/no proved members; a family YES/UNKNOWN without a group/member;
- a printed/handwritten flat or Nobi chain closes but the part went VIEWS_ONLY; VIEWS_ONLY before every source-supported face graph was tried; a local unknown escalated to VIEWS_ONLY;
- a source view/DATA member has no role; output much simpler than the source inventory; PASS only by ledger self-equality;
- two codes own the same complete source bundle (`PART_IDENTITY_COLLISION`);
- a shared bend-edge length reused as a face/blank extent;
- assembly views exist but no weld-site inventory; a KH851 weld site without a KEGAKI member/FLAG.

Unresolved part names its blocker: `TRUE_SOURCE_AMBIGUITY` (several interpretations survive source exhaustion) · `AI_INTERPRETATION_GAP` (evidence exists, not yet solved — never blame the source) · `SOURCE_MEMBER_CENSUS_GAP` · `PART_IDENTITY_GAP` · `GEOMETRY_DECODE_GAP` · `ROUTING_COVERAGE_GAP` · `CUSTOMER_CONFIRMATION_PENDING`. Record: object, candidates, evidence used / not yet used, result per candidate, remaining DOF.

Final sanity question before canonical: unused view? unowned number? suspiciously simple output? untested candidate? Any yes → back to the source.

## 6. Cross-feature
Hole/KEGAKI on a bent face moves with its face and keeps its physical edge identity · slit/relief vs bend domain (one mechanism per junction) · explicit R/C beats auto Laser R · tap→pilot keeps quantity and datum · cancellation scoped to its callout · RIB cut and main-part KEGAKI are separate families · DATA cleanup never redraws unchanged DATA · pair/対称 codes: `pair_consistency.py` shows no unexplained difference.

## 7. Manufacturing attributes
HL (ヘアライン) with grain direction relative to the part unproved → `status=REVIEW`, `review_reason=HL_DIRECTION_UNPROVED`, full geometry, no individual PASS cut (Excel `横目` alone is not proof).

## 8. Feasibility = advisory only (never move geometry, never FLAG)
Bridge/web ≥ t · adjacent piercings ≥ 10 mm · hole edge to bend ≥ 2t + R · bend die minimum L/Z (`lookup.py tooling`) → internal WARN. Real self-intersection, containment, hole capacity and unproved dimensions still FLAG.

## 9. Report the checks
One compact line when all pass, then every FAIL / FLAG / actionable WARN / question. No long PASS lists.

## Lessons
`regression/lessons/VALIDATE/` — 521007-07 (holistic challenge, identity collision, reference firewall).
