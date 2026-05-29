# TrustOps Phase 1 — Splunk foundation

This phase stands up **indexes**, **synthetic authentication data**, **sample analyst decision telemetry**, and **starter searches/dashboards** so analysts (and the future React UI) can reason about VPN login anomalies and human-in-the-loop outcomes.

## Canonical demo story

Use **`TO-VPN-2026-514`** everywhere as the primary VPN/geo anomaly alert:

- Auth events: `data/synthetic_auth_logs.csv` (generated) — `jsmith`, failed burst, success from Romania.
- Decisions: `data/sample_decisions.csv` — mostly this `alert_id`, with **accepted**, **modified**, and **rejected** AI outcomes.
- Alerts JSON: `data/sample_alerts.json` — documents the same scenario.
- Low-severity contrast: **`TO-BASELINE-0001`** appears in a couple of decision rows.

## Assumptions

- Splunk Enterprise is installed locally with web UI at `http://localhost:8000`.
- Management REST API is reachable at `https://localhost:8089` (self-signed TLS is typical — scripts use `curl -k`).
- Splunk binaries live under `/opt/splunk` (override with `SPLUNK_HOME` for ingest scripts).

## Indexes and sourcetypes

| Index               | Purpose                                      | Sourcetype          |
|---------------------|----------------------------------------------|---------------------|
| `trustops`          | Synthetic VPN / authentication events        | `trustops:auth`     |
| `trustops_decisions`| Analyst decision telemetry                   | `trustops:decision` |

## Environment variables

All ingest scripts require:

```bash
export SPLUNK_USER="cjalessi"
export SPLUNK_PASSWORD="your-admin-password"
```

Optional:

```bash
export SPLUNK_HOME="/opt/splunk"
export SPLUNK_MGMT_URL="https://localhost:8089"
export AUTH_CSV="/path/to/synthetic_auth_logs.csv"
export DECISIONS_CSV="/path/to/sample_decisions.csv"
```

If `SPLUNK_USER` or `SPLUNK_PASSWORD` is missing, the scripts print an error and exit with status `1`.

## Full setup (recommended order)

From the repository root:

```bash
chmod +x scripts/*.sh

python3 scripts/generate_synthetic_data.py
bash scripts/setup_splunk_indexes.sh
bash scripts/ingest_auth_logs.sh
bash scripts/ingest_decisions.sh
```

### Step 1 — Generate synthetic auth CSV

```bash
python3 scripts/generate_synthetic_data.py
```

Writes `data/synthetic_auth_logs.csv` with normal **jsmith** activity, peers, and the **`TO-VPN-2026-514`** burst + Romania success scenario.

Columns: `timestamp`, `user`, `src_ip`, `dest_host`, `action`, `geo_country`, `auth_method`, `risk_score`, `event_type`, `alert_id`, `scenario`.

### Step 2 — Create indexes

```bash
bash scripts/setup_splunk_indexes.sh
```

POSTs to `/services/data/indexes` for `trustops` and `trustops_decisions`. HTTP **409** (already exists) is treated as success.

### Step 3 — Ingest auth logs

```bash
bash scripts/ingest_auth_logs.sh
```

` splunk add oneshot` → `index=trustops`, `sourcetype=trustops:auth`, host `trustops-synthetic`.

### Step 4 — Ingest decision telemetry

```bash
bash scripts/ingest_decisions.sh
```

` splunk add oneshot` → `index=trustops_decisions`, `sourcetype=trustops:decision`, host **`trustops-lab`**.

**CSV schema** (`data/sample_decisions.csv`):

`timestamp`, `alert_id`, `analyst`, `ai_recommendation`, `analyst_decision`, `final_severity`, `confidence_score`, `trust_score`, `time_to_decision_seconds`, `ai_recommendation_status`, `evidence_reviewed_count`, `sop_followed`, `notes`

Avoid commas inside fields so `_raw` splitting and the bundled `rex` patterns stay reliable.

### Optional: improve `_time` at ingest

Oneshot uses file metadata for `_time` unless configured. Searches and the dashboard use `strptime(timestamp, ...)` on extracted fields where needed. For index-time accuracy, add `props.conf` (dev example):

```ini
[trustops:auth]
TIME_PREFIX = ^
MAX_TIMESTAMP_LOOKAHEAD = 32
TIME_FORMAT = %Y-%m-%dT%H:%M:%SZ

[trustops:decision]
TIME_PREFIX = ^
MAX_TIMESTAMP_LOOKAHEAD = 32
TIME_FORMAT = %Y-%m-%dT%H:%M:%SZ
```

## Install the dashboard

1. In Splunk Web, go to **Search & Reporting** (or your app).
2. **Settings → User interface → Views → Create new dashboard → Classic Dashboard**.
3. Open **Source** and paste `splunk/trustops_dashboard.xml`, then **Save**.

Panels include auth analytics plus **decision aggregates** and a **canonical-alert** decision table for `TO-VPN-2026-514`.

## Verification searches

**Authentication for the canonical alert**

```spl
index=trustops sourcetype=trustops:auth alert_id="TO-VPN-2026-514"
| sort _time
| table _time user src_ip geo_country action auth_method risk_score alert_id scenario
```

**Decision telemetry aggregates**

```spl
index=trustops_decisions sourcetype=trustops:decision
| eval _is_header=if(match(_raw,"^timestamp,alert_id,analyst,"),1,0)
| where _is_header=0
| fields - _is_header
| rex field=_raw "^(?<timestamp>[^,]+),(?<alert_id>[^,]+),(?<analyst>[^,]+),(?<ai_recommendation>[^,]+),(?<analyst_decision>[^,]+),(?<final_severity>[^,]+),(?<confidence_score>\d+),(?<trust_score>\d+),(?<time_to_decision_seconds>\d+),(?<ai_recommendation_status>[^,]+),(?<evidence_reviewed_count>\d+),(?<sop_followed>[^,]+),(?<notes>[^\r\n]+)"
| eval confidence_score=tonumber(confidence_score), trust_score=tonumber(trust_score), time_to_decision_seconds=tonumber(time_to_decision_seconds)
| stats count as decisions avg(confidence_score) as avg_confidence avg(trust_score) as avg_trust avg(time_to_decision_seconds) as avg_time_to_decision by ai_recommendation_status
```

Expect **`accepted`**, **`modified`**, and **`rejected`** in `ai_recommendation_status` after a successful `ingest_decisions.sh` run.

## Reference searches

See `splunk/core_searches.spl` for copy-paste SPL (copy **one** block at a time into Search).

## Sample alerts JSON

`data/sample_alerts.json` mirrors **`TO-VPN-2026-514`** for future API/UI integration; it is **not** ingested automatically by the shell scripts in this phase.
