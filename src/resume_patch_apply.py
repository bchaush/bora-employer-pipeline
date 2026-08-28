"""Apply structured résumé patches to a master copy (derivative only)."""

from __future__ import annotations

import copy
from typing import Any, Mapping


def _error(code: str, **fields: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {"code": code}
    payload.update(fields)
    return payload


def _module_index(master: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    modules = master.get("modules")
    if not isinstance(modules, list):
        return {}
    out: dict[str, dict[str, Any]] = {}
    for module in modules:
        if isinstance(module, Mapping):
            mid = module.get("module_id")
            if isinstance(mid, str):
                out[mid] = copy.deepcopy(dict(module))
    return out


def apply_resume_patch(
    master: Mapping[str, Any],
    patch: Mapping[str, Any],
) -> dict[str, Any]:
    """Return a new derivative state dict without mutating master."""
    if master.get("protected") is not True:
        return {
            "valid": False,
            "errors": [
                _error("MASTER_NOT_PROTECTED", detail="master must be protected")
            ],
        }

    derivative = {
        "master_id": master.get("master_id"),
        "master_version": master.get("version"),
        "patch_id": patch.get("patch_id"),
        "job_id": patch.get("job_id"),
        "contact": copy.deepcopy(master.get("contact")),
        "education": copy.deepcopy(master.get("education", [])),
        "experience_sections": copy.deepcopy(master.get("experience_sections", [])),
        "modules": copy.deepcopy(master.get("modules", [])),
        "module_order": list(master.get("default_module_order", [])),
        "included_module_ids": list(master.get("default_module_order", [])),
        "excluded_module_ids": [],
        "summary_module_id": master.get("summary_module_id"),
        "skills_order": list(master.get("skills_order", [])),
    }

    module_by_id = _module_index(master)
    errors: list[dict[str, Any]] = []

    operations = patch.get("operations")
    if not isinstance(operations, list):
        return {
            "valid": False,
            "errors": [_error("MALFORMED_PATCH", detail="operations required")],
        }

    for index, operation in enumerate(operations):
        if not isinstance(operation, Mapping):
            errors.append(_error("MALFORMED_OPERATION", index=index))
            continue
        op = operation.get("op")

        if op == "INCLUDE_MODULE":
            module_id = operation.get("module_id")
            if module_id not in module_by_id:
                errors.append(
                    _error("UNKNOWN_MODULE_ID", module_id=module_id, op=op)
                )
                continue
            if module_id not in derivative["included_module_ids"]:
                derivative["included_module_ids"].append(module_id)
            if module_id in derivative["excluded_module_ids"]:
                derivative["excluded_module_ids"].remove(module_id)

        elif op == "EXCLUDE_MODULE":
            module_id = operation.get("module_id")
            if module_id in derivative["included_module_ids"]:
                derivative["included_module_ids"].remove(module_id)
            if module_id not in derivative["excluded_module_ids"]:
                derivative["excluded_module_ids"].append(module_id)

        elif op == "REORDER_MODULES":
            module_ids = operation.get("module_ids")
            if not isinstance(module_ids, list):
                errors.append(_error("MALFORMED_OPERATION", op=op, index=index))
                continue
            derivative["module_order"] = list(module_ids)

        elif op == "REORDER_BULLETS":
            section_id = operation.get("section_id")
            bullet_ids = operation.get("bullet_module_ids")
            for section in derivative["experience_sections"]:
                if section.get("section_id") == section_id:
                    section["bullet_module_ids"] = list(bullet_ids or [])
                    break

        elif op == "REORDER_SKILLS":
            skills = operation.get("skills")
            if isinstance(skills, list):
                derivative["skills_order"] = list(skills)

        elif op == "INCLUDE_SUMMARY":
            derivative["summary_module_id"] = operation.get("module_id")

        elif op == "EXCLUDE_SUMMARY":
            derivative["summary_module_id"] = None

        elif op == "SELECT_WORDING_VARIANT":
            module_id = operation.get("module_id")
            variant_index = operation.get("variant_index")
            module_found = False
            for module in derivative["modules"]:
                if module.get("module_id") == module_id:
                    module_found = True
                    variants = module.get("approved_wording_variants")
                    if (
                        not isinstance(variants, list)
                        or not isinstance(variant_index, int)
                        or variant_index >= len(variants)
                    ):
                        errors.append(
                            _error(
                                "INVALID_WORDING_VARIANT",
                                module_id=module_id,
                                variant_index=variant_index,
                            )
                        )
                    else:
                        module["wording"] = variants[variant_index]
                    break
            if not module_found:
                errors.append(
                    _error("UNKNOWN_MODULE_ID", module_id=module_id, op=op)
                )

        elif op == "TERMINOLOGY_SUBSTITUTE":
            module_id = operation.get("module_id")
            from_term = str(operation.get("from_term") or "")
            to_term = str(operation.get("to_term") or "")
            module_found = False
            for module in derivative["modules"]:
                if module.get("module_id") == module_id:
                    module_found = True
                    wording = str(module.get("wording") or "")
                    if from_term not in wording:
                        errors.append(
                            _error(
                                "TERMINOLOGY_SUBSTITUTE_NOT_FOUND",
                                module_id=module_id,
                                from_term=from_term,
                            )
                        )
                    else:
                        module["wording"] = wording.replace(from_term, to_term, 1)
                    break
            if not module_found:
                errors.append(
                    _error("UNKNOWN_MODULE_ID", module_id=module_id, op=op)
                )
        else:
            errors.append(_error("UNSUPPORTED_PATCH_OP", op=op, index=index))

    return {"valid": len(errors) == 0, "derivative": derivative, "errors": errors}


def validate_immutable_fields_preserved(
    master: Mapping[str, Any],
    derivative: Mapping[str, Any],
) -> dict[str, Any]:
    """Ensure derivative did not alter protected master history fields."""
    errors: list[dict[str, Any]] = []

    for key in ("contact",):
        if master.get(key) != derivative.get(key):
            errors.append(
                _error("IMMUTABLE_CONTACT_ALTERED", field=key)
            )

    master_sections = {
        s.get("section_id"): s
        for s in (master.get("experience_sections") or [])
        if isinstance(s, Mapping)
    }
    deriv_sections = {
        s.get("section_id"): s
        for s in (derivative.get("experience_sections") or [])
        if isinstance(s, Mapping)
    }
    for section_id, master_section in master_sections.items():
        deriv_section = deriv_sections.get(section_id)
        if not isinstance(deriv_section, Mapping):
            continue
        for field in (
            "organization",
            "formal_title",
            "employment_category",
            "date_range",
            "location",
            "experience_id",
            "source_contractual_position",
            "source_functional_role",
            "display_title",
            "display_title_approval",
        ):
            if master_section.get(field) != deriv_section.get(field):
                errors.append(
                    _error(
                        "IMMUTABLE_EXPERIENCE_FIELD_ALTERED",
                        section_id=section_id,
                        field=field,
                        master_value=master_section.get(field),
                        derivative_value=deriv_section.get(field),
                    )
                )

    master_education = {
        entry.get("education_id"): entry
        for entry in (master.get("education") or [])
        if isinstance(entry, Mapping) and isinstance(entry.get("education_id"), str)
    }
    deriv_education = {
        entry.get("education_id"): entry
        for entry in (derivative.get("education") or [])
        if isinstance(entry, Mapping) and isinstance(entry.get("education_id"), str)
    }
    for education_id, master_entry in master_education.items():
        deriv_entry = deriv_education.get(education_id)
        if not isinstance(deriv_entry, Mapping):
            errors.append(
                _error(
                    "IMMUTABLE_EDUCATION_ENTRY_MISSING",
                    education_id=education_id,
                )
            )
            continue
        for field in ("school_name", "degree_name", "date_range", "location"):
            if master_entry.get(field) != deriv_entry.get(field):
                errors.append(
                    _error(
                        "IMMUTABLE_EDUCATION_FIELD_ALTERED",
                        education_id=education_id,
                        field=field,
                        master_value=master_entry.get(field),
                        derivative_value=deriv_entry.get(field),
                    )
                )

    master_modules = {
        module.get("module_id"): module
        for module in (master.get("modules") or [])
        if isinstance(module, Mapping) and isinstance(module.get("module_id"), str)
    }
    deriv_modules = {
        module.get("module_id"): module
        for module in (derivative.get("modules") or [])
        if isinstance(module, Mapping) and isinstance(module.get("module_id"), str)
    }
    protected_snapshot_fields = (
        "organization",
        "formal_title",
        "display_title",
        "employment_category",
        "date_range",
        "location",
        "degree_name",
        "school_name",
        "approved_metrics",
        "approved_tools",
    )
    for module_id, master_module in master_modules.items():
        master_snapshot = master_module.get("immutable_snapshot")
        if not isinstance(master_snapshot, Mapping):
            continue
        deriv_module = deriv_modules.get(module_id)
        if not isinstance(deriv_module, Mapping):
            errors.append(
                _error("IMMUTABLE_MODULE_MISSING", module_id=module_id)
            )
            continue
        deriv_snapshot = deriv_module.get("immutable_snapshot")
        if not isinstance(deriv_snapshot, Mapping):
            errors.append(
                _error("IMMUTABLE_MODULE_SNAPSHOT_MISSING", module_id=module_id)
            )
            continue
        for field in protected_snapshot_fields:
            if master_snapshot.get(field) != deriv_snapshot.get(field):
                errors.append(
                    _error(
                        "IMMUTABLE_MODULE_SNAPSHOT_ALTERED",
                        module_id=module_id,
                        field=field,
                        master_value=master_snapshot.get(field),
                        derivative_value=deriv_snapshot.get(field),
                    )
                )

    return {"valid": len(errors) == 0, "errors": errors}


def reject_forbidden_patch_extension(patch: Mapping[str, Any]) -> dict[str, Any]:
    """Fail closed on forbidden patch shapes outside the schema (e.g. title/tool/metric)."""
    errors: list[dict[str, Any]] = []
    forbidden_keys = (
        "formal_title",
        "organization",
        "date_range",
        "add_tool",
        "add_metric",
        "immutable_overrides",
        "experience_id",
    )
    operations = patch.get("operations")
    if isinstance(operations, list):
        for index, operation in enumerate(operations):
            if not isinstance(operation, Mapping):
                continue
            for key in forbidden_keys:
                if key in operation:
                    errors.append(
                        _error(
                            "FORBIDDEN_PATCH_FIELD",
                            index=index,
                            field=key,
                            detail="patches cannot alter immutable history or add unsupported facts",
                        )
                    )
            op = operation.get("op")
            if op in {
                "SET_FORMAL_TITLE",
                "SET_EMPLOYER",
                "ADD_TOOL",
                "ADD_METRIC",
                "ALTER_IMMUTABLE",
            }:
                errors.append(
                    _error("FORBIDDEN_PATCH_OP", op=op, index=index)
                )
    return {"valid": len(errors) == 0, "errors": errors}
