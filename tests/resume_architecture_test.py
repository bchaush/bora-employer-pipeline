import copy
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = ROOT / "src"
FIXTURES = ROOT / "fixtures" / "resume_architecture"

if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from claim_repository import validate_claim_repository  # noqa: E402
from evidence_repository import validate_evidence_repository  # noqa: E402
from experience_repository import validate_experience_repository  # noqa: E402
from resume_diff import compute_resume_diff  # noqa: E402
from resume_lineage import validate_resume_module_lineage  # noqa: E402
from resume_patch_apply import (  # noqa: E402
    apply_resume_patch,
    reject_forbidden_patch_extension,
    validate_immutable_fields_preserved,
)
from resume_style import validate_resume_prose_style  # noqa: E402
from resume_validation import (  # noqa: E402
    approve_derivative_for_export,
    build_resume_derivative,
    complete_semantic_review,
    master_unchanged_after_derivative_build,
    validate_derivative_eligibility,
    validate_master_module_ids_unique,
    validate_resume_master,
    validate_resume_module,
    validate_resume_patch,
)


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        print(f"FAIL: {message}")
        raise SystemExit(1)


def assert_false(condition: bool, message: str) -> None:
    assert_true(not condition, message)


def has_code(items: list, code: str) -> bool:
    return any(item.get("code") == code for item in items)


def load_trusted_indexes() -> tuple[dict, dict]:
    experience_result = validate_experience_repository()
    assert_true(experience_result["valid"] is True, "experience repository invalid")
    evidence_result = validate_evidence_repository(
        experience_result=experience_result,
    )
    assert_true(evidence_result["valid"] is True, "evidence repository invalid")
    claim_result = validate_claim_repository()
    assert_true(claim_result["valid"] is True, "claim repository invalid")
    return evidence_result["index"], claim_result["index"]


EVIDENCE_INDEX, CLAIM_INDEX = load_trusted_indexes()
MASTER = json.loads((FIXTURES / "synthetic_master.json").read_text(encoding="utf-8"))


# A. valid résumé module with approved claim → PASS
module_a = MASTER["modules"][0]
result_a = validate_resume_module(
    module_a, claim_index=CLAIM_INDEX, evidence_index=EVIDENCE_INDEX
)
assert_true(result_a["valid"] is True, "A: valid module should pass")
print("PASS A: valid module with approved claim.")


# B. module without Claim_ID → FAIL
module_b = copy.deepcopy(module_a)
module_b["module_id"] = "MOD_NO_CLAIMS"
module_b["claim_ids"] = []
result_b = validate_resume_module_lineage(
    module_b, claim_index=CLAIM_INDEX, evidence_index=EVIDENCE_INDEX
)
assert_false(result_b["valid"], "B: empty claim_ids should fail")
assert_true(has_code(result_b["errors"], "MISSING_CLAIM_LINEAGE"), "B: missing lineage code")
print("PASS B: module without Claim_ID fails.")


# C. module referencing unapproved/non-reusable claim → FAIL
module_c = copy.deepcopy(module_a)
module_c["module_id"] = "MOD_BAD_CLAIM"
module_c["claim_ids"] = ["CLAIM_UNAPPROVED_SYNTH"]
bad_claim = {
    "claim_id": "CLAIM_UNAPPROVED_SYNTH",
    "wording": "Synthetic unapproved claim for architecture test.",
    "evidence_ids": ["WW_ARCH_001"],
    "evidence_state": "SUPPORTED",
    "allowed_contexts": ["resume"],
    "forbidden_contexts": [],
    "human_approval": False,
    "date": "2026-08-28",
    "version": "1",
}
claim_index_c = dict(CLAIM_INDEX)
claim_index_c["CLAIM_UNAPPROVED_SYNTH"] = bad_claim
result_c = validate_resume_module_lineage(
    module_c, claim_index=claim_index_c, evidence_index=EVIDENCE_INDEX
)
assert_false(result_c["valid"], "C: unapproved claim should fail")
assert_true(has_code(result_c["errors"], "CLAIM_NOT_REUSABLE"), "C: non-reusable code")
print("PASS C: unapproved/non-reusable claim fails.")


# D. missing Evidence lineage → FAIL
module_d = copy.deepcopy(module_a)
module_d["module_id"] = "MOD_BAD_EVIDENCE"
module_d["evidence_ids"] = ["EVIDENCE_DOES_NOT_EXIST"]
result_d = validate_resume_module_lineage(
    module_d, claim_index=CLAIM_INDEX, evidence_index=EVIDENCE_INDEX
)
assert_false(result_d["valid"], "D: missing evidence should fail")
assert_true(
    has_code(result_d["errors"], "MISSING_EVIDENCE_ID")
    or has_code(result_d["errors"], "EVIDENCE_LINEAGE_MISMATCH"),
    "D: evidence lineage error",
)
print("PASS D: missing evidence lineage fails.")


# E. title-changing patch → FAIL
patch_e = {
    "patch_id": "PATCH_TITLE_CHANGE",
    "target_master_id": MASTER["master_id"],
    "operations": [
        {
            "op": "INCLUDE_MODULE",
            "module_id": "MOD_BULLET_WW_SCOPE",
            "formal_title": "Chief Executive Officer",
        }
    ],
}
forbidden_e = reject_forbidden_patch_extension(patch_e)
assert_false(forbidden_e["valid"], "E: forbidden title field should fail")
assert_true(has_code(forbidden_e["errors"], "FORBIDDEN_PATCH_FIELD"), "E: forbidden field")
patch_schema_e = validate_resume_patch(patch_e, master=MASTER)
assert_false(patch_schema_e["valid"], "E: schema should reject extra patch fields")
print("PASS E: title-changing patch fails.")


# F. employer-changing patch → FAIL
patch_f = {
    "patch_id": "PATCH_EMPLOYER_CHANGE",
    "target_master_id": MASTER["master_id"],
    "operations": [
        {
            "op": "EXCLUDE_MODULE",
            "module_id": "MOD_OPTIONAL_ARCHIVE",
            "organization": "Other Org",
        }
    ],
}
forbidden_f = reject_forbidden_patch_extension(patch_f)
assert_false(forbidden_f["valid"], "F: forbidden employer field should fail")
derivative_mutated = apply_resume_patch(MASTER, {
    "patch_id": "PATCH_NOOP",
    "target_master_id": MASTER["master_id"],
    "operations": [{"op": "EXCLUDE_MODULE", "module_id": "MOD_OPTIONAL_ARCHIVE"}],
})["derivative"]
derivative_mutated["experience_sections"][0]["organization"] = "Changed Org"
immutable_f = validate_immutable_fields_preserved(MASTER, derivative_mutated)
assert_false(immutable_f["valid"], "F: mutated employer should fail immutable check")
assert_true(
    has_code(immutable_f["errors"], "IMMUTABLE_EXPERIENCE_FIELD_ALTERED"),
    "F: immutable employer",
)
print("PASS F: employer-changing patch fails.")


# G. unsupported metric/tool addition → FAIL
patch_g = {
    "patch_id": "PATCH_ADD_TOOL",
    "target_master_id": MASTER["master_id"],
    "operations": [
        {
            "op": "REORDER_SKILLS",
            "skills": ["ServiceNow", "Google Workspace"],
            "add_tool": "ServiceNow",
        }
    ],
}
forbidden_g = reject_forbidden_patch_extension(patch_g)
assert_false(forbidden_g["valid"], "G: add_tool should fail")
assert_true(has_code(forbidden_g["errors"], "FORBIDDEN_PATCH_FIELD"), "G: add_tool field")
patch_metric_g = {
    "patch_id": "PATCH_ADD_METRIC",
    "target_master_id": MASTER["master_id"],
    "operations": [{"op": "REORDER_MODULES", "module_ids": ["MOD_BULLET_WW_PROC"], "add_metric": "40%"}],
}
forbidden_g2 = reject_forbidden_patch_extension(patch_metric_g)
assert_false(forbidden_g2["valid"], "G: add_metric should fail")
print("PASS G: unsupported metric/tool patch extension fails.")


# H. legal include/exclude/reorder patch → PASS
patch_h = {
    "patch_id": "PATCH_LEGAL_001",
    "target_master_id": MASTER["master_id"],
    "job_id": "JOB_FIXTURE_BSA_001",
    "operations": [
        {"op": "EXCLUDE_MODULE", "module_id": "MOD_OPTIONAL_ARCHIVE"},
        {
            "op": "REORDER_MODULES",
            "module_ids": ["MOD_BULLET_WW_PROC", "MOD_BULLET_WW_SCOPE"],
        },
        {
            "op": "REORDER_SKILLS",
            "skills": ["process mapping", "Google Workspace", "requirements definition"],
        },
    ],
}
master_before = copy.deepcopy(MASTER)
result_h = build_resume_derivative(
    master=MASTER,
    patch=patch_h,
    claim_index=CLAIM_INDEX,
    evidence_index=EVIDENCE_INDEX,
    derivative_id="DERIV_LEGAL_001",
)
assert_true(result_h["valid"] is True, "H: legal patch should pass")
assert_true(
    master_unchanged_after_derivative_build(master_before, MASTER),
    "H: master unchanged during build",
)
print("PASS H: legal include/exclude/reorder patch passes.")


# I. derivative does not mutate master → PASS
assert_true(MASTER == master_before, "I: master deep equality preserved")
applied = apply_resume_patch(MASTER, patch_h)
assert_true(applied["valid"] is True, "I: apply patch valid")
assert_true(MASTER == master_before, "I: master still unchanged after apply_resume_patch")
print("PASS I: derivative workflow does not mutate master.")


# J. diff accurately reports derivative changes → PASS
derivative_state = applied["derivative"]
diff = compute_resume_diff(MASTER, derivative_state)
assert_true(
    any(entry.get("change_type") == "REORDERED" for entry in diff),
    "J: diff should report reorder",
)
assert_true(
    any(
        entry.get("change_type") == "REMOVED"
        and entry.get("target") == "MOD_OPTIONAL_ARCHIVE"
        for entry in diff
    ),
    "J: diff should report excluded module",
)
built_diff = result_h["derivative"]["diff"]
assert_true(
    any(entry.get("change_type") == "REORDERED" for entry in built_diff),
    "J: built derivative diff includes reorder",
)
print("PASS J: diff reports derivative changes.")


# K. em-dash style rule → style failure (distinct from provenance)
style_k = validate_resume_prose_style(
    "Built workflow controls — with human approval.",
    context="MOD_STYLE_K",
)
assert_false(style_k["valid"], "K: em dash should fail style")
assert_true(has_code(style_k["warnings"], "RESUME_STYLE_EM_DASH"), "K: em dash code")
module_k = copy.deepcopy(module_a)
module_k["module_id"] = "MOD_EM_DASH"
module_k["wording"] = "Built workflow controls — with human approval."
result_k = validate_resume_module(
    module_k, claim_index=CLAIM_INDEX, evidence_index=EVIDENCE_INDEX
)
assert_true(result_k["factual_valid"] is True, "K: factual lineage still valid")
assert_false(result_k["style_valid"], "K: style should fail")
assert_false(has_code(result_k["errors"], "RESUME_STYLE_EM_DASH"), "K: style not factual error")
assert_true(has_code(result_k["style_warnings"], "RESUME_STYLE_EM_DASH"), "K: style warning")
print("PASS K: em-dash style rule catches prose separately from provenance.")


# L. generic AI filler → style failure (distinct from provenance)
style_l = validate_resume_prose_style(
    "Spearheaded seamless innovative solutions for stakeholders.",
    context="MOD_STYLE_L",
)
assert_false(style_l["valid"], "L: AI filler should fail style")
assert_true(has_code(style_l["warnings"], "RESUME_STYLE_AI_FILLER"), "L: filler code")
print("PASS L: generic AI filler rule catches prose.")


# Human review gate: export blocked until full eligibility + explicit approval
assert_true(result_h["derivative"]["export_allowed"] is False, "export blocked by default")
assert_true(
    result_h["derivative"]["review_status"] == "HUMAN_REVIEW_REQUIRED",
    "review required by default",
)
approved = approve_derivative_for_export(
    derivative=result_h["derivative"],
    master=MASTER,
    claim_index=CLAIM_INDEX,
    evidence_index=EVIDENCE_INDEX,
    human_approval=True,
)
assert_true(approved["valid"] is True, "approval path valid for built derivative")
assert_true(approved["derivative"]["export_allowed"] is True, "export allowed after approval")
print("PASS: human review gate blocks export until approval.")


# F1 trust boundary: fabricated derivative cannot be approved
fabricated_claim = copy.deepcopy(result_h["derivative"])
fabricated_claim["modules"][0]["claim_ids"] = ["CLAIM_DOES_NOT_EXIST"]
fabricated_claim["validation_digest"] = result_h["derivative"]["validation_digest"]
fabricated_approval = approve_derivative_for_export(
    derivative=fabricated_claim,
    master=MASTER,
    claim_index=CLAIM_INDEX,
    evidence_index=EVIDENCE_INDEX,
    human_approval=True,
)
assert_false(fabricated_approval["valid"], "F1: fabricated claim should fail approval")
assert_true(
    has_code(fabricated_approval["errors"], "DERIVATIVE_MUTATED_AFTER_VALIDATION")
    or has_code(fabricated_approval["errors"], "MISSING_CLAIM_ID"),
    "F1: fabricated derivative rejected",
)
print("PASS F1: fabricated derivative with nonexistent Claim cannot be approved.")


fabricated_raw = copy.deepcopy(result_h["derivative"])
fabricated_raw["modules"][0]["wording"] = (
    "Spearheaded seamless enterprise SaaS platform ownership."
)
fabricated_raw["validation_digest"] = result_h["derivative"]["validation_digest"]
fabricated_raw_approval = approve_derivative_for_export(
    derivative=fabricated_raw,
    master=MASTER,
    claim_index=CLAIM_INDEX,
    evidence_index=EVIDENCE_INDEX,
    human_approval=True,
)
assert_false(fabricated_raw_approval["valid"], "F1: unsupported prose should fail")
print("PASS F1: fabricated derivative with unsupported prose cannot be approved.")


mutated_derivative = copy.deepcopy(result_h["derivative"])
mutated_derivative["modules"][0]["wording"] = "Changed wording after validation."
mutated_approval = approve_derivative_for_export(
    derivative=mutated_derivative,
    master=MASTER,
    claim_index=CLAIM_INDEX,
    evidence_index=EVIDENCE_INDEX,
    human_approval=True,
)
assert_false(mutated_approval["valid"], "F1: mutation should fail approval")
assert_true(
    has_code(mutated_approval["errors"], "DERIVATIVE_MUTATED_AFTER_VALIDATION"),
    "F1: mutation digest mismatch",
)
print("PASS F1: derivative mutated after validation cannot be approved.")


no_digest = copy.deepcopy(result_h["derivative"])
del no_digest["validation_digest"]
no_digest_approval = approve_derivative_for_export(
    derivative=no_digest,
    master=MASTER,
    claim_index=CLAIM_INDEX,
    evidence_index=EVIDENCE_INDEX,
    human_approval=True,
)
assert_false(no_digest_approval["valid"], "F1: missing digest should fail")
assert_true(
    has_code(no_digest_approval["errors"], "DERIVATIVE_VALIDATION_DIGEST_MISSING"),
    "F1: digest required",
)
print("PASS F1: derivative without validation digest cannot be approved.")


# F2 semantics: unsupported terminology substitution fails
patch_bpmn = {
    "patch_id": "PATCH_BPMN_TRAP",
    "target_master_id": MASTER["master_id"],
    "operations": [
        {
            "op": "TERMINOLOGY_SUBSTITUTE",
            "module_id": "MOD_BULLET_WW_PROC",
            "from_term": "operating process",
            "to_term": "BPMN enterprise process modeling process",
        }
    ],
}
result_bpmn = build_resume_derivative(
    master=MASTER,
    patch=patch_bpmn,
    claim_index=CLAIM_INDEX,
    evidence_index=EVIDENCE_INDEX,
    derivative_id="DERIV_BPMN_TRAP",
)
assert_false(result_bpmn["valid"], "F2: BPMN substitution should fail")
assert_true(
    has_code(result_bpmn["errors"], "RESUME_FORBIDDEN_CONTEXT_LEAKAGE")
    or has_code(result_bpmn["errors"], "RESUME_WORDING_SEMANTIC_VIOLATION"),
    "F2: BPMN blocked",
)
print("PASS F2: BPMN substitution against CLAIM_WW_006 fails.")


patch_lean = {
    "patch_id": "PATCH_LEAN_TRAP",
    "target_master_id": MASTER["master_id"],
    "operations": [
        {
            "op": "TERMINOLOGY_SUBSTITUTE",
            "module_id": "MOD_BULLET_WW_PROC",
            "from_term": "structured operating process",
            "to_term": "Lean Six Sigma transformation process",
        }
    ],
}
result_lean = build_resume_derivative(
    master=MASTER,
    patch=patch_lean,
    claim_index=CLAIM_INDEX,
    evidence_index=EVIDENCE_INDEX,
    derivative_id="DERIV_LEAN_TRAP",
)
assert_false(result_lean["valid"], "F2: Lean/Six Sigma substitution should fail")
print("PASS F2: Lean/Six Sigma substitution fails.")


patch_seniority = {
    "patch_id": "PATCH_SENIORITY_TRAP",
    "target_master_id": MASTER["master_id"],
    "operations": [
        {
            "op": "TERMINOLOGY_SUBSTITUTE",
            "module_id": "MOD_BULLET_WW_PROC",
            "from_term": "human approval",
            "to_term": "organization-wide transformation leadership",
        }
    ],
}
result_seniority = build_resume_derivative(
    master=MASTER,
    patch=patch_seniority,
    claim_index=CLAIM_INDEX,
    evidence_index=EVIDENCE_INDEX,
    derivative_id="DERIV_SENIORITY_TRAP",
)
assert_false(result_seniority["valid"], "F2: seniority expansion should fail")
print("PASS F2: unsupported scope/seniority expansion fails.")


patch_benign = {
    "patch_id": "PATCH_BENIGN_TERM",
    "target_master_id": MASTER["master_id"],
    "operations": [
        {
            "op": "TERMINOLOGY_SUBSTITUTE",
            "module_id": "MOD_BULLET_WW_PROC",
            "from_term": "manual OP-support workflow",
            "to_term": "documented manual OP-support workflow",
        }
    ],
}
result_benign = build_resume_derivative(
    master=MASTER,
    patch=patch_benign,
    claim_index=CLAIM_INDEX,
    evidence_index=EVIDENCE_INDEX,
    derivative_id="DERIV_BENIGN_TERM",
)
assert_true(result_benign["valid"], "F2: benign substitution should build")
assert_true(
    result_benign["derivative"]["review_status"] == "NEEDS_SEMANTIC_REVIEW",
    "F2: benign terminology requires semantic review",
)
semantic_blocked = approve_derivative_for_export(
    derivative=result_benign["derivative"],
    master=MASTER,
    claim_index=CLAIM_INDEX,
    evidence_index=EVIDENCE_INDEX,
    human_approval=True,
)
assert_false(semantic_blocked["valid"], "F2: unresolved semantic review blocks export")
assert_true(
    has_code(semantic_blocked["errors"], "DERIVATIVE_NOT_READY_FOR_EXPORT_APPROVAL")
    or has_code(semantic_blocked["errors"], "SEMANTIC_REVIEW_UNRESOLVED"),
    "F2: semantic review gate",
)
cleared = complete_semantic_review(
    derivative=result_benign["derivative"],
    master=MASTER,
    claim_index=CLAIM_INDEX,
    evidence_index=EVIDENCE_INDEX,
)
assert_true(cleared["valid"], "F2: semantic review can be cleared")
approved_benign = approve_derivative_for_export(
    derivative=cleared["derivative"],
    master=MASTER,
    claim_index=CLAIM_INDEX,
    evidence_index=EVIDENCE_INDEX,
    human_approval=True,
)
assert_true(approved_benign["valid"], "F2: cleared derivative can export")
print("PASS F2: benign terminology substitution is review-gated; unsafe substitutions fail.")


# F3 immutability: education and immutable_snapshot
master_immutable = copy.deepcopy(MASTER)
master_immutable["education"] = [
    {
        "education_id": "EDU_SYNTH_001",
        "school_name": "Synthetic State University",
        "degree_name": "B.S. Synthetic Studies",
        "date_range": "2020 – 2024",
        "location": "Synthetic City",
    }
]
master_immutable["modules"][0]["immutable_snapshot"] = {
    "organization": "Winter Walk",
    "formal_title": "SYNTHETIC_FIXTURE_ROLE",
}
deriv_immutable = build_resume_derivative(
    master=master_immutable,
    patch=patch_h,
    claim_index=CLAIM_INDEX,
    evidence_index=EVIDENCE_INDEX,
    derivative_id="DERIV_IMMUTABLE_BASE",
)
assert_true(deriv_immutable["valid"], "F3: immutable base derivative builds")

degree_mutated = copy.deepcopy(deriv_immutable["derivative"])
degree_mutated["education"][0]["degree_name"] = "Ph.D. Invented Studies"
immutable_degree = validate_immutable_fields_preserved(
    master_immutable, degree_mutated
)
assert_false(immutable_degree["valid"], "F3: degree mutation should fail")
assert_true(
    has_code(immutable_degree["errors"], "IMMUTABLE_EDUCATION_FIELD_ALTERED"),
    "F3: degree name",
)
print("PASS F3: degree name mutation fails.")

school_mutated = copy.deepcopy(deriv_immutable["derivative"])
school_mutated["education"][0]["school_name"] = "Other University"
immutable_school = validate_immutable_fields_preserved(
    master_immutable, school_mutated
)
assert_false(immutable_school["valid"], "F3: school mutation should fail")
print("PASS F3: school name mutation fails.")

snapshot_title_mutated = copy.deepcopy(deriv_immutable["derivative"])
snapshot_title_mutated["modules"][0]["immutable_snapshot"]["formal_title"] = "CEO"
immutable_snapshot = validate_immutable_fields_preserved(
    master_immutable, snapshot_title_mutated
)
assert_false(immutable_snapshot["valid"], "F3: snapshot title mutation should fail")
assert_true(
    has_code(immutable_snapshot["errors"], "IMMUTABLE_MODULE_SNAPSHOT_ALTERED"),
    "F3: snapshot title",
)
print("PASS F3: immutable snapshot title mutation fails.")

snapshot_employer_mutated = copy.deepcopy(deriv_immutable["derivative"])
snapshot_employer_mutated["modules"][0]["immutable_snapshot"]["organization"] = "Other Org"
immutable_employer = validate_immutable_fields_preserved(
    master_immutable, snapshot_employer_mutated
)
assert_false(immutable_employer["valid"], "F3: snapshot employer mutation should fail")
print("PASS F3: immutable snapshot employer mutation fails.")

untouched_eligibility = validate_derivative_eligibility(
    deriv_immutable["derivative"],
    master=master_immutable,
    claim_index=CLAIM_INDEX,
    evidence_index=EVIDENCE_INDEX,
)
assert_true(untouched_eligibility["valid"], "F3: untouched derivative passes")
print("PASS F3: untouched derivative passes immutability checks.")


# F4 unknown wording target fails
patch_unknown_variant = {
    "patch_id": "PATCH_UNKNOWN_VARIANT",
    "target_master_id": MASTER["master_id"],
    "operations": [
        {
            "op": "SELECT_WORDING_VARIANT",
            "module_id": "MOD_DOES_NOT_EXIST",
            "variant_index": 0,
        }
    ],
}
applied_unknown_variant = apply_resume_patch(MASTER, patch_unknown_variant)
assert_false(applied_unknown_variant["valid"], "F4: unknown variant target should fail")
assert_true(
    has_code(applied_unknown_variant["errors"], "UNKNOWN_MODULE_ID"),
    "F4: unknown variant module",
)
patch_unknown_term = {
    "patch_id": "PATCH_UNKNOWN_TERM",
    "target_master_id": MASTER["master_id"],
    "operations": [
        {
            "op": "TERMINOLOGY_SUBSTITUTE",
            "module_id": "MOD_DOES_NOT_EXIST",
            "from_term": "workflow",
            "to_term": "process",
        }
    ],
}
applied_unknown_term = apply_resume_patch(MASTER, patch_unknown_term)
assert_false(applied_unknown_term["valid"], "F4: unknown terminology target should fail")
assert_true(
    has_code(applied_unknown_term["errors"], "UNKNOWN_MODULE_ID"),
    "F4: unknown terminology module",
)
print("PASS F4: unknown wording targets fail explicitly.")


# F5 duplicate module IDs fail closed
master_duplicate = copy.deepcopy(MASTER)
master_duplicate["modules"].append(copy.deepcopy(MASTER["modules"][0]))
duplicate_check = validate_master_module_ids_unique(master_duplicate)
assert_false(duplicate_check["valid"], "F5: duplicate module_id should fail")
assert_true(has_code(duplicate_check["errors"], "DUPLICATE_MODULE_ID"), "F5: duplicate code")
master_duplicate_validation = validate_resume_master(
    master_duplicate,
    claim_index=CLAIM_INDEX,
    evidence_index=EVIDENCE_INDEX,
)
assert_false(master_duplicate_validation["valid"], "F5: master with duplicates should fail")
print("PASS F5: duplicate module IDs fail closed.")


print("PASS: resume architecture tests A–L and audit remediations complete.")
