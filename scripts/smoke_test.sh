#!/usr/bin/env bash
# Run TrustOps SAIA + agentic smoke tests against a running API.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND="${ROOT}/backend"
ENV_FILE="${BACKEND}/.env"
BASE_URL="${TRUSTOPS_API_BASE_URL:-http://127.0.0.1:8001}"

if [[ -f "${ENV_FILE}" ]]; then
  set -a
  # shellcheck source=/dev/null
  source "${ENV_FILE}"
  set +a
fi

cd "${BACKEND}"
if [[ ! -d .venv ]]; then
  echo "error: backend/.venv not found. Run scripts/start_backend.sh first." >&2
  exit 1
fi

exec .venv/bin/python -m smoke_test --base-url "${BASE_URL}" --wait "$@"
