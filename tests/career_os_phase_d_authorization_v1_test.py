import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / 'milestone_contracts' / 'governance' / 'career-os-phase-d-authorization-v1.json'
CHECKPOINT = ROOT / 'CURRENT_EXECUTION_CHECKPOINT.json'
PROJECT_STATE = json.loads((ROOT / 'project_state.json').read_text(encoding='utf-8'))
AGENTS = (ROOT / 'AGENTS.md').read_text(encoding='utf-8')
CURRENT_MILESTONE = (ROOT / 'CURRENT_MILESTONE.md').read_text(encoding='utf-8')
CURRENT_STATE = (ROOT / 'CURRENT_STATE.md').read_text(encoding='utf-8')
CHANGELOG = (ROOT / 'CHANGELOG.md').read_text(encoding='utf-8')
ADR = (ROOT / 'docs' / 'decisions' / 'ADR-CAREER-OS-EVAL-HARNESS-SEQUENCE-V1.md').read_text(encoding='utf-8')
POLICY_ADR_PATH = ROOT / 'docs' / 'decisions' / 'ADR-CAREER-OS-AGENT-CONTEXT-USAGE-EFFICIENCY-V1.md'

BASELINE_SHA = '4902f74a9282ba00f77ae2badf2b8e0139dbc7f1'

assert CONTRACT.exists(), 'Phase D authorization governance milestone contract missing'
contract = json.loads(CONTRACT.read_text(encoding='utf-8'))
assert contract['milestone_id'] == 'CAREER_OS_PHASE_D_AUTHORIZATION_V1'
assert contract['kind'] == 'GOVERNANCE_SYNC'
assert contract['baseline_sha'] == BASELINE_SHA
for forbidden_path in (
    'BLUEPRINT.md', 'CLAUDE.md', '.cursor/**', '.cursorignore', '.claude/**', 'src/**',
    'schemas/**', 'claims/**', 'evidence/**', 'experiences/**', 'resume/**', 'golden-tests/**',
):
    assert forbidden_path in contract['forbidden_paths'], f'contract must forbid {forbidden_path}'
assert 'CURRENT_EXECUTION_CHECKPOINT.json' in contract['allowed_paths']
assert 'project_state.json' in contract['allowed_paths']

# This governance sync must not touch the already-accepted policy ADR --
# it records only the Phase D authorization transition.
assert 'docs/decisions/ADR-CAREER-OS-AGENT-CONTEXT-USAGE-EFFICIENCY-V1.md' in contract['forbidden_paths']
assert POLICY_ADR_PATH.exists()

# Live checkpoint must record the Phase D authorization transition exactly.
assert CHECKPOINT.exists(), 'canonical execution checkpoint missing'
cp = json.loads(CHECKPOINT.read_text(encoding='utf-8'))
assert cp['canonical_basis_sha'] == BASELINE_SHA
assert cp['phase_id'] == 'CAREER_OS_FAILURE_TAXONOMY_AND_EVALUATOR_COVERAGE_MAP_V1'
assert cp['phase_mode'] == 'READ_ONLY_DESIGN_ONLY'
assert cp['authorization_status'] == 'BORA_AUTHORIZED'
assert cp['selection_status'] == 'SELECTED'
assert cp['operator_status'] == 'NOT_YET_COMPLETED'
assert cp['implementation_authorized'] is False
assert cp['prior_phase']['phase_id'] == 'CAREER_OS_AGENT_CONTEXT_AND_USAGE_EFFICIENCY_V1'
assert cp['prior_phase']['human_acceptance_status'] == 'BORA_ACCEPTED'

# No substantive Phase D taxonomy/evaluator-coverage-map content may be
# fabricated by this bounded authorization-only sync.
completed = ' '.join(cp['completed_actions'])
assert 'taxonomy' not in completed.lower() or 'no substantive' in completed.lower()
assert 'severity ranking' not in completed
assert 'evaluator-coverage map' not in completed or 'no substantive' in completed.lower()

# project_state.json must point at Phase D, authorized but not completed,
# with no implementation authorized and Phase E still proposed only.
assert PROJECT_STATE['current_phase'].startswith('CAREER_OS_FAILURE_TAXONOMY_AND_EVALUATOR_COVERAGE_MAP_V1')
assert 'BORA_AUTHORIZED' in PROJECT_STATE['current_phase']
assert 'SELECTED' in PROJECT_STATE['current_phase']
assert 'NOT_YET_COMPLETED' in PROJECT_STATE['current_phase']
assert 'NO_IMPLEMENTATION_AUTHORIZED' in PROJECT_STATE['current_phase']
assert 'Phase E' in PROJECT_STATE['next_authorized_action']
assert 'PROPOSED_NOT_AUTHORIZED' in PROJECT_STATE['next_authorized_action']

# CURRENT_MILESTONE.md / CURRENT_STATE.md / AGENTS.md / the eval-harness ADR
# must all agree: the prior policy milestone remains BORA_ACCEPTED/GOVERNING
# and Phase D is BORA_AUTHORIZED / SELECTED / NOT_YET_COMPLETED, with Phase E
# and later still PROPOSED_NOT_AUTHORIZED.
for surface_name, surface_text in (
    ('CURRENT_MILESTONE.md', CURRENT_MILESTONE),
    ('CURRENT_STATE.md', CURRENT_STATE),
    ('AGENTS.md', AGENTS),
    ('ADR-CAREER-OS-EVAL-HARNESS-SEQUENCE-V1.md', ADR),
):
    assert 'COMPLETED_BY_OPERATOR / BORA_ACCEPTED (2026-09-11) / GOVERNANCE_ONLY / GOVERNING' in surface_text, (
        f'{surface_name} must preserve the prior policy milestone acceptance unchanged'
    )
    assert 'BORA_AUTHORIZED / SELECTED / NOT_YET_COMPLETED' in surface_text, (
        f'{surface_name} must record Phase D as BORA_AUTHORIZED / SELECTED / NOT_YET_COMPLETED'
    )
    assert 'implementation_authorized' in surface_text.lower() or 'implementation not authorized' in surface_text.lower() or 'no implementation' in surface_text.lower() or 'NO_IMPLEMENTATION_AUTHORIZED' in surface_text, (
        f'{surface_name} must state that implementation remains unauthorized'
    )
    assert 'PROPOSED_NOT_AUTHORIZED' in surface_text, f'{surface_name} must state Phase E remains PROPOSED_NOT_AUTHORIZED'

# CHANGELOG.md must record this transition as a distinct dated entry,
# separate from the prior policy-acceptance entry.
assert 'CAREER_OS_FAILURE_TAXONOMY_AND_EVALUATOR_COVERAGE_MAP_V1' in CHANGELOG
assert 'BORA_AUTHORIZED' in CHANGELOG
assert 'authorized by Bora (READ_ONLY / DESIGN_ONLY, BORA_AUTHORIZED)' in CHANGELOG
assert 'accepted by Bora (GOVERNANCE-ONLY, BORA ACCEPTED)' in CHANGELOG

# The already-accepted policy ADR itself must be untouched by this sync --
# still governing, without a Phase D re-adjudication inside it.
policy_adr_text = POLICY_ADR_PATH.read_text(encoding='utf-8')
assert 'GOVERNING' in policy_adr_text
assert 'DECISION (BORA_ACCEPTED, GOVERNING):' in policy_adr_text

print('PASS: Career OS Phase D authorization transition verified.')
