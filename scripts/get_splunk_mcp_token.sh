#!/usr/bin/env bash
#
# Mint an encrypted Splunk MCP token via REST (same token the MCP app UI should create).
# Writes token to a file; does not print the token to the terminal.
#
#   set +H
#   export SPLUNK_USER='cjalessi'
#   export SPLUNK_PASSWORD='your-password'
#   bash scripts/get_splunk_mcp_token.sh
#
# Output: ~/.splunk_mcp_token (mode 600)
#

set -euo pipefail
set +H

SPLUNK_MGMT_URL="${SPLUNK_MGMT_URL:-https://localhost:8089}"
SPLUNK_MGMT_URL="${SPLUNK_MGMT_URL%/}"
MCP_USER="${SPLUNK_MCP_USER:-${SPLUNK_USER:-cjalessi}}"
OUT_FILE="${SPLUNK_MCP_TOKEN_FILE:-${HOME}/.splunk_mcp_token}"
# URL-encode leading '+' (%2B) or curl treats it as a space in query strings
EXPIRES="${SPLUNK_MCP_EXPIRES:-+720h}"
EXPIRES_ENC="$(python3 -c "import urllib.parse; print(urllib.parse.quote('${EXPIRES}', safe=''))")"

if [[ -z "${SPLUNK_USER:-}" || -z "${SPLUNK_PASSWORD:-}" ]]; then
  echo "error: set SPLUNK_USER and SPLUNK_PASSWORD" >&2
  exit 1
fi

export SPLUNK_PASSWORD

echo "Logging in to Splunk REST..."
login_xml="$(curl -sk -u "${SPLUNK_USER}:${SPLUNK_PASSWORD}" \
  -X POST "${SPLUNK_MGMT_URL}/services/auth/login" \
  -d "username=${SPLUNK_USER}" \
  -d "password=${SPLUNK_PASSWORD}")"

session_key="$(python3 -c "
import sys, xml.etree.ElementTree as ET
root = ET.fromstring(sys.stdin.read())
print(root.findtext('sessionKey') or '')
" <<< "${login_xml}")"

if [[ -z "${session_key}" ]]; then
  echo "error: Splunk login failed (no sessionKey)" >&2
  exit 1
fi

echo "Requesting encrypted MCP token for user ${MCP_USER} (expires ${EXPIRES})..."
resp_file="$(mktemp)"
http_code="$(curl -sk -o "${resp_file}" -w '%{http_code}' \
  -H "Authorization: Splunk ${session_key}" \
  "${SPLUNK_MGMT_URL}/services/mcp_token?output_mode=json&username=${MCP_USER}&expires_on=${EXPIRES_ENC}")"

if [[ "${http_code}" != "200" ]]; then
  echo "error: mcp_token request failed (HTTP ${http_code})" >&2
  head -c 500 "${resp_file}" >&2
  echo >&2
  rm -f "${resp_file}"
  exit 1
fi

python3 -c "
import json, sys
data = json.load(open('${resp_file}'))
token = data.get('token') or (data.get('entry',[{}])[0].get('content',{}).get('token') if data.get('entry') else None)
if not token:
    print('error: no token field in response', file=sys.stderr)
    sys.exit(1)
open('${OUT_FILE}', 'w').write(token)
print('token_chars', len(token))
print('looks_encrypted', '.' in token and '==' in token)
print('starts_eyJ', token.startswith('eyJ'))
" || { rm -f "${resp_file}"; exit 1; }

chmod 600 "${OUT_FILE}"
rm -f "${resp_file}"

echo "[OK] Encrypted MCP token written to ${OUT_FILE}"
echo "     Test: bash scripts/test_splunk_mcp.sh"
echo "     (If you exported SPLUNK_MCP_TOKEN earlier, run: unset SPLUNK_MCP_TOKEN)"
