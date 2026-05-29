"""Agentic investigation helpers for investigation API (follow-up SPL, contradictory evidence)."""

from __future__ import annotations

from typing import Any

from agents.spl_queries import (
    auth_base,
    spl_active_vpn_sessions,
    spl_failed_burst_by_src,
    spl_mfa_changes,
    spl_other_users_suspicious_geo,
    spl_prior_success_logins,
)
from models import ContradictoryEvidence, FollowUpQuery


def build_contradictory_evidence(alert: dict[str, Any]) -> ContradictoryEvidence:
    alert_id = str(alert.get("alert_id", ""))
    if alert_id == "TO-VPN-2026-514" or alert.get("scenario") == "vpn_brute_then_geo_anomaly":
        return ContradictoryEvidence(
            possible_benign_explanations=[
                "User may be traveling internationally.",
                "IP geolocation may be inaccurate.",
                "Approved vendor or contractor activity may use the account.",
                "Failed attempts could reflect user lockout or misconfigured client.",
            ],
            recommended_validation_steps=[
                "Contact user through known-good channel.",
                "Check HR or travel records if available.",
                "Review VPN session metadata.",
                "Check whether the Romania IP has appeared for other users.",
                "Validate MFA enrollment and recent changes.",
            ],
            evidence_gaps=[
                "No IP reputation enrichment available.",
                "No endpoint telemetry reviewed yet.",
                "No user travel context available.",
            ],
        )
    return ContradictoryEvidence(
        possible_benign_explanations=[
            "Activity may align with approved business travel or remote work.",
            "Alert correlation may be incomplete for this data source.",
            "User lockout or client misconfiguration can mimic attack patterns.",
        ],
        recommended_validation_steps=[
            "Contact the account owner through a known-good channel.",
            "Review recent authentication history and device posture.",
            "Validate whether related alerts share a common benign root cause.",
        ],
        evidence_gaps=[
            "Limited enrichment beyond index trustops auth events.",
            "No endpoint or identity-provider change logs in scope.",
        ],
    )


def build_follow_up_queries(alert: dict[str, Any], auth_index: str = "trustops") -> list[FollowUpQuery]:
    user = str(alert.get("user") or "jsmith")
    alert_id = str(alert.get("alert_id") or "")

    if alert_id == "TO-VPN-2026-514" or alert.get("scenario") == "vpn_brute_then_geo_anomaly":
        return [
            FollowUpQuery(
                title="Prior successful logins for jsmith",
                purpose="Establish baseline geography and VPN usage before the anomaly window.",
                spl=spl_prior_success_logins(user, auth_index),
                priority="high",
            ),
            FollowUpQuery(
                title="Other users authenticating from suspicious Romania IP",
                purpose="Determine whether the successful-login source IP is shared or isolated to this account.",
                spl=spl_other_users_suspicious_geo(user, "Romania", auth_index),
                priority="high",
            ),
            FollowUpQuery(
                title="Active VPN sessions for jsmith after successful login",
                purpose="Identify ongoing sessions that may require revocation after containment.",
                spl=spl_active_vpn_sessions(user, alert_id, auth_index),
                priority="high",
            ),
            FollowUpQuery(
                title="MFA changes for jsmith",
                purpose="Detect MFA enrollment or factor changes that may indicate takeover preparation.",
                spl=spl_mfa_changes(user, auth_index),
                priority="medium",
            ),
            FollowUpQuery(
                title="Failed login burst by source IP",
                purpose="Cluster failed attempts by source IP to spot distributed credential testing.",
                spl=spl_failed_burst_by_src(alert_id, auth_index),
                priority="medium",
            ),
        ]

    return [
        FollowUpQuery(
            title=f"Authentication history for {user}",
            purpose="Review recent successes and failures for this account.",
            spl=spl_prior_success_logins(user, auth_index),
            priority="high",
        ),
        FollowUpQuery(
            title="Failed attempts for this alert",
            purpose="Summarize failure sources tied to the selected alert.",
            spl=spl_failed_burst_by_src(alert_id, auth_index),
            priority="medium",
        ),
    ]


# Re-export for tests that import _auth_base
_auth_base = auth_base
