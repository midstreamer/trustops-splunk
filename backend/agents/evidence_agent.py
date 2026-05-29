"""Evidence Agent — Splunk auth event search and factual summary."""

from __future__ import annotations

from agents.base import InvestigationContext, summarize_events_stats, utc_now_iso
from models import AgentStepResult
from splunk_client import spl_auth_events_spl


def run_evidence_agent(ctx: InvestigationContext) -> AgentStepResult:
    alert_id = str(ctx.alert.get("alert_id", ""))
    input_summary = f"Retrieve authentication events for alert_id={alert_id} from index {ctx.auth_index}."

    if not ctx.splunk_client:
        ctx.events = []
        ctx.evidence_stats = summarize_events_stats([])
        return AgentStepResult(
            agent_name="Evidence Agent",
            objective="Retrieve and summarize Splunk evidence",
            status="error",
            started_at=utc_now_iso(),
            completed_at=utc_now_iso(),
            tools_used=[],
            input_summary=input_summary,
            output_summary="Splunk client not configured; no events retrieved.",
            evidence=["Splunk credentials required for evidence retrieval."],
            recommendations=["Configure SPLUNK_USER and SPLUNK_PASSWORD and retry."],
            error="Splunk not configured",
        )

    spl = spl_auth_events_spl(alert_id, ctx.auth_index)
    ctx.spl_query_used = spl
    rows = ctx.splunk_client.run_oneshot_json(spl)
    ctx.events = [dict(r) for r in rows]
    stats = summarize_events_stats(ctx.events)
    ctx.evidence_stats = stats

    evidence = [
        f"Retrieved {stats['event_count']} authentication event(s) from Splunk.",
        f"Failures: {stats['failure_count']}; successes: {stats['success_count']}.",
        f"Distinct source IPs on failures: {stats['distinct_failure_src_ips']}.",
        f"Geographies: {', '.join(stats['countries']) or 'none'}.",
        f"Max risk_score: {stats['max_risk_score']}.",
    ]

    return AgentStepResult(
        agent_name="Evidence Agent",
        objective="Retrieve and summarize Splunk evidence",
        status="complete",
        started_at="",
        completed_at="",
        tools_used=["splunk_search"],
        input_summary=input_summary,
        output_summary=(
            f"Splunk search returned {stats['event_count']} rows "
            f"({stats['failure_count']} failures, {stats['success_count']} successes)."
        ),
        evidence=evidence,
        recommendations=[
            "Review the event timeline table in the investigation panel.",
            "Use follow-up SPL pivots to validate baseline and shared-IP hypotheses.",
        ],
    )
