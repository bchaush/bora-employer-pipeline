import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / 'milestone_contracts' / 'audit' / 'career-os-system-eval-set-architecture-v1.json'
REPORT_PATH = ROOT / 'docs' / 'audits' / 'CAREER_OS_SYSTEM_EVAL_SET_ARCHITECTURE_V1_REPORT.md'

BASELINE_SHA = 'd2127314172f8d0b3b5f7a91c68cb00b3d242c1a'

assert CONTRACT_PATH.exists(), 'Phase E system-eval-set-architecture milestone contract missing'
contract = json.loads(CONTRACT_PATH.read_text(encoding='utf-8'))
assert contract['milestone_id'] == 'CAREER_OS_SYSTEM_EVAL_SET_ARCHITECTURE_V1'
assert contract['kind'] == 'READ_ONLY_AUDIT'
assert contract['baseline_sha'] == BASELINE_SHA
assert 'CURSOR_INDEPENDENT_ADVERSARIAL_REVIEW_REQUIRED_BEFORE_COMMIT' in contract['review_requirements']
assert 'NO_COMMIT_PUSH_PR_OR_MERGE_AUTHORIZED_BY_THIS_CONTRACT_ALONE' in contract['review_requirements']
assert 'BORA_EXPLICIT_REVIEW_AND_ACCEPTANCE_OR_CORRECTION_OF_THE_PHASE_E_CHECKPOINT_REQUIRED_BEFORE_PHASE_F_OR_ANY_IMPLEMENTATION' in contract['human_approval_requirements']
assert 'NO_PHASE_F_AUTHORIZATION_IMPLIED' in contract['human_approval_requirements']

FORBIDDEN_PATHS = (
    'BLUEPRINT.md', 'CLAUDE.md', 'GEMINI.md', '.cursor/**', '.cursorignore', '.claude/**',
    'src/**', 'schemas/**', 'claims/**', 'evidence/**', 'experiences/**', 'resume/**',
    'golden-tests/**', 'fixtures/**', 'config/**', 'prompts/**',
)
for forbidden_path in FORBIDDEN_PATHS:
    assert forbidden_path in contract['forbidden_paths'], f'contract must forbid {forbidden_path}'

assert REPORT_PATH.exists(), 'substantive Phase E system-eval-set-architecture report missing'
report_text = REPORT_PATH.read_text(encoding='utf-8')

# ---------------------------------------------------------------------------
# Status banner and epistemic discipline.
# ---------------------------------------------------------------------------
assert 'COMPLETED_BY_OPERATOR / PENDING_BORA_ACCEPTANCE / READ_ONLY_DESIGN_ONLY' in report_text
assert 'implementation_authorized' in report_text
assert 'PROPOSED_NOT_AUTHORIZED' in report_text
for label in ('OBSERVED', 'RECONSTRUCTED_FROM_DURABLE_EVIDENCE', 'MISSING'):
    assert label in report_text, f'report must use provenance label {label}'
assert 'does not constitute' in report_text

# Terminal-state vs step-level diagnostic separation, including the explicit
# invariant that a case can fail terminally while its available step
# diagnostics all pass.
assert 'TERMINAL_END_TO_END' in report_text
assert 'STEP_LEVEL_DIAGNOSTIC' in report_text
assert 'a system case can fail terminally even when every step diagnostic it has available passes' in report_text

# ---------------------------------------------------------------------------
# Structural parse of every case block. Case blocks are rendered as:
#   **Case `<case_id>` — <title>**
#   - `<field>`: <value>
#   - `<field>`: <value>
#   ...
# terminated by the next case heading or the next '## ' section heading.
# This parses the actual rendered fields rather than grepping for global
# substrings, so a case cannot satisfy the schema by accident.
# ---------------------------------------------------------------------------
CASE_HEADING_RE = re.compile(r'^\*\*Case `([^`]+)`[^\n]*\*\*\s*$', re.MULTILINE)
FIELD_LINE_RE = re.compile(r'^\s*-\s*`([a-z_]+)`:\s*(.*)$')

headings = list(CASE_HEADING_RE.finditer(report_text))

REQUIRED_FIELDS = (
    'case_id', 'family', 'case_role', 'provenance_quality', 'operating_case_identity',
    'expected_terminal_outcome', 'diagnostic_layer', 'evaluator_type_owner',
    'current_executability', 'blocking_evidence_gap',
)

ALLOWED_EXECUTABILITY = (
    'EXECUTABLE_NOW', 'RECONSTRUCTION_BACKED_DESIGN_CASE', 'BLOCKED_CANDIDATE', 'HUMAN_CONFIRMED_REFERENCE',
)
ALLOWED_CASE_ROLES = (
    'CONFIRMED_FAILURE_REGRESSION', 'IMPORTANT_WORKFLOW', 'POSITIVE_CONTINUITY_REFERENCE',
)
ALLOWED_FAMILIES = (
    'LIVE_OPPORTUNITY_ACTIONABILITY_IDENTITY_ROUTE_FAILURE',
    'PACKAGE_SPAWN_AND_CANDIDATE_ARTIFACT_QUALITY_FAILURE',
    'CONTROLLER_REVIEWER_EVIDENCE_INTEGRITY_FAILURE',
    'PROVIDER_SESSION_TRANSPORT_RECOVERABILITY_FAILURE',
    'APPLICATION_LIFECYCLE_DUPLICATE_CONTINUITY_FAILURE',
    'SEMANTIC_CONTRACT_ARCHITECTURE_FIDELITY_FAILURE',
    'POSITIVE_CONTINUITY',
    'CROSS_CUTTING_RECENCY_SUPPRESSION',
)
ALLOWED_DIAGNOSTIC_LAYERS = (
    'TERMINAL_END_TO_END', 'STEP_LEVEL_DIAGNOSTIC', 'BOTH',
)

cases = {}
for i, m in enumerate(headings):
    heading_case_id = m.group(1)
    start = m.end()
    end = headings[i + 1].start() if i + 1 < len(headings) else len(report_text)
    block = report_text[start:end]
    section_break = re.search(r'\n## ', block)
    if section_break:
        block = block[:section_break.start()]

    fields = {}
    for line in block.splitlines():
        fm = FIELD_LINE_RE.match(line)
        if fm:
            field_name = fm.group(1)
            # first bullet wins if a field name is accidentally repeated
            fields.setdefault(field_name, fm.group(2).strip())

    assert heading_case_id not in cases, f'duplicate case heading {heading_case_id}'
    cases[heading_case_id] = fields

EXPECTED_CASE_IDS = (
    'F1-A', 'F1-B', 'F1-C', 'F1-D', 'F1-E',
    'F2-A', 'F2-B', 'F2-C',
    'F3-A', 'F4-A',
    'F5-A', 'F5-B',
    'REC-A',
    'POS-A', 'POS-B',
)
for expected_id in EXPECTED_CASE_IDS:
    assert expected_id in cases, f'expected case block {expected_id} missing from rendered report'

# The admitted corpus must be exactly these 15 case IDs: no fewer (a missing
# case silently narrows coverage) and no more (an extra case, e.g. a
# resurrected Family 6 row, would silently expand the corpus beyond what was
# architecturally authorized).
assert set(cases.keys()) == set(EXPECTED_CASE_IDS), (
    f'admitted case corpus must be exactly {sorted(EXPECTED_CASE_IDS)}, found {sorted(cases.keys())}'
)
assert len(cases) == 15, f'expected exactly 15 admitted case blocks, found {len(cases)}'

# Every case block must carry every required field, and the field's own
# `case_id` bullet must agree with its heading (catches copy-paste drift).
seen_case_id_values = []
for heading_id, fields in cases.items():
    for field in REQUIRED_FIELDS:
        assert field in fields, f'case {heading_id} is missing required field `{field}`'
        assert fields[field], f'case {heading_id} field `{field}` is empty'

    inline_case_id = fields['case_id'].strip('`').strip('.').strip()
    assert inline_case_id == heading_id, (
        f'case {heading_id} heading does not match its own `case_id` bullet value {inline_case_id!r}'
    )
    seen_case_id_values.append(inline_case_id)

# Case IDs must be unique (belt-and-suspenders on top of the dict-key check above).
assert len(seen_case_id_values) == len(set(seen_case_id_values)), 'duplicate case_id values found across case blocks'

# ---------------------------------------------------------------------------
# Shared leading-enum-token parser. Fields are rendered as a single
# backticked token immediately after the colon, optionally followed by
# trailing explanatory prose (e.g. "`BLOCKED_CANDIDATE` — no runtime..."),
# which may legitimately contrast with or name other enum classes. Only the
# leading backticked token is the actual enum value; matching enum tokens
# anywhere in the trailing prose (as the previous implementation did) both
# false-flags legitimate contrastive explanations and misses compound/slash
# leading values whose pieces individually match an allowed token.
# ---------------------------------------------------------------------------
LEADING_BACKTICK_RE = re.compile(r'^\s*`([^`]*)`')


def leading_backtick_content(value):
    m = LEADING_BACKTICK_RE.match(value)
    return m.group(1) if m else None


# ---------------------------------------------------------------------------
# current_executability must lead with exactly one allowed token per case,
# never a slash/compound value combining two classes in one field. Trailing
# prose may legitimately reference other executability classes (e.g. to
# contrast terminal coverage with a narrower EXECUTABLE_NOW step diagnostic)
# without being flagged.
# ---------------------------------------------------------------------------
for heading_id, fields in cases.items():
    value = fields['current_executability']
    leading_content = leading_backtick_content(value)
    assert leading_content is not None, (
        f'case {heading_id} current_executability has no leading backticked token: {value!r}'
    )
    assert leading_content in ALLOWED_EXECUTABILITY, (
        f'case {heading_id} current_executability leading token is not an allowed executability class '
        f'(compound/slash or unrecognized leading value not allowed): {value!r}'
    )

# ---------------------------------------------------------------------------
# case_role must lead with exactly one allowed enum value per case.
# ---------------------------------------------------------------------------
for heading_id, fields in cases.items():
    value = fields['case_role']
    leading_content = leading_backtick_content(value)
    assert leading_content is not None, (
        f'case {heading_id} case_role has no leading backticked token: {value!r}'
    )
    assert leading_content in ALLOWED_CASE_ROLES, (
        f'case {heading_id} case_role leading token is not an allowed case role '
        f'(compound/slash or unrecognized leading value not allowed): {value!r}'
    )

# ---------------------------------------------------------------------------
# family must lead with exactly one allowed token per case (the six Phase D
# families, POSITIVE_CONTINUITY, or the explicit REC-A cross-cutting
# addition) — never an unrecognized or compound value.
# ---------------------------------------------------------------------------
for heading_id, fields in cases.items():
    value = fields['family']
    leading_content = leading_backtick_content(value)
    assert leading_content is not None, (
        f'case {heading_id} family has no leading backticked token: {value!r}'
    )
    assert leading_content in ALLOWED_FAMILIES, (
        f'case {heading_id} family leading token is not an allowed family '
        f'(compound/slash or unrecognized leading value not allowed): {value!r}'
    )

assert cases['REC-A']['family'].strip('`.') == 'CROSS_CUTTING_RECENCY_SUPPRESSION', (
    'REC-A must carry the explicit CROSS_CUTTING_RECENCY_SUPPRESSION family token'
)

# ---------------------------------------------------------------------------
# diagnostic_layer must begin with exactly one allowed enum token; a value
# combining two leading tokens (e.g. "TERMINAL_END_TO_END ... ;
# STEP_LEVEL_DIAGNOSTIC ...") fails closed even though both tokens
# individually are recognized.
# ---------------------------------------------------------------------------
for heading_id, fields in cases.items():
    value = fields['diagnostic_layer']
    stripped = value.strip('`.')
    assert any(stripped.startswith(token) for token in ALLOWED_DIAGNOSTIC_LAYERS), (
        f'case {heading_id} diagnostic_layer does not begin with an allowed enum token: {value!r}'
    )
    leading_token = next(token for token in ALLOWED_DIAGNOSTIC_LAYERS if stripped.startswith(token))
    if leading_token != 'BOTH':
        # BOTH is the sole enum value permitted to reference the two
        # sub-tokens in trailing prose (e.g. "BOTH -- TERMINAL_END_TO_END
        # for X; STEP_LEVEL_DIAGNOSTIC for Y"). A non-BOTH leading token
        # must not also name the other token, which would indicate an
        # un-fused compound value masquerading as a single enum.
        remaining = stripped[len(leading_token):]
        other_tokens_present = [
            token for token in ALLOWED_DIAGNOSTIC_LAYERS
            if token not in ('BOTH', leading_token) and token in remaining
        ]
        assert not other_tokens_present, (
            f'case {heading_id} diagnostic_layer names more than one enum token in the leading position '
            f'(compound value not allowed, use BOTH): {value!r}'
        )

assert cases['REC-A']['diagnostic_layer'].strip('`.').startswith('BOTH'), (
    'REC-A diagnostic_layer must lead with BOTH exactly, with prose describing the terminal/step split after it'
)

# Doctrine-only workflow candidates (no preserved failure event) must not be
# relabeled as confirmed failures.
assert cases['F5-B']['case_role'].startswith('`IMPORTANT_WORKFLOW`'), (
    'F5-B (duplicate suppression, no preserved real duplicate-failure event) must be case_role IMPORTANT_WORKFLOW'
)
assert cases['REC-A']['case_role'].startswith('`IMPORTANT_WORKFLOW`'), (
    'REC-A (recency suppression, no preserved confirmed-failure event) must be case_role IMPORTANT_WORKFLOW'
)

# ---------------------------------------------------------------------------
# No combined two-identity row: the previously-combined MGB RQ4055007 /
# Fresenius R0266808 row must now be two separate cases (F1-D, F1-E), and no
# single case's operating_case_identity may name both requisitions at once.
# ---------------------------------------------------------------------------
assert 'RQ4055007' in cases['F1-E']['operating_case_identity']
assert 'R0266808' in cases['F1-D']['operating_case_identity']
for heading_id, fields in cases.items():
    identity = fields['operating_case_identity']
    assert not ('RQ4055007' in identity and 'R0266808' in identity), (
        f'case {heading_id} combines MGB RQ4055007 and Fresenius R0266808 into one row; they must be separate cases'
    )

# ---------------------------------------------------------------------------
# Exact PCG JR102087 recency/duplicate-suppression identity (replacing the
# generic "any discovered role" / "any future employer" placeholders).
# ---------------------------------------------------------------------------
for case_id in ('REC-A', 'F5-B'):
    identity = cases[case_id]['operating_case_identity']
    assert 'JR102087' in identity, f'{case_id} must name the durable PCG JR102087 identity'
    assert 'Public Consulting Group' in identity, f'{case_id} must name Public Consulting Group by name'

# ---------------------------------------------------------------------------
# POS-A must be the explicit non-executable human-handoff reference class,
# never claimed as EXECUTABLE_NOW for the submission act itself.
# ---------------------------------------------------------------------------
assert cases['POS-A']['current_executability'].startswith('`HUMAN_CONFIRMED_REFERENCE`'), (
    'POS-A (14 submitted applications) must use current_executability HUMAN_CONFIRMED_REFERENCE, '
    'not EXECUTABLE_NOW, for the human submission act'
)

# ---------------------------------------------------------------------------
# F1-A must not claim terminal E2E coverage from the step-level routing-gate
# test; its current_executability reflects the unproven terminal claim, and
# its step-level diagnostic is recorded separately.
# ---------------------------------------------------------------------------
assert cases['F1-A']['current_executability'].startswith('`RECONSTRUCTION_BACKED_DESIGN_CASE`'), (
    'F1-A must not claim EXECUTABLE_NOW terminal coverage from posting_state_decision_wiring_v1_test.py alone'
)
assert 'available_step_diagnostics' in cases['F1-A'], 'F1-A must record its step-level diagnostic separately'
assert 'EXECUTABLE_NOW' in cases['F1-A']['available_step_diagnostics']

# F2-A: same discipline for the page-utilization function vs. the
# render-to-validator terminal path.
assert cases['F2-A']['current_executability'].startswith('`RECONSTRUCTION_BACKED_DESIGN_CASE`'), (
    'F2-A must not claim EXECUTABLE_NOW terminal coverage for the full render-to-validator path'
)
assert 'available_step_diagnostics' in cases['F2-A'], 'F2-A must record its step-level diagnostic separately'
assert 'EXECUTABLE_NOW' in cases['F2-A']['available_step_diagnostics']

# ---------------------------------------------------------------------------
# Family 6 must have no admitted operating case, only an explicit exclusion
# note preserving the six-family taxonomy without laundering experimental
# evidence into the repeatable corpus.
# ---------------------------------------------------------------------------
family_6_names = [f for f in cases if cases[f]['family'].strip('`.') == 'SEMANTIC_CONTRACT_ARCHITECTURE_FIDELITY_FAILURE']
assert not family_6_names, f'no Family-6 case may be admitted to the repeatable corpus, found: {family_6_names}'
assert 'SEMANTIC_CONTRACT_ARCHITECTURE_FIDELITY_FAILURE' in report_text
assert 'no Family-6 case is promoted into this repeatable corpus' in report_text
assert 'EXPERIMENTAL_NON_CANONICAL' in report_text

# ---------------------------------------------------------------------------
# Deterministic pass/fail pairing rule.
# ---------------------------------------------------------------------------
assert 'Deterministic pass/fail pairing rule' in report_text
assert 'missing counterpart requirement' in report_text.lower() or 'Missing counterpart requirement' in report_text
assert 'PASS/FAIL pair present' in report_text

# ---------------------------------------------------------------------------
# Fail closed if a generic placeholder identity returns in admitted cases.
# ---------------------------------------------------------------------------
GENERIC_PLACEHOLDER_PHRASES = (
    'any discovered role whose posting age',
    'any future employer+exact-requisition pair',
)
for phrase in GENERIC_PLACEHOLDER_PHRASES:
    assert phrase not in report_text, f'generic placeholder identity must not appear in admitted cases: {phrase!r}'

# ---------------------------------------------------------------------------
# operating_case_identity must be a single durable identity/artifact/run for
# each of these cases, not a generic/descriptive group. Enforce the exact
# stable identity strings the Phase E normalization pass fixed.
# ---------------------------------------------------------------------------
assert 'BORA_APPLICATION_HISTORY_V1' in cases['F5-A']['operating_case_identity'], (
    'F5-A operating_case_identity must name the canonical BORA_APPLICATION_HISTORY_V1 ledger artifact, '
    'not a generic "ledger schema integrity" description'
)
assert 'ledger schema integrity' not in cases['F5-A']['operating_case_identity'].lower()

assert 'BORA_APPLICATION_HISTORY_V1' in cases['POS-A']['operating_case_identity'], (
    'POS-A operating_case_identity must name the canonical BORA_APPLICATION_HISTORY_V1 ledger as one artifact'
)
BANNED_INDIVIDUAL_ENTRY_PHRASE = 'each of the 14'
assert BANNED_INDIVIDUAL_ENTRY_PHRASE not in cases['POS-A']['operating_case_identity'], (
    'POS-A operating_case_identity must not enumerate each of the 14 ledger entries individually plus the '
    'ledger; it must name the ledger as one aggregate artifact/reference set'
)
assert BANNED_INDIVIDUAL_ENTRY_PHRASE not in report_text, (
    'no admitted case may use the "each of the 14 ... individually plus" identity form'
)

assert '20260908T184816Z-d3a8a974' in cases['POS-B']['operating_case_identity']
assert 'CAREER_OS_CURSOR_REVIEWER_STDIN_TRANSPORT_V1' in cases['POS-B']['operating_case_identity']

assert '20260907T220348Z-3dacfcfd' in cases['F4-A']['operating_case_identity']

assert 'CAREER_OS_BOUNDED_AGENT_BUILD_LOOP_V1' in cases['F3-A']['operating_case_identity']
assert 'PR #19' in cases['F3-A']['operating_case_identity']

for case_id in ('F2-B', 'F2-C'):
    identity = cases[case_id]['operating_case_identity']
    assert '20260909T172902Z-7add4b47' in identity, (
        f'{case_id} operating_case_identity must name the exact governed closure run, '
        f'since the role title is not durably preserved'
    )
    assert 'role name not durably preserved' in identity or 'role name not further specified' in identity

# ---------------------------------------------------------------------------
# Executability classes must all be present and distinct, and the report
# must explicitly disclaim presenting a reconstruction/blocked case as an
# existing executable fixture.
# ---------------------------------------------------------------------------
for executability in ALLOWED_EXECUTABILITY:
    assert executability in report_text, f'report must use executability class {executability}'
assert 'never presented as production evidence' in report_text or 'never described as' in report_text or 'never claim runtime dedupe coverage' in report_text or 'does not claim runtime dedupe coverage exists' in report_text

# Case-row schema fields required by the acceptance conditions.
for field in REQUIRED_FIELDS + ('available_step_diagnostics',):
    assert field in report_text, f'report must define case-row field {field}'

# Reused Phase D coverage vocabulary must appear (no new vocabulary invented).
for coverage in (
    'RUNTIME_CONSEQUENTIAL_EVALUATOR',
    'DETERMINISTIC_DOCTRINE_OR_CONTRACT_REGRESSION',
    'HUMAN_SEMANTIC_ADJUDICATION',
    'POTENTIAL_CALIBRATED_LLM_JUDGE',
    'UNCOVERED_CONSEQUENTIAL_SURFACE',
    'EVALUATOR_PRESENT_NOT_AT_CONSEQUENTIAL_BOUNDARY',
):
    assert coverage in report_text, f'report must reuse coverage vocabulary {coverage}'

# Deterministic-first / future LLM judge discipline, reused from Phase D.
assert 'deterministic-first' in report_text
assert 'genuinely subjective' in report_text
assert 'No LLM judge design, prompt, rubric, or implementation is authorized or specified' in report_text

# CI regression vs live monitoring distinction; no production failure-rate claim.
assert 'CI regression eval' in report_text
assert 'live production monitoring' in report_text or 'live monitoring' in report_text
assert 'no production failure-rate claim' in report_text.lower() or 'makes no production failure-rate claim' in report_text

# Representative case families required by the acceptance conditions must
# each be named with a concrete, evidence-grounded operating case identity.
REQUIRED_CASE_IDENTITIES = (
    'MGB RQ4075857',       # live-actionability
    'Point32Health R9102', # dead-route false positive
    '260005JH',            # excluded application-route host
    'SUPPRESSED_WINDOW',   # recency suppression
    'BORA_APPLICATION_HISTORY_V1',  # application lifecycle / duplicate continuity
    'F1-F9',                # controller/reviewer integrity, cited via findings label
    'Atominvest',           # package-quality/gold-family
    'DraftKings',
    'Santander',
    '14-entry',              # clean successful/handoff ledger
    'JR102087',              # durable PCG motivating/replay identity
)
for identity in REQUIRED_CASE_IDENTITIES:
    assert identity in report_text, f'report must name representative case identity {identity}'

# Negative-case discipline: reconstruction/blocked cases must not be
# misdescribed as currently executable fixtures. Spot-check the duplicate-
# suppression case (the key Phase D finding this report must not overclaim).
assert 'does not claim runtime dedupe coverage exists' in report_text

# Phase F+ non-authorization must be explicit at the end of the report.
assert 'Phase F and every later roadmap phase remain **PROPOSED_NOT_AUTHORIZED**' in report_text

# ---------------------------------------------------------------------------
# Cursor finding A: EXECUTABLE_NOW must not be defined as production-path-src
# behavior only. It must admit both RUNTIME_CONSEQUENTIAL_EVALUATOR and
# DETERMINISTIC_DOCTRINE_OR_CONTRACT_REGRESSION, with evaluator_type_owner as
# the authoritative coverage-boundary classifier, and EXECUTABLE_NOW must
# never itself imply runtime-consequential or terminal coverage.
# ---------------------------------------------------------------------------
FORBIDDEN_EXECUTABLE_NOW_NARROWING = (
    "already exercises the case's production-path code today (the case can be run as "
    "`python tests/<file>` right now and its assertions are grounded in real `src/` behavior, "
    "not merely doctrine text)"
)
assert FORBIDDEN_EXECUTABLE_NOW_NARROWING not in report_text, (
    'EXECUTABLE_NOW must not be narrowly defined as production-path-src-only behavior'
)
assert 'evaluator_type_owner` — not `current_executability` — is the authoritative classifier' in report_text, (
    'report must state evaluator_type_owner is the authoritative coverage-boundary classifier, not current_executability'
)
assert '`EXECUTABLE_NOW` alone never implies runtime-consequential coverage, and never implies terminal end-to-end coverage' in report_text, (
    'report must explicitly state EXECUTABLE_NOW alone never implies runtime-consequential or terminal coverage'
)

# ---------------------------------------------------------------------------
# Cursor finding C: Section 7 must distinguish CONFIRMED_FAILURE_REGRESSION
# cases (guard known reproduced defects) from IMPORTANT_WORKFLOW /
# POSITIVE_CONTINUITY_REFERENCE diagnostics (exercise important deterministic
# conditions/integrity, but do not imply a preserved defect event), and must
# not claim every EXECUTABLE_NOW case proves an already-reproduced defect
# stays fixed.
# ---------------------------------------------------------------------------
assert 'proves that a specific, already-reproduced defect class stays fixed when the existing deterministic test suite runs' in report_text
assert 'CONFIRMED_FAILURE_REGRESSION' in report_text and 'IMPORTANT_WORKFLOW' in report_text
assert (
    "does not itself imply that a previously-reproduced defect event is being kept fixed"
    in report_text
), 'Section 7 must state IMPORTANT_WORKFLOW/POSITIVE_CONTINUITY_REFERENCE diagnostics do not imply a preserved defect event'
FORBIDDEN_UNIFORM_EXECUTABLE_NOW_CLAIM = (
    'every `EXECUTABLE_NOW` case in Section 5 is a **CI regression eval** — it proves that a specific, '
    'already-reproduced defect class stays fixed'
)
assert FORBIDDEN_UNIFORM_EXECUTABLE_NOW_CLAIM not in report_text, (
    'Section 7 must not claim every EXECUTABLE_NOW case uniformly proves an already-reproduced defect stays fixed'
)

# ---------------------------------------------------------------------------
# Cursor finding D: Phase F must not be called an implementation step. Phase F
# is trace/contract architecture, Phase G is assurance architecture, and any
# fixture/runtime implementation belongs no earlier than a separately
# authorized Phase H bounded implementation milestone.
# ---------------------------------------------------------------------------
assert 'Phase F/H implementation step' not in report_text, (
    'report must not call Phase F (or a fused Phase F/H) an implementation step'
)
assert 'Phase F is trace/contract architecture' in report_text
assert 'Phase G is assurance architecture' in report_text
assert 'Phase H bounded implementation' in report_text
assert 'building it is not a Phase F step' in report_text

# ---------------------------------------------------------------------------
# Cursor round-2 finding: case_role's CONFIRMED_FAILURE_REGRESSION definition
# must not overclaim that a confirmed historical failure is "now guarded by
# regression" -- the role alone does not imply current terminal
# executability/protection. Current coverage is determined separately by
# current_executability + evaluator_type_owner + diagnostic_layer, per
# Section 7.
# ---------------------------------------------------------------------------
FORBIDDEN_CASE_ROLE_OVERCLAIMS = (
    'now guarded by regression',
    'previously-reproduced defect now guarded by regression',
)
for phrase in FORBIDDEN_CASE_ROLE_OVERCLAIMS:
    assert phrase not in report_text, (
        f'report must not overclaim a confirmed historical failure is currently protected: {phrase!r}'
    )

assert (
    "the role alone does **not** imply the terminal claim is currently executable, runtime-covered, "
    "or protected by a current regression" in report_text
), 'case_role definition must explicitly disclaim that CONFIRMED_FAILURE_REGRESSION implies current protection'

assert (
    'current protection/coverage is determined separately by `current_executability` + `evaluator_type_owner` '
    '+ `diagnostic_layer`' in report_text
    or 'determined separately by `current_executability`, `evaluator_type_owner`, and `diagnostic_layer`' in report_text
), 'report must state that current_executability, evaluator_type_owner, and diagnostic_layer determine current coverage'

assert (
    'only an `EXECUTABLE_NOW` `CONFIRMED_FAILURE_REGRESSION` case with matching coverage can claim a reproduced '
    'defect stays fixed today, per Section 7' in report_text
), 'report must state only an EXECUTABLE_NOW CONFIRMED_FAILURE_REGRESSION case with matching coverage can claim a reproduced defect stays fixed today'

# Section 7's existing assertions must still be intact (not weakened by this correction).
assert 'proves that a specific, already-reproduced defect class stays fixed when the existing deterministic test suite runs' in report_text
assert "does not itself imply that a previously-reproduced defect event is being kept fixed" in report_text
assert FORBIDDEN_UNIFORM_EXECUTABLE_NOW_CLAIM not in report_text

# ---------------------------------------------------------------------------
# Cursor round-3 finding: Section 2 must not imply current_executability can
# itself reflect a narrower step-level diagnostic fact. current_executability
# always records the terminal-outcome case classification; a narrower
# executable step diagnostic is recorded only in available_step_diagnostics
# and never changes or inflates the terminal classification.
# ---------------------------------------------------------------------------
FORBIDDEN_SECTION_2_STEP_NARROWING = (
    "`current_executability` reflects that narrower fact (via the optional "
    "`available_step_diagnostics` field, Section 3), and is never inflated to describe "
    "the unproven terminal path as an existing fixture"
)
assert FORBIDDEN_SECTION_2_STEP_NARROWING not in report_text, (
    'Section 2 must not imply current_executability itself reflects a narrower step-level diagnostic fact'
)
assert (
    '`current_executability` always records the terminal-outcome case classification, never a narrower '
    'step-level substitute for it' in report_text
), 'Section 2 must state current_executability always records the terminal-outcome classification'
assert (
    'that fact is recorded solely in the optional `available_step_diagnostics` field (Section 3); it is '
    'never used to change or inflate `current_executability` itself' in report_text
), 'Section 2 must state a narrower step diagnostic is recorded only in available_step_diagnostics and never changes/inflates current_executability'

print('PASS: Career OS Phase E system eval-set architecture report verified.')
