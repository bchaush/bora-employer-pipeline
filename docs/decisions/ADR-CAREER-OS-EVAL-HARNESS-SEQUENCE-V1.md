# ADR — Career OS Eval & Harness Sequence v1

Status: **ACCEPTED ROADMAP / PHASE B (`CAREER_OS_EVAL_AND_HARNESS_AUDIT_V1`) COMPLETED_BY_OPERATOR AND BORA_ACCEPTED / PHASE C (`CAREER_OS_TRACE_AND_FAILURE_CORPUS_INVENTORY_V1`) COMPLETED_BY_OPERATOR AND BORA_ACCEPTED — READ_ONLY / GOVERNANCE-ONLY `CAREER_OS_AGENT_CONTEXT_AND_USAGE_EFFICIENCY_V1` POLICY MILESTONE COMPLETED_BY_OPERATOR AND BORA_ACCEPTED (2026-09-11) / GOVERNING — PHASE D (`CAREER_OS_FAILURE_TAXONOMY_AND_EVALUATOR_COVERAGE_MAP_V1`) COMPLETED_BY_OPERATOR / BORA_ACCEPTED (2026-09-11) (READ_ONLY / DESIGN_ONLY), now PRIOR PHASE — PHASE E (`CAREER_OS_SYSTEM_EVAL_SET_ARCHITECTURE_V1`) BORA_AUTHORIZED / SELECTED / NOT_YET_COMPLETED / READ_ONLY_DESIGN_ONLY — PHASE F AND EVERY LATER ROADMAP PHASE REMAIN PROPOSED_NOT_AUTHORIZED**
Date: 2026-09-10 (Phase B acceptance and Phase C authorization recorded 2026-09-11; Phase C operator completion and Bora acceptance recorded 2026-09-11; `CAREER_OS_AGENT_CONTEXT_AND_USAGE_EFFICIENCY_V1` policy milestone authorized and operator-completed 2026-09-11; Bora accepted this policy milestone as GOVERNING on 2026-09-11; Bora authorized Phase D (`CAREER_OS_FAILURE_TAXONOMY_AND_EVALUATOR_COVERAGE_MAP_V1`), READ_ONLY / DESIGN_ONLY, on 2026-09-11; Phase D substantive read-only/design-only work operator-completed 2026-09-11; Bora explicitly accepted the Phase D checkpoint/report on 2026-09-11, stating "I am satisfied."; Bora explicitly authorized Phase E (`CAREER_OS_SYSTEM_EVAL_SET_ARCHITECTURE_V1`), READ_ONLY / DESIGN_ONLY, on 2026-09-12, stating "I authorize Phase E - System Eval-Set Architecture - as the next bounded READ_ONLY / DESIGN_ONLY phase. No implementation is authorized.")
Owner: Bora + ChatGPT architecture/adjudication layer

## 1. Purpose

Career OS has completed a successful manual reliability-testing phase across genuine survivor, no-survivor, stale/dead-route, missing-artifact, duplicate-opportunity, application-history, package-QA, and human-submission boundaries.

Before adding automation or widening autonomy, the system must audit its own engineering discipline and establish a durable eval/harness architecture. The goal is not more agents. The goal is a system that can state what it knows, what it cannot prove, why a consequential decision occurred, and which deterministic or human gate authorized the next transition.

This ADR locks the sequence and operating method only. It does **not** authorize product automation, a trace database, new agent infrastructure, LLM judges, provider routing, auto-apply, or any other implementation.

## 2. External reference basis

The audit must explicitly use current primary/public materials from IndyDevDan, Hamel Husain, and Cole Medin as reference frameworks, while distinguishing their published guidance from Career OS-specific adaptation.

No statement becomes Career OS doctrine merely because one of these practitioners recommends it. Each adoption still requires evidence that it fits Career OS's observed failure modes, consequences, or workload.

### IndyDevDan reference frame

Use his public harness/software-factory work for the principle that deterministic code should own sequencing, retries, acceptance, and phase boundaries; agents should operate inside bounded phases; structured/typed envelopes should cross seams; observable traces should make failures localizable; and objective checks should be code rather than model rediscovery.

Career OS adaptation: the future controller should own state transitions and deterministic gates. Reasoning agents may propose or interpret, but cannot self-certify success or bypass deterministic truth boundaries.

### Hamel Husain reference frame

Use his public AI-evals material for trace-first error analysis, human open/axial coding, failure-taxonomy construction, code-based evaluators for objective failures, calibrated LLM judges only for genuinely subjective failures, end-to-end task-success evaluation before step diagnostics, complete human-handoff traces, and the distinction between CI regression evals and production/real-run monitoring.

Career OS adaptation: real Career OS runs and reproduced failures are the primary eval material. Numeric sample-size guidance is guidance, not permission to fabricate traces or delay obvious deterministic protections.

### Cole Medin reference frame

Use his public Agentic Engineering materials for the AI-layer concept, Plan → Implement → Validate separation, validation-depth layering, commandifying repeated workflows, reducing assumptions before implementation, context isolation/reset between phases, Git history as durable memory, and system evolution after every meaningful bug.

Career OS adaptation: repeated operating instructions should become versioned workflows only after their contracts and evals are understood. Context must cross phases through durable artifacts rather than hidden conversational memory.

## 3. Permanent role separation

**ChatGPT — architect / semantic adjudicator / initiator.** Recover canonical state, research primary sources, define the bounded problem, decide whether a milestone is earned, design the architecture/acceptance criteria, adjudicate findings, and sequence the work. ChatGPT must not treat its own prior chat output as canonical state.

**Claude Code — bounded implementation builder.** Implement only an explicitly authorized milestone against the accepted plan/contract. No silent scope expansion, doctrine invention, or self-approval. If implementation discovers a contradiction or a necessary surface outside authorization, stop and return it for architectural adjudication.

**Cursor — independent adversarial reviewer.** Review the consequential diff and its tests independently from the builder. Challenge scope, truth boundaries, causal coverage, fail-closed behavior, and regression risk. Cursor is not a rubber stamp and must not repair its own findings unless a separately authorized builder pass is requested.

**Deterministic assurance — mechanical gate.** Schemas, tests, golden cases, static checks, hashes, exact-state checks, and CI decide objective invariants. Model agreement never substitutes for these gates.

**Bora — consequential human authority.** Final authority for Candidate Truth corrections, ambiguous personal facts, pursuit/submission/legal attestations, acceptance of major architecture direction, and final merge/release decisions.

## 4. Locked operating sequence

The phases below are sequential. A later phase is not authorized merely because it is named here.

### Phase A — Freeze and recover

Treat the current tested Career OS behavior as the candidate operating baseline. No convenience automation or architectural rewrite is added during the audit. Every new session independently verifies live canonical `main` and recovers doctrine from the repository before using prior-chat context.

### Phase B — `CAREER_OS_EVAL_AND_HARNESS_AUDIT_V1` (READ-ONLY)

Inventory the real system end to end against the three reference frameworks. Identify what is already deterministic, what is model-mediated, what is human-mediated, where state lives, what can mutate real-world state, what current tests/evals cover, and where observability/contract/assurance gaps actually exist.

### Phase C — `CAREER_OS_TRACE_AND_FAILURE_CORPUS_INVENTORY_V1` — Real trace and failure inventory

Use genuine Career OS operating runs, package attempts, rejected/suppressed cases, and confirmed defects as the primary corpus. Preserve the full journey through human handoff where relevant. Bora/ChatGPT perform the first qualitative review and open coding before delegating clustering or summaries to an LLM.

Do not fabricate a target sample count. If the genuine corpus is smaller than published heuristic targets, say so. Synthetic cases may supplement narrowly defined missing edge cases, but must be labeled synthetic and never presented as production evidence.

### Phase D — Failure taxonomy and evaluator coverage map

Create a Career OS-specific failure taxonomy from observed traces. For each material failure mode, record severity, first causal failure point, current detector/gate, evidence that the detector works, missing coverage, and whether the best evaluator is deterministic code, human review, or a potentially calibrated LLM judge.

Do not build an evaluator for every imaginable failure. Prioritize demonstrated consequential defects and high-value workload reduction.

### Phase E — System eval-set architecture

Design a repeatable system-level eval set using confirmed pass/fail operating cases. Preserve separate layers for end-to-end terminal-state correctness and step-level diagnostics. Real cases such as duplicate submissions, dead ATS pages, missing recency anchors, no-survivor batches, missing gold artifacts, role-preserving authentication, package-output failure, and clean survivor packages should be represented when source material is sufficient.

### Phase F — Trace/contract architecture

Only after the audit establishes the need, design `CAREER_OS_RUN_TRACE_V1` and phase contracts/typed envelopes. The trace should make canonical SHA, inputs, sources attempted, unavailable sources, state transitions, suppression reasons, model/tool provenance where relevant, human handoffs, artifact hashes, QA outcomes, and terminal state reconstructable without reading a chat transcript.

Architecture first. No database, UI, or vendor is preselected.

### Phase G — Assurance architecture

Review the existing assurance runtime and split fast/slow checks only if evidence shows the current loop is too slow or unreliable for frequent use. Preserve one authoritative full-suite path. A faster tier must never silently become a weaker substitute for required full assurance.

### Phase H — Bounded implementation milestones

Only after Phases B–G produce accepted architecture may implementation begin. Each milestone uses the locked role sequence:

1. ChatGPT recovers canonical state, researches/adjudicates, and writes a bounded implementation contract with acceptance criteria.
2. Bora approves the consequential direction when required.
3. Claude Code implements only that contract on a bounded branch/worktree.
4. Deterministic checks run.
5. Cursor independently reviews the exact consequential diff and causal tests.
6. Findings return to ChatGPT for adjudication; required corrections return to Claude as a new bounded builder pass.
7. Required CI/assurance passes on the reviewed state.
8. Bora performs final merge/release approval.

### Phase I — Automation after proof

Automate orchestration only after traceability, contracts, evaluator coverage, and fail-closed boundaries are proven. Deterministic code should own sequencing, retries, acceptance, and state transitions wherever objective rules exist. Agents remain bounded reasoning components.

### Phase J — Additional agents/model routing only when earned

Do not add multi-agent roles, model routers, provider abstractions, autonomous self-correction, or LLM judges because they are fashionable. Introduce them only when trace/error evidence shows a concrete quality, reliability, latency, cost, or workload problem that the added mechanism measurably addresses.

## 5. Hard prohibitions during this roadmap

- No auto-submit or autonomous legal/work-authorization attestations.
- No LLM judge for an objective fact that deterministic code/evidence can decide.
- No synthetic trace represented as a genuine production run.
- No numeric reliability claim unsupported by an adequate labeled sample.
- No model/provider abstraction without a real consumer need.
- No generic agent framework adoption merely to appear agentic.
- No self-modifying canonical governance without human-reviewed repository changes.
- No replacing evidence provenance with model consensus.
- No allowing a builder to modify the mechanism that independently grades its work unless the milestone explicitly authorizes that evaluator change and it receives separate review.

## 6. New-chat recovery protocol

A fresh ChatGPT session must be able to resume without conversational memory. This is the single canonical recovery order — every other governance file (`AGENTS.md`, `CURRENT_MILESTONE.md`, `CURRENT_STATE.md`, `CURRENT_EXECUTION_CHECKPOINT.json`) must stay consistent with it rather than defining a competing order. Before any consequential work it must:

1. independently fetch/verify live canonical `main`;
2. read `project_state.json` (the mechanically-checked phase/authority pointer);
3. read `CURRENT_EXECUTION_CHECKPOINT.json` (the bounded progress-handoff detail for whatever phase `project_state.json` names — never a new strategic authority above `BLUEPRINT.md`/`project_state.json`);
4. read `AGENTS.md` and `BLUEPRINT.md`;
5. read this ADR and `CURRENT_MILESTONE.md`/`CURRENT_STATE.md` prose for historical context (informational only; verify against steps 2-3 rather than trusting prose alone);
6. verify live Git/GitHub state and whether a newer accepted ADR supersedes this one;
7. state the current recovered phase/status and exactly one next allowed action before beginning any work;
8. use prior chat context only after canonical recovery and only when consistent with the repository.

Phase B (`CAREER_OS_EVAL_AND_HARNESS_AUDIT_V1`) is **COMPLETED_BY_OPERATOR** and **BORA_ACCEPTED** — see `CURRENT_EXECUTION_CHECKPOINT.json`. Phase C (`CAREER_OS_TRACE_AND_FAILURE_CORPUS_INVENTORY_V1`), in **READ_ONLY** mode, is **COMPLETED_BY_OPERATOR** and **BORA_ACCEPTED** — see `docs/audits/CAREER_OS_TRACE_AND_FAILURE_CORPUS_INVENTORY_V1_REPORT.md`. The governance-only `CAREER_OS_AGENT_CONTEXT_AND_USAGE_EFFICIENCY_V1` policy milestone, authorized by Bora before Phase D, remains **COMPLETED_BY_OPERATOR** and **BORA_ACCEPTED (2026-09-11)** / **GOVERNING** — see `docs/decisions/ADR-CAREER-OS-AGENT-CONTEXT-USAGE-EFFICIENCY-V1.md`. Bora explicitly authorized Phase D (`CAREER_OS_FAILURE_TAXONOMY_AND_EVALUATOR_COVERAGE_MAP_V1`), in **READ_ONLY / DESIGN_ONLY** mode, on 2026-09-11; Phase D substantive read-only/design-only work is **COMPLETED_BY_OPERATOR / BORA_ACCEPTED (2026-09-11)** — see `docs/audits/CAREER_OS_FAILURE_TAXONOMY_AND_EVALUATOR_COVERAGE_MAP_V1_REPORT.md`. Bora explicitly accepted the Phase D checkpoint, stating "I am satisfied." Phase D is now **PRIOR_PHASE**. Bora explicitly authorized Phase E (`CAREER_OS_SYSTEM_EVAL_SET_ARCHITECTURE_V1`), in **READ_ONLY / DESIGN_ONLY** mode, on 2026-09-12, stating "I authorize Phase E - System Eval-Set Architecture - as the next bounded READ_ONLY / DESIGN_ONLY phase. No implementation is authorized." Phase E is now **BORA_AUTHORIZED / SELECTED / NOT_YET_COMPLETED / READ_ONLY_DESIGN_ONLY**. `implementation_authorized` remains false. Phase F and every later roadmap phase remain **PROPOSED_NOT_AUTHORIZED**. A new chat must not jump directly to trace infrastructure, orchestration automation, a database, multi-agent implementation, or Phase F merely because Phase E has been authorized — Bora must separately authorize each later phase before it or any implementation is authorized.

## 7. Audit deliverables required before implementation

The read-only audit must produce, at minimum:

- current-system phase/control-flow map;
- deterministic-vs-agent-vs-human responsibility map;
- observed real-run corpus inventory and provenance quality;
- first-pass Career OS failure taxonomy grounded in observed traces;
- existing evaluator/test/CI coverage map;
- uncovered consequential failure modes;
- subjective-quality surfaces that may eventually require human-labelled evaluation;
- observability/trace gaps;
- assurance-runtime bottlenecks and evidence of materiality;
- recommendations ranked by demonstrated risk/workload value;
- explicit non-recommendations for fashionable but unjustified infrastructure;
- a proposed architecture milestone only if the audit evidence earns one.

The audit itself must not change production semantics, schemas, Candidate Truth, Employer Truth, Match Truth, application history, package generation, or submission behavior.

## 8. Source honesty / citation rule

External references must be cited to primary/public material when reasonably available. The audit must label claims as one of:

- **SOURCE-DIRECT** — explicitly supported by the cited practitioner material;
- **CAREER-OS-ADAPTATION** — our reasoned adaptation of that material to this repository;
- **OBSERVED-REPO-FACT** — established by direct inspection/test of Career OS;
- **OPEN-HYPOTHESIS** — plausible but not yet proven and therefore not implementation authority.

If a source cannot be verified or guidance conflicts across sources, preserve the uncertainty rather than harmonizing it silently.

## 9. Reference materials reviewed for this lock

Primary/public reference starting points used for this roadmap:

- IndyDevDan / `disler/fusion-harness`: validator-defined acceptance gate before builder work, baseline red→green behavior, bounded builder/validator roles, and validation-loop artifacts.
- IndyDevDan / `disler/super-simple-software-factory`: deterministic Python control plane, bounded agents, typed envelopes, phase traces, objective code phases, protected grader machinery, and explicit acceptance semantics.
- Hamel Husain + Shreya Shankar / AI Evals FAQ: error analysis from representative traces; open/axial coding; objective code evaluators; human-labelled validation for LLM judges; end-to-end task success before step diagnostics; human-handoff tracing; and caution against speculative eval-driven development without observed errors.
- Cole Medin / `coleam00/ai-transformation-workshop`: AI layer, Plan→Implement→Validate loop, validation pyramid, commandify repeated work, reduce assumptions, context isolation, Git history as memory, and system evolution after bugs.

These references are anchors for the audit, not frozen third-party dependencies. The audit should refresh primary sources when materially relevant because practitioner guidance can evolve.

## 10. Decision

**LOCKED SEQUENCE:** audit → real-trace/error inventory → failure taxonomy/evaluator map → eval-set architecture → trace/contract architecture → assurance architecture → bounded implementation → automation → optional agent/model specialization.

**CURRENT STATUS:** Phase B (`CAREER_OS_EVAL_AND_HARNESS_AUDIT_V1`, read-only) is **COMPLETED_BY_OPERATOR / BORA_ACCEPTED** — see `CURRENT_EXECUTION_CHECKPOINT.json` for the machine-readable handoff and `docs/audits/CAREER_OS_EVAL_AND_HARNESS_AUDIT_V1_REPORT.md` for the operator audit report, both reflecting Bora's acceptance. Phase C (`CAREER_OS_TRACE_AND_FAILURE_CORPUS_INVENTORY_V1`), in **READ_ONLY** mode, is **COMPLETED_BY_OPERATOR / BORA_ACCEPTED** — see `docs/audits/CAREER_OS_TRACE_AND_FAILURE_CORPUS_INVENTORY_V1_REPORT.md`. Bora separately authorized the governance-only `CAREER_OS_AGENT_CONTEXT_AND_USAGE_EFFICIENCY_V1` policy milestone before Phase D; that milestone remains **COMPLETED_BY_OPERATOR / BORA_ACCEPTED (2026-09-11) / GOVERNANCE_ONLY / GOVERNING** — see `docs/decisions/ADR-CAREER-OS-AGENT-CONTEXT-USAGE-EFFICIENCY-V1.md`. Bora subsequently, explicitly authorized Phase D (`CAREER_OS_FAILURE_TAXONOMY_AND_EVALUATOR_COVERAGE_MAP_V1`) as the next phase, in **READ_ONLY / DESIGN_ONLY** mode, on 2026-09-11; Phase D substantive read-only/design-only work remains **COMPLETED_BY_OPERATOR / BORA_ACCEPTED (2026-09-11) / READ_ONLY_DESIGN_ONLY** — see `CURRENT_EXECUTION_CHECKPOINT.json`, `milestone_contracts/audit/career-os-failure-taxonomy-evaluator-coverage-map-v1.json`, and `docs/audits/CAREER_OS_FAILURE_TAXONOMY_AND_EVALUATOR_COVERAGE_MAP_V1_REPORT.md`, now recorded as **PRIOR_PHASE**. Bora's acceptance of the already-merged Phase D checkpoint/report ("I am satisfied.") did not itself authorize Phase E or any later phase. Bora has since, separately and explicitly, authorized Phase E (`CAREER_OS_SYSTEM_EVAL_SET_ARCHITECTURE_V1`) as the next phase, in **READ_ONLY / DESIGN_ONLY** mode, on 2026-09-12, stating: "I authorize Phase E - System Eval-Set Architecture - as the next bounded READ_ONLY / DESIGN_ONLY phase. No implementation is authorized." Phase E is now **BORA_AUTHORIZED / SELECTED / NOT_YET_COMPLETED / READ_ONLY_DESIGN_ONLY** — see `CURRENT_EXECUTION_CHECKPOINT.json` and `milestone_contracts/governance/career-os-phase-e-authorization-v1.json`. This authorization does not itself perform any substantive Phase E work, and `implementation_authorized` remains false.

The intervening governance-only `CAREER_OS_AGENT_CONTEXT_AND_USAGE_EFFICIENCY_V1` policy milestone is not itself a roadmap phase and is not a violation of this sequence -- Bora explicitly authorized it as a governance step before Phase D and has since accepted it as governing. Phase D substantive work remains COMPLETED_BY_OPERATOR / BORA_ACCEPTED (2026-09-11) / READ_ONLY_DESIGN_ONLY, now prior_phase. Phase E (`CAREER_OS_SYSTEM_EVAL_SET_ARCHITECTURE_V1`) is BORA_AUTHORIZED / SELECTED / NOT_YET_COMPLETED, in READ_ONLY / DESIGN_ONLY mode. Phase F and every later roadmap phase (Phase F through Phase J) remain **PROPOSED_NOT_AUTHORIZED**, and no product/runtime implementation is authorized, until a next phase is separately authorized by Bora.
## 11. Reference URLs at lock time

- https://github.com/disler/fusion-harness
- https://github.com/disler/super-simple-software-factory
- https://hamel.dev/blog/posts/evals-faq/
- https://github.com/coleam00/ai-transformation-workshop

## 12. Fresh-session checkpoint protocol

`CURRENT_EXECUTION_CHECKPOINT.json` is the canonical machine-readable handoff for bounded phase progress within whatever phase `project_state.json`/`BLUEPRINT.md` currently authorize — it is subordinate to both and is never a new strategic authority. It exists to prevent fresh chats from re-running completed work or inferring authority from prose. A checkpoint must separate operator completion, Bora acceptance, and next-phase authorization; none implies either of the others. It must record exact completed actions, unresolved/not-authorized work, the proposed next phase if any, and exactly one next allowed action.

Fresh sessions recover in the exact order fixed by "Section 6. New-chat recovery protocol" above — do not restate a different order here. When a meaningful bounded session changes canonical progress, continuity is not considered locked until the checkpoint and state pointers are updated consistently and merged to `main`. Git history preserves prior checkpoint versions, so the current checkpoint stays small rather than becoming a second narrative log.
