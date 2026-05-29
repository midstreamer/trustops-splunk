#!/usr/bin/env bash
# Start TrustOps FastAPI with Splunk credentials from backend/.env or ~/.splunk_pass
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND="${ROOT}/backend"
ENV_FILE="${BACKEND}/.env"
PORT="${TRUSTOPS_BACKEND_PORT:-8001}"

if [[ ! -f "${ENV_FILE}" && -f "${BACKEND}/.env.example" ]]; then
  cp "${BACKEND}/.env.example" "${ENV_FILE}"
  chmod 600 "${ENV_FILE}"
  echo "Created ${ENV_FILE} from .env.example — set SPLUNK_PASSWORD before continuing." >&2
fi

if [[ -f "${ENV_FILE}" ]]; then
  set -a
  # shellcheck source=/dev/null
  source "${ENV_FILE}"
  set +a
fi

if [[ -z "${SPLUNK_PASSWORD:-}" && -n "${SPLUNK_PASSWORD_FILE:-}" && -f "${SPLUNK_PASSWORD_FILE}" ]]; then
  SPLUNK_PASSWORD="$(<"${SPLUNK_PASSWORD_FILE}")"
  export SPLUNK_PASSWORD
elif [[ -z "${SPLUNK_PASSWORD:-}" && -f "${HOME}/.splunk_pass" ]]; then
  SPLUNK_PASSWORD="$(<"${HOME}/.splunk_pass")"
  export SPLUNK_PASSWORD
fi

if [[ -z "${SPLUNK_USER:-}" ]]; then
  echo "error: SPLUNK_USER is not set. Add it to ${ENV_FILE} (see .env.example)." >&2
  exit 1
fi

if [[ -z "${SPLUNK_PASSWORD:-}" ]]; then
  echo "error: SPLUNK_PASSWORD is not set." >&2
  echo "  Edit ${ENV_FILE} and replace your-splunk-password with your Splunk Web password." >&2
  echo "  Or: echo 'your-password' > ~/.splunk_pass && chmod 600 ~/.splunk_pass" >&2
  exit 1
fi

if [[ "${SPLUNK_PASSWORD}" == "your-splunk-password" ]]; then
  echo "error: SPLUNK_PASSWORD is still the placeholder in ${ENV_FILE}." >&2
  echo "  Set it to the password you use at http://localhost:8000" >&2
  exit 1
fi

export SPLUNK_USER SPLUNK_PASSWORD

# Stop existing listener on this port
if command -v ss >/dev/null 2>&1; then
  old_pid="$(ss -tlnp 2>/dev/null | grep ":${PORT} " | sed -n 's/.*pid=\([0-9]*\).*/\1/p' | head -1)"
  if [[ -n "${old_pid}" ]]; then
    kill "${old_pid}" 2>/dev/null || true
    sleep 1
  fi
fi

cd "${BACKEND}"
if [[ ! -d .venv ]]; then
  python3 -m venv .venv
  .venv/bin/pip install -r requirements.txt
fi

echo "Starting TrustOps API on http://0.0.0.0:${PORT} (user=${SPLUNK_USER})"
exec .venv/bin/uvicorn app:app --reload --host 0.0.0.0 --port "${PORT}"
