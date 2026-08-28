"""Source-vs-display title metadata validation for résumé experience sections."""

from __future__ import annotations

from typing import Any, Mapping

from resume_protected_metadata import UNRESOLVED_PROTECTED_METADATA_SENTINEL


def is_source_formal_title_unresolved(formal_title: Any) -> bool:
    """True when no single source-verbatim formal title is stored."""
    return formal_title == UNRESOLVED_PROTECTED_METADATA_SENTINEL


def has_approved_display_title(section: Mapping[str, Any]) -> bool:
    """True when section carries a human-approved display title binding."""
    display_title = section.get("display_title")
    approval = section.get("display_title_approval")
    if not isinstance(display_title, str) or not display_title:
        return False
    if not isinstance(approval, Mapping):
        return False
    if approval.get("approved") is not True:
        return False
    if approval.get("is_source_verbatim") is not False:
        return False
    return approval.get("approved_display_title") == display_title


def is_experience_title_export_ready(section: Mapping[str, Any]) -> bool:
    """Export may use an approved display title when source formal title is unresolved."""
    formal_title = section.get("formal_title")
    if not is_source_formal_title_unresolved(formal_title):
        return isinstance(formal_title, str) and bool(formal_title)
    return has_approved_display_title(section)


def validate_experience_title_metadata(
    section: Mapping[str, Any],
    *,
    field_prefix: str,
) -> dict[str, Any]:
    """Validate source/display title separation for one experience section."""
    errors: list[dict[str, Any]] = []
    formal_title = section.get("formal_title")
    display_title = section.get("display_title")
    approval = section.get("display_title_approval")

    if display_title is not None or approval is not None:
        if not isinstance(display_title, str) or not display_title:
            errors.append(
                {
                    "code": "DISPLAY_TITLE_REQUIRED",
                    "field": f"{field_prefix}.display_title",
                    "detail": "display_title must be a non-empty string when title metadata is present",
                }
            )
        if not isinstance(approval, Mapping):
            errors.append(
                {
                    "code": "DISPLAY_TITLE_APPROVAL_REQUIRED",
                    "field": f"{field_prefix}.display_title_approval",
                    "detail": "human-approved display title requires display_title_approval metadata",
                }
            )
        elif approval.get("approved") is not True:
            errors.append(
                {
                    "code": "DISPLAY_TITLE_NOT_APPROVED",
                    "field": f"{field_prefix}.display_title_approval.approved",
                    "detail": "display title requires explicit human approval",
                }
            )
        elif approval.get("is_source_verbatim") is not False:
            errors.append(
                {
                    "code": "DISPLAY_TITLE_MARKED_SOURCE_VERBATIM",
                    "field": f"{field_prefix}.display_title_approval.is_source_verbatim",
                    "detail": "display title must not be marked as source-verbatim formal title",
                }
            )
        elif isinstance(display_title, str) and approval.get("approved_display_title") != display_title:
            errors.append(
                {
                    "code": "DISPLAY_TITLE_APPROVAL_MISMATCH",
                    "field": f"{field_prefix}.display_title",
                    "detail": "display_title changed without matching approved_display_title approval binding",
                }
            )

    if (
        isinstance(formal_title, str)
        and isinstance(display_title, str)
        and formal_title == display_title
        and is_source_formal_title_unresolved(formal_title) is False
    ):
        errors.append(
            {
                "code": "SOURCE_FORMAL_TITLE_CONFLATED",
                "field": f"{field_prefix}.formal_title",
                "detail": "formal_title must not be silently replaced by display title wording",
            }
        )

    if (
        isinstance(formal_title, str)
        and isinstance(display_title, str)
        and formal_title == display_title
        and has_approved_display_title(section)
    ):
        errors.append(
            {
                "code": "DISPLAY_TITLE_CONFLATED_WITH_FORMAL_TITLE",
                "field": f"{field_prefix}.display_title",
                "detail": "approved display title must remain distinct from unresolved formal_title sentinel",
            }
        )

    return {"valid": len(errors) == 0, "errors": errors}


def build_experience_section_index(
    sections: Any,
) -> dict[str, Mapping[str, Any]]:
    """Map experience_id to its experience section record."""
    index: dict[str, Mapping[str, Any]] = {}
    if not isinstance(sections, list):
        return index
    for section in sections:
        if not isinstance(section, Mapping):
            continue
        experience_id = section.get("experience_id")
        if isinstance(experience_id, str) and experience_id:
            index[experience_id] = section
    return index


def validate_module_snapshot_title_binding(
    module: Mapping[str, Any],
    section: Mapping[str, Any] | None,
    *,
    field_prefix: str,
) -> dict[str, Any]:
    """Ensure module snapshot title presentation matches section-approved display title."""
    errors: list[dict[str, Any]] = []
    snapshot = module.get("immutable_snapshot")
    if not isinstance(snapshot, Mapping):
        return {"valid": True, "errors": errors}

    formal_title = snapshot.get("formal_title")
    if "formal_title" not in snapshot or not is_source_formal_title_unresolved(formal_title):
        return {"valid": True, "errors": errors}

    experience_id = module.get("experience_id")
    display_title = snapshot.get("display_title")

    if section is None:
        errors.append(
            {
                "code": "MODULE_DISPLAY_TITLE_SECTION_NOT_FOUND",
                "field": f"{field_prefix}.display_title",
                "experience_id": experience_id,
                "detail": (
                    "module immutable_snapshot display title requires a corresponding "
                    "experience section"
                ),
            }
        )
        return {"valid": False, "errors": errors}

    if not is_experience_title_export_ready(section):
        errors.append(
            {
                "code": "MODULE_DISPLAY_TITLE_APPROVAL_UNRESOLVED",
                "field": f"{field_prefix}.display_title",
                "experience_id": section.get("experience_id"),
                "detail": (
                    "module title readiness requires section-level approved display title"
                ),
            }
        )

    if not isinstance(display_title, str) or not display_title:
        errors.append(
            {
                "code": "UNRESOLVED_PROTECTED_METADATA",
                "field": f"{field_prefix}.display_title",
                "value": display_title,
                "detail": (
                    f"protected metadata field {field_prefix}.display_title remains unresolved "
                    f"({UNRESOLVED_PROTECTED_METADATA_SENTINEL!r})"
                ),
            }
        )
        return {"valid": len(errors) == 0, "errors": errors}

    section_display_title = section.get("display_title")
    if display_title != section_display_title:
        errors.append(
            {
                "code": "MODULE_DISPLAY_TITLE_MISMATCH",
                "field": f"{field_prefix}.display_title",
                "module_display_title": display_title,
                "section_display_title": section_display_title,
                "experience_id": section.get("experience_id"),
                "detail": (
                    "module immutable_snapshot display_title must exactly match the "
                    "corresponding experience section display_title"
                ),
            }
        )

    return {"valid": len(errors) == 0, "errors": errors}
