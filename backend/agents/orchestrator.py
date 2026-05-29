"""Sequential agent orchestrator for TrustOps investigations."""

from __future__ import annotations

import uuid
from typing import Any

from agents.base import InvestigationContext, run_agent_step, utc_now_iso
from agents.contradictory_evidence_agent import run_contradictory_evidence_agent
from agents.evidence_agent import run_evidence_agent
from agents.mitre_attack_agent import run_mitre_attack_agent
from agents.sop_agent import run_sop_agent
from agents.spl_agent import run_spl_agent
from agents.triage_agent import run_triage_agent
from agents.trust_calibration_agent import run_trust_calibration_agent
from config import Settings
from models import AgentRunResult, AgentStepResult
from splunk_client import SplunkClient


def _plan_summary(alert_id: str, steps: list[AgentStepResult]) -> str:
    errors = sum(1 for s in steps if s.status == "error")
    return (
        f"Tool-backed agentic workflow for alert {alert_id}: "
        f"{len(steps)} specialized steps executed sequentially "
        f"({errors} error(s)). Evidence Agent queries Splunk; SPL Agent builds follow-up searches "
        f"with SAIA explain when available."
    )


def _final_summary(ctx: InvestigationContext, steps: list[AgentStepResult]) -> str:
    stats = ctx.evidence_stats
    sev = ctx.triage_severity
    parts = [
        f"Triage: {sev}.",
        f"Splunk evidence: {stats.get('event_count', 0)} events "
        f"({stats.get('failure_count', 0)} failures, {stats.get('success_count', 0)} successes).",
    ]
    if ctx.mitre_mappings:
        labels = [
            f"{m.get('technique', '')} ({m.get('technique_id', '')})"
            for m in ctx.mitre_mappings
            if m.get("technique_id")
        ]
        if labels:
            parts.insert(2, f"MITRE mapping: {', '.join(labels)}.")
    if ctx.follow_up_queries:
        parts.append(f"{len(ctx.follow_up_queries)} follow-up SPL queries prepared.")
    if ctx.sop_checklist:
        parts.append(f"SOP: {len(ctx.sop_checklist)} response actions.")
    if any(s.status == "error" for s in steps):
        parts.append("Review steps marked error before deciding.")
    return " ".join(parts)


def run_agentic_investigation(
    alert: dict[str, Any],
    *,
    settings: Settings,
    splunk_client: SplunkClient | None,
) -> AgentRunResult:
    """
    Run specialized investigation agents in order.

    Order: Evidence → Triage → SPL → MITRE ATT&CK → Contradictory Evidence → SOP → Trust Calibration.
    """
    run_id = str(uuid.uuid4())
    started = utc_now_iso()

    ctx = InvestigationContext(
        alert=alert,
        auth_index=settings.splunk_auth_index,
        settings=settings,
        splunk_client=splunk_client if settings.splunk_credentials_configured() else None,
    )

    pipeline: list[tuple[str, str, Any]] = [
        ("Evidence Agent", "Retrieve and summarize Splunk evidence", run_evidence_agent),
        ("Triage Agent", "Classify severity and urgency", run_triage_agent),
        ("SPL Agent", "Generate and explain SPL queries", run_spl_agent),
        (
            "MITRE ATT&CK Mapping Agent",
            "Map Splunk-grounded alert evidence to MITRE ATT&CK tactics and techniques",
            run_mitre_attack_agent,
        ),
        (
            "Contradictory Evidence Agent",
            "Identify benign explanations and evidence gaps",
            run_contradictory_evidence_agent,
        ),
        ("SOP Agent", "Map alert to response procedure", run_sop_agent),
        (
            "Trust Calibration Agent",
            "Provide human-AI trust calibration guidance",
            run_trust_calibration_agent,
        ),
    ]

    steps: list[AgentStepResult] = []
    run_status: str = "complete"

    for name, objective, fn in pipeline:
        step = run_agent_step(name, objective, fn, ctx)
        steps.append(step)
        if step.status == "error":
            run_status = "error"

    completed = utc_now_iso()
    plan_summary = _plan_summary(str(alert.get("alert_id", "")), steps)
    final_summary = _final_summary(ctx, steps)

    return AgentRunResult(
        run_id=run_id,
        alert_id=str(alert.get("alert_id", "")),
        status=run_status,  # type: ignore[arg-type]
        started_at=started,
        completed_at=completed,
        plan_summary=plan_summary,
        steps=steps,
        final_summary=final_summary,
    )


def run_to_legacy_agent_plan(run: AgentRunResult) -> dict[str, Any]:
    """Map AgentRunResult to legacy agent-plan shape for backward-compatible clients."""
    from models import AgentPlanAgent, AgentPlanResponse

    agents = [
        AgentPlanAgent(
            agent_name=s.agent_name,
            objective=s.objective,
            status="complete" if s.status == "complete" else ("running" if s.status == "running" else "pending"),
            output_summary=s.output_summary or (s.error or ""),
        )
        for s in run.steps
    ]
    return AgentPlanResponse(
        alert_id=run.alert_id,
        plan_summary=run.plan_summary,
        agents=agents,
    ).model_dump()
