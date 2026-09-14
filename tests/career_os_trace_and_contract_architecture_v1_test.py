import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / 'milestone_contracts' / 'design' / 'career-os-phase-f-trace-contract-architecture-v1.json'
REPORT_PATH = ROOT / 'docs' / 'audits' / 'CAREER_OS_TRACE_AND_CONTRACT_ARCHITECTURE_V1_REPORT.md'

BASELINE_SHA = '4dbee89f07b5a22c9f0d166655f223038793d0f2'

assert CONTRACT_PATH.exists(), 'Phase F trace-contract-architecture milestone contract missing'
contract = json.loads(CONTRACT_PATH.read_text(encoding='utf-8'))
assert contract['milestone_id'] == 'CAREER_OS_TRACE_AND_CONTRACT_ARCHITECTURE_V1'
assert contract['kind'] == 'READ_ONLY_AUDIT'
assert contract['baseline_sha'] == BASELINE_SHA
assert 'CURSOR_INDEPENDENT_ADVERSARIAL_REVIEW_REQUIRED_BEFORE_COMMIT' in contract['review_requirements']
assert 'NO_COMMIT_PUSH_PR_OR_MERGE_AUTHORIZED_BY_THIS_CONTRACT_ALONE' in contract['review_requirements']

FORBIDDEN_PATHS = (
    'BLUEPRINT.md', 'CLAUDE.md', 'GEMINI.md', '.cursor/**', '.cursorignore', '.claude/**',
    'src/**', 'schemas/**', 'claims/**', 'evidence/**', 'experiences/**', 'resume/**',
    'golden-tests/**', 'fixtures/**', 'config/**', 'prompts/**',
)
for forbidden_path in FORBIDDEN_PATHS:
    assert forbidden_path in contract['forbidden_paths'], f'contract must forbid {forbidden_path}'

# ---------------------------------------------------------------------------
# The milestone contract's acceptance_conditions must lock the exact repaired
# semantics adjudicated by Cursor: the three-way terminal_state /
# first_point_of_divergence / first_causal_failure_point distinction plus the
# recoverable-divergence rule, human_handoffs being Bora-only and never
# merged with model_tool_provenance, and EXPERIMENTAL_NON_CANONICAL's
# exclusion from per-fact provenance_quality. These must fail closed if a
# future edit weakens or drops the exact locked condition text.
# ---------------------------------------------------------------------------
REQUIRED_ACCEPTANCE_CONDITIONS = (
    'provenance_quality on each trace fact is the three-value evidence-quality subset '
    'OBSERVED / RECONSTRUCTED_FROM_DURABLE_EVIDENCE / MISSING; EXPERIMENTAL_NON_CANONICAL '
    'is excluded from provenance_quality and remains a case/architecture-status label, '
    'not a per-fact evidence-quality value.',
    'The design separates end-to-end terminal outcome from step-level diagnostics and '
    'distinguishes terminal_state, first_point_of_divergence, and first_causal_failure_point '
    'as three never-conflated concepts, applying the recoverable-divergence rule: a '
    'first_point_of_divergence that a later gate in the run\'s own trajectory recovers from '
    'is never labeled first_causal_failure_point merely because it occurred first.',
    'human_handoffs entries exist only for genuine control-passing events to Bora (the human) '
    'and are never merged with model_tool_provenance, which records machine/model/tool-attributed '
    'consequential decisions; a model/tool decision is never recorded as a human_handoffs entry.',
    'The multi-divergence rule holds exactly: first_point_of_divergence always names the earliest '
    'identifiable divergence point in a run, including one that was later recovered; every '
    'identifiable first_causal_failure_point is itself a divergence point but equals the run\'s '
    'first_point_of_divergence only when no earlier recovered divergence exists; in a run with an '
    'earlier recovered divergence A followed by a distinct, later, unrecovered divergence B, '
    'first_point_of_divergence is A and first_causal_failure_point is B, at two different points '
    'in the same run. No identifiable first_causal_failure_point is claimed to be the run\'s '
    'first_point_of_divergence merely because it is an identifiable divergence point. The symmetric '
    'CAUSE_UNKNOWN / UNINSTRUMENTED_BOUNDARY label for an uninstrumented boundary is preserved unchanged.',
)
for condition in REQUIRED_ACCEPTANCE_CONDITIONS:
    assert condition in contract['acceptance_conditions'], \
        f'contract acceptance_conditions must lock: {condition}'

MIXED_ATTRIBUTION_CONDITION = (
    'The mixed attribution case is preserved: a run may have an identifiable, recovered '
    'first_point_of_divergence = A while the run\'s actual causal defect lived in a separate, '
    'later, uninstrumented boundary with no identifiable point B; in that case '
    'first_point_of_divergence = A is preserved unchanged (never wiped or reattributed) and '
    'first_causal_failure_point is separately recorded as CAUSE_UNKNOWN / UNINSTRUMENTED_BOUNDARY '
    'rather than a fabricated point B; the fully-uninstrumented symmetric pair case (both fields '
    'CAUSE_UNKNOWN / UNINSTRUMENTED_BOUNDARY) remains preserved unchanged alongside it.'
)
assert MIXED_ATTRIBUTION_CONDITION in contract['acceptance_conditions'], \
    f'contract acceptance_conditions must lock the mixed attribution case: {MIXED_ATTRIBUTION_CONDITION}'

# ---------------------------------------------------------------------------
# Success-vs-failure absence semantics: CAUSE_UNKNOWN / UNINSTRUMENTED_BOUNDARY
# is reserved exclusively for an incorrect terminal_state where a real
# divergence/causal failure exists but no instrumented point is identifiable.
# A correct terminal_state with no divergence uses NOT_APPLICABLE / NO_DIVERGENCE
# for first_point_of_divergence; any correct terminal_state uses NOT_APPLICABLE /
# NO_TERMINAL_FAILURE for first_causal_failure_point, even when a recovered
# first_point_of_divergence = A is preserved. Fail closed if the contract
# stops locking this distinction.
# ---------------------------------------------------------------------------
SUCCESS_FAILURE_ABSENCE_CONDITION = (
    'Success-vs-failure absence semantics are locked: CAUSE_UNKNOWN / UNINSTRUMENTED_BOUNDARY '
    'is reserved exclusively for an incorrect terminal_state where a real divergence or causal '
    'failure exists but no instrumented point is identifiable; for a correct terminal_state with '
    'no divergence, first_point_of_divergence is recorded NOT_APPLICABLE / NO_DIVERGENCE; for any '
    'correct terminal_state, first_causal_failure_point is recorded NOT_APPLICABLE / '
    'NO_TERMINAL_FAILURE, including when a recovered first_point_of_divergence = A is preserved '
    'unchanged; CAUSE_UNKNOWN / UNINSTRUMENTED_BOUNDARY is never used on a correct-terminal success '
    'case for either field, and the pre-existing identifiable A->B failure case, the mixed failure '
    'case (first_point_of_divergence = A with first_causal_failure_point = CAUSE_UNKNOWN / '
    'UNINSTRUMENTED_BOUNDARY), and the fully-uninstrumented incorrect-terminal pair case (both '
    'fields CAUSE_UNKNOWN / UNINSTRUMENTED_BOUNDARY) remain preserved unchanged.'
)
assert SUCCESS_FAILURE_ABSENCE_CONDITION in contract['acceptance_conditions'], \
    f'contract acceptance_conditions must lock success-vs-failure absence semantics: {SUCCESS_FAILURE_ABSENCE_CONDITION}'

# ---------------------------------------------------------------------------
# Reconstructability acceptance_condition must explicitly include
# first_point_of_divergence and first_causal_failure_point alongside every
# other run-trace field -- omitting either is a drift regression.
# ---------------------------------------------------------------------------
RECONSTRUCTABILITY_CONDITION = (
    'The run trace makes canonical SHA, run identity, inputs, sources attempted, unavailable '
    'sources, state transitions, suppression reasons, model/tool provenance where relevant, human '
    'handoffs, artifact hashes, QA outcomes, terminal state, first point of divergence, and first '
    'causal failure point reconstructable without a chat transcript.'
)
assert RECONSTRUCTABILITY_CONDITION in contract['acceptance_conditions'], \
    'contract acceptance_conditions must lock the reconstructability condition including ' \
    'first_point_of_divergence and first_causal_failure_point'

# ---------------------------------------------------------------------------
# An explicit acceptance_condition must enumerate every protected append-only
# field -- fail closed if the enumeration is dropped or narrowed.
# ---------------------------------------------------------------------------
PROTECTED_APPEND_ONLY_FIELDS_CONDITION_FRAGMENT = (
    'the protected append-only fields are exactly: canonical_sha, run_identity, inputs, '
    'sources_attempted, unavailable_sources, state_transitions, suppression_reasons, '
    'model_tool_provenance, human_handoffs, artifact_hashes, qa_outcomes, terminal_state, '
    'first_point_of_divergence, and first_causal_failure_point.'
)
assert any(PROTECTED_APPEND_ONLY_FIELDS_CONDITION_FRAGMENT in condition for condition in contract['acceptance_conditions']), \
    'contract acceptance_conditions must enumerate the exact protected append-only field list'

# ---------------------------------------------------------------------------
# The governing ADR's own Phase F reconstructability list (Section 4) must
# name first_point_of_divergence and first_causal_failure_point alongside
# terminal_state -- omitting either from the ADR's own field list is a drift
# regression distinct from the milestone contract's own enumeration above.
# ---------------------------------------------------------------------------
ADR_PATH = ROOT / 'docs' / 'decisions' / 'ADR-CAREER-OS-EVAL-HARNESS-SEQUENCE-V1.md'
assert ADR_PATH.exists(), 'governing ADR missing'
adr_text = ADR_PATH.read_text(encoding='utf-8')
assert (
    'QA outcomes, terminal state, first point of divergence, and first causal failure point '
    'reconstructable without reading a chat transcript' in adr_text
), 'ADR Phase F reconstructability list must include first point of divergence and first causal failure point alongside terminal state'

# ---------------------------------------------------------------------------
# ADR repair: the Phase F reconstructability list must also name run identity
# (alongside canonical SHA and every other listed field) -- omitting it is a
# drift regression distinct from the terminal_state/divergence fields above.
# ---------------------------------------------------------------------------
assert (
    'The trace should make canonical SHA, run identity, inputs, sources attempted, unavailable '
    'sources, state transitions, suppression reasons, model/tool provenance where relevant, human '
    'handoffs, artifact hashes, QA outcomes, terminal state, first point of divergence, and first '
    'causal failure point reconstructable without reading a chat transcript.' in adr_text
), 'ADR Phase F reconstructability list must include run identity alongside canonical SHA and every other field'

assert REPORT_PATH.exists(), 'substantive Phase F trace/contract architecture report missing'
report_text = REPORT_PATH.read_text(encoding='utf-8')

# ---------------------------------------------------------------------------
# Status banner and epistemic discipline.
# ---------------------------------------------------------------------------
assert 'COMPLETED_BY_OPERATOR / BORA_ACCEPTED (2026-09-14) / READ_ONLY_DESIGN_ONLY' in report_text
assert 'implementation_authorized' in report_text
assert 'PROPOSED_NOT_AUTHORIZED' in report_text
for label in ('OBSERVED', 'RECONSTRUCTED_FROM_DURABLE_EVIDENCE', 'MISSING'):
    assert label in report_text, f'report must use provenance label {label}'

# ---------------------------------------------------------------------------
# CAREER_OS_RUN_TRACE_V1 must be conceptual only -- no schema/implementation.
# ---------------------------------------------------------------------------
assert 'CAREER_OS_RUN_TRACE_V1' in report_text
assert 'no schema file' in report_text.lower() or 'no schema, no' in report_text.lower() or 'conceptually only' in report_text.lower()
assert 'no JSON Schema, Python class, or persisted file is created' in report_text

REQUIRED_TRACE_FIELDS = (
    'canonical_sha', 'run_identity', 'inputs', 'sources_attempted', 'unavailable_sources',
    'state_transitions', 'suppression_reasons', 'model_tool_provenance', 'human_handoffs',
    'artifact_hashes', 'qa_outcomes', 'terminal_state', 'first_point_of_divergence',
    'first_causal_failure_point',
)
for field in REQUIRED_TRACE_FIELDS:
    assert f'`{field}`' in report_text, f'report must define run-trace field {field}'

# ---------------------------------------------------------------------------
# Terminal outcome vs. first point of divergence vs. first causal failure
# point must be explicitly distinct three-way, not conflated pairwise or
# collapsed, per the acceptance conditions -- including the recoverable-
# divergence case where first_point_of_divergence != first_causal_failure_point.
# ---------------------------------------------------------------------------
assert 'terminal_state' in report_text and 'first_point_of_divergence' in report_text \
    and 'first_causal_failure_point' in report_text
assert 'never conflated with' in report_text.lower()
assert 'these three are never conflated' in report_text.lower()
assert 'a recoverable divergence is never labeled `first_causal_failure_point`' in report_text.lower()
assert 'explicitly not a `first_causal_failure_point`' in report_text.lower()

# ---------------------------------------------------------------------------
# Repaired multi-divergence three-way semantics: first_point_of_divergence
# remains the earliest divergence (including a recovered one); a later,
# distinct, unrecovered divergence may be first_causal_failure_point. The
# stale universal claim that every identifiable first_causal_failure_point
# is first_point_of_divergence "at the same point" must not appear, and the
# report must instead lock the narrower, correct subset relation.
# ---------------------------------------------------------------------------
STALE_UNIVERSAL_FCFP_CLAIM = (
    'every identifiable `first_causal_failure_point` is an identifiable `first_point_of_divergence` '
    'at the same point'
)
assert STALE_UNIVERSAL_FCFP_CLAIM not in report_text, \
    'report must not claim every identifiable first_causal_failure_point is first_point_of_divergence at the same point'

STALE_UNCONDITIONAL_COINCIDENCE_CLAIM = 'which is necessarily also its `first_point_of_divergence` in that run'
assert STALE_UNCONDITIONAL_COINCIDENCE_CLAIM not in report_text, \
    'report must not claim first_causal_failure_point is unconditionally also the run\'s first_point_of_divergence'

assert (
    'it equals the run\'s `first_point_of_divergence` only when no earlier recovered divergence exists'
    in report_text
), 'report must lock that first_causal_failure_point equals first_point_of_divergence only absent an earlier recovered divergence'

assert (
    'yields `first_point_of_divergence` = A and `first_causal_failure_point` = B, at two different '
    'points in the same run' in report_text
), 'report must give the explicit multi-divergence A/B example distinguishing first_point_of_divergence from first_causal_failure_point'

# ---------------------------------------------------------------------------
# Mixed attribution case: an identifiable, recovered first_point_of_divergence
# = A may coexist with a later, uninstrumented causal defect that never
# produces an identifiable point B. The report must preserve A rather than
# wiping it, and must record first_causal_failure_point as CAUSE_UNKNOWN /
# UNINSTRUMENTED_BOUNDARY rather than fabricating a point B. The pre-existing
# fully-uninstrumented symmetric-pair case must remain present unchanged.
# ---------------------------------------------------------------------------
assert 'Mixed attribution case' in report_text, \
    'report must add the mixed attribution case (recovered A coexisting with a later uninstrumented causal failure)'
assert (
    'first_point_of_divergence` = A is preserved unchanged (never wiped or reattributed) and separately '
    'records `first_causal_failure_point` = `CAUSE_UNKNOWN` / `UNINSTRUMENTED_BOUNDARY`, never inventing '
    'a fabricated point B to fill the gap' in report_text
), 'report must lock that a recovered first_point_of_divergence = A is preserved and first_causal_failure_point is CAUSE_UNKNOWN/UNINSTRUMENTED_BOUNDARY, never a fabricated B'

# ---------------------------------------------------------------------------
# Section 2.1 repair: the first_point_of_divergence and first_causal_failure_point
# table rows must each explicitly, in their own evidence-honesty rule text (not
# only in Section 3's narrative), record CAUSE_UNKNOWN / UNINSTRUMENTED_BOUNDARY
# when no instrumented point is identifiable -- and must preserve the distinction
# between the fully-uninstrumented pair case and the mixed A+unknown case. Fail
# closed if either row's own definition omits this or collapses the two cases.
# ---------------------------------------------------------------------------
FPOD_ROW_CAUSE_UNKNOWN_FRAGMENT = (
    "When no instrumented divergence point is identifiable anywhere in the run's own "
    '`state_transitions` — the causal defect lived in a boundary the trace never instrumented — '
    '`first_point_of_divergence` is itself recorded as `CAUSE_UNKNOWN` / `UNINSTRUMENTED_BOUNDARY` '
    '(the fully-uninstrumented pair case, Section 3), paired with the same label on '
    '`first_causal_failure_point`; this differs from the mixed case where `first_point_of_divergence` '
    'is identified as a concrete point A while only `first_causal_failure_point` carries `CAUSE_UNKNOWN` '
    "/ `UNINSTRUMENTED_BOUNDARY` (Section 3's mixed attribution case) — `first_point_of_divergence` is "
    'never inferred or backfilled merely because `first_causal_failure_point` cannot be identified.'
)
assert FPOD_ROW_CAUSE_UNKNOWN_FRAGMENT in report_text, \
    "report's first_point_of_divergence table row must itself record CAUSE_UNKNOWN / UNINSTRUMENTED_BOUNDARY " \
    'semantics and distinguish the fully-uninstrumented pair case from the mixed A+unknown case'

FCFP_ROW_CAUSE_UNKNOWN_FRAGMENT = (
    "More generally, whenever no instrumented causal failure point is identifiable in the run's own "
    '`state_transitions`, `first_causal_failure_point` is recorded as `CAUSE_UNKNOWN` / '
    '`UNINSTRUMENTED_BOUNDARY` — this occurs both in the fully-uninstrumented pair case above (where '
    '`first_point_of_divergence` carries the same label) and in the mixed attribution case (Section 3) '
    'where `first_point_of_divergence` is instead identified as a concrete, recovered point A; '
    '`first_causal_failure_point` is never inferred or backfilled with a fabricated point merely because '
    'an earlier divergence was identified.'
)
assert FCFP_ROW_CAUSE_UNKNOWN_FRAGMENT in report_text, \
    "report's first_causal_failure_point table row must itself record CAUSE_UNKNOWN / UNINSTRUMENTED_BOUNDARY " \
    'semantics and distinguish the fully-uninstrumented pair case from the mixed A+unknown case'

# ---------------------------------------------------------------------------
# Section 2.1 repair (Purpose column specifically): the sentinel semantics
# above must live in the table's own "Purpose" cell -- the definition of what
# the field *is* -- not only in the adjacent "Evidence-honesty rule" cell of
# the same row. Extract each row's Purpose cell (the text between the field
# name's closing pipe and the next unescaped pipe that opens the
# Evidence-honesty-rule cell) and fail closed if the sentinel wording is
# missing there, even if it is present elsewhere in the row.
# ---------------------------------------------------------------------------
FPOD_ROW_LINES = [
    line for line in report_text.splitlines()
    if line.startswith('| `first_point_of_divergence`')
]
assert len(FPOD_ROW_LINES) == 1, \
    'report must contain exactly one first_point_of_divergence table row'
FPOD_ROW_CELLS = FPOD_ROW_LINES[0].split(' | ')
assert len(FPOD_ROW_CELLS) == 3, \
    'first_point_of_divergence table row must have exactly three cells (field, Purpose, Evidence-honesty rule)'
FPOD_PURPOSE_CELL = FPOD_ROW_CELLS[1]
FPOD_PURPOSE_SENTINEL_FRAGMENT = (
    'when no instrumented divergence point is identifiable anywhere in the run\'s own '
    '`state_transitions`, the field itself is recorded as `CAUSE_UNKNOWN` / '
    '`UNINSTRUMENTED_BOUNDARY` rather than left blank or inferred'
)
assert FPOD_PURPOSE_SENTINEL_FRAGMENT in FPOD_PURPOSE_CELL, \
    "first_point_of_divergence table row's Purpose cell must itself state the field can be " \
    'CAUSE_UNKNOWN / UNINSTRUMENTED_BOUNDARY when no instrumented point is identifiable -- ' \
    'this must be part of the field definition, not only the adjacent Evidence-honesty-rule cell'

FCFP_ROW_LINES = [
    line for line in report_text.splitlines()
    if line.startswith('| `first_causal_failure_point`')
]
assert len(FCFP_ROW_LINES) == 1, \
    'report must contain exactly one first_causal_failure_point table row'
FCFP_ROW_CELLS = FCFP_ROW_LINES[0].split(' | ')
assert len(FCFP_ROW_CELLS) == 3, \
    'first_causal_failure_point table row must have exactly three cells (field, Purpose, Evidence-honesty rule)'
FCFP_PURPOSE_CELL = FCFP_ROW_CELLS[1]
FCFP_PURPOSE_SENTINEL_FRAGMENT = (
    'when no instrumented causal failure point is identifiable — including the mixed case where '
    '`first_point_of_divergence` is a concrete point A but no later point B is ever identifiable — '
    'the field itself is recorded as `CAUSE_UNKNOWN` / `UNINSTRUMENTED_BOUNDARY` rather than a '
    'fabricated point'
)
assert FCFP_PURPOSE_SENTINEL_FRAGMENT in FCFP_PURPOSE_CELL, \
    "first_causal_failure_point table row's Purpose cell must itself state the field can be " \
    'CAUSE_UNKNOWN / UNINSTRUMENTED_BOUNDARY when no instrumented point is identifiable, while ' \
    'preserving the mixed case where first_point_of_divergence is a concrete point A -- this must ' \
    'be part of the field definition, not only the adjacent Evidence-honesty-rule cell'

# ---------------------------------------------------------------------------
# Success-vs-failure absence semantics must live in the table rows' own
# Purpose cells (the field definition itself), not only in narrative prose:
# a correct terminal_state with no divergence uses NOT_APPLICABLE / NO_DIVERGENCE
# for first_point_of_divergence; any correct terminal_state uses NOT_APPLICABLE /
# NO_TERMINAL_FAILURE for first_causal_failure_point, distinct from the
# CAUSE_UNKNOWN / UNINSTRUMENTED_BOUNDARY unknown-cause label reserved for a
# genuine incorrect-terminal, unidentifiable-point case.
# ---------------------------------------------------------------------------
FPOD_NO_DIVERGENCE_SENTINEL_FRAGMENT = (
    "When the run's `terminal_state` is correct and no divergence occurred anywhere in its "
    'trajectory, `first_point_of_divergence` is instead recorded as `NOT_APPLICABLE` / '
    '`NO_DIVERGENCE`, a known-absence label distinct from `CAUSE_UNKNOWN` / `UNINSTRUMENTED_BOUNDARY`, '
    "which is reserved for an incorrect `terminal_state` where a real divergence exists but no "
    'instrumented point is identifiable.'
)
assert FPOD_NO_DIVERGENCE_SENTINEL_FRAGMENT in FPOD_PURPOSE_CELL, \
    "first_point_of_divergence table row's Purpose cell must itself state the field is " \
    'NOT_APPLICABLE / NO_DIVERGENCE for a correct terminal_state with no divergence, distinct ' \
    'from CAUSE_UNKNOWN / UNINSTRUMENTED_BOUNDARY'

FCFP_NO_TERMINAL_FAILURE_SENTINEL_FRAGMENT = (
    'For any correct `terminal_state`, `first_causal_failure_point` is recorded as `NOT_APPLICABLE` '
    '/ `NO_TERMINAL_FAILURE` — including when a recovered `first_point_of_divergence` = A is '
    'preserved unchanged — never `CAUSE_UNKNOWN` / `UNINSTRUMENTED_BOUNDARY`, because there is no '
    'terminal failure to attribute a cause to.'
)
assert FCFP_NO_TERMINAL_FAILURE_SENTINEL_FRAGMENT in FCFP_PURPOSE_CELL, \
    "first_causal_failure_point table row's Purpose cell must itself state the field is " \
    'NOT_APPLICABLE / NO_TERMINAL_FAILURE for any correct terminal_state, including when a ' \
    'recovered first_point_of_divergence = A is preserved, never CAUSE_UNKNOWN / UNINSTRUMENTED_BOUNDARY'

# ---------------------------------------------------------------------------
# Section 3 must carry an explicit success-vs-failure absence semantics
# bullet that: (a) reserves CAUSE_UNKNOWN / UNINSTRUMENTED_BOUNDARY for an
# incorrect terminal_state with a real, unidentifiable divergence/failure;
# (b) forbids CAUSE_UNKNOWN on a correct-terminal success case for either
# field; and (c) preserves the pre-existing A->B, mixed-failure, and
# fully-uninstrumented pair cases unchanged.
# ---------------------------------------------------------------------------
SUCCESS_FAILURE_ABSENCE_BULLET_FRAGMENT = (
    '**Success-vs-failure absence semantics:** `CAUSE_UNKNOWN` / `UNINSTRUMENTED_BOUNDARY` is '
    'reserved exclusively for an incorrect `terminal_state` where a real divergence or causal '
    "failure genuinely exists but no instrumented point in the run's own `state_transitions` can "
    'identify it — it is never used to describe the simple absence of any divergence or failure.'
)
assert SUCCESS_FAILURE_ABSENCE_BULLET_FRAGMENT in report_text, \
    'report must add the Section 3 success-vs-failure absence semantics bullet'

assert (
    'A run with a correct `terminal_state` and no divergence anywhere in its trajectory records '
    '`first_point_of_divergence` = `NOT_APPLICABLE` / `NO_DIVERGENCE`, a known-absence label '
    "distinct from `CAUSE_UNKNOWN` / `UNINSTRUMENTED_BOUNDARY`'s unknown-cause label." in report_text
), 'report must lock NOT_APPLICABLE / NO_DIVERGENCE for a correct terminal_state with no divergence'

assert (
    'For any correct `terminal_state` — whether or not an earlier divergence occurred — '
    '`first_causal_failure_point` is recorded as `NOT_APPLICABLE` / `NO_TERMINAL_FAILURE`, because '
    'there is no terminal failure for a causal point to explain;' in report_text
), 'report must lock NOT_APPLICABLE / NO_TERMINAL_FAILURE for any correct terminal_state'

assert (
    "when a recovered `first_point_of_divergence` = A exists alongside a correct `terminal_state`, "
    '`first_point_of_divergence` = A is preserved unchanged (exactly as in the recoverable-divergence '
    'case above) while `first_causal_failure_point` = `NOT_APPLICABLE` / `NO_TERMINAL_FAILURE` applies '
    'instead of `CAUSE_UNKNOWN` / `UNINSTRUMENTED_BOUNDARY`.' in report_text
), 'report must lock that a recovered first_point_of_divergence = A is preserved unchanged for a ' \
   'correct terminal_state while first_causal_failure_point is NOT_APPLICABLE / NO_TERMINAL_FAILURE'

assert (
    '`CAUSE_UNKNOWN` / `UNINSTRUMENTED_BOUNDARY` never appears on a correct-terminal success case '
    'for either field.' in report_text
), 'report must forbid CAUSE_UNKNOWN / UNINSTRUMENTED_BOUNDARY on correct-terminal success cases'

assert (
    'The pre-existing identifiable A→B failure case, the mixed failure case (`first_point_of_divergence` '
    '= A with `first_causal_failure_point` = `CAUSE_UNKNOWN` / `UNINSTRUMENTED_BOUNDARY`), and the '
    'fully-uninstrumented incorrect-terminal pair case (both fields `CAUSE_UNKNOWN` / '
    '`UNINSTRUMENTED_BOUNDARY`) remain preserved unchanged, because all three describe an incorrect '
    '`terminal_state`, not a correct one.' in report_text
), 'report must preserve the pre-existing A->B, mixed-failure, and fully-uninstrumented pair cases ' \
   'unchanged alongside the new success-vs-failure absence semantics'

# ---------------------------------------------------------------------------
# Repaired collapsed-framing residuals (Cursor v4 adjudicated findings): the
# report must not imply that first_point_of_divergence itself is the thing
# that "became unrecoverable" / "ever became" first_causal_failure_point --
# first_causal_failure_point may be a later, distinct divergence point B.
# Fail closed if either collapsed phrasing regresses back into the report.
# ---------------------------------------------------------------------------
COLLAPSED_FRAMING_RESIDUALS = (
    'that departure became unrecoverable',
    'that divergence became unrecoverable',
    'did it ever become a `first_causal_failure_point`',
)
for residual_phrase in COLLAPSED_FRAMING_RESIDUALS:
    assert residual_phrase not in report_text, \
        f'report must not restate the collapsed-framing residual phrase: {residual_phrase}'

assert (
    'separately again from **the earliest point — which may be that same departure, or a later, '
    'distinct divergence — after which the run\'s incorrect `terminal_state` became unavoidable** '
    '(`first_causal_failure_point`)' in report_text
), 'report must lock the repaired Section 3 wording distinguishing first_causal_failure_point from a collapsed same-point reading'

assert (
    'about whichever divergence point — the same point, or a later, distinct one — after which the '
    'run\'s incorrect `terminal_state` became unavoidable (`first_causal_failure_point`)' in report_text
), 'report must lock the repaired Section 2.3 wording distinguishing first_causal_failure_point from a collapsed same-point reading'

assert (
    'was that same point (or a later, distinct point) the run\'s `first_causal_failure_point`' in report_text
), 'report must lock the repaired closing-paragraph wording that does not ask whether divergence "ever became" first_causal_failure_point'

# ---------------------------------------------------------------------------
# Human-handoff architecture: requested action, context transferred, human
# decision/confirmation source, final outcome -- and no fabricated machine
# observability past the human boundary.
# ---------------------------------------------------------------------------
for field in ('requested_action', 'context_transferred', 'human_decision_or_confirmation_source', 'final_outcome'):
    assert field in report_text, f'report must define human-handoff field {field}'
assert 'HUMAN_ACT_NOT_MACHINE_OBSERVED' in report_text
assert 'fabricate machine observability past the human boundary' in report_text

# ---------------------------------------------------------------------------
# human_handoffs is genuine control transfer to Bora only; a model/tool
# decision belongs in model_tool_provenance, and the two entry types must
# never be merged.
# ---------------------------------------------------------------------------
assert 'never for a model/tool decision' in report_text
assert 'never merged into one entry type' in report_text

# ---------------------------------------------------------------------------
# provenance_quality is the three-value evidence-quality subset
# (OBSERVED | RECONSTRUCTED_FROM_DURABLE_EVIDENCE | MISSING); EXPERIMENTAL_NON_CANONICAL
# is excluded from per-fact provenance_quality and remains a case/architecture-status label.
# ---------------------------------------------------------------------------
assert 'three-value evidence-quality subset' in report_text
assert 'EXPERIMENTAL_NON_CANONICAL` is deliberately excluded from `provenance_quality`' in report_text
assert 'it is a case/architecture-status label' in report_text

# ---------------------------------------------------------------------------
# Bounded phase/typed-envelope contract fields.
# ---------------------------------------------------------------------------
REQUIRED_PHASE_CONTRACT_FIELDS = (
    'phase_id', 'input_refs', 'output_refs', 'decision_or_state',
    'evidence_or_provenance_refs', 'gate_outcome', 'error_or_unavailable_state',
    'authority_or_handoff_metadata',
)
for field in REQUIRED_PHASE_CONTRACT_FIELDS:
    assert f'`{field}`' in report_text, f'report must define phase-contract field {field}'

# ---------------------------------------------------------------------------
# Append-only trace facts vs. derived summaries must be explicitly separated.
# ---------------------------------------------------------------------------
assert 'append-only' in report_text.lower()
assert 'derived summaries' in report_text.lower()

# ---------------------------------------------------------------------------
# Artifact references: durable identity + hash semantics; missing/gitignored
# artifacts recorded as unavailable, never invented.
# ---------------------------------------------------------------------------
assert 'ARTIFACT_UNAVAILABLE' in report_text
assert 'never invents a hash' in report_text or 'never invented or backfilled' in report_text

# ---------------------------------------------------------------------------
# Model/tool provenance materiality boundary; no hidden reasoning/CoT.
# ---------------------------------------------------------------------------
assert 'materially relevant' in report_text
assert 'chain-of-thought' in report_text.lower()
assert 'does not require' in report_text.lower() and 'hidden reasoning' in report_text.lower()

# ---------------------------------------------------------------------------
# CI regression evals vs. live production monitoring/incidence; no
# unsupported reliability/production-frequency claim.
# ---------------------------------------------------------------------------
assert 'CI regression eval' in report_text
assert 'live production monitoring' in report_text
assert 'no production failure-rate or reliability claim' in report_text.lower() or \
    'makes no production failure-rate' in report_text.lower()

# ---------------------------------------------------------------------------
# No implementation/infrastructure selected or authorized.
# ---------------------------------------------------------------------------
NOT_AUTHORIZED_PHRASES = (
    'No database, UI, orchestration automation, new agent, model router, provider abstraction, or LLM judge.',
    'No `CAREER_OS_RUN_TRACE_V1` JSON Schema, Python class, or persisted file',
)
for phrase in NOT_AUTHORIZED_PHRASES:
    assert phrase in report_text, f'report must explicitly disclaim: {phrase}'

# ---------------------------------------------------------------------------
# Phase D/Phase E evidence consumed, not re-adjudicated.
# ---------------------------------------------------------------------------
assert 'F1-A' in report_text and 'F2-A' in report_text and 'F5-B' in report_text and 'POS-A' in report_text
assert 'No re-adjudication of Phase D' in report_text or 'not re-adjudicated' in report_text.lower()

# ---------------------------------------------------------------------------
# Phase completion / authorization discipline.
# ---------------------------------------------------------------------------
assert 'Phase G and every later roadmap phase remain **PROPOSED_NOT_AUTHORIZED**' in report_text
assert 'does not itself authorize Phase G' in report_text or "does not itself authorize" in report_text
assert 'Cursor' in report_text and 'may not repair its own findings' in report_text

# ---------------------------------------------------------------------------
# Checkpoint completed_actions must not restate the stale provenance_quality
# claim or the stale undifferentiated "causally-inevitable divergence"
# phrasing; they must carry the truthful, repaired semantics instead.
# ---------------------------------------------------------------------------
CHECKPOINT_PATH = ROOT / 'CURRENT_EXECUTION_CHECKPOINT.json'
assert CHECKPOINT_PATH.exists(), 'CURRENT_EXECUTION_CHECKPOINT.json missing'
checkpoint = json.loads(CHECKPOINT_PATH.read_text(encoding='utf-8'))
completed_actions_text = '\n'.join(checkpoint['completed_actions'])

STALE_PHRASES = (
    'reused unchanged from Phase C/D/E',
    'earliest causally-inevitable divergence',
)
for stale_phrase in STALE_PHRASES:
    assert stale_phrase not in completed_actions_text, \
        f'stale phrase must not appear in completed_actions: {stale_phrase}'

assert 'three-value per-fact evidence-quality subset of the preserved four-label Phase C/D/E vocabulary' in completed_actions_text, \
    'completed_actions must truthfully describe provenance_quality as the three-value per-fact subset of the preserved four-label vocabulary'
assert 'EXPERIMENTAL_NON_CANONICAL remaining a case/architecture-status label' in completed_actions_text, \
    'completed_actions must state EXPERIMENTAL_NON_CANONICAL remains a case/architecture-status label, not a provenance_quality value'

assert 'first_point_of_divergence (the earliest identifiable divergence point' in completed_actions_text, \
    'completed_actions must define first_point_of_divergence as the earliest identifiable divergence point, including one later recovered'
assert 'first_causal_failure_point (the divergence point' in completed_actions_text and \
    'became unavoidable' in completed_actions_text, \
    'completed_actions must define first_causal_failure_point as a divergence point (not necessarily the earliest one) after which the incorrect terminal outcome became unavoidable'
assert 'became unrecoverable' not in completed_actions_text, \
    'completed_actions must use the normalized "became unavoidable" wording, not "became unrecoverable"'
assert 'no later gate in the run' in completed_actions_text and 'recovered from it' in completed_actions_text, \
    'completed_actions must state that no later gate recovered from the first_causal_failure_point'

# ---------------------------------------------------------------------------
# Collapsed framing must not appear: first_causal_failure_point must never be
# defined as unconditionally "the earliest point" -- that erases the case
# where an earlier divergence A is recovered and a later, distinct divergence
# B is the actual first_causal_failure_point.
# ---------------------------------------------------------------------------
assert 'first_causal_failure_point (the earliest point after which' not in completed_actions_text, \
    'completed_actions must not define first_causal_failure_point as unconditionally the earliest point (collapsed framing)'

# ---------------------------------------------------------------------------
# The A/B multi-divergence rule and the equality-only-if-no-earlier-recovered-
# divergence rule must be explicitly carried in completed_actions -- this is
# the exact repair distinguishing first_point_of_divergence from
# first_causal_failure_point when an earlier recovered divergence exists.
# ---------------------------------------------------------------------------
assert 'equals first_point_of_divergence only when no earlier recovered divergence exists' in completed_actions_text, \
    'completed_actions must state first_causal_failure_point equals first_point_of_divergence only absent an earlier recovered divergence'
assert 'first_point_of_divergence = A and first_causal_failure_point = B at two different points in the same run' in completed_actions_text, \
    'completed_actions must give the explicit A/B multi-divergence example'

# ---------------------------------------------------------------------------
# Mixed attribution rule (v6 recovery-completeness repair): a recovered
# first_point_of_divergence = A can coexist with a later, uninstrumented
# causal defect that never produces an identifiable point B. completed_actions
# must preserve A unchanged and record first_causal_failure_point as
# CAUSE_UNKNOWN / UNINSTRUMENTED_BOUNDARY, never a fabricated B, and must not
# collapse this into (or drop) the pre-existing fully-uninstrumented pair case.
# ---------------------------------------------------------------------------
MIXED_ATTRIBUTION_SURFACE_FRAGMENT = (
    'first_point_of_divergence = A is preserved unchanged (never wiped or reattributed) and '
    'first_causal_failure_point is separately recorded as CAUSE_UNKNOWN / UNINSTRUMENTED_BOUNDARY '
    'rather than a fabricated point B'
)
assert MIXED_ATTRIBUTION_SURFACE_FRAGMENT in completed_actions_text, \
    'completed_actions must carry the mixed attribution rule: recovered A preserved, ' \
    'first_causal_failure_point recorded CAUSE_UNKNOWN / UNINSTRUMENTED_BOUNDARY, never a fabricated B'
assert 'fully-uninstrumented case where both fields carry that same symmetric CAUSE_UNKNOWN / UNINSTRUMENTED_BOUNDARY label' in completed_actions_text, \
    'completed_actions must preserve the fully-uninstrumented symmetric-pair case alongside the mixed attribution rule'

# ---------------------------------------------------------------------------
# Success-vs-failure absence semantics (Cursor v10 F1/F2/F3 repair) must be
# propagated to completed_actions: a correct terminal_state with no divergence
# records first_point_of_divergence as NOT_APPLICABLE / NO_DIVERGENCE; any
# correct terminal_state (including one preserving a recovered
# first_point_of_divergence = A) records first_causal_failure_point as
# NOT_APPLICABLE / NO_TERMINAL_FAILURE, never CAUSE_UNKNOWN / UNINSTRUMENTED_
# BOUNDARY, which stays reserved for a genuine incorrect-terminal case.
# ---------------------------------------------------------------------------
SUCCESS_FAILURE_ABSENCE_SURFACE_FRAGMENT = (
    'a correct terminal_state with no divergence records first_point_of_divergence as '
    'NOT_APPLICABLE / NO_DIVERGENCE, and any correct terminal_state -- including one '
    'preserving a recovered first_point_of_divergence = A unchanged -- records '
    'first_causal_failure_point as NOT_APPLICABLE / NO_TERMINAL_FAILURE, never CAUSE_UNKNOWN '
    '/ UNINSTRUMENTED_BOUNDARY, which remains reserved exclusively for an incorrect '
    'terminal_state with a real but uninstrumented divergence or causal failure'
)
assert SUCCESS_FAILURE_ABSENCE_SURFACE_FRAGMENT in completed_actions_text, \
    'completed_actions must propagate the success-vs-failure absence semantics: correct ' \
    'terminal_state with no divergence -> NOT_APPLICABLE / NO_DIVERGENCE; any correct ' \
    'terminal_state -> NOT_APPLICABLE / NO_TERMINAL_FAILURE'

# ---------------------------------------------------------------------------
# The conceptual CAREER_OS_RUN_TRACE_V1 field-list summary in completed_actions
# must include first_point_of_divergence alongside terminal_state and
# first_causal_failure_point -- omitting it is a drift regression.
# ---------------------------------------------------------------------------
assert 'terminal_state, first_point_of_divergence, and first_causal_failure_point' in completed_actions_text, \
    'completed_actions field-list summary must include first_point_of_divergence alongside terminal_state and first_causal_failure_point'

# ---------------------------------------------------------------------------
# The append-only-vs-derived summary in completed_actions must name every
# protected underlying recorded fact/event -- not just the five originally
# named -- and must state derived summaries may reinterpret but must not
# rewrite them.
# ---------------------------------------------------------------------------
PROTECTED_APPEND_ONLY_FACTS = (
    'state_transitions', 'suppression_reasons', 'artifact_hashes', 'qa_outcomes',
    'human_handoffs', 'canonical_sha', 'run_identity', 'inputs', 'sources_attempted',
    'unavailable_sources', 'model_tool_provenance', 'terminal_state',
    'first_point_of_divergence', 'first_causal_failure_point',
)
for fact in PROTECTED_APPEND_ONLY_FACTS:
    assert fact in completed_actions_text, \
        f'completed_actions append-only summary must name protected fact/event {fact}'
assert 'may reinterpret but must not rewrite them' in completed_actions_text, \
    'completed_actions append-only summary must state derived summaries may reinterpret but must not rewrite the protected facts/events'

# ---------------------------------------------------------------------------
# completed_actions must explicitly restate that human_handoffs are Bora-only
# control-passing events, never a model/tool decision, and never merged with
# model_tool_provenance -- fail closed if this restatement is dropped.
# ---------------------------------------------------------------------------
assert 'genuine Bora-only control-passing events' in completed_actions_text, \
    'completed_actions must restate human_handoffs as genuine Bora-only control-passing events'
assert 'never for a model/tool decision' in completed_actions_text, \
    'completed_actions must restate human_handoffs are never for a model/tool decision'
assert 'never merged with model_tool_provenance' in completed_actions_text, \
    'completed_actions must restate human_handoffs are never merged with model_tool_provenance'

# ---------------------------------------------------------------------------
# The CHANGELOG.md Phase F operator-completion entry must carry the same
# repaired semantics as the checkpoint's completed_actions: it must not
# restate the stale "reused unchanged from Phase C/D/E" provenance_quality
# claim, and it must separate terminal_state from BOTH first_point_of_divergence
# and first_causal_failure_point, not just from first_causal_failure_point alone.
# ---------------------------------------------------------------------------
CHANGELOG_PATH = ROOT / 'CHANGELOG.md'
assert CHANGELOG_PATH.exists(), 'CHANGELOG.md missing'
changelog_text = CHANGELOG_PATH.read_text(encoding='utf-8')

CHANGELOG_PHASE_F_COMPLETION_HEADING = (
    '## 2026-09-13 — Career OS Phase F (`CAREER_OS_TRACE_AND_CONTRACT_ARCHITECTURE_V1`) '
    'substantive read-only/design-only work completed by operator (PENDING BORA ACCEPTANCE)'
)
assert CHANGELOG_PHASE_F_COMPLETION_HEADING in changelog_text, \
    'CHANGELOG.md must contain the Phase F operator-completion entry heading'

_heading_index = changelog_text.index(CHANGELOG_PHASE_F_COMPLETION_HEADING)
_next_heading_index = changelog_text.find('\n## ', _heading_index + 1)
changelog_phase_f_block = changelog_text[_heading_index:_next_heading_index if _next_heading_index != -1 else None]

CHANGELOG_STALE_PHRASES = (
    'reused unchanged from Phase C/D/E',
    'Separated `terminal_state` from `first_causal_failure_point`, never conflating the two',
)
for stale_phrase in CHANGELOG_STALE_PHRASES:
    assert stale_phrase not in changelog_phase_f_block, \
        f'stale phrase must not appear in CHANGELOG.md Phase F completion entry: {stale_phrase}'

assert '`first_point_of_divergence`' in changelog_phase_f_block, \
    'CHANGELOG.md Phase F completion entry must name first_point_of_divergence alongside terminal_state and first_causal_failure_point'
assert 'three-value per-fact evidence-quality subset of the preserved four-label Phase C/D/E vocabulary' in changelog_phase_f_block, \
    'CHANGELOG.md Phase F completion entry must describe provenance_quality as the three-value per-fact subset of the preserved four-label vocabulary'
assert 'EXPERIMENTAL_NON_CANONICAL` remaining a case/architecture-status label' in changelog_phase_f_block, \
    'CHANGELOG.md Phase F completion entry must state EXPERIMENTAL_NON_CANONICAL remains a case/architecture-status label, not a provenance_quality value'
assert 'never conflating any of the three' in changelog_phase_f_block, \
    'CHANGELOG.md Phase F completion entry must state terminal_state, first_point_of_divergence, and first_causal_failure_point are never conflated'
assert 'no later gate in the run' in changelog_phase_f_block and 'recovered from it' in changelog_phase_f_block, \
    'CHANGELOG.md Phase F completion entry must state that no later gate recovered from the first_causal_failure_point'
assert 'may reinterpret but must not rewrite' in changelog_phase_f_block, \
    'CHANGELOG.md Phase F completion entry must state derived summaries may reinterpret but must not rewrite the protected append-only facts'
for fact in PROTECTED_APPEND_ONLY_FACTS:
    assert fact in changelog_phase_f_block, \
        f'CHANGELOG.md Phase F completion entry must name protected fact/event {fact}'

# ---------------------------------------------------------------------------
# CHANGELOG.md must also carry the A/B multi-divergence rule and the
# equality-only-if-no-earlier-recovered-divergence rule, and must not
# collapse first_causal_failure_point into "the earliest point" unconditionally.
# ---------------------------------------------------------------------------
assert 'first_causal_failure_point (the earliest point after which' not in changelog_phase_f_block, \
    'CHANGELOG.md Phase F completion entry must not define first_causal_failure_point as unconditionally the earliest point (collapsed framing)'
assert 'equals `first_point_of_divergence` only when no earlier recovered divergence exists' in changelog_phase_f_block, \
    'CHANGELOG.md Phase F completion entry must state first_causal_failure_point equals first_point_of_divergence only absent an earlier recovered divergence'
assert '`first_point_of_divergence` = A and `first_causal_failure_point` = B at two different points in the same run' in changelog_phase_f_block, \
    'CHANGELOG.md Phase F completion entry must give the explicit A/B multi-divergence example'

# ---------------------------------------------------------------------------
# CHANGELOG.md must also carry the mixed attribution rule (v6 repair): a
# recovered first_point_of_divergence = A preserved unchanged alongside a
# later uninstrumented causal defect recorded CAUSE_UNKNOWN /
# UNINSTRUMENTED_BOUNDARY, never a fabricated B, and must preserve the
# pre-existing fully-uninstrumented symmetric-pair case alongside it.
# ---------------------------------------------------------------------------
MIXED_ATTRIBUTION_CHANGELOG_FRAGMENT = (
    '`first_point_of_divergence` = A is preserved unchanged (never wiped or reattributed) and '
    '`first_causal_failure_point` is separately recorded as `CAUSE_UNKNOWN` / `UNINSTRUMENTED_BOUNDARY` '
    'rather than a fabricated point B'
)
assert MIXED_ATTRIBUTION_CHANGELOG_FRAGMENT in changelog_phase_f_block, \
    'CHANGELOG.md Phase F completion entry must carry the mixed attribution rule: recovered A ' \
    'preserved, first_causal_failure_point recorded CAUSE_UNKNOWN / UNINSTRUMENTED_BOUNDARY, never a fabricated B'
assert 'fully-uninstrumented case where both fields carry that same symmetric `CAUSE_UNKNOWN` / `UNINSTRUMENTED_BOUNDARY` label' in changelog_phase_f_block, \
    'CHANGELOG.md Phase F completion entry must preserve the fully-uninstrumented symmetric-pair case alongside the mixed attribution rule'

# ---------------------------------------------------------------------------
# The CHANGELOG.md Phase F completion entry must also carry the success-vs-
# failure absence semantics (Cursor v10 F1/F2/F3 repair), matching the
# checkpoint's completed_actions wording exactly (backtick-quoted style).
# ---------------------------------------------------------------------------
SUCCESS_FAILURE_ABSENCE_CHANGELOG_FRAGMENT = (
    'a correct `terminal_state` with no divergence records `first_point_of_divergence` as '
    '`NOT_APPLICABLE` / `NO_DIVERGENCE`, and any correct `terminal_state` -- including one '
    'preserving a recovered `first_point_of_divergence` = A unchanged -- records '
    '`first_causal_failure_point` as `NOT_APPLICABLE` / `NO_TERMINAL_FAILURE`, never '
    '`CAUSE_UNKNOWN` / `UNINSTRUMENTED_BOUNDARY`, which remains reserved exclusively for an '
    'incorrect `terminal_state` with a real but uninstrumented divergence or causal failure'
)
assert SUCCESS_FAILURE_ABSENCE_CHANGELOG_FRAGMENT in changelog_phase_f_block, \
    'CHANGELOG.md Phase F completion entry must propagate the success-vs-failure absence ' \
    'semantics: correct terminal_state with no divergence -> NOT_APPLICABLE / NO_DIVERGENCE; ' \
    'any correct terminal_state -> NOT_APPLICABLE / NO_TERMINAL_FAILURE'
assert 'became unrecoverable' not in changelog_phase_f_block, \
    'CHANGELOG.md Phase F completion entry must use the normalized "became unavoidable" wording, not "became unrecoverable"'

# ---------------------------------------------------------------------------
# The CHANGELOG.md Phase F completion entry must carry the same explicit
# human_handoffs Bora-only / never-merged-with-model_tool_provenance
# restatement as the checkpoint's completed_actions.
# ---------------------------------------------------------------------------
assert 'genuine Bora-only control-passing events' in changelog_phase_f_block, \
    'CHANGELOG.md Phase F completion entry must restate human_handoffs as genuine Bora-only control-passing events'
assert 'never for a model/tool decision' in changelog_phase_f_block, \
    'CHANGELOG.md Phase F completion entry must restate human_handoffs are never for a model/tool decision'
assert 'never merged with `model_tool_provenance`' in changelog_phase_f_block, \
    'CHANGELOG.md Phase F completion entry must restate human_handoffs are never merged with model_tool_provenance'

# ---------------------------------------------------------------------------
# Live Phase F recovery/state surfaces must not restate the stale two-way
# terminal-state-vs-first-causal-failure-point shorthand, and must instead
# name first_point_of_divergence alongside terminal_state and
# first_causal_failure_point (the three-way distinction the accepted report
# actually defines).
# ---------------------------------------------------------------------------
STALE_TWO_WAY_SHORTHAND = 'terminal-state-vs-first-causal-failure-point'

# The old, collapsed one-line capsule definition: it implied
# first_causal_failure_point is unconditionally "the earliest point" -- the
# same point as first_point_of_divergence -- with no room for a later,
# distinct, unrecovered divergence B. This must never regress back into any
# live recovery/state surface.
STALE_COLLAPSED_CAPSULE_FRAGMENT = (
    'first_causal_failure_point = the earliest point after which no later gate recovered'
)

LIVE_PHASE_F_SURFACES = (
    ROOT / 'AGENTS.md',
    ROOT / 'CURRENT_STATE.md',
    ROOT / 'CURRENT_MILESTONE.md',
    ROOT / 'CURRENT_EXECUTION_CHECKPOINT.json',
    ROOT / 'project_state.json',
    ROOT / 'docs' / 'decisions' / 'ADR-CAREER-OS-EVAL-HARNESS-SEQUENCE-V1.md',
)

for surface_path in LIVE_PHASE_F_SURFACES:
    assert surface_path.exists(), f'live Phase F surface missing: {surface_path}'
    surface_text = surface_path.read_text(encoding='utf-8')
    assert STALE_TWO_WAY_SHORTHAND not in surface_text, \
        f'stale two-way shorthand must not appear in {surface_path.name}'
    assert 'first_point_of_divergence' in surface_text, \
        f'{surface_path.name} must name first_point_of_divergence, not just terminal_state/first_causal_failure_point'
    assert STALE_COLLAPSED_CAPSULE_FRAGMENT not in surface_text, \
        f'{surface_path.name} must not restate the collapsed capsule framing that makes ' \
        f'first_causal_failure_point unconditionally the same earliest point as first_point_of_divergence'
    assert 'equals first_point_of_divergence only when no earlier recovered divergence exists' in surface_text, \
        f'{surface_path.name} must state first_causal_failure_point equals first_point_of_divergence ' \
        f'only when no earlier recovered divergence exists'
    assert 'first_point_of_divergence = A and first_causal_failure_point = B at two different points in the same run' in surface_text, \
        f'{surface_path.name} must carry the explicit A/B multi-divergence example ' \
        f'(recovered A vs. later, distinct, unrecovered B)'
    # Success-vs-failure absence semantics (Cursor v10 F1/F2/F3 repair): every
    # live recovery/state surface must propagate the same success-side
    # distinction the accepted report locks -- a clean correct terminal with
    # no divergence records first_point_of_divergence as NOT_APPLICABLE /
    # NO_DIVERGENCE; any correct terminal (including one preserving a
    # recovered first_point_of_divergence = A) records first_causal_failure_point
    # as NOT_APPLICABLE / NO_TERMINAL_FAILURE, never CAUSE_UNKNOWN /
    # UNINSTRUMENTED_BOUNDARY, which stays reserved for a genuine
    # incorrect-terminal, uninstrumented case.
    assert SUCCESS_FAILURE_ABSENCE_SURFACE_FRAGMENT in surface_text, \
        f'{surface_path.name} must propagate the success-vs-failure absence semantics: correct ' \
        f'terminal_state with no divergence -> NOT_APPLICABLE / NO_DIVERGENCE; any correct ' \
        f'terminal_state -> NOT_APPLICABLE / NO_TERMINAL_FAILURE'
    assert 'became unrecoverable' not in surface_text, \
        f'{surface_path.name} must use the normalized "became unavoidable" wording, not "became unrecoverable"'
    # Mixed attribution rule (v6 recovery-completeness repair): a recovered
    # first_point_of_divergence = A can coexist with a later, uninstrumented
    # causal defect with no identifiable point B. Every live recovery/state
    # surface must preserve A unchanged and record first_causal_failure_point
    # as CAUSE_UNKNOWN / UNINSTRUMENTED_BOUNDARY, never a fabricated B, and
    # must not drop the pre-existing fully-uninstrumented symmetric pair case.
    assert MIXED_ATTRIBUTION_SURFACE_FRAGMENT in surface_text, \
        f'{surface_path.name} must carry the mixed attribution rule: recovered A preserved, ' \
        f'first_causal_failure_point recorded CAUSE_UNKNOWN / UNINSTRUMENTED_BOUNDARY, never a fabricated B'
    assert 'fully-uninstrumented case where both fields carry that same symmetric CAUSE_UNKNOWN / UNINSTRUMENTED_BOUNDARY label' in surface_text, \
        f'{surface_path.name} must preserve the fully-uninstrumented symmetric-pair case alongside the mixed attribution rule'

# ---------------------------------------------------------------------------
# project_state.json's conceptual field list must include all three:
# terminal_state, first_point_of_divergence, first_causal_failure_point.
# ---------------------------------------------------------------------------
PROJECT_STATE_PATH = ROOT / 'project_state.json'
project_state_text = PROJECT_STATE_PATH.read_text(encoding='utf-8')
for concept_field in ('terminal_state', 'first_point_of_divergence', 'first_causal_failure_point'):
    assert concept_field in project_state_text, \
        f'project_state.json conceptual field list must include {concept_field}'

print('PASS: Career OS Phase F trace/contract architecture report verified.')
