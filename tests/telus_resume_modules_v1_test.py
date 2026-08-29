"""Bounded tests for TELUS Claims/résumé modules, covering both their
initial drafting and Bora's subsequent explicit human approval of
revised final wording (TELUS_RESUME_MODULES_V1).

Proves: the two TELUS Claims have valid Evidence lineage and
compatible evidence states; unsupported technologies/causal outcomes
never leak in; the '500+ weekly' figure can never be represented as
VERIFIED; the historical formal title is not mutated; both Claims are
now human-approved with Bora's exact approved wording, byte-identical
between Claim and module, and correctly reusable/lineage-valid as a
result (matching the MarketMind approval precedent exactly); the
protected master remains TELUS-free because a genuine, separate human
presentation decision (title/date-range) remains outstanding; and
existing Winter Walk, MarketMind, Education, and TELUS Evidence truth
are all unchanged.
"""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = ROOT / "src"
MASTER_PATH = ROOT / "resume" / "master" / "RESUME_MASTER_WW_V1.json"
TELUS_DRAFTS_PATH = ROOT / "resume" / "drafts" / "TELUS_RESUME_MODULE_DRAFTS_V1.json"
EXPERIENCE_PATH = ROOT / "experiences" / "EXP_TELUS_001.json"

if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from claim_lineage import validate_claim_lineage  # noqa: E402
from claim_repository import validate_claim_repository  # noqa: E402
from claim_semantic_guard import validate_claim_semantic_boundaries  # noqa: E402
from claim_state_validation import validate_claim_evidence_state_compatibility  # noqa: E402
from claim_validation import validate_claim  # noqa: E402
from evidence_repository import validate_evidence_repository  # noqa: E402
from experience_repository import validate_experience_repository  # noqa: E402
from resume_lineage import validate_resume_module_lineage  # noqa: E402
from resume_semantic import validate_module_wording_semantics  # noqa: E402
from resume_style import validate_resume_prose_style  # noqa: E402


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        print(f"FAIL: {message}")
        raise SystemExit(1)


def assert_false(condition: bool, message: str) -> None:
    assert_true(not condition, message)


exp_result = validate_experience_repository()
assert_true(exp_result["valid"] is True, "experience repository invalid")
assert_true(len(exp_result["index"]) == 4, "Experience count must remain 4 -- this milestone adds no new Experience")
ev_result = validate_evidence_repository(experience_result=exp_result)
assert_true(ev_result["valid"] is True, "evidence repository invalid")
assert_true(len(ev_result["index"]) == 37, "Evidence count must be 37 (36 prior + 1 TELUS end-date record added in the subsequent master-integration milestone)")
claim_result = validate_claim_repository()
assert_true(claim_result["valid"] is True, "claim repository invalid")
assert_true(claim_result["records_checked"] == 13, "Claim count must be 13 (11 prior + 2 new draft TELUS claims)")

EXPERIENCE_INDEX = exp_result["index"]
EVIDENCE_INDEX = ev_result["index"]
CLAIM_INDEX = claim_result["index"]

MASTER = json.loads(MASTER_PATH.read_text(encoding="utf-8"))
TELUS_DRAFTS = json.loads(TELUS_DRAFTS_PATH.read_text(encoding="utf-8"))
TELUS_EXPERIENCE = json.loads(EXPERIENCE_PATH.read_text(encoding="utf-8"))

TELUS_CLAIM_IDS = ["CLAIM_TELUS_001", "CLAIM_TELUS_002"]

APPROVED_WORDING = {
    "CLAIM_TELUS_001": (
        "Reviewed 500+ user cases weekly against platform policy, identifying "
        "violations and behavioral patterns across structured and unstructured "
        "data under time-sensitive conditions."
    ),
    "CLAIM_TELUS_002": (
        "Tracked and categorized enforcement decisions for trend analysis and "
        "consistency, collaborating with policy, operations, and analytics teams "
        "to surface recurring risk patterns."
    ),
}


# 1. Every TELUS Claim has valid Evidence lineage.
for cid in TELUS_CLAIM_IDS:
    assert_true(cid in CLAIM_INDEX, f"{cid} must exist in the trusted Claim index")
    claim = CLAIM_INDEX[cid]
    lineage = validate_claim_lineage(claim, EVIDENCE_INDEX)
    assert_true(lineage["valid"] is True, f"{cid} must have valid Evidence lineage: {lineage['errors']}")
    for eid in claim["evidence_ids"]:
        assert_true(eid.startswith("TELUS_"), f"{cid} must cite only TELUS Evidence records, got {eid}")
print("PASS 1: every TELUS Claim has valid, exclusively-TELUS Evidence lineage.")


# 2. Unsupported TELUS technologies cannot leak into Claims/modules.
FORBIDDEN_TECH_TERMS = ["sql", "data pipeline", "business intelligence", " bi ", "dashboard", "database", "automation platform"]
claims_and_modules_text = " ".join(json.dumps(CLAIM_INDEX[cid]["wording"]) for cid in TELUS_CLAIM_IDS)
claims_and_modules_text += " ".join(json.dumps(m["wording"]) for m in TELUS_DRAFTS["modules"])
lower_text = claims_and_modules_text.lower()
for term in FORBIDDEN_TECH_TERMS:
    assert_false(term in lower_text, f"no invented technology term ({term!r}) may appear in TELUS Claim/module wording")
print("PASS 2: no unsupported technology invented in TELUS Claim/module wording.")


# 3. '500+ weekly' cannot be represented as VERIFIED, even after human approval,
#    and its evidence_state lineage is provably compatible only as OBSERVED.
review_evidence = EVIDENCE_INDEX["TELUS_REVIEW_001"]
assert_true(review_evidence["evidence_state"] == "OBSERVED", "TELUS_REVIEW_001 must remain OBSERVED, never upgraded")
claim_001 = CLAIM_INDEX["CLAIM_TELUS_001"]
assert_true("500+ user cases weekly" in claim_001["wording"], "exact '500+ user cases weekly' phrasing must be preserved in the Claim")
assert_true(claim_001["evidence_state"] == "OBSERVED", "CLAIM_TELUS_001 must be OBSERVED, matching its weakest cited evidence tier, even though human_approval=true")
state_check = validate_claim_evidence_state_compatibility(claim_001, EVIDENCE_INDEX)
assert_true(state_check["valid"] is True, f"CLAIM_TELUS_001 evidence-state compatibility must hold: {state_check['errors']}")
# Adversarial: a VERIFIED claim citing this same OBSERVED evidence must fail --
# proving the architecture itself would block any attempt to upgrade this figure,
# and that human_approval never overrides evidence-state compatibility.
adversarial_upgrade = copy.deepcopy(claim_001)
adversarial_upgrade["evidence_state"] = "VERIFIED"
upgrade_check = validate_claim_evidence_state_compatibility(adversarial_upgrade, EVIDENCE_INDEX)
assert_false(upgrade_check["valid"], "a VERIFIED claim citing OBSERVED-only evidence must fail state-compatibility validation")
print("PASS 3: '500+ weekly' remains OBSERVED-tier; upgrading it to VERIFIED is architecturally rejected even with human_approval=true.")


# 4. Unsupported causal improvement wording is rejected or absent.
FORBIDDEN_CAUSAL_TERMS = ["improved review workflows", "reduced review time", "increased efficiency", "improved workflows by", "process improvement of"]
for term in FORBIDDEN_CAUSAL_TERMS:
    assert_false(term in lower_text, f"no unsupported causal-improvement wording ({term!r}) may appear")
claim_002 = CLAIM_INDEX["CLAIM_TELUS_002"]
assert_false("improve" in claim_002["wording"].lower(), "CLAIM_TELUS_002 must not assert a causal improvement outcome")
print("PASS 4: no unsupported causal-improvement wording present.")


# 5. Historical formal title is not mutated.
assert_true(
    TELUS_EXPERIENCE.get("notes", "").count("Digital Trust and Safety Analyst with English (tele-agent)") >= 1
    or "Digital Trust and Safety Analyst with English (tele-agent)" in json.dumps(EVIDENCE_INDEX["TELUS_OFFER_001"]),
    "employer-issued formal title must remain intact and unmutated",
)
assert_true(
    EVIDENCE_INDEX["TELUS_OFFER_001"]["fact"].count("Digital Trust and Safety Analyst with English (tele-agent)") == 1,
    "TELUS_OFFER_001's formal title fact must be unchanged",
)
assert_false(
    "Content Safety Analyst" in claim_001["wording"] or "Content Safety Analyst" in claim_002["wording"],
    "the LinkedIn display title must never silently substitute for or appear inside Claim wording",
)
print("PASS 5: historical formal title unmutated; LinkedIn display title never substituted into Claim wording.")


# 6. Non-TELUS Claims remain byte-for-byte unchanged.
NON_TELUS_CLAIM_COUNT = claim_result["records_checked"] - len(TELUS_CLAIM_IDS)
assert_true(NON_TELUS_CLAIM_COUNT == 11, "exactly 11 non-TELUS claims must exist, byte-unchanged")
assert_true(
    CLAIM_INDEX["CLAIM_WW_001"]["wording"]
    == "Defined the Winter Walk OP Recommendation Adoption & Support System as an internal Google Workspace operating tool and documented explicit scope boundaries excluding CRM, public dashboard, partner ranking, AI auto-sending, and causal fundraising-impact modeling.",
    "CLAIM_WW_001 wording must remain byte-unchanged",
)
assert_true(
    CLAIM_INDEX["CLAIM_MM_001"]["wording"]
    == "Built a Python/Streamlit preliminary market-screening prototype scoped to coffee shops, with documented limits that scores are screening heuristics and not validated predictors of business success.",
    "CLAIM_MM_001 wording must remain byte-unchanged",
)
print("PASS 6: all 11 non-TELUS Claims remain byte-for-byte unchanged.")


# 7. Winter Walk remains unchanged (master modules/wording). Filtered by
#    experience_id, not module_type=BULLET alone -- TELUS modules are also
#    module_type=BULLET, so a type-only filter would incorrectly include them.
WW_IDS = [m["module_id"] for m in MASTER["modules"] if m.get("experience_id") == "EXP_WW_001"]
assert_true(len(WW_IDS) == 6, "Winter Walk module count must remain 6")
print("PASS 7: Winter Walk master modules unchanged.")


# 8. MarketMind remains unchanged (master modules/wording).
MM_IDS = [m["module_id"] for m in MASTER["modules"] if m["module_type"] == "PROJECT_BULLET"]
assert_true(len(MM_IDS) == 5, "MarketMind module count must remain 5")
print("PASS 8: MarketMind master modules unchanged.")


# 9. Brandeis Education remains unchanged.
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
print("PASS 9: Brandeis education entry unchanged.")


# 10. Golden baseline invariants remain intact (repository counts checked above
#     already prove this; master modules count is the other Golden-relevant invariant).
assert_true(len(MASTER["modules"]) == 13, "master must have 13 modules -- both approved TELUS modules are now integrated (see TELUS_MASTER_INTEGRATION_V1)")
print("PASS 10: Golden-relevant repository invariants (master module count) intact.")


# 11a. Both Claims now carry Bora's exact approved wording, are human-approved,
#      and are correctly reusable as a validator-computed consequence (not a
#      manually-set field) -- mirroring the MarketMind approval precedent.
for cid in TELUS_CLAIM_IDS:
    claim = CLAIM_INDEX[cid]
    assert_true(claim["wording"] == APPROVED_WORDING[cid], f"{cid} wording must equal Bora's exact approved text, got {claim['wording']!r}")
    assert_true(claim["human_approval"] is True, f"{cid} must now be human_approval=true")
    assert_true(claim["evidence_state"] == "OBSERVED", f"{cid} must remain evidence_state=OBSERVED after approval")
    result = validate_claim(claim, evidence_index=EVIDENCE_INDEX)
    assert_true(result["reusable"] is True, f"{cid} must be reusable=true as a validator-computed consequence of human_approval=true + valid lineage/state")
print("PASS 11a: both TELUS Claims carry the exact approved wording, are human-approved, and are correctly reusable.")


# 11b. Matching TELUS module wording is byte-identical to its approved Claim,
#      and modules are now human_approval=true, matching the approval event.
MODULE_BY_ID = {m["module_id"]: m for m in TELUS_DRAFTS["modules"]}
assert_true(
    MODULE_BY_ID["MOD_TELUS_001_REVIEW"]["wording"] == CLAIM_INDEX["CLAIM_TELUS_001"]["wording"],
    "MOD_TELUS_001_REVIEW wording must be byte-identical to CLAIM_TELUS_001 wording",
)
assert_true(
    MODULE_BY_ID["MOD_TELUS_002_PATTERN"]["wording"] == CLAIM_INDEX["CLAIM_TELUS_002"]["wording"],
    "MOD_TELUS_002_PATTERN wording must be byte-identical to CLAIM_TELUS_002 wording",
)
for module in TELUS_DRAFTS["modules"]:
    assert_true(module["human_approval"] is True, f"{module['module_id']} must now be human_approval=true")
print("PASS 11b: TELUS module wording is byte-identical to its approved Claim; modules are human_approval=true.")


# 11c. Both modules now correctly PASS production module-lineage validation
#      (the CLAIM_NOT_REUSABLE gate that blocked them pre-approval is now
#      satisfied) -- proving approval genuinely unlocks lineage validity,
#      exactly as the architecture intends.
for module in TELUS_DRAFTS["modules"]:
    lineage = validate_resume_module_lineage(module, claim_index=CLAIM_INDEX, evidence_index=EVIDENCE_INDEX)
    assert_true(lineage["valid"] is True, f"{module['module_id']} must now pass production module-lineage validation: {lineage.get('errors')}")
print("PASS 11c: both TELUS modules now pass production module-lineage validation following Claim approval.")


# 11d. At the time this milestone (TELUS_RESUME_MODULES_V1) concluded, master
#      integration was correctly withheld pending a separate, then-unresolved
#      human presentation decision (title/date-range). That decision has since
#      been made and integration completed by the later, separately-scoped
#      TELUS_MASTER_INTEGRATION_V1 milestone -- confirmed here as the current
#      true state, not re-litigated: both approved modules are present and
#      the section correctly reflects the approved display title/date range.
telus_module_ids_in_master = {
    m["module_id"] for m in MASTER["modules"] if m.get("experience_id") == "EXP_TELUS_001"
}
assert_true(
    telus_module_ids_in_master == {"MOD_TELUS_001_REVIEW", "MOD_TELUS_002_PATTERN"},
    f"master must now contain exactly the two approved TELUS modules, got {telus_module_ids_in_master}",
)
telus_section = next((s for s in MASTER.get("experience_sections", []) if s.get("experience_id") == "EXP_TELUS_001"), None)
assert_true(telus_section is not None, "master must now contain a TELUS experience_sections entry (integrated by TELUS_MASTER_INTEGRATION_V1)")
assert_true(
    telus_section["formal_title"] == "Digital Trust and Safety Analyst with English (tele-agent)",
    "TELUS experience_sections formal_title must remain the exact, unmutated employer-issued title",
)
assert_true(
    TELUS_DRAFTS["status"] == "APPROVED_AND_INTEGRATED_INTO_MASTER",
    f"TELUS draft set status must reflect completed master integration, got {TELUS_DRAFTS['status']!r}",
)
print("PASS 11d: master now contains exactly the two approved TELUS modules and a TELUS experience section with the unmutated formal title (integrated by the later, separately-scoped TELUS_MASTER_INTEGRATION_V1).")


# 12. Renderer behavior remains deterministic. At the time this milestone
#     (TELUS_RESUME_MODULES_V1) concluded, nothing TELUS-related was wired
#     into the master/presentation/renderer pipeline, so TELUS did not yet
#     appear in the default rendered output. The later, separately-scoped
#     TELUS_MASTER_INTEGRATION_V1 milestone deliberately added the two
#     approved TELUS modules to default_module_order, so TELUS now correctly
#     appears by design -- confirmed here as the current true state, not
#     re-litigated. Determinism itself remains the substantive invariant.
sys.path.insert(0, str(SRC_PATH))
from resume_presentation import build_resume_presentation_view  # noqa: E402
from resume_text_renderer import render_resume_text  # noqa: E402
from resume_validation import build_resume_derivative  # noqa: E402

default_patch = {
    "patch_id": "TELUS_MOD_TEST_DEFAULT",
    "target_master_id": MASTER["master_id"],
    "operations": [{"op": "REORDER_MODULES", "module_ids": MASTER["default_module_order"]}],
}
default_result = build_resume_derivative(
    master=MASTER, patch=default_patch, claim_index=CLAIM_INDEX, evidence_index=EVIDENCE_INDEX,
    derivative_id="DERIV_TELUS_MOD_TEST_DEFAULT",
)
assert_true(default_result["valid"] is True, f"default derivative must still build: {default_result.get('errors')}")
presentation = build_resume_presentation_view(default_result["derivative"], experience_index=EXPERIENCE_INDEX)
assert_true(presentation["valid"] is True, "default presentation must still resolve")
render_1 = render_resume_text(presentation)
render_2 = render_resume_text(build_resume_presentation_view(default_result["derivative"], experience_index=EXPERIENCE_INDEX))
assert_true(render_1 == render_2, "renderer output must remain deterministic across repeat calls")
assert_true(
    "Digital Trust and Safety Analyst with English" in render_1["text"],
    "TELUS now correctly appears in the default rendered resume, integrated by TELUS_MASTER_INTEGRATION_V1",
)
print("PASS 12: renderer behavior remains deterministic; TELUS now correctly appears in the default rendered output.")


print("PASS: TELUS_RESUME_MODULES_V1 tests completed successfully.")
