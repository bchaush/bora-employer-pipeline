import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MERGE_SHA = '01602bf6ba4329b37d8b0365a77f53f953dce597'
REVIEWED_HEAD = '5cb49e0eba7b86773e20738f3e250252c389b3fd'
TREE = '3ddcd3cecb54ad9a3bc053dff59833ebc90e5cfb'
FINGERPRINT = 'bc073a55b8b14aab954f19a0d220e5eb9184f09607761bf35866b6883590a253'
SLICE = 'SUPERVISED_PRODUCTION_V1_SLICE_1_GMAIL_TO_SHEET'

ps = json.loads((ROOT / 'project_state.json').read_text(encoding='utf-8'))
cp = json.loads((ROOT / 'CURRENT_EXECUTION_CHECKPOINT.json').read_text(encoding='utf-8'))
contract = json.loads((ROOT / 'milestone_contracts/governance/career-os-supervised-production-v1-continuity-sync.json').read_text(encoding='utf-8'))
agents = (ROOT / 'AGENTS.md').read_text(encoding='utf-8')
milestone = (ROOT / 'CURRENT_MILESTONE.md').read_text(encoding='utf-8')
state = (ROOT / 'CURRENT_STATE.md').read_text(encoding='utf-8')
changelog = (ROOT / 'CHANGELOG.md').read_text(encoding='utf-8')

assert ps['current_phase'].startswith('SUPERVISED_PRODUCTION_V1')
assert SLICE in ps['current_phase']
assert 'SELECTED_NOT_AUTHORIZED' in ps['current_phase']
assert SLICE in ps['next_authorized_action']
assert 'NOT_AUTHORIZED' in ps['next_authorized_action']
assert cp['checkpoint_id'] == 'CAREER_OS_CHECKPOINT_2026-09-16_SUPERVISED_PRODUCTION_V1_CONTINUITY_SYNC'
assert cp['canonical_basis_sha'] == MERGE_SHA
assert cp['phase_id'] == 'SUPERVISED_PRODUCTION_V1'
assert cp['phase_mode'] == 'SUPERVISED_PRODUCTION_GOVERNANCE'
assert cp['human_acceptance_status'] == 'BORA_ACCEPTED'
assert cp['implementation_authorized'] is False

sp = cp['supervised_production_v1']
assert sp['canonical_merge_sha'] == MERGE_SHA
assert sp['reviewed_head_sha'] == REVIEWED_HEAD
assert sp['reviewed_tree_sha'] == TREE
assert sp['merge_tree_sha'] == TREE
assert sp['reviewed_candidate_fingerprint'] == FINGERPRINT
assert sp['cursor_review_exception']['scope'] == 'ONE_TASK_FINGERPRINT_SPECIFIC_DOCTRINE_ONLY_EXCEPTION'
assert sp['cursor_review_exception']['fingerprint'] == FINGERPRINT
assert sp['cursor_review_exception']['human_authorization_event'] == 'I explicitly authorize a one-task human governance exception to the mandatory Cursor review for the exact frozen SUPERVISED_PRODUCTION_V1 doctrine-only candidate with fingerprint: ' + FINGERPRINT
assert 'This authorization applies only to this exact fingerprint' in sp['cursor_review_exception']['human_scope_event']
assert 'substitute_evidence' not in sp['cursor_review_exception']
assert 'UNCHANGED_MANDATORY' in sp['cursor_review_exception']['future_cursor_rule']

next_seam = cp['next_candidate_seam']
assert next_seam['milestone_id'] == SLICE
assert next_seam['selection_status'] == 'SELECTED_NOT_AUTHORIZED'
assert next_seam['implementation_authorized'] is False
assert 'separate explicit Bora authorization' in ' '.join(next_seam['required_before_implementation'])
assert 'docs/SUPERVISED_PRODUCTION_V1.md' in cp['continuity_rule']
assert 'Do not implement Gmail or Google Sheets before that authorization' in cp['exact_next_allowed_action']
assert 'recommendation_b_completion' in cp
assert cp['recommendation_b_completion']['human_acceptance_status'] == 'BORA_ACCEPTED'
assert 'phase_h_acceptance' in cp
assert cp['phase_h_acceptance']['human_acceptance_status'] == 'BORA_ACCEPTED'

for text in (agents, milestone, state):
    assert 'SUPERVISED_PRODUCTION_V1' in text
    assert SLICE in text
    assert 'SELECTED_NOT_AUTHORIZED' in text
assert 'docs/SUPERVISED_PRODUCTION_V1.md' in agents
assert 'SUPERVISED_PRODUCTION_V1 continuity sync' in changelog

assert contract['milestone_id'] == 'SUPERVISED_PRODUCTION_V1_CONTINUITY_SYNC'
assert contract['kind'] == 'GOVERNANCE_SYNC'
assert contract['baseline_sha'] == MERGE_SHA
assert 'src/**' in contract['forbidden_paths']
assert 'schemas/**' in contract['forbidden_paths']
assert 'docs/**' in contract['forbidden_paths']
assert 'project_state.json' in contract['allowed_paths']
assert 'CURRENT_EXECUTION_CHECKPOINT.json' in contract['allowed_paths']
assert 'tests/career_os_supervised_production_v1_continuity_sync_test.py' in contract['allowed_paths']
assert 'SLICE_1_IMPLEMENTATION_REQUIRES_SEPARATE_EXPLICIT_BORA_AUTHORIZATION' in contract['human_approval_requirements']

print('PASS: supervised production v1 continuity sync verified.')
