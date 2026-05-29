#!/usr/bin/env bash
#
# Install or update Splunk MCP Server from a Splunkbase download (.tgz or .spl).
#
# Modes:
#   TRUSTOPS_MCP_MANUAL=1  — copy app into etc/apps (no Splunk CLI login; recommended)
#   default                — splunk install app (needs SPLUNK_USER + SPLUNK_PASSWORD)
#
# Optional:
#   SPLUNK_MCP_PACKAGE       — path to .tgz / .spl (required)
#   SPLUNK_HOME              — defaults to /opt/splunk
#   SPLUNK_USER / SPLUNK_PASSWORD — for CLI mode only
#   SPLUNK_PASSWORD_FILE     — read password from file (avoids shell ! history issues)
#
# Passwords with "!" must use SINGLE quotes in the shell, or a password file:
#   export SPLUNK_PASSWORD='your!password'
#   echo -n 'your!password' > ~/.splunk_pass && chmod 600 ~/.splunk_pass
#   export SPLUNK_PASSWORD_FILE=~/.splunk_pass
#
# Manual install (no Splunk password):
#   export SPLUNK_MCP_PACKAGE="$HOME/Downloads/splunk-mcp-server_113.tgz"
#   sudo TRUSTOPS_MCP_MANUAL=1 bash scripts/install_splunk_mcp_server.sh
#

set -euo pipefail
set +H  # disable bash history expansion (! in passwords)

SPLUNK_HOME="${SPLUNK_HOME:-/opt/splunk}"
SPLUNK_BIN="${SPLUNK_HOME}/bin/splunk"
APP_NAME="Splunk_MCP_Server"

if [[ -z "${SPLUNK_MCP_PACKAGE:-}" ]]; then
  echo "error: SPLUNK_MCP_PACKAGE is not set" >&2
  echo "hint: export SPLUNK_MCP_PACKAGE=\"\$HOME/Downloads/splunk-mcp-server_113.tgz\"" >&2
  exit 1
fi

if [[ ! -f "${SPLUNK_MCP_PACKAGE}" ]]; then
  echo "error: package not found: ${SPLUNK_MCP_PACKAGE}" >&2
  exit 1
fi

if [[ ! -x "${SPLUNK_BIN}" ]]; then
  echo "error: splunk binary not found at ${SPLUNK_BIN}" >&2
  exit 1
fi

case "${SPLUNK_MCP_PACKAGE}" in
  *.spl|*.tgz|*.tar.gz|*.zip) ;;
  *)
    echo "error: expected .spl, .tgz, .tar.gz, or .zip" >&2
    exit 1
    ;;
esac

load_password() {
  if [[ -n "${SPLUNK_PASSWORD_FILE:-}" ]]; then
    if [[ ! -f "${SPLUNK_PASSWORD_FILE}" ]]; then
      echo "error: SPLUNK_PASSWORD_FILE not found: ${SPLUNK_PASSWORD_FILE}" >&2
      exit 1
    fi
    SPLUNK_PASSWORD="$(<"${SPLUNK_PASSWORD_FILE}")"
    export SPLUNK_PASSWORD
  fi
}

require_cli_credentials() {
  if [[ -z "${SPLUNK_USER:-}" ]]; then
    echo "error: SPLUNK_USER is not set (not needed for TRUSTOPS_MCP_MANUAL=1)" >&2
    exit 1
  fi
  if [[ "${SPLUNK_USER}" == *"@"* ]]; then
    echo "warning: SPLUNK_USER looks like an email (${SPLUNK_USER})" >&2
    echo "warning: Splunk CLI usually needs your local Splunk Web username (e.g. cjalessi), not an email." >&2
  fi
  load_password
  if [[ -z "${SPLUNK_PASSWORD:-}" ]]; then
    echo "error: SPLUNK_PASSWORD is not set" >&2
    echo "hint: use single quotes if password contains ! : export SPLUNK_PASSWORD='pass!word'" >&2
    echo "hint: or export SPLUNK_PASSWORD_FILE=~/.splunk_pass" >&2
    exit 1
  fi
  export SPLUNK_PASSWORD
}

stage_package_for_splunk_user() {
  local staged
  staged="/tmp/trustops-mcp-install-$$.tgz"
  cp -f "${SPLUNK_MCP_PACKAGE}" "${staged}"
  chmod 644 "${staged}"
  echo "${staged}"
}

run_install_manual() {
  local tmpdir
  tmpdir="$(mktemp -d)"
  trap 'rm -rf "${tmpdir}"' RETURN

  echo "Manual install: extracting to ${tmpdir} ..."
  tar -xzf "${SPLUNK_MCP_PACKAGE}" -C "${tmpdir}"

  if [[ ! -d "${tmpdir}/${APP_NAME}" ]]; then
    echo "error: expected ${tmpdir}/${APP_NAME} in package" >&2
    exit 1
  fi

  local dest="${SPLUNK_HOME}/etc/apps/${APP_NAME}"
  if [[ -d "${dest}" ]]; then
    echo "Backing up existing app to ${dest}.bak.$$ ..."
    mv "${dest}" "${dest}.bak.$$"
  fi

  echo "Installing ${APP_NAME} to ${dest} ..."
  cp -a "${tmpdir}/${APP_NAME}" "${dest}"
  chown -R splunk:splunk "${dest}"
  echo "[OK] ${APP_NAME} installed (manual). Enable/reload in Splunk Web if needed."
}

run_install_cli() {
  local staged
  staged="$(stage_package_for_splunk_user)"
  trap 'rm -f "${staged}"' RETURN

  echo "CLI install via splunk install app (staged at ${staged}) ..."
  "${SPLUNK_BIN}" install app "${staged}" -update 1 \
    -auth "${SPLUNK_USER}:${SPLUNK_PASSWORD}"
}

echo "Splunk MCP Server package: ${SPLUNK_MCP_PACKAGE}"
echo "Splunk home: ${SPLUNK_HOME}"

# Default to manual install unless CLI explicitly requested (avoids recurring Login failed)
if [[ "${TRUSTOPS_MCP_CLI:-}" != "1" && "${TRUSTOPS_MCP_MANUAL:-}" != "0" ]]; then
  TRUSTOPS_MCP_MANUAL=1
fi

if [[ "${TRUSTOPS_MCP_MANUAL:-}" == "1" ]]; then
  if [[ "$(id -un)" != "root" && "$(id -un)" != "splunk" ]]; then
    echo "Manual install requires sudo (no Splunk CLI password needed):" >&2
    echo "  sudo TRUSTOPS_MCP_MANUAL=1 SPLUNK_MCP_PACKAGE=\"${SPLUNK_MCP_PACKAGE}\" bash $0" >&2
    exit 1
  fi
  run_install_manual
else
  echo "CLI mode (set TRUSTOPS_MCP_CLI=1). If you see Login failed, use manual install instead." >&2
  require_cli_credentials
  if [[ "$(id -un)" == "splunk" ]]; then
    run_install_cli
  elif command -v sudo >/dev/null 2>&1; then
    echo "Running CLI install as user splunk ..."
    staged="$(stage_package_for_splunk_user)"
    sudo -u splunk "${SPLUNK_BIN}" install app "${staged}" -update 1 \
      -auth "${SPLUNK_USER}:${SPLUNK_PASSWORD}"
    rm -f "${staged}"
  else
    echo "error: need sudo or run as splunk user" >&2
    exit 1
  fi
fi

echo ""
echo "Checking for MCP app..."
if [[ "$(id -un)" == "root" || "$(id -un)" == "splunk" ]]; then
  ls -1 "${SPLUNK_HOME}/etc/apps/" | grep -i mcp || true
else
  sudo ls -1 "${SPLUNK_HOME}/etc/apps/" 2>/dev/null | grep -i mcp || echo "(run: sudo ls /opt/splunk/etc/apps/ | grep -i mcp)"
fi

echo ""
echo "Next: Splunk Web → Apps → Splunk MCP Server → configure tokens"
