import json
import re
from pathlib import Path

PHASE_H_PROPOSED_NOT_AUTHORIZED = re.compile(
    r'Phase H and every later roadmap phase remain \*{0,2}PROPOSED_NOT_AUTHORIZED\*{0,2}',
    re.IGNORECASE,
)

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / 'milestone_contracts' / 'governance' / 'career-os-phase-f-authorization-v1.json'
ACCEPTANCE_CONTRACT = ROOT / 'milestone_contracts' / 'governance' / 'career-os-phase-f-acceptance-v1.json'
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

assert ACCEPTANCE_CONTRACT.exists(), 'Phase F acceptance governance milestone contract missing'
acceptance_contract = json.loads(ACCEPTANCE_CONTRACT.read_text(encoding='utf-8'))
assert acceptance_contract['milestone_id'] == 'CAREER_OS_PHASE_F_ACCEPTANCE_V1'
assert acceptance_contract['kind'] == 'GOVERNANCE_SYNC'
assert acceptance_contract['baseline_sha'] == '256edcc01f6860f6614a8e0d8e409f5900765082'
_expected_acceptance_allowed_paths = {
    'AGENTS.md', 'CHANGELOG.md', 'CURRENT_EXECUTION_CHECKPOINT.json', 'CURRENT_MILESTONE.md', 'CURRENT_STATE.md',
    'project_state.json', 'docs/audits/CAREER_OS_TRACE_AND_CONTRACT_ARCHITECTURE_V1_REPORT.md',
    'docs/decisions/ADR-CAREER-OS-EVAL-HARNESS-SEQUENCE-V1.md',
    'tests/career_os_trace_and_contract_architecture_v1_test.py', 'tests/career_os_execution_checkpoint_v1_test.py',
    'tests/career_os_eval_harness_sequence_v1_test.py', 'tests/career_os_agent_context_usage_efficiency_v1_test.py',
    'tests/career_os_phase_d_authorization_v1_test.py', 'tests/career_os_phase_e_authorization_v1_test.py',
    'tests/career_os_phase_f_authorization_v1_test.py', 'milestone_contracts/governance/career-os-phase-f-acceptance-v1.json',
}
assert set(acceptance_contract['allowed_paths']) == _expected_acceptance_allowed_paths
_expected_acceptance_required_tests = {
    'tests/career_os_trace_and_contract_architecture_v1_test.py', 'tests/career_os_execution_checkpoint_v1_test.py',
    'tests/career_os_eval_harness_sequence_v1_test.py', 'tests/career_os_agent_context_usage_efficiency_v1_test.py',
    'tests/career_os_phase_d_authorization_v1_test.py', 'tests/career_os_phase_e_authorization_v1_test.py',
    'tests/career_os_phase_f_authorization_v1_test.py',
}
assert set(acceptance_contract['required_tests']) == _expected_acceptance_required_tests
for _forbidden in ('BLUEPRINT.md', 'CLAUDE.md', 'GEMINI.md', '.cursor/**', '.claude/**', 'src/**', 'schemas/**', 'claims/**', 'evidence/**', 'resume/**', 'golden-tests/**', 'fixtures/**', 'config/**', 'prompts/**'):
    assert _forbidden in acceptance_contract['forbidden_paths'], f'acceptance contract must forbid {_forbidden}'
assert 'I explicitly accept Phase F brother' in acceptance_contract['goal']
assert acceptance_contract['human_approval_requirements'] == 'BORA_EXPLICITLY_ACCEPTED_PHASE_F_ON_2026-09-14; NO_PHASE_G_AUTHORIZED; NO_IMPLEMENTATION_AUTHORIZED'
_acceptance_conditions = ' '.join(acceptance_contract['acceptance_conditions'])
_stop_conditions = ' '.join(acceptance_contract['stop_conditions'])
assert '2026-09-14 acceptance-sync entry' in _acceptance_conditions
assert 'exact acceptance statement' in _acceptance_conditions
assert 'BORA_ACCEPTED' in _acceptance_conditions and '2026-09-14' in _acceptance_conditions
assert 'implementation_authorized=false' in _acceptance_conditions
assert 'Phase G and every later roadmap phase PROPOSED_NOT_AUTHORIZED' in _acceptance_conditions
assert 'rewrites historical PENDING_BORA_ACCEPTANCE entries' in _stop_conditions
assert 'authorizes or implies authorization of Phase G or any later phase' in _stop_conditions

# This governance authorization sync's own contract is unmodified. The
# substantive Phase F report is a SEPARATE, dedicated deliverable governed by
# milestone_contracts/design/career-os-phase-f-trace-contract-architecture-v1.json.
assert PHASE_D_REPORT_PATH.exists()
assert PHASE_E_REPORT_PATH.exists()
assert PHASE_F_REPORT_PATH.exists(), 'substantive Phase F trace/contract architecture report missing'

# Live checkpoint must now preserve Phase F's completed architecture and
# Bora's explicit 2026-09-14 acceptance as prior_phase, since Bora has since
# separately, explicitly authorized Phase G as the live current phase, while
# preserving implementation_authorized=false and keeping Phase H/later
# separately unauthorized.
assert CHECKPOINT.exists(), 'canonical execution checkpoint missing'
cp = json.loads(CHECKPOINT.read_text(encoding='utf-8'))
assert cp['implementation_authorized'] is False

# The checkpoint's own narrative fields must tie "Phase H" tightly to
# PROPOSED_NOT_AUTHORIZED, not merely contain both words somewhere.
assert PHASE_H_PROPOSED_NOT_AUTHORIZED.search(cp['terminal_adjudication']), (
    'checkpoint terminal_adjudication must couple Phase H to PROPOSED_NOT_AUTHORIZED'
)
_not_done_joined = ' '.join(cp['not_completed_or_not_authorized'])
assert PHASE_H_PROPOSED_NOT_AUTHORIZED.search(_not_done_joined), (
    'checkpoint not_completed_or_not_authorized must couple Phase H to PROPOSED_NOT_AUTHORIZED'
)
assert PHASE_H_PROPOSED_NOT_AUTHORIZED.search(cp['continuity_rule']), (
    'checkpoint continuity_rule must couple Phase H to PROPOSED_NOT_AUTHORIZED'
)

# Phase F must be preserved distinctly as prior_phase, Phase E as
# prior_prior_phase, and Phase D as prior_prior_prior_phase -- never
# conflated with Phase G's own freshly authorized status.
prior_phase = cp['prior_phase']
assert prior_phase['phase_id'] == 'CAREER_OS_TRACE_AND_CONTRACT_ARCHITECTURE_V1'
assert prior_phase['phase_mode'] == 'READ_ONLY_DESIGN_ONLY'
assert prior_phase['operator_status'] == 'COMPLETED_BY_OPERATOR'
assert prior_phase['human_acceptance_status'] == 'BORA_ACCEPTED'
assert prior_phase['accepted_at'] == '2026-09-14'

prior_prior_phase = cp['prior_prior_phase']
assert prior_prior_phase['phase_id'] == 'CAREER_OS_SYSTEM_EVAL_SET_ARCHITECTURE_V1'
assert prior_prior_phase['phase_mode'] == 'READ_ONLY_DESIGN_ONLY'
assert prior_prior_phase['operator_status'] == 'COMPLETED_BY_OPERATOR'
assert prior_prior_phase['human_acceptance_status'] == 'BORA_ACCEPTED'
assert prior_prior_phase['accepted_at'] == '2026-09-12'

prior_prior_prior_phase = cp['prior_prior_prior_phase']
assert prior_prior_prior_phase['phase_id'] == 'CAREER_OS_FAILURE_TAXONOMY_AND_EVALUATOR_COVERAGE_MAP_V1'
assert prior_prior_prior_phase['human_acceptance_status'] == 'BORA_ACCEPTED'
assert prior_prior_prior_phase['accepted_at'] == '2026-09-11'

# Phase E's full operator-completion/acceptance lifecycle narrative must be
# preserved as historical reference now that Phase G is current and Phase E occupies prior_prior_phase.
assert 'phase_e_completed_actions_reference' in cp
phase_e_reference = ' '.join(cp['phase_e_completed_actions_reference'])
assert 'exactly 15 case IDs' in phase_e_reference
assert 'HUMAN_CONFIRMED_REFERENCE' in phase_e_reference

# The live Phase F completed_actions must now record substantive conceptual
# trace/contract architecture design content, not merely an authorization
# transition.
completed = ' '.join(cp['completed_actions'])
assert 'CAREER_OS_TRACE_AND_CONTRACT_ARCHITECTURE_V1' in completed
assert 'CAREER_OS_RUN_TRACE_V1' in completed
assert 'first_causal_failure_point' in completed
assert 'human-handoff' in completed.lower()
assert 'historical-at-phase-f-completion only' in completed.lower()

# Each individual completed_actions entry, not the joined string, must carry
# its own negation wherever it names a forbidden non-authorized deliverable --
# otherwise an unrelated entry's negation could vacuously excuse a different
# entry that actually claims to have authored forbidden Phase F production
# content (a schema file, a serialization format, trace infrastructure, a
# database/UI, a model router, or an LLM judge).
_NEGATION_REQUIRED_TERMS = (
    'career_os_run_trace_v1 schema',
    'phase-contract serialization format',
    'trace infrastructure',
    'database',
    'model router',
    'llm judge',
    'llm-judge',
)
for _entry in cp['completed_actions']:
    _entry_lower = _entry.lower()
    for _term in _NEGATION_REQUIRED_TERMS:
        _idx = _entry_lower.find(_term)
        while _idx != -1:
            _preceding = _entry_lower[max(0, _idx - 12):_idx]
            assert 'no ' in _preceding, (
                f'checkpoint completed_actions entry names forbidden term {_term!r} without '
                f'its own preceding negation ("no ..."): {_entry!r}'
            )
            _idx = _entry_lower.find(_term, _idx + 1)

# project_state.json must now point at Phase G as operator-completed / pending Bora acceptance, while
# preserving Phase F as operator-completed and BORA_ACCEPTED (2026-09-14) in
# the next_authorized_action seam text, with no implementation authorized
# and Phase H still proposed only.
assert PROJECT_STATE['current_phase'].startswith('CAREER_OS_ASSURANCE_ARCHITECTURE_V1')
assert 'COMPLETED_BY_OPERATOR' in PROJECT_STATE['current_phase']
assert 'PENDING_BORA_ACCEPTANCE' in PROJECT_STATE['current_phase']
assert 'READ_ONLY_DESIGN_ONLY' in PROJECT_STATE['current_phase']
assert 'NO_IMPLEMENTATION_AUTHORIZED' in PROJECT_STATE['current_phase']
assert PHASE_H_PROPOSED_NOT_AUTHORIZED.search(PROJECT_STATE['next_authorized_action']), (
    'project_state.next_authorized_action must couple Phase H to PROPOSED_NOT_AUTHORIZED'
)
assert 'CAREER_OS_TRACE_AND_CONTRACT_ARCHITECTURE_V1' in PROJECT_STATE['next_authorized_action']
assert 'COMPLETED_BY_OPERATOR / BORA_ACCEPTED (2026-09-14) / READ_ONLY_DESIGN_ONLY' in PROJECT_STATE['next_authorized_action']
assert 'CAREER_OS_SYSTEM_EVAL_SET_ARCHITECTURE_V1' in PROJECT_STATE['next_authorized_action']
assert 'COMPLETED_BY_OPERATOR / BORA_ACCEPTED (2026-09-12) / READ_ONLY_DESIGN_ONLY' in PROJECT_STATE['next_authorized_action']
assert 'CAREER_OS_FAILURE_TAXONOMY_AND_EVALUATOR_COVERAGE_MAP_V1' in PROJECT_STATE['next_authorized_action']
assert 'COMPLETED_BY_OPERATOR / BORA_ACCEPTED (2026-09-11) / READ_ONLY_DESIGN_ONLY' in PROJECT_STATE['next_authorized_action']
assert 'once we are proper to standard' in PROJECT_STATE['next_authorized_action'].lower()
assert 'done g lets keep going brother' in PROJECT_STATE['next_authorized_action'].lower()
# Live recovery doctrine must keep Phase G authorization separate from implementation authority.
for _surface_name, _surface_text in (('ADR', ADR), ('AGENTS', AGENTS)):
    assert 'Phase H' in _surface_text, f'{_surface_name} must preserve the Phase H implementation boundary'
    assert 'authorizing Phase G alone does not authorize implementation' in _surface_text or 'Authorizing Phase G alone does not authorize implementation' in _surface_text, f'{_surface_name} must state that Phase G authorization alone never authorizes implementation'
    assert 'until a next phase is separately authorized by Bora' not in _surface_text, f'{_surface_name} must not make next-phase authorization the implementation unlock'
    assert 'before it or any implementation is authorized' not in _surface_text, f'{_surface_name} must not couple generic next-phase authorization to implementation authority'
    assert 'no implementation is authorized until then' not in _surface_text, f'{_surface_name} must not use ambiguous next-phase-as-implementation-gate wording'

# Phase G authorization must remain independent from implementation authority on every live recovery/state surface.
_phase_h_surfaces = (
    ('project_state.next_authorized_action', PROJECT_STATE['next_authorized_action']),
    ('CURRENT_MILESTONE.md', CURRENT_MILESTONE),
    ('CURRENT_STATE.md', CURRENT_STATE),
    ('ADR', ADR),
    ('AGENTS', AGENTS),
    ('Phase F report', PHASE_F_REPORT_PATH.read_text(encoding='utf-8')),
)
for _surface_name, _surface_text in _phase_h_surfaces:
    _surface_lower = _surface_text.lower()
    assert 'phase h' in _surface_lower, f'{_surface_name} must preserve the independent Phase H implementation boundary'
    assert ('authorizing phase g alone does not authorize implementation' in _surface_lower or 'operator completion of phase g alone does not authorize implementation' in _surface_lower), f'{_surface_name} must state that neither Phase G authorization nor operator completion authorizes implementation'
assert 'no phase g or implementation work may begin' not in PROJECT_STATE['next_authorized_action'].lower(), 'project_state must not couple Phase G authorization to implementation permission'
assert 'authorizing Phase G alone does not authorize implementation' in _acceptance_conditions
assert 'Phase H bounded implementation milestone' in _acceptance_conditions
assert 'couples authorization of Phase G or any next phase to permission for implementation/runtime/storage work' in _stop_conditions

# CURRENT_MILESTONE.md / CURRENT_STATE.md / AGENTS.md / the eval-harness ADR
# must all agree on the post-G layout: Phase D=prior_prior_prior_phase,
# Phase E=prior_prior_phase, Phase F=prior_phase and BORA_ACCEPTED (2026-09-14),
# while Phase G is the live BORA_AUTHORIZED / SELECTED / NOT_YET_COMPLETED /
# READ_ONLY_DESIGN_ONLY phase and Phase H/later remain PROPOSED_NOT_AUTHORIZED.
for surface_name, surface_text in (
    ('CURRENT_MILESTONE.md', CURRENT_MILESTONE),
    ('CURRENT_STATE.md', CURRENT_STATE),
    ('AGENTS.md', AGENTS),
    ('ADR-CAREER-OS-EVAL-HARNESS-SEQUENCE-V1.md', ADR),
):
    assert 'COMPLETED_BY_OPERATOR / BORA_ACCEPTED (2026-09-11) / READ_ONLY_DESIGN_ONLY' in surface_text, (
        f'{surface_name} must preserve Phase D itself as COMPLETED_BY_OPERATOR / '
        f'BORA_ACCEPTED (2026-09-11) / READ_ONLY_DESIGN_ONLY, now prior_prior_prior_phase'
    )
    assert 'CAREER_OS_SYSTEM_EVAL_SET_ARCHITECTURE_V1' in surface_text, (
        f'{surface_name} must name Phase E (CAREER_OS_SYSTEM_EVAL_SET_ARCHITECTURE_V1)'
    )
    assert 'COMPLETED_BY_OPERATOR / BORA_ACCEPTED (2026-09-12) / READ_ONLY_DESIGN_ONLY' in surface_text, (
        f'{surface_name} must state Phase E\'s own coupled state as '
        f'COMPLETED_BY_OPERATOR / BORA_ACCEPTED (2026-09-12) / READ_ONLY_DESIGN_ONLY'
    )
    assert 'CAREER_OS_TRACE_AND_CONTRACT_ARCHITECTURE_V1' in surface_text, (
        f'{surface_name} must name Phase F (CAREER_OS_TRACE_AND_CONTRACT_ARCHITECTURE_V1)'
    )
    assert 'COMPLETED_BY_OPERATOR / BORA_ACCEPTED (2026-09-14) / READ_ONLY_DESIGN_ONLY' in surface_text, (
        f'{surface_name} must state Phase F\'s own coupled state as '
        f'COMPLETED_BY_OPERATOR / BORA_ACCEPTED (2026-09-14) / READ_ONLY_DESIGN_ONLY'
    )
    assert 'CAREER_OS_ASSURANCE_ARCHITECTURE_V1' in surface_text, (
        f'{surface_name} must name Phase G (CAREER_OS_ASSURANCE_ARCHITECTURE_V1)'
    )
    assert 'COMPLETED_BY_OPERATOR / PENDING_BORA_ACCEPTANCE / READ_ONLY_DESIGN_ONLY' in surface_text, (
        f'{surface_name} must state Phase G\'s own coupled state as '
        f'COMPLETED_BY_OPERATOR / PENDING_BORA_ACCEPTANCE / READ_ONLY_DESIGN_ONLY'
    )
    assert (
        'implementation_authorized' in surface_text.lower()
        or 'implementation not authorized' in surface_text.lower()
        or 'no implementation' in surface_text.lower()
        or 'NO_IMPLEMENTATION_AUTHORIZED' in surface_text
    ), f'{surface_name} must state that implementation remains unauthorized'
    assert PHASE_H_PROPOSED_NOT_AUTHORIZED.search(surface_text), (
        f'{surface_name} must couple Phase H to PROPOSED_NOT_AUTHORIZED'
    )

# FINAL hardened Phase F completion facts (Phase F's own coupled prior_phase state,
# Phase E's coupled prior_prior_phase state, and Phase G's live BORA_AUTHORIZED
# current status with Phase H still PROPOSED_NOT_AUTHORIZED) must appear inside the live recovery-governing sections this
# milestone is authorized to maintain (CURRENT_MILESTONE.md, AGENTS.md,
# CURRENT_STATE.md's Current Execution Checkpoint section, and the ADR's
# Section 6 New-chat recovery protocol), not merely somewhere else in the
# file -- so a fresh session reading only the recovery section cannot land
# on a stale or unrelated summary.
_RECOVERY_SECTION_BOUNDS = {
    'CURRENT_MILESTONE.md': ('## Current Checkpoint - Phase G (Assurance Architecture) Completed by Operator (2026-09-14, PENDING BORA ACCEPTANCE)', '## Eval & Harness Audit - Roadmap Reference'),
    'AGENTS.md': ('## Eval / Harness Roadmap Recovery', '## Agent Context & Usage Efficiency'),
    'CURRENT_STATE.md': ('## Current Execution Checkpoint (2026-09-14)', '## Eval & Harness Audit Roadmap Reference (2026-09-14)'),
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
    assert 'COMPLETED_BY_OPERATOR / BORA_ACCEPTED (2026-09-14) / READ_ONLY_DESIGN_ONLY' in _recovery_section, (
        f'{surface_name} recovery-governing section must state Phase F\'s own coupled state as '
        f'COMPLETED_BY_OPERATOR / BORA_ACCEPTED (2026-09-14) / READ_ONLY_DESIGN_ONLY'
    )
    assert 'CAREER_OS_SYSTEM_EVAL_SET_ARCHITECTURE_V1' in _recovery_section, (
        f'{surface_name} recovery-governing section must name Phase E (CAREER_OS_SYSTEM_EVAL_SET_ARCHITECTURE_V1)'
    )
    assert 'COMPLETED_BY_OPERATOR' in _recovery_section and 'BORA_ACCEPTED (2026-09-12)' in _recovery_section, (
        f'{surface_name} recovery-governing section must state Phase E\'s own prior_prior_phase state as '
        f'COMPLETED_BY_OPERATOR / BORA_ACCEPTED (2026-09-12)'
    )
    assert 'CAREER_OS_ASSURANCE_ARCHITECTURE_V1' in _recovery_section, (
        f'{surface_name} recovery-governing section must name Phase G (CAREER_OS_ASSURANCE_ARCHITECTURE_V1)'
    )
    assert 'COMPLETED_BY_OPERATOR / PENDING_BORA_ACCEPTANCE / READ_ONLY_DESIGN_ONLY' in _recovery_section, (
        f'{surface_name} recovery-governing section must state Phase G as the live authorized current phase'
    )
    assert PHASE_H_PROPOSED_NOT_AUTHORIZED.search(_recovery_section), (
        f'{surface_name} recovery-governing section must couple Phase H to PROPOSED_NOT_AUTHORIZED'
    )

# CHANGELOG.md must preserve authorization and operator-completion history and
# record the distinct 2026-09-14 Bora acceptance event as its own dated entry.
assert 'CAREER_OS_TRACE_AND_CONTRACT_ARCHITECTURE_V1' in CHANGELOG
assert 'PENDING BORA ACCEPTANCE' in CHANGELOG
assert 'substantive read-only/design-only work completed by operator' in CHANGELOG
assert 'I authorize Phase F - Trace/Contract Architecture' in CHANGELOG
assert '## 2026-09-14 — Career OS Phase F (`CAREER_OS_TRACE_AND_CONTRACT_ARCHITECTURE_V1`) accepted by Bora (BORA ACCEPTED)' in CHANGELOG
assert 'I explicitly accept Phase F brother' in CHANGELOG
assert '## 2026-09-13 — Career OS Phase F (`CAREER_OS_TRACE_AND_CONTRACT_ARCHITECTURE_V1`) substantive read-only/design-only work completed by operator (PENDING BORA ACCEPTANCE)' in CHANGELOG
_ACCEPT_HEADING = '## 2026-09-14 — Career OS Phase F (`CAREER_OS_TRACE_AND_CONTRACT_ARCHITECTURE_V1`) accepted by Bora (BORA ACCEPTED)'
_accept_start = CHANGELOG.index(_ACCEPT_HEADING)
_accept_next = CHANGELOG.find('\n## ', _accept_start + len(_ACCEPT_HEADING))
_accept_block = CHANGELOG[_accept_start:_accept_next if _accept_next != -1 else len(CHANGELOG)]
assert 'I explicitly accept Phase F brother' in _accept_block, 'Bora acceptance quote must be inside the distinct 2026-09-14 Phase F acceptance CHANGELOG block'

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

print('PASS: Career OS Phase F Bora-acceptance governance sync verified.')


# Post-Phase-G dependent recovery-slot checks.
for _surface_name, _surface_text, _start_marker, _end_marker in (
    ('AGENTS.md', AGENTS, '## Eval / Harness Roadmap Recovery', '## Agent Context & Usage Efficiency'),
    ('CURRENT_STATE.md', CURRENT_STATE, '## Current Execution Checkpoint (2026-09-14)', '## Eval & Harness Audit Roadmap Reference (2026-09-14)'),
    ('ADR-CAREER-OS-EVAL-HARNESS-SEQUENCE-V1.md', ADR, '## 6. New-chat recovery protocol', '## 7. Audit deliverables required before implementation'),
):
    _section = _surface_text.split(_start_marker, 1)[1].split(_end_marker, 1)[0].lower()
    assert re.search(r'career_os_failure_taxonomy_and_evaluator_coverage_map_v1.*?prior_prior_prior_phase', _section, re.S), f'{_surface_name} must map Phase D to prior_prior_prior_phase'
    assert re.search(r'career_os_system_eval_set_architecture_v1.*?prior_prior_phase', _section, re.S), f'{_surface_name} must map Phase E to prior_prior_phase'
    assert re.search(r'career_os_trace_and_contract_architecture_v1.*?prior_phase', _section, re.S), f'{_surface_name} must map Phase F to prior_phase'
