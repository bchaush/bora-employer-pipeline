import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
cp=json.loads((ROOT/"CURRENT_EXECUTION_CHECKPOINT.json").read_text(encoding="utf-8"))
ps=json.loads((ROOT/"project_state.json").read_text(encoding="utf-8"))
agents=(ROOT/"AGENTS.md").read_text(encoding="utf-8")
state=(ROOT/"CURRENT_STATE.md").read_text(encoding="utf-8")
milestone=(ROOT/"CURRENT_MILESTONE.md").read_text(encoding="utf-8")
adr=(ROOT/"docs/decisions/ADR-CAREER-OS-EVAL-HARNESS-SEQUENCE-V1.md").read_text(encoding="utf-8")
assert cp["checkpoint_id"]=="CAREER_OS_CHECKPOINT_2026-09-24_SUPERVISED_PRODUCTION_V1_SLICE_2_COMPLETION_SYNC"
assert cp["canonical_basis_sha"]=="f70ef63386e9eb5134480b4996ad493720abc02c"
assert cp["phase_id"]=="SUPERVISED_PRODUCTION_V1"
assert cp["operator_status"]=="SLICE_2_COMPLETION_SYNC_COMPLETED_BY_OPERATOR"
assert cp["human_acceptance_status"]=="BORA_ACCEPTED" and cp["accepted_at"]=="2026-09-24"
assert cp["slice_1_completion"]["human_acceptance_status"]=="BORA_ACCEPTED"
assert cp["slice_2_completion"]["human_acceptance_status"]=="BORA_ACCEPTED"
assert cp["next_candidate_seam"]["milestone_id"] is None
assert cp["next_candidate_seam"]["selection_status"]=="NONE_SELECTED"
assert cp["recommendation_b_completion"]["milestone_id"]=="CAREER_OS_MILESTONE_RUN_V1_TARGETED_OPTIMIZATION_V1"
assert cp["implementation_authorized"] is False
assert cp["recommendation_b_completion"]["human_acceptance_status"]=="BORA_ACCEPTED"
acc=cp["recommendation_b_acceptance"]
assert acc["human_acceptance_status"]=="BORA_ACCEPTED" and acc["accepted_at"]=="2026-09-15"
assert "I explicitly accept `CAREER_OS_MILESTONE_RUN_V1_TARGETED_OPTIMIZATION_V1` as completed." in acc["human_acceptance_event"]
assert "35033992088" in acc["canonical_acceptance_basis"]
assert cp["recommendation_b_authorization"]["operator_status"]=="NOT_YET_COMPLETED"  # historical authorization snapshot only
assert "HISTORICAL_AUTHORIZATION_SNAPSHOT" in cp["recommendation_b_authorization"]["record_semantics"]
assert "OPERATE FIRST / BUILD SECOND" in cp["exact_next_allowed_action"]
assert "No successor runtime milestone is selected or authorized" in cp["exact_next_allowed_action"]
assert "Section 9 item 2 is roadmap context only" in cp["exact_next_allowed_action"]
assert "Recommendation C remains NOT_AUTHORIZED" in cp["exact_next_allowed_action"]
assert "Phase I and every later roadmap phase remain PROPOSED_NOT_AUTHORIZED" in cp["exact_next_allowed_action"]
assert "BORA_ACCEPTED (2026-09-15)" in ps["current_phase"] and "PENDING_BORA_ACCEPTANCE" not in ps["current_phase"]
assert "OPERATE FIRST / BUILD SECOND" in ps["next_authorized_action"]
for surface in (agents,state,milestone,adr): assert "BORA_ACCEPTED (2026-09-15)" in surface
assert "PENDING_BORA_ACCEPTANCE" in (ROOT/"CHANGELOG.md").read_text(encoding="utf-8")
assert "BORA_ACCEPTED (2026-09-15)" in cp["continuity_rule"]
assert "PENDING_BORA_ACCEPTANCE" not in cp["continuity_rule"]
sec10=adr[adr.index("## 10. Decision"):adr.index("## 11. Reference URLs at lock time")]
assert "is now **COMPLETED_BY_OPERATOR / PENDING_BORA_ACCEPTANCE**" not in sec10
assert "COMPLETED_BY_OPERATOR / BORA_ACCEPTED (2026-09-15)" in sec10
assert "OPERATE FIRST / BUILD SECOND" in sec10
agent_context=agents[agents.index("## Agent Context & Usage Efficiency"):]
assert "PENDING_BORA_ACCEPTANCE after verified PR #63 merge" not in agent_context
print("PASS: Recommendation B explicit Bora acceptance is recorded without opening successor engineering authority.")
