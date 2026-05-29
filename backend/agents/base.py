"""Shared types and helpers for TrustOps agent workflow steps."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable

from config import Settings
from models import AgentStepResult
from splunk_client import SplunkClient


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def safe_int(value: Any) -> int | None:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


@dataclass
class InvestigationContext:
    """Mutable shared state passed through sequential agent steps."""

    alert: dict[str, Any]
    auth_index: str
    settings: Settings
    splunk_client: SplunkClient | None = None
    events: list[dict[str, Any]] = field(default_factory=list)
    spl_query_used: str = ""
    evidence_stats: dict[str, Any] = field(default_factory=dict)
    triage_severity: str = "Medium"
    triage_rationale: str = ""
    follow_up_queries: list[dict[str, Any]] = field(default_factory=list)
    spl_explain_summary: str = ""
    spl_explain_source: str = ""
    contradictory: dict[str, list[str]] = field(default_factory=dict)
    sop_checklist: list[str] = field(default_factory=list)
    trust_notice: str = ""
    trust_level: str = "low"
    mitre_mappings: list[dict[str, Any]] = field(default_factory=list)


AgentFn = Callable[[InvestigationContext], AgentStepResult]


def run_agent_step(
    agent_name: str,
    objective: str,
    fn: AgentFn,
    ctx: InvestigationContext,
) -> AgentStepResult:
    """Execute one agent with timestamps; capture errors without raising."""
    started = utc_now_iso()
    step = AgentStepResult(
        agent_name=agent_name,
        objective=objective,
        status="running",
        started_at=started,
        completed_at="",
        tools_used=[],
        input_summary="",
        output_summary="",
        evidence=[],
        recommendations=[],
    )
    try:
        result = fn(ctx)
        result.started_at = started
        if not result.completed_at:
            result.completed_at = utc_now_iso()
        if result.status == "running":
            result.status = "complete"
        return result
    except Exception as exc:  # noqa: BLE001
        return AgentStepResult(
            agent_name=agent_name,
            objective=objective,
            status="error",
            started_at=started,
            completed_at=utc_now_iso(),
            tools_used=[],
            input_summary="",
            output_summary="",
            evidence=[],
            recommendations=[],
            error=str(exc),
        )


def summarize_events_stats(events: list[dict[str, Any]]) -> dict[str, Any]:
    failures = [e for e in events if str(e.get("action", "")).lower() == "failure"]
    successes = [e for e in events if str(e.get("action", "")).lower() == "success"]
    countries = sorted({str(e.get("geo_country") or "").strip() for e in events if e.get("geo_country")})
    source_ips = sorted({str(e.get("src_ip") or "").strip() for e in events if e.get("src_ip")})
    risk_vals = [safe_int(e.get("risk_score")) for e in events]
    risk_vals = [r for r in risk_vals if r is not None]
    return {
        "event_count": len(events),
        "failure_count": len(failures),
        "success_count": len(successes),
        "unique_countries": len(countries),
        "countries": countries,
        "source_ips": source_ips,
        "distinct_failure_src_ips": len({str(e.get("src_ip")) for e in failures if e.get("src_ip")}),
        "max_risk_score": max(risk_vals) if risk_vals else 0,
    }
