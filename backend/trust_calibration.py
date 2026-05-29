"""Human-AI trust calibration: notices, automation bias scoring, post-decision feedback."""

from __future__ import annotations

from typing import Literal

from models import DecisionCreate

TrustCalibrationLevel = Literal["low", "moderate", "high"]
BiasRiskLevel = Literal["Low", "Moderate", "High"]

TRUST_CALIBRATION_NOTICE_HIGH = (
    "High-confidence AI recommendations can increase automation bias. "
    "Review independent evidence before accepting the recommendation."
)

TRUST_CALIBRATION_NOTICE_MODERATE = (
    "Review key evidence before acting on the AI recommendation. "
    "Calibrated trust reduces both overreliance and unnecessary rejection."
)

TRUST_CALIBRATION_NOTICE_LOW = (
    "AI guidance is advisory. Confirm findings against Splunk evidence before deciding."
)


def trust_calibration_for_investigation(
    alert_id: str,
    alert_severity: str,
    recommended_severity: str,
) -> tuple[str, TrustCalibrationLevel]:
    """Return analyst-facing notice and calibration level for the investigation panel."""
    sev = (alert_severity or "").strip().lower()
    rec = (recommended_severity or "").strip().lower()

    high_trigger = (
        alert_id == "TO-VPN-2026-514"
        or sev in ("high", "critical")
        or rec in ("high", "critical")
    )
    moderate_trigger = sev == "medium" or rec == "medium"

    if high_trigger:
        return TRUST_CALIBRATION_NOTICE_HIGH, "high"
    if moderate_trigger:
        return TRUST_CALIBRATION_NOTICE_MODERATE, "moderate"
    return TRUST_CALIBRATION_NOTICE_LOW, "low"


def automation_bias_risk_score(decision: DecisionCreate) -> int:
    score = 0
    if decision.ai_recommendation_status == "accepted":
        score += 2
    if decision.trust_score >= 5:
        score += 2
    if decision.time_to_decision_seconds < 60:
        score += 2
    if decision.evidence_reviewed_count < 2:
        score += 2
    if decision.confidence_score >= 5:
        score += 1
    return score


def automation_bias_risk_level(score: int) -> BiasRiskLevel:
    if score <= 2:
        return "Low"
    if score <= 5:
        return "Moderate"
    return "High"


def post_decision_feedback(decision: DecisionCreate) -> tuple[str, str]:
    status = decision.ai_recommendation_status
    evidence = decision.evidence_reviewed_count

    if status == "accepted" and evidence >= 3:
        return (
            "You accepted the AI recommendation after reviewing multiple evidence points. "
            "This supports calibrated reliance.",
            "High-risk account takeover alerts should still be validated against independent "
            "evidence before containment.",
        )
    if status == "accepted" and evidence < 2:
        return (
            "You accepted the AI recommendation with limited evidence review. "
            "This may indicate automation bias risk.",
            "Before accepting AI guidance, confirm at least two independent evidence points.",
        )
    if status == "modified":
        return (
            "You modified the AI recommendation, which indicates active analyst judgment.",
            "Healthy human-AI collaboration includes adjusting AI recommendations when local "
            "context changes the risk picture.",
        )
    if status == "rejected":
        return (
            "You rejected the AI recommendation. Ensure the rejection is supported by "
            "contradictory evidence.",
            "Algorithm aversion can be as risky as overreliance when analysts dismiss useful "
            "AI guidance without evidence.",
        )
    return (
        "Decision recorded. Continue to balance AI assistance with independent evidence review.",
        "Calibrated trust improves outcomes in AI-augmented SOC workflows.",
    )
