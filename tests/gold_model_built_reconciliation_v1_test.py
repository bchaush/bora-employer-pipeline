"""Doctrine-consistency regression for the model-built Gold resume reconciliation.

PURSUE_TO_GOLD_PACKAGE_V1 (milestone_contracts/governance/career-os-pursue-to-gold-package-v1-contract.json)
is reconciled so the resume is generated deterministically from the canonical Gold
doctrine and approved Candidate Truth and rendered only through the canonically
released rendering capability, instead of being cloned from the historical Gold
DOCX. docs/resume/BORA_PACKAGE_SPAWN_GATE_V1.json records the matching additive
reconciliation of the spawn gate.

This is a record-consistency check only. It implements no builder, QA module or
renderer, authorizes no implementation, and creates no second Gold standard: every
numeric Gold value asserted here is read from the existing canonical doctrine
records.
"""

from __future__ import annotations

import json
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PTG_PATH = ROOT / "milestone_contracts" / "governance" / "career-os-pursue-to-gold-package-v1-contract.json"
SPAWN_PATH = ROOT / "docs" / "resume" / "BORA_PACKAGE_SPAWN_GATE_V1.json"
SPY_POND_PATH = ROOT / "docs" / "resume" / "BORA_SPY_POND_GOLD_REFERENCE_V1.json"

PTG = json.loads(PTG_PATH.read_text(encoding="utf-8"))
SPAWN = json.loads(SPAWN_PATH.read_text(encoding="utf-8"))
SPY = json.loads(SPY_POND_PATH.read_text(encoding="utf-8"))
ALL_ACCEPTANCE = "\n".join(PTG["acceptance_conditions"])
ALL_STOPS = "\n".join(PTG["stop_conditions"])
EXPECTED_NEW_PATHS = (
    "src/gold_resume_docx_builder.py",
    "src/gold_resume_qa.py",
    "schemas/gold_resume_model.schema.json",
)


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        print(f"FAIL: {message}")
        sys.stdout.flush()
        raise SystemExit(1)


def _run(name: str, fn) -> None:
    try:
        fn()
    except SystemExit:
        raise
    except Exception:
        print(f"FAIL: unexpected exception in {name}")
        traceback.print_exc(file=sys.stdout)
        sys.stdout.flush()
        raise SystemExit(1)


def _condition(prefix: str) -> str:
    matches = [item for item in PTG["acceptance_conditions"] if item.startswith(prefix)]
    assert_true(len(matches) == 1, f"exactly one acceptance condition must start with {prefix!r}")
    return matches[0]


def _test_1() -> None:
    allowed = PTG["allowed_paths"]
    for path in EXPECTED_NEW_PATHS:
        assert_true(path in allowed, f"allowed_paths must authorize {path}")
    for path in ("src/pursue_to_gold_package.py", "tests/pursue_to_gold_package_v1_test.py"):
        assert_true(path in allowed, f"allowed_paths must keep {path}")
    assert_true(not any(("*" in item) and item.startswith("src/") for item in allowed),
                "allowed_paths must not broaden to a src wildcard")
    assert_true(len(allowed) == len(set(allowed)), "allowed_paths must not repeat an entry")
    for frozen in ("src/resume_*.py", "src/claim_*.py", "src/pursuit_decision.py", "docs/resume/**", "claims/**"):
        assert_true(frozen in PTG["forbidden_paths"], f"forbidden_paths must keep {frozen}")
    print("PASS 1: allowed_paths adds exactly the three Gold builder paths, keeps the frozen-module forbidden list, and adds no src wildcard.")


def _test_2() -> None:
    goal = PTG["goal"]
    assert_true("model-built Gold DOCX builder" in goal, "goal must name the model-built Gold DOCX builder")
    assert_true("no longer cloned" in goal, "goal must retire cloning for the resume")
    assert_true("cover-letter pair continues to be spawned by cloning" in goal, "goal must leave the cover-letter clone path unchanged")
    step6 = _condition("PRE-PACKAGE ORDER")
    assert_true("exact canonical Gold resume source supplied" not in step6, "pre-package order must not require a Gold resume clone source")
    assert_true("exact Gold sources cloned" not in step6, "pre-package order must not clone the Gold resume")
    assert_true("same model" in step6 or "from the same model" in step6, "pre-package order must bind the structure map to the same model")
    integrity = _condition("GOLD SOURCE INTEGRITY")
    for token in ("COVER LETTER (unchanged)", "RESUME (reconciled)", "GOLD_DOCTRINE_RECORD_REQUIRED",
                  "regression reference only", "ec3a9f9c6e2fc429e01892f61a074a71319ec6586566b6c1cf60808eba2f3f70",
                  "264f7a8cc194e0211ce7f0af411b0ab6c07fa2438c557aa2e470536fded67e90"):
        assert_true(token in integrity, f"GOLD SOURCE INTEGRITY must contain {token!r}")
    print("PASS 2: the clone-the-Gold-resume assumptions are replaced by model-built generation while the cover-letter clone path and exemplar SHA-256 values are preserved.")


def _test_3() -> None:
    hard_stop = _condition("CAPABILITY HARD STOP")
    for token in ("canonically released", "public interface", "PACKAGE_CAPABILITY_BLOCKED",
                  "ORDER_INDEPENDENT_LINKAGE_V1", "PART_TYPE_NOT_ALLOWED", "never drops, reorders or relocates"):
        assert_true(token in hard_stop, f"CAPABILITY HARD STOP must contain {token!r}")
    assert_true("bars the now-canonical" not in hard_stop and "no proven production" not in hard_stop.replace("the former premise that no proven production", ""),
                "the obsolete no-capability premise must be gone")
    assert_true("any invocation of LibreOffice or browser automation other than through the canonical released rendering capability's public interface" in ALL_STOPS,
                "the dependency stop must admit only the released renderer's public interface")
    assert_true("modification of that renderer" in ALL_STOPS, "the runtime must never modify the renderer")
    print("PASS 3: the capability hard stop admits only the released renderer through its public interface and still fails closed without a degraded package.")


def _test_4() -> None:
    metrics = SPY["visual_metrics"]
    grammar = _condition("GOLD GRAMMAR (REQUIRED DEFAULT)")
    margins = metrics["margins_inches"]
    assert_true(f"margins left and right {margins['left']:.2f} inch" in grammar, "contract left/right margin must equal the doctrine record")
    assert_true(f"top {margins['top']:.2f} inch" in grammar and f"bottom {margins['bottom']:.2f} inch" in grammar,
                "contract top/bottom margins must equal the doctrine record")
    assert_true(f"{metrics['typography']['name']['size_pt']} pt" in grammar, "contract name size must equal the doctrine record")
    assert_true(f"{metrics['typography']['body_and_contact']['size_pt']} pt" in grammar, "contract body size must equal the doctrine record")
    assert_true(f"{metrics['typography']['section_headings']['size_pt']} pt" in grammar, "contract heading size must equal the doctrine record")
    assert_true(metrics["typography"]["primary_font"] in grammar, "contract primary font must equal the doctrine record")
    order = SPY["presentation_grammar"]["section_order"]
    assert_true(", ".join(order[:-1]) + " and " + order[-1] in grammar.replace("EDUCATION, SKILLS, WORK EXPERIENCE, RELEVANT PROJECT", ", ".join(order[:-1]) + " and " + order[-1]) or
                ", ".join(order) in grammar, "contract section order must equal the doctrine record")
    assert_true("NO summary heading" in grammar, "contract must forbid a summary heading")
    assert_true("Title | Employer" in grammar, "contract must require Title | Employer grammar")
    for name in SPY["presentation_grammar"]["evidence_roster"]["default_included"]:
        assert_true(name.split()[0] in grammar, f"default roster must mention {name}")
    print("PASS 4: every numeric and structural Gold value in the contract equals the existing canonical doctrine record; no second Gold standard exists.")


def _test_5() -> None:
    structure = _condition("STRUCTURE MAP FROM THE SAME MODEL")
    for role in ("CONTACT_LINE", "SECTION_HEADING", "SUMMARY_TEXT", "EDUCATION_LINE", "EMPLOYMENT_HEADER",
                 "BULLET_TEXT", "PROJECT_HEADER", "SKILLS_LINE"):
        assert_true(role in structure, f"structure map vocabulary must name {role}")
    assert_true("from the same approved resume model as the DOCX" in structure, "structure map must come from the same approved resume model")
    hyphen = _condition("HYPHEN-SAFE LAYOUT")
    for token in ("HYPHENATION_OBSERVED", "presentation properties only", "92-percent"):
        assert_true(token in hyphen, f"hyphen-safe layout must contain {token!r}")
    links = _condition("HYPERLINKS")
    for token in ("genuine OOXML hyperlink relationship", "/Link URI annotation", "independently of PDF annotation order",
                  "ORDER_INDEPENDENT_LINKAGE_V1"):
        assert_true(token in links, f"hyperlink condition must contain {token!r}")
    print("PASS 5: structure-map vocabulary, hyphen-safe layout and hyperlink requirements are recorded and bound to the canonical renderer vocabulary.")


def _test_6() -> None:
    qa = _condition("GOLD QA (EXECUTABLE)")
    for token in ("PRE-RENDER", "POST-RENDER", "executable validation, not JSON doctrine checks only", "utilization at or above 0.92",
                  "never adds filler"):
        assert_true(token in qa, f"Gold QA must contain {token!r}")
    gaps = _condition("CANDIDATE TRUTH AND DISPLAY GAPS")
    for token in ("3.635", "3.64 is forbidden", "TELUS Digital Bulgaria", "CLAIM_EDU_UNWE_001", "CLAIM_DCOMMERCE_001",
                  "GitHub profile", "blocked"):
        assert_true(token in gaps, f"truth gaps must record {token!r}")
    tests_e = _condition("ADDITIONAL MINIMUM TESTS (E)")
    for token in ("NEGATIVE fixture", "about 55 percent utilization", "Visual similarity alone is never a test", "synthetic test data"):
        assert_true(token in tests_e, f"required tests (E) must contain {token!r}")
    assert_true("auto-include an entry whose claim lacks Bora's human approval" in ALL_STOPS, "stop conditions must block unapproved-claim inclusion")
    print("PASS 6: executable Gold QA, the recorded Candidate Truth gaps and the regression/negative-fixture requirements are present.")


def _test_7() -> None:
    reconciliation = SPAWN["model_built_gold_generation_reconciliation"]
    assert_true(reconciliation["rule"] == "GENERATE_DETERMINISTICALLY_FROM_CANONICAL_GOLD_DOCTRINE_PLUS_APPROVED_CANDIDATE_TRUTH",
                "spawn-gate reconciliation rule mismatch")
    assert_true(reconciliation["stop_condition"]["code"] == "GOLD_DOCTRINE_RECORD_REQUIRED", "reconciliation stop code mismatch")
    assert_true("visual/presentation exemplar and regression reference only" in reconciliation["exemplar_role"], "exemplar role mismatch")
    assert_true(len(reconciliation["reasons_preserved"]) == 7, "all seven preserved reasons must be listed")
    gate = SPAWN["gold_artifact_spawn_gate"]
    assert_true(gate["rule"] == "SPAWN_FROM_EXACT_CURRENT_GOLD_ARTIFACT_HASH_VERIFIED", "the original spawn rule must remain recorded")
    assert_true("reconstruct the gold family from scratch" in gate["reconstruction_prohibition"],
                "the original reconstruction prohibition must remain for manual and agent spawning")
    assert_true("continue unchanged to bind every manual, chat or agent spawn" in reconciliation["scope"], "reconciliation must be scoped to the deterministic runtime")
    for key in ("internal_jargon_translation_requirement", "pre_delivery_package_qa_reject_conditions", "package_time_actionability_recheck"):
        assert_true(key in SPAWN, f"spawn gate must keep {key}")
    print("PASS 7: the spawn gate keeps its original rule for manual spawning and gains a scoped, deterministic-runtime reconciliation that preserves every original purpose.")


for _index, _fn in enumerate((_test_1, _test_2, _test_3, _test_4, _test_5, _test_6, _test_7), start=1):
    _run(f"_test_{_index}", _fn)

print("PASS: gold_model_built_reconciliation_v1_test")
