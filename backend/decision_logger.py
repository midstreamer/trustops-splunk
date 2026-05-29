"""Format analyst decisions as CSV _raw and submit to Splunk."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from decision_telemetry import build_decision_csv_line
from models import DecisionCreate, DecisionLogged
from splunk_client import SplunkClient
from trust_calibration import (
    automation_bias_risk_level,
    automation_bias_risk_score,
    post_decision_feedback,
)

logger = logging.getLogger(__name__)


def log_decision_to_splunk(client: SplunkClient, decision: DecisionCreate) -> DecisionLogged:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    bias_score = automation_bias_risk_score(decision)
    bias_level = automation_bias_risk_level(bias_score)
    feedback_message, learning_point = post_decision_feedback(decision)

    raw = build_decision_csv_line(
        ts,
        decision,
        automation_bias_risk_score=bias_score,
        automation_bias_risk_level=bias_level,
        feedback_message=feedback_message,
        learning_point=learning_point,
    )
    logger.info("Submitting decision event to Splunk (%s bytes)", len(raw))
    client.submit_raw_event(raw)

    return DecisionLogged(
        timestamp=ts,
        automation_bias_risk_score=bias_score,
        automation_bias_risk_level=bias_level,
        feedback_message=feedback_message,
        learning_point=learning_point,
        **decision.model_dump(),
    )
