# Capture Notes -- CASE_C_MIT_LL_BUSINESS_SYSTEMS_ANALYST

Plain-text/Markdown companion note, unstructured by design, for the same
reason given in Case A's `capture_notes.md`: `job.json` uses the existing,
unmodified `schemas/job.schema.json`, and this file carries only what that
schema has no field for (source-authority classification, freeform known
unknowns, freeform source-conflict narrative, structural-placement
ambiguity notes).

## Identity
- CASE_ID: CASE_C
- Employer: MIT Lincoln Laboratory
- Role: Business/Systems Analyst
- Requisition ID: 43037

## Source authority
EMPLOYER_CONTROLLED (`careers.ll.mit.edu`, MIT Lincoln Laboratory's own
careers domain) -- recorded via the existing `source_verification_status`
vocabulary as `VERIFIED_DIRECT` in `job.json`.

## Source URL
https://careers.ll.mit.edu/job/Lexington-BusinessSystems-Analyst-MA-02420/1396804300/

## Capture / check timestamps (actual, machine-clock UTC; not copied from any prompt)
- Pass 1 (initial full-text request): 2026-08-31T01:47Z (approx.)
- Pass 2 (verbatim field-by-field request, to resolve ambiguity): 2026-08-31T01:47Z (approx.)
- Pass 3 (full responsibilities/apply-route request): 2026-08-31T01:48Z (approx.)

## Observable access/status at capture
Page loaded successfully across all three retrieval passes; substantive
content was returned each time (unlike Case A).

## Known unknowns (genuinely unresolved, not guessed)
- No sponsorship, OPT, E-Verify, or I-983 wording was observed anywhere in
  the retrieved content. UNKNOWN whether any such policy exists -- absence
  of observation is not evidence of absence.
- The exact section heading under which the citizenship/clearance sentence
  appears on the live page is ambiguous across retrieval passes (see
  "Structural-placement ambiguity" below) -- the sentence text itself is
  not in doubt, only its section grouping.
- Compensation figures were observed in only one of the three retrieval
  passes and were not independently cross-checked in the other two.
- The exact fully-resolved absolute Apply URL was not confirmed; only a
  relative path (`/talentcommunity/apply/1396804300/?locale=en_US`) and a
  button label ("Apply now »") were observed.
- Whether this posting has any application-form screening questions beyond
  the base JD is UNKNOWN -- not investigated, per this milestone's explicit
  scope boundary (source-JD freeze only, no application-question capture
  unless directly part of the observed JD source itself; none were).

## Structural-placement ambiguity (minor, not a factual conflict)
Across two of the three retrieval passes, the sentence "US citizenship
required to obtain and maintain a security clearance" was reported once as
appearing under a distinctly-labeled "Citizenship/Clearance Requirements"
grouping, and once as appearing within the "Preferred Qualifications"
section. The retrieval tool renders/summarizes page content through an
intermediate model rather than returning raw HTML, so exact section
boundaries are not independently verifiable from these passes alone. The
sentence's existence and exact wording, however, were consistent and
verbatim across all three passes -- high confidence in the text itself, low
confidence in exactly which named subsection contains it on the live page.

## Source conflict vs. this milestone's navigation aids
- Navigation aid stated: "date Aug 1, 2026". Retrieved page (two
  independent passes, consistent): "Aug 30, 2026". **Material discrepancy.**
  Per the Source Integrity Rule, the retrieved official source wins:
  the posted date is recorded as observed ("Aug 30, 2026"), not "Aug 1,
  2026". This conflict is reported, not resolved by assumption -- it is
  possible the posting date field changed since an earlier reference point,
  or that the navigation aid's original observation used a different
  capture time; neither possibility is confirmed here.
- All other navigation-aid facts (7+ years SAP FI/CO, 7+ years SAP ERP,
  U.S. citizenship/clearance requirement, Secret-level DoD clearance
  language, remote-within-100-miles condition, Requisition 43037, Lexington
  MA location) were independently corroborated by the retrieved official
  source, verbatim or near-verbatim, as quoted in `jd.txt`. See the parent
  Section D answer for the explicit yes/no confirmation of each.

## Application route observed?
Yes, partially: an "Apply now »" button linking to a relative path
(`/talentcommunity/apply/1396804300/?locale=en_US`) was observed. No
application-form screening questions were part of the observed JD source
page itself (that would require actually starting the application flow,
which is out of scope for this source-freeze milestone).

## Immigration wording observed?
Yes: citizenship-for-clearance and Secret-level DoD clearance language, both
quoted verbatim in `jd.txt`. No sponsorship/visa/OPT/E-Verify/I-983 wording
was observed anywhere in the retrieved content.

## Snapshot completeness
SUBSTANTIALLY COMPLETE. Title, requisition ID, location, position
description, full primary-duties text, minimum and preferred qualifications,
citizenship/clearance language, remote-work condition, and a partial
application-route observation were all captured. Not independently
byte-verified against raw HTML (the retrieval tool summarizes/converts
HTML to text via an intermediate model); treat as a high-fidelity but
tool-mediated transcription, not a raw archive.
