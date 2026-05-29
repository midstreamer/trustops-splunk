"""Trust Calibration Agent — human-AI oversight guidance (pre-decision)."""

from __future__ import annotations

from agents.base import InvestigationContext
from models import AgentStepResult
from trust_calibration import trust_calibration_for_investigation

_PRE_DECISION_GUIDANCE = (
    "High-confidence AI recommendations can increase automation bias. "
    "Validate at least two independent evidence points before accepting severity or containment actions."
)


def run_trust_calibration_agent(ctx: InvestigationContext) -> AgentStepResult:
    alert_id = str(ctx.alert.get("alert_id", ""))
    alert_sev = str(ctx.alert.get("severity", "Medium"))
    rec_sev = ctx.triage_severity or str(ctx.alert.get("severity", "Medium"))

    notice, level = trust_calibration_for_investigation(alert_id, alert_sev, rec_sev)
    ctx.trust_notice = notice
    ctx.trust_level = level

    recommendations = [
        _PRE_DECISION_GUIDANCE,
        "Complete the evidence checklist and document supporting vs contradicting rationale.",
        "Record whether you accepted, modified, or rejected the AI recommendation on submit.",
    ]
    if level == "high":
        recommendations.append(
            "High calibration level: prioritize independent Splunk pivots before escalation."
        )

    return AgentStepResult(
        agent_name="Trust Calibration Agent",
        objective="Provide human-AI trust calibration guidance",
        status="complete",
        started_at="",
        completed_at="",
        tools_used=["trust_calibration_rules"],
        input_summary=f"Pre-decision guidance for alert {alert_id} (triage={rec_sev}).",
        output_summary=notice,
        evidence=[f"trust_calibration_level={level}", f"triage_severity={rec_sev}"],
        recommendations=recommendations,
    )
