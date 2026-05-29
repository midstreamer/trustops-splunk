"""
Deterministic local "AI" investigation summary (no external LLM).

Produces structured triage guidance so the Phase 2 workflow is reliable offline.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class InvestigationAIResult:
    investigation_summary: str
    key_evidence: list[str]
    ai_recommendation: str
    recommended_severity: str
    recommended_actions: list[str]
    confidence_rationale: str


def _safe_int(value: Any) -> int | None:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def generate_investigation(alert: dict[str, Any], events: list[dict[str, Any]]) -> InvestigationAIResult:
    """
    Rule-based triage from alert metadata + Splunk auth rows.

    Optimized for the canonical VPN burst → geo anomaly (TO-VPN-2026-514), but
    returns a sensible generic summary when events are sparse.
    """
    alert_id = str(alert.get("alert_id", ""))
    scenario = str(alert.get("scenario", ""))
    user = str(alert.get("user", ""))

    failures = [e for e in events if str(e.get("action", "")).lower() == "failure"]
    successes = [e for e in events if str(e.get("action", "")).lower() == "success"]
    geos = sorted({str(e.get("geo_country") or "").strip() for e in events if e.get("geo_country")})
    risk_vals = [_safe_int(e.get("risk_score")) for e in events]
    risk_vals = [r for r in risk_vals if r is not None]
    max_risk = max(risk_vals) if risk_vals else 0

    distinct_fail_src = len({str(e.get("src_ip")) for e in failures if e.get("src_ip")})

    is_vpn_burst_geo = (
        alert_id == "TO-VPN-2026-514"
        or scenario == "vpn_brute_then_geo_anomaly"
        or (len(failures) >= 3 and len(successes) >= 1 and len(geos) >= 2)
    )

    key_evidence: list[str] = []
    if failures:
        key_evidence.append(
            f"Observed {len(failures)} failed authentication events"
            + (f" across {distinct_fail_src} source IPs." if distinct_fail_src else ".")
        )
    if successes:
        key_evidence.append(f"Observed {len(successes)} successful authentication event(s).")
    if geos:
        key_evidence.append(f"Geographies seen in window: {', '.join(geos)}.")
    if max_risk:
        key_evidence.append(f"Peak risk_score in retrieved events: {max_risk}.")

    if is_vpn_burst_geo and (failures or successes):
        investigation_summary = (
            f"Pattern consistent with credential testing followed by a successful VPN login for `{user}` "
            "from an unfamiliar geography relative to prior successes in the same window."
        )
        ai_recommendation = (
            "Treat as high-priority account takeover risk until disproven: verify the user out-of-band, "
            "review active sessions, and prepare for credential reset and containment."
        )
        recommended_severity = "High"
        recommended_actions = [
            "Contact the user via a known-good channel to confirm whether VPN activity was expected.",
            "Revoke or invalidate suspicious VPN/SAML sessions tied to this account.",
            "Force a password reset and review MFA enrollment for drift or takeover.",
            "Escalate to incident response if the user denies the activity or evidence aligns with compromise.",
        ]
        confidence_rationale = (
            "Deterministic rules: repeated failures followed by success, multiple geographies, and elevated "
            f"risk_score ({max_risk}) increase confidence in a malicious session pivot narrative."
        )
    else:
        investigation_summary = (
            f"Reviewed {len(events)} authentication-related event(s) for alert `{alert_id}`. "
            "No strong automated pattern match to the canonical VPN/geo burst scenario."
        )
        ai_recommendation = (
            "Continue standard triage: validate user intent, review correlated alerts, and collect "
            "additional context before major containment actions."
        )
        recommended_severity = str(alert.get("severity", "Medium") or "Medium").title()
        recommended_actions = list(alert.get("recommended_actions") or [])[:5] or [
            "Validate user activity with the account owner.",
            "Review related authentication sources and device posture.",
        ]
        confidence_rationale = (
            "Deterministic rules: limited or ambiguous event evidence reduces automated confidence; "
            "rely on analyst judgment and additional searches."
        )

    return InvestigationAIResult(
        investigation_summary=investigation_summary,
        key_evidence=key_evidence or ["No authentication events were returned from Splunk for this alert."],
        ai_recommendation=ai_recommendation,
        recommended_severity=recommended_severity,
        recommended_actions=recommended_actions,
        confidence_rationale=confidence_rationale,
    )
