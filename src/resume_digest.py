"""Deterministic validation digest for résumé derivatives."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping


def compute_derivative_validation_digest(derivative: Mapping[str, Any]) -> str:
    """Hash the validated résumé content surface for mutation detection."""
    payload = {
        "master_id": derivative.get("master_id"),
        "master_version": derivative.get("master_version"),
        "patch_id": derivative.get("patch_id"),
        "module_order": derivative.get("module_order"),
        "included_module_ids": derivative.get("included_module_ids"),
        "excluded_module_ids": derivative.get("excluded_module_ids"),
        "skills_order": derivative.get("skills_order"),
        "summary_module_id": derivative.get("summary_module_id"),
        "modules": derivative.get("modules"),
        "experience_sections": derivative.get("experience_sections"),
        "contact": derivative.get("contact"),
        "education": derivative.get("education"),
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
