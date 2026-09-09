"""Regression tests for BORA_RESUME_REFERENCE_STYLE_LOCK_V1.

Root cause reproduced live: a résumé package spawned for the Cable One
application drifted from Bora's actual approved presentation grammar (a
generic "PROFESSIONAL SUMMARY" heading, wrong default section order, an
employer-first-plus-italic-title work-entry line, internal Career OS
terminology leaking into candidate-facing skills text, Bulmarma
auto-inserted into the evidence roster, and internal/system jargon in
candidate-facing prose) with no mechanical check anywhere in the
repository capable of catching it. BLUEPRINT.md Section 141
(`BORA_RESUME_REFERENCE_STYLE_LOCK_V1`) locks Bora's explicitly approved
Spy Pond FINAL_REFERENCE_STYLE DOCX as the corrected canonical grammar,
recorded in full at `docs/resume/BORA_SPY_POND_GOLD_REFERENCE_V1.json`.

This is a doctrine-record consistency check, not a résumé generator or
renderer (no generator/renderer/automated-validator implementation is
authorized by §141 -- see its Doctrine-only lock subsection). The
`_find_drift_violations()` helper below is test-only, pure, in-memory
logic that exercises the locked JSON record against small synthetic
candidate structures; it is not wired into any export/build path.
"""

from __future__ import annotations

import json
import re
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
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
    GOLD = json.loads(GOLD_REFERENCE_PATH.read_text(encoding="utf-8"))
except Exception:
    print(f"FAIL: could not load gold-reference JSON at {GOLD_REFERENCE_PATH}")
    traceback.print_exc(file=sys.stdout)
    sys.stdout.flush()
    raise SystemExit(1)

# Internal Career OS vocabulary that must never leak into candidate-facing
# text (skills or prose). A small, bounded list matching the concrete
# examples §141.2 / the gold-reference record itself names.
_SKILLS_INTERNAL_TERMS = (
    "EvidenceMatch",
    "STRONG",
    "SUPPORTED",
    "PARTIAL",
    "module_id",
    "Claim_ID",
)
_PROSE_INTERNAL_TERMS = (
    "EvidenceMatch",
    "module_id",
    "Claim_ID",
    "human approval",
    "operating system",
    "Career OS",
)


def _find_drift_violations(candidate: dict, gold: dict) -> set[str]:
    """Pure, test-only check of a synthetic candidate résumé structure
    against the locked gold-reference grammar. Returns the set of
    drift_patterns_rejected ids the candidate violates."""
    violations: set[str] = set()
    grammar = gold["presentation_grammar"]

    if candidate.get("summary_heading") is not None:
        violations.add("DRIFT_PROFESSIONAL_SUMMARY_HEADING")

    if candidate.get("section_order") != grammar["section_order"]:
        violations.add("DRIFT_SECTION_ORDER")

    expected_work_grammar = grammar["work_entry_grammar"]["rule"]
    if any(
        entry.get("grammar") != expected_work_grammar
        for entry in candidate.get("work_entries", [])
    ):
        violations.add("DRIFT_EMPLOYER_FIRST_ITALIC_TITLE")

    skills_text = candidate.get("skills_text", "")
    if any(term in skills_text for term in _SKILLS_INTERNAL_TERMS):
        violations.add("DRIFT_INTERNAL_TAXONOMY_IN_SKILLS")

    roster = candidate.get("evidence_roster", [])
    not_automatic = grammar["evidence_roster"]["not_automatic"]
    if any(name in roster for name in not_automatic) and not candidate.get(
        "bulmarma_crosswalk_earned", False
    ):
        violations.add("DRIFT_BULMARMA_AUTO_INSERTED")

    prose_text = candidate.get("prose_text", "")
    if any(term.lower() in prose_text.lower() for term in _PROSE_INTERNAL_TERMS):
        violations.add("DRIFT_INTERNAL_JARGON_IN_PROSE")

    return violations


def _gold_candidate() -> dict:
    """A synthetic candidate structure that conforms exactly to the
    locked gold-reference grammar -- must trip zero drift violations."""
    grammar = GOLD["presentation_grammar"]
    return {
        "summary_heading": None,
        "section_order": list(grammar["section_order"]),
        "work_entries": [
            {"grammar": grammar["work_entry_grammar"]["rule"]},
            {"grammar": grammar["work_entry_grammar"]["rule"]},
        ],
        "skills_text": "Process & quality, Technical, Operations",
        "evidence_roster": list(grammar["evidence_roster"]["default_included"]),
        "bulmarma_crosswalk_earned": False,
        "prose_text": "Coordinated onboarding logistics for new hires and vendors.",
    }


def _cable_one_drift_candidate() -> dict:
    """A synthetic candidate structure reproducing every recorded Cable
    One drift pattern -- must trip every drift_patterns_rejected id."""
    return {
        "summary_heading": "PROFESSIONAL SUMMARY",
        "section_order": ["WORK EXPERIENCE", "EDUCATION", "SKILLS", "RELEVANT PROJECT"],
        "work_entries": [{"grammar": "EMPLOYER_FIRST_ITALIC_TITLE"}],
        "skills_text": "EvidenceMatch: STRONG, PARTIAL",
        "evidence_roster": ["Winter Walk", "Bulmarma"],
        "bulmarma_crosswalk_earned": False,
        "prose_text": "Obtained human approval within the Career OS operating system.",
    }


# ======================================================================
# 1. The gold-reference record itself encodes the acceptance-condition
# grammar exactly (SHA-256, section order, work/education/skills
# grammar, evidence roster, visual metrics).
# ======================================================================
def _test_1() -> None:
    assert_true(GOLD["record_id"] == "BORA_SPY_POND_GOLD_REFERENCE_V1", "record_id must match")
    assert_true(GOLD["blueprint_section"] == 141, "blueprint_section must point at Section 141")
    sha = GOLD["source_artifact"]["sha256"]
    assert_true(
        sha == "330b600e8cc18bd4edd4aa75422df903cdf8a230a6e97192094c89a254851d43",
        f"gold reference SHA-256 must match the Bora-approved artifact, got {sha!r}",
    )
    assert_true(bool(re.fullmatch(r"[0-9a-f]{64}", sha)), f"sha256 must be well-formed, got {sha!r}")

    grammar = GOLD["presentation_grammar"]
    assert_true(
        grammar["summary_heading"]["rule"] == "NO_PROFESSIONAL_SUMMARY_HEADING",
        "summary_heading rule must be NO_PROFESSIONAL_SUMMARY_HEADING",
    )
    assert_true(
        grammar["section_order"] == ["EDUCATION", "SKILLS", "WORK EXPERIENCE", "RELEVANT PROJECT"],
        f"section_order must be the locked default order, got {grammar['section_order']}",
    )
    assert_true(
        grammar["work_entry_grammar"]["rule"] == "TITLE_PIPE_EMPLOYER_SINGLE_BOLD_LINE",
        "work_entry_grammar must be the single-bold-line Title | Employer grammar",
    )
    assert_true(
        grammar["education_grammar"]["rule"] == "BOLD_SCHOOL_RIGHT_ALIGNED_DATE_DEGREE_LINE_BELOW",
        f"education_grammar.rule must be BOLD_SCHOOL_RIGHT_ALIGNED_DATE_DEGREE_LINE_BELOW, got {grammar['education_grammar']['rule']!r}",
    )
    education_description = grammar["education_grammar"]["description"]
    assert_true(
        "two-school" in education_description.lower(),
        "education_grammar description must retain the two-school gold-reference grammar language",
    )
    assert_true(
        "bold school" in education_description.lower(),
        "education_grammar description must retain the bold-school structural requirement",
    )
    assert_true(
        "right-aligned" in education_description,
        "education_grammar description must retain the right-aligned month-year date requirement",
    )
    assert_true(
        "degree line" in education_description.lower(),
        "education_grammar description must retain the degree-line-below structural requirement",
    )
    assert_true(
        "Brandeis GPA" in education_description,
        "education_grammar must record the Brandeis GPA retention rule",
    )
    assert_true(
        set(grammar["skills_grammar"]["rows_modeled_on"])
        == {"Process & quality", "Technical", "Operations"},
        f"skills rows must match the locked three rows, got {grammar['skills_grammar']['rows_modeled_on']}",
    )
    roster = grammar["evidence_roster"]
    assert_true(
        roster["default_included"]
        == ["Winter Walk", "TELUS Digital Bulgaria", "D Commerce Bank", "MarketMind"],
        f"default evidence roster must match, got {roster['default_included']}",
    )
    assert_true(
        "Bulmarma" in roster["not_automatic"],
        "Bulmarma must be recorded as not automatically inserted",
    )
    marketmind = grammar["marketmind_heading_grammar"]
    assert_true(
        marketmind["rule"] == "TECH_LABEL_PLUS_RIGHT_SIDE_GITHUB_LINK",
        f"marketmind_heading_grammar rule must be TECH_LABEL_PLUS_RIGHT_SIDE_GITHUB_LINK, got {marketmind['rule']!r}",
    )
    assert_true(
        "GitHub" in marketmind["description"] and "right-side" in marketmind["description"],
        "marketmind_heading_grammar description must require a right-side GitHub hyperlink",
    )
    assert_true(
        "hyperlink object" in marketmind["description"],
        "marketmind_heading_grammar description must require a genuine hyperlink object, not merely styled text",
    )

    prose_style = grammar["candidate_facing_prose_style"]
    assert_true(
        prose_style["rule"] == "HUMAN_EARLY_CAREER_CONCRETE_STYLE",
        f"candidate_facing_prose_style rule must be HUMAN_EARLY_CAREER_CONCRETE_STYLE, got {prose_style['rule']!r}",
    )
    prose_description = prose_style["description"]
    assert_true(
        "early-career" in prose_description,
        "candidate_facing_prose_style description must retain the early-career role framing requirement",
    )
    assert_true(
        "concrete action/context/why wording" in prose_description,
        "candidate_facing_prose_style description must retain the concrete action/context/why wording requirement",
    )
    assert_true(
        "ordinary American English" in prose_description,
        "candidate_facing_prose_style description must retain the ordinary American English requirement",
    )
    assert_true(
        "No generic capability-stuffing summary" in prose_description,
        "candidate_facing_prose_style description must retain the no-generic-capability-stuffing-summary requirement",
    )

    metrics = GOLD["visual_metrics"]
    assert_true(metrics["page_size"] == "US_LETTER", "visual metrics page size must be US Letter")
    assert_true(metrics["margins_inches"]["top"] == 0.46, "top margin must be 0.46in")
    assert_true(metrics["margins_inches"]["bottom"] == 0.32, "bottom margin must be 0.32in")
    assert_true(metrics["margins_inches"]["left"] == 0.72, "left margin must be 0.72in")
    assert_true(metrics["margins_inches"]["right"] == 0.72, "right margin must be 0.72in")
    assert_true(metrics["typography"]["name"]["size_pt"] == 18.5, "name size must be 18.5pt")
    assert_true(metrics["typography"]["body_and_contact"]["size_pt"] == 10.5, "body size must be 10.5pt")
    assert_true(metrics["typography"]["section_headings"]["size_pt"] == 11, "heading size must be 11pt")
    assert_true(metrics["typography"]["primary_font"] == "Liberation Sans", "primary font must be Liberation Sans")
    assert_true(metrics["typography"]["fallback_font"] == "Arial", "fallback font must be Arial")


_run("_test_1", _test_1)
print("PASS 1: gold-reference record encodes the exact locked SHA-256, section order, work/education/skills grammar, evidence roster, and visual metrics.")
sys.stdout.flush()


# ======================================================================
# 2. Every drift_patterns_rejected entry in the gold-reference record has
# a corresponding, distinct check in _find_drift_violations() -- the
# record and the regression logic cannot silently drift apart.
# ======================================================================
def _test_2() -> None:
    recorded_ids = {entry["id"] for entry in GOLD["drift_patterns_rejected"]}
    expected_ids = {
        "DRIFT_PROFESSIONAL_SUMMARY_HEADING",
        "DRIFT_SECTION_ORDER",
        "DRIFT_EMPLOYER_FIRST_ITALIC_TITLE",
        "DRIFT_INTERNAL_TAXONOMY_IN_SKILLS",
        "DRIFT_BULMARMA_AUTO_INSERTED",
        "DRIFT_INTERNAL_JARGON_IN_PROSE",
    }
    assert_true(
        recorded_ids == expected_ids,
        f"gold-reference drift_patterns_rejected ids must match the regression test's coverage, got {recorded_ids}",
    )


_run("_test_2", _test_2)
print("PASS 2: gold-reference drift_patterns_rejected ids exactly match this regression test's coverage.")
sys.stdout.flush()


# ======================================================================
# 3. The reproduced Cable One drift candidate fails -- trips every
# recorded drift pattern.
# ======================================================================
def _test_3() -> None:
    violations = _find_drift_violations(_cable_one_drift_candidate(), GOLD)
    expected_ids = {entry["id"] for entry in GOLD["drift_patterns_rejected"]}
    assert_true(
        violations == expected_ids,
        f"Cable One drift candidate must trip every recorded drift pattern, got {violations}, expected {expected_ids}",
    )


_run("_test_3", _test_3)
print("PASS 3: the reproduced Cable One drift candidate trips every recorded drift_patterns_rejected id.")
sys.stdout.flush()


# ======================================================================
# 4. The locked gold-reference candidate passes cleanly -- zero drift
# violations.
# ======================================================================
def _test_4() -> None:
    violations = _find_drift_violations(_gold_candidate(), GOLD)
    assert_true(violations == set(), f"a candidate conforming to the gold-reference grammar must have zero drift violations, got {violations}")


_run("_test_4", _test_4)
print("PASS 4: a candidate conforming exactly to the locked gold-reference grammar passes with zero drift violations.")
sys.stdout.flush()


# ======================================================================
# 5. Each drift pattern is independently detectable -- a candidate that
# is otherwise gold-conformant but violates exactly one rule trips only
# that rule's id, never zero and never a different one.
# ======================================================================
def _test_5() -> None:
    base = _gold_candidate()

    case = dict(base)
    case["summary_heading"] = "PROFESSIONAL SUMMARY"
    assert_true(
        _find_drift_violations(case, GOLD) == {"DRIFT_PROFESSIONAL_SUMMARY_HEADING"},
        "an added PROFESSIONAL SUMMARY heading alone must trip only DRIFT_PROFESSIONAL_SUMMARY_HEADING",
    )

    case = dict(base)
    case["section_order"] = ["WORK EXPERIENCE", "EDUCATION", "SKILLS", "RELEVANT PROJECT"]
    assert_true(
        _find_drift_violations(case, GOLD) == {"DRIFT_SECTION_ORDER"},
        "an employer-first section order alone must trip only DRIFT_SECTION_ORDER",
    )

    case = dict(base)
    case["work_entries"] = [{"grammar": "EMPLOYER_FIRST_ITALIC_TITLE"}]
    assert_true(
        _find_drift_violations(case, GOLD) == {"DRIFT_EMPLOYER_FIRST_ITALIC_TITLE"},
        "an employer-first-plus-italic-title work entry alone must trip only DRIFT_EMPLOYER_FIRST_ITALIC_TITLE",
    )

    case = dict(base)
    case["skills_text"] = "EvidenceMatch STRONG"
    assert_true(
        _find_drift_violations(case, GOLD) == {"DRIFT_INTERNAL_TAXONOMY_IN_SKILLS"},
        "internal taxonomy leaking into skills text alone must trip only DRIFT_INTERNAL_TAXONOMY_IN_SKILLS",
    )

    case = dict(base)
    case["evidence_roster"] = list(base["evidence_roster"]) + ["Bulmarma"]
    case["bulmarma_crosswalk_earned"] = False
    assert_true(
        _find_drift_violations(case, GOLD) == {"DRIFT_BULMARMA_AUTO_INSERTED"},
        "an un-earned Bulmarma insertion alone must trip only DRIFT_BULMARMA_AUTO_INSERTED",
    )

    # An earned Bulmarma insertion (explicit crosswalk flag) must NOT
    # trip the drift rule -- §141.2 allows it when materially earned.
    case = dict(base)
    case["evidence_roster"] = list(base["evidence_roster"]) + ["Bulmarma"]
    case["bulmarma_crosswalk_earned"] = True
    assert_true(
        _find_drift_violations(case, GOLD) == set(),
        "a Bulmarma insertion explicitly earned by a role-specific crosswalk must not be flagged as drift",
    )

    case = dict(base)
    case["prose_text"] = "Secured human approval before proceeding."
    assert_true(
        _find_drift_violations(case, GOLD) == {"DRIFT_INTERNAL_JARGON_IN_PROSE"},
        "internal/system jargon in candidate-facing prose alone must trip only DRIFT_INTERNAL_JARGON_IN_PROSE",
    )

    case = dict(base)
    case["prose_text"] = "Strong collaboration supported partial workflow improvements."
    assert_true(
        _find_drift_violations(case, GOLD) == set(),
        "ordinary English strong/supported/partial in prose must not be treated as Career OS jargon",
    )


_run("_test_5", _test_5)
print("PASS 5: each of the six drift patterns is independently detectable without false positives on an otherwise gold-conformant candidate, and an explicitly-earned Bulmarma insertion is correctly not flagged.")
sys.stdout.flush()


# ======================================================================
# 6. The doctrine surfaces actually cross-reference this lock -- BLUEPRINT.md
# carries a locked Section 141 pointing at the milestone id and the gold
# reference's SHA-256, and .cursor/rules/resume.mdc cross-references it.
# ======================================================================
def _test_6() -> None:
    blueprint_text = BLUEPRINT_PATH.read_text(encoding="utf-8")
    assert_true(
        "**141. BORA RESUME REFERENCE STYLE LOCK — BORA_RESUME_REFERENCE_STYLE_LOCK_V1 (LOCKED)**"
        in blueprint_text,
        "BLUEPRINT.md must carry a locked Section 141 heading for BORA_RESUME_REFERENCE_STYLE_LOCK_V1",
    )
    assert_true(
        GOLD["source_artifact"]["sha256"] in blueprint_text,
        "BLUEPRINT.md Section 141 must record the same gold-reference SHA-256 as the JSON record",
    )
    assert_true(
        "**Final Locked Blueprint v3.13**" in blueprint_text,
        "BLUEPRINT.md version header must be bumped to v3.13 alongside the new Section 141",
    )

    mdc_text = RESUME_MDC_PATH.read_text(encoding="utf-8")
    assert_true(
        "§141" in mdc_text and "BORA_RESUME_REFERENCE_STYLE_LOCK_V1" in mdc_text,
        ".cursor/rules/resume.mdc must operationally cross-reference BLUEPRINT.md Section 141",
    )

    state = json.loads((ROOT / "project_state.json").read_text(encoding="utf-8"))
    assert_true(state["blueprint_version"] == "3.13", f"project_state.json blueprint_version must be 3.13, got {state['blueprint_version']}")
    assert_true(state["latest_locked_section"] == 141, f"project_state.json latest_locked_section must be 141, got {state['latest_locked_section']}")


_run("_test_6", _test_6)
print("PASS 6: BLUEPRINT.md Section 141, .cursor/rules/resume.mdc, and project_state.json all consistently cross-reference this lock.")
sys.stdout.flush()


# ======================================================================
# 7. Correction-pass governance fixes (REV-001/REV-002 from the prior
# review round) stay regression-locked, so they cannot be silently
# reverted while this test still passes: §134's "section order" and
# "numeric visual metrics" paragraphs must carry their explicit AMENDED
# BY §141 notes, and the gold-reference record must retain its
# never-a-source-of-Candidate-Truth authority-scope language.
# ======================================================================
def _test_7() -> None:
    blueprint_text = BLUEPRINT_PATH.read_text(encoding="utf-8")
    assert_true(
        "**Presentation grammar — AMENDED BY §141.**" in blueprint_text,
        "BLUEPRINT.md §134 must carry the 'Presentation grammar — AMENDED BY §141' note narrowing "
        "the original job-specific-strategic-variable paragraph (section order/heading/work-entry "
        "grammar are governed by §141, not free per-application choices)",
    )
    assert_true(
        "**Numeric visual metrics — AMENDED BY §141 for gold-reference packages.**" in blueprint_text,
        "BLUEPRINT.md §134 must carry the 'Numeric visual metrics — AMENDED BY §141' note resolving "
        "which exemplar (MGB PDF vs. Spy Pond DOCX) governs numeric visual metrics for gold-reference packages",
    )
    assert_true(
        re.search(r"never frozen as\s+universal", blueprint_text) is not None,
        "the narrowed (not deleted) job-specific-variable language must still be present in §134",
    )

    scope = GOLD["role_tailoring_boundary"].get("gold_reference_authority_scope", "")
    assert_true(
        "never a source of Candidate Truth" in scope,
        f"gold-reference record's role_tailoring_boundary must retain 'never a source of Candidate Truth' authority-scope language, got {scope!r}",
    )
    assert_true(
        "claim-evidence lineage" in scope or "claim/evidence lineage" in scope,
        f"gold-reference record's authority-scope language must still require claim/evidence lineage for substantive facts, got {scope!r}",
    )
    must_never = GOLD["role_tailoring_boundary"]["must_never"]
    assert_true(
        any("Spy Pond exemplar" in item for item in must_never),
        f"role_tailoring_boundary.must_never must still forbid inventing/copying facts merely because they appear in the Spy Pond exemplar, got {must_never}",
    )


_run("_test_7", _test_7)
print("PASS 7: the REV-001/REV-002 correction-pass fixes (§134's AMENDED BY §141 notes for section order and numeric visual metrics; the gold reference's never-a-source-of-Candidate-Truth authority scope) remain present and regression-locked.")
sys.stdout.flush()

print("ALL resume_reference_style_lock_v1_test CHECKS PASSED")
sys.stdout.flush()
