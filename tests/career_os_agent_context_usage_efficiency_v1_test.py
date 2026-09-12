import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ADR = ROOT / 'docs' / 'decisions' / 'ADR-CAREER-OS-AGENT-CONTEXT-USAGE-EFFICIENCY-V1.md'
CONTRACT = ROOT / 'milestone_contracts' / 'governance' / 'career-os-agent-context-and-usage-efficiency-v1.json'
ACCEPTANCE_CONTRACT = ROOT / 'milestone_contracts' / 'governance' / 'career-os-agent-context-usage-efficiency-acceptance-v1.json'
CURRENT_MILESTONE = ROOT / 'CURRENT_MILESTONE.md'
CURRENT_STATE = ROOT / 'CURRENT_STATE.md'
CHANGELOG = ROOT / 'CHANGELOG.md'
AGENTS = (ROOT / 'AGENTS.md').read_text(encoding='utf-8')
BASELINE_SHA = 'ba6530498be3410e3524aacd1ff5fba0c815d8d0'
ACCEPTANCE_BASELINE_SHA = '7d795d6c06a67965d70d219e901f1c7f67328d58'

assert ADR.exists(), 'canonical agent context/usage-efficiency ADR missing'
text = ADR.read_text(encoding='utf-8')

# Every material claim must be source-labeled; the ADR must not assert
# doctrine without one of the four required labels present overall.
for label in ('SOURCE_DIRECT', 'CAREER_OS_ADAPTATION', 'OBSERVED_REPO_FACT', 'OPEN_HYPOTHESIS'):
    assert label in text, f'missing required source label: {label}'

# The 17 candidate policy principles, the Cursor economy rule, and the
# Claude economy rule must all be present.
for required in (
    'Quality/evidence/validation depth outrank quota conservation',
    'One bounded milestone per primary Claude/Cursor session',
    'Repository/checkpoint/Git state is durable memory',
    'Deterministic commands/tests/hashes/diffs/schema checks stay deterministic',
    'Smallest sufficient relevant context',
    'Exact-file targeting when known',
    'Avoid dumping full passing logs',
    'Subagents only when isolation of large/noisy exploration',
    'no unsupported cache folklore',
    'Never lower reasoning effort on consequential semantic/architecture/truth/debugging/adversarial-review work',
    'Cursor standard/ordinary context by default',
    'Do not disable required resume/cover-letter visual QA',
    'Use Claude `/context` and `/usage`',
    'never as a complete security boundary',
    'No numerical savings claims until Career OS itself measures them',
    'Context optimization must never weaken Candidate Truth',
    'Cursor economy rule',
    'Claude economy rule',
):
    assert required in text, f'missing candidate policy clause: {required}'

# Hard prohibitions for this governance-only milestone must be explicit.
for forbidden in (
    'No `BLUEPRINT.md`, `CLAUDE.md`, `.cursor/rules/*`, or `.cursorignore` change',
    'No `.claude/` settings/skills/subagents/hooks/context-loader restructuring',
    'No `src/`, `schemas/`, `claims/`, `evidence/`, `experiences/`, `resume/`, `golden-tests/` product/truth behavior change',
    'No Phase D taxonomy/evaluator work',
    'No `CAREER_OS_RUN_TRACE_V1`',
    'No unsupported savings percentage',
):
    assert forbidden in text, f'missing required prohibition: {forbidden}'

# The ADR must record OBSERVED_REPO_FACT baseline measurements and defer
# structural context-surface change as OPEN_HYPOTHESIS -- never assert a
# structural refactor is authorized here.
assert '2,860 bytes' in text and '78 lines' in text
assert '21,888 bytes' in text and '256 lines' in text
assert 'seven `alwaysApply: true` files' in text
assert 'deferred to a later, separately authorized, measured context-surface audit' in text

# The ADR's OBSERVED_REPO_FACT byte/line counts must match the exact git
# blob content at the recorded baseline commit -- not a CRLF-inflated
# disk-file measurement. Verified with deterministic local Git rather than
# by merely checking numerals in the ADR.
_BASELINE_FILE_COUNTS = {
    'CLAUDE.md': (2860, 78),
    'AGENTS.md': (21888, 256),
    '.cursor/rules/architecture.mdc': (5180, 175),
    '.cursor/rules/data-integrity.mdc': (5432, 212),
    '.cursor/rules/opt-safety.mdc': (9565, 247),
    '.cursor/rules/resume.mdc': (28832, 635),
    '.cursor/rules/role-selection.mdc': (16775, 244),
    '.cursor/rules/testing.mdc': (4908, 184),
    '.cursor/rules/truth.mdc': (3599, 126),
}
def _ensure_baseline_commit_available(sha):
    # CI checks out the PR merge ref with fetch-depth=1, so the historical
    # baseline commit object may be absent from the shallow clone even though
    # it is a real ancestor in the repo's full history. Fetch it directly
    # before relying on `git show <sha>:<path>` / `git ls-tree <sha>`.
    probe = subprocess.run(
        ['git', 'cat-file', '-e', f'{sha}^{{commit}}'], cwd=ROOT, capture_output=True,
    )
    if probe.returncode == 0:
        return
    fetch = subprocess.run(
        ['git', 'fetch', '--depth=1', 'origin', sha], cwd=ROOT, capture_output=True,
    )
    if fetch.returncode != 0:
        subprocess.run(
            ['git', 'fetch', '--unshallow', 'origin'], cwd=ROOT, capture_output=True,
        )
    probe = subprocess.run(
        ['git', 'cat-file', '-e', f'{sha}^{{commit}}'], cwd=ROOT, capture_output=True,
    )
    assert probe.returncode == 0, f'baseline commit {sha} unavailable even after fetch attempts'


_ensure_baseline_commit_available(BASELINE_SHA)

for rel_path, (expected_bytes, expected_lines) in _BASELINE_FILE_COUNTS.items():
    blob = subprocess.run(
        ['git', 'show', f'{BASELINE_SHA}:{rel_path}'],
        cwd=ROOT, capture_output=True, check=True,
    ).stdout
    actual_bytes = len(blob)
    actual_lines = blob.count(b'\n')
    assert actual_bytes == expected_bytes, (
        f'{rel_path} baseline byte count mismatch: git blob={actual_bytes}, expected={expected_bytes}'
    )
    assert actual_lines == expected_lines, (
        f'{rel_path} baseline line count mismatch: git blob={actual_lines}, expected={expected_lines}'
    )

# Verify the seven baseline .cursor/rules/*.mdc alwaysApply:true facts
# directly against the baseline git tree, fail closed on any mismatch.
_baseline_rules_listing = subprocess.run(
    ['git', 'ls-tree', '-r', '--name-only', BASELINE_SHA, '--', '.cursor/rules'],
    cwd=ROOT, capture_output=True, check=True,
).stdout.decode('utf-8').split()
assert set(_baseline_rules_listing) == {
    '.cursor/rules/architecture.mdc',
    '.cursor/rules/data-integrity.mdc',
    '.cursor/rules/opt-safety.mdc',
    '.cursor/rules/resume.mdc',
    '.cursor/rules/role-selection.mdc',
    '.cursor/rules/testing.mdc',
    '.cursor/rules/truth.mdc',
}, 'baseline .cursor/rules directory must contain exactly the seven recorded files'
for rel_path in _baseline_rules_listing:
    blob_text = subprocess.run(
        ['git', 'show', f'{BASELINE_SHA}:{rel_path}'],
        cwd=ROOT, capture_output=True, check=True,
    ).stdout.decode('utf-8')
    assert 'alwaysApply: true' in blob_text, f'{rel_path} must carry alwaysApply: true at baseline'

# ADR source-label fidelity: the Anthropic model-config bullet must not
# assert a blanket claim the cited docs do not make, and the Career OS
# no-bypass-default rule must live under CAREER_OS_ADAPTATION (Section 5),
# not be misattributed to the vendor SOURCE_DIRECT settings/permissions bullet.
assert 'high is a minimum for intelligence-sensitive work' not in text
assert 'xhigh is recommended default on supported Opus 4.7' not in text
assert "is Opus 4.7's default" in text
_settings_bullet_start = text.index('code.claude.com/docs/en/settings')
_settings_bullet_end = text.index('\n', _settings_bullet_start)
assert 'must not become the Career OS default' not in text[_settings_bullet_start:_settings_bullet_end], (
    'the Career OS no-bypass-default rule must not appear inside the vendor SOURCE_DIRECT settings/permissions bullet'
)
assert 'must not become the Career OS default' in text
# The consequential-work effort rule must remain unaltered by this correction pass.
assert 'Never lower reasoning effort on consequential semantic/architecture/truth/debugging/adversarial-review work merely to preserve quota' in text

# Status/decision must reflect Bora's explicit 2026-09-11 acceptance:
# governance-only, GOVERNING, with Phase D explicitly not authorized and
# implementation_authorized false.
assert 'BORA_ACCEPTED (2026-09-11)' in text
assert 'GOVERNANCE_ONLY' in text
assert 'GOVERNING' in text
assert 'PROPOSED_NOT_AUTHORIZED' in text
assert '`implementation_authorized` is `false`' in text

# The acceptance must be recorded as a genuine Bora human event, not an
# operator self-grant: the ADR must positively state Bora's explicit
# acceptance quote and must not claim the operator itself accepted or
# self-authorized the policy.
assert 'Bora explicitly accepted this ADR on 2026-09-11' in text
assert 'I accept CAREER_OS_AGENT_CONTEXT_AND_USAGE_EFFICIENCY_V1 as governing policy' in text
assert 'self-grant' not in text
assert 'DECISION (BORA_ACCEPTED, GOVERNING):' in text

# Section 5 must contain exactly 17 numbered candidate policy principles
# (lines beginning "1." through "17."), mechanically counted rather than
# assumed from the prose above.
_section5_start = text.index('## 5. Policy principles')
_section5_end = text.index('## 6. Cursor economy rule')
_section5_text = text[_section5_start:_section5_end]
_numbered_principles = re.findall(r'^(\d+)\. ', _section5_text, flags=re.MULTILINE)
assert _numbered_principles == [str(n) for n in range(1, 18)], (
    f'Section 5 must contain exactly 17 sequentially numbered principles (1-17), found: {_numbered_principles}'
)

assert CONTRACT.exists(), 'governance milestone contract missing'
contract = json.loads(CONTRACT.read_text(encoding='utf-8'))
assert contract['milestone_id'] == 'CAREER_OS_AGENT_CONTEXT_AND_USAGE_EFFICIENCY_V1'
assert contract['kind'] == 'GOVERNANCE_SYNC'
assert contract['baseline_sha'] == 'ba6530498be3410e3524aacd1ff5fba0c815d8d0'
for forbidden_path in ('BLUEPRINT.md', 'CLAUDE.md', '.cursor/**', '.cursorignore', '.claude/**', 'src/**', 'schemas/**', 'golden-tests/**'):
    assert forbidden_path in contract['forbidden_paths'], f'contract must forbid {forbidden_path}'
assert 'docs/decisions/ADR-CAREER-OS-AGENT-CONTEXT-USAGE-EFFICIENCY-V1.md' in contract['allowed_paths']

# The separate acceptance-sync contract governs this bounded correction
# pass (recording Bora's explicit acceptance) and must not be confused
# with the earlier ADR-authoring contract above.
assert ACCEPTANCE_CONTRACT.exists(), 'governance acceptance-sync milestone contract missing'
acceptance_contract = json.loads(ACCEPTANCE_CONTRACT.read_text(encoding='utf-8'))
assert acceptance_contract['baseline_sha'] == ACCEPTANCE_BASELINE_SHA

# The acceptance-sync contract schema forbids a top-level
# `implementation_authorized` property; the semantic invariant that
# implementation_authorized remains false and Phase D remains unauthorized
# must instead be carried in the contract's goal/acceptance_conditions/
# stop_conditions text, verified mechanically below.
assert 'implementation_authorized' not in acceptance_contract, (
    'acceptance_contract must not carry a top-level implementation_authorized property'
)
assert 'implementation_authorized remaining false' in acceptance_contract['goal']
assert 'Phase D remaining PROPOSED_NOT_AUTHORIZED' in acceptance_contract['goal']
assert any(
    'implementation_authorized=false' in condition or 'implementation_authorized as false' in condition
    for condition in acceptance_contract['acceptance_conditions']
), 'acceptance_conditions must preserve implementation_authorized=false as a checked invariant'
assert any(
    'Phase D PROPOSED_NOT_AUTHORIZED' in condition
    for condition in acceptance_contract['acceptance_conditions']
), 'acceptance_conditions must preserve Phase D PROPOSED_NOT_AUTHORIZED as a checked invariant'
assert any(
    'authorize or imply authorization of Phase D' in condition
    for condition in acceptance_contract['stop_conditions']
), 'stop_conditions must forbid authorizing or implying authorization of Phase D'
assert 'NO_IMPLEMENTATION_AUTHORIZED' in acceptance_contract['human_approval_requirements']

for forbidden_path in (
    'BLUEPRINT.md', 'CLAUDE.md', '.cursor/**', '.claude/**', 'src/**', 'schemas/**',
    'claims/**', 'evidence/**', 'experiences/**', 'resume/**', 'golden-tests/**',
):
    assert forbidden_path in acceptance_contract['forbidden_paths'], f'acceptance contract must forbid {forbidden_path}'
_expected_acceptance_allowed_paths = {
    'CHANGELOG.md',
    'CURRENT_EXECUTION_CHECKPOINT.json',
    'CURRENT_MILESTONE.md',
    'CURRENT_STATE.md',
    'docs/decisions/ADR-CAREER-OS-AGENT-CONTEXT-USAGE-EFFICIENCY-V1.md',
    'docs/decisions/ADR-CAREER-OS-EVAL-HARNESS-SEQUENCE-V1.md',
    'AGENTS.md',
    'project_state.json',
    'tests/career_os_agent_context_usage_efficiency_v1_test.py',
    'tests/career_os_execution_checkpoint_v1_test.py',
    'tests/career_os_eval_harness_sequence_v1_test.py',
    'milestone_contracts/governance/career-os-agent-context-usage-efficiency-acceptance-v1.json',
}
assert set(acceptance_contract['allowed_paths']) == _expected_acceptance_allowed_paths, (
    f'acceptance contract allowed_paths must be exactly the bounded correction-pass surface, got: {acceptance_contract["allowed_paths"]}'
)

# AGENTS.md must carry a concise operational pointer only -- it must not
# restate the full policy body (e.g. must not itself enumerate all 16
# principles verbatim).
assert 'ADR-CAREER-OS-AGENT-CONTEXT-USAGE-EFFICIENCY-V1' in AGENTS
assert 'Quality/evidence/validation depth outrank quota conservation' not in AGENTS
assert 'One bounded milestone per primary Claude/Cursor session' not in AGENTS

# CURRENT_MILESTONE.md's live checkpoint block must explicitly separate the
# PRIOR (already Bora-accepted, GOVERNING policy milestone) mode/operator/
# acceptance fields from the CURRENT Phase D authorization's own fields --
# no unscoped BORA_ACCEPTED / GOVERNANCE_ONLY may appear as if it applies to
# Phase D rather than to the prior policy milestone, and Phase D must read
# READ_ONLY_DESIGN_ONLY / BORA_AUTHORIZED / SELECTED / NOT_YET_COMPLETED.
milestone_text = CURRENT_MILESTONE.read_text(encoding='utf-8')
assert 'Prior-milestone operator status: **COMPLETED_BY_OPERATOR**' in milestone_text
assert 'Prior-milestone human acceptance: **BORA_ACCEPTED (2026-09-11)**' in milestone_text
assert 'Prior-milestone governing status: **GOVERNING**' in milestone_text
assert 'Current-phase mode: **READ_ONLY_DESIGN_ONLY**' in milestone_text
assert 'Current-phase operator status: **COMPLETED_BY_OPERATOR**' in milestone_text
assert 'Current-phase human acceptance status: **BORA_ACCEPTED (2026-09-11)**' in milestone_text
_checkpoint_block_end = milestone_text.index('## Eval & Harness Audit - Roadmap Reference')
_checkpoint_block = milestone_text[:_checkpoint_block_end]
assert 'Current phase: `CAREER_OS_FAILURE_TAXONOMY_AND_EVALUATOR_COVERAGE_MAP_V1`\nCurrent-phase mode: **READ_ONLY_DESIGN_ONLY**' in _checkpoint_block, (
    'the current Phase D line must be immediately followed by its own scoped fields, not unscoped prior-milestone fields'
)
assert '`implementation_authorized`: **false**' in _checkpoint_block, (
    'the current Phase D checkpoint block must explicitly record implementation_authorized as false'
)
assert (
    'Bora separately decides whether to authorize Phase E' in _checkpoint_block
), (
    'the current Phase D checkpoint block must identify the single next allowed seam as '
    "Bora's separate decision whether to authorize Phase E"
)
assert (
    'no Phase E or implementation work may begin' in _checkpoint_block
), (
    'the current Phase D checkpoint block must state that no Phase E or implementation work may begin '
    'absent that separate Bora authorization'
)
assert 'PROPOSED_NOT_AUTHORIZED' in _checkpoint_block

# CURRENT_STATE.md must record this policy as Bora-accepted and governing
# (a genuine human acceptance event, not operator self-acceptance), while
# also recording Phase D as Bora-accepted (COMPLETED_BY_OPERATOR / BORA_ACCEPTED)
# and implementation_authorized remaining false, with Phase E/later still
# PROPOSED_NOT_AUTHORIZED.
state_text = CURRENT_STATE.read_text(encoding='utf-8')
assert 'COMPLETED_BY_OPERATOR / BORA_ACCEPTED (2026-09-11) / GOVERNANCE_ONLY / GOVERNING' in state_text
assert 'not self-granted by the operator' in state_text
assert 'COMPLETED_BY_OPERATOR / BORA_ACCEPTED (2026-09-11)' in state_text
assert '`implementation_authorized` remains `false`' in state_text
assert 'PROPOSED_NOT_AUTHORIZED' in state_text
assert 'READ_ONLY_DESIGN_ONLY' in state_text
# Phase D's own accepted state must be proven by the single non-collidable
# anchored block, not by the bare COMPLETED_BY_OPERATOR / BORA_ACCEPTED
# (2026-09-11) substring above (a strict prefix of the GOVERNANCE_ONLY/
# GOVERNING policy clause) plus the separate, unanchored READ_ONLY_DESIGN_ONLY
# check above.
assert 'COMPLETED_BY_OPERATOR / BORA_ACCEPTED (2026-09-11) / READ_ONLY_DESIGN_ONLY' in state_text

# CHANGELOG.md must carry a dated entry recording Bora's explicit
# acceptance as a distinct historical event from the earlier candidate
# policy draft entry (preserved below it as historical, superseded record).
changelog_text = CHANGELOG.read_text(encoding='utf-8')
assert 'accepted by Bora (GOVERNANCE-ONLY, BORA ACCEPTED)' in changelog_text
assert 'GOVERNANCE-ONLY CANDIDATE POLICY, PENDING BORA ACCEPTANCE' in changelog_text
assert 'historical, superseded by the acceptance entry above' in changelog_text

print('PASS: Career OS agent context/usage-efficiency governance-only accepted policy verified.')
