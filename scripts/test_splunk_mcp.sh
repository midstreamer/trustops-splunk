#!/usr/bin/env bash
# Test MCP initialize with SPLUNK_MCP_TOKEN or ~/.splunk_mcp_token
set -euo pipefail
set +H

TOKEN_FILE="${HOME}/.splunk_mcp_token"
# Prefer the minted token file over a stale SPLUNK_MCP_TOKEN in the shell.
if [[ -f "${TOKEN_FILE}" ]]; then
  TOKEN="$(<"${TOKEN_FILE}")"
  if [[ -n "${SPLUNK_MCP_TOKEN:-}" && "${SPLUNK_MCP_TOKEN}" != "${TOKEN}" ]]; then
    echo "note: ignoring SPLUNK_MCP_TOKEN env; using ${TOKEN_FILE} ($(wc -c <"${TOKEN_FILE}") bytes)" >&2
  fi
elif [[ -n "${SPLUNK_MCP_TOKEN:-}" ]]; then
  TOKEN="${SPLUNK_MCP_TOKEN}"
else
  echo "error: run scripts/get_splunk_mcp_token.sh first (or set SPLUNK_MCP_TOKEN)" >&2
  exit 1
fi

echo "token_chars: ${#TOKEN}"
echo "starts_eyJ: $([[ "${TOKEN}" == eyJ* ]] && echo yes || echo no)"
echo "has_double_equals: $([[ "${TOKEN}" == *==* ]] && echo yes || echo no)"

resp="$(curl -sk -X POST "https://localhost:8089/services/mcp" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "Authorization: Bearer ${TOKEN}" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}')"

if echo "${resp}" | grep -q '"result"'; then
  echo "[OK] MCP initialize succeeded"
  echo "${resp}" | head -c 200
  echo "..."
  exit 0
fi

echo "[ERROR] MCP initialize failed"
echo "${resp}"
exit 1
