# Capture Notes -- CASE_A_ATOMINVEST_IMPLEMENTATION_ANALYST

Plain-text/Markdown companion note, unstructured by design (mirrors the
existing `jd.txt` convention of carrying no schema). Not a new schema or
architecture: `job.json` in this directory already uses the repository's
existing, unmodified `schemas/job.schema.json`; the fields below simply do
not have a slot in that schema (source-authority classification, freeform
known-unknowns, freeform source-conflict/relationship narrative) and this
file exists only to carry them without expanding `job.schema.json`'s
`additionalProperties: false` contract.

## Identity
- CASE_ID: CASE_A
- Employer: Atominvest
- Role: Implementation Analyst
- Target job ID (fixed, never replaced): `c7469459-426c-405c-a178-db8421c8b3ec`

## Source authority
EMPLOYER_AUTHORIZED_ATS (Ashby-hosted job board, `jobs.ashbyhq.com/atominvest/...`)
-- recorded via the existing `source_verification_status` vocabulary as
`VERIFIED_DIRECT` in `job.json` (upgraded from `SOURCE_VERIFICATION_REQUIRED`
after recovery; see "Retrieval history" below).

## Source URL
https://jobs.ashbyhq.com/atominvest/c7469459-426c-405c-a178-db8421c8b3ec?embed=js

## Retrieval history (both attempts preserved -- nothing erased)

**Attempt 1-2 (CASE_A_ATOMINVEST_SOURCE_FREEZE, 2026-08-31T01:47Z approx.):**
The available HTML-to-text web-fetch tool retrieved only the page's
`<title>` metadata ("Implementation Analyst @ Atominvest") from the target
URL, both with and without the `?embed=js` query parameter. At that time
this was correctly treated as an incomplete capture and NOT interpreted as
proof the page contained only a title -- the fixture was marked
`role_status=POSSIBLY_STALE` / `source_verification_status=SOURCE_VERIFICATION_REQUIRED`
and left genuinely incomplete rather than reconstructed from any prompt
hint.

**Attempt 3 (CASE_A_ATOMINVEST_SOURCE_RECOVERY_V1, 2026-08-31T01:57Z):**
A direct raw HTTP GET (`curl`, no JavaScript execution) of
`https://jobs.ashbyhq.com/atominvest/c7469459-426c-405c-a178-db8421c8b3ec`
returned HTTP 200 with a 35,832-byte response. Unlike the earlier
tool-mediated fetch, this raw retrieval exposed two server-embedded JSON
blocks already present in the initial HTML response (not client-rendered,
so no JavaScript execution was required to reach them):
1. An `application/ld+json` `schema.org/JobPosting` block.
2. An application-bootstrap JSON blob containing a `"posting":{...}` object.

Both blocks independently agree on every field, and both carry
`"id":"c7469459-426c-405c-a178-db8421c8b3ec"` / a matching `identifier.value`
-- an exact match to the target job ID this milestone specifies. This
resolves the earlier limitation: the earlier tool's HTML-to-text conversion
step did not surface these embedded script blocks; raw retrieval did. No
authentication, no headless browser, and no new dependency were used or
required -- only a plain HTTP GET already available in this environment.
One additional attempt, Ashby's authenticated single-posting API
(`api.ashbyhq.com/posting-api/job-posting/{id}`), was tried and correctly
abandoned after returning HTTP 401 (requires an API key this environment
does not have and was not asked to obtain).

## Capture / check timestamps (actual, machine-clock UTC; not copied from any prompt)
- Recovery fetch: 2026-08-31T01:57:36Z (curl retrieval of the raw target URL)
- Extraction/verification of embedded JSON: same session, immediately after

## Observable access/status at capture
HTTP 200. `isListed: true`, `isConfidential: false` (both fields read
directly from the employer's own embedded posting data) -- a direct,
strong, source-based signal that this exact posting is currently listed as
open, as of this capture. This is a snapshot fact, not an eternal claim
(see `job.json`'s `role_status`/date fields).

## Fields recovered (all verbatim from the embedded employer data; none inferred from this milestone's navigation aids)
- title: "Implementation Analyst"
- departmentName / departmentExternalName: "Customer Success"
- teamNames: ["Customer Success"]
- locationName / locationAddress: "New York City" / "New York City, New York"
- secondaryLocationNames: ["Boston"]
- workplaceType: "Hybrid"
- employmentType: "FullTime" (ld+json: "FULL_TIME")
- jobLocationType (ld+json): "TELECOMMUTE"
- applicantLocationRequirements (ld+json): Country "United States"
- datePosted: "2026-08-05"
- hiringOrganization: "Atominvest", sameAs "https://www.atominvest.co"
- Full description text: reproduced verbatim in `jd.txt`

## Known unknowns (still genuinely unresolved, not guessed)
- Exact application route/URL: not found as an explicit field in the
  retrieved embedded data; only the platform's conventional pattern is
  noted in `jd.txt`, explicitly labeled as inferred-from-platform-pattern,
  not observed.
- Any work-authorization, sponsorship, citizenship, clearance, OPT, or
  E-Verify wording: a full-text search of the entire retrieved raw HTML
  (35,832 bytes, including all embedded scripts) found zero matches for
  "visa", "sponsor", "citizen", "authoriz", "E-Verify", or "clearance".
  This means no such wording is present on this specific page as of this
  capture -- it does not establish that no sponsorship policy exists.
  UNKNOWN remains the correct status for the policy question itself.
- `applicantLocationRequirements: "United States"` is a real observed field
  or an ATS default is not further disambiguated here; it is recorded
  as-observed without an inference about what it implies for a non-U.S.
  candidate's eligibility.

## Application route observed?
Not explicitly, as a stated field. See "Known unknowns" above.

## Immigration wording observed?
No wording found (exhaustive search of full retrieved content). UNKNOWN
remains the correct policy status per the primary rule.

## Snapshot completeness
SUBSTANTIALLY COMPLETE as of the recovery attempt: title, department/team,
both locations, workplace type, employment type, posting date, full
role/company description, and full "What You'll Be Doing" and
"Requirements" sections were all independently retrieved and are frozen
verbatim in `jd.txt`. Not independently byte-verified beyond the raw HTTP
response captured; the JSON extraction itself was deterministic (Python
`re`/`json`, not a summarizing model), so this capture carries higher
fidelity than the Case A attempt in the prior milestone.

---

## CONFLICT / RELATIONSHIP PRESERVATION (does not delete the earlier finding)

The immediately preceding milestone (`CASE_A_ATOMINVEST_SOURCE_FREEZE_A_C_V1`)
independently observed, via Atominvest's public Ashby job-board API listing
all current postings, a **separate** Implementation Analyst posting:
- job ID `e59c8e9e-4b2c-411c-bf60-458b6d7e3abb`
- Customer Success department/team
- Location: London
- FullTime
- published `2026-08-05T09:31:52.248Z`
- `isListed: true`

That observation is **preserved here, not deleted or overwritten**, because
recovering the target posting's content does not invalidate it -- both are
independently observed, currently-listed postings at the same employer,
under the same title, in the same department.

**Relationship, stated conservatively (not guessed):**
Two distinct Implementation Analyst requisitions with different job IDs and
different locations were independently observed as listed during the
relevant capture window: this fixture's target (`c746...`, New York
City/Boston) and a separate posting (`e59c8e9e...`, London). Both carry a
`datePosted`/`publishedAt` of 2026-08-05, and both were independently
observed as `isListed: true` at their respective capture times. This is
consistent with simultaneous multi-location hiring for the same title, but
that is not established as a fact by these two point-in-time observations
alone -- it is not evidence that either observation is stale, mistaken, or
fabricated, and no stronger claim (e.g. that Atominvest currently has, or
had, two concurrently open requisitions) is made than the observations
themselves support. This repository does not currently have a dedicated
"related/sibling posting" vocabulary; the relationship is recorded here in
free text rather than encoded into `job.schema.json`, consistent with this
milestone's instruction not to expand schema for this purpose. No claim is
made that the two postings are the "same role," and no claim is made that
one supersedes the other -- both remain independently valid observations of
this employer's board.
