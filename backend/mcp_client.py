"""Splunk MCP Server JSON-RPC client (HTTP streamable transport)."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import requests

from config import Settings

logger = logging.getLogger(__name__)


class McpClientError(Exception):
    """MCP request or tool call failed."""


class McpClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._id = 0

    def configured(self) -> bool:
        return bool(self._token())

    def _token(self) -> str:
        if self.settings.splunk_mcp_token.strip():
            return self.settings.splunk_mcp_token.strip()
        path = Path(self.settings.splunk_mcp_token_file).expanduser()
        if path.is_file():
            return path.read_text(encoding="utf-8").strip()
        return ""

    def _next_id(self) -> int:
        self._id += 1
        return self._id

    def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        if not self.configured():
            raise McpClientError(
                "Splunk MCP token not configured. Set SPLUNK_MCP_TOKEN or SPLUNK_MCP_TOKEN_FILE."
            )

        payload = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "tools/call",
            "params": {"name": name, "arguments": arguments},
        }
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "Authorization": f"Bearer {self._token()}",
        }
        url = self.settings.splunk_mcp_url.rstrip("/")

        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=120)
        except requests.RequestException as exc:
            raise McpClientError(f"MCP HTTP request failed: {exc}") from exc

        if resp.status_code >= 400:
            raise McpClientError(f"MCP HTTP {resp.status_code}: {resp.text[:500]}")

        try:
            data = resp.json()
        except json.JSONDecodeError as exc:
            raise McpClientError(f"MCP returned non-JSON: {resp.text[:300]}") from exc

        if "error" in data:
            err = data["error"]
            msg = err.get("message", err) if isinstance(err, dict) else str(err)
            raise McpClientError(f"MCP error: {msg}")

        result = data.get("result") or {}
        if result.get("isError"):
            text = _extract_text_content(result)
            raise McpClientError(text or "MCP tool returned an error")

        return _parse_tool_result(result)


def _extract_text_content(result: dict[str, Any]) -> str:
    parts: list[str] = []
    for block in result.get("content") or []:
        if isinstance(block, dict) and block.get("type") == "text":
            parts.append(str(block.get("text", "")))
    return "\n".join(parts).strip()


def _parse_tool_result(result: dict[str, Any]) -> Any:
    text = _extract_text_content(result)
    if not text:
        return result
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text
