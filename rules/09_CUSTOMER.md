# 09 — CUSTOMER-SCOPED CAD RULES | Production rules V4.34

> Customer exceptions are scoped by verified numeric customer ID. Per-customer machine-readable policy stays in CUSTOMER_CAD_RULES.yaml.

<!-- BEGIN MODULE: references/CAD_CUSTOMER_POLICY.md -->
# CAD customer rule authority — approved 2026-10-12
Source `CAD_顧客別 0911 .xlsm` **only** worksheet `顧客別情報一覧`. Sanitized, CAD-only records live in `CUSTOMER_CAD_RULES.yaml`. No personnel, contact, sales, CAD-time, repeat-job accounting or NC toolpath data may enter production rules.

- Identify customer from **numeric customer code in JOB STATISTICS**, not inferred Japanese name. No code => **general CAD rules**, not automatic REVIEW. The unrelated 'job family 646 requires DATA' instruction is not a customer-code identifier.
- KH851 weld-location requirement: every independently proved weld site requires KEGAKI even without a printed marking callout. See WELD_SITE_KEGAKI_CLOSURE.md. Missing site/mark is not cured by syntactically valid DXF or a complete ledger over an incomplete source census.
- Source-specific correction/handwriting for a physical parameter > applicable customer exception > standard manufacturing table. For explicit handwritten Nobi, calculate from handwriting; discrepancy from table is **nonblocking audit**, not a blocking FLAG.
- `DATA_NO_DIM_COMPARE` means customer DATA controls dimensions without generic numeric-only PDF/DATA conflict flags. It **never waives** source hole count/type/M/Ø/position, full feature census, topology, revisions, DATA physical harvest, canonical completeness, unchanged geometry or DXF read-back. Missing or contradictory source holes => local REVIEW; don't invent the hole.
- `PDF_PRIORITY`: PDF controls *conflicting physical parameter*, preserving DATA provenance; `CONFIRM_CONFLICT`: local REVIEW. Do not globally disable source-semantic QA. Select each exception by scoped physical parameter.
- KH646 only when code 646 is printed in job summary. Use `AIKOKU_646_NOBI.md`; don't fill nonexistent profile rows from `旭26-9-18`. No Nobi => local REVIEW and retain proved orthographic/separated geometry; on non-90° bends without a proved Nobi follow existing separated-view/manual reassembly rule.
- Geometrically correct drawings can PASS with advisory WARN for die minimum L/Z, machine reach and process capability. WARN never authorizes editing PDF geometry.
- **NC is deferred:** no lead-in/out, pierce start paths, joint or NC routing in the CAD CUT DXF. CAD PIERCING/white piercing/POINT/KEGAKI from current rules still apply. Welding after laser isn't a CUT.
- Struck-through rich text is OBSOLETE; AS済 only sync metadata. Exclude rules in unrequested auxiliary sheets; when an unexamined cross-sheet rule is necessary, local REVIEW.
- Catalog records are a manually vetted **subset** of customer CAD notes, not an assertion that all 469 rows are covered. Noncatalogued codes continue under general rules and the source manufacturing-note census. Complete remaining CAD-only extraction before claiming full-workbook coverage; do not publish workbook personal/management content.
<!-- END MODULE: references/CAD_CUSTOMER_POLICY.md -->

---

<!-- BEGIN MODULE: references/AIKOKU_646_NOBI.md -->
# KH 646 — customer bend Nobi
Source: `伸び下穴経路一覧.xlsx`, `アイコクアルファ`. Apply **only if numeric customer_code=646** on the job statistics sheet. Do not confuse with unrelated historical job-family '646' DATA handling.

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

For explicitly ordered R2 tooling ONLY: t2.3 R2/V18 Nobi4.44, t3.2 R2/V18 Nobi5.56, t4.5 R2/V25 Nobi7.72 (C4:F8). When a near-bend hole deforms, t4.5 R3/V18 Nobi7.48/minL12.8 is listed in H9:H15, but **do not infer** tooling change merely from proximity.

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

R10 special steel: t0.8/V25/Nobi5.44, t1.2/V25/Nobi6.02; t2.3/3.2/4.5 are 確認 (REVIEW). R10 SUS304 t4 Nobi10.06. R10 machine reach/shape restrictions are manufacturing WARN if shape otherwise proved. For missing Nobi or out-of-range length, local REVIEW, **no** fallback to general 旭 Nobi. For unclear non-90° bend, retain separate views for manual reassembly, not 90° Nobi. Clear handwritten PDF Nobi overrides this table; difference recorded only as nonblocking evidence.
<!-- END MODULE: references/AIKOKU_646_NOBI.md -->
