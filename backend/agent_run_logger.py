"""Log agent workflow step telemetry to Splunk (JSON _raw per step)."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from models import AgentRunResult, AgentStepResult
from splunk_client import SplunkClient

logger = logging.getLogger(__name__)

AGENT_STEP_SOURCETYPE = "trustops:agent_step"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def duration_ms(started_at: str, completed_at: str) -> int:
    if not started_at or not completed_at:
        return 0
    try:
        start = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
        end = datetime.fromisoformat(completed_at.replace("Z", "+00:00"))
        return max(0, int((end - start).total_seconds() * 1000))
    except (TypeError, ValueError):
        return 0


def build_agent_step_event(run: AgentRunResult, step: AgentStepResult) -> dict[str, object]:
    """Single JSON object for Splunk _raw (one event per agent step)."""
    ts = step.completed_at or step.started_at or run.completed_at or utc_now_iso()
    tools = step.tools_used or []
    payload: dict[str, object] = {
        "timestamp": ts,
        "run_id": run.run_id,
        "alert_id": run.alert_id,
        "agent_name": step.agent_name,
        "status": step.status,
        "tools_used": "|".join(tools) if tools else "",
        "started_at": step.started_at,
        "completed_at": step.completed_at,
        "duration_ms": duration_ms(step.started_at, step.completed_at),
        "evidence_count": len(step.evidence or []),
        "recommendation_count": len(step.recommendations or []),
        "output_summary": (step.output_summary or "")[:4000],
        "error": step.error or "",
    }
    if step.mitre_techniques:
        payload["mitre_techniques"] = step.mitre_techniques
        payload["mitre_techniques_flat"] = "|".join(step.mitre_techniques)
    if step.mitre_tactics:
        payload["mitre_tactics"] = step.mitre_tactics
        payload["mitre_tactics_flat"] = "|".join(step.mitre_tactics)
    if step.mitre_mappings:
        payload["mitre_mappings"] = [m.model_dump() for m in step.mitre_mappings]
    return payload


def log_agent_run_to_splunk(client: SplunkClient, run: AgentRunResult) -> tuple[int, str | None]:
    """
    Write one Splunk event per agent step.

    Returns (events_logged, warning_message). Does not raise on partial failure.
    """
    if not run.steps:
        return 0, None

    logged = 0
    errors: list[str] = []

    for step in run.steps:
        try:
            payload = build_agent_step_event(run, step)
            raw = json.dumps(payload, ensure_ascii=False)
            client.submit_raw_event(
                raw,
                index=client.settings.splunk_agent_run_index,
                sourcetype=AGENT_STEP_SOURCETYPE,
            )
            logged += 1
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Failed to log agent step %s for run %s: %s",
                step.agent_name,
                run.run_id,
                exc,
            )
            errors.append(f"{step.agent_name}: {exc}")

    if errors and logged == 0:
        return 0, "Agent run telemetry could not be written to Splunk: " + "; ".join(errors[:3])
    if errors:
        return logged, (
            f"Logged {logged}/{len(run.steps)} agent steps; failures: " + "; ".join(errors[:2])
        )
    return logged, None
