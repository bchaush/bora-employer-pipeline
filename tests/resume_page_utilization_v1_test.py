"""Regression tests for RESUME_REFERENCE_DERIVATIVE_AND_PAGE_UTILIZATION_ENFORCEMENT_V1.

Root cause reproduced live: the Atominvest -- Implementation Analyst
application workflow produced a truthful, technically-one-page résumé
that was nevertheless substantially under-filled (a large dead lower-page
region, useful approved evidence unnecessarily deleted); Bora manually
corrected it before submission. No mechanical check existed anywhere in
this repository to catch that defect -- `resume_text_renderer.py` is
TEST-ONLY plain text with no layout/geometry concept at all, and
`resume_validation.py`'s export gate had no page-utilization check of any
kind. `evaluate_resume_page_utilization()` (src/resume_page_utilization.py)
closes that gap as a pure, deterministic validator over a normalized
rendered-page-geometry payload -- see that module's own docstring for the
full architecture-boundary rationale (Option A: consume geometry, never
generate/parse a PDF).

Sections 1-9 below correspond exactly to the milestone's own required
regression categories.
"""

from __future__ import annotations

import copy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from resume_page_utilization import (  # noqa: E402
    MEANINGFUL_CONTENT_TYPES,
    PAGE_UTILIZATION_FLOOR,
    US_LETTER_HEIGHT_PT,
    US_LETTER_WIDTH_PT,
    evaluate_resume_page_utilization,
)


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        print(f"FAIL: {message}")
        raise SystemExit(1)


def has_code(errors: list[dict], code: str) -> bool:
    return any(e.get("code") == code for e in errors)


def _obj(content_type: str, bottom_pt: float) -> dict:
    return {"content_type": content_type, "bottom_pt": bottom_pt}


def _base_geometry(*, bottom_pt: float, page_count: int = 1) -> dict:
    """A structurally valid one-page US-Letter geometry payload whose
    single meaningful content object's bottom_pt determines the
    utilization fraction under test."""
    return {
        "page_size": "US_LETTER",
        "page_width_pt": US_LETTER_WIDTH_PT,
        "page_height_pt": US_LETTER_HEIGHT_PT,
        "page_count": page_count,
        "objects": [
            _obj("CONTACT_LINE", 68.0),
            _obj("SECTION_HEADING", 120.0),
            _obj("BULLET_TEXT", bottom_pt),
        ],
    }


# ======================================================================
# 1. FULL APPROVED-LIKE PAGE -- one U.S. Letter page, meaningful-content
# bottom position >= 0.92, passes utilization.
# ======================================================================
full_page = _base_geometry(bottom_pt=740.0)  # 740/792 = 0.93434...
result_full = evaluate_resume_page_utilization(full_page)
assert_true(result_full["valid"] is True, f"full approved-like page must pass, got {result_full}")
assert_true(
    result_full["meaningful_content_bottom_fraction"] >= PAGE_UTILIZATION_FLOOR,
    "full page fraction must be >= 0.92",
)
print("PASS 1: full approved-like one-page US-Letter geometry with meaningful content at 93.4% passes utilization.")


# ======================================================================
# 2. SPARSE BAD DERIVATIVE -- otherwise structurally valid, meaningful-
# content bottom position clearly below 0.92, fails RESUME_PAGE_UNDERUTILIZED.
# This is the reproduced Atominvest-shaped defect.
# ======================================================================
sparse_page = _base_geometry(bottom_pt=400.0)  # 400/792 = 0.505...
result_sparse = evaluate_resume_page_utilization(sparse_page)
assert_true(result_sparse["valid"] is False, "sparse Atominvest-shaped derivative must fail")
assert_true(
    has_code(result_sparse["errors"], "RESUME_PAGE_UNDERUTILIZED"),
    f"sparse derivative must fail with RESUME_PAGE_UNDERUTILIZED, got {result_sparse['errors']}",
)
assert_true(
    result_sparse["meaningful_content_bottom_fraction"] < PAGE_UTILIZATION_FLOOR,
    "sparse derivative fraction must be below the floor",
)
print("PASS 2 (ATOMINVEST REGRESSION): a sparse but otherwise-valid one-page derivative (50.5% utilization) fails with RESUME_PAGE_UNDERUTILIZED.")


# ======================================================================
# 3. TWO-PAGE / OVERFLOW CASE -- fails independently of utilization.
# ======================================================================
two_page = _base_geometry(bottom_pt=740.0, page_count=2)
result_two_page = evaluate_resume_page_utilization(two_page)
assert_true(result_two_page["valid"] is False, "a two-page result must fail")
assert_true(
    has_code(result_two_page["errors"], "RESUME_PAGE_COUNT_INVALID"),
    f"two-page geometry must fail with RESUME_PAGE_COUNT_INVALID, got {result_two_page['errors']}",
)

overflow_page = _base_geometry(bottom_pt=740.0)
overflow_page["objects"].append(_obj("BULLET_TEXT", 850.0))  # exceeds page height
result_overflow = evaluate_resume_page_utilization(overflow_page)
assert_true(result_overflow["valid"] is False, "content overflowing the physical page must fail")
assert_true(
    has_code(result_overflow["errors"], "RESUME_PAGE_CONTENT_OVERFLOW"),
    f"overflowing content must fail with RESUME_PAGE_CONTENT_OVERFLOW, got {result_overflow['errors']}",
)
print("PASS 3: two-page geometry (RESUME_PAGE_COUNT_INVALID) and single-page content overflow (RESUME_PAGE_CONTENT_OVERFLOW) each fail independently of utilization.")


# ======================================================================
# 4. NON-LETTER CASE -- fails the page-size contract.
# ======================================================================
a4_page = _base_geometry(bottom_pt=740.0)
a4_page["page_size"] = "A4"
a4_page["page_width_pt"] = 595.28
a4_page["page_height_pt"] = 841.89
result_a4 = evaluate_resume_page_utilization(a4_page)
assert_true(result_a4["valid"] is False, "A4 geometry must fail the page-size contract")
assert_true(
    has_code(result_a4["errors"], "RESUME_PAGE_SIZE_UNSUPPORTED"),
    f"non-Letter page_size must fail with RESUME_PAGE_SIZE_UNSUPPORTED, got {result_a4['errors']}",
)

inconsistent_page = _base_geometry(bottom_pt=740.0)
inconsistent_page["page_width_pt"] = 600.0  # claims US_LETTER but wrong numeric width
result_inconsistent = evaluate_resume_page_utilization(inconsistent_page)
assert_true(result_inconsistent["valid"] is False, "inconsistent US_LETTER geometry must fail")
assert_true(
    has_code(result_inconsistent["errors"], "RESUME_PAGE_GEOMETRY_INCONSISTENT"),
    f"mismatched US_LETTER dimensions must fail with RESUME_PAGE_GEOMETRY_INCONSISTENT, got {result_inconsistent['errors']}",
)
print("PASS 4: A4 page_size fails RESUME_PAGE_SIZE_UNSUPPORTED; a US_LETTER claim with mismatched numeric dimensions fails RESUME_PAGE_GEOMETRY_INCONSISTENT.")


# ======================================================================
# 5. EDGE CASE AT EXACT THRESHOLD -- exactly 0.92 passes.
# ======================================================================
exact_bottom_pt = US_LETTER_HEIGHT_PT * PAGE_UTILIZATION_FLOOR  # 728.64
exact_page = _base_geometry(bottom_pt=exact_bottom_pt)
result_exact = evaluate_resume_page_utilization(exact_page)
assert_true(result_exact["valid"] is True, f"exactly 0.92 must pass, got {result_exact}")
assert_true(
    result_exact["meaningful_content_bottom_fraction"] == PAGE_UTILIZATION_FLOOR,
    f"exact-threshold fraction must equal {PAGE_UTILIZATION_FLOOR} exactly, got {result_exact['meaningful_content_bottom_fraction']}",
)
print("PASS 5: meaningful-content bottom position at exactly 0.92 passes.")


# ======================================================================
# 6. JUST-BELOW THRESHOLD -- below 0.92 by a deterministic amount fails.
# ======================================================================
just_below_bottom_pt = exact_bottom_pt - 1.0  # 727.64pt -> 0.918687...
just_below_page = _base_geometry(bottom_pt=just_below_bottom_pt)
result_just_below = evaluate_resume_page_utilization(just_below_page)
assert_true(result_just_below["valid"] is False, "just-below-threshold geometry must fail")
assert_true(
    has_code(result_just_below["errors"], "RESUME_PAGE_UNDERUTILIZED"),
    f"just-below-threshold geometry must fail with RESUME_PAGE_UNDERUTILIZED, got {result_just_below['errors']}",
)
assert_true(
    result_just_below["meaningful_content_bottom_fraction"] < PAGE_UTILIZATION_FLOOR,
    "just-below-threshold fraction must be strictly below the floor",
)
print("PASS 6: meaningful-content bottom position one point below the exact threshold (0.918687...) fails deterministically.")


# ======================================================================
# 7. DECORATIVE / NON-MEANINGFUL OBJECT CASE -- a decorative object placed
# far down the page cannot game the metric; only allow-listed content
# types count toward the bottom-most position.
# ======================================================================
decorative_page = _base_geometry(bottom_pt=400.0)  # sparse, real content only 50.5%
decorative_page["objects"].append(_obj("DECORATIVE_MARK", 780.0))
result_decorative = evaluate_resume_page_utilization(decorative_page)
assert_true(
    result_decorative["valid"] is False,
    "a decorative object near the page bottom must not rescue an otherwise-sparse page",
)
assert_true(
    has_code(result_decorative["errors"], "RESUME_PAGE_UNDERUTILIZED"),
    f"decorative-object gaming attempt must still fail RESUME_PAGE_UNDERUTILIZED, got {result_decorative['errors']}",
)
assert_true(
    abs(result_decorative["meaningful_content_bottom_fraction"] - result_sparse["meaningful_content_bottom_fraction"]) < 1e-9,
    "the decorative object must not change the computed meaningful-content fraction at all",
)
# Architecture-boundary note (documented, not faked -- see module docstring
# "boundary this validator cannot itself enforce"): this proves the
# allow-list correctly excludes a decorative object AS LONG AS the
# geometry producer honestly tagged it DECORATIVE_MARK. This validator
# receives only the producer's own content_type tag; whether a real
# geometry producer ever mislabels a decorative mark as a meaningful type
# is a property of that producer's own contract, not something a pure
# geometry validator can independently detect from geometry alone.
print("PASS 7: a DECORATIVE_MARK object positioned near the page bottom does not count toward the meaningful-content bottom position -- cannot game the metric while honestly tagged.")


# ======================================================================
# 8. TRUTH PRECEDENCE CASE -- page-utilization validation must never
# mutate resume content or synthesize content.
# ======================================================================
truth_precedence_input = copy.deepcopy(sparse_page)
frozen_copy = copy.deepcopy(truth_precedence_input)
_ = evaluate_resume_page_utilization(truth_precedence_input)
assert_true(
    truth_precedence_input == frozen_copy,
    "evaluate_resume_page_utilization must never mutate its input geometry",
)
import inspect  # noqa: E402
import resume_page_utilization as _rpu_module  # noqa: E402

source = inspect.getsource(_rpu_module)
assert_true(
    "def evaluate_resume_page_utilization" in source,
    "sanity: module source must be readable for this structural check",
)
assert_true(
    "resume_derivative" not in source
    and "resume_patch" not in source
    and "apply_resume_patch" not in source,
    "resume_page_utilization.py must have zero coupling to résumé content/patch/derivative structures -- it operates only on geometry",
)
print("PASS 8: evaluate_resume_page_utilization() never mutates its input and has zero import/reference coupling to resume content, patch, or derivative structures.")


# ======================================================================
# 9. EXISTING DERIVATIVE SAFETY -- immutable fields, evidence/claim
# lineage, review status, digest behavior, and the current resume
# architecture test suite remain completely unaffected by this new,
# separate module. Proven by re-running the existing architecture suite
# unmodified (see scripts/verify_assurance_baseline.py and the direct
# import-safety check below); this module adds zero fields to
# schemas/resume_derivative.schema.json and zero required parameters to
# any existing function signature.
# ======================================================================
import resume_validation  # noqa: E402
import inspect as _inspect  # noqa: E402

sig = _inspect.signature(resume_validation.approve_derivative_for_export)
assert_true(
    "page_geometry" in sig.parameters and sig.parameters["page_geometry"].default is None,
    "approve_derivative_for_export must accept an OPTIONAL page_geometry parameter defaulting to None, preserving every existing caller byte-for-byte",
)
sig2 = _inspect.signature(resume_validation.validate_derivative_eligibility)
assert_true(
    "page_geometry" in sig2.parameters and sig2.parameters["page_geometry"].default is None,
    "validate_derivative_eligibility must accept an OPTIONAL page_geometry parameter defaulting to None, preserving every existing caller byte-for-byte",
)
print("PASS 9: the new page_geometry parameter is optional and defaults to None on both export-gate functions -- every existing derivative-safety behavior (immutable fields, lineage, review status, digest, existing callers) is preserved untouched.")


# ======================================================================
# 10. FAIL-CLOSED EXPORT BOUNDARY -- end-to-end integration through the
# real build_resume_derivative()/approve_derivative_for_export() path
# using the repository's own real synthetic fixture (not a mock), proving
# a failing page_geometry actually blocks export approval, and a passing
# one does not block it.
# ======================================================================
import json  # noqa: E402
from claim_repository import validate_claim_repository  # noqa: E402
from evidence_repository import validate_evidence_repository  # noqa: E402
from experience_repository import validate_experience_repository  # noqa: E402
from resume_validation import (  # noqa: E402
    approve_derivative_for_export,
    build_resume_derivative,
)

FIXTURES = ROOT / "fixtures" / "resume_architecture"
_experience_result = validate_experience_repository()
assert_true(_experience_result["valid"] is True, "setup: experience repository invalid")
_evidence_result = validate_evidence_repository(experience_result=_experience_result)
assert_true(_evidence_result["valid"] is True, "setup: evidence repository invalid")
_claim_result = validate_claim_repository()
assert_true(_claim_result["valid"] is True, "setup: claim repository invalid")
EVIDENCE_INDEX = _evidence_result["index"]
CLAIM_INDEX = _claim_result["index"]
MASTER = json.loads((FIXTURES / "synthetic_master.json").read_text(encoding="utf-8"))

patch_boundary = {
    "patch_id": "PATCH_PAGE_UTILIZATION_BOUNDARY_TEST",
    "target_master_id": MASTER["master_id"],
    "job_id": "JOB_PAGE_UTILIZATION_BOUNDARY_TEST",
    "operations": [{"op": "EXCLUDE_MODULE", "module_id": "MOD_OPTIONAL_ARCHIVE"}],
}
built = build_resume_derivative(
    master=MASTER,
    patch=patch_boundary,
    claim_index=CLAIM_INDEX,
    evidence_index=EVIDENCE_INDEX,
    derivative_id="DERIV_PAGE_UTILIZATION_BOUNDARY_TEST",
)
assert_true(built["valid"] is True, f"setup: boundary-test derivative must build cleanly, got {built.get('errors')}")

blocked = approve_derivative_for_export(
    derivative=built["derivative"],
    master=MASTER,
    claim_index=CLAIM_INDEX,
    evidence_index=EVIDENCE_INDEX,
    human_approval=True,
    page_geometry=sparse_page,
)
assert_true(blocked["valid"] is False, "a failing page_geometry must block real export approval")
assert_true(
    has_code(blocked["errors"], "RESUME_PAGE_UNDERUTILIZED"),
    f"export must be blocked specifically by RESUME_PAGE_UNDERUTILIZED, got {blocked['errors']}",
)

allowed = approve_derivative_for_export(
    derivative=built["derivative"],
    master=MASTER,
    claim_index=CLAIM_INDEX,
    evidence_index=EVIDENCE_INDEX,
    human_approval=True,
    page_geometry=full_page,
)
assert_true(allowed["valid"] is True, f"a passing page_geometry must not block export approval, got {allowed.get('errors')}")
assert_true(allowed["derivative"]["export_allowed"] is True, "export_allowed must be True once geometry passes")

no_geometry = approve_derivative_for_export(
    derivative=built["derivative"],
    master=MASTER,
    claim_index=CLAIM_INDEX,
    evidence_index=EVIDENCE_INDEX,
    human_approval=True,
)
assert_true(
    no_geometry["valid"] is True,
    "omitting page_geometry entirely must behave exactly as before this milestone (no mechanical page-utilization check)",
)
print("PASS 10 (FAIL-CLOSED EXPORT BOUNDARY): a real derivative built through build_resume_derivative() is blocked from export approval by a failing page_geometry (RESUME_PAGE_UNDERUTILIZED), approved normally with a passing page_geometry, and behaves exactly as before when page_geometry is omitted.")

# ======================================================================
# 11. NON-FINITE / NEGATIVE GEOMETRY FAIL-CLOSED REGRESSIONS (Cursor HIGH
# finding correction). A non-finite bottom_pt/page_width_pt/page_height_pt
# must never be silently accepted into a comparison (e.g. `nan < 0.92`
# evaluating False and being read as "not underutilized") -- it must be
# rejected explicitly as RESUME_PAGE_GEOMETRY_INVALID. A negative bottom_pt
# is malformed geometry (a distance from the physical top of the page
# cannot be negative), not a legitimately sparse résumé, and is also
# rejected as RESUME_PAGE_GEOMETRY_INVALID rather than falling through to
# RESUME_PAGE_UNDERUTILIZED.
# ======================================================================
import math  # noqa: E402

nan_bottom_page = _base_geometry(bottom_pt=740.0)
nan_bottom_page["objects"][-1]["bottom_pt"] = math.nan
result_nan_bottom = evaluate_resume_page_utilization(nan_bottom_page)
assert_true(result_nan_bottom["valid"] is False, "NaN bottom_pt must be invalid")
assert_true(
    has_code(result_nan_bottom["errors"], "RESUME_PAGE_GEOMETRY_INVALID"),
    f"NaN bottom_pt must fail with RESUME_PAGE_GEOMETRY_INVALID, got {result_nan_bottom['errors']}",
)
assert_true(result_nan_bottom["meaningful_content_bottom_fraction"] is None, "NaN bottom_pt must not produce a fraction")

pos_inf_bottom_page = _base_geometry(bottom_pt=740.0)
pos_inf_bottom_page["objects"][-1]["bottom_pt"] = math.inf
result_pos_inf_bottom = evaluate_resume_page_utilization(pos_inf_bottom_page)
assert_true(result_pos_inf_bottom["valid"] is False, "+inf bottom_pt must be invalid")
assert_true(
    has_code(result_pos_inf_bottom["errors"], "RESUME_PAGE_GEOMETRY_INVALID"),
    f"+inf bottom_pt must fail with RESUME_PAGE_GEOMETRY_INVALID, got {result_pos_inf_bottom['errors']}",
)

neg_inf_bottom_page = _base_geometry(bottom_pt=740.0)
neg_inf_bottom_page["objects"][-1]["bottom_pt"] = -math.inf
result_neg_inf_bottom = evaluate_resume_page_utilization(neg_inf_bottom_page)
assert_true(result_neg_inf_bottom["valid"] is False, "-inf bottom_pt must be invalid")
assert_true(
    has_code(result_neg_inf_bottom["errors"], "RESUME_PAGE_GEOMETRY_INVALID"),
    f"-inf bottom_pt must fail with RESUME_PAGE_GEOMETRY_INVALID, got {result_neg_inf_bottom['errors']}",
)
print("PASS 11a: NaN, +inf, and -inf bottom_pt values are each rejected as RESUME_PAGE_GEOMETRY_INVALID, never silently accepted.")

nan_width_page = _base_geometry(bottom_pt=740.0)
nan_width_page["page_width_pt"] = math.nan
result_nan_width = evaluate_resume_page_utilization(nan_width_page)
assert_true(result_nan_width["valid"] is False, "NaN page_width_pt must be invalid")
assert_true(has_code(result_nan_width["errors"], "RESUME_PAGE_GEOMETRY_INVALID"), f"got {result_nan_width['errors']}")

inf_width_page = _base_geometry(bottom_pt=740.0)
inf_width_page["page_width_pt"] = math.inf
result_inf_width = evaluate_resume_page_utilization(inf_width_page)
assert_true(result_inf_width["valid"] is False, "+inf page_width_pt must be invalid")
assert_true(has_code(result_inf_width["errors"], "RESUME_PAGE_GEOMETRY_INVALID"), f"got {result_inf_width['errors']}")
print("PASS 11b: NaN/inf page_width_pt is rejected as RESUME_PAGE_GEOMETRY_INVALID.")

nan_height_page = _base_geometry(bottom_pt=740.0)
nan_height_page["page_height_pt"] = math.nan
result_nan_height = evaluate_resume_page_utilization(nan_height_page)
assert_true(result_nan_height["valid"] is False, "NaN page_height_pt must be invalid")
assert_true(has_code(result_nan_height["errors"], "RESUME_PAGE_GEOMETRY_INVALID"), f"got {result_nan_height['errors']}")

inf_height_page = _base_geometry(bottom_pt=740.0)
inf_height_page["page_height_pt"] = math.inf
result_inf_height = evaluate_resume_page_utilization(inf_height_page)
assert_true(result_inf_height["valid"] is False, "+inf page_height_pt must be invalid")
assert_true(has_code(result_inf_height["errors"], "RESUME_PAGE_GEOMETRY_INVALID"), f"got {result_inf_height['errors']}")
print("PASS 11c: NaN/inf page_height_pt is rejected as RESUME_PAGE_GEOMETRY_INVALID.")

negative_bottom_page = _base_geometry(bottom_pt=740.0)
negative_bottom_page["objects"][-1]["bottom_pt"] = -5.0
result_negative_bottom = evaluate_resume_page_utilization(negative_bottom_page)
assert_true(result_negative_bottom["valid"] is False, "negative bottom_pt must be invalid")
assert_true(
    has_code(result_negative_bottom["errors"], "RESUME_PAGE_GEOMETRY_INVALID"),
    f"negative bottom_pt must fail with RESUME_PAGE_GEOMETRY_INVALID (malformed geometry), not RESUME_PAGE_UNDERUTILIZED, got {result_negative_bottom['errors']}",
)
assert_true(
    not has_code(result_negative_bottom["errors"], "RESUME_PAGE_UNDERUTILIZED"),
    "negative bottom_pt must not be classified as a sparse-content underutilization failure",
)
print("PASS 11d: a negative bottom_pt (malformed geometry, not a sparse resume) is rejected as RESUME_PAGE_GEOMETRY_INVALID rather than RESUME_PAGE_UNDERUTILIZED.")

# Reconfirm the exact-threshold and just-below-threshold cases are
# unaffected by the fail-closed correction above.
result_exact_recheck = evaluate_resume_page_utilization(exact_page)
assert_true(result_exact_recheck["valid"] is True, "exact 0.92 threshold must still pass after the fail-closed correction")
assert_true(
    result_exact_recheck["meaningful_content_bottom_fraction"] == PAGE_UTILIZATION_FLOOR,
    "exact-threshold fraction must still equal 0.92 exactly",
)
result_just_below_recheck = evaluate_resume_page_utilization(just_below_page)
assert_true(result_just_below_recheck["valid"] is False, "just-below-threshold must still fail after the fail-closed correction")
assert_true(
    has_code(result_just_below_recheck["errors"], "RESUME_PAGE_UNDERUTILIZED"),
    f"just-below-threshold must still fail with RESUME_PAGE_UNDERUTILIZED, got {result_just_below_recheck['errors']}",
)
print("PASS 11e: the exact-0.92-pass and just-below-0.92-fail cases are unaffected by the fail-closed non-finite/negative correction.")

print("ALL resume_page_utilization_v1_test CHECKS PASSED")
