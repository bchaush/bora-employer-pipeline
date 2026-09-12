import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECKPOINT = ROOT / 'CURRENT_EXECUTION_CHECKPOINT.json'
PROJECT_STATE = json.loads((ROOT / 'project_state.json').read_text(encoding='utf-8'))
AGENTS = (ROOT / 'AGENTS.md').read_text(encoding='utf-8')

CANONICAL_BASELINE_SHA = '4902f74a9282ba00f77ae2badf2b8e0139dbc7f1'

assert CHECKPOINT.exists(), 'canonical execution checkpoint missing'
cp = json.loads(CHECKPOINT.read_text(encoding='utf-8'))

assert cp['schema_version'] == '1.0'
assert cp['canonical_basis_sha'] == CANONICAL_BASELINE_SHA
assert cp['phase_id'] == 'CAREER_OS_FAILURE_TAXONOMY_AND_EVALUATOR_COVERAGE_MAP_V1'
assert cp['phase_mode'] == 'READ_ONLY_DESIGN_ONLY'
assert cp['authorization_status'] == 'BORA_AUTHORIZED'
assert cp['selection_status'] == 'SELECTED'
assert cp['operator_status'] == 'COMPLETED_BY_OPERATOR'
assert cp['human_acceptance_status'] == 'BORA_ACCEPTED'
assert cp['accepted_at'] == '2026-09-11'
assert cp['implementation_authorized'] is False

# The governance-only agent context/usage-efficiency policy milestone must
# be recorded distinctly from this new Phase D authorization -- operator
# completion, Bora acceptance/authorization, and next-phase authorization
# must never collapse into one undifferentiated claim.
prior_phase = cp['prior_phase']
assert prior_phase['phase_id'] == 'CAREER_OS_AGENT_CONTEXT_AND_USAGE_EFFICIENCY_V1'
assert prior_phase['phase_mode'] == 'GOVERNANCE_ONLY'
assert prior_phase['operator_status'] == 'COMPLETED_BY_OPERATOR'
assert prior_phase['human_acceptance_status'] == 'BORA_ACCEPTED'
assert prior_phase['accepted_at'] == '2026-09-11'

prior_prior_phase = cp['prior_prior_phase']
assert prior_prior_phase['phase_id'] == 'CAREER_OS_TRACE_AND_FAILURE_CORPUS_INVENTORY_V1'
assert prior_prior_phase['phase_mode'] == 'READ_ONLY'
assert prior_prior_phase['human_acceptance_status'] == 'BORA_ACCEPTED'

assert isinstance(cp['exact_next_allowed_action'], str) and cp['exact_next_allowed_action'].strip()
assert 'COMPLETED_BY_OPERATOR / BORA_ACCEPTED (2026-09-11) / READ_ONLY_DESIGN_ONLY' in cp['exact_next_allowed_action']
assert 'I am satisfied' in cp['exact_next_allowed_action']
assert 'implementation_authorized remains false' in cp['exact_next_allowed_action']
assert 'Phase E' in cp['exact_next_allowed_action']

# The Phase D acceptance is a Bora human event, and that acceptance must
# never be read as itself authorizing Phase E: this must be proven by exact
# wording in the machine-readable seam field, not merely inferred from
# nearby PROPOSED_NOT_AUTHORIZED text elsewhere.
assert 'Bora separately decides whether to authorize Phase E' in cp['exact_next_allowed_action']
assert 'does not itself authorize Phase E' in cp['exact_next_allowed_action']
assert (
    "does not itself constitute that separate decision" in cp['exact_next_allowed_action']
    or "never self-granted" in cp['exact_next_allowed_action']
)
assert "Absent Bora's separate, explicit authorization of Phase E" in cp['exact_next_allowed_action']
assert 'no Phase E and no implementation' in cp['exact_next_allowed_action']

# terminal_adjudication must reflect the prior GOVERNING policy AND Bora's
# explicit Phase D acceptance event, while still stating implementation and
# Phase E are not authorized.
assert 'GOVERNANCE_ONLY / GOVERNING' in cp['terminal_adjudication']
assert 'COMPLETED_BY_OPERATOR / BORA_ACCEPTED (2026-09-11) / READ_ONLY_DESIGN_ONLY' in cp['terminal_adjudication']
assert 'PROPOSED_NOT_AUTHORIZED' in cp['terminal_adjudication']
assert 'IMPLEMENTATION NOT AUTHORIZED' in cp['terminal_adjudication']

# Must record the genuine substantive Phase D completion action, including
# the durable report path, and Bora's acceptance of it.
completed = ' '.join(cp['completed_actions'])
assert 'CAREER_OS_FAILURE_TAXONOMY_AND_EVALUATOR_COVERAGE_MAP_V1' in completed
assert 'docs/audits/CAREER_OS_FAILURE_TAXONOMY_AND_EVALUATOR_COVERAGE_MAP_V1_REPORT.md' in completed
assert 'I am satisfied' in completed

not_done = ' '.join(cp['not_completed_or_not_authorized'])
assert 'BORA_ACCEPTED' in not_done
assert 'CAREER_OS_RUN_TRACE_V1' in not_done
assert 'trace infrastructure' in not_done
assert 'Phase E' in not_done or 'later' in not_done
assert 'No production Career OS behavior changed' in not_done
assert 'CLAUDE.md' in not_done and '.cursor/rules' in not_done

# Phase D acceptance must be pinned as a genuine Bora human event, never an
# operator self-grant, and must be pinned as NOT itself authorizing Phase E,
# implementation, or any later phase -- each with its own exact wording so
# these invariants cannot silently regress into a vaguer, weaker claim.
assert 'recorded human event' in not_done
assert 'never self-granted by the operator' in not_done
assert 'does not itself authorize Phase E' in not_done
assert 'implementation_authorized remains false' in not_done

# Phase B, Phase C, and the agent context/usage-efficiency policy
# milestone's completed-action lineage must all survive as historical
# reference even though none is the live current phase.
assert 'phase_b_completed_actions_reference' in cp
assert 'phase_c_completed_actions_reference' in cp
assert 'policy_milestone_completed_actions_reference' in cp

assert PROJECT_STATE['current_phase'].startswith('CAREER_OS_FAILURE_TAXONOMY_AND_EVALUATOR_COVERAGE_MAP_V1 (COMPLETED_BY_OPERATOR')
assert 'BORA_ACCEPTED (2026-09-11)' in PROJECT_STATE['current_phase']
assert 'READ_ONLY_DESIGN_ONLY' in PROJECT_STATE['current_phase']
assert 'NO_IMPLEMENTATION_AUTHORIZED' in PROJECT_STATE['current_phase']
assert 'CAREER_OS_FAILURE_TAXONOMY_AND_EVALUATOR_COVERAGE_MAP_V1' in PROJECT_STATE['next_authorized_action']
assert 'COMPLETED_BY_OPERATOR / BORA_ACCEPTED (2026-09-11)' in PROJECT_STATE['next_authorized_action']
assert 'Phase E' in PROJECT_STATE['next_authorized_action']
assert 'PROPOSED_NOT_AUTHORIZED' in PROJECT_STATE['next_authorized_action']
assert 'CURRENT_EXECUTION_CHECKPOINT.json' in AGENTS
assert 'BORA_ACCEPTED (2026-09-11)' in AGENTS
assert 'GOVERNING' in AGENTS
assert 'COMPLETED_BY_OPERATOR / BORA_ACCEPTED (2026-09-11)' in AGENTS
# Phase D's own accepted state in AGENTS.md must be proven by the single
# non-collidable anchored block, not by the bare substring above (a strict
# prefix of the GOVERNANCE_ONLY policy milestone's own acceptance clause).
assert 'COMPLETED_BY_OPERATOR / BORA_ACCEPTED (2026-09-11) / READ_ONLY_DESIGN_ONLY' in AGENTS

# AGENTS.md must keep requiring project_state.json to be read before
# CURRENT_EXECUTION_CHECKPOINT.json, and must not restate a competing
# recovery order outside the single canonical ADR Section 6 order.
project_state_pos = AGENTS.find('`project_state.json`')
checkpoint_pos = AGENTS.find('`CURRENT_EXECUTION_CHECKPOINT.json`')
assert project_state_pos != -1, 'AGENTS.md no longer mentions project_state.json'
assert checkpoint_pos != -1, 'AGENTS.md no longer mentions CURRENT_EXECUTION_CHECKPOINT.json'
assert project_state_pos < checkpoint_pos, (
    'AGENTS.md must read project_state.json before CURRENT_EXECUTION_CHECKPOINT.json'
)
assert 'do not restate a different order elsewhere' in AGENTS
assert 'do not restate a different or partial order here' in AGENTS

# AGENTS.md must carry a concise pointer to the new context/usage-efficiency
# ADR without restating its policy body.
assert 'ADR-CAREER-OS-AGENT-CONTEXT-USAGE-EFFICIENCY-V1' in AGENTS
assert 'never overrides the Authority Order above' in AGENTS or 'never overrides' in AGENTS

print('PASS: Career OS execution checkpoint and fresh-chat handoff lock verified.')
