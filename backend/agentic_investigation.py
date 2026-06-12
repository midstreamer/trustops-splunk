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
from models import FollowUpQuery


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
