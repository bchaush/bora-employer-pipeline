import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECKPOINT = ROOT / 'CURRENT_EXECUTION_CHECKPOINT.json'
PROJECT_STATE = json.loads((ROOT / 'project_state.json').read_text(encoding='utf-8'))
AGENTS = (ROOT / 'AGENTS.md').read_text(encoding='utf-8')

CANONICAL_BASELINE_SHA = '4902f74a9282ba00f77ae2badf2b8e0139dbc7f1'

assert CHECKPOINT.exists(), 'canonical execution checkpoint missing'
cp = json.loads(CHECKPOINT.read_text(encoding='utf-8'))

assert cp['schema_version'] == '1.0'
assert cp['canonical_basis_sha'] == CANONICAL_BASELINE_SHA
assert cp['phase_id'] == 'CAREER_OS_FAILURE_TAXONOMY_AND_EVALUATOR_COVERAGE_MAP_V1'
assert cp['phase_mode'] == 'READ_ONLY_DESIGN_ONLY'
assert cp['authorization_status'] == 'BORA_AUTHORIZED'
assert cp['selection_status'] == 'SELECTED'
assert cp['operator_status'] == 'COMPLETED_BY_OPERATOR'
assert cp['human_acceptance_status'] == 'BORA_ACCEPTED'
assert cp['accepted_at'] == '2026-09-11'
assert cp['implementation_authorized'] is False

# The governance-only agent context/usage-efficiency policy milestone must
# be recorded distinctly from this new Phase D authorization -- operator
# completion, Bora acceptance/authorization, and next-phase authorization
# must never collapse into one undifferentiated claim.
prior_phase = cp['prior_phase']
assert prior_phase['phase_id'] == 'CAREER_OS_AGENT_CONTEXT_AND_USAGE_EFFICIENCY_V1'
assert prior_phase['phase_mode'] == 'GOVERNANCE_ONLY'
assert prior_phase['operator_status'] == 'COMPLETED_BY_OPERATOR'
assert prior_phase['human_acceptance_status'] == 'BORA_ACCEPTED'
assert prior_phase['accepted_at'] == '2026-09-11'

prior_prior_phase = cp['prior_prior_phase']
assert prior_prior_phase['phase_id'] == 'CAREER_OS_TRACE_AND_FAILURE_CORPUS_INVENTORY_V1'
assert prior_prior_phase['phase_mode'] == 'READ_ONLY'
assert prior_prior_phase['human_acceptance_status'] == 'BORA_ACCEPTED'

assert isinstance(cp['exact_next_allowed_action'], str) and cp['exact_next_allowed_action'].strip()
assert 'COMPLETED_BY_OPERATOR / BORA_ACCEPTED (2026-09-11) / READ_ONLY_DESIGN_ONLY' in cp['exact_next_allowed_action']
assert 'I am satisfied' in cp['exact_next_allowed_action']
assert 'implementation_authorized remains false' in cp['exact_next_allowed_action']
assert 'Phase E' in cp['exact_next_allowed_action']

# The Phase D acceptance is a Bora human event, and that acceptance must
# never be read as itself authorizing Phase E: this must be proven by exact
# wording in the machine-readable seam field, not merely inferred from
# nearby PROPOSED_NOT_AUTHORIZED text elsewhere.
assert 'Bora separately decides whether to authorize Phase E' in cp['exact_next_allowed_action']
assert 'does not itself authorize Phase E' in cp['exact_next_allowed_action']
assert (
    "does not itself constitute that separate decision" in cp['exact_next_allowed_action']
    or "never self-granted" in cp['exact_next_allowed_action']
)
assert "Absent Bora's separate, explicit authorization of Phase E" in cp['exact_next_allowed_action']
assert 'no Phase E and no implementation' in cp['exact_next_allowed_action']

# terminal_adjudication must reflect the prior GOVERNING policy AND Bora's
# explicit Phase D acceptance event, while still stating implementation and
# Phase E are not authorized.
assert 'GOVERNANCE_ONLY / GOVERNING' in cp['terminal_adjudication']
assert 'COMPLETED_BY_OPERATOR / BORA_ACCEPTED (2026-09-11) / READ_ONLY_DESIGN_ONLY' in cp['terminal_adjudication']
assert 'PROPOSED_NOT_AUTHORIZED' in cp['terminal_adjudication']
assert 'IMPLEMENTATION NOT AUTHORIZED' in cp['terminal_adjudication']

# Must record the genuine substantive Phase D completion action, including
# the durable report path, and Bora's acceptance of it.
completed = ' '.join(cp['completed_actions'])
assert 'CAREER_OS_FAILURE_TAXONOMY_AND_EVALUATOR_COVERAGE_MAP_V1' in completed
assert 'docs/audits/CAREER_OS_FAILURE_TAXONOMY_AND_EVALUATOR_COVERAGE_MAP_V1_REPORT.md' in completed
assert 'I am satisfied' in completed

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
    action for action in cp['completed_actions']
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
# is ever renamed back into an LLM-judge candidate, on this entry or any
# other completed_actions entry.
assert 'gold-family style/naturalness/fidelity), jargon-leakage detection' not in completed
assert 'fidelity, jargon-leakage detection' not in completed

not_done = ' '.join(cp['not_completed_or_not_authorized'])
assert 'BORA_ACCEPTED' in not_done
assert 'CAREER_OS_RUN_TRACE_V1' in not_done
assert 'trace infrastructure' in not_done
assert 'Phase E' in not_done or 'later' in not_done
assert 'No production Career OS behavior changed' in not_done
assert 'CLAUDE.md' in not_done and '.cursor/rules' in not_done

# Phase D acceptance must be pinned as a genuine Bora human event, never an
# operator self-grant, and must be pinned as NOT itself authorizing Phase E,
# implementation, or any later phase -- each with its own exact wording so
# these invariants cannot silently regress into a vaguer, weaker claim.
assert 'recorded human event' in not_done
assert 'never self-granted by the operator' in not_done
assert 'does not itself authorize Phase E' in not_done
assert 'implementation_authorized remains false' in not_done

# Phase B, Phase C, and the agent context/usage-efficiency policy
# milestone's completed-action lineage must all survive as historical
# reference even though none is the live current phase.
assert 'phase_b_completed_actions_reference' in cp
assert 'phase_c_completed_actions_reference' in cp
assert 'policy_milestone_completed_actions_reference' in cp

assert PROJECT_STATE['current_phase'].startswith('CAREER_OS_FAILURE_TAXONOMY_AND_EVALUATOR_COVERAGE_MAP_V1 (COMPLETED_BY_OPERATOR')
assert 'BORA_ACCEPTED (2026-09-11)' in PROJECT_STATE['current_phase']
assert 'READ_ONLY_DESIGN_ONLY' in PROJECT_STATE['current_phase']
assert 'NO_IMPLEMENTATION_AUTHORIZED' in PROJECT_STATE['current_phase']
assert 'CAREER_OS_FAILURE_TAXONOMY_AND_EVALUATOR_COVERAGE_MAP_V1' in PROJECT_STATE['next_authorized_action']
assert 'COMPLETED_BY_OPERATOR / BORA_ACCEPTED (2026-09-11)' in PROJECT_STATE['next_authorized_action']
assert 'Phase E' in PROJECT_STATE['next_authorized_action']
assert 'PROPOSED_NOT_AUTHORIZED' in PROJECT_STATE['next_authorized_action']
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
