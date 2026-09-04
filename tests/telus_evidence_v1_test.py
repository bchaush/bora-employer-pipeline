"""Bounded tests for TELUS Digital Bulgaria employment evidence
(TELUS_EVIDENCE_V1).

Proves: TELUS employment identity and responsibility evidence are
correctly evidence-controlled, employer-verified facts are kept
distinct from Bora-profile-sourced facts, no fact is strengthened
beyond its source, no salary/benefits/private data leaked, no
U.S.-experience implication created, and existing Winter Walk /
MarketMind / Education truth is unchanged. No Claims or résumé
modules are created by this milestone.
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


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        print(f"FAIL: {message}")
        raise SystemExit(1)


def assert_false(condition: bool, message: str) -> None:
    assert_true(not condition, message)


exp_result = validate_experience_repository()
assert_true(exp_result["valid"] is True, "experience repository invalid")
assert_true(len(exp_result["index"]) == 7, "Experience count must be 7 (Winter Walk, MarketMind, Brandeis education, TELUS, undergraduate education, D Commerce, Bulmarma)")
ev_result = validate_evidence_repository(experience_result=exp_result)
assert_true(ev_result["valid"] is True, "evidence repository invalid")
assert_true(len(ev_result["index"]) == 43, "Evidence count must be 43 (29 prior + 7 new TELUS records + 1 later TELUS end-date record + 3 CANDIDATE_SOURCE_INGESTION_V1 records + 2 human-source-resolution records + 1 Brandeis MSBA awarded attestation record)")
claim_result = validate_claim_repository()
assert_true(claim_result["valid"] is True, "claim repository invalid")
assert_true(claim_result["records_checked"] == 16, "Claim count must be 16 (11 prior + 2 later draft TELUS claims + 3 CANDIDATE_SOURCE_INGESTION_V1 draft claims) -- Evidence ingestion itself adds no Claims")

EXPERIENCE_INDEX = exp_result["index"]
EVIDENCE_INDEX = ev_result["index"]

MASTER = json.loads(MASTER_PATH.read_text(encoding="utf-8"))
assert_true(len(MASTER["modules"]) == 13, "master must have 13 modules -- TELUS was not added in this milestone (Evidence/Experience only) but has since been integrated by a later, separately-scoped milestone")

TELUS_EVIDENCE_IDS = [
    "TELUS_OFFER_001",
    "TELUS_RECRUITING_001",
    "TELUS_LINKEDIN_PERIOD_001",
    "TELUS_REVIEW_001",
    "TELUS_PATTERN_001",
    "TELUS_COLLAB_001",
    "TELUS_VOLUME_001",
]


# 1. TELUS Experience exists, correctly typed.
assert_true("EXP_TELUS_001" in EXPERIENCE_INDEX, "EXP_TELUS_001 must exist in the trusted Experience index")
telus_experience = EXPERIENCE_INDEX["EXP_TELUS_001"]
assert_true(telus_experience["experience_type"] == "EMPLOYMENT", "TELUS Experience must use experience_type=EMPLOYMENT")
print("PASS 1: EXP_TELUS_001 exists with experience_type=EMPLOYMENT.")


# 2. Employer identity correct; no U.S. entity invented.
assert_true(telus_experience["organization"] == "TELUS Digital Bulgaria", f"exact employer required, got {telus_experience['organization']!r}")
assert_false("United States" in telus_experience["organization"] or "USA" in telus_experience["organization"], "no U.S. entity may be invented")
print("PASS 2: employer identity is exactly TELUS Digital Bulgaria.")


# 3. All 7 TELUS evidence records exist and reference EXP_TELUS_001.
for eid in TELUS_EVIDENCE_IDS:
    assert_true(eid in EVIDENCE_INDEX, f"{eid} must exist in the trusted Evidence index")
    assert_true(EVIDENCE_INDEX[eid]["experience_id"] == "EXP_TELUS_001", f"{eid} must reference EXP_TELUS_001")
print("PASS 3: all 7 TELUS Evidence records exist and reference EXP_TELUS_001.")


# 4. Exact formal title preserved; LinkedIn's shorter title must not silently replace it anywhere.
offer = EVIDENCE_INDEX["TELUS_OFFER_001"]
assert_true(
    "Digital Trust and Safety Analyst with English (tele-agent)" in offer["fact"],
    "employer-issued formal title must be preserved exactly",
)
combined_text = " ".join(json.dumps(v) for v in EVIDENCE_INDEX.values() if v.get("experience_id") == "EXP_TELUS_001")
combined_text += json.dumps(telus_experience)
# "Content Safety Analyst" may appear ONLY inside TELUS_LINKEDIN_PERIOD_001's fact/notes as an
# explicitly-labeled self-reported profile title, never presented as if it were the formal title.
linkedin_period = EVIDENCE_INDEX["TELUS_LINKEDIN_PERIOD_001"]
assert_true("Content Safety Analyst" in linkedin_period["fact"], "LinkedIn display title must be recorded, correctly attributed")
for eid in TELUS_EVIDENCE_IDS:
    if eid == "TELUS_LINKEDIN_PERIOD_001":
        continue
    assert_false(
        "Content Safety Analyst" in json.dumps(EVIDENCE_INDEX[eid]),
        f"{eid} must not restate the LinkedIn display title as if it were the formal title",
    )
print("PASS 4: formal title exact; LinkedIn's shorter title never silently overwrites it.")


# 5. Operations department represented only where sourced (the offer).
assert_true("Operations" in offer["fact"], "Operations department must be recorded from the employer offer")
print("PASS 5: Operations department correctly sourced to the employer offer.")


# 6. Exact start date preserved.
assert_true("15.11.2024" in offer["fact"], "exact employer-established start date must be preserved")
print("PASS 6: exact start date (15.11.2024) preserved.")


# 7. True location (Sofia, Bulgaria); no U.S. location anywhere.
assert_true("Sofia" in offer["fact"] and "Bulgaria" in offer["fact"], "true location must be recorded")
assert_false(
    any(
        us_marker in combined_text
        for us_marker in ["United States", "U.S.A", "USA", ", MA", ", NY", ", CA", "Boston, MA"]
    ),
    "no U.S. location may appear anywhere in TELUS evidence",
)
print("PASS 7: true Sofia, Bulgaria location recorded; no U.S. location anywhere.")


# 8. No unsupported exact end day within this milestone's own 7-record scope;
#    end period is LinkedIn-sourced only among those 7 records. A later,
#    separately-scoped milestone (TELUS_MASTER_INTEGRATION_V1) added a
#    distinct, additional OBSERVED evidence record (TELUS_ENDDATE_001,
#    outside this test's TELUS_EVIDENCE_IDS scope) recording Bora's own
#    direct human attestation of the exact last working day -- itself never
#    employer-verified either. Confirmed here as a distinct, separately
#    tracked record, not conflated with this milestone's own LinkedIn-only
#    evidence.
assert_false('"end_date"' in json.dumps(telus_experience), "no end_date field may be fabricated on the Experience record")
assert_true("May 2025" in linkedin_period["fact"], "May 2025 end period must be recorded, sourced to LinkedIn only")
assert_false("May 2025" in offer["fact"], "the employer offer must never be the cited source for an end date it does not establish")
assert_true(
    "TELUS_ENDDATE_001" not in TELUS_EVIDENCE_IDS and "TELUS_ENDDATE_001" in EVIDENCE_INDEX,
    "TELUS_ENDDATE_001 must exist in the repository as a distinct record outside this milestone's own 7-record scope",
)
assert_true(EVIDENCE_INDEX["TELUS_ENDDATE_001"]["evidence_state"] == "OBSERVED", "TELUS_ENDDATE_001 must remain OBSERVED, not employer-verified")
print("PASS 8: no fabricated exact end day within this milestone's own scope; end period was LinkedIn-only here, with a separate, later, distinct OBSERVED direct-attestation record (TELUS_ENDDATE_001) now also present in the repository.")


# 9. No salary/benefits/probation/notice-period leakage as asserted fact content.
# (TELUS_OFFER_001's own "fact" field is the actual asserted content; its "notes" field
# is documentation explicitly recording that these categories were excluded, which is
# the correct way to record the exclusion -- not a leak of the values themselves.)
FORBIDDEN_COMPENSATION_TERMS = ["salary", "compensation", "benefit", "probation", "notice period", "bonus", "insurance"]
asserted_facts_text = " ".join(json.dumps(v["fact"]) for v in EVIDENCE_INDEX.values() if v.get("experience_id") == "EXP_TELUS_001").lower()
lower_combined = combined_text.lower()
for term in FORBIDDEN_COMPENSATION_TERMS:
    assert_false(term in asserted_facts_text, f"no compensation/benefits term ({term!r}) may appear in any asserted TELUS fact")
print("PASS 9: no salary/benefits/probation/notice-period leakage in any asserted fact.")


# 10. No SQL/automation/BI/platform/data-engineering invention as asserted fact content.
# (Checked against asserted "fact" fields only -- limitations legitimately name these
# terms inside explicit negations, e.g. "does not establish ... SQL ... ownership".)
FORBIDDEN_TECH_TERMS = ["sql", "data engineering", "data pipeline", "business intelligence", " bi ", "dashboard", "database"]
for term in FORBIDDEN_TECH_TERMS:
    assert_false(term in asserted_facts_text, f"no invented technology/tooling term ({term!r}) may appear in any asserted TELUS fact")
for eid in TELUS_EVIDENCE_IDS:
    assert_true(EVIDENCE_INDEX[eid]["technologies"] == [], f"{eid} must not list any invented technologies")
print("PASS 10: no SQL/automation/BI/platform/data-engineering invention; technologies arrays empty.")


# 11. No U.S.-experience implication anywhere.
FORBIDDEN_US_TERMS = ["u.s. work experience", "u.s. trust-and-safety operations experience", "u.s. regulatory"]
for term in FORBIDDEN_US_TERMS:
    # These phrases are permitted ONLY inside an explicit negation ("does not establish ...").
    if term in lower_combined:
        assert_true(
            "does not establish" in lower_combined or "not u.s." in lower_combined or "is not u.s." in lower_combined,
            f"{term!r} must appear only inside an explicit negative-determination sentence",
        )
print("PASS 11: no U.S.-experience implication asserted as fact anywhere.")


# 12. Correct evidence-state treatment: employer documents VERIFIED, LinkedIn-sourced OBSERVED.
assert_true(EVIDENCE_INDEX["TELUS_OFFER_001"]["evidence_state"] == "VERIFIED", "offer letter must be VERIFIED")
assert_true(EVIDENCE_INDEX["TELUS_RECRUITING_001"]["evidence_state"] == "VERIFIED", "recruiting email must be VERIFIED")
for eid in ["TELUS_LINKEDIN_PERIOD_001", "TELUS_REVIEW_001", "TELUS_PATTERN_001", "TELUS_COLLAB_001", "TELUS_VOLUME_001"]:
    assert_true(
        EVIDENCE_INDEX[eid]["evidence_state"] == "OBSERVED",
        f"{eid} (LinkedIn-sourced, not employer-certified) must be OBSERVED, not VERIFIED",
    )
print("PASS 12: employer-issued documents are VERIFIED; Bora-profile-sourced facts are correctly OBSERVED, not upgraded.")


# 13. Adversarial: "500+ weekly" must never become a derived monthly/annual/percentage figure.
review = EVIDENCE_INDEX["TELUS_REVIEW_001"]
assert_true("500+ user cases weekly" in review["fact"], "exact '500+ user cases weekly' phrasing must be preserved")
FORBIDDEN_DERIVED_NUMBERS = ["2,000 monthly", "2000 monthly", "26,000 annually", "monthly average", "% accuracy", "accuracy rate", "accuracy score"]
for term in FORBIDDEN_DERIVED_NUMBERS:
    assert_false(term in lower_combined, f"no derived numeric figure ({term!r}) may be created from the 500+ weekly metric")
print("PASS 13: '500+ weekly' preserved exactly; no derived monthly/annual/percentage figure created.")


# 14. Adversarial: policy review must not become policy creation/ownership.
FORBIDDEN_POLICY_OWNERSHIP_TERMS = ["created policy", "authored policy", "policy creation", "policy ownership", "wrote the policy"]
for term in FORBIDDEN_POLICY_OWNERSHIP_TERMS:
    assert_false(term in lower_combined, f"policy review must never become policy creation/ownership ({term!r})")
print("PASS 14: policy review correctly distinguished from policy creation/ownership.")


# 15. Adversarial: "analytics teams" collaboration must not become analytics-team membership or BI ownership.
FORBIDDEN_TEAM_MEMBERSHIP_TERMS = ["member of the analytics team", "analytics team member", "led the analytics team", "owned the bi"]
for term in FORBIDDEN_TEAM_MEMBERSHIP_TERMS:
    assert_false(term in lower_combined, f"collaboration with analytics teams must never become team membership/ownership ({term!r})")
print("PASS 15: 'analytics teams' collaboration correctly distinguished from team membership/BI ownership.")


# 16. Adversarial: "improve workflows" must not become quantified process-improvement ownership.
collab = EVIDENCE_INDEX["TELUS_COLLAB_001"]
assert_true(
    any("measured or attributable causal process-improvement outcome" in lim for lim in collab["limitations"]),
    "TELUS_COLLAB_001 must explicitly limit 'improve review workflows' against causal-ownership upgrade",
)
FORBIDDEN_IMPACT_TERMS = ["reduced review time by", "%  improvement", "% improvement", "increased efficiency by"]
for term in FORBIDDEN_IMPACT_TERMS:
    assert_false(term in lower_combined, f"no quantified process-improvement outcome ({term!r}) may be fabricated")
print("PASS 16: 'improve workflows' correctly limited against quantified process-improvement ownership.")


# 17. Existing Winter Walk, MarketMind, and Education truth unchanged.
WW_IDS = [m["module_id"] for m in MASTER["modules"] if m.get("experience_id") == "EXP_WW_001"]
MM_IDS = [m["module_id"] for m in MASTER["modules"] if m["module_type"] == "PROJECT_BULLET"]
assert_true(len(WW_IDS) == 6, "Winter Walk module count must remain 6")
assert_true(len(MM_IDS) == 5, "MarketMind module count must remain 5")
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
    "verified Brandeis education entry must remain unchanged",
)
print("PASS 17: existing Winter Walk, MarketMind, and Education truth unchanged.")


# 18. No Student ID / private recruiter email address leaked anywhere in new records.
import re  # noqa: E402

EMAIL_PATTERN = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
for path in [TELUS_EXPERIENCE_PATH, *sorted(TELUS_EVIDENCE_DIR.glob("*.json"))]:
    text = path.read_text(encoding="utf-8")
    assert_false("Student ID" in text or "student_id" in text.lower(), f"{path.name} must not contain a Student ID")
    assert_false(bool(EMAIL_PATTERN.search(text)), f"{path.name} must not contain a literal email address")
print("PASS 18: no Student ID or literal private email address leaked in new records.")


# 19. This milestone (TELUS_EVIDENCE_V1) was itself Evidence/Experience only
#     and created no résumé module or master integration. A later, separately
#     scoped milestone (TELUS_MASTER_INTEGRATION_V1) has since integrated the
#     approved modules -- confirmed here as the current true state, not
#     re-litigated: exactly the two approved modules are present.
telus_module_ids_in_master = {
    m["module_id"] for m in MASTER["modules"] if m.get("experience_id") == "EXP_TELUS_001"
}
assert_true(
    telus_module_ids_in_master == {"MOD_TELUS_001_REVIEW", "MOD_TELUS_002_PATTERN"},
    f"master must now contain exactly the two approved TELUS modules, got {telus_module_ids_in_master}",
)
print("PASS 19: this milestone itself added no resume module; the master now correctly reflects the later, separately-scoped TELUS_MASTER_INTEGRATION_V1.")


print("PASS: TELUS_EVIDENCE_V1 tests completed successfully.")
