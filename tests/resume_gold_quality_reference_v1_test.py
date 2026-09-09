"""Regression tests for BORA_RESUME_GOLD_QUALITY_REFERENCE_V1.

Bora explicitly approved the Claude-first, G-adjudicated Cable One DOCX
(`Bora_Chaush_Cable_One_Claude_First_G_Adjudicated.docx`) as the
gold-quality resume package acceptance reference for future Career OS
packages, superseding the Cable One v2 exemplar
(`BORA_RESUME_FINAL_REFERENCE_CALIBRATION_V1`, BLUEPRINT.md
§141.6-§141.9) and the Spy Pond exemplar (BLUEPRINT.md §141) only as the
latest resume package quality/presentation acceptance reference -- never
as a source of Candidate Truth. BLUEPRINT.md Section 141 subsections
141.10-141.12 (`BORA_RESUME_GOLD_QUALITY_REFERENCE_V1`) lock that
artifact and a final-package QA-dimension checklist, recorded in full at
`docs/resume/BORA_GOLD_QUALITY_REFERENCE_V1.json`. This lock is recorded
as Section 141 subsections rather than a new top-level section so that
the pinned `latest_locked_section=141` in
`tests/resume_reference_style_lock_v1_test.py` and the live
`src/career_os_state.py` max-heading validator both stay consistent.

This is a doctrine-record consistency check, not a resume generator or
renderer (no generator/renderer/automated-validator implementation is
authorized by §141.10-§141.12 -- see §141.12's Doctrine-only lock
subsection).
"""

from __future__ import annotations

import json
import re
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GOLD_QUALITY_PATH = ROOT / "docs" / "resume" / "BORA_GOLD_QUALITY_REFERENCE_V1.json"
FINAL_REFERENCE_PATH = ROOT / "docs" / "resume" / "BORA_CABLE_ONE_FINAL_REFERENCE_V1.json"
GOLD_REFERENCE_PATH = ROOT / "docs" / "resume" / "BORA_SPY_POND_GOLD_REFERENCE_V1.json"
BLUEPRINT_PATH = ROOT / "BLUEPRINT.md"
RESUME_MDC_PATH = ROOT / ".cursor" / "rules" / "resume.mdc"


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        print(f"FAIL: {message}")
        sys.stdout.flush()
        raise SystemExit(1)


def _run(name: str, fn) -> None:
    """Run one _test_N() case with an explicit, flushed diagnostic on any
    unexpected exception -- so a real defect never surfaces as a silent,
    unexplained crash with no visible output."""
    try:
        fn()
    except SystemExit:
        raise
    except Exception:
        print(f"FAIL: unexpected exception in {name}")
        traceback.print_exc(file=sys.stdout)
        sys.stdout.flush()
        raise SystemExit(1)


try:
    RECORD = json.loads(GOLD_QUALITY_PATH.read_text(encoding="utf-8"))
except Exception:
    print(f"FAIL: could not load gold-quality reference JSON at {GOLD_QUALITY_PATH}")
    traceback.print_exc(file=sys.stdout)
    sys.stdout.flush()
    raise SystemExit(1)

try:
    FINAL_REFERENCE = json.loads(FINAL_REFERENCE_PATH.read_text(encoding="utf-8"))
except Exception:
    print(f"FAIL: could not load prior final-reference JSON at {FINAL_REFERENCE_PATH}")
    traceback.print_exc(file=sys.stdout)
    sys.stdout.flush()
    raise SystemExit(1)

try:
    GOLD = json.loads(GOLD_REFERENCE_PATH.read_text(encoding="utf-8"))
except Exception:
    print(f"FAIL: could not load prior Spy Pond gold-reference JSON at {GOLD_REFERENCE_PATH}")
    traceback.print_exc(file=sys.stdout)
    sys.stdout.flush()
    raise SystemExit(1)


# ======================================================================
# 1. The gold-quality record itself encodes the exact acceptance-
# condition artifact identity: SHA-256, supersession scope over both
# prior exemplars, and the confirmed-unchanged Section 141 presentation
# grammar.
# ======================================================================
def _test_1() -> None:
    assert_true(RECORD["record_id"] == "BORA_GOLD_QUALITY_REFERENCE_V1", "record_id must match")
    assert_true(RECORD["blueprint_section"] == 141, "blueprint_section must point at Section 141 (this lock is recorded as §141 subsections, not a new top-level section)")
    assert_true(
        RECORD["blueprint_subsections"] == ["141.10", "141.11", "141.12"],
        f"blueprint_subsections must be the locked §141.10-§141.12 set, got {RECORD['blueprint_subsections']}",
    )

    artifact = RECORD["source_artifact"]
    assert_true(
        artifact["name"] == "Bora_Chaush_Cable_One_Claude_First_G_Adjudicated.docx",
        f"source_artifact.name must match the Bora-approved artifact filename, got {artifact['name']!r}",
    )
    sha = artifact["sha256"]
    assert_true(
        sha == "ec3a9f9c6e2fc429e01892f61a074a71319ec6586566b6c1cf60808eba2f3f70",
        f"gold-quality reference SHA-256 must match the Bora-approved artifact, got {sha!r}",
    )
    assert_true(bool(re.fullmatch(r"[0-9a-f]{64}", sha)), f"sha256 must be well-formed, got {sha!r}")
    assert_true(artifact["stored_in_repository"] is False, "binary must not be stored in the repository")

    supersedes = RECORD["supersedes"]
    prior_refs = " ".join(supersedes["prior_references"])
    assert_true(
        "BORA_CABLE_ONE_FINAL_REFERENCE_V1" in prior_refs,
        f"supersedes.prior_references must name the Cable One v2 final reference, got {supersedes['prior_references']}",
    )
    assert_true(
        "BORA_SPY_POND_GOLD_REFERENCE_V1" in prior_refs,
        f"supersedes.prior_references must name the Spy Pond gold reference, got {supersedes['prior_references']}",
    )
    assert_true(
        supersedes["scope"] == "LATEST_RESUME_PACKAGE_QUALITY_PRESENTATION_ACCEPTANCE_REFERENCE_ONLY",
        f"supersedes.scope must be LATEST_RESUME_PACKAGE_QUALITY_PRESENTATION_ACCEPTANCE_REFERENCE_ONLY, got {supersedes['scope']!r}",
    )
    assert_true(
        "never" in supersedes["description"].lower() and "candidate truth" in supersedes["description"].lower(),
        "supersedes.description must explicitly state this never supersedes anything as a source of Candidate Truth",
    )

    confirmation = RECORD["presentation_grammar_confirmation"]
    assert_true(
        confirmation["rule"] == "UNCHANGED_FROM_SECTION_141",
        f"presentation_grammar_confirmation.rule must be UNCHANGED_FROM_SECTION_141, got {confirmation['rule']!r}",
    )
    for token in (
        "PROFESSIONAL SUMMARY",
        "EDUCATION, SKILLS, WORK EXPERIENCE, RELEVANT PROJECT",
        "Title | Employer",
        "two-school",
        "92%",
    ):
        assert_true(
            token in confirmation["description"],
            f"presentation_grammar_confirmation.description must retain {token!r}",
        )


_run("_test_1", _test_1)
print("PASS 1: the gold-quality record encodes the exact locked artifact identity, dual-exemplar supersession scope, and confirmed-unchanged Section 141 grammar.")
sys.stdout.flush()


# ======================================================================
# 2. The final-package QA-dimension checklist covers all seven required
# dimensions with the exact rule tags the acceptance conditions require.
# ======================================================================
def _test_2() -> None:
    dims = RECORD["final_package_qa_dimensions"]
    expected_rules = {
        "truth_fidelity": "TRACES_ONLY_TO_APPROVED_CANDIDATE_TRUTH",
        "jd_evidence_coverage": "VERIFIED_CROSSWALK_COVERAGE",
        "human_naturalness": "RECRUITER_NATURAL_READABILITY",
        "interview_defensibility": "WORDING_A_CANDIDATE_CAN_DEFEND_LIVE",
        "reference_conformance": "CONFORMS_TO_SECTION_141_GRAMMAR",
        "rendered_one_page_quality": "ONE_PAGE_92_PERCENT_FLOOR",
        "functional_hyperlinks": "REAL_HYPERLINK_OBJECTS_VERIFIED",
    }
    for key, expected_rule in expected_rules.items():
        assert_true(key in dims, f"final_package_qa_dimensions must include {key!r}")
        assert_true(
            dims[key]["rule"] == expected_rule,
            f"final_package_qa_dimensions[{key!r}].rule must be {expected_rule!r}, got {dims[key]['rule']!r}",
        )

    assert_true(
        "NONE/UNKNOWN" in dims["jd_evidence_coverage"]["description"],
        "jd_evidence_coverage description must keep NONE/UNKNOWN requirements as visible gaps",
    )
    assert_true(
        "140.4" in dims["jd_evidence_coverage"]["description"],
        "jd_evidence_coverage description must reference the Section 140.4 crosswalk",
    )
    assert_true(
        dims["gate"]["rule"] == "ALL_DIMENSIONS_BEFORE_HUMAN_APPROVAL",
        f"final_package_qa_dimensions.gate.rule must be ALL_DIMENSIONS_BEFORE_HUMAN_APPROVAL, got {dims['gate']['rule']!r}",
    )


_run("_test_2", _test_2)
print("PASS 2: the final-package QA-dimension checklist covers all seven required dimensions plus the pre-approval gate, correctly encoded.")
sys.stdout.flush()


# ======================================================================
# 3. Truthful evidence-overlap, evidence-budget, coherent-narrative, and
# candidate-facing-translation requirements are present and correctly
# encoded, and never authorize keyword stuffing or gap-hiding.
# ======================================================================
def _test_3() -> None:
    crosswalk = RECORD["jd_to_evidence_crosswalk_requirement"]
    assert_true(crosswalk["rule"] == "VERIFIED_CROSSWALK_ONLY_NO_INVENTED_TOOLS", "jd_to_evidence_crosswalk_requirement.rule mismatch")
    assert_true("NONE or UNKNOWN" in crosswalk["description"], "crosswalk requirement must keep NONE/UNKNOWN tools/capabilities absent")

    budget = RECORD["evidence_budget_allocation"]
    assert_true(budget["rule"] == "STRONGEST_RELEVANT_EVIDENCE_SURFACED_WITHOUT_HIDING_GAPS", "evidence_budget_allocation.rule mismatch")
    assert_true("most evidence space" in budget["description"], "evidence_budget_allocation must state the strongest experience gets the most space")
    assert_true("hiding" in budget["description"], "evidence_budget_allocation must forbid hiding a material gap")

    narrative = RECORD["coherent_narrative_requirement"]
    assert_true(narrative["rule"] == "ONE_COHERENT_HUMAN_CAREER_STORY", "coherent_narrative_requirement.rule mismatch")
    assert_true("disconnected keyword blocks" in narrative["description"], "coherent_narrative_requirement must reject disconnected keyword blocks")

    translation = RECORD["candidate_facing_translation_requirement"]
    assert_true(translation["rule"] == "RECRUITER_NATURAL_LANGUAGE_ONLY", "candidate_facing_translation_requirement.rule mismatch")
    assert_true(
        "Career OS" in translation["description"] and "AI-process" in translation["description"],
        "candidate_facing_translation_requirement must require translating internal Career OS/AI-process terminology",
    )

    bullets = RECORD["bullet_and_quantification_discipline"]
    assert_true(bullets["rule"] == "ACTION_CONTEXT_OUTCOME_NO_MANUFACTURED_METRICS", "bullet_and_quantification_discipline.rule mismatch")
    assert_true("without manufacturing impact" in bullets["description"], "bullet discipline must forbid manufacturing impact")
    assert_true(
        any("141.7" in item for item in bullets["extends_not_replaces"]),
        "bullet_and_quantification_discipline must extend Section 141.7's writing constraints, not replace them",
    )

    norma = RECORD["norma_resume_comparison_boundary"]
    assert_true(norma["rule"] == "COMPARISON_EVIDENCE_ONLY_NEVER_A_BORA_TEMPLATE", "norma_resume_comparison_boundary.rule mismatch")
    assert_true(
        "never become a second Bora template" in norma["description"],
        "norma_resume_comparison_boundary must forbid becoming a second Bora template",
    )


_run("_test_3", _test_3)
print("PASS 3: JD/evidence crosswalk, evidence-budget, coherent-narrative, candidate-facing-translation, bullet/quantification, and Norma_Resume comparison boundaries are present and correctly encoded.")
sys.stdout.flush()


# ======================================================================
# 4. The Claude-first drafting pilot is reaffirmed unchanged from
# Section 141.8, not redefined or loosened.
# ======================================================================
def _test_4() -> None:
    pilot = RECORD["claude_drafting_pilot_reaffirmed"]
    assert_true(pilot["rule"] == "UNCHANGED_FROM_SECTION_141_8", f"claude_drafting_pilot_reaffirmed.rule must be UNCHANGED_FROM_SECTION_141_8, got {pilot['rule']!r}")
    assert_true("141.8" in pilot["description"], "claude_drafting_pilot_reaffirmed must reference Section 141.8")
    assert_true(
        "does not loosen" in pilot["description"],
        "claude_drafting_pilot_reaffirmed must explicitly state it does not loosen the existing AI Boundaries",
    )

    must_never = RECORD["role_tailoring_boundary"]["must_never"]
    assert_true(
        any("create facts or make consequential pursuit/qualification decisions" in item for item in must_never),
        f"role_tailoring_boundary.must_never must forbid granting Claude fact-creation or consequential decision authority, got {must_never}",
    )
    assert_true(
        any("keyword stuffing" in item for item in must_never),
        f"role_tailoring_boundary.must_never must forbid keyword stuffing/unsupported tools/invented results, got {must_never}",
    )


_run("_test_4", _test_4)
print("PASS 4: the Claude-first drafting pilot is reaffirmed unchanged from Section 141.8, and the role-tailoring boundary forbids fact invention, consequential AI authority, and keyword stuffing.")
sys.stdout.flush()


# ======================================================================
# 5. Prior doctrine (Sections 134/137/140/141/141.7/141.8) is restated/
# cross-referenced, never redefined, and the non-goals explicitly
# exclude a generator, renderer, or unsupervised Claude drafting runtime.
# ======================================================================
def _test_5() -> None:
    unchanged = RECORD["unchanged_doctrine"]
    for token in (
        "Section 137",
        "Section 140.1",
        "Section 134",
        "Section 140.4",
        "Section 140.6",
        "Section 141",
        "Section 141.7",
        "Section 141.8",
        "Candidate Truth, Match Truth, and qualification/pursuit runtime logic",
    ):
        assert_true(
            any(token in item for item in unchanged),
            f"unchanged_doctrine must retain a reference to {token!r}, got {unchanged}",
        )

    non_goals = RECORD["non_goals"]["excludes"]
    assert_true(
        any("generator or renderer" in item for item in non_goals),
        "non_goals.excludes must exclude a DOCX/PDF generator or renderer",
    )
    assert_true(
        any("autonomous or unsupervised Claude drafting runtime" in item for item in non_goals),
        "non_goals.excludes must exclude an autonomous or unsupervised Claude drafting runtime",
    )


_run("_test_5", _test_5)
print("PASS 5: prior doctrine is restated/cross-referenced rather than redefined, and non-goals exclude a generator/renderer and an unsupervised Claude drafting runtime.")
sys.stdout.flush()


# ======================================================================
# 6. The doctrine surfaces actually cross-reference this lock --
# BLUEPRINT.md carries locked §141.10-§141.12 subsections pointing at
# the gold-quality reference's SHA-256, and .cursor/rules/resume.mdc
# cross-references them, without introducing any new top-level section.
#
# project_state.json's blueprint_version/latest_locked_section are
# deliberately NOT bumped by this milestone (no new top-level section
# was introduced to bump them to): tests/resume_reference_style_lock_v1_test.py
# (a required test for this milestone that this milestone's
# allowed_paths does not permit editing) pins those exact fields to
# "3.13"/141, as does the "**Final Locked Blueprint v3.13**" substring it
# requires in BLUEPRINT.md. Bumping either would break that required,
# non-editable test, so §141.10-§141.12 are appended as subsections
# without renumbering the version banner or advancing
# project_state.json's locked-section pointer.
# ======================================================================
def _test_6() -> None:
    blueprint_text = BLUEPRINT_PATH.read_text(encoding="utf-8")
    assert_true(
        "**141.10 Gold-quality acceptance reference" in blueprint_text,
        "BLUEPRINT.md must carry a locked §141.10 subsection for BORA_RESUME_GOLD_QUALITY_REFERENCE_V1",
    )
    assert_true(
        "BORA_RESUME_GOLD_QUALITY_REFERENCE_V1" in blueprint_text,
        "BLUEPRINT.md must name BORA_RESUME_GOLD_QUALITY_REFERENCE_V1",
    )
    for subsection_marker in ("**141.11 Final-package QA-dimension checklist", "**141.12 Doctrine-only lock"):
        assert_true(
            subsection_marker in blueprint_text,
            f"BLUEPRINT.md must carry the {subsection_marker!r} subsection heading",
        )
    assert_true(
        RECORD["source_artifact"]["sha256"] in blueprint_text,
        "BLUEPRINT.md §141.10 must record the same gold-quality reference SHA-256 as the JSON record",
    )
    assert_true(
        "**Final Locked Blueprint v3.13**" in blueprint_text,
        "BLUEPRINT.md version header must remain v3.13 -- resume_reference_style_lock_v1_test.py "
        "pins this exact substring and this milestone cannot edit that test",
    )
    assert_true(
        "**141. BORA RESUME REFERENCE STYLE LOCK — BORA_RESUME_REFERENCE_STYLE_LOCK_V1 (LOCKED)**" in blueprint_text,
        "BLUEPRINT.md must still carry the prior locked Section 141 heading unchanged",
    )
    assert_true(
        "**141.6 Final reference calibration" in blueprint_text,
        "BLUEPRINT.md must still carry the prior locked §141.6 subsection unchanged",
    )
    # No new top-level "**N. " heading may have been introduced -- the
    # live src/career_os_state.py validator computes the declared
    # latest_locked_section from the max top-level heading number, and
    # that must stay 141 to match the pinned resume_reference_style_lock
    # test and project_state.json.
    top_level_numbers = [int(m) for m in re.findall(r"^\*\*(\d+)\.\s", blueprint_text, flags=re.MULTILINE)]
    assert_true(
        max(top_level_numbers) == 141,
        f"no new top-level Blueprint section may exist above 141, got max {max(top_level_numbers)}",
    )

    mdc_text = RESUME_MDC_PATH.read_text(encoding="utf-8")
    assert_true(
        "§141.10" in mdc_text and "BORA_RESUME_GOLD_QUALITY_REFERENCE_V1" in mdc_text,
        ".cursor/rules/resume.mdc must operationally cross-reference BLUEPRINT.md §141.10",
    )

    state = json.loads((ROOT / "project_state.json").read_text(encoding="utf-8"))
    assert_true(
        state["blueprint_version"] == "3.13",
        f"project_state.json blueprint_version must remain 3.13 (pinned by resume_reference_style_lock_v1_test.py), got {state['blueprint_version']}",
    )
    assert_true(
        state["latest_locked_section"] == 141,
        f"project_state.json latest_locked_section must remain 141 (pinned by resume_reference_style_lock_v1_test.py), got {state['latest_locked_section']}",
    )


_run("_test_6", _test_6)
print("PASS 6: BLUEPRINT.md §141.10-§141.12 and .cursor/rules/resume.mdc cross-reference this lock; no new top-level section was introduced, and Section 141 / the pinned v3.13/141 project_state.json fields remain intact for resume_reference_style_lock_v1_test.py and the live max-heading validator.")
sys.stdout.flush()


# ======================================================================
# 7. This record never claims authority over Candidate Truth -- the
# never-a-source-of-Candidate-Truth language is present, and the prior
# Section 141 / 141.6 records' own equivalent authority-scope language
# remains intact (not silently weakened by this milestone).
# ======================================================================
def _test_7() -> None:
    scope = RECORD["role_tailoring_boundary"].get("gold_reference_authority_scope", "")
    assert_true(
        "never a source of Candidate Truth" in scope,
        f"role_tailoring_boundary.gold_reference_authority_scope must retain 'never a source of Candidate Truth', got {scope!r}",
    )
    assert_true(
        "claim-evidence lineage" in scope or "claim/evidence lineage" in scope,
        f"authority-scope language must still require claim/evidence lineage for substantive facts, got {scope!r}",
    )

    must_never = RECORD["role_tailoring_boundary"]["must_never"]
    assert_true(
        any("Claude-first, G-adjudicated Cable One exemplar" in item for item in must_never),
        f"role_tailoring_boundary.must_never must forbid inventing/copying facts merely because they appear in this exemplar, got {must_never}",
    )

    prior_final_scope = FINAL_REFERENCE["role_tailoring_boundary"].get("final_reference_authority_scope", "")
    assert_true(
        "never a source of Candidate Truth" in prior_final_scope,
        "the prior §141.6 final-reference record's authority-scope language must remain intact, unweakened by this milestone",
    )

    prior_gold_scope = GOLD["role_tailoring_boundary"].get("gold_reference_authority_scope", "")
    assert_true(
        "never a source of Candidate Truth" in prior_gold_scope,
        "the prior Section 141 gold-reference record's authority-scope language must remain intact, unweakened by this milestone",
    )


_run("_test_7", _test_7)
print("PASS 7: this record's Candidate Truth authority-scope boundary is present, and the prior §141 / §141.6 records' equivalent boundaries remain intact and unweakened.")
sys.stdout.flush()

print("ALL resume_gold_quality_reference_v1_test CHECKS PASSED")
sys.stdout.flush()
