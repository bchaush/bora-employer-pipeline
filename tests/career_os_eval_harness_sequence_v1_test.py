import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ADR = ROOT / 'docs' / 'decisions' / 'ADR-CAREER-OS-EVAL-HARNESS-SEQUENCE-V1.md'
AGENTS = (ROOT / 'AGENTS.md').read_text(encoding='utf-8')
MILESTONE = (ROOT / 'CURRENT_MILESTONE.md').read_text(encoding='utf-8')
CURRENT_STATE = (ROOT / 'CURRENT_STATE.md').read_text(encoding='utf-8')
PROJECT_STATE = json.loads((ROOT / 'project_state.json').read_text(encoding='utf-8'))

assert ADR.exists(), 'canonical eval/harness sequence ADR missing'
text = ADR.read_text(encoding='utf-8')

for required in (
    'CAREER_OS_EVAL_AND_HARNESS_AUDIT_V1',
    'COMPLETED_BY_OPERATOR',
    'BORA_ACCEPTED',
    'CAREER_OS_TRACE_AND_FAILURE_CORPUS_INVENTORY_V1',
    'BORA_AUTHORIZED',
    'NOT_YET_COMPLETED',
    'NO IMPLEMENTATION OR LATER PHASE AUTHORIZED',
    'IndyDevDan', 'Hamel Husain', 'Cole Medin',
    'ChatGPT', 'architect / semantic adjudicator / initiator',
    'Claude Code', 'bounded implementation builder',
    'Cursor', 'independent adversarial reviewer',
    'No LLM judge for an objective fact',
    'real-trace/error inventory',
    'failure taxonomy/evaluator map',
):
    assert required in text, f'missing locked sequence clause: {required}'

# Recovery Section 6 must still name the single canonical recovery order
# and must not silently drop the requirement to state the current phase
# and exactly one next allowed action before work begins.
assert 'New-chat recovery protocol' in text
assert 'exactly one next allowed action' in text

# Mechanically reject reintroducing corrected contradictions: neither
# Phase B nor Phase C may regress to a stale prior-state description
# once Bora has accepted Phase B and authorized Phase C.
for stale in (
    'READ-ONLY AUDIT SELECTED / NO IMPLEMENTATION AUTHORIZED',
    'the next authorized phase is **Phase B',
    'CURRENT AUTHORITY:** Phase B only',
    'PENDING_BORA_ACCEPTANCE',
    'CAREER_OS_TRACE_AND_FAILURE_CORPUS_INVENTORY_V1`) is proposed and **PROPOSED_NOT_AUTHORIZED**',
):
    assert stale not in text, f'stale contradictory wording reintroduced in ADR: {stale}'

# Phase D and later must remain explicitly not authorized even though
# Phase C itself is now authorized.
assert 'PROPOSED_NOT_AUTHORIZED' in text
assert 'Phase D' in text

assert 'CAREER_OS_EVAL_AND_HARNESS_AUDIT_V1' in AGENTS
assert 'do not jump directly to implementation' in AGENTS
assert 'COMPLETED_BY_OPERATOR and BORA_ACCEPTED' in AGENTS
assert 'CAREER_OS_TRACE_AND_FAILURE_CORPUS_INVENTORY_V1' in AGENTS
assert 'NOT_YET_COMPLETED' in AGENTS
assert 'SELECTED / READ-ONLY / NO IMPLEMENTATION AUTHORIZED' not in AGENTS
assert 'PENDING_BORA_ACCEPTANCE' not in AGENTS

assert 'COMPLETED_BY_OPERATOR / BORA_ACCEPTED' in MILESTONE
assert 'BORA_AUTHORIZED / SELECTED / READ_ONLY / NOT_YET_COMPLETED' in MILESTONE
assert 'PROPOSED_NOT_AUTHORIZED' in MILESTONE
assert 'Status: **SELECTED / READ-ONLY / NO IMPLEMENTATION AUTHORIZED**' not in MILESTONE
assert 'PENDING_BORA_ACCEPTANCE' not in MILESTONE
assert str(ADR.relative_to(ROOT)).replace('\\', '/') in MILESTONE

assert 'CAREER_OS_EVAL_AND_HARNESS_AUDIT_V1' in CURRENT_STATE
assert 'COMPLETED_BY_OPERATOR / BORA_ACCEPTED' in CURRENT_STATE
assert 'BORA_AUTHORIZED / SELECTED / READ_ONLY / NOT_YET_COMPLETED' in CURRENT_STATE
assert '**SELECTED / READ-ONLY / NO IMPLEMENTATION AUTHORIZED**' not in CURRENT_STATE
assert 'PENDING_BORA_ACCEPTANCE' not in CURRENT_STATE

assert PROJECT_STATE['current_phase'].startswith('CAREER_OS_TRACE_AND_FAILURE_CORPUS_INVENTORY_V1')
assert 'BORA_AUTHORIZED' in PROJECT_STATE['current_phase']
assert 'NOT_YET_COMPLETED' in PROJECT_STATE['current_phase']
assert 'NO_IMPLEMENTATION_AUTHORIZED' in PROJECT_STATE['current_phase']
assert 'PROPOSED_NOT_AUTHORIZED' in PROJECT_STATE['next_authorized_action']
assert 'No product automation' in PROJECT_STATE['next_authorized_action']
assert PROJECT_STATE['semantic_state_updated_at'] == '2026-09-11'

AUDIT_REPORT = ROOT / 'docs' / 'audits' / 'CAREER_OS_EVAL_AND_HARNESS_AUDIT_V1_REPORT.md'
assert AUDIT_REPORT.exists(), 'durable Phase B operator audit report missing'
report_text = AUDIT_REPORT.read_text(encoding='utf-8')
assert 'OPERATOR AUDIT REPORT / BORA ACCEPTED' in report_text
assert 'BORA ACCEPTED' in report_text
assert 'does not itself authorize' in report_text

# The report is historical Phase B material that Bora has already accepted.
# It must not carry residual "not yet accepted" / pending-acceptance wording,
# and its findings lineage must point at the historical Phase B reference
# list, not be conflated with the live authorization-only completed_actions
# entry on the current Phase C START checkpoint.
for stale in (
    'not yet Bora-accepted',
    'not yet accepted',
    'PENDING_BORA_ACCEPTANCE',
    'pending acceptance',
    'pending-acceptance',
):
    assert stale not in report_text, f'stale pending-acceptance wording in audit report: {stale}'

assert 'phase_b_completed_actions_reference' in report_text, (
    'audit report findings must cite phase_b_completed_actions_reference lineage'
)
assert "the `completed_actions` already recorded" not in report_text, (
    'audit report must not claim its Phase B findings come from the live completed_actions field'
)
assert 'does not constitute acceptance of the current Phase C START checkpoint' in report_text

print('PASS: Career OS eval/harness roadmap and cold-start recovery lock verified.')
