# Career OS Operate Mode V1 — Run Contract V1.1

Operator CLI: src/career_os_run_v1.py (CAREER_OS_RUN_CONTRACT_V1_1).

It is pure/local. It reads caller-supplied files and writes local receipts/output. It never calls Drive, Sheets, the web, or an employer application surface. ChatGPT connectors perform external reads/writes and hand exact readbacks to the CLI.

A step is done only when its receipt exists.
Every run's final reply ends with the closeout block.
Upload package files as-is. Never convert the PDF, DOCX, or ZIP into Google Docs/Sheets formats.

## State machine

1. preflight
2. slate
3. STOP for Bora decision
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

### 1. preflight

    python src/career_os_run_v1.py preflight ^
      --runtime-root runtime_extracted ^
      --expected-main-sha <LIVE_MAIN_SHA> ^
      --font-dir governed_fonts_extracted ^
      --settings settings.json ^
      --adapter career_os_cloud_operate_v1.py ^
      --config CAREER_OS_OPERATE_MODE_V1.json ^
      --runbook CAREER_OS_OPERATE_MODE_V1.md ^
      --runtime-zip Career_OS_Runtime_<sha>_FULL.zip ^
      --fonts-zip Liberation_Sans_Governed.zip ^
      --receipt receipts/preflight.json

The CLI hashes the actual runtime ZIP and governed-fonts ZIP. It requires these live SETTINGS keys:
CANONICAL_MAIN_SHA, RUNTIME_BUNDLE_SHA256, CLOUD_ADAPTER_SHA256, OPERATE_MODE_CONFIG_SHA256, OPERATE_MODE_RUNBOOK_SHA256, GOVERNED_FONTS_SHA256, CLOUD_RENDER_PROFILE.

CLOUD_RENDER_PROFILE must equal CHATGPT_CLOUD_OPERATIONAL_RENDER_V1.

### 2. slate

    python src/career_os_run_v1.py slate ^
      --screening screening.json ^
      --ledger ledger.json ^
      --receipt receipts/slate.json

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

ledger.json always has JOBS, APPLICATIONS, and LOG arrays. Each row uses the exact live headers.

JOBS headers (20):
Job_ID, Company, Role, Discovery_Source, Discovery_URL, Official_URL, First_Seen, Last_Verified, Pipeline_State, Freshness_State, Geography_State, OPT_Screen_State, Candidate_Condition_State, Threshold_State, Role_Status, Match_State, Decision, Bora_Decision, Package_Status, Application_Status.

APPLICATIONS headers (10):
Application_ID, Job_ID, Applied_Date, Resume_Version, Cover_Letter_Version, Channel, Current_Status, Last_Update, Next_Action, Outcome.

LOG headers (9):
Run_ID, Timestamp, Stage, Source, Job_ID, Status, Error_Code, Engine_Baseline, Notes.

Minimal ledger.json:

    {
      "JOBS": [],
      "APPLICATIONS": [],
      "LOG": []
    }

### 3. STOP for Bora decision

Only Bora sets Bora_Decision = PURSUE|WATCH|REJECT. A system recommendation never grants package or submission authority.

### 4. package

    python src/career_os_run_v1.py package ^
      --request request.json ^
      --ledger ledger.json ^
      --runtime-root runtime_extracted ^
      --font-dir governed_fonts_extracted ^
      --output-root run_output ^
      --expected-main-sha <LIVE_MAIN_SHA> ^
      --company "Acme" ^
      --role "Data Analyst" ^
      --target-folder-name "2026-10-05 — Acme — Data Analyst"

The request jobs_rows entry must exactly equal the Ledger JOBS row on Job_ID, Company, Role, and Official_URL.
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

    python src/career_os_run_v1.py verify-persisted ^
      --plan run_output/persist_plan.json ^
      --downloaded-dir drive_readback ^
      --receipt receipts/persisted.json

Only exact filenames, byte sizes, and SHA-256s emit PERSISTED_COMPLETE and Package_Status=READY.

### 8. human visual + claim review

Bora reviews the PDF/DOCX and the claim-review table. Automated QA does not replace this.

### 9. Bora manual submit

Career OS never submits externally. Bora alone submits.

### 10. record-submit

    python src/career_os_run_v1.py record-submit ^
      --plan run_output/persist_plan.json ^
      --persist-receipt receipts/persisted.json ^
      --job-id "ACME::DATA-ANALYST" ^
      --company "Acme" ^
      --role "Data Analyst" ^
      --channel "Company careers site" ^
      --applied-date "2026-10-05" ^
      --bora-confirmed ^
      --receipt receipts/submitted.json

Use --receipt-file <path> instead of --bora-confirmed when a separate receipt artifact exists.

The emitted APPLICATIONS row has exactly the 10 live columns.
Resume_Version is:
<pdf filename> | sha256:<plan-derived sha256>

Next_Action is Monitor for employer response.

### 11. closeout

    python src/career_os_run_v1.py closeout ^
      --slate-receipt receipts/slate.json ^
      --ledger ledger_after_writes.json ^
      --folders drive_folder_listing.json ^
      --plans plans.json ^
      --receipt receipts/closeout.json

The slate receipt, not a hand-typed batch list, defines the batch.
A newly processed submitted role must supply its persist plan; otherwise closeout reports PLAN_NOT_SUPPLIED.
An already-tracked historical submitted role may close without a plan only when durable Ledger submission truth exists and its role folder is non-empty.

The final line is exactly one of:
CAREER_OS_RUN_CLOSEOUT: COMPLETE
CAREER_OS_RUN_CLOSEOUT: INCOMPLETE

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
