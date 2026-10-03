#!/usr/bin/env bash
# Live inventory + SDK HTTP/QA/checkpoint regression suite.
set -euo pipefail
cd "$(dirname "$0")/.."
inspector=(npx -y @modelcontextprotocol/inspector@2.8.0 --cli --server-url "${MCP_URL:-http://127.0.0.1:8787/mcp}" --transport http)

list=$("${inspector[@]}" --method tools/list)
for name in open_chatgpt_cad_job ingest_cad_file open_cad_job prepare_cad_source get_cad_source_image get_cad_rules submit_cad_evidence route_cad_parts build_canonical_geometry verify_cad_geometry export_dxf audit_dxf get_cad_job get_cad_artifact get_repo_direct_contract export_repo_direct_dxf get_repo_direct_artifact; do
  if ! [[ "$list" == *"$name"* ]]; then
    echo "FAIL: missing tool $name" >&2
    exit 1
  fi
done
echo "PASS: all 17 tools are listed by the live Inspector"

# Run strict portability as an additional diagnostic. The legacy
# prepare_cad_source ROI tuple is a known pre-existing Inspector portability
# error; do not let new repo-direct tools add any further strict errors.
set +e
strict_output=$("${inspector[@]}" --strict --method tools/list 2>&1)
strict_status=$?
set -e
printf '%s\n' "$strict_output"
new_errors=$(printf '%s\n' "$strict_output" | grep '^Error: tool ' | grep -v 'tool "prepare_cad_source"' || true)
if [[ -n "$new_errors" ]]; then
  echo "FAIL: new strict schema portability error(s):" >&2
  printf '%s\n' "$new_errors" >&2
  exit 1
fi
if [[ "$strict_status" -eq 0 ]]; then
  echo "PASS: all tool schemas are strict-portable"
else
  echo "PASS: repo-direct schemas are strict-portable; only the known legacy prepare_cad_source tuple remains"
fi

node --import tsx --test tests/v04.test.ts tests/storage.test.ts
# For real PDF smoke, separately supply an independently read fixture:
# npm run smoke:pdf -- source.pdf fixture.json summary.json
