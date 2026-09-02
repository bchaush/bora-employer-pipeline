Status: IMPLEMENTATION_AUTHORIZED
Active task:
DOMAIN_QUALIFIED_EXPERIENCE_DURATION_UNKNOWN_V1
Canonical baseline:
dee032295cdfb95c79063c4179a2eb0b0a547c29

Selection provenance:
ChatGPT Work/Bora selected this milestone only after
POST_CLOSURE_REAL_JOB_SYSTEM_BOTTLENECK_AUDIT_V1 (read-only) reproduced the
same epistemic hard-blocker defect on two independent real MBTA controls,
and DOMAIN_QUALIFIED_EXPERIENCE_DURATION_SEMANTIC_SCOPE_V1 (read-only)
designed a narrow, bounded correction architecture for it. No milestone
was preselected before that audit chain.

Locked root cause:
REQ_D_SYS_ANALYSIS_EXP and REQ_E_SYS_ANALYSIS_EXP (MBTA direct and
contractor real fixtures) are both ENTRY_QUALIFICATION, MANDATORY, HIGH
relevance, domain="System Analysis", technology=[], experience_level="3
years". Their text requires three years of experience in system
analysis, with enterprise-application activities described under that
umbrella. The generic experience-range evaluator correctly excludes them
because they are domain-qualified; infer_requirement_capabilities()
returns empty; the ordinary matcher therefore falls through to NONE;
NONE becomes a hard blocker; neither domain support nor duration was
actually evaluated.

Correct current epistemic state:
DOMAIN_SUPPORT_STATE = UNKNOWN
DURATION_STATE = UNKNOWN
WHOLE_REQUIREMENT_RESULT = UNKNOWN

Locked routing contract:
A requirement may enter the new domain-qualified-duration evaluator ONLY
when ALL are true:
1. structured domain is a non-empty string;
2. structured technology is empty;
3. the existing, UNMODIFIED infer_requirement_capabilities() returns no
   capabilities for the requirement;
4. the raw requirement text matches a narrowly bounded numeric
   domain-experience-duration grammar such as:
   "N years of experience in <domain phrase>"
   or equivalent explicitly enumerated variants.

Do NOT route based on domain alone.
Do NOT route based on the words "years" or "experience" alone.
Do NOT route technology-qualified duration requirements.
Do NOT route any requirement with non-empty inferred capabilities.

This deliberately excludes: SAP FI/CO duration requirements; Salesforce
duration requirements; UAT requirements already recognized by the
matcher; other named-platform NONE_TRAPS cases; "2 years of experience
with Python" or analogous technology-qualified rows; generic domain-free
"0-2 years of work experience", which remains owned by
experience_range.py.

Locked result semantics:
For V1, every requirement that safely enters this evaluator returns
result = UNKNOWN, because no recognized capability comparison was
performed and no canonical candidate years-of-experience computation
exists. It must never return NONE, PARTIAL, SUPPORTED, or STRONG. This
V1 does NOT attempt human-level adjacent-capability reasoning. UNKNOWN
means "the system has not established whether the candidate satisfies
this domain-qualified duration requirement." It does NOT mean "the
candidate lacks the domain capability."

Locked implementation shape:
Preferred architecture: a new narrow domain-qualified-duration
evaluator/helper; routing from job_analysis.py alongside the existing
generic experience-range path.

Expected implementation surface should remain approximately:
- new src/domain_qualified_duration.py
- src/job_analysis.py
- focused tests / necessary regression tests

Must remain unchanged unless a newly reproduced necessity is reported
and approved before editing:
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
- golden expected results unless a genuine existing expectation is
  proven stale and separately adjudicated

Locked counterfactual (expected real-control effect):
REQ_D_SYS_ANALYSIS_EXP: NONE -> UNKNOWN; hard blocker -> non-blocker.
REQ_E_SYS_ANALYSIS_EXP: NONE -> UNKNOWN; hard blocker -> non-blocker.
MBTA Direct: REJECT remains REJECT because REQ_D_DEGREE remains a
blocker.
MBTA Contractor: REJECT remains REJECT because REQ_E_DEGREE remains a
blocker.
qualification_gaps: remove fabricated unsupported-mandatory entries for
these system-analysis duration rows.
qualification_unknowns: add truthful UNKNOWN entries for these rows.
No APPLY-like decision is expected from this milestone.

Explicit non-goals:
Do not: compute Bora's years of experience; approve any Claim; add
system-analysis capability mappings; wire WW/MM/TELUS Claims; change
source-semantic-role classification; change posting-state semantics;
change Application Gate; change immigration/work-authorization behavior;
perform a global NONE-vs-UNKNOWN rewrite; weaken named-platform
NONE_TRAPS; fix technology-qualified duration requirements; redesign
qualification branches; redesign duration aggregation.

Required workflow:
Claude implements test-first only after this pointer update is
reviewed, committed, and pushed. Cursor must independently
adversarially review the complete uncommitted implementation diff
before implementation commit/push.

Locked conclusions (carried forward, not reopened):

Task: ATOMINVEST_REJECT_CAUSALITY_AND_APPLICATION_ACTIONABILITY_AUDIT_V1
Status: COMPLETE_ADJUDICATED
Baseline: e3af81a7ce6bd149eb2d0415bc7d1d217c600f61
Adjudication result:
- Atominvest human status remains HOLD.
- Responsibility-versus-entry classification is the highest-priority
  causal defect (RESPONSIBILITY_CLASSIFICATION_FIX_JUSTIFIED) --
  addressed by SOURCE_SEMANTIC_ROLE_QUALIFICATION_VIEW_V1, now CLOSED.
- NONE-vs-UNKNOWN remains a separate, secondary, not-yet-globally-fixed
  defect (now partially and narrowly addressed for domain-qualified
  duration requirements by this active milestone; still not a global
  rewrite).
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
fabrication on REQ_D_SYS_ANALYSIS_EXP/REQ_E_SYS_ANALYSIS_EXP is the
highest-earned next bottleneck (high generalization risk, real if
non-decision-flipping current impact); no other reproduced defect
outranked it.

Task: DOMAIN_QUALIFIED_EXPERIENCE_DURATION_SEMANTIC_SCOPE_V1
Status: COMPLETE_ADJUDICATED (read-only)
Baseline: dee032295cdfb95c79063c4179a2eb0b0a547c29
Adjudication result: IMPLEMENTATION_MILESTONE_JUSTIFIED; produced the
locked routing contract and result semantics recorded above.

Historical anchors:
Governance role-sync commit: 4b55448a8d189fe29344aded3d883a2fb35e9b5a
Prior baseline-clarification commit: 445899ccbd934360ee0a240b7b7bd1a4239cf0df

The stored SHAs are historical anchors, not an assertion that any of
them must equal the future current HEAD.
