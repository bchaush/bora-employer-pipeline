"""CAREER_OS_RUN_CONTRACT_V1 operator CLI (contract V1_2).

A pure, local run-contract state machine for a ChatGPT-operated Career OS run:

    readback -> preflight -> slate -> STOP for Bora decision -> decide -> package -> connector uploads exactly 3
    -> connector downloads/readback -> verify-persisted -> human visual + claim review -> Bora manual submit -> record-submit
    -> closeout

`readback` is the only way a Ledger readback file is built: it turns the raw Sheets values (arrays of cells, header row first)
into the exact JSON every other command consumes, so no step ever hand-builds Ledger rows.

Every subcommand reads only caller-supplied local files and writes only local receipts/output. There are no Drive, Sheets, web or
submission calls anywhere in this module; the ChatGPT connector performs every external write and read-back and hands the results
to this CLI as files. A step is done only when its receipt exists. Receipts are deterministic canonical JSON (no clock).

Success prints exactly one fenced operator block intended for verbatim paste (closeout additionally ends with its exact status
line). Failure returns a nonzero exit code and one machine-readable line: CAREER_OS_RUN_FAILURE: {json}.

Bora keeps every consequential decision: this module never writes anything; `decide` only turns Bora's explicit decision into
the pursuit_decision.py mutation plan values. It never submits and never records a submission without an explicit
--bora-confirmed or a receipt file.
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import io
import json
import re
import sys
import zipfile
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parent))

import career_os_cloud_operate_v1 as cloud  # noqa: E402
import gold_package_handoff as handoff  # noqa: E402
import pursuit_decision  # noqa: E402

RUN_CONTRACT_ID = "CAREER_OS_RUN_CONTRACT_V1_2"
EXIT_OK, EXIT_STOP, EXIT_ERROR = 0, 1, 2
FAILURE_MARKER = "CAREER_OS_RUN_FAILURE:"
CLOSEOUT_MARKER = "CAREER_OS_RUN_CLOSEOUT:"
FENCE = "```"
EFFECTIVE_REQUEST_FILE = "effective_request.json"

# SETTINGS readback keys (flat object, or a list of {"Key"/"Value"} rows).
SETTINGS_CANONICAL_MAIN = "CANONICAL_MAIN_SHA"
SETTINGS_RUNTIME_SHA = "RUNTIME_BUNDLE_SHA256"
SETTINGS_ADAPTER_SHA = "CLOUD_ADAPTER_SHA256"
SETTINGS_CONFIG_SHA = "OPERATE_MODE_CONFIG_SHA256"
SETTINGS_RUNBOOK_SHA = "OPERATE_MODE_RUNBOOK_SHA256"
SETTINGS_FONTS_SHA = "GOVERNED_FONTS_SHA256"
SETTINGS_PROFILE = "CLOUD_RENDER_PROFILE"

JOBS_HEADERS = ("Job_ID", "Company", "Role", "Discovery_Source", "Discovery_URL", "Official_URL", "First_Seen", "Last_Verified",
                "Pipeline_State", "Freshness_State", "Geography_State", "OPT_Screen_State", "Candidate_Condition_State",
                "Threshold_State", "Role_Status", "Match_State", "Decision", "Bora_Decision", "Package_Status", "Application_Status")
APPLICATIONS_HEADERS = ("Application_ID", "Job_ID", "Applied_Date", "Resume_Version", "Cover_Letter_Version", "Channel",
                        "Current_Status", "Last_Update", "Next_Action", "Outcome")
LOG_HEADERS = ("Run_ID", "Timestamp", "Stage", "Source", "Job_ID", "Status", "Error_Code", "Engine_Baseline", "Notes")
NETWORK_HEADERS = ("Contact_ID", "Name", "Company", "Role_Title", "How_Found", "Relationship", "Purpose", "Linked_Job_ID",
                   "Status", "Added_On", "Last_Touch", "Next_Action_Date", "Notes")
READBACK_TABS = (("JOBS", JOBS_HEADERS, True), ("APPLICATIONS", APPLICATIONS_HEADERS, True), ("LOG", LOG_HEADERS, True),
                 ("NETWORK", NETWORK_HEADERS, False))
AWARE_TIMESTAMP = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2}(\.\d+)?)?(Z|[+-]\d{2}:\d{2})$")

SLATE_KEYS = ("job_id", "company", "role", "official_url", "source", "location_arrangement", "Geography_State",
              "work_authorization_text", "OPT_Screen_State", "mandatory_gaps", "recommendation", "reasons")
SLATE_TEXT_KEYS = ("job_id", "company", "role", "official_url", "source", "location_arrangement", "Geography_State",
                   "work_authorization_text", "OPT_Screen_State")
SLATE_LIST_KEYS = ("mandatory_gaps", "reasons")
RECOMMENDATIONS = ("PURSUE", "WATCH", "HOLD", "REJECT")
UNKNOWN_GEOGRAPHY = frozenset({"", "UNKNOWN", "UNCLEAR", "UNRESOLVED", "NOT_SPECIFIED", "NOT SPECIFIED"})

PLAN_SPEC = "CAREER_OS_PERSIST_PLAN_V1"
PERSIST_RECEIPT_SPEC = "CAREER_OS_PERSIST_VERIFIED_V1"
PERSIST_DIR = "persist"
PLAN_FILE = "persist_plan.json"
BUNDLE_NAME = "package_bundle.zip"
READY_PACKAGE_STATES = frozenset({"READY", "PERSISTED_COMPLETE"})


class RunError(Exception):
    """Fail-closed CLI outcome with a stable CODE."""

    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(code, detail)
        self.code = code
        self.detail = detail


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:  # argparse would print usage to stderr; failures are one machine-readable block
        raise RunError("ARGUMENT_ERROR", message)


# Helpers ----------------------------------------------------------------------------------------

def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8") + b"\n"


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_json(path: str, what: str) -> Any:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise RunError("INPUT_UNREADABLE", "%s: %s" % (what, type(error).__name__)) from error


def read_bytes(path: str, what: str) -> bytes:
    try:
        return Path(path).read_bytes()
    except OSError as error:
        raise RunError("INPUT_UNREADABLE", "%s: %s" % (what, type(error).__name__)) from error


def write_receipt(path: str, value: Mapping[str, Any]) -> str:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    data = canonical_bytes(value)
    target.write_bytes(data)
    return sha256_hex(data)


def block(lines: Sequence[str]) -> str:
    return FENCE + "text\n" + "\n".join(lines) + "\n" + FENCE


def sanitize(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]+", "_", str(value)).strip("_")
    if not cleaned:
        raise RunError("NAME_UNSANITIZABLE", repr(value))
    return cleaned


def require_sha(value: str, what: str) -> str:
    if not re.fullmatch(r"[0-9a-f]{64}", str(value or "")):
        raise RunError("SHA256_INVALID", what)
    return value


def non_empty(value: Any) -> bool:
    return value is not None and str(value).strip() != ""


def _require_exact_row_shape(row: Mapping[str, Any], headers: Sequence[str], label: str) -> None:
    keys = set(row)
    expected = set(headers)
    if keys != expected:
        missing = sorted(expected - keys)
        extra = sorted(keys - expected)
        raise RunError("LEDGER_SHAPE_INVALID", "%s missing=%s extra=%s" % (label, missing, extra))


def load_ledger(path: str) -> dict:
    ledger = read_json(path, "Ledger readback")
    if not isinstance(ledger, Mapping):
        raise RunError("LEDGER_INVALID", "Ledger readback must be an object")
    for name, headers in (("JOBS", JOBS_HEADERS), ("APPLICATIONS", APPLICATIONS_HEADERS), ("LOG", LOG_HEADERS)):
        rows = ledger.get(name)
        if not isinstance(rows, list):
            raise RunError("LEDGER_INVALID", "%s must be an array" % name)
        for index, row in enumerate(rows):
            if not isinstance(row, Mapping):
                raise RunError("LEDGER_SHAPE_INVALID", "%s[%d] must be an object" % (name, index))
            _require_exact_row_shape(row, headers, "%s[%d]" % (name, index))
    return dict(ledger)


def _resume_sha_from_version(value: Any) -> Optional[str]:
    match = re.search(r"sha256:([0-9a-fA-F]{64})(?:\b|$)", str(value or ""))
    return match.group(1).lower() if match else None


def require_aware_timestamp(value: Any, what: str) -> str:
    text = str(value or "")
    if not AWARE_TIMESTAMP.match(text):
        raise RunError("TIMESTAMP_INVALID", "%s must be an ISO timestamp with a UTC offset, e.g. 2026-10-06T09:40:00-04:00" % what)
    return text


# readback ---------------------------------------------------------------------------------------

def normalize_tab(name: str, values: Any, headers: Sequence[str]) -> tuple:
    """Raw Sheets values (header row first) -> exact row objects.

    The only changes made: null cells become "", rows shorter than the header are padded with "", and rows whose every cell is
    exactly "" are skipped. Everything else fails closed: the header must match exactly (no trimming), and any cell beyond the
    last header column, even a blank one, is refused."""
    if not isinstance(values, list) or not values or not isinstance(values[0], list):
        raise RunError("READBACK_INVALID", "%s must be an array of rows with the header row first" % name)
    header = list(values[0])
    if header != list(headers):
        raise RunError("READBACK_HEADER_MISMATCH", "%s header is %s; expected exactly %s" % (name, header, list(headers)))
    rows, skipped = [], 0
    for number, raw in enumerate(values[1:], start=2):
        if not isinstance(raw, list):
            raise RunError("READBACK_INVALID", "%s row %d is not an array" % (name, number))
        cells = []
        for cell in raw:
            if cell is None:
                cells.append("")
            elif isinstance(cell, str):
                cells.append(cell)
            else:
                raise RunError("READBACK_CELL_TYPE", "%s row %d has a %s cell; read the sheet with formatted (string) values"
                               % (name, number, type(cell).__name__))
        if len(cells) > len(headers):
            raise RunError("READBACK_ROW_TOO_LONG", "%s row %d has %d cells; the header has %d" % (name, number, len(cells), len(headers)))
        cells = cells + [""] * (len(headers) - len(cells))
        if all(cell == "" for cell in cells):
            skipped += 1
            continue
        rows.append(dict(zip(headers, cells)))
    return rows, skipped


def cmd_readback(args: argparse.Namespace) -> tuple:
    raw = read_json(args.raw, "raw Sheets values")
    if not isinstance(raw, Mapping):
        raise RunError("READBACK_INVALID", "raw values must be an object keyed by tab name")
    unknown = sorted(set(raw) - {name for name, _headers, _required in READBACK_TABS})
    if unknown:
        raise RunError("READBACK_INVALID", "unknown tabs %s" % unknown)
    ledger, counts = {}, []
    for name, headers, required in READBACK_TABS:
        if name not in raw:
            if required:
                raise RunError("READBACK_INVALID", "%s values are required" % name)
            continue
        rows, skipped = normalize_tab(name, raw[name], headers)
        ledger[name] = rows
        counts.append("%s rows=%d blank_rows_skipped=%d" % (name, len(rows), skipped))
    ids = [row["Job_ID"] for row in ledger["JOBS"]]
    duplicates = sorted({job_id for job_id in ids if ids.count(job_id) > 1})
    if duplicates:
        raise RunError("READBACK_DUPLICATE_JOB_ID", ",".join(duplicates))
    ledger_sha = write_receipt(args.out, ledger)
    load_ledger(args.out)
    receipt = {"spec": "CAREER_OS_RUN_READBACK_RECEIPT_V1", "contract": RUN_CONTRACT_ID,
               "raw_sha256": sha256_hex(read_bytes(args.raw, "raw Sheets values")), "ledger_sha256": ledger_sha, "counts": counts}
    receipt_sha = write_receipt(args.receipt, receipt)
    lines = ["CAREER_OS_RUN_READBACK: LEDGER FILE READY (use this file for every --ledger in this run)", "ledger: " + args.out,
             "ledger_sha256: " + ledger_sha] + counts + ["receipt_sha256: " + receipt_sha]
    return EXIT_OK, block(lines), None


# decide / pursuit-state -------------------------------------------------------------------------

def _single_job(ledger: Mapping[str, Any], job_id: str) -> Mapping[str, Any]:
    rows = [row for row in ledger["JOBS"] if row.get("Job_ID") == job_id]
    if len(rows) != 1:
        raise RunError("JOB_UNRESOLVED", "%s must match exactly one Ledger JOBS row (found %d)" % (job_id, len(rows)))
    return rows[0]


def _pursuit_state(ledger: Mapping[str, Any], job_id: str) -> tuple:
    row = _single_job(ledger, job_id)
    try:
        state = pursuit_decision.derive_current_pursuit_state(row, ledger["LOG"])
        fingerprint = pursuit_decision.compute_context_fingerprint(row)
    except pursuit_decision.PursuitDecisionError as error:
        raise RunError(error.error_code, str(error)) from error
    return state, fingerprint


def cmd_pursuit_state(args: argparse.Namespace) -> tuple:
    ledger = load_ledger(args.ledger)
    state, fingerprint = _pursuit_state(ledger, args.job_id)
    receipt = {"spec": "CAREER_OS_RUN_PURSUIT_STATE_RECEIPT_V1", "contract": RUN_CONTRACT_ID, "job_id": args.job_id,
               "state": state["state"], "authorizes_pursuit": state["authorizes_pursuit"],
               "latest_event_id": state["latest_event_id"], "decision_context_fingerprint": fingerprint}
    receipt_sha = write_receipt(args.receipt, receipt)
    lines = ["CAREER_OS_RUN_PURSUIT_STATE " + args.job_id, "state: %s" % state["state"],
             "authorizes_pursuit: %s" % ("true" if state["authorizes_pursuit"] else "false"),
             "latest_event_id: %s" % (state["latest_event_id"] or ""), "decision_context_fingerprint: " + fingerprint,
             "receipt_sha256: " + receipt_sha]
    return EXIT_OK, block(lines), None


def cmd_decide(args: argparse.Namespace) -> tuple:
    ledger = load_ledger(args.ledger)
    decided_at = require_aware_timestamp(args.decided_at, "--decided-at")
    if args.decision not in pursuit_decision.VALID_DECISIONS:
        raise RunError("INVALID_DECISION", "--decision must be PURSUE, WATCH or REJECT")
    state, fingerprint = _pursuit_state(ledger, args.job_id)
    if state["state"] == args.decision:
        raise RunError("ALREADY_DECIDED", "%s is already %s on the current JOBS context" % (args.job_id, args.decision))
    run_id = "DECISION::%s::%s" % (args.job_id, decided_at)
    request = {"job_id": args.job_id, "decision": args.decision, "reviewed_context_fingerprint": fingerprint,
               "decision_run_id": run_id, "decided_at": decided_at, "supersedes_event_id": state["latest_event_id"],
               "reason_note": args.reason_note}
    try:
        plan = pursuit_decision.build_decision_mutation_plan(request, ledger["JOBS"], ledger["LOG"])
    except pursuit_decision.PursuitDecisionError as error:
        raise RunError(error.error_code, str(error)) from error
    if not plan["log_mutations"]:
        raise RunError("ALREADY_RECORDED", "this exact decision event is already in LOG")
    log = {key: ("" if value is None else value) for key, value in plan["log_mutations"][0].items()}
    _require_exact_row_shape(log, LOG_HEADERS, "LOG")
    jobs_update = {"Job_ID": args.job_id, "Bora_Decision": args.decision}
    receipt = {"spec": "CAREER_OS_RUN_DECIDE_RECEIPT_V1", "contract": RUN_CONTRACT_ID, "request": request,
               "jobs_update": jobs_update, "log_row": log}
    receipt_sha = write_receipt(args.receipt, receipt)
    lines = ["CAREER_OS_RUN_DECIDE (Bora's decision; set this one JOBS cell and append this LOG row exactly, then run readback again)",
             "previous_state: %s" % state["state"],
             "JOBS_UPDATE: " + json.dumps(jobs_update, ensure_ascii=False),
             "LOG_ROW_VALUES: " + json.dumps(log, ensure_ascii=False),
             "receipt_sha256: " + receipt_sha]
    return EXIT_OK, block(lines), None


# preflight --------------------------------------------------------------------------------------

def _settings_map(raw: Any) -> dict:
    if isinstance(raw, Mapping):
        return {str(key): value for key, value in raw.items()}
    if isinstance(raw, list):
        result = {}
        for row in raw:
            if isinstance(row, Mapping):
                key = row.get("Key", row.get("key"))
                if key is not None:
                    result[str(key)] = row.get("Value", row.get("value"))
        return result
    raise RunError("SETTINGS_SHAPE_INVALID", "SETTINGS readback must be an object or a list of Key/Value rows")


def cmd_preflight(args: argparse.Namespace) -> tuple:
    settings = _settings_map(read_json(args.settings, "SETTINGS readback"))
    expected = args.expected_main_sha
    observed = {"runtime_bundle_sha256": sha256_hex(read_bytes(args.runtime_zip, "runtime ZIP")),
                "governed_fonts_sha256": sha256_hex(read_bytes(args.fonts_zip, "governed fonts ZIP")),
                "adapter_sha256": sha256_hex(read_bytes(args.adapter, "adapter")),
                "config_sha256": sha256_hex(read_bytes(args.config, "config")),
                "runbook_sha256": sha256_hex(read_bytes(args.runbook, "runbook"))}
    checks = []

    def check(name: str, passed: bool, detail: str = "") -> None:
        checks.append({"check": name, "passed": bool(passed), "detail": detail})

    def settings_equals(name: str, key: str, observed_value: str) -> None:
        recorded = settings.get(key)
        recorded = str(recorded).strip().lower() if recorded is not None else None
        check(name, recorded is not None and recorded == str(observed_value).lower(),
              "SETTINGS %s %s" % (key, "missing" if recorded is None else "differs" if recorded != str(observed_value).lower() else "matches"))

    settings_equals("SETTINGS_CANONICAL_MAIN_MATCHES_EXPECTED", SETTINGS_CANONICAL_MAIN, expected)
    try:
        runtime = cloud.verify_runtime(Path(args.runtime_root), expected)
        check("RUNTIME_VERIFIED", True, "files=%d" % runtime["verified_file_count"])
    except Exception as error:  # any runtime verification failure is a STOP, never a pass
        check("RUNTIME_VERIFIED", False, "%s: %s" % (type(error).__name__, error))
    try:
        cloud.verify_fonts(Path(args.runtime_root), Path(args.font_dir))
        check("GOVERNED_FONTS_VERIFIED", True)
    except Exception as error:
        check("GOVERNED_FONTS_VERIFIED", False, "%s: %s" % (type(error).__name__, error))
    settings_equals("SETTINGS_RUNTIME_SHA_MATCHES_OBSERVED_ZIP", SETTINGS_RUNTIME_SHA, observed["runtime_bundle_sha256"])
    settings_equals("SETTINGS_FONTS_SHA_MATCHES_OBSERVED_ZIP", SETTINGS_FONTS_SHA, observed["governed_fonts_sha256"])
    settings_equals("SETTINGS_ADAPTER_SHA_MATCHES_OBSERVED_ADAPTER", SETTINGS_ADAPTER_SHA, observed["adapter_sha256"])
    settings_equals("SETTINGS_CONFIG_SHA_MATCHES_OBSERVED_CONFIG", SETTINGS_CONFIG_SHA, observed["config_sha256"])
    settings_equals("SETTINGS_RUNBOOK_SHA_MATCHES_OBSERVED_RUNBOOK", SETTINGS_RUNBOOK_SHA, observed["runbook_sha256"])
    profile = settings.get(SETTINGS_PROFILE)
    check("CLOUD_RENDER_PROFILE_REQUIRED", profile == cloud.PROFILE_ID,
          "missing" if profile is None else "present %s" % profile)
    passed = all(item["passed"] for item in checks)
    receipt = {"spec": "CAREER_OS_RUN_PREFLIGHT_RECEIPT_V1", "contract": RUN_CONTRACT_ID, "status": "PASS" if passed else "STOP",
               "expected_main_sha": expected, "observed": observed, "checks": checks}
    receipt_sha = write_receipt(args.receipt, receipt)
    lines = ["RUN CONTRACT PREFLIGHT: %s" % receipt["status"]]
    lines += ["[%s] %s" % ("PASS" if item["passed"] else "STOP", item["check"]) + ("" if item["passed"] else " -- " + item["detail"]) for item in checks]
    lines += ["expected_main_sha: " + expected, "receipt_sha256: " + receipt_sha]
    if passed:
        return EXIT_OK, block(lines), None
    return EXIT_STOP, block(lines), {"command": "preflight", "code": "PREFLIGHT_STOP", "failed_checks": [item["check"] for item in checks if not item["passed"]]}


# slate ------------------------------------------------------------------------------------------

_FIT = r"(?:fit|match|score)"
_PERCENT = r"\d+(?:\.\d+)?\s*%"
FIT_SCORE_PATTERNS = (
    re.compile(r"\bfit\s+score\b|\bmatch\s+score\b|\bscore\s*:", re.IGNORECASE),
    re.compile(r"\bscore\s*(?:of|is|=)\s*\d", re.IGNORECASE),
    re.compile(_PERCENT + r"\s*(?:\w+\s+)?" + _FIT + r"\b", re.IGNORECASE),
    re.compile(r"\b" + _FIT + r"\b(?:\s+(?:score|rating|of|is|at|about|around|approximately))*\s*[:=~-]?\s*" + _PERCENT, re.IGNORECASE),
    # Letter-grade fit: "A fit", "B+ match", "fit grade A", "fit: B-".
    re.compile(r"\b[A-F][+-]?\s+(?i:fit|match)\b"),
    re.compile(r"\b(?i:fit|match)\s+(?i:grade|rating)\s*[:=]?\s*[A-F][+-]?(?![\w+-])"),
    re.compile(r"\b(?i:fit|match)\s*[:=]\s*[A-F][+-]?(?![\w+-])"),
    re.compile(r"\b(?i:grade)\s*[:=]\s*[A-F][+-]?(?![\w+-])\s*(?i:fit|match)\b"),
)
NUMERIC_SCALE = re.compile(r"\b\d+(?:\.\d+)?\s*(?:/|out\s+of)\s*(?:100|10|5)\b", re.IGNORECASE)
FIT_WORD = re.compile(r"\b" + _FIT + r"\b", re.IGNORECASE)


def fit_score_hit(text: str) -> Optional[str]:
    """The first obvious FIT SCORE pattern in text, or None. Ordinary factual percentages (for example '100% onsite') are not hits."""
    for pattern in FIT_SCORE_PATTERNS:
        found = pattern.search(text)
        if found:
            return found.group(0)
    scale = NUMERIC_SCALE.search(text)
    if scale and FIT_WORD.search(text):
        return scale.group(0)
    return None


def _onsite_location_unknown(role: Mapping[str, Any]) -> bool:
    geography = str(role["Geography_State"]).strip().upper()
    if geography in UNKNOWN_GEOGRAPHY:
        return True
    arrangement = str(role["location_arrangement"]).lower()
    onsite = re.search(r"\bon[\s-]?site\b|\bin[\s-]?office\b|\bin[\s-]?person\b", arrangement)
    return bool(onsite and re.search(r"\b(?:unknown|unclear|unspecified|not\s+specified|tbd)\b", arrangement))


def validate_slate_role(role: Any, index: int) -> list:
    where = "role[%d]" % index
    if not isinstance(role, Mapping):
        return ["%s: not an object" % where]
    problems = []
    keys = set(role)
    for key in sorted(keys - set(SLATE_KEYS)):
        problems.append("%s: extra key %s" % (where, key))
    for key in sorted(set(SLATE_KEYS) - keys):
        problems.append("%s: missing key %s" % (where, key))
    if problems:
        return problems
    for key in SLATE_TEXT_KEYS:
        if not isinstance(role[key], str):
            problems.append("%s: %s must be a string" % (where, key))
    for key in ("job_id", "company", "role", "official_url", "Geography_State", "OPT_Screen_State"):
        if isinstance(role[key], str) and not role[key].strip():
            problems.append("%s: %s must be non-empty" % (where, key))
    for key in SLATE_LIST_KEYS:
        if not isinstance(role[key], list) or not all(isinstance(item, str) for item in role[key]):
            problems.append("%s: %s must be a list of strings" % (where, key))
    if role["recommendation"] not in RECOMMENDATIONS:
        problems.append("%s: recommendation must be one of %s" % (where, "|".join(RECOMMENDATIONS)))
    if problems:
        return problems
    for key in SLATE_KEYS:
        if key in ("job_id", "official_url", "recommendation"):
            continue
        for text in role[key] if isinstance(role[key], list) else [role[key]]:
            hit = fit_score_hit(text)
            if hit:
                problems.append("%s: fit score content in %s: %r" % (where, key, hit))
    if _onsite_location_unknown(role) and role["recommendation"] != "HOLD":
        problems.append("%s: onsite geography is unknown or unclear, so recommendation must be HOLD" % where)
    return problems


def jobs_row_values(role: Mapping[str, Any], as_of: str) -> dict:
    """Full live JOBS-row shape for one new screened role. Bora_Decision is never populated here."""
    values = {key: "" for key in JOBS_HEADERS}
    values.update({"Job_ID": role["job_id"], "Company": role["company"], "Role": role["role"], "Discovery_Source": role["source"],
                   "Discovery_URL": role["official_url"], "Official_URL": role["official_url"], "First_Seen": as_of,
                   "Last_Verified": as_of, "Pipeline_State": "REVIEW_READY",
                   "Geography_State": role["Geography_State"], "OPT_Screen_State": role["OPT_Screen_State"],
                   "Match_State": "ANALYZED", "Decision": role["recommendation"], "Bora_Decision": None})
    return values


def _tracked_job(role: Mapping[str, Any], jobs: Sequence[Mapping[str, Any]]) -> Optional[Mapping[str, Any]]:
    official = str(role.get("official_url") or "").strip()
    for row in jobs:
        if row.get("Job_ID") == role.get("job_id"):
            return row
        if official and str(row.get("Official_URL") or "").strip() == official:
            return row
    return None


def cmd_slate(args: argparse.Namespace) -> tuple:
    as_of = require_aware_timestamp(args.as_of, "--as-of")
    raw_bytes = read_bytes(args.screening, "screening")
    try:
        roles = json.loads(raw_bytes.decode("utf-8"))
    except ValueError as error:
        raise RunError("INPUT_UNREADABLE", "screening: invalid JSON") from error
    if not isinstance(roles, list) or not roles:
        raise RunError("SLATE_INVALID", "screening.json must be a non-empty array")
    problems = []
    for index, role in enumerate(roles):
        problems += validate_slate_role(role, index)
    ids = [role["job_id"] for role in roles if isinstance(role, Mapping) and isinstance(role.get("job_id"), str)]
    problems += ["duplicate job_id %s" % job_id for job_id in sorted({item for item in ids if ids.count(item) > 1})]
    if problems:
        raise RunError("SLATE_INVALID", "; ".join(problems[:20]))
    ledger = load_ledger(args.ledger)
    rows = []
    slate = []
    for role in roles:
        tracked = _tracked_job(role, ledger["JOBS"])
        item = {"job_id": role["job_id"], "company": role["company"], "role": role["role"], "recommendation": role["recommendation"],
                "Geography_State": role["Geography_State"], "OPT_Screen_State": role["OPT_Screen_State"],
                "mandatory_gaps": list(role["mandatory_gaps"]), "reasons": list(role["reasons"])}
        if tracked is not None:
            item.update({"tracking_status": "ALREADY_TRACKED", "tracked_job_id": tracked["Job_ID"],
                         "current_Bora_Decision": tracked.get("Bora_Decision"), "current_Package_Status": tracked.get("Package_Status"),
                         "current_Application_Status": tracked.get("Application_Status")})
        else:
            item["tracking_status"] = "NEW"
            rows.append(jobs_row_values(role, as_of))
        slate.append(item)
    receipt = {"spec": "CAREER_OS_RUN_SLATE_RECEIPT_V1", "contract": RUN_CONTRACT_ID, "status": "SLATE_READY_AWAITING_BORA_DECISION",
               "screening_sha256": sha256_hex(raw_bytes), "slate": slate, "jobs_rows": rows}
    receipt_sha = write_receipt(args.receipt, receipt)
    lines = ["CAREER_OS_RUN_SLATE (system recommendations only; STOP for Bora decision)"]
    for item in slate:
        if item["tracking_status"] == "ALREADY_TRACKED":
            lines.append("%s | %s | %s | ALREADY_TRACKED | Bora=%s | Package=%s | Application=%s" % (
                item["job_id"], item["company"], item["role"], item.get("current_Bora_Decision") or "",
                item.get("current_Package_Status") or "", item.get("current_Application_Status") or ""))
        else:
            lines.append("%s | %s | %s | %s | geo=%s | opt=%s | gaps=%s | %s" % (
                item["job_id"], item["company"], item["role"], item["recommendation"], item["Geography_State"], item["OPT_Screen_State"],
                "; ".join(item["mandatory_gaps"]) or "none", "; ".join(item["reasons"])))
    lines.append("JOBS_ROW_VALUES (Bora_Decision stays null):")
    lines += [json.dumps(row, sort_keys=True, ensure_ascii=False) for row in rows]
    lines.append("receipt_sha256: " + receipt_sha)
    return EXIT_OK, block(lines), None


# package ----------------------------------------------------------------------------------------

def deterministic_zip(members: Mapping[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for name in sorted(members):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, members[name])
    return buffer.getvalue()


def persist_names(company: str, role: str) -> tuple:
    stem = "Bora_Chaush_%s_%s_Resume" % (sanitize(company), sanitize(role))
    return stem + ".pdf", stem + ".docx", BUNDLE_NAME


def cmd_package(args: argparse.Namespace) -> tuple:
    request = read_json(args.request, "request")
    ledger = load_ledger(args.ledger)
    job_id = request.get("job_id") if isinstance(request, Mapping) else None
    rows = [row for row in (request.get("jobs_rows") or []) if isinstance(row, Mapping) and row.get("Job_ID") == job_id] if job_id else []
    ledger_rows = [row for row in ledger["JOBS"] if row.get("Job_ID") == job_id]
    if len(rows) != 1 or len(ledger_rows) != 1:
        raise RunError("REQUEST_JOB_UNRESOLVED", "request.job_id must match exactly one request jobs_rows row and one Ledger JOBS row")
    live = ledger_rows[0]
    if not non_empty(live.get("Official_URL")):
        raise RunError("OFFICIAL_URL_MISSING_IN_LEDGER", str(job_id))
    for key in ("Job_ID", "Company", "Role", "Official_URL"):
        if rows[0].get(key) != live.get(key):
            raise RunError("REQUEST_LEDGER_IDENTITY_MISMATCH", "%s differs between request and Ledger" % key)
    if live.get("Company") != args.company or live.get("Role") != args.role:
        raise RunError("ROLE_IDENTITY_MISMATCH", "--company/--role must equal the Ledger JOBS row Company/Role for %s" % job_id)
    pdf_name, docx_name, bundle_name = persist_names(args.company, args.role)
    folder = args.target_folder_name
    if not non_empty(folder):
        raise RunError("TARGET_FOLDER_NAME_EMPTY")
    output_root = Path(args.output_root)
    persist = output_root / PERSIST_DIR
    if persist.exists() and any(persist.iterdir()):
        raise RunError("PERSIST_DIR_NOT_CLEAN", str(persist))
    # The pursuit gate reads JOBS and the decision LOG from the same canonical Ledger file as every other step.
    effective = dict(request)
    effective["jobs_rows"] = [dict(live)]
    effective["decision_log_rows"] = [dict(row) for row in ledger["LOG"]]
    output_root.mkdir(parents=True, exist_ok=True)
    effective_path = output_root / EFFECTIVE_REQUEST_FILE
    write_receipt(str(effective_path), effective)
    captured = io.StringIO()
    try:
        with contextlib.redirect_stdout(captured):  # run_request prints the claim table itself; the block below carries it
            result = cloud.run_request(str(effective_path), args.runtime_root, args.font_dir, str(output_root), args.expected_main_sha)
    except RunError:
        raise
    except Exception as error:
        raise RunError(getattr(error, "code", None) or type(error).__name__, str(getattr(error, "detail", "") or error)[:300]) from error
    inventory = result["package_inventory"]
    if not inventory.get("complete"):
        raise RunError("PACKAGE_INVENTORY_INCOMPLETE", ",".join(inventory.get("problems", [])))
    package_dir = Path(result["output_dir"])
    json_members = {path.name: path.read_bytes() for path in sorted(package_dir.iterdir()) if path.is_file() and path.suffix == ".json"}
    for required in (handoff.INVENTORY_FILE, "cloud_operate_manifest.json", "manifest.json"):
        if required not in json_members:
            raise RunError("BUNDLE_MEMBER_MISSING", required)
    persist.mkdir(parents=True, exist_ok=True)
    contents = {pdf_name: (package_dir / "resume.pdf").read_bytes(), docx_name: (package_dir / "resume.docx").read_bytes(),
                bundle_name: deterministic_zip(json_members)}
    for name, data in contents.items():
        (persist / name).write_bytes(data)
    roles = {pdf_name: "resume_pdf", docx_name: "resume_docx", bundle_name: "package_bundle"}
    files = [{"role": roles[name], "name": name, "byte_size": len(contents[name]), "sha256": sha256_hex(contents[name])}
             for name in (pdf_name, docx_name, bundle_name)]
    plan = {"spec": PLAN_SPEC, "contract": RUN_CONTRACT_ID, "job_id": job_id, "company": args.company, "role": args.role,
            "target_folder_name": folder, "package_generation_id": result["manifest"]["package_generation_id"], "files": files}
    plan_sha = write_receipt(str(output_root / PLAN_FILE), plan)
    review = json.loads((package_dir / handoff.REVIEW_FILE).read_text(encoding="utf-8"))
    lines = ["CAREER_OS_RUN_PACKAGE: GENERATED (human visual + claim review still required; no submission authority)",
             "CLAIM REVIEW TABLE", handoff.format_claim_wording_review_table(review), "",
             "UPLOAD THESE 3 FILES to Drive folder: " + folder, "from local directory: " + str(persist)]
    lines += ["%s | %d bytes | sha256 %s" % (item["name"], item["byte_size"], item["sha256"]) for item in files]
    lines += ["persist_plan: %s" % (output_root / PLAN_FILE), "persist_plan_sha256: " + plan_sha]
    return EXIT_OK, block(lines), None


# verify-persisted -------------------------------------------------------------------------------

def load_plan(path: str) -> dict:
    plan = read_json(path, "persist plan")
    if not isinstance(plan, Mapping) or plan.get("spec") != PLAN_SPEC:
        raise RunError("PLAN_INVALID", "spec must be " + PLAN_SPEC)
    for key in ("job_id", "company", "role", "target_folder_name"):
        if not non_empty(plan.get(key)):
            raise RunError("PLAN_INVALID", "missing " + key)
    inventory = handoff.persist_plan_inventory(plan)
    if not inventory["complete"]:
        raise RunError("PLAN_INVALID", ",".join(inventory["problems"]))
    for item in plan["files"]:
        require_sha(item.get("sha256"), "plan file sha256")
    return dict(plan)


def plan_file(plan: Mapping[str, Any], role: str) -> dict:
    return next(item for item in plan["files"] if item["role"] == role)


def cmd_verify_persisted(args: argparse.Namespace) -> tuple:
    plan_bytes = read_bytes(args.plan, "persist plan")
    plan = load_plan(args.plan)
    directory = Path(args.downloaded_dir)
    if not directory.is_dir():
        raise RunError("DOWNLOAD_DIR_MISSING", str(directory))
    observed = {}
    for path in sorted(directory.iterdir()):
        if path.is_file():
            data = path.read_bytes()
            observed[path.name] = {"sha256": sha256_hex(data), "byte_size": len(data)}
        else:
            observed[path.name] = {"status": "NOT_A_FILE"}
    verdict = handoff.verify_persisted(handoff.persist_plan_inventory(plan), observed, exact=True)
    receipt = {"spec": PERSIST_RECEIPT_SPEC, "contract": RUN_CONTRACT_ID, "status": verdict["status"], "job_id": plan["job_id"],
               "plan_sha256": sha256_hex(plan_bytes), "verdict": verdict,
               "files": [{"name": item["name"], "byte_size": item["byte_size"], "sha256": item["sha256"]} for item in plan["files"]]}
    if verdict["status"] != "PERSISTED_COMPLETE":
        write_receipt(args.receipt, receipt)
        raise RunError("PERSISTENCE_FAILED", json.dumps({key: verdict[key] for key in ("missing", "hash_mismatch", "size_mismatch", "unexpected")}, sort_keys=True))
    row = {"Job_ID": plan["job_id"], "Package_Status": "READY"}
    receipt["jobs_row_values"] = row
    receipt_sha = write_receipt(args.receipt, receipt)
    lines = ["PERSISTED_COMPLETE", "job_id: %s | folder: %s" % (plan["job_id"], plan["target_folder_name"])]
    lines += ["%s | %d bytes | sha256 %s | verified" % (item["name"], item["byte_size"], item["sha256"]) for item in plan["files"]]
    lines += ["JOBS_ROW_VALUES (write after this block): " + json.dumps(row, sort_keys=True), "receipt_sha256: " + receipt_sha]
    return EXIT_OK, block(lines), None


# record-submit ----------------------------------------------------------------------------------

def cmd_record_submit(args: argparse.Namespace) -> tuple:
    plan_bytes = read_bytes(args.plan, "persist plan")
    plan = load_plan(args.plan)
    for key, value in (("job_id", args.job_id), ("company", args.company), ("role", args.role)):
        if plan[key] != value:
            raise RunError("PLAN_IDENTITY_MISMATCH", "%s does not match the persist plan" % key)
    persisted = read_json(args.persist_receipt, "persist receipt")
    if not isinstance(persisted, Mapping) or persisted.get("spec") != PERSIST_RECEIPT_SPEC or persisted.get("status") != "PERSISTED_COMPLETE" \
            or persisted.get("plan_sha256") != sha256_hex(plan_bytes):
        raise RunError("PERSISTENCE_NOT_VERIFIED", "a PERSISTED_COMPLETE receipt bound to this plan is required before recording a submission")
    if not non_empty(args.channel):
        raise RunError("CHANNEL_EMPTY")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", args.applied_date):
        raise RunError("APPLIED_DATE_INVALID", "expected YYYY-MM-DD")
    pdf = plan_file(plan, "resume_pdf")
    if args.receipt_file:
        receipt_data = read_bytes(args.receipt_file, "submission receipt file")
        if not receipt_data:
            raise RunError("SUBMISSION_RECEIPT_EMPTY")
        proof_note = "receipt sha256:%s" % sha256_hex(receipt_data)
        log_note = "Bora manual submit; " + proof_note
    else:
        proof_note = "Bora confirmed; no separate receipt"
        log_note = "Bora manual submit; Bora confirmed; no separate receipt artifact"
    application = {"Application_ID": "APP::%s::%s" % (args.job_id, args.applied_date),
                   "Job_ID": args.job_id, "Applied_Date": args.applied_date,
                   "Resume_Version": "%s | sha256:%s" % (pdf["name"], pdf["sha256"]),
                   "Cover_Letter_Version": "NONE", "Channel": args.channel,
                   "Current_Status": "SUBMITTED", "Last_Update": args.applied_date,
                   "Next_Action": "Monitor for employer response", "Outcome": proof_note}
    _require_exact_row_shape(application, APPLICATIONS_HEADERS, "APPLICATIONS")
    jobs = {"Job_ID": args.job_id, "Application_Status": "SUBMITTED"}
    log = {"Run_ID": "RECORD_SUBMIT::%s::%s" % (args.job_id, args.applied_date), "Timestamp": args.applied_date,
           "Stage": "APPLICATION_RECORDED", "Source": "CAREER_OS_RUN_V1", "Job_ID": args.job_id,
           "Status": "SUBMITTED", "Error_Code": "", "Engine_Baseline": "", "Notes": log_note}
    _require_exact_row_shape(log, LOG_HEADERS, "LOG")
    receipt = {"spec": "CAREER_OS_RECORD_SUBMIT_RECEIPT_V1", "contract": RUN_CONTRACT_ID, "status": "SUBMISSION_RECORDED_BY_BORA",
               "plan_sha256": sha256_hex(plan_bytes), "applications_row": application, "jobs_row": jobs, "log_row": log}
    receipt_sha = write_receipt(args.receipt, receipt)
    lines = ["CAREER_OS_RUN_RECORD_SUBMIT (no external submit performed; Bora submitted manually)",
             "APPLICATIONS_ROW_VALUES: " + json.dumps(application, sort_keys=True, ensure_ascii=False),
             "JOBS_ROW_VALUES: " + json.dumps(jobs, sort_keys=True), "LOG_ROW_VALUES: " + json.dumps(log, sort_keys=True, ensure_ascii=False),
             "receipt_sha256: " + receipt_sha]
    return EXIT_OK, block(lines), None


# closeout ---------------------------------------------------------------------------------------

def _folder_map(raw: Any) -> dict:
    if isinstance(raw, Mapping) and isinstance(raw.get("folders"), (Mapping, list)):
        raw = raw["folders"]
    result = {}
    if isinstance(raw, Mapping):
        for name, entries in raw.items():
            result[str(name)] = list(entries) if isinstance(entries, list) else []
    elif isinstance(raw, list):
        for item in raw:
            if isinstance(item, Mapping) and non_empty(item.get("name", item.get("folder"))):
                entries = item.get("files", item.get("children", []))
                result[str(item.get("name", item.get("folder")))] = list(entries) if isinstance(entries, list) else []
    else:
        raise RunError("FOLDER_LISTING_SHAPE_INVALID")
    return result


def closeout_missing(slate: Sequence[Mapping[str, Any]], ledger: Mapping[str, Any], folders: Mapping[str, list],
                    plans: Sequence[Mapping[str, Any]]) -> list:
    jobs, applications = ledger.get("JOBS", []), ledger.get("APPLICATIONS", [])
    plans_by_job = {plan.get("job_id"): plan for plan in plans}
    missing = []
    for role in sorted(slate, key=lambda item: str(item.get("job_id"))):
        job_id = role.get("job_id")
        tracking = role.get("tracking_status")
        if not non_empty(job_id):
            missing.append("(slate): BATCH_ROLE_WITHOUT_JOB_ID")
            continue
        rows = [row for row in jobs if row.get("Job_ID") == job_id or (tracking == "ALREADY_TRACKED" and row.get("Job_ID") == role.get("tracked_job_id"))]
        if len(rows) != 1:
            missing.append("%s: %s" % (job_id, "JOBS_ROW_MISSING" if not rows else "JOBS_ROW_DUPLICATE"))
            continue
        row = rows[0]
        if not any(non_empty(row.get(key)) for key in ("Decision", "Bora_Decision", "Package_Status", "Application_Status")):
            missing.append("%s: JOBS_DURABLE_STATE_MISSING" % job_id)
        submitted = str(row.get("Application_Status") or "").strip().upper() == "SUBMITTED"
        if str(row.get("Bora_Decision") or "").strip().upper() == "PURSUE" and not submitted \
                and str(row.get("Package_Status") or "").strip().upper() not in READY_PACKAGE_STATES:
            missing.append("%s: PURSUE_PACKAGE_NOT_PERSISTED_COMPLETE" % job_id)
        if not submitted:
            continue
        plan = plans_by_job.get(job_id)
        if tracking != "ALREADY_TRACKED" and plan is None:
            missing.append("%s: PLAN_NOT_SUPPLIED" % job_id)
        app_rows = [item for item in applications if item.get("Job_ID") == row.get("Job_ID")]
        if not app_rows:
            missing.append("%s: APPLICATIONS_ROW_MISSING" % job_id)
        elif len(app_rows) > 1:
            missing.append("%s: APPLICATIONS_ROW_DUPLICATE" % job_id)
        folder_key = job_id if job_id in folders else (plan.get("target_folder_name") if plan else role.get("target_folder_name"))
        if not non_empty(folder_key):
            missing.append("%s: ROLE_FOLDER_UNRESOLVED" % job_id)
        elif not folders.get(str(folder_key)):
            missing.append("%s: ROLE_FOLDER_MISSING_OR_EMPTY" % job_id)
        if plan and len(app_rows) == 1:
            recorded = _resume_sha_from_version(app_rows[0].get("Resume_Version"))
            if recorded is None:
                missing.append("%s: APPLICATIONS_RESUME_SHA_MISSING" % job_id)
            elif recorded != plan_file(plan, "resume_pdf")["sha256"]:
                missing.append("%s: APPLICATIONS_RESUME_SHA_MISMATCH_WITH_PLAN" % job_id)
    return missing


def cmd_closeout(args: argparse.Namespace) -> tuple:
    slate_receipt = read_json(args.slate_receipt, "slate receipt")
    if not isinstance(slate_receipt, Mapping) or slate_receipt.get("spec") != "CAREER_OS_RUN_SLATE_RECEIPT_V1" \
            or not isinstance(slate_receipt.get("slate"), list) or not slate_receipt["slate"]:
        raise RunError("SLATE_RECEIPT_INVALID", "closeout requires the complete slate receipt")
    slate = slate_receipt["slate"]
    ledger = load_ledger(args.ledger)
    folders = _folder_map(read_json(args.folders, "Drive folder listing"))
    plans = read_json(args.plans, "plans") if args.plans else []
    if not isinstance(plans, list) or not all(isinstance(plan, Mapping) for plan in plans):
        raise RunError("PLANS_INVALID", "plans must be a JSON list of persist plans")
    for plan in plans:
        for key in ("job_id", "target_folder_name"):
            if not non_empty(plan.get(key)):
                raise RunError("PLANS_INVALID", "plan missing " + key)
        handoff_inventory = handoff.persist_plan_inventory(plan)
        if not handoff_inventory["complete"]:
            raise RunError("PLANS_INVALID", ",".join(handoff_inventory["problems"]))
    missing = closeout_missing(slate, ledger, folders, plans)
    status = "COMPLETE" if not missing else "INCOMPLETE"
    receipt = {"spec": "CAREER_OS_RUN_CLOSEOUT_RECEIPT_V1", "contract": RUN_CONTRACT_ID, "status": status,
               "slate_receipt_sha256": sha256_hex(read_bytes(args.slate_receipt, "slate receipt")),
               "roles": sorted(str(item.get("job_id")) for item in slate), "missing": missing}
    receipt_sha = write_receipt(args.receipt, receipt)
    lines = ["CAREER_OS_RUN_CLOSEOUT_DETAIL roles=%d missing=%d" % (len(slate), len(missing))] + ["MISSING: " + item for item in missing]
    lines.append("receipt_sha256: " + receipt_sha)
    return (EXIT_OK if not missing else EXIT_STOP), block(lines) + "\n" + CLOSEOUT_MARKER + " " + status, None


# CLI --------------------------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = _Parser(prog="career_os_run_v1", description="Career OS run-contract operator CLI (local, pure; no Drive/Sheets/web/submission).")
    sub = parser.add_subparsers(dest="command", required=True, parser_class=_Parser)

    def add(name: str, handler, receipt: bool = True) -> argparse.ArgumentParser:
        item = sub.add_parser(name)
        item.set_defaults(handler=handler)
        if receipt:
            item.add_argument("--receipt", required=True, help="local receipt JSON to write")
        return item

    item = add("readback", cmd_readback)
    item.add_argument("--raw", required=True, help="raw Sheets values: {JOBS|APPLICATIONS|LOG[|NETWORK]: [[header...], [row...], ...]}")
    item.add_argument("--out", required=True, help="Ledger file to write; use it for every --ledger in this run")
    item = add("pursuit-state", cmd_pursuit_state)
    item.add_argument("--ledger", required=True)
    item.add_argument("--job-id", required=True)
    item = add("decide", cmd_decide)
    item.add_argument("--ledger", required=True)
    item.add_argument("--job-id", required=True)
    item.add_argument("--decision", required=True, help="PURSUE|WATCH|REJECT, exactly as Bora said it")
    item.add_argument("--decided-at", required=True, help="ISO timestamp with offset, e.g. 2026-10-06T09:40:00-04:00")
    item.add_argument("--reason-note", help="optional short note in Bora's words")
    item = add("preflight", cmd_preflight)
    item.add_argument("--runtime-root", required=True)
    item.add_argument("--expected-main-sha", required=True)
    item.add_argument("--font-dir", required=True)
    item.add_argument("--settings", required=True, help="SETTINGS readback JSON")
    item.add_argument("--adapter", required=True)
    item.add_argument("--config", required=True)
    item.add_argument("--runbook", required=True)
    item.add_argument("--runtime-zip", required=True, help="downloaded runtime bundle ZIP; hashed by the CLI")
    item.add_argument("--fonts-zip", required=True, help="downloaded governed fonts ZIP; hashed by the CLI")
    item = add("slate", cmd_slate)
    item.add_argument("--screening", required=True, help="screening.json array")
    item.add_argument("--as-of", required=True, help="ISO timestamp with offset; stamped into First_Seen and Last_Verified")
    item.add_argument("--ledger", required=True, help="live Ledger readback JSON with JOBS/APPLICATIONS/LOG arrays")
    item = add("package", cmd_package, receipt=False)
    item.add_argument("--request", required=True)
    item.add_argument("--ledger", required=True, help="live Ledger readback JSON")
    item.add_argument("--runtime-root", required=True)
    item.add_argument("--font-dir", required=True)
    item.add_argument("--output-root", required=True)
    item.add_argument("--expected-main-sha", required=True)
    item.add_argument("--company", required=True)
    item.add_argument("--role", required=True)
    item.add_argument("--target-folder-name", required=True)
    item = add("verify-persisted", cmd_verify_persisted)
    item.add_argument("--plan", required=True)
    item.add_argument("--downloaded-dir", required=True)
    item = add("record-submit", cmd_record_submit)
    item.add_argument("--plan", required=True)
    item.add_argument("--persist-receipt", required=True, help="receipt written by verify-persisted")
    item.add_argument("--job-id", required=True)
    item.add_argument("--company", required=True)
    item.add_argument("--role", required=True)
    item.add_argument("--channel", required=True)
    item.add_argument("--applied-date", required=True)
    proof = item.add_mutually_exclusive_group(required=True)
    proof.add_argument("--bora-confirmed", action="store_true")
    proof.add_argument("--receipt-file")
    item = add("closeout", cmd_closeout)
    item.add_argument("--slate-receipt", required=True)
    item.add_argument("--ledger", required=True)
    item.add_argument("--folders", required=True)
    item.add_argument("--plans")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    command = None
    try:
        args = build_parser().parse_args(list(sys.argv[1:] if argv is None else argv))
        command = args.command
        code, output, failure = args.handler(args)
        print(output)
        if failure is not None:
            print(FAILURE_MARKER + " " + json.dumps(failure, sort_keys=True))
        return code
    except RunError as error:
        print(FAILURE_MARKER + " " + json.dumps({"command": command, "code": error.code, "detail": error.detail}, sort_keys=True))
        return EXIT_ERROR


if __name__ == "__main__":
    raise SystemExit(main())
