"""Generate investigation guidance via Splunk AI Assistant with local fallback."""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Literal

from agents.base import summarize_events_stats
from ai_agent import InvestigationAIResult, generate_investigation
from config import Settings
from saia_rest_client import SaiaRestClient, SaiaRestError

logger = logging.getLogger(__name__)

InvestigationSource = Literal["saia", "fallback"]
_VALID_SEVERITIES = frozenset({"low", "medium", "high", "critical"})


def _format_event_sample(events: list[dict[str, Any]], *, limit: int = 6) -> str:
    if not events:
        return "- No authentication events returned from Splunk."
    lines: list[str] = []
    for event in events[:limit]:
        lines.append(
            f"- time={event.get('_time')} user={event.get('user')} action={event.get('action')} "
            f"src_ip={event.get('src_ip')} geo={event.get('geo_country')} "
            f"auth_method={event.get('auth_method')} risk={event.get('risk_score')}"
        )
    if len(events) > limit:
        lines.append(f"- … and {len(events) - limit} more event(s)")
    return "\n".join(lines)


def _build_investigation_context(alert: dict[str, Any], events: list[dict[str, Any]]) -> str:
    stats = summarize_events_stats(events)
    tactics = alert.get("mitre_tactics") or []
    return (
        f"Alert ID: {alert.get('alert_id')}\n"
        f"Title: {alert.get('title', '')}\n"
        f"User: {alert.get('user', '')}\n"
        f"Scenario: {alert.get('scenario', '')}\n"
        f"Catalog severity: {alert.get('severity', '')}\n"
        f"Summary: {alert.get('summary', '')}\n"
        f"MITRE tactics (catalog): {', '.join(tactics) if tactics else 'none'}\n"
        "\n"
        "Splunk auth event stats:\n"
        f"- Event count: {stats.get('event_count', 0)}\n"
        f"- Failures: {stats.get('failure_count', 0)}\n"
        f"- Successes: {stats.get('success_count', 0)}\n"
        f"- Countries: {', '.join(stats.get('countries') or []) or 'none'}\n"
        f"- Distinct failure source IPs: {stats.get('distinct_failure_src_ips', 0)}\n"
        f"- Max risk_score: {stats.get('max_risk_score', 0)}\n"
        "\n"
        "Sample Splunk events:\n"
        f"{_format_event_sample(events)}\n"
    )


def _build_investigation_prompt(context_block: str) -> str:
    return (
        "You are a SOC analyst assistant for TrustOps. Using ONLY the alert metadata and "
        "Splunk evidence below, produce investigation guidance.\n\n"
        f"{context_block.strip()}\n\n"
        "Return a single JSON object with exactly these keys:\n"
        '- "investigation_summary": string (1-2 sentences)\n'
        '- "key_evidence": array of 3-5 short evidence bullets grounded in the Splunk data\n'
        '- "ai_recommendation": string (actionable analyst guidance; note that human approval '
        "is required before containment or response actions)\n"
        '- "recommended_severity": one of Low, Medium, High, Critical\n'
        '- "recommended_actions": array of 3-5 concrete response steps\n'
        '- "confidence_rationale": string explaining confidence in the assessment\n\n'
        "Return ONLY valid JSON with no markdown fences or commentary."
    )


def _extract_json_object(text: str) -> dict[str, Any] | None:
    raw = text.strip()
    if not raw:
        return None

    candidates = [raw]
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw, re.IGNORECASE)
    if fence:
        candidates.insert(0, fence.group(1).strip())

    start = raw.find("{")
    end = raw.rfind("}")
    if start >= 0 and end > start:
        candidates.append(raw[start : end + 1])

    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed
    return None


def _as_string_list(value: Any, *, field: str) -> list[str]:
    if isinstance(value, list):
        items = [str(v).strip() for v in value if str(v).strip()]
        if items:
            return items
    if isinstance(value, str) and value.strip():
        return [line.strip() for line in value.split("\n") if line.strip()]
    raise ValueError(f"invalid or empty list field: {field}")


def _normalize_severity(value: Any) -> str:
    text = str(value or "Medium").strip().lower()
    if text not in _VALID_SEVERITIES:
        raise ValueError(f"invalid severity: {value}")
    return text.title()


def _parse_investigation_payload(data: dict[str, Any]) -> InvestigationAIResult:
    return InvestigationAIResult(
        investigation_summary=str(data.get("investigation_summary") or "").strip(),
        key_evidence=_as_string_list(data.get("key_evidence"), field="key_evidence"),
        ai_recommendation=str(data.get("ai_recommendation") or "").strip(),
        recommended_severity=_normalize_severity(data.get("recommended_severity")),
        recommended_actions=_as_string_list(data.get("recommended_actions"), field="recommended_actions"),
        confidence_rationale=str(data.get("confidence_rationale") or "").strip(),
    )


def _validate_investigation_result(result: InvestigationAIResult) -> None:
    if len(result.investigation_summary) < 20:
        raise ValueError("investigation_summary too short")
    if len(result.ai_recommendation) < 20:
        raise ValueError("ai_recommendation too short")
    if len(result.confidence_rationale) < 20:
        raise ValueError("confidence_rationale too short")
    if not result.key_evidence:
        raise ValueError("key_evidence empty")
    if not result.recommended_actions:
        raise ValueError("recommended_actions empty")


def _try_saia_investigation(settings: Settings, prompt: str) -> tuple[str | None, str | None]:
    try:
        client = SaiaRestClient(settings)
        if not client.configured():
            return None, "Splunk credentials not configured"
        answer = client.answer_question(prompt)
        if answer and answer.strip():
            return answer.strip(), None
        return None, "empty SAIA response"
    except SaiaRestError as exc:
        return None, str(exc)


def resolve_investigation(
    alert: dict[str, Any],
    events: list[dict[str, Any]],
    settings: Settings,
) -> tuple[InvestigationAIResult, InvestigationSource, str | None]:
    """
    Ask Splunk AI Assistant for investigation guidance; fall back to deterministic rules.
    """
    context = _build_investigation_context(alert, events)
    prompt = _build_investigation_prompt(context)
    answer, saia_err = _try_saia_investigation(settings, prompt)

    if answer:
        payload = _extract_json_object(answer)
        if payload is not None:
            try:
                result = _parse_investigation_payload(payload)
                _validate_investigation_result(result)
                return result, "saia", None
            except ValueError as exc:
                saia_err = saia_err or f"SAIA JSON parse/validation failed: {exc}"
                logger.warning("SAIA investigation response unusable: %s", exc)
        else:
            saia_err = saia_err or "SAIA response was not valid JSON"

    fallback = generate_investigation(alert, events)
    detail = saia_err or "Splunk AI Assistant unavailable; using local fallback."
    return fallback, "fallback", detail
