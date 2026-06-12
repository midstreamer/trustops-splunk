# TrustOps architecture

This document complements the Mermaid diagram in the repository root: [`architecture.mmd`](../architecture.mmd). Open that file in GitHub, VS Code (Mermaid preview), or any Mermaid-compatible viewer to see the visual flow.

## Diagram walkthrough (hackathon checklist)

1. **Synthetic security data** is loaded into Splunk **`index=trustops`** (authentication-style events for the demo scenario).
2. **Splunk Enterprise** stores those events and exposes **Splunk AI Assistant** and optionally the **Splunk MCP Server** for agentic investigation support.
3. The **FastAPI backend** queries Splunk via the SDK and orchestrates investigation through **Splunk AI Assistant** (primary, REST `/predict`) with a **deterministic local fallback** when SAIA is unavailable.
4. **Splunk MCP** (optional, off by default) can bridge IDE agents and backend tool-calling to Splunk capabilities when configured.
5. The **React analyst UI** shows the **alert queue**, **investigation panel** (agentic status → SAIA analysis → chat → seven agent sections), **decision form**, and **metrics**. Selecting an alert **auto-starts** the seven-agent workflow; the **status bar** shows a compact investigation-flow timeline.
6. **Agent-step telemetry** is written to **`index=trustops_agent_runs`** as the workflow completes.
7. The **analyst submits a decision** through the UI (`POST /decisions`); **time to decision** is recorded automatically.
8. **FastAPI writes decision telemetry** to Splunk **`index=trustops_decisions`**.
9. A **Splunk dashboard** (bundled XML in the repo) visualizes **human–AI decision metrics** alongside security data.

## Plain-language overview

TrustOps is a **human-in-the-loop agentic triage loop** around Splunk: authentication events live in Splunk, the backend assembles evidence and **SAIA-assisted investigation context**, a **seven-agent workflow** runs automatically when an analyst selects an alert, and analysts record **how they used AI guidance** before decisions are written back to Splunk for **dashboards and research**.

### 1. Data in Splunk

- **Authentication-style events** are stored in **`index=trustops`** with **`sourcetype=trustops:auth`**. In the hackathon repo, rows come from generated CSV and align on canonical demo alert **`TO-VPN-2026-514`** (jsmith VPN/SAML failures, then successful Romania login).
- **Analyst decision telemetry** is stored in **`index=trustops_decisions`** with **`sourcetype=trustops:decision`**. Each event is a single CSV-shaped line so Splunk panels can parse it consistently.
- **Agent and chat telemetry** share **`index=trustops_agent_runs`** with distinct sourcetypes (see [Splunk telemetry indexes](#splunk-telemetry-indexes) below).

### 2. Splunk AI Assistant and Splunk MCP

- **Splunk AI Assistant (SAIA)** is the **primary AI path**. TrustOps calls SAIA through the same **v1 `/predict`** REST path the Search UI uses on Enterprise 10.2.x (reliable on CMP-connected stacks). SAIA powers investigation narrative on load, alert-scoped chat, and SPL explain in agent steps.
- **Splunk MCP Server** is **optional** (`SAIA_USE_MCP=false` by default). When enabled, MCP can complement SAIA for IDE-side agents and optional backend tool-calling. MCP is not required for the demo UI path.

### 3. FastAPI backend — two-phase investigation

The backend sits on **port 8001** (by default) so it does not collide with Splunk Web on **8000**. The React UI triggers investigation in **two phases**:

| Phase | Trigger | What runs |
|-------|---------|-----------|
| **A — On load** | `GET /alerts/{id}/investigation` | Splunk auth search → **`resolve_investigation()`** (SAIA-first via `saia_investigation.py`; fallback to `ai_agent.py`) → trust calibration → contradictory evidence, follow-up SPL, and MITRE resolver functions for pre-run UI fallbacks |
| **B — Auto-run** | `POST /alerts/{id}/agent-run` (UI on alert select) | **`run_agentic_investigation()`** — seven sequential agents; per-step JSON logged to `trustops_agent_runs` |

**AI modes** (within both phases):

| Mode | Role |
|------|------|
| **Splunk AI Assistant** | Primary: investigation narrative, chat, SPL explain, and context inside agent steps. |
| **Deterministic local fallback** | Rule-based `ai_agent.py` and agent modules when SAIA is unreachable—repeatable narratives for offline demos. |

Shared backend responsibilities:

- Serve the **alert catalog** (from `data/sample_alerts.json`) for the UI queue.
- Run **Splunk searches** (SDK) for auth events scoped to an `alert_id` (SPL available via API; not shown in the current UI).
- Run **agent orchestrator** (`backend/agents/`) via **`GET`/`POST /alerts/{id}/agent-run`** (seven steps including **MITRE ATT&CK Mapping Agent**); log each step to **`index=trustops_agent_runs`** (`trustops:agent_step` JSON events); query via **`/agent-runs/{run_id}/telemetry`** and **`/agent-runs/summary`**.
- Optional **MITRE ATT&CK enrichment** via `mitreattack-python` and local `data/enterprise-attack.json` (`backend/attack_enrichment.py`); **local fallback mappings** when package or STIX file is unavailable.
- Expose **`POST /saia/explain`** and **`POST /saia/generate`** (explain is used in the UI; generate is API-only today).
- Accept **`POST /decisions`** and write rows to **`trustops_decisions`** via Splunk’s HTTP receiver (including agentic panel view flags).
- Run a **startup smoke test** in the background on boot (`TRUSTOPS_STARTUP_SMOKE_TEST=quick|full|skip`) to verify SAIA and core routes; results log to the uvicorn console without blocking startup.

### 4. React analyst UI

The Vite + React app on **port 5173** calls the API with **`VITE_API_BASE_URL`**. Layout:

- **StatusBar** — Backend online/offline, Splunk configured/reachable, **Agents: Running…** during workflow execution, and a compact **seven-step investigation-flow timeline**.
- **AlertQueue** — static catalog; **`TO-VPN-2026-514`** selected by default.
- **InvestigationPanel** — in order:
  - **Agentic investigation** status badge (`running` / `complete` / `not run`)
  - **Splunk AI analysis** (SAIA on load: summary, key evidence, severity/actions, AI recommendation, trust calibration; source badge)
  - **Splunk AI Assistant chat** (alert-scoped Q&A)
  - **Seven agent callouts** (Evidence → Trust Calibration) with two-column Evidence/Recommendations; MITRE mapping cards; follow-up SPL with **Explain SPL**
- **DecisionForm** — four sections (details, checklist ≥2, challenge fields, submit/feedback); **automatic time-to-decision** on submit; automation bias feedback.
- **MetricsPanel** — Splunk-backed aggregates from `GET /decisions/summary`.

The UI does **not** render the raw SPL-used block, event timeline table, or aggregate investigation-result summary (data remains on the API).

### 5. Analyst action and telemetry

When an analyst submits a decision, the UI POSTs structured fields. The backend timestamps the row in UTC, records **elapsed time to decision** automatically (since investigation loaded), and sends the event to Splunk. The bundled **Splunk dashboard** charts acceptance vs modification vs rejection, averages, and time-to-decision—the measurable side of **human–AI collaboration**.

### Splunk telemetry indexes

| Index | Sourcetype | Purpose |
|-------|------------|---------|
| `trustops` | `trustops:auth` | Synthetic VPN/authentication events |
| `trustops_decisions` | `trustops:decision` | CSV-shaped analyst decision rows |
| `trustops_agent_runs` | `trustops:agent_step` | Per-agent JSON step events (`run_id`, `tools_used`, `duration_ms`, MITRE fields) |
| `trustops_agent_runs` | `trustops:analyst_chat` | Alert-scoped chat Q&A telemetry |

Create indexes with `scripts/setup_splunk_indexes.sh`.

## Human-AI Trust Calibration Layer

TrustOps extends the triage loop with research-oriented controls for **calibrated trust** in AI-augmented SOCs:

1. **Trust Calibration Notice** — surfaced on investigation load for high-severity / high-confidence scenarios (strip + level: low, moderate, high).
2. **Evidence Review Checklist** — UI gate requiring ≥2 checks; `evidence_checklist` stored as pipe-delimited tokens in Splunk.
3. **AI Challenge fields** — `supporting_evidence` and `contradicting_evidence` required before submit (commas sanitized for CSV `_raw`).
4. **Automation bias risk** — server-side score on `POST /decisions` using acceptance, trust, time-to-decision, evidence count, and confidence; returned with tier (Low / Moderate / High).
5. **Automatic time-to-decision** — elapsed seconds since investigation loaded; recorded on submit, not entered by the analyst.
6. **Post-decision feedback** — deterministic `feedback_message` and `learning_point` for analyst upskilling (not enforcement).

Splunk dashboards and `splunk/core_searches.spl` include bias, checklist coverage, and trust-vs-confidence panels. Older 13-field ingested rows still parse via column-index SPL.

## Why this shape

- **Splunk remains the system of record** for security events and analyst telemetry.
- **Splunk AI Assistant** keeps investigation assistance inside Splunk-aligned, governable workflows (REST `/predict` primary path).
- **Optional MCP** allows IDE and backend extension without requiring MCP for the core demo.
- **Auto-run agent workflow** reduces analyst friction while preserving transparency via inline agent sections and status-bar timeline.
- **Deterministic fallback** guarantees a judge-ready demo even when SAIA is misconfigured.
- **Transparency** (source badges, `tools_used` per agent step, API-returned SPL) supports audit and training.

## Future extensions

- **Expand MCP tool coverage** (knowledge objects, lookups, enrichment) for richer agentic playbooks.
- **More alert scenarios** beyond VPN/geo with the same decision schema and additional MITRE technique chains.
- **Generate SPL in the UI** — wire `POST /saia/generate` into the investigation panel.
- **Richer agent-run dashboards** on `trustops_agent_runs`.
- **SOAR-style response recommendations** (human-approved) with audit trails.
- **Research exports** of decision telemetry for trust, workload, and model-iteration studies.
