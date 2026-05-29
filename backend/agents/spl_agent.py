"""SPL Agent — follow-up queries and optional SAIA explain."""

from __future__ import annotations

from agents.base import InvestigationContext
from agents.spl_queries import (
    spl_active_vpn_sessions,
    spl_failed_burst_by_src,
    spl_failed_burst_by_user,
    spl_mfa_changes,
    spl_other_users_suspicious_geo,
    spl_prior_success_logins,
)
from models import AgentStepResult
from saia_service import explain_spl


def _pick_suspicious_geo(events: list[dict], default: str = "Romania") -> str:
    for e in events:
        if str(e.get("action", "")).lower() == "success":
            geo = str(e.get("geo_country") or "").strip()
            if geo:
                return geo
    return default


def run_spl_agent(ctx: InvestigationContext) -> AgentStepResult:
    user = str(ctx.alert.get("user") or "jsmith")
    alert_id = str(ctx.alert.get("alert_id", ""))
    auth_index = ctx.auth_index
    geo = _pick_suspicious_geo(ctx.events)

    queries = [
        {
            "title": f"Prior successful logins for {user}",
            "purpose": "Establish baseline geography and VPN usage before the anomaly window.",
            "spl": spl_prior_success_logins(user, auth_index),
            "priority": "high",
        },
        {
            "title": f"Other users authenticating from {geo}",
            "purpose": "Determine whether the successful-login geography is shared across accounts.",
            "spl": spl_other_users_suspicious_geo(user, geo, auth_index),
            "priority": "high",
        },
        {
            "title": f"Failed login burst by source IP ({alert_id})",
            "purpose": "Cluster failed attempts by source IP for credential-testing patterns.",
            "spl": spl_failed_burst_by_src(alert_id, auth_index),
            "priority": "medium",
        },
        {
            "title": f"Failed login burst for {user}",
            "purpose": "Summarize failure volume and sources for the affected account.",
            "spl": spl_failed_burst_by_user(user, alert_id, auth_index),
            "priority": "medium",
        },
        {
            "title": f"Active VPN sessions for {user} (placeholder)",
            "purpose": "Review recent successful VPN/SAML sessions that may need revocation.",
            "spl": spl_active_vpn_sessions(user, alert_id, auth_index),
            "priority": "high",
        },
        {
            "title": f"MFA changes for {user} (placeholder)",
            "purpose": "Placeholder search for MFA enrollment or factor changes in demo indexes.",
            "spl": spl_mfa_changes(user, auth_index),
            "priority": "low",
        },
    ]
    ctx.follow_up_queries = queries

    tools_used = ["local_spl_generator"]
    explain_note = ""

    if queries:
        first_spl = queries[0]["spl"]
        try:
            text, source = explain_spl(
                ctx.settings,
                first_spl,
                additional_context=queries[0].get("purpose"),
            )
            ctx.spl_explain_summary = (text or "")[:500]
            ctx.spl_explain_source = source
            if source == "saia":
                tools_used = ["local_spl_generator", "splunk_ai_assistant_explain_spl"]
                explain_note = " Splunk AI Assistant explained the first follow-up query."
            else:
                tools_used = ["local_spl_generator", "local_spl_explain_fallback"]
                explain_note = " Local fallback used to summarize the first follow-up SPL."
        except Exception as exc:  # noqa: BLE001
            explain_note = f" SPL explain unavailable: {exc}."

    return AgentStepResult(
        agent_name="SPL Agent",
        objective="Generate and explain SPL queries",
        status="complete",
        started_at="",
        completed_at="",
        tools_used=tools_used,
        input_summary=f"User={user}, alert={alert_id}, {len(ctx.events)} events in context.",
        output_summary=(
            f"Generated {len(queries)} follow-up SPL queries.{explain_note}"
        ),
        evidence=[f"{q['title']} ({q['priority']})" for q in queries],
        recommendations=[
            "Copy or explain follow-up SPL from the investigation panel.",
            "Run searches in Splunk Search after validating time range.",
        ],
    )
