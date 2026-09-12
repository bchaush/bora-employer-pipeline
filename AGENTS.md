# Bora Employer Pipeline OS — Agent Contract
This repository implements the Bora Employer Pipeline OS.

## Authority Order
If instructions conflict, enforce state using this order:
1. Bora's explicit current instruction
2. BLUEPRINT.md
3. Active `.cursor/rules/*.mdc` — operational enforcement of BLUEPRINT.md
4. Approved architecture decisions (docs/decisions/)
5. Schemas and deterministic validators
6. Model preference

A model's preferred approach never overrides a locked system rule or validation schema.

## Canonical Source
BLUEPRINT.md is the strategic, product, reliability, implementation, and coding source of truth.
- Do not redesign the system from scratch.
- Do not silently reinterpret a locked rule.
- Do not weaken reliability rules for speed.
- If a materially better approach is discovered: surface risks/tradeoffs and wait for explicit approval from Bora before modifying code.

## Locked AI / Tool Roles
- **ChatGPT Work**: primary architect, research, semantic adjudication, truth/calibration, priority selection, market/career/application guidance, reasoning, sequencing, and final decision guidance.
- **Claude Code**: primary bounded implementation agent.
- **Cursor**: mandatory independent adversarial reviewer of consequential uncommitted diffs before commit/push; not the default primary builder after governance sync.
- **Gemini**: optional non-coding strategic/directional second opinion only; not part of the coding execution or coding-review loop.
- No runtime workflow may depend on multi-model agreement. Deterministic validators enforce invariants. Evidence wins over model opinion. Bora retains consequential approval.

## Execution Checkpoint / Fresh-Chat Handoff
Recovery order: independently verify live canonical `main`; read `project_state.json`; then read `CURRENT_EXECUTION_CHECKPOINT.json` before beginning any phase work (full order fixed in `docs/decisions/ADR-CAREER-OS-EVAL-HARNESS-SEQUENCE-V1.md` Section 6 — do not restate a different order elsewhere). The checkpoint records operator-completed work, Bora acceptance status, unresolved/not-authorized work, and exactly one next allowed action. It is a bounded progress-handoff record only: it never outranks `BLUEPRINT.md`, the Authority Order above, or `project_state.json`, and never independently authorizes a new phase. Operator completion never grants human acceptance and a proposed next phase is never authorized merely because it is named. Before ending a meaningful bounded work session that changes canonical progress, update the checkpoint and the mechanically authoritative state pointers consistently; do not claim continuity is locked until that state is merged to canonical `main`.

## Eval / Harness Roadmap Recovery
Before any Career OS eval, harness, orchestration, or automation work, follow the canonical recovery order fixed in `docs/decisions/ADR-CAREER-OS-EVAL-HARNESS-SEQUENCE-V1.md` Section 6 (`main` -> `project_state.json` -> `CURRENT_EXECUTION_CHECKPOINT.json` -> `AGENTS.md`/`BLUEPRINT.md` -> this ADR/`CURRENT_MILESTONE.md`/`CURRENT_STATE.md`) — do not restate a different or partial order here. Phase B (`CAREER_OS_EVAL_AND_HARNESS_AUDIT_V1`) is COMPLETED_BY_OPERATOR and BORA_ACCEPTED; Phase C (`CAREER_OS_TRACE_AND_FAILURE_CORPUS_INVENTORY_V1`), READ_ONLY, is COMPLETED_BY_OPERATOR and BORA_ACCEPTED — see `docs/audits/CAREER_OS_TRACE_AND_FAILURE_CORPUS_INVENTORY_V1_REPORT.md` and `CURRENT_EXECUTION_CHECKPOINT.json`. The governance-only `CAREER_OS_AGENT_CONTEXT_AND_USAGE_EFFICIENCY_V1` policy milestone is COMPLETED_BY_OPERATOR / BORA_ACCEPTED (2026-09-11) / GOVERNING — see `docs/decisions/ADR-CAREER-OS-AGENT-CONTEXT-USAGE-EFFICIENCY-V1.md`. Phase D (`CAREER_OS_FAILURE_TAXONOMY_AND_EVALUATOR_COVERAGE_MAP_V1`) substantive read-only/design-only work remains COMPLETED_BY_OPERATOR / BORA_ACCEPTED (2026-09-11) / READ_ONLY_DESIGN_ONLY, now recorded as prior_phase — see `docs/audits/CAREER_OS_FAILURE_TAXONOMY_AND_EVALUATOR_COVERAGE_MAP_V1_REPORT.md` and `CURRENT_EXECUTION_CHECKPOINT.json`. Bora explicitly authorized `CAREER_OS_SYSTEM_EVAL_SET_ARCHITECTURE_V1` (Phase E), in READ_ONLY / DESIGN_ONLY mode, on 2026-09-12, stating: "I authorize Phase E - System Eval-Set Architecture - as the next bounded READ_ONLY / DESIGN_ONLY phase. No implementation is authorized." Phase E is now BORA_AUTHORIZED / SELECTED / NOT_YET_COMPLETED / READ_ONLY_DESIGN_ONLY. `implementation_authorized` remains false. Phase F and every later roadmap phase remain PROPOSED_NOT_AUTHORIZED; do not jump directly to implementation, to trace infrastructure, or to Phase F merely because Phase E has been authorized — Bora must separately authorize each later phase, and no implementation is authorized until then. The locked execution roles are ChatGPT architect/adjudicator/initiator -> Claude Code bounded builder after explicit authorization -> deterministic checks -> Cursor independent adversarial review -> CI -> Bora final merge/release authority.

## Agent Context & Usage Efficiency
Operational pointer: `docs/decisions/ADR-CAREER-OS-AGENT-CONTEXT-USAGE-EFFICIENCY-V1.md` (COMPLETED_BY_OPERATOR / BORA_ACCEPTED (2026-09-11) / GOVERNANCE_ONLY / GOVERNING) locks quality-preserving Claude Code / Cursor session and context discipline (bounded milestones, smallest sufficient relevant context, deterministic checks over agent reasoning where possible, Cursor as a consequential adversarial reviewer rather than an exploratory assistant). Bora explicitly accepted this policy on 2026-09-11, not as an operator self-grant. It governs usage/context economy only — it never overrides the Authority Order above, a locked rule, a validation schema, required review effort on consequential work, or any existing truth/evidence/approval boundary, and `implementation_authorized` remains false. Phase D (`CAREER_OS_FAILURE_TAXONOMY_AND_EVALUATOR_COVERAGE_MAP_V1`) remains COMPLETED_BY_OPERATOR / BORA_ACCEPTED (2026-09-11) / READ_ONLY_DESIGN_ONLY, now prior_phase; Phase E (`CAREER_OS_SYSTEM_EVAL_SET_ARCHITECTURE_V1`) is BORA_AUTHORIZED / SELECTED / NOT_YET_COMPLETED / READ_ONLY_DESIGN_ONLY, and Phase F and every later roadmap phase remain PROPOSED_NOT_AUTHORIZED. Any structural change to `CLAUDE.md`, `.cursor/rules/*`, `.cursorignore`, or `.claude/` settings remains a separate, not-yet-authorized decision.

## Truth Rules
Never invent or infer a factual claim merely to improve job fit. Unknown information must remain unknown.
- Do NOT fabricate: work experience, technologies, metrics, employment dates, titles, immigration/OPT facts, employer details, sponsorship facts, or résumé claims.
- Every material factual claim must trace directly to approved evidence in `evidence/` or `claims/`. No evidence lineage = no claim creation.

## Fresh First-Party Employer Source Rule
Operational execution of `BLUEPRINT.md`'s fresh first-party employer source rule: before acting on an employer-specific consequential premise, re-fetch the current source rather than reusing chat summaries, memory, sibling-role wording, or stale fixtures. If fresh source invalidates the premise, stop and report — do not adjust capture to fit the premise.

This applies to live career operations, not only implementation work: before meaningful employer-specific tailoring, package generation, or application execution, re-verify the exact requisition on the current first-party employer source in the same operating session (or same day) when reasonably retrievable — no universal freshness TTL is defined beyond that. When current first-party evidence conflicts with cached search results, search-engine indexes, aggregators/job boards, prior captures, chat summaries, or memory, the current first-party state controls current actionability; if it cannot be re-established from a first-party source, do not fabricate `VERIFIED_LIVE`. Preserve uncertainty on the existing independent axes — `source_verification_status` (e.g. `SOURCE_VERIFICATION_REQUIRED`) and `role_status` (e.g. `UNCLEAR` or `POSSIBLY_STALE`) — without collapsing them or inferring one from the other. A later closed/stale posting does not erase historical Employer Truth already captured (the prior JD, prior qualification analysis, or a previously submitted application) — only current actionability changes. "Already applied" is Application Truth, never a posting-freshness state.

For live discovery, also apply `SUBMITTED_OPPORTUNITY_DEDUPE_V1` (Section 138.15) before promoting a serious role or generating a package: if the same employer + exact requisition/opportunity already has historical Submitted Application Truth, or the exact first-party ATS explicitly says the candidate already applied, suppress it as a new opportunity. Do not treat an existing package folder alone as proof of submission, and do not fuzzy-match by title. `PREPARING`/`READY_FOR_REVIEW` continue the existing workflow rather than create a duplicate survivor.
Load `docs/application/BORA_APPLICATION_HISTORY_V1.json` at the start of every live discovery run and use it as the canonical persisted Application Truth ledger for exact-role dedupe. Update it only from authoritative Application Truth; never infer submission from a package folder or from chat memory alone.

For genuinely broad fresh discovery, attempt the canonical first-wave LinkedIn Free and Brandeis Handshake surfaces when they are accessible in the current execution context, alongside targeted direct employer/official ATS searches. If either surface is unavailable, authentication-gated, or otherwise not actually inspected, do not claim it was checked; continue through the remaining canonical source ladder and preserve the coverage limitation internally.

Cheap preliminary fit triage against discovery/index evidence is allowed before first-party verification (`BLUEPRINT.md` §135's `DiscoveryLead` → triage → gate → pursuit chain) — the gate applies before treating a role as actionable, not before any fit analysis. "Successfully established" requires the exact requisition to positively establish matching role/title identity, matching requisition identity, substantive current job-description content, and a current actionable application route/instruction. HTTP 200, a surviving requisition token/string, an ATS shell, or an Apply-like control alone never passes; any explicit dead/error-page state vetoes PASS even when HTTP 200 is returned or the requisition token survives. This is the current-actionability test defined in `BLUEPRINT.md` §135 — not merely evidence that the requisition once existed.

## End-User Application Transition Validation
Operational pointer: `BLUEPRINT.md` §135.1
(`END_USER_APPLICATION_TRANSITION_QUORUM_V1`) extends §135's current
actionability gate: establishing current first-party actionability, and
passing the §141.13 package-time recheck, both require end-to-end
validation, in the same operating session, of (1) the exact public
job-detail URL Bora would open for the exact role/requisition and (2) the
actual application transition/destination reached from that exact page.
An explicit dead/error page, a generic careers/search-landing redirect
with no matching current role, loss of exact role/requisition identity,
or an unusable application transition (broken link, dead-end redirect,
login/paywall dead end with no recoverable application path, or
a destination that no longer matches the exact role) vetoes
actionability even when the job-detail page itself returns HTTP 200,
still shows the requisition token, or displays an Apply-like control. An
Apply-looking control, an ATS API record, embedded page metadata, a
search/index result, or a requisition token may support discovery and
role/requisition identity but never substitutes for successful end-user
transition validation.

**Auth carve-out (not a veto).** A role-preserving login, SSO, or other
authentication step that continues into a usable, exact-role application
destination is not itself a veto — role identity must survive the auth
step and a recoverable application path must exist beyond it. Only a
login/paywall/auth dead end with no recoverable application path, or
identity loss across the auth step, fails closed. Operationally: the
application transition must be exercised or otherwise directly resolved
to the actual current end-user destination; an Apply control, ATS
API/index/metadata, HTTP 200, or a requisition token cannot substitute
for that resolution.

This does not blacklist Workday or any ATS vendor
and does not create a new actionability system, posting-state axis, or
enum; it does not alter Qualification Truth, Candidate Truth, Match
Truth, immigration, recency, start-horizon, employer-exclusion,
resume-content, or cover-letter-content doctrine.

## Package-Time First-Party Actionability Recheck and Gold-Artifact Spawn Gate
Operational pointer: `BLUEPRINT.md` §141.13-§141.15
(`CAREER_OS_PACKAGE_GATE_HARDENING_V1`) and
`docs/resume/BORA_PACKAGE_SPAWN_GATE_V1.json`, enforced by
`.cursor/rules/resume.mdc`, lock the correction earned by three reproduced
live defects: a Santander package produced before the exact first-party
requisition was proven actionable; a DraftKings resume that drifted from
the canonical gold family and leaked internal-system language; and the
Point32Health R9102 HTTP-200 dead-page false positive that continued despite
`TITLE_MATCH=False`.

Immediately before Claude drafting, DOCX mutation, cover-letter
drafting, or any other meaningful package work, the exact current
first-party employer requisition must be re-opened in the current
operating session and must still establish the full positive semantic
quorum: matching role/title identity, matching requisition identity,
substantive current job-description content, and a current actionable
application route/instruction — including the requirement to repeat both
elements of §135.1 again in the current operating session: (1) exact job-detail validation (the exact public
job-detail URL still establishes the current exact role) and (2) the
actual application transition/destination reached from it, exercised or
otherwise directly resolved. Prior pursuit-time success on either element
alone is insufficient at package time. §135.1's auth carve-out applies
unchanged: a role-preserving login/SSO step into a usable, exact-role
destination is not itself a veto; only a login/auth dead end with no
recoverable application path, or identity loss across it, fails closed.
HTTP 200, a requisition token, ATS shell, Apply-like control, or ATS
API/index/search metadata alone is never enough; any explicit dead/error-page
state, generic careers/search redirect, loss of exact role/requisition
identity, or unusable application transition fails closed even if HTTP
200 is returned or the requisition string survives. This applies the
Fresh First-Party Employer Source Rule above again at package time, since
a prior pursuit-time pass does not by itself satisfy it. On failure, no
resume, cover letter, or other candidate-facing package may be generated
or revised for that role; report the role as non-actionable/
verification-required using the existing `role_status`/
`source_verification_status` axes, never a new enum.

Resume spawning must clone the exact current Bora gold-quality DOCX
artifact as the starting document when available, with its SHA-256
verified against the canonical gold-reference record before making
bounded content edits; if the exact artifact is unavailable or its hash
does not match, stop with `GOLD_REFERENCE_ARTIFACT_REQUIRED` rather than
reconstructing the gold family from scratch. Candidate-facing package
text must not expose internal Career OS/governance/evidence-system/
implementation-control language unless the exact term is independently
job-relevant and recruiter-natural.

## Complete Four-Artifact Survivor Package Standard and Cover-Letter Gold Reference
Operational pointer: `BLUEPRINT.md` §141.16-§141.19
(`PACKAGE_OUTPUT_COVER_LETTER_GOLD_LOCK_V1`) and
`docs/resume/BORA_COVER_LETTER_GOLD_REFERENCE_V1.json`, enforced by
`.cursor/rules/resume.mdc`, lock complete survivor packages and a
hash-verified cover-letter gold reference.

Every genuine survivor role's FINAL package must durably contain résumé
DOCX, résumé PDF, cover-letter DOCX, and cover-letter PDF, unless Bora
explicitly opts out of the cover letter for that application. An
employer/application-system format instruction controls submission
choice only (§140.1) and never reduces which artifacts are generated in
the FINAL package (§140.9). Cover-letter DOCX construction must clone
the exact hash-verified `Bora_Chaush_Cover_Letter_Gold_Reference.docx`
(SHA-256 `264f7a8cc194e0211ce7f0af411b0ab6c07fa2438c557aa2e470536fded67e90`)
rather than reconstructing a template from doctrine text. The gold
DOCX's existence and SHA-256 match alone control clone authority and
spawn permission: if the exact gold DOCX artifact is unavailable or its
SHA-256 does not match, stop with
`COVER_LETTER_GOLD_REFERENCE_ARTIFACT_REQUIRED`. A rendered
visual-reference PDF of that same gold DOCX is separately recorded
(SHA-256 `0b7da43108b0fae5ba4211078b4308cad9014d1e11cb533bc25ed64feec8df42`)
and must be verified whenever that PDF is actually used for
visual-fidelity QA — but a missing or mismatched visual-reference PDF
hash alone does not trigger this stop condition. This reference is
presentation/quality/template authority only — never Candidate Truth.
Role-specific cover-letter content must remain grounded exclusively in
the verified current JD, Match Truth, and approved Candidate
Truth/evidence — never copied from the Northeastern University R141882
motivating exemplar's own role-specific facts. Cover letters are one
U.S. Letter page, visually clean, recruiter-natural, and conform to
this gold reference; §141's resume-specific presentation grammar and
§137's 92% meaningful-page-utilization floor are resume-scoped and do
not govern cover letters.

## Bora-Specific Employer-Family Exclusion and Discovery-Source Ladder
Operational pointer: `BLUEPRINT.md` §138.6.2
(`BORA_EXCLUDED_EMPLOYER_FAMILY_V1`) and §18.1
(`DISCOVERY_SOURCE_LADDER_V1` — a distinct identifier naming the source-
ladder ordering only, with no cross-ID coupling to the exclusion
identifier), enforced by `.cursor/rules/role-selection.mdc`. Mass General
Brigham system roles (first-party-identified, including Mass General
Brigham, Massachusetts General Hospital / The General Hospital
Corporation, Brigham and Women's Hospital, and other MGB-system entities a
first-party source itself identifies) are a Bora-specific pursuit/
preference exclusion from serious Bora-facing discovery and package
generation — not a claim that Mass General Brigham is a bad employer, and
not Qualification/Employer/Candidate/Match Truth. No unsupported global
affiliate list. This exclusion is integrated into §138.8 serious-role
promotion as a required third check alongside the §138.5 recency
visibility gate and the §138.14 start horizon gate: promotion requires all
three to PASS, and the employer-family-exclusion check cannot be skipped
once recency and start-horizon pass. When an excluded role is referenced
for audit/debugging only, its reason is labeled `BORA_EXCLUDED_EMPLOYER`
and must never be presented as a Qualification Truth REJECT; any
independent REJECT caused by a separate blocker is preserved unchanged.
Remains active until Bora explicitly overrides one specific role or
explicitly revokes the family exclusion; a per-role override does not
revoke the family exclusion for any other MGB-system role — it applies
only to that one specific role. Historical Submitted Application Truth for
any already-submitted Mass General Brigham system application is not
rewritten.
Separately, LinkedIn Free and Brandeis Handshake are preferred first-wave
discovery surfaces alongside targeted direct employer/official ATS
searches; Simplify Free, Built In, HigherEdJobs, Idealist, staffing/
recruiting firms, company lists, referrals, recruiter outreach, and other
credible job sources remain valid secondary/specialized discovery; generic
aggregators/generic search/index snippet results remain the
lowest-confidence tier — lead-generation only. Discovery source and
verification/application source stay separate: a LinkedIn/Handshake
listing may justify checking a role but never alone establishes Employer
Truth, the §138.5 recency anchor, first-party actionability, or
package-time semantic quorum — serious-role promotion still requires the
existing §138.5/§138.14/§135/§138.6 gates, the §138.6.2
employer-family-exclusion check PASS, and the package-time first-party
recheck above.

## Bora-Specific Hiring Relevance
Operational pointer: `BLUEPRINT.md` §136 locks Bora-specific hiring relevance as a structured component of Competitive Position (not a fifth truth axis, not a schema field, not a score). Comparison-pool alignment is distinct from seniority; institutional-affinity strength is tiered; network/access leverage is a separate concept from hiring relevance. Positive relevance signals never override a hard qualification blocker, a failed §135 actionability gate, or any legal/OPT/credential blocker. No numeric scores or weights — see §136 for the full doctrine.

## Approved Claim Is Not an Automatic Capability Mapping
An approved Claim does not automatically become an EvidenceMatch capability mapping merely because the Claim exists. Capability mapping requires its own supported/authorized basis. Do not automatically wire MM/TELUS or any other approved Claim to capabilities.

## Priority Selection
Next-task selection favors real operational constraint, a reproduced reliability defect, or meaningful Bora time savings over historical TODO order or theoretical completeness — see `BLUEPRINT.md`'s build-economy gate.

## Claim Actor Attribution (v1)

Substantive Evidence in `evidence_ids` establishes what happened. Bora's explicit `human_approval` on the exact Claim establishes conventional résumé active-voice actor attribution for that supported work. Human approval cannot create unsupported substantive facts. Authoritative policy: `docs/decisions/ADR-CLAIM-ACTOR-ATTRIBUTION-POLICY-V1.md`.

## Deterministic Work vs AI Work
- **Code (Deterministic)**: IDs, duplicate detection, dates, paths, schemas, state, audit logs, retries, idempotency, validation, and missing field checks.
- **AI (Semantic)**: Interpreting job descriptions, semantic evidence matching, qualification classification, and initial draft wording.
- **Rule**: If an operation can be calculated or validated deterministically, fail closed if validation fails. Never use AI for deterministic tasks.

## Pre-Execution & Schema Discipline
Before modifying or creating code, the active bounded implementation agent MUST:
1. Inspect `schemas/` and relevant existing files first.
2. Verify existing data models to prevent duplicate/conflicting types.
3. Perform the minimal required change without unrelated refactoring.

Consequential uncommitted diffs require Cursor adversarial review before commit/push unless Bora explicitly waives review for a specific task.

## Data Integrity & PII
- Missing fields must remain explicit (`null`, `UNKNOWN`, or `NOT_FOUND_IN_PUBLIC_SEARCH`). Never fill missing fields with plausible assumptions.
- Scrub raw PII from logs and application traces.
- Treat external APIs and Google Sheets as untrusted boundaries.

## Non-Interactive Testing Requirement
"It works" is not sufficient evidence.
- Run tests using the repository’s documented non-watch/non-interactive command. Never start watch mode unless explicitly requested.
- Test happy paths, boundary conditions, malformed inputs, and duplicate retry behaviors.
- Never delete, skip, or disable a test to force a build to pass.

## Stop Conditions
Stop and request clarification from Bora immediately if:
- A requested task conflicts with `BLUEPRINT.md`.
- Required evidence for a claim is missing.
- An OPT or legal work-authorization field is ambiguous.
- A material architecture change, database migration, or new infrastructure dependency is required.
