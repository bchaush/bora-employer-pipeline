# CAREER OS OPERATOR V1

Status: CANONICAL OPERATING ENTRYPOINT
Recorded: 2026-09-27
Purpose: let any fresh operator/session run Career OS without reconstructing the workflow from chat history.

This file is a router to canonical authority, not a replacement for BLUEPRINT.md, accepted ADRs, schemas, or runtime contracts.

## Authority Order

1. Bora's explicit current instruction.
2. Live canonical Git/GitHub state.
3. BLUEPRINT.md and accepted repository doctrine/ADRs.
4. project_state.json + CURRENT_EXECUTION_CHECKPOINT.json, cross-checked against live Git.
5. CURRENT_MILESTONE.md / CURRENT_STATE.md as continuity prose.
6. Live production ledger and durable application history for operational truth.
7. Chat history only as supporting context when consistent with the above.

Never let chat memory override repository or live operating evidence.

## Fresh-Session Recovery

> **Historical / superseded for current routing (2026-10-04):** start at `docs/CAREER_OS_RECOVERY_POINTER_V1.md`. The list below is retained as provenance; items 3-4 and 7 read stale continuity files.

Before consequential work:
1. Fetch `origin/main`.
2. Verify local/canonical SHA and worktree state.
3. Read `project_state.json`.
4. Read `CURRENT_EXECUTION_CHECKPOINT.json`.
5. Read `AGENTS.md` and `BLUEPRINT.md`.
6. Read the recovery ADR: `docs/decisions/ADR-CAREER-OS-EVAL-HARNESS-SEQUENCE-V1.md` Section 6.
7. Read `CURRENT_MILESTONE.md`, `CURRENT_STATE.md`, and `docs/SUPERVISED_PRODUCTION_V1.md`.
8. Read `docs/CAREER_OS_PERSONAL_V1_DIRECTION.md`.
9. Verify relevant live ledger/application-history state.
10. State the recovered phase and next bounded action before mutation.

If any recovery pointer disagrees with live canonical Git or newer accepted repository evidence:
- report the inconsistency;
- do not silently trust stale prose;
- repair only through a bounded governance change.

## When Bora Says "Run Career OS"

Determine intake type:
- Gmail alert
- direct/manual URL
- screenshot/private board
- existing canonical Job_ID

Then follow one conveyor:

```text
lawful discovery observation
→ durable DiscoveryLead
→ exact employer/opportunity identity
→ dedupe
→ canonical gates
→ Match Truth when permitted
→ present facts, gaps, blocker and result to Bora
→ STOP for Bora decision
```

The operator must not skip from discovery or partial analysis directly to package generation.

## Required Decision Boundary

Bora chooses one of:
- PURSUE
- WATCH
- REJECT

No current-role PURSUE:
→ no meaningful resume tailoring
→ no cover-letter drafting
→ no candidate-facing package generation

WATCH is not PURSUE.
A previous role's PURSUE does not authorize a materially changed opportunity.

## After PURSUE

1. Re-open the exact current first-party posting.
2. Revalidate exact role/requisition identity.
3. Revalidate current actionability and the actual application transition/destination.
4. Verify the Gold resume source exists and matches canonical SHA-256.
5. Verify the Gold cover-letter source exists and matches canonical SHA-256.
6. Load canonical current JD requirements.
7. Load canonical Requirement/EvidenceMatch output.
8. Build the explicit JD → evidence crosswalk.
9. Clone the exact Gold sources.
10. Apply only bounded evidence-grounded content changes.
11. Run claim lineage, immutable-field, format, and rendered visual QA.
12. Produce the four-artifact survivor package unless Bora explicitly waives the cover letter.
13. Persist exact artifacts and provenance.
14. Bora reviews and manually submits.

## Gold Hard Stops

Resume source expected SHA-256:
`ec3a9f9c6e2fc429e01892f61a074a71319ec6586566b6c1cf60808eba2f3f70`

Cover-letter source expected SHA-256:
`264f7a8cc194e0211ce7f0af411b0ab6c07fa2438c557aa2e470536fded67e90`

Wrong/missing resume artifact:
→ `GOLD_REFERENCE_ARTIFACT_REQUIRED`

Wrong/missing cover-letter artifact:
→ `COVER_LETTER_GOLD_REFERENCE_ARTIFACT_REQUIRED`

Never reconstruct an equivalent template from memory or doctrine text.

## Truth Discipline

- UNKNOWN stays UNKNOWN.
- Discovery-platform IDs are not employer opportunity IDs.
- Search/index snippets are discovery evidence, not first-party actionability.
- Approved Claim existence does not create unsupported capability mapping.
- Job terminology may be used only when it truthfully describes approved evidence.
- Never invent tools, metrics, outcomes, titles, dates, citizenship, work authorization, sponsorship facts, or employer facts.
- One held/failed Job_ID must not poison unrelated jobs.

## Engineering Escalation

Do not turn ordinary operation into engineering by default.

Engineer only when a real run shows:
1. a reproducible consequential system failure; or
2. repeated material operator workload/friction.

Then:
```text
reproduce
→ classify missing reality vs system defect
→ add regression when warranted
→ smallest bounded repair
→ validate
→ independent review
→ return to operation
```

Do not reopen mature architecture without evidence.

## Tool/Usage Discipline

- Use deterministic code for deterministic work.
- Use AI for semantic work.
- Conserve Claude/Cursor usage; use them where independent building/review materially helps.
- Do not run multiple autonomous builders against the same critical branch.
- Consequential uncommitted diffs receive independent adversarial review before promotion unless Bora explicitly waives it for that exact task.

## Operational Logging

Every consequential run/change should leave durable evidence sufficient for a fresh session to answer:
- what canonical SHA/state was used;
- what job/run/milestone was processed;
- what sources were inspected;
- what decision was reached;
- what human approval occurred;
- what files/artifacts changed;
- what validation/review ran;
- what exact next action remains.

Do not use chat history as the audit database.

## Current Product Direction

The locked Personal V1 sequence is maintained in:
`docs/CAREER_OS_PERSONAL_V1_DIRECTION.md`

The operator does not select a later roadmap step early merely because it exists there. Complete the current bounded step, validate it, update continuity, then proceed.

## Permanent No-Submit Rule

Career OS may research, verify, compare, prioritize, prepare, and assist with repetitive form filling.

External application submission remains Bora-controlled.
