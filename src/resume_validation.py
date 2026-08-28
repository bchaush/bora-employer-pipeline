"""Unified deterministic résumé architecture validation gate."""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any, Mapping

from resume_diff import compute_resume_diff
from resume_lineage import validate_resume_module_lineage
from resume_patch_apply import (
    apply_resume_patch,
    reject_forbidden_patch_extension,
    validate_immutable_fields_preserved,
)
from resume_style import validate_modules_style, validate_resume_prose_style
from schema_validation import build_draft202012_validator


ROOT = Path(__file__).resolve().parents[1]
MODULE_SCHEMA = ROOT / "schemas" / "resume_module.schema.json"
MASTER_SCHEMA = ROOT / "schemas" / "resume_master.schema.json"
PATCH_SCHEMA = ROOT / "schemas" / "resume_patch.schema.json"
DERIVATIVE_SCHEMA = ROOT / "schemas" / "resume_derivative.schema.json"


def _error(code: str, **fields: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {"code": code}
    payload.update(fields)
    return payload


def _schema_validate(schema_path: Path, instance: Any) -> list[dict[str, Any]]:
    validator = build_draft202012_validator(schema_path)
    if validator.is_valid(instance):
        return []
    return [
        _error("RESUME_SCHEMA_INVALID", detail=msg)
        for msg in (e.message for e in validator.iter_errors(instance))
    ]


def validate_resume_module(
    module: Mapping[str, Any],
    *,
    claim_index: Mapping[str, Any],
    evidence_index: Mapping[str, Any],
) -> dict[str, Any]:
    errors = _schema_validate(MODULE_SCHEMA, module)
    lineage = validate_resume_module_lineage(
        module, claim_index=claim_index, evidence_index=evidence_index
    )
    if not lineage["valid"]:
        errors.extend(lineage["errors"])
    style = validate_resume_prose_style(
        str(module.get("wording") or ""),
        context=str(module.get("module_id")),
    )
    if not style["valid"]:
        errors.extend(style["warnings"])
    return {
        "valid": len(errors) == 0,
        "module_id": module.get("module_id"),
        "errors": errors,
    }


def validate_resume_master(
    master: Mapping[str, Any],
    *,
    claim_index: Mapping[str, Any],
    evidence_index: Mapping[str, Any],
) -> dict[str, Any]:
    errors = _schema_validate(MASTER_SCHEMA, master)
    if master.get("protected") is not True:
        errors.append(_error("MASTER_NOT_PROTECTED"))

    modules = master.get("modules")
    if isinstance(modules, list):
        for module in modules:
            if isinstance(module, Mapping):
                result = validate_resume_module(
                    module,
                    claim_index=claim_index,
                    evidence_index=evidence_index,
                )
                if not result["valid"]:
                    errors.extend(result["errors"])

    return {
        "valid": len(errors) == 0,
        "master_id": master.get("master_id"),
        "errors": errors,
    }


def validate_resume_patch(
    patch: Mapping[str, Any],
    *,
    master: Mapping[str, Any],
) -> dict[str, Any]:
    errors = _schema_validate(PATCH_SCHEMA, patch)
    forbidden = reject_forbidden_patch_extension(patch)
    if not forbidden["valid"]:
        errors.extend(forbidden["errors"])
    if patch.get("target_master_id") != master.get("master_id"):
        errors.append(
            _error(
                "PATCH_MASTER_MISMATCH",
                patch_id=patch.get("patch_id"),
                target_master_id=patch.get("target_master_id"),
                master_id=master.get("master_id"),
            )
        )
    return {
        "valid": len(errors) == 0,
        "patch_id": patch.get("patch_id"),
        "errors": errors,
    }


def build_resume_derivative(
    *,
    master: Mapping[str, Any],
    patch: Mapping[str, Any],
    claim_index: Mapping[str, Any],
    evidence_index: Mapping[str, Any],
    derivative_id: str,
) -> dict[str, Any]:
    """Apply patch to master copy, validate lineage/immutability, return derivative package."""
    errors: list[dict[str, Any]] = []

    master_validation = validate_resume_master(
        master, claim_index=claim_index, evidence_index=evidence_index
    )
    if not master_validation["valid"]:
        errors.extend(master_validation["errors"])

    patch_validation = validate_resume_patch(patch, master=master)
    if not patch_validation["valid"]:
        errors.extend(patch_validation["errors"])

    if errors:
        return {"valid": False, "errors": errors}

    applied = apply_resume_patch(master, patch)
    if not applied["valid"]:
        return {"valid": False, "errors": applied["errors"]}

    derivative_state = applied["derivative"]
    immutable = validate_immutable_fields_preserved(master, derivative_state)
    if not immutable["valid"]:
        errors.extend(immutable["errors"])

    visible_modules = [
        m
        for m in derivative_state.get("modules", [])
        if isinstance(m, Mapping)
        and m.get("module_id") in derivative_state.get("included_module_ids", [])
    ]
    for module in visible_modules:
        result = validate_resume_module(
            module, claim_index=claim_index, evidence_index=evidence_index
        )
        if not result["valid"]:
            errors.extend(result["errors"])

    style = validate_modules_style(list(visible_modules))
    style_warnings = style.get("warnings", [])

    diff = compute_resume_diff(master, derivative_state)

    derivative = {
        "derivative_id": derivative_id,
        "master_id": master.get("master_id"),
        "master_version": master.get("version"),
        "patch_id": patch.get("patch_id"),
        "job_id": patch.get("job_id"),
        "module_order": derivative_state.get("module_order", []),
        "included_module_ids": derivative_state.get("included_module_ids", []),
        "excluded_module_ids": derivative_state.get("excluded_module_ids", []),
        "summary_module_id": derivative_state.get("summary_module_id"),
        "skills_order": derivative_state.get("skills_order", []),
        "modules": derivative_state.get("modules", []),
        "experience_sections": derivative_state.get("experience_sections", []),
        "contact": derivative_state.get("contact"),
        "education": derivative_state.get("education", []),
        "diff": diff,
        "review_status": "HUMAN_REVIEW_REQUIRED",
        "export_allowed": False,
        "style_warnings": [w.get("code") for w in style_warnings if w.get("code")],
    }

    errors.extend(_schema_validate(DERIVATIVE_SCHEMA, derivative))
    if errors:
        return {"valid": False, "errors": errors}

    return {
        "valid": True,
        "derivative": derivative,
        "errors": [],
        "style_warnings": style_warnings,
    }


def master_unchanged_after_derivative_build(
    master_before: Mapping[str, Any],
    master_after: Mapping[str, Any],
) -> bool:
    """True when derivative workflow did not mutate the protected master."""
    return master_before == master_after


def approve_derivative_for_export(
    derivative: Mapping[str, Any],
) -> dict[str, Any]:
    """Human review gate placeholder. No auto-export."""
    updated = copy.deepcopy(dict(derivative))
    updated["review_status"] = "APPROVED_FOR_EXPORT"
    updated["export_allowed"] = True
    errors = _schema_validate(DERIVATIVE_SCHEMA, updated)
    return {
        "valid": len(errors) == 0,
        "derivative": updated,
        "errors": errors,
    }
