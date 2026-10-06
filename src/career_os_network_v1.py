"""CAREER_OS_NETWORK_V1 operator CLI: networking contacts, outreach drafts, application outcomes, weekly report.

A pure, local companion to career_os_run_v1.py. It reads caller-supplied files (a live Production Ledger readback and,
for drafts, the canonical runtime's Candidate Truth) and writes only local receipts. It never calls LinkedIn, Gmail,
Drive, Sheets or the web, never sends a message and never submits anything. The ChatGPT connectors write the emitted
row values to the Ledger; Bora sends every message himself.

Doctrine (BLUEPRINT.md section 136): network access is separate from qualification. Nothing here reads or changes a
screening decision, a JOBS decision field, a resume, or Candidate Truth.

Commands:
    network-add      validate one real contact and emit its NETWORK row + LOG event (no invented people: How_Found)
    network-update   move a contact to a new status with a deterministic follow-up date + LOG event
    network-draft    an outreach draft under 120 words built only from approved, networking-allowed resume language
    record-outcome   an employer response for an APPLICATIONS row (+ LOG event); JOBS is never touched
    weekly-report    counts from the Ledger readback for a date window, plus follow-ups due (counts only, no scores)
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parent))

import career_os_run_v1 as run  # noqa: E402

NETWORK_CONTRACT_ID = "CAREER_OS_NETWORK_V1"
LOG_SOURCE = "CAREER_OS_NETWORK_V1"

NETWORK_HEADERS = ("Contact_ID", "Name", "Company", "Role_Title", "How_Found", "Relationship", "Purpose", "Linked_Job_ID",
                   "Status", "Added_On", "Last_Touch", "Next_Action_Date", "Notes")
CONTACT_INPUT_KEYS = ("Name", "Company", "Role_Title", "How_Found", "Relationship", "Purpose", "Linked_Job_ID", "Notes")
RELATIONSHIPS = ("BRANDEIS_ALUMNI", "FORMER_COLLEAGUE", "WINTER_WALK", "FACULTY", "RECRUITER", "OTHER")
PURPOSES = ("JOB_REFERRAL", "INFO_CHAT", "CLIENT_PROSPECT")
STATUSES = ("TO_CONTACT", "SENT", "REPLIED", "CALL_DONE", "REFERRED", "NO_REPLY", "CLOSED")
KNOWN_PERSONALLY = "KNOWN_PERSONALLY"
# Days until the next action after moving to a status; None means no automatic next action.
FOLLOW_UP_DAYS = {"SENT": 7, "REPLIED": 3, "CALL_DONE": 7, "REFERRED": 14, "NO_REPLY": None, "CLOSED": None}

OUTCOME_STATUSES = ("UNDER_REVIEW", "INTERVIEW", "REJECTED", "OFFER", "WITHDRAWN", "NO_RESPONSE")
OUTCOME_NEXT_ACTION = {"UNDER_REVIEW": "Monitor for employer response", "INTERVIEW": "Prepare for interview",
                       "REJECTED": "None", "OFFER": "Review offer; confirm work authorization with ISSO before accepting",
                       "WITHDRAWN": "None", "NO_RESPONSE": "None"}

STAGE_NETWORK_ADDED = "NETWORK_ADDED"
STAGE_NETWORK_UPDATE = "NETWORK_UPDATE"
STAGE_OUTCOME = "APPLICATION_OUTCOME"

DRAFT_MAX_WORDS = 120
# Fixed, true phrases per relationship, each backed by Candidate Truth (Brandeis MSBA degree; Winter Walk claims allow
# networking). Nothing about a contact is invented: these describe Bora, not the contact.
RELATIONSHIP_PHRASE = {
    "BRANDEIS_ALUMNI": "a fellow Brandeis alum (MS in Business Analytics)",
    "FACULTY": "an MS in Business Analytics graduate from Brandeis",
    "WINTER_WALK": "reaching out from my work with Winter Walk",
    "FORMER_COLLEAGUE": "reaching out as a former colleague",
    "RECRUITER": "an MS in Business Analytics graduate from Brandeis",
    "OTHER": "an MS in Business Analytics graduate from Brandeis",
}
ASK = {"JOB_REFERRAL": "Would you be open to a 10-minute chat about the team, or pointing me to the right person?",
       "INFO_CHAT": "Would you be open to a 10-minute chat about your work there?",
       "CLIENT_PROSPECT": "Would you be open to a 15-minute conversation?"}
CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


class NetworkError(run.RunError):
    pass


# Helpers ----------------------------------------------------------------------------------------

def parse_date(value: Any, what: str) -> datetime.date:
    text = str(value or "")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        raise NetworkError("DATE_INVALID", "%s must be YYYY-MM-DD" % what)
    try:
        return datetime.date.fromisoformat(text)
    except ValueError as error:
        raise NetworkError("DATE_INVALID", "%s is not a real date" % what) from error


def date_prefix(value: Any) -> Optional[datetime.date]:
    """The calendar date at the start of a Ledger timestamp/date cell, or None when there is none."""
    match = re.match(r"(\d{4}-\d{2}-\d{2})", str(value or ""))
    if not match:
        return None
    try:
        return datetime.date.fromisoformat(match.group(1))
    except ValueError:
        return None


def clean_text(value: Any, what: str, *, required: bool) -> str:
    if not isinstance(value, str):
        raise NetworkError("FIELD_INVALID", "%s must be a string" % what)
    text = value.strip()
    if CONTROL_CHARS.search(text) or "\n" in text or "\r" in text or "\t" in text:
        raise NetworkError("FIELD_INVALID", "%s contains control characters or line breaks" % what)
    if required and not text:
        raise NetworkError("FIELD_INVALID", "%s must be non-empty" % what)
    return text


def load_ledger_with_network(path: str) -> dict:
    ledger = run.load_ledger(path)
    rows = ledger.get("NETWORK")
    if not isinstance(rows, list):
        raise NetworkError("LEDGER_INVALID", "NETWORK must be an array (use [] when the tab has no rows)")
    for index, row in enumerate(rows):
        if not isinstance(row, Mapping):
            raise NetworkError("LEDGER_SHAPE_INVALID", "NETWORK[%d] must be an object" % index)
        run._require_exact_row_shape(row, NETWORK_HEADERS, "NETWORK[%d]" % index)
    ids = [row["Contact_ID"] for row in rows]
    duplicates = sorted({cid for cid in ids if ids.count(cid) > 1})
    if duplicates:
        raise NetworkError("NETWORK_DUPLICATE_CONTACT_ID", ",".join(duplicates))
    return ledger


def contact_id(how_found: str, name: str, company: str) -> str:
    key = how_found.lower().rstrip("/") if how_found != KNOWN_PERSONALLY else "KNOWN::%s|%s" % (name.lower(), company.lower())
    return "NET::" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:12].upper()


def log_row(run_id: str, as_of: str, stage: str, job_id: str, status: str, notes: str) -> dict:
    row = {"Run_ID": run_id, "Timestamp": as_of, "Stage": stage, "Source": LOG_SOURCE, "Job_ID": job_id, "Status": status,
           "Error_Code": "", "Engine_Baseline": "", "Notes": notes}
    run._require_exact_row_shape(row, run.LOG_HEADERS, "LOG")
    return row


def require_new_run_id(ledger: Mapping[str, Any], run_id: str) -> None:
    if any(row.get("Run_ID") == run_id for row in ledger["LOG"]):
        raise NetworkError("ALREADY_RECORDED", "LOG already holds %s" % run_id)


def append_note(existing: str, as_of: str, label: str, note: str) -> str:
    entry = "%s %s: %s" % (as_of, label, note)
    return entry if not existing.strip() else existing.rstrip() + " | " + entry


def find_contact(ledger: Mapping[str, Any], cid: str) -> dict:
    rows = [row for row in ledger["NETWORK"] if row.get("Contact_ID") == cid]
    if not rows:
        raise NetworkError("CONTACT_NOT_FOUND", cid)
    return dict(rows[0])


def output(lines: Sequence[str], receipt_path: str, receipt: Mapping[str, Any]) -> tuple:
    receipt_sha = run.write_receipt(receipt_path, receipt)
    return run.EXIT_OK, run.block(list(lines) + ["receipt_sha256: " + receipt_sha]), None


# network-add ------------------------------------------------------------------------------------

def validate_contact(raw: Any, ledger: Mapping[str, Any]) -> dict:
    if not isinstance(raw, Mapping):
        raise NetworkError("CONTACT_INVALID", "contact must be one JSON object")
    keys = set(raw)
    if keys != set(CONTACT_INPUT_KEYS):
        raise NetworkError("CONTACT_INVALID", "keys missing=%s extra=%s" % (sorted(set(CONTACT_INPUT_KEYS) - keys), sorted(keys - set(CONTACT_INPUT_KEYS))))
    contact = {
        "Name": clean_text(raw["Name"], "Name", required=True),
        "Company": clean_text(raw["Company"], "Company", required=True),
        "Role_Title": clean_text(raw["Role_Title"], "Role_Title", required=False),
        "How_Found": clean_text(raw["How_Found"], "How_Found", required=False),
        "Relationship": clean_text(raw["Relationship"], "Relationship", required=True),
        "Purpose": clean_text(raw["Purpose"], "Purpose", required=True),
        "Linked_Job_ID": clean_text(raw["Linked_Job_ID"], "Linked_Job_ID", required=False),
        "Notes": clean_text(raw["Notes"], "Notes", required=False),
    }
    if re.search(r"https?://", contact["Name"]):
        raise NetworkError("FIELD_INVALID", "Name must be a person's name, not a link")
    how = contact["How_Found"]
    if how == KNOWN_PERSONALLY:
        if not contact["Notes"]:
            raise NetworkError("HOW_FOUND_UNVERIFIABLE", "KNOWN_PERSONALLY requires Notes saying how Bora knows this person")
    elif not re.fullmatch(r"https://\S+\.\S+", how):
        raise NetworkError("HOW_FOUND_UNVERIFIABLE", "How_Found must be an https profile/directory link or KNOWN_PERSONALLY")
    if contact["Relationship"] not in RELATIONSHIPS:
        raise NetworkError("FIELD_INVALID", "Relationship must be one of %s" % "|".join(RELATIONSHIPS))
    if contact["Purpose"] not in PURPOSES:
        raise NetworkError("FIELD_INVALID", "Purpose must be one of %s" % "|".join(PURPOSES))
    if contact["Linked_Job_ID"] and not any(row.get("Job_ID") == contact["Linked_Job_ID"] for row in ledger["JOBS"]):
        raise NetworkError("LINKED_JOB_UNKNOWN", "Linked_Job_ID %s is not a JOBS row" % contact["Linked_Job_ID"])
    return contact


def cmd_network_add(args: argparse.Namespace) -> tuple:
    ledger = load_ledger_with_network(args.ledger)
    as_of = parse_date(args.as_of, "--as-of").isoformat()
    contact = validate_contact(run.read_json(args.contact, "contact"), ledger)
    cid = contact_id(contact["How_Found"], contact["Name"], contact["Company"])
    for row in ledger["NETWORK"]:
        same_link = contact["How_Found"] != KNOWN_PERSONALLY and str(row.get("How_Found", "")).lower().rstrip("/") == contact["How_Found"].lower().rstrip("/")
        same_person = str(row.get("Name", "")).strip().lower() == contact["Name"].lower() and str(row.get("Company", "")).strip().lower() == contact["Company"].lower()
        if row.get("Contact_ID") == cid or same_link or same_person:
            raise NetworkError("ALREADY_IN_NETWORK", "existing Contact_ID %s" % row.get("Contact_ID"))
    network_row = dict(contact, Contact_ID=cid, Status="TO_CONTACT", Added_On=as_of, Last_Touch="", Next_Action_Date=as_of)
    network_row = {key: network_row[key] for key in NETWORK_HEADERS}
    run_id = "NETWORK::%s::%s::TO_CONTACT" % (cid, as_of)
    require_new_run_id(ledger, run_id)
    log = log_row(run_id, as_of, STAGE_NETWORK_ADDED, contact["Linked_Job_ID"], "TO_CONTACT", "%s %s" % (cid, contact["Purpose"]))
    receipt = {"spec": "CAREER_OS_NETWORK_ADD_RECEIPT_V1", "contract": NETWORK_CONTRACT_ID, "network_row": network_row, "log_row": log}
    lines = ["CAREER_OS_NETWORK_ADD (append this NETWORK row and this LOG row; nothing is sent)",
             "NETWORK_ROW_VALUES: " + json.dumps(network_row, ensure_ascii=False),
             "LOG_ROW_VALUES: " + json.dumps(log, ensure_ascii=False)]
    return output(lines, args.receipt, receipt)


# network-update ---------------------------------------------------------------------------------

def cmd_network_update(args: argparse.Namespace) -> tuple:
    ledger = load_ledger_with_network(args.ledger)
    as_of_date = parse_date(args.as_of, "--as-of")
    as_of = as_of_date.isoformat()
    row = find_contact(ledger, args.contact_id)
    status = args.status
    if status not in STATUSES or status == "TO_CONTACT":
        raise NetworkError("STATUS_INVALID", "status must be one of %s" % "|".join(s for s in STATUSES if s != "TO_CONTACT"))
    if row["Status"] == "CLOSED":
        raise NetworkError("CONTACT_CLOSED", args.contact_id)
    for label in ("Added_On", "Last_Touch"):
        previous = date_prefix(row.get(label))
        if previous and as_of_date < previous:
            raise NetworkError("DATE_BACKWARDS", "--as-of %s is before %s %s" % (as_of, label, previous.isoformat()))
    if args.next_date:
        next_date = parse_date(args.next_date, "--next-date")
        if next_date < as_of_date:
            raise NetworkError("DATE_BACKWARDS", "--next-date is before --as-of")
        next_action = next_date.isoformat()
    else:
        days = FOLLOW_UP_DAYS[status]
        next_action = "" if days is None else (as_of_date + datetime.timedelta(days=days)).isoformat()
    note = clean_text(args.note or "", "--note", required=False)
    updated = dict(row, Status=status, Last_Touch=as_of, Next_Action_Date=next_action)
    if note:
        updated["Notes"] = append_note(str(row.get("Notes", "")), as_of, status, note)
    updated = {key: updated[key] for key in NETWORK_HEADERS}
    run_id = "NETWORK::%s::%s::%s" % (row["Contact_ID"], as_of, status)
    require_new_run_id(ledger, run_id)
    log = log_row(run_id, as_of, STAGE_NETWORK_UPDATE, row["Linked_Job_ID"], status, "%s %s->%s" % (row["Contact_ID"], row["Status"], status))
    receipt = {"spec": "CAREER_OS_NETWORK_UPDATE_RECEIPT_V1", "contract": NETWORK_CONTRACT_ID, "network_row": updated, "log_row": log}
    lines = ["CAREER_OS_NETWORK_UPDATE (overwrite this contact's NETWORK row and append this LOG row; nothing is sent)",
             "NETWORK_ROW_VALUES: " + json.dumps(updated, ensure_ascii=False),
             "LOG_ROW_VALUES: " + json.dumps(log, ensure_ascii=False)]
    return output(lines, args.receipt, receipt)


# network-draft ----------------------------------------------------------------------------------

def load_networking_bullets(runtime_root: Path) -> dict:
    """bullet_id -> exact approved text, only for bullets whose every claim is human-approved and allows networking."""
    sys.path.insert(0, str(runtime_root / "src"))
    from claim_repository import load_validated_claim_repository
    claims = load_validated_claim_repository(runtime_root / "claims")
    if not claims.get("valid"):
        raise NetworkError("CANDIDATE_TRUTH_INVALID", "claims repository failed validation")
    index = claims["index"]
    approved = run.read_json(str(runtime_root / "docs" / "resume" / "BORA_APPROVED_RESUME_LANGUAGE_V1.json"), "approved language")
    usable = {}
    for bullet in approved.get("bullets", []):
        bound = [index.get(cid) or {} for cid in bullet.get("claim_ids", [])]
        if bound and all(claim.get("human_approval") is True and "networking" in claim.get("allowed_contexts", []) for claim in bound):
            usable[bullet["bullet_id"]] = bullet["text"]
    return usable


def first_person(bullet_text: str) -> str:
    """'Built X.' -> 'I built X.' A grammatical change only; the approved words are otherwise unchanged."""
    text = bullet_text.strip()
    if not text or not text[0].isupper():
        raise NetworkError("BULLET_UNUSABLE", "approved bullet must start with a capitalized verb")
    return "I " + text[0].lower() + text[1:]


def compose_draft(contact: Mapping[str, Any], job: Optional[Mapping[str, Any]], evidence: str) -> str:
    first = contact["Name"].split()[0]
    intro = "I'm Bora Chaush, %s." % RELATIONSHIP_PHRASE[contact["Relationship"]]
    purpose = contact["Purpose"]
    if job is not None and purpose != "CLIENT_PROSPECT":
        link = job.get("Official_URL") or job.get("Discovery_URL") or ""
        verb = "applying for" if purpose == "JOB_REFERRAL" else "interested in"
        context = "I'm %s the %s role at %s%s." % (verb, job["Role"], job["Company"], " (%s)" % link if link else "")
    elif purpose == "CLIENT_PROSPECT":
        context = "I'd like to learn how your team at %s handles its recurring manual workflows." % contact["Company"]
    else:
        context = "I'd like to learn how your team at %s works." % contact["Company"]
    body = " ".join([intro, context, "One example of my work: " + evidence, ASK[purpose]])
    return "Hi %s,\n\n%s\n\nThank you,\nBora" % (first, body)


def cmd_network_draft(args: argparse.Namespace) -> tuple:
    ledger = load_ledger_with_network(args.ledger)
    contact = find_contact(ledger, args.contact_id)
    if contact["Status"] == "CLOSED":
        raise NetworkError("CONTACT_CLOSED", args.contact_id)
    if contact["Relationship"] not in RELATIONSHIP_PHRASE or contact["Purpose"] not in ASK:
        raise NetworkError("CONTACT_INVALID", "NETWORK row has an unknown Relationship or Purpose")
    bullets = load_networking_bullets(Path(args.runtime_root))
    if args.bullet_id not in bullets:
        raise NetworkError("BULLET_NOT_ALLOWED", "%s is not an approved bullet whose claims allow networking" % args.bullet_id)
    job = None
    if contact["Linked_Job_ID"]:
        matches = [row for row in ledger["JOBS"] if row.get("Job_ID") == contact["Linked_Job_ID"]]
        if len(matches) != 1:
            raise NetworkError("LINKED_JOB_UNKNOWN", contact["Linked_Job_ID"])
        job = matches[0]
    draft = compose_draft(contact, job, first_person(bullets[args.bullet_id]))
    words = len(draft.split())
    if words > DRAFT_MAX_WORDS:
        raise NetworkError("DRAFT_TOO_LONG", "%d words; choose a shorter approved bullet" % words)
    receipt = {"spec": "CAREER_OS_NETWORK_DRAFT_RECEIPT_V1", "contract": NETWORK_CONTRACT_ID, "contact_id": contact["Contact_ID"],
               "bullet_id": args.bullet_id, "word_count": words, "draft": draft}
    lines = ["CAREER_OS_NETWORK_DRAFT (Bora reviews and sends it himself; nothing is sent)",
             "contact: %s | %s | %s | bullet %s | %d words" % (contact["Contact_ID"], contact["Name"], contact["Company"], args.bullet_id, words),
             "", draft]
    return output(lines, args.receipt, receipt)


# record-outcome ---------------------------------------------------------------------------------

def cmd_record_outcome(args: argparse.Namespace) -> tuple:
    ledger = run.load_ledger(args.ledger)
    as_of_date = parse_date(args.as_of, "--as-of")
    as_of = as_of_date.isoformat()
    if args.status not in OUTCOME_STATUSES:
        raise NetworkError("STATUS_INVALID", "status must be one of %s" % "|".join(OUTCOME_STATUSES))
    note = clean_text(args.note, "--note", required=True)
    rows = [row for row in ledger["APPLICATIONS"] if row.get("Job_ID") == args.job_id]
    if args.application_id:
        rows = [row for row in rows if row.get("Application_ID") == args.application_id]
    if not rows:
        raise NetworkError("APPLICATION_NOT_FOUND", args.job_id)
    if len(rows) > 1:
        raise NetworkError("APPLICATION_AMBIGUOUS", "pass --application-id")
    row = dict(rows[0])
    for label in ("Applied_Date", "Last_Update"):
        previous = date_prefix(row.get(label))
        if previous and as_of_date < previous:
            raise NetworkError("DATE_BACKWARDS", "--as-of %s is before %s %s" % (as_of, label, previous.isoformat()))
    updated = dict(row, Current_Status=args.status, Last_Update=as_of, Next_Action=OUTCOME_NEXT_ACTION[args.status],
                   Outcome=append_note(str(row.get("Outcome", "")), as_of, args.status, note))
    updated = {key: updated[key] for key in run.APPLICATIONS_HEADERS}
    run_id = "OUTCOME::%s::%s::%s" % (row["Application_ID"], as_of, args.status)
    if any(item.get("Run_ID") == run_id for item in ledger["LOG"]):
        raise NetworkError("ALREADY_RECORDED", "LOG already holds %s" % run_id)
    log = log_row(run_id, as_of, STAGE_OUTCOME, args.job_id, args.status, note)
    receipt = {"spec": "CAREER_OS_RECORD_OUTCOME_RECEIPT_V1", "contract": NETWORK_CONTRACT_ID, "applications_row": updated, "log_row": log}
    lines = ["CAREER_OS_RECORD_OUTCOME (overwrite this APPLICATIONS row and append this LOG row; JOBS is unchanged)",
             "APPLICATIONS_ROW_VALUES: " + json.dumps(updated, ensure_ascii=False),
             "LOG_ROW_VALUES: " + json.dumps(log, ensure_ascii=False)]
    return output(lines, args.receipt, receipt)


# weekly-report ----------------------------------------------------------------------------------

def _count(values: Sequence[str]) -> dict:
    result: dict = {}
    for value in values:
        key = str(value or "").strip() or "(blank)"
        result[key] = result.get(key, 0) + 1
    return dict(sorted(result.items()))


def weekly_counts(ledger: Mapping[str, Any], start: datetime.date, end: datetime.date) -> dict:
    def in_window(value: Any) -> bool:
        day = date_prefix(value)
        return day is not None and start <= day <= end
    window_log = [row for row in ledger["LOG"] if in_window(row.get("Timestamp"))]
    due = [row for row in ledger["NETWORK"] if row.get("Status") != "CLOSED" and date_prefix(row.get("Next_Action_Date"))
           and date_prefix(row.get("Next_Action_Date")) <= end]
    return {
        "window": [start.isoformat(), end.isoformat()],
        "jobs_first_seen_in_window": sum(1 for row in ledger["JOBS"] if in_window(row.get("First_Seen"))),
        "applications_submitted_in_window": sum(1 for row in ledger["APPLICATIONS"] if in_window(row.get("Applied_Date"))),
        "outcomes_in_window": _count([row["Status"] for row in window_log if row.get("Stage") == STAGE_OUTCOME]),
        "contacts_added_in_window": sum(1 for row in window_log if row.get("Stage") == STAGE_NETWORK_ADDED),
        "contact_updates_in_window": _count([row["Status"] for row in window_log if row.get("Stage") == STAGE_NETWORK_UPDATE]),
        "snapshot_bora_decisions": _count([row.get("Bora_Decision") for row in ledger["JOBS"]]),
        "snapshot_application_status": _count([row.get("Current_Status") for row in ledger["APPLICATIONS"]]),
        "snapshot_network_status": _count([row.get("Status") for row in ledger["NETWORK"]]),
        "follow_ups_due": sorted(({"Contact_ID": row["Contact_ID"], "Name": row["Name"], "Company": row["Company"],
                                   "Status": row["Status"], "Next_Action_Date": row["Next_Action_Date"]} for row in due),
                                 key=lambda item: (item["Next_Action_Date"], item["Contact_ID"])),
    }


def cmd_weekly_report(args: argparse.Namespace) -> tuple:
    ledger = load_ledger_with_network(args.ledger)
    start, end = parse_date(args.start, "--from"), parse_date(args.end, "--to")
    if end < start:
        raise NetworkError("DATE_BACKWARDS", "--to is before --from")
    counts = weekly_counts(ledger, start, end)
    lines = ["CAREER_OS_WEEKLY_REPORT %s to %s (counts only; no scores)" % (counts["window"][0], counts["window"][1])]
    for key in ("jobs_first_seen_in_window", "applications_submitted_in_window", "outcomes_in_window", "contacts_added_in_window",
                "contact_updates_in_window", "snapshot_bora_decisions", "snapshot_application_status", "snapshot_network_status"):
        lines.append("%s: %s" % (key, json.dumps(counts[key], sort_keys=True)))
    lines.append("follow_ups_due: %d" % len(counts["follow_ups_due"]))
    lines += ["  %s | %s | %s | %s | due %s" % (item["Contact_ID"], item["Name"], item["Company"], item["Status"], item["Next_Action_Date"])
              for item in counts["follow_ups_due"]]
    receipt = {"spec": "CAREER_OS_WEEKLY_REPORT_RECEIPT_V1", "contract": NETWORK_CONTRACT_ID, "counts": counts}
    return output(lines, args.receipt, receipt)


# CLI --------------------------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = run._Parser(prog="career_os_network_v1", description="Career OS network/outcome CLI (local, pure; never sends or submits).")
    sub = parser.add_subparsers(dest="command", required=True, parser_class=run._Parser)

    def add(name: str, handler) -> argparse.ArgumentParser:
        item = sub.add_parser(name)
        item.set_defaults(handler=handler)
        item.add_argument("--ledger", required=True, help="live Ledger readback JSON (JOBS/APPLICATIONS/LOG, and NETWORK for network commands)")
        item.add_argument("--receipt", required=True, help="local receipt JSON to write")
        return item

    item = add("network-add", cmd_network_add)
    item.add_argument("--contact", required=True, help="contact JSON with exactly: " + ", ".join(CONTACT_INPUT_KEYS))
    item.add_argument("--as-of", required=True)
    item = add("network-update", cmd_network_update)
    item.add_argument("--contact-id", required=True)
    item.add_argument("--status", required=True)
    item.add_argument("--as-of", required=True)
    item.add_argument("--next-date")
    item.add_argument("--note")
    item = add("network-draft", cmd_network_draft)
    item.add_argument("--contact-id", required=True)
    item.add_argument("--bullet-id", required=True)
    item.add_argument("--runtime-root", required=True, help="verified Career OS runtime root (claims + approved language)")
    item = add("record-outcome", cmd_record_outcome)
    item.add_argument("--job-id", required=True)
    item.add_argument("--application-id")
    item.add_argument("--status", required=True)
    item.add_argument("--as-of", required=True)
    item.add_argument("--note", required=True)
    item = add("weekly-report", cmd_weekly_report)
    item.add_argument("--from", dest="start", required=True)
    item.add_argument("--to", dest="end", required=True)
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    command = None
    try:
        args = build_parser().parse_args(list(sys.argv[1:] if argv is None else argv))
        command = args.command
        code, text, _failure = args.handler(args)
        print(text)
        return code
    except run.RunError as error:
        print(run.FAILURE_MARKER + " " + json.dumps({"command": command, "code": error.code, "detail": error.detail}, sort_keys=True))
        return run.EXIT_ERROR


if __name__ == "__main__":
    raise SystemExit(main())
