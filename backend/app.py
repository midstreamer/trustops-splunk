"""
TrustOps FastAPI backend — Splunk-backed triage API with deterministic local "AI".
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager
from functools import lru_cache
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from agent_run_logger import log_agent_run_to_splunk
from agent_telemetry import build_agent_runs_summary, rows_to_telemetry_steps
from agents.contradictory_evidence_agent import resolve_contradictory_evidence
from agentic_investigation import build_follow_up_queries
from alert_chat import handle_alert_chat
from alert_chat_logger import log_analyst_chat_to_splunk
from agents.mitre_attack_agent import resolve_mitre_attack_mappings
from agents.orchestrator import run_agentic_investigation
from saia_investigation import resolve_investigation
from config import Settings, get_settings
from decision_duplicate_guard import register_client_decision_id
from decision_logger import log_decision_to_splunk
from models import (
    AlertChatRequest,
    AlertChatResponse,
    AlertModel,
    AuthEventModel,
    AuthEventsResponse,
    DecisionCreate,
    DecisionRowModel,
    DecisionSubmitResponse,
    DecisionSummaryResponse,
    DecisionSummaryRow,
    DecisionsForAlertResponse,
    HealthResponse,
    AgentPlanResponse,
    AgentRunResult,
    AgentRunTelemetryResponse,
    AgentRunsSummaryResponse,
    FollowUpQueriesResponse,
    InvestigationResponse,
    SaiaExplainRequest,
    SaiaGenerateRequest,
    SaiaSplResponse,
)
from saia_service import explain_spl, generate_spl
from smoke_test import (
    DEFAULT_BASE_URL,
    format_report,
    run_startup_smoke,
    startup_smoke_mode,
    wait_for_health,
)
from splunk_client import (
    SplunkClient,
    spl_agent_steps_for_run_spl,
    spl_agent_steps_recent_spl,
    spl_auth_events_spl,
    spl_decisions_for_alert_spl,
    spl_decisions_summary_spl,
    validate_alert_id_for_spl,
    validate_run_id_for_spl,
)
from trust_calibration import trust_calibration_for_investigation

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parent.parent
SAMPLE_ALERTS_PATH = REPO_ROOT / "data" / "sample_alerts.json"


@lru_cache
def load_alerts() -> tuple[AlertModel, ...]:
    if not SAMPLE_ALERTS_PATH.is_file():
        raise RuntimeError(f"Missing sample alerts file: {SAMPLE_ALERTS_PATH}")
    raw = json.loads(SAMPLE_ALERTS_PATH.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise RuntimeError("sample_alerts.json must be a JSON array")
    return tuple(AlertModel.model_validate(a) for a in raw)


def require_alert(alert_id: str) -> AlertModel:
    aid = require_safe_alert_id(alert_id)
    for a in load_alerts():
        if a.alert_id == aid:
            return a
    raise HTTPException(status_code=404, detail=f"Unknown alert_id: {aid}")


def require_safe_alert_id(alert_id: str) -> str:
    try:
        return validate_alert_id_for_spl(alert_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid alert_id") from exc


def normalize_time_field(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        from datetime import datetime, timezone

        return datetime.fromtimestamp(float(value), tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    s = str(value).strip()
    return s or None


def normalize_auth_event(row: dict[str, Any]) -> AuthEventModel:
    data = dict(row)
    if "_time" in data:
        data["_time"] = normalize_time_field(data.get("_time"))
    return AuthEventModel.model_validate(data)


def get_splunk_client() -> SplunkClient:
    return SplunkClient(get_settings())


async def _run_startup_smoke_test(app: FastAPI) -> None:
    del app
    mode = startup_smoke_mode()
    if mode is None:
        return
    base_url = os.getenv("TRUSTOPS_API_BASE_URL", DEFAULT_BASE_URL)
    if not await asyncio.to_thread(wait_for_health, base_url, attempts=60, interval=0.5):
        logger.warning("Startup smoke test skipped: API not reachable at %s", base_url)
        return
    try:
        report = await asyncio.to_thread(run_startup_smoke)
        output = format_report(report)
        if report.passed:
            logger.info("Startup smoke test passed (%s mode):\n%s", mode, output)
        else:
            logger.warning("Startup smoke test failed (%s mode):\n%s", mode, output)
    except Exception:  # noqa: BLE001
        logger.exception("Startup smoke test crashed")


@asynccontextmanager
async def lifespan(app: FastAPI):
    mode = startup_smoke_mode()
    if mode is not None:
        asyncio.create_task(_run_startup_smoke_test(app))
    yield


app = FastAPI(
    title="TrustOps API",
    description="Hackathon backend: Splunk searches + deterministic investigation summaries + decision logging.",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse)
def health(settings: Settings = Depends(get_settings)) -> HealthResponse:
    configured = settings.splunk_credentials_configured()
    reachable: bool | None = None
    detail: str | None = None
    status: str = "ok"

    if not configured:
        detail = "Set SPLUNK_USER and SPLUNK_PASSWORD to enable Splunk-backed routes."
        status = "degraded"
        reachable = False
    else:
        client = SplunkClient(settings)
        try:
            reachable = client.ping()
        except Exception as exc:  # noqa: BLE001
            logger.exception("Health Splunk probe failed")
            reachable = False
            detail = f"Splunk unreachable: {exc}"
            status = "degraded"

    mcp_detail: str | None = None
    if not settings.splunk_mcp_configured():
        mcp_detail = "Set SPLUNK_MCP_TOKEN or SPLUNK_MCP_TOKEN_FILE for SAIA SPL tools."
    elif status == "ok":
        mcp_detail = "MCP token configured (SAIA explain/generate)."

    return HealthResponse(
        status=status,
        splunk_configured=configured,
        splunk_reachable=reachable,
        detail=detail,
        mcp_configured=settings.splunk_mcp_configured(),
        mcp_detail=mcp_detail,
    )


@app.get("/alerts", response_model=list[AlertModel])
def list_alerts() -> list[AlertModel]:
    return list(load_alerts())


@app.get("/alerts/{alert_id}", response_model=AlertModel)
def get_alert(alert_id: str) -> AlertModel:
    return require_alert(alert_id)


@app.get("/alerts/{alert_id}/events", response_model=AuthEventsResponse)
def get_alert_events(
    alert_id: str,
    settings: Settings = Depends(get_settings),
    client: SplunkClient = Depends(get_splunk_client),
) -> AuthEventsResponse:
    aid = require_safe_alert_id(alert_id)
    require_alert(aid)  # 404 if unknown catalog id
    if not settings.splunk_credentials_configured():
        raise HTTPException(status_code=503, detail="Splunk credentials are not configured.")

    spl = spl_auth_events_spl(aid, settings.splunk_auth_index)
    try:
        rows = client.run_oneshot_json(spl)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Splunk search failed for /events")
        raise HTTPException(status_code=503, detail=f"Splunk search failed: {exc}") from exc

    events = [normalize_auth_event(r) for r in rows]
    return AuthEventsResponse(alert_id=aid, spl_query_used=spl, events=events)


@app.get("/alerts/{alert_id}/investigation", response_model=InvestigationResponse)
def get_investigation(
    alert_id: str,
    settings: Settings = Depends(get_settings),
    client: SplunkClient = Depends(get_splunk_client),
) -> InvestigationResponse:
    alert = require_alert(alert_id)
    aid = alert.alert_id

    if not settings.splunk_credentials_configured():
        raise HTTPException(status_code=503, detail="Splunk credentials are not configured.")

    spl = spl_auth_events_spl(aid, settings.splunk_auth_index)
    try:
        rows = client.run_oneshot_json(spl)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Splunk search failed for /investigation")
        raise HTTPException(status_code=503, detail=f"Splunk search failed: {exc}") from exc

    events = [normalize_auth_event(r) for r in rows]
    event_dicts = [e.model_dump() for e in events]
    ai, investigation_source, investigation_source_detail = resolve_investigation(
        alert.model_dump(),
        event_dicts,
        settings,
    )
    notice, cal_level = trust_calibration_for_investigation(
        alert.alert_id,
        alert.severity,
        ai.recommended_severity,
    )

    contradictory = resolve_contradictory_evidence(
        alert.model_dump(),
        event_dicts,
        settings,
    )
    follow_ups = build_follow_up_queries(alert.model_dump(), settings.splunk_auth_index)
    mitre_mappings, mitre_rationale = resolve_mitre_attack_mappings(
        alert.model_dump(),
        event_dicts,
        settings,
    )

    return InvestigationResponse(
        alert=alert,
        events=events,
        investigation_summary=ai.investigation_summary,
        key_evidence=ai.key_evidence,
        ai_recommendation=ai.ai_recommendation,
        recommended_severity=ai.recommended_severity,
        recommended_actions=ai.recommended_actions,
        confidence_rationale=ai.confidence_rationale,
        spl_query_used=spl,
        investigation_source=investigation_source,
        investigation_source_detail=investigation_source_detail,
        trust_calibration_notice=notice,
        trust_calibration_level=cal_level,
        follow_up_queries=follow_ups,
        contradictory_evidence=contradictory,
        mitre_attack_mappings=mitre_mappings or None,
        mitre_attack_rationale=mitre_rationale or None,
    )


def _run_agent_workflow(
    alert_id: str,
    settings: Settings,
    client: SplunkClient,
) -> AgentRunResult:
    if not settings.splunk_credentials_configured():
        raise HTTPException(status_code=503, detail="Splunk credentials are not configured.")
    alert = require_alert(alert_id)
    try:
        run = run_agentic_investigation(
            alert.model_dump(),
            settings=settings,
            splunk_client=client,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Agentic investigation workflow failed")
        raise HTTPException(status_code=503, detail=f"Agent workflow failed: {exc}") from exc

    logged, warning = log_agent_run_to_splunk(client, run)
    if warning:
        logger.warning("Agent run telemetry: %s", warning)
    return run.model_copy(
        update={
            "telemetry_logged": logged > 0,
            "telemetry_steps_logged": logged,
            "telemetry_warning": warning,
        }
    )


@app.get("/alerts/{alert_id}/agent-run", response_model=AgentRunResult)
def get_agent_run(
    alert_id: str,
    settings: Settings = Depends(get_settings),
    client: SplunkClient = Depends(get_splunk_client),
) -> AgentRunResult:
    """Execute the sequential tool-backed agent workflow and return execution trace."""
    return _run_agent_workflow(alert_id, settings, client)


@app.post("/alerts/{alert_id}/agent-run", response_model=AgentRunResult)
def post_agent_run(
    alert_id: str,
    settings: Settings = Depends(get_settings),
    client: SplunkClient = Depends(get_splunk_client),
) -> AgentRunResult:
    """Start a new agentic investigation run (same orchestration as GET)."""
    return _run_agent_workflow(alert_id, settings, client)


@app.get("/alerts/{alert_id}/agent-plan", response_model=AgentRunResult)
def get_agent_plan(
    alert_id: str,
    settings: Settings = Depends(get_settings),
    client: SplunkClient = Depends(get_splunk_client),
) -> AgentRunResult:
    """Run orchestrated workflow (replaces static template plan)."""
    return _run_agent_workflow(alert_id, settings, client)


@app.get("/agent-runs/summary", response_model=AgentRunsSummaryResponse)
def agent_runs_summary(
    settings: Settings = Depends(get_settings),
    client: SplunkClient = Depends(get_splunk_client),
) -> AgentRunsSummaryResponse:
    if not settings.splunk_credentials_configured():
        raise HTTPException(status_code=503, detail="Splunk credentials are not configured.")
    spl = spl_agent_steps_recent_spl(settings.splunk_agent_run_index)
    try:
        rows = client.run_oneshot_json(spl)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Splunk agent-runs summary search failed")
        raise HTTPException(status_code=503, detail=f"Splunk search failed: {exc}") from exc
    return build_agent_runs_summary(rows)


@app.get("/agent-runs/{run_id}/telemetry", response_model=AgentRunTelemetryResponse)
def agent_run_telemetry(
    run_id: str,
    settings: Settings = Depends(get_settings),
    client: SplunkClient = Depends(get_splunk_client),
) -> AgentRunTelemetryResponse:
    if not settings.splunk_credentials_configured():
        raise HTTPException(status_code=503, detail="Splunk credentials are not configured.")
    try:
        rid = validate_run_id_for_spl(run_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid run_id") from exc
    spl = spl_agent_steps_for_run_spl(rid, settings.splunk_agent_run_index)
    try:
        rows = client.run_oneshot_json(spl)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Splunk agent-run telemetry search failed")
        raise HTTPException(status_code=503, detail=f"Splunk search failed: {exc}") from exc
    return AgentRunTelemetryResponse(
        run_id=rid,
        spl_query_used=spl,
        steps=rows_to_telemetry_steps(rows),
    )


@app.get("/alerts/{alert_id}/follow-up-queries", response_model=FollowUpQueriesResponse)
def get_follow_up_queries(
    alert_id: str,
    settings: Settings = Depends(get_settings),
) -> FollowUpQueriesResponse:
    alert = require_alert(alert_id)
    queries = build_follow_up_queries(alert.model_dump(), settings.splunk_auth_index)
    return FollowUpQueriesResponse(alert_id=alert.alert_id, queries=queries)


@app.post("/alerts/{alert_id}/chat", response_model=AlertChatResponse)
def post_alert_chat(
    alert_id: str,
    body: AlertChatRequest,
    settings: Settings = Depends(get_settings),
    client: SplunkClient = Depends(get_splunk_client),
) -> AlertChatResponse:
    """Alert-scoped analyst chat grounded in Splunk evidence and investigation context."""
    if not settings.splunk_credentials_configured():
        raise HTTPException(status_code=503, detail="Splunk credentials are not configured.")

    alert = require_alert(alert_id)
    aid = alert.alert_id
    spl = spl_auth_events_spl(aid, settings.splunk_auth_index)
    try:
        rows = client.run_oneshot_json(spl)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Splunk search failed for /chat")
        raise HTTPException(status_code=503, detail=f"Splunk search failed: {exc}") from exc

    events = [normalize_auth_event(r) for r in rows]
    ai_preview, _, _ = resolve_investigation(
        alert.model_dump(),
        [e.model_dump() for e in events],
        settings,
    )
    trust_notice, _ = trust_calibration_for_investigation(
        alert.alert_id,
        alert.severity,
        ai_preview.recommended_severity,
    )

    response = handle_alert_chat(
        alert=alert.model_dump(),
        events=[e.model_dump() for e in events],
        message=body.message.strip(),
        conversation_id=body.conversation_id,
        include_context=body.include_context,
        settings=settings,
        trust_notice=trust_notice,
    )

    log_analyst_chat_to_splunk(
        client,
        conversation_id=response.conversation_id,
        alert_id=aid,
        question=body.message.strip(),
        response=response,
    )

    return response


@app.post("/decisions", response_model=DecisionSubmitResponse)
def post_decision(
    body: DecisionCreate,
    client: SplunkClient = Depends(get_splunk_client),
    settings: Settings = Depends(get_settings),
) -> DecisionSubmitResponse:
    if not settings.splunk_credentials_configured():
        raise HTTPException(status_code=503, detail="Splunk credentials are not configured.")
    if not register_client_decision_id(body.client_decision_id):
        raise HTTPException(
            status_code=409,
            detail="This decision was already submitted.",
        )
    try:
        logged = log_decision_to_splunk(client, body)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to log decision to Splunk")
        raise HTTPException(status_code=503, detail=f"Splunk receiver failed: {exc}") from exc
    return DecisionSubmitResponse(
        success=True,
        decision=logged,
        automation_bias_risk_score=logged.automation_bias_risk_score,
        automation_bias_risk_level=logged.automation_bias_risk_level,
        feedback_message=logged.feedback_message,
        learning_point=logged.learning_point,
    )


@app.get("/decisions/summary", response_model=DecisionSummaryResponse)
def decisions_summary(
    settings: Settings = Depends(get_settings),
    client: SplunkClient = Depends(get_splunk_client),
) -> DecisionSummaryResponse:
    if not settings.splunk_credentials_configured():
        raise HTTPException(status_code=503, detail="Splunk credentials are not configured.")

    spl = spl_decisions_summary_spl(settings.splunk_decision_index)
    try:
        rows = client.run_oneshot_json(spl)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Splunk summary search failed")
        raise HTTPException(status_code=503, detail=f"Splunk search failed: {exc}") from exc

    out: list[DecisionSummaryRow] = []
    for r in rows:
        try:
            out.append(
                DecisionSummaryRow(
                    ai_recommendation_status=str(r.get("ai_recommendation_status", "")),
                    decision_count=int(float(r.get("decision_count", 0))),
                    avg_confidence=_maybe_float(r.get("avg_confidence")),
                    avg_trust=_maybe_float(r.get("avg_trust")),
                    avg_time_to_decision=_maybe_float(r.get("avg_time_to_decision")),
                    avg_automation_bias_risk_score=_maybe_float(
                        r.get("avg_automation_bias_risk_score")
                    ),
                )
            )
        except (TypeError, ValueError) as exc:
            logger.warning("Skipping malformed summary row: %s (%s)", r, exc)
    return DecisionSummaryResponse(rows=out)


def _maybe_float(v: Any) -> float | None:
    if v in (None, "", "null"):
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


@app.post("/saia/explain", response_model=SaiaSplResponse)
def saia_explain(
    body: SaiaExplainRequest,
    settings: Settings = Depends(get_settings),
) -> SaiaSplResponse:
    try:
        text, source = explain_spl(settings, body.spl, body.additional_context)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return SaiaSplResponse(text=text, source=source)


@app.post("/saia/generate", response_model=SaiaSplResponse)
def saia_generate(
    body: SaiaGenerateRequest,
    settings: Settings = Depends(get_settings),
) -> SaiaSplResponse:
    alert_id: str | None = None
    if body.alert_id:
        try:
            alert_id = validate_alert_id_for_spl(body.alert_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid alert_id") from exc

    try:
        text, source, generated = generate_spl(
            settings,
            body.prompt,
            alert_id=alert_id,
            spl_only=body.spl_only,
            additional_context=body.additional_context,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return SaiaSplResponse(text=text, source=source, generated_spl=generated)


@app.get("/decisions/{alert_id}", response_model=DecisionsForAlertResponse)
def decisions_for_alert(
    alert_id: str,
    settings: Settings = Depends(get_settings),
    client: SplunkClient = Depends(get_splunk_client),
) -> DecisionsForAlertResponse:
    # Do not require the alert to exist in sample_alerts.json — Splunk may hold telemetry
    # for IDs not shipped in the static catalog.
    aid = require_safe_alert_id(alert_id)

    if not settings.splunk_credentials_configured():
        raise HTTPException(status_code=503, detail="Splunk credentials are not configured.")

    spl = spl_decisions_for_alert_spl(aid, settings.splunk_decision_index)
    try:
        rows = client.run_oneshot_json(spl)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Splunk decisions search failed")
        raise HTTPException(status_code=503, detail=f"Splunk search failed: {exc}") from exc

    decisions = [DecisionRowModel.model_validate(r) for r in rows]
    return DecisionsForAlertResponse(alert_id=aid, spl_query_used=spl, decisions=decisions)
