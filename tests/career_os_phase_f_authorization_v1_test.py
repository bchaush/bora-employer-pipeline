import json
import re
from pathlib import Path

# Requires the exact subject-coupled phrase "Phase G and every later roadmap
# phase remain PROPOSED_NOT_AUTHORIZED" as one contiguous subject, so this can
# never be satisfied by two unrelated, independently true substrings (e.g. a
# bare "Phase G" mention somewhere and an unrelated PROPOSED_NOT_AUTHORIZED
# elsewhere). Markdown bold is allowed around PROPOSED_NOT_AUTHORIZED only
# where the surface actually renders it that way.
PHASE_G_PROPOSED_NOT_AUTHORIZED = re.compile(
    r'Phase G and every later roadmap phase remain \*{0,2}PROPOSED_NOT_AUTHORIZED\*{0,2}',
    re.IGNORECASE,
)

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / 'milestone_contracts' / 'governance' / 'career-os-phase-f-authorization-v1.json'
CHECKPOINT = ROOT / 'CURRENT_EXECUTION_CHECKPOINT.json'
PROJECT_STATE = json.loads((ROOT / 'project_state.json').read_text(encoding='utf-8'))
AGENTS = (ROOT / 'AGENTS.md').read_text(encoding='utf-8')
CURRENT_MILESTONE = (ROOT / 'CURRENT_MILESTONE.md').read_text(encoding='utf-8')
CURRENT_STATE = (ROOT / 'CURRENT_STATE.md').read_text(encoding='utf-8')
CHANGELOG = (ROOT / 'CHANGELOG.md').read_text(encoding='utf-8')
ADR = (ROOT / 'docs' / 'decisions' / 'ADR-CAREER-OS-EVAL-HARNESS-SEQUENCE-V1.md').read_text(encoding='utf-8')
PHASE_D_REPORT_PATH = ROOT / 'docs' / 'audits' / 'CAREER_OS_FAILURE_TAXONOMY_AND_EVALUATOR_COVERAGE_MAP_V1_REPORT.md'
PHASE_E_REPORT_PATH = ROOT / 'docs' / 'audits' / 'CAREER_OS_SYSTEM_EVAL_SET_ARCHITECTURE_V1_REPORT.md'

BASELINE_SHA = '767aff19a13dbcb33af1d5cd81e5c3edfe6d3bbd'

assert CONTRACT.exists(), 'Phase F authorization governance milestone contract missing'
contract = json.loads(CONTRACT.read_text(encoding='utf-8'))
assert contract['milestone_id'] == 'CAREER_OS_PHASE_F_AUTHORIZATION_V1'
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

# This governance sync must not touch the already-accepted Phase D or Phase E
# reports -- it records only the Phase F authorization transition. Neither
# report is created or modified by this authorization-only sync.
assert PHASE_D_REPORT_PATH.exists()
assert PHASE_E_REPORT_PATH.exists()

# Live checkpoint must record the Phase F authorization event only -- no
# substantive Phase F work, and no human acceptance of Phase F yet (it has
# not been operator-completed).
assert CHECKPOINT.exists(), 'canonical execution checkpoint missing'
cp = json.loads(CHECKPOINT.read_text(encoding='utf-8'))
assert cp['checkpoint_id'] == 'CAREER_OS_CHECKPOINT_2026-09-13_PHASE_F_AUTHORIZATION'
assert cp['canonical_basis_sha'] == BASELINE_SHA
assert cp['phase_id'] == 'CAREER_OS_TRACE_AND_CONTRACT_ARCHITECTURE_V1'
assert cp['phase_mode'] == 'READ_ONLY_DESIGN_ONLY'
assert cp['authorization_status'] == 'BORA_AUTHORIZED'
assert cp['selection_status'] == 'SELECTED'
assert cp['operator_status'] == 'NOT_YET_COMPLETED'
assert cp['implementation_authorized'] is False
assert 'human_acceptance_status' not in cp, (
    'Phase F has not been operator-completed; the checkpoint must not carry a top-level '
    'human_acceptance_status for a phase that has not yet been operator-completed'
)
assert 'accepted_at' not in cp

# The checkpoint's own narrative fields must tie "Phase G" tightly to
# PROPOSED_NOT_AUTHORIZED, not merely contain both words somewhere.
assert PHASE_G_PROPOSED_NOT_AUTHORIZED.search(cp['terminal_adjudication']), (
    'checkpoint terminal_adjudication must couple Phase G to PROPOSED_NOT_AUTHORIZED'
)
_not_done_joined = ' '.join(cp['not_completed_or_not_authorized'])
assert PHASE_G_PROPOSED_NOT_AUTHORIZED.search(_not_done_joined), (
    'checkpoint not_completed_or_not_authorized must couple Phase G to PROPOSED_NOT_AUTHORIZED'
)
assert PHASE_G_PROPOSED_NOT_AUTHORIZED.search(cp['continuity_rule']), (
    'checkpoint continuity_rule must couple Phase G to PROPOSED_NOT_AUTHORIZED'
)

# Phase E must be preserved distinctly as prior_phase, and Phase D as
# prior_prior_phase -- never conflated with Phase F's own (authorized,
# not yet completed) status.
prior_phase = cp['prior_phase']
assert prior_phase['phase_id'] == 'CAREER_OS_SYSTEM_EVAL_SET_ARCHITECTURE_V1'
assert prior_phase['phase_mode'] == 'READ_ONLY_DESIGN_ONLY'
assert prior_phase['operator_status'] == 'COMPLETED_BY_OPERATOR'
assert prior_phase['human_acceptance_status'] == 'BORA_ACCEPTED'
assert prior_phase['accepted_at'] == '2026-09-12'

prior_prior_phase = cp['prior_prior_phase']
assert prior_prior_phase['phase_id'] == 'CAREER_OS_FAILURE_TAXONOMY_AND_EVALUATOR_COVERAGE_MAP_V1'
assert prior_prior_phase['phase_mode'] == 'READ_ONLY_DESIGN_ONLY'
assert prior_prior_phase['operator_status'] == 'COMPLETED_BY_OPERATOR'
assert prior_prior_phase['human_acceptance_status'] == 'BORA_ACCEPTED'
assert prior_prior_phase['accepted_at'] == '2026-09-11'

prior_prior_prior_phase = cp['prior_prior_prior_phase']
assert prior_prior_prior_phase['phase_id'] == 'CAREER_OS_AGENT_CONTEXT_AND_USAGE_EFFICIENCY_V1'
assert prior_prior_prior_phase['human_acceptance_status'] == 'BORA_ACCEPTED'

# Phase E's full operator-completion/acceptance lifecycle narrative must be
# preserved as historical reference now that Phase F is current.
assert 'phase_e_completed_actions_reference' in cp
phase_e_reference = ' '.join(cp['phase_e_completed_actions_reference'])
assert 'exactly 15 case IDs' in phase_e_reference
assert 'HUMAN_CONFIRMED_REFERENCE' in phase_e_reference

# The live Phase F completed_actions must record only the authorization
# transition -- no substantive trace/contract architecture design content.
completed = ' '.join(cp['completed_actions'])
assert 'CAREER_OS_TRACE_AND_CONTRACT_ARCHITECTURE_V1' in completed
assert 'CAREER_OS_SYSTEM_EVAL_SET_ARCHITECTURE_V1' in completed
assert 'prior_phase' in completed
# Each individual completed_actions entry, not the joined string, must carry
# its own negation -- otherwise an unrelated entry's "no substantive" phrase
# could vacuously excuse a different entry that actually authors forbidden
# Phase F design content.
for _entry in cp['completed_actions']:
    _entry_lower = _entry.lower()
    for forbidden_term in ('CAREER_OS_RUN_TRACE_V1 schema', 'typed-envelope design', 'trace contract', 'phase contract'):
        if forbidden_term.lower() in _entry_lower:
            assert 'no substantive' in _entry_lower, (
                f'checkpoint completed_actions entry must not author substantive Phase F design '
                f'content without its own explicit negation: {forbidden_term!r} in entry {_entry!r}'
            )

# project_state.json must point at Phase F, BORA_AUTHORIZED / SELECTED /
# NOT_YET_COMPLETED, with no implementation authorized and Phase G still
# proposed only.
assert PROJECT_STATE['current_phase'].startswith('CAREER_OS_TRACE_AND_CONTRACT_ARCHITECTURE_V1')
assert 'BORA_AUTHORIZED' in PROJECT_STATE['current_phase']
assert 'SELECTED' in PROJECT_STATE['current_phase']
assert 'NOT_YET_COMPLETED' in PROJECT_STATE['current_phase']
assert 'READ_ONLY_DESIGN_ONLY' in PROJECT_STATE['current_phase']
assert 'NO_IMPLEMENTATION_AUTHORIZED' in PROJECT_STATE['current_phase']
assert PHASE_G_PROPOSED_NOT_AUTHORIZED.search(PROJECT_STATE['next_authorized_action']), (
    'project_state.next_authorized_action must couple Phase G to PROPOSED_NOT_AUTHORIZED'
)
assert 'CAREER_OS_SYSTEM_EVAL_SET_ARCHITECTURE_V1' in PROJECT_STATE['next_authorized_action']
assert 'COMPLETED_BY_OPERATOR / BORA_ACCEPTED (2026-09-12) / READ_ONLY_DESIGN_ONLY' in PROJECT_STATE['next_authorized_action']
assert 'CAREER_OS_FAILURE_TAXONOMY_AND_EVALUATOR_COVERAGE_MAP_V1' in PROJECT_STATE['next_authorized_action']
assert 'COMPLETED_BY_OPERATOR / BORA_ACCEPTED (2026-09-11) / READ_ONLY_DESIGN_ONLY' in PROJECT_STATE['next_authorized_action']

# CURRENT_MILESTONE.md / CURRENT_STATE.md / AGENTS.md / the eval-harness ADR
# must all agree: Phase E remains BORA_ACCEPTED/READ_ONLY_DESIGN_ONLY as
# prior_phase, Phase D remains prior_prior_phase, and Phase F is
# BORA_AUTHORIZED / SELECTED / NOT_YET_COMPLETED / READ_ONLY_DESIGN_ONLY,
# with Phase G and later still PROPOSED_NOT_AUTHORIZED.
for surface_name, surface_text in (
    ('CURRENT_MILESTONE.md', CURRENT_MILESTONE),
    ('CURRENT_STATE.md', CURRENT_STATE),
    ('AGENTS.md', AGENTS),
    ('ADR-CAREER-OS-EVAL-HARNESS-SEQUENCE-V1.md', ADR),
):
    assert 'COMPLETED_BY_OPERATOR / BORA_ACCEPTED (2026-09-11) / READ_ONLY_DESIGN_ONLY' in surface_text, (
        f'{surface_name} must preserve Phase D itself as COMPLETED_BY_OPERATOR / '
        f'BORA_ACCEPTED (2026-09-11) / READ_ONLY_DESIGN_ONLY, now prior_prior_phase'
    )
    assert 'CAREER_OS_SYSTEM_EVAL_SET_ARCHITECTURE_V1' in surface_text, (
        f'{surface_name} must name Phase E (CAREER_OS_SYSTEM_EVAL_SET_ARCHITECTURE_V1)'
    )
    assert 'COMPLETED_BY_OPERATOR / BORA_ACCEPTED (2026-09-12) / READ_ONLY_DESIGN_ONLY' in surface_text, (
        f'{surface_name} must state Phase E\'s own coupled state as '
        f'COMPLETED_BY_OPERATOR / BORA_ACCEPTED (2026-09-12) / READ_ONLY_DESIGN_ONLY, now prior_phase'
    )
    assert 'CAREER_OS_TRACE_AND_CONTRACT_ARCHITECTURE_V1' in surface_text, (
        f'{surface_name} must name Phase F (CAREER_OS_TRACE_AND_CONTRACT_ARCHITECTURE_V1)'
    )
    assert 'BORA_AUTHORIZED / SELECTED / NOT_YET_COMPLETED / READ_ONLY_DESIGN_ONLY' in surface_text, (
        f'{surface_name} must state Phase F\'s own coupled state as '
        f'BORA_AUTHORIZED / SELECTED / NOT_YET_COMPLETED / READ_ONLY_DESIGN_ONLY'
    )
    assert (
        'implementation_authorized' in surface_text.lower()
        or 'implementation not authorized' in surface_text.lower()
        or 'no implementation' in surface_text.lower()
        or 'NO_IMPLEMENTATION_AUTHORIZED' in surface_text
    ), f'{surface_name} must state that implementation remains unauthorized'
    assert PHASE_G_PROPOSED_NOT_AUTHORIZED.search(surface_text), (
        f'{surface_name} must couple Phase G to PROPOSED_NOT_AUTHORIZED'
    )

# FINAL hardened Phase F authorization facts (Phase F's own coupled state,
# Phase E's coupled prior_phase state, and Phase G's PROPOSED_NOT_AUTHORIZED
# status) must appear inside the live recovery-governing sections this
# milestone is authorized to maintain (CURRENT_MILESTONE.md, AGENTS.md,
# CURRENT_STATE.md's Current Execution Checkpoint section, and the ADR's
# Section 6 New-chat recovery protocol), not merely somewhere else in the
# file -- so a fresh session reading only the recovery section cannot land
# on a stale or unrelated summary.
_RECOVERY_SECTION_BOUNDS = {
    'CURRENT_MILESTONE.md': ('## Current Checkpoint', '## Eval & Harness Audit - Roadmap Reference'),
    'AGENTS.md': ('## Eval / Harness Roadmap Recovery', '## Agent Context & Usage Efficiency'),
    'CURRENT_STATE.md': ('## Current Execution Checkpoint (2026-09-13)', '## Eval & Harness Audit Roadmap Reference (2026-09-13)'),
    'ADR-CAREER-OS-EVAL-HARNESS-SEQUENCE-V1.md': ('## 6. New-chat recovery protocol', '## 7. Audit deliverables required before implementation'),
}
_RECOVERY_SURFACE_TEXT = {
    'CURRENT_MILESTONE.md': CURRENT_MILESTONE,
    'AGENTS.md': AGENTS,
    'CURRENT_STATE.md': CURRENT_STATE,
    'ADR-CAREER-OS-EVAL-HARNESS-SEQUENCE-V1.md': ADR,
}
for surface_name in (
    'CURRENT_MILESTONE.md', 'AGENTS.md', 'CURRENT_STATE.md', 'ADR-CAREER-OS-EVAL-HARNESS-SEQUENCE-V1.md',
):
    _start_marker, _end_marker = _RECOVERY_SECTION_BOUNDS[surface_name]
    surface_text = _RECOVERY_SURFACE_TEXT[surface_name]
    _start_idx = surface_text.index(_start_marker)
    _end_idx = surface_text.index(_end_marker, _start_idx)
    _recovery_section = surface_text[_start_idx:_end_idx]
    assert 'CAREER_OS_TRACE_AND_CONTRACT_ARCHITECTURE_V1' in _recovery_section, (
        f'{surface_name} recovery-governing section must name Phase F (CAREER_OS_TRACE_AND_CONTRACT_ARCHITECTURE_V1)'
    )
    assert 'BORA_AUTHORIZED / SELECTED / NOT_YET_COMPLETED / READ_ONLY_DESIGN_ONLY' in _recovery_section, (
        f'{surface_name} recovery-governing section must state Phase F\'s own coupled state as '
        f'BORA_AUTHORIZED / SELECTED / NOT_YET_COMPLETED / READ_ONLY_DESIGN_ONLY'
    )
    assert 'CAREER_OS_SYSTEM_EVAL_SET_ARCHITECTURE_V1' in _recovery_section, (
        f'{surface_name} recovery-governing section must name Phase E (CAREER_OS_SYSTEM_EVAL_SET_ARCHITECTURE_V1)'
    )
    assert 'COMPLETED_BY_OPERATOR' in _recovery_section and 'BORA_ACCEPTED (2026-09-12)' in _recovery_section, (
        f'{surface_name} recovery-governing section must state Phase E\'s own prior_phase state as '
        f'COMPLETED_BY_OPERATOR / BORA_ACCEPTED (2026-09-12)'
    )
    assert PHASE_G_PROPOSED_NOT_AUTHORIZED.search(_recovery_section), (
        f'{surface_name} recovery-governing section must couple Phase G to PROPOSED_NOT_AUTHORIZED'
    )

# CHANGELOG.md must record this authorization transition as a distinct dated
# entry, separate from the Phase E acceptance entry.
assert 'CAREER_OS_TRACE_AND_CONTRACT_ARCHITECTURE_V1' in CHANGELOG
assert 'BORA_AUTHORIZED' in CHANGELOG
assert 'authorized by Bora (READ_ONLY / DESIGN_ONLY, BORA_AUTHORIZED)' in CHANGELOG
assert 'I authorize Phase F - Trace/Contract Architecture' in CHANGELOG

# The already-accepted Phase D and Phase E reports must be untouched by this
# sync -- their substance is not re-adjudicated.
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

print('PASS: Career OS Phase F authorization transition verified.')
