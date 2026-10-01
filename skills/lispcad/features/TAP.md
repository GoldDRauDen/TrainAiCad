# LISPCAD Feature Router — TAP / metric thread pilot

This routing module adds **no new thread table values**.

When a source family is marked M*, preserve the source thread identity, quantity and datum, then load `../../../references/THREAD_PILOT_TABLE.md` for the approved pilot diameter. Apply the normal HOLE, datum, material and validation rules to the resulting manufacturing geometry.

Thread-to-pilot conversion changes the laser-cut diameter representation only. It does not change source quantity, host face, source witness ownership or the semantic family record.
