# 521005-02 — face creation needs bend evidence (approved 2026-10-05)

Rule: `rules/BEND.md` §2.

## 7. 521005-02 regression intent

- `26-057867`: control case — one source-proved bend; simple full-width flange remains valid.
- `26-057869` / `26-057870`: local flange only; approved/reference bend pair spans 555 mm, not the whole 1025 mm part width. Complex neighboring contour remains on the main face.
- `26-057871` / `26-057872`: sloped outer contour is part of the same planar face; only the proved bottom flange becomes a new face. The R10-trimmed physical bbox is smaller than the theoretical-sharp overall, so bbox mismatch alone is not a source/reference error.

Job-specific coordinates are regression evidence only and must never become generic construction coordinates.
