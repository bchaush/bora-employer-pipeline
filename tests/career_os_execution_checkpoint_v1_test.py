import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECKPOINT = ROOT / 'CURRENT_EXECUTION_CHECKPOINT.json'
PROJECT_STATE = json.loads((ROOT / 'project_state.json').read_text(encoding='utf-8'))
AGENTS = (ROOT / 'AGENTS.md').read_text(encoding='utf-8')

CANONICAL_BASELINE_SHA = '615ac17029bc62cd6b8cd514b9c25ef972fadd6f'

assert CHECKPOINT.exists(), 'canonical execution checkpoint missing'
cp = json.loads(CHECKPOINT.read_text(encoding='utf-8'))

assert cp['schema_version'] == '1.0'
assert cp['canonical_basis_sha'] == CANONICAL_BASELINE_SHA
assert cp['phase_id'] == 'CAREER_OS_TRACE_AND_FAILURE_CORPUS_INVENTORY_V1'
assert cp['phase_mode'] == 'READ_ONLY'
assert cp['phase_status'] == 'BORA_AUTHORIZED_NOT_YET_COMPLETED'
assert cp['implementation_authorized'] is False

# Phase B human acceptance must be recorded distinctly from Phase C
# authorization -- operator completion, Bora acceptance, and next-phase
# authorization must never collapse into one undifferentiated claim.
prior_phase = cp['prior_phase']
assert prior_phase['phase_id'] == 'CAREER_OS_EVAL_AND_HARNESS_AUDIT_V1'
assert prior_phase['phase_mode'] == 'READ_ONLY'
assert prior_phase['operator_status'] == 'COMPLETED_BY_OPERATOR'
assert prior_phase['human_acceptance_status'] == 'BORA_ACCEPTED'

assert isinstance(cp['exact_next_allowed_action'], str) and cp['exact_next_allowed_action'].strip()
assert 'Begin Phase C' in cp['exact_next_allowed_action']
assert 'no later phase' in cp['exact_next_allowed_action'] or 'no phase beyond Phase C' in cp['exact_next_allowed_action']

# terminal_adjudication must reflect Bora's acceptance of Phase B and
# Bora's authorization of Phase C, while still stating Phase C is not
# yet completed and implementation is not authorized.
assert 'BORA ACCEPTED' in cp['terminal_adjudication']
assert 'BORA AUTHORIZED' in cp['terminal_adjudication']
assert 'NOT YET COMPLETED' in cp['terminal_adjudication']
assert 'IMPLEMENTATION NOT AUTHORIZED' in cp['terminal_adjudication']

# Must not fabricate Phase C substantive findings/corpus inventory at
# this authorization-only transition point.
not_done = ' '.join(cp['not_completed_or_not_authorized'])
assert 'CAREER_OS_RUN_TRACE_V1' in not_done
assert 'trace schema' in not_done or 'trace infrastructure' in not_done
assert 'Phase D' in not_done or 'later phase' in not_done
assert 'No production Career OS behavior changed' in not_done
assert not any('corpus inventory' in action.lower() and 'no' not in action.lower() for action in cp['completed_actions'])

assert PROJECT_STATE['current_phase'].startswith('CAREER_OS_TRACE_AND_FAILURE_CORPUS_INVENTORY_V1 (BORA_AUTHORIZED')
assert 'NOT_YET_COMPLETED' in PROJECT_STATE['current_phase']
assert 'NO_IMPLEMENTATION_AUTHORIZED' in PROJECT_STATE['current_phase']
assert 'CAREER_OS_TRACE_AND_FAILURE_CORPUS_INVENTORY_V1' in PROJECT_STATE['next_authorized_action']
assert 'Phase D' in PROJECT_STATE['next_authorized_action']
assert 'PROPOSED_NOT_AUTHORIZED' in PROJECT_STATE['next_authorized_action']
assert 'CURRENT_EXECUTION_CHECKPOINT.json' in AGENTS
assert 'Operator completion never grants human acceptance' in AGENTS

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

print('PASS: Career OS execution checkpoint and fresh-chat handoff lock verified.')
