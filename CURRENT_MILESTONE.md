Status: CLOSED
Closed task:
SOURCE_SEMANTIC_ROLE_QUALIFICATION_VIEW_V1
Canonical implementation SHA:
ddc29b9525acee7de141cd9551d9f3b39665a718
Historical implementation baseline (not current HEAD):
e3af81a7ce6bd149eb2d0415bc7d1d217c600f61

Purpose (achieved):
1. Persist an auditable source-semantic-role classification and its
   provenance.
2. Derive a qualification-eligible view so ROLE_RESPONSIBILITY rows
   cannot independently create qualification hard blockers.
3. Separate qualification gaps/unknowns from responsibility
   observations.
4. Preserve all responsibility rows and their existing match/evidence
   information without labeling evidence absence as a candidate
   deficiency.

Accepted final implementation semantics:
- Four source semantic roles: ENTRY_QUALIFICATION, ROLE_RESPONSIBILITY,
  APPLICATION_OR_LEGAL_GATE, AMBIGUOUS.
- IMPORTANCE (MANDATORY/PREFERRED/UNCLEAR) remains an independent
  dimension, never redefined by source_semantic_role.
- QUALIFICATION_GATE (YES/NO/AMBIGUOUS) is derived, never independently
  persisted or hand-editable.
- Fit and tailoring uses (FIT_SIGNAL, TAILORING_SIGNAL) remain separate
  downstream concepts, also derived, never independently editable.
- ROLE_RESPONSIBILITY cannot independently create a qualification hard
  blocker.
- AMBIGUOUS cannot independently hard-block and always requires human
  review (human_review_required derived true).
- Responsibility rows remain fully visible (responsibility_observations),
  never deleted or hidden.
- Responsibility evidence absence is reported in explicitly
  matcher-bounded, non-deficiency language ("no established current
  approved match for this responsibility") -- never framed as a
  qualification gap, candidate weakness, or development need.
- A canonical artifact entering ordinary analyze_job() production routing
  fails closed (SOURCE_SEMANTIC_ROLE_NOT_MIGRATED, no consequential
  decision produced) on any unmigrated (missing/null/invalid) row.
- A low-level caller that bypasses canonical ingestion still degrades
  safely: missing/invalid role -> AMBIGUOUS, non-blocking,
  human_review_required -- never a silent YES.
- Persisted role/provenance is authoritative at runtime; ordinary
  analysis only ever consumes it, never silently recomputes or
  overwrites a valid persisted classification. Classification itself
  runs only at extraction/ingestion/backfill time
  (requirement_source_role.classify_source_semantic_roles(), invoked by
  scripts/generate_job_analysis_golden_fixtures.py for the golden corpus
  and by the equivalent one-time backfill for the real fixture corpus).
- No Claim/Evidence approval or résumé-fact promotion occurred at any
  point in this milestone.

Final migration/reproducibility facts:
- 47/47 real requirement rows (5 fixtures: CASE_A_ATOMINVEST_IMPLEMENTATION_ANALYST,
  CASE_C_MIT_LL_BUSINESS_SYSTEMS_ANALYST, CASE_D_MBTA_DIRECT_APPLICATION_ANALYST,
  CASE_E_MBTA_CONTRACTOR_APPLICATION_ANALYST, JOB_FIXTURE_BSA_001) migrated
  with zero final-classifier recompute drift.
- 60/60 golden requirement rows (15 fixtures under golden-tests/job_analysis/)
  migrated with zero final-classifier recompute drift.
- Generator reproducibility: 0/45 byte drift across all 15 golden
  fixtures' jd.txt/structured_extraction.json/expected.json.
- Golden role distribution: 57 ENTRY_QUALIFICATION / 3 AMBIGUOUS
  (GT_VAGUE_JD's three UNCLEAR/LOW "About you" noise rows).

Accepted causal results:
- Atominvest human status remains HOLD.
- Atominvest engine result remains REJECT, with only REQ_A_DEGREE and
  REQ_A_EXCEL_DATA as hard blockers.
- REQ_A_CONFIG_IMPLEMENTATION and REQ_A_QA_TROUBLESHOOTING are preserved
  responsibility observations and no longer independently create
  qualification blockers.
- MIT LL's REQ_C_REGRESSION_TESTING no longer creates a false
  qualification blocker; genuine citizenship/clearance, degree/experience,
  and SAP blockers remain intact.
- JOB_FIXTURE_BSA_001 canonical routing remains WATCH.
- REQ_BSA_007 and REQ_BSA_008 are correctly surfaced as preferred
  qualification gaps (Google Cloud and Enterprise QA "Also desired" rows).
- REQ_BSA_010 remains STRONG.
- MBTA direct/contractor blocker behavior remains unchanged.
- GT_PROCESS_MAP_P2 remains APPLY with REQ_P2_MAP STRONG + provenance.

Tailoring safety (carried forward, not reopened):
A future TAILORING_SIGNAL consumer may use only candidate-facing-safe,
human-approved Claims/modules while respecting forbidden_contexts and
limitations. Raw adjacency alone can never authorize résumé content.

Carried-forward exclusions/conclusions (not reopened):
- NONE-vs-UNKNOWN remains a separate, secondary defect -- not globally
  fixed by this milestone.
- Do not wire approved MM/TELUS Claims merely because they are approved
  (APPROVED_CLAIM_CAPABILITY_MAPPING_CAUSALITY_AUDIT_V1 adjudication
  stands).
- No new Claim-to-capability mapping was authorized.
- No immigration/work-authorization inference was added.
- "Gain exposure to..." under a Requirements heading resolving
  ENTRY_QUALIFICATION (no future-tense marker present) is an accepted
  current classifier edge behavior, not a new open milestone.

NO NEW ACTIVE IMPLEMENTATION MILESTONE IS CURRENTLY SELECTED.
The next action is a truth-first, read-only real-job/system bottleneck
audit and prioritization by ChatGPT Work/Bora -- not preselected here.

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

Task: SOURCE_SEMANTIC_ROLE_QUALIFICATION_VIEW_V1
Status: CLOSED
Implementation SHA: ddc29b9525acee7de141cd9551d9f3b39665a718
Historical implementation baseline: e3af81a7ce6bd149eb2d0415bc7d1d217c600f61

Historical anchors:
Governance role-sync commit: 4b55448a8d189fe29344aded3d883a2fb35e9b5a
Prior baseline-clarification commit: 445899ccbd934360ee0a240b7b7bd1a4239cf0df

The stored SHAs are historical anchors, not an assertion that any of
them must equal the future current HEAD.
