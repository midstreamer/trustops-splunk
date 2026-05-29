#!/usr/bin/env bash
#
# Ingest synthetic TrustOps auth CSV into Splunk via oneshot.
#
# Required environment variables:
#   SPLUNK_USER      — Splunk admin username (used if oneshot prompts; often not needed non-interactive)
#   SPLUNK_PASSWORD  — Splunk admin password
#
# Optional:
#   SPLUNK_HOME      — defaults to /opt/splunk
#   AUTH_CSV         — path to CSV; defaults to repo data/synthetic_auth_logs.csv
#

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SPLUNK_HOME="${SPLUNK_HOME:-/opt/splunk}"
AUTH_CSV="${AUTH_CSV:-${REPO_ROOT}/data/synthetic_auth_logs.csv}"

if [[ -z "${SPLUNK_USER:-}" ]]; then
  echo "error: SPLUNK_USER is not set" >&2
  exit 1
fi

if [[ -z "${SPLUNK_PASSWORD:-}" ]]; then
  echo "error: SPLUNK_PASSWORD is not set" >&2
  exit 1
fi

if [[ ! -x "${SPLUNK_HOME}/bin/splunk" ]]; then
  echo "error: splunk binary not found or not executable at ${SPLUNK_HOME}/bin/splunk" >&2
  echo "hint: set SPLUNK_HOME to your Splunk install root" >&2
  exit 1
fi

if [[ ! -f "${AUTH_CSV}" ]]; then
  echo "error: auth CSV not found at ${AUTH_CSV}" >&2
  echo "hint: run python3 scripts/generate_synthetic_data.py first" >&2
  exit 1
fi

export SPLUNK_PASSWORD

echo "Ingesting ${AUTH_CSV} into index=trustops sourcetype=trustops:auth ..."
# -auth avoids interactive password prompts in many environments.
"${SPLUNK_HOME}/bin/splunk" add oneshot "${AUTH_CSV}" \
  -auth "${SPLUNK_USER}:${SPLUNK_PASSWORD}" \
  -index trustops \
  -sourcetype trustops:auth \
  -host trustops-synthetic

echo "Ingest complete."
