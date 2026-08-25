# Bora Employer Pipeline OS — Change Log

This file records material changes to the system.

Do not use this file for every typo or formatting edit. Record changes that affect:

* architecture;
* data models;
* evidence rules;
* claim rules;
* resume logic;
* immigration/work-authorization handling;
* integrations;
* application workflow;
* safety controls;
* schemas;
* validators;
* production behavior.

---

## 2026-08-25 — Workbench Initialization

### Added

* Initialized Git repository.
* Added canonical `BLUEPRINT.md`.
* Added `AGENTS.md` operating contract.
* Added `CURRENT_STATE.md`.

### Blueprint Hardening

Added or reinforced:

* external market-softness diagnostic handling;
* `LEGAL_VERIFICATION_REQUIRED` boundary for unresolved consequential immigration/work-authorization interpretation;
* strict JSON Schema validation before structured AI output reaches downstream rendering or production components.

### Architecture Status

Locked tool roles:

* ChatGPT — architecture, research, semantic reasoning, quality decisions
* Cursor — primary implementation and repository agent
* Gemini — independent verifier and backup
* Claude — optional escalation/review only

### Current Status

Workbench setup in progress.

No production features or external integrations have been built yet.

---

## Change Entry Template

Copy this section for future material changes.

### YYYY-MM-DD — Short Change Name

**Reason**

Why the change was required.

**Changed**

* item
* item

**Affected Areas**

* files/modules/rules

**Risks / Tradeoffs**

* risk or tradeoff

**Tests / Verification**

* what was tested or reviewed

**Approved By**

Bora

**Status**

Approved / Implemented / Reverted
