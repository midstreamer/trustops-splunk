#!/usr/bin/env bash
#
# Reset a Splunk native user's password from the CLI (when Splunk Web login fails).
# Must run as root via sudo so splunk user can execute the command.
#
# Usage:
#   set +H
#   export SPLUNK_USER='cjalessi'
#   export SPLUNK_NEW_PASSWORD='YourNewSecurePassword'
#   # If you still know the CURRENT password for -auth:
#   export SPLUNK_ADMIN_USER='cjalessi'
#   export SPLUNK_ADMIN_PASSWORD='current-password'
#   sudo bash scripts/reset_splunk_user_password.sh
#
# If you do NOT know any working admin password, use bootstrap mode (see docs).
#

set -euo pipefail
set +H

SPLUNK_HOME="${SPLUNK_HOME:-/opt/splunk}"
SPLUNK_BIN="${SPLUNK_HOME}/bin/splunk"

TARGET_USER="${SPLUNK_USER:-cjalessi}"
NEW_PASSWORD="${SPLUNK_NEW_PASSWORD:-}"

if [[ -z "${NEW_PASSWORD}" ]]; then
  echo "error: set SPLUNK_NEW_PASSWORD to the new password" >&2
  echo "  export SPLUNK_NEW_PASSWORD='your-new-password'  # use single quotes if it contains !" >&2
  exit 1
fi

if [[ "$(id -un)" != "root" ]]; then
  echo "error: run with sudo" >&2
  echo "  sudo bash scripts/reset_splunk_user_password.sh" >&2
  exit 1
fi

if [[ -n "${SPLUNK_ADMIN_PASSWORD:-}" ]]; then
  ADMIN_USER="${SPLUNK_ADMIN_USER:-cjalessi}"
  echo "Resetting password for ${TARGET_USER} (auth as ${ADMIN_USER}) ..."
  sudo -u splunk "${SPLUNK_BIN}" edit user "${TARGET_USER}" \
    -password "${NEW_PASSWORD}" \
    -role admin \
    -auth "${ADMIN_USER}:${SPLUNK_ADMIN_PASSWORD}"
else
  echo "error: SPLUNK_ADMIN_PASSWORD not set — needed to authenticate splunk edit user" >&2
  echo "" >&2
  echo "If NO password works, reset via user-seed (bootstrap) instead:" >&2
  echo "  1. sudo -u splunk ${SPLUNK_BIN} stop" >&2
  echo "  2. sudo mv ${SPLUNK_HOME}/etc/passwd ${SPLUNK_HOME}/etc/passwd.bak" >&2
  echo "  3. Create ${SPLUNK_HOME}/etc/system/local/user-seed.conf with new admin user/password" >&2
  echo "  4. sudo -u splunk ${SPLUNK_BIN} start" >&2
  echo "  5. Sign in at http://localhost:8000 and remove user-seed.conf" >&2
  echo "  See docs/troubleshoot_splunk_login.md" >&2
  exit 1
fi

echo "[OK] Password change command completed for ${TARGET_USER}."
echo "Try Splunk Web: http://localhost:8000  (username: ${TARGET_USER})"
