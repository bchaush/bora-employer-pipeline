import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECKPOINT = ROOT / 'CURRENT_EXECUTION_CHECKPOINT.json'
PROJECT_STATE = json.loads((ROOT / 'project_state.json').read_text(encoding='utf-8'))
AGENTS = (ROOT / 'AGENTS.md').read_text(encoding='utf-8')

assert CHECKPOINT.exists(), 'canonical execution checkpoint missing'
cp = json.loads(CHECKPOINT.read_text(encoding='utf-8'))

assert cp['schema_version'] == '1.0'
assert cp['phase_id'] == 'CAREER_OS_EVAL_AND_HARNESS_AUDIT_V1'
assert cp['phase_mode'] == 'READ_ONLY'
assert cp['operator_status'] == 'COMPLETED_BY_OPERATOR'
assert cp['human_acceptance_status'] == 'PENDING_BORA_ACCEPTANCE'
assert cp['implementation_authorized'] is False
assert cp['proposed_next_phase']['phase_id'] == 'CAREER_OS_TRACE_AND_FAILURE_CORPUS_INVENTORY_V1'
assert cp['proposed_next_phase']['status'] == 'PROPOSED_NOT_AUTHORIZED'
assert isinstance(cp['exact_next_allowed_action'], str) and cp['exact_next_allowed_action'].strip()
assert 'no Phase C work may begin' in cp['exact_next_allowed_action']

# terminal_adjudication must read as an operator finding pending Bora
# acceptance, never as already-accepted doctrine.
assert 'PENDING BORA ACCEPTANCE' in cp['terminal_adjudication']
assert 'NOT ACCEPTED DOCTRINE' in cp['terminal_adjudication']

assert PROJECT_STATE['current_phase'].startswith('CAREER_OS_EVAL_AND_HARNESS_AUDIT_V1 (COMPLETED_BY_OPERATOR; PENDING_BORA_ACCEPTANCE')
assert 'CURRENT_EXECUTION_CHECKPOINT.json' in PROJECT_STATE['next_authorized_action']
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

