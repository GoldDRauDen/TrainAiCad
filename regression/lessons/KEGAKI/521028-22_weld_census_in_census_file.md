# 521028-17 / 521028-22 — the KH851 weld census was injected by job-local scripts

FACT: both jobs wrote the weld-site census twice: once in `census_<code>.json` (L1) and again by a script
(`inject_weld.py`, a python block in `build.sh`) that copied `source_assembly_view_ids` / `source_weld_site_ids` /
`weld_site_census` onto the built canonical job, prefixed the mark ids with the code and flipped unresolved marks to
Magenta / no geometry, before exporting by hand instead of with `run_job.py`.

ROOT_CAUSE: the spec builder carried no weld census and no FLAGGED kegaki, so every KH851 job needed a patch step.

LESSON: the census file is the one place: the spec build copies the weld keys from `census_<code>.json` (next to the
spec or one folder up) or from the spec part, a short mark id (`K1`) names the part's kegaki id, and a `kegaki` item
with `flag:` is an unresolved mark (Magenta estimate, or no lines = `FLAGGED_NO_GEOMETRY`). Rebuilding 521028-22 with
`run_job.py` gives the same census as the hand patch. Test `tests/test_weld_census_spec.py`.
