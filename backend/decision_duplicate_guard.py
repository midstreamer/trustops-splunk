"""In-memory guard against duplicate decision submissions (same client_decision_id)."""

from __future__ import annotations

_submitted_client_ids: set[str] = set()


def register_client_decision_id(client_decision_id: str) -> bool:
    """
    Register a client-side decision id for this backend process.

    Returns True if newly registered, False if already submitted.
    """
    cid = (client_decision_id or "").strip()
    if not cid:
        return True
    if cid in _submitted_client_ids:
        return False
    _submitted_client_ids.add(cid)
    return True
