# LISPCAD Feature Router — chamfer / radius family

Use when explicit C/R callouts, rounded corners, chamfers or source-proved radius families are present or uncertain.

This module adds no new R/C formula. Apply the core source-callout, datum and validation rules. Lock `family + value + quantity/scope + target corner/edge + leader/witness` before canonical geometry.

An explicit C family is straight chamfer geometry and must not be silently converted to R. Explicit source R/C takes precedence over automatic material Laser-R treatment. Material auto-R applies only through the approved `MATERIAL_RULES.md` conditions.
