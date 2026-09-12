import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / 'milestone_contracts' / 'audit' / 'career-os-failure-taxonomy-evaluator-coverage-map-v1.json'
REPORT_PATH = ROOT / 'docs' / 'audits' / 'CAREER_OS_FAILURE_TAXONOMY_AND_EVALUATOR_COVERAGE_MAP_V1_REPORT.md'
CHECKPOINT_PATH = ROOT / 'CURRENT_EXECUTION_CHECKPOINT.json'
PROJECT_STATE_PATH = ROOT / 'project_state.json'
CHANGELOG_PATH = ROOT / 'CHANGELOG.md'
AGENTS_PATH = ROOT / 'AGENTS.md'
ADR_PATH = ROOT / 'docs' / 'decisions' / 'ADR-CAREER-OS-EVAL-HARNESS-SEQUENCE-V1.md'

BASELINE_SHA = '7f46768fab51beb4f5c2e8576dedfce691a7ee12'

assert CONTRACT_PATH.exists(), 'Phase D substantive-work milestone contract missing'
contract = json.loads(CONTRACT_PATH.read_text(encoding='utf-8'))
assert contract['milestone_id'] == 'CAREER_OS_FAILURE_TAXONOMY_AND_EVALUATOR_COVERAGE_MAP_V1'
assert contract['kind'] == 'READ_ONLY_AUDIT'
assert contract['baseline_sha'] == BASELINE_SHA

# This regression now governs the SUBSTANTIVE Phase D completion step: the
# report must exist and satisfy the epistemic/scope discipline the contract
# and the governing prompt require.
assert REPORT_PATH.exists(), 'substantive Phase D failure-taxonomy/evaluator-coverage-map report missing'
report_text = REPORT_PATH.read_text(encoding='utf-8')

# Every material claim must be labeled with one of the four provenance
# states; none may be upgraded from UNKNOWN/MISSING.
for label in ('OBSERVED', 'RECONSTRUCTED_FROM_DURABLE_EVIDENCE', 'EXPERIMENTAL_NON_CANONICAL', 'MISSING'):
    assert label in report_text, f'report must use provenance label {label}'

# The six provisional failure families must all be present by exact name.
FAILURE_FAMILIES = (
    'LIVE_OPPORTUNITY_ACTIONABILITY_IDENTITY_ROUTE_FAILURE',
    'PACKAGE_SPAWN_AND_CANDIDATE_ARTIFACT_QUALITY_FAILURE',
    'CONTROLLER_REVIEWER_EVIDENCE_INTEGRITY_FAILURE',
    'PROVIDER_SESSION_TRANSPORT_RECOVERABILITY_FAILURE',
    'APPLICATION_LIFECYCLE_DUPLICATE_CONTINUITY_FAILURE',
    'SEMANTIC_CONTRACT_ARCHITECTURE_FIDELITY_FAILURE',
)
for family in FAILURE_FAMILIES:
    assert family in report_text, f'report must name failure family {family}'

# Severity vocabulary must be present and explicitly stated as consequence-
# class-only, never frequency/likelihood.
for sev in ('S3', 'S2', 'S1', 'INTEGRITY_OR_USER_ACTION_CRITICAL', 'USER_FACING_OR_WORKFLOW_HIGH', 'FAIL_CLOSED_OPERATIONAL'):
    assert sev in report_text, f'report must use severity vocabulary {sev}'
assert 'consequence class' in report_text
assert 'never a frequency' in report_text or 'never a frequency/probability' in report_text or 'never a frequency/probability/incidence claim' in report_text

# Coverage vocabulary must be present.
for coverage in (
    'RUNTIME_CONSEQUENTIAL_EVALUATOR',
    'DETERMINISTIC_DOCTRINE_OR_CONTRACT_REGRESSION',
    'HUMAN_SEMANTIC_ADJUDICATION',
    'POTENTIAL_CALIBRATED_LLM_JUDGE',
    'UNCOVERED_CONSEQUENTIAL_SURFACE',
    'EVALUATOR_PRESENT_NOT_AT_CONSEQUENTIAL_BOUNDARY',
):
    assert coverage in report_text, f'report must use coverage vocabulary {coverage}'

# Required adjudicated coverage findings must be preserved, not conflated
# or upgraded.
assert 'posting_state_decision_wiring_v1_test.py' in report_text
assert 'live_actionability_semantic_quorum_v1_test.py' in report_text
assert 'evaluate_resume_page_utilization' in report_text
assert 'resume_package_spawn_gate_v1_test.py' in report_text
assert 'BORA_APPLICATION_HISTORY_V1' in report_text
assert 'does' in report_text and 'NOT' in report_text and 'runtime dedupe' in report_text
assert 'milestone_run_v1_test.py' in report_text

# Antigravity benchmark #1 must be labeled EXPERIMENTAL_NON_CANONICAL only
# and must never be treated as authoritative or authority-granting.
assert 'Antigravity' in report_text
_antigravity_heading = '## 8. Antigravity benchmark #1'
assert _antigravity_heading in report_text, 'dedicated Antigravity benchmark section heading missing'
_antigravity_idx = report_text.index(_antigravity_heading)
_antigravity_section_end = report_text.index('## 9.', _antigravity_idx)
_antigravity_section = report_text[_antigravity_idx:_antigravity_section_end]
assert 'EXPERIMENTAL_NON_CANONICAL' in _antigravity_section, 'dedicated Antigravity section must label EXPERIMENTAL_NON_CANONICAL'
assert 'FAILS_BOUNDED_BUILDER_QUALIFICATION_CASE_1' in report_text
assert 'IMPLEMENTATION_PLAUSIBLE_BUT_SEMANTICALLY_MISALIGNED' in report_text
assert '7c7d4daa373c7e8f0bd7843eee4b65823980c9dc' in report_text
assert '8539e9f13482465bd149abd051a3522548f8569e0864b2f7b6e3b5a44978409c' in report_text
assert '437ad3c6612d1c19ecf66071212c7895f6f3bbaac0ea522bd8c9ddfb05ff0f42' in report_text
assert 'grants' in report_text and 'zero' in report_text.lower()

# CAREER_OS_RUN_TRACE_V1 may appear only as an out-of-scope/future/missing
# observability item -- the report must not design/specify/schema it.
assert 'CAREER_OS_RUN_TRACE_V1' in report_text
assert 'does not design, specify, schema, or authorize it' in report_text or 'does not design, specify, schema, implement, or authorize' in report_text

# No LLM judge implementation/design; potential judge is a future candidate only.
assert 'No LLM judge design, prompt, rubric, or implementation is authorized or specified' in report_text or 'future candidate only' in report_text

# No experimental-run-receipts audit; receipts recorded only as OPEN_HYPOTHESIS.
assert 'OPEN_HYPOTHESIS' in report_text
assert 'does not perform an experimental-run-receipts audit' in report_text

# No numeric production failure-rate/incidence claim.
assert 'No production failure-rate' in report_text or 'no production failure-rate' in report_text or 'makes no claim about how often' in report_text

# Report must record it does not authorize Phase E or implementation.
assert 'PROPOSED_NOT_AUTHORIZED' in report_text
assert 'implementation_authorized' in report_text
assert 'authorizes no implementation' in report_text

# Report must explicitly state operator completion is not Bora acceptance.
assert "does not constitute Bora's acceptance" in report_text

# The Phase D contract-lock invariants remain true (unchanged from the
# earlier contract-lock step): forbidden/allowed path scoping and the
# required-tests set must still be exactly as originally locked.
FORBIDDEN_PATHS = (
    'BLUEPRINT.md', 'CLAUDE.md', 'GEMINI.md',
    '.cursor/**', '.cursorignore', '.claude/**', 'src/**', 'schemas/**',
    'claims/**', 'evidence/**', 'experiences/**', 'resume/**',
    'golden-tests/**', 'config/**', 'prompts/**', 'fixtures/**',
)
for forbidden_path in FORBIDDEN_PATHS:
    assert forbidden_path in contract['forbidden_paths'], f'contract must forbid {forbidden_path}'

allowed = set(contract['allowed_paths'])
assert allowed.isdisjoint(set(contract['forbidden_paths']))
EXPECTED_ALLOWED = {
    'docs/audits/CAREER_OS_FAILURE_TAXONOMY_AND_EVALUATOR_COVERAGE_MAP_V1_REPORT.md',
    'CURRENT_EXECUTION_CHECKPOINT.json',
    'project_state.json',
    'CURRENT_STATE.md',
    'CURRENT_MILESTONE.md',
    'CHANGELOG.md',
    'AGENTS.md',
    'docs/decisions/ADR-CAREER-OS-EVAL-HARNESS-SEQUENCE-V1.md',
    'tests/career_os_failure_taxonomy_and_evaluator_coverage_map_v1_test.py',
    'milestone_contracts/audit/career-os-failure-taxonomy-evaluator-coverage-map-v1.json',
    'tests/career_os_execution_checkpoint_v1_test.py',
    'tests/career_os_eval_harness_sequence_v1_test.py',
    'tests/career_os_agent_context_usage_efficiency_v1_test.py',
    'tests/career_os_phase_d_authorization_v1_test.py',
}
assert allowed == EXPECTED_ALLOWED, 'allowed_paths must stay bounded to report/docs plus checkpoint/state/changelog/tests/status-sync AGENTS.md/ADR and the four permitted governance-regression test files'

EXPECTED_REQUIRED_TESTS = [
    'tests/career_os_failure_taxonomy_and_evaluator_coverage_map_v1_test.py',
    'tests/career_os_execution_checkpoint_v1_test.py',
    'tests/career_os_eval_harness_sequence_v1_test.py',
    'tests/career_os_agent_context_usage_efficiency_v1_test.py',
    'tests/career_os_phase_d_authorization_v1_test.py',
]
assert contract['required_tests'] == EXPECTED_REQUIRED_TESTS

# Phase D has since been superseded as the live current phase by Phase E
# (separately, explicitly authorized by Bora); the checkpoint must now
# preserve Phase D's substantive-completion/acceptance facts as prior_phase
# -- never dropped, never self-granted -- distinct from Phase E's own
# (not yet completed) live status.
assert CHECKPOINT_PATH.exists(), 'canonical execution checkpoint missing'
cp = json.loads(CHECKPOINT_PATH.read_text(encoding='utf-8'))
prior_phase = cp['prior_phase']
assert prior_phase['phase_id'] == 'CAREER_OS_FAILURE_TAXONOMY_AND_EVALUATOR_COVERAGE_MAP_V1'
assert prior_phase['phase_mode'] == 'READ_ONLY_DESIGN_ONLY'
assert prior_phase['operator_status'] == 'COMPLETED_BY_OPERATOR'
assert prior_phase['human_acceptance_status'] == 'BORA_ACCEPTED'
assert prior_phase['accepted_at'] == '2026-09-11'
assert cp['implementation_authorized'] is False
assert 'docs/audits/CAREER_OS_FAILURE_TAXONOMY_AND_EVALUATOR_COVERAGE_MAP_V1_REPORT.md' in ' '.join(
    cp['phase_d_completed_actions_reference']
)

# project_state.json must reflect Phase D's preserved acceptance lineage
# (now cited from the Phase E next_authorized_action seam) even though
# Phase E is the live current phase.
project_state = json.loads(PROJECT_STATE_PATH.read_text(encoding='utf-8'))
assert 'COMPLETED_BY_OPERATOR / BORA_ACCEPTED (2026-09-11) / READ_ONLY_DESIGN_ONLY' in project_state['next_authorized_action']
assert 'CAREER_OS_FAILURE_TAXONOMY_AND_EVALUATOR_COVERAGE_MAP_V1' in project_state['next_authorized_action']

# CHANGELOG.md must record the acceptance as a distinct dated entry while
# preserving the prior operator-completion/pending-acceptance entry as
# explicitly superseded history.
changelog_text = CHANGELOG_PATH.read_text(encoding='utf-8')
assert 'substantive read-only/design-only work completed by operator' in changelog_text
assert 'PENDING BORA ACCEPTANCE' in changelog_text or 'PENDING_BORA_ACCEPTANCE' in changelog_text
assert 'accepted by Bora (BORA ACCEPTED)' in changelog_text
assert 'I am satisfied.' in changelog_text

# AGENTS.md and the ADR: status/recovery-pointer sync only, no doctrine
# change (spot-check the live status strings are synchronized). This must
# prove Phase D's OWN status specifically -- the bare substring
# 'COMPLETED_BY_OPERATOR / BORA_ACCEPTED (2026-09-11)' is also a prefix of
# the prior GOVERNANCE_ONLY/GOVERNING policy milestone's own accepted line,
# so a check against that bare substring alone would pass even if Phase D's
# own status line were missing entirely.
agents_text = AGENTS_PATH.read_text(encoding='utf-8')
assert 'COMPLETED_BY_OPERATOR / BORA_ACCEPTED (2026-09-11) / READ_ONLY_DESIGN_ONLY' in agents_text, (
    "AGENTS.md must record Phase D itself, not merely some other accepted milestone, "
    "as COMPLETED_BY_OPERATOR / BORA_ACCEPTED (2026-09-11) / READ_ONLY_DESIGN_ONLY"
)
assert agents_text.count('COMPLETED_BY_OPERATOR / BORA_ACCEPTED (2026-09-11)') >= 2
adr_text = ADR_PATH.read_text(encoding='utf-8')
assert 'COMPLETED_BY_OPERATOR / BORA_ACCEPTED (2026-09-11) / READ_ONLY_DESIGN_ONLY' in adr_text, (
    "the ADR must record Phase D itself, not merely some other accepted milestone, "
    "as COMPLETED_BY_OPERATOR / BORA_ACCEPTED (2026-09-11) / READ_ONLY_DESIGN_ONLY"
)
assert adr_text.count('COMPLETED_BY_OPERATOR / BORA_ACCEPTED (2026-09-11)') >= 2

# --- Phase D semantic-correction regression (fail-closed) ---
# These three corrections were required against the original Phase D
# candidate and must be mechanically enforced so they cannot silently
# regress.

# (A) Family 5: ledger/schema integrity and the submitted-opportunity
# doctrine lock must never be classified as a RUNTIME_CONSEQUENTIAL_EVALUATOR;
# they are DETERMINISTIC_DOCTRINE_OR_CONTRACT_REGRESSION. The runtime
# suppression check at the actual discovery/package consequential boundary
# must remain UNCOVERED_CONSEQUENTIAL_SURFACE.
assert '`RUNTIME_CONSEQUENTIAL_EVALUATOR` for ledger integrity' not in report_text, \
    'ledger integrity must not be classified as a RUNTIME_CONSEQUENTIAL_EVALUATOR'
_family5_heading = '## 6. Failure family 5'
_family5_idx = report_text.index(_family5_heading)
_family5_section_end = report_text.index('## 7.', _family5_idx)
_family5_section = report_text[_family5_idx:_family5_section_end]
assert 'DETERMINISTIC_DOCTRINE_OR_CONTRACT_REGRESSION' in _family5_section
assert 'UNCOVERED_CONSEQUENTIAL_SURFACE' in _family5_section
assert 'discovery/package consequential runtime boundary' in _family5_section or \
    'actual discovery/package consequential runtime boundary' in _family5_section

# (B) Family 6: must not claim the class is structurally uncoverable by
# deterministic tests "by definition" or "structurally not automatable".
# Must instead state no sufficient deterministic evaluator is established
# today, with human/adversarial semantic adjudication as current governing
# coverage, and must not foreclose future deterministic evaluators.
assert 'structurally uncoverable by deterministic tests alone by definition' not in report_text
assert 'structurally not automatable' not in report_text
_family6_heading = '## 7. Failure family 6'
_family6_idx = report_text.index(_family6_heading)
_family6_section_end = report_text.index('## 8.', _family6_idx)
_family6_section = report_text[_family6_idx:_family6_section_end]
assert 'no sufficient deterministic evaluator is established today' in _family6_section
assert 'HUMAN_SEMANTIC_ADJUDICATION' in _family6_section
assert ('neither designs nor authorizes' in _family6_section
        or 'neither design nor authorize' in _family6_section), \
    'family 6 must state future deterministic evaluators are neither designed nor authorized by this report'

# (C) Objective banned-term/jargon vocabulary is deterministic-first;
# POTENTIAL_CALIBRATED_LLM_JUDGE is reserved for genuinely subjective
# residual surfaces evaluated only after objective checks, and must never
# be positioned as a shortcut for objective rules or architecture-fidelity
# enforcement.
assert 'deterministic-first' in report_text
assert 'shortcut for objective banned-term rules' in report_text
assert "family 6's architecture-fidelity enforcement" in report_text
_family2_heading = '## 3. Failure family 2'
_family2_idx = report_text.index(_family2_heading)
_family2_section_end = report_text.index('## 4.', _family2_idx)
_family2_section = report_text[_family2_idx:_family2_section_end]
assert 'jargon' in _family2_section and 'UNCOVERED_CONSEQUENTIAL_SURFACE' in _family2_section
assert 'genuinely subjective' in _family2_section

# (D) Family 3: F1-F9 must be attributed to CAREER_OS_BOUNDED_AGENT_BUILD_LOOP_V1
# and PR #19, matching the canonical Phase C report, and the Family 3 evidence
# paragraph must never conflate the three separately-scoped closure run IDs
# (package gate / reviewer stdin-transport closure / resume gold-quality
# closure) into the F1-F9 provenance claim.
_family3_heading = '## 4. Failure family 3'
_family3_idx = report_text.index(_family3_heading)
_family3_section_end = report_text.index('## 5.', _family3_idx)
_family3_section = report_text[_family3_idx:_family3_section_end]
assert 'CAREER_OS_BOUNDED_AGENT_BUILD_LOOP_V1' in _family3_section, \
    'Family 3 must attribute F1-F9 to CAREER_OS_BOUNDED_AGENT_BUILD_LOOP_V1'
assert 'PR #19' in _family3_section, 'Family 3 must attribute F1-F9 to PR #19'
_family3_evidence_heading = '**Evidence/provenance:**'
_family3_evidence_idx = _family3_section.index(_family3_evidence_heading)
_family3_evidence_para_end = _family3_section.index('\n\n', _family3_evidence_idx)
_family3_evidence_para = _family3_section[_family3_evidence_idx:_family3_evidence_para_end]
assert 'CAREER_OS_BOUNDED_AGENT_BUILD_LOOP_V1' in _family3_evidence_para
assert 'PR #19' in _family3_evidence_para
assert 'separately-scoped closure evidence' in _family3_evidence_para, \
    'Family 3 evidence paragraph must characterize the closure runs as separately-scoped closure evidence'
_family3_evidence_para_normalized = _family3_evidence_para.replace('*', '')
assert 'not the source of F1' in _family3_evidence_para_normalized, \
    'Family 3 evidence paragraph must not conflate the three closure run IDs into F1-F9 provenance'

# (E) Family 2: the geometry-producer gap must not be attributed to "Phase
# C's own repo-fact finding" -- it is current repository/BLUEPRINT evidence
# reviewed in Phase D. The substantive conclusion itself must be preserved.
assert "Phase C's own repo-fact finding" not in report_text, \
    'geometry-producer gap must not be attributed to a Phase C repo-fact finding'
assert 'current repository/BLUEPRINT evidence reviewed in Phase D' in report_text
assert 'no observed rendered-geometry producer that mechanically feeds real page-geometry into this validator for every actual export' in report_text

print('PASS: Career OS Phase D substantive failure-taxonomy/evaluator-coverage-map completion verified.')
