#!/usr/bin/env bash
# Deploy TrustOps API to Railway (requires: railway login, Splunk reachable from cloud).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="${ROOT}/backend/.env"

if ! command -v railway >/dev/null 2>&1; then
  echo "error: Railway CLI not found. Install: npm install -g @railway/cli" >&2
  exit 1
fi

if ! railway whoami >/dev/null 2>&1; then
  echo "error: Not logged in. Run: railway login" >&2
  exit 1
fi

cd "${ROOT}"

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "error: Missing ${ENV_FILE} — set SPLUNK_USER and SPLUNK_PASSWORD." >&2
  exit 1
fi

set -a
# shellcheck source=/dev/null
source "${ENV_FILE}"
set +a

if [[ -z "${SPLUNK_USER:-}" || -z "${SPLUNK_PASSWORD:-}" ]]; then
  echo "error: SPLUNK_USER and SPLUNK_PASSWORD must be set in backend/.env" >&2
  exit 1
fi

if [[ "${SPLUNK_HOST:-localhost}" == "localhost" || "${SPLUNK_HOST:-}" == "127.0.0.1" ]]; then
  echo "warning: SPLUNK_HOST is local. Railway cannot reach localhost." >&2
  echo "         Expose Splunk with ngrok/cloudflared or use Splunk Cloud, then set:" >&2
  echo "           SPLUNK_HOST=your-tunnel-hostname" >&2
  echo "           SPLUNK_PORT=443" >&2
  echo "           SPLUNK_SCHEME=https" >&2
  read -r -p "Continue deploy anyway? [y/N] " ans
  [[ "${ans,,}" == "y" ]] || exit 1
fi

if [[ ! -f "${ROOT}/.railway/config.json" ]]; then
  echo "Linking Railway project (first time)..."
  railway init --name trustops-splunk-api
fi

echo "Setting Railway variables..."
railway variables set \
  SPLUNK_USER="${SPLUNK_USER}" \
  SPLUNK_PASSWORD="${SPLUNK_PASSWORD}" \
  SPLUNK_HOST="${SPLUNK_HOST:-localhost}" \
  SPLUNK_PORT="${SPLUNK_PORT:-8089}" \
  SPLUNK_SCHEME="${SPLUNK_SCHEME:-https}" \
  SPLUNK_VERIFY_SSL="${SPLUNK_VERIFY_SSL:-false}" \
  SPLUNK_AUTH_INDEX="${SPLUNK_AUTH_INDEX:-trustops}" \
  SPLUNK_DECISION_INDEX="${SPLUNK_DECISION_INDEX:-trustops_decisions}" \
  SPLUNK_AGENT_RUN_INDEX="${SPLUNK_AGENT_RUN_INDEX:-trustops_agent_runs}" \
  TRUSTOPS_STARTUP_SMOKE_TEST=skip \
  TRUSTOPS_CORS_ORIGINS="https://midstreamer.github.io"

echo "Deploying..."
railway up --detach

echo ""
echo "Generate a public URL in Railway dashboard: Settings → Networking → Generate Domain"
echo "Then set GitHub Actions variable VITE_API_BASE_URL to that URL and redeploy Pages."
railway status 2>/dev/null || true
