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
