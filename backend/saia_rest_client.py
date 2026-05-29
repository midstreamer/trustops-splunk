"""Splunk AI Assistant via v1 /predict (same path as Search UI on Enterprise 10.2.x).

SAIA v2 oneshot endpoints (explainspl, generatespl) and MCP saia_* tools call
saia-api-v2/v2alpha1/spl/* which returns HTTP 400 on many CMP stacks. The legacy
/predict flow with classification codes still works.
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any

import requests

from config import Settings

logger = logging.getLogger(__name__)

_SAIA_APP = "Splunk_AI_Assistant_Cloud"
# 0=write, 1=explain (matches generation_handler / Search UI)
_CLASS_WRITE = 0
_CLASS_EXPLAIN = 1
_THREAD_WRITE = "write"
_THREAD_EXPLAIN = "explain"
# loadingState: 0=loading, 1=streaming, 2=complete, 3=error, 4=stopped
_LOADING_COMPLETE = 2
_LOADING_ERROR = 3


class SaiaRestError(Exception):
    pass


class SaiaRestClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._session = requests.Session()
        self._session.auth = (
            settings.splunk_user.strip(),
            settings.effective_splunk_password(),
        )
        self._session.verify = settings.splunk_verify_ssl
        self._session.headers.update(
            {
                "Content-Type": "application/json",
                "Source-App-ID": settings.saia_source_app_id,
            }
        )
        self._base = (
            f"{settings.splunk_base_url()}/servicesNS/nobody/{_SAIA_APP}"
        )

    def configured(self) -> bool:
        return self.settings.splunk_credentials_configured()

    def explain_spl(self, spl: str, additional_context: str | None = None) -> str:
        prompt = _explain_prompt(spl)
        if additional_context:
            prompt = f"{prompt}\n\nAdditional context:\n{additional_context.strip()}"
        return self._predict_and_wait(prompt, _CLASS_EXPLAIN, _THREAD_EXPLAIN)

    def generate_spl(self, prompt: str, additional_context: str | None = None) -> str:
        user_prompt = prompt.strip()
        if additional_context:
            user_prompt = f"{user_prompt}\n\nAdditional context:\n{additional_context.strip()}"
        return self._predict_and_wait(user_prompt, _CLASS_WRITE, _THREAD_WRITE)

    def answer_question(self, prompt: str) -> str:
        """Investigation Q&A (explain thread) — not SPL generation."""
        return self._predict_and_wait(
            prompt.strip(),
            _CLASS_EXPLAIN,
            _THREAD_EXPLAIN,
            timeout_seconds=self.settings.saia_chat_timeout_seconds,
        )

    def _predict_and_wait(
        self,
        prompt: str,
        classification: int,
        thread_key: str,
        *,
        timeout_seconds: float | None = None,
    ) -> str:
        chat_id = str(uuid.uuid4())
        job_id = self._start_predict(chat_id, prompt, classification)
        return self._poll_chat_response(
            chat_id,
            job_id,
            thread_key,
            timeout_seconds=timeout_seconds,
        )

    def _start_predict(self, chat_id: str, prompt: str, classification: int) -> str:
        url = f"{self._base}/predict"
        payload = {
            "prompt": prompt,
            "classification": classification,
            "chat_id": chat_id,
        }
        try:
            resp = self._session.post(url, json=payload, timeout=60)
        except requests.RequestException as exc:
            raise SaiaRestError(f"SAIA predict request failed: {exc}") from exc

        if resp.status_code != 200:
            raise SaiaRestError(
                f"SAIA predict returned HTTP {resp.status_code}: {resp.text[:500]}"
            )

        data = resp.json()
        if "error" in data:
            raise SaiaRestError(str(data["error"]))
        job_id = data.get("job_id") or data.get("response_id")
        if not job_id:
            raise SaiaRestError(f"SAIA predict missing job_id: {data}")
        return str(job_id)

    def _poll_chat_response(
        self,
        chat_id: str,
        job_id: str,
        thread_key: str,
        *,
        timeout_seconds: float | None = None,
    ) -> str:
        limit = timeout_seconds if timeout_seconds is not None else self.settings.saia_predict_timeout_seconds
        deadline = time.monotonic() + limit
        interval = self.settings.saia_predict_poll_interval_seconds
        url = f"{self._base}/chathistory/{chat_id}"
        last_content = ""
        stable_reads = 0

        while time.monotonic() < deadline:
            try:
                resp = self._session.get(
                    url,
                    params={"output_mode": "json"},
                    timeout=30,
                )
            except requests.RequestException as exc:
                raise SaiaRestError(f"SAIA chathistory poll failed: {exc}") from exc

            if resp.status_code != 200:
                raise SaiaRestError(
                    f"SAIA chathistory returned HTTP {resp.status_code}: {resp.text[:300]}"
                )

            entry = _assistant_entry(resp.json(), thread_key, job_id)
            if entry is None:
                time.sleep(interval)
                continue

            state = entry.get("loadingState")
            content = (entry.get("content") or "").strip()
            if state == _LOADING_ERROR:
                meta = entry.get("metadata") or {}
                raise SaiaRestError(
                    str(meta.get("error") or content or "SAIA generation failed")
                )
            if state == _LOADING_COMPLETE and content:
                return content
            if content and content == last_content:
                stable_reads += 1
            else:
                stable_reads = 0
                last_content = content
            # Streaming may stay at state 1; accept stable full-looking text
            if content and stable_reads >= 2 and len(content) > 80:
                return content
            time.sleep(interval)

        if last_content:
            return last_content
        raise SaiaRestError("SAIA response timed out waiting for completion")


def _explain_prompt(spl: str) -> str:
    return f"Explain this SPL query in detail:\n\n```spl\n{spl.strip()}\n```"


def _assistant_entry(
    data: dict[str, Any],
    thread_key: str,
    job_id: str,
) -> dict[str, Any] | None:
    history = data.get("chat_history") or data
    records = history.get("records") if isinstance(history, dict) else None
    if not isinstance(records, dict):
        return None
    thread = records.get(thread_key) or []
    for item in reversed(thread):
        if item.get("role") == "assistant" and item.get("id") == job_id:
            return item
    for item in reversed(thread):
        if item.get("role") == "assistant":
            return item
    return None
