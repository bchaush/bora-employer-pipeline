Status: IMPLEMENTATION_AUTHORIZED
Active task:
SOURCE_SEMANTIC_ROLE_QUALIFICATION_VIEW_V1
Canonical baseline:
e3af81a7ce6bd149eb2d0415bc7d1d217c600f61

Purpose:
1. Persist an auditable source-semantic-role classification and its
   provenance.
2. Derive a qualification-eligible view so ROLE_RESPONSIBILITY rows
   cannot independently create qualification hard blockers.
3. Separate qualification gaps/unknowns from responsibility
   observations.
4. Preserve all responsibility rows and their existing match/evidence
   information without labeling evidence absence as a candidate
   deficiency.

Locked semantic roles:
- ENTRY_QUALIFICATION
- ROLE_RESPONSIBILITY
- APPLICATION_OR_LEGAL_GATE
- AMBIGUOUS

Locked independent dimensions:
- IMPORTANCE remains separate (MANDATORY/PREFERRED/UNCLEAR is not a
  source-semantic-role value and is never redefined by this milestone).
- QUALIFICATION_GATE (YES/NO/AMBIGUOUS) is derived, never independently
  editable.
- Fit and tailoring uses (FIT_SIGNAL, TAILORING_SIGNAL) remain separate
  downstream concepts, also derived, never independently editable.

Locked ambiguity behavior:
- AMBIGUOUS cannot independently hard-block.
- AMBIGUOUS remains visibly unresolved (never silently resolved either
  direction).
- AMBIGUOUS requires human adjudication (sets a human-review-required
  flag; surfaces in interview-preparation-signal output).
- It must not silently become ENTRY_QUALIFICATION or fit-only.
- human_review_required is derived deterministically from
  SOURCE_SEMANTIC_ROLE=AMBIGUOUS or from a classified override
  condition; it is never independently persisted or hand-editable.

Locked provenance requirements (per requirement row):
- preserve raw source_text;
- preserve raw source_location;
- record source_semantic_role;
- record classification basis;
- record explicit-prerequisite-language finding;
- record duplication-under-qualification finding;
- preserve any source contradiction;
- make classifier/version lineage auditable.

Locked output semantics:
- qualification_gaps: qualification-gate-eligible NONE rows only;
- qualification_unknowns: qualification-gate-eligible UNKNOWN rows only;
- responsibility_observations: all ROLE_RESPONSIBILITY rows with current
  match result and cited evidence information, without
  qualification-deficiency language;
- responsibility_evidence_unknowns: responsibility rows without
  established adjacent evidence; never labeled as proven candidate
  weakness or "development need."

Implementation exclusions (this milestone must NOT):
- approve any Claim or Evidence;
- No new Claim-to-capability mapping is authorized in this milestone.
- promote any résumé fact;
- implement automated résumé tailoring;
- perform any immigration/work-authorization inference;
- perform a global NONE-vs-UNKNOWN correction (remains a separate,
  secondary, not-yet-authorized defect);
- apply an Atominvest-fixture-only patch;
- delete or hide any responsibility row;
- adopt an "all Responsibility sections are non-gating" shortcut (source
  role must be classified per row, not assumed from section heading
  alone -- explicit-prerequisite-language and duplication findings can
  override the section-heading default in either direction).

Tailoring safety (recorded for future work, not this milestone):
A future TAILORING_SIGNAL consumer may use only candidate-facing-safe,
human-approved Claims/modules while respecting forbidden_contexts and
limitations. Raw adjacency alone can never authorize résumé content.

Required workflow:
Claude implements test-first only after this pointer update is
reviewed, committed, and pushed. ChatGPT adjudicates the implementation
semantics. Cursor adversarially reviews the complete uncommitted
implementation diff before commit/push.

Locked conclusions (carried forward, not reopened):

Task: ATOMINVEST_REJECT_CAUSALITY_AND_APPLICATION_ACTIONABILITY_AUDIT_V1
Status: COMPLETE_ADJUDICATED
Baseline: e3af81a7ce6bd149eb2d0415bc7d1d217c600f61
Adjudication result:
- Atominvest human status remains HOLD.
- Responsibility-versus-entry classification is the highest-priority
  causal defect (RESPONSIBILITY_CLASSIFICATION_FIX_JUSTIFIED).
- Two of Atominvest's four hard blockers
  (REQ_A_CONFIG_IMPLEMENTATION, REQ_A_QA_TROUBLESHOOTING) are
  responsibility-sourced false qualification gates.
- The defect recurs beyond Atominvest (confirmed live in
  CASE_C_MIT_LL_BUSINESS_SYSTEMS_ANALYST's REQ_C_REGRESSION_TESTING;
  structurally present in JOB_FIXTURE_BSA_001's REQ_BSA_010 though
  currently non-blocking there).
- NONE-vs-UNKNOWN remains a separate, secondary, not-yet-globally-fixed
  defect.
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

Historical anchors:
Governance role-sync commit: 4b55448a8d189fe29344aded3d883a2fb35e9b5a
Prior baseline-clarification commit: 445899ccbd934360ee0a240b7b7bd1a4239cf0df

The stored SHAs are historical anchors, not an assertion that any of
them must equal the future current HEAD.
