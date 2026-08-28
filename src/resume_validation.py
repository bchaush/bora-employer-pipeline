"""Unified deterministic résumé architecture validation gate."""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any, Mapping

from resume_diff import compute_resume_diff
from resume_digest import compute_derivative_validation_digest
from resume_lineage import validate_resume_module_lineage
from resume_patch_apply import (
    apply_resume_patch,
    reject_forbidden_patch_extension,
    validate_immutable_fields_preserved,
)
from resume_protected_metadata import validate_protected_metadata_resolved
from resume_semantic import (
    patch_contains_terminology_substitute,
    validate_module_wording_semantics,
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


def validate_master_module_ids_unique(master: Mapping[str, Any]) -> dict[str, Any]:
    """Fail closed when master modules reuse the same module_id."""
    errors: list[dict[str, Any]] = []
    seen: dict[str, int] = {}
    modules = master.get("modules")
    if not isinstance(modules, list):
        return {"valid": True, "errors": errors}

    for index, module in enumerate(modules):
        if not isinstance(module, Mapping):
            continue
        module_id = module.get("module_id")
        if not isinstance(module_id, str) or not module_id:
            continue
        if module_id in seen:
            errors.append(
                _error(
                    "DUPLICATE_MODULE_ID",
                    module_id=module_id,
                    first_index=seen[module_id],
                    duplicate_index=index,
                )
            )
        else:
            seen[module_id] = index

    return {"valid": len(errors) == 0, "errors": errors}


def _visible_modules(derivative_state: Mapping[str, Any]) -> list[dict[str, Any]]:
    included = set(derivative_state.get("included_module_ids", []))
    visible: list[dict[str, Any]] = []
    for module in derivative_state.get("modules", []):
        if isinstance(module, Mapping) and module.get("module_id") in included:
            visible.append(dict(module))
    return visible


def validate_resume_module_factual(
    module: Mapping[str, Any],
    *,
    claim_index: Mapping[str, Any],
    evidence_index: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate schema, lineage, and semantic boundaries (not style)."""
    errors = _schema_validate(MODULE_SCHEMA, module)
    lineage = validate_resume_module_lineage(
        module, claim_index=claim_index, evidence_index=evidence_index
    )
    if not lineage["valid"]:
        errors.extend(lineage["errors"])
    semantics = validate_module_wording_semantics(
        module, claim_index=claim_index, evidence_index=evidence_index
    )
    if not semantics["valid"]:
        errors.extend(semantics["errors"])
    return {
        "valid": len(errors) == 0,
        "module_id": module.get("module_id"),
        "errors": errors,
    }


def validate_resume_module(
    module: Mapping[str, Any],
    *,
    claim_index: Mapping[str, Any],
    evidence_index: Mapping[str, Any],
) -> dict[str, Any]:
    factual = validate_resume_module_factual(
        module, claim_index=claim_index, evidence_index=evidence_index
    )
    style = validate_resume_prose_style(
        str(module.get("wording") or ""),
        context=str(module.get("module_id")),
    )
    style_warnings = list(style.get("warnings", []))
    return {
        "valid": factual["valid"] and style["valid"],
        "factual_valid": factual["valid"],
        "style_valid": style["valid"],
        "module_id": module.get("module_id"),
        "errors": factual["errors"],
        "style_warnings": style_warnings,
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

    unique_modules = validate_master_module_ids_unique(master)
    if not unique_modules["valid"]:
        errors.extend(unique_modules["errors"])

    modules = master.get("modules")
    if isinstance(modules, list):
        for module in modules:
            if isinstance(module, Mapping):
                result = validate_resume_module_factual(
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


def validate_derivative_eligibility(
    derivative: Mapping[str, Any],
    *,
    master: Mapping[str, Any],
    claim_index: Mapping[str, Any],
    evidence_index: Mapping[str, Any],
    require_validation_digest: bool = True,
    for_export: bool = False,
) -> dict[str, Any]:
    """Re-validate a derivative against master and trusted indexes."""
    errors = _schema_validate(DERIVATIVE_SCHEMA, derivative)

    if derivative.get("master_id") != master.get("master_id"):
        errors.append(
            _error(
                "DERIVATIVE_MASTER_MISMATCH",
                master_id=derivative.get("master_id"),
                expected_master_id=master.get("master_id"),
            )
        )

    if require_validation_digest:
        stored_digest = derivative.get("validation_digest")
        if not isinstance(stored_digest, str) or not stored_digest:
            errors.append(
                _error(
                    "DERIVATIVE_VALIDATION_DIGEST_MISSING",
                    detail="derivative must carry a build-time validation digest",
                )
            )
        else:
            current_digest = compute_derivative_validation_digest(derivative)
            if stored_digest != current_digest:
                errors.append(
                    _error(
                        "DERIVATIVE_MUTATED_AFTER_VALIDATION",
                        detail="derivative content no longer matches validated digest",
                    )
                )

    immutable = validate_immutable_fields_preserved(master, derivative)
    if not immutable["valid"]:
        errors.extend(immutable["errors"])

    visible_modules = [
        module
        for module in derivative.get("modules", [])
        if isinstance(module, Mapping)
        and module.get("module_id") in derivative.get("included_module_ids", [])
    ]
    for module in visible_modules:
        factual = validate_resume_module_factual(
            module, claim_index=claim_index, evidence_index=evidence_index
        )
        if not factual["valid"]:
            errors.extend(factual["errors"])

    style = validate_modules_style(list(visible_modules))
    style_warnings = style.get("warnings", [])
    if style_warnings:
        errors.append(
            _error(
                "RESUME_STYLE_VIOLATION",
                detail="style violations block export eligibility",
                style_codes=[
                    warning.get("code")
                    for warning in style_warnings
                    if warning.get("code")
                ],
            )
        )

    review_status = derivative.get("review_status")
    if for_export and review_status == "NEEDS_SEMANTIC_REVIEW":
        errors.append(
            _error(
                "SEMANTIC_REVIEW_UNRESOLVED",
                detail="terminology substitution requires semantic review clearance",
            )
        )

    if for_export:
        protected_metadata = validate_protected_metadata_resolved(derivative)
        if not protected_metadata["valid"]:
            errors.extend(protected_metadata["errors"])

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "style_warnings": style_warnings,
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

    visible_modules = _visible_modules(derivative_state)
    for module in visible_modules:
        factual = validate_resume_module_factual(
            module, claim_index=claim_index, evidence_index=evidence_index
        )
        if not factual["valid"]:
            errors.extend(factual["errors"])

    style = validate_modules_style(list(visible_modules))
    style_warnings = style.get("warnings", [])

    if errors:
        return {"valid": False, "errors": errors}

    review_status = (
        "NEEDS_SEMANTIC_REVIEW"
        if patch_contains_terminology_substitute(patch)
        else "HUMAN_REVIEW_REQUIRED"
    )

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
        "review_status": review_status,
        "export_allowed": False,
        "style_warnings": [w.get("code") for w in style_warnings if w.get("code")],
    }
    derivative["validation_digest"] = compute_derivative_validation_digest(derivative)

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


def complete_semantic_review(
    *,
    derivative: Mapping[str, Any],
    master: Mapping[str, Any],
    claim_index: Mapping[str, Any],
    evidence_index: Mapping[str, Any],
) -> dict[str, Any]:
    """Clear NEEDS_SEMANTIC_REVIEW after human semantic review of wording changes."""
    if derivative.get("review_status") != "NEEDS_SEMANTIC_REVIEW":
        return {
            "valid": False,
            "errors": [
                _error(
                    "SEMANTIC_REVIEW_NOT_REQUIRED",
                    review_status=derivative.get("review_status"),
                )
            ],
        }

    eligibility = validate_derivative_eligibility(
        derivative,
        master=master,
        claim_index=claim_index,
        evidence_index=evidence_index,
        for_export=False,
    )
    if not eligibility["valid"]:
        return {"valid": False, "errors": eligibility["errors"]}

    updated = copy.deepcopy(dict(derivative))
    updated["review_status"] = "HUMAN_REVIEW_REQUIRED"
    schema_errors = _schema_validate(DERIVATIVE_SCHEMA, updated)
    if schema_errors:
        return {"valid": False, "errors": schema_errors}

    return {"valid": True, "derivative": updated, "errors": []}


def approve_derivative_for_export(
    *,
    derivative: Mapping[str, Any],
    master: Mapping[str, Any],
    claim_index: Mapping[str, Any],
    evidence_index: Mapping[str, Any],
    human_approval: bool = False,
) -> dict[str, Any]:
    """Explicit human export approval after full eligibility re-validation."""
    if human_approval is not True:
        return {
            "valid": False,
            "errors": [
                _error(
                    "HUMAN_APPROVAL_REQUIRED",
                    detail="export approval requires explicit human_approval=true",
                )
            ],
        }

    if derivative.get("review_status") != "HUMAN_REVIEW_REQUIRED":
        return {
            "valid": False,
            "errors": [
                _error(
                    "DERIVATIVE_NOT_READY_FOR_EXPORT_APPROVAL",
                    review_status=derivative.get("review_status"),
                )
            ],
        }

    if derivative.get("export_allowed") is True:
        return {
            "valid": False,
            "errors": [
                _error(
                    "DERIVATIVE_ALREADY_EXPORT_APPROVED",
                    detail="export approval is idempotent only through review workflow",
                )
            ],
        }

    eligibility = validate_derivative_eligibility(
        derivative,
        master=master,
        claim_index=claim_index,
        evidence_index=evidence_index,
        for_export=True,
    )
    if not eligibility["valid"]:
        return {"valid": False, "errors": eligibility["errors"]}

    updated = copy.deepcopy(dict(derivative))
    updated["review_status"] = "APPROVED_FOR_EXPORT"
    updated["export_allowed"] = True
    schema_errors = _schema_validate(DERIVATIVE_SCHEMA, updated)
    if schema_errors:
        return {"valid": False, "errors": schema_errors}

    return {
        "valid": True,
        "derivative": updated,
        "errors": [],
    }
