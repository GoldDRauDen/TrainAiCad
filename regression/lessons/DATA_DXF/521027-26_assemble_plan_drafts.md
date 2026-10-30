# 521023-09 / 521026-03 / 521027-11 / 521027-12 / 521027-22 / 521027-26 — assemble plans written by job-local scripts

FACT: six DATA jobs each wrote their own plan builder (`mkplan.py`, `mk.py`/`mk2.py`, `mkplans.py`, `build_plans.py`,
`gen2.py`): hand-typed piece-id lists (up to 33 ids per outline) plus the same exclusion classes by style (centre
linetype, dashed/phantom, layer 0 colour 0 dimension graphics, the noise bucket, other views, pieces outside the part's
box), and their own digest viewers (`dump.py` x4, `zoom.py`, `render_box.py`, `render_views.py`, `q.py`).

ROOT_CAUSE: `dxf_partition.py` proposed members only and `dxf_digest.py` had no way to list or zoom a view's pieces;
when the outline was not one simple loop (a SPLINE doubled in the DATA, 26-063852) partition took a small pocket as the
outer and called every slot "outside".

LESSON: `dxf_digest.py show` lists / zooms pieces; `dxf_partition.py --plan` drafts the whole plan (members, style
exclusions marked `auto ... confirm`, `todo` for what only the AI decides: unresolved contours, arcs concentric with a
hole, unstyled pieces); an unresolved contour larger than every loop is the outline, no outer is guessed. Tests in
`tests/test_dxf_partition.py`.
