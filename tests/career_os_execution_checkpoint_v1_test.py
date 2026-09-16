import json
import re
from pathlib import Path

PHASE_H_PROPOSED_NOT_AUTHORIZED = re.compile(
    r'Phase H and every later roadmap phase remain \*{0,2}PROPOSED_NOT_AUTHORIZED\*{0,2}',
    re.IGNORECASE,
)
# Phase H is now COMPLETED_BY_OPERATOR / BORA_ACCEPTED; live surfaces now
# couple Phase I, not Phase H, to PROPOSED_NOT_AUTHORIZED.
PHASE_I_PROPOSED_NOT_AUTHORIZED = re.compile(
    r'Phase I and every later roadmap phase remain \*{0,2}PROPOSED_NOT_AUTHORIZED\*{0,2}',
    re.IGNORECASE,
)

ROOT = Path(__file__).resolve().parents[1]
CHECKPOINT = ROOT / 'CURRENT_EXECUTION_CHECKPOINT.json'
PROJECT_STATE = json.loads((ROOT / 'project_state.json').read_text(encoding='utf-8'))
AGENTS = (ROOT / 'AGENTS.md').read_text(encoding='utf-8')

assert CHECKPOINT.exists(), 'canonical execution checkpoint missing'
cp = json.loads(CHECKPOINT.read_text(encoding='utf-8'))

assert cp['schema_version'] == '1.0'
# Checkpoint lineage convention: checkpoint_ids track the live phase event.
# Phase H's checkpoint_id must now reflect its own substantive 2026-09-15
# acceptance event and Recommendation B's scoped authorization.
assert cp['checkpoint_id'] == 'CAREER_OS_CHECKPOINT_2026-09-15_RECOMMENDATION_B_ACCEPTED'
assert cp['canonical_basis_sha'] == 'e521c7972a345f48379304b3df0e9598bc6326b2'
assert cp['phase_id'] == 'CAREER_OS_MILESTONE_RUN_V1_TARGETED_OPTIMIZATION_V1'
assert cp['authorization_status'] == 'BORA_AUTHORIZED'
assert cp['selection_status'] == 'SELECTED'
assert cp['operator_status'] == 'COMPLETED_BY_OPERATOR'
assert cp['human_acceptance_status'] == 'BORA_ACCEPTED'
assert cp['accepted_at'] == '2026-09-15'
assert cp['implementation_authorized'] is False

phase_h = cp['phase_h_acceptance']
assert phase_h['phase_id'] == 'CAREER_OS_ASSURANCE_TIMING_OBSERVABILITY_V1'
assert phase_h['authorization_status'] == 'BORA_AUTHORIZED'
assert phase_h['selection_status'] == 'SELECTED'
assert phase_h['operator_status'] == 'COMPLETED_BY_OPERATOR'
assert phase_h['human_acceptance_status'] == 'BORA_ACCEPTED'
assert phase_h['accepted_at'] == '2026-09-15'
assert phase_h['implementation_authorization_scope'] == 'SCOPED_TO_THIS_MILESTONE_ONLY_NOT_GLOBAL'

rec_b = cp['recommendation_b_authorization']
assert rec_b['milestone_id'] == 'CAREER_OS_MILESTONE_RUN_V1_TARGETED_OPTIMIZATION_V1'
assert rec_b['authorization_status'] == 'BORA_AUTHORIZED'
assert rec_b['selection_status'] == 'SELECTED'
assert rec_b['operator_status'] == 'NOT_YET_COMPLETED'
comp = cp['recommendation_b_completion']
assert comp['operator_status'] == 'COMPLETED_BY_OPERATOR'
assert comp['human_acceptance_status'] == 'BORA_ACCEPTED'
assert comp['canonical_merge_verification'].find('PR #63') != -1
assert rec_b['implementation_authorization_scope'] == 'SCOPED_TO_THIS_MILESTONE_ONLY_NOT_GLOBAL'
assert rec_b['selected_from'] == 'PHASE_G_RECOMMENDATION_B_ONLY'
timing = rec_b['timing_evidence_threshold']
assert timing['local_run_1']['milestone_run_v1_test_py_seconds'] == 318.025429
assert timing['local_run_1']['phase_2_seconds'] == 415.069786
assert timing['local_run_2']['milestone_run_v1_test_py_seconds'] == 312.284460
assert timing['local_run_2']['phase_2_seconds'] == 406.363878
assert timing['hosted_post_merge_run']['milestone_run_v1_test_py_seconds'] == 12.904488
assert timing['hosted_post_merge_run']['phase_2_seconds'] == 29.252603
assert 'NOT_AUTHORIZED' in rec_b['recommendation_c_fast_diagnostic_runner']

# CAREER_OS_ASSURANCE_ARCHITECTURE_V1 (Phase G) must be recorded distinctly
# as prior_phase, never conflated with Phase H's own freshly accepted status.
prior_phase = cp['prior_phase']
assert prior_phase['phase_id'] == 'CAREER_OS_ASSURANCE_ARCHITECTURE_V1'
assert prior_phase['phase_mode'] == 'READ_ONLY_DESIGN_ONLY'
assert prior_phase['operator_status'] == 'COMPLETED_BY_OPERATOR'
assert prior_phase['human_acceptance_status'] == 'BORA_ACCEPTED'
assert prior_phase['accepted_at'] == '2026-09-14'

prior_prior_phase = cp['prior_prior_phase']
assert prior_prior_phase['phase_id'] == 'CAREER_OS_TRACE_AND_CONTRACT_ARCHITECTURE_V1'
assert prior_prior_phase['phase_mode'] == 'READ_ONLY_DESIGN_ONLY'
assert prior_prior_phase['operator_status'] == 'COMPLETED_BY_OPERATOR'
assert prior_prior_phase['human_acceptance_status'] == 'BORA_ACCEPTED'
assert prior_prior_phase['accepted_at'] == '2026-09-14'

prior_prior_prior_phase = cp['prior_prior_prior_phase']
assert prior_prior_prior_phase['phase_id'] == 'CAREER_OS_SYSTEM_EVAL_SET_ARCHITECTURE_V1'
assert prior_prior_prior_phase['phase_mode'] == 'READ_ONLY_DESIGN_ONLY'
assert prior_prior_prior_phase['human_acceptance_status'] == 'BORA_ACCEPTED'
assert prior_prior_prior_phase['accepted_at'] == '2026-09-12'

assert isinstance(cp['exact_next_allowed_action'], str) and cp['exact_next_allowed_action'].strip()

# terminal_adjudication must reflect the prior GOVERNING policy, Phase D/E/F/G's
# preserved acceptance, AND Phase H's acceptance plus Recommendation B's scoped
# authorization, while still stating Phase I is not authorized.
assert 'GOVERNANCE_ONLY / GOVERNING' in cp['terminal_adjudication']
assert 'COMPLETED_BY_OPERATOR / BORA_ACCEPTED (2026-09-11) / READ_ONLY_DESIGN_ONLY' in cp['terminal_adjudication']
assert 'COMPLETED_BY_OPERATOR / BORA_ACCEPTED (2026-09-12) / READ_ONLY_DESIGN_ONLY' in cp['terminal_adjudication']
assert 'COMPLETED_BY_OPERATOR / BORA_ACCEPTED (2026-09-14) / READ_ONLY_DESIGN_ONLY' in cp['terminal_adjudication']
assert 'I explicitly accept Phase F brother' in cp['terminal_adjudication']
assert 'CAREER_OS_ASSURANCE_ARCHITECTURE_V1' in cp['terminal_adjudication']
assert 'CAREER_OS_ASSURANCE_TIMING_OBSERVABILITY_V1' in cp['terminal_adjudication']
assert 'once we are proper to standard' in cp['terminal_adjudication']
assert 'done G lets keep going brother' in cp['terminal_adjudication']
assert 'beautiful work G once u cehck everything being up to standart' in cp['terminal_adjudication']
assert 'Done brother carry the same discipline and manner' in cp['terminal_adjudication']
assert 'CAREER_OS_MILESTONE_RUN_V1_TARGETED_OPTIMIZATION_V1' in cp['terminal_adjudication']
assert 'SCOPED_TO_THIS_MILESTONE_ONLY_NOT_GLOBAL' in cp['terminal_adjudication']
assert PHASE_I_PROPOSED_NOT_AUTHORIZED.search(cp['terminal_adjudication']), (
    'terminal_adjudication must couple Phase I to PROPOSED_NOT_AUTHORIZED as one subject'
)

# Must record the genuine Phase F/G substantive narrative (preserved, appended
# to rather than overwritten) AND the new Phase H acceptance / Recommendation B
# authorization transition.
completed = ' '.join(cp['phase_h_acceptance_recommendation_b_authorization_completed_actions_reference'])
assert 'CAREER_OS_ASSURANCE_ARCHITECTURE_V1' in completed
assert 'CAREER_OS_TRACE_AND_CONTRACT_ARCHITECTURE_V1' in completed
assert 'CAREER_OS_SYSTEM_EVAL_SET_ARCHITECTURE_V1' in completed
assert 'CAREER_OS_ASSURANCE_TIMING_OBSERVABILITY_V1' in completed
assert 'CAREER_OS_MILESTONE_RUN_V1_TARGETED_OPTIMIZATION_V1' in completed
assert 'prior_phase' in completed
assert 'prior_prior_phase' in completed
assert 'prior_prior_prior_phase' in completed
assert 'Done brother carry the same discipline and manner' in completed
assert '318.025429' in completed and '415.069786' in completed
assert '312.284460' in completed and '406.363878' in completed
assert '12.904488' in completed and '29.252603' in completed

# Phase E's full lifecycle narrative (case corpus, executability classes,
# terminal-vs-step separation) must be preserved as historical reference,
# never reproduced/re-authored inside the live completed_actions.
assert 'phase_e_completed_actions_reference' in cp
phase_e_reference = ' '.join(cp['phase_e_completed_actions_reference'])
EXPECTED_15_CASE_IDS = (
    'F1-A', 'F1-B', 'F1-C', 'F1-D', 'F1-E',
    'F2-A', 'F2-B', 'F2-C',
    'F3-A', 'F4-A',
    'F5-A', 'F5-B',
    'REC-A',
    'POS-A', 'POS-B',
)
for case_id in EXPECTED_15_CASE_IDS:
    assert case_id in phase_e_reference, f'checkpoint phase_e_completed_actions_reference must name admitted case {case_id}'
assert 'exactly 15 case IDs' in phase_e_reference, (
    'checkpoint phase_e_completed_actions_reference must state the admitted corpus is exactly 15 case IDs'
)
for case_role in ('CONFIRMED_FAILURE_REGRESSION', 'IMPORTANT_WORKFLOW', 'POSITIVE_CONTINUITY_REFERENCE'):
    assert case_role in phase_e_reference, f'checkpoint phase_e_completed_actions_reference must name case role {case_role}'
assert 'Family 6' in phase_e_reference and 'EXPERIMENTAL_NON_CANONICAL' in phase_e_reference, (
    'checkpoint phase_e_completed_actions_reference must record that Family 6 has no admitted case '
    '(its only instance remains EXPERIMENTAL_NON_CANONICAL)'
)
assert 'Fresenius Medical Care R0266808 (F1-D)' in phase_e_reference
assert 'MGB RQ4055007 (F1-E)' in phase_e_reference
assert 'two separate, never-combined case identities' in phase_e_reference
assert 'Public Consulting Group JR102087' in phase_e_reference
assert 'never as a fabricated confirmed failure' in phase_e_reference
assert 'HUMAN_CONFIRMED_REFERENCE, never machine-executable' in phase_e_reference

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

# Phase E's own reference must reuse the same deterministic-first /
# genuinely-subjective framing for its own sole LLM-judge candidate
# (DraftKings gold-family style fidelity), never repositioning
# jargon-lexicon detection as an LLM-judge candidate.
assert 'deterministic-first' in phase_e_reference
assert 'POTENTIAL_CALIBRATED_LLM_JUDGE candidate to DraftKings' in phase_e_reference

not_done = ' '.join(cp['not_completed_or_not_authorized'])
assert PHASE_I_PROPOSED_NOT_AUTHORIZED.search(not_done), (
    'not_completed_or_not_authorized must couple Phase I to PROPOSED_NOT_AUTHORIZED as one subject'
)
assert cp['implementation_authorized'] is False
assert 'Recommendation C' in not_done and 'NOT_AUTHORIZED' in not_done
assert 'No new engineering milestone is selected or authorized' in not_done
assert 'CAREER_OS_MILESTONE_RUN_V1_TARGETED_OPTIMIZATION_V1' not in not_done

# Phase B, Phase C, the agent context/usage-efficiency policy milestone's,
# Phase D's, and Phase E's completed-action lineage must all survive as
# historical reference even though none is the live current phase.
assert 'phase_b_completed_actions_reference' in cp
assert 'phase_c_completed_actions_reference' in cp
assert 'policy_milestone_completed_actions_reference' in cp
assert 'phase_d_completed_actions_reference' in cp
assert 'phase_e_completed_actions_reference' in cp

# Phase F's own original authorization-era completed_actions (true only
# before Phase F was operator-completed) must survive as a distinct
# machine-readable historical reference array, analogous to the earlier
# phase_d/phase_e_completed_actions_reference lineage.
assert 'phase_f_authorization_completed_actions_reference' in cp
phase_f_authorization_reference = ' '.join(cp['phase_f_authorization_completed_actions_reference'])
assert 'I authorize Phase F - Trace/Contract Architecture' in phase_f_authorization_reference
assert 'NOT_YET_COMPLETED' in phase_f_authorization_reference
assert 'career-os-phase-f-authorization-v1.json' in phase_f_authorization_reference

# The prior Phase G acceptance / Phase H authorization sync's own
# completed_actions must survive as a distinct historical reference array.
assert 'phase_g_acceptance_phase_h_authorization_completed_actions_reference' in cp
phase_g_acceptance_reference = ' '.join(cp['phase_g_acceptance_phase_h_authorization_completed_actions_reference'])
assert 'beautiful work G once u cehck everything being up to standart' in phase_g_acceptance_reference

assert PROJECT_STATE['current_phase'].startswith('CAREER_OS_ASSURANCE_TIMING_OBSERVABILITY_V1')
assert 'BORA_ACCEPTED (2026-09-15)' in PROJECT_STATE['current_phase']
assert 'CAREER_OS_MILESTONE_RUN_V1_TARGETED_OPTIMIZATION_V1' in PROJECT_STATE['current_phase']
assert 'PRIOR_IMPLEMENTATION_AUTHORITY_SCOPED_TO_THIS_MILESTONE_ONLY_NOT_GLOBAL_EXHAUSTED_BY_OPERATOR_COMPLETION' in PROJECT_STATE['current_phase']
assert 'CAREER_OS_ASSURANCE_ARCHITECTURE_V1' in PROJECT_STATE['next_authorized_action']
assert 'COMPLETED_BY_OPERATOR / BORA_ACCEPTED (2026-09-14) / READ_ONLY_DESIGN_ONLY' in PROJECT_STATE['next_authorized_action']
assert 'OPERATE FIRST / BUILD SECOND' in PROJECT_STATE['next_authorized_action']
assert 'No new engineering milestone is selected or authorized' in PROJECT_STATE['next_authorized_action']
assert PHASE_I_PROPOSED_NOT_AUTHORIZED.search(PROJECT_STATE['next_authorized_action']), (
    "project_state.next_authorized_action must couple Phase I to PROPOSED_NOT_AUTHORIZED as one subject"
)
assert 'CURRENT_EXECUTION_CHECKPOINT.json' in AGENTS
assert 'BORA_ACCEPTED (2026-09-11)' in AGENTS
assert 'GOVERNING' in AGENTS
assert 'COMPLETED_BY_OPERATOR / BORA_ACCEPTED (2026-09-11)' in AGENTS
# Phase D's own accepted state in AGENTS.md must be proven by the single
# non-collidable anchored block, not by the bare substring above (a strict
# prefix of the GOVERNANCE_ONLY policy milestone's own acceptance clause).
assert 'COMPLETED_BY_OPERATOR / BORA_ACCEPTED (2026-09-11) / READ_ONLY_DESIGN_ONLY' in AGENTS
assert 'COMPLETED_BY_OPERATOR / BORA_ACCEPTED (2026-09-12) / READ_ONLY_DESIGN_ONLY' in AGENTS
assert 'COMPLETED_BY_OPERATOR / BORA_ACCEPTED (2026-09-14) / READ_ONLY_DESIGN_ONLY' in AGENTS
assert 'CAREER_OS_ASSURANCE_ARCHITECTURE_V1' in AGENTS
assert 'CAREER_OS_ASSURANCE_TIMING_OBSERVABILITY_V1' in AGENTS
assert 'CAREER_OS_MILESTONE_RUN_V1_TARGETED_OPTIMIZATION_V1' in AGENTS
assert 'SCOPED_TO_THIS_MILESTONE_ONLY_NOT_GLOBAL' in AGENTS

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
