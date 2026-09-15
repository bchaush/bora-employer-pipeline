import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CHECKPOINT = ROOT / 'CURRENT_EXECUTION_CHECKPOINT.json'
CONTRACT = ROOT / 'milestone_contracts' / 'governance' / 'career-os-phase-g-acceptance-phase-h-authorization-v1.json'
PROJECT_STATE = json.loads((ROOT / 'project_state.json').read_text(encoding='utf-8'))
AGENTS = (ROOT / 'AGENTS.md').read_text(encoding='utf-8')
CURRENT_MILESTONE = (ROOT / 'CURRENT_MILESTONE.md').read_text(encoding='utf-8')
CURRENT_STATE = (ROOT / 'CURRENT_STATE.md').read_text(encoding='utf-8')
CHANGELOG = (ROOT / 'CHANGELOG.md').read_text(encoding='utf-8')
ADR = (ROOT / 'docs' / 'decisions' / 'ADR-CAREER-OS-EVAL-HARNESS-SEQUENCE-V1.md').read_text(encoding='utf-8')
PHASE_G_REPORT_PATH = ROOT / 'docs' / 'audits' / 'CAREER_OS_ASSURANCE_ARCHITECTURE_V1_REPORT.md'

BASELINE_SHA = 'b48b9a504836a1e502af96f77cd1f6fe947cb604'
PHASE_H_ID = 'CAREER_OS_ASSURANCE_TIMING_OBSERVABILITY_V1'
BORA_QUOTE = (
    'beautiful work G once u cehck everything being up to standart to the three guys we refer to '
    'u have all authorization moving forwrad, please G just mind the usage limits of Cursor and Claude love u bro'
)

PHASE_I_PROPOSED_NOT_AUTHORIZED = re.compile(
    r'Phase I and every later roadmap phase remain \*{0,2}PROPOSED_NOT_AUTHORIZED\*{0,2}',
    re.IGNORECASE,
)

RECOMMENDATIONS_B_C_NOT_AUTHORIZED = re.compile(
    r'Recommendation B\b[^\n]*?Recommendation C\b[^\n]*?remain \*{0,2}NOT_AUTHORIZED\*{0,2}',
    re.IGNORECASE,
)

# --- Governance contract ---------------------------------------------------

assert CONTRACT.exists(), 'Phase G acceptance / Phase H authorization governance contract missing'
contract = json.loads(CONTRACT.read_text(encoding='utf-8'))
assert contract['milestone_id'] == 'CAREER_OS_PHASE_G_ACCEPTANCE_PHASE_H_AUTHORIZATION_V1'
assert contract['kind'] == 'GOVERNANCE_SYNC'
assert contract['baseline_sha'] == BASELINE_SHA
assert BORA_QUOTE in contract['goal']
assert PHASE_H_ID in contract['goal']
assert 'never self-granted by the operator' in contract['goal']
assert 'RECOMMENDATION A' in contract['goal'].upper()
for forbidden_path in (
    'BLUEPRINT.md', 'CLAUDE.md', 'GEMINI.md', '.cursor/**', '.cursorignore', '.claude/**', 'src/**',
    'schemas/**', 'claims/**', 'evidence/**', 'experiences/**', 'resume/**', 'golden-tests/**',
    'fixtures/**', 'config/**', 'prompts/**', 'docs/audits/**',
    'scripts/verify_assurance_baseline.py', '.github/workflows/**',
):
    assert forbidden_path in contract['forbidden_paths'], f'contract must forbid {forbidden_path}'

# --- Checkpoint: Phase G acceptance -----------------------------------------

assert CHECKPOINT.exists(), 'canonical execution checkpoint missing'
cp = json.loads(CHECKPOINT.read_text(encoding='utf-8'))
assert cp['canonical_basis_sha'] == BASELINE_SHA
assert cp['phase_id'] == 'CAREER_OS_ASSURANCE_ARCHITECTURE_V1'
assert cp['operator_status'] == 'COMPLETED_BY_OPERATOR'
assert cp['human_acceptance_status'] == 'BORA_ACCEPTED'
assert cp['accepted_at'] == '2026-09-14'
# The global implementation_authorized flag never flips to true from this
# sync -- the scoped Phase H grant lives only in its own distinct record.
assert cp['implementation_authorized'] is False

# --- Checkpoint: Phase H authorization, scoped only -------------------------

assert 'phase_h_authorization' in cp, 'checkpoint must record a distinct phase_h_authorization object'
phase_h = cp['phase_h_authorization']
assert phase_h['phase_id'] == PHASE_H_ID
assert phase_h['authorization_status'] == 'BORA_AUTHORIZED'
assert phase_h['selection_status'] == 'SELECTED'
assert phase_h['operator_status'] == 'NOT_YET_COMPLETED'
assert phase_h['selected_from'] == 'PHASE_G_RECOMMENDATION_A_TIMING_OBSERVABILITY_ONLY'
assert phase_h['implementation_authorization_scope'] == 'SCOPED_TO_THIS_MILESTONE_ONLY_NOT_GLOBAL'
assert 'NOT_AUTHORIZED' in phase_h['recommendation_b_milestone_run_optimization']
assert 'NOT_AUTHORIZED' in phase_h['recommendation_c_fast_diagnostic_runner']
assert 'Phase I or any later roadmap phase' in phase_h['explicitly_not_authorized']
assert BORA_QUOTE in phase_h['human_authorization_event']
assert 'never self-granted by the operator' in phase_h['human_authorization_event']

# --- Recommendation B/C explicitly not authorized, no implementation done --

completed = ' '.join(cp['completed_actions'])
assert BORA_QUOTE in completed
assert 'Recommendation B' in completed and 'NOT AUTHORIZE' in completed.upper()
assert 'Recommendation C' in completed
assert 'no timing-instrumentation code' in completed
assert 'no scripts/verify_assurance_baseline.py edit' in completed

not_done = ' '.join(cp['not_completed_or_not_authorized'])
assert PHASE_I_PROPOSED_NOT_AUTHORIZED.search(not_done), (
    'checkpoint not_completed_or_not_authorized must couple Phase I to PROPOSED_NOT_AUTHORIZED'
)
assert ('scoped exclusively to CAREER_OS_ASSURANCE_TIMING_OBSERVABILITY_V1' in not_done or 'never a blanket/global implementation grant' in not_done), 'narrative must preserve the scoped-not-global Phase H boundary'
assert 'NOT_AUTHORIZED' in not_done

# --- Prior phases (F/E/D) preserved unchanged, in their own distinct slots -

for slot, phase_id, accepted_at in (
    ('prior_phase', 'CAREER_OS_TRACE_AND_CONTRACT_ARCHITECTURE_V1', '2026-09-14'),
    ('prior_prior_phase', 'CAREER_OS_SYSTEM_EVAL_SET_ARCHITECTURE_V1', '2026-09-12'),
    ('prior_prior_prior_phase', 'CAREER_OS_FAILURE_TAXONOMY_AND_EVALUATOR_COVERAGE_MAP_V1', '2026-09-11'),
):
    record = cp[slot]
    assert record['phase_id'] == phase_id
    assert record['operator_status'] == 'COMPLETED_BY_OPERATOR'
    assert record['human_acceptance_status'] == 'BORA_ACCEPTED'
    assert record['accepted_at'] == accepted_at

# --- Phase G's substantive report preserved unchanged -----------------------

assert PHASE_G_REPORT_PATH.exists(), 'substantive Phase G assurance architecture report missing'

# --- project_state.json ------------------------------------------------------

assert PROJECT_STATE['current_phase'].startswith('CAREER_OS_ASSURANCE_ARCHITECTURE_V1')
assert 'BORA_ACCEPTED (2026-09-14)' in PROJECT_STATE['current_phase']
assert PHASE_H_ID in PROJECT_STATE['current_phase']
assert 'SCOPED_TO_THIS_MILESTONE_ONLY_NOT_GLOBAL' in PROJECT_STATE['current_phase']
assert PHASE_I_PROPOSED_NOT_AUTHORIZED.search(PROJECT_STATE['next_authorized_action']), (
    'project_state.next_authorized_action must couple Phase I to PROPOSED_NOT_AUTHORIZED'
)
assert BORA_QUOTE in PROJECT_STATE['next_authorized_action']

# --- Every live recovery/state surface agrees ------------------------------

for surface_name, surface_text in (
    ('CURRENT_MILESTONE.md', CURRENT_MILESTONE),
    ('CURRENT_STATE.md', CURRENT_STATE),
    ('AGENTS.md', AGENTS),
    ('ADR-CAREER-OS-EVAL-HARNESS-SEQUENCE-V1.md', ADR),
):
    assert 'COMPLETED_BY_OPERATOR / BORA_ACCEPTED (2026-09-14) / READ_ONLY_DESIGN_ONLY' in surface_text, (
        f'{surface_name} must state Phase G is COMPLETED_BY_OPERATOR / BORA_ACCEPTED (2026-09-14) / READ_ONLY_DESIGN_ONLY'
    )
    assert PHASE_H_ID in surface_text, f'{surface_name} must name Phase H ({PHASE_H_ID})'
    assert 'BORA_AUTHORIZED' in surface_text and 'NOT_YET_COMPLETED' in surface_text
    assert 'SCOPED_TO_THIS_MILESTONE_ONLY_NOT_GLOBAL' in surface_text, (
        f'{surface_name} must state Phase H implementation authority is scoped to this milestone only, not global'
    )
    assert PHASE_I_PROPOSED_NOT_AUTHORIZED.search(surface_text), (
        f'{surface_name} must couple Phase I to PROPOSED_NOT_AUTHORIZED'
    )

# Recommendation B and C must be explicitly not-authorized on every surface
# that discusses Phase H's scope (not required on every surface verbatim,
# but at least the checkpoint, ADR, and CURRENT_MILESTONE/CURRENT_STATE).
for surface_name, surface_text in (
    ('CURRENT_MILESTONE.md', CURRENT_MILESTONE),
    ('CURRENT_STATE.md', CURRENT_STATE),
    ('ADR-CAREER-OS-EVAL-HARNESS-SEQUENCE-V1.md', ADR),
):
    assert RECOMMENDATIONS_B_C_NOT_AUTHORIZED.search(surface_text), (
        f'{surface_name} must couple Recommendation B and Recommendation C to NOT_AUTHORIZED in one bounded statement'
    )

# --- No Phase H implementation performed in this sync -----------------------

VERIFY_ASSURANCE_SCRIPT = ROOT / 'scripts' / 'verify_assurance_baseline.py'
assert VERIFY_ASSURANCE_SCRIPT.exists(), 'canonical assurance script must still exist unmodified'
WORKFLOWS_DIR = ROOT / '.github' / 'workflows'
# This sync must not have touched CI workflow files; existence/non-existence
# is not asserted here (out of this contract's allowed_paths either way),
# only that this test file itself never edits them.
assert 'not_implemented_this_sync' in phase_h
assert 'no timing-instrumentation code' in phase_h['not_implemented_this_sync']

# --- CHANGELOG.md records two distinct dated sub-entries --------------------

assert BORA_QUOTE in CHANGELOG
_PHASE_H_HEADING_MARKER = 'Career OS Phase H (`CAREER_OS_ASSURANCE_TIMING_OBSERVABILITY_V1`) authorized by Bora'
_PHASE_G_ACCEPT_HEADING_MARKER = 'Career OS Phase G (`CAREER_OS_ASSURANCE_ARCHITECTURE_V1`) accepted by Bora'
assert _PHASE_H_HEADING_MARKER in CHANGELOG, 'CHANGELOG.md must record a distinct Phase H authorization entry'
assert _PHASE_G_ACCEPT_HEADING_MARKER in CHANGELOG, 'CHANGELOG.md must record a distinct Phase G acceptance entry'
_h_pos = CHANGELOG.find(_PHASE_H_HEADING_MARKER)
_g_accept_pos = CHANGELOG.find(_PHASE_G_ACCEPT_HEADING_MARKER)
assert _h_pos != -1 and _g_accept_pos != -1 and _h_pos != _g_accept_pos, (
    'Phase G acceptance and Phase H authorization must be two distinct CHANGELOG entries, never conflated'
)

print('PASS: Career OS Phase G acceptance / Phase H scoped authorization governance sync verified.')
