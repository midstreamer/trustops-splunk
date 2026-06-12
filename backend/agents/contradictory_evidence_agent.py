"""Contradictory Evidence Agent — benign hypotheses, gaps, validation steps."""

from __future__ import annotations

from typing import Any

from agents.base import InvestigationContext, summarize_events_stats
from config import Settings
from models import AgentStepResult, ContradictoryEvidence


def run_contradictory_evidence_agent(ctx: InvestigationContext) -> AgentStepResult:
    stats = ctx.evidence_stats
    scenario = str(ctx.alert.get("scenario", ""))
    alert_id = str(ctx.alert.get("alert_id", ""))

    benign = [
        "User may be traveling internationally.",
        "IP geolocation may be inaccurate.",
        "Approved vendor or contractor activity may use the account.",
        "Failed attempts could reflect user lockout or misconfigured client.",
    ]
    if stats.get("success_count", 0) == 0:
        benign.append("No successful login in retrieved window — pattern may be incomplete.")

    gaps = [
        "No user travel context available.",
        "No IP reputation enrichment available.",
        "No endpoint telemetry reviewed yet.",
        "No MFA change data confirmed in current indexes.",
    ]
    if stats.get("event_count", 0) == 0:
        gaps.insert(0, "No Splunk auth events returned for this alert in the selected time range.")

    validation = [
        "Contact user through known-good channel.",
        "Check HR or travel records if available.",
        "Review VPN session metadata.",
        "Check whether suspicious geography appears for other users.",
        "Validate MFA enrollment and recent changes.",
    ]

    if alert_id != "TO-VPN-2026-514" and scenario != "vpn_brute_then_geo_anomaly":
        benign[0] = "Activity may align with approved business travel or remote work."

    ctx.contradictory = {
        "possible_benign_explanations": benign,
        "recommended_validation_steps": validation,
        "evidence_gaps": gaps,
    }

    tools = ["local_reasoning"]
    if ctx.spl_explain_source == "saia":
        tools.append("splunk_ai_assistant_context")

    return AgentStepResult(
        agent_name="Contradictory Evidence Agent",
        objective="Identify benign explanations and evidence gaps",
        status="complete",
        started_at="",
        completed_at="",
        tools_used=tools,
        input_summary=f"Challenge AI narrative for alert {alert_id} using {stats.get('event_count', 0)} events.",
        output_summary=(
            f"Identified {len(benign)} benign hypotheses, {len(gaps)} evidence gaps, "
            f"and {len(validation)} validation steps."
        ),
        evidence=benign[:3] + gaps[:2],
        recommendations=validation,
    )


def resolve_contradictory_evidence(
    alert: dict[str, Any],
    events: list[dict[str, Any]],
    settings: Settings,
    *,
    spl_explain_source: str = "",
) -> ContradictoryEvidence:
    """Run the Contradictory Evidence Agent against alert metadata and Splunk events."""
    event_dicts = [dict(e) for e in events]
    ctx = InvestigationContext(
        alert=alert,
        auth_index=settings.splunk_auth_index,
        settings=settings,
        events=event_dicts,
        evidence_stats=summarize_events_stats(event_dicts),
        spl_explain_source=spl_explain_source,
    )
    run_contradictory_evidence_agent(ctx)
    contradictory = ctx.contradictory
    return ContradictoryEvidence(
        possible_benign_explanations=list(
            contradictory.get("possible_benign_explanations") or []
        ),
        recommended_validation_steps=list(
            contradictory.get("recommended_validation_steps") or []
        ),
        evidence_gaps=list(contradictory.get("evidence_gaps") or []),
    )
