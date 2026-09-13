import json
import re
from pathlib import Path

PHASE_F_PROPOSED_NOT_AUTHORIZED = re.compile(
    r'Phase F and every later roadmap phase remain \*{0,2}PROPOSED_NOT_AUTHORIZED\*{0,2}',
    re.IGNORECASE,
)

ROOT = Path(__file__).resolve().parents[1]
CHECKPOINT = ROOT / 'CURRENT_EXECUTION_CHECKPOINT.json'
PROJECT_STATE = json.loads((ROOT / 'project_state.json').read_text(encoding='utf-8'))
AGENTS = (ROOT / 'AGENTS.md').read_text(encoding='utf-8')

CANONICAL_BASELINE_SHA = 'a2c1172d29dff262dec705a5a573e4b3a1e3a778'

assert CHECKPOINT.exists(), 'canonical execution checkpoint missing'
cp = json.loads(CHECKPOINT.read_text(encoding='utf-8'))

assert cp['schema_version'] == '1.0'
# Checkpoint lineage convention: Phase D's own checkpoint_id preserved its
# "_AUTHORIZATION" suffix through operator completion and acceptance
# (CAREER_OS_CHECKPOINT_2026-09-11_PHASE_D_AUTHORIZATION); Phase E's
# checkpoint_id must follow the same established lineage convention rather
# than drift to an ad hoc "_OPERATOR_COMPLETION" suffix.
assert cp['checkpoint_id'] == 'CAREER_OS_CHECKPOINT_2026-09-12_PHASE_E_AUTHORIZATION', (
    "checkpoint_id must preserve the established lineage convention "
    "(CAREER_OS_CHECKPOINT_2026-09-12_PHASE_E_AUTHORIZATION), matching how "
    "Phase D's own authorization checkpoint_id/basis survived through its "
    "operator completion and acceptance"
)
assert cp['canonical_basis_sha'] == CANONICAL_BASELINE_SHA
assert cp['phase_id'] == 'CAREER_OS_SYSTEM_EVAL_SET_ARCHITECTURE_V1'
assert cp['phase_mode'] == 'READ_ONLY_DESIGN_ONLY'
assert cp['authorization_status'] == 'BORA_AUTHORIZED'
assert cp['selection_status'] == 'SELECTED'
assert cp['operator_status'] == 'COMPLETED_BY_OPERATOR'
assert cp['human_acceptance_status'] == 'PENDING_BORA_ACCEPTANCE'
assert cp['implementation_authorized'] is False
assert 'accepted_at' not in cp, (
    'Phase E is not yet Bora-accepted, so the top-level checkpoint must not '
    'carry an accepted_at for it'
)

# CAREER_OS_FAILURE_TAXONOMY_AND_EVALUATOR_COVERAGE_MAP_V1 (Phase D) must be
# recorded distinctly as prior_phase, never conflated with Phase E's own
# (operator-completed, not yet Bora-accepted) status.
prior_phase = cp['prior_phase']
assert prior_phase['phase_id'] == 'CAREER_OS_FAILURE_TAXONOMY_AND_EVALUATOR_COVERAGE_MAP_V1'
assert prior_phase['phase_mode'] == 'READ_ONLY_DESIGN_ONLY'
assert prior_phase['operator_status'] == 'COMPLETED_BY_OPERATOR'
assert prior_phase['human_acceptance_status'] == 'BORA_ACCEPTED'
assert prior_phase['accepted_at'] == '2026-09-11'

prior_prior_phase = cp['prior_prior_phase']
assert prior_prior_phase['phase_id'] == 'CAREER_OS_AGENT_CONTEXT_AND_USAGE_EFFICIENCY_V1'
assert prior_prior_phase['phase_mode'] == 'GOVERNANCE_ONLY'
assert prior_prior_phase['human_acceptance_status'] == 'BORA_ACCEPTED'

prior_prior_prior_phase = cp['prior_prior_prior_phase']
assert prior_prior_prior_phase['phase_id'] == 'CAREER_OS_TRACE_AND_FAILURE_CORPUS_INVENTORY_V1'
assert prior_prior_prior_phase['human_acceptance_status'] == 'BORA_ACCEPTED'

assert isinstance(cp['exact_next_allowed_action'], str) and cp['exact_next_allowed_action'].strip()
assert 'CAREER_OS_SYSTEM_EVAL_SET_ARCHITECTURE_V1' in cp['exact_next_allowed_action']
assert 'implementation_authorized remains false' in cp['exact_next_allowed_action']
assert 'Bora reviews the substantive Phase E' in cp['exact_next_allowed_action']
assert PHASE_F_PROPOSED_NOT_AUTHORIZED.search(cp['exact_next_allowed_action']), (
    'exact_next_allowed_action must couple Phase F to PROPOSED_NOT_AUTHORIZED as one subject'
)

# Operator completion must never be read as itself constituting Bora's
# eventual acceptance, and must never itself authorize Phase F.
assert 'does not itself authorize Phase F' in cp['exact_next_allowed_action']
assert "does not itself constitute Bora's eventual acceptance" in cp['exact_next_allowed_action']
assert 'No Phase F and no implementation' in cp['exact_next_allowed_action']

# terminal_adjudication must reflect the prior GOVERNING policy, Phase D's
# preserved acceptance, AND Phase E's substantive operator completion, while
# still stating implementation and Phase F are not authorized.
assert 'GOVERNANCE_ONLY / GOVERNING' in cp['terminal_adjudication']
assert 'COMPLETED_BY_OPERATOR / BORA_ACCEPTED (2026-09-11) / READ_ONLY_DESIGN_ONLY' in cp['terminal_adjudication']
assert 'COMPLETED_BY_OPERATOR / PENDING_BORA_ACCEPTANCE / READ_ONLY_DESIGN_ONLY' in cp['terminal_adjudication']
assert 'operator completion is explicitly not Bora acceptance' in cp['terminal_adjudication']
assert PHASE_F_PROPOSED_NOT_AUTHORIZED.search(cp['terminal_adjudication']), (
    'terminal_adjudication must couple Phase F to PROPOSED_NOT_AUTHORIZED as one subject'
)
assert 'IMPLEMENTATION NOT AUTHORIZED' in cp['terminal_adjudication']

# Must record the genuine Phase E substantive completion, and must preserve
# the Phase D prior-phase transition action, without re-authoring Phase D's
# own substantive report content.
completed = ' '.join(cp['completed_actions'])
assert 'CAREER_OS_SYSTEM_EVAL_SET_ARCHITECTURE_V1' in completed
assert 'docs/audits/CAREER_OS_SYSTEM_EVAL_SET_ARCHITECTURE_V1_REPORT.md' in completed
assert 'CAREER_OS_FAILURE_TAXONOMY_AND_EVALUATOR_COVERAGE_MAP_V1' in completed
assert 'prior_phase' in completed

# The Phase E completed_actions must state the case-row schema, executability
# classes, and the terminal-vs-step-diagnostic separation this report defines.
assert 'EXECUTABLE_NOW' in completed
assert 'RECONSTRUCTION_BACKED_DESIGN_CASE' in completed
assert 'BLOCKED_CANDIDATE' in completed
assert 'TERMINAL_END_TO_END' in completed
assert 'STEP_LEVEL_DIAGNOSTIC' in completed
assert 'tests/career_os_system_eval_set_architecture_v1_test.py' in completed

# FINAL hardened Phase E architecture facts must be reflected explicitly in
# this recovery summary, never left implicit or allowed to regress to a
# stale/looser prior draft's summary.
EXPECTED_15_CASE_IDS = (
    'F1-A', 'F1-B', 'F1-C', 'F1-D', 'F1-E',
    'F2-A', 'F2-B', 'F2-C',
    'F3-A', 'F4-A',
    'F5-A', 'F5-B',
    'REC-A',
    'POS-A', 'POS-B',
)
for case_id in EXPECTED_15_CASE_IDS:
    assert case_id in completed, f'checkpoint completed_actions must name admitted case {case_id}'
assert 'exactly 15 case IDs' in completed, (
    'checkpoint completed_actions must state the admitted corpus is exactly 15 case IDs'
)
for case_role in ('CONFIRMED_FAILURE_REGRESSION', 'IMPORTANT_WORKFLOW', 'POSITIVE_CONTINUITY_REFERENCE'):
    assert case_role in completed, f'checkpoint completed_actions must name case role {case_role}'
assert 'three-way case_role taxonomy' in completed
assert 'deterministic PASS/FAIL pairing requirement' in completed
assert 'Family 6' in completed and 'EXPERIMENTAL_NON_CANONICAL' in completed, (
    'checkpoint completed_actions must record that Family 6 has no admitted case '
    '(its only instance remains EXPERIMENTAL_NON_CANONICAL)'
)
assert 'Fresenius Medical Care R0266808 (F1-D)' in completed
assert 'MGB RQ4055007 (F1-E)' in completed
assert 'two separate, never-combined case identities' in completed
assert 'Public Consulting Group JR102087' in completed
assert 'never as a fabricated confirmed failure' in completed
assert 'HUMAN_CONFIRMED_REFERENCE, never machine-executable' in completed

# Continuity: Phase D's own corrected jargon/LLM-judge completed_actions
# entry (fixed by an earlier continuity repair) must remain unchanged.
_DASH_CHARS = ''.join(chr(code_point) for code_point in (
    0x002D, 0x2010, 0x2011, 0x2012, 0x2013, 0x2014, 0x2015, 0x2212,
))


def _normalize_for_jargon_judge_match(text):
    normalized = text
    for dash_char in _DASH_CHARS:
        normalized = normalized.replace(dash_char, ' ')
    normalized = re.sub(r'\s+', ' ', normalized).strip().lower()
    return normalized


jargon_judge_actions = [
    action for action in cp['phase_d_completed_actions_reference']
    if 'jargon' in _normalize_for_jargon_judge_match(action)
    and 'llm judge' in _normalize_for_jargon_judge_match(action)
]
assert len(jargon_judge_actions) == 1, (
    'expected exactly one phase_d_completed_actions_reference entry concerning jargon/internal '
    f'vocabulary and the calibrated LLM judge, found {len(jargon_judge_actions)}'
)
jargon_judge_action = jargon_judge_actions[0]

EXACT_JARGON_JUDGE_ACTION = (
    "Named CAREER_OS_RUN_TRACE_V1 only as an out-of-scope/future missing "
    "observability surface; recorded internal-jargon-leakage detection "
    "against an enumerable banned-term/internal-vocabulary list as "
    "deterministic-first, never an LLM-judge candidate; named a potential "
    "calibrated LLM judge only as a future candidate for genuinely subjective "
    "residual surfaces (package gold-family style/naturalness/fidelity) "
    "remaining after objective lexical/structural checks and human "
    "calibration; designed, specified, or implemented neither the LLM judge "
    "nor any deterministic jargon evaluator"
)
assert jargon_judge_action == EXACT_JARGON_JUDGE_ACTION, (
    'the identified jargon/LLM-judge phase_d_completed_actions_reference entry no longer '
    'matches the exact corrected sentence'
)

# Report itself must reuse the same deterministic-first / genuinely-subjective
# framing for its own sole LLM-judge candidate (DraftKings gold-family style
# fidelity), never repositioning jargon-lexicon detection as an LLM-judge
# candidate.
assert 'deterministic-first' in completed
assert 'POTENTIAL_CALIBRATED_LLM_JUDGE candidate to DraftKings' in completed

not_done = ' '.join(cp['not_completed_or_not_authorized'])
assert 'CAREER_OS_RUN_TRACE_V1' in not_done
assert 'trace infrastructure' in not_done
assert PHASE_F_PROPOSED_NOT_AUTHORIZED.search(not_done), (
    'not_completed_or_not_authorized must couple Phase F to PROPOSED_NOT_AUTHORIZED as one subject'
)
assert 'No production Career OS behavior changed' in not_done
assert 'CLAUDE.md' in not_done and '.cursor/rules' in not_done

# Phase E's operator completion must be pinned as never self-granted, and
# must be pinned as NOT itself constituting Bora's eventual acceptance --
# each with its own exact wording. Phase D's preserved report substance
# must also be explicitly reaffirmed unchanged.
assert 'recorded human event' in not_done
assert 'never self-granted by the operator' in not_done
assert "does not itself constitute Bora's eventual acceptance" in not_done
assert 'implementation_authorized remains false' in not_done
assert "Phase D's report substance" in not_done
assert 'COMPLETED_BY_OPERATOR / BORA_ACCEPTED (2026-09-11) / READ_ONLY_DESIGN_ONLY' in not_done

# Phase B, Phase C, the agent context/usage-efficiency policy milestone's,
# and Phase D's completed-action lineage must all survive as historical
# reference even though none is the live current phase.
assert 'phase_b_completed_actions_reference' in cp
assert 'phase_c_completed_actions_reference' in cp
assert 'policy_milestone_completed_actions_reference' in cp
assert 'phase_d_completed_actions_reference' in cp

assert PROJECT_STATE['current_phase'].startswith('CAREER_OS_SYSTEM_EVAL_SET_ARCHITECTURE_V1 (COMPLETED_BY_OPERATOR')
assert 'PENDING_BORA_ACCEPTANCE' in PROJECT_STATE['current_phase']
assert 'READ_ONLY_DESIGN_ONLY' in PROJECT_STATE['current_phase']
assert 'NO_IMPLEMENTATION_AUTHORIZED' in PROJECT_STATE['current_phase']
assert 'CAREER_OS_FAILURE_TAXONOMY_AND_EVALUATOR_COVERAGE_MAP_V1' in PROJECT_STATE['next_authorized_action']
assert 'COMPLETED_BY_OPERATOR / BORA_ACCEPTED (2026-09-11) / READ_ONLY_DESIGN_ONLY' in PROJECT_STATE['next_authorized_action']
assert PHASE_F_PROPOSED_NOT_AUTHORIZED.search(PROJECT_STATE['next_authorized_action']), (
    "project_state.next_authorized_action must couple Phase F to PROPOSED_NOT_AUTHORIZED as one subject"
)
assert 'CURRENT_EXECUTION_CHECKPOINT.json' in AGENTS
assert 'BORA_ACCEPTED (2026-09-11)' in AGENTS
assert 'GOVERNING' in AGENTS
assert 'COMPLETED_BY_OPERATOR / BORA_ACCEPTED (2026-09-11)' in AGENTS
# Phase D's own accepted state in AGENTS.md must be proven by the single
# non-collidable anchored block, not by the bare substring above (a strict
# prefix of the GOVERNANCE_ONLY policy milestone's own acceptance clause).
assert 'COMPLETED_BY_OPERATOR / BORA_ACCEPTED (2026-09-11) / READ_ONLY_DESIGN_ONLY' in AGENTS
assert 'COMPLETED_BY_OPERATOR / PENDING_BORA_ACCEPTANCE / READ_ONLY_DESIGN_ONLY' in AGENTS

# AGENTS.md must keep requiring project_state.json to be read before
# CURRENT_EXECUTION_CHECKPOINT.json, and must not restate a competing
# recovery order outside the single canonical ADR Section 6 order.
project_state_pos = AGENTS.find('`project_state.json`')
checkpoint_pos = AGENTS.find('`CURRENT_EXECUTION_CHECKPOINT.json`')
assert project_state_pos != -1, 'AGENTS.md no longer mentions project_state.json'
assert checkpoint_pos != -1, 'AGENTS.md no longer mentions CURRENT_EXECUTION_CHECKPOINT.json'
assert project_state_pos < checkpoint_pos, (
    'AGENTS.md must read project_state.json before CURRENT_EXECUTION_CHECKPOINT.json'
)
assert 'do not restate a different order elsewhere' in AGENTS
assert 'do not restate a different or partial order here' in AGENTS

# AGENTS.md must carry a concise pointer to the new context/usage-efficiency
# ADR without restating its policy body.
assert 'ADR-CAREER-OS-AGENT-CONTEXT-USAGE-EFFICIENCY-V1' in AGENTS
assert 'never overrides the Authority Order above' in AGENTS or 'never overrides' in AGENTS

print('PASS: Career OS execution checkpoint and fresh-chat handoff lock verified.')
