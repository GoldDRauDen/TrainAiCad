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

Continue with `route_cad_parts`, `build_canonical_geometry`, and `run_cad_qa`. Route or geometry uncertainty is retained as review flags. Server QA reports checks it cannot yet prove as `N/A`. `export_dxf` ignores caller-supplied QA and rejects any job whose required server checks are not `PASS`; do not treat a successful transport, route, geometry build, or image receipt as production acceptance.

The Inspector regression run is:

```powershell
& 'C:\Program Files\Git\bin\bash.exe' scripts/e2e_inspector.sh
```

That script exercises the live HTTP MCP endpoint, including real PDF ingest/render and forged-QA rejection. The current 56 passing assertions establish transport, source binding, receipt-gated evidence, classification, routing, supported canonical geometry, and fail-closed production export. They do not assert that a production DXF was approved.

## Current production gate

The current implementation does not yet complete a source-to-approved-DXF production run. The machine QA evaluator deliberately leaves material rules, containment, full datum proof, slot semantics, bend domain, and fold-back as `N/A`; export remains blocked until the required checks have deterministic implementations and pass against approved source cases. The DXF audit also checks the exported file hash and structural read-back; an independent geometry-to-source comparison remains a required next gate.
