#!/usr/bin/env bash
# Live inventory + SDK HTTP/QA/checkpoint regression suite.
set -euo pipefail
cd "$(dirname "$0")/.."
inspector=(npx -y @modelcontextprotocol/inspector@2.8.0 --cli --server-url "${MCP_URL:-http://127.0.0.1:8787/mcp}" --transport http)
# Strict portability is required because the live consumer is ChatGPT, not only the local SDK.
list=$("${inspector[@]}" --strict --method tools/list)
for name in open_chatgpt_cad_job ingest_cad_file open_cad_job prepare_cad_source get_cad_source_image get_cad_rules submit_cad_evidence route_cad_parts build_canonical_geometry verify_cad_geometry export_dxf audit_dxf get_cad_job get_cad_artifact get_repo_direct_contract export_repo_direct_dxf get_repo_direct_artifact; do
  if ! [[ "$list" == *"$name"* ]]; then
    echo "FAIL: missing tool $name" >&2
    exit 1
  fi
done
echo "PASS: all 17 tools are listed by the live Inspector with strict schema portability"
node --import tsx --test tests/v04.test.ts tests/storage.test.ts
# For real PDF smoke, separately supply an independently read fixture:
# npm run smoke:pdf -- source.pdf fixture.json summary.json
