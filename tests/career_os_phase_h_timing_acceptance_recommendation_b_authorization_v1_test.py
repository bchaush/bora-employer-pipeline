import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CHECKPOINT = ROOT / 'CURRENT_EXECUTION_CHECKPOINT.json'
CONTRACT = ROOT / 'milestone_contracts' / 'governance' / 'career-os-phase-h-timing-acceptance-recommendation-b-authorization-v1.json'
PROJECT_STATE = json.loads((ROOT / 'project_state.json').read_text(encoding='utf-8'))
AGENTS = (ROOT / 'AGENTS.md').read_text(encoding='utf-8')
CURRENT_MILESTONE = (ROOT / 'CURRENT_MILESTONE.md').read_text(encoding='utf-8')
CURRENT_STATE = (ROOT / 'CURRENT_STATE.md').read_text(encoding='utf-8')
CHANGELOG = (ROOT / 'CHANGELOG.md').read_text(encoding='utf-8')
ADR = (ROOT / 'docs' / 'decisions' / 'ADR-CAREER-OS-EVAL-HARNESS-SEQUENCE-V1.md').read_text(encoding='utf-8')

BASELINE_SHA = '52227f2d2ac913768bc558619f38d507358ebbaa'
REVIEWED_HEAD = 'dc8cde625ec4308a3a9790ad907009684955a3ca'
MERGE_TREE = 'c62db7f169c46c38b8df7dd7618a718e43d1525d'
PHASE_H_ID = 'CAREER_OS_ASSURANCE_TIMING_OBSERVABILITY_V1'
REC_B_ID = 'CAREER_OS_MILESTONE_RUN_V1_TARGETED_OPTIMIZATION_V1'
BORA_QUOTE = (
    'Done brother carry the same discipline and manner and u have my authorization to move forward '
    'ofc if all is up to the standard of the three guys we refer to love u'
)

TIMING_EVIDENCE = {
    'local_run_1': (318.025429, 415.069786),
    'local_run_2': (312.284460, 406.363878),
    'hosted_post_merge_run': (12.904488, 29.252603),
}

PHASE_I_PROPOSED_NOT_AUTHORIZED = re.compile(
    r'Phase I and every later roadmap phase remain \*{0,2}PROPOSED_NOT_AUTHORIZED\*{0,2}',
    re.IGNORECASE,
)
GLOBAL_IMPLEMENTATION_FALSE = re.compile(r'implementation_authorized[^\n.]{0,220}\bfalse\b', re.IGNORECASE)

# --- Governance contract ---------------------------------------------------

assert CONTRACT.exists(), 'Phase H timing acceptance / Recommendation B authorization governance contract missing'
contract = json.loads(CONTRACT.read_text(encoding='utf-8'))
assert contract['milestone_id'] == 'CAREER_OS_PHASE_H_TIMING_ACCEPTANCE_RECOMMENDATION_B_AUTHORIZATION_V1'
assert contract['kind'] == 'GOVERNANCE_SYNC'
assert contract['baseline_sha'] == BASELINE_SHA
assert BORA_QUOTE in contract['goal']
assert PHASE_H_ID in contract['goal']
assert REC_B_ID in contract['goal']
assert 'operator independently verified' in contract['goal']
assert 'RECOMMENDATION_B_AUTHORIZATION_EFFECTIVE_ONLY_BECAUSE_OPERATOR_INDEPENDENTLY_VERIFIED_THE_PHASE_G_EVIDENCE_CONDITION' in contract['human_approval_requirements']
for forbidden_path in (
    'BLUEPRINT.md', 'CLAUDE.md', 'GEMINI.md', '.cursor/**', '.cursorignore', '.claude/**', 'src/**',
    'schemas/**', 'claims/**', 'evidence/**', 'experiences/**', 'resume/**', 'golden-tests/**',
    'fixtures/**', 'config/**', 'prompts/**', 'docs/audits/**', '.github/workflows/**',
    'scripts/verify_assurance_baseline.py', 'scripts/verify_milestone_state.py',
    'tests/milestone_run_v1_test.py',
):
    assert forbidden_path in contract['forbidden_paths'], f'contract must forbid {forbidden_path}'

# --- Checkpoint: canonical merge verification -------------------------------

assert CHECKPOINT.exists(), 'canonical execution checkpoint missing'
cp = json.loads(CHECKPOINT.read_text(encoding='utf-8'))
assert cp['canonical_basis_sha'] == 'e521c7972a345f48379304b3df0e9598bc6326b2'
assert BASELINE_SHA in cp['phase_h_acceptance']['canonical_merge_verification']
assert cp['phase_id'] == REC_B_ID
assert cp['operator_status'] == 'COMPLETED_BY_OPERATOR'
assert cp['human_acceptance_status'] == 'BORA_ACCEPTED'
assert cp['accepted_at'] == '2026-09-15'
assert cp['implementation_authorized'] is False

# --- Checkpoint: Phase H acceptance, distinct fact 1 ------------------------

assert 'phase_h_acceptance' in cp, 'checkpoint must record a distinct phase_h_acceptance object'
phase_h = cp['phase_h_acceptance']
assert phase_h['phase_id'] == PHASE_H_ID
assert phase_h['operator_status'] == 'COMPLETED_BY_OPERATOR'
assert phase_h['human_acceptance_status'] == 'BORA_ACCEPTED'
assert phase_h['accepted_at'] == '2026-09-15'
assert REVIEWED_HEAD in phase_h['canonical_merge_verification']
assert MERGE_TREE in phase_h['canonical_merge_verification']
assert BASELINE_SHA in phase_h['canonical_merge_verification']
assert BORA_QUOTE in phase_h['human_acceptance_event']

# --- Checkpoint: Recommendation B authorization, distinct fact 2 -----------
# Never conflated with fact 1 above -- a separate top-level record.

assert 'recommendation_b_authorization' in cp, 'checkpoint must record a distinct recommendation_b_authorization object'
rec_b = cp['recommendation_b_authorization']
assert rec_b['milestone_id'] == REC_B_ID
assert rec_b['authorization_status'] == 'BORA_AUTHORIZED'
assert rec_b['selection_status'] == 'SELECTED'
assert rec_b['operator_status'] == 'NOT_YET_COMPLETED'
assert rec_b['record_semantics'] == 'HISTORICAL_AUTHORIZATION_SNAPSHOT_SUPERSEDED_BY_RECOMMENDATION_B_COMPLETION'
assert cp['recommendation_b_completion']['operator_status'] == 'COMPLETED_BY_OPERATOR'
assert cp['recommendation_b_completion']['human_acceptance_status'] == 'BORA_ACCEPTED'
assert rec_b['selected_from'] == 'PHASE_G_RECOMMENDATION_B_ONLY'
assert rec_b['implementation_authorization_scope'] == 'SCOPED_TO_THIS_MILESTONE_ONLY_NOT_GLOBAL'
assert 'semantic equivalence to full assurance required to be proven via dedicated regressions' in rec_b['scope_description']
assert 'before any optimization is trusted' in rec_b['scope_description']
assert 'semantic equivalence to full assurance proven via dedicated regressions' not in rec_b['scope_description']
assert 'NOT_AUTHORIZED' in rec_b['recommendation_c_fast_diagnostic_runner']
assert 'Phase I or any later roadmap phase' in rec_b['explicitly_not_authorized']
assert BORA_QUOTE in rec_b['human_authorization_event']
assert 'never self-granted by the operator' in rec_b['human_authorization_event']

timing = rec_b['timing_evidence_threshold']
for run_name, (milestone_seconds, phase2_seconds) in TIMING_EVIDENCE.items():
    assert timing[run_name]['milestone_run_v1_test_py_seconds'] == milestone_seconds
    assert timing[run_name]['phase_2_seconds'] == phase2_seconds
assert 'dominant individual Phase-2 test' in timing['conclusion']

# --- No optimization implementation performed in this sync -----------------

assert 'not_implemented_this_sync' in rec_b
assert 'no optimization' in rec_b['not_implemented_this_sync'].lower()
assert 'tests/milestone_run_v1_test.py mutation' in rec_b['not_implemented_this_sync']

VERIFY_ASSURANCE_SCRIPT = ROOT / 'scripts' / 'verify_assurance_baseline.py'
VERIFY_MILESTONE_STATE_SCRIPT = ROOT / 'scripts' / 'verify_milestone_state.py'
MILESTONE_RUN_TEST = ROOT / 'tests' / 'milestone_run_v1_test.py'
assert VERIFY_ASSURANCE_SCRIPT.exists(), 'canonical assurance script must still exist unmodified'
assert VERIFY_MILESTONE_STATE_SCRIPT.exists(), 'canonical milestone-state verifier must still exist unmodified'
assert MILESTONE_RUN_TEST.exists(), 'milestone_run_v1_test.py must still exist, untouched by this governance sync'

# --- Prior phases (G/F/E) shifted and preserved unchanged; Phase D dropped -

prior_phase = cp['prior_phase']
assert prior_phase['phase_id'] == 'CAREER_OS_ASSURANCE_ARCHITECTURE_V1'
assert prior_phase['operator_status'] == 'COMPLETED_BY_OPERATOR'
assert prior_phase['human_acceptance_status'] == 'BORA_ACCEPTED'
assert prior_phase['accepted_at'] == '2026-09-14'

prior_prior_phase = cp['prior_prior_phase']
assert prior_prior_phase['phase_id'] == 'CAREER_OS_TRACE_AND_CONTRACT_ARCHITECTURE_V1'
assert prior_prior_phase['human_acceptance_status'] == 'BORA_ACCEPTED'
assert prior_prior_phase['accepted_at'] == '2026-09-14'

prior_prior_prior_phase = cp['prior_prior_prior_phase']
assert prior_prior_prior_phase['phase_id'] == 'CAREER_OS_SYSTEM_EVAL_SET_ARCHITECTURE_V1'
assert prior_prior_prior_phase['human_acceptance_status'] == 'BORA_ACCEPTED'
assert prior_prior_prior_phase['accepted_at'] == '2026-09-12'

assert 'phase_d_completed_actions_reference' in cp, (
    "Phase D's substantive work must survive as historical reference after dropping out of the live chain"
)

# --- Global implementation_authorized never flips; Recommendation C and
# Phase I+ remain not authorized -------------------------------------------

not_done = ' '.join(cp['not_completed_or_not_authorized'])
assert 'Recommendation C' in not_done and 'NOT_AUTHORIZED' in not_done
assert PHASE_I_PROPOSED_NOT_AUTHORIZED.search(not_done)
assert REC_B_ID not in not_done
assert cp['recommendation_b_acceptance']['human_acceptance_status'] == 'BORA_ACCEPTED'

completed = ' '.join(cp['phase_h_acceptance_recommendation_b_authorization_completed_actions_reference'])
assert BORA_QUOTE in completed
assert REC_B_ID in completed
assert PHASE_H_ID in completed
for milestone_seconds, phase2_seconds in TIMING_EVIDENCE.values():
    assert str(milestone_seconds) in completed
    assert str(phase2_seconds) in completed

# --- project_state.json -----------------------------------------------------

assert PROJECT_STATE['current_phase'].startswith(PHASE_H_ID)
assert 'BORA_ACCEPTED (2026-09-15)' in PROJECT_STATE['current_phase']
assert REC_B_ID in PROJECT_STATE['current_phase']
assert 'PRIOR_IMPLEMENTATION_AUTHORITY_SCOPED_TO_THIS_MILESTONE_ONLY_NOT_GLOBAL_EXHAUSTED_BY_OPERATOR_COMPLETION' in PROJECT_STATE['current_phase']
assert BORA_QUOTE in PROJECT_STATE['next_authorized_action']
assert 'COMPLETED_BY_OPERATOR; BORA_ACCEPTED (2026-09-15)' in PROJECT_STATE['current_phase']
assert PHASE_I_PROPOSED_NOT_AUTHORIZED.search(PROJECT_STATE['next_authorized_action'])

# --- Every live recovery/state surface agrees -------------------------------

for surface_name, surface_text in (
    ('CURRENT_MILESTONE.md', CURRENT_MILESTONE),
    ('CURRENT_STATE.md', CURRENT_STATE),
    ('AGENTS.md', AGENTS),
    ('ADR-CAREER-OS-EVAL-HARNESS-SEQUENCE-V1.md', ADR),
):
    assert 'COMPLETED_BY_OPERATOR / BORA_ACCEPTED (2026-09-15)' in surface_text, (
        f'{surface_name} must state Phase H is COMPLETED_BY_OPERATOR / BORA_ACCEPTED (2026-09-15)'
    )
    assert REC_B_ID in surface_text, f'{surface_name} must name Recommendation B ({REC_B_ID})'
    assert 'BORA_AUTHORIZED' in surface_text
    assert 'COMPLETED_BY_OPERATOR' in surface_text and 'BORA_ACCEPTED (2026-09-15)' in surface_text
    assert 'SCOPED_TO_THIS_MILESTONE_ONLY_NOT_GLOBAL' in surface_text, (
        f'{surface_name} must state Recommendation B implementation authority is scoped to this milestone only, not global'
    )
    assert PHASE_I_PROPOSED_NOT_AUTHORIZED.search(surface_text), (
        f'{surface_name} must couple Phase I to PROPOSED_NOT_AUTHORIZED'
    )
    assert GLOBAL_IMPLEMENTATION_FALSE.search(surface_text), f'{surface_name} must state implementation_authorized remains false'

# --- Exact timing evidence recorded on at least the checkpoint, project_state,
# CURRENT_MILESTONE.md, and CURRENT_STATE.md ---------------------------------

for surface_name, surface_text in (
    ('CURRENT_MILESTONE.md', CURRENT_MILESTONE),
    ('CURRENT_STATE.md', CURRENT_STATE),
):
    assert '318.025429' in surface_text and '415.069786' in surface_text, (
        f'{surface_name} must record local run 1 timing evidence exactly'
    )
    assert '312.284460' in surface_text and '406.363878' in surface_text, (
        f'{surface_name} must record local run 2 timing evidence exactly'
    )
    assert '12.904488' in surface_text and '29.252603' in surface_text, (
        f'{surface_name} must record the hosted post-merge run timing evidence exactly'
    )

# --- Global implementation_authorized flag never flips to true -------------

assert GLOBAL_IMPLEMENTATION_FALSE.search(PROJECT_STATE['next_authorized_action']), 'project_state next_authorized_action must keep global implementation_authorized false'
assert cp['implementation_authorized'] is False

# --- CHANGELOG.md records two distinct dated sub-entries --------------------

assert BORA_QUOTE in CHANGELOG
_REC_B_HEADING_MARKER = 'Career OS Recommendation B (`CAREER_OS_MILESTONE_RUN_V1_TARGETED_OPTIMIZATION_V1`) authorized by Bora'
_PHASE_H_ACCEPT_HEADING_MARKER = 'Career OS Phase H (`CAREER_OS_ASSURANCE_TIMING_OBSERVABILITY_V1`) accepted by Bora'
assert _REC_B_HEADING_MARKER in CHANGELOG, 'CHANGELOG.md must record a distinct Recommendation B authorization entry'
assert _PHASE_H_ACCEPT_HEADING_MARKER in CHANGELOG, 'CHANGELOG.md must record a distinct Phase H acceptance entry'
_rec_b_pos = CHANGELOG.find(_REC_B_HEADING_MARKER)
_h_accept_pos = CHANGELOG.find(_PHASE_H_ACCEPT_HEADING_MARKER)
assert _rec_b_pos != -1 and _h_accept_pos != -1 and _rec_b_pos != _h_accept_pos, (
    'Phase H acceptance and Recommendation B authorization must be two distinct CHANGELOG entries, never conflated'
)

print('PASS: Career OS Phase H timing acceptance / Recommendation B scoped authorization governance sync verified.')
