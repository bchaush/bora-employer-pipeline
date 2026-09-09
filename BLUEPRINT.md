**BORA EMPLOYER PIPELINE OS**

**Final Locked Blueprint v3.13**

**Owner:** Bora Chaush  
**Date locked:** August 2026  
**Workspace:** Boston & Remote Employer Pipeline

**0. STATUS OF THIS DOCUMENT**

This is the **strategic, product, reliability, AI-agent, implementation,
and coding source of truth** for the Bora Employer Pipeline OS.

All future build chats, ChatGPT Work sessions, Claude Code implementation
sessions, Cursor adversarial-review sessions, optional occasional Gemini
non-coding second-opinion sessions, scripts, schemas, prompts, tests, and
changes must begin from
this document.

Do not redesign the system from scratch in a later chat.

Do not silently reinterpret a locked rule.

Do not loosen reliability rules to increase speed.

If a materially better approach is discovered:

1.  document it;

2.  explain why;

3.  show evidence;

4.  obtain Bora's approval;

5.  update the Change Log;

6.  version this Blueprint.

Until then:

**THIS DOCUMENT WINS.**

**1. WHY THIS SYSTEM EXISTS**

This system is being built specifically for **Bora Chaush**.

It is not a generic job-search product.

It is not primarily a résumé-writing tool.

It is not an ATS-score optimizer.

It is not a mass-apply bot.

It is not another Simplify.

Its purpose is:

**Turn a high-effort manual job search into a high-throughput,
evidence-controlled process where Bora can evaluate at least 50 real
roles per day and rapidly turn qualified roles into honest,
role-specific application packages.**

The system should perform the repetitive intellectual work that
currently makes a small number of applications expensive:

- company research;

- role verification;

- job-description parsing;

- OPT-related screening;

- evidence retrieval;

- fit analysis;

- gap detection;

- résumé emphasis;

- project selection;

- wording adaptation;

- networking research;

- follow-up planning.

The system should **not** remove Bora from consequential decisions.

**2. BORA — PERMANENT SYSTEM CONTEXT**

Every agent must understand why Bora is searching.

Bora's:

**Brandeis MS in Business Analytics**

is officially completed and awarded, per Bora's direct human attestation
dated 2026-09-03 (`evidence/education/EDU_BRANDEIS_AWARDED_ATTESTATION_001.json`,
`evidence_state=OBSERVED`) — all academic requirements are complete; the
physical diploma has not yet been received. This attestation-tier fact is
distinct from, and does not retroactively upgrade, the separate
documentary transcript/progress-screen evidence (`EDU_BRANDEIS_IDENTITY_001`,
`EDU_BRANDEIS_GPA_001`, `EDU_BRANDEIS_PROGRESS_001`), which on its own
establishes only program identity, GPA, and requirements-satisfied status,
never conferral. A future official diploma or registrar record may
strengthen or supersede this attestation tier.

His strongest current organizational evidence is:

**Winter Walk.**

His supporting technical/project evidence includes:

- MarketMind AI;

- Market Empire / FCAT;

- LoanIQ;

- additional verified GitHub/project work.

His earlier professional experience includes:

- financial analysis;

- reporting;

- reconciliation;

- regulatory/compliance-oriented work;

- trust and safety/data operations.

His longer-term professional/business direction is:

**RELIABLE AI-ENABLED BUSINESS SYSTEMS**

**BUILD → VERIFY → OPERATE**

This means:

**BUILD**  
Understand the real workflow and implement the smallest useful system.

**VERIFY**  
Test assumptions, inputs, outputs, boundaries and failures.

**OPERATE**  
Log, monitor, document, maintain and hand off the system reliably.

Bora is eventually building toward his own business in this field.

**3. WHY BORA WANTS EMPLOYMENT NOW**

Employment is not Bora's final destination.

It is currently valuable for:

- near-term income;

- initial OPT employment;

- U.S. professional experience;

- U.S. references;

- larger systems exposure;

- experienced coworkers;

- credibility;

- relationships;

- future clients/partners;

- potential STEM OPT pathway.

Therefore the system must not reject a useful role merely because it is
not Bora's perfect future title.

A good bridge role can be extremely valuable.

**4. IMMEDIATE JOB OBJECTIVE**

Prioritize legitimate roles Bora can realistically obtain quickly.

Especially consider:

- part-time;

- contract;

- W-2 contract;

- temporary;

- contract-to-hire;

- remote;

- Boston/hybrid;

- full-time when particularly strong;

- staffing-firm placements.

The system's purpose is **speed with quality**, not prestige.

**5. LOCKED OPTIMIZATION ORDER**

When factors conflict, use this hierarchy:

1.  **Legitimate MSBA / initial OPT relevance**

2.  **Realistic hiring probability**

3.  **Hiring speed**

4.  **Income / usable hours**

5.  **Strength of Bora's evidence**

6.  **U.S. credibility/reference value**

7.  **Learning and network value**

8.  **Long-term Business Systems alignment**

9.  **Future STEM OPT quality**

10. **Prestige**

Do not secretly optimize for prestige.

Do not secretly optimize for AI-sounding titles.

**6. JOB UNIVERSE**

The system searches functions, not merely titles.

**PRIMARY**

- Business Systems Analyst

- Business Analyst

- Implementation Analyst

- Implementation Consultant

- Customer Implementation Analyst

- Systems Analyst

- Application Analyst

- Data Operations Analyst

- Data Quality Analyst

- Business Process Analyst

- Operations Systems Analyst

- Digital Solutions Analyst

- Technical Operations Analyst

**HIGH-VALUE ADJACENT**

- Business Operations Analyst

- Operations Analyst

- Revenue Operations Analyst

- Sales Operations Analyst

- Sales Analyst

- Commercial Operations Analyst

- Data Sales roles

- Data Solutions roles

- technical/analytical sales roles

- Customer Success Operations

- Solutions Analyst

- junior pre-sales / solutions roles

- Analytics Consultant

- Institutional Research

- Advancement Operations

- Research/Program Operations

- AI Implementation Analyst

- AI Enablement Analyst

- AI Quality/Evaluation roles

A job containing the word **sales** is not automatically weak.

If the actual work meaningfully uses:

analytics, data, forecasting, systems, reporting, technical products,
process improvement, operations, customer implementation, CRM analysis,
or business intelligence,

it may be a legitimate strong target.

**7. GENERALLY LOW-PRIORITY / REJECT**

Unless unusually strong evidence says otherwise:

- senior BSA;

- senior implementation consultant;

- senior product roles;

- Solutions Architect;

- deep Software Engineer;

- ML Engineer;

- AI Engineer;

- deep Data Engineer;

- senior Data Scientist;

- enterprise Salesforce specialist;

- enterprise Workday specialist;

- enterprise ServiceNow specialist;

- roles requiring several years of direct platform experience Bora does
  not possess.

The system must recognize aspirational language versus actual hard
requirements.

**8. CENTRAL SYSTEM PRINCIPLE**

**THE RÉSUMÉ IS NOT THE SOURCE OF TRUTH.**

The source of truth is:

**BORA EVIDENCE REPOSITORY**

The résumé is generated from evidence.

Networking messages are generated from evidence.

Interview stories are generated from evidence.

Application answers are generated from evidence.

Never reverse this architecture.

**9. SOURCE-OF-TRUTH HIERARCHY**

**LEVEL 0 — ORIGINAL SOURCE**

Examples:

- actual code;

- GitHub;

- original project documents;

- approved stakeholder documents;

- original employment records;

- current résumé factual history;

- official university records;

- direct project outputs.

**LEVEL 1 — EVIDENCE RECORD**

Structured fact extracted from original source.

**LEVEL 2 — APPROVED CLAIM**

A human-reviewed statement supported by one or more evidence records.

**LEVEL 3 — RÉSUMÉ MODULE**

Approved presentation of claims.

**LEVEL 4 — APPLICATION-SPECIFIC OUTPUT**

Generated résumé, message or interview material.

AI can propose transformations downward.

AI cannot silently modify truth upward.

**10. EVIDENCE ID RULE**

Every material factual claim created by the system must trace back to
one or more:

**Evidence_IDs**

Example:

WW_REQ_003

WW_UAT_006

MM_API_004

No Evidence_ID:

**NO NEW FACTUAL CLAIM.**

This must be enforced by software.

Not merely by prompt.

**11. LEAN EVIDENCE REPOSITORY**

Do not turn evidence documentation into another capstone project.

Start with high-value evidence.

**INITIAL**

1.  Winter Walk

2.  MarketMind

3.  Market Empire

4.  LoanIQ

**PULL-BASED EXPANSION**

Add detailed evidence from:

- TELUS;

- Bulmarma;

- D Commerce;

- coursework;

- additional projects

when real job requirements make those experiences useful.

**12. MINIMUM EVIDENCE RECORD**

Each evidence record includes:

- Evidence_ID

- Experience_ID

- fact

- capability demonstrated

- technology/tool

- evidence state

- original source

- source location

- safe for external use?

- notes

Optional later:

- stakeholders;

- workflow stage;

- business context;

- tests;

- outcome;

- limitations;

- related claims.

**13. EVIDENCE STATES**

Only these states are permitted.

**VERIFIED**

Direct source evidence supports the fact.

**SUPPORTED**

Evidence strongly supports the interpretation, without introducing a
materially new fact.

**OBSERVED**

Real qualitative evidence exists but is not quantitatively verified.

**UNKNOWN**

Evidence is insufficient.

**CONTRADICTED**

Available evidence indicates the claim is wrong.

No model can turn:

UNKNOWN → VERIFIED

without new evidence.

**14. OUTCOME RULE**

Never fabricate business impact.

If Bora did not measure hours saved:

do not create hours saved.

If Bora did not measure percentage improvement:

do not create percentage improvement.

If a stakeholder observed the process became easier:

that can potentially be:

OBSERVED.

Not:

VERIFIED 37% productivity improvement.

**15. CLAIM BANK**

Every approved reusable claim receives:

- Claim_ID

- wording

- Evidence_ID(s)

- evidence state

- allowed contexts

- forbidden contexts

- human approval

- date

- version.

The claim bank prevents each AI from creatively reconstructing Bora's
history.

**Claim actor attribution (v1).** Substantive `evidence_ids` establish what
happened; Bora's explicit `human_approval` on the exact Claim establishes
conventional résumé active-voice actor attribution for that supported work.
Human approval cannot create unsupported substantive facts. Conventional
actor attribution does not imply sole, unaided, or exclusive authorship.
Authoritative detail:
`docs/decisions/ADR-CLAIM-ACTOR-ATTRIBUTION-POLICY-V1.md`.

**16. FORBIDDEN-CLAIM REGISTRY**

Maintain explicit semantic boundaries.

Examples:

**Bulgarian regulatory reporting**  
does not equal  
**U.S. GAAP regulatory expertise.**

**Google Apps Script**  
does not equal  
**Google Cloud Engineering.**

**LLM API integration**  
does not equal  
**ML Engineering.**

**UAT**  
does not automatically equal  
**enterprise QA engineering.**

**MarketMind**  
does not equal  
**enterprise production site-selection platform.**

**LoanIQ**  
does not equal  
**deployed regulated lending system.**

**Winter Walk**  
does not equal  
**enterprise SaaS platform.**

**AI-assisted coding**  
does not equal  
**expertise in every framework AI can generate.**

Semantic violations must fail validation.

**17. ORIGINAL TITLES**

Formal historical titles remain unchanged.

The system may describe underlying functional work in:

- summary;

- bullets;

- skills;

- cover note;

- interview preparation.

It must not secretly rename Bora's actual job title because a different
title matches the JD better.

**18. JOB DISCOVERY**

The OS does not need to become a job board.

Use existing discovery channels:

- LinkedIn Free;

- Simplify Free;

- Brandeis Handshake;

- employer career pages;

- Built In;

- HigherEdJobs;

- Idealist where relevant;

- staffing/recruiting firms;

- company lists;

- referrals;

- recruiter outreach;

- other credible job sources.

Discovery source and application source are separate fields.

**19. DIRECT-SOURCE RULE**

Whenever practical:

**VERIFY THE ROLE ON THE EMPLOYER'S OWN CAREERS PAGE.**

If the board listing exists but the company listing cannot be found:

do not automatically call it fake.

Classify:

**SOURCE_VERIFICATION_REQUIRED**

or:

**POSSIBLY_STALE**

depending on evidence.

Do not hard-reject solely from aggregator absence unless the evidence is
strong enough.

**20. ROLE FRESHNESS**

Store:

- discovered date;

- board-posted date if available;

- first-seen date;

- last-verified date;

- careers-page status;

- repost evidence.

Preference:

fresh and verified roles.

Do not create fake precision such as:

“applying within exactly 38 hours doubles Bora's odds.”

Directionally:

**earlier legitimate applications are generally preferable to
unnecessarily delayed applications.**

**21. GHOST / STALE ROLE DETECTION**

Use signals.

Possible red flags:

- old posting;

- repeated reposting;

- no company careers-page match;

- contradictory dates;

- generic permanent opening;

- apparent closed requisition;

- major recent layoffs;

- recruiter indicating role is frozen;

- broken application destination.

Do not classify something as a “ghost job” from one weak signal.

Preferred output:

**VERIFIED LIVE**

**LIKELY LIVE**

**UNCLEAR**

**POSSIBLY STALE**

**CONFIRMED CLOSED**

**22. APPLICANT COUNT RULE**

Applicant count is never a hard reject.

Especially do not assume:

LinkedIn's visible number = completed applications.

Use only as weak competition context.

Fresh strong fit:

apply regardless of visible applicant count.

**23. JOB RECORD**

Every discovered role receives:

Job_ID

Minimum fields:

- Job_ID

- company

- role

- official URL

- discovery URL

- location

- work arrangement

- employment type

- date first seen

- date last verified

- role status

- role family

- seniority

- JD snapshot

- work-authorization wording

- OPT flag

- E-Verify result

- evidence matches

- major gaps

- lane

- decision

- résumé version

- network action

- application status

- outcome.

**24. INITIAL OPT AND STEM OPT ARE DIFFERENT**

Never collapse them.

Every serious role receives:

**INITIAL OPT RELEVANCE**

and separately:

**FUTURE STEM QUALITY**

A job can be useful now but poor for future STEM.

That is acceptable when consciously chosen.

**25. IMMIGRATION SOURCE RULE**

For consequential immigration facts use:

1.  Brandeis ISSO;

2.  USCIS;

3.  DHS/SEVP;

4.  official E-Verify information;

5.  qualified immigration professional when necessary.

Do not use:

Reddit, a recruiter, AI memory, a career blog, or a job board

as legal authority.

**26. E-VERIFY RULE**

E-Verify matters primarily for future STEM planning.

Store possible results as:

- CONFIRMED / strong official evidence

- SEARCH MATCH FOUND

- NOT FOUND IN PUBLIC SEARCH

- UNKNOWN

- HR CONFIRMATION NEEDED

Never convert:

**not found**

into:

**not enrolled.**

The public search has limitations.

Before consequential STEM reliance, verify directly with the employer/HR
and follow current official guidance.

**IMMIGRATION BOUNDARY GUARD**

Descriptive job-posting text is not legal authority. If an AI component attempts to resolve OPT eligibility, E-Verify enrollment, or work-authorization status solely from descriptive job-posting text, deterministic validation must stop the pipeline for that field and return:

**LEGAL_VERIFICATION_REQUIRED**

The unresolved field must remain explicit until verified through an approved source under Section 25 or, where appropriate, direct employer/HR confirmation.

**27. H-1B HISTORY**

H-1B history may be used as one positive signal for future international
hiring familiarity.

Preferred sources:

- USCIS employer data;

- DOL disclosure data;

- reputable structured interfaces as secondary aids.

Past sponsorship:

does not guarantee future sponsorship.

No historical filing:

does not automatically mean the employer will never support Bora.

The same immigration boundary applies here: descriptive job-posting language may inform screening context, but it cannot by itself establish a legal work-authorization conclusion. Where a consequential status remains unresolved, return **LEGAL_VERIFICATION_REQUIRED** rather than infer a legal conclusion.

**28. HIGH-THROUGHPUT ARCHITECTURE**

The system target is:

**50+ JOB CHECKS PER DAY.**

A job check means the OS can:

1.  ingest;

2.  verify enough to proceed;

3.  extract requirements;

4.  compare to Bora;

5.  classify;

6.  expose major gaps.

This is different from promising:

50 externally submitted applications every day.

**29. THREE PROCESSING LANES**

**LANE 0 — REJECT**

Bad fit.

No résumé.

No network research.

Minimal compute.

**LANE 1 — EFFICIENT APPLY**

Plausible role.

Perform:

- standard evidence mapping;

- minimal résumé patch;

- automatic QA;

- application package.

Networking:

0–1 obvious high-value person.

**LANE 2 — PRIORITY APPLY**

Strong role.

Perform:

- deeper role verification;

- stronger evidence mapping;

- more deliberate résumé emphasis;

- company context;

- recruiter/team research;

- 1–3 networking targets;

- interview notes.

Do not spend Priority effort on every application.

**30. OPTIONAL WATCH LANE**

Use WATCH where:

- posting status uncertain;

- immigration point unresolved;

- potentially excellent job not currently active;

- strong employer but no relevant role;

- application paused.

WATCH is not rejection.

**31. JOB REQUIREMENT EXTRACTION**

AI converts a JD into structured requirements.

Each requirement receives:

- Requirement_ID

- text

- category

- mandatory/preferred/unclear

- seniority implication

- technology

- experience level

- domain

- relevance.

Never treat every noun in a JD as a hard requirement.

**32. EVIDENCE MATCHING**

For each important requirement:

Requirement_ID → Evidence_ID(s)

with one result:

- STRONG

- SUPPORTED

- PARTIAL

- NONE

- UNKNOWN

The system must expose gaps.

It is prohibited from “solving” gaps by creative wording.

**33. PARTIAL TRANSFER**

Important distinction:

Related experience can be useful without pretending equivalence.

Example:

Bora has regulatory reporting abroad.

A U.S. regulated employer may value:

- controls;

- deadlines;

- reconciliation;

- data quality;

- audit discipline.

System output:

**transferable control/reporting evidence**

not:

**U.S. regulatory reporting experience.**

**34. FIT DECISION**

Final routing:

**PRIORITY APPLY**

Very strong use of Bora's time.

**APPLY**

Good opportunity.

**EFFICIENT APPLY**

Reasonable probability and low enough cost.

**WATCH**

Potential but unresolved.

**REJECT**

Do not spend application time.

**35. NO FAKE HIRE PROBABILITY**

Do not output:

“72% chance.”

Use:

- strong;

- moderate;

- weak;

- unknown.

Only Bora-specific historical data can eventually justify statistical
prediction.

**36. SPEED SIGNALS**

Possible positive speed indicators:

- staffing/recruiter-led;

- contract;

- temporary;

- immediate start;

- clear start window;

- small implementation team;

- actively recruiting;

- freshly verified vacancy.

Possible slow indicators:

- long posting age;

- major multi-stage program;

- apparent freeze;

- heavily delayed process;

- vague evergreen requisition.

Unknown stays unknown.

**37. COMPANY VIABILITY**

Use deeper viability checks only where justified.

Priority roles may include:

- recent layoffs;

- WARN notices;

- hiring-freeze news;

- material financial stress;

- obvious headcount contraction;

- current company events relevant to the role.

Do not run expensive research on every Efficient Apply job.

**38. APPLICATION CHANNEL**

Preferred where available:

1.  meaningful referral/warm route;

2.  direct employer application;

3.  legitimate recruiter/staffing submission;

4.  major job-board application;

5.  Easy Apply as useful supplemental channel.

Do not invent universal conversion multipliers.

Track Bora's own results.

Eventually:

Bora's data overrides generic internet averages.

**39. NETWORKING ENGINE**

Every strong opportunity asks:

**IS THERE A LOW-EFFORT HIGH-VALUE HUMAN ROUTE?**

Look for:

1.  existing relationship;

2.  Brandeis alum;

3.  Winter Walk relationship;

4.  FCAT/Fidelity relationship;

5.  recruiter;

6.  hiring manager;

7.  relevant team member;

8.  useful second-degree contact.

**40. NETWORKING INTENSITY**

**REJECT**

none.

**EFFICIENT APPLY**

0–1.

**APPLY**

usually 1.

**PRIORITY APPLY**

1–3.

Never find 3 people merely because the system says 3 is allowed.

**41. LINKEDIN FREE**

System must work without LinkedIn Premium.

Default:

connect selectively.

If accepted:

message.

Use scarce personalized notes selectively when the platform permits
them.

Do not hardcode a permanent monthly LinkedIn invitation-note number
because platform limits change.

Never automate:

- mass connections;

- bulk messages;

- scraping behavior violating platform rules.

**42. RÉSUMÉ PRINCIPLE**

The résumé is assembled from:

**VERIFIED EVIDENCE + APPROVED CLAIMS + ROLE PRIORITIES.**

It is not rewritten freely from scratch.

**43. ONE MASTER DESIGN**

Maintain one protected résumé template.

Do not maintain three independently drifting master résumés.

Each generated résumé is a derivative.

**44. IMMUTABLE RÉSUMÉ FIELDS**

Unless Bora deliberately changes the master:

- name;

- contact information;

- formal employers;

- formal titles;

- dates;

- education;

- fundamental visual format.

AI cannot change these.

**45. ADJUSTABLE RÉSUMÉ FIELDS**

The system may change:

- summary;

- bullet selection;

- bullet order;

- supported wording;

- skill ordering;

- selected projects;

- amount of space given to a relevant experience;

- removal of weaker material.

This is the heart of job-specific tailoring.

**46. RÉSUMÉ PATCH — NOT FREEHAND REWRITE**

Model returns a structured patch.

Example:

**SUMMARY**  
Replace module.

**WINTER WALK**  
Move bullet WW_BULLET_08 to position 1.

**MARKETMIND**  
Include MM_BULLET_04.

**LOANIQ**  
Remove.

**SKILLS**  
Move SQL before Python.

**GAP**  
Salesforce unsupported.

The renderer performs the actual document operation.

**47. RÉSUMÉ DIFF REVIEW**

Bora should not need to reread a whole résumé every time.

Display:

- ADDED

- REMOVED

- REWORDED

- REORDERED

- UNCHANGED

- GAP

- WARNING.

The diff must be reviewable quickly.

**48. KEYWORD RULE**

Use job terminology when it truthfully describes Bora's evidence.

Do not use unsupported keywords simply because ATS may like them.

Example:

Bora genuinely performed requirements elicitation.

JD says:

“requirements gathering.”

A truthful adaptation is allowed.

JD says:

“ServiceNow administration.”

No ServiceNow evidence exists.

Do not insert it.

**49. FINAL RÉSUMÉ CLAIM VALIDATOR**

Before export:

every new or modified factual résumé statement must have:

Claim_ID

or:

Evidence_ID(s) approved for direct use.

No lineage:

**FAIL.**

**50. RÉSUMÉ FORMAT VALIDATION**

Check automatically:

- page count;

- title preservation;

- dates;

- employers;

- section structure;

- bullet formatting;

- placeholders;

- excessive line growth;

- export success.

Do not solve overflow by making the résumé unreadably small.

**51. MASTER FILE PROTECTION**

The master résumé must never be modified by generation.

Process:

copy → patch → validate → export.

If generation fails:

delete/mark failed derivative.

Original master remains untouched.

**52. APPLICATION QUESTIONS**

Three classes.

**SAFE / REUSABLE**

- name;

- contact;

- education;

- employment facts;

- links.

**REVIEW**

- salary;

- start date;

- travel;

- location;

- relocation.

**ALWAYS HUMAN**

- current work authorization;

- future sponsorship;

- visa/immigration;

- legal attestations;

- criminal/background attestations;

- voluntary demographic/EEO answers;

- ambiguous declarations.

**53. NO AUTO-SUBMIT**

Permanent default:

the system does not submit applications autonomously.

Simplify/browser tools may fill repetitive fields.

Bora verifies and submits.

This prevents one bad automation from creating 50 bad external records.

**54. TOOL ARCHITECTURE — LOCKED**

Core operating model:

**CHATGPT WORK + CLAUDE CODE + CURSOR**

* ChatGPT Work = primary architect, research, semantic adjudication, truth/calibration, priority selection, market/career/application guidance, reasoning, sequencing, and final decision guidance;
* Claude Code = primary bounded implementation agent;
* Cursor = mandatory independent adversarial reviewer of consequential uncommitted diffs before commit/push (not the default primary builder).

Gemini is an optional, occasional non-coding strategic, directional, or
research second-opinion agent only.

Gemini is:

**NOT part of the coding execution or coding-review loop.**

No runtime or production workflow may depend on agreement from multiple models.

Deterministic validators remain the real enforcement layer.

Evidence wins over model opinion.

Bora retains consequential approval.

The system must remain fully operable if Claude Code or Gemini is unavailable.

**55. CHATGPT WORK — PRIMARY ARCHITECT & RESEARCH ENGINE**

ChatGPT Work is the main intelligence layer for:

- system architecture;

- research;

- semantic adjudication;

- truth and calibration;

- priority selection;

- market, career, and application guidance;

- reasoning;

- sequencing;

- evidence reasoning;

- job research;

- company research;

- market research;

- source checking;

- fit analysis;

- rule interpretation;

- résumé content reasoning;

- ambiguity resolution;

- debugging plans;

- final decision guidance;

- final quality decisions.

ChatGPT should maintain this Project with:

- Blueprint;

- evidence material;

- project instructions;

- important reference files.

ChatGPT Projects support stored files and project-specific instructions
so recurring work can preserve the relevant workspace context.

However:

ChatGPT memory is not the authoritative system database.

The repository remains authoritative.

**56. CURSOR — MANDATORY ADVERSARIAL REVIEWER**

Cursor is the mandatory independent adversarial reviewer for consequential
uncommitted diffs before commit or push.

Cursor is **not** the default primary builder after governance sync.

Responsibilities:

- independent adversarial review of consequential uncommitted diffs;

- proving implementation wrong from the actual repository and diff;

- regression and fixture verification where review scope requires it;

- structured review verdicts before local commit/push.

Do not use Cursor as the default implementation owner.

Do not treat a passing self-review as sufficient for consequential changes.

Cursor supports version-controlled Project Rules under .cursor/rules and
project-level AGENTS.md, specifically for persistent repository
instructions.

**57. GEMINI — OPTIONAL, OCCASIONAL NON-CODING SECOND OPINION ONLY**

Gemini is an optional, occasional non-coding strategic, directional, or
research second-opinion agent only.

In this governance model:

- optional means never required;

- occasional means the expected frequency of use, not a workflow
  dependency.

Gemini is not a coding executor, coding reviewer, builder backup, or
required verifier in the implementation loop.

Use Gemini when a non-coding second opinion is genuinely useful, for
example:

- strategic direction;

- market or research framing;

- high-level product/priority tradeoffs;

- non-coding research second opinions.

Do not use Gemini as:

- primary architect;

- primary builder;

- primary bounded implementation agent;

- independent adversarial reviewer before commit/push;

- independent coding reviewer;

- independent evidence repository auditor;

- backup coding/build agent;

- required second reviewer for code, schemas, validators, or evidence records.

Gemini should not silently become a second primary architect or enter
the coding execution/review loop.

If Gemini CLI is used for occasional strategic/research sessions,
GEMINI.md may provide non-coding project context and must point back to
BLUEPRINT.md.

**58. CLAUDE CODE — PRIMARY BOUNDED IMPLEMENTATION AGENT**

Claude Code is the primary bounded implementation agent.

Use Claude Code for:

- repository implementation within approved milestones;

- schemas;

- validators;

- tests;

- refactoring within approved scope;

- debugging;

- local tooling;

- harder-code escalation on implementation tasks;

- bounded fixes after adversarial review findings.

Claude Code must not become:

- the primary architect;

- the owner of core architecture;

- the owner of the application or evidence database;

- the default independent adversarial reviewer before commit/push;

- a required runtime dependency.

If Claude Code is unavailable:

implementation may be deferred, but deterministic validators and Bora's
approval gates still apply. Cursor adversarial review remains required
before commit/push when implementation work is present.

**59. AI TEAM MODEL**

Default:

**ChatGPT Work**

Primary architect + research + semantic adjudication + truth/calibration
+ priority selection + market/career/application guidance + reasoning +
sequencing + final decision guidance.

**Claude Code**

Primary bounded implementation agent + harder-code escalation on
implementation tasks.

**Cursor**

Mandatory independent adversarial reviewer of consequential uncommitted
diffs before commit/push.

**Gemini**

Optional, occasional non-coding strategic / directional / research
second-opinion agent only.

This is deliberately not:

four AIs all rewriting the same thing.

**60. MODEL INDEPENDENCE**

No core stage may require agreement from multiple models.

That destroys speed and raises cost.

Default high-value flow:

**GENERATE / DECIDE**

ChatGPT Work or designated reasoning component.

**BUILD**

Claude Code (bounded implementation within approved milestones).

**VALIDATE**

Deterministic code / schemas / tests.

**ADVERSARIAL REVIEW BEFORE COMMIT/PUSH**

Cursor for consequential uncommitted diffs.

**OCCASIONAL NON-CODING SECOND OPINION**

Gemini only when genuinely useful.

**61. WHEN CURSOR ADVERSARIAL REVIEW IS REQUIRED**

Do not Gemini-review coding work or every Efficient Apply résumé.

Use Cursor independent adversarial review before commit/push for
consequential uncommitted diffs, including:

- requirement-matcher or semantic-capability changes;

- claim/evidence/resume/immigration logic changes;

- schema or validator changes;

- Golden Test or milestone-behavior changes;

- newly created or materially changed claim/evidence records;

- disputed OPT interpretation before consequential use;

- change to system architecture;

- change to forbidden-claim rules;

- Golden Test failure remediation;

- material evidence-repository or milestone implementation.

Routine reused approved modules with no consequential diff:

deterministic validation may be enough.

This preserves speed while keeping review on consequential changes.

Gemini is not required for these coding/evidence cases.

**62. WHEN GEMINI MAY BE USED**

Examples:

- strategic prioritization second opinion;

- market or research framing;

- non-coding directional tradeoffs;

- occasional research challenge outside the coding loop.

Gemini is an optional, occasional non-coding strategic, directional, or
research second-opinion agent only.

Not a workflow dependency.

Not a coding verifier.

**63. AI OUTPUT SCHEMA**

Production AI steps return structured data.

Do not let downstream code parse free-form essays.

Example:

{

"job_id": "JOB\_...",

"decision": "APPLY",

"requirements": \[\],

"evidence_matches": \[\],

"gaps": \[\],

"unknowns": \[\],

"resume_patch": \[\],

"network_actions": \[\],

"warnings": \[\]

}

Validate schema using strict JSON Schema validation.

Every structured AI output payload must pass the repository's applicable JSON Schema before it may reach any renderer, résumé patcher, exporter, Google Sheets writer, or other downstream component.

Schema validation is a deterministic code gate, not an AI self-check.

Invalid payload:

**BLOCK DOWNSTREAM PROCESSING.**

Failure:

retry.

Repeated failure:

PROCESSING_ERROR.

**64. NO SILENT FILLING**

Missing field must never become a plausible value.

Examples:

salary missing  
→ null.

employment type unclear  
→ UNKNOWN.

E-Verify not found  
→ NOT_FOUND_IN_PUBLIC_SEARCH.

outcome not measured  
→ UNKNOWN.

Never:

“probably.”

**65. CODE VS AI RESPONSIBILITY**

Use deterministic code whenever the task can be expressed reliably.

**CODE**

- IDs;

- duplicates;

- dates;

- file paths;

- application state;

- schema validation, including strict JSON Schema enforcement before any structured AI payload reaches rendering or downstream writes;

- claim lineage;

- immutable-field checks;

- page count;

- filenames;

- follow-up dates;

- duplicate applications;

- batch routing;

- caching;

- audit log.

**AI**

- interpreting JD language;

- semantic evidence matching;

- distinguishing preferred/hard requirements;

- résumé wording;

- company context;

- networking reasoning;

- ambiguous fit.

AI should not perform deterministic work simply because it can.

**66. REPOSITORY STRUCTURE**

Recommended:

bora-employer-pipeline/

│

├── BLUEPRINT.md

├── AGENTS.md

├── GEMINI.md

├── README.md

├── CHANGELOG.md

│

├── .cursor/

│ └── rules/

│ ├── truth.mdc

│ ├── architecture.mdc

│ ├── resume.mdc

│ ├── opt-safety.mdc

│ ├── testing.mdc

│ └── data-integrity.mdc

│

├── evidence/

├── claims/

├── prompts/

├── schemas/

├── src/

├── tests/

├── golden-tests/

├── docs/

└── logs/

**67. AGENTS.MD**

AGENTS.md contains the short non-negotiable operating contract.

It points to:

BLUEPRINT.md.

It should not duplicate all 100+ blueprint rules.

Cursor documentation itself recommends concise, focused rules and allows
AGENTS.md plus more structured .cursor/rules.

**68. CURSOR RULES**

Critical .mdc rules should use:

alwaysApply: true

where appropriate.

Examples:

**truth.mdc**

No unsupported facts.

**resume.mdc**

Only permitted slots.

**data-integrity.mdc**

Never overwrite evidence or submitted application history.

**testing.mdc**

Run tests before declaring done.

**architecture.mdc**

No silent architecture changes.

**69. GEMINI.MD AND CLAUDE.MD**

GEMINI.md provides non-coding project context for occasional Gemini
strategic/research second-opinion sessions and must point back to
BLUEPRINT.md.

CLAUDE.md, if present, provides short Claude Code bounded-implementation
instructions and must point back to BLUEPRINT.md.

Where practical, avoid manually maintaining divergent rule sets.

The goal:

one rule source.

Multiple agents with distinct roles.

**70. NO RULE DUPLICATION DRIFT**

Do not maintain five independently rewritten copies of the Blueprint.

Preferred:

BLUEPRINT.md

is canonical.

Agent files contain:

- short role-specific instructions;

- explicit reference to Blueprint;

- only tool-specific additions.

**71. INSTRUCTION PRECEDENCE**

If conflict occurs:

1.  Bora's explicit current instruction;

2.  Blueprint;

3.  approved architecture decision;

4.  validator/schema;

5.  tool-specific rule;

6.  model preference.

A model's “better idea” is last.

**72. ARCHITECTURE DECISION REQUIRED**

If an agent believes a locked rule must change:

do not change it.

Output:

**ARCHITECTURE_DECISION_REQUIRED**

with:

- conflict;

- current rule;

- proposed change;

- reason;

- risk;

- alternatives.

Bora decides.

**73. CODING HARD RULES**

1.  Never disable a failing validator merely to finish a feature.

2.  Never rewrite Golden Test expectations because new code fails them
    unless the expected behavior itself was deliberately changed.

3.  Never automatically delete original evidence.

4.  Never mutate historical submitted-application records.

5.  Never allow résumé text without lineage.

6.  Never store API keys in repository files.

7.  Never modify the master résumé in place.

8.  Never introduce a paid dependency without approval.

9.  Never silently replace Google Sheets with a database.

10. Never let an agent modify immigration logic casually.

11. Never execute destructive operations without rollback.

12. Never run two autonomous coding agents against the same critical
    branch simultaneously.

13. Never bypass tests because the change is “small.”

14. Never hide exceptions/errors from Bora.

**74. GIT**

All code lives in Git.

Minimum:

main

plus feature branches when useful.

Commit before major changes.

Commit after passing milestone.

Meaningful commit messages.

Rollback must be practical.

**75. PRIMARY STORAGE**

V1:

**Google Sheets + Google Drive.**

Development:

**Git.**

Do not introduce:

Postgres  
Firebase  
Supabase  
BigQuery  
vector database

until actual usage demonstrates Sheets is a bottleneck.

Cheap and boring wins.

**76. INITIAL SHEET TABS**

Start with seven.

**SETTINGS**

**JOBS**

**EVIDENCE**

**CLAIMS**

**APPLICATIONS**

**NETWORK**

**LOG**

Add tabs only from demonstrated need.

**77. DOCUMENT STORAGE**

Drive:

Bora Employer Pipeline/

00 Blueprint/

01 Evidence/

02 Resume/

Master/

Generated/

03 Applications/

04 Interviews/

05 Archive/

**78. COMPANY CACHE**

Do not research the same employer from zero for five openings.

Store reusable company facts with:

- Company_ID;

- verified sources;

- accessed date;

- E-Verify status;

- international-hiring signals;

- location;

- notes.

Time-sensitive fields expire.

**79. SOURCE EXPIRATION**

Example policies:

Job live status:  
verify immediately before application.

Job description:  
snapshot at ingest.

E-Verify:  
recheck when strategically important.

H-1B history:  
periodic refresh.

Company general description:  
cache longer.

Tool pricing/features:  
verify before purchase.

Immigration:  
recheck before consequential action.

**80. RESEARCH SOURCE TIERS**

**TIER 1**

- government;

- employer;

- Brandeis;

- official platform/vendor documentation.

**TIER 2**

- strong industry/recruiting datasets;

- reputable institutions;

- recognized professional research.

**TIER 3**

- reputable reporting;

- secondary databases.

**TIER 4**

- Reddit;

- Glassdoor;

- community commentary.

Tier 4 is useful for:

patterns and experience.

Not authoritative facts.

**81. INTERNET STATISTIC RULE**

Do not hardcode precise internet conversion claims into product logic
unless source quality warrants it.

Examples that should usually remain **heuristics**, not constants:

- referrals are X times better;

- Easy Apply response = X%;

- careers page = X times better;

- first 25 applicants = X times better.

Store the directional lesson.

Then measure Bora's own funnel.

**82. APPLICATION TIMING**

Priority:

apply promptly to verified strong roles.

Do not delay a good application for:

“perfect Tuesday 9:17 AM timing.”

Do not rush so much that evidence validation fails.

**83. BATCH MODE**

Bora can ingest 50+ roles.

System processes automatically.

Review screen:

- number rejected;

- Efficient Apply;

- Apply;

- Priority;

- Watch;

- processing errors.

Bora can batch-approve qualification results.

**84. GATE 1 — BATCH PURSUIT APPROVAL**

Instead of:

50 separate confirmations,

allow:

“Proceed with these 23.”

Human control stays.

Friction falls.

**85. GATE 2 — RÉSUMÉ APPROVAL**

System validates first.

Bora reviews:

diff.

For reusable approved modules with no semantic changes:

review can be extremely fast.

For new claims:

more scrutiny.

**86. GATE 3 — SUBMIT**

External submission stays human-controlled.

This remains permanent V1 architecture.

**87. APPLICATION-READY PACKAGE**

For every accepted role:

**ROLE**

**COMPANY**

**LIVE STATUS**

**DECISION**

**WHY**

**OPT/MSBA**

**STEM QUALITY**

**TOP EVIDENCE**

**GAPS**

**RÉSUMÉ DIFF**

**GENERATED PACKAGE (DOCX default; PDF only on explicit
employer/application-system override — §140.1/§140.7)**

**NETWORK ACTION**

**MANUAL APPLICATION WARNINGS**

**APPLY LINK**

Goal:

under one minute to understand.

**88. THROUGHPUT DEFINITION**

V1 goal:

**≥50 ROLE CHECKS/DAY.**

Stretch:

**up to 50 APPLICATION-READY PACKAGES/DAY**

when enough roles qualify.

Do not define success as:

50 submissions regardless of quality.

**89. PERFORMANCE GOAL**

Manual job-search bottleneck should move from:

**hours per set of applications**

to:

**minutes of review per qualified role.**

The system is worth building if it substantially removes:

repeated research + repeated résumé reasoning.

**90. COST GOAL**

V1:

**approximately \$0 in new mandatory monthly software.**

Already-available tools can be used.

Simplify Free may remain.

No automatic subscriptions to:

- LinkedIn Premium;

- Teal;

- Huntr Pro;

- Jobscan;

- mass-apply tools;

- extra SaaS.

**91. API COST RULE**

If API automation later becomes useful:

measure actual marginal cost.

Start with small batches.

Cache.

Use deterministic logic first.

Do not send whole evidence repositories unnecessarily with every
request.

**92. PRIVACY**

Application OS should not unnecessarily expose:

- passport;

- immigration documents;

- SSN;

- financial information;

- sensitive employer data.

Only minimum job-search facts enter AI contexts.

Do not store sensitive immigration scans in the job-engine repository.

**93. DATA MINIMIZATION**

Models receive only what is necessary.

Résumé generation should receive:

relevant evidence subset,

not the entire Bora archive every time.

This improves:

- cost;

- speed;

- context clarity;

- reliability.

**94. PROMPT VERSION CONTROL**

Prompts live in repository files.

Example:

prompts/

job_extract_v1.md

qualification_v1.md

evidence_match_v1.md

resume_patch_v1.md

verifier_v1.md

Log prompt version with each output.

**95. MODEL VERSION TRACKING**

Where available log:

- provider;

- model;

- prompt version;

- timestamp.

If model behavior changes later:

we can diagnose regression.

**96. GOLDEN TEST SET**

Create at least 20 jobs over time.

Must include:

- perfect BSA fit;

- implementation fit;

- Data Ops;

- RevOps;

- SalesOps;

- data-sales role;

- contract role;

- remote;

- Boston hybrid;

- senior reject;

- software-engineer reject;

- unsupported Salesforce;

- U.S.-regulatory trap;

- H-1B ambiguity;

- E-Verify not-found case;

- stale posting;

- closed role;

- fresh direct role;

- vague JD;

- project-selection test.

Expected outputs are stored.

**97. ADVERSARIAL TESTS**

Explicitly try to make the system hallucinate.

Example:

JD says:

“Salesforce.”

Evidence has none.

Expected:

NONE.

Another:

“five years U.S. banking regulation.”

Evidence has Bulgarian banking.

Expected:

PARTIAL_TRANSFER

not:

match.

Another:

“built production ML pipelines.”

MarketMind exists.

Expected:

gap.

**98. REGRESSION RULE**

Before material release:

run Golden Tests.

Unexpected changes require review.

Do not ship because:

“the new AI output looks better.”

**99. SYSTEM AUDIT**

Each run logs:

- Job_ID;

- model;

- evidence version;

- source set;

- qualification;

- patch;

- validator results;

- human approval;

- final résumé file.

AI chat history is not the audit database.

**100. FAILURE STATES**

Possible:

- INGEST_ERROR

- SOURCE_UNAVAILABLE

- JOB_STATUS_UNCLEAR

- SCHEMA_ERROR

- MODEL_ERROR

- EVIDENCE_CONFLICT

- CLAIM_VALIDATION_FAILED

- RESUME_RENDER_FAILED

- ARCHITECTURE_DECISION_REQUIRED

Never silently convert errors into “complete.”

**101. RETRY RULE**

Automated retry:

limited.

If repeated failure:

surface error.

Do not loop forever.

Do not invent fallback content.

**102. MODEL DISAGREEMENT**

If ChatGPT Work's guidance and Cursor's adversarial review of an
uncommitted consequential diff disagree materially on implementation,
audit findings, or semantic safety:

**HOLD.**

Options:

- inspect evidence;

- Bora decides;

- request a narrower Cursor re-review against specific evidence/rules.

Cursor adversarial review does not automatically win.

If Claude Code's implementation and Cursor's adversarial review of an
uncommitted consequential diff disagree materially:

**HOLD.**

- ChatGPT Work adjudicates semantics/evidence;

- Bora decides if still unresolved;

- never resolve by model voting.

Neither Claude Code implementation nor Cursor adversarial review
automatically wins.

Evidence wins.

Deterministic validators win over model opinion where they apply.

An occasional Gemini non-coding strategic second opinion does not
resolve coding/evidence disputes and must not be treated as coding-review
authority.

**103. FOLLOW-UP ENGINE**

Track:

- application date;

- recruiter interaction;

- networking attempt;

- interview;

- last action;

- next action;

- follow-up due;

- closed/rejected.

System can generate suggestions.

Bora controls communication.

**104. FOLLOW-UP CADENCE**

Avoid rigid universal cadence.

Different cases differ.

System should consider:

- recruiter instructions;

- interview date;

- application age;

- active relationship;

- urgency;

- company timeline.

No spam.

**105. LEARNING LOOP**

Eventually Bora's actual results become the most useful data.

Analyze:

- role family;

- source;

- location;

- remote/hybrid;

- employment type;

- résumé module;

- networking used;

- company size;

- cold/warm;

- recruiter screens;

- interviews;

- offers.

**106. STRATEGY CHECKPOINT**

Review after:

**15 submitted applications OR 10 calendar days,**

whichever comes first.

Also larger review after:

40+ serious applications.

Do not overhaul strategy based on three rejections.

**MARKET-SOFTNESS / SEASONALITY SIGNAL**

At a strategy checkpoint, if **40% or more of checked roles** fall into **POSSIBLY_STALE** or **WATCH**, classify that pattern as an external market-softness or seasonality signal for diagnostic purposes rather than treating it as evidence of a résumé or targeting failure.

This signal does not prove the market is soft and does not prevent separate investigation of targeting, résumé quality, immigration filters, or channel mix. It exists to prevent the system from silently diagnosing an external availability pattern as an internal candidate failure.

**107. CALLBACK TROUBLESHOOTING**

If response is weak:

investigate separately:

1.  role targeting;

2.  immigration filters;

3.  résumé/evidence presentation;

4.  channel mix;

5.  seniority mismatch;

6.  timing/freshness;

7.  application questions;

8.  market conditions.

Do not automatically assume:

“ATS problem.”

**108. SIMPLIFY**

Simplify remains optional infrastructure for:

- discovery;

- autofill;

- application convenience.

It does not control:

- evidence;

- résumé logic;

- fit;

- immigration interpretation;

- truth;

- networking;

- final submit.

We are not spending time rebuilding commodity autofill.

**Commodity tool / adapter rule.** The permanent, owned durable core of
this system is: **Employer Truth, Candidate Truth, Match Truth, Pursuit
Truth, Package Truth, Outcome Truth.** Commodity mechanics — job
discovery/search, LLM drafting, browser/form autofill, email/calendar
workflow, and similar — should normally use existing, replaceable
external tools when those tools are good enough. Do not canonically lock
a specific vendor as architecture. Do not build or integrate a provider
merely because its API is easy. Build or integrate a provider only when
live usage demonstrates enough Bora value to justify the implementation
and ongoing maintenance cost. External providers remain replaceable
adapters around the owned truth core; they never become the truth core
themselves.

**Discovery boundary (concept, not implemented by this milestone).**
External discovery produces untrusted leads only. Conceptual boundary:
external source → `DiscoveryLead` (untrusted lead representation) →
dedupe/resolution → fresh first-party verification → Employer Truth. No
external job-board representation, recommendation score, vendor match
score, or discovery result becomes Employer Truth or Match Truth without
independent first-party verification.

**109. WHAT THE OS REPLACES**

It replaces repeated manual work:

- rereading JDs;

- rethinking Bora's history;

- fighting AI over formatting;

- fighting AI over invented experience;

- project-selection decisions;

- repeated company research;

- repeated gap analysis;

- résumé reformatting;

- missed networking routes;

- inconsistent prioritization.

**110. WHAT IT DOES NOT REPLACE**

Do not rebuild:

- LinkedIn;

- employer ATS;

- Gmail;

- Google Docs;

- Drive;

- job boards;

- Simplify's browser autofill.

Only build differentiated intelligence and control.

**111. CORE COMMAND — MILESTONE 1**

First reliable engine:

analyze_job(job_input)

Output:

- Job_ID

- live-status result

- structured requirements

- OPT/MSBA assessment

- evidence mappings

- gaps

- lane

- decision

- proposed résumé patch

- network intensity

- warnings.

Test against 20 jobs.

**112. MILESTONE 2**

generate_resume(Job_ID)

Must:

1.  retrieve approved patch;

2.  copy master;

3.  modify allowed slots;

4.  validate lineage;

5.  validate immutable fields;

6.  test formatting;

7.  export submitted artifact (DOCX default; PDF only on explicit
    employer/application-system override — §140.1);

8.  log output.

**113. MILESTONE 3**

process_batch(50)

Must reliably:

- ingest;

- deduplicate;

- extract;

- filter;

- evidence-match;

- classify;

- show compact review queue.

No unnecessary résumé generation for rejects.

**114. MILESTONE 4**

Application-ready workflow:

batch approval → résumé generation → diff → network recommendation →
application handoff.

At this point:

system begins replacing substantial manual effort.

**115. MILESTONE 5**

Outcome learning.

Use real application data to tune:

- lane thresholds;

- role priorities;

- channel priorities;

- evidence modules.

Do not tune truth constraints.

Those remain fixed.

**116. DEVELOPMENT APPROACH**

Build in vertical slices.

Bad:

build entire database → entire résumé engine → entire network engine →
finally test.

Good:

one real job → full pipeline → test.

Then:

10. 

Then:

20. 

Then:

50. 

**117. MVP FIRST**

MVP needs:

- evidence registry;

- claim validation;

- job parser;

- fit classification;

- résumé patch;

- document generator;

- audit log.

Fancy dashboard is optional.

Reliability before UI polish.

**118. CURSOR BUILD PROCESS**

For each feature:

1.  read Blueprint/rules;

2.  inspect existing implementation;

3.  propose smallest change;

4.  implement;

5.  test;

6.  run relevant Golden Tests;

7.  show diff;

8.  commit after approval/passing state.

No giant autonomous “build the whole project” prompt.

**119. CHATGPT BUILD PROCESS**

Use ChatGPT Work for:

- feature specification;

- schemas;

- edge cases;

- architecture;

- test-case design;

- external research;

- logic reviews;

- bug diagnosis;

- verification strategy.

Then pass bounded implementation tasks to Claude Code.

**120. CLAUDE CODE IMPLEMENTATION PROCESS**

Use Claude Code for bounded implementation within approved milestones:

“Implement the approved smallest reliable diff.”

“Add or update tests required by the milestone.”

“Run the repository's non-interactive test commands.”

“Surface blockers instead of guessing past locked rules.”

Not:

“Rebuild the entire architecture your way.”

“Implement beyond the approved milestone scope.”

**121. CURSOR ADVERSARIAL REVIEW PROCESS**

Use Cursor before commit/push for consequential uncommitted diffs:

“Independent adversarial review of this uncommitted diff.”

“Prove the implementation wrong from the actual repository state.”

“Verify regressions, fixtures, and claim/evidence safety.”

Not:

“Become the default implementation owner.”

“Commit or push without Bora's explicit authorization when review-only.”

**122. GEMINI SECOND-OPINION PROCESS**

Use Gemini — an optional, occasional non-coding strategic, directional,
or research second-opinion agent only — for example:

“Second opinion on strategic priority tradeoffs.”

“Challenge this market/research framing.”

“Directional review outside the coding loop.”

Not:

“Review this coding diff.”

“Audit these evidence JSON records as coding verifier.”

“Act as backup builder.”

“Rebuild the entire architecture your way.”

System cannot depend on Gemini.

**123. PERIODIC MULTI-MODEL AUDIT**

Optional:

every major milestone or periodically:

select random outputs.

ChatGPT Work → primary reasoning/decision guidance.

Claude Code → bounded implementation when needed.

Cursor → adversarial review of consequential uncommitted diffs before
commit/push.

Compare.

Record discrepancies.

Improve rules if a generalizable failure appears.

No stage may require agreement from all models.

**124. HARD PRODUCT RULES**

1.  Evidence before résumé.

2.  Unknown stays unknown.

3.  No invented impact.

4.  No invented tools.

5.  No title fabrication.

6.  No immigration guessing.

7.  No automatic external submission.

8.  No silent architecture change.

9.  No mass networking spam.

10. No unsupported keyword stuffing.

11. No model is trusted as database.

12. Code enforces invariants.

13. AI performs semantic reasoning.

14. All generated material has provenance.

15. Bora retains consequential control.

**125. HARD SCALE RULE**

Throughput cannot weaken truth.

If the only way to process 50 jobs is to stop validating:

process fewer.

But architecture should be optimized so truth validation itself is fast
enough for 50+ checks.

**126. REALISTIC PROMISE**

We are not promising:

“50 perfect applications/day.”

We are building toward:

**50+ VERIFIED ROLE CHECKS/DAY**

and potentially:

**dozens of application-ready packages/day**

with dramatically less manual work than Bora currently performs.

External ATS submission remains variable.

**127. SUCCESS CONDITION**

This system is worth keeping if, after real usage, it:

- materially reduces Bora's time per serious application;

- preserves résumé quality;

- produces zero known fabricated claims;

- finds relevant jobs Bora would otherwise miss;

- improves consistency;

- enables significantly higher application throughput;

- generates useful networking opportunities;

- helps produce recruiter screens/interviews;

- reduces false rejects and false positives;

- keeps human review load useful rather than exhausting;

- helps produce applications submitted, recruiter responses, screens,
  interviews, and offers.

If it merely produces a pretty dashboard:

it failed.

Milestone count and code volume are not primary success metrics. Tests
protect reliability; green tests alone do not establish project success —
real-world operational results (above) do.

**128. RELATION TO BORA'S LONG-TERM BUSINESS**

This project is also a real internal implementation of Bora's broader
methodology.

It demonstrates:

**BUILD**

real workflow and bounded automation.

**VERIFY**

provenance, tests, adversarial checks, fail-closed rules.

**OPERATE**

logs, monitoring, versioning, repeatable operation.

Do not turn it into a portfolio gimmick while Bora needs it
operationally.

Its first job is:

help Bora get hired.

**129. MASTER PRINCIPLE**

**AI proposes.**

**Evidence grounds.**

**Code constrains.**

**Claude Code implements within approved milestones when needed.**

**Cursor adversarially reviews consequential uncommitted diffs before commit/push.**

**Gemini is an optional, occasional non-coding strategic, directional, or research second-opinion agent only.**

**Bora decides.**

**130. SYSTEM MOTTO**

**Research the opportunity.**

**Retrieve the truth.**

**Expose the gaps.**

**Present the strongest relevant evidence.**

**Automate repetition.**

**Verify before action.**

**Keep Bora in control.**

**131. NEW CHAT / AGENT BOOT PROMPT**

Use this whenever a new build agent/session needs context:

**You are working on Bora Employer Pipeline OS. Before doing any work,
read BLUEPRINT.md and the applicable repository rules. BLUEPRINT.md is
the project's authoritative source of truth. The system is being built
specifically for Bora Chaush, who holds a completed, awarded Brandeis MS
in Business Analytics per his own direct human attestation dated
2026-09-03 (physical diploma pending receipt; STEM/CIP designation
remains not independently ingested; see
`evidence/education/EDU_BRANDEIS_AWARDED_ATTESTATION_001.json`),
seeking legitimate U.S. employment quickly while building toward
Reliable AI-Enabled Business Systems — BUILD → VERIFY → OPERATE. The
Evidence Repository, not Bora's résumé and not model memory, is the
factual source of truth. Never invent experience, tools, metrics,
outcomes, company facts, sources, immigration conclusions or hiring
probabilities. UNKNOWN stays UNKNOWN. Preserve evidence provenance and
forbidden-claim boundaries. AI may propose semantic decisions;
deterministic code must enforce invariants. ChatGPT Work is the primary
architecture/research/semantic-adjudication/truth-calibration/priority-
selection/market-career-application-guidance/reasoning/sequencing and
final-decision-guidance agent; Claude Code is the primary bounded
implementation agent; Cursor is the mandatory independent adversarial
reviewer of consequential uncommitted diffs before commit/push and is
not the default primary builder; Gemini is an optional, occasional
non-coding strategic, directional, or research second-opinion agent only
and is not part of the coding execution or coding-review loop. No runtime
workflow may depend on multi-model agreement. Evidence wins over model
opinion. Bora retains consequential approval. The complete system must
remain operable without Claude Code or Gemini. Never weaken validation,
Golden Tests, provenance, human approval gates or safety rules merely to
increase throughput. Never silently change architecture. If a locked rule
blocks implementation, return ARCHITECTURE_DECISION_REQUIRED with the
conflict and alternatives. Make the smallest reliable change, test it,
preserve rollback, and record material changes.**

**132. CANDIDATE-FACING REAL-WORLD STANDARD (LOCKED)**

Bora has explicitly approved the following as permanent product and
candidate-facing standards, durable across future chats and agents.

**Permanent product goal (reinforced).** This is Bora's
evidence-controlled employer/application operating system. It is not
another Simplify, a mass-apply bot, an ATS-score optimizer, a generic AI
resume writer, a keyword-stuffing system, or an engineering project whose
goal is to perfect matcher logic forever. Its purpose is to materially
reduce Bora's manual job-search workload and produce real-world results:
interviews, offers, income, experience, references, and useful
professional relationships.

**Build philosophy.** After each closed milestone, return to real jobs
and end-to-end controls. Identify the largest materially wrong or missing
real-world outcome. Do not preselect another code patch. Stop improving
an area once further work no longer materially improves application
decisions or job-search outcomes. Attack the common weaknesses of generic
AI/vibe-coded tools: invented facts, false confidence, fragile
happy-path behavior, generic output, hidden assumptions, stale employer
information, unclear provenance, overfitting to keywords, inability to
distinguish UNKNOWN from disproven facts, poor handling of real-world
application gates, difficult manual review, and automation without
validation. Prefer the smallest useful reliable system over feature
volume.

**Real-world truth model.** Five layers: (1) **Employer truth** — what
the employer actually says, whether the role is really open, who the
legal employer is, requirements/preferences, location/work mode,
application gates, verified compensation, and public
work-authorization/sponsorship information. (2) **Candidate truth** —
verified Evidence, Experiences, approved Claims/modules, known
constraints, and explicit UNKNOWNs. (3) **Match truth** — what is
actually supported, unsupported, adjacent, or UNKNOWN between employer
and candidate truth. (4) **Pursuit truth** — whether the opportunity is
worth Bora's time given realistic hiring probability, hiring speed,
work-authorization practicality, income, location/work mode, evidence
strength, U.S. credibility, learning/network value, longer-term
direction, and opportunity cost. (5) **Package truth** — the strongest
honest presentation of already-supported candidate truth for a role Bora
has decided to pursue. Package generation must never repair a bad match
by inventing or silently upgrading candidate capability.

**Research standard.** Ground material employer/market conclusions in
current, verifiable evidence when practical, per the source tiers in
Section 80. Distinguish verified fact, source-reported claim, inference,
recommendation, and UNKNOWN. Do not turn expert opinion, a market trend,
or recruiter commentary into a universal employer rule. Market/trend
research may guide ranking and prioritization, but a current
employer-specific decision must use employer-specific evidence whenever
it is available — broad recruiter or market trends must never override a
real posting's own terms.

**Candidate-facing writing standard.** Applies to resumes, cover letters,
application answers, recruiter messages, networking outreach,
professional summaries, and other candidate-facing application text. Use
plain, natural American business English: professional, calm, specific,
concrete nouns and real systems/actions/outcomes, concise enough for a
busy hiring manager to understand quickly, employer terminology only when
truthful, no inflated AI/corporate hype, no unnecessary jargon, no fake
enthusiasm, no unsupported adjectives or grandiose transformation
language, and avoid repetitive AI-like sentence structures. Metrics must
be verified or safely deterministic only — never invented merely because
quantified bullets are preferred. Optimize for truthful, natural
communication by a real candidate, not for defeating AI detectors; the
goal is evidence-backed authenticity, not detector evasion.

**Punctuation — Bora's explicit preference.** Do not use em dashes (—) in
candidate-facing resume/application text. Prefer ordinary punctuation.
When a dash is genuinely useful, use the normal hyphen character: -. Do
not replace ordinary punctuation with decorative em dashes. This is
Bora's explicit style preference, not a claim that em dashes universally
prove AI authorship.

**Resume/package safety (reinforces Sections 42–51 and
`.cursor/rules/resume.mdc`).** Every meaningful factual candidate-facing
statement must remain traceable to approved evidence/Claims/modules under
the existing architecture. Tailoring may select, reorder, emphasize,
truthfully reword, choose projects, and reorder supported skills.
Tailoring may not manufacture fit, convert adjacency into equivalence,
turn UNKNOWN into competency, add unsupported technologies, invent
achievements/metrics, or rewrite formal history for keyword matching.
Candidate-facing claims must additionally respect each Claim's
`forbidden_contexts`, limitations, human-approval state, and intended
reuse scope — traceability to a `Claim_ID` is necessary but not
sufficient; the claim's own boundaries govern whether and how it may be
used. The resume/package generator must not override qualification
truth.

**UX / practical value.** The system must be easy for Bora to review and
operate. Prefer clear reasons, visible evidence, visible UNKNOWNs/gaps, a
concise recommended action, fast diffs, exact submitted-version
traceability, minimal repeated manual entry, and deterministic validation
where possible. Success is not "generated lots of text." Success is less
manual work, fewer materially wrong decisions, faster identification of
real worthwhile roles, credible application packages, better ability to
act on opportunities, and real interviews, offers, income, experience,
references, and useful professional relationships.

**133. REAL-WORLD OPERATION AND CALIBRATION DOCTRINE (LOCKED)**

Bora has explicitly approved the following as permanent, durable
operating doctrine, earned through real production milestones and real
job-market controls, not a hypothetical.

**Operate while building.** Development and real job-search operation
run in parallel. Do not wait for architectural completeness before using
the system on real opportunities. The system should be operated now,
with engineering responding to observed needs, not the reverse.

**Build-economy gate.** A new feature or capability is justified only if
at least one is true: (A) it fixes a demonstrated, reproduced material
reliability/truth defect; or (B) it materially reduces Bora's live
search/application workload. Otherwise, defer it. Do not build ontology
breadth, provider breadth, generic platform features, integrations, UI,
automation, or architectural completeness merely because they are
possible or convenient.

**Real-world calibration tiers.** Exactly three levels, never collapsed
into one another: **HARD CORRECTION** — a reproduced source,
representation, or deterministic defect; may justify implementation.
**CALIBRATION SIGNAL** — repeated real outcomes suggesting ranking,
evidence-resolution priorities, package emphasis, discovery-channel
priority, or workflow allocation should be investigated; requires
investigation before any consequential semantic change, and does not
itself rewrite truth. **ANECDOTE** — one rejection, silence, recruiter
response, screen, or interview; record it; do not redesign the system
around it.

**Outcomes do not rewrite truth.** Real-world outcomes may calibrate
pursuit ranking, role-family emphasis, discovery-channel priority,
application effort allocation, package emphasis among already-supported
Claims, evidence-resolution priorities, and workflow efficiency. Outcomes
do **not** independently convert: `UNKNOWN` → `SUPPORTED`; `UNKNOWN` →
`NONE`; requirements satisfied → degree conferred; silence → sponsorship
or work-authorization policy; adjacency → experience; rejection → proof
Candidate lacks a capability; interview → proof an unsupported Claim was
valid. Employer Truth, Candidate Truth, and Match Truth each require
their own independent evidence, regardless of any outcome.

**Human consequential control (summary — see
`docs/decisions/ADR-PURSUIT-APPROVAL-BOUNDARY-V1.md` for full detail and
rationale).** `Job.decision`/`Job.lane` are system recommendations, never
Bora's explicit pursuit authorization. Pursuit authorization remains a
separate, human-controlled state. A materially changed opportunity must
never silently inherit stale pursuit authorization merely because its
`Job_ID` is unchanged. Application Gate is separate from qualification
and Match truth; application-question answers never rewrite qualification
truth. `COMPLETE_HUMAN_CONFIRMED` requires explicit human confirmation.
Package generation does not authorize submission. Final application
submission remains human-controlled.

**Fresh first-party employer source rule.** Before an employer-specific
consequential implementation premise is authorized or acted upon,
re-establish the current first-party employer source whenever reasonably
retrievable. Fresh first-party employer evidence supersedes prior chat
summaries, model memory, sibling-role wording, stale fixture assumptions,
and in-memory reproductions. If fresh source invalidates the premise:
STOP. Never alter source capture or representation to manufacture the
authorized defect.

**134. RESUME REFERENCE VISUAL STANDARD — RESUME_REFERENCE_STANDARD_V1 (LOCKED)**

Bora explicitly approved **`Bora_Chaush_MGB_Application_Analyst_I_Resume_REFERENCE_v1.pdf`**
(2026-09) as the authoritative visual/reference exemplar for the Career OS
résumé standard. This is a reference-standard/QA-doctrine lock only —
Sections 44-51 already govern content architecture (master protection,
immutable/adjustable fields, structured patching, claim lineage, format
validation) and `.cursor/rules/resume.mdc` already operationally enforces
them; this section extends that existing doctrine with the visual
contract and content-quality principles the reference PDF embodies, and
does not restate what is already locked. The binary PDF is not stored in
the repository, consistent with this repository's existing practice for
Bora-supplied source documents (transcripts, offer letters, and similar
are recorded by description/date, never stored) — this section is the
canonical record of the approved exemplar and its extracted contract.

**Reference principle.** The PDF is the authority for visual execution.
Where written descriptions and the PDF differ on a visual detail, the
PDF's actual visual grammar governs, unless doing so would violate
Candidate Truth, ATS safety, accessibility/readability, an explicit
employer submission requirement, or a stronger canonical governance rule.
MGB-specific content itself (exact wording, bullet selection, evidence
allocation, role-family language, JD terminology, which links are
exposed) is a job-specific strategic variable, never frozen as
universal — only the visual/QA contract below is fixed.

**Presentation grammar — AMENDED BY §141.** This paragraph originally
also named "section order" and "Education-first ordering" as job-
specific strategic variables alongside MGB-specific wording/content.
`BLUEPRINT.md` §141 (`BORA_RESUME_REFERENCE_STYLE_LOCK_V1`) **expressly
amends and narrows** that original statement: default section order
(heading presence/labels, section sequence, and work-entry line grammar)
is no longer a free per-application variable — it is governed by §141's
locked gold-reference presentation grammar, correcting the reproduced
Cable One drift. Only job-specific wording/content choices (exact bullet
text, evidence allocation, role-family language, JD terminology, which
links are exposed) remain the free strategic variable this paragraph
describes; an agent must not read this paragraph as authorizing a
non-gold-reference section order, a "PROFESSIONAL SUMMARY" heading, or an
employer-first work-entry line merely because it predates §141. §141
governs presentation grammar going forward; this paragraph is retained,
amended, as the historical location of the now-narrowed rule.

**Numeric visual metrics — AMENDED BY §141 for gold-reference packages.**
The Reference principle above ("the PDF is the authority for visual
execution... the PDF's actual visual grammar governs") originally left
the approved MGB PDF as the sole named visual-metrics authority, with no
stated resolution for a second approved exemplar. §141.3 and
`docs/resume/BORA_SPY_POND_GOLD_REFERENCE_V1.json` now lock numeric
visual metrics (margins, point sizes, primary/fallback font) drawn from
the Spy Pond FINAL_REFERENCE_STYLE DOCX as the metrics of record for any
package built under §141's gold-reference grammar. This does not conflict
with or redefine the Fixed visual/QA contract immediately below (page
size, one-column structure, typographic hierarchy, thin-rule headings,
hyperlink rule), which stays qualitative and applies to both exemplars
identically; it resolves only the numeric-instantiation question. Where
the MGB PDF and the Spy Pond DOCX numeric metrics differ, §141.3's
Spy Pond-derived numbers govern for packages built under §141's grammar,
and the MGB PDF's original numeric instantiation remains authoritative
only for its own historical package. The Reference principle's PDF-
authority sentence is amended accordingly and must not be read as
overriding §141.3 for gold-reference packages.

**Fixed visual/QA contract (stable across every résumé derivative).**
U.S. Letter page; one page by default at Bora's current career stage;
one-column structure; the candidate name/contact information is a
centered block at the top of the document body, and must not be placed
in an actual Word/PDF page header or footer region; restrained
black-and-white design with no color accents needed for readability;
readable professional typography with a clear font-size hierarchy
(candidate name largest, section headings next, body/bullet text
smallest but fully readable); consistent, professional margins; section headings
set apart by a thin horizontal rule, not by color, shading, or boxes;
a clear role/employer/date hierarchy per entry (role and employer visually
distinct from the date range, dates right-aligned or otherwise clearly
separated); consistent bullet indentation and spacing; dense but readable
page utilization; no large dead lower-page region when relevant supported
evidence exists to fill it. Explicitly excluded: decorative graphics,
sidebars, skill bars/meters, icons, and text-box-based visual gimmicks.
Hyperlinks (e.g. LinkedIn, GitHub, Live Demo) use short, human-readable
visible labels, not raw URLs, and must be genuinely clickable (a real URI
annotation/hyperlink, not merely styled to look like a link) in whichever
artifact format is actually submitted — a real DOCX hyperlink run when
DOCX is submitted, a real URI annotation in the exported PDF when PDF is
submitted — per §140.5/§140.6, which apply this same clickable-URI rule
to the DOCX default; this is not a PDF-only requirement.

**Submitted-artifact format rule — SUPERSEDED by §140.** This paragraph's
original text locked PDF as the canonical/default submitted artifact,
DOCX as an optional companion only, and the rendered PDF as always the
final visual/format QA authority even when a different format was
submitted. §140 (`BORA_RESUME_PACKAGE_STANDARD_SYNC_V1`) expressly
reverses the default: **DOCX is now the canonical/default submitted
résumé artifact**, and PDF is a supported export/QA representation, not
the universal default — see §140.1-§140.2, which control. QA authority
is likewise resolved by §140.6, not by the rule this paragraph
originally stated: final visual/format QA authority belongs to whichever
format is actually going to be submitted (DOCX or PDF), rendered and
visually inspected before submission; the rendered PDF is no longer
mandated as final QA authority for a submission where DOCX is what is
actually submitted. This paragraph is retained only as a historical
record of the superseded rule and a pointer to §140 — it is not itself
an operative instruction. Everything else in this section (the Fixed
visual/QA contract, above, and the remaining paragraphs below) remains
fully authoritative and unchanged for both formats.

**Full-page utilization, honestly.** Substantially using the page with
relevant, evidence-supported material is the goal — not eliminating every
trace of whitespace, and never adding filler content merely to reach the
bottom margin. Overflow is never solved by shrinking type or crushing
margins to an unreadable size (already locked, Section 50 / `resume.mdc`
Format Validation) — this section extends that same discipline to
margins specifically, not only font size.

**Typographic character discipline.** Extends the existing no-em-dash
punctuation preference (Section 132): use normal, plain typographic
characters throughout Bora-facing and candidate-facing résumé text —
ordinary hyphens, not em/en dashes or other decorative Unicode dash
variants; straight quotation marks are acceptable but no other
decorative/smart-typography substitutions are needed to satisfy this
standard.

**Content-quality principles (extend, do not replace, the existing
Keyword Rule and Candidate-Facing Style doctrine already locked in
Section 48 / `resume.mdc`):**

- **Evidence Budget.** The space given to each experience/project on the
  page should be proportional to its relevance to the target role, not
  equal or automatic — a stronger, more relevant experience earns more
  bullets and more page space than a weaker or less relevant one.
- **Role-Specific Narrative Density.** How much detail a given bullet
  carries (how many concrete specifics vs. a compact summary) should flex
  with how central that experience is to the specific role being pursued,
  within Section 45's existing adjustable-field boundaries.
- **Human Resonance.** A bullet should read as something a real person
  actually did, in plain natural language (already governed by the
  Candidate-Facing Style rule), not as a generic, interchangeable
  capability statement that could describe anyone.
- **Employer Confidence Signals.** Where truthfully supported, prefer
  wording that shows reliability, ownership, and sound judgment in how
  work was carried out, not merely a list of tasks performed.
- **Interview Expandability.** A bullet should be phrased so a reasonable
  follow-up question about it is one Bora can truthfully and comfortably
  expand on in an interview — never a bullet whose only supporting detail
  runs out immediately.
- **Recruiter Inference Audit.** Before finalizing a bullet, check what a
  reasonable recruiter would infer from it as written, and confirm that
  inference is truthful and intended — not merely that the literal words
  are individually defensible.
- **Justified Curiosity.** An intentionally distinctive, truthful detail
  (e.g., a real project) may be included specifically because it invites
  a legitimate "tell me more" — never included as an empty gimmick.
- **Truthful Lexical Alignment.** The same rule as the existing Keyword
  Rule (Section 48): JD terminology may be mirrored only when it
  truthfully describes evidence Bora already has.
- **Completed-execution results are legitimate results.** A well-executed
  process, system, or control that has no fabricated quantified business
  metric attached is still a legitimate, presentable result on its own —
  the absence of an invented number is not a weakness to be papered over
  (extends, never weakens, the existing "never fabricate quantified
  business impact" rule already locked).
- **Skills summarize proof; they do not substitute for proof.** A Skills
  section is a derived summary of evidence-backed bullets elsewhere on
  the résumé, never an independent channel for asserting a capability
  that is not otherwise demonstrated.

**QA checklist (verification, not implementation — see Non-Goals below;
format scope amended by §140.6).** Before any résumé package is treated
as submission-ready: one-page-default overflow check; clipping/overlap
check (no visual element cut off or colliding); plain-text
extraction/read-order check (the document's underlying text extracts in
the correct logical order, relevant to ATS parsing); hyperlink
destination verification (each visible link label resolves to its
correct URI); final rendered visual QA (a human look at the actual
rendered document, not just the source data). This checklist applies to
whichever artifact format is actually going to be submitted — DOCX, PDF,
or both — per §140.6's final-QA-authority rule; it is no longer
PDF-exclusive now that §140 makes DOCX the default submitted artifact.
These are QA requirements this standard locks — not an instruction to
build automated tooling for them now (see Non-Goals).

**General GitHub contact-block inclusion.** Not made universally mandatory by
this section. It was appropriate and approved for the MGB reference PDF;
universal inclusion in every future derivative remains conditional on
public-surface Package Truth and relevance to the specific application,
a job-specific strategic variable like the others named above.

**Non-Goals (explicit, per the build-economy gate, Section 133).** This
section locks a reference standard and QA requirements, not an
implementation. It does not authorize: a PDF generator; DOCX parity
tooling; automated ATS scoring or generic keyword scoring; an automated
hyperlink validator, overflow checker, or visual-diff tool; any change to
matching/qualification logic, Candidate Truth, Employer Truth, schemas, or
runtime product code; application automation; or automated package
generation. Generator/tooling work to satisfy this standard must still be
separately earned under the build-economy gate (Section 133: a
demonstrated material reliability/truth defect, or recurring, measured
workflow cost from manual reproduction that materially wastes live
application time) — the existence of this reference standard alone does
not authorize building anything to enforce it.

**135. LIVE ROLE VERIFIED ACTIONABILITY GATE — LIVE_ROLE_VERIFIED_ACTIONABILITY_GATE_V1 (LOCKED)**

Earned by two reproduced live-market stale-role failures (Mass General
Brigham RQ4055007; Fresenius Medical Care R0266808, where employer-owned
indexed Workday evidence was treated as sufficient, but the exact
requisition returned "The page you are looking for doesn't exist" when
actually opened). This section sharpens, and does not contradict, the
already-locked Direct-Source Rule (Section 19), Role Freshness (Section
20), Ghost/Stale Role Detection (Section 21), the Discovery-boundary
concept (Section 133), and `LIVE_APPLICATION_FIRST_PARTY_EXECUTION_RULE_V1`
(`AGENTS.md`) — it does not create a competing truth system, a new
posting-state axis, or a new enum.

**The chain.** `DiscoveryLead` (untrusted lead) → cheap preliminary
triage allowed → exact first-party actionability gate → actionable
pursuit recommendation → meaningful tailoring/package/application work.
Cheap preliminary fit triage against discovery/index evidence remains
allowed and encouraged before verification — this section does not
require first-party verification before any fit analysis, only before
the role is treated as actionable. This preserves the Blueprint goal of
evaluating large numbers of roles cheaply.

**What discovery evidence may never do on its own.** Search-engine
results, LinkedIn/Indeed/Simplify/other aggregators, cached employer
search results, employer-owned indexed/search snippets, stale
Workday/ATS indexes, prior captures, chat summaries, and memory may all
support cheap preliminary triage, but none of them, alone, may establish
`VERIFIED_LIVE`, enter the actionable pursuit queue, receive a serious
pursuit recommendation, or trigger meaningful résumé tailoring, package
generation, or application execution — even when the source is
employer-owned, indexed, or otherwise appears first-party in origin. An
indexed listing is evidence that a requisition existed at index time,
never evidence that it is currently actionable.

**What "successfully established" means.** Not narrowly "contains an
Apply button." The exact current requisition must (a) load as the
matching current role/requisition identity, and (b) provide a current
actionable application route, or explicit current application
instructions/status sufficient to establish actionability. Both are
required.

**Examples that fail to establish current actionability:** the exact
requisition returns page-not-found; the exact requisition redirects only
to a generic job search with no matching current role; matching
requisition identity cannot be established; the application route or
instructions found are no longer current or cannot be established.

**When first-party actionability cannot be re-established.** Do not
fabricate `VERIFIED_LIVE`. Preserve uncertainty using the existing,
independent `source_verification_status` / `role_status` axes (Section
19-21) — do not collapse them, do not infer one from the other, and do
not add a new axis or enum to represent this state. Cheap preliminary
triage already recorded may remain recorded if useful. No meaningful
tailoring, package generation, or application execution may proceed.

**Historical truth is unaffected.** A role failing this gate today does
not erase historical Employer Truth already captured, historical
qualification analysis already performed, or Submitted Application Truth
for a prior, genuinely-verified application. Only current actionability
changes.

**136. BORA-SPECIFIC HIRING RELEVANCE — BORA_SPECIFIC_HIRING_RELEVANCE_V1 (LOCKED)**

Serious roles are evaluated through four axes: **Qualification Truth**
(can Bora credibly pursue this at all), **Competitive Position**
(how naturally does Bora fit this specific employer/role/recruiting
context, given career stage and comparison pool), **Opportunity Value**,
and **Pursuit Economics**. The four axes organize pursuit judgment. They
do not replace §5's locked optimization hierarchy or §132's five-layer
truth model. Competitive Position may inform §5's realistic-hiring-
probability judgment, but it is not a score, probability, or fifth truth
axis. Bora-specific hiring relevance is a **structured component of
Competitive Position** — not a fifth truth axis, not a qualification
field, not a probability, not a numeric score, and never a runtime hard
blocker. Qualification establishes whether Bora can credibly pursue;
hiring relevance strengthens Competitive Position and helps determine
pursuit priority among already-viable roles. Relevance alone never
determines where Bora spends his time — Opportunity Value and Pursuit
Economics remain independent, unreplaced considerations, and §5 remains
the governing hierarchy when factors conflict.

**The question this doctrine answers.** How naturally does this specific
employer, role, recruiting context, career stage, and Bora's verified
evidence combine into a coherent hiring case for Bora?

**Tier A — core relevance.** Strong functional evidence overlap (readable
directly from existing `EvidenceMatch`/`major_gaps` output — no new field
needed); comparison-pool alignment (see below); realistic seniority;
explicit recent-graduate/early-career/0-2-year targeting; degree/program
alignment; a coherent evidence-to-JD narrative.

**Comparison-pool alignment is a distinct concept from seniority.**
Seniority detection (already locked, `job_decision.py`) asks whether a
posting's *language* signals an advanced level, and functions only as a
negative/disqualifying signal. Comparison-pool alignment asks a different
question: who is this employer intentionally comparing Bora against?
Positive comparison-pool evidence includes: recent graduate; a named
graduating class (e.g. "Class of 2026"); new graduate; "master's
graduates welcomed"; 0-1 or 0-2 years; an analyst/associate development
program; campus recruiting; explicit early-career hiring language. This
is not a title check — a role explicitly targeting recent graduates/0-2
years may be materially more relevant to Bora than a superficially
similar role requiring 2-4 or 3-5 years, because the comparison pool
differs. Never converted into numeric weights.

**Tier B — strong supporting relevance.** Demonstrated employer
early-talent hiring behavior; relevant U.S. experience context;
geography/employment-arrangement compatibility with Bora's immediate
objective; explicit employer OPT compatibility when actually established
(silence remains UNKNOWN, never positive — unchanged from existing
immigration-evidence doctrine).

**Tier C — institutional/contextual relevance.** Brandeis affinity is
differentiated by evidence strength, not treated as one signal: (1)
generic employer familiarity ("Brandeis graduates work there") — weak,
supporting only; (2) a demonstrated recruiting relationship (the employer
actively recruits through Brandeis, Handshake, events, or fairs) —
stronger; (3) recent program/function-specific hiring (the employer
recently hired Brandeis IBS/Business Analytics graduates into relevant
functions) — the strongest institutional-affinity signal. Strength
increases with recency, directness, and role-family specificity. Never
interpreted as "Brandeis affinity means the employer prefers Bora" — the
correct reading is lower institutional unfamiliarity, a demonstrated
recruiting pathway, and potentially a stronger contextual/access signal.

**Institutional hiring relevance and network/access leverage remain
separate concepts, never collapsed.** Institutional hiring relevance
(above) affects Competitive Position. Network/access leverage — a
relevant alumnus, a recruiter contact, a referral path, hiring-manager
insight, an informational-interview opportunity — is a separate concept
entirely; a relevant alumnus may improve access while proving nothing
about qualification or employer preference. `network_action`'s own
representation is not redesigned by this milestone.

**Contextual experience transfer is not mechanical employer-type
similarity.** Winter Walk nonprofit experience does not mean nonprofits
are automatically strong targets. The question is whether Bora's prior
context makes his evidence easier for the target employer to understand
as relevant: "nonprofit + implementation/workflows/UAT" may matter;
"nonprofit + unrelated fundraising role" carries little or no relevance
benefit. Functional overlap remains primary.

**Weak signals only (never primary, never compensating):** prestige;
generic alumni presence; keyword counts; applicant counts; title
similarity without functional overlap; Simplify/ATS match scores.

**Non-compensation rule.** Positive relevance signals may compound with
each other, but never override: a hard qualification blocker; a failed
current-actionability gate (§135); explicit work-authorization/OPT
incompatibility; a legal/citizenship/clearance requirement; a required
credential/certification blocker; required direct technology/domain
experience with no acceptable alternative; or an application-specific
blocker. Brandeis affinity cannot upgrade Qualification Truth. Recent-grad
targeting cannot erase a hard technical blocker. Nonprofit/context overlap
cannot upgrade Candidate Truth. Network access cannot upgrade
qualification.

**Fake-precision prohibition.** No numeric relevance scores, arbitrary
weights, percentages, probabilities, point systems, or fake thresholds.
Any future quantitative weighting must be earned from Bora-specific
outcome evidence, never generic internet averages.

**Relationship to existing architecture (unchanged by this milestone).**
Qualification Truth's deterministic runtime logic; existing lane/decision
routing; hard-blocker logic; the `Job` schema; `initial_opt_relevance`/
`future_stem_quality`; source-verification/role-status independence
(§§19-21); the Pursuit Approval Boundary (`docs/decisions/
ADR-PURSUIT-APPROVAL-BOUNDARY-V1.md`). This doctrine governs semantic/
manual Competitive Position assessment now; it may later inform a
non-blocking runtime representation only if real live-role operation
earns it under the build-economy gate (§133) — not by default.

**Résumé connection (conceptual only, not implemented here).**
Bora-specific relevance may later inform selection and emphasis among
already-approved, truthful résumé content: evidence selection, project
selection, bullet selection/order, space allocation, summary emphasis,
skills ordering, and truthful lexical alignment (§48/§134). It must never
alter Candidate Truth, invent tools or methodologies, bypass approved
Claim lineage, change immutable dates/titles/employers/education, or
weaken the locked one-page visual/format standard (§134).

**137. RÉSUMÉ PAGE-UTILIZATION ENFORCEMENT — RESUME_REFERENCE_DERIVATIVE_AND_PAGE_UTILIZATION_ENFORCEMENT_V1 (LOCKED)**

Earned under §133's build-economy gate by a demonstrated, reproduced
material quality/workflow defect: the live Atominvest — Implementation
Analyst application produced a truthful, technically-one-page résumé that
was nevertheless substantially under-filled (a large dead lower-page
region; useful approved evidence unnecessarily deleted), which Bora
manually corrected before submission. This section locks the resulting
hard product rule and records exactly what is mechanically enforced today
versus what remains manual QA — it does not restate §134's fixed visual
contract, which remains the controlling reference standard.

**Hard floor.** For a normal Bora application résumé: one U.S. Letter
page, truthful and readable, with meaningful content extending through at
least 92% of page height (measured from the physical top of the page to
the bottom-most meaningful content, never `text_bbox_height / page_height`,
so a normal top margin is not penalized). 92% is a floor, not a target to
decorate past.

**Precedence (unchanged, restated for this rule specifically).** (1)
Candidate Truth / Evidence / approved Claims; (2) readability, ATS safety,
no clipping, no overflow; (3) immutable history; (4) 92% page utilization.
The 92% floor never authorizes filler, unsupported claims, invented
technologies or metrics, duplicated bullets, generic padding, distorted
spacing, crushed margins, or unreadably small type. Underutilization is a
QA failure to correct through truthful means already locked in §§45/134
(reordering, rewording, restoring stronger approved material, reallocating
space) — never an instruction to fabricate content. If 92% genuinely
cannot be reached with truthful, readable, useful supported material, the
résumé fails this QA gate; it is not padded to pass.

**What is mechanically enforced today.** A pure, deterministic validator
(`evaluate_resume_page_utilization()`, `src/resume_page_utilization.py`)
checks a normalized rendered-page-geometry payload (page size/count and a
list of content objects tagged with an explicit content-type) against the
92% floor, one-page U.S. Letter size, and page/content overflow — never
generating, rendering, or parsing a PDF itself, and never touching
Candidate Truth or résumé content. `resume_validation.py`'s existing
export-approval gate (`approve_derivative_for_export`,
`validate_derivative_eligibility`) accepts this payload through an
optional `page_geometry` parameter; when supplied, a failing result blocks
export approval exactly like any other eligibility failure.

**What remains human/manual (not mechanically enforced; format scope
amended by §140).** No DOCX/PDF generator, renderer, or
rendered-page-geometry producer exists anywhere in this repository;
Bora's actual submitted résumé package — DOCX by default per §140.1, or
PDF when an explicit employer/application-system instruction overrides
that default — is produced by a human-controlled
process outside this repository (§134/§140) and never passes through
this validator today. The correspondence between a supplied geometry
payload and the real exported document, and every item in §134's QA
checklist as amended by §140.6 (clipping/overlap, plain-text
extraction/read-order, hyperlink destination verification, final
rendered visual QA of whichever format is actually submitted), remain
manual human review. This section does not claim end-to-end automated
document enforcement — only that a geometry payload, once supplied, is
checked mechanically and fail-closed at the export-approval boundary,
regardless of which format that geometry payload describes.

**138. BORA ROLE SELECTION AND PURSUIT PRIORITY STANDARD — BORA_ROLE_SELECTION_AND_PURSUIT_PRIORITY_STANDARD_V1 (LOCKED)**

This is a governance/operating-doctrine lock, not a runtime implementation.
It operationalizes §136's Competitive Position / Opportunity Value /
Pursuit Economics doctrine into a concrete discovery and role-selection
standard, consistent with §5 (Locked Optimization Order), §6 (Job
Universe), and §7 (Generally Low-Priority/Reject) and operationalized
from §136's quantitative comparison-pool framing — not a claim that this
level of quantitative detail was already present in §5 itself. It does
not restate §136's comparison-
pool distinction, non-compensation rule, institutional-relevance ladder,
network/access separation, or fake-precision prohibition — those remain
authoritative and unchanged, cross-referenced here rather than duplicated.

**Governing boundary (restated once, applies to every subsection below).**
Nothing in this section may convert: `UNKNOWN` → `SUPPORTED`; `UNKNOWN` →
`NONE`; adjacent experience → direct experience; functional overlap →
qualification; good location → qualification; a fresh posting →
qualification; remote authenticity → qualification; institutional
affinity → qualification; or network access → qualification.
Qualification Truth, Employer Truth, Candidate Truth, and Match Truth are
governed entirely by existing, unchanged architecture (`job_analysis.py`,
`job_decision.py`, the requirement/evidence-match/qualification-gate
pipeline, and the existing mechanical recruiter-threshold guard). This
section governs only Pursuit Truth and Package Truth: discovery priority,
pursuit urgency, and how a serious role is presented for Bora's decision —
never whether Bora is qualified.

**138.1 Discovery/comparison-pool priority.** Career OS should actively
search and prioritize, in descending order: **A+** — recent/new graduate,
a named graduate/development/rotational program, or explicit no-prior-
professional-experience-required language; **A** — 0-1 or 0-2 years; **B**
— 1-2 years selectively, especially where internships, projects, academic
work, or equivalent/transferable experience are explicitly accepted; **C**
— exceptional 1-3 years only, and only when central functional overlap is
unusually strong with no material hard requirement blocking Bora. Do not
actively target 2-4 years, 3-5 years, 5+ years, Senior, Lead, Principal, or
Manager-type roles, unless an explicit employer-authored alternative
qualification branch materially changes the case (the existing
qualification-gate architecture, unchanged) — consistent with, and not a
narrowing of, §7's existing low-priority list. "Do not actively target" is
a discovery/pursuit-economics rule, never an automatic Qualification Truth
`REJECT` — the existing mechanical recruiter-threshold guard in
`job_decision.py` remains authoritative and unchanged, and this doctrine
does not duplicate or weaken it.

**138.2 Central functional overlap.** Within the correct comparison pool,
prioritize roles whose day-to-day work maps directly to Bora's verified
evidence: requirements clarification, workflow/process mapping,
implementation, UAT/QA, application/systems analysis, process improvement,
structured reporting, data operations, data quality, API/data workflows,
stakeholder coordination, operational controls, technical documentation,
and exception handling. Functional overlap is necessary for strong pursuit
priority but never repairs a hard qualification blocker; a 0-2 role is not
automatically a strong target merely because its recruiter threshold is
low.

**138.3 Required-skill non-compensation.** A favorable comparison pool
must never erase a genuinely required, unsupported mandatory requirement
(examples: SQL, Tableau, Salesforce, SAP, Epic, Workday, ERP/platform
ownership, specialized domain tenure, direct enterprise-platform
administration, Agile/Waterfall experience, a required
certification/license, or a citizenship/clearance requirement). Preferred/
plus/exposure language remains distinct from required language (§48's
existing Keyword Rule). Résumé/package generation may never invent a
required skill to solve a gap (§§45/49/134, `.cursor/rules/resume.mdc`,
unchanged).

**138.4 Bora's primary search lanes and work-format discovery preference.**
Career OS still evaluates every opportunity through Opportunity Value and Pursuit
Economics (§132); work format never changes Qualification Truth. The primary practical
lanes remain: **Lane A — Boston/Greater Boston** (Boston, Cambridge, Greater Boston,
and realistically commute-accessible hybrid/onsite roles); **Lane B — verified U.S.
remote part-time/contract/temporary**; and **Lane C — verified U.S. remote full-time**.

Within discovery and pursuit prioritization, Bora's standing work-format preferences
are now explicit and locked: **REMOTE**, **CONTRACT/CONTRACT-TO-HIRE/TEMPORARY**, and
**PART_TIME** are positive discovery preferences. A role combining two or more of those
traits (for example remote + contract, remote + part-time, or remote + temporary) gets
strong tiebreak priority among otherwise comparable opportunities. Verified U.S. remote
part-time/contract/temporary roles are therefore a favorite search lane and should be
actively surfaced early, especially where they provide U.S. experience, income,
references, implementation/UAT/data experience, finance/analytics experience, or
stronger future career capital. Boston/Greater Boston contract, temporary, and part-time
roles also receive positive preference even when hybrid or onsite. Verified U.S. remote
full-time remains a strong preferred lane when functional fit and access are strong.

These are **discovery/pursuit preferences, not hard filters and not qualification facts**.
The three primary lanes are not ranked above one another as a universal rule, and this
preference lock does not create a fixed Lane A > Lane B > Lane C hierarchy or a universal
employment-type ranking (§138.11). The preferences bias search effort and break ties among
otherwise comparable opportunities; they must never rescue a weak match, override an
authorization blocker, bypass first-party actionability (§135/§138.6), or suppress an
unusually strong accessible full-time/hybrid/onsite opportunity in another lane. Other
U.S. geographies remain secondary unless an opportunity is unusually strong and
realistically accessible.

**138.5 Freshness — Bora-specific pursuit priority and discovery-window lock (not a
universal employer-hiring-probability claim).** Extends §20's existing freshness fields
without redefining them. The existing Freshness vocabulary remains keyed to the reliable
`board_posted_date` field (`schemas/job.schema.json`): **0-2 days = VERY_FRESH**;
**3-7 days = FRESH**; **8-14 days = AGING**; **15+ days = STALE_LEANING**; and
**UNKNOWN** when posting date cannot be reliably established.

For discovery effort, Career OS must additionally apply Bora's locked pursuit-window
overlay: **0-7 days = GOLD_WINDOW** (default priority window; search and surface first);
**8-14 days = STRETCH_WINDOW** (still actively pursue when fit/value is good);
**15-21 days = FAR_STRETCH_WINDOW** (requires materially stronger fit/value and should
normally rank behind comparable fresher roles); **22+ days = EXCEPTION_ONLY_WINDOW**
(do not spend normal discovery/application effort unless the role is unusually strong,
verified live/actionable, or otherwise strategically exceptional); **UNKNOWN =
UNKNOWN_WINDOW** when the employer posting date cannot be established reliably.

The overlay is presentation/governance vocabulary only; it is not a schema enum and does
not replace `VERY_FRESH` / `FRESH` / `AGING` / `STALE_LEANING` / `UNKNOWN`. No age band
means closed or unqualified, and there is no universal magical employer cutoff at 7, 14,
21, or 22 days. After the Bora-facing recency visibility gate below has first been
satisfied by an authoritative recency anchor, first-party verified live/actionable evidence
(§135) outranks age-band assumptions; it never rescues an unanchored role. Thus an excellent
16-day-old or older verified-live role with authoritative recency evidence may still deserve
pursuit when fit/value is unusually strong. Freshness is a tiebreaker/urgency/pursuit-
economics factor only, never a qualification fact and never a claim about any employer's
actual hiring behavior. Where `board_posted_date` is unavailable or unreliable, preserve
`UNKNOWN`; never silently substitute `discovered_date` or `date_first_seen` as if it were
the employer's own posting date.

**Bora-facing recency visibility gate (fail closed).** `UNKNOWN_WINDOW` may exist during
cheap internal discovery, but it is not sufficient for Bora-facing serious-role surfacing
or package generation. Before a role may be shown to Bora as a serious discovery candidate
or enter a package queue, Career OS must establish at least one authoritative recency anchor:
(1) a reliable employer/official-ATS posting date, or (2) a dated application-intake window
from the employer/official ATS or another current exact-role application platform that
explicitly establishes when applications opened and/or the current open-through/close
period. A live Apply button, résumé-upload form, current requisition shell, search-engine
crawl date, `discovered_date`, `date_first_seen`, aggregator age, or social-platform age by
itself does **not** satisfy this gate. If neither authoritative recency anchor exists, suppress
the role from Bora-facing discovery, do not generate a package, and keep it internal only as
recency-unverified if useful.

A current exact-role state that explicitly says **closed**, **expired**, **filled**, or
**no longer accepting applications** is an immediate Bora-facing suppression signal unless
a newer first-party employer/official-ATS source explicitly says applications are currently
open again. Closure-state evidence and posting-age provenance are distinct: a current
application platform may establish that intake is closed without its displayed posting age
becoming Employer Truth or `board_posted_date`. This is a Bora-specific discovery/pursuit
visibility rule, not Qualification Truth and not a universal claim about employer hiring.

**138.6 First-party actionability.** §135 remains fully authoritative and
is not re-defined, narrowed, or duplicated here: before meaningful
tailoring/application work, the exact current requisition must load, its
role/requisition identity must match, a substantive current posting must
exist, and current application route/instructions must be actionable.
Discovery/search/index evidence alone supports only cheap preliminary
triage. Failed or unresolved first-party actionability routes to `WATCH`/
no serious application effort, unless an independent blocker already
produces `REJECT`. First-party actionability is necessary but, after the
§138.5 Bora-facing recency visibility gate, not sufficient by itself: a
live Apply/upload route cannot rescue a role whose recency is unanchored.
This section creates no new, competing actionability axis.

**138.7 Remote authenticity.** Remote is not suspicious by itself; missing
evidence is not proof of fraud. Remote authenticity is a separate Pursuit/
Trust assessment — never Bora Fit and never Qualification Truth. This
locks a qualitative vocabulary for human/model assessment now (explicitly
**not** a new schema enum or runtime field in this milestone):
`VERIFIED` — employer identity established, exact current requisition
verified, remote arrangement stated by the employer/a current first-party
source, an official careers/ATS route established, and location
restrictions checked where available; `LIKELY_LEGITIMATE` — strong
legitimate evidence exists but one non-critical authenticity element
remains unresolved; `UNCLEAR` — insufficient evidence to confidently
establish authenticity (must never be described as scam/fraud);
`HIGH_RISK` — material scam indicators exist (examples: requests to pay
for a job; fake-check/equipment-purchase/reimbursement schemes; gift-
card/crypto/payment requests; suspicious impersonation; sensitive
financial/identity information requested outside a normal verified
hiring/onboarding context; recruiter identity/domain inconsistencies;
unsolicited suspicious channels combined with other red flags);
`CONFIRMED_FRAUD` — only when strong direct evidence establishes
fraudulent activity, never inferred from one weak signal; `N/A` when the
role is not remote. The employer's official site/official ATS remains the
first verification layer; when recruiter contact occurs later, verify
recruiter/domain identity independently when consequential. External
fraud-safety rationale may reference current FTC/FBI/IC3 guidance
(illustrative operating basis: verify openings on official employer
sites; never pay for a job; a fake check or equipment-purchase/
reimbursement request is a scam indicator; be cautious with premature
personal/financial information requests; a fake employer/recruiter may
use a remote-job pretext to solicit crypto, money, or sensitive
information) without encoding external URLs into runtime logic or
treating one deviation from those examples as proof of fraud.

**138.8 Serious-role output standard.** Only roles that pass the §138.5
Bora-facing recency visibility gate may be promoted into this serious-role
output. When employer posting date remains unknown but an authoritative dated
application-intake window independently passes that gate, Freshness remains
`UNKNOWN` and Discovery Window remains `UNKNOWN_WINDOW`; never convert the
application-window date into an employer posting date. Every serious role
analysis should present these distinct qualitative judgments, none of which is
a numeric score, a fake probability, or an arbitrary point system: **Bora Fit**
(`HIGH` / `GOOD` / `STRETCH` / `LOW` — a synthesized qualitative
functional/competitive fit judgment for pursuit, never Qualification
Truth and never a hiring-probability claim); **Comparison Pool**
(`STRONG` / `ACCEPTABLE` / `WEAK`); **Freshness** (`VERY_FRESH` / `FRESH`
/ `AGING` / `STALE_LEANING` / `UNKNOWN`, per §138.5); **Discovery Window**
(`GOLD_WINDOW` / `STRETCH_WINDOW` / `FAR_STRETCH_WINDOW` /
`EXCEPTION_ONLY_WINDOW` / `UNKNOWN_WINDOW`, per §138.5, shown alongside Freshness
when reliable employer posting age is available and never persisted as a schema/runtime
field); **Location/Work Arrangement** (`STRONG` / `ACCEPTABLE` / `WEAK`); **First-Party
Actionability** (`VERIFIED` / `FAILED` / `UNKNOWN`, per §135/§138.6);
**Remote Authenticity** (`VERIFIED` / `LIKELY_LEGITIMATE` / `UNCLEAR` /
`HIGH_RISK` / `CONFIRMED_FRAUD` / `N/A`, per §138.7); **Authorization**
(`PASS` / `BLOCKER` / `UNKNOWN`); **Opportunity Value** (qualitative
narrative); **Pursuit Economics** (qualitative narrative); and a **Final
Verdict**: `PURSUE - DEEP` (exceptional verified target; substantial
tailoring/networking effort justified), `PURSUE - CONTROLLED HIGH-
QUALITY` (strong target; a good tailored application is justified, but
avoid disproportionate effort), `PURSUE - EFFICIENT` (worth applying;
keep time tightly bounded), `WATCH` (interesting/unresolved/low urgency;
do not spend serious application effort yet), or `REJECT` (a known
blocker, or clearly irrational pursuit). `REJECT` remains stronger than
bad freshness or geography alone — freshness, location, comparison pool,
or weak remote evidence alone should normally downgrade pursuit economics
rather than fabricate a Qualification Truth `REJECT`.

**Presentation-vocabulary disambiguation (required — Cursor MEDIUM
finding, presentation-vocabulary collision risk).** Every label in this
subsection is human/model presentation vocabulary for Pursuit Truth
only. None of them is a value of, or a synonym for, `Job.decision`,
`Job.lane`, `role_status`, or `source_verification_status` — these
remain separate, existing, unchanged runtime/schema fields
(`schemas/job.schema.json`, `job_decision.py`) and this doctrine's labels
must never be written into those persisted/runtime fields. Concretely:
Freshness `STALE_LEANING` (§138.5, a Bora-specific pursuit-urgency label)
is not the same value as, and must never be confused with, `role_status`
`POSSIBLY_STALE` (§21, an Employer Truth ghost/stale-role signal) — the
two describe different truth layers and may disagree on the same role.
First-Party Actionability (`VERIFIED` / `FAILED` / `UNKNOWN`) is a
presentation summary derived from existing §135/§§19-21 evidence
(`role_status`, `source_verification_status`), not a new persisted axis
and not a restatement of either field's own enum. Final Verdict `WATCH`
and `REJECT` are presentation-level pursuit judgments for this doctrine's
own output standard and do not redefine, alias, or replace the existing
`Job.decision` enum (`WATCH`, `REJECT`, `EFFICIENT_APPLY`, `APPLY`,
`PRIORITY_APPLY`), even where the label text coincides. Remote
Authenticity (§138.7) is presentation/doctrine vocabulary only, never a
persisted schema field or a value of any existing enum.

**138.9 Core selection principle (conceptual only).** Career OS should
optimize discovery toward the lowest realistic recruiter threshold,
combined with the strongest central-work overlap, combined with the
strongest practical accessibility — subject always to Qualification
Truth, first-party actionability, authorization/legal reality,
Opportunity Value, and Pursuit Economics. This is a conceptual
prioritization statement only; it does not authorize multiplication,
weights, numeric scoring, or a point system.

**138.10 Current role-family search targets.** Preserves §6's existing
Job Universe (Primary and High-Value Adjacent role families) without
redefinition; the illustrative list carried by this doctrine — Application/
Applications Analyst, Implementation Analyst, Systems Analyst, Business
Systems Analyst, genuinely junior Business Analyst/Technical BA, Associate/
Implementation Consultant, Customer Implementation Analyst, Operations
Systems Analyst, Process Systems Analyst, Technical Operations Analyst,
Data Operations Analyst, Data Quality Analyst, and Digital Solutions
Analyst — is not a permanent closed ontology; an adjacent role remains
eligible whenever its actual duties fit, per §6's own function-over-title
principle.

**138.11 Employment-type principle.** Do not impose a fake universal
ranking such as full-time > contract > temporary > part-time. For Bora
now, contract, temporary, or part-time work can be strategically
excellent when it improves U.S. experience, income, references,
implementation/systems credibility, or future access (consistent with
§§3-4's existing bridge-role doctrine). Evaluate employment type through
Opportunity Value and Pursuit Economics, never a fixed hierarchy.

**138.12 Build-economy/implementation boundary.** This doctrine lock does
not itself authorize runtime implementation. A separate, future READ-ONLY
architecture audit (working name: `BORA_ROLE_PRIORITY_FRESHNESS_AND_
REMOTE_AUTHENTICITY_V1`) is required to determine which pieces, if any,
merit deterministic code under §133's build-economy gate. This lock does
not pre-authorize any new schema, enum, runtime scoring, lane value,
decision value, database field, remote-fraud classifier, automated fraud
declaration, job-search automation change, or scraping/provider change.

**138.13 Atominvest (calibration reference only).** Atominvest —
Implementation Analyst remains a positive calibration case for: a 0-2
comparison pool; strong central functional overlap; finance/data
adjacency; a first-party verified role/application route; and
application-specific authorization discovery. This section does not
persist or alter Atominvest's Application Truth, which remains recorded
separately (Atominvest — Implementation Analyst, SUBMITTED, 2026-09-06,
exact approved application résumé retained); any Atominvest application-
record persistence change is a separate, later, bounded change.

**139. BORA IMMIGRATION ROLE ANALYSIS TIGHTENING — BORA_IMMIGRATION_ROLE_ANALYSIS_TIGHTENING_V1 (LOCKED)**

This section tightens §§24-27's existing immigration doctrine for serious-
role analysis. It restates and sharpens; it does not redefine the
underlying source hierarchy, evidence states, or the
`LEGAL_VERIFICATION_REQUIRED` boundary, all of which remain fully
authoritative as written.

**139.1 Three distinct immigration facets, never collapsed.** Every
serious role analysis must keep three facets visibly separate: (a)
Initial OPT practicality — whether Bora can start this specific opening
now, without employer sponsorship, under whatever OPT/work-authorization
status Candidate Truth currently and explicitly establishes for him;
(b) future STEM OPT employer support — whether this employer would
plausibly support a STEM OPT extension and I-983 training-plan
cooperation later, a separate, forward-looking question from (a); (c)
future sponsorship familiarity — whether this employer has any track
record or plausible willingness to sponsor a longer-term visa (e.g.,
H-1B) after OPT/STEM OPT, a separate, even-further-forward question from
(a) and (b). No single field, sentence, or verdict may merge two of
these into one conclusion. §24's Initial-OPT/STEM-OPT separation is the
floor; this subsection adds future sponsorship familiarity as a third,
equally distinct facet.

**139.2 Current-opening control rule.** For facet (a) — whether Bora can
start THIS opening now — the current role-specific work-
authorization/sponsorship wording on the actual job posting or from
direct employer/HR confirmation controls the *employer-policy
assessment* of the current opening as against employer historical
H-1B/LCA filing familiarity (§27), which is a facet-(c) signal only and
must never be used to override, soften, or reinterpret what the current
opening's own wording says about the current opening. A strong
historical sponsorship record does not make ambiguous or restrictive
current-opening wording more favorable, and a weak or absent historical
record does not make favorable current-opening wording less
trustworthy. This control rule governs only which signal wins when
assessing the employer's current-opening policy; it does not, by
itself, resolve OPT/STEM eligibility or legal work-authorization status,
and it does not displace §26's Immigration Boundary Guard. Current
posting/HR wording is not legal authority: where §26 already requires
`LEGAL_VERIFICATION_REQUIRED` because descriptive posting text alone
cannot resolve a consequential legal conclusion, that requirement
remains fully controlling regardless of this subsection.

**139.3 No-sponsorship wording does not become no-OPT-eligibility.**
"No sponsorship" or "no future sponsorship" wording on a posting
concerns facet (c) (or, later, (b)) — it must never be silently
converted into a facet-(a) conclusion about whether Bora is eligible to
work the current opening under whatever OPT/work-authorization status
Candidate Truth currently and explicitly establishes for him, since OPT
work authorization is not the same event as employer visa sponsorship.
This subsection states a relationship between wording types; it does
not itself assert that Bora currently holds OPT authorization or any
other status — that fact, if any, comes only from Candidate Truth.
Where the posting's wording is genuinely ambiguous about which facet it
addresses, the unresolved fact remains `LEGAL_VERIFICATION_REQUIRED` per
§26's existing boundary guard, or explicit HR confirmation — never an
inferred default in either direction.

**139.4 E-Verify and I-983 support are separately visible.** §26's
E-Verify states (CONFIRMED / SEARCH_MATCH_FOUND /
NOT_FOUND_IN_PUBLIC_SEARCH / UNKNOWN / HR_CONFIRMATION_NEEDED) describe
only E-Verify enrollment. They must never be read, by themselves, as
evidence of the employer's I-983 STEM OPT training-plan willingness or
operational capacity, which is a separate, additional fact under facet
(b) requiring its own separate evidentiary basis (direct employer/HR
confirmation, or an explicit prior/known I-983 program) before it may be
reported as anything other than UNKNOWN or HR_CONFIRMATION_NEEDED.
E-Verify enrollment, whatever its status for a given employer, is not
proof of I-983 willingness.

**139.5 No employer-size, prestige, or historical-filing shortcuts.**
Company size, headcount, prestige, industry reputation, recruiter
enthusiasm, and historical H-1B/LCA filing presence or absence remain
non-determinative context signals only, never a substitute for direct
evidence on any of the three facets above. In particular: a large or
well-known employer must not be assumed E-Verify-enrolled, I-983-
willing, or sponsorship-willing without direct evidence; a small
employer or startup must not be assumed unable or unwilling on any
facet without direct evidence; no historical H-1B/LCA filings found
must not become "will never sponsor" (§27 already establishes this;
this subsection extends the same non-determinative-signal treatment to
size/prestige/industry).

**139.6 Doctrine-only lock.** This section is a documentation/doctrine
tightening only. It does not add, remove, or redefine any schema field,
enum, qualification/decision runtime behavior, scoring model, or
numeric probability. `.cursor/rules/opt-safety.mdc` is updated in the
same change to operationally mirror 139.1-139.5; no other file's
behavior changes.

**140. BORA RESUME PACKAGE STANDARD SYNC — BORA_RESUME_PACKAGE_STANDARD_SYNC_V1 (LOCKED)**

Earned under §133's build-economy gate by live Spy Pond and Teradyne
application experience: a submission workflow that defaulted to PDF as
the universal submitted artifact did not fit every employer/application
system's actual accepted/preferred format. This section locks the
smallest correction — which submitted-artifact format is default and how
it stays traceable — and adds an explicit requirement/JD-to-evidence
crosswalk requirement for serious-role packages.

**Relationship to §134 (explicit, not silent).** This section
**expressly amends and supersedes** §134's now-struck "PDF-first output
rule" paragraph (submitted-artifact default and final-QA-authority
rule only, see §134's own superseded-paragraph note) — §140.1, §140.2,
and §140.6 below control that rule going forward. Everything else in
§134 — the Fixed visual/QA contract (page size, one-column structure,
typography, margins, section-rule headings, hyperlink requirements) and
§137's 92% page-utilization floor — is restated and cross-referenced,
not redefined, and remains fully unchanged for both formats (§140.3).
This section also cross-references, without redefining,
`.cursor/rules/resume.mdc`'s protected-master/structured-patch/claim-
lineage architecture and the existing `EvidenceMatch` states
(`schemas/evidence_match.schema.json`: `STRONG` / `SUPPORTED` /
`PARTIAL` / `NONE` / `UNKNOWN`). This is a doctrine lock, not a runtime
implementation.

**140.1 DOCX-first default, employer-format override.** For a normal Bora
application, the canonical editable/default submitted resume artifact is
DOCX. Where the employer/application system states or requires PDF (an
ATS upload field restricted to PDF, or an explicit employer instruction
requiring PDF), that explicit instruction controls for that application
and overrides the DOCX default. Absent any such instruction, DOCX is the
default, not PDF. This override is scoped to DOCX|PDF only, matching
§140.7's traceability record below; it does not admit a third submitted-
artifact format.

**140.2 PDF remains a supported representation, not the universal
default.** PDF stays fully available whenever it is required, requested,
or useful for visual-fidelity QA (§134) — it is no longer treated as the
universal default submitted artifact for every application regardless of
what the employer/application system actually accepts.

**140.3 Visual/ATS standard and 92% floor unchanged.** §134's Fixed
visual/QA contract (one-page U.S. Letter, one-column, restrained
black-and-white visual/ATS standard) and §137's 92%
meaningful-page-utilization floor apply identically regardless of
whether the submitted artifact is DOCX or PDF. Neither is redefined,
narrowed, or weakened by this section — only §134's now-superseded
submitted-artifact-default/final-QA-authority paragraph is amended, per
this section's preamble; a DOCX-first default never authorizes a
shorter, sparser, or less ATS-careful document than the standard already
required.

**140.4 Requirement/JD-to-approved-evidence crosswalk.** Every serious-
role resume/package must be built from an explicit crosswalk between the
job's stated requirements and Bora's approved evidence, driven entirely
by the existing Requirement/`EvidenceMatch` truth already produced by
`src/job_analysis.py` / `src/qualification_gate.py` — never a new,
duplicate, or parallel matching/scoring schema. Crosswalk semantics
preserve the existing states exactly: `STRONG` and `SUPPORTED` may guide
which approved bullets/summary language get emphasis and ordering;
`PARTIAL` may be used only within its recorded transfer boundary (never
promoted to a false direct-experience equivalence, consistent with
`.cursor/rules/resume.mdc`'s existing Transferable Experience section);
`NONE` remains a visible gap (§48's existing Gap Visibility rule) and
must never be resolved through creative wording; `UNKNOWN` remains
unresolved and must never be silently treated as `SUPPORTED` or `NONE`.
The crosswalk may drive summary emphasis, bullet selection/order, skills
ordering, project selection, truthful lexical alignment (§48's existing
Keyword Rule, unchanged), and how much space approved evidence is given —
it may never repair Qualification Truth, invent an unsupported
capability, or manufacture a requirement match that current
`EvidenceMatch` truth does not support.

**140.5 ATS-simple DOCX structure.** A DOCX package must be built for
reliable ATS parsing and plain-text extraction: no graphics, sidebars,
icons, text boxes, skill-bar graphics, or multi-column layouts likely to
scramble read order or defeat parsers. Prefer simple paragraphs and tab
stops for alignment over tables or floating text frames. This extends
§134's existing plain-text-extraction/read-order QA checklist item to the
DOCX artifact specifically; it does not relax any existing visual-standard
requirement. §134's Fixed visual/QA contract hyperlink rule (short
human-readable labels, genuinely clickable, never a raw URL) applies
identically to the DOCX artifact: a real DOCX hyperlink run, not text
merely styled to look like a link.

**140.6 Rendered visual QA before submission — final QA-authority rule
(amends §134).** Before any package is treated as submission-ready, it
must be rendered and visually inspected — not only spot-checked as raw
text — covering the same category of checks §134 already requires
(page-count/overflow, clipping/overlap, read order, and functional
human-readable hyperlink destinations). **Final visual/format QA
authority belongs to the rendered version of whichever format is
actually going to be submitted** — the rendered DOCX when DOCX is
submitted, the rendered PDF when PDF is submitted, or both when both are
submitted — never an intermediate/unrendered document, and never a
format other than the one actually going out. This explicitly replaces
§134's original rule that the rendered PDF is always final QA authority
even when a different format is submitted; PDF-rendered QA remains
required only when PDF is the artifact actually being submitted (or is
separately produced for visual-fidelity comparison per §140.2), not as a
mandatory gate on a DOCX-only submission. This remains a manual QA step
today, consistent with §134 and §137's existing "what remains
human/manual" boundary — no new automated DOCX renderer or geometry
producer is authorized by this section.

**140.7 Exact submitted-artifact traceability.** `.cursor/rules/resume.mdc`'s
existing Application-Specific Outputs requirement (distinct version
identifier; traceability to Job_ID, resume version, patch used,
claims/evidence used, validation result, export result) applies
identically regardless of submitted format. The record must additionally
capture which artifact format (DOCX or PDF) was actually submitted for
that application, so the exact submitted-artifact version remains
recoverable as Application/Package Truth.

**140.8 Doctrine-only lock / build-economy boundary.** This section adds
no new schema field or enum, no new Candidate Truth, no qualification or
decision runtime change, no new `EvidenceMatch`-parallel scoring system,
and no DOCX/PDF generator or renderer implementation — none of that is
pre-authorized merely because this doctrine exists (§133's build-economy
gate continues to govern any future runtime-implementation proposal).
`.cursor/rules/resume.mdc` is updated in the same change to operationally
mirror 140.1-140.7; `schemas/`, `src/`, `resume/`, and the existing
protected-master/structured-patch/claim-lineage architecture remain
unchanged.

**141. BORA RESUME REFERENCE STYLE LOCK — BORA_RESUME_REFERENCE_STYLE_LOCK_V1 (LOCKED)**

Earned under §133's build-economy gate: a previously reproduced résumé
package (spawned for the Cable One application) drifted from Bora's
actual approved presentation grammar — most visibly a generic
"PROFESSIONAL SUMMARY" heading, wrong default section order, and an
employer-first-plus-italic-title work-entry line the reference exemplar
does not use. Bora explicitly approved the **Spy Pond FINAL_REFERENCE_STYLE
DOCX** (SHA-256
`330b600e8cc18bd4edd4aa75422df903cdf8a230a6e97192094c89a254851d43`) as the
canonical gold-standard presentation grammar correcting that drift. The
binary is not stored in this repository, consistent with §134's existing
practice for Bora-supplied source documents; the full extracted contract
is recorded at `docs/resume/BORA_SPY_POND_GOLD_REFERENCE_V1.json`, which
this section incorporates by reference and does not restate in full here.
This is a doctrine/reference-style lock only — no generator, renderer, or
automated validator is authorized by this section (§133/§134 Non-Goals
continue to govern).

**141.1 Relationship to §134/§137/§140 (explicit, not silent).** §134's
Fixed visual/QA contract (page size, one-column structure, typography
hierarchy, margins, thin-rule section headings, real-hyperlink-object
rule) and §137's 92% meaningful-page-utilization floor are restated and
cross-referenced by the gold reference record, not redefined. §140's
DOCX-first default, requirement/JD-to-evidence crosswalk, ATS-simple DOCX
structure, and rendered-artifact final-QA-authority rule are unchanged.
This section adds presentation GRAMMAR — heading/section-order/entry-line
structure — that §134 previously left as a job-specific strategic
variable; MGB-specific and Spy-Pond-specific wording/content choices
themselves remain job-specific, only the grammar is fixed.

**141.2 Canonical presentation grammar.** The gold-reference grammar
(full detail in `docs/resume/BORA_SPY_POND_GOLD_REFERENCE_V1.json`):
no "PROFESSIONAL SUMMARY" (or equivalent generic) section heading — the
natural summary paragraph sits directly below the centered contact line;
default section order EDUCATION, SKILLS, WORK EXPERIENCE, RELEVANT
PROJECT; work entries use one bold left-side line in "Title | Employer"
grammar with dates right-aligned, never an employer-first heading plus a
separate italic title line; education preserves the two-school grammar —
bold school with right-aligned month-year range and a degree line below,
with Brandeis GPA retained when current Candidate Truth supports it;
skills use three natural recruiter-facing rows modeled on Process &
quality, Technical, and Operations, and internal Career OS terminology
must never appear in candidate-facing skills text; the default evidence
roster is Winter Walk, TELUS Digital Bulgaria, D Commerce Bank, and
MarketMind — Bulmarma is not automatically inserted and may replace space
only when a role-specific §140.4 crosswalk materially earns it; MarketMind
uses the gold-reference heading grammar with a technology label and a
genuine right-side GitHub hyperlink when included; candidate-facing prose
mirrors the gold reference's human style (early-career role framing,
concrete action/context/why wording, ordinary American English, no
generic capability-stuffing summary, no internal/system jargon such as
"human approval" or "operating system" language unless genuinely
necessary and recruiter-natural).

**141.3 Visual metrics of record.** U.S. Letter; one column;
approximately 0.46 in top / 0.32 in bottom / 0.72 in left/right margins;
18.5 pt centered bold name; 10.5 pt body/contact text; 11 pt section
headings with a thin rule; Liberation Sans as the primary font with
metrically compatible Arial as a fallback only if Liberation Sans is
unavailable. These are the numeric instantiation of §134's existing Fixed
visual/QA contract for this specific gold reference, not a redefinition
of that contract.

**141.4 Role-tailoring boundary.** Role-specific tailoring may still
change truthful summary emphasis, bullet selection/order, skills
emphasis, and evidence allocation within the existing §140.4 crosswalk.
It must preserve the gold-reference grammar above unless an explicit
employer requirement makes that grammar unusable for a specific
application. The gold reference is a presentation-grammar, visual-
metrics, and roster-structure authority only (heading presence/labels,
section order, work-entry/education/skills line grammar, margins,
typography, the default-roster mechanism) — it is never a source of
Candidate Truth. Substantive factual content (wording, claims, evidence,
metrics) must still trace only to approved Candidate Truth / claim-
evidence lineage (`.cursor/rules/resume.mdc` Claim Lineage), exactly as
before §141; nothing in the Spy Pond exemplar's own MGB-specific wording
or content authorizes inventing or copying a fact merely because it
appears in that DOCX. Role tailoring must never invent resume facts not
present in approved Candidate Truth, change Candidate Truth, Match Truth,
or qualification/pursuit logic, or weaken §137's 92% floor, §140's
DOCX-first rule, the real-hyperlink-object rule, or §140.6's
rendered-artifact QA authority.

**141.5 Doctrine-only lock / build-economy boundary.** This section adds
no new schema field or enum, no new Candidate Truth, no qualification or
decision runtime change, and no generator/renderer/automated-validator
implementation — none of that is pre-authorized merely because this
doctrine exists (§133's build-economy gate continues to govern any future
runtime-implementation proposal). `.cursor/rules/resume.mdc` is updated
in the same change to cross-reference this section's gold-reference
grammar; `schemas/`, `src/`, `resume/`, and the existing protected-
master/structured-patch/claim-lineage architecture remain unchanged.
`tests/resume_reference_style_lock_v1_test.py` is a focused regression
test that fails on the reproduced Cable One drift patterns
(`docs/resume/BORA_SPY_POND_GOLD_REFERENCE_V1.json`'s
`drift_patterns_rejected`) and passes on the locked gold-reference
grammar — it is a doctrine-record consistency check, not a résumé
generator or renderer.

**141.6 Final reference calibration — latest presentation reference
(BORA_RESUME_FINAL_REFERENCE_CALIBRATION_V1, extends §141, not a new
top-level section — `project_state.json`'s `latest_locked_section`
tracks the highest top-level Blueprint heading, and
`tests/resume_reference_style_lock_v1_test.py` pins that field to 141;
this calibration is deliberately recorded as §141 subsections so that
pinned, non-editable regression check and the live
`src/career_os_state.py` section-count validator agree).** Bora
explicitly approved a further user-tweaked DOCX,
**`Bora_Chaush_Cable_One_Business_Analyst_I_v2(1).docx`** (SHA-256
`236179c98b0e3ef68f7e79e392d73e57db41acb6f8493b0a7ab9eb8b2b353955`), as
the final human-approved resume presentation reference. The full
extracted contract is recorded at
`docs/resume/BORA_CABLE_ONE_FINAL_REFERENCE_V1.json`, which this
subsection incorporates by reference and does not restate in full here.
This is a doctrine/reference-calibration lock only — no generator,
renderer, or automated validator is authorized by this subsection
(§133/§134/§141.5 Non-Goals continue to govern).

This exemplar supersedes the Spy Pond FINAL_REFERENCE_STYLE DOCX
(above) only as the **latest presentation reference** — never as a
source of Candidate Truth. §141.1-§141.4's locked presentation grammar
(no generic PROFESSIONAL SUMMARY heading; default section order
EDUCATION, SKILLS, WORK EXPERIENCE, RELEVANT PROJECT; single bold
"Title | Employer" work-entry line with right-aligned dates; two-school
education grammar; three natural recruiter-facing skills rows; one
page; one column; DOCX-first; real hyperlinks; §137's 92%+ meaningful
utilization floor) is confirmed unchanged and remains fully
authoritative — the Cable One v2 exemplar conforms to that grammar
rather than replacing it. §134's Fixed visual/QA contract, §137's 92%
floor, and §140's DOCX-first/crosswalk/hyperlink/rendered-QA rules
remain unchanged and fully apply.

The user-tweaked reference's TELUS Digital Bulgaria display label and
GPA presentation are recorded
(`docs/resume/BORA_CABLE_ONE_FINAL_REFERENCE_V1.json`
`presentation_choices_not_truth`) as presentation choices only. Neither
may silently alter underlying Candidate Truth or evidence provenance;
any change to the underlying facts they display must still trace only
to approved Candidate Truth / claim-evidence lineage
(`.cursor/rules/resume.mdc` Claim Lineage).

**141.7 Research-backed recruiter/ATS writing constraints.** Grounded in
DOL VETS Resume Essentials 2026, University of Pennsylvania Career
Services, Yale Office of Career Strategy, and Indeed ATS guidance and LinkedIn
Talent Solutions recruiter guidance (full citations in the JSON
record's `research_basis`), the following constraints extend — and do
not replace — §134's Content-quality principles, §141.2's
candidate-facing prose style, and `.cursor/rules/resume.mdc`'s Keyword
Rule and Candidate-Facing Style: human readability outranks keyword
density, with ordinary, concrete, direct, recruiter-natural American
English and no internal-system jargon, capability stuffing, inflated
adjectives, or robotic phrasing; the summary is a short natural
positioning paragraph connecting current career stage, strongest
approved evidence, and target role family, never a keyword inventory;
experience/project bullets prefer action plus context plus
outcome/value when evidence supports an outcome, and action plus
context/purpose without inventing impact when it does not, kept concise
and normally one to two rendered lines where practical without forcing
uniform length; quantification is used only when it materially helps
the reader and is evidence-supported, never manufactured; JD terminology
is reused only where the §140.4 Requirement/EvidenceMatch crosswalk
establishes supported overlap, distributed naturally rather than
repeated for density; skills prioritize role-relevant, evidence-backed
hard/operational capabilities over generic soft-skill filler; and the
résumé reads as one coherent early-career story from education/skills
into work evidence and project proof, not disconnected keyword blocks.

**141.8 Bounded Claude-first drafting pilot.** At the PRODUCE PACKAGE
stage, Claude is authorized to draft candidate-facing wording from
exactly four inputs: the verified JD, the approved
Requirement/EvidenceMatch crosswalk, approved Candidate Truth/evidence
modules, and the current reference grammar (§141.1-§141.4 plus §141.6-
§141.7). Claude may not infer facts, tools, metrics, outcomes, or
qualification states. This operates strictly inside the AI Boundaries
already locked in `.cursor/rules/resume.mdc` (AI may
rank/draft/recommend/reorder/identify gaps; AI may not create
unsupported achievements, rename titles, manufacture technologies,
invent metrics, change dates, bypass lineage validation, or directly
modify the protected master) — it assigns Claude to operate inside
those existing boundaries at PRODUCE PACKAGE, it does not loosen them.
G remains responsible for orchestration, truth/evidence adjudication,
rejection of unsupported Claude language, final reference-grammar
conformance, rendered DOCX QA, hyperlink verification, and the human
approval gate; Bora retains consequential approval. This authorizes a
bounded pilot only — not an autonomous or unsupervised Claude drafting
runtime.

**141.9 Doctrine-only lock / build-economy boundary (calibration
addendum).** §141.6-§141.8 add no new schema field or enum, no new
Candidate Truth, no qualification or decision runtime change, and no
generator/renderer/automated-validator implementation — none of that is
pre-authorized merely because this doctrine exists (§133's
build-economy gate continues to govern any future
runtime-implementation proposal). `.cursor/rules/resume.mdc` is updated
in the same change to cross-reference this calibration's final-reference
record; `schemas/`, `src/`, `resume/`, and the existing protected-
master/structured-patch/claim-lineage architecture remain unchanged.
`tests/resume_final_reference_calibration_v1_test.py` is a focused
regression test verifying the final-reference record, the writing
constraints, the Claude drafting-pilot boundary, and doctrine
cross-references — it is a doctrine-record consistency check, not a
résumé generator or renderer.

**141.10 Gold-quality acceptance reference — Claude-first, G-adjudicated
Cable One DOCX (BORA_RESUME_GOLD_QUALITY_REFERENCE_V1, extends §141, not
a new top-level section — for the same reason §141.6 gives:
`project_state.json`'s `latest_locked_section` tracks the highest
top-level Blueprint heading, and
`tests/resume_reference_style_lock_v1_test.py` pins that field to 141;
this lock is recorded as §141 subsections so that pinned, non-editable
regression check and the live `src/career_os_state.py` section-count
validator agree).** Bora explicitly approved the Claude-first,
G-adjudicated Cable One DOCX,
**`Bora_Chaush_Cable_One_Claude_First_G_Adjudicated.docx`** (SHA-256
`ec3a9f9c6e2fc429e01892f61a074a71319ec6586566b6c1cf60808eba2f3f70`), as
Bora's gold-quality resume package acceptance reference for future
Career OS packages. The full extracted contract is recorded at
`docs/resume/BORA_GOLD_QUALITY_REFERENCE_V1.json`, which this subsection
incorporates by reference and does not restate in full here. This
artifact supersedes the Cable One v2 exemplar (§141.6) and the Spy Pond
exemplar (§141) only as the **latest resume package quality/presentation
acceptance reference** — never as a source of Candidate Truth. §141.1-
§141.4's locked presentation grammar and §141.7's research-backed
writing constraints are confirmed unchanged and remain fully
authoritative; the Claude-first, G-adjudicated exemplar conforms to that
grammar and those constraints rather than replacing them. This is a
doctrine/reference-acceptance lock only — no generator, renderer, or
automated validator is authorized by this subsection (§133/§134/§141.5/
§141.9 Non-Goals continue to govern).

**141.11 Final-package QA-dimension checklist and evidence-budget/
narrative discipline.** Every gold-quality package must be checked, before
Bora's human approval gate, across seven QA dimensions recorded in full at
`docs/resume/BORA_GOLD_QUALITY_REFERENCE_V1.json`
`final_package_qa_dimensions`: truth fidelity (traces only to approved
Candidate Truth / claim-evidence lineage), JD/evidence coverage (checked
against the verified §140.4 Requirement/EvidenceMatch crosswalk, with
NONE/UNKNOWN requirements remaining visible gaps), human naturalness
(ordinary recruiter-natural American English, no internal Career OS,
governance, evidence-system, implementation-control, or AI-process
terminology unless genuinely job-relevant), interview defensibility
(every claim must be truthfully explainable live, without embellishment),
reference conformance (§141's locked grammar), rendered one-page quality
(§137's 92% floor, no overflow/clipping/overlap), and functional
hyperlinks (real hyperlink objects with verified destinations per
§140.5/§140.6). This is a manual QA checklist, not an automated
validator. Future tailoring must operate through verified JD ->
canonical Requirement/EvidenceMatch state -> approved Candidate
Truth/evidence -> package decision; supported employer terminology may be
used naturally, while NONE or UNKNOWN tools/capabilities remain absent.
The strongest current/relevant experience receives the most evidence
space by default, without changing the underlying qualification result or
hiding a material gap; the résumé must read as one coherent human career
story rather than disconnected keyword blocks. Norma_Resume is retained
only as external comparison evidence supporting conventional one-column
density, visible tools, action-led bullets, and substantial page use; it
must never become a second Bora template or override Bora's own gold
reference.

**141.12 Doctrine-only lock / build-economy boundary (gold-quality
acceptance addendum).** §141.10-§141.11 add no new schema field or enum,
no new Candidate Truth, no qualification or decision runtime change, and
no generator/renderer/automated-validator implementation — none of that
is pre-authorized merely because this doctrine exists (§133's
build-economy gate continues to govern any future runtime-implementation
proposal). `.cursor/rules/resume.mdc` is updated in the same change to
cross-reference this gold-quality reference record; `schemas/`, `src/`,
`resume/`, and the existing protected-master/structured-patch/claim-
lineage architecture remain unchanged.
`tests/resume_gold_quality_reference_v1_test.py` is a focused regression
test verifying the gold-quality reference record, the final-package
QA-dimension checklist, the Norma_Resume comparison-evidence-only
boundary, and doctrine cross-references — it is a doctrine-record
consistency check, not a résumé generator or renderer.

**141.13 Package-time first-party actionability recheck —
CAREER_OS_PACKAGE_GATE_HARDENING_V1 (extends §141, not a new top-level
section — for the same reason §141.6 and §141.10 give: `project_state.json`'s
`latest_locked_section` tracks the highest top-level Blueprint heading,
and `tests/resume_reference_style_lock_v1_test.py` pins that field to
141; this lock is recorded as §141 subsections so that pinned,
non-editable regression check and the live `src/career_os_state.py`
section-count validator agree).** Earned by two reproduced live
defects, recorded in full at `docs/resume/BORA_PACKAGE_SPAWN_GATE_V1.json`:
a Santander resume/cover-letter package was produced before the exact
current first-party requisition had been re-opened and proven actionable
in the operating session doing the package work, and a DraftKings resume
drifted from the canonical gold family and leaked internal Career OS
language. This section sharpens the timing of the already-locked §135
gate (`LIVE_ROLE_VERIFIED_ACTIONABILITY_GATE_V1`) to also cover package
time — it does not create a competing actionability system, a new
posting-state axis, or a new enum.

Immediately before Claude drafting, DOCX mutation, cover-letter
drafting, or any other meaningful package work, the exact current
first-party employer requisition must be re-opened in the current
operating session and must still establish matching requisition identity
plus substantive current job-description content and a current
actionable application route/instruction — §135's existing two-part
"successfully established" test. A prior pursuit-time pass of §135 does
not by itself satisfy this package-time recheck. A blank or contentless
requisition shell, a JavaScript-only page with no recoverable current JD
content, a generic careers/search redirect, a page-not-found response,
an expired/closed page, an identity mismatch, or a missing current
application route fails the package gate; discovery indexes,
aggregators, cached snippets, prior captures, chat summaries, and memory
cannot rescue it — consistent with §135's existing rule that discovery/
index evidence may never by itself authorize meaningful tailoring,
package, or application work.

When the package-time actionability recheck fails, no resume, cover
letter, or other candidate-facing package may be generated or revised
for that role. Preserve historical analysis if useful, and report the
current role as non-actionable/verification-required using the existing,
independent `role_status`/`source_verification_status` axes already
defined in `schemas/job.schema.json` (§§19-21/135) — never a new
persisted job/actionability enum. Do not collapse the two axes or infer
one from the other. A later closed/stale posting does not erase
historical Employer Truth, historical qualification analysis, or
Submitted Application Truth already captured for that role; only current
package-time actionability changes.

**141.14 Gold-artifact-based spawning gate and internal-jargon
translation.** Resume spawning must use the exact current Bora
gold-quality DOCX artifact (`Bora_Chaush_Cable_One_Claude_First_G_
Adjudicated.docx`, §141.10) as the starting document when that artifact
is available; its SHA-256 must be verified against the canonical
gold-reference record
(`ec3a9f9c6e2fc429e01892f61a074a71319ec6586566b6c1cf60808eba2f3f70`)
before cloning and making bounded content edits. A chat or agent must
not reconstruct the gold family from scratch with a fresh document/
template, ad-hoc tables, margins, typography, or section grammar merely
by reading doctrine — this is exactly how the DraftKings drift
reproduced. If the exact gold artifact is unavailable or its hash does
not match, stop with `GOLD_REFERENCE_ARTIFACT_REQUIRED` rather than
improvising a new resume template.

Candidate-facing package text must not expose internal Career OS/
governance/evidence-system/implementation-control language — such as
"human approval," "operating system," "fail-closed," "queue-level
eligibility," "deterministic boundary," or "Candidate Truth" — unless the
exact term is independently job-relevant and recruiter-natural; otherwise
translate the supported work into ordinary professional American
English. This extends, and does not replace, §141.11's human-naturalness
QA dimension and `.cursor/rules/resume.mdc`'s Candidate-Facing Style
section.

Before delivery to Bora, package QA must explicitly reject a
PROFESSIONAL SUMMARY heading, noncanonical section order, noncanonical
Title | Employer work grammar, missing required gold-family hyperlink
objects, rendered overflow/clipping/overlap, sub-92-percent meaningful
utilization, or other material gold-family structural drift, unless an
explicit employer format instruction requires a documented exception.
This makes §141.11's "reference conformance" and "rendered one-page
quality" dimensions explicit reject conditions rather than leaving the
structural drift patterns implicit.

**141.15 Doctrine-only lock / build-economy boundary (package-gate
addendum).** §141.13-§141.14 add no new schema field or enum, no new
Candidate Truth, no qualification or decision runtime change, and no
generator/renderer/automated-validator implementation — none of that is
pre-authorized merely because this doctrine exists (§133's build-economy
gate continues to govern any future runtime-implementation proposal).
`AGENTS.md` and `.cursor/rules/resume.mdc` are updated in the same change
to cross-reference this package-gate record so that AGENTS.md,
BLUEPRINT.md, `.cursor/rules/resume.mdc`, and
`docs/resume/BORA_PACKAGE_SPAWN_GATE_V1.json` express one consistent
fail-closed operating chain; `schemas/`, `src/`, `resume/`, and the
existing protected-master/structured-patch/claim-lineage architecture
remain unchanged. `tests/resume_package_spawn_gate_v1_test.py` is a
focused regression test verifying the package-time actionability
recheck, the gold-artifact spawn gate and `GOLD_REFERENCE_ARTIFACT_
REQUIRED` stop condition, the internal-jargon translation requirement,
the pre-delivery QA reject conditions, the Santander/DraftKings
reproduced-failure citations, and doctrine cross-references — it is a
doctrine-record consistency check, not a résumé generator or renderer.

