# TrainAiCad MCP V0.5 — research only

This service experiments with PDF → model observations → deterministic geometry → **REVIEW ONLY / NO CUT DXF**. It does not replace repo-direct production or certify manufacturing. Changes stay inside this service directory.

## Implemented

- Freeze active `AI_ENTRYPOINT.md`, `ROUTER.yaml`, census, coverage, reachable modules and serializer. Entry/router/coverage must agree. Portable compatibility versions are not runtime authorities. Hashes detect changes to a job's immutable rules.
- Route from actual YAML and declared dependencies. Missing census is UNKNOWN; YES/UNKNOWN load their routes. Contradictory NO or a missing feature route fails closed.
- Read real ingested PDF/image bytes; verify SHA256, enumerate pages and cache overviews/crops by source/page/ROI/DPI/rotation/renderer. Deliver actual MCP images. Receipt proves delivery, not correct interpretation.
- Return relevant rule text by path and compact job summaries. Full hashes, evidence, geometry and source checks stay in the checkpoint rather than being repeated to the model at every call.
- Measure named dimension witnesses, linked X/Y datums, overall sizes, circle diameters, containment and overlap. Bind computed reports to geometry/source/rule hashes. Changed geometry, wrong dimensions or unanchored datums block export.
- Serialize checked source-view geometry with the job's frozen repository exporter; reopen the exact saved bytes. File QA_COMPLETE never means PRODUCTION_PASS. Return a real DXF resource or an expiring signed download.
- Optional private Supabase checkpoints preserve sources, frozen rules, images, receipts, job state and outputs across ephemeral-host restarts. Save immutable blobs before committing the index and verify every restored hash.

## Model workflow

| Stage | Tools | Purpose |
|---|---|---|
| Receive | `open_chatgpt_cad_job` (ChatGPT); `ingest_cad_file`, `open_cad_job` (developer) | Actual bytes; PDF_ONLY when no DATA DXF was supplied |
| Read | `prepare_cad_source`, `get_cad_source_image` | Page overviews and targeted crops with both witnesses |
| Load | `get_cad_rules` | Always-on rules first; selected modules after preliminary census |
| Interpret | `submit_cad_evidence`, `route_cad_parts` | Source identities, notes and independent feature inventory |
| Build | `build_canonical_geometry` | Typed source-authorized canonical entities |
| Check | `verify_cad_geometry` | Numeric/source-witness comparison and flat-circle QA |
| Deliver | `export_dxf`, `audit_dxf`, `get_cad_artifact` | Review DXF, actual read-back and file download |
| Resume | `get_cad_job` | Compact checkpoint state |

Inspect every relevant view and geometry-changing note. A crop must establish both dimension witnesses and their physical identities. Work one code through geometry/QA/read-back before expanding a batch. UNKNOWN is not NO. Confidence or OCR absence is not evidence.

`get_cad_rules` without code returns entrypoint/always-on rules. With code, request only the relevant `paths` subset when continuing work. An unresolved final census is tolerated only in explicitly labeled source-view review output and never cleared for manufacturing.

## Local use

Requires Node 22+, Python 3.11+, and the surrounding repository:

```bash
cd services/trainaicad-mcp
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
npm ci
export TRAINAICAD_PYTHON="$PWD/.venv/bin/python"
npm run check
npm run dev
```

Endpoint: `http://127.0.0.1:8787/mcp`. `.env.example` is a template; supply values through shell/host environment. The server does not automatically load `.env`. Cloud bootstrap `TRAINAICAD_AUTH_MODE=setup` exposes only OAuth discovery/health and rejects every CAD request until the owner config is completed.

`npm run check` runs TypeScript and synthetic regression tests. `scripts/e2e_inspector.sh` verifies a live server's Inspector tool inventory and runs the SDK HTTP/QA/checkpoint suite. Real-PDF smoke is separate:

```bash
npm run smoke:pdf -- /absolute/source.pdf /absolute/independently-read-fixture.json /absolute/summary.json
```

The fixture must come from independent source interpretation. Customer PDFs and numeric case fixtures stay outside production rules and the service repository. This script tests real SDK HTTP Request/Response in-process; it does not prove public hosting or an automatic ChatGPT integration.

## Proposed $0 hosting

Use Render Free Docker for research staging and Supabase Free private storage. Free Render sleeps while idle, incurs cold starts and has ephemeral files. Local disk is a cache; durable state needs remote storage. Supabase has quotas and may pause inactive projects.

- [Render Free limitations](https://render.com/docs/free)
- [Supabase pricing](https://supabase.com/pricing)
- [Supabase pausing](https://supabase.com/docs/guides/platform/free-project-pausing)

Run `deploy/supabase.sql` in a dedicated project. Keep the bucket private and the service role key only in backend environment secrets. Use Render Blueprint Path `services/trainaicad-mcp/deploy/render.yaml` with repository-root Docker context. Auto-deploy is disabled. Set `TRAINAICAD_SOURCE_COMMIT` to the actual deployed source commit.

The blueprint requires Supabase OAuth authentication and durable storage. It is a **single-owner staging endpoint**, not a multi-tenant application. Use one process/writer per storage namespace. Keep the signing secret stable across restarts and set the HTTPS origin in `TRAINAICAD_PUBLIC_URL`. Old content-addressed blobs need a retention policy to respect the free storage quota.

**ChatGPT connection implementation prepared, live acceptance pending:** `open_chatgpt_cad_job` advertises native `openai/fileParams` with the exact host file schema and downloads authorized binary bytes. The signed DXF link is returned as both text and `resource_link`. Supabase OAuth discovery, JWKS JWT verification, owner/client allowlists and a Vietnamese consent/login page are implemented. Only the configured OAuth client/owner with a resource-specific audience and `trainaicad_access` claim can use the server. The SQL hook and user account must be configured in the user's dedicated Supabase project. Cloud setup and actual ChatGPT host/file rendering are still unverified.

See [Vietnamese deployment instructions](deploy/HUONG-DAN.md). The blueprint now selects Supabase OAuth; static bearer remains developer testing only. Public deployment fails closed if OAuth settings are incomplete. The Node adapter and MCP handler both allow 36 MiB bodies. No model-generated PDF base64 is needed with native file params. Source URLs are downloaded over HTTPS, not returned/persisted, and each redirect is checked; DNS lookup is pinned to the validated target address.
No cloud project, public endpoint or ChatGPT connection is created by these files. Docker/provider validation requires the user's accounts and a Docker-capable environment; mock storage tests do not prove the cloud deployment.

## Remaining engineering boundaries

- Local release coherence is not proof of remote freshness. The server does not fetch GitHub on every request. Verify/update the deployment commit separately; research pinning does not replace AGENTS.md production synchronization.
- The model supplies source topology and witness identities. Numeric consistency cannot independently certify correct reading. Material-specific automatic R/C, chamfer scope, handwriting priority and complete source reprojection are not certified.
- Export currently accepts checked flat single-face geometry with circles. Unsupported feature QA, curved containment, full signed fold-back and raw-DATA bidirectional QA block export. Existing chain arithmetic remains investigational.
- A DATA SHA and declared origin do not prove DATA entity extraction. PDF_DATA_RAW needs its physical extraction/invariance pipeline before supported export.
- A real-PDF canary for one view/code is not completion of all pages/parts.
- Default source cap: 25 MiB; HTTP body cap: 36 MiB including base64 overhead. Source URL download remains bounded and private targets are blocked by default.
- A failed remote save may follow local mutation. Inspect/recover job state before retrying a transition. There are no multi-writer transactions.
- Jev stays advisory/disabled. No paid OCR or model API is added. Hosting at $0 does not make the user's ChatGPT subscription free.

## V0.5 validation commands

```sh
npm ci
npm run check
npm run smoke:native -- source.pdf independently-read-fixture.json report.json
npm run check:remote -- https://YOUR.onrender.com
```

`smoke:native` uses an ephemeral localhost HTTPS server and a trusted, temporary test CA (OpenSSL required), actual MCP TCP requests and signed DXF download. Private-host allowance is scoped to the test child; it is not enabled in the deployment. It replays independently prepared interpretation data: it does not run or benchmark model vision. `check:remote` is read-only and still requires subsequent actual owner OAuth consent + ChatGPT file tests.
