# ADR — Pursuit Approval Boundary v1

Status: **PROPOSED_FOR_IMPLEMENTATION_REVIEW**
Date: 2026-09-02
Approved by: Bora / ChatGPT Work (architecture-only decision; independent Cursor adversarial review: ACCEPT_ADR_DRAFT)

**ARCHITECTURE ONLY. This ADR authorizes no implementation** (see
Non-Goals). It exists to prevent a future transition-contract defect, not
to describe or fix a present one.

## Context

`PURSUIT_APPROVAL_BOUNDARY_ARCHITECTURE_AUDIT_V1` (read-only) determined
that no existing persisted field or record currently means "Bora
explicitly chose to pursue this specific opportunity," and adjudicated
`ARCHITECTURE_CONTRACT_JUSTIFIED_IMPLEMENTATION_DEFERRED`: a genuine
semantic boundary is missing from the repository's current architecture,
but no current production consumer creates a consequential defect from
that gap today, because the downstream actions that would need
pursuit-gating (résumé/package generation for pursuit, application-route
preparation, networking execution, submission) are not yet implemented.

Directly confirmed by that audit and independently re-confirmed while
drafting this ADR:

- `Job.decision` (`schemas/job.schema.json`, enum `PRIORITY_APPLY | APPLY
  | EFFICIENT_APPLY | WATCH | REJECT | UNDECIDED`) and `Job.lane` (enum
  `LANE_0_REJECT | LANE_1_EFFICIENT_APPLY | LANE_2_PRIORITY_APPLY | WATCH
  | UNASSIGNED`) are produced entirely by `src/job_decision.py`'s
  deterministic `decide_lane_and_decision()` — system-derived, no human
  input, regenerated identically on every `analyze_job()` re-run.
- `Job.application_status` (enum `NOT_STARTED | PREPARING |
  READY_FOR_REVIEW | SUBMITTED | INTERVIEWING | REJECTED | WITHDRAWN |
  OFFER | CLOSED | UNKNOWN`), `Job.resume_version` ("Identifier of the
  derivative resume version associated with the job. Null before
  generation."), and `Job.network_action` ("Reference to the approved
  networking action or recommendation. Null when none exists.") all exist
  in schema but have **no writer anywhere in `src/`** — confirmed by the
  preceding audit's repository-wide search and independently re-verified.
- `ApplicationAttempt.attempt_status`
  (`schemas/application_attempt.schema.json`) is route-scoped, not
  opportunity-scoped; the schema exists, but no current production
  constructor, persistence, or consumer path for `ApplicationAttempt`
  exists anywhere in `src/`.
- `Job.application_status`: no current `src/` reader or writer found.
- `Job.resume_version`: no current `src/` reader or writer found.
- `Job.network_action`: no current `src/` reader or writer found.
- `Job.lane`: system-derived (`src/job_decision.py`); currently read by
  `src/application_gate.py::gate_1_5_applicable()` only as a Gate-1.5
  compute-skip guard in the relevant downstream application-gate path
  (deciding whether to evaluate Application Gate questions at all, never
  as authorization for consequential work).
- `Job.decision` / `Job.lane`: produced and used within current
  analysis/routing behavior, including posting-state routing
  (`src/job_decision.py::apply_posting_state_routing()`, called from
  `src/job_analysis.py`) where applicable — routing/downgrade logic
  strictly internal to the system-recommendation computation itself, not
  a consumer that treats the recommendation as human authorization.

**None of these current uses constitutes or establishes Bora's human
pursuit authorization** — this list is a precise, independently-verified
inventory of what exists today, not a claim that no field has any
consumer.

This ADR drafts the minimum durable architectural contract separating
**system recommendation** from **Bora's human decision to pursue an
opportunity**, before any future downstream package/application workflow
is implemented — so that workflow, whenever it is separately authorized
and built, has an unambiguous boundary to build against rather than
inheriting an implicit, undocumented assumption.

## Decision

Lock the following conceptual/semantic architecture. No schema, enum,
state machine, storage representation, or production code is authorized
by this ADR (see Non-Goals) — every locked item below is a **semantic
requirement a future implementation must satisfy**, not a design of that
implementation.

### 1. System recommendation is not human authorization

`Job.decision` and `Job.lane` are system-derived analytical/recommendation
outputs. They do not, by themselves, constitute Bora's decision to pursue
an opportunity, and must never silently authorize consequential downstream
pursuit work — including, whenever these capabilities eventually exist:
job-specific résumé/package generation intended for pursuit, application
preparation, application-route initiation, external networking execution,
submission, or any other consequential pursuit action. No implementation
API for any of these is defined here.

**Read-only / decision-support safe harbor**: pursuit authorization is
NOT required merely to perform read-only, analytical activity intended to
inform Bora's pursuit decision itself — non-exhaustively: `analyze_job`/
re-analysis; employer/source verification; evidence gathering;
qualification analysis; posting-state verification; and exploratory
application-route inspection used to discover material application
conditions (see §4's exploratory-inspection invariant). This safe harbor
applies only when the activity is genuinely (a) read-only or analytical,
(b) intended to inform the pursuit decision, and (c) not itself materially
advancing an authorized application/pursuit workflow — it does not weaken
the human-authorization requirement for any consequential pursuit work
listed above, and it is not a complete action taxonomy or a future API
definition.

### 2. Human pursuit authorization is a distinct truth axis

Bora's opportunity-level human decision must remain a distinct axis from:
Employer truth; Candidate truth; Match truth; `Job.decision`; `Job.lane`;
posting/actionability truth; `Job.application_status`; `Job.network_action`;
`ApplicationAttempt`; Application Gate; résumé/package truth; submission
authorization; outcome truth. No concrete schema is defined for this axis
in this ADR.

**`Job.network_action` clarification**: a non-null `Job.network_action`
— including wording suggesting an "approved networking action" (per its
current schema description) — does not establish or substitute for
Bora's opportunity-level pursuit authorization. The inverse also holds:
pursuit authorization does not itself authorize execution of an external
networking action. This ADR does not redesign `Job.network_action`,
change its schema, or define networking workflow.

### 3. Opportunity-level scope

Pursuit authorization conceptually applies to the Job/opportunity, not to
one particular `ApplicationAttempt`. One pursued opportunity may later
have multiple application routes (e.g. direct application plus a referral
route); `ApplicationAttempt` remains route-scoped operational truth,
unaffected by this ADR.

### 4. Downstream authorization boundary (conceptual ordering only)

```
analyze_job / system recommendation
-> explicit Bora pursuit decision
-> authorized downstream pursuit preparation
-> application-route inspection / Application Gate as applicable
-> artifact/answer review
-> separate human submission authorization
-> immutable submission/history/tracking
-> follow-up
-> outcome learning
```

None of the stages after "system recommendation" is implemented by this
ADR. Résumé/package generation is recorded as the **first EXPECTED**
future consumer under the current product direction (§7) — this ordering
does not lock `generate_resume()` as the only possible first consumer;
a different concrete downstream operation could earn that position instead
if evidence at implementation time shows otherwise.

**Exploratory inspection invariant**: this ordering must not be read as
requiring pursuit approval before every application-route inspection.
Exploratory or read-only application-route inspection performed solely to
inform Bora's pursuit decision — e.g. inspecting an application route to
discover required questions, exploratory `ApplicationAttempt` activity, or
evaluating application-form structure strictly for decision support — is
not itself downstream pursuit preparation and does not require prior
pursuit authorization. This narrow carve-out does not change any other
invariant in this ADR: exploratory activity does not equal pursuit
authorization; exploratory activity does not equal application readiness;
exploratory answers gathered this way do not become submitted truth;
consequential downstream pursuit work (résumé/package generation for
pursuit, application preparation, application-route initiation, external
networking execution, submission) still requires the separate human
authorization boundary once a future consumer implements it; and
submission remains separately human-controlled regardless. This ADR
authorizes no new exploratory tooling or `ApplicationAttempt`
implementation — the carve-out is architecture semantics only.

### 5. `Job.application_status` is not pursuit authorization

`Job.application_status` is operational/lifecycle state. Values such as
`PREPARING` or `READY_FOR_REVIEW` do not establish, prove, or substitute
for Bora's pursuit decision — a future consumer must not read a non-
`NOT_STARTED` `application_status` as evidence that pursuit was approved,
and must not derive `application_status` from `Job.decision`/`lane` alone.
This ADR does not modify, deprecate, or redesign the field.

### 6. `ApplicationAttempt` is not pursuit authorization

`ApplicationAttempt` is application-route scoped. Its `attempt_status` and
`capture_status` must not establish or substitute for opportunity-level
human pursuit authorization — an `EXPLORATORY` or `IN_PROGRESS` attempt
existing for a job says nothing about whether Bora has actually decided to
pursue that opportunity, and a future pursuit-authorization consumer must
not infer approval merely from an attempt's existence.

### 7. Stale human intent / material truth change

Future pursuit authorization must not silently remain valid across a
materially changed opportunity merely because `Job_ID` remains the same.
A future implementation must bind authorization strongly enough to
relevant opportunity/analysis identity or freshness state that materially
changed source truth (e.g. a re-run `analyze_job()` producing a
substantially different match/decision picture, or a posting-state change)
cannot silently inherit stale human intent from an earlier, different
analysis of the same `Job_ID`. This ADR does **not** choose digest fields,
a version-number format, timestamps, an invalidation algorithm, a
revocation state machine, or a storage representation — those remain
implementation-design questions for a future, separately authorized
consumer milestone.

### 8. Negative semantics

Human pursuit authorization does **not** mean: the Candidate satisfies
every qualification; Match truth changed; the employer posting remains
live forever; posting-state truth changed; immigration/work authorization
has been legally cleared; Application Gate is complete; an application
route is complete; résumé/package content has been generated;
résumé/package content is truthful or validated; application answers are
approved; submission is authorized; the application was submitted; or the
employer outcome is known. Every one of these truth surfaces remains
separate, and pursuit authorization must never be treated as a proxy for
any of them. (`BLUEPRINT.md` §132's five-layer truth model already names
Pursuit truth (layer 4) — realistic hiring probability, hiring speed,
work-authorization practicality, income, location/work mode, evidence
strength, U.S. credibility, learning/network value, longer-term direction,
and opportunity cost — and Package truth (layer 5, "for a role Bora has
decided to pursue") as distinct layers. Blueprint Pursuit truth is
**broader** than the single human-authorization concept governed by this
ADR: this ADR defines only the human-authorization boundary/slice within
that broader Pursuit truth layer — the explicit record that Bora made a
pursuit decision — and does not attempt to define, redefine, or enumerate
all the factors listed above that determine whether an opportunity is
worth pursuing in the first place. This ADR does not introduce a new
truth layer; it specifies one slice of an already-named one.)

### 9. Human override preserves both truths

If system recommendation = `PRIORITY_APPLY` and Bora declines pursuit,
both facts remain representable. If system recommendation = `WATCH` (or
any lower recommendation) and Bora chooses to pursue anyway, both facts
remain representable. Human choice must never rewrite system analytical
truth (`Job.decision`/`Job.lane`) merely to make records look consistent,
and system recommendation must never overwrite human intent either. These
are two independent, co-existing facts, not one field that wins over the
other.

### 10. Future human-override learning (possibility only)

Architecture may preserve the possibility of later recording why Bora
accepted or declined a system recommendation, for future strategy
learning. No reason vocabulary is authorized by this ADR. No
outcome-learning implementation is authorized. Consistent with
`BLUEPRINT.md` §115 (Milestone 5: "Use real application data to tune...
Do not tune truth constraints. Those remain fixed."), any future learning
may tune strategy only, never truth.

### 11. Submission remains separate

Pursuit authorization must never equal submission authorization. Final
external submission remains a separate, later, Bora-controlled
consequential action under the Blueprint's permanent no-auto-submit/
human-control rule (`BLUEPRINT.md` §86, "Gate 3 — Submit... External
submission stays human-controlled. This remains permanent V1
architecture.").

### 12. Implementation status

**ARCHITECTURE ONLY.** No authorization exists, from this ADR, for: a
pursuit schema; pursuit enums; a pursuit state machine; persistence or
storage of any kind; production code; validators; tests; package
generation; résumé generation implementation; an application-readiness
engine; networking execution; submission automation; tracking
implementation; follow-up implementation; or outcome-learning wiring.
Implementation remains deferred until a concrete downstream consumer
milestone is separately earned and authorized.

## Why

Smallest reliable choice given the confirmed facts: the boundary is a
genuine, repo-authority-confirmed gap (Blueprint Gates 1/2/3, §132's
five-layer truth model, and the assurance-baseline ADR's own future-
pipeline design record all already point at this boundary independently
and consistently), but nothing downstream exists yet to misuse it —
authoring a full schema/state-machine now would be speculative engineering
against requirements no concrete consumer has yet exercised, exactly the
kind of premature implementation the repository's own governance
(`CLAUDE.md`, `BLUEPRINT.md` §118 "propose smallest change") and prior
audits (`POST_QUALIFICATION_GATE_REAL_MARKET_BOTTLENECK_AUDIT_V1`) warn
against. Recording the semantic contract now, without implementation,
lets a future consumer milestone (most likely résumé/package generation)
inherit an unambiguous boundary instead of an implicit one, at zero
current implementation cost or risk.

## Alternatives Considered

- **Implement a concrete `pursuit_approval` schema/record now.** Rejected:
  no current consumer would read or write it; this would be exactly the
  "manufacture a present production defect fix / build ahead of a
  reproduced need" pattern this repository's governance and prior
  bottleneck audits explicitly reject. Deferred to a future, separately
  earned and authorized consumer milestone.
- **Treat `Job.decision`/`lane` as already sufficient (do nothing).**
  Rejected: the preceding read-only audit found these are purely
  system-derived and regenerate identically on every re-analysis; treating
  them as pursuit authorization would let a batch re-run of `analyze_job()`
  silently "re-approve" every job merely by reproducing the same
  recommendation, violating the central invariant that a system
  recommendation must never silently become human authorization.
- **Repurpose `Job.application_status` (`PREPARING`) as the pursuit
  signal.** Rejected: it is operational/lifecycle state with no current
  writer, and `PREPARING`/`READY_FOR_REVIEW` sit directly adjacent to
  `SUBMITTED` in its enum with nothing distinguishing "system queued this"
  from "Bora chose to pursue this" — using it for pursuit approval would
  create exactly the semantically dangerous conflation identified in the
  preceding audit's Job.application_status adjudication.
- **Repurpose `ApplicationAttempt.attempt_status`.** Rejected: it is
  route-scoped, not opportunity-scoped, and a job may have zero, one, or
  several attempts — an attempt's existence or status cannot represent a
  single opportunity-level human decision.
- **Lock `generate_resume(Job_ID)` as the mandatory, only possible first
  consumer.** Rejected per this turn's own instruction: record it only as
  the currently expected first consumer under product direction, not as a
  locked requirement, since no implementation has earned that conclusion
  yet.

## Risks / Tradeoffs

- Recording an architectural boundary without implementation carries the
  usual documentation-drift risk: a future implementer could still ignore
  this ADR and wire résumé generation directly off `Job.decision` without
  reading it. Mitigation is procedural (Cursor adversarial review at
  implementation time, and this ADR's own explicit negative-semantics
  list), not technical, since no code exists yet to enforce it.
- Because no digest/version/staleness mechanism is chosen here (§7), a
  future consumer milestone must do real design work before pursuit
  authorization can be safely implemented — this ADR intentionally defers
  that cost rather than guessing at a mechanism with no concrete
  consumer's actual freshness requirements to validate against.
- `Job.application_status`'s existing adjacency risk (§5) is not resolved
  by this ADR — it remains a real latent risk for whenever résumé-
  generation wiring is eventually built, tracked here but not fixed here.

## Affected Areas

This ADR is a **proposed architectural boundary only** — nothing is
implemented by it.

- New: this ADR file only.
- Not modified: `CURRENT_STATE.md`, `CURRENT_MILESTONE.md` (see
  Continuity note below — a separate architecture-recording step is
  required before/with any canonical commit of this ADR), any schema, any
  production code in `src/`, any test, any fixture, Candidate truth,
  Evidence, Claims, Experiences, Requirements, Match semantics, job-
  analysis behavior, job-decision behavior, posting-state behavior,
  immigration/work-authorization semantics, Application Gate, résumé/
  package behavior, networking, application tracking, submission,
  follow-up, or outcome learning.

## Verification Required

Not applicable in this architecture-only turn — no implementation exists
to verify. A future consumer milestone that implements pursuit
authorization must separately define and satisfy its own verification
requirements (schema validation, state-transition tests, staleness-
invalidation tests, etc.) at that time.

## Rollback / Reversal

Delete this ADR file. Nothing else references it yet (see Continuity note
below); no schema, code, test, or other document currently depends on it.

## Non-Goals

No pursuit schema. No pursuit enums. No pursuit state machine. No
persistence/storage design. No production code. No validators. No tests.
No package-generation implementation. No résumé-generation implementation.
No application-readiness engine. No networking execution. No submission
automation. No tracking implementation. No follow-up implementation. No
outcome-learning wiring. No change to Candidate truth, Evidence, Claims,
Experiences, Requirements, Match semantics, job-analysis behavior, job-
decision behavior, posting-state behavior, immigration/work-authorization
semantics, Application Gate, résumé/package behavior, networking,
application tracking, submission, follow-up, or outcome learning. No
digest field, version-number format, timestamp format, invalidation
algorithm, revocation state machine, or storage representation is chosen
(§7) — all deferred to a future, separately authorized consumer milestone.

## Continuity note (not authorized to act on in this turn)

This ADR must not become canonical/committed while remaining unreferenced
by the project's canonical continuity pointers (`CURRENT_STATE.md`,
`CURRENT_MILESTONE.md`) — per this repository's own canonical-continuity
protocol (recorded in the closed `REPRODUCIBLE_CONSEQUENTIAL_ASSURANCE_
BASELINE_V1` ADR §12), a future session must be able to recover this ADR's
existence and status from the repo's canonical pointers, not from
conversation memory alone. If Cursor later accepts this ADR, a separate
architecture-recording step must determine and perform the minimal
`CURRENT_STATE.md`/`CURRENT_MILESTONE.md` pointer update required before
or with the canonical commit of this ADR. That update is explicitly not
performed in this turn.
