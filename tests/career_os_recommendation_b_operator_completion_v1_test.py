import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
MERGE="0120bcde46a10f1ee7d5ec33e17f5fca7b8fc310"
HEAD="d328350a232b9051b34fc302d100ed52bb5964c6"
TREE="49445e42fc9e1545c99cfe3b441c94037badc82c"
RID="CAREER_OS_MILESTONE_RUN_V1_TARGETED_OPTIMIZATION_V1"
cp=json.loads((ROOT/"CURRENT_EXECUTION_CHECKPOINT.json").read_text(encoding="utf-8"))
ps=json.loads((ROOT/"project_state.json").read_text(encoding="utf-8"))
contract=json.loads((ROOT/"milestone_contracts/governance/career-os-recommendation-b-completion-v1.json").read_text(encoding="utf-8"))
assert cp["checkpoint_id"]=="CAREER_OS_CHECKPOINT_2026-09-24_SUPERVISED_PRODUCTION_V1_SLICE_2_COMPLETION_SYNC"
assert cp["canonical_basis_sha"]=="f70ef63386e9eb5134480b4996ad493720abc02c"
assert cp["phase_id"]=="SUPERVISED_PRODUCTION_V1"
assert cp["operator_status"]=="SLICE_2_COMPLETION_SYNC_COMPLETED_BY_OPERATOR"
assert cp["human_acceptance_status"]=="BORA_ACCEPTED"
assert cp["accepted_at"]=="2026-09-24"
assert cp["recommendation_b_completion"]["milestone_id"]==RID
assert cp["implementation_authorized"] is False
assert cp["recommendation_b_authorization"]["operator_status"]=="NOT_YET_COMPLETED"  # historical authorization fact remains immutable
comp=cp["recommendation_b_completion"]
assert comp["operator_status"]=="COMPLETED_BY_OPERATOR"
assert comp["human_acceptance_status"]=="BORA_ACCEPTED"
assert HEAD in comp["canonical_merge_verification"] and TREE in comp["canonical_merge_verification"] and MERGE in comp["canonical_merge_verification"]
assert comp["reviewed_candidate"]["cursor_outcome"]=="SAFE" and comp["reviewed_candidate"]["cursor_findings"]==[]
assert comp["coverage_preservation"]["missing_old_functions"]==[]
assert comp["coverage_preservation"]["missing_old_pass_labels"]==[]
assert comp["coverage_preservation"]["added_test_function"]=="_test_prepared_baseline_fixture_isolation"
assert comp["performance_evidence"]["approx_median_improvement_percent"]==8.69
assert "real controller + real Git behavior" in comp["stop_line"]
assert "No successor runtime milestone is selected or authorized" in cp["exact_next_allowed_action"]
assert "Section 9 item 2 is roadmap context only" in cp["exact_next_allowed_action"]
assert "OPERATE FIRST / BUILD SECOND" in cp["exact_next_allowed_action"]  # historical context remains preserved
assert "Recommendation C remains NOT_AUTHORIZED" in cp["exact_next_allowed_action"]
assert "Phase I and every later roadmap phase remain PROPOSED_NOT_AUTHORIZED" in cp["exact_next_allowed_action"]
assert "COMPLETED_BY_OPERATOR; BORA_ACCEPTED (2026-09-15)" in ps["current_phase"]
assert "SUPERVISED_PRODUCTION_V1_SLICE_2_GATES_MATCH_TRUTH_TO_SHEET" in ps["next_authorized_action"]
assert "OPERATE FIRST / BUILD SECOND" in ps["next_authorized_action"]  # historical context remains preserved
assert contract["baseline_sha"]==MERGE and contract["kind"]=="GOVERNANCE_SYNC"
for forbidden in ("src/**","scripts/**","tests/milestone_run_v1_test.py","milestone_contracts/feature/career-os-milestone-run-v1-targeted-optimization-v1.json"):
    assert forbidden in contract["forbidden_paths"]
for rel in ("CURRENT_MILESTONE.md","CURRENT_STATE.md","AGENTS.md","CHANGELOG.md"):
    text=(ROOT/rel).read_text(encoding="utf-8")
    assert RID in text
    assert "COMPLETED_BY_OPERATOR" in text
    assert ("PENDING_BORA_ACCEPTANCE" in text) or ("BORA_ACCEPTED (2026-09-15)" in text)
adr=(ROOT/"docs/decisions/ADR-CAREER-OS-EVAL-HARNESS-SEQUENCE-V1.md").read_text(encoding="utf-8")
agents=(ROOT/"AGENTS.md").read_text(encoding="utf-8")
changelog=(ROOT/"CHANGELOG.md").read_text(encoding="utf-8")
assert "COMPLETED_BY_OPERATOR / BORA_ACCEPTED (2026-09-15)" in adr
assert "the live current authorized milestone" not in adr
assert "Recommendation B acceptance update (2026-09-15)" in adr
sec6=adr[adr.index("## 6. New-chat recovery protocol"):adr.index("## 7. Audit deliverables required before implementation")]
assert "**COMPLETED_BY_OPERATOR / BORA_ACCEPTED (2026-09-15)**" in sec6
assert "OPERATE FIRST / BUILD SECOND" in sec6
assert "is now **BORA_AUTHORIZED / SELECTED / NOT_YET_COMPLETED**" not in sec6
agent_eval=agents[agents.index("## Eval / Harness Roadmap Recovery"):agents.index("## Agent Context & Usage Efficiency")]
assert "is now COMPLETED_BY_OPERATOR / BORA_ACCEPTED (2026-09-15)" in agent_eval
assert "OPERATE FIRST / BUILD SECOND" in agent_eval
assert "now **BORA_AUTHORIZED / SELECTED / NOT_YET_COMPLETED**" not in agent_eval
assert cp["recommendation_b_authorization"]["record_semantics"]=="HISTORICAL_AUTHORIZATION_SNAPSHOT_SUPERSEDED_BY_RECOMMENDATION_B_COMPLETION"
assert "has since completed" in cp["recommendation_b_authorization"]["not_implemented_this_sync"]
assert "recommendation_b_authorization object unchanged" not in " ".join(cp["completed_actions"])
assert "superseded historical snapshot" in " ".join(cp["completed_actions"])
action=ps["next_authorized_action"]
current_action=action.split(" HISTORICAL_ACCEPTED_CONTEXT_ONLY_NOT_CURRENT_AUTHORITY:",1)[0]
assert not current_action.rstrip().endswith((", and", " and", ",", "-"))
assert current_action.rstrip().endswith("Global implementation_authorized remains false.")
assert "SUPERVISED_PRODUCTION_V1_SLICE_2_GATES_MATCH_TRUTH_TO_SHEET" in current_action
assert "No successor runtime milestone is selected or authorized" in current_action
assert "No successor runtime implementation is authorized by this completion sync." in current_action
assert "first_point_of_divergence = A and first_causal_failure_point = B at two different points in the same run" in action
assert changelog.startswith("# Bora Employer Pipeline OS")
assert changelog.index("# Bora Employer Pipeline OS") < changelog.index("Career OS Recommendation B operator completion")
assert "## Pre-existing canonical continuity notes" in changelog

current_state=(ROOT/"CURRENT_STATE.md").read_text(encoding="utf-8")
current_milestone=(ROOT/"CURRENT_MILESTONE.md").read_text(encoding="utf-8")
assert "prior SCOPED_TO_THIS_MILESTONE_ONLY_NOT_GLOBAL implementation authority is exhausted" in current_state
assert "no Recommendation-B implementation authority remains open" in current_state
assert "Prior implementation authority: **SCOPED_TO_THIS_MILESTONE_ONLY_NOT_GLOBAL** -- now exhausted by operator completion" in current_milestone
assert "implementation authority SCOPED_TO_THIS_MILESTONE_ONLY_NOT_GLOBAL" not in current_milestone
hist_ref=cp["phase_g_acceptance_phase_h_authorization_not_completed_or_not_authorized_reference"]
assert all(s.startswith("Historical at the Phase-G-acceptance / Phase-H-authorization sync only:") for s in hist_ref if ("NOT_YET_COMPLETED" in s or "Recommendation B (bounded optimization" in s))


assert "PRIOR_IMPLEMENTATION_AUTHORITY_SCOPED_TO_THIS_MILESTONE_ONLY_NOT_GLOBAL_EXHAUSTED_BY_OPERATOR_COMPLETION" in ps["current_phase"]
assert "Historical at the Recommendation-B authorization event only:" in cp["terminal_adjudication"]
assert "CAREER_OS_MILESTONE_RUN_V1_TARGETED_OPTIMIZATION_V1 is separately authorized" not in cp["terminal_adjudication"]
term=cp["terminal_adjudication"]
hist=term.split("Historical at the Recommendation-B authorization event only:",1)[1].split("Historical pre-acceptance Recommendation-B completion state:",1)[0]
preaccept=term.split("Historical pre-acceptance Recommendation-B completion state:",1)[1].split("Live Recommendation-B acceptance state:",1)[0]
live=term.split("Live Recommendation-B acceptance state:",1)[1]
assert "PR #63" not in hist and "COMPLETED_BY_OPERATOR" not in hist and "PENDING_BORA_ACCEPTANCE" not in hist
assert "PR #63" in preaccept and "COMPLETED_BY_OPERATOR / PENDING_BORA_ACCEPTANCE" in preaccept
assert "grant lives" not in hist
assert "grant lives" not in agent_eval
sec10=adr[adr.index("## 10. Decision"):adr.index("## 11. Reference URLs at lock time")]
assert "scoped authorization authorizes Phase I" not in sec10
assert "this scoped authorization authorizes Phase I or any later phase" not in sec10
assert ("The original scoped implementation authority is exhausted" in sec10 or "The prior Recommendation-B scoped implementation authority remains exhausted" in sec10)
assert "the narrow grant lives only in the distinct recommendation_b_authorization record" not in " ".join(cp["phase_h_acceptance_recommendation_b_authorization_completed_actions_reference"])
assert "PR #64" in live and "COMPLETED_BY_OPERATOR / BORA_ACCEPTED (2026-09-15)" in live and "no successor engineering milestone is selected or authorized" in live
assert "NON_AUTHORITATIVE_FOCUSED_DIAGNOSTIC" in current_state

print("PASS: Recommendation B operator completion is recorded fail-closed without self-granting Bora acceptance.")
