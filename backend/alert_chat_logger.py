"""Log alert-scoped analyst chat telemetry to Splunk."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from models import AlertChatResponse
from splunk_client import SplunkClient

logger = logging.getLogger(__name__)

ANALYST_CHAT_SOURCETYPE = "trustops:analyst_chat"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_analyst_chat_event(
    *,
    conversation_id: str,
    alert_id: str,
    question: str,
    response: AlertChatResponse,
    analyst: str = "",
) -> dict[str, object]:
    return {
        "timestamp": utc_now_iso(),
        "conversation_id": conversation_id,
        "alert_id": alert_id,
        "analyst": analyst,
        "question": question[:2000],
        "source": response.source,
        "suggested_spl_present": bool(response.suggested_spl),
        "answer_summary": (response.answer or "")[:500],
    }


def log_analyst_chat_to_splunk(
    client: SplunkClient,
    *,
    conversation_id: str,
    alert_id: str,
    question: str,
    response: AlertChatResponse,
    analyst: str = "",
) -> None:
    """Write one chat event; failures are logged and swallowed."""
    try:
        payload = build_analyst_chat_event(
            conversation_id=conversation_id,
            alert_id=alert_id,
            question=question,
            response=response,
            analyst=analyst,
        )
        raw = json.dumps(payload, ensure_ascii=False)
        client.submit_raw_event(
            raw,
            index=client.settings.splunk_agent_run_index,
            sourcetype=ANALYST_CHAT_SOURCETYPE,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to log analyst chat for alert %s: %s", alert_id, exc)
