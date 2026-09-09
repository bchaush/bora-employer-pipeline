"""Regression tests for BORA_PACKAGE_SPAWN_GATE_V1.

Bora reproduced two live package-generation defects: a Santander
resume/cover-letter package was produced before the exact first-party
requisition had been re-opened and proven actionable in the operating
session doing the package work, and a DraftKings resume drifted from the
canonical Bora gold-quality presentation family
(`BORA_RESUME_GOLD_QUALITY_REFERENCE_V1`) and leaked internal Career
OS/governance language into candidate-facing text. BLUEPRINT.md Section
141 subsections 141.13-141.15 (`CAREER_OS_PACKAGE_GATE_HARDENING_V1`)
lock the resulting package-time first-party actionability recheck and
gold-artifact spawn gate, recorded in full at
`docs/resume/BORA_PACKAGE_SPAWN_GATE_V1.json`. This lock is recorded as
Section 141 subsections rather than a new top-level section so that the
pinned `latest_locked_section=141` in
`tests/resume_reference_style_lock_v1_test.py` and the live
`src/career_os_state.py` max-heading validator both stay consistent.

This is a doctrine-record consistency check, not a resume generator,
renderer, or automated package-time validator (no such implementation is
authorized by §141.13-§141.15 -- see §141.15's Doctrine-only lock
subsection). It does not change Candidate Truth, Match Truth,
qualification/pursuit logic, immigration logic, or any schema.
"""

from __future__ import annotations

import json
import re
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPAWN_GATE_PATH = ROOT / "docs" / "resume" / "BORA_PACKAGE_SPAWN_GATE_V1.json"
GOLD_QUALITY_PATH = ROOT / "docs" / "resume" / "BORA_GOLD_QUALITY_REFERENCE_V1.json"
BLUEPRINT_PATH = ROOT / "BLUEPRINT.md"
RESUME_MDC_PATH = ROOT / ".cursor" / "rules" / "resume.mdc"
AGENTS_PATH = ROOT / "AGENTS.md"
JOB_SCHEMA_PATH = ROOT / "schemas" / "job.schema.json"


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
    RECORD = json.loads(SPAWN_GATE_PATH.read_text(encoding="utf-8"))
except Exception:
    print(f"FAIL: could not load package spawn gate JSON at {SPAWN_GATE_PATH}")
    traceback.print_exc(file=sys.stdout)
    sys.stdout.flush()
    raise SystemExit(1)

try:
    GOLD_QUALITY = json.loads(GOLD_QUALITY_PATH.read_text(encoding="utf-8"))
except Exception:
    print(f"FAIL: could not load gold-quality reference JSON at {GOLD_QUALITY_PATH}")
    traceback.print_exc(file=sys.stdout)
    sys.stdout.flush()
    raise SystemExit(1)

try:
    JOB_SCHEMA = json.loads(JOB_SCHEMA_PATH.read_text(encoding="utf-8"))
except Exception:
    print(f"FAIL: could not load job schema JSON at {JOB_SCHEMA_PATH}")
    traceback.print_exc(file=sys.stdout)
    sys.stdout.flush()
    raise SystemExit(1)


# ======================================================================
# 1. The record identifies itself correctly, is recorded as Section 141
# subsections (not a new top-level section), and cites both reproduced
# failures (Santander package-before-actionability; DraftKings gold-
# family/jargon drift) without turning either role's content into
# universal Candidate Truth.
# ======================================================================
def _test_1() -> None:
    assert_true(RECORD["record_id"] == "BORA_PACKAGE_SPAWN_GATE_V1", "record_id must match")
    assert_true(RECORD["blueprint_section"] == 141, "blueprint_section must point at Section 141 (recorded as §141 subsections, not a new top-level section)")
    assert_true(
        RECORD["blueprint_subsections"] == ["141.13", "141.14", "141.15"],
        f"blueprint_subsections must be the locked §141.13-§141.15 set, got {RECORD['blueprint_subsections']}",
    )

    failures = RECORD["reproduced_failures"]
    santander = failures["santander"]["description"]
    assert_true(
        "first-party requisition" in santander and "actionable" in santander,
        f"santander failure description must describe the package-before-actionability defect, got {santander!r}",
    )
    draftkings = failures["draftkings"]["description"]
    assert_true(
        "gold" in draftkings.lower() and "internal" in draftkings.lower(),
        f"draftkings failure description must describe the gold-family drift and internal-jargon leak, got {draftkings!r}",
    )
    assert_true(
        "universal Candidate Truth" in failures["scope_note"],
        "reproduced_failures.scope_note must state neither role's content becomes universal Candidate Truth",
    )


_run("_test_1", _test_1)
print("PASS 1: the record identifies itself correctly, is scoped as §141 subsections, and cites both reproduced failures without upgrading either role's content to universal Candidate Truth.")
sys.stdout.flush()


# ======================================================================
# 2. The package-time actionability recheck fires at the correct trigger
# points, extends (never replaces) §135, and requires the same positive
# semantic-quorum "successfully established" test.
# ======================================================================
def _test_2() -> None:
    recheck = RECORD["package_time_actionability_recheck"]
    assert_true(recheck["rule"] == "RECHECK_IMMEDIATELY_BEFORE_MEANINGFUL_PACKAGE_WORK", "package_time_actionability_recheck.rule mismatch")
    assert_true("Section 135" in recheck["extends_not_replaces"], "recheck must extend Section 135, not replace it")
    assert_true(
        "role/title identity" in recheck["description"] and "matching requisition identity" in recheck["description"] and "substantive current job-description content" in recheck["description"] and "actionable application route" in recheck["description"],
        "recheck description must restate §135's positive semantic-quorum successfully-established test",
    )
    triggers = recheck["trigger_points"]
    for expected in ("drafting", "DOCX mutation", "cover-letter drafting", "meaningful"):
        assert_true(
            any(expected in t for t in triggers),
            f"trigger_points must cover {expected!r}, got {triggers}",
        )


_run("_test_2", _test_2)
print("PASS 2: the package-time actionability recheck fires at drafting/DOCX-mutation/cover-letter/other meaningful-work trigger points and extends §135's positive semantic-quorum test.")
sys.stdout.flush()


# ======================================================================
# 3. The disqualifying-condition list and rescue prohibition are complete
# and match the acceptance-condition wording exactly.
# ======================================================================
def _test_3() -> None:
    disqualifying = RECORD["package_gate_disqualifying_conditions"]
    conditions = " ".join(disqualifying["conditions"]).lower()
    for expected in (
        "blank or contentless",
        "javascript-only",
        "generic careers/search redirect",
        "page-not-found",
        "expired or closed",
        "identity mismatch",
        "missing current application route",
    ):
        assert_true(expected in conditions, f"package_gate_disqualifying_conditions.conditions must cover {expected!r}, got {conditions!r}")

    rescue = disqualifying["rescue_prohibition"]
    sources = rescue["sources_that_cannot_rescue"]
    for expected in ("discovery indexes", "aggregators", "cached snippets", "prior captures", "chat summaries", "memory"):
        assert_true(expected in sources, f"rescue_prohibition.sources_that_cannot_rescue must list {expected!r}, got {sources}")


_run("_test_3", _test_3)
print("PASS 3: the package-gate disqualifying conditions and non-rescuing source list are complete and correctly encoded.")
sys.stdout.flush()


# ======================================================================
# 4. Failure handling uses the existing role_status/source_verification_
# status axes -- exactly matching the live enums in schemas/job.schema.json
# -- and forbids inventing a new persisted enum.
# ======================================================================
def _test_4() -> None:
    handling = RECORD["package_gate_failure_handling"]
    assert_true(handling["rule"] == "NO_NEW_ENUM_USE_EXISTING_TRUTH_AXES", "package_gate_failure_handling.rule mismatch")
    assert_true(
        "no resume, cover letter, or other candidate-facing package" in handling["description"],
        "failure handling must forbid generating/revising any candidate-facing package on recheck failure",
    )
    assert_true("historical" in handling["description"], "failure handling must preserve historical analysis if useful")

    recorded_role_status = set(handling["existing_axes_used"]["role_status_enum"])
    recorded_source_status = set(handling["existing_axes_used"]["source_verification_status_enum"])

    live_props = JOB_SCHEMA["properties"]
    live_role_status = set(live_props["role_status"]["enum"])
    live_source_status = set(live_props["source_verification_status"]["enum"])

    assert_true(
        recorded_role_status == live_role_status,
        f"recorded role_status_enum must exactly match the live schemas/job.schema.json enum; recorded={recorded_role_status}, live={live_role_status}",
    )
    assert_true(
        recorded_source_status == live_source_status,
        f"recorded source_verification_status_enum must exactly match the live schemas/job.schema.json enum; recorded={recorded_source_status}, live={live_source_status}",
    )


_run("_test_4", _test_4)
print("PASS 4: package-gate failure handling uses the existing role_status/source_verification_status axes, exactly matching the live schema enums, with no new persisted enum invented.")
sys.stdout.flush()


# ======================================================================
# 5. The gold-artifact spawn gate cites the exact current gold DOCX and
# SHA-256 from BORA_GOLD_QUALITY_REFERENCE_V1.json, forbids from-scratch
# reconstruction, and defines the GOLD_REFERENCE_ARTIFACT_REQUIRED stop
# condition.
# ======================================================================
def _test_5() -> None:
    spawn_gate = RECORD["gold_artifact_spawn_gate"]
    assert_true(spawn_gate["rule"] == "SPAWN_FROM_EXACT_CURRENT_GOLD_ARTIFACT_HASH_VERIFIED", "gold_artifact_spawn_gate.rule mismatch")
    assert_true("141.10" in spawn_gate["extends_not_replaces"], "gold_artifact_spawn_gate must extend §141.10")

    live_sha = GOLD_QUALITY["source_artifact"]["sha256"]
    assert_true(
        live_sha in spawn_gate["description"],
        f"gold_artifact_spawn_gate.description must cite the exact live gold-reference SHA-256 {live_sha!r}",
    )
    assert_true(bool(re.fullmatch(r"[0-9a-f]{64}", live_sha)), f"live gold-reference sha256 must be well-formed, got {live_sha!r}")
    assert_true(
        GOLD_QUALITY["source_artifact"]["name"] in spawn_gate["description"],
        "gold_artifact_spawn_gate.description must cite the exact live gold-reference artifact filename",
    )

    assert_true(
        "reconstruct the gold family from scratch" in spawn_gate["reconstruction_prohibition"],
        "gold_artifact_spawn_gate must forbid reconstructing the gold family from scratch",
    )

    stop = spawn_gate["stop_condition"]
    assert_true(stop["code"] == "GOLD_REFERENCE_ARTIFACT_REQUIRED", f"stop_condition.code must be GOLD_REFERENCE_ARTIFACT_REQUIRED, got {stop['code']!r}")
    assert_true("unavailable" in stop["when"] and "hash" in stop["when"], "stop_condition.when must cover both unavailable artifact and hash mismatch")
    assert_true("improvising a new resume template" in stop["action"], "stop_condition.action must forbid improvising a new resume template")


_run("_test_5", _test_5)
print("PASS 5: the gold-artifact spawn gate cites the exact live gold-reference artifact and SHA-256, forbids from-scratch reconstruction, and defines GOLD_REFERENCE_ARTIFACT_REQUIRED correctly.")
sys.stdout.flush()


# ======================================================================
# 6. Internal-jargon translation and pre-delivery QA reject conditions
# are present, correctly encoded, and extend (never replace) §141.11.
# ======================================================================
def _test_6() -> None:
    jargon = RECORD["internal_jargon_translation_requirement"]
    assert_true(jargon["rule"] == "TRANSLATE_INTERNAL_MECHANICS_TO_RECRUITER_NATURAL_ENGLISH", "internal_jargon_translation_requirement.rule mismatch")
    assert_true("141.11" in jargon["extends_not_replaces"], "jargon translation requirement must extend §141.11")
    examples = jargon["example_forbidden_terms_unless_job_relevant"]
    for expected in ("human approval", "operating system", "fail-closed", "queue-level eligibility", "deterministic boundary", "Candidate Truth"):
        assert_true(expected in examples, f"example_forbidden_terms_unless_job_relevant must include {expected!r}, got {examples}")

    qa = RECORD["pre_delivery_package_qa_reject_conditions"]
    assert_true(qa["rule"] == "REJECT_BEFORE_DELIVERY_TO_BORA_UNLESS_DOCUMENTED_EMPLOYER_EXCEPTION", "pre_delivery_package_qa_reject_conditions.rule mismatch")
    conditions = " ".join(qa["conditions"]).lower()
    for expected in (
        "professional summary",
        "noncanonical section order",
        "title | employer",
        "hyperlink objects",
        "overflow, clipping, or overlap",
        "sub-92-percent",
    ):
        assert_true(expected in conditions, f"pre_delivery_package_qa_reject_conditions.conditions must cover {expected!r}, got {conditions!r}")
    assert_true(
        "documented exception" in qa["exception"],
        "pre_delivery_package_qa_reject_conditions.exception must require a documented employer exception",
    )


_run("_test_6", _test_6)
print("PASS 6: internal-jargon translation and pre-delivery QA reject conditions are complete, correctly encoded, and extend (not replace) §141.11.")
sys.stdout.flush()


# ======================================================================
# 7. The doctrine surfaces actually cross-reference this lock --
# BLUEPRINT.md carries locked §141.13-§141.15 subsections, AGENTS.md and
# .cursor/rules/resume.mdc cross-reference them, no new top-level section
# was introduced, and project_state.json's pinned fields remain intact.
# ======================================================================
def _test_7() -> None:
    blueprint_text = BLUEPRINT_PATH.read_text(encoding="utf-8")
    assert_true(
        "**141.13 Package-time first-party actionability recheck" in blueprint_text,
        "BLUEPRINT.md must carry a locked §141.13 subsection for BORA_PACKAGE_SPAWN_GATE_V1",
    )
    for subsection_marker in (
        "**141.14 Gold-artifact-based spawning gate",
        "**141.15 Doctrine-only lock",
    ):
        assert_true(
            subsection_marker in blueprint_text,
            f"BLUEPRINT.md must carry the {subsection_marker!r} subsection heading",
        )
    assert_true(
        "CAREER_OS_PACKAGE_GATE_HARDENING_V1" in blueprint_text,
        "BLUEPRINT.md must name CAREER_OS_PACKAGE_GATE_HARDENING_V1",
    )
    assert_true("Santander" in blueprint_text, "BLUEPRINT.md §141.13 must cite the Santander reproduced failure")
    assert_true("DraftKings" in blueprint_text, "BLUEPRINT.md must cite the DraftKings reproduced failure")
    assert_true(
        "GOLD_REFERENCE_ARTIFACT_REQUIRED" in blueprint_text,
        "BLUEPRINT.md §141.14 must record the GOLD_REFERENCE_ARTIFACT_REQUIRED stop condition",
    )
    live_gold_sha = GOLD_QUALITY["source_artifact"]["sha256"]
    assert_true(
        live_gold_sha in blueprint_text,
        "BLUEPRINT.md §141.14 must cite the same gold-quality reference SHA-256 as the JSON record",
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
        "**141.10 Gold-quality acceptance reference" in blueprint_text,
        "BLUEPRINT.md must still carry the prior locked §141.10 subsection unchanged",
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
        "§141.13" in mdc_text and "BORA_PACKAGE_SPAWN_GATE_V1" in mdc_text,
        ".cursor/rules/resume.mdc must operationally cross-reference BLUEPRINT.md §141.13 and BORA_PACKAGE_SPAWN_GATE_V1",
    )
    assert_true(
        "GOLD_REFERENCE_ARTIFACT_REQUIRED" in mdc_text,
        ".cursor/rules/resume.mdc must record the GOLD_REFERENCE_ARTIFACT_REQUIRED stop condition",
    )

    agents_text = AGENTS_PATH.read_text(encoding="utf-8")
    assert_true(
        "141.13" in agents_text and "BORA_PACKAGE_SPAWN_GATE_V1" in agents_text,
        "AGENTS.md must operationally cross-reference BLUEPRINT.md §141.13 and BORA_PACKAGE_SPAWN_GATE_V1",
    )
    assert_true(
        "GOLD_REFERENCE_ARTIFACT_REQUIRED" in agents_text,
        "AGENTS.md must record the GOLD_REFERENCE_ARTIFACT_REQUIRED stop condition",
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
print("PASS 7: BLUEPRINT.md §141.13-§141.15, AGENTS.md, and .cursor/rules/resume.mdc all cross-reference this lock consistently; no new top-level section was introduced, and pinned project_state.json fields remain intact.")
sys.stdout.flush()


# ======================================================================
# 8. This record never claims authority over Candidate Truth, and never
# weakens §135, §137, §140, or §141's prior locked rules -- the
# must_never list and unchanged_doctrine references are present.
# ======================================================================
def _test_8() -> None:
    boundary = RECORD["role_tailoring_boundary"]
    scope = boundary.get("gold_reference_authority_scope", "")
    assert_true(
        "never a source of Candidate Truth" in scope,
        f"role_tailoring_boundary.gold_reference_authority_scope must retain 'never a source of Candidate Truth', got {scope!r}",
    )

    must_never = boundary["must_never"]
    for expected in (
        "fails the package-time actionability recheck",
        "freshly reconstructed template",
        "internal Career OS/governance/evidence-system/implementation-control language",
        "new persisted job/actionability enum",
        "rescue a failed package-time recheck",
        "unaddressed reject condition",
    ):
        assert_true(
            any(expected in item for item in must_never),
            f"role_tailoring_boundary.must_never must cover {expected!r}, got {must_never}",
        )

    unchanged = RECORD["unchanged_doctrine"]
    for token in (
        "Section 135",
        "Section 137",
        "Section 140",
        "Section 141",
        "141.10-141.11",
        "role_status and source_verification_status enums",
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
        any("new persisted job/actionability enum" in item for item in non_goals),
        "non_goals.excludes must exclude a new persisted job/actionability enum",
    )
    assert_true(
        any("Candidate Truth, Match Truth, qualification/pursuit logic, immigration logic, or schemas" in item for item in non_goals),
        "non_goals.excludes must exclude any change to Candidate Truth, Match Truth, qualification/pursuit logic, immigration logic, or schemas",
    )


_run("_test_8", _test_8)
print("PASS 8: this record's Candidate Truth authority-scope boundary is present, must_never/unchanged_doctrine/non_goals correctly forbid weakening §135/§137/§140/§141, and no schema/runtime/Candidate Truth change is authorized.")
sys.stdout.flush()

print("ALL resume_package_spawn_gate_v1_test CHECKS PASSED")
sys.stdout.flush()
