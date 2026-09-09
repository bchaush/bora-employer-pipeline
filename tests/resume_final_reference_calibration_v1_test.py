"""Regression tests for BORA_RESUME_FINAL_REFERENCE_CALIBRATION_V1.

Bora further hand-tweaked the Cable One package and explicitly approved
`Bora_Chaush_Cable_One_Business_Analyst_I_v2(1).docx` as the final
human-approved resume presentation reference, superseding the Spy Pond
exemplar (BLUEPRINT.md Section 141) only as the latest presentation
reference -- never as a source of Candidate Truth. BLUEPRINT.md
Section 141 subsections 141.6-141.9
(`BORA_RESUME_FINAL_REFERENCE_CALIBRATION_V1`) lock that artifact,
research-backed recruiter/ATS writing constraints, and a bounded
Claude-first drafting pilot, recorded in full at
`docs/resume/BORA_CABLE_ONE_FINAL_REFERENCE_V1.json`. This calibration
is recorded as Section 141 subsections rather than a new top-level
section so that the pinned `latest_locked_section=141` in
`tests/resume_reference_style_lock_v1_test.py` and the live
`src/career_os_state.py` max-heading validator both stay consistent.

This is a doctrine-record consistency check, not a resume generator or
renderer (no generator/renderer/automated-validator implementation is
authorized by §141.6-§141.9 -- see §141.9's Doctrine-only lock
subsection).
"""

from __future__ import annotations

import json
import re
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
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
    RECORD = json.loads(FINAL_REFERENCE_PATH.read_text(encoding="utf-8"))
except Exception:
    print(f"FAIL: could not load final-reference JSON at {FINAL_REFERENCE_PATH}")
    traceback.print_exc(file=sys.stdout)
    sys.stdout.flush()
    raise SystemExit(1)

try:
    GOLD = json.loads(GOLD_REFERENCE_PATH.read_text(encoding="utf-8"))
except Exception:
    print(f"FAIL: could not load prior gold-reference JSON at {GOLD_REFERENCE_PATH}")
    traceback.print_exc(file=sys.stdout)
    sys.stdout.flush()
    raise SystemExit(1)


# ======================================================================
# 1. The final-reference record itself encodes the exact acceptance-
# condition artifact identity: SHA-256, supersession scope, and the
# confirmed-unchanged Section 141 presentation grammar.
# ======================================================================
def _test_1() -> None:
    assert_true(RECORD["record_id"] == "BORA_CABLE_ONE_FINAL_REFERENCE_V1", "record_id must match")
    assert_true(RECORD["blueprint_section"] == 141, "blueprint_section must point at Section 141 (this calibration is recorded as §141 subsections, not a new top-level section)")
    assert_true(
        RECORD["blueprint_subsections"] == ["141.6", "141.7", "141.8", "141.9"],
        f"blueprint_subsections must be the locked §141.6-§141.9 set, got {RECORD['blueprint_subsections']}",
    )

    artifact = RECORD["source_artifact"]
    assert_true(
        artifact["name"] == "Bora_Chaush_Cable_One_Business_Analyst_I_v2(1).docx",
        f"source_artifact.name must match the Bora-approved artifact filename, got {artifact['name']!r}",
    )
    sha = artifact["sha256"]
    assert_true(
        sha == "236179c98b0e3ef68f7e79e392d73e57db41acb6f8493b0a7ab9eb8b2b353955",
        f"final reference SHA-256 must match the Bora-approved artifact, got {sha!r}",
    )
    assert_true(bool(re.fullmatch(r"[0-9a-f]{64}", sha)), f"sha256 must be well-formed, got {sha!r}")
    assert_true(artifact["stored_in_repository"] is False, "binary must not be stored in the repository")

    supersedes = RECORD["supersedes"]
    assert_true(
        "BORA_SPY_POND_GOLD_REFERENCE_V1" in supersedes["prior_reference"],
        f"supersedes.prior_reference must name the Spy Pond gold reference, got {supersedes['prior_reference']!r}",
    )
    assert_true(
        supersedes["scope"] == "LATEST_PRESENTATION_REFERENCE_ONLY",
        f"supersedes.scope must be LATEST_PRESENTATION_REFERENCE_ONLY, got {supersedes['scope']!r}",
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
print("PASS 1: the final-reference record encodes the exact locked artifact identity, supersession scope, and confirmed-unchanged Section 141 grammar.")
sys.stdout.flush()


# ======================================================================
# 2. TELUS display label and GPA presentation are recorded as
# presentation choices only, never as authority to alter Candidate
# Truth or evidence provenance.
# ======================================================================
def _test_2() -> None:
    choices = RECORD["presentation_choices_not_truth"]
    for key in ("telus_display_label", "gpa_presentation"):
        entry = choices[key]
        assert_true(
            entry["rule"] == "PRESENTATION_CHOICE_ONLY",
            f"{key}.rule must be PRESENTATION_CHOICE_ONLY, got {entry['rule']!r}",
        )
    assert_true(
        "Candidate Truth" in choices["telus_display_label"]["description"],
        "telus_display_label description must reference Candidate Truth constraints",
    )
    assert_true(
        "Candidate Truth" in choices["gpa_presentation"]["description"],
        "gpa_presentation description must reference Candidate Truth constraints",
    )


_run("_test_2", _test_2)
print("PASS 2: TELUS display label and GPA presentation are recorded as presentation choices only, gated against silently altering Candidate Truth.")
sys.stdout.flush()


# ======================================================================
# 3. The research-backed writing constraints are present, each carrying
# the rule the acceptance conditions require, and reference their
# research basis.
# ======================================================================
def _test_3() -> None:
    constraints = RECORD["writing_constraints"]
    expected_rules = {
        "human_readability_over_density": "READABILITY_OUTRANKS_KEYWORD_DENSITY",
        "summary_style": "SHORT_NATURAL_POSITIONING_PARAGRAPH",
        "bullet_style": "ACTION_CONTEXT_OUTCOME_WHEN_SUPPORTED",
        "quantification_discipline": "QUANTIFY_ONLY_WHEN_SUPPORTED_AND_MATERIAL",
        "jd_terminology_use": "CROSSWALK_GATED_NATURAL_DISTRIBUTION",
        "skills_priority": "ROLE_RELEVANT_EVIDENCE_BACKED_ONLY",
        "coherent_narrative": "ONE_COHERENT_EARLY_CAREER_STORY",
    }
    for key, expected_rule in expected_rules.items():
        assert_true(key in constraints, f"writing_constraints must include {key!r}")
        assert_true(
            constraints[key]["rule"] == expected_rule,
            f"writing_constraints[{key!r}].rule must be {expected_rule!r}, got {constraints[key]['rule']!r}",
        )

    assert_true(
        "keyword inventory" in constraints["summary_style"]["description"],
        "summary_style description must forbid becoming a keyword inventory",
    )
    assert_true(
        "without inventing impact" in constraints["bullet_style"]["description"],
        "bullet_style description must forbid inventing impact when no outcome exists",
    )
    assert_true(
        "never manufactured" in constraints["quantification_discipline"]["description"],
        "quantification_discipline description must forbid manufactured numbers",
    )
    assert_true(
        "140.4" in constraints["jd_terminology_use"]["description"],
        "jd_terminology_use description must reference the Section 140.4 crosswalk",
    )

    research_basis = RECORD["research_basis"]
    assert_true(
        any("VETS" in item for item in research_basis),
        "research_basis must include DOL VETS Resume Essentials",
    )
    assert_true(
        any("Yale" in item for item in research_basis),
        "research_basis must include Yale Office of Career Strategy",
    )
    assert_true(len(research_basis) >= 5, "research_basis must retain all cited sources")


_run("_test_3", _test_3)
print("PASS 3: research-backed writing constraints and their research basis are present and correctly encoded.")
sys.stdout.flush()


# ======================================================================
# 4. The Claude-first drafting pilot is authorized with the exact input
# restriction and prohibition boundaries the acceptance conditions
# require, and stays explicitly bound to the existing AI Boundaries.
# ======================================================================
def _test_4() -> None:
    pilot = RECORD["claude_drafting_pilot"]
    assert_true(
        pilot["authorized_stage"] == "PRODUCE PACKAGE",
        f"claude_drafting_pilot.authorized_stage must be 'PRODUCE PACKAGE', got {pilot['authorized_stage']!r}",
    )
    inputs = set(pilot["claude_receives_only"])
    expected_inputs = {
        "the exact verified JD",
        "the approved Requirement/EvidenceMatch crosswalk",
        "approved Candidate Truth/evidence modules",
        "current reference grammar (BLUEPRINT.md Section 141 and this record)",
    }
    assert_true(inputs == expected_inputs, f"claude_receives_only must match exactly, got {inputs}")

    forbidden = set(pilot["claude_may_not"])
    for must_forbid in (
        "infer facts",
        "infer tools",
        "infer metrics",
        "infer outcomes",
        "infer qualification states",
        "create unsupported achievements",
        "rename formal titles",
        "manufacture technologies",
        "invent metrics",
        "change dates",
        "bypass lineage validation",
        "directly modify the protected master",
    ):
        assert_true(
            must_forbid in forbidden,
            f"claude_may_not must forbid {must_forbid!r}, got {forbidden}",
        )

    g_responsibilities = set(pilot["g_responsibilities"])
    for required in (
        "orchestration",
        "truth/evidence adjudication",
        "rejection of unsupported Claude language",
        "final reference-grammar conformance",
        "rendered DOCX QA",
        "hyperlink verification",
        "the human approval gate",
    ):
        assert_true(
            required in g_responsibilities,
            f"g_responsibilities must retain {required!r}, got {g_responsibilities}",
        )

    assert_true(
        "AI Boundaries" in pilot["relationship_to_resume_mdc_ai_boundaries"],
        "pilot must explicitly bind itself to the existing resume.mdc AI Boundaries",
    )
    assert_true(
        "does not loosen" in pilot["relationship_to_resume_mdc_ai_boundaries"],
        "pilot must explicitly state it does not loosen the existing AI Boundaries",
    )

    must_never = RECORD["role_tailoring_boundary"]["must_never"]
    assert_true(
        any("create facts or make consequential pursuit/qualification decisions" in item for item in must_never),
        f"role_tailoring_boundary.must_never must forbid granting Claude fact-creation or consequential decision authority, got {must_never}",
    )


_run("_test_4", _test_4)
print("PASS 4: the Claude-first drafting pilot is authorized with the exact input restriction, prohibition, and G-responsibility boundaries, bound to the existing AI Boundaries.")
sys.stdout.flush()


# ======================================================================
# 5. Prior doctrine (Section 134/137/140/141) is restated/cross-
# referenced, never redefined, and the non-goals explicitly exclude a
# generator, renderer, or unsupervised Claude drafting runtime.
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
# BLUEPRINT.md carries locked §141.6-§141.9 subsections pointing at the
# final reference's SHA-256, and .cursor/rules/resume.mdc cross-
# references them, without introducing any new top-level section.
#
# project_state.json's blueprint_version/latest_locked_section are
# deliberately NOT bumped by this milestone (no new top-level section
# was introduced to bump them to):
# tests/resume_reference_style_lock_v1_test.py (a required test for this
# milestone that this milestone's allowed_paths does not permit editing)
# pins those exact fields to "3.13"/141, as does the "**Final Locked
# Blueprint v3.13**" substring it requires in BLUEPRINT.md. Bumping
# either would break that required, non-editable test, so §141.6-§141.9
# are appended as subsections without renumbering the version banner or
# advancing project_state.json's locked-section pointer.
# ======================================================================
def _test_6() -> None:
    blueprint_text = BLUEPRINT_PATH.read_text(encoding="utf-8")
    assert_true(
        "**141.6 Final reference calibration" in blueprint_text,
        "BLUEPRINT.md must carry a locked §141.6 subsection for BORA_RESUME_FINAL_REFERENCE_CALIBRATION_V1",
    )
    assert_true(
        "BORA_RESUME_FINAL_REFERENCE_CALIBRATION_V1" in blueprint_text,
        "BLUEPRINT.md must name BORA_RESUME_FINAL_REFERENCE_CALIBRATION_V1",
    )
    for subsection_marker in ("**141.7 Research-backed", "**141.8 Bounded Claude-first", "**141.9 Doctrine-only lock"):
        assert_true(
            subsection_marker in blueprint_text,
            f"BLUEPRINT.md must carry the {subsection_marker!r} subsection heading",
        )
    assert_true(
        RECORD["source_artifact"]["sha256"] in blueprint_text,
        "BLUEPRINT.md §141.6 must record the same final-reference SHA-256 as the JSON record",
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
        "§141.6" in mdc_text and "BORA_RESUME_FINAL_REFERENCE_CALIBRATION_V1" in mdc_text,
        ".cursor/rules/resume.mdc must operationally cross-reference BLUEPRINT.md §141.6",
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
print("PASS 6: BLUEPRINT.md §141.6-§141.9 and .cursor/rules/resume.mdc cross-reference this lock; no new top-level section was introduced, and Section 141 / the pinned v3.13/141 project_state.json fields remain intact for resume_reference_style_lock_v1_test.py and the live max-heading validator.")
sys.stdout.flush()


# ======================================================================
# 7. This record never claims authority over Candidate Truth -- the
# never-a-source-of-Candidate-Truth language is present and the prior
# Section 141 gold-reference record's own equivalent authority-scope
# language remains intact (not silently weakened by this milestone).
# ======================================================================
def _test_7() -> None:
    scope = RECORD["role_tailoring_boundary"].get("final_reference_authority_scope", "")
    assert_true(
        "never a source of Candidate Truth" in scope,
        f"role_tailoring_boundary.final_reference_authority_scope must retain 'never a source of Candidate Truth', got {scope!r}",
    )
    assert_true(
        "claim-evidence lineage" in scope or "claim/evidence lineage" in scope,
        f"authority-scope language must still require claim/evidence lineage for substantive facts, got {scope!r}",
    )

    must_never = RECORD["role_tailoring_boundary"]["must_never"]
    assert_true(
        any("Cable One v2 exemplar" in item for item in must_never),
        f"role_tailoring_boundary.must_never must forbid inventing/copying facts merely because they appear in the Cable One v2 exemplar, got {must_never}",
    )
    assert_true(
        any("external resume-writing research" in item for item in must_never),
        f"role_tailoring_boundary.must_never must forbid letting external research override the human-approved reference grammar, got {must_never}",
    )

    prior_scope = GOLD["role_tailoring_boundary"].get("gold_reference_authority_scope", "")
    assert_true(
        "never a source of Candidate Truth" in prior_scope,
        "the prior Section 141 gold-reference record's authority-scope language must remain intact, unweakened by this milestone",
    )


_run("_test_7", _test_7)
print("PASS 7: this record's Candidate Truth authority-scope boundary is present, and the prior Section 141 record's equivalent boundary remains intact and unweakened.")
sys.stdout.flush()

print("ALL resume_final_reference_calibration_v1_test CHECKS PASSED")
sys.stdout.flush()
