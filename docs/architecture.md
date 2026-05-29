# TrustOps architecture

This document complements the Mermaid diagram in the repository root: [`architecture.mmd`](../architecture.mmd). Open that file in GitHub, VS Code (Mermaid preview), or any Mermaid-compatible viewer to see the visual flow.

## Diagram walkthrough (hackathon checklist)

1. **Synthetic security data** is loaded into Splunk **`index=trustops`** (authentication-style events for the demo scenario).
2. **Splunk Enterprise** stores those events and exposes **Splunk AI Assistant** and the **Splunk MCP Server** for agentic investigation support.
3. The **FastAPI backend** queries Splunk via the SDK and orchestrates investigation through **Splunk AI Assistant** (primary) with a **deterministic local fallback** when cloud or MCP paths are unavailable.
4. **Splunk MCP** acts as the bridge between TrustOps agent workflows and Splunk capabilities—searches, knowledge objects, and optional tool-calling for deeper retrieval.
5. The **React analyst UI** shows the **alert queue**, **investigation** (narrative, evidence, SPL, SAIA explain/generate), **decision form**, and **metrics**.
6. The **analyst submits a decision** through the UI (`POST /decisions`).
7. **FastAPI writes decision telemetry** to Splunk **`index=trustops_decisions`**.
8. A **Splunk dashboard** (bundled XML in the repo) visualizes **human–AI decision metrics** alongside security data.

## Plain-language overview

TrustOps is a **human-in-the-loop agentic triage loop** around Splunk: authentication events live in Splunk, the backend assembles evidence and **AI-assisted investigation context**, analysts record **how they used AI guidance**, and those decisions are written back to Splunk for **dashboards and research**.

### 1. Data in Splunk

- **Authentication-style events** are stored in **`index=trustops`** with **`sourcetype=trustops:auth`**. In the hackathon repo, rows come from generated CSV and align on canonical demo alert **`TO-VPN-2026-514`** (jsmith VPN/SAML failures, then successful Romania login).
- **Analyst decision telemetry** is stored in **`index=trustops_decisions`** with **`sourcetype=trustops:decision`**. Each event is a single CSV-shaped line so Splunk panels can parse it consistently.

### 2. Splunk AI Assistant and Splunk MCP

- **Splunk AI Assistant (SAIA)** powers natural-language **SPL explain/generate**, investigation narrative support, and contextual recommendations. TrustOps calls SAIA through the same **v1 `/predict`** REST path the Search UI uses on Enterprise 10.2.x (reliable on CMP-connected stacks).
- **Splunk MCP Server** is the **capability bridge** for agentic workflows: the TrustOps backend (and IDE agents such as Cursor) can invoke MCP tools to run searches, inspect indexes, and extend investigation beyond static API routes. MCP complements SAIA—searches and platform operations through MCP; narrative and SPL assistance through SAIA.

### 3. FastAPI backend — dual investigation modes

The backend sits on **port 8001** (by default) so it does not collide with Splunk Web on **8000**. It supports **two investigation modes**:

| Mode | Role |
|------|------|
| **Splunk AI Assistant / MCP-powered** | Primary path for agentic investigation: SAIA for explain/generate and context; MCP for Splunk-native retrieval and tool use when configured. |
| **Deterministic local fallback** | Rule-based `ai_agent.py` when SAIA is unreachable or for **offline/demo reliability**—repeatable narratives without cloud dependency. |

Shared responsibilities across both modes:

- Serve the **alert catalog** (from `data/sample_alerts.json`) for the UI queue.
- Run **Splunk searches** (SDK) for auth events scoped to an `alert_id`, returning the **exact SPL** used.
- Produce **investigation summaries**, evidence bullets, severity, and recommended actions.
- Run **agent orchestrator** (`backend/agents/`) via **`GET`/`POST /alerts/{id}/agent-run`** (seven steps including **MITRE ATT&CK Mapping Agent**); log each step to **`index=trustops_agent_runs`** (`trustops:agent_step` JSON events, including optional `mitre_techniques` / `mitre_mappings`); query via **`/agent-runs/{run_id}/telemetry`** and **`/agent-runs/summary`**.
- Optional **MITRE ATT&CK enrichment** via `mitreattack-python` and local `data/enterprise-attack.json` (`backend/attack_enrichment.py`); **local fallback mappings** when package or STIX file is unavailable.
- Expose **`POST /saia/explain`** and **`POST /saia/generate`** for the investigation panel.
- Accept **`POST /decisions`** and write rows to **`trustops_decisions`** via Splunk’s HTTP receiver (including agentic panel view flags).

### 4. React analyst UI

The Vite + React app on **port 5173** calls the API with **`VITE_API_BASE_URL`**. It shows:

- **Status** (API + Splunk + MCP configuration hints),
- **Alert queue**,
- **Investigation** (summary, evidence, SPL, event table, **Explain SPL** / **Generate SPL** via SAIA),
- **Decision form** (human verdict + trust/confidence fields),
- **Metrics** aggregated from Splunk decision events.

### 5. Analyst action and telemetry

When an analyst submits a decision, the UI POSTs structured fields. The backend timestamps the row in UTC and sends it to Splunk. The bundled **Splunk dashboard** charts acceptance vs modification vs rejection, averages, and time-to-decision—the measurable side of **human–AI collaboration**.

## Human-AI Trust Calibration Layer

TrustOps extends the triage loop with research-oriented controls for **calibrated trust** in AI-augmented SOCs:

1. **Trust Calibration Notice** — surfaced on investigation load for high-severity / high-confidence scenarios (banner + level: low, moderate, high).
2. **Evidence Review Checklist** — UI gate requiring ≥2 checks; `evidence_checklist` stored as pipe-delimited tokens in Splunk.
3. **AI Challenge fields** — `supporting_evidence` and `contradicting_evidence` required before submit (commas sanitized for CSV `_raw`).
4. **Automation bias risk** — server-side score on `POST /decisions` using acceptance, trust, time-to-decision, evidence count, and confidence; returned with tier (Low / Moderate / High).
5. **Post-decision feedback** — deterministic `feedback_message` and `learning_point` for analyst upskilling (not enforcement).

Splunk dashboards and `splunk/core_searches.spl` include bias, checklist coverage, and trust-vs-confidence panels. Older 13-field ingested rows still parse via column-index SPL.

## Why this shape

- **Splunk remains the system of record** for security events and analyst telemetry.
- **Splunk MCP** standardizes how agents and the backend reach Splunk capabilities without bespoke integrations per tool.
- **Splunk AI Assistant** keeps investigation assistance inside Splunk-aligned, governable workflows.
- **Deterministic fallback** guarantees a judge-ready demo even when cloud SAIA or MCP tokens are misconfigured.
- **Transparency** (returned SPL, explicit source badges for SAIA vs local fallback) supports audit and training.

## Future extensions

- **Expand MCP tool coverage** (knowledge objects, lookups, enrichment) for richer agentic playbooks.
- **More alert scenarios** beyond VPN/geo with the same decision schema.
- **SOP mapping** — tie recommendations to internal procedure IDs and capture compliance signals.
- **Expanded MITRE coverage** beyond VPN/SAML (additional scenarios and technique chains).
- **SOAR-style response recommendations** (human-approved) with audit trails.
- **Research exports** of decision telemetry for trust, workload, and model-iteration studies.
