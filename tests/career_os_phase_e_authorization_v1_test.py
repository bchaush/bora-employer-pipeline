import json
import re
from pathlib import Path

# Requires the exact subject-coupled phrase "Phase F and every later roadmap
# phase remain PROPOSED_NOT_AUTHORIZED" as one contiguous subject, so this can
# never be satisfied by two unrelated, independently true substrings (e.g. a
# bare "Phase F" mention somewhere and an unrelated PROPOSED_NOT_AUTHORIZED
# elsewhere). Markdown bold is allowed around PROPOSED_NOT_AUTHORIZED only
# where the surface actually renders it that way.
PHASE_F_PROPOSED_NOT_AUTHORIZED = re.compile(
    r'Phase F and every later roadmap phase remain \*{0,2}PROPOSED_NOT_AUTHORIZED\*{0,2}',
    re.IGNORECASE,
)

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / 'milestone_contracts' / 'governance' / 'career-os-phase-e-authorization-v1.json'
CHECKPOINT = ROOT / 'CURRENT_EXECUTION_CHECKPOINT.json'
PROJECT_STATE = json.loads((ROOT / 'project_state.json').read_text(encoding='utf-8'))
AGENTS = (ROOT / 'AGENTS.md').read_text(encoding='utf-8')
CURRENT_MILESTONE = (ROOT / 'CURRENT_MILESTONE.md').read_text(encoding='utf-8')
CURRENT_STATE = (ROOT / 'CURRENT_STATE.md').read_text(encoding='utf-8')
CHANGELOG = (ROOT / 'CHANGELOG.md').read_text(encoding='utf-8')
ADR = (ROOT / 'docs' / 'decisions' / 'ADR-CAREER-OS-EVAL-HARNESS-SEQUENCE-V1.md').read_text(encoding='utf-8')
PHASE_D_REPORT_PATH = ROOT / 'docs' / 'audits' / 'CAREER_OS_FAILURE_TAXONOMY_AND_EVALUATOR_COVERAGE_MAP_V1_REPORT.md'

BASELINE_SHA = 'a2c1172d29dff262dec705a5a573e4b3a1e3a778'

assert CONTRACT.exists(), 'Phase E authorization governance milestone contract missing'
contract = json.loads(CONTRACT.read_text(encoding='utf-8'))
assert contract['milestone_id'] == 'CAREER_OS_PHASE_E_AUTHORIZATION_V1'
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

# This governance sync must not touch the already-accepted Phase D report --
# it records only the Phase E authorization transition.
assert PHASE_D_REPORT_PATH.exists()

# Live checkpoint must record the Phase E authorization transition exactly.
assert CHECKPOINT.exists(), 'canonical execution checkpoint missing'
cp = json.loads(CHECKPOINT.read_text(encoding='utf-8'))
assert cp['canonical_basis_sha'] == BASELINE_SHA
assert cp['phase_id'] == 'CAREER_OS_SYSTEM_EVAL_SET_ARCHITECTURE_V1'
assert cp['phase_mode'] == 'READ_ONLY_DESIGN_ONLY'
assert cp['authorization_status'] == 'BORA_AUTHORIZED'
assert cp['selection_status'] == 'SELECTED'
assert cp['operator_status'] == 'NOT_YET_COMPLETED'
assert cp['implementation_authorized'] is False

# Phase E's own live checkpoint record must carry NO human-acceptance
# fields at the top level -- those belong only to already-accepted prior
# phases (prior_phase / prior_prior_phase / ...), never to Phase E itself,
# which is authorized-but-not-yet-completed.
assert 'human_acceptance_status' not in cp, (
    'checkpoint top level must not carry a human_acceptance_status for the '
    'current (not yet completed) Phase E'
)
assert 'accepted_at' not in cp, (
    'checkpoint top level must not carry an accepted_at for the current '
    '(not yet completed) Phase E'
)

# The checkpoint's own narrative fields must tie "Phase F" tightly to
# PROPOSED_NOT_AUTHORIZED, not merely contain both words somewhere.
assert PHASE_F_PROPOSED_NOT_AUTHORIZED.search(cp['terminal_adjudication']), (
    'checkpoint terminal_adjudication must couple Phase F to PROPOSED_NOT_AUTHORIZED'
)
_not_done_joined = ' '.join(cp['not_completed_or_not_authorized'])
assert PHASE_F_PROPOSED_NOT_AUTHORIZED.search(_not_done_joined), (
    'checkpoint not_completed_or_not_authorized must couple Phase F to PROPOSED_NOT_AUTHORIZED'
)
assert 'BORA_AUTHORIZED / SELECTED / NOT_YET_COMPLETED / READ_ONLY_DESIGN_ONLY' in _not_done_joined, (
    'checkpoint not_completed_or_not_authorized must carry the full Phase E coupled quartet'
)

# The checkpoint's own continuity_rule must itself couple Phase F to
# PROPOSED_NOT_AUTHORIZED as one subject -- a fresh session reading only
# continuity_rule must not be able to infer Phase F/later authorization.
assert PHASE_F_PROPOSED_NOT_AUTHORIZED.search(cp['continuity_rule']), (
    'checkpoint continuity_rule must couple Phase F to PROPOSED_NOT_AUTHORIZED'
)

# The ADR's own top Status banner (the first thing a fresh session reads)
# must itself carry Phase E's exact coupled quartet and explicitly couple
# Phase F to PROPOSED_NOT_AUTHORIZED, not rely on a later section alone.
_adr_banner_start = ADR.index('Status:')
_adr_banner_end = ADR.index('\n', _adr_banner_start)
_adr_banner = ADR[_adr_banner_start:_adr_banner_end]
assert 'BORA_AUTHORIZED / SELECTED / NOT_YET_COMPLETED / READ_ONLY_DESIGN_ONLY' in _adr_banner, (
    'ADR top Status banner must carry the exact Phase E coupled quartet'
)
assert PHASE_F_PROPOSED_NOT_AUTHORIZED.search(_adr_banner), (
    'ADR top Status banner must couple Phase F to PROPOSED_NOT_AUTHORIZED'
)

# Phase D must be preserved distinctly as prior_phase, never conflated with
# Phase E's own (not yet completed) status.
prior_phase = cp['prior_phase']
assert prior_phase['phase_id'] == 'CAREER_OS_FAILURE_TAXONOMY_AND_EVALUATOR_COVERAGE_MAP_V1'
assert prior_phase['phase_mode'] == 'READ_ONLY_DESIGN_ONLY'
assert prior_phase['operator_status'] == 'COMPLETED_BY_OPERATOR'
assert prior_phase['human_acceptance_status'] == 'BORA_ACCEPTED'
assert prior_phase['accepted_at'] == '2026-09-11'

prior_prior_phase = cp['prior_prior_phase']
assert prior_prior_phase['phase_id'] == 'CAREER_OS_AGENT_CONTEXT_AND_USAGE_EFFICIENCY_V1'
assert prior_prior_phase['human_acceptance_status'] == 'BORA_ACCEPTED'

# project_state.json must point at Phase E, BORA_AUTHORIZED/SELECTED/
# NOT_YET_COMPLETED, with no implementation authorized and Phase F still
# proposed only.
assert PROJECT_STATE['current_phase'].startswith('CAREER_OS_SYSTEM_EVAL_SET_ARCHITECTURE_V1')
assert 'BORA_AUTHORIZED' in PROJECT_STATE['current_phase']
assert 'SELECTED' in PROJECT_STATE['current_phase']
assert 'NOT_YET_COMPLETED' in PROJECT_STATE['current_phase']
assert 'READ_ONLY_DESIGN_ONLY' in PROJECT_STATE['current_phase']
assert 'NO_IMPLEMENTATION_AUTHORIZED' in PROJECT_STATE['current_phase']
assert PHASE_F_PROPOSED_NOT_AUTHORIZED.search(PROJECT_STATE['next_authorized_action']), (
    'project_state.next_authorized_action must couple Phase F to PROPOSED_NOT_AUTHORIZED'
)
assert 'CAREER_OS_FAILURE_TAXONOMY_AND_EVALUATOR_COVERAGE_MAP_V1' in PROJECT_STATE['next_authorized_action']
assert 'COMPLETED_BY_OPERATOR / BORA_ACCEPTED (2026-09-11) / READ_ONLY_DESIGN_ONLY' in PROJECT_STATE['next_authorized_action']

# CURRENT_MILESTONE.md / CURRENT_STATE.md / AGENTS.md / the eval-harness ADR
# must all agree: Phase D remains BORA_ACCEPTED/READ_ONLY_DESIGN_ONLY as
# prior_phase, and Phase E is BORA_AUTHORIZED / SELECTED / NOT_YET_COMPLETED
# / READ_ONLY_DESIGN_ONLY, with Phase F and later still PROPOSED_NOT_AUTHORIZED.
for surface_name, surface_text in (
    ('CURRENT_MILESTONE.md', CURRENT_MILESTONE),
    ('CURRENT_STATE.md', CURRENT_STATE),
    ('AGENTS.md', AGENTS),
    ('ADR-CAREER-OS-EVAL-HARNESS-SEQUENCE-V1.md', ADR),
):
    assert 'COMPLETED_BY_OPERATOR / BORA_ACCEPTED (2026-09-11) / READ_ONLY_DESIGN_ONLY' in surface_text, (
        f'{surface_name} must preserve Phase D itself as COMPLETED_BY_OPERATOR / '
        f'BORA_ACCEPTED (2026-09-11) / READ_ONLY_DESIGN_ONLY, now prior_phase'
    )
    assert 'CAREER_OS_SYSTEM_EVAL_SET_ARCHITECTURE_V1' in surface_text, (
        f'{surface_name} must name Phase E (CAREER_OS_SYSTEM_EVAL_SET_ARCHITECTURE_V1)'
    )

    # Phase E's own state must appear as one coupled invariant on every live
    # surface -- BORA_AUTHORIZED / SELECTED / NOT_YET_COMPLETED /
    # READ_ONLY_DESIGN_ONLY together, not as independently-true substrings
    # that could each be satisfied by unrelated sentences.
    assert 'BORA_AUTHORIZED / SELECTED / NOT_YET_COMPLETED / READ_ONLY_DESIGN_ONLY' in surface_text, (
        f'{surface_name} must state Phase E\'s own coupled state as '
        f'BORA_AUTHORIZED / SELECTED / NOT_YET_COMPLETED / READ_ONLY_DESIGN_ONLY'
    )

    # No live surface may mark Phase E itself COMPLETED_BY_OPERATOR or
    # BORA_ACCEPTED -- check every occurrence of Phase E's own phase_id for
    # a nearby (same-sentence-scale) conflation with those prior-phase-only
    # terms.
    _search_from = 0
    _found_phase_e_mention = False
    while True:
        _idx = surface_text.find('CAREER_OS_SYSTEM_EVAL_SET_ARCHITECTURE_V1', _search_from)
        if _idx == -1:
            break
        _found_phase_e_mention = True
        _window = surface_text[_idx:_idx + 250]
        assert 'COMPLETED_BY_OPERATOR' not in _window, (
            f'{surface_name} must not mark Phase E itself COMPLETED_BY_OPERATOR'
        )
        assert 'BORA_ACCEPTED' not in _window, (
            f'{surface_name} must not mark Phase E itself BORA_ACCEPTED'
        )
        _search_from = _idx + 1
    assert _found_phase_e_mention, f'{surface_name} must name Phase E by its own phase_id'

    assert (
        'implementation_authorized' in surface_text.lower()
        or 'implementation not authorized' in surface_text.lower()
        or 'no implementation' in surface_text.lower()
        or 'NO_IMPLEMENTATION_AUTHORIZED' in surface_text
    ), f'{surface_name} must state that implementation remains unauthorized'

    # Phase F (and every later roadmap phase) must be coupled to
    # PROPOSED_NOT_AUTHORIZED, not proven by two unrelated substrings.
    assert PHASE_F_PROPOSED_NOT_AUTHORIZED.search(surface_text), (
        f'{surface_name} must couple Phase F to PROPOSED_NOT_AUTHORIZED'
    )

# A whole-document search is not enough: it can pass merely because some
# unrelated later section (e.g. a "Decision"/"Roadmap Reference" summary)
# happens to state the coupled quartet or the Phase F guard, while the
# actual live recovery-governing section a fresh session reads first stays
# vacuous (states "Phase F" without PROPOSED_NOT_AUTHORIZED, or splits the
# quartet across separate unlinked field lines). Anchor each surface's own
# recovery-governing section and require both invariants inside that exact
# section, not merely somewhere in the document.
_RECOVERY_SECTION_BOUNDS = {
    'CURRENT_MILESTONE.md': ('## Current Checkpoint', '## Eval & Harness Audit - Roadmap Reference'),
    'CURRENT_STATE.md': ('## Current Execution Checkpoint', '## Eval & Harness Audit Roadmap Reference'),
    'AGENTS.md': ('## Eval / Harness Roadmap Recovery', '## Agent Context & Usage Efficiency'),
    'ADR-CAREER-OS-EVAL-HARNESS-SEQUENCE-V1.md': ('## 6. New-chat recovery protocol', '## 7.'),
}
for surface_name, surface_text in (
    ('CURRENT_MILESTONE.md', CURRENT_MILESTONE),
    ('CURRENT_STATE.md', CURRENT_STATE),
    ('AGENTS.md', AGENTS),
    ('ADR-CAREER-OS-EVAL-HARNESS-SEQUENCE-V1.md', ADR),
):
    _start_marker, _end_marker = _RECOVERY_SECTION_BOUNDS[surface_name]
    _start_idx = surface_text.index(_start_marker)
    _end_idx = surface_text.index(_end_marker, _start_idx)
    _recovery_section = surface_text[_start_idx:_end_idx]

    assert 'BORA_AUTHORIZED / SELECTED / NOT_YET_COMPLETED / READ_ONLY_DESIGN_ONLY' in _recovery_section, (
        f'{surface_name} recovery-governing section must itself couple Phase E\'s '
        f'state as BORA_AUTHORIZED / SELECTED / NOT_YET_COMPLETED / READ_ONLY_DESIGN_ONLY, '
        f'not merely rely on an unrelated later section stating it'
    )
    assert PHASE_F_PROPOSED_NOT_AUTHORIZED.search(_recovery_section), (
        f'{surface_name} recovery-governing section must itself couple Phase F to '
        f'PROPOSED_NOT_AUTHORIZED, not merely rely on an unrelated later section stating it'
    )

# CHANGELOG.md must record this transition as a distinct dated entry,
# separate from the prior Phase D acceptance entry.
assert 'CAREER_OS_SYSTEM_EVAL_SET_ARCHITECTURE_V1' in CHANGELOG
assert 'BORA_AUTHORIZED' in CHANGELOG
assert 'authorized by Bora (READ_ONLY / DESIGN_ONLY, BORA_AUTHORIZED)' in CHANGELOG
assert 'accepted by Bora (BORA ACCEPTED)' in CHANGELOG

# The already-accepted Phase D report itself must be untouched by this
# sync -- its substance is not re-adjudicated.
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

print('PASS: Career OS Phase E authorization transition verified.')
