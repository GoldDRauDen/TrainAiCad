# Laser corner R / hole capacity / 白ピアス (Rule_Bo_R&Hole.xlsx, Bo_R_Hole, 2026.07.30)

Data for `tools/lookup.py` (AI: never read by eye; call the tool). Rules that use it live in `rules/`.
A dash is a BLANK cell, not zero.

## Original worksheet entries (a dash means the CELL IS BLANK, not zero)

| Excel row | Material group | t Min | t Max | Laser corner condition | Laser R | Minimum cut-hole diameter | 白ピアス capacity |
|---:|---|---:|---:|---|---|---|:---:|
| 4 | SS | — | 3.2 | outside corner ≤90° | R0.5 | ≥ t/2 | × |
| 5 | SS | 4 | 5 | outside corner ≤90° | R0.5 | — | 〇 |
| 6 | SS | 6 | 9 | outside corner ≤90° | R2 | — | 〇 |
| 7 | SS | 10 | 12 | — | none (無) | — | 〇 |
| 8 | SS | 16 | 16 | — | none (無) | ≥ t | 〇 |
| 9 | SS | 19 | — | outer material perimeter corners only (2026-10-12 active scope; original 内外角/面取含) | R3 (※3 ignored) | — | 〇 |
| 10 | SUS, 他 | — | 5 | outside corner ≤90° | R0.5 | ≥ t/2 | × |
| 11 | SUS, 他 | 6 | 6 | outside corner ≤90° | R0.5 | — | 〇 |
| 12 | SUS, 他 | 7 | 8 | — | none (無) | — | 〇 |
| 13 | SUS, 他 | 9 | 12 | — | none (無) | — | 〇 |
| 14 | SUS, 他 | 14 | 14 | — | none (無) | — | 〇 |
| 15 | SUS, 他 | 15 | 16 | — | none (無) | ≥ Ø10 | 〇 |
| 16 | SUS, 他 | 19 | 19 | — | none (無) | — | 〇 |
| 17 | SUS, 他 | 20 | — | — | none (無) | ≥ t | 〇 |
| 18 | AL | — | 0.5 | outside corner ≤90° | R0.5 | ≥ 0.8t | × |
| 19 | AL | — | 6 | outside corner ≤90° | R0.5 | — | 〇 |
| 20 | AL | 7 | 8 | — | none (無) | — | 〇 |
| 21 | AL | 9 | — | — | none (無) | — | 〇 |
| 22 | AL | 12 | — | — | none (無) | — | 〇 |
| 23 | AL | 16 | — | — | none (無) | ≥ t | 〇 |
| 24 | AL | 19 | — | — | none (無) | — | 〇 |
| 25 | Cu / Brass (銅・真ちゅう) | — | 5 | outside corner ≤90° | R0.5 | ≥ t/2 | × |
| 26 | Cu / Brass; ※ケガキ不可 | 6 | — | outside corner ≤90° | — [UNSPECIFIED] | ≥ t | × |
