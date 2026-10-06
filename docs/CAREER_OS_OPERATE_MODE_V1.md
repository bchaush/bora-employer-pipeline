# Career OS Operate Mode V1 — Run Contract V1.3

Operator CLI: src/career_os_run_v1.py (CAREER_OS_RUN_CONTRACT_V1_3).

It is pure/local. It reads caller-supplied files and writes local receipts/output. It never calls Drive, Sheets, the web, or an employer application surface. ChatGPT connectors perform external reads/writes and hand exact readbacks to the CLI.

A step is done only when its receipt exists.
Every run's final reply ends with the closeout block.
Upload package files as-is. Never convert the PDF, DOCX, or ZIP into Google Docs/Sheets formats.

## State machine

0. readback (again after every Ledger write)
1. preflight
2. slate
3. STOP for Bora decision, then decide
4. package for Bora-PURSUE roles only
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

Never hand-build ledger.json. Read each tab's values with the Google Sheets connector's read-values call (formatted values, header row first), never by downloading or exporting the spreadsheet file and parsing it, and save them as they come:

    {
      "JOBS": [["Job_ID", "Company", "..."], ["ACME::DATA-ANALYST", "Acme", "..."]],
      "APPLICATIONS": [["Application_ID", "..."]],
      "LOG": [["Run_ID", "..."]],
      "NETWORK": [["Contact_ID", "..."]]
    }

    python src/career_os_run_v1.py readback \
      --raw raw_values.json \
      --out ledger.json \
      --receipt receipts/readback.json

It changes only three things: null cells become "", short rows are padded with "", and rows whose every cell is "" are skipped. It fails closed on any header that is not exactly the live header (no trimming), any cell beyond the last header column (even a blank one), a non-string cell, a bare-number cell (READBACK_SUSPECT_NUMERIC_CELL: no Ledger cell holds one; it means the read was corrupted, so read the tab again with the read-values call), or a duplicate Job_ID. NETWORK is optional for run commands and required for network commands. Use the resulting ledger.json for every --ledger, and run readback again after every Ledger write.

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

### 2. slate

    python src/career_os_run_v1.py slate \
      --screening screening.json \
      --ledger ledger.json \
      --as-of 2026-10-06T09:40:00-04:00 \
      --receipt receipts/slate.json

--as-of is the screening time with its UTC offset; it is written to First_Seen and Last_Verified of every new JOBS row.

A role already present by Job_ID or non-empty Official_URL is ALREADY_TRACKED and produces no new JOBS row.
Unknown/unclear onsite geography requires HOLD. Numeric/letter fit scoring is forbidden. Bora_Decision remains empty until Bora acts.

Minimal screening.json:

    [
      {
        "job_id": "ACME::DATA-ANALYST",
        "company": "Acme",
        "role": "Data Analyst",
        "official_url": "https://careers.acme.example/jobs/123",
        "source": "FIRST_PARTY",
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

### 4. package

    python src/career_os_run_v1.py package \
      --request request.json \
      --ledger ledger.json \
      --runtime-root runtime_extracted \
      --font-dir governed_fonts_extracted \
      --output-root run_output \
      --expected-main-sha <LIVE_MAIN_SHA> \
      --company "Acme" \
      --role "Data Analyst" \
      --target-folder-name "2026-10-05 — Acme — Data Analyst"

The request jobs_rows entry must exactly equal the Ledger JOBS row on Job_ID, Company, Role, and Official_URL. package then replaces jobs_rows and decision_log_rows with the rows from ledger.json, so the pursuit gate always reads the same Ledger file (written to run_output/effective_request.json).
A blank live Official_URL fails with OFFICIAL_URL_MISSING_IN_LEDGER.

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

Resume_Version is written as EXTERNAL_NO_CAREER_OS_PACKAGE | <note>, never a résumé hash (a note containing "sha256" is refused). Notes must be single lines without control characters. It refuses a job that already has an APPLICATIONS row or an APPLICATION_RECORDED LOG event on any date. Write the three printed rows exactly, then run readback again. closeout counts such a role as submitted without a plan or folder.

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
