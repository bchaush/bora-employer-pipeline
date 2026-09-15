import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / 'milestone_contracts' / 'design' / 'career-os-phase-g-assurance-architecture-v1.json'
REPORT_PATH = ROOT / 'docs' / 'audits' / 'CAREER_OS_ASSURANCE_ARCHITECTURE_V1_REPORT.md'
CHECKPOINT_PATH = ROOT / 'CURRENT_EXECUTION_CHECKPOINT.json'

BASELINE_SHA = 'bb8ae10fa71adb663117a65d8c6176e23de29b42'

# ---------------------------------------------------------------------------
# Contract must exist, identify Phase G, and lock its baseline/kind/review.
# ---------------------------------------------------------------------------
assert CONTRACT_PATH.exists(), 'Phase G assurance-architecture milestone contract missing'
contract = json.loads(CONTRACT_PATH.read_text(encoding='utf-8'))
assert contract['milestone_id'] == 'CAREER_OS_ASSURANCE_ARCHITECTURE_V1'
assert contract['kind'] == 'READ_ONLY_AUDIT'
assert contract['baseline_sha'] == BASELINE_SHA
assert 'CURSOR_INDEPENDENT_ADVERSARIAL_REVIEW_REQUIRED_BEFORE_COMMIT' in contract['review_requirements']
assert 'NO_COMMIT_PUSH_PR_OR_MERGE_AUTHORIZED_BY_THIS_CONTRACT_ALONE' in contract['review_requirements']

FORBIDDEN_PATHS = (
    'BLUEPRINT.md', 'CLAUDE.md', 'GEMINI.md', '.cursor/**', '.cursorignore', '.claude/**',
    'src/**', 'schemas/**', 'claims/**', 'evidence/**', 'experiences/**', 'resume/**',
    'golden-tests/**', 'fixtures/**', 'config/**', 'prompts/**',
    'requirements.in', 'requirements-lock.txt', '.github/workflows/**',
    'scripts/verify_assurance_baseline.py',
)
for forbidden_path in FORBIDDEN_PATHS:
    assert forbidden_path in contract['forbidden_paths'], f'contract must forbid {forbidden_path}'

REQUIRED_TESTS_JOINED = ' '.join(contract['required_tests'])
assert 'python scripts/verify_assurance_baseline.py' in REQUIRED_TESTS_JOINED
assert 'python scripts/verify_milestone_state.py' in REQUIRED_TESTS_JOINED
assert 'git diff --check' in REQUIRED_TESTS_JOINED

EXPECTED_FOCUSED_VALIDATION_TESTS = (
    'python tests/career_os_assurance_architecture_v1_test.py',
    'python tests/career_os_phase_g_authorization_v1_test.py',
    'python tests/career_os_execution_checkpoint_v1_test.py',
    'python tests/career_os_eval_harness_sequence_v1_test.py',
    'python tests/career_os_trace_and_contract_architecture_v1_test.py',
    'python tests/career_os_phase_f_authorization_v1_test.py',
    'python tests/career_os_system_eval_set_architecture_v1_test.py',
    'python tests/career_os_failure_taxonomy_and_evaluator_coverage_map_v1_test.py',
    'python tests/career_os_agent_context_usage_efficiency_v1_test.py',
    'python tests/career_os_phase_d_authorization_v1_test.py',
    'python tests/career_os_phase_e_authorization_v1_test.py',
)
assert len(EXPECTED_FOCUSED_VALIDATION_TESTS) == 11

FULL_ASSURANCE_COMMAND = 'python scripts/verify_assurance_baseline.py'
MECHANICAL_ENVELOPE_CHECKS = (
    'python scripts/verify_milestone_state.py',
    'git diff --check',
)
ENVELOPE_COMMANDS_REMOVED_FROM_FOCUSED_SET = {FULL_ASSURANCE_COMMAND, *MECHANICAL_ENVELOPE_CHECKS}

# The 11-command focused TEST SET is required_tests minus exactly the three
# envelope commands -- this derivation is exact, not a superset/subset match.
computed_focused = tuple(cmd for cmd in contract['required_tests'] if cmd not in ENVELOPE_COMMANDS_REMOVED_FROM_FOCUSED_SET)
assert computed_focused == EXPECTED_FOCUSED_VALIDATION_TESTS
assert len(computed_focused) == 11
assert ENVELOPE_COMMANDS_REMOVED_FROM_FOCUSED_SET.issubset(set(contract['required_tests']))
# Full Assurance must never be a member of the focused TEST SET.
assert FULL_ASSURANCE_COMMAND not in EXPECTED_FOCUSED_VALIDATION_TESTS
assert FULL_ASSURANCE_COMMAND not in computed_focused
for envelope_check in MECHANICAL_ENVELOPE_CHECKS:
    assert envelope_check not in EXPECTED_FOCUSED_VALIDATION_TESTS
    assert envelope_check not in computed_focused

assert REPORT_PATH.exists(), 'substantive Phase G assurance architecture report missing'
report_text = REPORT_PATH.read_text(encoding='utf-8')
report_lower = report_text.lower()
checkpoint = json.loads(CHECKPOINT_PATH.read_text(encoding='utf-8'))
checkpoint_not_done = ' '.join(checkpoint['not_completed_or_not_authorized'])

# ---------------------------------------------------------------------------
# Status banner and epistemic discipline.
# ---------------------------------------------------------------------------
assert 'CAREER_OS_ASSURANCE_ARCHITECTURE_V1' in report_text
assert 'COMPLETED_BY_OPERATOR / PENDING_BORA_ACCEPTANCE / READ_ONLY_DESIGN_ONLY' in report_text
assert 'implementation_authorized' in report_text
assert 'PROPOSED_NOT_AUTHORIZED' in report_text
for label in ('OBSERVED', 'RECONSTRUCTED_FROM_DURABLE_EVIDENCE', 'EXPERIMENTAL_NON_CANONICAL', 'MISSING'):
    assert label in report_text, f'report must use evidence label {label}'

# ---------------------------------------------------------------------------
# The existing canonical full command remains the only promotion-authoritative
# full assurance path -- must be named exactly and stated as unmodified.
# ---------------------------------------------------------------------------
assert 'python scripts/verify_assurance_baseline.py' in report_text
assert 'sole promotion-authoritative local full-suite assurance gate' in report_text.lower() \
    or 'single promotion-authoritative full assurance path' in report_text.lower() \
    or 'single authoritative local full-suite assurance gate' in report_text.lower()
assert 'hosted CI command' in report_text
assert 'No assurance-runtime fast/slow-tier split, no assurance-runtime review' not in checkpoint_not_done
assert 'the read-only assurance-runtime review is complete as the Phase G design deliverable' in checkpoint_not_done

# ---------------------------------------------------------------------------
# Focused validation must be explicitly NON_AUTHORITATIVE and never able to
# authorize freeze/commit/push/PR/merge.
# ---------------------------------------------------------------------------
assert 'NON_AUTHORITATIVE' in report_text
assert '`required_tests` is the broader promotion-validation envelope' in report_text
assert 'MUST NOT be inherited wholesale into the focused loop' in report_text
for envelope_command in ENVELOPE_COMMANDS_REMOVED_FROM_FOCUSED_SET:
    assert envelope_command in report_text, f'report must name envelope command {envelope_command}'
assert 'after removing exactly these three envelope commands' in report_text
assert 'This subtraction rule for the focused TEST SET is exact and fail-closed' in report_text
assert 'never means' in report_text.lower() and 'assurance passed' in report_text.lower()
assert 'never grants freeze/commit/push/pr/merge authority' in report_text.lower() \
    or 'never grant freeze/commit/push/pr/merge authority' in report_text.lower()

# ---------------------------------------------------------------------------
# Authority terminology lock: milestone_state/git diff --check are separate
# MECHANICAL ENVELOPE checks run during iteration (not "promotion-only"), and
# only Full Assurance is the sole promotion-authoritative gate that must never
# enter the focused TEST SET or be re-added ahead of its own promotion run.
# The old self-contradictory framing (all three uniformly "promotion-only",
# and claimed to never be members of any broader focused-validation sequence)
# must not reappear.
# ---------------------------------------------------------------------------
assert 'MECHANICAL ENVELOPE' in report_text
assert 'mechanical envelope check' in report_lower
assert 'run after the focused test set' in report_lower or 'after the focused test set' in report_lower
assert 'during iteration' in report_lower
assert 'not solely at the promotion boundary' in report_lower
assert 'sole promotion-authoritative full-suite gate' in report_lower
assert 'must never enter the focused test set' in report_lower
assert 'must never be re-added earlier in the iteration sequence' in report_lower
# The retired self-contradictory phrase must not reappear anywhere.
assert 'the three promotion-only commands' not in report_lower
assert 'promotion-only commands' not in report_lower
assert 'never members of focused validation' not in report_lower
# milestone_state and git diff --check must never be labeled "promotion-only".
for envelope_check in MECHANICAL_ENVELOPE_CHECKS:
    assert envelope_check in report_text, f'report must name {envelope_check}'
assert 'routinely run as mechanical envelope checks' in report_lower

# ---------------------------------------------------------------------------
# Full assurance required before immutable freeze/review/promotion and after
# the final mutation; every mutation invalidates inherited green results.
# ---------------------------------------------------------------------------
assert 'mandatory before immutable freeze/review/promotion' in report_text.lower() \
    or 'required again after the final mutation' in report_text.lower()
assert 'every mutation invalidates' in report_text.lower()
assert 'full assurance is required again after the final mutation' in report_text.lower()
assert 'never substitute for full assurance' in report_text.lower() \
    or 'never substitutes for full assurance' in report_text.lower()

# ---------------------------------------------------------------------------
# milestone_run_v1_test.py preserved as consequential controller/meta-
# integration coverage, never globally excluded, and required in the focused
# loop whenever the changed causal surface touches controller logic.
# ---------------------------------------------------------------------------
assert 'milestone_run_v1_test.py' in report_text
assert 'controller/state-machine' in report_text.lower() or 'controller/meta-integration' in report_text.lower() \
    or 'controller/meta-integration coverage'.lower() in report_text.lower()
assert 'must be run directly in the focused loop even though it is slow' in report_text.lower()
assert 'not disposable noise' in report_text.lower()

# ---------------------------------------------------------------------------
# No static wall-clock threshold / no hardcoded global slow-test exclusion.
# ---------------------------------------------------------------------------
assert 'not hardcoded anywhere as globally excludable' in report_text.lower()
assert 'not based on a permanent' in report_text.lower() or 'never based on a permanent' in report_text.lower()
assert 'global slow-test exclusion list' in report_text.lower()

# ---------------------------------------------------------------------------
# Timing evidence must be labeled observed single-sample diagnostic evidence,
# not a reliability/SLA claim; must include the exact profiling figures.
# ---------------------------------------------------------------------------
assert 'single-sample' in report_text.lower()
assert 'not an sla' in report_text.lower() or 'never an sla' in report_text.lower()
for figure in ('3.118s', '416.406s', '1.248s', '420.772s', '0.447s', '318.741s', '35.100s', '15.247s', '5.089s'):
    assert figure in report_text, f'report must cite timing figure {figure}'
assert report_text.count('418.172s') == 1, 'invalid ALL_TOTAL may appear only once as retired evidence provenance'
assert 'RETIRED_AS_INVALID_EVIDENCE' in report_text
assert 'reused the variable `dt` inside the per-test loop' in report_text
assert abs((3.118 + 416.406 + 1.248) - 420.772) < 1e-9
assert '34915038186' in report_text
assert '~47s' in report_text or '47 seconds' in report_text.lower() or '47s' in report_text
assert 'environment-sensitive' in report_text.lower()
assert 'not that correctness or reliability differs' in report_text.lower() \
    or 'never a correctness or reliability comparison' in report_text.lower() \
    or 'no reliability or correctness inference' in report_text.lower()
# The retired invalid ALL_TOTAL figure (418.172s) and its rounded short form
# (~418s) may never be reused anywhere as valid runtime evidence -- only the
# recomputed ~420.772s displayed-component sum is a valid arithmetic figure.
assert '418s' not in report_text, 'retired rounded ~418s figure must not appear as valid runtime evidence'
assert '~420.772s' in report_text
assert 'never an observed wall-clock timer' in report_text.lower() \
    or 'not a separately observed wall-clock timer' in report_text.lower()

# ---------------------------------------------------------------------------
# Future timing observability / test optimization are Phase H recommendations
# only -- not implemented or authorized here.
# ---------------------------------------------------------------------------
assert 'Phase H' in report_text
for rec in ('A.', 'B.', 'C.'):
    assert rec in report_text, f'report must rank Phase H recommendation {rec}'
assert 'NON_AUTHORITATIVE_FOCUSED_DIAGNOSTIC' in report_text
assert 'none is selected, scheduled, or implemented by this report' in report_text.lower()

# ---------------------------------------------------------------------------
# No parallelism/sharding/cache/framework migration/second CI workflow is
# selected; no mutable fast allowlist/denylist is created.
# ---------------------------------------------------------------------------
NOT_SELECTED_PHRASES = (
    'parallel test execution',
    'test sharding',
    'cache-based test skipping',
    'pytest/framework migration',
    'mutable fast allowlist/denylist',
    'second ci workflow that bypasses the canonical full command',
)
report_lower = report_text.lower()
for phrase in NOT_SELECTED_PHRASES:
    assert phrase in report_lower, f'report must explicitly disclaim: {phrase}'

# ---------------------------------------------------------------------------
# No second canonical fast runner in V1.
# ---------------------------------------------------------------------------
assert 'no second canonical' in report_lower or 'not a second canonical' in report_lower

# ---------------------------------------------------------------------------
# No implementation/infrastructure selected or authorized.
# ---------------------------------------------------------------------------
NOT_AUTHORIZED_PHRASES = (
    'No change to `scripts/verify_assurance_baseline.py`',
    'No new runner script, CI workflow, database, UI, vendor, storage engine, orchestration runtime, provider abstraction, new agent, model router, or LLM judge.',
)
for phrase in NOT_AUTHORIZED_PHRASES:
    assert phrase in report_text, f'report must explicitly disclaim: {phrase}'

# ---------------------------------------------------------------------------
# Phase completion / authorization discipline.
# ---------------------------------------------------------------------------
assert 'Phase H and every later roadmap phase remain **PROPOSED_NOT_AUTHORIZED**' in report_text
assert 'not itself authorize' in report_lower or 'does not authorize phase h' in report_lower \
    or 'not authorize phase h or implementation' in report_lower
assert 'Cursor' in report_text and 'may not repair its own findings' in report_text
assert 'operator completion is explicitly' in report_lower and 'not' in report_lower and 'bora acceptance' in report_lower

# ---------------------------------------------------------------------------
# Mandatory Phase 2 coverage anchors must not be weakened -- report must name
# the nine anchors as preserved.
# ---------------------------------------------------------------------------
MANDATORY_ANCHORS = (
    'application_gate_golden_test.py',
    'posting_state_decision_wiring_v1_test.py',
    'alternative_qualification_branch_representation_v1_test.py',
)
for anchor in MANDATORY_ANCHORS:
    assert anchor in report_text, f'report must name mandatory coverage anchor {anchor}'
assert 'six schema smoke tests' in report_text.lower() or 'schema smoke test' in report_text.lower()

print('PASS: Career OS Phase G assurance architecture report verified.')
