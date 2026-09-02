Status: CLOSED
Closed task:
DOMAIN_QUALIFIED_EXPERIENCE_DURATION_UNKNOWN_V1
Canonical implementation SHA:
a4e849fe2629f4f25293e685776f49a1b1eddaa7
Authorization/pointer SHA (not current HEAD):
544125f2a6fbf466e40d4292313b05b974ada3ce
Selection baseline:
dee032295cdfb95c79063c4179a2eb0b0a547c29

Selection provenance:
ChatGPT Work/Bora selected this milestone only after
POST_CLOSURE_REAL_JOB_SYSTEM_BOTTLENECK_AUDIT_V1 (read-only) reproduced the
same epistemic hard-blocker defect on two independent real MBTA controls,
and DOMAIN_QUALIFIED_EXPERIENCE_DURATION_SEMANTIC_SCOPE_V1 (read-only)
designed a narrow, bounded correction architecture for it. No milestone
was preselected before that audit chain.

Locked root cause (resolved by this milestone):
REQ_D_SYS_ANALYSIS_EXP and REQ_E_SYS_ANALYSIS_EXP (MBTA direct and
contractor real fixtures) are both ENTRY_QUALIFICATION, MANDATORY, HIGH
relevance, domain="System Analysis", technology=[], experience_level="3
years". Their text requires three years of experience in system
analysis, with enterprise-application activities described under that
umbrella. The generic experience-range evaluator correctly excludes them
because they are domain-qualified; infer_requirement_capabilities()
returns empty; the ordinary matcher therefore fell through to NONE;
NONE became a hard blocker; neither domain support nor duration was
actually evaluated.

Accepted final implementation semantics:
- A requirement enters the new domain-qualified-duration evaluator ONLY
  when ALL are true:
  1. structured domain is a non-empty string;
  2. structured technology is empty;
  3. the existing, UNMODIFIED infer_requirement_capabilities() returns no
     capabilities for the requirement;
  4. the raw requirement text matches a narrowly bounded numeric
     domain-experience-duration grammar such as:
     "N years of experience in <domain phrase>"
     or equivalent explicitly enumerated variants.
- Routed requirements resolve result = UNKNOWN only -- never NONE,
  PARTIAL, SUPPORTED, or STRONG. UNKNOWN means "the system has not
  established whether the candidate satisfies this domain-qualified
  duration requirement." It does NOT mean "the candidate lacks the
  domain capability."
- No candidate years-of-experience computation was added.
- No global NONE-vs-UNKNOWN rewrite was performed.
- Named-platform/capability-backed requirements (SAP FI/CO, Salesforce,
  Workday, UAT, other NONE_TRAPS cases) remain owned by the unmodified
  ordinary matcher -- structurally protected by the empty-inferred-
  capabilities gate, proven in the regression matrix.
- Generic domain-free duration requirements ("0-2 years of work
  experience") remain owned by the unmodified experience_range.py.
- Technology-qualified duration requirements ("2 years of experience
  with Python") remain outside this milestone.

Implementation surface (as built):
- new src/domain_qualified_duration.py
- src/job_analysis.py (added a third requirement-partition branch)
- tests/domain_qualified_experience_duration_unknown_v1_test.py (new,
  test-first, 18 lettered sections)
- 4 pre-existing regression tests corrected for stale CASE_D/E
  hard-blocker-set expectations (accredited_institution_qualifier_
  semantics_v1_test.py, business_rules_technical_requirements_compound_
  completion_v1_test.py, process_mapping_compound_completion_v1_test.py,
  source_semantic_role_qualification_view_v1_test.py)

Unchanged (verified byte-identical / zero diff):
- src/requirement_match.py
- src/experience_range.py
- src/job_decision.py
- src/requirement_source_role.py
- src/requirement_normalize.py
- src/application_gate.py
- schemas
- Claims
- Evidence
- Experiences
- résumé
- immigration/work-authorization logic
- posting-state logic
- golden expected results (no golden fixture contains a domain-qualified-
  duration row)

Accepted real-control results:
- REQ_D_SYS_ANALYSIS_EXP: NONE -> UNKNOWN; hard blocker -> non-blocker.
- REQ_E_SYS_ANALYSIS_EXP: NONE -> UNKNOWN; hard blocker -> non-blocker.
- MBTA Direct: REJECT remains REJECT, blocker set reduced to
  {REQ_D_DEGREE} only.
- MBTA Contractor: REJECT remains REJECT, blocker set reduced to
  {REQ_E_DEGREE} only.
- qualification_gaps: fabricated unsupported-mandatory entries removed
  for both system-analysis duration rows.
- qualification_unknowns: truthful UNKNOWN entries added for both rows.
- No APPLY-like decision was introduced.
- Atominvest unchanged: blockers remain {REQ_A_DEGREE,
  REQ_A_EXCEL_DATA}.
- MIT LL unchanged: citizenship/clearance, degree/experience, and SAP
  blockers remain intact.
- JOB_FIXTURE_BSA_001 (synthetic) unchanged in milestone-relevant
  semantics -- no domain-qualified-duration row exists in it.

Validation performed:
- Cursor final adversarial review: SAFE_TO_COMMIT_AND_PUSH (no BLOCKING/
  HIGH/MEDIUM findings; two LOW documentation/test-wording observations
  only, not remediated in this closure).
- Full non-interactive suite: TOTAL=58 FAILED=0.
- Job Analysis Golden suite: 15/15 PASS.
- Application Gate Golden: 9/9 PASS.
- posting-state wiring tests: PASS.
- git diff --check: clean.
- Implementation commit independently verified on GitHub by ChatGPT
  Work: exactly one commit above the authorization baseline, exactly 7
  files changed, no protected surface changed, no CURRENT_MILESTONE.md /
  CURRENT_STATE.md change in the implementation commit.

Carried-forward exclusions/conclusions (not reopened):
- NONE-vs-UNKNOWN is NOT globally solved -- remains a separate,
  secondary, not-yet-globally-fixed defect, now only narrowly addressed
  for domain-qualified duration requirements.
- Do not wire approved MM/TELUS Claims merely because they are approved
  (APPROVED_CLAIM_CAPABILITY_MAPPING_CAUSALITY_AUDIT_V1 adjudication
  stands).
- No new Claim-to-capability mapping was authorized.
- Immigration/work-authorization logic remains separate and
  conservative -- unchanged.
- SOURCE_SEMANTIC_ROLE_QUALIFICATION_VIEW_V1 remains closed, not
  reopened.
- posting-state/Application Gate semantics remain unchanged.
- No candidate years-of-experience computation exists anywhere in the
  pipeline.
- Technology-qualified duration requirements remain outside this
  milestone.

NO NEW ACTIVE IMPLEMENTATION MILESTONE IS CURRENTLY SELECTED.
The next action is a fresh, truth-first, read-only real-job/system
bottleneck audit and prioritization by ChatGPT Work/Bora -- not
preselected here.

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

Historical anchors:
Governance role-sync commit: 4b55448a8d189fe29344aded3d883a2fb35e9b5a
Prior baseline-clarification commit: 445899ccbd934360ee0a240b7b7bd1a4239cf0df

The stored SHAs are historical anchors, not an assertion that any of
them must equal the future current HEAD.
