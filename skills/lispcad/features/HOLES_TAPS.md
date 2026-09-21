# LISPCAD Feature — Holes / Taps

Source: approved V4.3 production baseline.

- **Round Holes**: Extracted as `CIRCLE` entities. Threaded holes (`M*`) extract pilot diameters from the standard lookup table (Section 7.1).
- **Countersinks & Counterbores**: Extracted using the smallest pilot/through-hole diameter for laser cutting.


- **Polygonal Cutouts**: Extracted as closed `LWPOLYLINE`s using explicit vertex arrays.

For metric tapped-hole pilot diameters, use `../../../references/THREAD_PILOT_TABLE.md`.

Feature-family count, datum trace, containment, and feasibility checks remain mandatory under core validation.
