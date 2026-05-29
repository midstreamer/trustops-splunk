# TrustOps — Phase 2 FastAPI backend

Local API that connects to Splunk (management port **8089** by default), runs searches with the Splunk SDK (`splunklib`), orchestrates **Splunk AI Assistant** investigation support (with **`ai_agent.py`** deterministic fallback), applies a **Human-AI Trust Calibration** layer on decisions, and posts extended CSV-shaped telemetry to Splunk via **`/services/receivers/simple`**.

## Prerequisites

- Splunk Enterprise reachable from this machine (typical: `https://localhost:8089`).
- Phase 1 data ingested (`trustops`, `trustops_decisions`) — see repo root `README.md`.
- Python **3.10+** recommended.

## Environment variables

Required for Splunk-backed routes:

| Variable | Default | Description |
|----------|---------|--------------|
| `SPLUNK_USER` | _(none)_ | Splunk username |
| `SPLUNK_PASSWORD` | _(none)_ | Splunk password |

Optional:

| Variable | Default | Description |
|----------|---------|--------------|
| `SPLUNK_HOST` | `localhost` | Management host |
| `SPLUNK_PORT` | `8089` | Management port |
| `SPLUNK_SCHEME` | `https` | `http` or `https` |
| `SPLUNK_VERIFY_SSL` | `false` | Set `true` when using valid TLS |
| `SPLUNK_AUTH_INDEX` | `trustops` | Auth events index |
| `SPLUNK_DECISION_INDEX` | `trustops_decisions` | Decision telemetry index |
| `SPLUNK_AGENT_RUN_INDEX` | `trustops_agent_runs` | Agent-step telemetry index (JSON `trustops:agent_step`) |
| `SPLUNK_EVENT_HOST` | `trustops-api` | `host` field for API-written events |
| `SPLUNK_MCP_URL` | `http://localhost:8000/en-US/splunkd/__raw/services/mcp` | Splunk MCP HTTP endpoint (use Web proxy to avoid TLS issues locally) |
| `SPLUNK_MCP_TOKEN` | _(none)_ | Encrypted MCP token from Splunk MCP Server app |
| `SPLUNK_MCP_TOKEN_FILE` | `~/.splunk_mcp_token` | File path if token is not in env |
| `SAIA_USE_MCP` | `false` | Optional MCP `saia_*` tools (v2 cloud API often returns HTTP 400 on CMP stacks) |
| `SAIA_SOURCE_APP_ID` | `search` | `Source-App-ID` header for SAIA REST `/predict` (matches Search UI) |
| `ATTACK_STIX_PATH` | `data/enterprise-attack.json` | Optional Enterprise ATT&CK STIX JSON for MITRE enrichment |

Place variables in `backend/.env` (optional) or export them in your shell. **Never commit real credentials.**

### MITRE ATT&CK mapping

| Module | Role |
|--------|------|
| `agents/mitre_attack_agent.py` | Maps Splunk evidence to ATT&CK tactics/techniques (local rules + optional enrichment) |
| `attack_enrichment.py` | Optional `mitreattack-python` enrichment from local STIX data |

Install optional enrichment:

```bash
pip install -r requirements.txt
bash scripts/download_attack_data.sh   # writes data/enterprise-attack.json
```

If `mitreattack-python` or `data/enterprise-attack.json` is missing, mappings still work via **local fallback** (`validated=false`, `enrichment_source=local_fallback`).

SAIA explain/generate routes: `POST /saia/explain`, `POST /saia/generate` (used by the React investigation panel).

### Human-AI Trust Calibration

| Module | Role |
|--------|------|
| `trust_calibration.py` | Notice levels, automation bias scoring, post-decision feedback |
| `decision_telemetry.py` | Extended 19-field CSV schema and comma sanitization |

Investigation responses include `trust_calibration_notice` and `trust_calibration_level`.  
`POST /decisions` requires `supporting_evidence`, `contradicting_evidence`, and optional `evidence_checklist`; response includes bias score/level plus feedback fields.

### Agentic workflow observability

After `GET`/`POST` `/alerts/{alert_id}/agent-run`, the backend writes one JSON event per agent step to `trustops_agent_runs` (`agent_run_logger.py`). Failures are non-blocking; check `telemetry_warning` on `AgentRunResult`.

| Endpoint | Purpose |
|----------|---------|
| `GET /agent-runs/{run_id}/telemetry` | Splunk step events for a run |
| `GET /agent-runs/summary` | Counts by agent/status, avg duration, recent run IDs |

## Install and run

```bash
cp backend/.env.example backend/.env
# Edit backend/.env — set SPLUNK_USER and SPLUNK_PASSWORD (same as Splunk Web login)

bash scripts/start_backend.sh
```

Or manually:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export SPLUNK_USER=cjalessi
export SPLUNK_PASSWORD='your-splunk-password'
uvicorn app:app --reload --host 0.0.0.0 --port 8001
```

Password file alternative: `echo 'your-password' > ~/.splunk_pass && chmod 600 ~/.splunk_pass` then set only `SPLUNK_USER` in `.env`.

API docs: `http://localhost:8001/docs`

## Quick test URLs

- `http://localhost:8001/health`
- `http://localhost:8001/alerts`
- `http://localhost:8001/alerts/TO-VPN-2026-514`
- `http://localhost:8001/alerts/TO-VPN-2026-514/events`
- `http://localhost:8001/alerts/TO-VPN-2026-514/investigation`
- `POST http://localhost:8001/alerts/TO-VPN-2026-514/chat` — alert-scoped analyst chat (SAIA + local fallback)
- `http://localhost:8001/decisions/summary`
- `http://localhost:8001/decisions/TO-VPN-2026-514`

## Example POST /decisions

```bash
curl -sS -X POST "http://localhost:8001/decisions" \
  -H "Content-Type: application/json" \
  -d '{
    "client_decision_id": "00000000-0000-4000-8000-000000000001",
    "alert_id": "TO-VPN-2026-514",
    "analyst": "api-demo",
    "ai_recommendation": "Escalate as likely compromised account",
    "analyst_decision": "Escalate to incident response",
    "final_severity": "High",
    "confidence_score": 4,
    "trust_score": 4,
    "time_to_decision_seconds": 200,
    "ai_recommendation_status": "accepted",
    "evidence_reviewed_count": 3,
    "sop_followed": true,
    "notes": "Submitted via TrustOps API smoke test",
    "evidence_checklist": "auth_timeline|geo_anomaly|sop_comparison",
    "supporting_evidence": "Failed VPN burst then Romania success",
    "contradicting_evidence": "Possible approved travel"
  }' | jq .
```

## Architecture notes

- **Searches** use explicit SPL (returned as `spl_query_used` on read routes) with strict `alert_id` validation before embedding in SPL.
- **Decisions** are written as a single CSV-shaped `_raw` line (extended schema with `client_decision_id` as the last field; legacy rows still parse via column-index SPL). Duplicate `client_decision_id` values return HTTP 409 for the lifetime of the API process.
- **CORS** allows local React dev servers on `http://localhost:5173` and `http://localhost:3000`.

## Troubleshooting

- **`503 Splunk credentials are not configured`**: export `SPLUNK_USER` / `SPLUNK_PASSWORD`.
- **`503 Splunk search failed`**: confirm Splunk is up, indexes exist, and time range in Splunk UI would return data (demo data uses **May 2026** timestamps).
- **TLS warnings**: keep `SPLUNK_VERIFY_SSL=false` for default self-signed dev certs.
