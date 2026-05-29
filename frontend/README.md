# TrustOps — React analyst UI (Phase 3)

Vite + React console for reviewing Splunk-backed investigations and submitting analyst decisions to the **Phase 2** FastAPI API.

## Prerequisites

- Node.js **18+** (20 LTS recommended).
- Backend running with CORS allowed for this dev server (default `http://localhost:5173`).

## Environment

| Variable | Default | Description |
|----------|---------|-------------|
| `VITE_API_BASE_URL` | `http://localhost:8001` | TrustOps FastAPI base URL (no trailing slash required). |

Create `frontend/.env.local`:

```bash
VITE_API_BASE_URL=http://localhost:8001
```

## Install and run

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173** (Vite default).

Production build:

```bash
npm run build
npm run preview
```

## Expected backend

- **Health:** `GET {VITE_API_BASE_URL}/health`
- **Alerts / investigation / decisions:** see repo root `README.md` Phase 2 table.

If the backend is down, the **Status bar** shows **Backend: Offline** and queue/metrics surfaces friendly errors.

## Human-AI Trust Calibration (UI)

- **Investigation** — Compact **Trust Calibration** strip under the AI recommendation; severity/actions in a collapsible block; SPL and timeline in fixed regions.
- **Analyst decision** — Four sections: **Decision Details**, **Evidence Review Checklist**, **Challenge the AI Recommendation**, **Submit and Feedback**.
- **Submit readiness** — Shows **Ready to submit** when ≥2 checklist items, supporting/contradicting evidence, and analyst decision are filled; otherwise prompts you to complete review and challenge fields.
- **Post-decision feedback** — Compact panel under submit (bias badge + learning point).
- **Duplicate submit prevention** — After a successful submit, the form locks and the button reads **Decision submitted to Splunk**; use **Start new decision** to submit again for the same alert (new `client_decision_id`).
- **MITRE ATT&CK Mapping** — Compact panel in **Investigation** (tactics, techniques, rationale, validation badges); appears before running the full agent trace when mappings exist on `/investigation`.
- **Ask Splunk AI** — Collapsible alert-scoped chat below follow-up SPL; suggested prompt chips, last 5 exchanges, source badge (SAIA vs local fallback).
- **Agentic investigation workflow** — **Run agentic investigation** executes the backend orchestrator (**7 steps**, including MITRE ATT&CK) and shows tool-backed step traces (Splunk search, rules, SAIA explain when available). MITRE agent cards include an ATT&CK mapping table and technique chips.
- **Recommended Follow-Up SPL** — Copy or **Explain SPL** on suggested pivots (not executed from the UI).
- **Challenge the AI** — Contradictory Evidence Agent panel (benign explanations, validation steps, evidence gaps) before the decision form.
- **Decision metrics** — **Avg bias risk** column when the backend returns extended summary fields.

## Demo flow

1. Start Splunk (Phase 1 data ingested) and the API: `uvicorn app:app --reload --host 0.0.0.0 --port 8001` from `backend/`.
2. Start this UI: `npm run dev` from `frontend/`.
3. Confirm **Backend: Online** and **Splunk: Reachable** in the status bar.
4. **TO-VPN-2026-514** is auto-selected; review summary, AI recommendation + Trust Calibration strip, SPL block, and event timeline.
5. In **Analyst decision**, fill **Decision Details** (including analyst decision text), check **≥2** evidence items, and complete both challenge text areas until **Ready to submit** appears.
6. **Submit decision to Splunk** → feedback in **Submit and Feedback**.
7. **Decision metrics** refresh automatically.
