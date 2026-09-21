# LISPCAD Feature — Chamfer / Radius

Source: approved V4.3 production baseline.

### 4.5 Corner Filleting & Chamfer Baking
- **No Global Polyline Fillets**: Do NOT apply global fillet operations to outer boundaries containing internal notches.
- **Corner Topology Classification First**: Before applying any `C` or `R` callout, classify the target corner relative to the **material region** as:
  - **Convex / outside corner (góc lồi)**: material interior angle $< 180^\circ$.
  - **Concave / re-entrant corner (góc lõm)**: material interior angle $> 180^\circ$.
  Do not decide this from screen direction alone; use boundary orientation and which side of the boundary contains material.
- **Leader Arrow = Representative Feature, not blind global scope**: The leader/arrow location is primary evidence for the intended corner class. For callouts such as `6-C5`, `2-C10`, or `8-R10`, identify equivalent candidate corners by topology, symmetry, repeated geometry, and callout count. The final number of assigned corners MUST match the `n-` quantity. If more than one plausible assignment remains, flag and ask; do not spread the callout to arbitrary nearby corners.
- **Do Not Merge Feature Types**: `C` is a straight chamfer and `R` is an arc/fillet. Never encode a chamfer as a bulged arc or an R as a straight bevel.
- **Outer Corner Fillets**: Apply fillet radius ($R$) ONLY to vertices explicitly supported by the callout/topology assignment. Bake fillets into polyline bulges:
  $$\text{bulge} = \tan\left(\frac{\text{turn\_angle}}{4}\right) \quad (\text{for } 90^\circ, \text{bulge} \approx 0.41421356)$$
- **Internal Corners Default to R0**: Internal corners of $U$-shaped notches, tabs, or slots MUST remain sharp ($R=0$) unless explicitly specified. When an internal $R$ is present, record it in `internal_fillets`.
- **Chamfers**: Bake chamfers by replacing the corner vertex with two distinct vertices offset back along adjacent edges by chamfer size $C$, with bulge $0.0$.
- **Reference-DXF R0.5 Exception**: In Section 2.4 ground-truth mode, an uncalled-out `R0.5` that exists only in the DXF is a confirmed later shop addition and MUST be ignored for generation/comparison. Preserve the PDF corner as R0 unless the PDF itself explicitly specifies R0.5 or the current user explicitly overrides this rule for the job.
