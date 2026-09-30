# TrainAiCad MCP local runbook

This runbook describes the verified local MCP source-ingest and inspection path. It does not claim production DXF acceptance.

## Start

From the repository root, install the locked Node dependencies and Python bridge dependencies, then start the loopback server:

```powershell
cd services/trainaicad-mcp
npm ci
cd ../..
python -m pip install -r requirements.txt
cd services/trainaicad-mcp
npm run dev
```

The HTTP MCP endpoint is `http://127.0.0.1:8787/mcp`. The service checks the repository's live production release pin before it listens. Set `TRAINAICAD_MCP_PORT`, `TRAINAICAD_MCP_DATA`, or `TRAINAICAD_PYTHON` when using a different local port, data directory, or Python executable.

## Inspect a source

Call `ingest_cad_file` with the drawing bytes, then call `open_cad_job` with the returned file name and SHA-256. If those exact bytes were ingested into the `DRAWING` role, the job is marked `sourceVerified: true`; a descriptor without stored bytes stays unverified. Call `get_cad_source_view` for each evidence page. The result contains the rendered PNG and a server receipt. Include that receipt ID in `source.visualReceiptIds` when calling `submit_cad_evidence`.

For the drawing-to-evidence flow, call `process_cad_job`, give the returned real page images to the vision-capable agent, then call `advance_cad_job` with semantic evidence and the visual receipts. The model supplies interpretation evidence, never CAD coordinates or QA results. The router returns a pinned rule snapshot and a supported next step or an explicit blocker. For `PDF_DATA_RAW`, `advance_cad_job` also harvests the exact bound DATA DXF and returns a hash-addressed source-geometry ledger resource; `get_source_geometry_ledger` reads it back by hash, and `harvest_data_dxf` exposes the low-level parser for debugging. The ledger deliberately remains `REVIEW_REQUIRED`: `$INSUNITS` is recorded but does not prove physical scale, and PDF-to-DATA correspondence/canonical construction still need deterministic checks. Unsupported entities and INSERT arrays are flagged rather than treated as complete geometry. `build_canonical_geometry` is a low-level debug operation, not a substitute for the production orchestrator. `run_cad_qa` ignores caller-supplied QA and rejects any job whose required server checks are not `PASS`.

Local verification commands (run from `services/trainaicad-mcp`) are:

```powershell
npm run doctor
npm run check
npm run test:integration
npm run test:gate
npm run test:e2e
```

`test:e2e` starts the actual local MCP HTTP server and drives it through MCP Inspector. It exercises source ingest/render receipts, classification, routing, DATA DXF harvest and ledger reload, fail-closed QA/export, and artifact guards. The latest local transport run passed 87 assertions. The final source-acceptance gate exits nonzero while any required approved real source fixture is absent; this is intentional and must not be reported as a production E2E pass.

The lower-level Inspector script is:

```powershell
& 'C:\Program Files\Git\bin\bash.exe' scripts/e2e_inspector.sh
```

The DATA DXF harvester preserves raw entity fields, source handles, layers, layout, INSERT ancestry, and forward/inverse transforms for LINE, ARC, CIRCLE, LWPOLYLINE, POLYLINE, POINT, SPLINE, ELLIPSE, and INSERT. It never refits curves. Unhandled entity types, cyclic/deep block nesting, and INSERT arrays are explicit review flags. The ledger is stored by DATA source hash and ledger hash and can be retrieved only while it matches the bound job source.

The export bridge independently reads saved DXF entities back and compares them with the hash-locked serializer payload and manifest, including entity geometry and attributes. Mutation tests cover changed or missing geometry and output metadata. This verifies serialization integrity; it does not prove that model interpretation matches a customer's drawing.

## Current production gate

`npm run doctor` inventories fixtures and current rules. `npm run test:gate` runs the approved regression scripts. The production source acceptance set remains blocked: 14 required cases have 17 missing PDF/DATA/reference role files. The deterministic PDF-only geometry solver, physical scale proof, PDF-to-DATA correspondence, INSERT-array expansion, full material/unfold checks, and positive source-to-approved-DXF canaries remain incomplete. ChatGPT Web attachment/download acceptance also requires a reachable hosted MCP app/tunnel and cannot be inferred from loopback tests. See `docs/reports/2026-09-30-mcp-production-e2e-status.md` for the exact status and commands.
