import json
import re
from pathlib import Path

PHASE_F_PROPOSED_NOT_AUTHORIZED = re.compile(
    r'Phase F and every later roadmap phase remain \*{0,2}PROPOSED_NOT_AUTHORIZED\*{0,2}',
    re.IGNORECASE,
)

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

# Live checkpoint must preserve the Phase D authorization/acceptance facts
# exactly, now as prior_phase since Bora has since separately, explicitly
# authorized Phase E as the live current phase.
assert CHECKPOINT.exists(), 'canonical execution checkpoint missing'
cp = json.loads(CHECKPOINT.read_text(encoding='utf-8'))
assert cp['implementation_authorized'] is False
prior_phase = cp['prior_phase']
assert prior_phase['phase_id'] == 'CAREER_OS_FAILURE_TAXONOMY_AND_EVALUATOR_COVERAGE_MAP_V1'
assert prior_phase['phase_mode'] == 'READ_ONLY_DESIGN_ONLY'
assert prior_phase['operator_status'] == 'COMPLETED_BY_OPERATOR'
assert prior_phase['human_acceptance_status'] == 'BORA_ACCEPTED'
assert prior_phase['accepted_at'] == '2026-09-11'
assert cp['prior_prior_phase']['phase_id'] == 'CAREER_OS_AGENT_CONTEXT_AND_USAGE_EFFICIENCY_V1'
assert cp['prior_prior_phase']['human_acceptance_status'] == 'BORA_ACCEPTED'

# Phase D has since been legitimately completed by the operator AND
# explicitly accepted by Bora (a later, separately-locked acceptance
# contract governs that event), and is now preserved as prior_phase since
# Bora has separately, explicitly authorized Phase E as the next phase.
# This authorization-only test must recognize that live progression rather
# than assert Phase D's absence -- but the acceptance must remain a genuine
# Bora human event, never self-granted by the operator, and never an
# implementation authorization.
completed = ' '.join(cp['completed_actions'])
phase_d_reference = ' '.join(cp['phase_d_completed_actions_reference'])
assert 'taxonomy' in phase_d_reference.lower()
assert 'evaluator-coverage map' in phase_d_reference.lower()
assert prior_phase['human_acceptance_status'] == 'BORA_ACCEPTED'
assert cp['implementation_authorized'] is False

# project_state.json must point at Phase E, the live current phase, while
# preserving Phase D's completed/accepted status in the next_authorized_action
# seam text, with no implementation authorized and Phase F still proposed only.
assert PROJECT_STATE['current_phase'].startswith('CAREER_OS_SYSTEM_EVAL_SET_ARCHITECTURE_V1')
assert 'BORA_AUTHORIZED' in PROJECT_STATE['current_phase']
assert 'NOT_YET_COMPLETED' in PROJECT_STATE['current_phase']
assert 'READ_ONLY_DESIGN_ONLY' in PROJECT_STATE['current_phase']
assert 'NO_IMPLEMENTATION_AUTHORIZED' in PROJECT_STATE['current_phase']
assert 'CAREER_OS_FAILURE_TAXONOMY_AND_EVALUATOR_COVERAGE_MAP_V1' in PROJECT_STATE['next_authorized_action']
assert 'COMPLETED_BY_OPERATOR / BORA_ACCEPTED (2026-09-11) / READ_ONLY_DESIGN_ONLY' in PROJECT_STATE['next_authorized_action']
assert PHASE_F_PROPOSED_NOT_AUTHORIZED.search(PROJECT_STATE['next_authorized_action']), (
    "project_state.next_authorized_action must couple Phase F to PROPOSED_NOT_AUTHORIZED as one subject"
)

# CURRENT_MILESTONE.md / CURRENT_STATE.md / AGENTS.md / the eval-harness ADR
# must all agree: the prior policy milestone remains BORA_ACCEPTED/GOVERNING
# and Phase D is COMPLETED_BY_OPERATOR / BORA_ACCEPTED (2026-09-11) /
# READ_ONLY_DESIGN_ONLY, with Phase E and later still PROPOSED_NOT_AUTHORIZED.
for surface_name, surface_text in (
    ('CURRENT_MILESTONE.md', CURRENT_MILESTONE),
    ('CURRENT_STATE.md', CURRENT_STATE),
    ('AGENTS.md', AGENTS),
    ('ADR-CAREER-OS-EVAL-HARNESS-SEQUENCE-V1.md', ADR),
):
    assert 'COMPLETED_BY_OPERATOR / BORA_ACCEPTED (2026-09-11) / GOVERNANCE_ONLY / GOVERNING' in surface_text, (
        f'{surface_name} must preserve the prior policy milestone acceptance unchanged'
    )
    # Deliberately NOT a bare substring check: 'COMPLETED_BY_OPERATOR / BORA_ACCEPTED
    # (2026-09-11)' alone is a prefix of the prior policy milestone's own
    # '... / GOVERNANCE_ONLY / GOVERNING' line above and would pass merely because
    # that unrelated line exists. Require the READ_ONLY_DESIGN_ONLY-suffixed form,
    # which only Phase D's own status line can satisfy, so this proves Phase D's
    # own acceptance specifically, not merely that some accepted milestone exists.
    assert 'COMPLETED_BY_OPERATOR / BORA_ACCEPTED (2026-09-11) / READ_ONLY_DESIGN_ONLY' in surface_text, (
        f'{surface_name} must record Phase D itself (not merely some other accepted '
        f'milestone) as COMPLETED_BY_OPERATOR / BORA_ACCEPTED (2026-09-11) / READ_ONLY_DESIGN_ONLY'
    )
    assert surface_text.count('COMPLETED_BY_OPERATOR / BORA_ACCEPTED (2026-09-11)') >= 2, (
        f'{surface_name} must record both the prior policy milestone acceptance and '
        f'Phase D\'s own distinct acceptance as separate occurrences'
    )
    assert 'implementation_authorized' in surface_text.lower() or 'implementation not authorized' in surface_text.lower() or 'no implementation' in surface_text.lower() or 'NO_IMPLEMENTATION_AUTHORIZED' in surface_text, (
        f'{surface_name} must state that implementation remains unauthorized'
    )
    assert PHASE_F_PROPOSED_NOT_AUTHORIZED.search(surface_text), (
        f'{surface_name} must couple Phase F to PROPOSED_NOT_AUTHORIZED as one subject'
    )

# CHANGELOG.md must record this transition as a distinct dated entry,
# separate from the prior policy-acceptance entry.
assert 'CAREER_OS_FAILURE_TAXONOMY_AND_EVALUATOR_COVERAGE_MAP_V1' in CHANGELOG
assert 'BORA_AUTHORIZED' in CHANGELOG
assert 'authorized by Bora (READ_ONLY / DESIGN_ONLY, BORA_AUTHORIZED' in CHANGELOG
assert 'accepted by Bora (GOVERNANCE-ONLY, BORA ACCEPTED)' in CHANGELOG

# The already-accepted policy ADR itself must be untouched by this sync --
# still governing, without a Phase D re-adjudication inside it.
policy_adr_text = POLICY_ADR_PATH.read_text(encoding='utf-8')
assert 'GOVERNING' in policy_adr_text
assert 'DECISION (BORA_ACCEPTED, GOVERNING):' in policy_adr_text

print('PASS: Career OS Phase D authorization transition verified.')
