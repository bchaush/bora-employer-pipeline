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

# This test records the historical Phase G acceptance / Phase H scoped
# authorization event (2026-09-14). Phase H has since been itself accepted
# and Recommendation B separately authorized (2026-09-15, see
# career_os_phase_h_timing_acceptance_recommendation_b_authorization_v1_test.py);
# this file continues to verify that the 2026-09-14 event's substance was
# genuinely recorded and is preserved unchanged, even though the checkpoint's
# top-level "live current phase" fields have since moved on to Phase H.

PHASE_I_PROPOSED_NOT_AUTHORIZED = re.compile(
    r'Phase I and every later roadmap phase remain \*{0,2}PROPOSED_NOT_AUTHORIZED\*{0,2}',
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

# --- Checkpoint: Phase G acceptance, preserved as prior_phase --------------
# (Phase G's own record has moved from the checkpoint's top-level fields into
# prior_phase now that Phase H has itself been accepted -- this is the
# expected live-current-pointer shift, not a loss of the underlying fact.)

assert CHECKPOINT.exists(), 'canonical execution checkpoint missing'
cp = json.loads(CHECKPOINT.read_text(encoding='utf-8'))
prior_phase = cp['prior_phase']
assert prior_phase['phase_id'] == 'CAREER_OS_ASSURANCE_ARCHITECTURE_V1'
assert prior_phase['operator_status'] == 'COMPLETED_BY_OPERATOR'
assert prior_phase['human_acceptance_status'] == 'BORA_ACCEPTED'
assert prior_phase['accepted_at'] == '2026-09-14'

# --- Checkpoint: Phase H's own acceptance record preserves its original
# scoped-authorization substance (selected_from, scope) unchanged, even
# though operator_status/human_acceptance_status have since progressed from
# NOT_YET_COMPLETED to COMPLETED_BY_OPERATOR / BORA_ACCEPTED. -----------------

assert 'phase_h_acceptance' in cp, 'checkpoint must record a distinct phase_h_acceptance object'
phase_h = cp['phase_h_acceptance']
assert phase_h['phase_id'] == PHASE_H_ID
assert phase_h['authorization_status'] == 'BORA_AUTHORIZED'
assert phase_h['selection_status'] == 'SELECTED'
assert phase_h['selected_from'] == 'PHASE_G_RECOMMENDATION_A_TIMING_OBSERVABILITY_ONLY'
assert phase_h['implementation_authorization_scope'] == 'SCOPED_TO_THIS_MILESTONE_ONLY_NOT_GLOBAL'

# --- The original Phase G acceptance / Phase H authorization sync's own
# completed_actions / not_completed_or_not_authorized narrative is preserved
# unchanged in dedicated historical reference arrays. -----------------------

assert 'phase_g_acceptance_phase_h_authorization_completed_actions_reference' in cp
completed_reference = ' '.join(cp['phase_g_acceptance_phase_h_authorization_completed_actions_reference'])
assert BORA_QUOTE in completed_reference
assert 'Recommendation B' in completed_reference and 'NOT AUTHORIZE' in completed_reference.upper()
assert 'Recommendation C' in completed_reference
assert 'no timing-instrumentation code' in completed_reference
assert 'no scripts/verify_assurance_baseline.py edit' in completed_reference

assert 'phase_g_acceptance_phase_h_authorization_not_completed_or_not_authorized_reference' in cp
not_done_reference = ' '.join(cp['phase_g_acceptance_phase_h_authorization_not_completed_or_not_authorized_reference'])
assert PHASE_I_PROPOSED_NOT_AUTHORIZED.search(not_done_reference), (
    'preserved historical not_completed_or_not_authorized reference must couple Phase I to PROPOSED_NOT_AUTHORIZED'
)
assert 'scoped exclusively to CAREER_OS_ASSURANCE_TIMING_OBSERVABILITY_V1' in not_done_reference
assert 'NOT_AUTHORIZED' in not_done_reference

# --- Prior phases (F/E/D) preserved unchanged, in their own distinct slots -
# (Phase F/E have themselves shifted one slot further down the chain since
# Phase H's own acceptance; Phase D has dropped out of the live three-slot
# chain entirely, exactly as Phase C did before it, and is preserved only as
# historical reference -- this is the expected live-pointer progression.)

for slot, phase_id, accepted_at in (
    ('prior_prior_phase', 'CAREER_OS_TRACE_AND_CONTRACT_ARCHITECTURE_V1', '2026-09-14'),
    ('prior_prior_prior_phase', 'CAREER_OS_SYSTEM_EVAL_SET_ARCHITECTURE_V1', '2026-09-12'),
):
    record = cp[slot]
    assert record['phase_id'] == phase_id
    assert record['operator_status'] == 'COMPLETED_BY_OPERATOR'
    assert record['human_acceptance_status'] == 'BORA_ACCEPTED'
    assert record['accepted_at'] == accepted_at

assert 'phase_d_completed_actions_reference' in cp, (
    "Phase D's substantive work must survive as historical reference even after dropping out of the live chain"
)

# --- Phase G's substantive report preserved unchanged -----------------------

assert PHASE_G_REPORT_PATH.exists(), 'substantive Phase G assurance architecture report missing'

# --- project_state.json: Phase G's own record preserved as historical text -

assert 'BORA_ACCEPTED (2026-09-14)' in PROJECT_STATE['next_authorized_action']
assert PHASE_H_ID in PROJECT_STATE['next_authorized_action'] or PHASE_H_ID in PROJECT_STATE['current_phase']

# --- Every live recovery/state surface still carries the preserved,
# historical Phase G acceptance / Phase H authorization record -------------

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
    assert PHASE_I_PROPOSED_NOT_AUTHORIZED.search(surface_text), (
        f'{surface_name} must couple Phase I to PROPOSED_NOT_AUTHORIZED'
    )

# --- No Phase H implementation performed in the ORIGINAL 2026-09-14 sync ---
# (Phase H's substantive implementation was authored later, under its own
# separate, later-dated milestone contract and PR #61 -- never inside this
# 2026-09-14 governance-only sync.)

VERIFY_ASSURANCE_SCRIPT = ROOT / 'scripts' / 'verify_assurance_baseline.py'
assert VERIFY_ASSURANCE_SCRIPT.exists(), 'canonical assurance script must still exist unmodified'
assert 'no timing-instrumentation code' in completed_reference

# --- CHANGELOG.md preserves the two distinct dated sub-entries -------------

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

print('PASS: Career OS Phase G acceptance / Phase H scoped authorization governance sync verified (preserved as historical record).')
