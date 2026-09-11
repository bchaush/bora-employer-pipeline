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
    'READ-ONLY AUDIT SELECTED / NO IMPLEMENTATION AUTHORIZED',
    'CAREER_OS_EVAL_AND_HARNESS_AUDIT_V1',
    'IndyDevDan', 'Hamel Husain', 'Cole Medin',
    'ChatGPT — architect / semantic adjudicator / initiator',
    'Claude Code — bounded implementation builder',
    'Cursor — independent adversarial reviewer',
    'No LLM judge for an objective fact',
    'audit → real-trace/error inventory → failure taxonomy/evaluator map',
):
    assert required in text, f'missing locked sequence clause: {required}'

assert 'CAREER_OS_EVAL_AND_HARNESS_AUDIT_V1' in AGENTS
assert 'do not jump directly to implementation' in AGENTS
assert 'SELECTED / READ-ONLY / NO IMPLEMENTATION AUTHORIZED' in MILESTONE
assert str(ADR.relative_to(ROOT)).replace('\\', '/') in MILESTONE
assert 'CAREER_OS_EVAL_AND_HARNESS_AUDIT_V1' in CURRENT_STATE
assert PROJECT_STATE['current_phase'].startswith('CAREER_OS_EVAL_AND_HARNESS_AUDIT_V1')
assert 'No product automation' in PROJECT_STATE['next_authorized_action']
assert PROJECT_STATE['semantic_state_updated_at'] == '2026-09-10'

print('PASS: Career OS eval/harness roadmap and cold-start recovery lock verified.')
