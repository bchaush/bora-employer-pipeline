# Career OS Operate Mode V1 — Run Contract V1.6

Operator CLI: src/career_os_run_v1.py (CAREER_OS_RUN_CONTRACT_V1_6).

It is pure/local. It reads caller-supplied files and writes local receipts/output. It never calls Drive, Sheets, the web, or an employer application surface. ChatGPT connectors perform external reads/writes and hand exact readbacks to the CLI.

A step is done only when its receipt exists.
Every run's final reply ends with the closeout block.
Upload package files as-is. Never convert the PDF, DOCX, or ZIP into Google Docs/Sheets formats.

## State machine

0. readback (again after every Ledger write, then confirm-write)
1. preflight
2. slate
3. STOP for Bora decision, then decide
4. resume-model, then package with --resume-model, for Bora-PURSUE roles only
5. connector uploads exactly 3 files as-is
6. connector downloads/readbacks the same 3 files
7. verify-persisted
8. human visual + claim review
9. Bora manual submit
10. record-submit
11. closeout

## Quick reference commands

All examples use local files produced/downloaded by ChatGPT.

### 0. readback (the only way to build ledger.json)

Never hand-build, retype or partly read ledger.json. Download the whole Production Ledger with the Google Drive connector, exported as .xlsx (Microsoft Excel format), save it as is, and let the CLI read it:

    python src/career_os_run_v1.py readback \
      --xlsx ledger.xlsx \
      --out ledger.json \
      --receipt receipts/readback.json

The CLI parses the file itself (never parse it yourself) and reads the JOBS, APPLICATIONS, LOG and NETWORK tabs whole, so nothing is copied by hand and no row can be left out. Every cell must be text or empty; a number, true/false, error or date cell is refused (READBACK_CELL_TYPE), so fix that cell in the sheet as plain text and export again. Blank cells, blank rows and styled blank cells past the last header column are ignored; any non-blank cell past the header is refused.

Fallback only if the .xlsx export is unavailable: the raw values from the Google Sheets read-values call (formatted values, header row first), saved as they come:

    {
      "JOBS": [["Job_ID", "Company", "..."], ["ACME::DATA-ANALYST", "Acme", "..."]],
      "APPLICATIONS": [["Application_ID", "..."]],
      "LOG": [["Run_ID", "..."]],
      "NETWORK": [["Contact_ID", "..."]]
    }

    python src/career_os_run_v1.py readback --raw raw_values.json --out ledger.json --receipt receipts/readback.json

With --raw it changes only three things: null cells become "", short rows are padded with "", and rows whose every cell is "" are skipped; any cell beyond the last header column (even a blank one) is refused.

Both sources fail closed on any header that is not exactly the live header (no trimming), a non-string cell, a bare-number cell (READBACK_SUSPECT_NUMERIC_CELL: no Ledger cell holds one; it means the read was corrupted), or a duplicate Job_ID. Use the resulting ledger.json for every --ledger, and run readback again after every Ledger write. If neither source can be read whole, stop and tell Bora.

### 0b. confirm-write (after every Ledger write)

After writing the rows a command printed, read the whole Ledger again and prove the write:

    python src/career_os_run_v1.py confirm-write \
      --ledger ledger_after_write.json \
      --written receipts/decide_acme.json \
      --receipt receipts/confirm_decide_acme.json

--written takes the receipt of each command whose rows were written (slate, decide, verify-persisted, record-submit, record-external-submit, network-add, network-update, record-outcome); repeat it for several. PASS means every printed row is in the Ledger exactly. WRITE_NOT_CONFIRMED names the row and the cells that differ: fix only those cells to the printed values, read back, and run confirm-write again.

### 1. preflight

    python src/career_os_run_v1.py preflight \
      --runtime-root runtime_extracted \
      --expected-main-sha <LIVE_MAIN_SHA> \
      --font-dir governed_fonts_extracted \
      --settings settings.json \
      --adapter career_os_cloud_operate_v1.py \
      --config CAREER_OS_OPERATE_MODE_V1.json \
      --runbook CAREER_OS_OPERATE_MODE_V1.md \
      --runtime-zip Career_OS_Runtime_<sha>_FULL.zip \
      --fonts-zip Liberation_Sans_Governed.zip \
      --receipt receipts/preflight.json

The CLI hashes the actual runtime ZIP and governed-fonts ZIP. It requires these live SETTINGS keys:
CANONICAL_MAIN_SHA, RUNTIME_BUNDLE_SHA256, CLOUD_ADAPTER_SHA256, OPERATE_MODE_CONFIG_SHA256, OPERATE_MODE_RUNBOOK_SHA256, GOVERNED_FONTS_SHA256, CLOUD_RENDER_PROFILE.

CLOUD_RENDER_PROFILE must equal CHATGPT_CLOUD_OPERATIONAL_RENDER_V1.

### Posting verification (before slate)

Verify the employer and the live posting, not where it is posted (Bora's rule, 2026-10-06). Open the posting live in this session; a cached search result or an index snippet is never enough. Then give every role one tier, written first in its screening "source", followed by the evidence:

- EMPLOYER_SITE: the posting is open on the employer's own careers site or applicant system.
- SCHOOL_PORTAL: the posting is open on Handshake or a university career portal, and the employer checks out: a real company website, the posting's contact email on the company's own domain (not Gmail/Yahoo/Outlook), and a public footprint (address, leadership, news). Write that evidence, e.g. "SCHOOL_PORTAL (Babson; contact dkent@ae-ventures.com, same person listed on ae-ventures.com/careers)".
- JOB_BOARD: only a job board or repost (LinkedIn, Indeed, aggregators). First look for the employer's own posting or contact; if none, tell Bora in one line. His PURSUE then stands as his verification; write it, e.g. "JOB_BOARD (LinkedIn repost; Bora verified)".

Scam signs always stop the role, whatever the tier: a fee to apply or train, a check to cash or money to forward, bank, card or SSN details before an offer, a free-mail contact address, an interview only by chat, or pay far above the role. Name the sign and stop.

Every role Bora sends is screened and goes through slate, even when it is not ready to package; never keep a role outside the Ledger. If Bora already applied (he says so, or a screenshot shows "Applied"), record it with record-external-submit; do not package it.

### 2. slate

    python src/career_os_run_v1.py slate \
      --screening screening.json \
      --ledger ledger.json \
      --as-of 2026-10-06T09:40:00-04:00 \
      --receipt receipts/slate.json

--as-of is the screening time with its UTC offset; it is written to First_Seen and Last_Verified of every new JOBS row.

A role already present by Job_ID or non-empty Official_URL is ALREADY_TRACKED and produces no new JOBS row. Its line starts with the Ledger Job_ID (with screened_as=<your id> when they differ): use that Ledger Job_ID in every later command.
"source" must start with EMPLOYER_SITE, SCHOOL_PORTAL or JOB_BOARD (see Posting verification); anything else is SLATE_INVALID.
Unknown/unclear onsite geography requires HOLD. Numeric/letter fit scoring is forbidden. Bora_Decision remains empty until Bora acts.

Minimal screening.json:

    [
      {
        "job_id": "ACME::DATA-ANALYST",
        "company": "Acme",
        "role": "Data Analyst",
        "official_url": "https://careers.acme.example/jobs/123",
        "source": "EMPLOYER_SITE (careers.acme.example, opened live 2026-10-06)",
        "location_arrangement": "Remote",
        "Geography_State": "PASS",
        "work_authorization_text": "No sponsorship restriction stated.",
        "OPT_Screen_State": "HUMAN_REQUIRED",
        "mandatory_gaps": [],
        "recommendation": "PURSUE",
        "reasons": ["Verified requirements align with approved evidence."]
      }
    ]

### Ledger readback shape

readback produces ledger.json with JOBS, APPLICATIONS and LOG arrays (and NETWORK when read). Each row uses the exact live headers.

JOBS headers (20):
Job_ID, Company, Role, Discovery_Source, Discovery_URL, Official_URL, First_Seen, Last_Verified, Pipeline_State, Freshness_State, Geography_State, OPT_Screen_State, Candidate_Condition_State, Threshold_State, Role_Status, Match_State, Decision, Bora_Decision, Package_Status, Application_Status.

APPLICATIONS headers (10):
Application_ID, Job_ID, Applied_Date, Resume_Version, Cover_Letter_Version, Channel, Current_Status, Last_Update, Next_Action, Outcome.

LOG headers (9):
Run_ID, Timestamp, Stage, Source, Job_ID, Status, Error_Code, Engine_Baseline, Notes.

### 3. STOP for Bora decision, then decide

Only Bora decides PURSUE|WATCH|REJECT. A system recommendation never grants package or submission authority. For each role, run decide with exactly Bora's decision:

    python src/career_os_run_v1.py decide \
      --ledger ledger.json \
      --job-id "ACME::DATA-ANALYST" \
      --decision PURSUE \
      --decided-at 2026-10-06T09:45:00-04:00 \
      --receipt receipts/decide_acme.json

It fingerprints the JOBS row from the same ledger.json, supersedes the latest decision automatically, and prints JOBS_UPDATE (the one Bora_Decision cell) and LOG_ROW_VALUES (one append). Write exactly those, then run readback again. ALREADY_DECIDED means nothing needs writing.

Check any role at any time:

    python src/career_os_run_v1.py pursuit-state \
      --ledger ledger.json \
      --job-id "ACME::DATA-ANALYST" \
      --receipt receipts/state_acme.json

STALE_RECONFIRMATION_REQUIRED means the JOBS context changed after Bora's decision; ask Bora and run decide again. Use the printed latest_event_id and decision_context_fingerprint in the package attestation.

OPT_Screen_State, Geography_State and the system Decision are information for Bora. Once pursuit-state shows Bora's PURSUE with authorizes_pursuit true, they never block package; keep them as they are and mention them once.

### 4. resume-model, then package

Never assemble the resume model by hand. resume-model builds it from the approved language by id and proves it passes the page-fill floor and the pre-render quality checks before package runs:

    python src/career_os_run_v1.py resume-model \
      --job-id "ACME::DATA-ANALYST" \
      --project MARKETMIND \
      --summary S002 \
      --runtime-root runtime_extracted \
      --font-dir governed_fonts_extracted \
      --expected-main-sha <LIVE_MAIN_SHA> \
      --out run_output_model/model.json \
      --receipt receipts/resume_model_acme.json

Choices (the only ones; everything else is fixed by the approved recipe):
- --project MARKETMIND (default; data, analytics, operations, automation roles) or MARKET_EMPIRE (product, fintech, edtech, front-end or business-analyst roles where a tested React/TypeScript demo fits better). Pick per role and tell Bora which one was used and why, in one line.
- --summary: MARKETMIND takes S002 or S003; MARKET_EMPIRE takes S002.
- --order (optional): comma-separated bullet ids to put first within their own entry, most relevant first, e.g. B013,B022.

Work is Winter Walk (B010, B012, B013, B014), TELUS Digital (B008, B009) and D Commerce Bank (B001, B002), newest first. MARKETMIND adds MarketMind B003-B007; MARKET_EMPIRE adds Market Empire B019-B023 and records MarketMind as NOT_RELEVANT_PER_CROSSWALK. Bulmarma, B011, B015 and S005 are never used. RESUME_MODEL_* codes are gates: quote them and stop.

Then package with that model (it replaces any resume_model in request.json):

    python src/career_os_run_v1.py package \
      --request request.json \
      --ledger ledger.json \
      --runtime-root runtime_extracted \
      --font-dir governed_fonts_extracted \
      --output-root run_output \
      --expected-main-sha <LIVE_MAIN_SHA> \
      --company "Acme" \
      --role "Data Analyst" \
      --target-folder-name "2026-10-05 — Acme — Data Analyst" \
      --resume-model run_output_model/model.json

The request jobs_rows entry must exactly equal the Ledger JOBS row on Job_ID, Company, Role, and Official_URL. package then replaces jobs_rows and decision_log_rows with the rows from ledger.json, so the pursuit gate always reads the same Ledger file (written to run_output/effective_request.json).
A blank live Official_URL fails with OFFICIAL_URL_MISSING_IN_LEDGER.
Keep --output-root separate from the --out folder of resume-model (package needs an empty persist/). A failed quality check prints each failed check and why after "|" in the failure detail (for example RECRUITER_JARGON_PROHIBITION: hits=[...]); quote it and stop.

persist/ contains exactly:
- Bora_Chaush_<Company>_<Role>_Resume.pdf
- Bora_Chaush_<Company>_<Role>_Resume.docx
- package_bundle.zip

persist_plan.json stays outside persist/.

### 5–6. upload + readback

Upload exactly those 3 files as-is, with no Google Docs conversion. Download/read back the same 3 files to a local directory.

Minimal folder-listing JSON for closeout can be keyed by Job_ID:

    {
      "ACME::DATA-ANALYST": [
        "Bora_Chaush_Acme_Data_Analyst_Resume.pdf",
        "Bora_Chaush_Acme_Data_Analyst_Resume.docx",
        "package_bundle.zip"
      ]
    }

### 7. verify-persisted

    python src/career_os_run_v1.py verify-persisted \
      --plan run_output/persist_plan.json \
      --downloaded-dir drive_readback \
      --receipt receipts/persisted.json

Only exact filenames, byte sizes, and SHA-256s emit PERSISTED_COMPLETE and Package_Status=READY.

### 8. human visual + claim review

Bora reviews the PDF/DOCX and the claim-review table. Automated QA does not replace this.

### 9. Bora manual submit

Career OS never submits externally. Bora alone submits.

### 10. record-submit

    python src/career_os_run_v1.py record-submit \
      --plan run_output/persist_plan.json \
      --persist-receipt receipts/persisted.json \
      --job-id "ACME::DATA-ANALYST" \
      --company "Acme" \
      --role "Data Analyst" \
      --channel "Company careers site" \
      --applied-date "2026-10-05" \
      --bora-confirmed \
      --receipt receipts/submitted.json

Use --receipt-file <path> instead of --bora-confirmed when a separate receipt artifact exists.

The emitted APPLICATIONS row has exactly the 10 live columns.
Resume_Version is:
<pdf filename> | sha256:<plan-derived sha256>

Next_Action is Monitor for employer response.

### 10b. record-external-submit (applied outside a Career OS package)

When Bora applied himself without a Career OS package (Handshake Quick apply, LinkedIn Easy Apply with his own résumé), record it only after he confirms:

    python src/career_os_run_v1.py record-external-submit \
      --ledger ledger.json \
      --job-id "ACME::DATA-ANALYST" \
      --channel "Handshake Quick apply" \
      --applied-date 2026-10-06 \
      --resume-note "Bora's own Handshake résumé" \
      --evidence-note "Handshake shows Applied on October 6, 2026" \
      --bora-confirmed \
      --receipt receipts/external_acme.json

Resume_Version is written as exactly EXTERNAL_NO_CAREER_OS_PACKAGE, never a résumé hash; the résumé note goes into Outcome. Any note with anything hash-like (checked after Unicode normalization) is refused. Notes must be single lines without control, format or separator characters, and --applied-date must be a real calendar date. It refuses a job that already has an APPLICATIONS row or an APPLICATION_RECORDED LOG event on any date. Write the three printed rows exactly, then run readback again. closeout counts such a role as submitted without a plan or folder.

### 11. closeout

    python src/career_os_run_v1.py closeout \
      --slate-receipt receipts/slate.json \
      --ledger ledger_after_writes.json \
      --folders drive_folder_listing.json \
      --plans plans.json \
      --receipt receipts/closeout.json

The slate receipt, not a hand-typed batch list, defines the batch.
A newly processed submitted role must supply its persist plan; otherwise closeout reports PLAN_NOT_SUPPLIED.
An already-tracked historical submitted role may close without a plan only when durable Ledger submission truth exists and its role folder is non-empty.

The final line is exactly one of:
CAREER_OS_RUN_CLOSEOUT: COMPLETE
CAREER_OS_RUN_CLOSEOUT: INCOMPLETE

## Network and outcomes (CAREER_OS_NETWORK_V1)

src/career_os_network_v1.py is a separate local CLI. It never sends a message, never opens LinkedIn or Gmail, and never changes a JOBS decision, a resume, or Candidate Truth. Network access is separate from qualification (BLUEPRINT section 136). Write only the row values it prints; Bora sends every message himself.

For network commands, ledger.json also has a NETWORK array (use [] when the tab has no rows). NETWORK headers (13), in this order:
Contact_ID | Name | Company | Role_Title | How_Found | Relationship | Purpose | Linked_Job_ID | Status | Added_On | Last_Touch | Next_Action_Date | Notes

Contact JSON (exactly these 8 keys). How_Found is the https link where Bora found the person (LinkedIn profile, Brandeis directory, company page), or KNOWN_PERSONALLY with Notes saying how he knows them. No link and no personal tie means the contact is not added.

    {
      "Name": "First Last",
      "Company": "Company",
      "Role_Title": "Their title as shown on the profile",
      "How_Found": "https://www.linkedin.com/in/...",
      "Relationship": "BRANDEIS_ALUMNI",
      "Purpose": "JOB_REFERRAL",
      "Linked_Job_ID": "",
      "Notes": ""
    }

Relationship: BRANDEIS_ALUMNI|FORMER_COLLEAGUE|WINTER_WALK|FACULTY|RECRUITER|OTHER
Purpose: JOB_REFERRAL|INFO_CHAT|CLIENT_PROSPECT
Linked_Job_ID is blank or an existing JOBS Job_ID.

### network-add

    python src/career_os_network_v1.py network-add \
      --ledger ledger.json \
      --contact contact.json \
      --as-of 2026-10-06 \
      --receipt receipts/network_add.json

Append the printed NETWORK_ROW_VALUES to NETWORK and LOG_ROW_VALUES to LOG. ALREADY_IN_NETWORK means the person is already there.

### network-draft

    python src/career_os_network_v1.py network-draft \
      --ledger ledger.json \
      --contact-id NET::XXXXXXXXXXXX \
      --bullet-id B007 \
      --runtime-root runtime_extracted \
      --receipt receipts/network_draft.json

Prints a draft of at most 120 words. The work example is one approved resume bullet whose claims allow networking, quoted exactly. Bora edits and sends it himself. Nothing is written to the Ledger.

### network-update

    python src/career_os_network_v1.py network-update \
      --ledger ledger.json \
      --contact-id NET::XXXXXXXXXXXX \
      --status SENT \
      --as-of 2026-10-06 \
      --note "LinkedIn message" \
      --receipt receipts/network_update.json

Status: SENT|REPLIED|CALL_DONE|REFERRED|NO_REPLY|CLOSED. Next_Action_Date: SENT +7 days, REPLIED +3, CALL_DONE +7, REFERRED +14, NO_REPLY and CLOSED blank. These dates are fixed; there is no override. Overwrite the contact's NETWORK row and append the LOG row.

### record-outcome

    python src/career_os_network_v1.py record-outcome \
      --ledger ledger.json \
      --job-id "ACME::DATA-ANALYST" \
      --status INTERVIEW \
      --as-of 2026-10-09 \
      --note "Recruiter email: phone screen scheduled" \
      --receipt receipts/outcome.json

Status: UNDER_REVIEW|INTERVIEW|REJECTED|OFFER|WITHDRAWN|NO_RESPONSE. Use only what the employer actually sent. Overwrite the APPLICATIONS row and append the LOG row. JOBS is not changed. An OFFER sets Next_Action to confirm work authorization with ISSO before accepting.

### weekly-report

    python src/career_os_network_v1.py weekly-report \
      --ledger ledger.json \
      --from 2026-10-05 \
      --to 2026-10-11 \
      --receipt receipts/weekly.json

Counts only, no scores: jobs first seen, applications submitted, outcomes, contacts added, contact updates, current snapshots, and follow-ups due by --to.

## Rules that do not change

- No numeric or letter fit scores.
- Unknown onsite geography is HOLD.
- Bora alone decides PURSUE/WATCH/REJECT.
- Bora alone submits.
- CLAIM_OWNER_ON_PAGE and MANDATORY_EVIDENCE_ON_PAGE remain mandatory pre-render gates.
- Prior resumes, Drive files, and chat history are not Candidate Truth evidence.
- Desktop/Codespaces are engineering-only fallback paths.
- No cover-letter runtime.
- No auto-submit.
- The system never sends networking messages and never automates LinkedIn.
- A contact needs a real source link or a personal tie (How_Found); no invented people.
