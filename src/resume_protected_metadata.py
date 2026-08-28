"""Deterministic unresolved protected-metadata checks for résumé export."""

from __future__ import annotations

from typing import Any, Mapping

UNRESOLVED_PROTECTED_METADATA_SENTINEL = "PENDING_BORA_REVIEW"


def is_unresolved_protected_metadata_value(value: Any) -> bool:
    """True when a protected field still carries the repository unresolved sentinel."""
    return value == UNRESOLVED_PROTECTED_METADATA_SENTINEL


def _append_unresolved(
    errors: list[dict[str, Any]],
    *,
    field: str,
    value: Any = UNRESOLVED_PROTECTED_METADATA_SENTINEL,
) -> None:
    errors.append(
        {
            "code": "UNRESOLVED_PROTECTED_METADATA",
            "field": field,
            "value": value,
            "detail": (
                f"protected metadata field {field!r} remains unresolved "
                f"({UNRESOLVED_PROTECTED_METADATA_SENTINEL!r})"
            ),
        }
    )


def _check_required_string(
    errors: list[dict[str, Any]],
    *,
    field: str,
    value: Any,
) -> None:
    if is_unresolved_protected_metadata_value(value):
        _append_unresolved(errors, field=field, value=value)


def _check_optional_string(
    errors: list[dict[str, Any]],
    *,
    field: str,
    value: Any,
) -> None:
    if value is None:
        return
    if is_unresolved_protected_metadata_value(value):
        _append_unresolved(errors, field=field, value=value)


def validate_protected_metadata_resolved(
    derivative: Mapping[str, Any],
) -> dict[str, Any]:
    """Fail closed when export-required protected metadata remains unresolved."""
    errors: list[dict[str, Any]] = []

    contact = derivative.get("contact")
    if isinstance(contact, Mapping):
        _check_required_string(errors, field="contact.name", value=contact.get("name"))
        for optional_field in ("email", "phone", "location", "linkedin"):
            _check_optional_string(
                errors,
                field=f"contact.{optional_field}",
                value=contact.get(optional_field),
            )

    sections = derivative.get("experience_sections")
    if isinstance(sections, list):
        for index, section in enumerate(sections):
            if not isinstance(section, Mapping):
                continue
            prefix = f"experience_sections[{index}]"
            _check_required_string(
                errors, field=f"{prefix}.organization", value=section.get("organization")
            )
            _check_required_string(
                errors, field=f"{prefix}.formal_title", value=section.get("formal_title")
            )
            _check_required_string(
                errors, field=f"{prefix}.date_range", value=section.get("date_range")
            )
            _check_optional_string(
                errors,
                field=f"{prefix}.employment_category",
                value=section.get("employment_category"),
            )
            _check_optional_string(
                errors,
                field=f"{prefix}.location",
                value=section.get("location"),
            )

    education = derivative.get("education")
    if isinstance(education, list):
        for index, entry in enumerate(education):
            if not isinstance(entry, Mapping):
                continue
            prefix = f"education[{index}]"
            _check_required_string(
                errors, field=f"{prefix}.school_name", value=entry.get("school_name")
            )
            _check_required_string(
                errors, field=f"{prefix}.degree_name", value=entry.get("degree_name")
            )
            _check_optional_string(
                errors,
                field=f"{prefix}.date_range",
                value=entry.get("date_range"),
            )
            _check_optional_string(
                errors,
                field=f"{prefix}.location",
                value=entry.get("location"),
            )

    included = set(derivative.get("included_module_ids", []))
    modules = derivative.get("modules")
    if isinstance(modules, list):
        for module in modules:
            if not isinstance(module, Mapping):
                continue
            module_id = module.get("module_id")
            if module_id not in included:
                continue
            snapshot = module.get("immutable_snapshot")
            if not isinstance(snapshot, Mapping):
                continue
            prefix = f"modules[{module_id}].immutable_snapshot"
            for field in ("organization", "formal_title", "date_range"):
                if field in snapshot:
                    _check_required_string(
                        errors,
                        field=f"{prefix}.{field}",
                        value=snapshot.get(field),
                    )
            if "employment_category" in snapshot:
                _check_optional_string(
                    errors,
                    field=f"{prefix}.employment_category",
                    value=snapshot.get("employment_category"),
                )

    return {"valid": len(errors) == 0, "errors": errors}
