# TrustOps for Splunk

TrustOps is a **human-in-the-loop agentic security triage assistant** for Splunk. It helps SOC analysts investigate suspicious alerts using Splunk data, **Splunk AI Assistant**, and the **Splunk MCP Server**, then captures **analyst decision telemetry** (trust, confidence, final decision, and time-to-decision).

This repository implements **Phase 1** (Splunk foundation), **Phase 2** (FastAPI backend with SAIA/MCP integration), **Phase 3** (React analyst UI), and **Phase 4** (demo polish: runbook, dev check script, architecture diagram, Devpost narrative). Phase 1 covers synthetic VPN authentication data, **sample analyst decisions**, indexes, ingestion scripts, starter searches, and a Splunk dashboard. Phase 2 exposes a local API for alerts, Splunk-backed events, **agentic investigation** (Splunk AI Assistant + optional MCP), and decision logging back into Splunk—with a **deterministic local fallback** for reliable offline demos. Phase 3 is a Vite + React console that drives that API end-to-end, including **Explain SPL** and **Generate SPL** in the investigation panel.

## Agentic Ops Positioning

TrustOps is built for the **Splunk Agentic Ops** model: it uses Splunk data, **Splunk AI Assistant**, optional **MCP-enabled** tooling, and a **sequential agent orchestrator** to support SOC alert investigation. Each agent role performs a defined task and returns an **execution trace**, allowing analysts to see what evidence was used, which tools were called, and how recommendations were developed.

TrustOps intentionally keeps the **analyst in control**. The system supports investigation and recommendation development, but **final disposition remains a human decision** that is logged back into Splunk with trust, confidence, evidence review, and automation-bias telemetry.

## AI and MCP Integration

TrustOps integrates with Splunk AI Assistant and Splunk MCP to support agentic security investigation workflows. The system uses Splunk data to retrieve alert context, generate investigation support, and produce analyst-facing recommendations. A deterministic local fallback agent is also included so the demo can run reliably when cloud-connected AI services are unavailable.

This design allows TrustOps to demonstrate both Splunk-native AI integration and dependable local execution for hackathon judging.

## Human-AI Trust Calibration Layer

TrustOps captures whether analysts **accepted**, **modified**, or **rejected** AI recommendations—and whether that disposition was earned through evidence review.

- **Trust Calibration Notice** on high-confidence investigations (e.g. **`TO-VPN-2026-514`**) warns against automation bias before severity/actions.
- **Evidence Review Checklist** requires at least two independent checks before submit; count syncs to `evidence_reviewed_count`.
- **Challenge the AI Recommendation** requires supporting and contradicting evidence (stored in Splunk telemetry).
- **Automation bias risk score** (0–9) and **Low / Moderate / High** level are computed on submit and returned with **post-decision feedback** for analyst upskilling.
- Grounded in human–AI collaboration research: **calibrated trust**, **accountability**, **feedback**, and **skill reinforcement**.

Legacy 13-field decision rows in Splunk remain compatible; new UI submissions write the extended schema (including `client_decision_id` at the end of each CSV row). **Duplicate submissions are prevented** in the UI after a successful submit (form locks until **Start new decision**), and the backend rejects the same `client_decision_id` with HTTP 409 during a single API process lifetime.

## Agentic SOC Workflow

TrustOps uses a **real sequential agent orchestrator** in [`backend/agents/orchestrator.py`](backend/agents/orchestrator.py). The orchestrator executes specialized SOC agent roles in order and returns an **execution trace** to the UI. These are not uncontrolled autonomous bots; they are **tool-backed investigation roles** designed to make the workflow transparent, auditable, and demo-stable.

For the canonical alert **`TO-VPN-2026-514`**, the workflow runs seven steps:

1. **Evidence Agent** — queries Splunk and summarizes real alert telemetry (expect **8 rows: 7 failures and 1 success**).
2. **Triage Agent** — evaluates severity using event-driven rules (High / Medium / Low from failures, success-after-failure, geography, and `risk_score`).
3. **SPL Agent** — generates follow-up SPL and uses **Splunk AI Assistant Explain SPL** when available (local fallback otherwise).
4. **MITRE ATT&CK Mapping Agent** — maps Splunk-grounded evidence to enterprise ATT&CK tactics and techniques (e.g. **T1110 Brute Force**, **T1078 Valid Accounts**).
5. **Contradictory Evidence Agent** — identifies benign explanations, evidence gaps, and validation steps.
6. **SOP Agent** — maps findings to a suspected account-takeover response checklist.
7. **Trust Calibration Agent** — provides pre-decision human–AI oversight guidance.

Implementation modules live under **`backend/agents/`** (`evidence_agent.py`, `triage_agent.py`, `spl_agent.py`, `mitre_attack_agent.py`, and related files). Static plan templates are no longer used for **`/agent-plan`**; both **`/agent-run`** and **`/agent-plan`** invoke this orchestrator.

### MITRE ATT&CK Mapping Agent

TrustOps includes a **MITRE ATT&CK Mapping Agent** that maps Splunk-grounded evidence to relevant ATT&CK tactics and techniques. For the canonical VPN/SAML scenario, failed login bursts map to **Credential Access: Brute Force (T1110)**, while the successful VPN login using the target account maps to **Initial Access: Valid Accounts (T1078)**. The mapping appears in the investigation view, the agent execution trace, and the agent-run telemetry logged back to Splunk.

### MITRE ATT&CK Enrichment

TrustOps can optionally enrich ATT&CK mappings using MITRE’s **`mitreattack-python`** package and a local Enterprise ATT&CK STIX dataset at **`data/enterprise-attack.json`**. If the package or dataset is unavailable, TrustOps falls back to local mappings so the demo remains reliable.

```bash
pip install -r backend/requirements.txt
bash scripts/download_attack_data.sh
```

Verification: **`GET /alerts/TO-VPN-2026-514/agent-run`** should return **7 steps** and include the MITRE ATT&CK Mapping Agent with **T1078** and **T1110**.

### What makes this agentic?

- The backend **executes a multi-step investigation workflow**, not a single static paragraph.
- Each step has a **specialized SOC role** with a clear objective.
- Each step uses **alert context and/or Splunk evidence** produced by prior steps.
- The **Evidence Agent** performs a **real Splunk search** (not hardcoded counts in the UI).
- The **SPL Agent** uses **Splunk AI Assistant** where available, with transparent fallback labeling.
- The API returns an **execution trace**: tools used, evidence bullets, recommendations, per-step timestamps, and run status.
- The design **preserves analyst oversight** and avoids representing agents as fully autonomous black boxes.

### What it is not

- TrustOps does **not** claim to run five **fully autonomous, independent** agents.
- The current implementation is **sequential orchestrated workflow** with specialized agent roles—not unbounded multi-agent autonomy.
- **Deterministic/local fallback** logic is included for **demo reliability** and offline execution when SAIA or MCP is unavailable.

### API (agentic investigation)

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/alerts/{alert_id}/agent-run` | Run the orchestrated workflow; return `AgentRunResult` (`run_id`, `steps[]`, `final_summary`). |
| `POST` | `/alerts/{alert_id}/agent-run` | Same as GET; semantically starts a new run (new `run_id`). |
| `GET` | `/alerts/{alert_id}/agent-plan` | **Legacy-compatible route** that now executes the **same orchestrated workflow** (no longer returns the old static template plan). |
| `POST` | `/alerts/{alert_id}/chat` | Alert-scoped analyst chat grounded in Splunk evidence (SAIA with local fallback). |

The UI **Run agentic investigation** button calls **`POST /agent-run`** and renders the execution trace (summary stats, timeline, expandable step cards). **Recommended Follow-Up SPL** and **Challenge the AI** remain separate analyst surfaces. Decision telemetry records `agent_plan_viewed`, `follow_up_queries_viewed`, `contradictory_evidence_viewed`.

### Alert-Scoped Analyst Chat

TrustOps includes a scoped chat interface (**Ask Splunk AI about this alert**) that lets analysts ask Splunk AI Assistant follow-up questions about the selected alert. The chat is grounded in alert context and Splunk evidence—investigation summary, key evidence, MITRE mappings, contradictory evidence, and SOP guidance—and includes **local fallback** behavior for demo reliability. It is read-only investigation support, not a generic chatbot; containment and response actions require analyst approval.

### Agentic Workflow Observability

TrustOps logs **agent-step telemetry** to Splunk (`index=trustops_agent_runs`, `sourcetype=trustops:agent_step`) as JSON events—one row per agent step with `run_id`, `tools_used`, `duration_ms`, and summaries. Logging failures do not fail the workflow; the API returns `telemetry_warning` when needed.

- `GET /agent-runs/{run_id}/telemetry` — steps for a run from Splunk
- `GET /agent-runs/summary` — counts by agent/status, avg duration, recent `run_id`s

Create the index with `scripts/setup_splunk_indexes.sh` (includes `trustops_agent_runs`).

## Architecture

- **Diagram (Mermaid):** [`architecture.mmd`](architecture.mmd) — required hackathon architecture view; open in GitHub, VS Code Mermaid preview, or [mermaid.live](https://mermaid.live).
- **Narrative:** [`docs/architecture.md`](docs/architecture.md) — plain-language description of components and data flow.
- **Submission draft:** [`docs/devpost_submission.md`](docs/devpost_submission.md) — polished project story for Devpost / judges.

## Canonical demo story

All hackathon docs, sample data, SPL, and the UI should align on:

- **Primary alert:** `TO-VPN-2026-514` — multiple failed VPN/SAML attempts for **jsmith**, then a **successful** login from **Romania** (see `data/synthetic_auth_logs.csv` and `data/sample_alerts.json`).
- **Secondary (low severity) alert:** `TO-BASELINE-0001` — a few decision rows for contrast in `data/sample_decisions.csv`.

## Prerequisites

- **Splunk Enterprise** installed locally (default paths assume `/opt/splunk`).
- **Splunk Web** at `http://localhost:8000`.
- **Splunk management API** at `https://localhost:8089` (self-signed certificates are fine for local dev).
- **Python 3** for `scripts/generate_synthetic_data.py`.
- **curl** for `scripts/setup_splunk_indexes.sh`.
- Shell tools: `bash`, `chmod`.

## Environment variables

```bash
export SPLUNK_USER="cjalessi"
export SPLUNK_PASSWORD="your-splunk-password"
```

Use your real Splunk admin username (for example `cjalessi` if that is the account you created at install time).

Optional:

```bash
export SPLUNK_HOME="/opt/splunk"
export SPLUNK_MGMT_URL="https://localhost:8089"
export AUTH_CSV="/path/to/synthetic_auth_logs.csv"
export DECISIONS_CSV="/path/to/sample_decisions.csv"
```

The ingest scripts **validate** that `SPLUNK_USER` and `SPLUNK_PASSWORD` are set and exit with a clear error if not.

## Quick start

From the repository root:

```bash
chmod +x scripts/*.sh

python3 scripts/generate_synthetic_data.py
bash scripts/setup_splunk_indexes.sh
bash scripts/ingest_auth_logs.sh
bash scripts/ingest_decisions.sh
```

Then open Splunk at `http://localhost:8000`, set the time picker to **Last 7 days** or **All time** (demo timestamps are in **May 2026**), and run the verification searches below or install the dashboard from `splunk/trustops_dashboard.xml` (see `docs/phase1_setup.md`).

## Repository layout

| Path | Description |
|------|-------------|
| `data/synthetic_auth_logs.csv` | Generated VPN/auth CSV (regenerate via script). |
| `data/sample_decisions.csv` | Sample analyst decision telemetry (8–12 style rows; 12 data rows + header). |
| `data/sample_alerts.json` | Example alert objects for UI/API work. |
| `scripts/generate_synthetic_data.py` | Builds the synthetic auth CSV. |
| `scripts/setup_splunk_indexes.sh` | Creates indexes via REST (`curl`). |
| `scripts/ingest_auth_logs.sh` | Oneshot ingest into `trustops` / `trustops:auth`. |
| `scripts/ingest_decisions.sh` | Oneshot ingest into `trustops_decisions` / `trustops:decision`. |
| `splunk/core_searches.spl` | Reference SPL (copy **one** search at a time). |
| `splunk/trustops_dashboard.xml` | Simple Splunk classic dashboard definition. |
| `docs/phase1_setup.md` | Detailed setup and verification. |
| `backend/` | **Phase 2** FastAPI service (Splunk SDK, SAIA REST client, optional MCP, deterministic `ai_agent` fallback). |
| `backend/agents/` | Sequential agent orchestrator and per-role agent modules. |
| `backend/agents/orchestrator.py` | `run_agentic_investigation()` — wires Evidence → Triage → SPL → MITRE ATT&CK → Challenge → SOP → Trust Calibration. |
| `backend/agents/evidence_agent.py` | Splunk auth search + factual evidence summary. |
| `backend/agents/triage_agent.py` | Severity rules from Splunk-grounded stats. |
| `backend/agents/spl_agent.py` | Follow-up SPL + SAIA explain (with fallback). |
| `backend/agents/mitre_attack_agent.py` | ATT&CK tactic/technique mapping (T1078, T1110 for VPN demo). |
| `backend/attack_enrichment.py` | Optional `mitreattack-python` enrichment from local STIX. |
| `backend/agents/contradictory_evidence_agent.py` | Benign explanations, gaps, validation steps. |
| `backend/agents/sop_agent.py` | Account-takeover or generic response checklist. |
| `backend/agents/trust_calibration_agent.py` | Pre-decision trust calibration guidance. |
| `backend/agent_run_logger.py` | Writes per-step JSON telemetry to `trustops_agent_runs`. |
| `docs/configure_splunk_mcp_server.md` | Splunk MCP Server setup, tokens, and Cursor client notes. |
| `frontend/` | **Phase 3** Vite + React analyst console. |
| `architecture.mmd` | Mermaid architecture diagram (repo root). |
| `docs/architecture.md` | Architecture narrative. |
| `docs/devpost_submission.md` | Devpost / hackathon submission text. |
| `scripts/dev_check.sh` | Pre-flight check: Splunk + env + optional API/UI reachability. |

## Phase 4 — Three-minute demo (full stack)

Use **three terminals**. Adjust paths if your clone is not `~/trustops-splunk`.

### Terminal 1 — Splunk

```bash
sudo -u splunk /opt/splunk/bin/splunk status
```

If it is not running:

```bash
sudo -u splunk /opt/splunk/bin/splunk start
```

### Terminal 2 — Backend

```bash
cd ~/trustops-splunk/backend
source .venv/bin/activate
export SPLUNK_USER="cjalessi"
export SPLUNK_PASSWORD="your-splunk-password"
export SPLUNK_VERIFY_SSL=false
uvicorn app:app --reload --host 0.0.0.0 --port 8001
```

### Terminal 3 — Frontend

```bash
cd ~/trustops-splunk/frontend
npm run dev
```

Open **http://localhost:5173**.

### Developer pre-flight (optional)

With `SPLUNK_USER` and `SPLUNK_PASSWORD` exported in your shell (values never printed):

```bash
bash scripts/dev_check.sh
```

This verifies Splunk is running and credentials are set; it **does not** start services. It also **informationally** probes `http://localhost:8001/health` and `http://localhost:5173` (backend/UI down does **not** fail the script).

### Verify the demo flow (UI)

1. **Backend:** Online. **Splunk:** Reachable.
2. Select **`TO-VPN-2026-514`** (default).
3. In **Investigation**, confirm narrative, **Trust Calibration Notice** (level **High** on **`TO-VPN-2026-514`**), and **SPL transparency** + event table. Try **Explain SPL** / **Generate SPL** when SAIA is connected.
4. Click **Run agentic investigation**. Confirm the execution trace shows **seven steps**: Evidence, Triage, SPL, MITRE ATT&CK, Contradictory Evidence, SOP, Trust Calibration. Confirm **MITRE ATT&CK Mapping** panel and agent card show **T1078** and **T1110**. Confirm **Evidence** reports **8 rows, 7 failures, and 1 success**. Confirm **SPL Agent** shows **`splunk_ai_assistant_explain_spl`** in tools used when SAIA is available, or **local** fallback tools if not. Note **Agent run telemetry logged to Splunk** when `trustops_agent_runs` index exists.
5. In **Analyst decision**, work through four sections: **Decision Details** → **Evidence Review Checklist** (≥2) → **Challenge the AI Recommendation** → **Submit and Feedback**. The readiness line shows **Ready to submit** when checklist, challenge fields, and analyst decision are complete.
6. Submit as **`demo_analyst`** → feedback appears under **Submit and Feedback** (bias risk badge + learning point).
7. Refresh **Decision metrics** (includes **Avg bias risk** when extended telemetry exists).

**UI layout notes:** Trust Calibration sits inline under the AI recommendation (collapsible block holds severity/actions). SPL and the event timeline stay in dedicated regions so the table remains visible without excessive scrolling past narrative text.

### Verify in Splunk

```spl
index=trustops_decisions sourcetype=trustops:decision analyst="demo_analyst"
| table _time alert_id analyst analyst_decision final_severity confidence_score trust_score ai_recommendation_status notes
```

## Phase 3 — React analyst UI

From the repository root:

```bash
cd frontend
npm install
npm run dev
```

Then open **http://localhost:5173** (default Vite port). The UI reads the API base URL from **`VITE_API_BASE_URL`** (default **`http://localhost:8001`**). Use `frontend/.env.local` if your API runs elsewhere.

**Flow:** run Splunk + ingest Phase 1 data, run the **Phase 2** backend on port **8001**, then start the frontend — status bar shows backend/Splunk health; **TO-VPN-2026-514** is selected by default; submit a decision to refresh Splunk-backed metrics.

Details: **`frontend/README.md`**.

## Phase 2 — FastAPI backend

Run the API from `backend/` (default **http://localhost:8001** so it does not conflict with Splunk Web on **8000**).

### Environment variables (backend)

Required:

```bash
export SPLUNK_USER="cjalessi"
export SPLUNK_PASSWORD="your-splunk-password"
```

Optional (defaults shown):

```bash
export SPLUNK_HOST="localhost"
export SPLUNK_PORT="8089"
export SPLUNK_SCHEME="https"
export SPLUNK_VERIFY_SSL="false"
export SPLUNK_AUTH_INDEX="trustops"
export SPLUNK_DECISION_INDEX="trustops_decisions"
export SPLUNK_AGENT_RUN_INDEX="trustops_agent_runs"
```

Optional — **Splunk AI Assistant** and **MCP** (see `backend/.env.example` and `docs/configure_splunk_mcp_server.md`):

```bash
export SAIA_SOURCE_APP_ID="search"
export SAIA_USE_MCP="false"   # SAIA via Splunk REST /predict (recommended on Enterprise 10.2.x)
export SPLUNK_MCP_URL="http://localhost:8000/en-US/splunkd/__raw/services/mcp"
export SPLUNK_MCP_TOKEN_FILE="$HOME/.splunk_mcp_token"
```

You can also create `backend/.env` with the same keys (see `python-dotenv` in `backend/README.md`).

### Run the API

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --reload --host 0.0.0.0 --port 8001
```

### API (MVP)

| Method | Path | Purpose |
|--------|------|--------|
| `GET` | `/health` | Service status and Splunk configuration/reachability. |
| `GET` | `/alerts` | Static catalog from `data/sample_alerts.json`. |
| `GET` | `/alerts/{alert_id}` | One alert by id. |
| `GET` | `/alerts/{alert_id}/events` | Splunk auth events for that `alert_id` + `spl_query_used`. |
| `GET` | `/alerts/{alert_id}/investigation` | Alert + events + investigation summary + trust calibration + `follow_up_queries` + `contradictory_evidence` + SPL used. |
| `GET` | `/alerts/{alert_id}/agent-run` | Run sequential agent orchestrator; returns `AgentRunResult` execution trace; logs steps to Splunk when configured. |
| `POST` | `/alerts/{alert_id}/agent-run` | Same orchestration as GET; starts a new `run_id`. |
| `GET` | `/alerts/{alert_id}/agent-plan` | Legacy-compatible alias: **same orchestrated workflow** as `agent-run` (not the old static plan). |
| `GET` | `/agent-runs/{run_id}/telemetry` | Agent step events for a run from `trustops_agent_runs`. |
| `GET` | `/agent-runs/summary` | Aggregate agent-step metrics from Splunk. |
| `GET` | `/alerts/{alert_id}/follow-up-queries` | Recommended follow-up SPL queries (title, purpose, priority). |
| `POST` | `/saia/explain` | Natural-language SPL explanation via Splunk AI Assistant (local fallback if unavailable). |
| `POST` | `/saia/generate` | Generate SPL from a prompt via Splunk AI Assistant (local fallback if unavailable). |
| `POST` | `/decisions` | Log decision with trust-calibration fields and `client_decision_id`; returns automation bias score, feedback, and learning point. Duplicate `client_decision_id` → HTTP 409. |
| `GET` | `/decisions/summary` | Aggregate by `ai_recommendation_status` (includes `avg_automation_bias_risk_score` when present). |
| `GET` | `/decisions/{alert_id}` | Decision rows for one alert from Splunk. |

**CORS** is enabled for `http://localhost:5173` and `http://localhost:3000` (Vite / CRA).

Smoke-test URLs: `http://localhost:8001/health`, `http://localhost:8001/alerts`, `http://localhost:8001/alerts/TO-VPN-2026-514/investigation`, `http://localhost:8001/decisions/summary`.

Full setup and `curl` examples: **`backend/README.md`**.

## How AI is used

TrustOps uses AI in **three complementary ways**, with deterministic fallbacks for reliable demos:

1. **Splunk AI Assistant** — **Explain SPL** and **Generate SPL** in the investigation panel (`POST /saia/explain`, `POST /saia/generate`). Backend uses Splunk’s SAIA **`/predict`** REST flow (aligned with Search UI on Enterprise 10.2.x).
2. **Splunk AI Assistant / MCP-assisted investigation support** — Where configured, SAIA and the **Splunk MCP Server** enrich investigation context, optional MCP `saia_*` tools, and IDE-side agent access (`docs/configure_splunk_mcp_server.md`).
3. **Local deterministic fallback** — **`ai_agent.py`** (investigation narrative), **`backend/agents/`** rules (orchestrator steps), and local SPL explain/generate paths when SAIA is unavailable—so hackathon and offline runs stay coherent.

The **sequential agent orchestrator** can call **AI-assisted functions as tools inside agent steps** (for example SPL Agent → `splunk_ai_assistant_explain_spl`). The workflow remains **transparent and auditable**: each step records `tools_used`, evidence, and timestamps in the execution trace (and optionally in `trustops_agent_runs`).

### Splunk AI Assistant and Splunk MCP (primary)

- **SAIA** — Explain/generate SPL and narrative support; UI badges show **Splunk AI Assistant** vs **Local fallback**.
- **MCP** — Bridge for searches, indexes, and optional SAIA tools when `SAIA_USE_MCP=true` (often disabled on CMP stacks in favor of `/predict`).

### Deterministic fallback (reliability)

- **`ai_agent.py`** — Investigation summary for `/investigation` when SAIA paths are not used for narrative.
- **`backend/agents/*`** — Rule-based triage, evidence parsing, contradictory evidence, SOP mapping, and trust calibration without requiring cloud AI for every step.

The backend prefers **SAIA/MCP where available**; analysts always see which tools ran on each agent step.

## Verify authentication data

In **Search & Reporting**, time range **Last 7 days** or **All time**:

```spl
index=trustops sourcetype=trustops:auth alert_id="TO-VPN-2026-514"
| sort _time
| table _time user src_ip geo_country action auth_method risk_score alert_id scenario
```

You should see **jsmith** with multiple failed VPN/SAML attempts followed by a success from **Romania**.

## Verify decision telemetry

```spl
index=trustops_decisions sourcetype=trustops:decision
| eval _is_header=if(match(_raw,"^timestamp,alert_id,analyst,"),1,0)
| where _is_header=0
| fields - _is_header
| rex field=_raw "^(?<timestamp>[^,]+),(?<alert_id>[^,]+),(?<analyst>[^,]+),(?<ai_recommendation>[^,]+),(?<analyst_decision>[^,]+),(?<final_severity>[^,]+),(?<confidence_score>\d+),(?<trust_score>\d+),(?<time_to_decision_seconds>\d+),(?<ai_recommendation_status>[^,]+),(?<evidence_reviewed_count>\d+),(?<sop_followed>[^,]+),(?<notes>[^\r\n]+)"
| eval confidence_score=tonumber(confidence_score), trust_score=tonumber(trust_score), time_to_decision_seconds=tonumber(time_to_decision_seconds)
| stats count as decisions avg(confidence_score) as avg_confidence avg(trust_score) as avg_trust avg(time_to_decision_seconds) as avg_time_to_decision by ai_recommendation_status
```

You should see rows for **`accepted`**, **`modified`**, and **`rejected`** (plus metrics split by status).

## Example Splunk searches

**User authentication timeline (jsmith)**

```spl
index=trustops sourcetype="trustops:auth"
| eval _is_header=if(match(_raw,"^timestamp,user,"),1,0)
| where _is_header=0
| fields - _is_header
| rex field=_raw "^(?<timestamp>[^,]+),(?<user>[^,]+),(?<src_ip>[^,]+),(?<dest_host>[^,]+),(?<action>[^,]+),(?<geo_country>[^,]+),(?<auth_method>[^,]+),(?<risk_score>\d+),(?<event_type>[^,]+),(?<alert_id>[^,]*),(?<scenario>[^,\r\n]+)"
| where user="jsmith"
| eval _time=strptime(timestamp, "%Y-%m-%dT%H:%M:%SZ")
| sort _time
| table _time user src_ip action geo_country auth_method risk_score event_type alert_id scenario
```

**Failed-login burst (demo threshold)**

```spl
index=trustops sourcetype="trustops:auth"
| eval _is_header=if(match(_raw,"^timestamp,user,"),1,0)
| where _is_header=0
| fields - _is_header
| rex field=_raw "^(?<timestamp>[^,]+),(?<user>[^,]+),(?<src_ip>[^,]+),(?<dest_host>[^,]+),(?<action>[^,]+),(?<geo_country>[^,]+),(?<auth_method>[^,]+),(?<risk_score>\d+),(?<event_type>[^,]+),(?<alert_id>[^,]*),(?<scenario>[^,\r\n]+)"
| where action="failure" AND auth_method="vpn_saml"
| eval _time=strptime(timestamp, "%Y-%m-%dT%H:%M:%SZ")
| bin _time span=15m
| stats count as failed_logins dc(src_ip) as distinct_src by _time user
| where failed_logins>=5
```

More examples (alert pivot for `TO-VPN-2026-514`, IP history, risk rollups, decision summaries) live in `splunk/core_searches.spl`.

## Next steps

Future work (see also [`docs/architecture.md`](docs/architecture.md) and [`docs/devpost_submission.md`](docs/devpost_submission.md)):

- **Expand agent-run observability** — richer dashboards and SLA-style metrics on `trustops_agent_runs` (per-step logging exists today).
- **Expand MCP tool coverage** for agentic retrieval over lookups, knowledge objects, and enrichment.
- **More alert scenarios** beyond VPN/geo (cloud identity, endpoint, email) using the same decision schema.
- **SOP mapping** — link recommendations to internal runbooks and capture compliance signals.
- **MITRE ATT&CK** tagging on evidence and analyst decisions.
- **SOAR-style response recommendations** (human-approved) with audit trails.
- Production hardening: API authentication, TLS to Splunk, and secrets management.

The end-to-end demo path is:

**React UI (Phase 3) → FastAPI (Phase 2) → Splunk + sequential agent orchestrator + SAIA/MCP → investigation → `POST /decisions` → Splunk dashboards**

## License / hackathon

Built for a hackathon demo; replace synthetic data and hardening steps before production use.
