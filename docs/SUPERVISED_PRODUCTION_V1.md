# Career OS — Supervised Production V1

Status: CONTRACT_CANDIDATE_PENDING_REVIEW
Baseline: `d16c4473d3fb1505a95c5a95c90c766a0a4afd5c`
Purpose: move the existing truth engine into supervised daily production with the smallest reliable control plane.

## 1. Product boundary

Career OS V1 is:

`Scout -> Normalize -> Cheap Gates -> Verify -> Match Truth -> Bora Review -> Golden Package -> Application Ledger`

It is not a job board, mass-apply bot, universal scraper, or replacement ATS.

Permanent human gates:

1. `PURSUE?` — Bora decides whether an opportunity should advance into consequential package/application preparation.
2. `SUBMIT?` — Bora reviews and performs/authorizes final external submission.

System recommendation never equals pursuit authorization. Pursuit authorization never equals submission authorization.

## 2. Canonical authority

Authority order for production operation:

1. Git/repository canonical truth and protected schemas/tests.
2. Durable operational records (`JOBS`, `APPLICATIONS`, `LOG`) for run/application state.
3. Generated artifacts and provider observations.
4. Chat history.
Uploaded/historical documents never override a newer canonical repository contract.
The permanent truth core is Employer Truth, Candidate Truth, Match Truth, Pursuit Truth, Package Truth, and Outcome Truth.

## 3. Production baseline rule

Treat the current Match Truth semantic core as production-frozen. Treat the existing resume truth, lineage, patch, presentation-view, and validation modules as frozen reusable foundations; production Golden Package orchestration and DOCX/PDF generation/export are not yet implemented and remain MISSING.

A semantic engine mutation requires all of:

1. a real current role;
2. legitimate upstream clearance;
3. a consequential wrong canonical result;
4. mechanical reproduction;
5. causal semantic-owner adjudication;
6. deterministic RED coverage;
7. bounded implementation authorization;
8. green Assurance on exact candidate bytes;
9. independent review of those immutable bytes.

Interesting hypothetical edge cases do not earn mutation.

## 4. Source / adapter rule

Commodity sources are replaceable adapters. Initial supervised-production adapters may include Gmail alerts, Handshake, Simplify, selected employer alerts, and supplemental research services.

No provider is canonically locked as part of the truth core.
External discovery produces nominations only. A source freshness claim, platform fit score, or model recommendation never becomes Employer Truth or Match Truth without Career OS verification.

Workday cached/indexed relative age remains nomination-only; current exact employer UI or trustworthy absolute employer-side time evidence is required for authoritative freshness.
## 5. Gate order

Production operation must preserve cheap-failure-first routing:

`freshness -> geography -> employer exclusions/start horizon -> OPT/work-authorization screen -> candidate conditions -> threshold/seniority/specialist constraints -> actionability/conflicts -> crowding -> Match Truth`

Rules:

- no Match Truth before authoritative freshness;
- no Match Truth after an upstream terminal kill;
- candidate-condition gates must consume canonical Candidate Truth, not chat memory; Bora directly answered `driver_license = NO` on 2026-09-16, but that fact must be persisted through the existing evidence/attestation truth mechanism before unattended cross-chat production may rely on it;
- explicit employer exclusion of F-1/OPT/CPT or an incompatible permanent/indefinite-authorization condition terminates upstream;
- generic `no sponsorship` language alone is not silently converted into an OPT prohibition;
- ambiguous degree-to-duty or immigration questions become HOLD / human- or qualified-authority review, never invented legal certainty.

The OPT screen is currently an operating gate. This contract does not claim a fully implemented `OPT_ELIGIBILITY_GATE_V1` exists in canonical code.

## 6. Operational states

The control plane may use these production workflow states, kept separate from existing Job decision/lane enums:

`DISCOVERED`
`NORMALIZED`
`UPSTREAM_REJECTED`
`VERIFICATION_REQUIRED`
`EMPLOYER_VERIFICATION_PASSED`
`MATCH_ANALYZED`
`REVIEW_READY`
`PURSUIT_APPROVED`
`PACKAGE_READY`
`APPLICATION_RECORDED`
`OUTCOME_RECORDED`
`PROCESSING_ERROR`

These are control-plane workflow states only. They must not overwrite or impersonate existing canonical truth enums.

## 7. V1 operating ledger

Restore the visible control plane in Google Sheets without changing Blueprint В§76. The V1 Sheet is initialized with the canonical seven tabs: `SETTINGS`, `JOBS`, `EVIDENCE`, `CLAIMS`, `APPLICATIONS`, `NETWORK`, and `LOG`. Slice 1 writes only `JOBS` and `LOG`; the other canonical tabs remain present but are not expanded or repurposed by this slice.

### JOBS

Minimum fields:

`Job_ID, Company, Role, Discovery_Source, Discovery_URL, Official_URL, First_Seen, Last_Verified, Pipeline_State, Freshness_State, Geography_State, OPT_Screen_State, Candidate_Condition_State, Threshold_State, Role_Status, Match_State, Decision, Bora_Decision, Package_Status, Application_Status`

### APPLICATIONS

Minimum fields:

`Application_ID, Job_ID, Applied_Date, Resume_Version, Cover_Letter_Version, Channel, Current_Status, Last_Update, Next_Action, Outcome`

### LOG

Minimum fields:

`Run_ID, Timestamp, Stage, Source, Job_ID, Status, Error_Code, Engine_Baseline, Notes`

The seven-tab model remains canonical V1 doctrine. `APPLICATIONS` becomes an active persistence surface only in a later separately authorized slice; Slice 1 does not write application lifecycle state.
## 8. First vertical slice

The first implementation slice is deliberately narrow:

`Gmail -> extract alert nominations as untrusted DiscoveryLead inputs -> normalize -> exact-role dedupe/resolution -> JOBS + LOG persistence`

Do not attach Match Truth, package generation, Vercel UI, browser automation, or supplemental Scout vendors until this slice is reliable on real data.

Acceptance for Slice 1:

- one intake adapter only: Gmail;
- structured source provenance retained;
- exact-role dedupe/resolution uses exact employer/system identity + exact requisition/opportunity identifier, consistent with the canonical application-history identity rule; it must not equate `generate_job_id(company, role)` with exact-role identity; when the requisition/opportunity identifier is unavailable, identity remains unresolved rather than fuzzy-merged;
- duplicate nominations converge on one operational job row without deleting source observations;
- malformed/ambiguous nominations fail closed to a visible error/hold state;
- no nomination claim is promoted into Employer Truth;
- at least one real batch can be ingested and reconciled without manual row surgery;
- no truth-engine files need modification for ingestion to work.

## 9. Slice sequence

After Slice 1 proves reliable:

1. attach existing cheap gates + Employer Truth + Match Truth and write outcomes back to Sheet;
2. in a separately authorized consumer milestone, implement a durable record/schema/consumer for the pursuit semantic boundary already locked by `ADR-PURSUIT-APPROVAL-BOUNDARY-V1.md`, binding it to current opportunity/analysis identity strongly enough to prevent stale intent reuse;
3. in a later separately authorized package milestone, compose the existing resume truth/lineage/patch/validation foundations into production package orchestration only after `PURSUE`; DOCX/PDF generation/export and complete Golden Package orchestration are MISSING today and must not be treated as already available;
4. persist package artifacts in Drive and link them from the ledger only after the package milestone exists;
5. only then add a thin Vercel `TODAY / REVIEW / PACKAGES / APPLICATIONS / RUNS` control plane;
6. only after 3-5 clean supervised runs enable scheduled morning operation;
7. add Scout sources one at a time and retain them only when measured survivor yield justifies them.
## 10. Model / tool roles

- ChatGPT Work: primary architect, research, semantic adjudication, truth/calibration, operation, sequencing, and final decision guidance.
- Deterministic Career OS code: schemas, provenance, dedupe, gate order, hard constraints, Match Truth, validators, lineage.
- Claude Code: primary bounded implementation agent, only after explicit authorization and a frozen mutation contract.
- Cursor: mandatory independent adversarial reviewer of consequential uncommitted diffs before commit/push; not the default primary builder.
- Gemini: optional non-coding strategic/directional second opinion only; not part of the coding execution or coding-review loop.
- Claude Research or other model research services may be optional replaceable Scout/research adapters; no such service may become a required database or daily runtime dependency.
- Google Sheets: visible V1 operating ledger.
- Google Drive: generated package storage.
- Gmail: initial intake bus.
- Vercel: replaceable orchestration/runtime/UI adapter after the Sheet loop is proven.
- Bora: `PURSUE` and `SUBMIT` consequential gates.

## 11. Build economy / non-goals

Do not build in this phase:

- a new database;
- autonomous application submission;
- custom application autofill;
- a custom Handshake/Simplify job board;
- a universal Workday scraper;
- a Vercel dashboard before Sheet operation is proven;
- AI analysis of every raw nomination;
- package generation for roles Bora has not approved;
- semantic-engine improvements without an earned production defect.

## 12. Production metrics

Measure source and pipeline performance from durable run data:

`nominated, unique, employer-live, authoritative-fresh, geo-clean, OPT-screen-pass, OPT-screen-hold, threshold-clean, Match-Truth reached, Apply-like, duplicates, stale/dead, processing-errors, elapsed-time, incremental-cost`.

`OPT_Screen_State` and these metrics are operational screening outputs only, never legal determinations of OPT eligibility.
After 15 submitted applications or 10 calendar days, review strategy per Blueprint §106. Also report market-softness signals separately from targeting quality; do not blame résumé/targeting merely because a high share of checked inventory is stale/unclear.

## 13. New-chat recovery contract

Do not define a competing recovery sequence here. Fresh sessions must follow the single canonical recovery order in `docs/decisions/ADR-CAREER-OS-EVAL-HARNESS-SEQUENCE-V1.md` Section 6 exactly.

Once this contract is merged and the required post-merge governance sync has updated canonical pointers, `docs/SUPERVISED_PRODUCTION_V1.md` becomes an additional required production-context read alongside the existing canonical recovery surfaces; it does not replace, reorder, or omit `project_state.json`, `CURRENT_EXECUTION_CHECKPOINT.json`, `AGENTS.md`, `BLUEPRINT.md`, the recovery ADR, `CURRENT_MILESTONE.md`, or `CURRENT_STATE.md`.

After the canonical recovery sequence establishes that supervised production is the authorized active seam, the session may inspect durable `JOBS`, `APPLICATIONS`, and `LOG` state and continue only the exact action authorized by the recovered checkpoint. Repository and durable operating records outrank chat history.

Suggested shorthand may reference the canonical recovery order, but must never restate a partial or different order.

## 14. Exact next allowed implementation seam

After this doctrine-only contract is independently reviewed and accepted, the next bounded implementation candidate is:

`SUPERVISED_PRODUCTION_V1_SLICE_1_GMAIL_TO_SHEET`

Scope: Gmail CareerOS alert ingestion -> normalization -> exact-role dedupe -> `JOBS` Sheet persistence + `LOG` run records.

Explicitly out of scope for Slice 1: Match Truth mutation, package generation, Vercel UI, scheduling, supplemental Scout vendors, browser automation, auto-submit, and new database infrastructure.

Acceptance of this doctrine contract does **not** authorize Slice 1 implementation. Slice 1 remains blocked until the post-merge continuity sync is complete and a separate allowed-paths mutation contract is authored, independently reviewed as required, and explicitly authorized by Bora.
## 15. Post-merge continuity sync

Merging this doctrine contract is not sufficient to authorize Slice 1. After Bora accepts the merged contract, a separate bounded governance-sync milestone must update the repository continuity pointers/checkpoint surfaces to reference the accepted supervised-production contract, the exact merged SHA, and the exact next allowed action.

Until that governance sync passes its own deterministic state checks, a new chat must treat Slice 1 as not yet authorized even if this document exists on canonical.

This prevents the recurring failure mode where durable doctrine is correct but `CURRENT_EXECUTION_CHECKPOINT.json`, current-state prose, or other boot pointers lag behind and cause a fresh agent to reconstruct stale operating state from chat.
