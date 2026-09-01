# Capture Notes -- CASE_D_MBTA_DIRECT_APPLICATION_ANALYST

Plain-text/Markdown companion note, unstructured by design (mirrors the
existing `jd.txt`/`capture_notes.md` convention used by CASE_A and CASE_C).
`job.json` in this directory uses the repository's existing, unmodified
`schemas/job.schema.json`. This file exists only to carry information that
schema has no dedicated slot for (the official requisition/job number,
retrieval method, and source-authority classification) without expanding
`job.schema.json`'s `additionalProperties: false` contract.

## Identity
- CASE_ID: CASE_D
- Employer: Massachusetts Bay Transportation Authority (MBTA)
- Role: Application Analyst (Digital Workplace)
- **Official Job Number (requisition ID): 26-20235**
  -- this is the ONLY place besides `job.json`'s `jd_snapshot` prose that
  this repository currently stores the requisition ID.
  `schemas/job.schema.json` has no dedicated structured field for an
  external requisition/job number (confirmed by inspection during
  JOB_POSTING_IDENTITY_AND_REAL_FIXTURE_AUDIT_V1); per this milestone's
  explicit instruction, the schema was NOT changed to add one. The job
  number is preserved truthfully in the smallest available field
  (`jd_snapshot` free text) plus this note, exactly mirroring how
  CASE_C_MIT_LL_BUSINESS_SYSTEMS_ANALYST already preserves "Requisition
  43037" the same way.

## Source authority
EMPLOYER_AUTHORIZED_ATS (governmentjobs.com/careers/mbtama -- MBTA's own
first-party applicant-tracking system, not a third-party aggregator) --
recorded as `source_verification_status: VERIFIED_DIRECT` in `job.json`.

## Source URL
https://www.governmentjobs.com/careers/mbtama/jobs/5449649/application-analyst-digital-workplace

## Retrieval method
Tool-mediated web fetch (HTML-to-markdown conversion + a small extraction
model), NOT a raw HTTP GET / raw HTML capture (unlike CASE_A's recovery
attempt). Two separate fetch calls were made against the same URL with
different extraction prompts to independently confirm: (1) core minimum
qualifications, substitutions, named systems, work authorization, and the
Q1-Q6 supplemental questionnaire question text; (2) the exact verbatim
wording of the Minimum Qualifications paragraph and the exact verbatim Q1
option list. Both calls returned mutually consistent facts (job number,
dates, degree/experience structure, sponsorship wording) with no
contradiction between them.

## Capture / check timestamp
2026-08-31 (session date; exact machine-clock timestamp not separately
logged by the fetch tool used).

## Observable status at capture
Opening Date 08/24/2026, Closing Date 9/7/2026 11:59 PM Eastern -- today's
session date (2026-08-31) falls strictly between these, so the posting is
currently within its stated open window as of this capture. Recorded as
`role_status: VERIFIED_LIVE` on that basis (a direct, dated, first-party
open/close window from the employer's own ATS -- the strongest signal this
repository's `role_status` vocabulary currently has access to), not from
search-result existence alone.

## Fields recovered (from the official ATS page, via tool-mediated fetch)
- Job Number: 26-20235
- Job Title: "Application Analyst (Digital Workplace)"
- Employer: Massachusetts Bay Transportation Authority
- Location: 10 Park Plaza, Boston
- Employment Type: Full-Time
- Opening Date: 08/24/2026 / Closing Date: 9/7/2026 11:59 PM Eastern
- Minimum Qualifications: two separate sentences (degree; then, separately,
  "Three (3) years of experience in system analysis, including enterprise
  application design, configuration / development, implementation, and
  support.") -- period-separated, NOT a single AND/PLUS-conjoined clause.
  This is factually different from the hypothetical "Bachelor's degree AND
  3 years of system analysis experience" wording this repository's test
  suite has used as a stand-in for "real MBTA phrasing" throughout
  QUALIFIED_DEGREE_EXPERIENCE_DURATION_V1 and its predecessor milestones --
  see the audit report for the resulting adjudication finding.
- Substitution ladder (verbatim, four alternatives to the Bachelor's
  requirement): HS/GED+7yrs; Associate's+3yrs; Master's-substitutes-2yrs;
  certification-substitutes-1yr.
- Required Skills: business-process mapping/optimization, business-rules
  and technical-requirements documentation, SaaS/cloud-delivery-model
  knowledge, IT service management/ticketing systems, strong MS Office
  proficiency.
- Preferred: Comply365, Document Management Systems, HR, LMS, IDP; Power
  Platform (Power Automate/Power Apps); API/data-integration tools; M365
  governance/security; Power BI/Tableau; transit/transportation industry
  background.
- Work authorization (verbatim): "All employees must be legally authorized
  to work in the United States and on an unrestricted basis. The MBTA does
  not have an employer work sponsorship program."
- Supplemental Questionnaire: Q1 (education/experience substitution ladder,
  verbatim five options, including "A master's degree and one (1) or more
  years of experience in system analysis, including enterprise application
  design, configuration / development, implementation, and support." --
  this Q1 option DOES use "and" as its connector, unlike the plain-page
  Minimum Qualifications sentences, which use no connector at all because
  they are two separate sentences); Q2 (ITSM/ticketing yes/no); Q3
  (SaaS/cloud yes/no); Q4 (business-process-mapping yes/no); Q5 (current US
  work authorization yes/no); Q6 (future sponsorship need yes/no).

## Known unknowns (genuinely unresolved, not guessed)
- Exact work arrangement (onsite/hybrid/remote): no explicit dedicated
  sentence found; only "Ability to commute to assigned work locations in
  the Boston, MA metro area, as required by the role." Treated as
  insufficient to assert HYBRID or ONSITE -- `work_arrangement` recorded
  as `UNKNOWN` rather than guessed from the presence of a physical address.
- Whether the tool-mediated fetch's quoted sections are byte-identical to
  the live page's HTML (as opposed to a faithful markdown-converted
  rendering) is not independently verified the way CASE_A's raw-HTTP
  recovery was; treated as a lower-fidelity capture than CASE_A for that
  reason, though internally consistent across two independent fetch calls.
- Application-question EVALUATION behavior (whether the repository's
  `match_clause()`/Application Gate path can process these exact Q1-Q6
  questions) is reported separately in the audit output, not assumed here.

## Immigration wording observed?
Yes, explicit and direct: "The MBTA does not have an employer work
sponsorship program." Recorded in `job.json`'s `sponsorship_wording` and
`work_authorization_wording` fields verbatim. This is real, usable evidence
per this repository's existing immigration-evidence rules (an explicit
employer statement, not an inference).

## Relationship to CASE_E (contractor counterpart)
CASE_E_MBTA_CONTRACTOR_APPLICATION_ANALYST is a separately frozen, distinct
posting instance (different job number, different employment type,
different closing-date structure, explicit "not employed directly by
MBTA" statement). No text, requirement rows, or field values are shared or
copied between the two fixtures -- each was independently captured from its
own official source URL. See CASE_E's own `capture_notes.md` for its
identity and the employment-structure representability discussion.
