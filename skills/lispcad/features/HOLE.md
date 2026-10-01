# LISPCAD Feature Router — HOLE

This routing module adds **no new hole formula**. Use it whenever the census finds or suspects a round-hole family.

Load and apply the existing authoritative rules in:
- `../core/DRAWING_READING.md` for callout identity, quantity, cancellation and source reading;
- `../core/DATUM_DIMENSION.md` for witness/datum ownership and coordinates;
- `../core/VALIDATION.md` for family-count, containment and semantic checks;
- `../../../references/MATERIAL_RULES.md` when material/thickness affects cut-hole versus POINT/PIASU behavior.

Keep each explicit Ø family independent. A hole center, diameter, quantity or datum may not be borrowed from a neighboring family without source evidence.
