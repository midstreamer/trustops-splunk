#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

mkdir -p data

URL="https://raw.githubusercontent.com/mitre/cti/master/enterprise-attack/enterprise-attack.json"
OUT="data/enterprise-attack.json"

echo "Downloading Enterprise ATT&CK STIX from MITRE CTI..."
if ! curl -L -f -o "$OUT" "$URL"; then
  echo "ERROR: curl failed to download $URL" >&2
  exit 1
fi

ls -lh "$OUT"
echo "Saved to $OUT"
