#!/usr/bin/env bash
#
# Install Splunk AI Assistant from a Splunkbase download (.spl or .tgz).
#
# Prerequisites (manual — cannot be automated here):
#   1. Sign EULA: https://www.splunk.com/en_us/download/ai-assistant.html
#   2. Download app from https://splunkbase.splunk.com/app/7245/ (logged-in account)
#   3. After install, complete Cloud Connected activation in Splunk Web
#
# Required environment variables (avoids interactive Splunk CLI login):
#   SPLUNK_USER
#   SPLUNK_PASSWORD
#
# Usage (replace with your real downloaded filename):
#   export SPLUNK_USER="cjalessi"
#   export SPLUNK_PASSWORD="your-password"
#   export SPLUNK_AI_PACKAGE="$HOME/Downloads/splunk-ai-assistant_200.spl"
#   bash scripts/install_splunk_ai_assistant.sh
#

set -euo pipefail

SPLUNK_HOME="${SPLUNK_HOME:-/opt/splunk}"
SPLUNK_BIN="${SPLUNK_HOME}/bin/splunk"

if [[ -z "${SPLUNK_USER:-}" ]]; then
  echo "error: SPLUNK_USER is not set" >&2
  exit 1
fi

if [[ -z "${SPLUNK_PASSWORD:-}" ]]; then
  echo "error: SPLUNK_PASSWORD is not set" >&2
  exit 1
fi

if [[ -z "${SPLUNK_AI_PACKAGE:-}" ]]; then
  echo "error: SPLUNK_AI_PACKAGE is not set" >&2
  echo "hint: download from https://splunkbase.splunk.com/app/7245/ after EULA approval" >&2
  exit 1
fi

if [[ ! -f "${SPLUNK_AI_PACKAGE}" ]]; then
  echo "error: package not found: ${SPLUNK_AI_PACKAGE}" >&2
  exit 1
fi

if [[ ! -x "${SPLUNK_BIN}" ]]; then
  echo "error: splunk binary not found at ${SPLUNK_BIN}" >&2
  exit 1
fi

case "${SPLUNK_AI_PACKAGE}" in
  *.spl|*.tgz|*.tar.gz|*.zip) ;;
  *)
    echo "error: expected .spl, .tgz, .tar.gz, or .zip — got: ${SPLUNK_AI_PACKAGE}" >&2
    exit 1
    ;;
esac

export SPLUNK_PASSWORD

echo "Installing Splunk AI Assistant from: ${SPLUNK_AI_PACKAGE}"
echo "Splunk home: ${SPLUNK_HOME}"

run_install() {
  "${SPLUNK_BIN}" install app "${SPLUNK_AI_PACKAGE}" -update 1 \
    -auth "${SPLUNK_USER}:${SPLUNK_PASSWORD}"
}

if [[ "$(id -un)" == "splunk" ]]; then
  run_install
elif command -v sudo >/dev/null 2>&1; then
  echo "Running install as user splunk (sudo password may be required)..."
  sudo -u splunk env \
    SPLUNK_USER="${SPLUNK_USER}" \
    SPLUNK_PASSWORD="${SPLUNK_PASSWORD}" \
    "${SPLUNK_BIN}" install app "${SPLUNK_AI_PACKAGE}" -update 1 \
    -auth "${SPLUNK_USER}:${SPLUNK_PASSWORD}"
else
  echo "error: run as user 'splunk' or use sudo with -auth (see docs/install_splunk_ai_assistant.md)" >&2
  exit 1
fi

echo ""
echo "Install command finished. Checking for AI-related apps..."
ls -1 "${SPLUNK_HOME}/etc/apps/" 2>/dev/null | grep -iE 'ai|assistant' || echo "(no app folder name containing ai/assistant yet — check Manage Apps in Splunk Web)"

echo ""
echo "Next steps (required):"
echo "  1. Open Splunk Web → Apps → open Splunk AI Assistant"
echo "  2. Complete Cloud Connected setup (tenant code → activation token)"
echo "  3. See docs/install_splunk_ai_assistant.md"
