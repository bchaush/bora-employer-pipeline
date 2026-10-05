# Career OS Operate Mode V1 — run contract

Operator CLI: `src/career_os_run_v1.py` (`CAREER_OS_RUN_CONTRACT_V1`). It is pure and local: it reads files the operator supplies and writes local receipts only. It never calls Drive, Sheets or the web, and never submits. The ChatGPT connectors perform every Drive/Sheets write and read-back and hand the results to the CLI as files.

**A step is done only when its receipt exists.**
**Every run's final reply ends with the closeout block.**

## State machine

1. **preflight** — `career_os_run_v1.py preflight`: verify the runtime bundle and governed fonts, then compare SETTINGS (canonical main, runtime ZIP SHA, adapter SHA, config SHA, runbook SHA) with the observed artifacts. `CLOUD_RENDER_PROFILE` must equal `CHATGPT_CLOUD_OPERATIONAL_RENDER_V1` when present. Any mismatch is STOP. Receipt: `--receipt`.
2. **slate** — `slate`: validate `screening.json` (exact keys, `PURSUE|WATCH|HOLD|REJECT`, no fit-score content, unknown onsite geography is HOLD) and emit one owned JOBS row-value object per role. `Bora_Decision` stays null. Receipt: slate receipt.
3. **STOP for Bora decision.** Only Bora records `Bora_Decision`. Nothing proceeds on a system recommendation alone.
4. **package** — `package`, only for roles Bora set to PURSUE: runs the cloud adapter, then creates `persist/` with exactly three files (`Bora_Chaush_<company>_<role>_Resume.pdf`, `.docx`, `package_bundle.zip`) and `persist_plan.json` outside `persist/`. Prints the claim-review table and the UPLOAD THESE 3 FILES block. Receipt: `persist_plan.json`.
5. **connector uploads exactly 3** — the Drive connector uploads exactly those three files to the named role folder. No other file is uploaded.
6. **connector downloads/readback** — the connector downloads the three files back from Drive into a local directory.
7. **verify-persisted** — `verify-persisted`: exact names, sizes and SHA-256 against the plan. Only an exact match emits `PERSISTED_COMPLETE` and `Package_Status=READY` row values. Receipt: `--receipt`.
8. **human visual + claim review** — Bora reviews the raw PDF/DOCX and the claim-review table. Automated QA never replaces this.
9. **Bora manual submit** — Bora submits by hand. There is no auto-submit.
10. **record-submit** — `record-submit` with exactly one of `--bora-confirmed` or `--receipt-file`, and the `verify-persisted` receipt. The resume PDF SHA comes from the plan, never from typed input. Emits APPLICATIONS/JOBS/LOG row values for ChatGPT to write. Receipt: `--receipt`.
11. **closeout** — `closeout` over the batch, Ledger readback, Drive folder listing and any plans. The reply ends with `CAREER_OS_RUN_CLOSEOUT: COMPLETE` or `CAREER_OS_RUN_CLOSEOUT: INCOMPLETE`, with deterministic missing items.

## Rules that do not change

- No numeric or letter fit scores, anywhere.
- Unknown onsite geography is HOLD.
- Bora alone decides and submits.
- Visible-evidence integrity is enforced before render by `CLAIM_OWNER_ON_PAGE` and `MANDATORY_EVIDENCE_ON_PAGE`; a failed package is never uploaded.
- Desktop/Codespaces is the engineering fallback for code changes and local debugging, not a run path that skips a receipt.
- No cover-letter runtime.
