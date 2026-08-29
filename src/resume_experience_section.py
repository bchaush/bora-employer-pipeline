"""Deterministic presentation transform for employment (BULLET) résumé sections.

Closes the correctness gap identified by the read-only
RESUME_PRESENTATION_PIPELINE_GAP_ANALYSIS_V1 milestone:
`experience_sections[].bullet_module_ids` is never reconciled against a
derivative's `included_module_ids`. `INCLUDE_MODULE`/`EXCLUDE_MODULE`
patch operations only change `included_module_ids`; they never touch a
section's `bullet_module_ids` (see `resume_patch_apply.apply_resume_patch`).
A naive renderer reading `bullet_module_ids` directly could therefore
present a BULLET module the derivative intentionally excluded.

`build_employment_section_view()` is the employment-side counterpart to
the already-closed `build_project_section_view()` (`resume_project_bullet.py`),
but it cannot use an identical signature: the project view receives an
already-selected, already-ordered module sequence from its caller,
whereas the defect being fixed here is specifically that a section's own
stored `bullet_module_ids` is not yet reconciled against selection. This
function performs that reconciliation itself.

It stores no new truth, adds no schema, and never invents presentation
metadata: every field it emits is copied verbatim from already-validated
master/derivative data, or omitted when unresolved.

Ordering decision (documented per the milestone's ordering-precedence
requirement): within one employment section, bullet order is governed
solely by that section's own `bullet_module_ids` (filtered to selected
BULLET modules) -- `bullet_module_ids` is the field `REORDER_BULLETS`
exists to adjust, and it is explicitly excluded from the protected/
immutable field list in `resume_patch_apply.validate_immutable_fields_preserved`,
confirming it is the architecture's intended adjustable intra-section
ordering mechanism. The top-level `module_order`/`default_module_order`
governs a different concern (overall module sequencing across possibly
multiple module types) and is not consulted here, exactly as
`build_project_section_view()` also does not consult it. Section-level
order (when more than one experience section exists) is simply the
input `experience_sections` list order, which no patch operation
currently reorders. No ambiguity was found; nothing in this milestone
required an ARCHITECTURE_DECISION_REQUIRED stop.

Title-identity decision: this function does not redesign title
resolution. It reuses the already-accepted, already-closed
`is_source_formal_title_unresolved()` / `has_approved_display_title()`
checks from `resume_title_metadata.py` verbatim, exposing whichever of
`formal_title` / `display_title` the existing architecture already
considers export-ready -- never both, never the raw unresolved sentinel.
"""

from __future__ import annotations

from typing import Any, Iterable, Mapping, Sequence

from resume_protected_metadata import UNRESOLVED_PROTECTED_METADATA_SENTINEL
from resume_title_metadata import (
    has_approved_display_title,
    is_source_formal_title_unresolved,
)

EMPLOYMENT_MODULE_TYPE = "BULLET"


def _error(code: str, **fields: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {"code": code}
    payload.update(fields)
    return payload


def _unresolved(field: str, value: Any = UNRESOLVED_PROTECTED_METADATA_SENTINEL) -> dict[str, Any]:
    # Reuses the exact UNRESOLVED_PROTECTED_METADATA taxonomy already
    # established in resume_protected_metadata.py for this precise
    # situation (a protected field still carries the unresolved
    # sentinel), rather than inventing a new error code.
    return _error(
        "UNRESOLVED_PROTECTED_METADATA",
        field=field,
        value=value,
        detail=(
            f"protected metadata field {field!r} remains unresolved "
            f"({UNRESOLVED_PROTECTED_METADATA_SENTINEL!r})"
        ),
    )


def build_employment_section_view(
    experience_sections: Sequence[Mapping[str, Any]],
    modules: Sequence[Mapping[str, Any]],
    *,
    included_module_ids: Iterable[str] | None,
) -> dict[str, Any]:
    """Build a pure, derived employment-section presentation view.

    Not a renderer and not a schema: this stores no new truth. It only
    reshapes already-existing `experience_sections` + `modules` data into
    presentation-ready employment sections, filtered to currently
    selected `BULLET` modules.

    Input:
    * `experience_sections` -- the master's or a derivative's
      `experience_sections[]` list (unmodified structure/order).
    * `modules` -- the master's or a derivative's `modules[]` list (used
      only to resolve `module_type`/`wording` by `module_id`; any
      module_type may be present, non-`BULLET` entries are ignored).
    * `included_module_ids` -- the derivative's `included_module_ids`
      (or equivalent selection set). A module not in this set is
      correctly and silently absent from the view -- that is the
      defect this function exists to fix, not an error.

    Filtering: a bullet appears in a section's output only if its
    `module_id` is present in that section's own `bullet_module_ids`,
    is a member of `included_module_ids`, resolves to a real entry in
    `modules`, and that entry's `module_type == "BULLET"`. A selected
    `PROJECT_BULLET` (or any other non-`BULLET` module_type) referenced
    from `bullet_module_ids` is silently excluded, matching how
    `build_project_section_view()` silently excludes non-matching
    module types -- not an error, since mixed-type membership in
    `bullet_module_ids` is already prevented elsewhere
    (`validate_project_bullet_contract`); this function does not assume
    that invariant holds and enforces it defensively anyway. A
    `bullet_module_ids` entry that names a `module_id` absent from
    `modules` entirely is a genuine data-integrity problem and produces
    an explicit `EMPLOYMENT_BULLET_MODULE_NOT_FOUND` error rather than
    being silently dropped.

    Ordering: bullets within a section preserve that section's own
    `bullet_module_ids` order exactly (after filtering) -- see the
    module docstring for the full ordering-precedence decision.
    Duplicate `module_id` entries in `bullet_module_ids` are preserved
    in place, not deduplicated, matching the same documented,
    unenforced-elsewhere-so-preserved-here behavior already established
    by `build_project_section_view()`.

    Section identity: `organization` and `date_range` must be
    non-empty strings that are not the repository's
    `PENDING_BORA_REVIEW` unresolved-metadata sentinel. Title
    resolution uses the existing title architecture's own primitives
    (`is_source_formal_title_unresolved()` / `has_approved_display_title()`)
    with a corrected precedence: an approved `display_title` is used
    whenever one exists, regardless of whether `formal_title` also
    happens to be resolved; otherwise a resolved `formal_title` is
    used; otherwise the section fails to resolve. (Corrected during
    `TELUS_MASTER_INTEGRATION_V1`: the previous precedence only ever
    fell through to `display_title` when `formal_title` was the
    unresolved sentinel, so a resolved `formal_title` with a separately
    approved shorter `display_title` -- exactly TELUS's case, where
    Bora approved dropping the formal title's parenthetical suffix for
    recruiter readability -- was unreachable and silently rendered the
    full formal title instead. Winter Walk's behavior is unchanged by
    this fix, since its `formal_title` was already the unresolved
    sentinel.) `employment_category` and `location` are optional and
    only fail if explicitly set to the
    unresolved sentinel. No field is ever guessed or fabricated.

    Fail-closed contract: if ANY section fails to resolve (identity
    unresolved, or a dangling bullet module reference), the whole view
    is invalid: `valid: False` always means `sections: []` -- no
    partial result, matching the closed `build_project_section_view()`
    contract. `errors` is always fully populated regardless of `valid`.

    A section that resolves cleanly but ends up with zero currently
    selected bullets (e.g. `included_module_ids` excludes every bullet
    it lists) is omitted from the output entirely -- it is never
    emitted as an empty, bullet-less header. This is not an error
    (`valid` stays `True`; the section is simply absent), mirroring how
    `build_project_section_view()` never emits an empty project group.

    Returns `{"valid": bool, "sections": [...], "errors": [...]}`. Each
    section (only present when `valid` is `True` and it has at least
    one selected bullet) is
    `{"experience_id", "organization", "formal_title" or "display_title",
    "date_range", "employment_category" (if present), "location" (if
    present), "bullets": [{"module_id", "wording"}, ...]}` -- every
    value copied verbatim from already-validated source data, nothing
    computed or invented.
    """
    errors: list[dict[str, Any]] = []
    included = set(included_module_ids or [])

    module_by_id: dict[str, Mapping[str, Any]] = {}
    for module in modules or []:
        if not isinstance(module, Mapping):
            continue
        module_id = module.get("module_id")
        if isinstance(module_id, str) and module_id:
            module_by_id[module_id] = module

    sections: list[dict[str, Any]] = []

    for index, section in enumerate(experience_sections or []):
        if not isinstance(section, Mapping):
            continue
        prefix = f"experience_sections[{index}]"
        section_errors: list[dict[str, Any]] = []

        organization = section.get("organization")
        if (
            not isinstance(organization, str)
            or not organization
            or organization == UNRESOLVED_PROTECTED_METADATA_SENTINEL
        ):
            section_errors.append(_unresolved(f"{prefix}.organization", organization))

        date_range = section.get("date_range")
        if (
            not isinstance(date_range, str)
            or not date_range
            or date_range == UNRESOLVED_PROTECTED_METADATA_SENTINEL
        ):
            section_errors.append(_unresolved(f"{prefix}.date_range", date_range))

        formal_title = section.get("formal_title")
        title_field: tuple[str, Any] | None = None
        if has_approved_display_title(section):
            # A human-approved display title is always preferred when present,
            # regardless of whether the formal title happens to already be
            # resolved. The display-title mechanism exists specifically to let
            # Bora approve a cleaner/shorter recruiter-facing label without
            # touching the protected formal title; a resolved formal_title
            # must not silently pre-empt an approved display_title (defect
            # found and fixed here -- previously only an *unresolved*
            # formal_title fell through to display_title, so a resolved
            # formal_title with an approved shorter display_title, as with
            # TELUS, was never actually reachable).
            title_field = ("display_title", section.get("display_title"))
        elif not is_source_formal_title_unresolved(formal_title):
            if isinstance(formal_title, str) and formal_title:
                title_field = ("formal_title", formal_title)
            else:
                section_errors.append(_unresolved(f"{prefix}.formal_title", formal_title))
        else:
            section_errors.append(
                _unresolved(f"{prefix}.display_title", section.get("display_title"))
            )

        employment_category = section.get("employment_category")
        if employment_category == UNRESOLVED_PROTECTED_METADATA_SENTINEL:
            section_errors.append(
                _unresolved(f"{prefix}.employment_category", employment_category)
            )

        location = section.get("location")
        if location == UNRESOLVED_PROTECTED_METADATA_SENTINEL:
            section_errors.append(_unresolved(f"{prefix}.location", location))

        bullets: list[dict[str, Any]] = []
        for module_id in section.get("bullet_module_ids") or []:
            if not isinstance(module_id, str) or not module_id:
                continue
            module = module_by_id.get(module_id)
            if module is None:
                section_errors.append(
                    _error(
                        "EMPLOYMENT_BULLET_MODULE_NOT_FOUND",
                        section_id=section.get("section_id"),
                        module_id=module_id,
                        detail=(
                            "section bullet_module_ids references a module_id "
                            "absent from the provided modules"
                        ),
                    )
                )
                continue
            if module_id not in included:
                continue
            if module.get("module_type") != EMPLOYMENT_MODULE_TYPE:
                continue
            bullets.append({"module_id": module_id, "wording": module.get("wording")})

        if section_errors:
            errors.extend(section_errors)
            continue

        if not bullets:
            # A section whose identity resolves cleanly but which has zero
            # currently-selected bullets is omitted entirely, never emitted
            # as an empty, bullet-less header (defect found and fixed during
            # TELUS_MASTER_INTEGRATION_V1: this repository had only ever had
            # one experience_sections entry until now, so a scenario where
            # one section is fully selected while a second resolves with no
            # selected bullets -- e.g. a future derivative that excludes both
            # TELUS bullets while Winter Walk remains selected -- was never
            # exercised. Mirrors how build_project_section_view() never
            # emits an empty project group.)
            continue

        entry: dict[str, Any] = {
            "experience_id": section.get("experience_id"),
            "organization": organization,
            "date_range": date_range,
            "bullets": bullets,
        }
        assert title_field is not None
        entry[title_field[0]] = title_field[1]
        if employment_category is not None:
            entry["employment_category"] = employment_category
        if location is not None:
            entry["location"] = location
        sections.append(entry)

    valid = len(errors) == 0
    return {"valid": valid, "sections": sections if valid else [], "errors": errors}
