# LISPCAD Feature Router — straight slot

Use for straight stadium/obround slots. This routing module adds no new slot formula.

Apply the existing source-witness, datum and validation rules from the core modules. Lock whether each printed length is total slot length, center distance, local face distance or another dimension class before geometry. Width/end-radius/quantity must come from the actual callout and witnesses; do not substitute a nearby dimension.

For circular-arc center paths, route to `CURVED_SLOT.md` instead.
