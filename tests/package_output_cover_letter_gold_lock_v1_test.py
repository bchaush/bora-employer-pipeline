"""Regression tests for PACKAGE_OUTPUT_COVER_LETTER_GOLD_LOCK_V1.

Bora needed the résumé package-completeness and gold-artifact-clone
discipline already locked at BLUEPRINT.md Section 141.10-141.15
(`BORA_RESUME_GOLD_QUALITY_REFERENCE_V1`,
`BORA_PACKAGE_SPAWN_GATE_V1`) extended to two additional requirements:
(1) every genuine survivor role's FINAL package must durably contain
résumé DOCX, résumé PDF, cover-letter DOCX, and cover-letter PDF
regardless of which single format is actually submitted, unless Bora
explicitly opts out of the cover letter; and (2) cover-letter DOCX
construction must clone an exact hash-verified gold artifact
(`Bora_Chaush_Cover_Letter_Gold_Reference.docx`) rather than being
reconstructed from doctrine text, mirroring the resume gold-artifact
spawn gate. BLUEPRINT.md Section 141 subsections 141.16-141.19
(`PACKAGE_OUTPUT_COVER_LETTER_GOLD_LOCK_V1`) lock this, recorded in full
at `docs/resume/BORA_COVER_LETTER_GOLD_REFERENCE_V1.json`. This lock is
recorded as Section 141 subsections rather than a new top-level section
so that the pinned `latest_locked_section=141` in
`tests/resume_reference_style_lock_v1_test.py` and the live
`src/career_os_state.py` max-heading validator both stay consistent.

This is a doctrine-record consistency check, not a résumé/cover-letter
generator, renderer, or automated validator (no such implementation is
authorized by §141.19 -- see its Doctrine-only lock subsection). It does
not change Candidate Truth, Match Truth, qualification/pursuit logic,
immigration logic, or any schema.
"""

from __future__ import annotations

import json
import re
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COVER_LETTER_PATH = ROOT / "docs" / "resume" / "BORA_COVER_LETTER_GOLD_REFERENCE_V1.json"
GOLD_QUALITY_PATH = ROOT / "docs" / "resume" / "BORA_GOLD_QUALITY_REFERENCE_V1.json"
BLUEPRINT_PATH = ROOT / "BLUEPRINT.md"
RESUME_MDC_PATH = ROOT / ".cursor" / "rules" / "resume.mdc"
AGENTS_PATH = ROOT / "AGENTS.md"


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
    RECORD = json.loads(COVER_LETTER_PATH.read_text(encoding="utf-8"))
except Exception:
    print(f"FAIL: could not load cover-letter gold reference JSON at {COVER_LETTER_PATH}")
    traceback.print_exc(file=sys.stdout)
    sys.stdout.flush()
    raise SystemExit(1)

try:
    GOLD_QUALITY = json.loads(GOLD_QUALITY_PATH.read_text(encoding="utf-8"))
except Exception:
    print(f"FAIL: could not load prior gold-quality reference JSON at {GOLD_QUALITY_PATH}")
    traceback.print_exc(file=sys.stdout)
    sys.stdout.flush()
    raise SystemExit(1)


# ======================================================================
# 1. The record identifies itself correctly, is recorded as Section 141
# subsections (not a new top-level section), and encodes both artifact
# hashes exactly as the acceptance conditions require.
# ======================================================================
def _test_1() -> None:
    assert_true(RECORD["record_id"] == "BORA_COVER_LETTER_GOLD_REFERENCE_V1", "record_id must match")
    assert_true(RECORD["blueprint_section"] == 141, "blueprint_section must point at Section 141 (recorded as §141 subsections, not a new top-level section)")
    assert_true(
        RECORD["blueprint_subsections"] == ["141.16", "141.17", "141.18", "141.19"],
        f"blueprint_subsections must be the locked §141.16-§141.19 set, got {RECORD['blueprint_subsections']}",
    )

    artifact = RECORD["source_artifact"]
    assert_true(
        artifact["name"] == "Bora_Chaush_Cover_Letter_Gold_Reference.docx",
        f"source_artifact.name must match the Bora-approved cover-letter artifact filename, got {artifact['name']!r}",
    )
    sha = artifact["sha256"]
    assert_true(
        sha == "264f7a8cc194e0211ce7f0af411b0ab6c07fa2438c557aa2e470536fded67e90",
        f"cover-letter gold DOCX SHA-256 must match the acceptance condition, got {sha!r}",
    )
    assert_true(bool(re.fullmatch(r"[0-9a-f]{64}", sha)), f"sha256 must be well-formed, got {sha!r}")
    assert_true(artifact["stored_in_repository"] is False, "binary must not be stored in the repository")

    pdf = RECORD["visual_reference_pdf"]
    pdf_sha = pdf["sha256"]
    assert_true(
        pdf_sha == "0b7da43108b0fae5ba4211078b4308cad9014d1e11cb533bc25ed64feec8df42",
        f"cover-letter visual-reference PDF SHA-256 must match the acceptance condition, got {pdf_sha!r}",
    )
    assert_true(bool(re.fullmatch(r"[0-9a-f]{64}", pdf_sha)), f"visual reference sha256 must be well-formed, got {pdf_sha!r}")
    assert_true(pdf["stored_in_repository"] is False, "visual-reference PDF binary must not be stored in the repository")
    assert_true(sha != pdf_sha, "the DOCX and rendered PDF must have distinct SHA-256 hashes")


_run("_test_1", _test_1)
print("PASS 1: the cover-letter gold-reference record encodes the exact locked DOCX and visual-reference PDF SHA-256 hashes and is scoped as §141 subsections.")
sys.stdout.flush()


# ======================================================================
# 2. The motivating exemplar is cited by name only and explicitly
# forbidden from contributing role-specific facts to universal text.
# ======================================================================
def _test_2() -> None:
    exemplar = RECORD["motivating_exemplar"]
    assert_true(exemplar["rule"] == "MOTIVATING_EXEMPLAR_NEVER_UNIVERSAL_TEXT", "motivating_exemplar.rule mismatch")
    assert_true(
        "Northeastern" in exemplar["family"] and "R141882" in exemplar["family"],
        f"motivating_exemplar.family must name the Northeastern R141882 cover-letter family, got {exemplar['family']!r}",
    )
    assert_true(
        "never" in exemplar["description"].lower() and "role-specific facts" in exemplar["description"],
        "motivating_exemplar.description must forbid copying the exemplar's role-specific facts into universal doctrine",
    )


_run("_test_2", _test_2)
print("PASS 2: the Northeastern R141882 motivating exemplar is cited by name only, with an explicit prohibition on copying its role-specific facts into universal text.")
sys.stdout.flush()


# ======================================================================
# 3. The complete four-artifact package requirement is present, applies
# regardless of submission format, and is scoped by the Bora explicit
# opt-out provision (not by a missing employer upload field).
# ======================================================================
def _test_3() -> None:
    req = RECORD["complete_package_requirement"]
    assert_true(req["rule"] == "COMPLETE_FOUR_ARTIFACT_SURVIVOR_PACKAGE", "complete_package_requirement.rule mismatch")
    for token in ("resume DOCX", "resume PDF", "cover-letter DOCX", "cover-letter PDF"):
        assert_true(token in req["description"], f"complete_package_requirement.description must list {token!r}")
    assert_true(
        "regardless of which single format is actually submitted" in req["description"],
        "complete_package_requirement must apply regardless of submitted format",
    )
    assert_true(
        "submission choice only" in req["submission_format_is_distinct"]
        and "never" in req["submission_format_is_distinct"],
        "submission_format_is_distinct must state the employer format instruction governs submission choice only",
    )

    opt_out = RECORD["opt_out_provision"]
    assert_true(opt_out["rule"] == "BORA_EXPLICIT_OPT_OUT_ONLY", "opt_out_provision.rule mismatch")
    assert_true(
        "explicit" in opt_out["description"].lower(),
        "opt_out_provision.description must require an explicit Bora opt-out",
    )
    assert_true(
        "not, by itself, an opt-out" in opt_out["description"],
        "opt_out_provision must clarify a missing employer cover-letter upload field is not itself an opt-out",
    )


_run("_test_3", _test_3)
print("PASS 3: the complete four-artifact survivor package requirement applies regardless of submission format and is scoped only by an explicit Bora opt-out.")
sys.stdout.flush()


# ======================================================================
# 4. The gold-artifact clone requirement forbids from-scratch
# reconstruction and defines the correct stop condition.
# ======================================================================
def _test_4() -> None:
    clone = RECORD["gold_artifact_clone_requirement"]
    assert_true(clone["rule"] == "CLONE_EXACT_HASH_VERIFIED_ARTIFACT_NO_TEMPLATE_RECONSTRUCTION", "gold_artifact_clone_requirement.rule mismatch")
    assert_true("141.14" in clone["extends_not_replaces"], "gold_artifact_clone_requirement must extend §141.14")
    assert_true(
        "reconstruct the cover-letter family from scratch" in clone["description"],
        "gold_artifact_clone_requirement must forbid reconstructing the cover-letter family from scratch",
    )

    stop = clone["stop_condition"]
    assert_true(
        stop["code"] == "COVER_LETTER_GOLD_REFERENCE_ARTIFACT_REQUIRED",
        f"stop_condition.code must be COVER_LETTER_GOLD_REFERENCE_ARTIFACT_REQUIRED, got {stop['code']!r}",
    )
    assert_true("unavailable" in stop["when"] and "hash" in stop["when"], "stop_condition.when must cover both unavailable artifact and hash mismatch")
    assert_true("improvising a new cover-letter template" in stop["action"], "stop_condition.action must forbid improvising a new cover-letter template")

    authority = RECORD["authority_scope"]
    assert_true(authority["rule"] == "PRESENTATION_QUALITY_TEMPLATE_AUTHORITY_ONLY_NEVER_CANDIDATE_TRUTH", "authority_scope.rule mismatch")
    assert_true(
        "never a source of Candidate Truth" in authority["description"] or "never" in authority["description"],
        "authority_scope.description must state this is never a source of Candidate Truth",
    )
    assert_true(
        "verified current JD" in authority["description"] and "140.4" in authority["description"],
        "authority_scope.description must ground role-specific content in the verified JD and §140.4 crosswalk",
    )


_run("_test_4", _test_4)
print("PASS 4: the cover-letter gold-artifact clone requirement forbids from-scratch reconstruction, defines COVER_LETTER_GOLD_REFERENCE_ARTIFACT_REQUIRED correctly, and scopes authority to presentation/quality/template only.")
sys.stdout.flush()


# ======================================================================
# 5. Cover-letter content/style requirements cover one-page length,
# recruiter-natural language, full contact/date/hiring-team block,
# truthful gap handling, real hyperlinks, and no internal jargon.
# ======================================================================
def _test_5() -> None:
    style = RECORD["content_and_style_requirements"]
    assert_true(style["rule"] == "ONE_PAGE_RECRUITER_NATURAL_FULL_BLOCK_TRUTHFUL_GAP_HANDLING", "content_and_style_requirements.rule mismatch")
    description = style["description"]
    for token in (
        "one U.S. Letter page",
        "recruiter-natural American business English",
        "contact block",
        "current date",
        "hiring-team",
        "visible gaps",
        "hyperlink objects",
        "no internal Career OS",
    ):
        assert_true(token in description, f"content_and_style_requirements.description must retain {token!r}")

    assert_true(
        any("141.7" in item for item in style["extends_not_replaces"]),
        "content_and_style_requirements must extend §141.7's writing constraints, not replace them",
    )
    assert_true(
        any("141.11" in item for item in style["extends_not_replaces"]),
        "content_and_style_requirements must extend §141.11's final-package QA-dimension checklist",
    )


_run("_test_5", _test_5)
print("PASS 5: cover-letter content/style requirements cover one-page length, recruiter-natural language, full contact/date/hiring-team block, truthful gap handling, real hyperlinks, and no internal jargon.")
sys.stdout.flush()


# ======================================================================
# 6. Prior doctrine (Sections 135/137/140/141/141.7/141.10-141.14) is
# restated/cross-referenced, never redefined; non-goals explicitly
# exclude a generator/renderer and an unsupervised drafting runtime; and
# the role-tailoring boundary forbids fact invention, gap-solving, and
# reduced package generation because of a submission-format instruction.
# ======================================================================
def _test_6() -> None:
    unchanged = RECORD["unchanged_doctrine"]
    for token in (
        "Section 135",
        "Section 137",
        "Section 140",
        "Section 141",
        "141.10-141.11",
        "141.13-141.14",
        "Candidate Truth, Match Truth, and qualification/pursuit runtime logic",
        "immigration",
    ):
        assert_true(
            any(token in item for item in unchanged),
            f"unchanged_doctrine must retain a reference to {token!r}, got {unchanged}",
        )

    must_never = RECORD["role_tailoring_boundary"]["must_never"]
    for expected in (
        "Northeastern R141882 motivating exemplar's role-specific facts",
        "reconstruct the cover-letter gold family from scratch",
        "reduce durable FINAL package generation because of an employer submission-format instruction",
        "skip the cover letter for a survivor role absent an explicit Bora opt-out",
        "solve an unsupported requirement through confident-sounding cover-letter wording",
    ):
        assert_true(
            any(expected in item for item in must_never),
            f"role_tailoring_boundary.must_never must cover {expected!r}, got {must_never}",
        )

    scope = RECORD["role_tailoring_boundary"].get("gold_reference_authority_scope", "")
    assert_true(
        "never a source of Candidate Truth" in scope,
        f"role_tailoring_boundary.gold_reference_authority_scope must retain 'never a source of Candidate Truth', got {scope!r}",
    )

    non_goals = RECORD["non_goals"]["excludes"]
    assert_true(
        any("generator or renderer" in item for item in non_goals),
        "non_goals.excludes must exclude a DOCX/PDF generator or renderer",
    )
    assert_true(
        any("unsupervised cover-letter drafting runtime" in item for item in non_goals),
        "non_goals.excludes must exclude an autonomous or unsupervised cover-letter drafting runtime",
    )
    assert_true(
        any("Candidate Truth, Match Truth, qualification/pursuit logic, immigration logic, or schemas" in item for item in non_goals),
        "non_goals.excludes must exclude any change to Candidate Truth, Match Truth, qualification/pursuit logic, immigration logic, or schemas",
    )


_run("_test_6", _test_6)
print("PASS 6: prior doctrine is restated/cross-referenced rather than redefined, the role-tailoring boundary forbids fact invention/gap-solving/reduced generation, and non-goals exclude a generator/renderer and unsupervised drafting runtime.")
sys.stdout.flush()


# ======================================================================
# 7. The doctrine surfaces actually cross-reference this lock --
# BLUEPRINT.md carries locked §141.16-§141.19 subsections and §140.9,
# AGENTS.md and .cursor/rules/resume.mdc cross-reference them, no new
# top-level section was introduced, and project_state.json's pinned
# fields remain intact (this milestone cannot edit project_state.json or
# the tests that pin it).
# ======================================================================
def _test_7() -> None:
    blueprint_text = BLUEPRINT_PATH.read_text(encoding="utf-8")
    assert_true(
        "**140.9 Durable package-output completeness" in blueprint_text,
        "BLUEPRINT.md must carry a locked §140.9 subsection for durable package-output completeness",
    )
    assert_true(
        "**141.16 Complete four-artifact survivor package standard" in blueprint_text,
        "BLUEPRINT.md must carry a locked §141.16 subsection for PACKAGE_OUTPUT_COVER_LETTER_GOLD_LOCK_V1",
    )
    for subsection_marker in (
        "**141.17 Cover-letter gold-artifact clone requirement",
        "**141.18 Cover-letter content and style doctrine",
        "**141.19 Doctrine-only lock",
    ):
        assert_true(
            subsection_marker in blueprint_text,
            f"BLUEPRINT.md must carry the {subsection_marker!r} subsection heading",
        )
    assert_true(
        "PACKAGE_OUTPUT_COVER_LETTER_GOLD_LOCK_V1" in blueprint_text,
        "BLUEPRINT.md must name PACKAGE_OUTPUT_COVER_LETTER_GOLD_LOCK_V1",
    )
    assert_true(
        RECORD["source_artifact"]["sha256"] in blueprint_text,
        "BLUEPRINT.md §141.17 must record the same cover-letter gold DOCX SHA-256 as the JSON record",
    )
    assert_true(
        RECORD["visual_reference_pdf"]["sha256"] in blueprint_text,
        "BLUEPRINT.md §141.17 must record the same cover-letter visual-reference PDF SHA-256 as the JSON record",
    )
    assert_true(
        "COVER_LETTER_GOLD_REFERENCE_ARTIFACT_REQUIRED" in blueprint_text,
        "BLUEPRINT.md §141.17 must record the COVER_LETTER_GOLD_REFERENCE_ARTIFACT_REQUIRED stop condition",
    )
    assert_true(
        "Northeastern" in blueprint_text and "R141882" in blueprint_text,
        "BLUEPRINT.md must cite the Northeastern R141882 motivating exemplar",
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
        "**141.10 Gold-quality acceptance reference" in blueprint_text
        and "**141.13 Package-time first-party actionability recheck" in blueprint_text,
        "BLUEPRINT.md must still carry the prior locked §141.10 and §141.13 subsections unchanged",
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
        "§141.16" in mdc_text and "BORA_COVER_LETTER_GOLD_REFERENCE_V1" in mdc_text,
        ".cursor/rules/resume.mdc must operationally cross-reference BLUEPRINT.md §141.16 and BORA_COVER_LETTER_GOLD_REFERENCE_V1",
    )
    assert_true(
        "COVER_LETTER_GOLD_REFERENCE_ARTIFACT_REQUIRED" in mdc_text,
        ".cursor/rules/resume.mdc must record the COVER_LETTER_GOLD_REFERENCE_ARTIFACT_REQUIRED stop condition",
    )

    agents_text = AGENTS_PATH.read_text(encoding="utf-8")
    assert_true(
        "141.16" in agents_text and "BORA_COVER_LETTER_GOLD_REFERENCE_V1" in agents_text,
        "AGENTS.md must operationally cross-reference BLUEPRINT.md §141.16 and BORA_COVER_LETTER_GOLD_REFERENCE_V1",
    )
    assert_true(
        "COVER_LETTER_GOLD_REFERENCE_ARTIFACT_REQUIRED" in agents_text,
        "AGENTS.md must record the COVER_LETTER_GOLD_REFERENCE_ARTIFACT_REQUIRED stop condition",
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


_run("_test_7", _test_7)
print("PASS 7: BLUEPRINT.md §140.9/§141.16-§141.19, AGENTS.md, and .cursor/rules/resume.mdc all cross-reference this lock consistently; no new top-level section was introduced, and pinned project_state.json fields remain intact.")
sys.stdout.flush()


# ======================================================================
# 8. This lock does not silently weaken the résumé gold-quality
# reference's own artifact identity or authority-scope language (sanity
# cross-check against the still-required, non-editable prior test).
# ======================================================================
def _test_8() -> None:
    assert_true(
        GOLD_QUALITY["record_id"] == "BORA_GOLD_QUALITY_REFERENCE_V1",
        "the prior résumé gold-quality reference record must remain intact and unrenamed",
    )
    assert_true(
        GOLD_QUALITY["source_artifact"]["sha256"]
        == "ec3a9f9c6e2fc429e01892f61a074a71319ec6586566b6c1cf60808eba2f3f70",
        "the prior résumé gold-quality reference SHA-256 must remain unchanged by this cover-letter lock",
    )
    assert_true(
        GOLD_QUALITY["source_artifact"]["sha256"] != RECORD["source_artifact"]["sha256"],
        "the résumé gold artifact and the cover-letter gold artifact must be distinct hashes",
    )


_run("_test_8", _test_8)
print("PASS 8: the prior resume gold-quality reference record's identity and SHA-256 remain unchanged and distinct from the new cover-letter gold artifact.")
sys.stdout.flush()

# ======================================================================
# 9. Cover letters are NOT subject to §141's resume-specific presentation
# grammar or §137's 92% meaningful-page-utilization floor -- this must
# hold in the JSON record itself and be stated consistently across
# BLUEPRINT.md, .cursor/rules/resume.mdc, AGENTS.md, and CHANGELOG.md.
# ======================================================================
def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text)


def _test_9() -> None:
    not_applicable = RECORD["content_and_style_requirements"]["not_applicable_resume_specific_rules"]
    assert_true(
        not_applicable["rule"] == "RESUME_PRESENTATION_GRAMMAR_AND_92_PERCENT_FLOOR_DO_NOT_GOVERN_COVER_LETTERS",
        "content_and_style_requirements.not_applicable_resume_specific_rules.rule mismatch",
    )
    assert_true(
        "do NOT apply to cover letters" in not_applicable["description"],
        "not_applicable_resume_specific_rules.description must state §141 grammar/§137's floor do not apply to cover letters",
    )

    must_never = RECORD["role_tailoring_boundary"]["must_never"]
    assert_true(
        any("Section 141's resume-specific presentation grammar or Section 137's 92%" in item for item in must_never),
        "role_tailoring_boundary.must_never must forbid applying §141's grammar or §137's floor to a cover letter",
    )

    unchanged = RECORD["unchanged_doctrine"]
    assert_true(
        any("resume-scoped only" in item and "137" in item for item in unchanged),
        "unchanged_doctrine's §137 entry must clarify it is resume-scoped only, not imported onto cover letters",
    )
    assert_true(
        any("resume-scoped only" in item and "Section 141" in item for item in unchanged),
        "unchanged_doctrine's §141 entry must clarify its grammar is resume-scoped only, not imported onto cover letters",
    )

    blueprint_norm = _norm(BLUEPRINT_PATH.read_text(encoding="utf-8"))
    assert_true(
        "are résumé-specific and do not apply to cover letters" in blueprint_norm,
        "BLUEPRINT.md §141.18 must explicitly exclude §141's resume presentation grammar and §137's 92% floor from cover letters",
    )

    mdc_norm = _norm(RESUME_MDC_PATH.read_text(encoding="utf-8"))
    assert_true(
        "are resume-scoped and do not govern cover letters" in mdc_norm,
        ".cursor/rules/resume.mdc must explicitly exclude §141's resume presentation grammar and §137's 92% floor from cover letters",
    )

    agents_norm = _norm(AGENTS_PATH.read_text(encoding="utf-8"))
    assert_true(
        "are resume-scoped and do not govern cover letters" in agents_norm,
        "AGENTS.md must explicitly exclude §141's resume presentation grammar and §137's 92% floor from cover letters",
    )

    changelog_norm = _norm((ROOT / "CHANGELOG.md").read_text(encoding="utf-8"))
    assert_true(
        "do NOT apply to cover letters" in changelog_norm,
        "CHANGELOG.md must state §141's resume grammar and §137's 92% floor do NOT apply to cover letters",
    )
    assert_true(
        "fully apply to the cover letter as well" not in changelog_norm,
        "CHANGELOG.md must no longer claim resume presentation grammar and the 92% floor fully apply to the cover letter",
    )


_run("_test_9", _test_9)
print("PASS 9: cover letters are explicitly excluded from §141's resume-specific presentation grammar and §137's 92% page-utilization floor, consistently across the JSON record, BLUEPRINT.md, .cursor/rules/resume.mdc, AGENTS.md, and CHANGELOG.md.")
sys.stdout.flush()


# ======================================================================
# 10. Stop-condition semantics: the gold DOCX's existence + SHA-256 match
# alone controls COVER_LETTER_GOLD_REFERENCE_ARTIFACT_REQUIRED. The
# visual-reference PDF hash is still canonically recorded and must be
# verified for visual-reference integrity/QA when that PDF is used, but a
# missing/mismatched PDF hash alone must never trigger the stop condition.
# This must agree across the JSON record, BLUEPRINT.md, AGENTS.md, and
# .cursor/rules/resume.mdc.
# ======================================================================
def _test_10() -> None:
    stop = RECORD["gold_artifact_clone_requirement"]["stop_condition"]
    assert_true(
        "sha256 match alone control clone authority" in stop.get("controls_clone_authority", ""),
        "stop_condition.controls_clone_authority must state the gold DOCX hash alone controls clone authority/spawn permission",
    )
    assert_true(
        "does NOT trigger this stop_condition" in stop.get("visual_reference_pdf_hash_scope", ""),
        "stop_condition.visual_reference_pdf_hash_scope must state a missing/mismatched PDF hash alone does not trigger the stop condition",
    )

    for path, label in (
        (BLUEPRINT_PATH, "BLUEPRINT.md"),
        (AGENTS_PATH, "AGENTS.md"),
        (RESUME_MDC_PATH, ".cursor/rules/resume.mdc"),
    ):
        text_norm = _norm(path.read_text(encoding="utf-8"))
        assert_true(
            "does not trigger this stop condition" in text_norm,
            f"{label} must state a missing/mismatched visual-reference PDF hash alone does not trigger COVER_LETTER_GOLD_REFERENCE_ARTIFACT_REQUIRED",
        )
        assert_true(
            "either hash does not match" not in text_norm,
            f"{label} must not gate COVER_LETTER_GOLD_REFERENCE_ARTIFACT_REQUIRED on 'either hash' -- only the gold DOCX hash controls the stop condition",
        )
        assert_true(
            "COVER_LETTER_GOLD_REFERENCE_ARTIFACT_REQUIRED" in text_norm,
            f"{label} must still record the COVER_LETTER_GOLD_REFERENCE_ARTIFACT_REQUIRED stop condition",
        )


_run("_test_10", _test_10)
print("PASS 10: COVER_LETTER_GOLD_REFERENCE_ARTIFACT_REQUIRED is controlled solely by the gold DOCX's existence and SHA-256 match -- consistently across the JSON record, BLUEPRINT.md, AGENTS.md, and .cursor/rules/resume.mdc -- while the visual-reference PDF hash remains recorded for separate visual-fidelity QA verification.")
sys.stdout.flush()

print("ALL package_output_cover_letter_gold_lock_v1_test CHECKS PASSED")
sys.stdout.flush()
