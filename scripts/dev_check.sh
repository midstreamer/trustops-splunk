#!/usr/bin/env bash
#
# TrustOps developer sanity check — does NOT start services.
# Exits non-zero only if Splunk is not running or SPLUNK_USER / SPLUNK_PASSWORD is unset.
#

set -uo pipefail

SPLUNK_HOME="${SPLUNK_HOME:-/opt/splunk}"
SPLUNK_BIN="${SPLUNK_HOME}/bin/splunk"
BACKEND_HEALTH_URL="${BACKEND_HEALTH_URL:-http://localhost:8001/health}"
FRONTEND_URL="${FRONTEND_URL:-http://localhost:5173/}"

EXIT_CODE=0

echo "=== TrustOps dev check ==="
echo ""

# --- Required environment (fail if missing) ---
if [[ -z "${SPLUNK_USER:-}" ]]; then
  echo "[!] SPLUNK_USER is not set (required for backend / Splunk API)."
  EXIT_CODE=1
else
  echo "[OK] SPLUNK_USER is set (value not shown)."
fi

if [[ -z "${SPLUNK_PASSWORD:-}" ]]; then
  echo "[!] SPLUNK_PASSWORD is not set (required for backend / Splunk API)."
  EXIT_CODE=1
else
  echo "[OK] SPLUNK_PASSWORD is set (value never printed)."
fi

echo ""

# --- Splunk process status (fail if not running) ---
if [[ ! -x "${SPLUNK_BIN}" ]]; then
  echo "[!] Splunk binary not found or not executable: ${SPLUNK_BIN}"
  EXIT_CODE=1
else
  splunk_ok=0
  if sudo -n -u splunk "${SPLUNK_BIN}" status &>/dev/null; then
    echo "[OK] Splunk: splunkd running (checked via: sudo -n -u splunk splunk status)."
    splunk_ok=1
  elif "${SPLUNK_BIN}" status &>/dev/null; then
    echo "[OK] Splunk: splunkd running (checked as current user: splunk status)."
    splunk_ok=1
  fi

  if [[ "${splunk_ok}" -eq 0 ]]; then
    echo "[!] Splunk does not appear to be running (or status could not be verified)."
    echo "    Try: sudo -u splunk ${SPLUNK_BIN} start"
    EXIT_CODE=1
  fi
fi

echo ""

# --- Optional reachability checks (informational only; do not change exit code) ---
if curl -sf --max-time 3 "${BACKEND_HEALTH_URL}" &>/dev/null; then
  echo "[OK] Backend health reachable: ${BACKEND_HEALTH_URL}"
else
  echo "[i] Backend not reachable yet: ${BACKEND_HEALTH_URL}"
  echo "    Start with: cd backend && source .venv/bin/activate && uvicorn app:app --reload --host 0.0.0.0 --port 8001"
fi

http_code="$(curl -s -o /dev/null -w "%{http_code}" --max-time 3 "${FRONTEND_URL}" 2>/dev/null || echo 000)"
if [[ "${http_code}" == "200" ]]; then
  echo "[OK] Frontend reachable (HTTP ${http_code}): ${FRONTEND_URL}"
else
  echo "[i] Frontend not reachable yet (HTTP ${http_code}): ${FRONTEND_URL}"
  echo "    Start with: cd frontend && npm run dev"
fi

echo ""
echo "=== Summary ==="
if [[ "${EXIT_CODE}" -eq 0 ]]; then
  echo "Required checks passed (Splunk running + credentials present)."
else
  echo "One or more required checks failed (see [!] above)."
fi

exit "${EXIT_CODE}"
