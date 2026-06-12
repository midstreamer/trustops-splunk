"""Alert-scoped analyst chat — Splunk AI Assistant with local fallback."""

from __future__ import annotations

import uuid
from typing import Any

from agents.contradictory_evidence_agent import resolve_contradictory_evidence
from agentic_investigation import build_follow_up_queries
from agents.base import summarize_events_stats
from agents.mitre_attack_agent import resolve_mitre_attack_mappings
from agents.sop_agent import _ACCOUNT_TAKEOVER_SOP, _GENERIC_SOP
from ai_agent import generate_investigation
from config import Settings
from models import AlertChatResponse, MitreAttackMapping
from saia_rest_client import SaiaRestClient, SaiaRestError
from saia_service import _extract_spl_from_text, generate_spl

SAFETY_NOTE = "Analyst approval is required before containment or response actions."

_ACCOUNT_TAKEOVER_ALERTS = frozenset({"TO-VPN-2026-514"})
_VPN_SCENARIO = "vpn_brute_then_geo_anomaly"


def _sop_checklist(alert: dict[str, Any]) -> list[str]:
    alert_id = str(alert.get("alert_id", ""))
    scenario = str(alert.get("scenario", ""))
    if alert_id in _ACCOUNT_TAKEOVER_ALERTS or scenario == _VPN_SCENARIO:
        return list(_ACCOUNT_TAKEOVER_SOP)
    return list(_GENERIC_SOP)


def build_alert_context(
    alert: dict[str, Any],
    events: list[dict[str, Any]],
    *,
    investigation_summary: str,
    key_evidence: list[str],
    recommended_severity: str,
    recommended_actions: list[str],
    confidence_rationale: str,
    mitre_mappings: list[MitreAttackMapping] | None,
    mitre_rationale: str | None,
    contradictory: Any,
    sop_checklist: list[str],
    include_context: bool,
) -> tuple[str, list[str]]:
    """Format alert context for SAIA and list evidence sources referenced."""
    evidence_used: list[str] = []

    if not include_context:
        evidence_used.append(f"Alert {alert.get('alert_id')}")
        return f"Alert ID: {alert.get('alert_id')}\nTitle: {alert.get('title', '')}", evidence_used

    stats = summarize_events_stats(events)
    evidence_used.append(f"Splunk auth events ({stats.get('event_count', 0)} rows)")
    evidence_used.append("Investigation summary")
    if key_evidence:
        evidence_used.append("Key evidence bullets")
    if mitre_mappings:
        evidence_used.append("MITRE ATT&CK mappings")
    if contradictory:
        evidence_used.append("Contradictory evidence analysis")
    if sop_checklist:
        evidence_used.append("SOP response checklist")

    lines = [
        f"Alert ID: {alert.get('alert_id')}",
        f"Title: {alert.get('title', '')}",
        f"User: {alert.get('user', '')}",
        f"Scenario: {alert.get('scenario', '')}",
        f"Alert catalog severity: {alert.get('severity', '')}",
        "",
        "Splunk event summary:",
        f"- Event count: {stats.get('event_count', 0)}",
        f"- Failures: {stats.get('failure_count', 0)}",
        f"- Successes: {stats.get('success_count', 0)}",
        f"- Countries: {', '.join(stats.get('countries') or []) or 'none'}",
        f"- Max risk_score: {stats.get('max_risk_score', 0)}",
        f"- Distinct failure source IPs: {stats.get('distinct_failure_src_ips', 0)}",
        "",
        f"Investigation summary: {investigation_summary}",
        "",
        "Key evidence:",
    ]
    for item in key_evidence:
        lines.append(f"- {item}")

    lines.extend(
        [
            "",
            f"Recommended severity: {recommended_severity}",
            f"Confidence rationale: {confidence_rationale}",
            "",
            "Recommended actions:",
        ]
    )
    for action in recommended_actions:
        lines.append(f"- {action}")

    if mitre_mappings:
        lines.append("")
        lines.append("MITRE ATT&CK mappings:")
        if mitre_rationale:
            lines.append(f"Overall: {mitre_rationale}")
        for m in mitre_mappings:
            lines.append(
                f"- {m.tactic} / {m.technique} ({m.technique_id}): {m.rationale}"
            )

    if contradictory:
        lines.append("")
        lines.append("Possible benign explanations:")
        for item in contradictory.possible_benign_explanations:
            lines.append(f"- {item}")
        lines.append("Evidence gaps:")
        for item in contradictory.evidence_gaps:
            lines.append(f"- {item}")

    if sop_checklist:
        lines.append("")
        lines.append("SOP response checklist (human approval required before execution):")
        for i, step in enumerate(sop_checklist, 1):
            lines.append(f"{i}. {step}")

    return "\n".join(lines), evidence_used


def _build_compact_saia_context(
    alert: dict[str, Any],
    stats: dict[str, Any],
    *,
    investigation_summary: str,
    key_evidence: list[str],
    recommended_severity: str,
    mitre_mappings: list[MitreAttackMapping] | None,
    mitre_rationale: str | None,
) -> str:
    """Shorter context for SAIA /predict (large prompts often fail on Enterprise)."""
    lines = [
        f"alert_id={alert.get('alert_id')} user={alert.get('user')} scenario={alert.get('scenario')}",
        (
            f"Splunk: {stats.get('event_count', 0)} events, "
            f"{stats.get('failure_count', 0)} failures, {stats.get('success_count', 0)} successes, "
            f"countries={', '.join(stats.get('countries') or [])}, max_risk={stats.get('max_risk_score', 0)}"
        ),
        f"Summary: {investigation_summary[:500]}",
        f"Recommended severity: {recommended_severity}",
    ]
    for item in key_evidence[:4]:
        lines.append(f"Evidence: {item[:200]}")
    return "\n".join(lines)


def _build_saia_prompt(context_block: str, message: str) -> str:
    return (
        f"{context_block.strip()}\n\n"
        f"Question: {message.strip()}\n\n"
        "Answer using only the context above. "
        "Analyst approval is required before any containment or response action. "
        "If you suggest SPL, include one ```spl code block."
    )


def _try_saia_chat(settings: Settings, prompt: str) -> tuple[str | None, str | None]:
    try:
        client = SaiaRestClient(settings)
        if not client.configured():
            return None, "Splunk credentials not configured"
        answer = client.answer_question(prompt)
        if answer and answer.strip():
            text = answer.strip()
            if not _saia_answer_usable(text):
                return None, text[:200]
            return text, None
        return None, "empty SAIA response"
    except SaiaRestError as exc:
        return None, str(exc)


def _message_intent(message: str) -> str:
    lower = message.lower()
    if any(k in lower for k in ("high severity", "why high", "why is this high", "severity")):
        return "severity"
    if any(k in lower for k in ("benign", "false positive", "legitimate", "could make this")):
        return "benign"
    if any(k in lower for k in ("spl", "query", "search", "follow-up", "follow up")):
        return "spl"
    if any(k in lower for k in ("mitre", "att&ck", "attack", "t1078", "t1110")):
        return "mitre"
    if any(k in lower for k in ("sop", "what should i do", "next step", "response", "playbook")):
        return "sop"
    if any(k in lower for k in ("takeover", "compromise", "supports account", "evidence support")):
        return "takeover"
    if any(k in lower for k in ("trust", "calibration", "automation bias", "ai recommendation")):
        return "trust"
    return "general"


def _local_fallback_answer(
    message: str,
    *,
    alert: dict[str, Any],
    stats: dict[str, Any],
    investigation_summary: str,
    key_evidence: list[str],
    recommended_severity: str,
    mitre_mappings: list[MitreAttackMapping] | None,
    mitre_rationale: str | None,
    contradictory: Any,
    sop_checklist: list[str],
    trust_notice: str,
    settings: Settings,
) -> tuple[str, str | None]:
    intent = _message_intent(message)
    alert_id = str(alert.get("alert_id", ""))
    failures = int(stats.get("failure_count", 0))
    successes = int(stats.get("success_count", 0))
    countries = stats.get("countries") or []
    max_risk = int(stats.get("max_risk_score", 0))

    if intent == "severity":
        parts = [
            f"Recommended severity is {recommended_severity} based on Splunk-grounded evidence.",
            f"There were {failures} failed and {successes} successful authentication event(s).",
        ]
        if failures >= 5:
            parts.append(
                "The failed-login burst across multiple source IPs suggests credential testing."
            )
        if successes >= 1 and len(countries) >= 2:
            parts.append(
                f"A successful login followed failures from geography(ies): {', '.join(countries)}."
            )
        if max_risk >= 80:
            parts.append(f"Max observed risk_score is {max_risk}, above typical escalation thresholds.")
        if alert_id == "TO-VPN-2026-514" or alert.get("scenario") == _VPN_SCENARIO:
            parts.append(
                "For this VPN/SAML scenario, the Romania success after U.S. failures is a primary driver."
            )
        return "\n\n".join(parts), None

    if intent == "benign":
        explanations = (
            contradictory.possible_benign_explanations
            if contradictory
            else [
                "User may be traveling internationally.",
                "IP geolocation may be inaccurate.",
                "Approved vendor or contractor activity may use the account.",
                "Failed attempts could reflect user lockout or misconfigured client.",
            ]
        )
        lines = ["Possible benign explanations grounded in this alert context:"]
        for item in explanations:
            lines.append(f"- {item}")
        lines.append(
            "\nValidate with the user and supporting records before closing as false positive."
        )
        return "\n".join(lines), None

    if intent == "takeover":
        lines = ["Evidence supporting suspected account takeover in this alert context:"]
        for item in key_evidence:
            lines.append(f"- {item}")
        lines.append(
            f"\nSplunk stats: {failures} failures, {successes} success(es), "
            f"countries={', '.join(countries) or 'none'}, max risk_score={max_risk}."
        )
        return "\n".join(lines), None

    if intent == "spl":
        follow_ups = build_follow_up_queries(alert, settings.splunk_auth_index)
        spl = follow_ups[0].spl if follow_ups else ""
        if not spl:
            _, _, spl = generate_spl(
                settings,
                message,
                alert_id=alert_id,
                spl_only=True,
            )
        title = follow_ups[0].title if follow_ups else "Follow-up search"
        purpose = follow_ups[0].purpose if follow_ups else "Investigate related auth activity."
        answer = (
            f"Suggested follow-up SPL ({title}):\n\n{purpose}\n\n"
            f"```spl\n{spl.strip()}\n```"
        )
        return answer, spl.strip() if spl else None

    if intent == "mitre":
        if mitre_mappings:
            lines = ["MITRE ATT&CK mapping for this alert (from Splunk-grounded evidence):"]
            if mitre_rationale:
                lines.append(mitre_rationale)
            for m in mitre_mappings:
                lines.append(f"- {m.tactic} — {m.technique} ({m.technique_id}): {m.rationale}")
            return "\n".join(lines), None
        if alert_id == "TO-VPN-2026-514" or alert.get("scenario") == _VPN_SCENARIO:
            return (
                "MITRE ATT&CK mapping for this VPN/SAML scenario:\n\n"
                "- Credential Access — Brute Force (T1110): failed login burst suggests credential testing.\n"
                "- Initial Access — Valid Accounts (T1078): successful VPN/SAML login may indicate "
                "use of valid credentials after testing."
            ), None

    if intent == "sop":
        lines = ["Recommended SOP steps (analyst approval required before execution):"]
        for i, step in enumerate(sop_checklist, 1):
            lines.append(f"{i}. {step}")
        return "\n".join(lines), None

    if intent == "trust":
        if trust_notice:
            return trust_notice, None
        return (
            "Review supporting and contradicting evidence before accepting the AI recommendation. "
            "Calibrated trust means validating Splunk evidence independently and documenting your rationale."
        ), None

    summary_bits = [investigation_summary]
    if key_evidence:
        summary_bits.append("Key points: " + "; ".join(key_evidence[:3]))
    summary_bits.append(f"Current recommended severity: {recommended_severity}.")
    return " ".join(summary_bits), None


def _extract_suggested_spl(answer: str) -> str | None:
    spl = _extract_spl_from_text(answer)
    if spl:
        return spl
    if answer.strip().lower().startswith(("search ", "index=")):
        return answer.strip()
    return None


def _saia_answer_usable(answer: str) -> bool:
    lower = answer.lower().strip()
    if len(lower) < 40:
        return False
    unhelpful = (
        "can you clarify",
        "how does this question relate",
        "please provide more",
        "i cannot",
        "i can't help",
        "error occurred generating",
        "try again later",
    )
    return not any(p in lower for p in unhelpful)


def handle_alert_chat(
    *,
    alert: dict[str, Any],
    events: list[dict[str, Any]],
    message: str,
    conversation_id: str | None,
    include_context: bool,
    settings: Settings,
    trust_notice: str = "",
) -> AlertChatResponse:
    conv_id = conversation_id or str(uuid.uuid4())
    event_dicts = [dict(e) for e in events]
    stats = summarize_events_stats(event_dicts)

    ai = generate_investigation(alert, event_dicts)
    contradictory = resolve_contradictory_evidence(alert, event_dicts, settings)
    mitre_mappings, mitre_rationale = resolve_mitre_attack_mappings(
        alert, event_dicts, settings
    )
    sop_checklist = _sop_checklist(alert)

    context_block, evidence_used = build_alert_context(
        alert,
        event_dicts,
        investigation_summary=ai.investigation_summary,
        key_evidence=ai.key_evidence,
        recommended_severity=ai.recommended_severity,
        recommended_actions=ai.recommended_actions,
        confidence_rationale=ai.confidence_rationale,
        mitre_mappings=mitre_mappings or None,
        mitre_rationale=mitre_rationale,
        contradictory=contradictory,
        sop_checklist=sop_checklist,
        include_context=include_context,
    )

    suggested_spl: str | None = None
    compact_ctx = _build_compact_saia_context(
        alert,
        stats,
        investigation_summary=ai.investigation_summary,
        key_evidence=ai.key_evidence,
        recommended_severity=ai.recommended_severity,
        mitre_mappings=mitre_mappings or None,
        mitre_rationale=mitre_rationale,
    )
    saia_prompt = _build_saia_prompt(compact_ctx, message)
    answer, saia_err = _try_saia_chat(settings, saia_prompt)

    if answer and _saia_answer_usable(answer):
        source: str = "splunk_ai_assistant"
        suggested_spl = _extract_suggested_spl(answer)
    else:
        if answer and not _saia_answer_usable(answer):
            saia_err = saia_err or "SAIA response did not use alert context; using local fallback."
        answer, suggested_spl = _local_fallback_answer(
            message,
            alert=alert,
            stats=stats,
            investigation_summary=ai.investigation_summary,
            key_evidence=ai.key_evidence,
            recommended_severity=ai.recommended_severity,
            mitre_mappings=mitre_mappings or None,
            mitre_rationale=mitre_rationale,
            contradictory=contradictory,
            sop_checklist=sop_checklist,
            trust_notice=trust_notice,
            settings=settings,
        )
        source = "local_fallback"

    return AlertChatResponse(
        conversation_id=conv_id,
        alert_id=str(alert.get("alert_id", "")),
        answer=answer.strip(),
        evidence_used=evidence_used,
        suggested_spl=suggested_spl,
        source=source,  # type: ignore[arg-type]
        safety_note=SAFETY_NOTE,
    )
