"""Splunk search and connectivity via splunklib (SDK) + requests for raw receiver."""

from __future__ import annotations

import logging
from typing import Any
import requests
import splunklib.client as client
import splunklib.results as results

from config import Settings, get_settings

logger = logging.getLogger(__name__)

# Allowed characters for alert_id embedded in SPL (defense-in-depth; API also validates).
_ALERT_ID_SAFE = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-")
_RUN_ID_SAFE = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-")


def validate_run_id_for_spl(run_id: str) -> str:
    if not run_id or len(run_id) > 64 or not set(run_id).issubset(_RUN_ID_SAFE):
        raise ValueError("Invalid run_id for Splunk query")
    return run_id


def validate_alert_id_for_spl(alert_id: str) -> str:
    if not alert_id or len(alert_id) > 128 or not set(alert_id).issubset(_ALERT_ID_SAFE):
        raise ValueError("Invalid alert_id for Splunk query")
    return alert_id


def spl_auth_events_spl(alert_id: str, auth_index: str) -> str:
    """SPL for auth timeline tied to an alert_id (matches Phase 1 synthetic CSV in _raw)."""
    aid = validate_alert_id_for_spl(alert_id)
    # aid is safe for double-quoted SPL string
    return "\n".join(
        [
            f'search index={auth_index} sourcetype="trustops:auth"',
            '| eval _is_header=if(match(_raw,"^timestamp,user,"),1,0)',
            "| where _is_header=0",
            "| fields - _is_header",
            '| rex field=_raw "^(?<timestamp>[^,]+),(?<user>[^,]+),(?<src_ip>[^,]+),(?<dest_host>[^,]+),(?<action>[^,]+),(?<geo_country>[^,]+),(?<auth_method>[^,]+),(?<risk_score>\\d+),(?<event_type>[^,]+),(?<alert_id>[^,]*),(?<scenario>[^,\\r\\n]+)"',
            f'| where alert_id="{aid}"',
            "| eval _time=strptime(timestamp, \"%Y-%m-%dT%H:%M:%SZ\")",
            "| sort _time",
            "| table _time user src_ip dest_host action geo_country auth_method risk_score event_type alert_id scenario",
        ]
    )


def _decision_field_evals() -> str:
    """Parse decision _raw by column index (legacy 13-field and extended 19-field rows)."""
    return "\n".join(
        [
            '| eval _cols=split(_raw,",")',
            "| eval _nf=mvcount(_cols)",
            "| eval timestamp=mvindex(_cols,0)",
            "| eval alert_id=mvindex(_cols,1)",
            "| eval analyst=mvindex(_cols,2)",
            "| eval ai_recommendation=mvindex(_cols,3)",
            "| eval analyst_decision=mvindex(_cols,4)",
            "| eval final_severity=mvindex(_cols,5)",
            "| eval confidence_score=mvindex(_cols,6)",
            "| eval trust_score=mvindex(_cols,7)",
            "| eval time_to_decision_seconds=mvindex(_cols,8)",
            "| eval ai_recommendation_status=mvindex(_cols,9)",
            "| eval evidence_reviewed_count=mvindex(_cols,10)",
            "| eval sop_followed=mvindex(_cols,11)",
            '| eval notes=if(_nf>12,mvindex(_cols,12),"")',
            '| eval evidence_checklist=if(_nf>13,mvindex(_cols,13),"")',
            '| eval supporting_evidence=if(_nf>14,mvindex(_cols,14),"")',
            '| eval contradicting_evidence=if(_nf>15,mvindex(_cols,15),"")',
            '| eval automation_bias_risk_score=if(_nf>16,mvindex(_cols,16),"")',
            '| eval automation_bias_risk_level=if(_nf>17,mvindex(_cols,17),"")',
            '| eval feedback_message=if(_nf>18,mvindex(_cols,18),"")',
            '| eval learning_point=if(_nf>19,mvindex(_cols,19),"")',
            '| eval client_decision_id=if(_nf>20,mvindex(_cols,20),"")',
            '| eval agent_plan_viewed=if(_nf>21,mvindex(_cols,21),"")',
            '| eval follow_up_queries_viewed=if(_nf>22,mvindex(_cols,22),"")',
            '| eval contradictory_evidence_viewed=if(_nf>23,mvindex(_cols,23),"")',
            "| fields - _cols _nf",
        ]
    )


def spl_decisions_for_alert_spl(alert_id: str, decision_index: str) -> str:
    aid = validate_alert_id_for_spl(alert_id)
    return "\n".join(
        [
            f'search index={decision_index} sourcetype="trustops:decision"',
            '| eval _is_header=if(match(_raw,"^timestamp,alert_id,analyst,"),1,0)',
            "| where _is_header=0",
            "| fields - _is_header",
            _decision_field_evals(),
            f'| where alert_id="{aid}"',
            "| sort timestamp",
            "| table timestamp alert_id analyst ai_recommendation analyst_decision final_severity "
            "confidence_score trust_score time_to_decision_seconds ai_recommendation_status "
            "evidence_reviewed_count sop_followed notes evidence_checklist supporting_evidence "
            "contradicting_evidence automation_bias_risk_score automation_bias_risk_level",
        ]
    )


def spl_decisions_summary_spl(decision_index: str) -> str:
    return "\n".join(
        [
            f'search index={decision_index} sourcetype="trustops:decision"',
            '| eval _is_header=if(match(_raw,"^timestamp,alert_id,analyst,"),1,0)',
            "| where _is_header=0",
            "| fields - _is_header",
            _decision_field_evals(),
            "| eval confidence_score=tonumber(confidence_score)",
            "| eval trust_score=tonumber(trust_score)",
            "| eval time_to_decision_seconds=tonumber(time_to_decision_seconds)",
            "| eval automation_bias_risk_score=tonumber(automation_bias_risk_score)",
            "| stats count as decision_count avg(confidence_score) as avg_confidence "
            "avg(trust_score) as avg_trust avg(time_to_decision_seconds) as avg_time_to_decision "
            "avg(automation_bias_risk_score) as avg_automation_bias_risk_score "
            "by ai_recommendation_status",
            "| sort ai_recommendation_status",
        ]
    )


class SplunkClient:
    """Thin wrapper around splunklib + requests for one-shot searches and event submission."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def connect_service(self) -> client.Service:
        if not self.settings.splunk_credentials_configured():
            raise RuntimeError("Splunk credentials are not configured (SPLUNK_USER / SPLUNK_PASSWORD).")
        return client.connect(
            host=self.settings.splunk_host,
            port=self.settings.splunk_port,
            scheme=self.settings.splunk_scheme,
            username=self.settings.splunk_user,
            password=self.settings.effective_splunk_password(),
            verify=self.settings.splunk_verify_ssl,
            autologin=True,
        )

    def ping(self) -> bool:
        """Lightweight connectivity check."""
        try:
            svc = self.connect_service()
            svc.info()  # type: ignore[no-untyped-call]
            return True
        except Exception as exc:  # noqa: BLE001 — demo: log and return False
            logger.warning("Splunk ping failed: %s", exc)
            return False

    def run_oneshot_json(self, spl: str) -> list[dict[str, Any]]:
        svc = self.connect_service()
        stream = svc.jobs.oneshot(spl, output_mode="json")
        rows: list[dict[str, Any]] = []
        reader = results.JSONResultsReader(stream)
        for item in reader:
            if isinstance(item, dict):
                rows.append(dict(item))
        return rows

    def submit_raw_event(
        self,
        raw_line: str,
        *,
        index: str | None = None,
        sourcetype: str | None = None,
    ) -> None:
        """POST a single raw event to receivers/simple."""
        if not self.settings.splunk_credentials_configured():
            raise RuntimeError("Splunk credentials are not configured.")
        url = f"{self.settings.splunk_base_url()}/services/receivers/simple"
        params = {
            "index": index or self.settings.splunk_decision_index,
            "sourcetype": sourcetype or "trustops:decision",
            "host": self.settings.splunk_event_host,
        }
        # Splunk expects raw body; URL-encode is not applied to the body content.
        resp = requests.post(
            url,
            params=params,
            data=raw_line,
            auth=(self.settings.splunk_user, self.settings.effective_splunk_password()),
            verify=self.settings.splunk_verify_ssl,
            timeout=30,
        )
        if resp.status_code >= 400:
            raise RuntimeError(f"Splunk receiver error HTTP {resp.status_code}: {resp.text[:500]}")


def _agent_step_spath_evals() -> str:
    """Extract JSON fields from agent step _raw."""
    fields = (
        "timestamp",
        "run_id",
        "alert_id",
        "agent_name",
        "status",
        "tools_used",
        "started_at",
        "completed_at",
        "duration_ms",
        "evidence_count",
        "recommendation_count",
        "output_summary",
        "error",
    )
    return "\n".join(f"| spath input=_raw path={f} output={f}" for f in fields)


def spl_agent_steps_for_run_spl(run_id: str, agent_index: str) -> str:
    rid = validate_run_id_for_spl(run_id)
    return "\n".join(
        [
            f'search index={agent_index} sourcetype="trustops:agent_step"',
            _agent_step_spath_evals(),
            f'| search run_id="{rid}"',
            "| eval duration_ms=tonumber(duration_ms)",
            "| eval evidence_count=tonumber(evidence_count)",
            "| eval recommendation_count=tonumber(recommendation_count)",
            "| sort started_at",
            "| table timestamp run_id alert_id agent_name status tools_used started_at completed_at "
            "duration_ms evidence_count recommendation_count output_summary error",
        ]
    )


def spl_agent_steps_recent_spl(agent_index: str, limit: int = 500) -> str:
    lim = max(50, min(limit, 2000))
    return "\n".join(
        [
            f'search index={agent_index} sourcetype="trustops:agent_step"',
            _agent_step_spath_evals(),
            "| eval duration_ms=tonumber(duration_ms)",
            f"| head {lim}",
            "| table timestamp run_id alert_id agent_name status tools_used duration_ms output_summary error",
        ]
    )


def spl_agent_steps_by_alert_spl(alert_id: str, agent_index: str) -> str:
    aid = validate_alert_id_for_spl(alert_id)
    return "\n".join(
        [
            f'search index={agent_index} sourcetype="trustops:agent_step"',
            _agent_step_spath_evals(),
            f'| search alert_id="{aid}"',
            "| eval duration_ms=tonumber(duration_ms)",
            "| sort - timestamp",
            "| table timestamp run_id alert_id agent_name status tools_used duration_ms output_summary",
        ]
    )
