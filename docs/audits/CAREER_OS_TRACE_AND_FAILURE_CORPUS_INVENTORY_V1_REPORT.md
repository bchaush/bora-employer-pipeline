# OPERATOR INVENTORY REPORT / BORA ACCEPTED

**Phase:** `CAREER_OS_TRACE_AND_FAILURE_CORPUS_INVENTORY_V1` (Phase C, read-only)
**Status:** Operator-completed; **BORA ACCEPTED** (2026-09-11). This report remains a historical operator finding and durable rendering of the read-only Phase C inventory into canonical documentation. It does not itself authorize Phase D, a failure taxonomy, an evaluator map, trace infrastructure, or any implementation. At the time of this Phase C acceptance, Bora separately authorized `CAREER_OS_AGENT_CONTEXT_AND_USAGE_EFFICIENCY_V1` (a governance-only policy milestone) to begin as the next step before Phase D. Acceptance is recorded in `CURRENT_EXECUTION_CHECKPOINT.json`; that live checkpoint, not this historical report, governs current phase state. See `docs/decisions/ADR-CAREER-OS-EVAL-HARNESS-SEQUENCE-V1.md` for the governing roadmap and authority order.

## Scope

Read-only inventory of the genuine Career OS operating corpus — real application submissions, reproduced live failures, and controller/reviewer integrity defects — as durably preserved in repository history (`CHANGELOG.md`, `CURRENT_STATE.md`, `CURRENT_MILESTONE.md`, `docs/application/BORA_APPLICATION_HISTORY_V1.json`, merged-PR bodies, and milestone contracts). Per the governing ADR (Section 7), this deliverable is the observed real-run corpus inventory and its provenance quality — it is explicitly **not** the Phase D failure taxonomy/evaluator map, and open-coding buckets below are recorded as Phase C qualitative tags only, never a formal taxonomy or evaluator assignment. No production code, schema, Candidate/Employer/Match/Pursuit truth, or package-generation behavior was mutated by this inventory.

## Evidence-label legend

Every case below is labeled with exactly one of:

- **OBSERVED** — a durable, currently-tracked repository record (e.g. `docs/application/BORA_APPLICATION_HISTORY_V1.json`) that itself is the primary evidence.
- **RECONSTRUCTED_FROM_DURABLE_EVIDENCE** — no raw run trace/artifact survives in repository history; the case is reconstructed from durable secondary records that do survive (merged-PR titles/bodies, `CHANGELOG.md`/`CURRENT_STATE.md` narrative, milestone contracts, test files) which describe a genuine, already-adjudicated operating event.
- **MISSING** — the referenced artifact class does not exist in repository history (explicitly not fabricated).
- **SYNTHETIC** — a deliberately constructed edge-case, never presented as production evidence.

**No case in this report is labeled SYNTHETIC.** Every case below is either OBSERVED or RECONSTRUCTED_FROM_DURABLE_EVIDENCE from a genuine prior operating event; no synthetic case is primary production evidence in this inventory.

## Raw-artifact availability (checked directly)

`.gitignore` excludes `.career-os/` (local per-machine milestone-run manifests/locks/builder-reviewer-assurance artifacts) and `*.pdf`/`*.docx` (résumé/cover-letter/package artifacts), with no re-inclusion pattern for either. No `.career-os/` directory exists in this worktree. Consequently:

- Raw controller run manifests, `events.jsonl` logs, and reviewer transcripts referenced by run identifiers below are **MISSING** from repository history — they were never committed, by design (`.gitignore` comment: "restart-safety comes from this being reconstructible from Git plus these local files, never from repository history").
- Local PDF/DOCX package artifacts (résumés, cover letters) are **MISSING** from repository history for the same reason.
- What does survive durably is the *secondary record* of each run: merged-PR bodies citing exact run identifiers, diff fingerprints, and Assurance/Cursor verdicts, plus `CHANGELOG.md`/`CURRENT_STATE.md`/test-file narrative describing the reproduced defect and its fix. This report does not claim raw traces exist where only these durable secondary records survive — every such case is labeled RECONSTRUCTED_FROM_DURABLE_EVIDENCE, not OBSERVED.

## 1. Submitted-application corpus (OBSERVED)

`docs/application/BORA_APPLICATION_HISTORY_V1.json` (`record_version` 1, `updated_at` 2026-09-10) is the canonical, currently-tracked Submitted Application Truth ledger. It durably contains exactly **14** entries, each `application_status: "SUBMITTED"` with `evidence_basis: "BORA_DIRECT_CONFIRMATION"` (Bora's own direct confirmation is the evidence, not a reconstruction):

1. The Brattle Group — Research Analyst (Economics and Finance), req. 4720807005
2. Daley and Associates — Investment Operations Analyst, req. 30180
3. Harvard University / Harvard Medical School — Part-Time Program Coordinator, req. 003692SR
4. Harvard University / Harvard T.H. Chan School of Public Health — Coordinator I (Program Coordinator), req. 003736SR
5. Harvard University / Harvard Medical School — Program Coordinator, req. 003741SR
6. Harvard University / Harvard Medical School — Business Systems Analyst, Harvard Integrated Life Sciences, req. 003836SR
7. Massachusetts Department of Transportation — IT Data Analyst I, req. 260005JH
8. Mass General Brigham — Financial Coordinator, req. RQ4076320
9. Morgan Stanley — Financial Analyst, Real Estate Investment Group, req. JR041580
10. Northeastern University — Cash Management Accountant, req. R141882
11. Point32Health — Business Analyst, req. R9102
12. Public Consulting Group — Apprentice Business Analyst, req. JR102087
13. Road Scholar — Coordinator, Program Operation - Central Programs, req. COORD002072
14. The Chicago School — Operations Analyst, req. R0013342

This is the exact 14-entry `BORA_DIRECT_CONFIRMATION` count named in the Phase C task scope; no additional or fewer entries exist in the current record.

## 2. Stale/dead/actionability-gate failure cases (RECONSTRUCTED_FROM_DURABLE_EVIDENCE)

No raw crawl/fetch trace for any of these survives in repository history — each is reconstructed from the durable doctrine/changelog record of the reproduced live failure and the fix it motivated. Raw trace: **MISSING**.

- **Mass General Brigham RQ4055007** and **Fresenius Medical Care R0266808** — the two reproduced live-market stale-role failures motivating `LIVE_ROLE_VERIFIED_ACTIONABILITY_GATE_V1` (PR #12; `CHANGELOG.md` 2026-09-03 entry). This inventory can only durably re-establish the exact page content for one of the two: for **Fresenius R0266808**, employer-owned indexed/Workday evidence appeared sufficient, but the exact requisition returned the explicit dead-page text ("The page you are looking for doesn't exist") when actually opened; for **MGB RQ4055007**, the exact first-party requisition could not be re-established from durable records reviewed for this inventory. Both cases were part of the defect that sharpened `VERIFIED_LIVE` to require the exact current requisition to load as the matching current role identity, not merely be indexed.
- **MGB RQ4075857** — motivating case for `PRE_SURFACING_FIRST_PARTY_ACTIONABILITY_ENFORCEMENT_V1` (PR #14; `CURRENT_STATE.md` 2026-09-07 catch-up entry; `tests/posting_state_decision_wiring_v1_test.py` case 3). Before the fix, `source_verification_status` existed but was not consumed by routing: a role could carry `role_status=LIKELY_LIVE` while exact current first-party verification was unavailable/page-not-found, and still surface as an APPLY-like recommendation. Fixed by requiring both `role_status=="VERIFIED_LIVE"` AND `source_verification_status=="VERIFIED_DIRECT"`.
- **Point32Health R9102** — cited in `AGENTS.md`'s Package-Time Recheck doctrine (`CAREER_OS_PACKAGE_GATE_HARDENING_V1`, PR #30) as a reproduced HTTP-200 dead-page false positive that continued to appear actionable despite `TITLE_MATCH=False`. Note: this same requisition also appears in the OBSERVED Submitted Application Truth ledger (Section 1, item 11) as a completed submission — the dead-page false positive and the eventual successful submission are two distinct, non-contradictory Application Truth events at different points in time; this report does not collapse them.
- **MassDOT IT Data Analyst I, req. 260005JH** — application-route failure motivating `BORA_EXCLUDED_APPLICATION_ROUTE_HOST_V1` (`BLUEPRINT.md` §138.6.1; PR #35): `massanf.taleo.net` locked as a Bora-specific excluded application-route host after this requisition's only available application path failed. This role also appears in the OBSERVED submitted-application ledger (Section 1, item 7) as SUBMITTED with `evidence_basis: "BORA_DIRECT_CONFIRMATION"`; the ledger does not itself record which route the eventual submission used, so this report makes no claim about that route. The taleo-host application-path failure is recorded here as a separate reconstructed actionability event, not as evidence about how the eventual submission occurred.

## 3. Package/artifact-quality failure cases (RECONSTRUCTED_FROM_DURABLE_EVIDENCE)

Raw local package artifacts (DOCX/PDF) are **MISSING** from repository history (gitignored, per the Raw-artifact-availability section above). Each case is reconstructed from the durable doctrine lock it motivated.

- **Atominvest — Implementation Analyst (under-filled résumé)** — motivating case for `RESUME_REFERENCE_DERIVATIVE_AND_PAGE_UTILIZATION_ENFORCEMENT_V1` (PR #16; `BLUEPRINT.md` Section 137). A truthful but substantially under-filled one-page résumé that Bora had to manually correct; fixed by a new pure-geometry 92%-of-page-height validator (`src/resume_page_utilization.py`), no PDF generator/parser dependency.
- **Santander — premature package generation** — one of two reproduced live defects motivating `CAREER_OS_PACKAGE_GATE_HARDENING_V1` (PR #30, governed run `20260909T172902Z-7add4b47`): a package was generated before the exact first-party requisition was proven actionable, closed by the package-time first-party actionability recheck now locked in `AGENTS.md`/`BLUEPRINT.md` Sections 141.13-141.15.
- **DraftKings — résumé drift / internal-jargon leakage** — the second reproduced live defect motivating the same `CAREER_OS_PACKAGE_GATE_HARDENING_V1` closure (PR #30): a résumé that drifted from the canonical gold family and leaked internal Career-OS/governance language into candidate-facing text, closed by the gold-reference-artifact clone-and-hash-verify requirement.

## 4. Controller/reviewer transport and evidence-integrity findings (RECONSTRUCTED_FROM_DURABLE_EVIDENCE)

Raw controller run manifests and reviewer transcripts are **MISSING** from repository history (`.career-os/` is gitignored by design). Each finding below is reconstructed from the merged-PR body that recorded it as durable secondary evidence at merge time.

- **F1-F9 (`CAREER_OS_BOUNDED_AGENT_BUILD_LOOP_V1`, PR #19)** — nine controller/reviewer integrity findings closed across three rounds of independent Cursor adversarial review during the first bounded-agent build-loop controller's construction: **F1** stale-evidence detection in the ASSURING state; **F2** live scope-validation wiring into the actual controller loop; **F3** reviewer-mutation detection via a deterministic backstop; **F4** internally-inconsistent SAFE-result rejection; **F5** test/review same-diff enforcement; **F6** fail-closed noisy-provider JSON extraction (corrected twice — first to reject ambiguous multi-candidate output, then to replace a handwritten brace/string scanner with `json.JSONDecoder().raw_decode` after Cursor reproduced a genuine false-SAFE attack via an unbalanced brace inside a finding's own text); **F7** fetch-failure fail-closed handling; **F8** lock-ownership-not-run-identity correction; **F9** empirically-verified real Claude Code CLI envelope parsing. Final independent Cursor verdict: SAFE. This PR was merged; its findings are preserved here as historical evidence of the controller's construction, not as a claim about the currently-merged state's remaining defects.
- **CLI argv-ordering defect (`CAREER_OS_CLAUDE_BUILDER_ARGV_ORDERING_FIX_V1`, PR #20)** — first real end-to-end controller invocation failed before Claude ever received a prompt: `--allowedTools` is a Commander.js variadic option in the real Claude Code CLI that greedily consumed the prompt as an additional tool-name value; fixed with a `--` positional-terminator placed after flags and before the prompt. A second, independently reproduced defect in the same PR: `shutil.which("claude")` resolved to the npm-generated Windows `claude.CMD` wrapper, which re-parses argv through `cmd.exe`'s `%*` expansion and silently truncated a multiline prompt at its first newline; fixed by preferring the native `claude.exe` sibling and failing closed (`InfrastructureError`) if none exists.
- **Session-recovery defect (`CAREER_OS_BUILDER_SESSION_RECOVERY_AND_STRUCTURED_COMPLETION_V1`, PR #21, run `20260907T193310Z-f6a756d2`)** — on a long-running builder task, Claude performed substantial real work across 3 independent attempts, but each attempt's final reply was conversational prose rather than the required structured JSON completion result; the outer envelope's `session_id` was only copied into the result after inner-result extraction succeeded, so every validation failure silently discarded a resumable session. Fixed with `RecoverableSessionInfrastructureError`, durable recovery reconstruction from `events.jsonl`, and a narrow resumed-completion prompt.
- **Provider stdout/stderr transport defect (`CAREER_OS_PROVIDER_ENVELOPE_STDOUT_STDERR_SEPARATION_V1`, PR #22)** — reproduced by fresh canary run `20260907T220348Z-3dacfcfd` (with runs `20260907T180932Z-656eae27` and `20260907T193310Z-f6a756d2` preserved as historical evidence per the governing milestone contract): subprocess capture combined stdout and stderr before strict outer-envelope parsing, so valid structured JSON on stdout plus diagnostic text on stderr could fail with "Extra data." Fixed by parsing provider structured JSON from stdout only, keeping stderr diagnostic-only; nonzero exits and malformed/trailing/multi-document stdout continue to fail closed.
- **Reviewer prompt-transport defect (`CAREER_OS_CURSOR_REVIEWER_STDIN_TRANSPORT_V1`, PR #23, run `20260908T184816Z-d3a8a974`)** — moved the Cursor reviewer prompt transport from argv to stdin with explicit UTF-8 encoding, preserving read-only Ask-mode authority and structured JSON envelope semantics; regression coverage added for long, short, and non-ASCII prompts. Final Cursor review: SAFE, zero findings.
- **Reviewer post-review gate separation (`CAREER_OS_REVIEWER_POST_REVIEW_GATE_SEPARATION_V1`, PR #25)** — bounded controller reviewer-stage fix distinguishing current reviewer evidence from later mandatory controller/human gates, without weakening or bypassing those later gates. Exact reviewed three-file scope.

Two additional governed runs are recorded here as durable secondary evidence of separately-scoped, non-defect milestone closures rather than integrity findings: `20260909T040202Z-811bdf0a` (`BORA_RESUME_GOLD_QUALITY_REFERENCE_V1`, PR #29) and `20260909T172902Z-7add4b47` (`CAREER_OS_PACKAGE_GATE_HARDENING_V1`, PR #30 — see Section 3 for its Santander/DraftKings defect content).

## 5. Duplicate/application-lifecycle continuity (OBSERVED + RECONSTRUCTED_FROM_DURABLE_EVIDENCE)

`SUBMITTED_OPPORTUNITY_DEDUPE_V1` (PR #40) and the seeding of `BORA_APPLICATION_HISTORY_V1` (PR #41) lock exact employer+requisition dedupe ahead of fresh discovery/package generation, using the OBSERVED 14-entry ledger in Section 1 as the canonical Submitted Application Truth source. No raw duplicate-detection run trace survives; the dedupe mechanism itself (`src/` dedupe logic and `tests/application_history_registry_v1_test.py`) is OBSERVED as currently-tracked code, while the specific triggering real-world duplicate event, if any beyond the general risk the milestone addressed, is not separately named in durable records reviewed for this inventory.

## Open-coding qualitative tags (Phase C only — not a Phase D taxonomy)

These are qualitative groupings applied to the cases above for this read-only inventory. They are explicitly **not** a formal failure taxonomy, not a severity ranking, and not an evaluator-coverage map — those are Phase D deliverables and remain `PROPOSED_NOT_AUTHORIZED`.

- **current-role/actionability** — Section 2 (MGB RQ4055007, Fresenius R0266808, MGB RQ4075857, Point32Health R9102, MassDOT 260005JH).
- **package/artifact quality/spawn** — Section 3 (Atominvest, Santander, DraftKings).
- **controller/reviewer transport/evidence integrity** — Section 4 (F1-F9, argv-ordering, session-recovery, stdout/stderr separation, stdin transport, post-review gate separation).
- **duplicate/application-lifecycle continuity** — Section 5 (submitted-opportunity dedupe, application-history ledger).
- **human-handoff/submission continuity** — Section 1 (the 14-entry `BORA_DIRECT_CONFIRMATION` submitted-application ledger itself, as the record of completed human handoff/submission for each role).

## Not done / not authorized by this inventory

- No `CAREER_OS_RUN_TRACE_V1` design or trace schema.
- No formal Phase D failure taxonomy, severity ranking, or evaluator-coverage map.
- No trace infrastructure, database, dashboard, orchestration automation, new agent, model router, or LLM judge.
- No production Career OS behavior, schema, Candidate/Employer/Match/Pursuit truth, or package-generation logic changed.
- No claim that raw run traces exist beyond what durable secondary records (merged-PR bodies, changelog/state narrative, test files) establish.

## Acceptance

Bora has explicitly accepted the Phase C (`CAREER_OS_TRACE_AND_FAILURE_CORPUS_INVENTORY_V1`) checkpoint and this operator inventory report (2026-09-11), recorded as `prior_phase` in `CURRENT_EXECUTION_CHECKPOINT.json` (see `phase_c_completed_actions_reference` there for the same completed inventory actions listed above). This acceptance is the accepted basis for Bora's separate authorization of `CAREER_OS_AGENT_CONTEXT_AND_USAGE_EFFICIENCY_V1` (governance-only policy milestone), which at the time of this Phase C acceptance had not yet started. Bora's acceptance of this historical report does not constitute acceptance of any later phase's current state; current state is governed solely by the live `CURRENT_EXECUTION_CHECKPOINT.json`. This report does not authorize implementation, trace infrastructure, a database/UI, orchestration automation, a new agent, model routing, an LLM judge, or Phase D.
