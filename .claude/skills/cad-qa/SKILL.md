---
name: cad-qa
description: Reverse QA of an existing DXF against its source in TrainAiCad. Use only when the user explicitly says QA, "QA file này", "QA ngược DXF này", or asks to audit/check an already-made DXF.
---

Read `rules/QA_REVERSE.md` and follow it. Decode both the source DATA and the audit target with `python tools/dxf_census.py <file.dxf>`; then route the source with `rules/CENSUS.md` + `python tools/resolve_rules.py census.json` and read the cards it lists. Do not edit the audited DXF or the repo.
