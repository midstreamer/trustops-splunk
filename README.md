## License

This project is released under the MIT License. See [`LICENSE.md`](LICENSE.md) for details.

TrustOps is a hackathon prototype and demonstration project. It may reference or integrate with third-party tools, platforms, APIs, datasets, and open-source packages, including Splunk, Splunk AI Assistant, Splunk MCP Server, MITRE ATT&CK, and `mitreattack-python`. Those third-party components remain subject to their own licenses and terms of use.

# TrustOps for Splunk

TrustOps is a **human-in-the-loop agentic security triage assistant** for Splunk. It helps SOC analysts investigate suspicious alerts using Splunk data, **Splunk AI Assistant (SAIA)**, and optional **Splunk MCP Server** tooling, then captures **analyst decision telemetry** (trust, confidence, final decision, and automatically recorded time-to-decision).

This repository implements **Phase 1** (Splunk foundation), **Phase 2** (FastAPI backend with SAIA/MCP integration), **Phase 3** (React analyst UI), and **Phase 4** (demo polish: runbook, dev check script, architecture diagram, Devpost narrative). Phase 1 covers synthetic VPN authentication data, **sample analyst decisions**, indexes, ingestion scripts, starter searches, and a Splunk dashboard. Phase 2 exposes a local API for alerts, Splunk-backed events, **SAIA-first investigation** (`saia_investigation.py`), **agentic investigation** (seven-step orchestrator), and decision logging back into Splunk—with a **deterministic local fallback** for reliable offline demos. Phase 3 is a Vite + React console that is **SAIA-first with auto-run agentic investigation**: Splunk AI analysis on load, alert-scoped SAIA chat, seven inline agent result sections, and **Explain SPL** on follow-up queries (`POST /saia/generate` is API-only; there is no Generate SPL button in the UI).

## Agentic Ops Positioning

TrustOps is built for the **Splunk Agentic Ops** model: it uses Splunk data, **Splunk AI Assistant**, optional **MCP-enabled** tooling, and a **sequential agent orchestrator** to support SOC alert investigation. Each agent role performs a defined task and returns an **execution trace**, allowing analysts to see what evidence was used, which tools were called, and how recommendations were developed.

TrustOps intentionally keeps the **analyst in control**. The system supports investigation and recommendation development, but **final disposition remains a human decision** that is logged back into Splunk with trust, confidence, evidence review, and automation-bias telemetry.

## AI and MCP Integration

TrustOps integrates with **Splunk AI Assistant** as the primary AI path (Splunk REST **`/predict`**, aligned with Search UI on Enterprise 10.2.x). **Splunk MCP** is **optional** (`SAIA_USE_MCP=false` by default) for IDE-side agents and optional backend tool-calling when configured.

The system uses Splunk data to retrieve alert context, generate investigation support, and produce analyst-facing recommendations. A deterministic local fallback is included so the demo can run reliably when SAIA is unavailable.

This design allows TrustOps to demonstrate both Splunk-native AI integration and dependable local execution for hackathon judging.

## Human-AI Trust Calibration Layer

TrustOps captures whether analysts **accepted**, **modified**, or **rejected** AI recommendations—and whether that disposition was earned through evidence review.

- **Trust Calibration Notice** on high-confidence investigations (e.g. **`TO-VPN-2026-514`**) warns against automation bias before severity/actions.
- **Evidence Review Checklist** requires at least two independent checks before submit; count syncs to `evidence_reviewed_count`.
- **Challenge the AI Recommendation** requires supporting and contradicting evidence (stored in Splunk telemetry).
- **Automation bias risk score** (0–9) and **Low / Moderate / High** level are computed on submit and returned with **post-decision feedback** for analyst upskilling.
- **Time to decision** is **recorded automatically** by the system when the analyst submits (elapsed since investigation loaded)—analysts do not enter it manually.
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

### React UI (investigation workflow)

When an analyst selects an alert, the UI **automatically** calls **`POST /alerts/{alert_id}/agent-run`** (no manual run button). Investigation content appears in this order:

1. **Status bar** — Backend, Splunk, **Agents: Running…** while the workflow executes, and a compact **Investigation flow** timeline (seven steps).
2. **Agentic investigation** status badge (`running` / `complete` / `not run`) at the top of the investigation panel.
3. **Splunk AI analysis** — SAIA-generated summary, key evidence, severity/actions/confidence, AI recommendation, and trust calibration strip; **`investigation_source`** badge shows **Splunk AI Assistant** vs **Local fallback**.
4. **Splunk AI Assistant chat** — alert-scoped follow-up Q&A (always visible).
5. **Seven agent callouts** — Evidence → Triage → SPL → MITRE ATT&CK → Contradictory Evidence → SOP → Trust Calibration, with two-column **Evidence / Recommendations** where applicable; follow-up SPL includes **Explain SPL** via SAIA.

The UI **does not show** the raw SPL query block, event timeline table, or aggregate “Investigation result” summary (those remain available from the API). Decision telemetry records `agent_plan_viewed`, `follow_up_queries_viewed`, `contradictory_evidence_viewed`.

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

## GitHub Pages (live UI)

The React analyst console is published automatically on every push to **`main`**:

**https://midstreamer.github.io/trustops-splunk/**

Workflow: [`.github/workflows/deploy-pages.yml`](.github/workflows/deploy-pages.yml) builds `frontend/` with `VITE_BASE_PATH=/trustops-splunk/` and deploys to GitHub Pages.

GitHub Pages hosts the **static UI only**. The FastAPI backend and Splunk must run on a reachable host (your laptop, VM, or cloud).

**From another device** (phone, second PC, GitHub Pages URL):

1. Start the backend bound to all interfaces: `uvicorn app:app --host 0.0.0.0 --port 8001`
2. On the hosted UI, use the **Backend connection required** banner to enter your API URL, e.g. `http://192.168.1.10:8001` (your machine's LAN IP), or open:
   `https://midstreamer.github.io/trustops-splunk/?api=http://YOUR_SERVER:8001`
3. Ensure the backend allows CORS from `https://midstreamer.github.io` (default in `backend/config.py`).

**Build-time API URL** (optional): In GitHub → **Settings → Secrets and variables → Actions → Variables**, set **`VITE_API_BASE_URL`** to your public API base URL, then redeploy.

Local Pages-style build:

```bash
cd frontend
VITE_BASE_PATH=/trustops-splunk/ npm run build
npm run preview -- --base /trustops-splunk/
```

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
| `backend/saia_investigation.py` | SAIA-first investigation resolver for `GET /investigation` (fallback to `ai_agent.py`). |
| `backend/smoke_test.py` | Startup and manual smoke tests for SAIA + agentic workflow. |
| `scripts/smoke_test.sh` | CLI wrapper: `npm run smoke-test` / `smoke-test:full`. |
| `package.json` | Root scripts: `dev:api`, `dev:frontend`, `smoke-test`, `smoke-test:full`. |
| `scripts/start_backend.sh` | Start API with `.env`, venv bootstrap, and startup smoke test. |
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
cd ~/trustops-splunk
npm run dev:api
```

Or manually:

```bash
bash ~/trustops-splunk/scripts/start_backend.sh
```

The backend loads `backend/.env`, runs on **http://localhost:8001**, and runs a **quick startup smoke test** by default (see [Smoke test](#smoke-test) below).

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

1. **Status bar:** Backend online, Splunk reachable; on alert select the **Investigation flow** timeline animates while agents run.
2. Select **`TO-VPN-2026-514`** (default).
3. **Splunk AI analysis** loads with the **Splunk AI Assistant** source badge (not **Local fallback** when SAIA is connected). Confirm summary, key evidence, severity/actions, AI recommendation, and **Trust Calibration** strip (level **High** on **`TO-VPN-2026-514`**).
4. **Agentic investigation** badge shows **running**, then **complete**; agents auto-run without a manual button. Confirm seven agent sections populate (Evidence **8 rows, 7 failures, 1 success**; MITRE **T1078** and **T1110**; SPL Agent tools include **`splunk_ai_assistant_explain_spl`** when SAIA is available).
5. Use **Explain SPL** on a follow-up query in the SPL Agent section; use **Splunk AI Assistant chat** for follow-up questions.
6. In **Analyst decision**, work through four sections: **Decision Details** → **Evidence Review Checklist** (≥2) → **Challenge the AI Recommendation** → **Submit and Feedback**. The readiness line shows **Ready to submit** when checklist, challenge fields, and analyst decision are complete.
7. Submit as **`demo_analyst`** → feedback appears (bias risk badge, learning point, and **time to decision recorded automatically**).
8. **Decision metrics** panel refreshes (includes **Avg bias risk** when extended telemetry exists).

**UI layout notes:** Agentic status sits at the top of the investigation panel; Splunk AI analysis, chat, and seven agent callouts follow. Trust Calibration sits inline under the AI recommendation. Raw SPL-used text and the event timeline table are not shown in the UI (available via API).

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

**Flow:** run Splunk + ingest Phase 1 data, run the **Phase 2** backend on port **8001**, then start the frontend — status bar shows backend/Splunk health and the agent timeline; **TO-VPN-2026-514** is selected by default; agents auto-run on alert select; submit a decision to refresh Splunk-backed metrics.

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

Optional — **startup smoke test** (see `backend/.env.example`):

```bash
export TRUSTOPS_STARTUP_SMOKE_TEST="quick"   # quick | full | skip
export TRUSTOPS_SMOKE_CANONICAL_ALERT="TO-VPN-2026-514"
export TRUSTOPS_API_BASE_URL="http://127.0.0.1:8001"
```

You can also create `backend/.env` with the same keys (see `python-dotenv` in `backend/README.md`).

### Run the API

```bash
bash scripts/start_backend.sh
```

Or manually:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --reload --host 0.0.0.0 --port 8001
```

### Smoke test

On backend startup, a **quick smoke test** runs in the background by default (`TRUSTOPS_STARTUP_SMOKE_TEST=quick`): health, alerts, SAIA investigation (`investigation_source=saia`), and SAIA explain. Results are logged to the uvicorn console.

Manual checks from the repo root:

```bash
npm run smoke-test          # quick (waits for /health)
npm run smoke-test:full     # also agent 7-step run + alert chat
bash scripts/smoke_test.sh --wait --full
```

Set `TRUSTOPS_STARTUP_SMOKE_TEST=skip` to disable startup checks.

### API (MVP)

| Method | Path | Purpose |
|--------|------|--------|
| `GET` | `/health` | Service status and Splunk configuration/reachability. |
| `GET` | `/alerts` | Static catalog from `data/sample_alerts.json`. |
| `GET` | `/alerts/{alert_id}` | One alert by id. |
| `GET` | `/alerts/{alert_id}/events` | Splunk auth events for that `alert_id` + `spl_query_used`. |
| `GET` | `/alerts/{alert_id}/investigation` | Alert + events + **SAIA-first** investigation (`investigation_source`, summary, evidence, trust calibration, follow-ups, contradictory evidence, MITRE mappings). |
| `GET` | `/alerts/{alert_id}/agent-run` | Run sequential agent orchestrator; returns `AgentRunResult` execution trace; logs steps to Splunk when configured. |
| `POST` | `/alerts/{alert_id}/agent-run` | Same orchestration as GET; starts a new `run_id` (UI auto-calls on alert select). |
| `GET` | `/alerts/{alert_id}/agent-plan` | Legacy-compatible alias: **same orchestrated workflow** as `agent-run` (not the old static plan). |
| `POST` | `/alerts/{alert_id}/chat` | Alert-scoped SAIA chat grounded in investigation context (logged to Splunk). |
| `GET` | `/agent-runs/{run_id}/telemetry` | Agent step events for a run from `trustops_agent_runs`. |
| `GET` | `/agent-runs/summary` | Aggregate agent-step metrics from Splunk. |
| `GET` | `/alerts/{alert_id}/follow-up-queries` | Recommended follow-up SPL queries (title, purpose, priority). |
| `POST` | `/saia/explain` | Natural-language SPL explanation via Splunk AI Assistant (local fallback if unavailable). |
| `POST` | `/saia/generate` | Generate SPL from a prompt via Splunk AI Assistant (local fallback if unavailable). |
| `POST` | `/decisions` | Log decision with trust-calibration fields and `client_decision_id`; returns automation bias score, feedback, and learning point. Duplicate `client_decision_id` → HTTP 409. |
| `GET` | `/decisions/summary` | Aggregate by `ai_recommendation_status` (includes `avg_automation_bias_risk_score` when present). |
| `GET` | `/decisions/{alert_id}` | Decision rows for one alert from Splunk. |

**CORS** is enabled for `http://localhost:5173` and `http://localhost:3000` (Vite / CRA).

Smoke-test URLs: `http://localhost:8001/health`, `http://localhost:8001/alerts`, `http://localhost:8001/alerts/TO-VPN-2026-514/investigation`, `http://localhost:8001/decisions/summary`. Or run `npm run smoke-test`.

Full setup and `curl` examples: **`backend/README.md`**.

## How AI is used

TrustOps uses AI in **five complementary layers**, with deterministic fallbacks and source badges so analysts always know what ran:

1. **SAIA investigation on load** — `resolve_investigation()` in [`backend/saia_investigation.py`](backend/saia_investigation.py) powers the top **Splunk AI analysis** block (`GET /investigation`; badge: **Splunk AI Assistant** vs **Local fallback**).
2. **SAIA alert chat** — `POST /alerts/{id}/chat` for follow-up questions grounded in alert context and evidence.
3. **Agentic orchestrator** — seven sequential agents (`POST /agent-run`, auto-triggered by the UI); SAIA assists inside **SPL Agent** (`splunk_ai_assistant_explain_spl`) and **Contradictory Evidence Agent** (`splunk_ai_assistant_context`).
4. **SAIA explain on follow-up SPL** — **Explain SPL** in the SPL Agent section (`POST /saia/explain`). **`POST /saia/generate`** exists for API/IDE use but is not wired in the React UI.
5. **Deterministic fallback** — [`backend/ai_agent.py`](backend/ai_agent.py) and rule-based agents when SAIA is unavailable.

The backend uses Splunk REST **`/predict`** (v1) as the primary SAIA path on Enterprise 10.2.x. **MCP is optional** (`SAIA_USE_MCP=false` by default). Each agent step records `tools_used`, evidence, and timestamps in the execution trace and in `trustops_agent_runs` when configured.

### Splunk AI Assistant (primary)

- **SAIA** — Investigation narrative, chat, and SPL explain; UI badges show **Splunk AI Assistant** vs **Local fallback**.
- **MCP** — Optional bridge for IDE agents and backend tool-calling when `SAIA_USE_MCP=true` and tokens are configured (`docs/configure_splunk_mcp_server.md`).

### Deterministic fallback (reliability)

- **`ai_agent.py`** — Investigation summary when SAIA is unreachable.
- **`backend/agents/*`** — Rule-based triage, evidence parsing, contradictory evidence, SOP mapping, and trust calibration without requiring cloud AI for every step.

The backend prefers **SAIA where available**; analysts see source badges on investigation load and `tools_used` on each agent step.

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

- **Richer agent-run dashboards** — SLA-style metrics and visualizations on `trustops_agent_runs` (per-step logging exists today).
- **Expand MCP tool coverage** for agentic retrieval over lookups, knowledge objects, and enrichment.
- **More alert scenarios** beyond VPN/geo (cloud identity, endpoint, email) using the same decision schema.
- **Generate SPL in the UI** — wire `POST /saia/generate` into the investigation panel.
- **SOAR-style response recommendations** (human-approved) with audit trails.
- Production hardening: API authentication, TLS to Splunk, and secrets management.

The end-to-end demo path is:

**React UI (Phase 3) → FastAPI (Phase 2) → Splunk + SAIA + sequential agent orchestrator → investigation → `POST /decisions` → Splunk dashboards**

## License / hackathon

Built for a hackathon demo; replace synthetic data and hardening steps before production use.
