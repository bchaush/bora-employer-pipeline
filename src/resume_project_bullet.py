"""Deterministic rendering contract for PROJECT_BULLET résumé modules.

A PROJECT_BULLET module represents a personal-project bullet that is not
tied to a formal employment/experience_sections header. Unlike a BULLET
module (Winter Walk), a PROJECT_BULLET has no verified employer, formal
title, employment dates, or location, and none may be invented for it.

This module defines the smallest safe contract for carrying such modules
through derivative generation:

- What structural data a PROJECT_BULLET module may NOT carry (employment-
  shaped immutable_snapshot fields, experience_sections membership) —
  enforced deterministically so a future addition cannot silently attach
  fabricated employment-style metadata to a project bullet.
- What a future renderer MAY safely resolve for display: only the
  project's own Experience-record `experience_name`, which already exists
  as verified repository data. No date, location, title, or technology
  "display line" is resolved here, because none is currently verified;
  a renderer that needs one of those fields must obtain it through a
  separate, explicit evidence/approval decision, not through this module.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence


PROJECT_MODULE_TYPE = "PROJECT_BULLET"


def _error(code: str, **fields: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {"code": code}
    payload.update(fields)
    return payload


def validate_project_bullet_contract(
    module: Mapping[str, Any],
    *,
    experience_sections: Sequence[Mapping[str, Any]] | None,
) -> dict[str, Any]:
    """Return contract-violation errors for one module.

    Non-PROJECT_BULLET modules are out of scope and always pass.

    Rules for PROJECT_BULLET modules:
    - Must not carry `immutable_snapshot` at all. No verified employer,
      formal title, employment dates, or location exists for a personal
      project with no external title-granting authority, so none may be
      snapshotted, sentinel or otherwise.
    - Must not be referenced by any `experience_sections[].bullet_module_ids`
      list. That grouping is reserved for employment-shaped BULLET modules
      with a real, schema-required organization/formal_title/date_range
      header; a project bullet has none of those and must not be presented
      as if it belonged to one.
    """
    errors: list[dict[str, Any]] = []
    if module.get("module_type") != PROJECT_MODULE_TYPE:
        return {"valid": True, "errors": errors}

    module_id = module.get("module_id")

    if "immutable_snapshot" in module:
        errors.append(
            _error(
                "PROJECT_BULLET_SNAPSHOT_FORBIDDEN",
                module_id=module_id,
                detail=(
                    "PROJECT_BULLET modules must not carry immutable_snapshot; "
                    "no verified employment-shaped data exists for a personal project"
                ),
            )
        )

    for section in experience_sections or []:
        if not isinstance(section, Mapping):
            continue
        bullet_ids = section.get("bullet_module_ids") or []
        if module_id in bullet_ids:
            errors.append(
                _error(
                    "PROJECT_BULLET_IN_EXPERIENCE_SECTION",
                    module_id=module_id,
                    section_id=section.get("section_id"),
                    detail=(
                        "PROJECT_BULLET modules must not be referenced by an "
                        "experience_sections bullet_module_ids list"
                    ),
                )
            )

    return {"valid": len(errors) == 0, "errors": errors}


def resolve_project_display_name(
    module: Mapping[str, Any],
    *,
    experience_index: Mapping[str, Any] | None,
) -> str | None:
    """Resolve the verified project display name for a PROJECT_BULLET module.

    Returns the module's Experience record's own `experience_name` (already-
    verified repository data) or None when the module is not a
    PROJECT_BULLET, its `experience_id` does not resolve, or no name is
    recorded. Never fabricates a value — a renderer must treat None as
    UNKNOWN, not as license to guess.
    """
    if module.get("module_type") != PROJECT_MODULE_TYPE:
        return None
    experience_id = module.get("experience_id")
    if not isinstance(experience_id, str) or not experience_id:
        return None
    record = experience_index.get(experience_id) if experience_index else None
    if not isinstance(record, Mapping):
        return None
    name = record.get("experience_name")
    return name if isinstance(name, str) and name else None
