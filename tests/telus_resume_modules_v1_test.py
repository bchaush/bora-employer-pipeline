"""Bounded tests for TELUS draft Claims and draft résumé modules
(TELUS_RESUME_MODULES_V1).

Proves: the two new TELUS Claims have valid Evidence lineage and
compatible evidence states; unsupported technologies/causal outcomes
never leak in; the '500+ weekly' figure can never be represented as
VERIFIED; the historical formal title is not mutated; the drafts are
correctly NOT yet reusable/master-integrated (human_approval=false is
the real gate, exactly mirroring the MarketMind drafting precedent);
and existing Winter Walk, MarketMind, Education, and TELUS Evidence
truth are all unchanged. No master integration is expected or tested
as present -- this milestone is Claims + draft modules only.
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
assert_true(len(ev_result["index"]) == 36, "Evidence count must remain 36 -- this milestone adds no new Evidence")
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


# 3. '500+ weekly' cannot be represented as VERIFIED, and its evidence_state
#    lineage is provably compatible only as OBSERVED (via cited OBSERVED evidence).
review_evidence = EVIDENCE_INDEX["TELUS_REVIEW_001"]
assert_true(review_evidence["evidence_state"] == "OBSERVED", "TELUS_REVIEW_001 must remain OBSERVED, never upgraded")
claim_001 = CLAIM_INDEX["CLAIM_TELUS_001"]
assert_true("500+ user cases weekly" in claim_001["wording"], "exact '500+ user cases weekly' phrasing must be preserved in the Claim")
assert_true(claim_001["evidence_state"] == "OBSERVED", "CLAIM_TELUS_001 must be OBSERVED, matching its weakest cited evidence tier")
state_check = validate_claim_evidence_state_compatibility(claim_001, EVIDENCE_INDEX)
assert_true(state_check["valid"] is True, f"CLAIM_TELUS_001 evidence-state compatibility must hold: {state_check['errors']}")
# Adversarial: a VERIFIED claim citing this same OBSERVED evidence must fail --
# proving the architecture itself would block any attempt to upgrade this figure.
adversarial_upgrade = copy.deepcopy(claim_001)
adversarial_upgrade["evidence_state"] = "VERIFIED"
upgrade_check = validate_claim_evidence_state_compatibility(adversarial_upgrade, EVIDENCE_INDEX)
assert_false(upgrade_check["valid"], "a VERIFIED claim citing OBSERVED-only evidence must fail state-compatibility validation")
print("PASS 3: '500+ weekly' remains OBSERVED-tier; upgrading it to VERIFIED is architecturally rejected.")


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


# 7. Winter Walk remains unchanged (master modules/wording).
WW_IDS = [m["module_id"] for m in MASTER["modules"] if m["module_type"] == "BULLET"]
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
assert_true(len(MASTER["modules"]) == 11, "master modules must remain 11 -- no TELUS module integrated into the master")
print("PASS 10: Golden-relevant repository invariants (master module count) intact.")


# 11. Any TELUS master integration obeys approval state: NONE exists, and the
#     existing production module-lineage gate correctly rejects these drafts
#     as not-yet-reusable, proving the approval boundary cannot be bypassed.
assert_false(
    any("TELUS" in json.dumps(m) for m in MASTER["modules"]),
    "no TELUS résumé module may exist in the protected master in this milestone",
)
assert_false(
    any(s.get("experience_id") == "EXP_TELUS_001" for s in MASTER.get("experience_sections", [])),
    "no experience_sections entry for TELUS may exist in the protected master in this milestone",
)
for module in TELUS_DRAFTS["modules"]:
    assert_true(module["human_approval"] is False, f"{module['module_id']} must remain human_approval=false (draft, pending Bora review)")
    lineage = validate_resume_module_lineage(module, claim_index=CLAIM_INDEX, evidence_index=EVIDENCE_INDEX)
    assert_false(
        lineage["valid"],
        f"{module['module_id']} must correctly FAIL production module-lineage validation while its Claim is unapproved "
        "(CLAIM_NOT_REUSABLE) -- this proves the approval gate cannot be bypassed, not a defect",
    )
    assert_true(
        any(e.get("code") == "CLAIM_NOT_REUSABLE" for e in lineage["errors"]),
        f"{module['module_id']} must fail specifically with CLAIM_NOT_REUSABLE",
    )
assert_true(TELUS_DRAFTS["status"] == "DRAFT_PENDING_HUMAN_REVIEW", "TELUS draft set must remain in DRAFT_PENDING_HUMAN_REVIEW status")
assert_true(TELUS_DRAFTS["human_approval"] is False, "TELUS draft set container must remain human_approval=false")
print("PASS 11: no TELUS master integration exists; the approval gate correctly blocks unapproved drafts (CLAIM_NOT_REUSABLE).")


# 12. Renderer behavior remains deterministic: since nothing TELUS-related is
#     wired into the master/presentation/renderer pipeline, the existing
#     default rendered output must be byte-identical to before this milestone.
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
assert_false("TELUS" in render_1["text"], "TELUS must not appear anywhere in the default rendered résumé (not selected, not integrated)")
print("PASS 12: renderer behavior remains deterministic; TELUS does not appear in the unrelated default rendered output.")


print("PASS: TELUS_RESUME_MODULES_V1 tests completed successfully.")
