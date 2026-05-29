#!/usr/bin/env bash
# Test Splunk REST login (same credentials as TrustOps / install scripts).
# Does not print the password.
#
#   set +H
#   export SPLUNK_USER='cjalessi'
#   export SPLUNK_PASSWORD='your-password'
#   bash scripts/verify_splunk_login.sh

set -euo pipefail
set +H

SPLUNK_MGMT_URL="${SPLUNK_MGMT_URL:-https://localhost:8089}"
SPLUNK_MGMT_URL="${SPLUNK_MGMT_URL%/}"

if [[ -z "${SPLUNK_USER:-}" || -z "${SPLUNK_PASSWORD:-}" ]]; then
  echo "error: set SPLUNK_USER and SPLUNK_PASSWORD first" >&2
  exit 1
fi

if [[ "${SPLUNK_USER}" == *"@"* ]]; then
  echo "warning: SPLUNK_USER looks like an email — use your Splunk Web username (e.g. cjalessi)" >&2
fi

export SPLUNK_PASSWORD
http_code="$(curl -sk -o /tmp/trustops-splunk-login-test.json -w '%{http_code}' \
  -u "${SPLUNK_USER}:${SPLUNK_PASSWORD}" \
  "${SPLUNK_MGMT_URL}/services/server/info?output_mode=json")"

if [[ "${http_code}" == "200" ]]; then
  version="$(python3 -c "import json; d=json.load(open('/tmp/trustops-splunk-login-test.json')); print(d['entry'][0]['content'].get('version','?'))" 2>/dev/null || echo "?")"
  echo "[OK] Splunk REST login succeeded (HTTP 200, version ${version})"
  echo "     Credentials are valid. If 'splunk install app' still fails, use manual MCP install."
  rm -f /tmp/trustops-splunk-login-test.json
  exit 0
fi

echo "[ERROR] Splunk REST login failed (HTTP ${http_code})" >&2
echo "  Fix username/password to match Splunk Web (http://localhost:8000)." >&2
rm -f /tmp/trustops-splunk-login-test.json
exit 1
