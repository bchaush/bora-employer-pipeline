# ADR — Alternative Qualification Branch Representation v1

Status: **PROPOSED_FOR_IMPLEMENTATION_REVIEW**
Date: 2026-09-02
Approved by: Bora / ChatGPT Work (architecture decision milestone; independent Cursor implementation review pending)

## Context

`LIVE_EMPLOYER_TRUTH_AND_CANDIDATE_APPLICATION_GATE_AUDIT_V1` and
`ALTERNATIVE_QUALIFICATION_BRANCH_REPRESENTATION_CAUSALITY_V1` reproduced a
real employer-truth representation defect on two live, currently-open real
controls:

- **CASE_D** — Application Analyst (Digital Workplace), MBTA, Job #26-20235
- **CASE_E** — Application Analyst - Digital Workplace (Contractor), MBTA,
  Job #20260804A-ITS87

Both postings state that ANY of several education/experience branches
satisfies one mandatory employer gate (e.g. CASE_D: HS/GED + 10 years
system-analysis experience, OR Associate's + 6 years, OR Bachelor's + 3
years, OR Master's in a related subject + 1 year). Current `Requirement`
records are flat, atomic, single-condition rows; `structured_extraction.json`
for both fixtures represents only the flat Bachelor's-branch condition.
`job_decision.py`'s hard-blocker loop treats each mandatory HIGH `NONE` row
independently, so naively representing every branch as its own mandatory
row would fabricate false blockers, and the current schema has no
alternative/OR-grouping concept at all.

Four subsequent read-only architecture passes
(`ALTERNATIVE_QUALIFICATION_BRANCH_ARCHITECTURE_DECISION_V1`,
`NEGATIVE_SUFFICIENCY_AND_SUPPORT_SEMANTICS_FINAL_AUDIT`,
`MATCH_TRUTH_PROVENANCE_FINAL_CORRECTION`) iteratively resolved two
remaining architecture questions: (1) how alternative qualification
composition should be represented without breaking Requirement-row atomicity
or requiring fixture migration, and (2) exactly when a `NONE` match result
may be treated as conclusive enough to close (`block`) a qualification-gate
leaf, without silently reintroducing a fabricated-negative class of the kind
prior closed milestones (`SOURCE_SEMANTIC_ROLE_QUALIFICATION_VIEW_V1`,
`DOMAIN_QUALIFIED_EXPERIENCE_DURATION_UNKNOWN_V1`) already had to correct.

This ADR records the converged answer to both questions.

### Terminology note (permanent — do not remove)

The repository already contains `derive_qualification_gate()` in
`src/requirement_source_role.py`, part of the closed
`SOURCE_SEMANTIC_ROLE_QUALIFICATION_VIEW_V1` milestone. That function
derives a **per-Requirement-row** `YES`/`NO`/`AMBIGUOUS` entry-gating
eligibility view from a single row's `source_semantic_role` — it answers
"is this one row eligible to independently gate a decision at all." It is
evaluated once per row, in isolation.

The new **`qualification_gate` record** introduced by this ADR is a
completely different concept: an **employer-level, multi-Requirement,
alternative-branch composition record** (e.g. "any ONE of these four
education/experience combinations satisfies this posting's degree gate").
It answers "which combination of rows, together, satisfies one employer
condition," never a single-row eligibility question.

**`qualification_gate` record != `derive_qualification_gate()` per-row
eligibility view.** The two names are unfortunately similar; this note is
permanent and must not be removed by future edits. No existing committed
function is renamed by this ADR.

## Decision

Adopt **Option B**: Requirement rows remain atomic; alternative employer
qualification composition is represented separately, in a new
`qualification_gate` record, additive within `structured_extraction.json`,
referencing existing/new Requirement IDs via a recursive boolean expression.
Gate leaf truth is derived at evaluation time by a new, deterministic,
conservative, path-keyed Match-truth policy — never authored inside the
gate record itself.

### 1. Requirements remain atomic

`Requirement` records remain canonical atomic employer statements.
`schemas/requirement.schema.json` is **not modified** by this milestone. No
`qualification_group_id`/`qualification_branch_id` or equivalent field is
added to Requirement rows.

### 2. Separate qualification-gate record (Employer truth only)

A new `qualification_gate` record represents alternative composition.
Canonical eventual storage: additive `qualification_gates: []` inside
`structured_extraction.json` — the same already-canonical, per-job derived-
truth container `requirements[]` already lives in; no sidecar file, no
second source of truth.

Conceptual fields:

```
qualification_gate_id
job_id
source_text              # array of exact raw-source excerpts -- see §3
source_location
logic_expression          # terms reference existing Requirement IDs only
unmodeled_branches_note  # optional, bounded, e.g. certification-branch
                         # arithmetic the employer source does not state
                         # explicitly and which must not be invented
extraction/classification lineage, as required by the final schema design
```

**Operator scope (V1, conservative)**: the gate schema/evaluator may reuse
`application_logic.py`'s existing four-operator expression shape
(`ALL_OF`/`ANY_OF`/`AT_LEAST_N`/`NOT`) if doing so costs nothing beyond
what CASE_D/CASE_E already need — the real MBTA controls currently
demonstrate only `ALL_OF`/`ANY_OF`. **CASE_D and CASE_E must author only
employer-demonstrated `ALL_OF`/`ANY_OF` logic.** `AT_LEAST_N`/`NOT` must
not be authored for any `qualification_gate` until a real employer source
requires them — retaining the shared expression shape for schema/evaluator
reuse is acceptable and harmless; inventing an `AT_LEAST_N`/`NOT` branch
merely because the shape supports it is not. This is not a generic
qualification rules language; it is the smallest expression shape that
already exists, applied narrowly.

The gate contains **employer truth only**. It carries **no** candidate
Evidence/Claim/match-state field, and **no** per-leaf sufficiency judgment
(`negative_sufficient` or equivalent) — this was proposed in an earlier pass
of this same architecture decision and explicitly rejected: a candidate-
specific judgment inside an employer-truth record would make the gate
invalid the moment candidate evidence changes, violating the static-gate
invariant below.

Example (CASE_D, illustrative, not authored by this ADR):

```json
{
  "qualification_gate_id": "GATE_D_DEGREE_EXPERIENCE",
  "job_id": "JOB_D",
  "source_text": [
    "Bachelor's degree from an accredited institution.",
    "Three (3) years of experience in system analysis, including enterprise application design, configuration / development, implementation, and support.",
    "A Master's degree in a related subject substitute for two (2) years of general experience."
  ],
  "source_location": "Minimum Qualifications + Substitutions",
  "logic_expression": {
    "op": "ANY_OF",
    "terms": [
      {"op": "ALL_OF", "terms": ["REQ_D_DEGREE_HS_BRANCH", "REQ_D_SYS_ANALYSIS_10Y_BRANCH"]},
      {"op": "ALL_OF", "terms": ["REQ_D_DEGREE_ASSOC_BRANCH", "REQ_D_SYS_ANALYSIS_6Y_BRANCH"]},
      {"op": "ALL_OF", "terms": ["REQ_D_DEGREE", "REQ_D_SYS_ANALYSIS_EXP"]},
      {"op": "ALL_OF", "terms": ["REQ_D_DEGREE_MASTERS_BRANCH", "REQ_D_SYS_ANALYSIS_1Y_BRANCH"]}
    ]
  },
  "unmodeled_branches_note": "Certification branch intentionally not modeled: the employer source does not state the resulting base-experience arithmetic explicitly."
}
```

### 3. Raw-source traceability (fail-closed, mandatory, deterministic)

`source_text` on a `qualification_gate` is an **array of exact excerpts**,
not a single synthetic combined sentence — a gate composed from multiple
raw-source locations (e.g. the base Minimum-Qualifications sentence plus a
separate Substitutions-paragraph sentence) must cite each excerpt
separately, never paraphrase or merge them into invented connective
wording.

**Deterministic V1 traceability rule**: a gate is valid only if, for
**every** string in its `source_text` array, that exact string is a
substring of the job's captured `jd.txt`, after **whitespace-only
normalization** (collapsing runs of whitespace, trimming leading/trailing
whitespace) and nothing else. No other normalization (case-folding,
punctuation stripping, stemming, synonym matching) is permitted for this
check.

**Explicitly prohibited as a traceability mechanism**: semantic similarity,
embeddings, or any model judgment. A gate's `source_text` must never assert
wording `jd.txt` does not contain, even if a human or model believes it is
an accurate paraphrase.

This is a small, exact-substring-after-whitespace-normalization check — not
span indexing, not a parser, not an NLU component. It is sufficient to
prove every excerpt was actually captured from the employer's own posting,
which is the only invariant that matters: **gate composition must be
deterministically traceable back to captured raw employer text.**

- **CASE_D**: `jd.txt` already contains the relevant substitution/
  questionnaire text — an extraction-only correction is needed.
- **CASE_E**: `jd.txt` currently omits the live posting's Substitutions
  section and its full supplemental questionnaire entirely (confirmed by
  direct live re-fetch during the predecessor audits) — `jd.txt` must be
  corrected first, before any gate record referencing that content may be
  authored for CASE_E.

### 4. Match-truth evaluation provenance (additive, minimal)

`EvidenceMatch` (`schemas/evidence_match.schema.json`) gains one new,
additive, stable, machine-readable field: `evaluation_path`.

**Correction (population sites)**: `evaluation_path` is populated at the
actual result-producing sites, not inside a single call tree.
`src/requirement_match.py::match_requirement()` does **not** call the
narrow duration evaluators. The real routing is:
`src/job_analysis.py` partitions each job's `requirements[]` into three
disjoint groups — `generic_range_requirements`,
`domain_qualified_duration_requirements`, `remaining_requirements` — then
calls, respectively, `evaluate_generic_experience_range()`
(`src/experience_range.py`), `evaluate_domain_qualified_duration_requirement()`
(`src/domain_qualified_duration.py`), and `match_requirements()`/
`match_requirement()` (`src/requirement_match.py`) for
`remaining_requirements` only, then recombines all three result sets keyed
by `requirement_id` (`src/job_analysis.py:404-457`, confirmed by direct
reading). `src/job_analysis.py` is the routing/orchestration layer; the
three result-producing sites each populate their own `evaluation_path`
value on the records they themselves produce. Human-readable `explanation`
text must never control consequential logic.

V1 enumerates only currently-real paths, closed, not a general ontology,
with exact deterministic production rules:

| `evaluation_path` | Produced by | Exact rule |
|---|---|---|
| `NONE_TRAP` | `match_requirement()` | The explicit `_NONE_TRAPS` branch fires: `req_caps.intersection(trap_caps)` non-empty |
| `NO_CAPABILITY_OVERLAP` | `match_requirement()` | `infer_requirement_capabilities(requirement)` is non-empty, but no reusable Claim's capabilities intersect it (`best_claim is None or not best_overlap`) |
| `NO_CAPABILITY_COVERAGE` | `match_requirement()` | `infer_requirement_capabilities(requirement)` is empty (the generic "No specific capability tags inferred" fallback) |
| `FULL_CAPABILITY_MATCH` | `match_requirement()` | `req_caps.issubset(claim_caps)` for the best-overlap Claim (STRONG/SUPPORTED) |
| `PARTIAL_CAPABILITY_MATCH` | `match_requirement()` | Non-empty overlap, but `req_caps` is not a full subset of `claim_caps` (PARTIAL) |
| `EXPERIENCE_RANGE_EVALUATOR` | `evaluate_generic_experience_range()` (`src/experience_range.py`) | Any result this evaluator produces (always `UNKNOWN` today, by that module's own closed design) |
| `DOMAIN_QUALIFIED_DURATION_EVALUATOR` | `evaluate_domain_qualified_duration_requirement()` (`src/domain_qualified_duration.py`) | Any result this evaluator produces (always `UNKNOWN` today, by that module's own closed design) |

**A distinct, non-`NONE` failure class exists and is explicitly not one of
the seven paths above**: `match_requirements()`'s
`POSITIVE_MATCH_WITHOUT_PROVENANCE` check (`src/requirement_match.py:1091-1101`)
is a defensive validator rejection, not a match result — it fires only if a
`STRONG`/`SUPPORTED`/`PARTIAL` result somehow lacks `evidence_ids`/
`claim_ids` (a state `match_requirement()`'s own logic should never
produce). When it fires, that requirement is excluded from `matches[]`
entirely and recorded in `errors[]` instead; `match_requirements()` returns
`valid: false`, and `job_analysis.py` short-circuits the **entire**
`analyze_job()` call before any qualification-gate evaluation is ever
reached (`if not match_result["valid"]: ... return empty`, confirmed by
direct reading). A requirement affected by this path therefore **never
produces an `EvidenceMatch.result` a gate leaf could see** — Option B is
selected: **this is not classified as one of the seven `evaluation_path`
values; it fails the whole job-analysis call closed, upstream of gate
evaluation, and requires no leaf-adapter handling.**

### 5. Qualification support states — not candidate fact truth

The qualification gate evaluates current, bounded **match support** truth —
never a claim about candidate factual reality.

```
SUPPORTED
BLOCKED_BY_MATCHING_POLICY
UNRESOLVED
```

**`NONE_TRAP` is explicitly not labeled "unsupported by current evidence."**
`_NONE_TRAPS` fire unconditionally on capability-tag intersection, **before**
any Claim is examined — confirmed by direct reading of
`src/requirement_match.py`'s `match_requirement()`, in which the
`_NONE_TRAPS` loop runs first and returns `NONE` purely from
`req_caps.intersection(trap_caps)`, independent of `reusable_claims`
content. A trap would continue to fire identically even if a future, exact,
approved Claim carried the trapped capability tag. Calling this
"unsupported by current evidence" would misleadingly imply future-evidence-
sensitivity the mechanism does not have.

`BLOCKED_BY_MATCHING_POLICY` means: **the current deterministic matcher
intentionally refuses this requirement class/transfer under an explicitly
coded protection rule.** It does **not** mean Bora factually lacks the
qualification, and it does **not** mean current approved evidence was
exhaustively checked and proved absence.

### 6. V1 leaf adapter (conservative, locked)

```
STRONG / SUPPORTED                              -> SUPPORTED
PARTIAL / UNKNOWN                                -> UNRESOLVED
NONE, evaluation_path == NONE_TRAP               -> BLOCKED_BY_MATCHING_POLICY
NONE, evaluation_path == NO_CAPABILITY_OVERLAP   -> UNRESOLVED
NONE, evaluation_path == NO_CAPABILITY_COVERAGE  -> UNRESOLVED
missing/unrecognized evaluation_path             -> UNRESOLVED
any unrecognized result                          -> UNRESOLVED
```

`NO_CAPABILITY_OVERLAP` is deliberately **excluded** from
`BLOCKED_BY_MATCHING_POLICY` in V1. This was proven necessary, not merely
cautious: the identical capability signature `{bachelors_degree_credential}`
can arise from both a complete, single-concept requirement ("Bachelor's
degree") and an incomplete, compound one ("Bachelor's degree and required
professional certification") — empirically confirmed during
`NEGATIVE_SUFFICIENCY_AND_SUPPORT_SEMANTICS_FINAL_AUDIT`. No tag-signature-
based allowlist can safely disambiguate these without span-level text-
coverage analysis, which this milestone explicitly does not build (see
Non-Goals).

No leaf state is automatically derived from: non-empty inferred
capabilities alone; a null `domain`; a null `experience_level`; explanation
formatting; or the current absence of Claim overlap alone.

### 7. Tree-walker adapter — internal only

```
SUPPORTED                  -> TRUE
BLOCKED_BY_MATCHING_POLICY -> FALSE
UNRESOLVED                 -> UNCERTAIN
```

`application_logic.evaluate_expression()`/`_evaluate()` is reused
**unmodified** as the deterministic tree walker — confirmed by direct
reading to already be leaf-value-agnostic (it consumes only pre-computed
`TRUE`/`FALSE`/`UNCERTAIN` values, never `EvidenceMatch` results directly).
`application_logic.RESULT_TO_LOGIC_VALUE`/`result_to_logic_value()`
(Application Gate's own, differently-purposed `NONE -> UNCERTAIN` mapping)
is **never** reused for qualification gates. Shared mechanism does not
imply shared business meaning.

### 8. Three-valued gate semantics

```
ANY_OF: one TRUE -> TRUE; no TRUE + one UNCERTAIN -> UNCERTAIN; all FALSE -> FALSE
ALL_OF: one FALSE -> FALSE; no FALSE + one UNCERTAIN -> UNCERTAIN; all TRUE -> TRUE
```

Gate business outputs: `TRUE -> SUPPORTED`; `FALSE -> BLOCKED_BY_MATCHING_POLICY`;
`UNCERTAIN -> UNRESOLVED`. Gate `FALSE` means every viable branch is blocked
under the current bounded matching policy — never a statement of candidate
factual falsehood.

### 9. Output / UX

- **Gate `SUPPORTED`**: no hard blocker; failed alternative branches produce
  **no** qualification-gap entries — the employer only required one branch
  to clear, and surfacing the others would misleadingly imply a missing
  requirement.
- **Gate `UNRESOLVED`**: one `qualification_unknowns` entry citing the gate,
  identifying which branch(es)/leg(s) are unresolved and closest to
  resolvable, with source provenance retained.
- **Gate `BLOCKED_BY_MATCHING_POLICY`**: one `hard_blockers` entry citing the
  gate ID, employer source text, branch diagnostics, and the matching-policy
  reason — not one blocker per underlying row. Wording must make clear this
  is a system support/policy result, not a statement of candidate factual
  absence.

### 10. Ungrouped-requirement interaction

`job_decision.py`'s existing per-row hard-blocker loop gains one additive
membership-skip: any `requirement_id` referenced by some `qualification_gate`
is evaluated only through that gate, never independently double-counted.
Every requirement not referenced by any gate retains its exact current
behavior — byte-unchanged.

**Deliberate, explicitly recorded asymmetry**: `NO_CAPABILITY_OVERLAP` may
still independently block an *ordinary, ungrouped* mandatory-HIGH
requirement under existing, unmodified `job_decision.py` behavior, while the
new gate adapter treats the identical evaluation path as `UNRESOLVED`. This
is not silently "fixed" by this milestone — the broader NONE-vs-UNKNOWN
question for ungrouped requirements remains open, separate, and explicitly
out of scope (`CURRENT_STATE.md`: "NONE-vs-UNKNOWN is NOT globally solved").
The gate is intentionally held to a stricter standard because it exists
specifically to model compound/branch employer language, where the risk
this asymmetry guards against is exactly what is being represented.

### 11. Zero / multiple gates per job

Zero `qualification_gate` records on a job is valid and means existing
(ungrouped) behavior for every requirement on that job — the common case
for all 17 currently-unaffected fixtures. Multiple, independent
`qualification_gate` records on one job are allowed (e.g. a degree/
experience gate and, separately, a certification-OR-experience gate
elsewhere in the same posting); each gate is evaluated **independently**.
Final qualification aggregation must not let satisfaction of one gate
erase or suppress an independent, separate mandatory gate — each gate's
`SUPPORTED`/`UNRESOLVED`/`BLOCKED_BY_MATCHING_POLICY` result and its
own blocker/unknown output (§9) are computed and surfaced on their own.
No real fixture currently requires a second gate on one job; a synthetic
multi-gate unit test is required (§ Verification Required) rather than
authoring a real multi-gate fixture prematurely.

### 12. Application Gate separation — hard invariant

```
qualification_gate_result != application_question_answer
```

CASE_E proves why this matters concretely: its live posting exposes the
same Master's-substitution structure as CASE_D, but its own supplemental
questionnaire independently asks a strict, fixed "Do you have at least
three (3) years of experience in system analysis...?" with no branch
language at all (re-verified live during
`ALTERNATIVE_QUALIFICATION_BRANCH_REPRESENTATION_CAUSALITY_V1`). A
`SUPPORTED` posting-level qualification-gate result must never auto-answer
that form question `YES`. Both may reuse the same deterministic tree-walker
mechanism; neither may read the other's result. Application Gate remains
its own independent employer/actionability truth surface.

**Scope clarification**: this milestone does **not** require live
Application Gate capture merely to prove architectural separation. A
focused unit test may use a synthetic/mock `ApplicationQuestion`/answer
state to prove `qualification_gate_result` does not populate, mutate, or
auto-answer `application_question_answer` (§ Verification Required). Real
CASE_E Application Gate capture (actually authoring `ApplicationAttempt`/
`ApplicationQuestion` records from its live questionnaire) remains
separately deferred (see Non-Goals).

### 13. Backwards compatibility

Jobs without employer alternative-qualification logic require no gate, no
fixture migration, and no behavior change. All 15 golden fixtures and
Atominvest/MIT LL remain unchanged unless a real source independently
demonstrates genuine branch logic for them.

## Why

Smallest reliable design proven across four converging architecture passes:
zero migration cost for the 17 unaffected fixtures; Requirement rows stay
atomic and byte-unchanged; a proven, tested logic primitive is reused
without duplication or modification; the one genuinely dangerous decision
in this whole problem — when a `NONE` may become an operational negative —
is isolated into one small, explicit, conservative, code-reviewed,
candidate-independent policy table, rather than being smeared across rows,
authored per-instance, or silently inherited from a differently-purposed
module (Application Gate's `NONE -> UNCERTAIN` mapping).

## Alternatives Considered

- **Option A — fields on Requirement rows** (`qualification_group_id`/
  `qualification_branch_id`). Rejected: breaks row atomicity (a row's true
  logical role becomes recoverable only by joining the whole array),
  duplicates relational metadata across every member row, weaker branch-
  level provenance, and a new class of cross-row consistency validator
  would be required that this schema has never previously needed.
- **`negative_sufficient` authored inside the gate record** (an
  intermediate design considered and rejected during this same architecture
  decision). Rejected: conflates Employer truth with Match truth and
  violates the static-gate invariant — a gate record would need editing
  every time candidate evidence changed, which the final design proves is
  never necessary.
- **Broad `evaluation_path`-based negative-sufficiency allowlist** (treating
  `NO_CAPABILITY_OVERLAP` as safe whenever `domain`/`experience_level` are
  null). Rejected: proven unsafe by direct construction — six concrete
  counterexamples (`NEGATIVE_SUFFICIENCY_AND_SUPPORT_SEMANTICS_FINAL_AUDIT`
  §5) showed this heuristic incorrectly treats materially-incomplete
  compound requirements as conclusive.
- **No `EvidenceMatch` NONE ever becomes a gate negative in V1** (fully
  conservative). Rejected as *too* conservative: it would make the gate
  structurally incapable of ever reaching `BLOCKED_BY_MATCHING_POLICY`, even
  for the unambiguous `NONE_TRAP` class already individually reviewed and
  already trusted as a whole-row hard blocker for ordinary requirements
  today — defeating the purpose of building the gate at all.

## Risks / Tradeoffs

- `NONE_TRAP`'s `BLOCKED_BY_MATCHING_POLICY` label, while more accurate than
  "unsupported by current evidence," still requires careful UX wording so
  Bora does not read it as a permanent, unappealable fact — it is a policy
  refusal, reviewable and changeable only by a future, separately-approved
  code change to `_NONE_TRAPS`, not by new Evidence/Claims alone.
- The ungrouped-vs-gated `NO_CAPABILITY_OVERLAP` asymmetry (§10) is a real,
  visible inconsistency in the codebase going forward; it is deliberate and
  documented, not accidental, but a future maintainer unfamiliar with this
  ADR could mistake it for a bug.
- `evaluation_path` requires a small, additive change to
  `match_requirement()` and the two narrow evaluators
  (`evaluate_generic_experience_range()`,
  `evaluate_domain_qualified_duration_requirement()`) — each populating its
  own value at its own result-producing site, per §4. Together with the new
  gate module, the `job_decision.py` skip-check, and `job_analysis.py`'s
  routing/wiring updates, this is a wider — though still each individually
  small and additive — touch surface than a single-file change; see
  Affected Areas.
- CASE_E requires a raw-source (`jd.txt`) correction before any gate can be
  authored for it — an extra prerequisite step this milestone must sequence
  correctly.

## Affected Areas

This is a **proposed implementation surface only** — nothing below is
implemented by this ADR itself.

Schemas:
- New: `schemas/qualification_gate.schema.json`
- Additive: `schemas/evidence_match.schema.json` (`evaluation_path`)
- Additive: `schemas/job_analysis_result.schema.json` (optional gate-result
  output fields)

Code:
- New: a small, bounded qualification-gate evaluator/module (leaf-adapter +
  conservative `_NEGATIVE_SUFFICIENT_EVALUATION_PATHS` policy table +
  thin wrapper around unmodified `application_logic.evaluate_expression()`)
- Additive: `src/requirement_match.py` (`evaluation_path` population for the
  five paths it produces — `NONE_TRAP`, `NO_CAPABILITY_OVERLAP`,
  `NO_CAPABILITY_COVERAGE`, `FULL_CAPABILITY_MATCH`,
  `PARTIAL_CAPABILITY_MATCH` — no change to existing result/explanation
  logic)
- Additive: `src/experience_range.py` (`evaluation_path` population:
  `EXPERIENCE_RANGE_EVALUATOR`)
- Additive: `src/domain_qualified_duration.py` (`evaluation_path`
  population: `DOMAIN_QUALIFIED_DURATION_EVALUATOR`)
- Additive: `src/job_analysis.py` — the routing/orchestration layer that
  partitions `requirements[]` and recombines the three result-producing
  paths (§4); gains reading/passing-through of `qualification_gates[]` from
  `structured_extraction.json` and gate-result output wiring
- Additive: `src/requirement_normalize.py` — as needed for
  `qualification_gates[]` to pass through normalization/ingestion alongside
  `requirements[]`, without weakening its existing fail-closed guarantees
- Additive: `src/job_decision.py` (gate-membership exclusion in the existing
  hard-blocker loop)

Fixtures:
- `fixtures/jobs/CASE_D_MBTA_DIRECT_APPLICATION_ANALYST/structured_extraction.json`
  (new branch Requirement rows + one gate record)
- `fixtures/jobs/CASE_E_MBTA_CONTRACTOR_APPLICATION_ANALYST/jd.txt` (raw-text
  restoration, first) then its `structured_extraction.json`

Tests: new focused tests per Verification Required, below.

Not modified: `schemas/requirement.schema.json`, `src/application_logic.py`,
all 15 golden fixtures, Atominvest, MIT LL.

## Verification Required

- Tree-walker `TRUE`/`FALSE`/`UNCERTAIN` behavior (§8), reused unmodified.
- `NO_CAPABILITY_OVERLAP -> UNRESOLVED` inside gates (regression-locks the
  `{bachelors_degree_credential}` ambiguity finding).
- `NO_CAPABILITY_COVERAGE -> UNRESOLVED`.
- `NONE_TRAP -> BLOCKED_BY_MATCHING_POLICY`.
- Missing/unrecognized `evaluation_path -> UNRESOLVED` (fail-closed
  default).
- A test proving partial semantic recognition cannot produce gate `FALSE`
  (the compound-requirement counterexample class from §5 of the
  predecessor audit).
- Static employer-gate invariant: gate record byte-identical before and
  after a simulated Claim-approval state change; only recomputed leaf/gate
  *results* differ.
- CASE_D real branch structure (all four branches, full matrix).
- CASE_E gate/application-question separation (a `SUPPORTED` gate must never
  answer CASE_E's own fixed-3-year question `YES`).
- Missing Requirement-ID reference in a gate fails closed
  (`QUALIFICATION_GATE_UNKNOWN_REQUIREMENT_ID`).
- Raw-source traceability fails closed, exactly per the deterministic
  whitespace-normalized-substring rule in §3 (both a passing case and a
  failing case — an excerpt absent from `jd.txt` -> gate invalid, not
  authored).
- **Gate-referenced row output suppression (load-bearing, explicit output
  test, not merely `job_decision.py` skip-logic)**: when a gate resolves
  `SUPPORTED`, prove (a) every `Requirement` referenced by that gate is
  **not** independently emitted in `qualification_gaps`, (b) not
  independently emitted in `qualification_unknowns`, (c) the gate's failed
  alternative branches create no user-facing gap noise at all, and (d)
  unrelated, ungrouped `Requirement` outputs on the same job are unchanged.
  This must assert on `analyze_job()`'s actual output structures, not only
  on `job_decision.py`'s internal blocker-loop skip.
- **Independent multiple-gate aggregation** (synthetic unit test): two
  independent `qualification_gate` records on one synthetic job, one
  `SUPPORTED` and one `BLOCKED_BY_MATCHING_POLICY`/`UNRESOLVED` —  prove
  satisfaction of the first never suppresses or erases the second's own
  independent result and output.
- **CASE_E Application Gate separation via synthetic/mock state**: prove,
  using a synthetic/mock `ApplicationQuestion`/answer record (not requiring
  real CASE_E Application Gate capture), that a `SUPPORTED` qualification
  gate result does not populate, mutate, or auto-answer
  `application_question_answer`.
- Gate `SUPPORTED` suppresses irrelevant failed-alternative gaps.
- Full existing regression/golden suite: zero drift on all currently-passing
  fixtures.

## Rollback / Reversal

Delete the new schema, the new qualification-gate module, the additive
`evaluation_path` population code in `requirement_match.py`,
`experience_range.py`, and `domain_qualified_duration.py`, the additive
routing/wiring in `job_analysis.py`, the additive
`qualification_gates[]` handling in `requirement_normalize.py`, and the one
additive skip-check in `job_decision.py`. No existing data depends on any
of it — `Requirement` rows, `application_logic.py`, and every currently-
passing fixture are untouched by this design and require no reversal of
their own.

## Non-Goals

No candidate-truth fabrication. No immigration/work-authorization inference.
No Claim approval. No candidate-year calculation. No certification-branch
arithmetic invention (the employer source does not state it; it is recorded
via `unmodeled_branches_note`, not invented). No generalized rule engine. No
package-generation implementation. No broad matcher rewrite. No global
NONE-vs-UNKNOWN rewrite (remains separate, open, tracked in
`CURRENT_STATE.md`). No change to Application Gate semantics. Explicitly
deferred, not bundled into this milestone: Associate's-degree and Master's-
degree base-credential capability-pattern coverage (both currently produce
empty `req_caps`, so those branch legs will resolve `UNRESOLVED` under this
design even once employer/candidate facts are otherwise settled);
technology-qualified-duration semantics (a separate, already-identified,
still-open matcher gap); span-level semantic-coverage analysis; real
Application Gate capture for either MBTA role; résumé/package-generation
glue.
