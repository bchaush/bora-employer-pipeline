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

## Truth Rules
Never invent or infer a factual claim merely to improve job fit. Unknown information must remain unknown.
- Do NOT fabricate: work experience, technologies, metrics, employment dates, titles, immigration/OPT facts, employer details, sponsorship facts, or résumé claims.
- Every material factual claim must trace directly to approved evidence in `evidence/` or `claims/`. No evidence lineage = no claim creation.

## Fresh First-Party Employer Source Rule
Operational execution of `BLUEPRINT.md`'s fresh first-party employer source rule: before acting on an employer-specific consequential premise, re-fetch the current source rather than reusing chat summaries, memory, sibling-role wording, or stale fixtures. If fresh source invalidates the premise, stop and report — do not adjust capture to fit the premise.

This applies to live career operations, not only implementation work: before meaningful employer-specific tailoring, package generation, or application execution, re-verify the exact requisition on the current first-party employer source in the same operating session (or same day) when reasonably retrievable — no universal freshness TTL is defined beyond that. When current first-party evidence conflicts with cached search results, search-engine indexes, aggregators/job boards, prior captures, chat summaries, or memory, the current first-party state controls current actionability; if it cannot be re-established from a first-party source, do not fabricate `VERIFIED_LIVE`. Preserve uncertainty on the existing independent axes — `source_verification_status` (e.g. `SOURCE_VERIFICATION_REQUIRED`) and `role_status` (e.g. `UNCLEAR` or `POSSIBLY_STALE`) — without collapsing them or inferring one from the other. A later closed/stale posting does not erase historical Employer Truth already captured (the prior JD, prior qualification analysis, or a previously submitted application) — only current actionability changes. "Already applied" is Application Truth, never a posting-freshness state.

Cheap preliminary fit triage against discovery/index evidence is allowed before first-party verification (`BLUEPRINT.md` §135's `DiscoveryLead` → triage → gate → pursuit chain) — the gate applies before treating a role as actionable, not before any fit analysis. "Successfully established" requires the exact requisition to positively establish matching role/title identity, matching requisition identity, substantive current job-description content, and a current actionable application route/instruction. HTTP 200, a surviving requisition token/string, an ATS shell, or an Apply-like control alone never passes; any explicit dead/error-page state vetoes PASS even when HTTP 200 is returned or the requisition token survives. This is the current-actionability test defined in `BLUEPRINT.md` §135 — not merely evidence that the requisition once existed.

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
application route/instruction. HTTP 200, a requisition token, ATS shell,
or Apply-like control alone is never enough; any explicit dead/error-page
state fails closed even if HTTP 200 is returned or the requisition string
survives. This applies the Fresh First-Party Employer Source Rule above
again at package time, since a prior pursuit-time pass does not by itself
satisfy it. On failure, no
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
