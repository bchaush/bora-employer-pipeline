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
PROJECT_EXPERIENCE_TYPE = "PERSONAL_PROJECT"


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


def build_project_section_view(
    modules: Sequence[Mapping[str, Any]],
    *,
    experience_index: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Build a pure, derived project-section presentation view.

    Not a renderer and not a schema: this stores no new truth. It only
    reshapes already-selected modules (e.g. a derivative's included
    modules) into project groups for a future renderer to consume.

    Input: `modules` is a sequence of already-selected module objects
    (any module_type; non-PROJECT_BULLET entries are ignored). Duplicate
    module_ids are not deduplicated here — master-level uniqueness
    (`validate_master_module_ids_unique`) and `INCLUDE_MODULE`'s own
    not-already-included check already prevent duplicates from reaching
    this function in practice; if a caller passes one anyway, it is
    preserved in place (not silently dropped), matching the existing
    fail-closed-elsewhere-not-here division of responsibility.

    Grouping: strictly by each module's own `experience_id`. Groups are
    emitted in first-occurrence order; within a group, bullets preserve
    the exact order they appeared in the input `modules` sequence
    (never alphabetized or reordered by module ID, Evidence, Claim, or
    Experience metadata).

    Display identity: resolved only via `resolve_project_display_name()`,
    which reads only `Experience.experience_name`. Additionally, the
    resolved Experience record's own `experience_type` must equal
    `PERSONAL_PROJECT` — a PROJECT_BULLET module whose `experience_id`
    resolves to a non-project Experience (e.g. an ORGANIZATIONAL_ENGAGEMENT
    like Winter Walk) is treated as unresolved, not silently grouped
    under that Experience's identity. This does not modify
    `resolve_project_display_name()` itself; it is an additional guard
    applied here, since nothing upstream currently guarantees that a
    future PROJECT_BULLET module's `experience_id` points at a
    PERSONAL_PROJECT-typed Experience.

    Any unresolved group (missing/unknown experience_id, missing/empty
    experience_name, or a non-PERSONAL_PROJECT Experience type) produces
    a deterministic `PROJECT_DISPLAY_NAME_UNRESOLVED` error — it never
    guesses, never falls back to "Personal Project"/"Untitled
    Project"/module wording, and never silently drops the group.

    Fail-closed contract: if ANY group fails to resolve, the whole view
    is invalid. `valid: False` always means `groups: []` — there is no
    partial result. A caller (or future renderer) that forgets to check
    `valid` and reads `groups` directly still gets nothing renderable
    rather than an incomplete project section. `errors` is always fully
    populated with every discovered problem regardless of `valid`, so
    callers that DO check `valid` can still see exactly what failed.

    Returns `{"valid": bool, "groups": [...], "errors": [...]}`. When
    `valid` is `True`, each group is `{"experience_id": str,
    "display_name": str, "bullets": [{"module_id": str, "wording": str},
    ...]}` — no date, location, formal_title,
    employer/organization/client/sponsor, url, technology_line, or
    subtitle field is ever included, even if the source module happens
    to carry one; only `module_id` and `wording` are copied out of each
    module. When `valid` is `False`, `groups` is always `[]`.
    """
    errors: list[dict[str, Any]] = []
    order: list[str] = []
    grouped: dict[str, list[Mapping[str, Any]]] = {}

    for module in modules:
        if not isinstance(module, Mapping):
            continue
        if module.get("module_type") != PROJECT_MODULE_TYPE:
            continue
        experience_id = module.get("experience_id")
        key = experience_id if isinstance(experience_id, str) and experience_id else ""
        if key not in grouped:
            grouped[key] = []
            order.append(key)
        grouped[key].append(module)

    groups: list[dict[str, Any]] = []
    for key in order:
        group_modules = grouped[key]
        first_module = group_modules[0]

        record = experience_index.get(key) if (key and experience_index) else None
        experience_type = record.get("experience_type") if isinstance(record, Mapping) else None
        display_name = resolve_project_display_name(first_module, experience_index=experience_index)

        if not key or display_name is None or experience_type != PROJECT_EXPERIENCE_TYPE:
            errors.append(
                _error(
                    "PROJECT_DISPLAY_NAME_UNRESOLVED",
                    experience_id=first_module.get("experience_id"),
                    module_ids=[m.get("module_id") for m in group_modules],
                    detail=(
                        "could not resolve a verified project display identity "
                        "(missing/unknown experience_id, missing experience_name, "
                        "or a non-PERSONAL_PROJECT Experience type); refusing to guess"
                    ),
                )
            )
            continue

        groups.append(
            {
                "experience_id": key,
                "display_name": display_name,
                "bullets": [
                    {"module_id": m.get("module_id"), "wording": m.get("wording")}
                    for m in group_modules
                ],
            }
        )

    valid = len(errors) == 0
    return {"valid": valid, "groups": groups if valid else [], "errors": errors}
