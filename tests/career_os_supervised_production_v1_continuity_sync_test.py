import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

DOCTRINE_MERGE_SHA = "01602bf6ba4329b37d8b0365a77f53f953dce597"
DOCTRINE_HEAD = "5cb49e0eba7b86773e20738f3e250252c389b3fd"
DOCTRINE_FINGERPRINT = "bc073a55b8b14aab954f19a0d220e5eb9184f09607761bf35866b6883590a253"

SLICE1 = "SUPERVISED_PRODUCTION_V1_SLICE_1_GMAIL_TO_SHEET"
SLICE1_HEAD = "18883e12dc307d22b2928a3c3ece4da3d7bb8fd8"
SLICE1_MERGE = "c236ac03c3afe3c8f6bfb7c53f72b663374df468"
SLICE1_FINGERPRINT = "1620050e603b16fd3a188c8c1f6b4e47b55f5801ec447e1666251a45280f26e6"
SLICE2 = "SUPERVISED_PRODUCTION_V1_SLICE_2_GATES_MATCH_TRUTH_TO_SHEET"

ps = json.loads((ROOT / "project_state.json").read_text(encoding="utf-8"))
cp = json.loads((ROOT / "CURRENT_EXECUTION_CHECKPOINT.json").read_text(encoding="utf-8"))
old_contract = json.loads((ROOT / "milestone_contracts/governance/career-os-supervised-production-v1-continuity-sync.json").read_text(encoding="utf-8"))
sync_contract = json.loads((ROOT / "milestone_contracts/governance/career-os-supervised-production-v1-slice1-completion-sync.json").read_text(encoding="utf-8"))
agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
milestone = (ROOT / "CURRENT_MILESTONE.md").read_text(encoding="utf-8")
state = (ROOT / "CURRENT_STATE.md").read_text(encoding="utf-8")
changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")

# Active production doctrine remains intact.
assert ps["current_phase"].startswith("SUPERVISED_PRODUCTION_V1")
assert cp["phase_id"] == "SUPERVISED_PRODUCTION_V1"
assert cp["phase_mode"] == "SUPERVISED_PRODUCTION_GOVERNANCE"
assert cp["human_acceptance_status"] == "BORA_ACCEPTED"
assert cp["implementation_authorized"] is False
assert "docs/SUPERVISED_PRODUCTION_V1.md" in cp["continuity_rule"]
assert "docs/SUPERVISED_PRODUCTION_V1.md" in agents

# The original doctrine continuity evidence remains machine-readable historical truth.
sp = cp["supervised_production_v1"]
assert sp["canonical_merge_sha"] == DOCTRINE_MERGE_SHA
assert sp["reviewed_head_sha"] == DOCTRINE_HEAD
assert sp["reviewed_candidate_fingerprint"] == DOCTRINE_FINGERPRINT
assert sp["cursor_review_exception"]["fingerprint"] == DOCTRINE_FINGERPRINT
assert old_contract["milestone_id"] == "SUPERVISED_PRODUCTION_V1_CONTINUITY_SYNC"

# Slice 1 completion is current canonical state.
assert cp["checkpoint_id"] == "CAREER_OS_CHECKPOINT_2026-09-23_SUPERVISED_PRODUCTION_V1_SLICE_1_COMPLETION_SYNC"
assert cp["canonical_basis_sha"] == SLICE1_MERGE
assert cp["recorded_at"] == "2026-09-23"
s1 = cp["slice_1_completion"]
assert s1["milestone_id"] == SLICE1
assert s1["operator_status"] == "COMPLETED_BY_OPERATOR"
assert s1["human_acceptance_status"] == "BORA_ACCEPTED"
assert s1["reviewed_head_sha"] == SLICE1_HEAD
assert s1["canonical_merge_sha"] == SLICE1_MERGE
assert s1["reviewed_candidate_fingerprint"] == SLICE1_FINGERPRINT
assert s1["local_assurance"] == "102/102_PASS_ALL_PHASES"
assert s1["golden"] == "15/15_PASS"
assert s1["github_assurance"] == "RUN_151_SUCCESS"
assert s1["independent_review"] == "SAFE"
assert s1["implementation_authority_status"] == "EXHAUSTED_BY_COMPLETION"
assert SLICE1 in ps["current_phase"]
assert "SLICE_1_COMPLETED_BY_OPERATOR_BORA_ACCEPTED" in ps["current_phase"]

# The next seam is selected only, never silently authorized.
next_seam = cp["next_candidate_seam"]
assert next_seam["milestone_id"] == SLICE2
assert next_seam["selection_status"] == "SELECTED_NOT_AUTHORIZED"
assert next_seam["implementation_authorized"] is False
assert "cheap gates + Employer Truth + Match Truth" in next_seam["scope_summary"]
assert "separate explicit Bora authorization" in " ".join(next_seam["required_before_implementation"])
assert SLICE2 in ps["current_phase"]
assert "SELECTED_NOT_AUTHORIZED" in ps["current_phase"]
assert SLICE2 in ps["next_authorized_action"]
assert "SELECTED_NOT_AUTHORIZED" in ps["next_authorized_action"]
assert "Global implementation_authorized remains false" in ps["next_authorized_action"]
assert "Do not implement Slice 2 before that authorization" in cp["exact_next_allowed_action"]

# Human-readable recovery pointers agree with the machine-readable routing.
for text in (milestone, state):
    assert SLICE1 in text
    assert "COMPLETED_BY_OPERATOR / BORA_ACCEPTED (2026-09-23)" in text
    assert SLICE2 in text
    assert "SELECTED_NOT_AUTHORIZED" in text

assert "2026-09-23 — SUPERVISED_PRODUCTION_V1 Slice 1 completion continuity sync" in changelog
assert SLICE1_FINGERPRINT in changelog
assert "GitHub Assurance run #151 SUCCESS" in changelog

# The completion sync itself is governance-only and fail-closed.
assert sync_contract["milestone_id"] == "SUPERVISED_PRODUCTION_V1_SLICE_1_COMPLETION_SYNC"
assert sync_contract["kind"] == "GOVERNANCE_SYNC"
assert sync_contract["baseline_sha"] == SLICE1_MERGE
assert "src/**" in sync_contract["forbidden_paths"]
assert "schemas/**" in sync_contract["forbidden_paths"]
assert "docs/**" in sync_contract["forbidden_paths"]
assert "project_state.json" in sync_contract["allowed_paths"]
assert "CURRENT_EXECUTION_CHECKPOINT.json" in sync_contract["allowed_paths"]
assert "NEXT_RUNTIME_SEAM_REQUIRES_SEPARATE_EXPLICIT_BORA_AUTHORIZATION" in sync_contract["human_approval_requirements"]

# Historical accepted roadmap state remains present.
assert "recommendation_b_completion" in cp
assert cp["recommendation_b_completion"]["human_acceptance_status"] == "BORA_ACCEPTED"
assert "phase_h_acceptance" in cp
assert cp["phase_h_acceptance"]["human_acceptance_status"] == "BORA_ACCEPTED"

print("PASS: supervised production v1 Slice 1 completion continuity sync verified.")
