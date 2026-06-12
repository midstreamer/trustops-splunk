"""
TrustOps startup / CI smoke tests for Splunk AI Assistant and agentic investigation.

Run manually:
  cd backend && source .venv/bin/activate && python -m smoke_test

Against a running API:
  python -m smoke_test --base-url http://127.0.0.1:8001 --full
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Protocol

logger = logging.getLogger(__name__)

DEFAULT_CANONICAL_ALERT = "TO-VPN-2026-514"
DEFAULT_BASE_URL = "http://127.0.0.1:8001"


@dataclass
class SmokeCheck:
    name: str
    passed: bool
    detail: str = ""


@dataclass
class SmokeTestReport:
    checks: list[SmokeCheck] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return bool(self.checks) and all(c.passed for c in self.checks)

    def add(self, name: str, passed: bool, detail: str = "") -> None:
        self.checks.append(SmokeCheck(name=name, passed=passed, detail=detail))


class HttpClient(Protocol):
    def request(
        self,
        method: str,
        path: str,
        *,
        body: dict[str, Any] | None = None,
        timeout: float = 120.0,
    ) -> tuple[int, dict[str, Any] | list[Any] | None, str]: ...


class UrllibHttpClient:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    def request(
        self,
        method: str,
        path: str,
        *,
        body: dict[str, Any] | None = None,
        timeout: float = 120.0,
    ) -> tuple[int, dict[str, Any] | list[Any] | None, str]:
        url = f"{self.base_url}{path if path.startswith('/') else f'/{path}'}"
        data = None
        headers = {"Accept": "application/json"}
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(url, data=data, headers=headers, method=method.upper())
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read().decode("utf-8")
                status = resp.status
        except urllib.error.HTTPError as exc:
            status = exc.code
            raw = exc.read().decode("utf-8", errors="replace")
        payload: dict[str, Any] | list[Any] | None
        try:
            payload = json.loads(raw) if raw else None
        except json.JSONDecodeError:
            payload = None
        return status, payload, raw


def run_smoke_test(
    client: HttpClient,
    *,
    full: bool = False,
    canonical_alert: str = DEFAULT_CANONICAL_ALERT,
    investigation_timeout: float = 120.0,
    agent_run_timeout: float = 240.0,
) -> SmokeTestReport:
    report = SmokeTestReport()

    status, health, _ = client.request("GET", "/health", timeout=15.0)
    if status != 200 or not isinstance(health, dict):
        report.add("health", False, f"HTTP {status}")
        return report

    splunk_ok = bool(health.get("splunk_configured")) and health.get("splunk_reachable") is True
    report.add(
        "health",
        splunk_ok,
        "Splunk configured and reachable"
        if splunk_ok
        else f"splunk_configured={health.get('splunk_configured')} splunk_reachable={health.get('splunk_reachable')}",
    )
    if not splunk_ok:
        return report

    status, alerts, _ = client.request("GET", "/alerts", timeout=15.0)
    alert_ids: list[str] = []
    if status == 200 and isinstance(alerts, list):
        alert_ids = [str(a.get("alert_id")) for a in alerts if isinstance(a, dict)]
    has_canonical = canonical_alert in alert_ids
    report.add(
        "alerts",
        status == 200 and bool(alert_ids),
        f"{len(alert_ids)} alert(s); canonical present={has_canonical}",
    )

    inv_path = f"/alerts/{canonical_alert}/investigation"
    status, inv, _ = client.request("GET", inv_path, timeout=investigation_timeout)
    inv_source = inv.get("investigation_source") if isinstance(inv, dict) else None
    inv_ok = (
        status == 200
        and isinstance(inv, dict)
        and inv_source == "saia"
        and bool(inv.get("investigation_summary"))
        and bool(inv.get("ai_recommendation"))
    )
    report.add(
        "investigation_saia",
        inv_ok,
        f"source={inv_source!r}, summary={'yes' if isinstance(inv, dict) and inv.get('investigation_summary') else 'no'}",
    )

    explain_body = {
        "spl": f"index=trustops alert_id={canonical_alert} | stats count",
        "additional_context": "TrustOps startup smoke test",
    }
    status, explain, _ = client.request(
        "POST",
        "/saia/explain",
        body=explain_body,
        timeout=90.0,
    )
    explain_source = explain.get("source") if isinstance(explain, dict) else None
    explain_ok = status == 200 and explain_source == "saia" and bool(explain.get("text"))
    report.add(
        "saia_explain",
        explain_ok,
        f"source={explain_source!r}",
    )

    if not full:
        return report

    run_path = f"/alerts/{canonical_alert}/agent-run"
    status, agent_run, _ = client.request(
        "POST",
        run_path,
        timeout=agent_run_timeout,
    )
    steps = agent_run.get("steps") if isinstance(agent_run, dict) else None
    run_status = agent_run.get("status") if isinstance(agent_run, dict) else None
    agent_ok = (
        status == 200
        and isinstance(agent_run, dict)
        and run_status == "complete"
        and isinstance(steps, list)
        and len(steps) == 7
        and all(isinstance(s, dict) and s.get("status") == "complete" for s in steps)
    )
    saia_tools = []
    if isinstance(steps, list):
        for step in steps:
            if not isinstance(step, dict):
                continue
            for tool in step.get("tools_used") or []:
                if "ai_assistant" in str(tool) or tool == "splunk_ai_assistant_context":
                    saia_tools.append(f"{step.get('agent_name')}:{tool}")
    report.add(
        "agentic_run",
        agent_ok,
        f"status={run_status!r}, steps={len(steps) if isinstance(steps, list) else 0}, saia_tools={saia_tools or 'none'}",
    )

    chat_body = {"message": "Summarize the top risk for this alert in one sentence."}
    status, chat, _ = client.request(
        "POST",
        f"/alerts/{canonical_alert}/chat",
        body=chat_body,
        timeout=90.0,
    )
    chat_source = chat.get("source") if isinstance(chat, dict) else None
    chat_ok = (
        status == 200
        and chat_source == "splunk_ai_assistant"
        and bool(chat.get("answer"))
    )
    report.add(
        "alert_chat_saia",
        chat_ok,
        f"source={chat_source!r}",
    )

    return report


def format_report(report: SmokeTestReport) -> str:
    lines = ["=== TrustOps smoke test ==="]
    for check in report.checks:
        mark = "OK" if check.passed else "FAIL"
        suffix = f" — {check.detail}" if check.detail else ""
        lines.append(f"[{mark}] {check.name}{suffix}")
    lines.append("")
    lines.append("PASSED" if report.passed else "FAILED")
    return "\n".join(lines)


def wait_for_health(base_url: str, *, attempts: int = 30, interval: float = 1.0) -> bool:
    client = UrllibHttpClient(base_url)
    for _ in range(attempts):
        try:
            status, health, _ = client.request("GET", "/health", timeout=5.0)
            if status == 200 and isinstance(health, dict):
                return True
        except (urllib.error.URLError, TimeoutError):
            pass
        time.sleep(interval)
    return False


def startup_smoke_mode() -> str | None:
    """Return 'quick', 'full', or None to skip."""
    raw = os.getenv("TRUSTOPS_STARTUP_SMOKE_TEST", "quick").strip().lower()
    if raw in ("0", "false", "no", "off", "skip", "disabled"):
        return None
    if raw == "full":
        return "full"
    return "quick"


def run_startup_smoke(app: Any = None) -> SmokeTestReport:
    del app
    base_url = os.getenv("TRUSTOPS_API_BASE_URL", DEFAULT_BASE_URL)
    canonical = os.getenv("TRUSTOPS_SMOKE_CANONICAL_ALERT", DEFAULT_CANONICAL_ALERT)
    mode = startup_smoke_mode()
    full = mode == "full"
    client = UrllibHttpClient(base_url)
    return run_smoke_test(client, full=full, canonical_alert=canonical)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="TrustOps SAIA + agentic smoke test")
    parser.add_argument(
        "--base-url",
        default=os.getenv("TRUSTOPS_API_BASE_URL", DEFAULT_BASE_URL),
        help="Running API base URL (default: http://127.0.0.1:8001)",
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Also run agentic investigation and alert chat checks",
    )
    parser.add_argument(
        "--wait",
        action="store_true",
        help="Wait for /health before running checks",
    )
    parser.add_argument(
        "--canonical-alert",
        default=os.getenv("TRUSTOPS_SMOKE_CANONICAL_ALERT", DEFAULT_CANONICAL_ALERT),
    )
    args = parser.parse_args(argv)

    if args.wait and not wait_for_health(args.base_url):
        print(f"Timed out waiting for {args.base_url}/health", file=sys.stderr)
        return 1

    client = UrllibHttpClient(args.base_url)
    report = run_smoke_test(
        client,
        full=args.full,
        canonical_alert=args.canonical_alert,
    )
    output = format_report(report)
    print(output)
    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
