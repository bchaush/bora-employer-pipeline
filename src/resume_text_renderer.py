"""Deterministic TEST-ONLY plain-text résumé renderer.

Proves that the pure unified presentation view
(`resume_presentation.build_resume_presentation_view()`) can be safely
converted into a linear, ATS-safe plain-text representation, before any
PDF/DOCX/layout complexity is introduced. This is a TEST-ONLY renderer:
it is not wired into export approval, application generation, PDF/DOCX
generation, Google Drive/Docs, job-specific derivative generation, or
any browser workflow, and produces no artifact suitable for submission.

It renders only fields already present in an already-valid presentation
payload. It never invents, infers, or re-derives content, never
re-filters bullets, never re-resolves titles, and never re-queries
modules -- all of that truth was already established by the closed
employment-section view, the closed project-section view, and the
closed unified presentation assembler. This file adds only linear
text-layout logic: heading selection, section order, and line
formatting.

Section-order decision (documented; no ARCHITECTURE_DECISION_REQUIRED
was needed): no schema, validator, or `.cursor/rules/*.mdc` file
specifies an authoritative order among résumé sections -- confirmed by
inspection, consistent with the closed `UNIFIED_RESUME_PRESENTATION_MODEL_V1`
milestone's own finding and deliberate choice to expose a flat,
unordered structure for exactly this reason. However, two pieces of
real, citable evidence in `BLUEPRINT.md` make a linear order reasonably
derivable rather than an invented layout preference:
  1. Section 2 ("BORA -- PERMANENT SYSTEM CONTEXT") introduces Bora's
     MSBA education before describing Winter Walk, and separately
     describes Winter Walk as his "strongest current organizational
     evidence" before MarketMind AI as "supporting technical/project
     evidence" -- direct textual precedence for
     Education-before-Experience and Experience-before-Projects.
  2. Section 46 ("RÉSUMÉ PATCH -- NOT FREEHAND REWRITE")'s own
     illustrative patch-diff example lists SUMMARY first, then
     per-employer/per-project categories, then SKILLS last.
Combined with the universal, conventional résumé structure this
architecture already commits to elsewhere (`.cursor/rules/resume.mdc`:
"conventional headings", "readable chronology"), the order used here is:

    CONTACT -> SUMMARY -> EDUCATION -> EXPERIENCE -> PROJECTS -> SKILLS

Contact carries no heading (matching every heading example given
anywhere in this repository's own instructions, which never lists
"CONTACT" among headings, and matching universal résumé convention
where the identity line at the top is unlabeled). This order is
recorded here as the smallest reasonable, evidence-grounded choice for
a TEST-ONLY renderer -- not a locked, Bora-approved final visual layout
decision; a future production renderer milestone remains free to
revisit it with explicit approval.

Purity: this module performs no I/O, no file writes, no mutation of its
input, and no persistence. Identical input always produces identical
output.
"""

from __future__ import annotations

from typing import Any, Mapping

CONTACT_FIELD_ORDER = ("name", "email", "phone", "location", "linkedin")
BULLET_PREFIX = "- "


def _error(code: str, **fields: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {"code": code}
    payload.update(fields)
    return payload


def _is_nonempty_str(value: Any) -> bool:
    return isinstance(value, str) and bool(value)


def _render_contact(contact: Mapping[str, Any], errors: list[dict[str, Any]]) -> str | None:
    if not isinstance(contact, Mapping) or not _is_nonempty_str(contact.get("name")):
        errors.append(_error("RENDER_MALFORMED_CONTACT", detail="contact.name must be a non-empty string"))
        return None
    parts = [contact.get(field) for field in CONTACT_FIELD_ORDER]
    parts = [p for p in parts if _is_nonempty_str(p)]
    return " | ".join(parts)


def _render_bullets(bullets: Any, errors: list[dict[str, Any]], *, context: str) -> list[str] | None:
    if not isinstance(bullets, list):
        errors.append(_error("RENDER_MALFORMED_BULLET", context=context, detail="bullets must be a list"))
        return None
    lines: list[str] = []
    for bullet in bullets:
        if not isinstance(bullet, Mapping) or not _is_nonempty_str(bullet.get("wording")):
            errors.append(
                _error(
                    "RENDER_MALFORMED_BULLET",
                    context=context,
                    detail="each bullet must be an object with a non-empty wording string",
                )
            )
            return None
        lines.append(BULLET_PREFIX + bullet["wording"])
    return lines


def _render_employment_sections(
    employment_sections: Any, errors: list[dict[str, Any]]
) -> list[str] | None:
    if not isinstance(employment_sections, list):
        errors.append(_error("RENDER_MALFORMED_EMPLOYMENT_SECTION", detail="employment_sections must be a list"))
        return None

    lines: list[str] = []
    for index, section in enumerate(employment_sections):
        context = f"employment_sections[{index}]"
        if not isinstance(section, Mapping):
            errors.append(_error("RENDER_MALFORMED_EMPLOYMENT_SECTION", context=context))
            return None

        organization = section.get("organization")
        title = section.get("formal_title") if _is_nonempty_str(section.get("formal_title")) else section.get("display_title")
        date_range = section.get("date_range")
        if not _is_nonempty_str(organization) or not _is_nonempty_str(title) or not _is_nonempty_str(date_range):
            errors.append(
                _error(
                    "RENDER_MALFORMED_EMPLOYMENT_SECTION",
                    context=context,
                    detail="organization, a resolved title, and date_range are all required",
                )
            )
            return None

        header_parts = [organization, title, date_range]
        location = section.get("location")
        if _is_nonempty_str(location):
            header_parts.append(location)
        lines.append(", ".join(header_parts))

        bullet_lines = _render_bullets(section.get("bullets"), errors, context=context)
        if bullet_lines is None:
            return None
        lines.extend(bullet_lines)

    return lines


def _render_project_sections(project_sections: Any, errors: list[dict[str, Any]]) -> list[str] | None:
    if not isinstance(project_sections, list):
        errors.append(_error("RENDER_MALFORMED_PROJECT_SECTION", detail="project_sections must be a list"))
        return None

    lines: list[str] = []
    for index, group in enumerate(project_sections):
        context = f"project_sections[{index}]"
        if not isinstance(group, Mapping) or not _is_nonempty_str(group.get("display_name")):
            errors.append(
                _error(
                    "RENDER_MALFORMED_PROJECT_SECTION",
                    context=context,
                    detail="display_name is required",
                )
            )
            return None

        lines.append(group["display_name"])
        bullet_lines = _render_bullets(group.get("bullets"), errors, context=context)
        if bullet_lines is None:
            return None
        lines.extend(bullet_lines)

    return lines


def _render_skills(skills: Any, errors: list[dict[str, Any]]) -> str | None:
    if not isinstance(skills, list) or not all(_is_nonempty_str(s) for s in skills):
        errors.append(_error("RENDER_MALFORMED_SKILLS", detail="skills must be a list of non-empty strings"))
        return None
    return ", ".join(skills)


def _render_education(education: Any, errors: list[dict[str, Any]]) -> list[str] | None:
    lines: list[str] = []
    for index, entry in enumerate(education):
        context = f"education[{index}]"
        if not isinstance(entry, Mapping) or not _is_nonempty_str(entry.get("degree_name")) or not _is_nonempty_str(entry.get("school_name")):
            errors.append(
                _error(
                    "RENDER_MALFORMED_EDUCATION",
                    context=context,
                    detail="degree_name and school_name are required",
                )
            )
            return None
        parts = [entry["degree_name"], entry["school_name"]]
        for optional_field in ("date_range", "location"):
            value = entry.get(optional_field)
            if _is_nonempty_str(value):
                parts.append(value)
        lines.append(", ".join(parts))
    return lines


def _render_summary(summary: Any, errors: list[dict[str, Any]]) -> str | None:
    if not isinstance(summary, Mapping) or not _is_nonempty_str(summary.get("wording")):
        errors.append(_error("RENDER_MALFORMED_SUMMARY", detail="summary.wording must be a non-empty string"))
        return None
    return summary["wording"]


def render_resume_text(presentation_result: Mapping[str, Any]) -> dict[str, Any]:
    """Render a deterministic, TEST-ONLY plain-text résumé from a valid
    unified presentation result.

    Input contract: the FULL envelope returned by
    `build_resume_presentation_view()` -- `{"valid", "presentation", "errors"}`
    -- not the bare inner `presentation` dict. This is the safer of the
    two documented options: it lets the renderer explicitly detect and
    fail on `valid=False`/`presentation=None` (an upstream sub-view
    failure) rather than requiring every caller to remember to check
    `valid` before ever calling this function. A caller who already has
    a known-valid `presentation` dict in hand may wrap it as
    `{"valid": True, "presentation": presentation, "errors": []}`.

    Output contract: `{"valid": bool, "text": str | None, "errors": [...]}`.
    `text` is `None` whenever `valid` is `False` -- no partial text is
    ever returned. `errors` accumulates the first structural problem
    encountered per section (rendering stops at the first malformed
    section it finds, since a partially-rendered résumé is never
    acceptable output regardless of how many other sections might have
    been fine).

    Section order: CONTACT (unlabeled), SUMMARY, EDUCATION, EXPERIENCE,
    PROJECTS, SKILLS -- see the module docstring for the exact
    documented rationale. Only sections with actual verified content
    produce a heading; an absent/empty section is omitted entirely,
    never rendered as an empty heading or placeholder.

    Failure behavior: fails explicitly (not partially) on: a malformed
    envelope; `valid` not `True`; a missing/malformed `presentation`
    object; a contact block missing a name; any employment section
    missing organization/resolved-title/date_range; any project group
    missing `display_name`; any bullet missing non-empty `wording`;
    non-string skills entries; malformed education/summary shape. This
    performs only cheap, deterministic shape checks -- it does not
    re-run upstream schema/lineage/semantic validation, and it trusts
    the presentation's semantic truth once its shape is confirmed
    sane.
    """
    errors: list[dict[str, Any]] = []

    if not isinstance(presentation_result, Mapping):
        return {"valid": False, "text": None, "errors": [_error("RENDER_INPUT_INVALID", detail="presentation_result must be an object")]}

    if presentation_result.get("valid") is not True:
        return {
            "valid": False,
            "text": None,
            "errors": [
                _error(
                    "RENDER_INPUT_INVALID",
                    detail="presentation_result.valid must be True; renderer does not render an invalid upstream presentation",
                )
            ],
        }

    presentation = presentation_result.get("presentation")
    if not isinstance(presentation, Mapping):
        return {"valid": False, "text": None, "errors": [_error("RENDER_INPUT_INVALID", detail="presentation_result.presentation must be an object")]}

    blocks: list[list[str]] = []

    contact_line = _render_contact(presentation.get("contact"), errors)
    if errors:
        return {"valid": False, "text": None, "errors": errors}
    blocks.append([contact_line])

    if "summary" in presentation:
        summary_text = _render_summary(presentation["summary"], errors)
        if errors:
            return {"valid": False, "text": None, "errors": errors}
        blocks.append(["SUMMARY", summary_text])

    if "education" in presentation:
        education = presentation["education"]
        if not isinstance(education, list):
            errors.append(_error("RENDER_MALFORMED_EDUCATION", detail="education must be a list"))
            return {"valid": False, "text": None, "errors": errors}
        if education:
            education_lines = _render_education(education, errors)
            if errors:
                return {"valid": False, "text": None, "errors": errors}
            blocks.append(["EDUCATION", *education_lines])

    employment_sections = presentation.get("employment_sections")
    employment_lines = _render_employment_sections(employment_sections, errors)
    if errors:
        return {"valid": False, "text": None, "errors": errors}
    if employment_lines:
        blocks.append(["EXPERIENCE", *employment_lines])

    project_sections = presentation.get("project_sections")
    project_lines = _render_project_sections(project_sections, errors)
    if errors:
        return {"valid": False, "text": None, "errors": errors}
    if project_lines:
        blocks.append(["PROJECTS", *project_lines])

    skills = presentation.get("skills")
    skills_line = _render_skills(skills, errors)
    if errors:
        return {"valid": False, "text": None, "errors": errors}
    if skills_line:
        blocks.append(["SKILLS", skills_line])

    text = "\n\n".join("\n".join(block) for block in blocks)
    return {"valid": True, "text": text, "errors": []}
