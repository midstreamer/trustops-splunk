#!/usr/bin/env bash
#
# Bootstrap Splunk admin password when REST/Web login returns 401.
#
# IMPORTANT: plain "sudo bash" does NOT pass your exports. Use ONE of:
#
#   sudo bash scripts/bootstrap_splunk_admin.sh cjalessi 'TempPass123!'
#
#   sudo SPLUNK_BOOTSTRAP_USER=cjalessi SPLUNK_BOOTSTRAP_PASSWORD='TempPass123!' \
#     bash scripts/bootstrap_splunk_admin.sh
#
#   sudo -E bash scripts/bootstrap_splunk_admin.sh   # only if export SPLUNK_BOOTSTRAP_PASSWORD first
#

set -euo pipefail
set +H

SPLUNK_HOME="${SPLUNK_HOME:-/opt/splunk}"
SPLUNK_BIN="${SPLUNK_HOME}/bin/splunk"

# Args override env (best with sudo)
BOOT_USER="${1:-${SPLUNK_BOOTSTRAP_USER:-cjalessi}}"
BOOT_PASS="${2:-${SPLUNK_BOOTSTRAP_PASSWORD:-}}"

SEED_CONF="${SPLUNK_HOME}/etc/system/local/user-seed.conf"
PASSWD_FILE="${SPLUNK_HOME}/etc/passwd"

if [[ "$(id -un)" != "root" ]]; then
  echo "error: run with sudo" >&2
  echo "" >&2
  echo "  sudo bash $0 cjalessi 'TempPass123!'" >&2
  exit 1
fi

if [[ -z "${BOOT_PASS}" ]]; then
  echo "error: password not provided to root shell" >&2
  echo "" >&2
  echo "sudo does not pass 'export SPLUNK_BOOTSTRAP_PASSWORD' from your user shell." >&2
  echo "Use:" >&2
  echo "  sudo bash $0 cjalessi 'TempPass123!'" >&2
  exit 1
fi

echo "=== Splunk admin bootstrap ==="
echo "User: ${BOOT_USER}"
echo "Will: stop Splunk, backup passwd, write user-seed.conf, start Splunk"
echo ""

if [[ "${TRUSTOPS_BOOTSTRAP_YES:-}" != "1" ]]; then
  read -r -p "Continue? [y/N] " confirm
  if [[ "${confirm}" != "y" && "${confirm}" != "Y" ]]; then
    echo "Aborted."
    exit 0
  fi
fi

echo "Stopping Splunk..."
sudo -u splunk "${SPLUNK_BIN}" stop || true

if [[ -f "${PASSWD_FILE}" ]]; then
  backup="${PASSWD_FILE}.bak.$(date +%s)"
  echo "Backing up ${PASSWD_FILE} -> ${backup}"
  mv "${PASSWD_FILE}" "${backup}"
fi

mkdir -p "${SPLUNK_HOME}/etc/system/local"
cat > "${SEED_CONF}" <<EOF
[user_info]
USERNAME = ${BOOT_USER}
PASSWORD = ${BOOT_PASS}
EOF
chown splunk:splunk "${SEED_CONF}"
chmod 600 "${SEED_CONF}"
echo "Wrote ${SEED_CONF}"

echo "Starting Splunk..."
sudo -u splunk "${SPLUNK_BIN}" start --accept-license --answer-yes --no-prompt

echo ""
echo "[OK] Bootstrap complete."
echo ""
echo "1. Open http://localhost:8000  (port 8000 — not 80000)"
echo "2. Login: ${BOOT_USER} / TempPass (the password you passed to this script)"
echo "3. Settings → Users → set a permanent password"
echo "4. Then run:"
echo "     sudo rm -f ${SEED_CONF}"
echo "     sudo -u splunk ${SPLUNK_BIN} restart"
echo "5. Verify: bash scripts/verify_splunk_login.sh with the NEW password"
