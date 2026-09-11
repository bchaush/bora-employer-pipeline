# ADR — Career OS Agent Context & Usage Efficiency v1

Status: **CANDIDATE_POLICY / GOVERNANCE_ONLY / COMPLETED_BY_OPERATOR / PENDING_BORA_ACCEPTANCE / NOT_YET_GOVERNING / NO IMPLEMENTATION AUTHORIZED**
Date: 2026-09-11
Owner: Bora + ChatGPT architecture/adjudication layer; implemented by Claude Code as bounded governance builder
Milestone: `CAREER_OS_AGENT_CONTEXT_AND_USAGE_EFFICIENCY_V1`

## 1. Purpose

Bora explicitly accepted the Phase C (`CAREER_OS_TRACE_AND_FAILURE_CORPUS_INVENTORY_V1`) checkpoint and explicitly authorized this governance-only policy milestone before Phase D (see `docs/decisions/ADR-CAREER-OS-EVAL-HARNESS-SEQUENCE-V1.md`). Phase D remains **PROPOSED_NOT_AUTHORIZED**.

This ADR sets out a candidate policy to lock quality-preserving Claude Code / Cursor context-and-usage discipline: minimize irrelevant context, duplicated reasoning, and unnecessary model work, without ever reducing evidence depth, validation depth, required intelligence, truth standards, independent review, or human-approval boundaries. The operator cannot self-grant acceptance of this policy; it is COMPLETED_BY_OPERATOR / PENDING_BORA_ACCEPTANCE / NOT_YET_GOVERNING until Bora explicitly accepts it. If and when Bora accepts this ADR, it will govern subsequent Career OS engineering work as described below. It authorizes **no** product/runtime implementation, no `CAREER_OS_RUN_TRACE_V1`, no Phase D taxonomy/evaluator work, and no structural change to any currently loaded context surface (`CLAUDE.md`, `.cursor/rules/*`, `.cursorignore`, `.claude/` settings/skills/subagents/hooks).

## 2. Source-label discipline

Every material claim below carries exactly one label:

- **SOURCE_DIRECT** — a current first-party vendor/practitioner source states the fact directly.
- **CAREER_OS_ADAPTATION** — our bounded operating rule derived from sources + Career OS governance.
- **OBSERVED_REPO_FACT** — a directly inspected fact about this repository/current tooling surface.
- **OPEN_HYPOTHESIS** — a plausible optimization target requiring later measurement; never doctrine-as-fact.

No statement becomes Career OS doctrine merely because a vendor or practitioner recommends it, and no OPEN_HYPOTHESIS may be treated as an implementation authority.

## 3. SOURCE_DIRECT facts (retrieved 2026-09-11; not strengthened beyond what each source states)

### Anthropic

- `https://claude.com/blog/using-claude-code-session-management-and-1m-context` — SOURCE_DIRECT: Claude Code context contains the system prompt, conversation, tool calls/outputs, and files read; larger/older irrelevant context can degrade performance ("context rot"). `/usage` exposes usage information. Fresh context/subagents can isolate noisy intermediate work.
- `https://claude.com/blog/steering-claude-code-skills-hooks-rules-subagents-and-more` — SOURCE_DIRECT: root `CLAUDE.md` loads at session start and stays in context; every line costs context whether relevant or not. Path-scoped rules load only when relevant; Skills load full bodies on demand; subagents isolate side work; deterministic command/http hooks can run outside main model reasoning/context.
- `https://code.claude.com/docs/en/costs` — SOURCE_DIRECT: `/clear` is recommended when switching to unrelated work; stale context wastes tokens on later messages. `/context` shows what consumes context; `/usage` reports usage. Anthropic suggests keeping `CLAUDE.md` focused (under roughly 200 lines) and moving specialized workflows to on-demand skills where appropriate. Extended/deeper thinking materially helps complex reasoning; lower effort is a cost/capability tradeoff, not a free optimization.
- `https://code.claude.com/docs/en/model-config` — SOURCE_DIRECT: each effort level trades token spend against capability. Low effort is for short, well-scoped, latency-sensitive tasks that are not intelligence-sensitive. Medium effort reduces tokens for work that can tolerate some tradeoff in intelligence. High effort balances token usage and intelligence. Xhigh effort gives deeper reasoning at higher token spend and is Opus 4.7's default. Max effort may improve very demanding tasks but carries a diminishing-returns/overthinking risk and should be tested before broad adoption.
- `https://code.claude.com/docs/en/settings` and `https://code.claude.com/docs/en/permissions` — SOURCE_DIRECT: current supported exclusions for sensitive paths use `permissions.deny`/settings; deprecated `ignorePatterns` should not be resurrected as folklore. `bypassPermissions` skips normal prompts and is intended only for isolated environments.
- `https://code.claude.com/docs/en/prompt-caching` and `https://claude.com/blog/lessons-from-building-claude-code-prompt-caching-is-everything` — SOURCE_DIRECT: prompt caching is prefix-based; stable content/configuration supports reuse. Model/context/tool changes can affect cache behavior. No unsupported cache rule is invented beyond what these sources state.

### Cursor

- `https://cursor.com/blog/agent-best-practices` — SOURCE_DIRECT: give Agent the context it needs; if the exact relevant file is known, tag it, otherwise let Agent search; irrelevant files can confuse the task. Cursor Rules are persistent/static context; Skills are dynamic/on-demand capabilities.
- `https://prod.cursor.com/docs/reference/ignore-file` and `https://prod.cursor.com/help/customization/ignore-files` — SOURCE_DIRECT: `.cursorignore` can exclude safely irrelevant files from Cursor AI file access/discovery; Cursor also respects `.gitignore`. Terminal/MCP tools are not bounded by `.cursorignore`, so it is not a complete security boundary.
- `https://cursor.com/docs/models-and-pricing` and `https://prod.cursor.com/help/models-and-usage/usage-limits` — SOURCE_DIRECT: current usage-based plans do not use legacy Max Mode. Legacy Max Mode extends context and can cost more; ordinary/default context is enough for most tasks.

### Practitioner cross-checks (philosophy only, not vendor-fact authority)

- IndyDevDan, `https://github.com/disler/super-simple-software-factory` — SOURCE_DIRECT (as a citation of published guidance, not a vendor fact): deterministic code owns sequencing/retries/acceptance; coding agents are bounded nodes. Known gates/tests belong in code; correction of the same bounded session can be cheaper/cleaner than a cold restart.
- Hamel Husain + Shreya Shankar, `https://hamel.dev/blog/posts/evals-faq/` — SOURCE_DIRECT: use representative real traces and human error analysis/open coding before formal evaluators; measure real behavior rather than generic claims.
- Cole Medin, `https://github.com/coleam00/ai-transformation-workshop` — SOURCE_DIRECT: PIV = Plan → Implement → Validate; fresh/reset context between major phases; Git/reusable commands are durable project machinery; on-demand context is preferable to loading everything everywhere.

## 4. OBSERVED_REPO_FACT — measured on baseline `ba6530498be3410e3524aacd1ff5fba0c815d8d0`

Measured deterministically via `git show <baseline>:<path> | wc -c` / `wc -l` (the canonical git-blob byte count, not a CRLF-checkout disk-file byte count, which inflates the byte total by exactly one byte per line on a Windows CRLF working tree):

- `CLAUDE.md` = 2,860 bytes / 78 lines.
- `AGENTS.md` = 21,888 bytes / 256 lines.
- `.cursor/rules` has seven `alwaysApply: true` files: `architecture.mdc` 5,180 B / 175 lines; `data-integrity.mdc` 5,432 B / 212 lines; `opt-safety.mdc` 9,565 B / 247 lines; `resume.mdc` 28,832 B / 635 lines; `role-selection.mdc` 16,775 B / 244 lines; `testing.mdc` 4,908 B / 184 lines; `truth.mdc` 3,599 B / 126 lines.

These are facts only, recorded for future measured comparison. This ADR does **not** change `CLAUDE.md`, `.cursor/rules/*`, `.cursorignore`, or any `alwaysApply` rule. `AGENTS.md` receives only a concise operational pointer to this ADR (Section 8), not a restatement of policy. Any later reduction/splitting of loaded context is **OPEN_HYPOTHESIS**, requiring a separately authorized, measured context-surface audit before any change.

## 5. Candidate policy principles (quality first; pending Bora acceptance)

CAREER_OS_ADAPTATION, derived from Sections 3-4 above plus existing Career OS governance:

1. Quality/evidence/validation depth outrank quota conservation.
2. One bounded milestone per primary Claude/Cursor session; a new milestone starts a fresh session rather than reviving a stale unrelated huge context.
3. Repository/checkpoint/Git state is durable memory; do not carry giant conversational histories forward.
4. Deterministic commands/tests/hashes/diffs/schema checks stay deterministic rather than consuming agent reasoning.
5. Smallest sufficient relevant context, never less than correctness requires.
6. Exact-file targeting when known; targeted search when not; no whole-repo dumping "just in case."
7. Avoid dumping full passing logs/unrelated output into model context; preserve failures/details needed for diagnosis.
8. Subagents only when isolation of large/noisy exploration genuinely benefits parent context; not for trivial tightly coupled work.
9. Keep model/tool/effort configuration stable within a bounded session when practical; no unsupported cache folklore.
10. Never lower reasoning effort on consequential semantic/architecture/truth/debugging/adversarial-review work merely to preserve quota. Lower effort only for fully specified mechanical work with deterministic closure.
11. Cursor standard/ordinary context by default; enlarged context only when demonstrably needed.
12. Do not disable required resume/cover-letter visual QA in the name of token savings.
13. Use Claude `/context` and `/usage` during future measurement/audits rather than guessing.
14. `.cursorignore` only for safely irrelevant material and never as a complete security boundary. Do not introduce `.claudeignore` folklore; use current Anthropic-supported settings/permissions.
15. No numerical savings claims until Career OS itself measures them.
16. Context optimization must never weaken Candidate Truth, evidence lineage, deterministic gates, independent review, or human-approval boundaries.
17. `bypassPermissions` (which skips normal Claude Code permission prompts and is, per Anthropic's own documentation, intended only for isolated environments) must not become the Career OS default.

## 6. Cursor economy rule (candidate; pending Bora acceptance)

CAREER_OS_ADAPTATION: Cursor is a consequential adversarial reviewer, not an exploratory assistant, by default. Before spending review: Claude bounded builder work is complete; ChatGPT independently adjudicates obvious scope/provenance issues; deterministic required checks are green; the exact consequential diff is frozen/fingerprinted; Cursor receives the milestone contract plus the exact diff plus relevant authority only. Findings return to ChatGPT adjudication; accepted corrections go only to Claude; deterministic gates rerun before another Cursor pass.

## 7. Claude economy rule (candidate; pending Bora acceptance)

CAREER_OS_ADAPTATION: Claude Code is a bounded builder, not project memory or architecture owner. A new implementation/governance milestone starts from canonical repo/checkpoint state with a concise bounded contract. Do not revive an unrelated multi-day session merely because it exists. A same-session correction loop is appropriate only while the same milestone/context remains directly relevant and clean.

## 8. `AGENTS.md` operational pointer

`AGENTS.md` gains one concise pointer to this ADR (not a restatement of the policy): the candidate context-and-usage-efficiency principles, if and when Bora accepts this ADR, will govern Claude Code / Cursor session and context discipline, subordinate to the existing Authority Order and never overriding a locked rule, validation schema, or the existing review/approval boundaries. Until Bora accepts this ADR, it is not yet governing.

## 9. Deferred structural work (OPEN_HYPOTHESIS)

Any later reduction, splitting, or restructuring of a currently loaded context surface (`CLAUDE.md`, `.cursor/rules/*`, `.cursorignore`, `.claude/` settings/skills/subagents/hooks) is explicitly deferred to a later, separately authorized, measured context-surface audit. This ADR records the Section 4 baseline measurements so that a future audit has a comparison point, but it does not itself authorize any structural change, and no percentage or numeric savings claim is made here.

## 10. Hard prohibitions in this milestone

- No `BLUEPRINT.md`, `CLAUDE.md`, `.cursor/rules/*`, or `.cursorignore` change; no `alwaysApply` change.
- No `.claude/` settings/skills/subagents/hooks/context-loader restructuring.
- No `src/`, `schemas/`, `claims/`, `evidence/`, `experiences/`, `resume/`, `golden-tests/` product/truth behavior change.
- No Phase D taxonomy/evaluator work.
- No `CAREER_OS_RUN_TRACE_V1`, trace schema/infrastructure, database/UI, automation, new runtime agents, model routing, or LLM judge.
- No unsupported savings percentage, no invented current vendor command/setting, no blanket "low effort saves quality-neutral tokens" claim.

## 11. Decision

**CANDIDATE DECISION (NOT YET GOVERNING):** the policy principles in Sections 5-7, if and when Bora explicitly accepts this ADR, will govern Claude Code and Cursor session/context discipline going forward, as a quality-preserving usage-efficiency layer subordinate to the existing Authority Order in `AGENTS.md` and to every existing truth/evidence/review/approval rule. The operator/builder cannot self-grant that acceptance. Structural context-surface changes remain **OPEN_HYPOTHESIS**, requiring a separate measured audit and separate authorization (Section 9). This ADR does not authorize Phase D or any product/runtime implementation.

**STATUS:** `CAREER_OS_AGENT_CONTEXT_AND_USAGE_EFFICIENCY_V1` is **COMPLETED_BY_OPERATOR / PENDING_BORA_ACCEPTANCE / GOVERNANCE_ONLY / NOT_YET_GOVERNING / NO_IMPLEMENTATION_AUTHORIZED**. Phase D (`FAILURE_TAXONOMY_AND_EVALUATOR_COVERAGE_MAP`) remains **PROPOSED_NOT_AUTHORIZED**. `implementation_authorized` is `false`. The sole next allowed action is for Bora to review and accept or reject this policy milestone/checkpoint; no Phase D work may begin until Bora separately accepts this checkpoint and separately authorizes a next phase. Until that acceptance, this ADR does not govern anything.

## 12. Reference URLs at lock time

- https://claude.com/blog/using-claude-code-session-management-and-1m-context
- https://claude.com/blog/steering-claude-code-skills-hooks-rules-subagents-and-more
- https://code.claude.com/docs/en/costs
- https://code.claude.com/docs/en/model-config
- https://code.claude.com/docs/en/settings
- https://code.claude.com/docs/en/permissions
- https://code.claude.com/docs/en/prompt-caching
- https://claude.com/blog/lessons-from-building-claude-code-prompt-caching-is-everything
- https://cursor.com/blog/agent-best-practices
- https://prod.cursor.com/docs/reference/ignore-file
- https://prod.cursor.com/help/customization/ignore-files
- https://cursor.com/docs/models-and-pricing
- https://prod.cursor.com/help/models-and-usage/usage-limits
- https://github.com/disler/super-simple-software-factory
- https://hamel.dev/blog/posts/evals-faq/
- https://github.com/coleam00/ai-transformation-workshop
