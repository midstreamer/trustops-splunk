#!/usr/bin/env bash
#
# Create Splunk indexes for TrustOps (Enterprise local instance).
# Uses the Splunk management API over HTTPS on port 8089.
#
# Required environment variables:
#   SPLUNK_USER      — Splunk admin username
#   SPLUNK_PASSWORD  — Splunk admin password
#
# Optional:
#   SPLUNK_MGMT_URL  — defaults to https://localhost:8089
#

set -euo pipefail

SPLUNK_MGMT_URL="${SPLUNK_MGMT_URL:-https://localhost:8089}"
SPLUNK_MGMT_URL="${SPLUNK_MGMT_URL%/}"

if [[ -z "${SPLUNK_USER:-}" ]]; then
  echo "error: SPLUNK_USER is not set" >&2
  exit 1
fi

if [[ -z "${SPLUNK_PASSWORD:-}" ]]; then
  echo "error: SPLUNK_PASSWORD is not set" >&2
  exit 1
fi

INDEXES=(trustops trustops_decisions trustops_agent_runs)

create_index() {
  local name="$1"
  local url="${SPLUNK_MGMT_URL}/services/data/indexes"
  local http_code
  local tmp
  tmp="$(mktemp)"

  http_code="$(
    curl -sS -k -u "${SPLUNK_USER}:${SPLUNK_PASSWORD}" \
      -w "%{http_code}" -o "${tmp}" \
      -X POST "${url}" \
      -d "name=${name}"
  )" || true

  case "${http_code}" in
    200|201|409)
      rm -f "${tmp}"
      return 0
      ;;
    *)
      echo "[ERROR] failed to create index ${name} (HTTP ${http_code})" >&2
      cat "${tmp}" >&2 || true
      rm -f "${tmp}"
      return 1
      ;;
  esac
}

verify_index() {
  local name="$1"
  local url="${SPLUNK_MGMT_URL}/services/data/indexes/${name}"
  local http_code
  local tmp
  tmp="$(mktemp)"

  http_code="$(
    curl -sS -k -u "${SPLUNK_USER}:${SPLUNK_PASSWORD}" \
      -w "%{http_code}" -o "${tmp}" \
      -X GET "${url}"
  )" || true

  if [[ "${http_code}" == "200" ]]; then
    echo "[OK] ${name}"
    rm -f "${tmp}"
    return 0
  fi

  echo "[ERROR] index ${name} missing or not accessible (HTTP ${http_code})" >&2
  cat "${tmp}" >&2 || true
  rm -f "${tmp}"
  return 1
}

failed=0

for name in "${INDEXES[@]}"; do
  if ! create_index "${name}"; then
    failed=1
  fi
done

for name in "${INDEXES[@]}"; do
  if ! verify_index "${name}"; then
    failed=1
  fi
done

exit "${failed}"
