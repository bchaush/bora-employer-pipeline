import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

DOCTRINE_MERGE_SHA = "01602bf6ba4329b37d8b0365a77f53f953dce597"
DOCTRINE_HEAD = "5cb49e0eba7b86773e20738f3e250252c389b3fd"
DOCTRINE_FINGERPRINT = "bc073a55b8b14aab954f19a0d220e5eb9184f09607761bf35866b6883590a253"

SLICE1 = "SUPERVISED_PRODUCTION_V1_SLICE_1_GMAIL_TO_SHEET"
SLICE1_MERGE = "c236ac03c3afe3c8f6bfb7c53f72b663374df468"

SLICE2 = "SUPERVISED_PRODUCTION_V1_SLICE_2_GATES_MATCH_TRUTH_TO_SHEET"
SLICE2_HEAD = "64483de7b0588a0822ca0e4dc219867c8c054bbb"
SLICE2_MERGE = "f70ef63386e9eb5134480b4996ad493720abc02c"
SLICE2_FINGERPRINT = "f425894766c2423f00148c184dbbd4e4f40a9300831ac2d03d813d8cd8add643"
SLICE2_TREE = "50410d136d352373fb85d39c457805a62118cf50"

ps = json.loads((ROOT / "project_state.json").read_text(encoding="utf-8"))
cp = json.loads((ROOT / "CURRENT_EXECUTION_CHECKPOINT.json").read_text(encoding="utf-8"))
doctrine_contract = json.loads((ROOT / "milestone_contracts/governance/career-os-supervised-production-v1-continuity-sync.json").read_text(encoding="utf-8"))
slice1_sync = json.loads((ROOT / "milestone_contracts/governance/career-os-supervised-production-v1-slice1-completion-sync.json").read_text(encoding="utf-8"))
slice2_sync = json.loads((ROOT / "milestone_contracts/governance/supervised-production-v1-slice2-completion-sync.json").read_text(encoding="utf-8"))
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

# Original doctrine and Slice 1 completion remain preserved as history.
sp = cp["supervised_production_v1"]
assert sp["canonical_merge_sha"] == DOCTRINE_MERGE_SHA
assert sp["reviewed_head_sha"] == DOCTRINE_HEAD
assert sp["reviewed_candidate_fingerprint"] == DOCTRINE_FINGERPRINT
assert sp["cursor_review_exception"]["fingerprint"] == DOCTRINE_FINGERPRINT
assert doctrine_contract["milestone_id"] == "SUPERVISED_PRODUCTION_V1_CONTINUITY_SYNC"
assert slice1_sync["milestone_id"] == "SUPERVISED_PRODUCTION_V1_SLICE_1_COMPLETION_SYNC"
s1 = cp["slice_1_completion"]
assert s1["milestone_id"] == SLICE1
assert s1["operator_status"] == "COMPLETED_BY_OPERATOR"
assert s1["human_acceptance_status"] == "BORA_ACCEPTED"
assert s1["reviewed_head_sha"] == "18883e12dc307d22b2928a3c3ece4da3d7bb8fd8"
assert s1["canonical_merge_sha"] == SLICE1_MERGE
assert s1["reviewed_candidate_fingerprint"] == "1620050e603b16fd3a188c8c1f6b4e47b55f5801ec447e1666251a45280f26e6"
assert s1["local_assurance"] == "102/102_PASS_ALL_PHASES"
assert s1["golden"] == "15/15_PASS"
assert s1["github_assurance"] == "RUN_151_SUCCESS"
assert s1["independent_review"] == "SAFE"
assert s1["implementation_authority_status"] == "EXHAUSTED_BY_COMPLETION"

# Slice 2 is now the current completed canonical seam.
assert cp["checkpoint_id"] == "CAREER_OS_CHECKPOINT_2026-09-24_SUPERVISED_PRODUCTION_V1_SLICE_2_COMPLETION_SYNC"
assert cp["canonical_basis_sha"] == SLICE2_MERGE
assert cp["recorded_at"] == "2026-09-24"
assert cp["operator_status"] == "SLICE_2_COMPLETION_SYNC_COMPLETED_BY_OPERATOR"
s2 = cp["slice_2_completion"]
assert s2["milestone_id"] == SLICE2
assert s2["operator_status"] == "COMPLETED_BY_OPERATOR"
assert s2["human_acceptance_status"] == "BORA_ACCEPTED"
assert s2["accepted_at"] == "2026-09-24"
assert s2["reviewed_head_sha"] == SLICE2_HEAD
assert s2["canonical_merge_sha"] == SLICE2_MERGE
assert s2["reviewed_candidate_fingerprint"] == SLICE2_FINGERPRINT
assert s2["reviewed_tree"] == s2["merge_tree"] == SLICE2_TREE
assert s2["local_assurance"] == "103/103_PASS_ALL_PHASES"
assert s2["golden"] == "15/15_PASS"
assert s2["github_assurance"] == "RUN_157_SUCCESS"
assert s2["independent_review"] == "SAFE"
assert s2["implementation_authority_status"] == "EXHAUSTED_BY_COMPLETION"

# Closure deliberately stops with no successor runtime seam selected.
next_seam = cp["next_candidate_seam"]
assert next_seam["milestone_id"] is None
assert next_seam["selection_status"] == "NONE_SELECTED"
assert next_seam["implementation_authorized"] is False
assert "Section 9 item 2" in next_seam["roadmap_context"]
assert "does not select or authorize it" in next_seam["roadmap_context"]
assert "NEXT_CANDIDATE_SEAM NONE_SELECTED" in ps["current_phase"]
assert "No successor runtime milestone is selected or authorized" in ps["next_authorized_action"]
assert "Section 9 item 2 is roadmap context only" in ps["next_authorized_action"]
assert "Global implementation_authorized remains false" in ps["next_authorized_action"]
assert "No successor runtime milestone is selected or authorized" in cp["exact_next_allowed_action"]
assert "Historical Recommendation-B implementation authority was SCOPED_TO_THIS_MILESTONE_ONLY_NOT_GLOBAL and is exhausted/closed; never a blanket/global implementation grant." in cp["exact_next_allowed_action"]
assert " ? " not in cp["exact_next_allowed_action"]
assert " ? " not in cp["continuity_rule"]

# Human-readable recovery pointers agree with the machine-readable routing.
for text in (milestone, state):
    assert SLICE2 in text
    assert "COMPLETED_BY_OPERATOR / BORA_ACCEPTED (2026-09-24)" in text
    assert "No successor runtime" in text
    assert "Section 9 item 2" in text

assert "2026-09-24 — SUPERVISED_PRODUCTION_V1 Slice 2 completion continuity sync" in changelog
assert SLICE2_FINGERPRINT in changelog
assert "GitHub Assurance run #157 SUCCESS" in changelog

# The Slice 2 completion sync itself is governance-only and fail-closed.
assert slice2_sync["milestone_id"] == "SUPERVISED_PRODUCTION_V1_SLICE_2_COMPLETION_SYNC"
assert slice2_sync["kind"] == "GOVERNANCE_SYNC"
assert slice2_sync["baseline_sha"] == SLICE2_MERGE
for forbidden in ("src/**", "schemas/**", "docs/**"):
    assert forbidden in slice2_sync["forbidden_paths"]
for allowed in ("project_state.json", "CURRENT_EXECUTION_CHECKPOINT.json"):
    assert allowed in slice2_sync["allowed_paths"]
assert "no successor runtime seam selected or authorized" in slice2_sync["goal"]
assert "NO SUCCESSOR RUNTIME SEAM IS AUTHORIZED BY THIS CLOSURE" in slice2_sync["human_approval_requirements"]

# Historical accepted roadmap state remains present.
assert cp["recommendation_b_completion"]["human_acceptance_status"] == "BORA_ACCEPTED"
assert cp["phase_h_acceptance"]["human_acceptance_status"] == "BORA_ACCEPTED"

print("PASS: supervised production v1 Slice 2 completion continuity sync verified.")
