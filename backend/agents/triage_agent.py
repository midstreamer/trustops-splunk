"""Triage Agent — severity from Splunk-grounded event statistics."""

from __future__ import annotations

from agents.base import InvestigationContext
from models import AgentStepResult


def run_triage_agent(ctx: InvestigationContext) -> AgentStepResult:
    stats = ctx.evidence_stats
    failures = int(stats.get("failure_count", 0))
    successes = int(stats.get("success_count", 0))
    unique_countries = int(stats.get("unique_countries", 0))
    max_risk = int(stats.get("max_risk_score", 0))

    if failures >= 5 and successes >= 1 and (unique_countries >= 2 or max_risk >= 80):
        severity = "High"
        rationale = (
            f"High: {failures} failures, {successes} success(es), "
            f"{unique_countries} countries, max risk_score {max_risk}."
        )
    elif failures >= 3 or max_risk >= 60:
        severity = "Medium"
        rationale = (
            f"Medium: {failures} failures, max risk_score {max_risk} "
            f"(threshold: failures>=3 or risk>=60)."
        )
    else:
        severity = "Low"
        rationale = (
            f"Low: {failures} failures, {successes} successes, "
            f"max risk_score {max_risk} below escalation thresholds."
        )

    ctx.triage_severity = severity
    ctx.triage_rationale = rationale

    return AgentStepResult(
        agent_name="Triage Agent",
        objective="Classify severity and urgency",
        status="complete",
        started_at="",
        completed_at="",
        tools_used=["local_rules", "splunk_event_context"],
        input_summary=f"Alert {ctx.alert.get('alert_id')} with {stats.get('event_count', 0)} Splunk events.",
        output_summary=f"Recommended triage severity: {severity}. {rationale}",
        evidence=[
            f"failure_count={failures}",
            f"success_count={successes}",
            f"unique_countries={unique_countries}",
            f"max_risk_score={max_risk}",
        ],
        recommendations=[
            f"Set investigation final severity considering triage result ({severity}).",
            "Escalate if user denies activity or evidence aligns with takeover.",
        ],
    )
