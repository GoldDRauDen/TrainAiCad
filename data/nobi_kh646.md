# KH646 Nobi (アイコクアルファ sheet)

Data for `tools/lookup.py` (AI: never read by eye; call the tool). Rules that use it live in `rules/`.

## Standard steel (90° bend default)

| t | punch R | V | Nobi | min L | source cells |
|---:|---:|---|---:|---:|---|
|0.8|0.6|V8|1.68|7.5|B10:B15|
|1.2|0.6|V8|2.14|7.5|C10:C15|
|1.6|0.6|V8|2.64|7.5|D10:D15|
|2.3|3|V18|4.62|12.8|E10:E15|
|3.2|3|V18|5.78|12.8|F10:F15|
|4.5|3|V25|7.84|17.8|G10:G15|
|6|3|V25|9.78|17.8|I10:I15|
|9|3|V40|14.62|28.4|J10:J15|
|12|6|V80|20.48|57|K10:K15|

## SUS304

| t | punch R | V | Nobi | L range | source |
|---:|---:|---|---:|---|---|
|1|0.6|V8|2.14|standard|B20:B24|
|2|0.6|V12|3.68|standard|C20:C24|
|3|3|V18|5.70|standard|D20:D24|
|5|3|V32|9.58|L ≤750 mm (approved application)|E20:E24|
|5|3|V40|10.20|751–1000 mm|F20:F24|
|6|3|V32|10.72|standard|G20:G24|
|9|6|V80|19.08|standard|H20:H24|

## Special tooling (not returned by lookup; apply only when the drawing/order states it)

- Explicitly ordered R2 tooling ONLY: t2.3 R2/V18 Nobi 4.44, t3.2 R2/V18 Nobi 5.56, t4.5 R2/V25 Nobi 7.72 (C4:F8). Near-bend hole deformation lists t4.5 R3/V18 Nobi 7.48 / min L 12.8 (H9:H15); never infer a tooling change from proximity.
- SUS304 R10 special: t0.8/V25 Nobi 5.44, t1.2/V25 Nobi 6.02, t4 Nobi 10.06; t2.3/3.2/4.5 are 確認 (REVIEW). R10 reach/shape limits are WARN.
