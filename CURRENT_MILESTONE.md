Status: CLOSED
Closed task:
REPRODUCIBLE_CONSEQUENTIAL_ASSURANCE_BASELINE_V1
Canonical architecture SHA:
d8826aa368e5dbfafb80531f03913bd43cd00713
Authorization SHA:
4a5ea68736f4c82274283ff154c7e53492320fba
Canonical implementation SHA:
b05c39022f791e3b6ef3f605f535a66620cd7c2a
Canonical ADR:
docs/decisions/ADR-REPRODUCIBLE-CONSEQUENTIAL-ASSURANCE-BASELINE-V1.md

Governance record (not a product implementation milestone; Status above
remains CLOSED; supersedes the historical BRANCH_PROTECTION_UNVERIFIED
text further below in this file for CURRENT branch-enforcement truth --
see chronology):

MAIN_BRANCH_PROTECTION_AND_MERGE_ENFORCEMENT_AUDIT_V1:
MINIMAL_ENFORCEMENT_ARCHITECTURE_JUSTIFIED (read-only audit; independently
verified at its own audit baseline that main was unprotected, required-
status-check enforcement was off, and repository rulesets were empty).

MAIN_BRANCH_PROTECTION_AND_MERGE_ENFORCEMENT_V1:
SETTINGS_APPLIED_AND_VERIFIED.

Chronology (so a fresh reader does not mistake historical assurance text
for current branch-enforcement state):
1. At REPRODUCIBLE_CONSEQUENTIAL_ASSURANCE_BASELINE_V1 closure (recorded
   below in this file), branch enforcement was BRANCH_PROTECTION_UNVERIFIED
   -- true at that time; that milestone verified reproducible assurance
   only, not branch enforcement, and explicitly said so.
2. MAIN_BRANCH_PROTECTION_AND_MERGE_ENFORCEMENT_AUDIT_V1 later superseded
   that epistemic state by directly, independently re-verifying at its own
   audit baseline that no enforcement existed (main unprotected; classic
   required-status-check enforcement off; repository rulesets = []).
3. MAIN_BRANCH_PROTECTION_AND_MERGE_ENFORCEMENT_V1 then created and
   independently verified an active minimal repository ruleset. CURRENT
   state: main is protected by that ruleset, not by classic branch
   protection (classic branch-protection configuration remains a separate,
   still-unused mechanism). GitHub's branch metadata now reports
   protected=true precisely because it is protected by a ruleset.

Live enforced architecture (independently verified against the GitHub API,
not merely trusted from any prior instruction):
- Ruleset name: main-minimal-enforcement, ID 22154366.
- Target: refs/heads/main only.
- Enforcement: active. Bypass actors: none. current_user_can_bypass: never.
- Deletion of main blocked.
- Force pushes / non-fast-forward updates to main blocked.
- Pull request required to change main.
- Required approving reviews: 0.
- CODEOWNERS review not required. Last-push approval not required.
  Review-thread resolution not required.
- Required status check: verify, source/integration GitHub Actions
  (integration_id 15368) -- independently confirmed against a live check
  run on commit 777423af7b190d36763abf605a7c6c3ff6adf5d0.
- strict_required_status_checks_policy: false (loose mode -- the PR head
  must pass verify; it does not need to be updated with the latest main
  first).
- Intentionally NOT required: signed commits, CODEOWNERS, merge queue,
  linear history, GitHub-approving review, strict/up-to-date branch
  requirement -- each evaluated and omitted as unnecessary ceremony for a
  single-collaborator repository, closing no real additional risk.
- Platform-populated field require_extra_approval_for_unattributed_changes
  = true: this governs unattributed Copilot pull requests (a Copilot-
  authored PR not opened on behalf of a person), not commit signatures or
  authorship verification -- it is not an added human review gate.
  Adjudication: ACCEPTABLE_PLATFORM_DEFAULT_NO_SEMANTIC_EFFECT, because
  GitHub's own documentation states this field has no effect when
  required_approving_review_count = 0, which this ruleset sets. Do not
  read this field as an unsigned-commit or authorship-signature
  requirement -- it is not.
- Bora retains final merge action and full settings/admin access
  (independent of the ruleset's own bypass-actor list, which is empty) --
  admin ruleset edit/disable remains available for genuine emergency
  recovery, distinct from any routine merge-time bypass, of which none
  exists.

Fork contributor workflow approval policy:
FORK_PR_CONTRIBUTOR_APPROVAL_POLICY = UNVERIFIED_REPO_SPECIFIC_VALUE.
Not retrievable via REST or GraphQL API in this environment (UI-only
GitHub setting); not modified; not inferred from GitHub's documented
default. This UNKNOWN is orthogonal to the ruleset above: it governs
whether an external contributor's fork PR workflow run may execute at
all, while the ruleset governs whether main may be updated once a PR
exists.

New canonical development workflow (governance/process record, not a
claim about GitHub's own enforcement capability):
bounded branch -> independent Cursor adversarial review against the
consequential uncommitted diff -> authorized commit to the bounded branch
-> push the bounded branch -> pull request -> required GitHub Actions
verify check -> Bora final merge -> main. GitHub mechanically enforces
only: PR association for changes to main, the required verify check and
its bound source (GitHub Actions / integration 15368), no force push, and
no main deletion. GitHub does NOT mechanically verify that Cursor reviewed
the diff, that any agent stayed in authorized scope, or that Bora's
semantic adjudication was correct -- those remain process/governance
invariants, not GitHub-enforced facts.

This governance record does not select, open, or imply a new PRODUCT
implementation milestone. The Status/Closed-task pointer at the top of
this file remains authoritative. PURSUIT_APPROVAL_BOUNDARY_ARCHITECTURE_V1
(recorded separately below) remains ARCHITECTURE ACCEPTED / IMPLEMENTATION
DEFERRED, unaffected by this governance record.

Implementation commit provenance:
Parent authorization SHA 4a5ea68736f4c82274283ff154c7e53492320fba; commit
message "REPRODUCIBLE_CONSEQUENTIAL_ASSURANCE_BASELINE_V1: implement
reproducible assurance baseline"; exactly five implementation files
changed (.github/workflows/assurance-baseline.yml, requirements.in,
requirements-lock.txt, scripts/verify_assurance_baseline.py,
tests/p0_causal_invariants_v1_test.py); no business, production, schema,
Claim, Evidence, Experience, résumé, fixture, or governance file was part
of the implementation commit; independently verified on GitHub by ChatGPT
Work. Preceded by one narrow test-only correction (Cursor M-01: the
original P0 §A only proved gated-leaf exclusion from hard_blockers/
qualification_gaps/qualification_unknowns via a BLOCKED_BY_MATCHING_POLICY
gate scenario, which exits decide_lane_and_decision() before its
high_none-sensitive branch is reached; corrected by adding P0 §A2, an
UNRESOLVED-gate scenario plus an ungrouped control, isolating and proving
the SEPARATE gated-exclusion inside decide_lane_and_decision()'s own
mandatory/preferred list comprehensions) -- second Cursor review verdict
SAFE_TO_COMMIT_AND_PUSH, M-01 CLOSED.

Hosted assurance evidence (independently verified by ChatGPT Work):
- GitHub Actions workflow: Assurance Baseline
- run id: 33678696541
- event: push
- head SHA: b05c39022f791e3b6ef3f605f535a66620cd7c2a
- conclusion: success
- hosted OS: Ubuntu 24.04
- exact Python: 3.14.6
- Phase 1 PASS (compile/syntax)
- Phase 2: 60/60 PASS, all mandatory coverage anchors present
  (application_gate_golden_test.py, posting_state_decision_wiring_v1_test.py,
  alternative_qualification_branch_representation_v1_test.py, all six
  schema smoke tests, p0_causal_invariants_v1_test.py)
- Phase 3 Job Analysis Golden 15/15 PASS
- final canonical verifier result: ALL PHASES PASSED

REPRODUCIBILITY_UNVERIFIED is CLOSED for this canonical assurance
baseline: dependencies reconstructed solely from requirements-lock.txt on
a clean GitHub-hosted runner, Python 3.14.6 successfully resolved via the
full-commit-SHA-pinned actions/setup-python, and the canonical verifier
(python scripts/verify_assurance_baseline.py) reproduced the identical
result set independently proven locally (see the prior turn's byte-for-
byte-identical-output verification). This closure is bounded strictly to
this canonical baseline and this exact hosted environment (Ubuntu 24.04,
Python 3.14.6, this exact dependency lock) -- it does NOT establish that
every OS is verified, that every Python version is supported, that branch
protection exists, or that every future dependency change is automatically
reproducible. Any of those remains a separate, future, evidence-gated
claim.

BRANCH_PROTECTION_UNVERIFIED is preserved unchanged. CI existence and CI
success do not prove merge enforcement; branch-protection state is not
touched by this closure and requires separate evidence to change.

Authorization:
ChatGPT Work/Bora explicitly authorized bounded implementation only within
the canonical ADR's locked surface below; implementation completed exactly
within that surface (items A-D of the locked surface; E and F were not
built -- no concrete need for the optional newline/provenance test was
demonstrated, and F's documentation requirement is satisfied by the ADR
and this closure record, not a new file).

Selection provenance:
ChatGPT Work/Bora selected this milestone after
POST_QUALIFICATION_GATE_REAL_MARKET_BOTTLENECK_AUDIT_V1
(NO_IMPLEMENTATION_MILESTONE_JUSTIFIED),
DEGREE_CREDENTIAL_CANDIDATE_EVIDENCE_ADJUDICATION_V1 (read-only complete),
and SYSTEM_WIDE_TRUST_AND_CONSISTENCY_AUDIT_V1 (read-only complete)
converged on assurance/reproducibility debt -- not a reproduced business-
logic defect -- as the highest-earned next action. The prior architecture-
recording step authored the ADR and pointer faithfully without
implementing it; this step authorizes bounded implementation only. No CI
workflow, dependency file, verification runner, or new test file has been
created yet. No production code, schema, Claim, Evidence, Experience, or
resume has been touched.

Locked terminology: REPRODUCIBILITY_UNVERIFIED (not
REPRODUCIBILITY_BROKEN) -- current development-machine assurance already
passes; a clean GitHub-hosted environment has not yet reconstructed it
from repo-declared dependencies alone and reproduced the same results.

Locked bounded implementation surface (future step only, not yet
authorized):
A. requirements.in / requirements-lock.txt
B. scripts/verify_assurance_baseline.py
C. .github/workflows/assurance-baseline.yml
D. tests/p0_causal_invariants_v1_test.py
E. optional narrow newline/provenance test, only if independently
   necessary and deterministic
F. minimal documentation (canonical verification command,
   analyze_job() outer runtime-envelope contract, milestone/state
   bookkeeping)
Any implementation need outside this surface: STOP AND REPORT before
expanding scope.

Directly observed facts recorded in the ADR: Python 3.14.6 verified
runtime; third-party dependencies are exactly jsonschema and referencing;
no requirements/pyproject/setup.py/Pipfile exists; no .github/workflows
exists; no .gitattributes exists; exactly 59 tests/*_test.py files exist
today.

Explicit exclusions (not reopened by this milestone): Master's credential
capability/matcher; Bachelor's-abbreviation parsing; experience-grammar
broadening; global NONE-vs-UNKNOWN remediation; immigration/work-
authorization decision consumer; legal-employer schema redesign;
E-Verify/sponsorship/I-983 policy; Claim creation/approval/capability
wiring; resume/package generation; follow-up/networking automation;
outcome learning; new pursuit thresholds; role-discovery changes;
employer-market expansion; branch-protection/required-status-check
change; OS test matrix; .gitattributes addition; any packaging-tool
adoption beyond a requirements.in/requirements-lock.txt pair.

Implementation was completed strictly within the locked surface above
(A-F) and the locked implementation principles carried in the canonical
ADR (three-phase canonical verification command; exact Python 3.14.6
runtime truth, independently confirmed available and used on GitHub-hosted
CI; requirements.in/requirements-lock.txt with a complete resolved
transitive environment -- attrs, jsonschema, jsonschema-specifications,
referencing, rpds-py -- no packaging-tool conversion, no hash-enforcement
in V1; immutable full-commit-SHA-pinned GitHub Actions; least privilege;
BRANCH_PROTECTION_UNVERIFIED unchanged; zero new business/Employer/
Candidate/Match/Pursuit/Application semantics). No implementation need
arose outside the locked surface.

NO NEW ACTIVE IMPLEMENTATION MILESTONE IS CURRENTLY SELECTED. The next
action is a fresh, read-only bottleneck/system/real-market prioritization
audit by ChatGPT Work/Bora -- not preselected here. No new business
implementation is authorized by this closure.

Architecture record (not an implementation milestone; Status above
remains CLOSED):

PURSUIT_APPROVAL_BOUNDARY_ARCHITECTURE_V1

Canonical ADR:
docs/decisions/ADR-PURSUIT-APPROVAL-BOUNDARY-V1.md (committed, canonical)

Canonical architecture SHA:
6a6a1da8b3ed2ddf6c6cf86b708d74bf2e0e0644

Architecture adjudication:
ACCEPTED -- IMPLEMENTATION DEFERRED

Preceding audit:
PURSUIT_APPROVAL_BOUNDARY_ARCHITECTURE_AUDIT_V1

Audit result:
ARCHITECTURE_CONTRACT_JUSTIFIED_IMPLEMENTATION_DEFERRED

Second Cursor review:
ACCEPT_ADR_DRAFT (one residual exploratory/consequential-boundary
scoping note adjudicated ACCEPTABLE_ARCHITECTURE_DEFERRAL, not a
contradiction)

Core invariant:
system recommendation (Job.decision / Job.lane, fully system-derived)
must never silently become Bora's human pursuit authorization.

What the ADR locks (semantics only -- no schema, enum, state machine,
persistence, or code authorized): pursuit authorization is an
opportunity-level human-authorization slice within the broader Blueprint
Section 132 Pursuit truth layer, distinct from Employer truth, Candidate
truth, Match truth, posting/actionability truth, Job.application_status,
Job.network_action, ApplicationAttempt, Application Gate, résumé/package
truth, submission authorization, and outcome truth; read-only/
decision-support analysis (e.g. analyze_job re-analysis, exploratory
application-route inspection) may occur before pursuit authorization when
it does not materially advance pursuit; a materially changed opportunity
must not silently inherit stale authorization merely because Job_ID is
unchanged; the exact future representation/enforcement mechanism is
explicitly deferred.

PURSUIT_APPROVAL_BOUNDARY_ARCHITECTURE_AUDIT_V1 did not reproduce a
current downstream pursuit-authorization bypass; no pursuit-production
consumer currently exists; no current production defect is being fixed by
this architecture record; pursuit authorization remains distinct from
final submission authorization.

Implementation status:
NONE AUTHORIZED.

Future activation condition:
a concrete downstream pursuit consumer must be separately earned,
architected, reviewed, and explicitly authorized before this boundary
receives implementation.

Expected first consumer under current product direction:
résumé/package generation -- not locked as the only possible first
consumer.

This architecture record does not select, open, or imply a new active
implementation milestone. The Status/Closed-task pointer at the top of
this file remains authoritative.

Historical closed milestone (superseded as the active pointer by the
above, record preserved below):

Closed task:
ALTERNATIVE_QUALIFICATION_BRANCH_REPRESENTATION_V1
Canonical implementation SHA:
b10a38d09da60ef2e833fcbf718778e4132edabc
Architecture SHA (canonical ADR commit):
26f799075bd44c6fad729b4e14043c3eec2ab31c
Authorization/pointer SHA (not current HEAD):
beff126455ec933cad78dcdb30837148c525fea1
Canonical ADR:
docs/decisions/ADR-ALTERNATIVE-QUALIFICATION-BRANCH-REPRESENTATION-V1.md

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

Locked root cause (resolved by this milestone):
Two live, currently-open real MBTA postings (CASE_D Job #26-20235, CASE_E
Job #20260804A-ITS87) state that alternative education/experience branches
satisfy one mandatory employer gate. Current Requirement records are flat,
atomic, single-condition rows; structured_extraction.json for both
fixtures represented only the flat Bachelor's-branch condition.
job_decision.py's hard-blocker loop treats each mandatory HIGH NONE row
independently, so naively representing every branch as its own mandatory
row would fabricate false blockers, and the schema had no alternative/OR-
grouping concept at all.

Accepted implementation contract (all 20 items, from the canonical ADR --
carried forward as the locked semantics; do not reopen without a
separately approved architecture decision):
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

Implementation surface (as built):
- new schemas/qualification_gate.schema.json
- schemas/evidence_match.schema.json (additive: evaluation_path)
- schemas/job_analysis_result.schema.json (additive: qualification_gate_results)
- new src/qualification_gate.py (leaf policy, tree-walker wrapper reusing
  application_logic.evaluate_expression() unmodified, traceability and
  referential-integrity validators)
- src/requirement_match.py (additive: evaluation_path population for the
  five paths it produces)
- src/experience_range.py / src/domain_qualified_duration.py (additive:
  evaluation_path population)
- src/job_analysis.py (gate reading/validation/evaluation, output wiring)
- src/job_decision.py (gate-membership exclusion in both the hard-blocker
  loop AND the mandatory/preferred counting loop -- the latter a necessary
  addition beyond the ADR's literal text, to prevent a gated row's raw
  NONE from still counting toward none/high_none thresholds)
- fixtures/jobs/CASE_D_MBTA_DIRECT_APPLICATION_ANALYST/structured_extraction.json
  (6 new branch Requirement rows + 1 gate record, GATE_D_DEGREE_EXPERIENCE)
- fixtures/jobs/CASE_E_MBTA_CONTRACTOR_APPLICATION_ANALYST/jd.txt (raw-text
  restoration: Substitutions section + 10-item questionnaire) then its
  structured_extraction.json (4 branch rows + 1 gate record,
  GATE_E_DEGREE_COMPONENT, corrected per below)
- tests/alternative_qualification_branch_representation_v1_test.py (new,
  test-first) + 6 pre-existing tests corrected for stale CASE_D/E
  blocker-set/decision expectations (accredited_institution_qualifier_
  semantics_v1_test.py, business_rules_technical_requirements_compound_
  completion_v1_test.py, domain_qualified_experience_duration_unknown_v1_
  test.py, process_mapping_compound_completion_v1_test.py, process_mapping_
  real_grammar_v1_test.py, source_semantic_role_qualification_view_v1_test.py)
- src/requirement_normalize.py was NOT touched -- proven unnecessary
  (structured_extraction's raw qualification_gates[] is read directly by
  job_analysis.py, needing no normalization pass of its own)

Unchanged (verified byte-identical / zero diff):
- src/requirement_source_role.py
- src/application_gate.py
- schemas/requirement.schema.json
- src/application_logic.py (reused unmodified per locked-contract item 9)
- src/requirement_normalize.py
- all 15 golden fixtures
- Atominvest and MIT LL real fixtures
- Claims, Evidence, Experiences, résumé
- immigration/work-authorization logic, posting-state logic
- BLUEPRINT.md, AGENTS.md, CLAUDE.md

Proposition-specific provenance lesson (BOUNDED CORRECTION, mid-milestone,
found by Cursor's first re-review, BLOCKING): the initial CASE_E authoring
copied CASE_D's 4-branch HS+10yr/Associate's+6yr/Bachelor's+3yr/Master's+1yr
system-analysis-duration structure onto CASE_E merely because the postings
are similar. This was invalid: CASE_D's per-branch system-analysis-duration
figures (10/6/1 years) are directly, explicitly stated verbatim in CASE_D's
OWN supplemental questionnaire (Q1) -- not arithmetic. CASE_E's own
restored jd.txt has no equivalent explicit questionnaire breakdown (only a
single fixed "at least three (3) years system analysis" Yes/No question);
CASE_E's Substitutions sentences state only that HS/GED+7yr and
Associate's+3yr substitute "for the bachelor's degree requirement"
specifically (never restating a system-analysis-domain duration), so
building matching 10/6/1-year system-analysis branches for CASE_E would
have required inferring arithmetic/domain conversion the employer's own
CASE_E text never states. CASE_E was corrected to a source-grounded
"degree-component" gate: ALL_OF(REQ_E_SYS_ANALYSIS_EXP [always mandatory,
unaffected by either substitution], ANY_OF(Bachelor's, HS/GED + 7yr
directly-related experience, Associate's + 3yr directly-related
experience)) -- with duration legs correctly named/typed as generic
"directly related experience" (domain=null), never mislabeled as
"system analysis" experience. Lesson: source_text traceability to jd.txt
is necessary but not sufficient -- a traceable substitution sentence may
not be reused as provenance for a different, uncited semantic proposition
(here, a domain/duration conversion) that sentence does not itself state.
A permanent regression test (Section M2,
tests/alternative_qualification_branch_representation_v1_test.py) checks
semantic grounding, not merely source_text-substring presence, and fails
closed if CASE_E's fixture or gate ever again contains an invented
system-analysis-duration branch.

Master's/certification arithmetic remains intentionally unmodeled for
BOTH real fixtures: CASE_D's certification branch and CASE_E's Master's
AND certification branches are recorded via unmodeled_branches_note only,
never invented -- CASE_D's Master's branch is the sole exception,
supportable because CASE_D's own Q1 explicitly resolves it; CASE_E's
Master's/certification substitution sentences do not state what
Minimum-Qualifications component they substitute for, and this ambiguity
was reported (STOP_AND_REPORT), not resolved by inference.

Accepted real-control results:
- CASE_D: gate GATE_D_DEGREE_EXPERIENCE resolves UNRESOLVED (all 8 branch
  leaves UNRESOLVED -- no branch's capability recognition establishes
  either SUPPORTED or a NONE_TRAP-backed negative on current evidence).
  REQ_D_DEGREE/REQ_D_SYS_ANALYSIS_EXP no longer independently appear in
  qualification_gaps/unknowns. Decision remains REJECT, via unrelated,
  unaffected ungrouped gaps (ITSM/SaaS/MS Office); hard_blockers empty.
- CASE_E: gate GATE_E_DEGREE_COMPONENT (corrected) resolves UNRESOLVED (6
  leaves, all UNRESOLVED). REQ_E_DEGREE/REQ_E_SYS_ANALYSIS_EXP no longer
  independently appear in qualification_gaps. Decision changes from
  REJECT to UNDECIDED/UNASSIGNED -- an honest, unmanufactured consequence:
  removing the fabricated degree-only blocker surfaces CASE_E's actual
  underlying state (one genuinely STRONG requirement, process mapping,
  alongside unrelated NONE gaps), which the existing, unmodified decision
  thresholds route to UNDECIDED, not REJECT. Production decision
  thresholds were NOT altered to avoid or preserve this outcome (locked
  contract: truth outranks a desired decision).
- No APPLY-like decision was introduced for either fixture.
- Atominvest and MIT LL unaffected (zero diff).

Validation performed:
- Second independent Cursor adversarial re-review: SAFE_TO_COMMIT_AND_PUSH
  (after a first REQUIRES_CORRECTION verdict on the CASE_E provenance
  defect above, which was corrected before this second review).
- Full non-interactive suite: TOTAL=59 FAILED=0.
- Job Analysis Golden suite: 15/15 PASS.
- Application Gate Golden: 9/9 PASS.
- posting-state wiring tests: PASS.
- git diff --check: clean.
- Implementation commit independently verified on GitHub by ChatGPT Work.

Carried-forward exclusions/conclusions (not reopened):
- No global NONE-vs-UNKNOWN remediation was performed (remains separate,
  open, tracked below).
- No Master's/Associate's base-credential capability-pattern expansion.
- No technology-qualified-duration fix.
- No Application Gate capture (real ApplicationAttempt/ApplicationQuestion
  authoring) for either MBTA role.
- No package-generation work.
- No certification-branch arithmetic invented for either fixture.
- No candidate years-of-experience computation exists anywhere in the
  pipeline.
- Immigration/work-authorization and posting-state logic remain separate
  and conservative -- unchanged.

This closure's own "no new active implementation milestone" statement was
superseded by REPRODUCIBLE_CONSEQUENTIAL_ASSURANCE_BASELINE_V1 above, after
POST_QUALIFICATION_GATE_REAL_MARKET_BOTTLENECK_AUDIT_V1,
DEGREE_CREDENTIAL_CANDIDATE_EVIDENCE_ADJUDICATION_V1, and
SYSTEM_WIDE_TRUST_AND_CONSISTENCY_AUDIT_V1 ran and converged. See the
active pointer at the top of this file for current status.

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

Task: ALTERNATIVE_QUALIFICATION_BRANCH_REPRESENTATION_V1
Status: CLOSED
Implementation SHA: b10a38d09da60ef2e833fcbf718778e4132edabc
Architecture SHA: 26f799075bd44c6fad729b4e14043c3eec2ab31c
Authorization/pointer SHA: beff126455ec933cad78dcdb30837148c525fea1
Adjudication result: full source-grounded qualification_gate architecture
implemented per the canonical ADR; two independent Cursor adversarial
reviews (first REQUIRES_CORRECTION on a CASE_E employer-truth provenance
defect, corrected; second SAFE_TO_COMMIT_AND_PUSH); implementation commit
independently verified on GitHub by ChatGPT Work. TOTAL=59 FAILED=0; Golden
15/15; Application Gate Golden 9/9; posting-state PASS. See the detailed
closure record above for CASE_D/CASE_E results, the mid-milestone
provenance-lesson correction, and carried-forward exclusions.

Task: REPRODUCIBLE_CONSEQUENTIAL_ASSURANCE_BASELINE_V1
Status: CLOSED
Architecture SHA: d8826aa368e5dbfafb80531f03913bd43cd00713
Authorization SHA: 4a5ea68736f4c82274283ff154c7e53492320fba
Implementation SHA: b05c39022f791e3b6ef3f605f535a66620cd7c2a
Adjudication result: assurance/reproducibility debt (not a reproduced
business-logic defect) closed via a bounded requirements.in/requirements-
lock.txt pair, scripts/verify_assurance_baseline.py (three-phase canonical
command), .github/workflows/assurance-baseline.yml (SHA-pinned Actions),
and tests/p0_causal_invariants_v1_test.py (P0 integration invariants A-E,
including the M-01-corrected A2 high_none-counting isolation case); one
prior ADR-phase REQUIRES_CORRECTION (ambiguous verification-command phase
structure) and one prior implementation-phase M-01 correction (P0 §A
narrow gap), both corrected and re-reviewed SAFE_TO_COMMIT before
proceeding. Hosted GitHub Actions run (id 33678696541, head SHA
b05c39022f791e3b6ef3f605f535a66620cd7c2a, Ubuntu 24.04, Python 3.14.6)
independently verified: ALL PHASES PASSED (60/60 Phase 2, Application Gate
9/9, Job Analysis Golden 15/15). REPRODUCIBILITY_UNVERIFIED closed for
this exact canonical baseline/hosted environment only; BRANCH_PROTECTION_
UNVERIFIED unchanged. No business/production/schema/Claim/Evidence/
Experience/résumé semantics were touched at any stage. No new
implementation milestone auto-selected.

Historical anchors:
Governance role-sync commit: 4b55448a8d189fe29344aded3d883a2fb35e9b5a
Prior baseline-clarification commit: 445899ccbd934360ee0a240b7b7bd1a4239cf0df

The stored SHAs are historical anchors, not an assertion that any of
them must equal the future current HEAD.
