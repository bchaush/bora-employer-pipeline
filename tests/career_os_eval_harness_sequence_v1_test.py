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
    'PENDING_BORA_ACCEPTANCE',
    'NO PHASE C OR LATER IMPLEMENTATION AUTHORIZED',
    'IndyDevDan', 'Hamel Husain', 'Cole Medin',
    'ChatGPT', 'architect / semantic adjudicator / initiator',
    'Claude Code', 'bounded implementation builder',
    'Cursor', 'independent adversarial reviewer',
    'No LLM judge for an objective fact',
    'real-trace/error inventory',
    'failure taxonomy/evaluator map',
):
    assert required in text, f'missing locked sequence clause: {required}'

# Mechanically reject reintroducing the corrected contradiction: Phase B must
# never again be presented as merely selected / next to run once it is
# operator-complete and pending Bora acceptance.
for stale in (
    'READ-ONLY AUDIT SELECTED / NO IMPLEMENTATION AUTHORIZED',
    'the next authorized phase is **Phase B',
    'CURRENT AUTHORITY:** Phase B only',
):
    assert stale not in text, f'stale contradictory Phase-B-selected wording reintroduced in ADR: {stale}'

assert 'CAREER_OS_EVAL_AND_HARNESS_AUDIT_V1' in AGENTS
assert 'do not jump directly to implementation' in AGENTS
assert 'COMPLETED_BY_OPERATOR and PENDING_BORA_ACCEPTANCE' in AGENTS
assert 'SELECTED / READ-ONLY / NO IMPLEMENTATION AUTHORIZED' not in AGENTS

assert 'COMPLETED_BY_OPERATOR / PENDING_BORA_ACCEPTANCE' in MILESTONE
assert 'PROPOSED_NOT_AUTHORIZED' in MILESTONE
assert 'Status: **SELECTED / READ-ONLY / NO IMPLEMENTATION AUTHORIZED**' not in MILESTONE
assert str(ADR.relative_to(ROOT)).replace('\\', '/') in MILESTONE

assert 'CAREER_OS_EVAL_AND_HARNESS_AUDIT_V1' in CURRENT_STATE
assert 'COMPLETED_BY_OPERATOR / PENDING_BORA_ACCEPTANCE' in CURRENT_STATE
assert 'PROPOSED_NOT_AUTHORIZED' in CURRENT_STATE
assert '**SELECTED / READ-ONLY / NO IMPLEMENTATION AUTHORIZED**' not in CURRENT_STATE

assert PROJECT_STATE['current_phase'].startswith('CAREER_OS_EVAL_AND_HARNESS_AUDIT_V1')
assert 'COMPLETED_BY_OPERATOR' in PROJECT_STATE['current_phase']
assert 'PENDING_BORA_ACCEPTANCE' in PROJECT_STATE['current_phase']
assert 'PROPOSED_NOT_AUTHORIZED' in PROJECT_STATE['next_authorized_action']
assert 'No product automation' in PROJECT_STATE['next_authorized_action']
assert PROJECT_STATE['semantic_state_updated_at'] == '2026-09-10'

AUDIT_REPORT = ROOT / 'docs' / 'audits' / 'CAREER_OS_EVAL_AND_HARNESS_AUDIT_V1_REPORT.md'
assert AUDIT_REPORT.exists(), 'durable Phase B operator audit report missing'
report_text = AUDIT_REPORT.read_text(encoding='utf-8')
assert 'OPERATOR AUDIT REPORT / PENDING BORA ACCEPTANCE' in report_text
assert 'not accepted Career OS doctrine' in report_text

print('PASS: Career OS eval/harness roadmap and cold-start recovery lock verified.')
