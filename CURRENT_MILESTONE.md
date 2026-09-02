Status: IMPLEMENTATION_AUTHORIZED
Active task:
ALTERNATIVE_QUALIFICATION_BRANCH_REPRESENTATION_V1
Architecture baseline (commit containing the canonical ADR):
26f799075bd44c6fad729b4e14043c3eec2ab31c
Canonical ADR:
docs/decisions/ADR-ALTERNATIVE-QUALIFICATION-BRANCH-REPRESENTATION-V1.md
Current HEAD at authorization:
26f799075bd44c6fad729b4e14043c3eec2ab31c

Selection provenance:
ChatGPT Work/Bora selected this milestone only after a chain of read-only
audits (LIVE_EMPLOYER_TRUTH_AND_CANDIDATE_APPLICATION_GATE_AUDIT_V1,
ALTERNATIVE_QUALIFICATION_BRANCH_REPRESENTATION_CAUSALITY_V1) reproduced a
real employer-truth representation defect on two live, currently-open real
MBTA controls, and four subsequent architecture-decision passes
(ALTERNATIVE_QUALIFICATION_BRANCH_ARCHITECTURE_DECISION_V1,
NEGATIVE_SUFFICIENCY_AND_SUPPORT_SEMANTICS_FINAL_AUDIT,
MATCH_TRUTH_PROVENANCE_FINAL_CORRECTION) converged on Option B, recorded
and Cursor-reviewed (SAFE_TO_COMMIT_ADR) as the canonical ADR above. This
milestone exists to implement that already-approved ADR faithfully. It
must NOT redesign the architecture.

Locked root cause (the ADR-approved architecture addresses):
Two live, currently-open real MBTA postings (CASE_D Job #26-20235, CASE_E
Job #20260804A-ITS87) state that ANY of several education/experience
branches satisfies one mandatory employer gate (e.g. HS/GED + 10 years
system-analysis experience, OR Associate's + 6 years, OR Bachelor's + 3
years, OR Master's in a related subject + 1 year). Current Requirement
records are flat, atomic, single-condition rows; structured_extraction.json
for both fixtures represents only the flat Bachelor's-branch condition.
job_decision.py's hard-blocker loop treats each mandatory HIGH NONE row
independently, so naively representing every branch as its own mandatory
row would fabricate false blockers, and the schema has no alternative/OR-
grouping concept at all.

Locked implementation contract (all 20 items, from the canonical ADR --
implementation must preserve every one; do not reopen without a separately
approved architecture decision):
1. Requirement rows remain atomic.
2. Employer qualification composition is represented separately through
   qualification_gates[] in structured_extraction.json.
3. Qualification-gate records contain Employer truth only -- no candidate
   Evidence/Claim/match-specific state.
4. Gate logic_expression leaves reference Requirement IDs only.
5. Raw employer-source (jd.txt) traceability is deterministic and
   fail-closed (exact-substring-after-whitespace-normalization; no
   semantic/embedding/model-judgment traceability).
6. EvidenceMatch gains one new, additive, machine-readable evaluation_path
   field (Match truth); explanation text never controls logic.
7. V1 qualification support states: SUPPORTED / BLOCKED_BY_MATCHING_POLICY
   / UNRESOLVED -- never a claim about candidate factual reality.
8. Conservative V1 leaf policy:
   STRONG/SUPPORTED -> SUPPORTED
   PARTIAL/UNKNOWN -> UNRESOLVED
   NONE + NONE_TRAP -> BLOCKED_BY_MATCHING_POLICY
   NONE + NO_CAPABILITY_OVERLAP -> UNRESOLVED
   NONE + NO_CAPABILITY_COVERAGE -> UNRESOLVED
   missing/unrecognized evaluation_path -> UNRESOLVED
9. application_logic.evaluate_expression() is reused only as an unmodified,
   leaf-value-agnostic tree walker unless a concrete implementation
   contradiction is proven and separately reported.
10. Gate-referenced Requirement rows are not independently double-counted
    by the existing ordinary hard-blocker loop.
11. Gate SUPPORTED suppresses failed-alternative-branch gap/unknown noise
    (no gap entries for branches the employer did not require once one
    branch clears).
12. Application Gate remains completely independent:
    qualification_gate_result != application_question_answer, always.
13. Ungrouped Requirement behavior remains byte-unchanged in this
    milestone (the documented NO_CAPABILITY_OVERLAP ungrouped-vs-gated
    asymmetry is deliberate, not silently fixed).
14. CASE_E raw jd.txt restoration (missing Substitutions section and full
    supplemental questionnaire) occurs before any structured
    qualification-gate authoring for CASE_E.
15. No certification-branch arithmetic invention (the employer source does
    not state it; record via unmodeled_branches_note only).
16. No Master's/Associate's base-credential capability-pattern expansion in
    this milestone (explicitly deferred; those branch legs remain
    UNRESOLVED under current capability coverage).
17. No technology-qualified-duration fix in this milestone (separate,
    already-identified, still-open matcher gap).
18. No global NONE-vs-UNKNOWN remediation (remains separate, open, tracked
    in CURRENT_STATE.md).
19. No Application Gate capture milestone bundled (real ApplicationAttempt/
    ApplicationQuestion authoring for either MBTA role stays deferred).
20. No package-generation work bundled.

Expected bounded implementation surface (minimum necessary subset only;
any need outside this surface: STOP AND REPORT, do not expand scope
automatically):
- schemas/qualification_gate.schema.json (new)
- schemas/evidence_match.schema.json (additive: evaluation_path)
- schemas/job_analysis_result.schema.json (additive: optional gate-result
  output fields)
- src/requirement_match.py (additive: evaluation_path population for the
  five paths it produces)
- src/experience_range.py (additive: evaluation_path population)
- src/domain_qualified_duration.py (additive: evaluation_path population)
- src/job_analysis.py (additive: qualification_gates[] routing/wiring)
- src/requirement_normalize.py (additive: qualification_gates[] pass-
  through, as needed)
- src/job_decision.py (additive: gate-membership exclusion in the existing
  hard-blocker loop)
- one new, bounded qualification-gate evaluator/module
- CASE_D structured_extraction.json (new branch Requirement rows + one
  gate record)
- CASE_E jd.txt restoration first, then its structured_extraction.json
- focused tests required by the ADR

Must remain unchanged unless a newly reproduced necessity is reported and
approved before editing:
- src/requirement_source_role.py
- src/application_gate.py
- schemas/requirement.schema.json
- src/application_logic.py (reused unmodified per locked-contract item 9)
- all 15 golden fixtures
- Atominvest and MIT LL real fixtures
- Claims
- Evidence
- Experiences
- résumé
- immigration/work-authorization logic
- posting-state logic
- BLUEPRINT.md, AGENTS.md, CLAUDE.md

Required workflow:
Test-first. Before production edits, add/reproduce focused failing tests
for the real defect and the locked semantics above, covering at minimum:
ALL_OF/ANY_OF three-valued behavior; NONE_TRAP -> BLOCKED_BY_MATCHING_POLICY;
NO_CAPABILITY_OVERLAP -> UNRESOLVED inside gates; NO_CAPABILITY_COVERAGE ->
UNRESOLVED; missing evaluation_path -> UNRESOLVED; partial semantic
recognition cannot create gate FALSE; the static gate invariant across
Claim-state changes; raw-source traceability fail-closed; missing
Requirement-reference fail-closed; the CASE_D four-branch representation;
gate SUPPORTED suppressing alternative gap/unknown noise; multiple
independent gates not erasing one another; CASE_E qualification/
application-state separation; and the full existing regression/golden
suite. Cursor must independently adversarially review the complete
uncommitted implementation diff before implementation commit/push.

NO IMPLEMENTATION HAS OCCURRED YET. This is a pointer/authorization state
only.

Locked conclusions (carried forward, not reopened):

Task: ATOMINVEST_REJECT_CAUSALITY_AND_APPLICATION_ACTIONABILITY_AUDIT_V1
Status: COMPLETE_ADJUDICATED
Baseline: e3af81a7ce6bd149eb2d0415bc7d1d217c600f61
Adjudication result:
- Atominvest human status remains HOLD.
- Responsibility-versus-entry classification is the highest-priority
  causal defect (RESPONSIBILITY_CLASSIFICATION_FIX_JUSTIFIED) --
  addressed by SOURCE_SEMANTIC_ROLE_QUALIFICATION_VIEW_V1, now CLOSED.
- NONE-vs-UNKNOWN remains a separate, secondary defect (now narrowly
  addressed for domain-qualified duration requirements by
  DOMAIN_QUALIFIED_EXPERIENCE_DURATION_UNKNOWN_V1, now CLOSED; still not
  a global rewrite).
- No Claim approval was authorized at any point in this audit chain.
- Prior MM/TELUS capability-mapping and accreditation-qualifier
  conclusions remain closed, not reopened.

Task: APPROVED_CLAIM_CAPABILITY_MAPPING_CAUSALITY_AUDIT_V1
Status: COMPLETE_ADJUDICATED
Baseline: 01142d19fa80400ce94db5f5fa2e85ea01f23e1c
Adjudication result: Do not wire MM/TELUS Claims yet, merely because
they are approved.

Task: ACCREDITED_INSTITUTION_QUALIFIER_SEMANTICS_V1
Status: CLOSED
Implementation SHA: 9950c7c3eacdebf741c2e6a990a5b391adba3c44
State-closure SHA: bf1f395ee1d79dec04f7ac39e3d972e48dcbe304

Task: SOURCE_SEMANTIC_ROLE_QUALIFICATION_VIEW_V1
Status: CLOSED
Implementation SHA: ddc29b9525acee7de141cd9551d9f3b39665a718
State-closure SHA: dee032295cdfb95c79063c4179a2eb0b0a547c29
Historical implementation baseline: e3af81a7ce6bd149eb2d0415bc7d1d217c600f61

Task: POST_CLOSURE_REAL_JOB_SYSTEM_BOTTLENECK_AUDIT_V1
Status: COMPLETE_ADJUDICATED (read-only)
Baseline: dee032295cdfb95c79063c4179a2eb0b0a547c29
Adjudication result: domain-qualified experience-duration NONE
fabrication on REQ_D_SYS_ANALYSIS_EXP/REQ_E_SYS_ANALYSIS_EXP was the
highest-earned next bottleneck (high generalization risk, real if
non-decision-flipping current impact); no other reproduced defect
outranked it -- addressed by DOMAIN_QUALIFIED_EXPERIENCE_DURATION_
UNKNOWN_V1, now CLOSED.

Task: DOMAIN_QUALIFIED_EXPERIENCE_DURATION_SEMANTIC_SCOPE_V1
Status: COMPLETE_ADJUDICATED (read-only)
Baseline: dee032295cdfb95c79063c4179a2eb0b0a547c29
Adjudication result: IMPLEMENTATION_MILESTONE_JUSTIFIED; produced the
locked routing contract and result semantics implemented and closed by
DOMAIN_QUALIFIED_EXPERIENCE_DURATION_UNKNOWN_V1 above.

Task: DOMAIN_QUALIFIED_EXPERIENCE_DURATION_UNKNOWN_V1
Status: CLOSED
Implementation SHA: a4e849fe2629f4f25293e685776f49a1b1eddaa7
Authorization/pointer SHA: 544125f2a6fbf466e40d4292313b05b974ada3ce
Selection baseline: dee032295cdfb95c79063c4179a2eb0b0a547c29

Task: POST_V3_3_END_TO_END_REAL_WORLD_BOTTLENECK_AUDIT_V1
Status: COMPLETE_ADJUDICATED (read-only)
Baseline: 8ce2538735ff11571d088702fff42d8d5085ec7d
Adjudication result: NO_IMPLEMENTATION_MILESTONE_JUSTIFIED at that time --
highest-leverage findings (undergraduate degree evidence, Excel evidence)
were candidate-truth/human-approval actions outside this system's
authority, not code defects.

Task: LIVE_EMPLOYER_TRUTH_AND_CANDIDATE_APPLICATION_GATE_AUDIT_V1
Status: COMPLETE_ADJUDICATED (read-only)
Baseline: 8ce2538735ff11571d088702fff42d8d5085ec7d
Adjudication result: live re-fetch of both real, currently-open MBTA
postings (CASE_D Job #26-20235, CASE_E Job #20260804A-ITS87) found employer
alternative education/experience qualification branches (HS/Associate's/
Bachelor's/Master's-plus-experience) genuinely present on both live
postings and materially under-represented in the frozen fixtures; also
corrected two documentation-drift findings (Q-2 Excel qualifier overmatch
already fixed in code; CANDIDATE_SOURCE_INGESTION_V1 push-status label
stale) and adjudicated the UNWE Academic Reference as establishing identity/
program only, not degree conferral. Highest-leverage next action identified
as G (alternative-branch representation), not a candidate-evidence action.

Task: ALTERNATIVE_QUALIFICATION_BRANCH_REPRESENTATION_CAUSALITY_V1
Status: COMPLETE_ADJUDICATED (read-only)
Baseline: 8ce2538735ff11571d088702fff42d8d5085ec7d
Adjudication result: ARCHITECTURE_DECISION_REQUIRED -- flat, atomic
Requirement rows cannot safely represent employer OR-branch qualification
logic; naive representation would create false blockers.

Task: ALTERNATIVE_QUALIFICATION_BRANCH_ARCHITECTURE_DECISION_V1
Status: COMPLETE_ADJUDICATED (read-only, four converging passes)
Baseline: 8ce2538735ff11571d088702fff42d8d5085ec7d
Adjudication result: Option B (separate qualification_gate employer-truth
record, additive in structured_extraction.json, Requirement rows remain
atomic) selected over Option A (fields on Requirement rows); negative-
sufficiency semantics converged, across NEGATIVE_SUFFICIENCY_AND_SUPPORT_
SEMANTICS_FINAL_AUDIT and MATCH_TRUTH_PROVENANCE_FINAL_CORRECTION, on a
conservative, Match-truth-only, evaluation_path-keyed policy (SUPPORTED /
BLOCKED_BY_MATCHING_POLICY / UNRESOLVED) that never authors a candidate-
specific judgment inside the employer-truth gate record --
ARCHITECTURE_DECISION_READY_FOR_BORA_APPROVAL. Recorded as the canonical
ADR: docs/decisions/ADR-ALTERNATIVE-QUALIFICATION-BRANCH-REPRESENTATION-V1.md
(commit 26f799075bd44c6fad729b4e14043c3eec2ab31c; Cursor review:
SAFE_TO_COMMIT_ADR, no BLOCKING/HIGH/MEDIUM findings).

Historical anchors:
Governance role-sync commit: 4b55448a8d189fe29344aded3d883a2fb35e9b5a
Prior baseline-clarification commit: 445899ccbd934360ee0a240b7b7bd1a4239cf0df

The stored SHAs are historical anchors, not an assertion that any of
them must equal the future current HEAD.
