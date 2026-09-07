"""RESUME_REFERENCE_DERIVATIVE_AND_PAGE_UTILIZATION_ENFORCEMENT_V1.

Deterministic, pure QA validator enforcing Bora's explicit hard
page-utilization floor: for a normal one-page Bora application résumé,
meaningful rendered content must reach at least 92% of U.S. Letter page
height, measured from the physical top of the page. Authorized under
BLUEPRINT.md Section 133's build-economy gate (a demonstrated, reproduced
material quality/workflow defect -- the Atominvest Implementation Analyst
live application, where the system produced a truthful but substantially
under-filled one-page résumé that Bora had to manually correct before
submission) and extends the fixed visual/QA contract already locked in
Section 134.

ARCHITECTURE BOUNDARY (read before using or extending this module):

Canonical main contains no production PDF generator, no PDF-inspection
dependency, and no rendered-page-geometry producer of any kind -- the only
existing résumé renderer (`resume_text_renderer.py`) is an explicit
TEST-ONLY linear plain-text renderer with no coordinate/layout concept
whatsoever. Bora's actual submitted PDF is produced by a human-controlled
process outside this repository (per BLUEPRINT.md Section 134, the binary
itself is never committed here). Building a PDF generator or a PDF-parsing
dependency to satisfy this milestone would therefore either invent a new,
unauthorized production subsystem (explicitly out of scope -- see the
milestone's own DO NOT BUILD list) or add a dependency to parse an
artifact that never actually enters this repository's pipeline today.

The smallest reliable, honest enforcement boundary is therefore Option A:
a pure validator that consumes an already-computed, normalized
rendered-page-geometry payload -- a plain, renderer-agnostic
measurement contract -- and returns a deterministic pass/fail result.
This module NEVER renders, generates, or parses a PDF/DOCX artifact
itself; it has zero I/O and zero third-party dependency. It can be fed by
a human manually transcribing measurements from the actual rendered PDF
today, or by a future automated geometry producer, without this module
changing. THE PRODUCTION PDF ARTIFACT ITSELF DOES NOT CURRENTLY PASS
THROUGH THIS REPOSITORY OR THIS VALIDATOR -- this module mechanically
enforces the geometry payload it is given; it does not, and cannot
honestly claim to, independently verify that payload matches Bora's real
exported PDF. That correspondence remains a manual QA step (see
`RESUME_PAGE_UTILIZATION_GEOMETRY_CONTRACT` below and
`.cursor/rules/resume.mdc`).

MEASUREMENT SEMANTICS.

The enforced ratio is:

    bottom-most meaningful rendered content position / page height >= 0.92

not `text_bbox_height / page_height` -- a normal top margin must not count
against utilization, and only the position of the LOWEST meaningful
content matters, not the total height any content occupies. Coordinates
are normalized from the physical top of a U.S. Letter page (612pt x
792pt), consistent with common PDF coordinate/layout convention, and are
expressed in points (pt) via the geometry payload's own
`page_height_pt`/`objects[].bottom_pt` fields -- this module does not
assume a particular vertical coordinate origin beyond requiring the
caller's `bottom_pt` values to already be normalized as "distance from
the physical top of the page."

WHAT COUNTS AS MEANINGFUL CONTENT.

This module enforces an EXPLICIT ALLOW-LIST (`MEANINGFUL_CONTENT_TYPES`)
of content-object type tags that correspond exactly to the résumé's own
approved structural sections (contact block, section headings, summary,
education entries, employment headers, bullets, project headers, skills
line -- the same structural vocabulary already established by
`resume_presentation.py`/`resume_text_renderer.py`). Any object whose
`content_type` is not on this allow-list -- including but not limited to
blank whitespace, hidden/white text, transparent/invisible objects, PDF
metadata, page-boundary artifacts, unrelated footer artifacts, decorative
marks inserted solely to satisfy density, or any unrecognized/misspelled
tag -- is excluded from the bottom-most-position calculation by
construction (fail-closed default-exclude; an object is counted only if
it is affirmatively on the allow-list, never counted merely because it is
not affirmatively excluded).

BOUNDARY THIS VALIDATOR CANNOT ITSELF ENFORCE (documented, not faked):
this validator receives only the normalized `content_type` tag a geometry
producer already assigned to each object -- it does not itself inspect
raw PDF objects, fonts, colors, or visibility. Whether a given real PDF
object is honestly tagged (e.g., a decorative mark is never mislabeled as
`BULLET_TEXT` merely to inflate the metric) is the responsibility of the
geometry-producer contract that fills in this payload, not something this
pure validator can independently verify from geometry alone. Any future
automated geometry producer must itself be trustworthy about content-type
tagging; this module's contribution is refusing to count anything that is
not affirmatively tagged as one of the approved meaningful types.

TRUTH/READABILITY PRECEDENCE.

This validator NEVER mutates, synthesizes, reorders, or pads résumé
content. It performs no writes and returns no modified geometry or résumé
data -- only a diagnostic pass/fail result. It has no knowledge of
Candidate Truth, Claims, Evidence, or the résumé derivative/patch
architecture at all (see `resume_validation.py` for that separate,
untouched layer) and cannot upgrade, downgrade, or influence resume
content in any way. A failing result (`RESUME_PAGE_UNDERUTILIZED`) is a
QA failure to be corrected by truthful means (reordering, rewording,
restoring stronger approved material, reallocating space) upstream of
this module -- it is never an instruction, to this module or its caller,
to insert filler, invented content, or decorative padding to pass.

FAIL-CLOSED EXPORT INTEGRATION.

`resume_validation.approve_derivative_for_export()` and
`validate_derivative_eligibility(..., for_export=True)` accept an optional
`page_geometry` argument. When a geometry payload is supplied, a failing
page-utilization result blocks export approval exactly like any other
export-eligibility failure. When `page_geometry` is omitted (the default,
and the only mode possible today, since no geometry producer exists yet),
no mechanical page-utilization check occurs and export approval proceeds
exactly as it did before this milestone -- this is an honest reflection
of current reality, not a claim that page-utilization is already
mechanically enforced end-to-end for every real export. Until a real
geometry producer exists, satisfying the 92% floor for an actual
submitted résumé remains a human QA step per BLUEPRINT.md Section 134's
QA checklist.
"""

from __future__ import annotations

import math
from typing import Any, Mapping

US_LETTER_WIDTH_PT = 612.0
US_LETTER_HEIGHT_PT = 792.0
PAGE_UTILIZATION_FLOOR = 0.92

# Explicit allow-list only -- an object is counted as meaningful content
# only when its content_type is affirmatively one of these tags, which
# correspond exactly to resume_presentation.py's/resume_text_renderer.py's
# own approved structural vocabulary (CONTACT, SUMMARY, EDUCATION,
# EXPERIENCE headers/bullets, PROJECTS headers/bullets, SKILLS). Any other
# value -- including a plausible-sounding but unrecognized tag -- is
# excluded by construction; see the module docstring's "boundary this
# validator cannot itself enforce" section.
MEANINGFUL_CONTENT_TYPES = frozenset(
    {
        "CONTACT_LINE",
        "SECTION_HEADING",
        "SUMMARY_TEXT",
        "EDUCATION_LINE",
        "EMPLOYMENT_HEADER",
        "BULLET_TEXT",
        "PROJECT_HEADER",
        "SKILLS_LINE",
    }
)

# Documented for readability only -- NOT consulted by the logic below,
# which uses fail-closed default-exclude (only MEANINGFUL_CONTENT_TYPES
# counts). Listed so a geometry-producer implementer has explicit,
# citable examples of what must never be tagged as meaningful.
NON_MEANINGFUL_CONTENT_TYPE_EXAMPLES = frozenset(
    {
        "WHITESPACE",
        "HIDDEN_TEXT",
        "TRANSPARENT_OBJECT",
        "PAGE_METADATA",
        "FOOTER_ARTIFACT",
        "DECORATIVE_MARK",
        "SPACER",
    }
)

_OVERFLOW_EPSILON_PT = 0.01


def _error(code: str, **fields: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {"code": code}
    payload.update(fields)
    return payload


def evaluate_resume_page_utilization(geometry: Any) -> dict[str, Any]:
    """Deterministically validate a normalized rendered-page-geometry payload.

    Input contract (`RESUME_PAGE_UTILIZATION_GEOMETRY_CONTRACT`), a plain
    mapping:

        {
          "page_size": "US_LETTER",
          "page_width_pt": 612.0,
          "page_height_pt": 792.0,
          "page_count": 1,
          "objects": [
            {"content_type": "CONTACT_LINE", "bottom_pt": 68.0},
            {"content_type": "BULLET_TEXT", "bottom_pt": 731.4},
            ...
          ]
        }

    `bottom_pt` on each object is the object's lowest rendered edge,
    normalized as distance in points from the PHYSICAL TOP of the page
    (not from any margin). Only objects whose `content_type` is in
    `MEANINGFUL_CONTENT_TYPES` participate in the utilization
    calculation; every other object is still checked for page overflow
    but never contributes to the bottom-most-meaningful-content position.

    Returns `{"valid": bool, "errors": [...], "meaningful_content_bottom_fraction": float | None}`.
    `meaningful_content_bottom_fraction` is the deterministic
    (round-to-6-decimal-places) ratio actually computed, or `None` when a
    structural problem prevented computing one at all. This function
    performs no I/O, renders nothing, and never mutates its input.

    All numeric geometry fields (`page_width_pt`, `page_height_pt`, every
    object's `bottom_pt`) must be finite (`math.isfinite`) -- NaN and
    +/-inf are rejected as RESUME_PAGE_GEOMETRY_INVALID, never silently
    accepted into a comparison (a fail-closed invariant: a non-finite
    value must never be able to produce a False "underutilized"
    comparison, e.g. `nan < 0.92`, that this validator would otherwise
    read as passing). `bottom_pt` must also be non-negative (it is a
    distance from the physical top of the page); a negative value is
    malformed geometry, not a legitimately sparse résumé, and is also
    rejected as RESUME_PAGE_GEOMETRY_INVALID rather than being allowed to
    fall through to a RESUME_PAGE_UNDERUTILIZED judgment.

    Failure codes:
      - RESUME_PAGE_GEOMETRY_INVALID: malformed/missing/non-finite/
        negative required geometry fields (not itself a page-count/size/
        utilization judgment).
      - RESUME_PAGE_SIZE_UNSUPPORTED: `page_size` is not "US_LETTER" --
        fails the page-size contract independently of utilization.
      - RESUME_PAGE_GEOMETRY_INCONSISTENT: `page_size` claims US_LETTER
        but `page_width_pt`/`page_height_pt` do not match 612.0/792.0.
      - RESUME_PAGE_COUNT_INVALID: `page_count` != 1 -- fails independently
        of utilization (the two-page/overflow case).
      - RESUME_PAGE_CONTENT_OVERFLOW: some object's `bottom_pt` exceeds
        `page_height_pt` -- fails independently of utilization (content
        would be clipped/overflow the physical page).
      - RESUME_PAGE_CONTENT_MISSING: no objects at all, or no object
        recognized as meaningful content.
      - RESUME_PAGE_UNDERUTILIZED: structurally valid one-page US-Letter
        content whose meaningful-content bottom fraction is below
        `PAGE_UTILIZATION_FLOOR` (0.92).
    """
    if not isinstance(geometry, Mapping):
        return {
            "valid": False,
            "errors": [_error("RESUME_PAGE_GEOMETRY_INVALID", detail="geometry must be an object")],
            "meaningful_content_bottom_fraction": None,
        }

    errors: list[dict[str, Any]] = []

    page_size = geometry.get("page_size")
    width_pt = geometry.get("page_width_pt")
    height_pt = geometry.get("page_height_pt")
    page_count = geometry.get("page_count")
    objects = geometry.get("objects")

    if page_size != "US_LETTER":
        errors.append(_error("RESUME_PAGE_SIZE_UNSUPPORTED", page_size=page_size))

    height_is_numeric = (
        isinstance(height_pt, (int, float))
        and not isinstance(height_pt, bool)
        and math.isfinite(height_pt)
    )
    width_is_numeric = (
        isinstance(width_pt, (int, float))
        and not isinstance(width_pt, bool)
        and math.isfinite(width_pt)
    )
    if not width_is_numeric or not height_is_numeric:
        errors.append(
            _error(
                "RESUME_PAGE_GEOMETRY_INVALID",
                detail="page_width_pt and page_height_pt must be finite numbers (not NaN/inf)",
            )
        )
    elif page_size == "US_LETTER" and (
        round(float(width_pt), 2) != US_LETTER_WIDTH_PT or round(float(height_pt), 2) != US_LETTER_HEIGHT_PT
    ):
        errors.append(
            _error(
                "RESUME_PAGE_GEOMETRY_INCONSISTENT",
                page_width_pt=width_pt,
                page_height_pt=height_pt,
                expected_width_pt=US_LETTER_WIDTH_PT,
                expected_height_pt=US_LETTER_HEIGHT_PT,
            )
        )

    if not isinstance(page_count, int) or isinstance(page_count, bool) or page_count < 1:
        errors.append(_error("RESUME_PAGE_GEOMETRY_INVALID", detail="page_count must be a positive integer"))
    elif page_count != 1:
        errors.append(_error("RESUME_PAGE_COUNT_INVALID", page_count=page_count))

    if not isinstance(objects, list) or not objects:
        errors.append(_error("RESUME_PAGE_CONTENT_MISSING", detail="objects must be a non-empty list"))
        return {"valid": False, "errors": errors, "meaningful_content_bottom_fraction": None}

    meaningful_bottoms: list[float] = []
    for index, obj in enumerate(objects):
        if not isinstance(obj, Mapping):
            errors.append(_error("RESUME_PAGE_GEOMETRY_INVALID", detail=f"objects[{index}] must be an object"))
            continue
        bottom_pt = obj.get("bottom_pt")
        if (
            not isinstance(bottom_pt, (int, float))
            or isinstance(bottom_pt, bool)
            or not math.isfinite(bottom_pt)
        ):
            errors.append(
                _error(
                    "RESUME_PAGE_GEOMETRY_INVALID",
                    detail=f"objects[{index}].bottom_pt must be a finite number (not NaN/inf)",
                )
            )
            continue
        if bottom_pt < 0:
            errors.append(
                _error(
                    "RESUME_PAGE_GEOMETRY_INVALID",
                    detail=f"objects[{index}].bottom_pt must not be negative (distance from the physical top of the page)",
                )
            )
            continue
        if height_is_numeric and float(bottom_pt) > float(height_pt) + _OVERFLOW_EPSILON_PT:
            errors.append(
                _error(
                    "RESUME_PAGE_CONTENT_OVERFLOW",
                    index=index,
                    bottom_pt=bottom_pt,
                    page_height_pt=height_pt,
                )
            )
        if obj.get("content_type") in MEANINGFUL_CONTENT_TYPES:
            meaningful_bottoms.append(float(bottom_pt))

    if errors:
        return {"valid": False, "errors": errors, "meaningful_content_bottom_fraction": None}

    if not meaningful_bottoms:
        errors.append(_error("RESUME_PAGE_CONTENT_MISSING", detail="no meaningful content objects present"))
        return {"valid": False, "errors": errors, "meaningful_content_bottom_fraction": None}

    bottom_most_pt = max(meaningful_bottoms)
    fraction = round(bottom_most_pt / float(height_pt), 6)

    if fraction < PAGE_UTILIZATION_FLOOR:
        errors.append(
            _error(
                "RESUME_PAGE_UNDERUTILIZED",
                meaningful_content_bottom_fraction=fraction,
                floor=PAGE_UTILIZATION_FLOOR,
            )
        )
        return {"valid": False, "errors": errors, "meaningful_content_bottom_fraction": fraction}

    return {"valid": True, "errors": [], "meaningful_content_bottom_fraction": fraction}
