"""Bounded tests for TELUS master integration (TELUS_MASTER_INTEGRATION_V1).

Proves: the human-approved presentation decisions (display title,
month-level date range) are correctly represented using the existing
title-resolution and evidence-state architecture; the exact end date
is human-attested (OBSERVED) and never employer-verified or leaked
into normal résumé presentation; the formal title is never mutated or
replaced by LinkedIn's separate display wording; exactly the two
approved TELUS modules exist in the protected master with byte-
identical wording; the unified presentation and test-only renderer
show a compact, correct TELUS block; and Winter Walk, MarketMind, and
Brandeis Education remain completely unchanged.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = ROOT / "src"
MASTER_PATH = ROOT / "resume" / "master" / "RESUME_MASTER_WW_V1.json"
TELUS_EVIDENCE_DIR = ROOT / "evidence" / "telus"
TELUS_EXPERIENCE_PATH = ROOT / "experiences" / "EXP_TELUS_001.json"

if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from claim_repository import validate_claim_repository  # noqa: E402
from evidence_repository import validate_evidence_repository  # noqa: E402
from experience_repository import validate_experience_repository  # noqa: E402
from resume_lineage import validate_resume_module_lineage  # noqa: E402
from resume_presentation import build_resume_presentation_view  # noqa: E402
from resume_text_renderer import render_resume_text  # noqa: E402
from resume_validation import build_resume_derivative, validate_resume_master  # noqa: E402


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        print(f"FAIL: {message}")
        raise SystemExit(1)


def assert_false(condition: bool, message: str) -> None:
    assert_true(not condition, message)


exp_result = validate_experience_repository()
assert_true(exp_result["valid"] is True, "experience repository invalid")
assert_true(len(exp_result["index"]) == 4, "Experience count must remain 4")
ev_result = validate_evidence_repository(experience_result=exp_result)
assert_true(ev_result["valid"] is True, "evidence repository invalid")
assert_true(len(ev_result["index"]) == 37, "Evidence count must be 37 (36 prior + 1 new TELUS end-date record)")
claim_result = validate_claim_repository()
assert_true(claim_result["valid"] is True, "claim repository invalid")
assert_true(claim_result["records_checked"] == 13, "Claim count must remain 13 -- this milestone adds no new Claims")

EXPERIENCE_INDEX = exp_result["index"]
EVIDENCE_INDEX = ev_result["index"]
CLAIM_INDEX = claim_result["index"]

MASTER = json.loads(MASTER_PATH.read_text(encoding="utf-8"))
assert_true(len(MASTER["modules"]) == 13, "master must have 13 modules (6 WW + 5 MM + 2 TELUS)")

FORMAL_TITLE = "Digital Trust and Safety Analyst with English (tele-agent)"
DISPLAY_TITLE = "Digital Trust and Safety Analyst with English"
DATE_RANGE = "Nov 2024 – May 2025"
APPROVED_WORDING = {
    "MOD_TELUS_001_REVIEW": (
        "Reviewed 500+ user cases weekly against platform policy, identifying "
        "violations and behavioral patterns across structured and unstructured "
        "data under time-sensitive conditions."
    ),
    "MOD_TELUS_002_PATTERN": (
        "Tracked and categorized enforcement decisions for trend analysis and "
        "consistency, collaborating with policy, operations, and analytics teams "
        "to surface recurring risk patterns."
    ),
}

telus_section = next(s for s in MASTER["experience_sections"] if s["experience_id"] == "EXP_TELUS_001")
telus_modules = {m["module_id"]: m for m in MASTER["modules"] if m.get("experience_id") == "EXP_TELUS_001"}


# 1. Master validates cleanly as a whole.
master_result = validate_resume_master(MASTER, claim_index=CLAIM_INDEX, evidence_index=EVIDENCE_INDEX)
assert_true(master_result["valid"] is True, f"master must validate cleanly: {master_result['errors']}")
print("PASS 1: protected master validates cleanly with TELUS integrated.")


# 2. Formal TELUS title remains exactly the employer-issued string.
assert_true(telus_section["formal_title"] == FORMAL_TITLE, f"formal_title must be exact, got {telus_section['formal_title']!r}")
offer_evidence = EVIDENCE_INDEX["TELUS_OFFER_001"]
assert_true(FORMAL_TITLE in offer_evidence["fact"], "formal title must still be traceable to TELUS_OFFER_001")
print("PASS 2: formal TELUS title remains exactly the employer-issued string.")


# 3. Approved display title is exactly the approved text.
assert_true(telus_section["display_title"] == DISPLAY_TITLE, f"display_title must be exact, got {telus_section['display_title']!r}")
approval = telus_section["display_title_approval"]
assert_true(approval["approved"] is True, "display_title_approval must be approved=true")
assert_true(approval["is_source_verbatim"] is False, "display_title_approval must be is_source_verbatim=false")
assert_true(approval["approved_display_title"] == DISPLAY_TITLE, "approved_display_title must match display_title exactly")
print("PASS 3: approved display title is exact and correctly approved.")


# 4. "Content Safety Analyst" is not used as any structural presentation field
#    (module wording, section title fields). It legitimately appears once in
#    the master's own free-text "notes" field, explicitly documenting that it
#    was considered and NOT used -- the correct way to record that exclusion,
#    not a leak of it into presentation.
structural_text = json.dumps(MASTER["modules"]) + json.dumps(MASTER["experience_sections"]) + json.dumps(MASTER["contact"]) + json.dumps(MASTER["education"])
assert_false("Content Safety Analyst" in structural_text, "LinkedIn's display title must never appear in any structural presentation field")
print("PASS 4: 'Content Safety Analyst' is not used in any structural presentation field.")


# 5. Exact end date 2025-05-01 has correct human-attested, OBSERVED provenance.
enddate_evidence = EVIDENCE_INDEX["TELUS_ENDDATE_001"]
assert_true("2025-05-01" in enddate_evidence["fact"], "exact end date must be recorded")
assert_true(enddate_evidence["evidence_state"] == "OBSERVED", "end date evidence must be OBSERVED, not upgraded")
assert_true(
    "human attestation" in enddate_evidence["original_source"].lower() or "bora" in enddate_evidence["original_source"].lower(),
    "end date evidence must record direct human attestation as its source",
)
print("PASS 5: exact end date 2025-05-01 is human-attested with correct OBSERVED provenance.")


# 6. Exact end date is NOT represented as employer-VERIFIED anywhere.
assert_false(
    '"evidence_state": "VERIFIED"' in json.dumps(enddate_evidence) if False else enddate_evidence["evidence_state"] == "VERIFIED",
    "end date must never be VERIFIED",
)
assert_false("2025-05-01" in offer_evidence["fact"], "the employer offer must never be the cited source for the exact end date")
print("PASS 6: exact end date is not represented as employer-verified.")


# 7. Master renders the exact approved date range.
assert_true(telus_section["date_range"] == DATE_RANGE, f"date_range must be exact, got {telus_section['date_range']!r}")
print("PASS 7: master date_range is exactly 'Nov 2024 - May 2025'.")


# 8. No exact day leaks into normal résumé presentation.
default_patch = {
    "patch_id": "TELUS_MASTER_INT_DEFAULT",
    "target_master_id": MASTER["master_id"],
    "operations": [{"op": "REORDER_MODULES", "module_ids": MASTER["default_module_order"]}],
}
default_result = build_resume_derivative(
    master=MASTER, patch=default_patch, claim_index=CLAIM_INDEX, evidence_index=EVIDENCE_INDEX,
    derivative_id="DERIV_TELUS_MASTER_INT_DEFAULT",
)
assert_true(default_result["valid"] is True, f"default derivative must build: {default_result.get('errors')}")
presentation = build_resume_presentation_view(default_result["derivative"], experience_index=EXPERIENCE_INDEX)
assert_true(presentation["valid"] is True, f"presentation must resolve: {presentation.get('errors')}")
render = render_resume_text(presentation)
assert_true(render["valid"] is True, f"render must succeed: {render.get('errors')}")
assert_false("2025-05-01" in render["text"], "exact end day must never leak into rendered resume presentation")
assert_false("May 1" in render["text"], "exact end day must never leak into rendered resume presentation")
assert_true(DATE_RANGE in render["text"], "month-level date range must appear in rendered output")
print("PASS 8: no exact day leaks into normal resume presentation; only the month-level range appears.")


# 9. Both approved TELUS Claims remain OBSERVED.
assert_true(CLAIM_INDEX["CLAIM_TELUS_001"]["evidence_state"] == "OBSERVED", "CLAIM_TELUS_001 must remain OBSERVED")
assert_true(CLAIM_INDEX["CLAIM_TELUS_002"]["evidence_state"] == "OBSERVED", "CLAIM_TELUS_002 must remain OBSERVED")
print("PASS 9: both approved TELUS Claims remain OBSERVED.")


# 10. '500+ weekly' remains OBSERVED and is preserved exactly.
assert_true("500+ user cases weekly" in telus_modules["MOD_TELUS_001_REVIEW"]["wording"], "exact '500+ user cases weekly' phrasing must be preserved")
assert_true(EVIDENCE_INDEX["TELUS_REVIEW_001"]["evidence_state"] == "OBSERVED", "TELUS_REVIEW_001 must remain OBSERVED")
print("PASS 10: '500+ weekly' remains OBSERVED and preserved exactly.")


# 11. TELUS modules validate successfully now that Claims are approved.
for module_id, module in telus_modules.items():
    lineage = validate_resume_module_lineage(module, claim_index=CLAIM_INDEX, evidence_index=EVIDENCE_INDEX)
    assert_true(lineage["valid"] is True, f"{module_id} must pass production module-lineage validation: {lineage.get('errors')}")
print("PASS 11: both TELUS modules validate successfully.")


# 12. Protected master contains exactly the intended two TELUS modules.
assert_true(
    set(telus_modules.keys()) == {"MOD_TELUS_001_REVIEW", "MOD_TELUS_002_PATTERN"},
    f"master must contain exactly the two approved TELUS modules, got {set(telus_modules.keys())}",
)
assert_true(telus_section["bullet_module_ids"] == ["MOD_TELUS_001_REVIEW", "MOD_TELUS_002_PATTERN"], "section bullet order must match approved modules exactly")
print("PASS 12: protected master contains exactly the intended two TELUS modules.")


# 13. TELUS bullet wording remains byte-identical to approved wording.
for module_id, expected_wording in APPROVED_WORDING.items():
    assert_true(telus_modules[module_id]["wording"] == expected_wording, f"{module_id} wording must be byte-identical to approved text")
print("PASS 13: TELUS bullet wording is byte-identical to approved wording.")


# 14. No third TELUS bullet appears anywhere (master or rendered output).
assert_true(len(telus_section["bullet_module_ids"]) == 2, "exactly 2 TELUS bullets may exist in the section")
telus_render_block = render["text"][render["text"].index("TELUS Digital Bulgaria"):]
telus_bullet_lines = [line for line in telus_render_block.splitlines() if line.startswith("- ")]
assert_true(len(telus_bullet_lines) == 2, f"rendered output must show exactly 2 TELUS bullets, got {len(telus_bullet_lines)}")
print("PASS 14: no third TELUS bullet appears anywhere.")


# 15. Winter Walk remains unchanged.
ww_modules = [m for m in MASTER["modules"] if m.get("experience_id") == "EXP_WW_001"]
assert_true(len(ww_modules) == 6, "Winter Walk module count must remain 6")
ww_section = next(s for s in MASTER["experience_sections"] if s["experience_id"] == "EXP_WW_001")
assert_true(ww_section["date_range"] == "Jun 2026 – Aug 2026", "Winter Walk date_range must remain unchanged")
assert_true(ww_section["display_title"] == "AI Researcher & Developer Intern", "Winter Walk display_title must remain unchanged")
print("PASS 15: Winter Walk remains unchanged.")


# 16. MarketMind remains unchanged.
mm_modules = [m for m in MASTER["modules"] if m["module_type"] == "PROJECT_BULLET"]
assert_true(len(mm_modules) == 5, "MarketMind module count must remain 5")
assert_false(any(s["experience_id"] == "EXP_MM_001" for s in MASTER["experience_sections"]), "MarketMind must still have no experience_sections entry")
print("PASS 16: MarketMind remains unchanged.")


# 17. Brandeis Education remains unchanged.
assert_true(
    MASTER["education"] == [
        {
            "education_id": "EDU_BRANDEIS_MSBA",
            "school_name": "Brandeis University",
            "degree_name": "Business Analytics (M.S.)",
            "date_range": "Fall 2025 – Summer 2026",
            "location": None,
        }
    ],
    "Brandeis education entry must remain unchanged",
)
print("PASS 17: Brandeis Education remains unchanged.")


# 18. Renderer remains deterministic.
render_repeat = render_resume_text(build_resume_presentation_view(default_result["derivative"], experience_index=EXPERIENCE_INDEX))
assert_true(render_repeat == render, "renderer output must remain deterministic across repeat calls")
print("PASS 18: renderer remains deterministic.")


# 19. No forbidden semantic leakage appears specifically within the TELUS
#     portion of the rendered output (checked against the TELUS block only,
#     not the whole resume -- Winter Walk's own already-approved wording
#     legitimately mentions unrelated terms like "public dashboards", which
#     is pre-existing approved content, not a TELUS leak).
FORBIDDEN_TERMS = [
    "sql", "business intelligence", " bi ", "dashboard", "database", "data pipeline",
    "automation platform", "policy creation", "quantified process improvement",
    "united states", "u.s.a", " usa ", "salary", "compensation", "probation",
]
lower_telus_block = telus_render_block.lower()
for term in FORBIDDEN_TERMS:
    assert_false(term in lower_telus_block, f"forbidden term {term!r} must not leak into the TELUS portion of rendered output")
print("PASS 19: no forbidden semantic leakage appears in the TELUS portion of rendered output.")


print("PASS: TELUS_MASTER_INTEGRATION_V1 tests completed successfully.")
