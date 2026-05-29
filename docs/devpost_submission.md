# TrustOps for Splunk — Devpost / hackathon submission

## Project name

**TrustOps for Splunk**

## Tagline

**Human-in-the-loop agentic triage for security operations.**

---

## Inspiration

Security operations centers live under constant pressure: high alert volume, overlapping tools, and limited time to validate whether activity is malicious or benign. Analysts are asked to move faster while still being accountable for decisions.

Generative AI can summarize evidence and suggest next steps, but organizations also need **visibility into how analysts actually use AI**: when they accept guidance, when they adapt it to context, and when they override it. Without that telemetry, teams cannot measure trust, workload impact, or the quality of human–AI collaboration.

TrustOps was built to bridge that gap: **Splunk as the evidence store**, **Splunk AI Assistant and MCP for agentic investigation**, **a guided triage UI**, and **structured decision logging** so human–AI interactions become measurable, not invisible.

---

## What it does

TrustOps helps an analyst work a suspicious alert end-to-end:

1. **Alert queue** — Prioritized or curated alerts (demo data includes the canonical VPN/geo scenario **`TO-VPN-2026-514`**).
2. **Investigation view** — Pulls related authentication events from Splunk, shows an **AI-assisted investigation narrative**, **MITRE ATT&CK mapping** (e.g. **T1078 Valid Accounts**, **T1110 Brute Force** for the VPN/SAML demo), **key evidence**, **recommended severity and actions**, the **exact SPL** used, and **Splunk AI Assistant** actions to **explain** or **generate** SPL in context.
3. **Analyst decision form** — Captures who decided what, how they rated **confidence** and **trust**, whether they **accepted, modified, or rejected** the AI-style recommendation, time-to-decision, and free-text notes.
4. **Metrics** — Aggregates decision telemetry so teams can see distributions across recommendation outcomes.
5. **Splunk dashboard** — Visualizes human–AI decision patterns alongside the underlying security data.

In short: **investigate in Splunk with AI and MCP, decide with structure, measure in Splunk.**

---

## How we built it

- **Splunk Enterprise** indexes synthetic VPN-style authentication logs (**`trustops`**) and analyst decision rows (**`trustops_decisions`**), plus a **Splunk XML dashboard** for demo charts.
- **Splunk AI Assistant (cloud-connected)** for SPL explain/generate and investigation assistance via Splunk REST **`/predict`** (same path as Search UI on Enterprise 10.2.x).
- **Splunk MCP Server** so agents and the backend can reach Splunk searches, indexes, and platform tools through a standard MCP bridge.
- **Synthetic data + ingest scripts** seed repeatable hackathon scenarios (failed logins, success from an unfamiliar geography, canonical alert id **`TO-VPN-2026-514`**).
- **FastAPI** exposes REST endpoints for health, alerts, Splunk-backed investigations, **SAIA explain/generate**, decision summaries, and decision submission.
- **Splunk SDK (`splunklib`)** runs searches; **HTTP receiver** posts new decision events back to Splunk.
- **React + Vite** front end: status bar, investigation panel with SAIA buttons, decision form, and metrics.
- **Deterministic `ai_agent` fallback** — local rules for **reliable offline demos** when SAIA or MCP is unavailable; the UI labels whether content came from **Splunk AI Assistant** or **local fallback**.

---

## Human-AI Trust Calibration Layer

Beyond agentic investigation, TrustOps implements a **trust calibration layer** informed by human–AI collaboration research (automation bias, calibrated reliance, analyst upskilling):

- Analysts see a **Trust Calibration Notice** when AI confidence is high—prompting independent evidence review before acceptance.
- Submission requires an **Evidence Review Checklist** and explicit **supporting / contradicting** rationale for the AI recommendation.
- Each decision computes an **automation bias risk score** and returns **post-decision feedback** plus a **learning point** (feedback, not blocking).
- Telemetry lands in Splunk for dashboarding: bias by analyst, checklist coverage, trust vs confidence, and decisions missing challenge text.

This makes human–AI collaboration **measurable and trainable**, not just narrated.

## Agentic SOC Workflow

TrustOps uses a **backend orchestrator** with **tool-backed specialized roles** (not five fully autonomous agents):

- **Evidence Agent** executes a real Splunk search and summarizes failures, successes, geographies, and risk scores.
- **Triage Agent** applies transparent severity rules to those counts.
- **SPL Agent** generates follow-up SPL and attempts **Splunk AI Assistant explain** on the first query (local fallback when SAIA is unavailable).
- **Contradictory Evidence Agent** and **SOP Agent** produce challenge hypotheses and response checklists.
- **Trust Calibration Agent** delivers pre-decision human–AI oversight guidance.

The UI **Run agentic investigation** action calls `POST /alerts/{id}/agent-run` and renders the **execution trace** (tools used, evidence bullets, timestamps). **Agent-step telemetry** is written to Splunk (`trustops_agent_runs`) so the workflow itself is auditable—step duration, tools, and errors can be measured in dashboards. **Recommended Follow-Up SPL** and **Challenge the AI** complement the workflow. **Ask Splunk AI** provides an alert-scoped chat so analysts can interrogate the AI recommendation, request follow-up SPL, review benign explanations, and confirm MITRE/SOP guidance before submitting a decision. Deterministic/local modes remain **fallback mechanisms** for demo reliability.

## How AI is used

TrustOps integrates **Splunk AI Assistant** and **Splunk MCP** into agentic investigation workflows:

- **Splunk AI Assistant** helps analysts **explain** existing SPL, **generate** new queries from natural language, and enrich investigation context—surfaced in the React panel and backed by Splunk’s SAIA REST APIs.
- **Splunk MCP Server** is the **bridge** between TrustOps (and IDE agents) and Splunk: run searches, inspect data, and extend playbooks with tool-calling instead of one-off custom integrations.
- Together, SAIA and MCP support **context generation**, **SPL transparency**, and **recommendation development** while the analyst stays in control.

For **reliability**, the backend also ships a **deterministic local fallback** (`ai_agent.py`): rule-based summaries that mirror the canonical **`TO-VPN-2026-514`** story without depending on cloud tokens. Judges always get a coherent narrative; production teams still get real SAIA/MCP when configured.

TrustOps deliberately separates **machine assistance** from **analyst verdict** so adoption, trust, and override behavior stay measurable in **`trustops_decisions`**.

---

## Challenges

- **Splunk data shaping** — CSV-style `_raw` events are easy to demo but require careful field extraction (`rex` or props) so the UI and API stay aligned.
- **SAIA API paths** — v2 oneshot/MCP endpoints can return HTTP 400 on some CMP stacks; we aligned TrustOps with the **v1 `/predict`** flow Search UI uses.
- **Human oversight** — The UI must show what is **Splunk AI Assistant** vs **local fallback**, with **SPL transparency** for skeptical analysts.
- **Useful telemetry** — Fields that are lightweight for analysts yet meaningful for metrics (status, trust, confidence, time-to-decision, evidence counts).

---

## Accomplishments

- **End-to-end Splunk integration**: search auth evidence by `alert_id`, return SPL with results, write analyst decisions back to an index.
- **Splunk AI Assistant** explain/generate in the investigation panel with source badges (SAIA vs fallback).
- **Splunk MCP** documented and wired for agentic Splunk access (Cursor and backend configuration).
- **Working analyst UI** with health, investigation, decision capture, and summary metrics.
- **Enterprise-ready MITRE ATT&CK mapping** — Splunk-grounded **T1078** / **T1110** alignment for detection engineering, reporting, and response playbooks.
- **Dual-mode investigation**: agentic SAIA/MCP primary path plus deterministic fallback for demo reliability.
- **Human–AI metrics path**: decisions land in Splunk where dashboards and research queries can consume them.

---

## What we learned

The future of **agentic security operations** is not about replacing analysts. It is about **compressing time-to-context**, **standardizing quality**, and **measuring how humans and models collaborate** under real operational constraints. Splunk MCP and Splunk AI Assistant belong in that loop—but teams still need **fallbacks** and **telemetry** to iterate safely.

---

## What’s next

- **Expand MCP tool coverage** across searches, lookups, knowledge objects, and enrichment for deeper agentic playbooks.
- **More alert scenarios** beyond VPN/geo (cloud identity, endpoint, email) with the shared decision schema.
- **SOP mapping** — tie recommendations to internal procedure IDs and capture compliance signals.
- **Expanded MITRE coverage** across additional alert scenarios and technique chains.
- **SOAR-style response recommendations** (still human-approved) with audit trails.
- **Research use** — export decision telemetry for studies on trust, workload, decision quality, and model iteration over time.

---

*TrustOps for Splunk — built for hackathon demonstration; harden auth, secrets, and production Splunk practices before real deployment.*
