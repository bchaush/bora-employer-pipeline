"""Compute inspectable résumé derivative diffs."""

from __future__ import annotations

from typing import Any, Mapping


def compute_resume_diff(
    master: Mapping[str, Any],
    derivative: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Return Blueprint-aligned diff entries between master default and derivative."""
    diff: list[dict[str, Any]] = []

    master_order = list(master.get("default_module_order", []))
    deriv_order = list(derivative.get("module_order", []))
    if master_order != deriv_order:
        diff.append(
            {
                "change_type": "REORDERED",
                "target": "module_order",
                "before": ", ".join(master_order),
                "after": ", ".join(deriv_order),
                "detail": "module order changed",
            }
        )

    master_skills = list(master.get("skills_order", []))
    deriv_skills = list(derivative.get("skills_order", []))
    if master_skills != deriv_skills:
        diff.append(
            {
                "change_type": "REORDERED",
                "target": "skills_order",
                "before": ", ".join(master_skills),
                "after": ", ".join(deriv_skills),
                "detail": "skills reordered",
            }
        )

    included = set(derivative.get("included_module_ids", []))
    excluded = set(derivative.get("excluded_module_ids", []))
    default_set = set(master.get("default_module_order", []))

    for module_id in sorted(excluded):
        if module_id in default_set:
            diff.append(
                {
                    "change_type": "REMOVED",
                    "target": module_id,
                    "detail": "module excluded by patch",
                }
            )

    for module_id in sorted(included - default_set):
        diff.append(
            {
                "change_type": "ADDED",
                "target": module_id,
                "detail": "module included by patch",
            }
        )

    master_summary = master.get("summary_module_id")
    deriv_summary = derivative.get("summary_module_id")
    if master_summary != deriv_summary:
        diff.append(
            {
                "change_type": "REWORDED" if deriv_summary else "REMOVED",
                "target": "summary",
                "before": str(master_summary),
                "after": str(deriv_summary),
                "detail": "summary selection changed",
            }
        )

    master_modules = {
        m.get("module_id"): m.get("wording")
        for m in (master.get("modules") or [])
        if isinstance(m, Mapping)
    }
    deriv_modules = {
        m.get("module_id"): m.get("wording")
        for m in (derivative.get("modules") or [])
        if isinstance(m, Mapping)
    }
    for module_id, master_wording in master_modules.items():
        deriv_wording = deriv_modules.get(module_id)
        if deriv_wording is None:
            continue
        if deriv_wording != master_wording:
            diff.append(
                {
                    "change_type": "REWORDED",
                    "target": module_id,
                    "before": str(master_wording),
                    "after": str(deriv_wording),
                    "detail": "wording changed on derivative",
                }
            )
        elif module_id not in excluded and module_id in included:
            diff.append(
                {
                    "change_type": "UNCHANGED",
                    "target": module_id,
                    "detail": "wording unchanged",
                }
            )

    if not diff:
        diff.append(
            {
                "change_type": "UNCHANGED",
                "target": "derivative",
                "detail": "no material changes detected",
            }
        )

    return diff
