"""Optional MITRE ATT&CK enrichment from local Enterprise STIX data."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_ATTACK_PATH = _REPO_ROOT / "data" / "enterprise-attack.json"

_enricher: "_AttackEnricher | None" = None
_enricher_failed: bool = False


def _attack_data_path() -> Path:
    override = os.environ.get("ATTACK_STIX_PATH", "").strip()
    if override:
        p = Path(override)
        return p if p.is_absolute() else _REPO_ROOT / p
    return _DEFAULT_ATTACK_PATH


def _slug_to_tactic(phase_name: str) -> str:
    return phase_name.replace("-", " ").title()


def _obj_get(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _external_refs(obj: Any) -> list[Any]:
    refs = _obj_get(obj, "external_references") or []
    return list(refs)


def _mitre_url(obj: Any) -> str | None:
    for ref in _external_refs(obj):
        source = _obj_get(ref, "source_name")
        url = _obj_get(ref, "url")
        if source == "mitre-attack" and url:
            return str(url)
    return None


def _phase_names(obj: Any) -> list[str]:
    phases = _obj_get(obj, "kill_chain_phases") or []
    names: list[str] = []
    for phase in phases:
        kc = _obj_get(phase, "kill_chain_name")
        pn = _obj_get(phase, "phase_name")
        if kc == "mitre-attack" and pn:
            names.append(str(pn))
    return names


class _AttackEnricher:
    """Wraps mitreattack-python MitreAttackData for technique lookups."""

    def __init__(self, stix_path: Path) -> None:
        from mitreattack.stix20 import MitreAttackData  # type: ignore[import-untyped]

        if not stix_path.is_file():
            raise FileNotFoundError(f"ATT&CK STIX file not found: {stix_path}")
        self._data = MitreAttackData(str(stix_path))

    def enrich(self, technique_id: str, fallback_tactic: str = "") -> dict[str, Any] | None:
        obj = self._data.get_object_by_attack_id(technique_id, "attack-pattern")
        if not obj:
            return None

        tactic = ""
        fallback_slug = fallback_tactic.lower().replace(" ", "-")
        for phase in _phase_names(obj):
            if fallback_slug and phase == fallback_slug:
                tactic = _slug_to_tactic(phase)
                break
        if not tactic:
            try:
                tactics = self._data.get_tactics_by_technique(_obj_get(obj, "id"))
                if tactics:
                    tactic = str(_obj_get(tactics[0], "name") or "")
            except Exception:  # noqa: BLE001
                pass
        if not tactic:
            phases = _phase_names(obj)
            if phases:
                tactic = _slug_to_tactic(phases[0])

        platforms = _obj_get(obj, "x_mitre_platforms")
        detection = _obj_get(obj, "x_mitre_detection")
        description = _obj_get(obj, "description")

        return {
            "technique_id": technique_id,
            "technique": str(_obj_get(obj, "name") or technique_id),
            "tactic": tactic,
            "description": str(description)[:4000] if description else None,
            "detection": str(detection)[:2000] if detection else None,
            "platforms": list(platforms) if platforms else None,
            "data_sources": None,
            "url": _mitre_url(obj),
            "validated": True,
            "enrichment_source": "mitreattack-python",
            "note": None,
        }


def get_attack_enricher() -> _AttackEnricher | None:
    """Return cached enricher, or None if package/data unavailable."""
    global _enricher, _enricher_failed
    if _enricher_failed:
        return None
    if _enricher is not None:
        return _enricher
    try:
        _enricher = _AttackEnricher(_attack_data_path())
        return _enricher
    except Exception as exc:  # noqa: BLE001
        _enricher_failed = True
        logger.debug("ATT&CK enricher unavailable: %s", exc)
        return None


def enrich_technique(
    technique_id: str,
    fallback_name: str = "",
    fallback_tactic: str = "",
    fallback_rationale: str = "",
) -> dict[str, Any]:
    """Enrich one technique; always returns a dict preserving local fallbacks."""
    base: dict[str, Any] = {
        "technique_id": technique_id,
        "technique": fallback_name or technique_id,
        "tactic": fallback_tactic,
        "rationale": fallback_rationale,
        "description": None,
        "detection": None,
        "platforms": None,
        "data_sources": None,
        "url": None,
        "validated": False,
        "enrichment_source": "local_fallback",
        "note": None,
    }

    try:
        from mitreattack.stix20 import MitreAttackData  # noqa: F401
    except ImportError:
        base["note"] = "mitreattack-python not installed; using fallback mapping."
        return base

    if not _attack_data_path().is_file():
        base["note"] = "ATT&CK STIX data not available; using fallback mapping."
        return base

    enricher = get_attack_enricher()
    if not enricher:
        base["note"] = "ATT&CK STIX data not available; using fallback mapping."
        return base

    enriched = enricher.enrich(technique_id, fallback_tactic=fallback_tactic)
    if not enriched:
        base["note"] = f"No ATT&CK object found for {technique_id}; using fallback mapping."
        return base

    base.update(enriched)
    base["rationale"] = fallback_rationale
    if not base.get("tactic"):
        base["tactic"] = fallback_tactic
    return base


def enrich_mappings(mappings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Enrich a list of local mapping dicts; preserve tactic/technique/rationale on fallback."""
    result: list[dict[str, Any]] = []
    for m in mappings:
        enriched = enrich_technique(
            str(m.get("technique_id", "")),
            fallback_name=str(m.get("technique", "")),
            fallback_tactic=str(m.get("tactic", "")),
            fallback_rationale=str(m.get("rationale", "")),
        )
        out = {**m, **enriched}
        out["rationale"] = m.get("rationale", out.get("rationale", ""))
        if not out.get("technique"):
            out["technique"] = m.get("technique", "")
        if not out.get("tactic"):
            out["tactic"] = m.get("tactic", "")
        result.append(out)
    return result
