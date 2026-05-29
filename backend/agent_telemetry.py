"""Aggregate agent-step rows from Splunk for summary API."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from models import (
    AgentRunAvgDuration,
    AgentRunCountByAgent,
    AgentRunCountByStatus,
    AgentRunsSummaryResponse,
    AgentStepTelemetryRow,
)


def rows_to_telemetry_steps(rows: list[dict[str, Any]]) -> list[AgentStepTelemetryRow]:
    out: list[AgentStepTelemetryRow] = []
    for r in rows:
        dm = r.get("duration_ms")
        ec = r.get("evidence_count")
        rc = r.get("recommendation_count")
        try:
            dm_i = int(float(dm)) if dm not in (None, "") else None
        except (TypeError, ValueError):
            dm_i = None
        try:
            ec_i = int(float(ec)) if ec not in (None, "") else None
        except (TypeError, ValueError):
            ec_i = None
        try:
            rc_i = int(float(rc)) if rc not in (None, "") else None
        except (TypeError, ValueError):
            rc_i = None
        out.append(
            AgentStepTelemetryRow(
                timestamp=r.get("timestamp"),
                run_id=r.get("run_id"),
                alert_id=r.get("alert_id"),
                agent_name=r.get("agent_name"),
                status=r.get("status"),
                tools_used=r.get("tools_used"),
                started_at=r.get("started_at"),
                completed_at=r.get("completed_at"),
                duration_ms=dm_i,
                evidence_count=ec_i,
                recommendation_count=rc_i,
                output_summary=r.get("output_summary"),
                error=r.get("error"),
            )
        )
    return out


def build_agent_runs_summary(rows: list[dict[str, Any]]) -> AgentRunsSummaryResponse:
    by_agent: dict[str, int] = defaultdict(int)
    by_status: dict[str, int] = defaultdict(int)
    dur_sum: dict[str, float] = defaultdict(float)
    dur_cnt: dict[str, int] = defaultdict(int)
    run_latest: dict[str, str] = {}

    for r in rows:
        agent = str(r.get("agent_name") or "unknown")
        status = str(r.get("status") or "unknown")
        by_agent[agent] += 1
        by_status[status] += 1
        try:
            dm = int(float(r.get("duration_ms") or 0))
        except (TypeError, ValueError):
            dm = 0
        if dm > 0:
            dur_sum[agent] += dm
            dur_cnt[agent] += 1
        rid = r.get("run_id")
        ts = r.get("timestamp") or r.get("started_at") or ""
        if rid:
            if rid not in run_latest or str(ts) > str(run_latest[rid]):
                run_latest[str(rid)] = str(ts)

    recent = sorted(run_latest.keys(), key=lambda k: run_latest[k], reverse=True)[:20]

    return AgentRunsSummaryResponse(
        count_by_agent=[
            AgentRunCountByAgent(agent_name=k, count=v)
            for k, v in sorted(by_agent.items(), key=lambda x: -x[1])
        ],
        count_by_status=[
            AgentRunCountByStatus(status=k, count=v)
            for k, v in sorted(by_status.items(), key=lambda x: -x[1])
        ],
        avg_duration_by_agent=[
            AgentRunAvgDuration(agent_name=k, avg_duration_ms=round(dur_sum[k] / dur_cnt[k], 1))
            for k in sorted(dur_sum.keys())
            if dur_cnt[k] > 0
        ],
        recent_run_ids=recent,
    )
