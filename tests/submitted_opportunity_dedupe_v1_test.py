from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BLUEPRINT=(ROOT/'BLUEPRINT.md').read_text(encoding='utf-8')
RULE=(ROOT/'.cursor'/'rules'/'role-selection.mdc').read_text(encoding='utf-8')
AGENTS=(ROOT/'AGENTS.md').read_text(encoding='utf-8')

def req(c,m):
    if not c: raise SystemExit('FAIL: '+m)

req('SUBMITTED_OPPORTUNITY_DEDUPE_V1' in BLUEPRINT,'blueprint marker missing')
req('same employer + exact requisition/opportunity identity' in BLUEPRINT,'exact identity rule missing')
req('already applied' in BLUEPRINT,'first-party already-applied rule missing')
req('A durable package folder by itself is not proof of submission.' in BLUEPRINT,'package-folder boundary missing')
for s in ['SUBMITTED','INTERVIEWING','REJECTED','WITHDRAWN','OFFER','CLOSED']:
    req(s in BLUEPRINT,f'lifecycle state {s} missing')
req('PREPARING' in BLUEPRINT and 'READY_FOR_REVIEW' in BLUEPRINT,'in-progress continuation rule missing')
req('fuzzy company matching' in BLUEPRINT,'fuzzy-match prohibition missing')
req('SUBMITTED_OPPORTUNITY_DEDUPE_V1' in RULE,'role-selection lock missing')
req('SUBMITTED_OPPORTUNITY_DEDUPE_V1' in AGENTS,'AGENTS operational lock missing')
print('PASS: submitted-opportunity dedupe doctrine locked across canonical operating surfaces.')
