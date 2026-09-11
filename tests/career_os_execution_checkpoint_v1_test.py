import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECKPOINT = ROOT / 'CURRENT_EXECUTION_CHECKPOINT.json'
PROJECT_STATE = json.loads((ROOT / 'project_state.json').read_text(encoding='utf-8'))
AGENTS = (ROOT / 'AGENTS.md').read_text(encoding='utf-8')

CANONICAL_BASELINE_SHA = 'ba6530498be3410e3524aacd1ff5fba0c815d8d0'

assert CHECKPOINT.exists(), 'canonical execution checkpoint missing'
cp = json.loads(CHECKPOINT.read_text(encoding='utf-8'))

assert cp['schema_version'] == '1.0'
assert cp['canonical_basis_sha'] == CANONICAL_BASELINE_SHA
assert cp['phase_id'] == 'CAREER_OS_AGENT_CONTEXT_AND_USAGE_EFFICIENCY_V1'
assert cp['phase_mode'] == 'GOVERNANCE_ONLY'
assert cp['operator_status'] == 'COMPLETED_BY_OPERATOR'
assert cp['human_acceptance_status'] == 'PENDING_BORA_ACCEPTANCE'
assert cp['implementation_authorized'] is False

# Phase C human acceptance must be recorded distinctly from this policy
# milestone's operator completion -- operator completion, Bora acceptance,
# and next-phase authorization must never collapse into one
# undifferentiated claim.
prior_phase = cp['prior_phase']
assert prior_phase['phase_id'] == 'CAREER_OS_TRACE_AND_FAILURE_CORPUS_INVENTORY_V1'
assert prior_phase['phase_mode'] == 'READ_ONLY'
assert prior_phase['operator_status'] == 'COMPLETED_BY_OPERATOR'
assert prior_phase['human_acceptance_status'] == 'BORA_ACCEPTED'

assert isinstance(cp['exact_next_allowed_action'], str) and cp['exact_next_allowed_action'].strip()
assert 'Bora reviews and accepts or rejects this policy milestone/checkpoint' in cp['exact_next_allowed_action']

# terminal_adjudication must reflect Bora's acceptance of Phase C and
# operator completion (not Bora acceptance) of this policy milestone,
# while still stating Phase D is not authorized and implementation is not
# authorized.
assert 'BORA ACCEPTED' in cp['terminal_adjudication']
assert 'PENDING_BORA_ACCEPTANCE' in cp['terminal_adjudication']
assert 'PROPOSED_NOT_AUTHORIZED' in cp['terminal_adjudication']
assert 'IMPLEMENTATION NOT AUTHORIZED' in cp['terminal_adjudication']

# Must record genuine completed policy-lock actions, not merely an
# authorization-only transition, but must not fabricate Phase D work.
completed = ' '.join(cp['completed_actions'])
assert 'ADR-CAREER-OS-AGENT-CONTEXT-USAGE-EFFICIENCY-V1' in completed
assert 'SOURCE_DIRECT' in completed
assert 'OPEN_HYPOTHESIS' in completed

not_done = ' '.join(cp['not_completed_or_not_authorized'])
assert 'CAREER_OS_RUN_TRACE_V1' in not_done
assert 'trace schema' in not_done or 'trace infrastructure' in not_done
assert 'Phase D' in not_done or 'later phase' in not_done
assert 'No production Career OS behavior changed' in not_done
assert 'CLAUDE.md' in not_done and '.cursor/rules' in not_done

# Phase B and Phase C completed-action lineage must both survive as
# historical reference even though neither is the live current phase.
assert 'phase_b_completed_actions_reference' in cp
assert 'phase_c_completed_actions_reference' in cp

assert PROJECT_STATE['current_phase'].startswith('CAREER_OS_AGENT_CONTEXT_AND_USAGE_EFFICIENCY_V1 (COMPLETED_BY_OPERATOR')
assert 'PENDING_BORA_ACCEPTANCE' in PROJECT_STATE['current_phase']
assert 'NO_IMPLEMENTATION_AUTHORIZED' in PROJECT_STATE['current_phase']
assert 'CAREER_OS_AGENT_CONTEXT_AND_USAGE_EFFICIENCY_V1' in PROJECT_STATE['next_authorized_action']
assert 'Phase D' in PROJECT_STATE['next_authorized_action']
assert 'PROPOSED_NOT_AUTHORIZED' in PROJECT_STATE['next_authorized_action']
assert 'CURRENT_EXECUTION_CHECKPOINT.json' in AGENTS
assert 'PENDING_BORA_ACCEPTANCE' in AGENTS

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
