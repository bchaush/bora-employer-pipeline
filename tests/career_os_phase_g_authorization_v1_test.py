import json
import re
from pathlib import Path

PHASE_H_PROPOSED_NOT_AUTHORIZED = re.compile(
    r'Phase H and every later roadmap phase remain \*{0,2}PROPOSED_NOT_AUTHORIZED\*{0,2}',
    re.IGNORECASE,
)
# Phase H is now BORA_AUTHORIZED (scoped to CAREER_OS_ASSURANCE_TIMING_OBSERVABILITY_V1
# only); live state surfaces now couple Phase I, not Phase H, to PROPOSED_NOT_AUTHORIZED.
PHASE_I_PROPOSED_NOT_AUTHORIZED = re.compile(
    r'Phase I and every later roadmap phase remain \*{0,2}PROPOSED_NOT_AUTHORIZED\*{0,2}',
    re.IGNORECASE,
)

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / 'milestone_contracts' / 'governance' / 'career-os-phase-g-authorization-v1.json'
CHECKPOINT = ROOT / 'CURRENT_EXECUTION_CHECKPOINT.json'
PROJECT_STATE = json.loads((ROOT / 'project_state.json').read_text(encoding='utf-8'))
AGENTS = (ROOT / 'AGENTS.md').read_text(encoding='utf-8')
CURRENT_MILESTONE = (ROOT / 'CURRENT_MILESTONE.md').read_text(encoding='utf-8')
CURRENT_STATE = (ROOT / 'CURRENT_STATE.md').read_text(encoding='utf-8')
CHANGELOG = (ROOT / 'CHANGELOG.md').read_text(encoding='utf-8')
ADR = (ROOT / 'docs' / 'decisions' / 'ADR-CAREER-OS-EVAL-HARNESS-SEQUENCE-V1.md').read_text(encoding='utf-8')
PHASE_D_REPORT_PATH = ROOT / 'docs' / 'audits' / 'CAREER_OS_FAILURE_TAXONOMY_AND_EVALUATOR_COVERAGE_MAP_V1_REPORT.md'
PHASE_E_REPORT_PATH = ROOT / 'docs' / 'audits' / 'CAREER_OS_SYSTEM_EVAL_SET_ARCHITECTURE_V1_REPORT.md'
PHASE_F_REPORT_PATH = ROOT / 'docs' / 'audits' / 'CAREER_OS_TRACE_AND_CONTRACT_ARCHITECTURE_V1_REPORT.md'

BASELINE_SHA = 'e199623c73b08e986beb32437e65f40a5b63b435'

BORA_QUOTE_CONDITIONAL = 'once we are proper to standard and all u have my absolute authorization to start the next phase G'
BORA_QUOTE_CONFIRMATION = 'done G lets keep going brother we got this beautiful work we are doing here'

assert CONTRACT.exists(), 'Phase G authorization governance milestone contract missing'
contract = json.loads(CONTRACT.read_text(encoding='utf-8'))
assert contract['milestone_id'] == 'CAREER_OS_PHASE_G_AUTHORIZATION_V1'
assert contract['kind'] == 'GOVERNANCE_SYNC'
assert contract['baseline_sha'] == BASELINE_SHA
for forbidden_path in (
    'BLUEPRINT.md', 'CLAUDE.md', 'GEMINI.md', '.cursor/**', '.cursorignore', '.claude/**', 'src/**',
    'schemas/**', 'claims/**', 'evidence/**', 'experiences/**', 'resume/**', 'golden-tests/**',
    'fixtures/**', 'config/**', 'prompts/**', 'docs/audits/**',
):
    assert forbidden_path in contract['forbidden_paths'], f'contract must forbid {forbidden_path}'
assert 'CURRENT_EXECUTION_CHECKPOINT.json' in contract['allowed_paths']
assert 'project_state.json' in contract['allowed_paths']
assert BORA_QUOTE_CONDITIONAL in contract['goal']
assert BORA_QUOTE_CONFIRMATION in contract['goal']
assert 'never self-granted by the operator' in contract['goal']

# This governance sync must not touch the already-accepted Phase D/E/F reports --
# it records only the Phase G authorization transition. The Phase G substantive
# design report itself is a SEPARATE, future, dedicated deliverable.
assert PHASE_D_REPORT_PATH.exists()
assert PHASE_E_REPORT_PATH.exists()
assert PHASE_F_REPORT_PATH.exists(), 'substantive Phase F report missing'

# Live checkpoint must record Phase G's fresh authorization while preserving
# Phase F/E/D each in their own distinct, shifted-down slot.
assert CHECKPOINT.exists(), 'canonical execution checkpoint missing'
cp = json.loads(CHECKPOINT.read_text(encoding='utf-8'))
assert cp['checkpoint_id'] == 'CAREER_OS_CHECKPOINT_2026-09-14_PHASE_G_ACCEPTANCE_PHASE_H_AUTHORIZATION', (
    "checkpoint_id must reflect Phase G's acceptance and Phase H's scoped authorization, "
    "the state that superseded this test's original Phase-G-operator-completion checkpoint_id"
)
assert cp['canonical_basis_sha'] == 'b48b9a504836a1e502af96f77cd1f6fe947cb604'
assert cp['phase_id'] == 'CAREER_OS_ASSURANCE_ARCHITECTURE_V1'
assert cp['phase_mode'] == 'READ_ONLY_DESIGN_ONLY'
assert cp['authorization_status'] == 'BORA_AUTHORIZED'
assert cp['selection_status'] == 'SELECTED'
assert cp['operator_status'] == 'COMPLETED_BY_OPERATOR'
# Phase G has since been Bora-accepted (a later, distinct governance sync);
# this authorization-era test now checks that the acceptance is recorded
# consistently rather than asserting the stale PENDING_BORA_ACCEPTANCE value.
assert cp['human_acceptance_status'] == 'BORA_ACCEPTED'
assert cp['accepted_at'] == '2026-09-14'
assert cp['implementation_authorized'] is False

phase_h = cp['phase_h_authorization']
assert phase_h['phase_id'] == 'CAREER_OS_ASSURANCE_TIMING_OBSERVABILITY_V1'
assert phase_h['authorization_status'] == 'BORA_AUTHORIZED'
assert phase_h['selection_status'] == 'SELECTED'
assert phase_h['operator_status'] == 'NOT_YET_COMPLETED'
assert phase_h['implementation_authorization_scope'] == 'SCOPED_TO_THIS_MILESTONE_ONLY_NOT_GLOBAL'

prior_phase = cp['prior_phase']
assert prior_phase['phase_id'] == 'CAREER_OS_TRACE_AND_CONTRACT_ARCHITECTURE_V1'
assert prior_phase['phase_mode'] == 'READ_ONLY_DESIGN_ONLY'
assert prior_phase['operator_status'] == 'COMPLETED_BY_OPERATOR'
assert prior_phase['human_acceptance_status'] == 'BORA_ACCEPTED'
assert prior_phase['accepted_at'] == '2026-09-14'

prior_prior_phase = cp['prior_prior_phase']
assert prior_prior_phase['phase_id'] == 'CAREER_OS_SYSTEM_EVAL_SET_ARCHITECTURE_V1'
assert prior_prior_phase['human_acceptance_status'] == 'BORA_ACCEPTED'
assert prior_prior_phase['accepted_at'] == '2026-09-12'

prior_prior_prior_phase = cp['prior_prior_prior_phase']
assert prior_prior_prior_phase['phase_id'] == 'CAREER_OS_FAILURE_TAXONOMY_AND_EVALUATOR_COVERAGE_MAP_V1'
assert prior_prior_prior_phase['human_acceptance_status'] == 'BORA_ACCEPTED'
assert prior_prior_prior_phase['accepted_at'] == '2026-09-11'

# Phase H is now BORA_AUTHORIZED (scoped, not global) rather than
# PROPOSED_NOT_AUTHORIZED; the checkpoint's live narrative fields must
# instead couple Phase I to PROPOSED_NOT_AUTHORIZED, and must state Phase
# H's scoped, non-global authorization explicitly.
assert PHASE_I_PROPOSED_NOT_AUTHORIZED.search(cp['terminal_adjudication']), (
    'checkpoint terminal_adjudication must couple Phase I to PROPOSED_NOT_AUTHORIZED'
)
_not_done_joined = ' '.join(cp['not_completed_or_not_authorized'])
assert 'SCOPED_TO_THIS_MILESTONE_ONLY_NOT_GLOBAL' in cp['exact_next_allowed_action']
assert PHASE_I_PROPOSED_NOT_AUTHORIZED.search(cp['continuity_rule']), (
    'checkpoint continuity_rule must couple Phase I to PROPOSED_NOT_AUTHORIZED'
)
assert PHASE_I_PROPOSED_NOT_AUTHORIZED.search(cp['exact_next_allowed_action']), (
    'checkpoint exact_next_allowed_action must couple Phase I to PROPOSED_NOT_AUTHORIZED'
)
assert 'CAREER_OS_ASSURANCE_TIMING_OBSERVABILITY_V1' in cp['exact_next_allowed_action']

completed = ' '.join(cp['completed_actions'])
assert BORA_QUOTE_CONDITIONAL in completed
assert BORA_QUOTE_CONFIRMATION in completed
assert 'CAREER_OS_ASSURANCE_ARCHITECTURE_V1' in completed
assert 'never self-granted by the operator' in completed
_historical_phase_g_proposed = [
    _entry for _entry in cp['completed_actions']
    if 'Phase G and every later roadmap phase remained PROPOSED_NOT_AUTHORIZED' in _entry
]
assert len(_historical_phase_g_proposed) == 2, (
    'exactly two historical Phase-F-era completed_actions entries should record Phase G as then-PROPOSED'
)
for _entry in _historical_phase_g_proposed:
    assert 'before Phase G authorization' in _entry, (
        'historical completed_actions Phase-G-PROPOSED claim must be explicitly time-bounded before Phase G authorization'
    )

# Phase F's own substantive narrative (already recorded before this sync) must
# remain present in completed_actions, since this authorization sync appends
# to -- rather than overwrites -- the live progress record.
assert 'CAREER_OS_RUN_TRACE_V1' in completed
assert 'first_causal_failure_point' in completed
assert 'human-handoff' in completed.lower()

# project_state.json must now point at Phase G as Bora-accepted, with Phase H
# BORA_AUTHORIZED (scoped) and Phase I/later still proposed only.
assert PROJECT_STATE['current_phase'].startswith('CAREER_OS_ASSURANCE_ARCHITECTURE_V1')
assert 'BORA_ACCEPTED (2026-09-14)' in PROJECT_STATE['current_phase']
assert 'READ_ONLY_DESIGN_ONLY' in PROJECT_STATE['current_phase']
assert 'CAREER_OS_ASSURANCE_TIMING_OBSERVABILITY_V1' in PROJECT_STATE['current_phase']
assert 'SCOPED_TO_THIS_MILESTONE_ONLY_NOT_GLOBAL' in PROJECT_STATE['current_phase']
assert 'CAREER_OS_TRACE_AND_CONTRACT_ARCHITECTURE_V1' in PROJECT_STATE['next_authorized_action']
assert 'COMPLETED_BY_OPERATOR / BORA_ACCEPTED (2026-09-14) / READ_ONLY_DESIGN_ONLY' in PROJECT_STATE['next_authorized_action']
assert PHASE_I_PROPOSED_NOT_AUTHORIZED.search(PROJECT_STATE['next_authorized_action']), (
    'project_state.next_authorized_action must couple Phase I to PROPOSED_NOT_AUTHORIZED'
)
assert 'SCOPED_TO_THIS_MILESTONE_ONLY_NOT_GLOBAL' in PROJECT_STATE['next_authorized_action']

# Every live recovery/state surface must agree: Phase G is COMPLETED_BY_OPERATOR /
# BORA_ACCEPTED (2026-09-14) / READ_ONLY_DESIGN_ONLY, Phase F remains BORA_ACCEPTED
# (2026-09-14) as prior_phase, Phase H is BORA_AUTHORIZED and scoped, and Phase
# I/later remain PROPOSED_NOT_AUTHORIZED.
for surface_name, surface_text in (
    ('CURRENT_MILESTONE.md', CURRENT_MILESTONE),
    ('CURRENT_STATE.md', CURRENT_STATE),
    ('AGENTS.md', AGENTS),
    ('ADR-CAREER-OS-EVAL-HARNESS-SEQUENCE-V1.md', ADR),
):
    assert 'CAREER_OS_ASSURANCE_ARCHITECTURE_V1' in surface_text, (
        f'{surface_name} must name Phase G (CAREER_OS_ASSURANCE_ARCHITECTURE_V1)'
    )
    assert 'COMPLETED_BY_OPERATOR / BORA_ACCEPTED (2026-09-14) / READ_ONLY_DESIGN_ONLY' in surface_text, (
        f'{surface_name} must state Phase G\'s own coupled state as '
        f'COMPLETED_BY_OPERATOR / BORA_ACCEPTED (2026-09-14) / READ_ONLY_DESIGN_ONLY'
    )
    assert 'CAREER_OS_ASSURANCE_TIMING_OBSERVABILITY_V1' in surface_text, (
        f'{surface_name} must name Phase H (CAREER_OS_ASSURANCE_TIMING_OBSERVABILITY_V1)'
    )
    assert 'SCOPED_TO_THIS_MILESTONE_ONLY_NOT_GLOBAL' in surface_text, (
        f'{surface_name} must state Phase H implementation authority is scoped, not global'
    )
    assert PHASE_I_PROPOSED_NOT_AUTHORIZED.search(surface_text), (
        f'{surface_name} must couple Phase I to PROPOSED_NOT_AUTHORIZED'
    )

# CHANGELOG.md must record Bora's exact two statements as a distinct dated
# entry, separate from the Phase F acceptance entry.
assert 'CAREER_OS_ASSURANCE_ARCHITECTURE_V1' in CHANGELOG
assert BORA_QUOTE_CONDITIONAL in CHANGELOG
assert BORA_QUOTE_CONFIRMATION in CHANGELOG
assert (
    '## 2026-09-14 — Career OS Phase G (`CAREER_OS_ASSURANCE_ARCHITECTURE_V1`) authorized by Bora '
    '(READ_ONLY / DESIGN_ONLY, BORA_AUTHORIZED — historical, superseded by the operator-completion entry above)'
) in CHANGELOG
_PHASE_G_HEADING = (
    '## 2026-09-14 — Career OS Phase G (`CAREER_OS_ASSURANCE_ARCHITECTURE_V1`) authorized by Bora '
    '(READ_ONLY / DESIGN_ONLY, BORA_AUTHORIZED — historical, superseded by the operator-completion entry above)'
)
_g_start = CHANGELOG.index(_PHASE_G_HEADING)
_g_next = CHANGELOG.find('\n## ', _g_start + len(_PHASE_G_HEADING))
_g_block = CHANGELOG[_g_start:_g_next if _g_next != -1 else len(CHANGELOG)]
assert BORA_QUOTE_CONDITIONAL in _g_block
assert BORA_QUOTE_CONFIRMATION in _g_block
assert 'never self-granted by the operator' in _g_block

# The already-accepted Phase D/E reports must be untouched by this sync --
# their substance is not re-adjudicated.
phase_d_report_text = PHASE_D_REPORT_PATH.read_text(encoding='utf-8')
for family in (
    'LIVE_OPPORTUNITY_ACTIONABILITY_IDENTITY_ROUTE_FAILURE',
    'PACKAGE_SPAWN_AND_CANDIDATE_ARTIFACT_QUALITY_FAILURE',
    'CONTROLLER_REVIEWER_EVIDENCE_INTEGRITY_FAILURE',
    'PROVIDER_SESSION_TRANSPORT_RECOVERABILITY_FAILURE',
    'APPLICATION_LIFECYCLE_DUPLICATE_CONTINUITY_FAILURE',
    'SEMANTIC_CONTRACT_ARCHITECTURE_FIDELITY_FAILURE',
):
    assert family in phase_d_report_text, f'Phase D report must still name failure family {family}'

phase_e_report_text = PHASE_E_REPORT_PATH.read_text(encoding='utf-8')
for case_id in ('F1-A', 'F1-D', 'F1-E', 'F2-A', 'F3-A', 'F4-A', 'F5-A', 'REC-A', 'POS-A', 'POS-B'):
    assert case_id in phase_e_report_text, f'Phase E report must still name admitted case {case_id}'

# Phase G's own substantive design deliverable (a separate, later, dedicated
# artifact from this authorization-only governance sync) must now exist and
# record the operator-completed state.
PHASE_G_REPORT_PATH = ROOT / 'docs' / 'audits' / 'CAREER_OS_ASSURANCE_ARCHITECTURE_V1_REPORT.md'
PHASE_G_DESIGN_CONTRACT_PATH = ROOT / 'milestone_contracts' / 'design' / 'career-os-phase-g-assurance-architecture-v1.json'
assert PHASE_G_REPORT_PATH.exists(), 'substantive Phase G assurance architecture report missing'
assert PHASE_G_DESIGN_CONTRACT_PATH.exists(), 'Phase G design milestone contract missing'
assert 'COMPLETED_BY_OPERATOR / PENDING_BORA_ACCEPTANCE / READ_ONLY_DESIGN_ONLY' in completed

print('PASS: Career OS Phase G authorization governance sync verified.')
