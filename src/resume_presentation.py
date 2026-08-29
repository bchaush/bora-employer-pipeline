"""Deterministic runtime assembler combining already-proven presentation
transforms into one renderer-ready résumé presentation view.

This is NOT a renderer, NOT an exporter, and stores no new truth. It
answers exactly one question: given an already-built derivative (from
`resume_validation.build_resume_derivative`) and the existing Experience
source data, what structured résumé content is currently eligible to be
presented? It composes the two already-closed pure transforms
(`build_employment_section_view()`, `build_project_section_view()`)
without duplicating their filtering, ordering, or identity-resolution
logic, and adds only the small amount of new composition logic those
transforms do not already cover: deriving the effective selected+ordered
module set, and reconciling contact/education/skills/summary.

Selected-module-order decision (documented; no ARCHITECTURE_DECISION_REQUIRED
was needed): `included_module_ids` is the only field guaranteed to be
complete -- a module cannot be selected without being in it, and
`INCLUDE_MODULE` always appends new ids to it (`resume_patch_apply.py`).
`module_order` (adjusted only by the explicit `REORDER_MODULES` op) is
*not* guaranteed complete: a real derivative built with only
`INCLUDE_MODULE` operations (the pattern used throughout this
repository's own MarketMind-selection tests) leaves `module_order`
containing only the original `default_module_order` ids, never the
newly included ones. Silently using `module_order` alone would
therefore silently drop legitimately selected modules -- unacceptable.
The precedence used here is: iterate `module_order` first (kept for
modules explicitly resequenced via `REORDER_MODULES`), filtered to
`included_module_ids`; then append any remaining `included_module_ids`
not already covered, in their own list order. This is complete (nothing
selected is ever dropped), deterministic, and uses only existing fields
in their existing documented semantics -- no schema change, no new
stored field.

This ordered/selected module list is used only for the two composition
concerns that need it: (a) supplying `build_project_section_view()` an
already-selected, already-ordered sequence (project bullets have no
per-group order field analogous to `bullet_module_ids`, unlike
employment sections), and (b) resolving the optional summary module. It
is NOT used for employment bullet order -- that remains governed solely
by each section's own `bullet_module_ids`, exactly as the closed
`build_employment_section_view()` already decided; passing this
top-level order into that function would silently reintroduce the very
ambiguity its own design decision closed off, so it is deliberately not
given to it.

Section-order decision: no existing field or validator establishes an
authoritative order among résumé sections (Contact / Education /
Employment / Projects / Skills / Summary) -- `default_module_order` and
`module_order` order individual modules, never top-level sections, and
no such field exists anywhere in the schemas. Inventing a visually
opinionated section order here would be exactly the kind of
presentation/layout decision this milestone is not authorized to make
(that belongs to a future renderer). The output is therefore a flat,
named-key object, not an ordered list of sections -- deterministic (the
same input always produces the same key set and values) without
asserting a reading order.

Education/summary presence decision: a key is present only when there
is verified content to show; it is omitted, never emitted as an empty
placeholder or a fabricated value, when nothing is currently
selected/verified. This single rule is applied uniformly to both
`education` (currently always empty in the real master -- no Evidence-
backed education record exists yet) and `summary` (no `SUMMARY` module
currently exists in the real master), so the contract does not need two
different conventions for the same underlying situation ("nothing
verified to present").
"""

from __future__ import annotations

from typing import Any, Mapping

from resume_experience_section import build_employment_section_view
from resume_project_bullet import build_project_section_view

SUMMARY_MODULE_TYPE = "SUMMARY"
PROJECT_MODULE_TYPE = "PROJECT_BULLET"


def _error(code: str, **fields: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {"code": code}
    payload.update(fields)
    return payload


def _effective_selected_module_ids(derivative: Mapping[str, Any]) -> list[str]:
    """Return the effective selected module id order (see module docstring)."""
    included = list(derivative.get("included_module_ids") or [])
    included_set = set(included)
    module_order = list(derivative.get("module_order") or [])

    ordered: list[str] = []
    seen: set[str] = set()
    for module_id in module_order:
        if module_id in included_set and module_id not in seen:
            ordered.append(module_id)
            seen.add(module_id)
    for module_id in included:
        if module_id not in seen:
            ordered.append(module_id)
            seen.add(module_id)
    return ordered


def build_resume_presentation_view(
    derivative: Mapping[str, Any],
    *,
    experience_index: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Assemble a pure, derived, renderer-ready presentation view.

    Input: an already-built derivative (as returned by
    `resume_validation.build_resume_derivative`) and the trusted
    `experience_index` needed by `build_project_section_view()` for
    project display-identity resolution. No other source is consulted;
    this function does not read files or global repository state.

    Selected-module derivation: see the module docstring for the exact,
    documented precedence rule (`module_order` first, then any
    remaining `included_module_ids` in their own order).

    Composition:
    * Employment sections come exclusively from
      `build_employment_section_view(derivative["experience_sections"],
      derivative["modules"], included_module_ids=derivative["included_module_ids"])`
      -- unmodified, no duplicated filtering/ordering/title logic.
    * Project sections come exclusively from
      `build_project_section_view(selected_project_modules,
      experience_index=experience_index)`, where `selected_project_modules`
      is the effective selected/ordered module list filtered to
      `module_type == "PROJECT_BULLET"` -- unmodified, no duplicated
      grouping/identity logic.
    * `contact` is copied verbatim from `derivative["contact"]` -- never
      transformed or invented.
    * `education` is copied verbatim from `derivative["education"]` only
      when it is a non-empty list; otherwise the key is omitted (see
      module docstring).
    * `skills` is copied verbatim from `derivative["skills_order"]`.
    * `summary` is included only when `derivative["summary_module_id"]`
      resolves to a real module that is `module_type == "SUMMARY"` AND
      is present in the effective selected module set (a summary module
      id that was set via `INCLUDE_SUMMARY` but never actually included
      -- or was since excluded -- must not silently render, exactly the
      same reconciliation principle the closed employment view applies
      to `bullet_module_ids`). When present, its value is
      `{"module_id", "wording"}`, matching the bullet shape used
      elsewhere; otherwise the key is omitted.

    Fail-closed contract: if the employment sub-view or the project
    sub-view is invalid, the whole result is invalid
    (`valid: False`, `presentation: None`), with both sub-views' errors
    accumulated into `errors`. No partial presentation is ever returned.

    Returns `{"valid": bool, "presentation": dict | None, "errors": [...]}`.
    """
    errors: list[dict[str, Any]] = []

    experience_sections = derivative.get("experience_sections") or []
    modules = list(derivative.get("modules") or [])
    included_module_ids = derivative.get("included_module_ids") or []

    employment_view = build_employment_section_view(
        experience_sections, modules, included_module_ids=included_module_ids
    )
    if not employment_view["valid"]:
        errors.append(
            _error(
                "EMPLOYMENT_VIEW_INVALID",
                detail="employment section view failed to resolve",
                sub_errors=employment_view["errors"],
            )
        )

    module_by_id: dict[str, Mapping[str, Any]] = {}
    for module in modules:
        if not isinstance(module, Mapping):
            continue
        module_id = module.get("module_id")
        if isinstance(module_id, str) and module_id:
            module_by_id[module_id] = module

    selected_ids = _effective_selected_module_ids(derivative)
    selected_project_modules = [
        module_by_id[module_id]
        for module_id in selected_ids
        if module_id in module_by_id
        and module_by_id[module_id].get("module_type") == PROJECT_MODULE_TYPE
    ]

    project_view = build_project_section_view(
        selected_project_modules, experience_index=experience_index
    )
    if not project_view["valid"]:
        errors.append(
            _error(
                "PROJECT_VIEW_INVALID",
                detail="project section view failed to resolve",
                sub_errors=project_view["errors"],
            )
        )

    if errors:
        return {"valid": False, "presentation": None, "errors": errors}

    presentation: dict[str, Any] = {
        "contact": derivative.get("contact"),
        "employment_sections": employment_view["sections"],
        "project_sections": project_view["groups"],
        "skills": list(derivative.get("skills_order") or []),
    }

    education = derivative.get("education")
    if isinstance(education, list) and education:
        presentation["education"] = education

    summary_module_id = derivative.get("summary_module_id")
    if isinstance(summary_module_id, str) and summary_module_id:
        summary_module = module_by_id.get(summary_module_id)
        if (
            summary_module is not None
            and summary_module.get("module_type") == SUMMARY_MODULE_TYPE
            and summary_module_id in selected_ids
        ):
            presentation["summary"] = {
                "module_id": summary_module_id,
                "wording": summary_module.get("wording"),
            }

    return {"valid": True, "presentation": presentation, "errors": []}
