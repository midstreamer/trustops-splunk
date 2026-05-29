"""Splunk AI Assistant (SAIA) via Splunk REST /predict (v1), optional MCP, local fallback."""

from __future__ import annotations

import re
from typing import Any

from config import Settings
from mcp_client import McpClient, McpClientError
from saia_rest_client import SaiaRestClient, SaiaRestError
from splunk_client import spl_auth_events_spl

_SAIA_CHAT_HISTORY = "[]"


def _saia_tool_args(base: dict[str, Any]) -> dict[str, Any]:
    """Splunk cloud SAIA often expects chat_history even when optional in MCP schema."""
    args = dict(base)
    args.setdefault("chat_history", _SAIA_CHAT_HISTORY)
    return args


def _try_saia_rest(
    settings: Settings,
    *,
    mode: str,
    spl: str | None = None,
    prompt: str | None = None,
    additional_context: str | None = None,
) -> tuple[str | None, str | None]:
    """Call SAIA through v1 /predict (Search UI path)."""
    try:
        client = SaiaRestClient(settings)
        if not client.configured():
            return None, "Splunk credentials not configured"
        if mode == "explain" and spl is not None:
            return client.explain_spl(spl, additional_context), None
        if mode == "generate" and prompt is not None:
            return client.generate_spl(prompt, additional_context), None
        return None, "invalid SAIA REST request"
    except SaiaRestError as exc:
        return None, str(exc)


def _try_saia_mcp(settings: Settings, tool: str, args: dict[str, Any]) -> tuple[str | None, str | None]:
    """Call SAIA via MCP. Returns (response_text, error_detail)."""
    try:
        client = McpClient(settings)
        if not client.configured():
            return None, "MCP token not configured"
        raw = client.call_tool(tool, _saia_tool_args(args))
        text = _format_saia_response(raw)
        if text and not _looks_like_saia_error(text):
            return text, None
        return None, text or "empty SAIA response"
    except McpClientError as exc:
        return None, str(exc)


def explain_spl(settings: Settings, spl: str, additional_context: str | None = None) -> tuple[str, str]:
    """
    Explain SPL in natural language.

    Returns (explanation_text, source) where source is ``saia`` or ``fallback``.
    """
    spl = spl.strip()
    if not spl:
        raise ValueError("SPL query is required")

    saia_err: str | None = None
    text, saia_err = _try_saia_rest(
        settings,
        mode="explain",
        spl=spl[:5000],
        additional_context=additional_context[:2000] if additional_context else None,
    )
    if text:
        return text, "saia"

    if settings.saia_use_mcp:
        args: dict[str, Any] = {"spl": spl[:5000]}
        if additional_context:
            args["additional_context"] = additional_context[:2000]
        text, saia_err = _try_saia_mcp(settings, "saia_explain_spl", args)
        if text:
            return text, "saia"

    return _fallback_explain_spl(spl, saia_err), "fallback"


def generate_spl(
    settings: Settings,
    prompt: str,
    *,
    alert_id: str | None = None,
    spl_only: bool = False,
    additional_context: str | None = None,
) -> tuple[str, str, str | None]:
    """
    Generate SPL from natural language.

    Returns (display_text, source, generated_spl_or_none).
    """
    prompt = prompt.strip()
    if not prompt:
        raise ValueError("Prompt is required")

    saia_err: str | None = None
    text, saia_err = _try_saia_rest(
        settings,
        mode="generate",
        prompt=prompt[:1000],
        additional_context=additional_context[:2000] if additional_context else None,
    )
    if text:
        extracted = _extract_spl_from_text(text) if not spl_only else text.strip()
        return text, "saia", extracted

    if settings.saia_use_mcp:
        args = {"prompt": prompt[:1000], "spl_only": spl_only}
        if additional_context:
            args["additional_context"] = additional_context[:2000]
        text, saia_err = _try_saia_mcp(settings, "saia_generate_spl", args)
        if text:
            extracted = _extract_spl_from_text(text) if not spl_only else text.strip()
            return text, "saia", extracted

    spl = _fallback_generate_spl(settings, prompt, alert_id)
    if spl_only:
        return _saia_fallback_prefix(saia_err) + spl, "fallback", spl
    explanation = (
        _saia_fallback_prefix(saia_err)
        + "This query follows TrustOps index and field conventions for the selected alert.\n\n"
        f"{spl}"
    )
    return explanation, "fallback", spl


def _looks_like_saia_error(text: str) -> bool:
    lower = text.lower()
    return (
        "referenced before assignment" in lower
        or lower.startswith('{"error"')
        or '"error"' in lower
        or "client error" in lower
        or "400 " in text
        or "splunk ai assistant" in lower and "not" in lower
    )


def _saia_fallback_prefix(saia_err: str | None) -> str:
    if not saia_err:
        return "Generated locally (Splunk AI Assistant unavailable). "
    if "400" in saia_err:
        return (
            "SAIA v2/MCP returned HTTP 400 (use REST /predict or Search UI). "
            "Summary:\n\n"
        )
    return f"Splunk AI Assistant call failed ({saia_err[:200]}). Using local fallback:\n\n"


def _format_saia_response(raw: Any) -> str:
    if raw is None:
        return ""
    if isinstance(raw, str):
        return raw.strip()
    if isinstance(raw, dict):
        if "error" in raw:
            return str(raw["error"])
        for key in ("explanation", "spl", "response", "text", "answer", "result"):
            if key in raw and raw[key]:
                return str(raw[key]).strip()
        return str(raw)
    return str(raw).strip()


def _extract_spl_from_text(text: str) -> str | None:
    """Pull SPL from fenced code blocks or lines starting with search/index."""
    fence = re.search(r"```(?:spl)?\s*\n([\s\S]*?)```", text, re.IGNORECASE)
    if fence:
        return fence.group(1).strip()
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.lower().startswith(("search ", "index=", "| ")):
            return stripped
    if text.strip().lower().startswith("search "):
        return text.strip()
    return None


def _spl_pipeline_stages(spl: str) -> list[str]:
    """Split multiline SPL into ordered pipeline stages."""
    stages: list[str] = []
    for line in spl.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("|"):
            stages.append(line[1:].strip())
        elif line.lower().startswith("search ") and not stages:
            stages.append(line)
    return stages


def _describe_spl_stage(stage: str) -> str | None:
    lower = stage.lower()
    if lower.startswith("search "):
        idx = re.search(r"index=(\S+)", stage, re.I)
        st = re.search(r'sourcetype="([^"]+)"', stage, re.I)
        bits = ["Search events"]
        if idx:
            bits.append(f"in index `{idx.group(1)}`")
        if st:
            bits.append(f"with sourcetype `{st.group(1)}`")
        return " ".join(bits) + "."
    if "eval _is_header" in lower:
        return "Flags ingested CSV header rows so they can be filtered out."
    if re.search(r"where\s+_is_header\s*=\s*0", lower):
        return "Removes the synthetic CSV header row from results."
    if lower.startswith("fields "):
        return "Drops helper fields used only during parsing."
    if "rex field=_raw" in lower:
        return "Extracts structured fields from CSV-shaped `_raw` (user, src_ip, geo, action, alert_id, etc.)."
    if lower.startswith("where alert_id="):
        return "Keeps only events for this investigation alert id."
    if "strptime" in lower:
        return "Converts the CSV timestamp field into Splunk `_time` for timeline charts."
    if lower.startswith("sort "):
        return "Sorts events chronologically."
    if lower.startswith("table "):
        return "Projects a concise table for the analyst UI."
    if lower.startswith("head ") or lower.startswith("tail "):
        return f"Limits how many rows are returned ({stage.strip()})."
    return None


def _fallback_explain_spl(spl: str, saia_err: str | None = None) -> str:
    stages = _spl_pipeline_stages(spl)
    if not stages:
        return "Empty SPL query."

    parts: list[str] = []
    seen: set[str] = set()
    for stage in stages:
        desc = _describe_spl_stage(stage)
        if not desc:
            desc = f"Processing step: `{stage[:120]}{'…' if len(stage) > 120 else ''}`"
        if desc in seen:
            continue
        seen.add(desc)
        parts.append(desc)

    header = _saia_fallback_prefix(saia_err).strip() or (
        "Local SPL explanation (Splunk AI Assistant unavailable)."
    )
    return header + "\n\n" + "\n".join(f"- {p}" for p in parts)


def _fallback_generate_spl(settings: Settings, prompt: str, alert_id: str | None) -> str:
    auth_index = settings.splunk_auth_index
    lower = prompt.lower()

    if alert_id:
        return spl_auth_events_spl(alert_id, auth_index)

    user_match = re.search(r"\buser\s+([a-zA-Z0-9._-]+)", prompt, re.I)
    user = user_match.group(1) if user_match else "jsmith"
    geo_match = re.search(r"\b(?:from|in)\s+([A-Za-z][A-Za-z ]+)", prompt)
    geo_filter = ""
    if geo_match and "romania" in lower:
        geo_filter = '| where geo_country="Romania"'
    elif geo_match:
        country = geo_match.group(1).strip().title()
        geo_filter = f'| where geo_country="{country}"'

    action_filter = ""
    if "fail" in lower:
        action_filter = '| where action="failure"'
    elif "success" in lower:
        action_filter = '| where action="success"'

    stages = [
        f'search index={auth_index} sourcetype="trustops:auth"',
        '| eval _is_header=if(match(_raw,"^timestamp,user,"),1,0)',
        "| where _is_header=0",
        "| fields - _is_header",
        '| rex field=_raw "^(?<timestamp>[^,]+),(?<user>[^,]+),(?<src_ip>[^,]+),(?<dest_host>[^,]+),(?<action>[^,]+),(?<geo_country>[^,]+),(?<auth_method>[^,]+),(?<risk_score>\\d+),(?<event_type>[^,]+),(?<alert_id>[^,]*),(?<scenario>[^,\\r\\n]+)"',
        f'| where user="{user}"',
        action_filter,
        geo_filter,
        '| eval _time=strptime(timestamp, "%Y-%m-%dT%H:%M:%SZ")',
        "| sort _time",
        "| table _time user src_ip geo_country action auth_method risk_score alert_id",
    ]
    return "\n".join(s for s in stages if s)
