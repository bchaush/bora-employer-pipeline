"""Regression tests for CANDIDATE_SOURCE_INGESTION_V1.

Covers:
- undergraduate credential evidence exists independently of the Brandeis
  M.S. and never implies unsupported institutional-quality ("top-tier
  university") facts;
- EXPLICIT_EXCEL / SPREADSHEET (Google Sheets) / CSV_OR_TABULAR_DATA remain
  distinct capability tiers -- generic evidence must not silently become
  explicit Excel evidence;
- newly ingested draft claims (human_approval=false) are correctly excluded
  from matching, exactly like every other unapproved claim in this
  repository;
- protected TELUS/Winter Walk identity is untouched by this milestone,
  proving profile-display wording ("Content Safety Analyst", "May 2026")
  never silently overwrote already-approved repository truth.

Exercises real production code (schema validators, repository loaders,
requirement_match.py) -- no logic is duplicated here.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from claim_repository import validate_claim_repository  # noqa: E402
from evidence_repository import validate_evidence_repository  # noqa: E402
from experience_repository import validate_experience_repository  # noqa: E402
from requirement_match import (  # noqa: E402
    infer_requirement_capabilities,
    load_reusable_claims,
    match_requirement,
)


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        print(f"FAIL: {message}")
        raise SystemExit(1)


exp_result = validate_experience_repository()
assert_true(exp_result["valid"] is True, "experience repository must be valid")
assert_true(exp_result["records_checked"] == 7, f"expected 7 Experience records (4 prior + 3 new), got {exp_result['records_checked']}")
ev_result = validate_evidence_repository()
assert_true(ev_result["valid"] is True, "evidence repository must be valid")
assert_true(ev_result["records_checked"] == 43, f"expected 43 Evidence records (37 prior + 3 initial + 2 human-source-resolution: DCOMMERCE_REFERENCE_001, DCOMMERCE_LINKEDIN_PERIOD_001 + 1 Brandeis MSBA awarded attestation record), got {ev_result['records_checked']}")
cl_result = validate_claim_repository()
assert_true(cl_result["valid"] is True, "claim repository must be valid")
assert_true(cl_result["records_checked"] == 16, f"expected 16 Claim records (13 prior + 3 new), got {cl_result['records_checked']}")

EXPERIENCE_INDEX = exp_result["index"]
EVIDENCE_INDEX = ev_result["index"]
CLAIM_INDEX = cl_result["index"]


# ======================================================================
# 1. Undergraduate credential: independence from Brandeis M.S.
# ======================================================================
assert_true("EXP_EDU_UNWE_001" in EXPERIENCE_INDEX, "undergraduate Experience must exist")
assert_true("EXP_EDU_BRANDEIS_001" in EXPERIENCE_INDEX, "Brandeis M.S. Experience must remain present/unchanged")
assert_true(EXPERIENCE_INDEX["EXP_EDU_UNWE_001"]["experience_id"] != EXPERIENCE_INDEX["EXP_EDU_BRANDEIS_001"]["experience_id"], "undergraduate and Brandeis M.S. must be distinct Experience records")

unwe_evidence = EVIDENCE_INDEX["EDU_UNWE_IDENTITY_001"]
assert_true(unwe_evidence["experience_id"] == "EXP_EDU_UNWE_001", "undergraduate evidence must cite the undergraduate Experience, not Brandeis")
assert_true("BRANDEIS" not in unwe_evidence["fact"].upper(), "undergraduate evidence fact must not reference Brandeis")
assert_true(unwe_evidence["evidence_state"] == "OBSERVED", "candidate-supplied résumé-history evidence must be OBSERVED, not VERIFIED (no official transcript supplied)")
print("PASS 1: undergraduate credential evidence exists independently of the Brandeis M.S., correctly OBSERVED-tier.")


# ======================================================================
# 2. Bachelor's degree must never imply "top-tier university".
# ======================================================================
unwe_claim = CLAIM_INDEX["CLAIM_EDU_UNWE_001"]
assert_true(unwe_claim["human_approval"] is False, "undergraduate claim must not be self-approved")
assert_true("top-tier university" in unwe_claim["forbidden_contexts"], "undergraduate claim must explicitly forbid a top-tier-university context")
assert_true("top-tier" not in unwe_claim["wording"].lower(), "undergraduate claim wording must not assert institutional ranking")

# The capability pattern must recognize the degree fact but must never fire
# on institutional-quality language alone.
degree_only = {"text": "Bachelor's degree required", "source_text": "Bachelor's degree required", "domain": None, "category": None, "technology": []}
# REQUIREMENT_QUALIFIER_SEMANTICS_V1 superseded this assertion's original
# form twice: first it required frozenset() for "from a top-tier university"
# alone (institutional-quality language completely invisible to capability
# inference -- the OLD protection mechanism Q-1's audit found insufficient,
# since it let a bundled "Bachelor's ... from top-tier university"
# requirement silently resolve SUPPORTED once a plain degree claim was
# approved). That was corrected to give institutional-quality language its
# own dedicated qualifier tag. The regex-scope-tightening pass then narrowed
# detection to require a credential word (degree/bachelor's/master's/
# credential) connected via "from" to the institution phrase -- so
# "from a top-tier university" with no credential word present in the same
# text no longer matches by itself (this alone is correct: it mirrors real
# false-positive JD phrasing like "customers include top-tier universities",
# where an institution is merely an object, not a credential source -- see
# tests/requirement_qualifier_semantics_v1_test.py PASS L). This control
# text is updated to "degree from a top-tier university" -- a bare "degree"
# (not "bachelor's degree") that still triggers the credential-connected
# qualifier pattern while confirming it does NOT also manufacture the
# bachelor's-specific bachelors_degree_credential tag (the invariant this
# test exists to guard: institutional-quality language alone must never
# produce a degree-credential claim by itself). See
# tests/requirement_qualifier_semantics_v1_test.py for the full PARTIAL-path
# and regex-scope-tightening regression coverage.
quality_only = {"text": "degree from a top-tier university", "source_text": "degree from a top-tier university", "domain": None, "category": None, "technology": []}
assert_true(infer_requirement_capabilities(degree_only) == frozenset({"bachelors_degree_credential"}), "degree-only text must produce the bachelors_degree_credential tag")
assert_true(
    infer_requirement_capabilities(quality_only) == frozenset({"institutional_quality_qualifier"}),
    "institutional-quality language alone must produce only its own qualifier tag, never the bachelors_degree_credential tag",
)
print("PASS 2: bachelor's-degree recognition never extends to unsupported institutional-quality ('top-tier university') claims -- now represented as an explicit, never-claimed qualifier tag rather than blind non-recognition.")


# ======================================================================
# 3. Excel tiers remain distinct: EXPLICIT_EXCEL != SPREADSHEET (Google
#    Sheets) != CSV_OR_TABULAR_DATA.
# ======================================================================
dcommerce_evidence = EVIDENCE_INDEX["DCOMMERCE_EXCEL_001"]
bulmarma_evidence = EVIDENCE_INDEX["BULMARMA_EXCEL_001"]
assert_true(dcommerce_evidence["technologies"] == ["Microsoft Excel"], "D Commerce evidence must tag Microsoft Excel explicitly")
assert_true(bulmarma_evidence["technologies"] == ["Microsoft Excel"], "Bulmarma evidence must tag Microsoft Excel explicitly")

# Existing Winter Walk Google Sheets evidence must not be reclassified.
ww_sheets_evidence = EVIDENCE_INDEX["WW_ARCH_002"]
assert_true("Google Sheets" in ww_sheets_evidence["technologies"], "existing Winter Walk Google Sheets evidence must remain Google Sheets, not Excel")
assert_true("Microsoft Excel" not in ww_sheets_evidence["technologies"], "Google Sheets evidence must never be silently promoted to Microsoft Excel")

# Existing Winter Walk CSV evidence must not be reclassified as Excel.
ww_csv_evidence = EVIDENCE_INDEX["WW_DATA_002"]
assert_true("Microsoft Excel" not in ww_csv_evidence.get("technologies", []), "CSV/tabular-data evidence must never be silently promoted to Microsoft Excel")

# Generic Sheets/CSV text must not trigger the new explicit-Excel capability tag.
sheets_text = {"text": "Uses Google Sheets for tracking", "source_text": "Uses Google Sheets for tracking", "domain": None, "category": None, "technology": []}
csv_text = {"text": "CSV import and data intake", "source_text": "CSV import and data intake", "domain": None, "category": None, "technology": []}
assert_true("excel_proficiency" not in infer_requirement_capabilities(sheets_text), "Google Sheets text must not trigger the Excel-proficiency tag")
assert_true("excel_proficiency" not in infer_requirement_capabilities(csv_text), "CSV/tabular text must not trigger the Excel-proficiency tag")
print("PASS 3: EXPLICIT_EXCEL, SPREADSHEET (Google Sheets), and CSV_OR_TABULAR_DATA remain distinct; no tier was silently promoted into another.")


# ======================================================================
# 4. Excel precision: "excel" as an ordinary verb must not false-positive.
# ======================================================================
verb_text = {"text": "You will excel in a fast-paced environment", "source_text": "You will excel in a fast-paced environment", "domain": None, "category": None, "technology": []}
assert_true(infer_requirement_capabilities(verb_text) == frozenset(), "the ordinary verb 'excel in' must never be recognized as Excel-tool proficiency")
tool_text = {"text": "Excel skills", "source_text": "Excel skills", "domain": None, "category": None, "technology": []}
assert_true(infer_requirement_capabilities(tool_text) == frozenset({"excel_proficiency"}), "'Excel skills' (the tool) must be recognized")
# REQUIREMENT_QUALIFIER_SEMANTICS_V1: this positive control previously used
# the literal text "strong Excel skills" -- which is exactly Q-2's
# demonstrated defect phrase, now intentionally changed to also carry
# excel_elevated_proficiency_qualifier (see
# tests/requirement_qualifier_semantics_v1_test.py). Switched the control
# text here to plain "Excel skills" so this assertion continues to test only
# what it originally intended (the tool name is recognized), without
# colliding with the now-corrected qualifier behavior it was never meant to
# exercise.
print("PASS 4: Excel-verb usage ('excel in/at') does not false-positive as Excel-tool proficiency.")


# ======================================================================
# 5. Draft claims (human_approval=false) are correctly excluded from
#    matching -- new evidence exists and is traceable, but is not yet
#    usable by the matcher, exactly like every other unapproved claim.
# ======================================================================
reusable = load_reusable_claims(CLAIM_INDEX, EVIDENCE_INDEX)
reusable_ids = {c["claim_id"] for c in reusable}
for draft_id in ("CLAIM_EDU_UNWE_001", "CLAIM_DCOMMERCE_001", "CLAIM_BULMARMA_001"):
    assert_true(draft_id not in reusable_ids, f"{draft_id} must remain excluded from matching until explicitly approved (human_approval=false)")
assert_true(len(reusable_ids) == 13, f"reusable claim count must remain 13 (unchanged) until these drafts are approved; got {len(reusable_ids)}")

degree_requirement = {
    "requirement_id": "REQ_TEST_DEGREE", "text": "Bachelor's Degree (or higher) from top-tier university",
    "source_text": "Bachelor's Degree (or higher) from top-tier university", "domain": None, "category": None,
    "technology": [], "relevance": "HIGH", "importance": "MANDATORY",
}
degree_match = match_requirement(job_id="JOB_TEST", requirement=degree_requirement, reusable_claims=reusable, evidence_index=EVIDENCE_INDEX, match_index=0)
assert_true(degree_match["result"] == "NONE", f"degree requirement must still be NONE while the claim is an unapproved draft; got {degree_match['result']}")
print("PASS 5: newly ingested draft claims are traceable but correctly excluded from matching until approved -- current matcher behavior is unchanged by this ingestion.")


# ======================================================================
# 6. Protected TELUS / Winter Walk identity is untouched by this
#    milestone -- profile-display wording never overwrote approved truth.
# ======================================================================
telus_experience = json.loads((ROOT / "experiences" / "EXP_TELUS_001.json").read_text(encoding="utf-8"))
assert_true(
    "Digital Trust and Safety Analyst with English (tele-agent)" in telus_experience["notes"],
    "TELUS protected formal title must remain unmutated",
)
assert_true("Content Safety Analyst" in telus_experience["notes"], "TELUS notes must still document (not adopt) the LinkedIn/profile display title as a separately-noted, non-authoritative fact")

master = json.loads((ROOT / "resume" / "master" / "RESUME_MASTER_WW_V1.json").read_text(encoding="utf-8"))
ww_section = next(s for s in master["experience_sections"] if s["section_id"] == "SEC_WW_001")
assert_true(ww_section["date_range"] == "Jun 2026 – Aug 2026", f"Winter Walk protected date_range must remain 'Jun 2026 – Aug 2026', not the profile-display 'May 2026 – Aug 2026'; got {ww_section['date_range']}")
telus_section = next(s for s in master["experience_sections"] if s["section_id"] == "SEC_TELUS_001")
assert_true(telus_section["display_title"] == "Digital Trust and Safety Analyst with English", f"TELUS approved display title must remain unchanged; got {telus_section['display_title']}")
print("PASS 6: protected TELUS/Winter Walk identity is byte-unchanged; profile-display wording was never used to overwrite approved repository truth.")


# ======================================================================
# 7. D Commerce human source resolution: VERIFIED employer letter
#    establishes the canonical chronology and EMPLOYMENT reclassification,
#    without upgrading the still-unverified Excel/transaction facts.
# ======================================================================
dcommerce_offer = EVIDENCE_INDEX["DCOMMERCE_REFERENCE_001"]
assert_true(dcommerce_offer["evidence_state"] == "VERIFIED", "D Commerce employer Letter of Reference must be VERIFIED-tier")
assert_true("09.08.2021" in dcommerce_offer["fact"], "D Commerce offer evidence must state the internship start date")
assert_true("01.10.2021" in dcommerce_offer["fact"], "D Commerce offer evidence must state the full-time transition date")
assert_true("19.09.2022" in dcommerce_offer["fact"], "D Commerce offer evidence must state the documented end date")
assert_true("Junior expert" in dcommerce_offer["fact"], "D Commerce offer evidence must state the formal employer-side title 'Junior expert'")

dcommerce_linkedin = EVIDENCE_INDEX["DCOMMERCE_LINKEDIN_PERIOD_001"]
assert_true(dcommerce_linkedin["evidence_state"] == "OBSERVED", "D Commerce LinkedIn display evidence must remain OBSERVED, not VERIFIED")
assert_true("Junior Financial Data Analyst" in dcommerce_linkedin["fact"], "D Commerce LinkedIn evidence must state the display title distinctly from the formal title")
assert_true(dcommerce_linkedin["fact"] != dcommerce_offer["fact"], "formal employer title and LinkedIn display title must never be merged into a single fact")

dcommerce_experience = EXPERIENCE_INDEX["EXP_DCOMMERCE_001"]
assert_true(dcommerce_experience["experience_type"] == "EMPLOYMENT", "D Commerce must be reclassified EMPLOYMENT now that a VERIFIED employer document exists, paralleling TELUS")
assert_true(dcommerce_experience["experience_type"] == EXPERIENCE_INDEX["EXP_TELUS_001"]["experience_type"], "D Commerce EMPLOYMENT classification must match the TELUS precedent it is modeled on")

# The still-unverified Excel/transaction facts must not inherit VERIFIED
# merely because the overall relationship is now VERIFIED.
assert_true(EVIDENCE_INDEX["DCOMMERCE_EXCEL_001"]["evidence_state"] == "OBSERVED", "D Commerce Excel/transaction evidence must remain OBSERVED even though the employment relationship is now VERIFIED")
print("PASS 7: D Commerce human source resolution correctly establishes VERIFIED chronology and EMPLOYMENT reclassification while keeping Excel/transaction facts OBSERVED-tier.")


# ======================================================================
# 8. Bulmarma human source resolution: Bora's explicit correction updates
#    the canonical chronology/org display without upgrading evidence state
#    or changing experience_type (no equivalent employer document exists).
# ======================================================================
bulmarma_experience = EXPERIENCE_INDEX["EXP_BULMARMA_001"]
assert_true(bulmarma_experience["experience_type"] == "ORGANIZATIONAL_ENGAGEMENT", "Bulmarma must remain ORGANIZATIONAL_ENGAGEMENT -- no equivalent employer document was supplied for Bulmarma in this milestone")
assert_true("Sep 2022 - Nov 2023" in bulmarma_experience["notes"], "Bulmarma notes must document the corrected Sep 2022 - Nov 2023 chronology")
assert_true("Nov 2024" in bulmarma_experience["notes"], "Bulmarma notes must still name the superseded Nov 2024 value so the correction is auditable")
assert_true("Bulmarma 2008 Ltd" in bulmarma_experience["organization"], "Bulmarma organization display must be the corrected 'Bulmarma 2008 Ltd'")
assert_true("OOD" in bulmarma_experience["notes"], "Bulmarma notes must name the superseded 'Bulmarma OOD' résumé value so the correction is auditable")
assert_true("legal-entity equivalence" in bulmarma_experience["notes"], "Bulmarma notes must explicitly disclaim any 'Ltd'='OOD' legal-entity equivalence")

# Bora's correction resolves which history to use, but is not itself
# independent verification -- Bulmarma evidence must stay OBSERVED.
assert_true(EVIDENCE_INDEX["BULMARMA_EXCEL_001"]["evidence_state"] == "OBSERVED", "Bulmarma evidence must remain OBSERVED -- a human-authorized correction is not independent employer verification")
print("PASS 8: Bulmarma human source resolution correctly updates the canonical chronology/org display via Bora's explicit correction, without upgrading evidence state or experience_type.")


# ======================================================================
# 9. All three draft claims remain unapproved/non-reusable after the
#    source-resolution correction -- claim wording itself was untouched.
# ======================================================================
for draft_id in ("CLAIM_EDU_UNWE_001", "CLAIM_DCOMMERCE_001", "CLAIM_BULMARMA_001"):
    claim = CLAIM_INDEX[draft_id]
    assert_true(claim["human_approval"] is False, f"{draft_id} must remain human_approval=false after source resolution")
reusable_after = load_reusable_claims(CLAIM_INDEX, EVIDENCE_INDEX)
reusable_ids_after = {c["claim_id"] for c in reusable_after}
for draft_id in ("CLAIM_EDU_UNWE_001", "CLAIM_DCOMMERCE_001", "CLAIM_BULMARMA_001"):
    assert_true(draft_id not in reusable_ids_after, f"{draft_id} must still be excluded from matching after source resolution")
assert_true(len(reusable_ids_after) == 13, f"reusable claim count must remain 13 after source resolution (no claim was approved); got {len(reusable_ids_after)}")
print("PASS 9: all three draft claims remain unapproved and excluded from matching after the source-resolution correction.")

print("ALL candidate_source_ingestion_v1_test CHECKS PASSED")
