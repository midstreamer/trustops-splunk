"""SOP Agent — map scenario to response checklist."""

from __future__ import annotations

from agents.base import InvestigationContext
from models import AgentStepResult

_ACCOUNT_TAKEOVER_SOP = [
    "Validate user via known-good channel.",
    "Review active VPN/SAML sessions.",
    "Revoke suspicious sessions.",
    "Reset password if unauthorized.",
    "Review MFA enrollment.",
    "Escalate to IR if user denies activity.",
]

_GENERIC_SOP = [
    "Validate user activity with account owner.",
    "Review related authentication sources.",
    "Document findings and severity rationale.",
    "Escalate per local incident response policy if needed.",
]


def run_sop_agent(ctx: InvestigationContext) -> AgentStepResult:
    scenario = str(ctx.alert.get("scenario", ""))
    alert_id = str(ctx.alert.get("alert_id", ""))
    severity = ctx.triage_severity

    if scenario == "vpn_brute_then_geo_anomaly" or alert_id == "TO-VPN-2026-514":
        checklist = list(_ACCOUNT_TAKEOVER_SOP)
        sop_name = "Suspected account takeover SOP"
    else:
        checklist = list(_GENERIC_SOP)
        sop_name = "Standard authentication triage SOP"

    ctx.sop_checklist = checklist

    return AgentStepResult(
        agent_name="SOP Agent",
        objective="Map alert to response procedure",
        status="complete",
        started_at="",
        completed_at="",
        tools_used=["sop_mapping"],
        input_summary=f"scenario={scenario}, triage_severity={severity}.",
        output_summary=f"Mapped to {sop_name} ({len(checklist)} checklist items).",
        evidence=[f"Triage severity: {severity}", f"Scenario: {scenario or 'unspecified'}"],
        recommendations=checklist,
    )
