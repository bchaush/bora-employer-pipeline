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
assert cp['canonical_basis_sha'] == CANONICAL_BASELINE_SHA
assert cp['phase_id'] == 'CAREER_OS_SYSTEM_EVAL_SET_ARCHITECTURE_V1'
assert cp['phase_mode'] == 'READ_ONLY_DESIGN_ONLY'
assert cp['authorization_status'] == 'BORA_AUTHORIZED'
assert cp['selection_status'] == 'SELECTED'
assert cp['operator_status'] == 'NOT_YET_COMPLETED'
assert cp['implementation_authorized'] is False
assert 'human_acceptance_status' not in cp, (
    'Phase E is not yet operator-completed, so the top-level checkpoint must not '
    'carry a human_acceptance_status/accepted_at for it'
)

# CAREER_OS_FAILURE_TAXONOMY_AND_EVALUATOR_COVERAGE_MAP_V1 (Phase D) must be
# recorded distinctly as prior_phase, never conflated with Phase E's own
# (not yet completed) status -- operator completion, Bora acceptance, and
# this new authorization must never collapse into one undifferentiated claim.
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
assert 'I authorize Phase E' in cp['exact_next_allowed_action']
assert PHASE_F_PROPOSED_NOT_AUTHORIZED.search(cp['exact_next_allowed_action']), (
    'exact_next_allowed_action must couple Phase F to PROPOSED_NOT_AUTHORIZED as one subject'
)

# This authorization is a Bora human event, and it must never be read as
# itself authorizing Phase F, or as itself constituting Phase E's eventual
# operator completion/Bora acceptance.
assert 'does not itself authorize Phase F' in cp['exact_next_allowed_action']
assert 'does not itself constitute' in cp['exact_next_allowed_action']
assert "Bora's separate, explicit authorization of Phase F" in cp['exact_next_allowed_action']
assert 'No Phase F and no implementation' in cp['exact_next_allowed_action']

# terminal_adjudication must reflect the prior GOVERNING policy, Phase D's
# preserved acceptance, AND Bora's explicit Phase E authorization event,
# while still stating implementation and Phase F are not authorized.
assert 'GOVERNANCE_ONLY / GOVERNING' in cp['terminal_adjudication']
assert 'COMPLETED_BY_OPERATOR / BORA_ACCEPTED (2026-09-11) / READ_ONLY_DESIGN_ONLY' in cp['terminal_adjudication']
assert 'BORA_AUTHORIZED / SELECTED / NOT_YET_COMPLETED / READ_ONLY_DESIGN_ONLY' in cp['terminal_adjudication']
assert PHASE_F_PROPOSED_NOT_AUTHORIZED.search(cp['terminal_adjudication']), (
    'terminal_adjudication must couple Phase F to PROPOSED_NOT_AUTHORIZED as one subject'
)
assert 'IMPLEMENTATION NOT AUTHORIZED' in cp['terminal_adjudication']

# Must record the genuine Phase E authorization action, and must preserve
# the Phase D prior-phase transition action, without re-authoring Phase D's
# own substantive report content.
completed = ' '.join(cp['completed_actions'])
assert 'CAREER_OS_SYSTEM_EVAL_SET_ARCHITECTURE_V1' in completed
assert 'I authorize Phase E' in completed
assert 'CAREER_OS_FAILURE_TAXONOMY_AND_EVALUATOR_COVERAGE_MAP_V1' in completed
assert 'prior_phase' in completed

# Continuity repair: completed_actions must state that enumerable
# banned/internal vocabulary (jargon-leakage) detection is deterministic-
# first, and that any potential calibrated LLM judge is limited to
# genuinely subjective residual surfaces (style/naturalness/fidelity) left
# over after objective lexical/structural checks and human calibration --
# never positioned as a shortcut for the deterministic jargon check itself.
# This must fail closed if the stale "jargon-leakage detection" framing
# (naming jargon-leakage as an LLM-judge candidate) returns.
#
# The joined `completed` string is insufficient on its own: distinct
# historical actions could each satisfy a different substring, letting the
# assertions pass even if no single action states the corrected semantics
# coherently. Identify the exact single completed_actions entry that
# concerns jargon/internal-vocabulary detection and the calibrated LLM
# judge, require there be exactly one such entry, and assert every
# corrected-semantics substring against that same entry.
# Fail-closed selector: detect the jargon/LLM-judge entry regardless of
# spaced/hyphenated/dash-variant surface form (e.g. "LLM judge",
# "LLM-judge", "calibrated-LLM-judge"), and regardless of case/whitespace,
# so a stale entry cannot slip past this check merely by swapping a space
# for a hyphen or another dash character.
_DASH_CHARS = ''.join(chr(code_point) for code_point in (
    0x002D,  # HYPHEN-MINUS
    0x2010,  # HYPHEN
    0x2011,  # NON-BREAKING HYPHEN
    0x2012,  # FIGURE DASH
    0x2013,  # EN DASH
    0x2014,  # EM DASH
    0x2015,  # HORIZONTAL BAR
    0x2212,  # MINUS SIGN
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
    'expected exactly one completed_actions entry concerning jargon/internal '
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
    'the identified jargon/LLM-judge completed_actions entry no longer '
    'matches the exact corrected sentence'
)

assert 'deterministic-first' in jargon_judge_action
assert 'never an LLM-judge candidate' in jargon_judge_action
assert 'style/naturalness/fidelity' in jargon_judge_action
assert 'after objective lexical/structural checks and human calibration' in jargon_judge_action

# Stale-phrase negative assertion: fail closed if jargon-leakage detection
# is ever renamed back into an LLM-judge candidate, anywhere in the
# preserved Phase D reference lineage.
phase_d_reference_joined = ' '.join(cp['phase_d_completed_actions_reference'])
assert 'gold-family style/naturalness/fidelity), jargon-leakage detection' not in phase_d_reference_joined
assert 'fidelity, jargon-leakage detection' not in phase_d_reference_joined

not_done = ' '.join(cp['not_completed_or_not_authorized'])
assert 'CAREER_OS_RUN_TRACE_V1' in not_done
assert 'trace infrastructure' in not_done
assert PHASE_F_PROPOSED_NOT_AUTHORIZED.search(not_done), (
    'not_completed_or_not_authorized must couple Phase F to PROPOSED_NOT_AUTHORIZED as one subject'
)
assert 'No production Career OS behavior changed' in not_done
assert 'CLAUDE.md' in not_done and '.cursor/rules' in not_done

# Phase E's authorization must be pinned as a genuine Bora human event, never
# an operator self-grant, and must be pinned as NOT itself performing
# substantive Phase E work -- each with its own exact wording so these
# invariants cannot silently regress into a vaguer, weaker claim. Phase D's
# preserved report substance must also be explicitly reaffirmed unchanged.
assert 'recorded human event' in not_done
assert 'never self-granted by the operator' in not_done
assert "does not itself perform, design, or begin any substantive Phase E" in not_done
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

assert PROJECT_STATE['current_phase'].startswith('CAREER_OS_SYSTEM_EVAL_SET_ARCHITECTURE_V1 (BORA_AUTHORIZED')
assert 'SELECTED' in PROJECT_STATE['current_phase']
assert 'NOT_YET_COMPLETED' in PROJECT_STATE['current_phase']
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
