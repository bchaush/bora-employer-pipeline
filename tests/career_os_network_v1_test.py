"""Live-shape tests for CAREER_OS_NETWORK_V1 (src/career_os_network_v1.py).

Fixtures use the exact Production Ledger headers (JOBS 20, APPLICATIONS 10, LOG 9) plus the NETWORK 13-column shape this
milestone defines. Drafts use the repository's real Candidate Truth and approved resume language. All tests are local.
"""

from __future__ import annotations

import ast
import contextlib
import copy
import io
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.dont_write_bytecode = True

import career_os_network_v1 as net  # noqa: E402
import career_os_run_v1 as run  # noqa: E402

JOB_ID = "FIXTURE::BUSINESS-SYSTEMS-ANALYST"
URL = "https://careers.example/jobs/business-systems-analyst"
PROFILE = "https://www.linkedin.com/in/fixture-alum"


def assert_true(condition, message):
    if not condition:
        print("FAIL: " + message)
        raise SystemExit(1)


def jobs_row(**values):
    row = {key: "" for key in run.JOBS_HEADERS}
    row.update(values)
    return row


def app_row(**values):
    row = {key: "" for key in run.APPLICATIONS_HEADERS}
    row.update(values)
    return row


def log_row(**values):
    row = {key: "" for key in run.LOG_HEADERS}
    row.update(values)
    return row


def base_ledger():
    return {
        "JOBS": [jobs_row(Job_ID=JOB_ID, Company="Fixture Co", Role="Business Systems Analyst", Official_URL=URL,
                          First_Seen="2026-10-06T08:30:00-04:00", Bora_Decision="PURSUE", Package_Status="READY",
                          Application_Status="SUBMITTED")],
        "APPLICATIONS": [app_row(Application_ID="APP::%s::2026-10-06" % JOB_ID, Job_ID=JOB_ID, Applied_Date="2026-10-06",
                                 Resume_Version="r.pdf | sha256:" + "a" * 64, Cover_Letter_Version="NONE", Channel="Careers site",
                                 Current_Status="SUBMITTED", Last_Update="2026-10-06", Next_Action="Monitor for employer response",
                                 Outcome="receipt sha256:" + "b" * 64)],
        "LOG": [log_row(Run_ID="RECORD_SUBMIT::%s::2026-10-06" % JOB_ID, Timestamp="2026-10-06", Stage="APPLICATION_RECORDED",
                        Source="CAREER_OS_RUN_V1", Job_ID=JOB_ID, Status="SUBMITTED")],
        "NETWORK": [],
    }


def contact(**overrides):
    value = {"Name": "Jane Fixture", "Company": "Fixture Co", "Role_Title": "Operations Manager", "How_Found": PROFILE,
             "Relationship": "BRANDEIS_ALUMNI", "Purpose": "JOB_REFERRAL", "Linked_Job_ID": JOB_ID, "Notes": ""}
    value.update(overrides)
    return value


class Workspace:
    def __init__(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="career-os-network-test-")
        self.dir = Path(self.tmp.name)
        self.n = 0

    def file(self, value) -> str:
        self.n += 1
        path = self.dir / ("in_%d.json" % self.n)
        path.write_text(json.dumps(value), encoding="utf-8")
        return str(path)

    def receipt(self) -> str:
        self.n += 1
        return str(self.dir / ("receipt_%d.json" % self.n))


def invoke(argv):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = net.main([str(x) for x in argv])
    return code, out.getvalue()


def failure_code(text):
    for line in text.splitlines():
        if line.startswith(run.FAILURE_MARKER):
            return json.loads(line[len(run.FAILURE_MARKER):])["code"]
    return None


def row_values(text, label):
    for line in text.splitlines():
        if line.startswith(label + ": "):
            return json.loads(line[len(label) + 2:])
    raise AssertionError("missing " + label)


def add_contact(ws, ledger, value, as_of="2026-10-07"):
    return invoke(["network-add", "--ledger", ws.file(ledger), "--contact", ws.file(value), "--as-of", as_of, "--receipt", ws.receipt()])


def ledger_with_contact(ws, **overrides):
    ledger = base_ledger()
    code, text = add_contact(ws, ledger, contact(**overrides))
    assert_true(code == 0, "fixture contact add succeeds: " + text)
    ledger["NETWORK"].append(row_values(text, "NETWORK_ROW_VALUES"))
    ledger["LOG"].append(row_values(text, "LOG_ROW_VALUES"))
    return ledger, ledger["NETWORK"][0]["Contact_ID"]


def test_add():
    ws = Workspace()
    code, text = add_contact(ws, base_ledger(), contact())
    assert_true(code == 0, "valid contact is accepted")
    row = row_values(text, "NETWORK_ROW_VALUES")
    assert_true(tuple(row) == net.NETWORK_HEADERS, "NETWORK row has exactly the 13 headers in order")
    assert_true(row["Status"] == "TO_CONTACT" and row["Added_On"] == "2026-10-07" and row["Next_Action_Date"] == "2026-10-07"
                and row["Last_Touch"] == "", "new contact starts TO_CONTACT, due today, untouched")
    assert_true(row["Contact_ID"].startswith("NET::") and len(row["Contact_ID"]) == 17, "Contact_ID is deterministic NET::<12 hex>")
    log = row_values(text, "LOG_ROW_VALUES")
    assert_true(tuple(log) == run.LOG_HEADERS and log["Stage"] == "NETWORK_ADDED" and log["Job_ID"] == JOB_ID, "LOG event has the live 9 columns")
    _, again = add_contact(ws, base_ledger(), contact())
    assert_true(row_values(again, "NETWORK_ROW_VALUES") == row, "same input gives the same row (deterministic)")

    rejects = {
        "HOW_FOUND_UNVERIFIABLE": [contact(How_Found=""), contact(How_Found="linkedin jane"), contact(How_Found="http://insecure.example/x"),
                                   contact(How_Found="KNOWN_PERSONALLY", Notes="")],
        "FIELD_INVALID": [contact(Relationship="FRIEND"), contact(Purpose="SALES"), contact(Name=""), contact(Name="Jane\nFixture"),
                          contact(Name="https://x.example/jane")],
        "CONTACT_INVALID": [dict(contact(), Email="jane@example.com"), {k: v for k, v in contact().items() if k != "Notes"}],
        "LINKED_JOB_UNKNOWN": [contact(Linked_Job_ID="NOPE::ROLE")],
    }
    for expected, values in rejects.items():
        for value in values:
            code, text = add_contact(ws, base_ledger(), value)
            assert_true(code == run.EXIT_ERROR and failure_code(text) == expected, "%s rejects %r (got %s)" % (expected, value, failure_code(text)))
    code, text = add_contact(ws, base_ledger(), contact(How_Found="KNOWN_PERSONALLY", Notes="Winter Walk supervisor", Relationship="WINTER_WALK"))
    assert_true(code == 0, "KNOWN_PERSONALLY with a note is accepted")

    ledger, cid = ledger_with_contact(ws)
    for dup in (contact(), contact(How_Found=PROFILE + "/"), contact(How_Found="https://brandeisconnect.com/profile/9", Name="JANE FIXTURE")):
        code, text = add_contact(ws, ledger, dup)
        assert_true(failure_code(text) == "ALREADY_IN_NETWORK", "duplicate contact is refused: %r" % dup)
    bad = copy.deepcopy(ledger)
    bad["NETWORK"][0]["Email"] = "x"
    code, text = add_contact(ws, bad, contact(How_Found="https://example.org/other", Name="Other Person"))
    assert_true(failure_code(text) == "LEDGER_SHAPE_INVALID", "a NETWORK row with an extra column fails closed")
    missing = base_ledger()
    del missing["NETWORK"]
    code, text = add_contact(ws, missing, contact())
    assert_true(failure_code(text) == "LEDGER_INVALID", "a readback without NETWORK fails closed")
    print("PASS: network-add validates real contacts, dedupes, and emits exact NETWORK + LOG rows.")


def test_update():
    ws = Workspace()
    ledger, cid = ledger_with_contact(ws)

    def update(led, status, as_of, *extra):
        return invoke(["network-update", "--ledger", ws.file(led), "--contact-id", cid, "--status", status, "--as-of", as_of,
                       "--receipt", ws.receipt(), *extra])

    code, text = update(ledger, "SENT", "2026-10-08", "--note", "LinkedIn message after connection accepted")
    assert_true(code == 0, "SENT is accepted")
    row = row_values(text, "NETWORK_ROW_VALUES")
    assert_true(tuple(row) == net.NETWORK_HEADERS and row["Status"] == "SENT" and row["Last_Touch"] == "2026-10-08"
                and row["Next_Action_Date"] == "2026-10-15", "SENT schedules a follow-up 7 days later")
    assert_true(row["Notes"] == "2026-10-08 SENT: LinkedIn message after connection accepted", "note is appended with date and status")
    for status, expected in (("REPLIED", "2026-10-11"), ("CALL_DONE", "2026-10-15"), ("REFERRED", "2026-10-22"), ("NO_REPLY", ""), ("CLOSED", "")):
        code, text = update(ledger, status, "2026-10-08")
        assert_true(code == 0 and row_values(text, "NETWORK_ROW_VALUES")["Next_Action_Date"] == expected, "%s next action %s" % (status, expected))
    code, text = update(ledger, "SENT", "2026-10-08", "--next-date", "2026-10-20")
    assert_true(row_values(text, "NETWORK_ROW_VALUES")["Next_Action_Date"] == "2026-10-20", "explicit --next-date wins")
    for args, expected in ((("TO_CONTACT", "2026-10-08"), "STATUS_INVALID"), (("WAITING", "2026-10-08"), "STATUS_INVALID"),
                           (("SENT", "2026-10-06"), "DATE_BACKWARDS"), (("SENT", "2026-13-01"), "DATE_INVALID")):
        code, text = update(ledger, *args)
        assert_true(failure_code(text) == expected, "%r fails %s (got %s)" % (args, expected, failure_code(text)))
    code, text = update(ledger, "SENT", "2026-10-08", "--next-date", "2026-10-01")
    assert_true(failure_code(text) == "DATE_BACKWARDS", "--next-date before --as-of fails")

    sent = copy.deepcopy(ledger)
    _, text = update(sent, "SENT", "2026-10-08")
    sent["NETWORK"][0] = row_values(text, "NETWORK_ROW_VALUES")
    sent["LOG"].append(row_values(text, "LOG_ROW_VALUES"))
    code, text = update(sent, "SENT", "2026-10-08")
    assert_true(failure_code(text) == "ALREADY_RECORDED", "the same event on the same day is not recorded twice")
    closed = copy.deepcopy(ledger)
    closed["NETWORK"][0]["Status"] = "CLOSED"
    code, text = update(closed, "SENT", "2026-10-09")
    assert_true(failure_code(text) == "CONTACT_CLOSED", "a CLOSED contact cannot be reopened")
    code, text = invoke(["network-update", "--ledger", ws.file(ledger), "--contact-id", "NET::000000000000", "--status", "SENT",
                         "--as-of", "2026-10-08", "--receipt", ws.receipt()])
    assert_true(failure_code(text) == "CONTACT_NOT_FOUND", "unknown contact fails")
    print("PASS: network-update enforces statuses, dates, idempotency and deterministic follow-ups.")


def test_draft():
    ws = Workspace()
    approved = json.loads((ROOT / "docs" / "resume" / "BORA_APPROVED_RESUME_LANGUAGE_V1.json").read_text(encoding="utf-8"))
    texts = {bullet["bullet_id"]: bullet["text"] for bullet in approved["bullets"]}
    usable = net.load_networking_bullets(ROOT)
    assert_true(usable and set(usable) <= set(texts), "networking bullets are a subset of approved bullets")
    assert_true(all(usable[key] == texts[key] for key in usable), "networking bullets carry the exact approved text")

    def draft(led, cid, bullet):
        return invoke(["network-draft", "--ledger", ws.file(led), "--contact-id", cid, "--bullet-id", bullet,
                       "--runtime-root", ROOT, "--receipt", ws.receipt()])

    for relationship in net.RELATIONSHIPS:
        for purpose in net.PURPOSES:
            for linked in (JOB_ID, ""):
                ledger, cid = ledger_with_contact(ws, Relationship=relationship, Purpose=purpose, Linked_Job_ID=linked)
                for bullet_id in sorted(usable):
                    code, text = draft(ledger, cid, bullet_id)
                    assert_true(code == 0, "draft builds for %s/%s/%s/%s: %s" % (relationship, purpose, linked, bullet_id, text))
                    receipt = json.loads(Path(ws.dir / ("receipt_%d.json" % ws.n)).read_text(encoding="utf-8"))
                    body = receipt["draft"]
                    assert_true(receipt["word_count"] <= net.DRAFT_MAX_WORDS, "draft is at most 120 words")
                    original = texts[bullet_id]
                    assert_true(("I " + original[0].lower() + original[1:]) in body, "draft quotes the approved bullet verbatim")
                    assert_true(body.startswith("Hi Jane,") and net.RELATIONSHIP_PHRASE[relationship] in body and net.ASK[purpose] in body,
                                "draft uses only fixed phrases for relationship and ask")
                    if linked and purpose != "CLIENT_PROSPECT":
                        assert_true("Business Systems Analyst" in body and "Fixture Co" in body and URL in body, "linked role is cited from JOBS")
                    assert_true("referral" not in body.lower(), "the first message never asks a stranger for a referral")
    ledger, cid = ledger_with_contact(ws)
    code, text = draft(ledger, cid, "B999")
    assert_true(failure_code(text) == "BULLET_NOT_ALLOWED", "unknown bullet is refused")
    long_ledger = copy.deepcopy(ledger)
    long_ledger["JOBS"][0]["Role"] = " ".join(["Very"] * 120) + " Analyst"
    code, text = draft(long_ledger, cid, sorted(usable)[0])
    assert_true(failure_code(text) == "DRAFT_TOO_LONG", "a draft over 120 words fails instead of being trimmed")
    closed = copy.deepcopy(ledger)
    closed["NETWORK"][0]["Status"] = "CLOSED"
    code, text = draft(closed, cid, sorted(usable)[0])
    assert_true(failure_code(text) == "CONTACT_CLOSED", "no drafts for CLOSED contacts")
    print("PASS: network-draft builds every relationship x purpose x approved bullet within 120 words from exact approved text.")


def test_outcome():
    ws = Workspace()
    ledger = base_ledger()

    def outcome(led, status, as_of, note="Recruiter email: phone screen scheduled", *extra):
        return invoke(["record-outcome", "--ledger", ws.file(led), "--job-id", JOB_ID, "--status", status, "--as-of", as_of,
                       "--note", note, "--receipt", ws.receipt(), *extra])

    code, text = outcome(ledger, "INTERVIEW", "2026-10-09")
    assert_true(code == 0, "INTERVIEW is recorded")
    row = row_values(text, "APPLICATIONS_ROW_VALUES")
    assert_true(tuple(row) == run.APPLICATIONS_HEADERS, "APPLICATIONS row keeps the live 10 columns")
    assert_true(row["Current_Status"] == "INTERVIEW" and row["Last_Update"] == "2026-10-09" and row["Next_Action"] == "Prepare for interview",
                "status, date and next action are set")
    assert_true(row["Outcome"].startswith("receipt sha256:" + "b" * 64) and row["Outcome"].endswith("2026-10-09 INTERVIEW: Recruiter email: phone screen scheduled"),
                "original receipt evidence is kept and the outcome is appended")
    assert_true(row["Resume_Version"] == ledger["APPLICATIONS"][0]["Resume_Version"], "Resume_Version is untouched")
    assert_true("JOBS_ROW_VALUES" not in text, "JOBS is never touched")
    log = row_values(text, "LOG_ROW_VALUES")
    assert_true(log["Stage"] == "APPLICATION_OUTCOME" and log["Status"] == "INTERVIEW", "outcome LOG event")
    for args, expected in ((("OFFERED", "2026-10-09"), "STATUS_INVALID"), (("REJECTED", "2026-10-01"), "DATE_BACKWARDS")):
        code, text = outcome(ledger, *args)
        assert_true(failure_code(text) == expected, "%r fails %s" % (args, expected))
    code, text = outcome(ledger, "REJECTED", "2026-10-09", "")
    assert_true(failure_code(text) == "FIELD_INVALID", "an outcome needs a note")
    two = copy.deepcopy(ledger)
    two["APPLICATIONS"].append(dict(two["APPLICATIONS"][0], Application_ID="APP::%s::2026-10-08" % JOB_ID))
    code, text = outcome(two, "REJECTED", "2026-10-09")
    assert_true(failure_code(text) == "APPLICATION_AMBIGUOUS", "two applications for one job need --application-id")
    code, text = outcome(two, "REJECTED", "2026-10-09", "No longer considered", "--application-id", "APP::%s::2026-10-08" % JOB_ID)
    assert_true(code == 0, "--application-id resolves the ambiguity")
    none = copy.deepcopy(ledger)
    none["APPLICATIONS"] = []
    code, text = outcome(none, "REJECTED", "2026-10-09")
    assert_true(failure_code(text) == "APPLICATION_NOT_FOUND", "no application fails")
    print("PASS: record-outcome updates only APPLICATIONS + LOG, keeps evidence, and fails closed.")


def test_weekly_report():
    ws = Workspace()
    ledger, cid = ledger_with_contact(ws)
    ledger["NETWORK"][0].update(Status="SENT", Last_Touch="2026-10-08", Next_Action_Date="2026-10-11")
    ledger["LOG"].append(log_row(Run_ID="NETWORK::%s::2026-10-08::SENT" % cid, Timestamp="2026-10-08", Stage="NETWORK_UPDATE",
                                 Source=net.LOG_SOURCE, Job_ID=JOB_ID, Status="SENT"))
    ledger["LOG"].append(log_row(Run_ID="OUTCOME::x::2026-10-09::INTERVIEW", Timestamp="2026-10-09", Stage="APPLICATION_OUTCOME",
                                 Source=net.LOG_SOURCE, Job_ID=JOB_ID, Status="INTERVIEW"))
    ledger["LOG"].append(log_row(Run_ID="OLD", Timestamp="2026-09-01T10:00:00-04:00", Stage="APPLICATION_OUTCOME", Status="REJECTED"))
    code, text = invoke(["weekly-report", "--ledger", ws.file(ledger), "--from", "2026-10-05", "--to", "2026-10-11", "--receipt", ws.receipt()])
    assert_true(code == 0, "weekly report runs: " + text)
    counts = json.loads(Path(ws.dir / ("receipt_%d.json" % ws.n)).read_text(encoding="utf-8"))["counts"]
    assert_true(counts["jobs_first_seen_in_window"] == 1 and counts["applications_submitted_in_window"] == 1, "window counts for JOBS/APPLICATIONS")
    assert_true(counts["outcomes_in_window"] == {"INTERVIEW": 1}, "outcomes are counted from LOG events inside the window only")
    assert_true(counts["contacts_added_in_window"] == 1 and counts["contact_updates_in_window"] == {"SENT": 1}, "network events counted")
    assert_true([item["Contact_ID"] for item in counts["follow_ups_due"]] == [cid], "due follow-ups are listed")
    assert_true("%" not in text and "score" not in text.lower().replace("no scores", ""), "no percentages or scores in the report")
    code, text = invoke(["weekly-report", "--ledger", ws.file(ledger), "--from", "2026-10-11", "--to", "2026-10-05", "--receipt", ws.receipt()])
    assert_true(failure_code(text) == "DATE_BACKWARDS", "reversed window fails")
    print("PASS: weekly-report counts events by window and lists due follow-ups.")


def test_purity_and_live_contract():
    source = (ROOT / "src" / "career_os_network_v1.py").read_text(encoding="utf-8")
    imported = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            imported |= {alias.name.split(".")[0] for alias in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    forbidden = {"requests", "urllib", "http", "socket", "subprocess", "smtplib", "selenium", "playwright", "googleapiclient"}
    assert_true(not (imported & forbidden), "network CLI imports nothing that can send, browse or call out: %s" % sorted(imported & forbidden))
    assert_true(len(net.NETWORK_HEADERS) == 13 and len(set(net.NETWORK_HEADERS)) == 13, "NETWORK has 13 unique headers")
    assert_true(set(net.FOLLOW_UP_DAYS) == set(net.STATUSES) - {"TO_CONTACT"}, "every reachable status has a follow-up rule")
    runbook = (ROOT / "docs" / "CAREER_OS_OPERATE_MODE_V1.md").read_text(encoding="utf-8")
    for needle in ("career_os_network_v1.py network-add", "network-update", "network-draft", "record-outcome", "weekly-report",
                   " | ".join(net.NETWORK_HEADERS)):
        assert_true(needle in runbook, "runbook documents %s" % needle)
    assert_true(" ^\n" not in runbook, "runbook command lines use POSIX line continuation, not Windows ^")
    config = json.loads((ROOT / "docs" / "CAREER_OS_OPERATE_MODE_V1.json").read_text(encoding="utf-8"))
    network = config.get("network_contract", {})
    assert_true(network.get("cli") == "src/career_os_network_v1.py" and network.get("network_headers") == list(net.NETWORK_HEADERS)
                and network.get("sends_messages") is False, "config names the network CLI, headers and no-send rule")
    print("PASS: the network CLI is pure/local and the runbook/config document it.")


test_add()
test_update()
test_draft()
test_outcome()
test_weekly_report()
test_purity_and_live_contract()
print("PASS: 6 groups of career_os_network_v1_test")
