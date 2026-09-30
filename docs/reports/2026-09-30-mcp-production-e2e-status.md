# TrainAiCad MCP production E2E status

Date: 2026-09-30
Repository: `GoldDRauDen/TrainAiCad`
Branch snapshot: `codex/mcp-production-e2e` at `f84093081bd03286d6758bd77733ecaa5bb2c24d`
Production rule pin: V4.22

## Result

The local MCP transport and defensive export workflow are runnable and tested. The full production E2E acceptance is **not achieved**. Local Inspector assertions pass, but source acceptance deliberately stops because approved real PDF/DATA canaries are missing. No claim is made that a real drawing reached an approved production DXF.

## Implemented and locally verified

- Persistent source manifest with roles, content hashes, verification receipts and atomic writes. Public job results omit local paths; job IDs are traversal-checked.
- `process_cad_job` renders real PDF pages and returns image bytes/receipts; `advance_cad_job` accepts semantic evidence and returns pinned production rules or explicit unsupported-stage blockers. Caller-supplied coordinates and QA are not accepted as proof.
- Source-view cropping, rotation and cache receipts are tied to the source hash, page, crop and DPI.
- `get_cad_artifact` serves the exact audited DXF bytes as an MCP resource only while file, serializer payload, source manifest and rule snapshot hashes remain valid.
- DXF bridge reads the saved composite back and compares physical entities and attributes with the locked canonical serializer input and manifest. Mutation tests exercise geometry and metadata changes.
- Doctor, regression-gate, local HTTP Inspector E2E and Windows/Ubuntu CI workflows are wired into package scripts/workflow.

## Phase status

| Phase | Status | Evidence / remaining work |
|---|---|---|
| 1. Native upload and artifact | Partial | Hash-bound ingest and MCP artifact resource are implemented; ChatGPT Web native attachment delivery/download remains untested and unverified. |
| 2. Production orchestrator | Partial | `process_cad_job` / `advance_cad_job` and explicit unsupported-stage response exist; full production state machine is not implemented. |
| 3. CAD evidence V2 and census | Partial | V1 semantic evidence, source receipts, page/code manifest fields, crop/rotation/cache exist; the complete V2 evidence schema and census are missing. |
| 4. Customer DATA DXF harvester | Blocked/incomplete | Source binding/classification exists; full supported entity ledger, transforms and scale proof do not. |
| 5. PDF-only deterministic solver | Blocked/incomplete | Router explicitly flags unsupported solver; no production coordinate solver. |
| 6. Executable CURRENT rule engine | Partial | Immutable content-hashed rule snapshots and routing dependencies exist; production execution of every listed rule family is not complete. |
| 7. Manufacturing QA V2 and reprojection | Blocked/incomplete | Caller QA is rejected and some checks run; dual-source reprojection and full manufacturing checks are not complete. |
| 8. Physical DXF read-back | Partial | Saved entities are compared with locked serializer payload/manifest; independent source/canonical reprojection is still missing. |
| 9. Face graph and bend engine | Partial | Existing regression gates pass; requested full L/U/multi-axis/BOXMET production fold-back is not implemented. |
| 10. Composite, uncertainty and audit modes | Partial | Fail-closed artifact/export path exists; complete all-code composite contract and per-code audit outcomes remain unfinished. |
| 11. Revision and persistence | Partial | Atomic persistence and stale-PASS migration/guards exist; full immutable revision lineage, idempotent retry and conflict recovery are incomplete. |
| 12. True E2E and CI | Partial | Local MCP HTTP Inspector passes 69 checks; source gate reports SOURCE_UNAVAILABLE; Windows/Ubuntu CI is configured but not run, and real ChatGPT Web E2E is unavailable. |

## Verification on this Windows machine

- `npm run check`: TypeScript compile and **44/44 unit tests passed**.
- `python -m pytest -q`: **90 passed**.
- `npm run test:gate`: **7/7 approved regression scripts passed**, including the acute-bend geometry derivation.
- `npm run test:integration`: **69/69 local MCP HTTP Inspector assertions passed**.
- `npm run test:e2e`: MCP Inspector transport/flow assertions pass; final source-acceptance check exits with a blocked status by design while required source fixtures are absent.
- `git diff --check`: clean (Git may report expected LF-to-CRLF conversion warnings).
- No GitHub Actions run was triggered, and this snapshot was not pushed.

## Remaining blockers for true production E2E

1. The acceptance manifest has 14 cases, but **17 required source-role paths are not declared/present** (for example, `DRAWING`, `DATA_DXF`, `AI_DXF` and `REFERENCE_DXF` roles). The gate reports these as `SOURCE_UNAVAILABLE`; it does not invent filenames. Fill the approved fixture paths/roles in `regression/production-e2e/acceptance-set.json`, provide the source bytes, and rerun `npm run test:e2e`.
2. The PDF-only deterministic geometry solver is incomplete. The orchestrator flags this rather than making up coordinates. General customer DATA-DXF entity harvesting and provenance preservation also remain incomplete.
3. Full material, datum, contour, bend/unfold and fold-back QA is not implemented for all requested source classes. Current regression passes do not establish those production checks.
4. Positive independently reviewed source-to-DXF canaries are unavailable, so the pipeline has no honest basis to issue `PRODUCTION_PASS` for the requested customer drawing classes.
5. ChatGPT Web's native attachment-to-MCP invocation and artifact download were not tested. This local loopback test is not evidence of remote client reachability; hosted MCP application and secure tunnel/client setup are separate requirements.
6. Ubuntu CI is configured but unexecuted. Run CI after approved fixtures are provided and the source gate passes.

## Next executable sequence

1. Add only approved fixture files matching `regression/production-e2e/acceptance-set.json`; preserve source hashes and role labels.
2. Implement and test DATA-DXF harvesting against real approved data, retaining unsupported entities as explicit flags.
3. Complete one representative plate source through visual evidence, deterministic geometry, all applicable QA, DXF serialization, independent read-back and reference comparison. Do not expand to other classes until this canary passes.
4. Add canaries for each requested part family, then negative/mutation cases; rerun unit, Python, regression-gate and full source-acceptance E2E.
5. Run Windows and Ubuntu CI. Separately configure hosted MCP/Secure MCP Tunnel and verify the actual ChatGPT Web upload, tool call and exact artifact download.

## Reproduction

From `services/trainaicad-mcp`, run `npm ci`, `npm run doctor`, `npm run check`, `npm run test:integration`, `npm run test:gate`, then `npm run test:e2e`. The final command is expected to fail closed until all acceptance source-role files exist.
