#!/usr/bin/env bash
#
# Ingest sample analyst decision telemetry CSV into Splunk (oneshot).
#
# Canonical demo alert for most rows: TO-VPN-2026-514 (see data/sample_decisions.csv).
#
# Required environment variables:
#   SPLUNK_USER      — Splunk admin username
#   SPLUNK_PASSWORD  — Splunk admin password
#
# Optional:
#   SPLUNK_HOME      — defaults to /opt/splunk
#   DECISIONS_CSV    — path to CSV; defaults to repo data/sample_decisions.csv
#

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SPLUNK_HOME="${SPLUNK_HOME:-/opt/splunk}"
DECISIONS_CSV="${DECISIONS_CSV:-${REPO_ROOT}/data/sample_decisions.csv}"

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

if [[ ! -f "${DECISIONS_CSV}" ]]; then
  echo "error: decisions CSV not found at ${DECISIONS_CSV}" >&2
  echo "hint: ensure data/sample_decisions.csv exists or set DECISIONS_CSV" >&2
  exit 1
fi

export SPLUNK_PASSWORD

echo "Ingesting ${DECISIONS_CSV} into index=trustops_decisions sourcetype=trustops:decision ..."
"${SPLUNK_HOME}/bin/splunk" add oneshot "${DECISIONS_CSV}" \
  -auth "${SPLUNK_USER}:${SPLUNK_PASSWORD}" \
  -index trustops_decisions \
  -sourcetype trustops:decision \
  -host trustops-lab

echo "Decision telemetry ingest complete."
