# Capture Notes -- CASE_E_MBTA_CONTRACTOR_APPLICATION_ANALYST

Plain-text/Markdown companion note, unstructured by design (mirrors the
existing `jd.txt`/`capture_notes.md` convention). `job.json` in this
directory uses the repository's existing, unmodified `schemas/job.schema.json`.

## Identity
- CASE_ID: CASE_E
- Posting organization: Massachusetts Bay Transportation Authority (MBTA)
- Role: Application Analyst - Digital Workplace (Contractor Position)
- **Official Job Number (requisition ID): 20260804A-ITS87**
  -- preserved in `job.json`'s `jd_snapshot` prose and here, exactly the
  same treatment as CASE_D. No schema change was made to store it.

## Source authority
EMPLOYER_AUTHORIZED_ATS (governmentjobs.com/careers/mbtama, contractor
postings section) -- recorded as `source_verification_status:
VERIFIED_DIRECT` in `job.json`.

## Source URL
https://www.governmentjobs.com/careers/mbtama/jobs/5436565-0/application-analyst-digital-workplace-contractor-position

## Retrieval method
Tool-mediated web fetch (HTML-to-markdown conversion + a small extraction
model), same method class as CASE_D, independently invoked against this
posting's own URL. Not a raw HTTP GET / raw HTML capture.

## Capture / check timestamp
2026-08-31 (session date).

## Observable status at capture
Opening Date 08/04/2026, Closing Date "Continuous" (no fixed end date).
Recorded as `role_status: VERIFIED_LIVE` on the basis of a direct,
first-party ATS page with an open (non-past) posting and no closing date
that would place it outside its window -- "Continuous" postings have no
expiry to check against, so freshness confidence here rests entirely on
the page being currently retrievable and listed, which is a weaker signal
than CASE_D's dated closing window. This distinction is recorded, not
smoothed over: a "Continuous" posting is architecturally a different kind
of freshness signal than a dated one, even though both are recorded under
the same `VERIFIED_LIVE` enum value today (this repository's `role_status`
vocabulary does not currently distinguish "verified live with a known
future close date" from "verified live, continuously open, no close date
to check" -- both collapse to `VERIFIED_LIVE`).

## Fields recovered (from the official ATS page, via tool-mediated fetch)
- Job Number: 20260804A-ITS87
- Job Title: "Application Analyst - Digital Workplace (Contractor Position)"
- Posting organization: Massachusetts Bay Transportation Authority
- Location: 10 Park Plaza, Boston; hybrid, "at least two (2) days per
  week" in-office (explicit -- unlike CASE_D, where no explicit work
  arrangement sentence was found)
- Employment Type: Contractor (term-limited and project-specific)
- Compensation: $48.00 hourly
- Opening Date: 08/04/2026 / Closing Date: Continuous
- **Employment Status Clarification (verbatim, explicit)**: "not employed
  directly by the MBTA"; "a term-limited and project-specific contractor
  position." No staffing agency, vendor, or other named legal employer is
  stated anywhere on the retrieved page.
- Minimum Qualifications: substantively the same core duties as CASE_D
  (degree, 3 years system-analysis experience with the same "enterprise
  application design, configuration/development, implementation, and
  support" phrasing, business-process mapping, business-rules/technical-
  requirements documentation, SaaS/cloud knowledge, ITSM/ticketing, MS
  Office), independently worded on this separate page (e.g. this page's
  minimum-qualifications list omits the direct posting's "and identify
  opportunities for optimization or automation" clause on the
  process-mapping line, and omits the substitution ladder and preferred-
  systems list entirely) -- NOT copy-pasted from CASE_D.
- Work authorization (verbatim, as retrieved): candidates must be
  "legally authorized to work in the United States" on an unrestricted
  basis; "The MBTA does not have an employer work sponsorship program."

## Employment-structure representability (read-only observation, no schema change made)
`schemas/job.schema.json` has exactly one employer-identity field,
`company`, plus a categorical `employment_type` enum (which does include
`CONTRACT`). It has no `legal_employer`, `client_worksite`, or
`posting_employer` field. This fixture's `company` is set to "Massachusetts
Bay Transportation Authority (MBTA)" -- the posting organization named on
the page -- NOT a claim that MBTA is the legal employer; the page itself
explicitly denies that. The following information is real, explicitly
stated by the source, and currently has **no structured field to live in**:
who the actual legal employer / staffing vehicle is (not named on the
page at all -- genuinely unknown, not merely unstored); and the fact that
the posting organization's own no-sponsorship statement may not bind
whoever the actual (unnamed) employer of record turns out to be. Both
points are preserved only in free text (`jd_snapshot`, `sponsorship_wording`,
and this file) per this milestone's explicit instruction not to redesign
the schema in this phase.

## Known unknowns (genuinely unresolved, not guessed)
- **This posting's supplemental application questionnaire, if one exists,
  was not fetched or verified this pass** (unlike CASE_D, whose Q1-Q6 were
  independently fetched and are preserved verbatim in `jd.txt`/`job.json`).
  This is a stated omission, not a claim that no questionnaire exists --
  no questionnaire content is asserted or fabricated anywhere in this
  fixture as a substitute.
- The actual legal employer / staffing agency, if any, is not named on the
  retrieved page. Not inferred here.
- Whether the "no sponsorship program" statement (attributed to MBTA)
  applies to the actual (unnamed) employer of record for this contractor
  role is not established by the source text. Not inferred here.
- E-Verify enrollment, STEM-OPT viability, and any other immigration
  conclusion beyond the literal quoted sentences: not addressed by the
  source, recorded UNKNOWN, not inferred from "government contractor" or
  any other proxy.

## Relationship to CASE_D (direct counterpart)
See CASE_D's own `capture_notes.md`. Both fixtures were captured
independently from their own distinct official source URLs; no text or
field values were copied between them.
