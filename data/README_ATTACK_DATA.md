# Enterprise ATT&CK STIX data (optional)

TrustOps can optionally enrich MITRE ATT&CK mappings using local Enterprise ATT&CK STIX data and the `mitreattack-python` package.

## Expected file

```
data/enterprise-attack.json
```

Download it with:

```bash
bash scripts/download_attack_data.sh
```

## Behavior

- If `data/enterprise-attack.json` is present **and** `mitreattack-python` is installed, the MITRE ATT&CK Mapping Agent may mark mappings as **validated** using MITRE’s official technique metadata.
- If the file is missing, or the package is not installed, TrustOps **falls back to local static mappings** so the demo remains reliable.
- No outbound network calls are made at runtime; enrichment uses only local files.

## Override path

Set `ATTACK_STIX_PATH` to point at an alternate STIX JSON file (absolute or relative to the repository root).
