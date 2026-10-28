# 521028-17 — a wider ear behind a narrower neck is a step with S > 0

Rule: `rules/SLIT_RELIEF.md` §3; executable `tools/bend_corner.py` (`end_step` shoulder), `tests/test_bend_end_shoulder.py`. Approved by the user (DUYỆT).

## FACT
- 26-063995 (t6, 88°, Nobi 9.35 handwritten): web 44, flange ear 59 wide only in the last 30 mm. OD2 40.4 − 30 = 10.4 = shoulder − line1 (217.35 − 206.95).
- I flagged a missing slit. The sample has none and flags only the unprinted ear length (30, red).

## ROOT_CAUSE
`TOOL_SILENT_NO_SITE` + role swap: the straight edge ran past the zone, `end_step` returned "no corner" and wrote no site; I then read the roles backwards (S ≤ 0) and invented a FLAG. Below 90° the relief depth also crashed (`slit_depth_gt90`).

## LESSON
1. Web = the face that continues beyond the bend end; S = shoulder − the other face's bend line toward the web. Shoulder standing back from the neck: S > 0, no slit, site recorded as NO_RELIEF.
2. The ear length itself is a source dimension; when unprinted it is an integer estimate with a local FLAG.
