"""Splunk decision CSV schema and field sanitization."""

from __future__ import annotations

from models import DecisionCreate

DECISION_CSV_FIELD_NAMES = (
    "timestamp",
    "alert_id",
    "analyst",
    "ai_recommendation",
    "analyst_decision",
    "final_severity",
    "confidence_score",
    "trust_score",
    "time_to_decision_seconds",
    "ai_recommendation_status",
    "evidence_reviewed_count",
    "sop_followed",
    "notes",
    "evidence_checklist",
    "supporting_evidence",
    "contradicting_evidence",
    "automation_bias_risk_score",
    "automation_bias_risk_level",
    "feedback_message",
    "learning_point",
    "client_decision_id",
    "agent_plan_viewed",
    "follow_up_queries_viewed",
    "contradictory_evidence_viewed",
)

LEGACY_DECISION_FIELD_COUNT = 13


def sanitize_csv_field(value: str) -> str:
    """Replace commas and newlines so comma-delimited _raw parses reliably in Splunk."""
    return value.replace(",", ";").replace("\r", " ").replace("\n", " ").strip()


def build_decision_csv_line(
    ts: str,
    decision: DecisionCreate,
    *,
    automation_bias_risk_score: int,
    automation_bias_risk_level: str,
    feedback_message: str,
    learning_point: str,
) -> str:
    """Single CSV line (no header) matching DECISION_CSV_FIELD_NAMES order."""
    fields = [
        ts,
        sanitize_csv_field(decision.alert_id),
        sanitize_csv_field(decision.analyst),
        sanitize_csv_field(decision.ai_recommendation),
        sanitize_csv_field(decision.analyst_decision),
        sanitize_csv_field(decision.final_severity),
        str(decision.confidence_score),
        str(decision.trust_score),
        str(decision.time_to_decision_seconds),
        sanitize_csv_field(decision.ai_recommendation_status),
        str(decision.evidence_reviewed_count),
        "true" if decision.sop_followed else "false",
        sanitize_csv_field(decision.notes),
        sanitize_csv_field(decision.evidence_checklist),
        sanitize_csv_field(decision.supporting_evidence),
        sanitize_csv_field(decision.contradicting_evidence),
        str(automation_bias_risk_score),
        sanitize_csv_field(automation_bias_risk_level),
        sanitize_csv_field(feedback_message),
        sanitize_csv_field(learning_point),
        sanitize_csv_field(decision.client_decision_id),
        "true" if decision.agent_plan_viewed else "false",
        "true" if decision.follow_up_queries_viewed else "false",
        "true" if decision.contradictory_evidence_viewed else "false",
    ]
    return ",".join(fields)
