"""Focused regression for CAREER_OS_PURSUIT_DECISION_PERSISTENCE_V1."""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from production_ledger import empty_state, state_from_ledger_rows  # noqa: E402
from pursuit_decision import (  # noqa: E402
    ENGINE_BASELINE,
    PursuitDecisionError,
    build_decision_mutation_plan,
    compute_context_fingerprint,
    compute_event_id,
    derive_current_pursuit_state,
)


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def expect_error(code: str, fn, message: str) -> None:
    try:
        fn()
    except PursuitDecisionError as exc:
        check(exc.error_code == code, f"{message}: expected {code}, got {exc.error_code}")
    else:
        raise AssertionError(f"{message}: expected fail-closed {code}")


def make_job(job_id: str, **overrides) -> dict:
    row = {
        "Job_ID": job_id,
        "Company": "Test Co",
        "Role": "Test Role",
        "Discovery_Source": "MANUAL_URL",
        "Discovery_URL": "https://discovery.example/x",
        "Official_URL": f"https://careers.example/{job_id}",
        "First_Seen": "2026-09-27T10:00:00+00:00",
        "Last_Verified": "2026-09-27T12:00:00+00:00",
        "Pipeline_State": "REVIEW_READY",
        "Freshness_State": "PASS",
        "Geography_State": "PASS",
        "OPT_Screen_State": "PASS",
        "Candidate_Condition_State": "PASS",
        "Threshold_State": "PASS",
        "Role_Status": "VERIFIED_LIVE",
        "Match_State": "ANALYZED",
        "Decision": "WATCH",
        "Bora_Decision": None,
    }
    row.update(overrides)
    return row


class Ledger:
    """In-memory JOBS/LOG applying mutation plans exactly as a provider would."""

    def __init__(self, jobs: list[dict]) -> None:
        self.jobs = [copy.deepcopy(j) for j in jobs]
        self.log: list[dict] = []
        self.applications: list[dict] = []
        self.counter = 0

    def row(self, job_id: str) -> dict:
        return next(j for j in self.jobs if j["Job_ID"] == job_id)

    def latest(self, job_id: str) -> str | None:
        ids = derive_current_pursuit_state(self.row(job_id), self.log)["history_event_ids"]
        return ids[-1] if ids else None

    def decide(self, job_id: str, decision: str, *, run: str | None = None,
               supersedes="AUTO", reviewed="AUTO", reason=None,
               decided_at="2026-09-28T09:00:00-04:00") -> dict:
        self.counter += 1
        request = {
            "job_id": job_id,
            "decision": decision,
            "reviewed_context_fingerprint": (
                compute_context_fingerprint(self.row(job_id)) if reviewed == "AUTO" else reviewed
            ),
            "decision_run_id": run or f"RUN_{self.counter}",
            "decided_at": decided_at,
            "supersedes_event_id": self.latest(job_id) if supersedes == "AUTO" else supersedes,
            "reason_note": reason,
        }
        plan = build_decision_mutation_plan(request, self.jobs, self.log)
        for m in plan["jobs_mutations"]:
            self.row(m["Job_ID"])["Bora_Decision"] = m["Bora_Decision"]
        self.log.extend(plan["log_mutations"])
        return plan

    def snapshot(self):
        return copy.deepcopy((self.jobs, self.log))


# 1. Fingerprint is deterministic, null-explicit, and ignores Bora_Decision.
a = make_job("TEST::A")
fp = compute_context_fingerprint(a)
check(fp == compute_context_fingerprint(copy.deepcopy(a)), "fingerprint must be deterministic")
check(fp == compute_context_fingerprint({**a, "Bora_Decision": "PURSUE"}), "Bora_Decision must not enter fingerprint")
check(fp != compute_context_fingerprint({**a, "Match_State": "NOT_REACHED"}), "Match_State must enter fingerprint")
check(fp != compute_context_fingerprint({**a, "Last_Verified": "2026-09-28T00:00:00+00:00"}), "Last_Verified must enter fingerprint")
check(fp != compute_context_fingerprint({**a, "Decision": "REJECT"}), "system Decision must enter fingerprint")
sparse = {"Job_ID": "TEST::S"}
check(len(compute_context_fingerprint(sparse)) == 64, "missing fields must be explicit nulls, not errors")
print("PASS 1: context fingerprint deterministic, null-explicit, excludes Bora_Decision.")

# 2. Exact canonical Job_ID membership; noncanonical subjects fail closed with zero mutation.
L = Ledger([make_job("TEST::A")])
before = L.snapshot()
for bad in ("TEST::B", "test::a", " TEST::A", "TEST::A ", "linkedin:3912345678", "https://www.linkedin.com/jobs/view/1", "Test Co Test Role", "", None):
    expect_error(
        "UNKNOWN_JOB_ID",
        lambda bad=bad: build_decision_mutation_plan(
            {"job_id": bad, "decision": "PURSUE", "reviewed_context_fingerprint": fp,
             "decision_run_id": "R", "decided_at": "2026-09-28T09:00:00-04:00", "supersedes_event_id": None},
            L.jobs, L.log),
        f"noncanonical Job_ID {bad!r}",
    )
check(L.snapshot() == before, "failed decisions must leave JOBS/LOG untouched")
dup = [make_job("TEST::D"), make_job("TEST::D")]
expect_error("AMBIGUOUS_JOB_ID", lambda: build_decision_mutation_plan(
    {"job_id": "TEST::D", "decision": "REJECT", "reviewed_context_fingerprint": compute_context_fingerprint(dup[0]),
     "decision_run_id": "R", "decided_at": "2026-09-28T09:00:00-04:00", "supersedes_event_id": None}, dup, []),
    "duplicate JOBS rows")
print("PASS 2: exact canonical JOBS membership required; no Job_ID invented or fuzzy matched.")

# 3. Only PURSUE/WATCH/REJECT; system decision values are not human decisions.
for bad in ("APPLY", "PRIORITY_APPLY", "EFFICIENT_APPLY", "UNDECIDED", "pursue", None):
    expect_error("INVALID_DECISION", lambda bad=bad: L.decide("TEST::A", bad), f"decision {bad!r}")
check(L.snapshot() == before, "invalid decisions must not mutate")
print("PASS 3: only PURSUE/WATCH/REJECT are valid human decisions.")

# 4. Reviewed-context binding: missing or stale fingerprint fails closed; no mutation.
expect_error("MISSING_REVIEWED_CONTEXT_FINGERPRINT", lambda: L.decide("TEST::A", "PURSUE", reviewed=None), "missing reviewed fp")
reviewed_before_change = compute_context_fingerprint(L.row("TEST::A"))
L.row("TEST::A")["Last_Verified"] = "2026-09-28T08:00:00+00:00"  # JOBS changes after Bora's review
before = L.snapshot()
expect_error("STALE_REVIEWED_CONTEXT", lambda: L.decide("TEST::A", "PURSUE", reviewed=reviewed_before_change), "stale reviewed fp")
check(L.snapshot() == before, "stale reviewed context must produce no JOBS or LOG mutation")
plan = L.decide("TEST::A", "PURSUE")  # re-reviewed against current context
check(len(plan["jobs_mutations"]) == 1 and len(plan["log_mutations"]) == 1, "fresh review persists")
print("PASS 4: reviewed_context_fingerprint must equal current recomputed context.")

# 5. Exact log encoding, event identity, and JOBS projection bounds.
row = L.log[-1]
check(
    (row["Stage"], row["Source"], row["Status"], row["Error_Code"], row["Engine_Baseline"])
    == ("PURSUIT_DECISION", "BORA", "NORMALIZED", None, "CAREER_OS_PURSUIT_DECISION_PERSISTENCE_V1"),
    "LOG row must use the exact contract encoding",
)
event = json.loads(row["Notes"])
check(row["Notes"] == json.dumps(event, sort_keys=True, separators=(",", ":"), ensure_ascii=False), "Notes must be canonical sorted-key compact JSON")
check(
    set(event) == {"Job_ID", "decision", "decided_at", "decided_by", "decision_run_id", "reason_note",
                   "reviewed_context_fingerprint", "decision_context_fingerprint", "event_id", "supersedes_event_id"},
    "Notes must carry exactly the decision-event fields",
)
check(event["decided_by"] == "BORA" and event["supersedes_event_id"] is None, "first event: decided_by BORA, no supersedes")
check(event["reviewed_context_fingerprint"] == event["decision_context_fingerprint"] == compute_context_fingerprint(L.row("TEST::A")), "fingerprints must agree")
expected_id = compute_event_id(job_id="TEST::A", decision="PURSUE",
                               decision_context_fingerprint=event["decision_context_fingerprint"],
                               supersedes_event_id=None, decision_run_id=event["decision_run_id"])
check(event["event_id"] == expected_id and expected_id.startswith("PDE_V1::") and len(expected_id) == 8 + 64, "event_id format")
check(
    compute_event_id(job_id="TEST::A", decision="PURSUE", decision_context_fingerprint="0" * 64,
                     supersedes_event_id=None, decision_run_id="X")
    == compute_event_id(job_id="TEST::A", decision="PURSUE", decision_context_fingerprint="0" * 64,
                        supersedes_event_id=None, decision_run_id="X"),
    "event_id deterministic",
)
check(set(plan["jobs_mutations"][0]) == {"Op", "Job_ID", "Bora_Decision"}, "JOBS mutation touches Bora_Decision only")
check(plan["jobs_mutations"][0]["Bora_Decision"] == "PURSUE", "Bora_Decision projection")
print("PASS 5: exact PURSUIT_DECISION LOG encoding and bounded Bora_Decision-only JOBS mutation.")

# 6. Idempotent exact replay; decided_at / reason_note excluded from identity; conflicts fail closed.
L2 = Ledger([make_job("TEST::R")])
first = L2.decide("TEST::R", "PURSUE", run="RUN_FIXED", reason="initial")
state_before = L2.snapshot()
replay = build_decision_mutation_plan(
    {"job_id": "TEST::R", "decision": "PURSUE",
     "reviewed_context_fingerprint": compute_context_fingerprint(L2.row("TEST::R")),
     "decision_run_id": "RUN_FIXED", "decided_at": "2030-01-01T00:00:00+00:00",
     "supersedes_event_id": None, "reason_note": "initial"},
    L2.jobs, L2.log)
check(replay == {"jobs_mutations": [], "log_mutations": []}, "exact replay (different decided_at) must be a no-op")
expect_error("EVENT_ID_CONFLICT", lambda: build_decision_mutation_plan(
    {"job_id": "TEST::R", "decision": "PURSUE",
     "reviewed_context_fingerprint": compute_context_fingerprint(L2.row("TEST::R")),
     "decision_run_id": "RUN_FIXED", "decided_at": "2026-09-28T09:00:00-04:00",
     "supersedes_event_id": None, "reason_note": "different"}, L2.jobs, L2.log), "conflicting reuse of event_id")
tampered = copy.deepcopy(L2.log)
tampered.append(copy.deepcopy(tampered[0]))
tn = json.loads(tampered[1]["Notes"])
tn["reason_note"] = "tampered"
tampered[1]["Notes"] = json.dumps(tn, sort_keys=True, separators=(",", ":"))
expect_error("EVENT_ID_CONFLICT", lambda: derive_current_pursuit_state(L2.row("TEST::R"), tampered), "conflicting LOG duplicate")
dup_ok = copy.deepcopy(L2.log) + copy.deepcopy(L2.log)
check(derive_current_pursuit_state(L2.row("TEST::R"), dup_ok)["history_event_ids"] == derive_current_pursuit_state(L2.row("TEST::R"), L2.log)["history_event_ids"], "exact duplicate LOG rows collapse")
check(L2.snapshot() == state_before, "replay must not mutate")
print("PASS 6: exact replay idempotent; conflicting event_id reuse fails closed.")

# 7. Explicit supersession, PURSUE -> REJECT -> PURSUE, append-only history.
L3 = Ledger([make_job("TEST::S")])
e1 = L3.decide("TEST::S", "PURSUE")
id1 = json.loads(e1["log_mutations"][0]["Notes"])["event_id"]
expect_error("SUPERSEDES_MISMATCH", lambda: L3.decide("TEST::S", "REJECT", supersedes=None), "missing supersedes")
expect_error("SUPERSEDES_MISMATCH", lambda: L3.decide("TEST::S", "REJECT", supersedes="PDE_V1::" + "a" * 64), "wrong supersedes")
check(len(L3.log) == 1, "failed supersession must not append")
e2 = L3.decide("TEST::S", "REJECT")
id2 = json.loads(e2["log_mutations"][0]["Notes"])["event_id"]
e3 = L3.decide("TEST::S", "PURSUE", run="RUN_3")
id3 = json.loads(e3["log_mutations"][0]["Notes"])["event_id"]
check(len({id1, id2, id3}) == 3, "PURSUE->REJECT->PURSUE under unchanged context must yield three distinct events")
check(json.loads(e3["log_mutations"][0]["Notes"])["supersedes_event_id"] == id2, "third event supersedes second")
st = derive_current_pursuit_state(L3.row("TEST::S"), L3.log)
check(st["state"] == "PURSUE" and st["history_event_ids"] == [id1, id2, id3], "chain preserved in order, current is last")
check([json.loads(r["Notes"])["decision"] for r in L3.log] == ["PURSUE", "REJECT", "PURSUE"], "history append-only")
# Branching history is not trusted.
branch = copy.deepcopy(L3.log)
fork = copy.deepcopy(L3.log[1])
fn = json.loads(fork["Notes"])
fn["decision_run_id"] = "FORK"
fn["decision"] = "WATCH"
fn["event_id"] = compute_event_id(job_id="TEST::S", decision="WATCH",
                                  decision_context_fingerprint=fn["decision_context_fingerprint"],
                                  supersedes_event_id=fn["supersedes_event_id"], decision_run_id="FORK")
fork["Notes"] = json.dumps(fn, sort_keys=True, separators=(",", ":"))
branch.append(fork)
expect_error("BROKEN_DECISION_CHAIN", lambda: derive_current_pursuit_state(L3.row("TEST::S"), branch), "branching history")
print("PASS 7: explicit supersession; PURSUE->REJECT->PURSUE deterministic; history append-only.")

# 8. Bora_Decision is display-only; stale derived state is non-authorizing.
check(L3.row("TEST::S")["Bora_Decision"] == "PURSUE", "cell shows latest decision")
L3.row("TEST::S")["Match_State"] = "PROCESSING_ERROR"  # unrelated later ledger change; cell not rewritten
check(L3.row("TEST::S")["Bora_Decision"] == "PURSUE", "cell still visibly PURSUE")
st = derive_current_pursuit_state(L3.row("TEST::S"), L3.log)
check(st["state"] == "STALE_RECONFIRMATION_REQUIRED" and not st["authorizes_pursuit"], "stale PURSUE must not authorize")
check(st["latest_decision"] == "PURSUE", "stale state still reports what was latest")
# Cell alone never authorizes.
cell_only = make_job("TEST::C", Bora_Decision="PURSUE")
st = derive_current_pursuit_state(cell_only, [])
check(st["state"] == "NO_DECISION" and not st["authorizes_pursuit"], "Bora_Decision cell alone is not authorization")
# Reconfirmation restores authority, still appending.
L3.decide("TEST::S", "PURSUE", run="RUN_RECONFIRM")
st = derive_current_pursuit_state(L3.row("TEST::S"), L3.log)
check(st["state"] == "PURSUE" and st["authorizes_pursuit"] and len(st["history_event_ids"]) == 4, "reconfirmation appends and re-authorizes")
print("PASS 8: Bora_Decision display-only; stale intent derives STALE_RECONFIRMATION_REQUIRED.")

# 9. WATCH and REJECT never authorize; system Decision is separate from human decision.
L4 = Ledger([make_job("TEST::W", Decision="PRIORITY_APPLY")])
L4.decide("TEST::W", "WATCH")
st = derive_current_pursuit_state(L4.row("TEST::W"), L4.log)
check(st["state"] == "WATCH" and not st["authorizes_pursuit"], "WATCH must not authorize")
check(L4.row("TEST::W")["Decision"] == "PRIORITY_APPLY", "system Decision untouched by human decision")
check(derive_current_pursuit_state(make_job("TEST::P", Decision="PRIORITY_APPLY"), [])["authorizes_pursuit"] is False,
      "system recommendation is never Bora authorization")
L4.decide("TEST::W", "REJECT")
check(not derive_current_pursuit_state(L4.row("TEST::W"), L4.log)["authorizes_pursuit"], "REJECT must not authorize")
print("PASS 9: WATCH/REJECT non-authorizing; system recommendation separate from Bora decision.")

# 10. Parser isolation: only exact Stage + Engine_Baseline rows; malformed own rows fail closed.
noise = [
    {"Run_ID": "N", "Timestamp": "2026-09-28T09:00:00+00:00", "Stage": "PURSUIT_DECISION", "Source": "BORA",
     "Job_ID": "TEST::S", "Status": "NORMALIZED", "Error_Code": None,
     "Engine_Baseline": "SOME_OTHER_BASELINE", "Notes": "not json"},
    {"Run_ID": "N", "Timestamp": "2026-09-28T09:00:00+00:00", "Stage": "LEDGER_PERSISTENCE", "Source": "GMAIL",
     "Job_ID": "TEST::S", "Status": "NORMALIZED", "Error_Code": None,
     "Engine_Baseline": ENGINE_BASELINE, "Notes": "not json"},
]
check(derive_current_pursuit_state(L3.row("TEST::S"), noise + L3.log)["state"] == "PURSUE", "foreign rows ignored")
bad_own = [{**L3.log[0], "Notes": "not json"}]
expect_error("MALFORMED_DECISION_EVENT", lambda: derive_current_pursuit_state(L3.row("TEST::S"), bad_own), "malformed own row")
forged = copy.deepcopy(L3.log[0])
fnotes = json.loads(forged["Notes"])
fnotes["decision"] = "REJECT"  # event_id no longer matches identity material
forged["Notes"] = json.dumps(fnotes, sort_keys=True, separators=(",", ":"))
expect_error("EVENT_ID_MISMATCH", lambda: derive_current_pursuit_state(L3.row("TEST::S"), [forged]), "forged event")
print("PASS 10: parser consumes only exact rows; tampered own rows fail closed.")

# 11. Existing production_ledger rehydration is unchanged by PURSUIT_DECISION rows.
existing_log = [
    {"Run_ID": "GM1", "Timestamp": "2026-09-27T10:00:00+00:00", "Stage": "INGESTION", "Source": "GMAIL",
     "Job_ID": "TEST::S", "Status": "NORMALIZED", "Error_Code": None,
     "Engine_Baseline": "SUPERVISED_PRODUCTION_V1_SLICE_1_GMAIL_TO_SHEET",
     "Notes": json.dumps({"discovery_lead_id": "LEAD-1"}, sort_keys=True, separators=(",", ":"))},
    {"Run_ID": "GM2", "Timestamp": "2026-09-27T11:00:00+00:00", "Stage": "GATE_MATCH_PROJECTION", "Source": "SUPERVISED_ANALYSIS",
     "Job_ID": "TEST::S", "Status": "REVIEW_READY", "Error_Code": None,
     "Engine_Baseline": "SUPERVISED_PRODUCTION_V1_SLICE_2_GATES_MATCH_TRUTH_TO_SHEET",
     "Notes": json.dumps({"operational_job_id": "TEST::S", "gate_match_fingerprint": "f" * 64}, sort_keys=True, separators=(",", ":"))},
]
jobs_for_ledger = [make_job("TEST::S")]
baseline_state = state_from_ledger_rows(jobs_for_ledger, existing_log)
with_pursuit = state_from_ledger_rows(jobs_for_ledger, existing_log + L3.log)
check(baseline_state == with_pursuit, "PURSUIT_DECISION rows must not change production_ledger rehydration")
check(baseline_state["processed_lead_ids"] == ["LEAD-1"], "baseline rehydration sanity")
check(state_from_ledger_rows([], L3.log) == state_from_ledger_rows([], []) == {**empty_state()}, "pursuit rows alone rehydrate to empty state")
print("PASS 11: production_ledger.state_from_ledger_rows unchanged with PURSUIT_DECISION rows present.")

# 12. Five-role dogfood regression (deterministic test rows/IDs only).
roles = ["TEST::EXPANSION", "TEST::JOBRIGHT", "TEST::DAIRYLAND", "TEST::MAYO", "TEST::LIDS"]


def run_five_role() -> Ledger:
    fx = Ledger([make_job(r, Discovery_Source="MANUAL_URL", Discovery_URL=f"https://www.linkedin.com/jobs/view/{i}")
                 for i, r in enumerate(roles)])
    fx.decide("TEST::EXPANSION", "PURSUE", run="DOG_EXP_1")
    fx.decide("TEST::EXPANSION", "REJECT", run="DOG_EXP_2")
    fx.decide("TEST::JOBRIGHT", "PURSUE", run="DOG_JR_1")
    fx.decide("TEST::JOBRIGHT", "REJECT", run="DOG_JR_2")
    for r, tag in (("TEST::DAIRYLAND", "DAIRY"), ("TEST::MAYO", "MAYO"), ("TEST::LIDS", "LIDS")):
        fx.decide(r, "REJECT", run=f"DOG_{tag}_1")
    return fx


fx = run_five_role()
check(len(fx.log) == 7, "fixture preserves seven human events")
for r in roles:
    st = derive_current_pursuit_state(fx.row(r), fx.log)
    check(st["state"] == "REJECT" and not st["authorizes_pursuit"], f"{r} current derived decision is REJECT")
for r in ("TEST::EXPANSION", "TEST::JOBRIGHT"):
    decisions = [json.loads(x["Notes"])["decision"] for x in fx.log if x["Job_ID"] == r]
    check(decisions == ["PURSUE", "REJECT"], f"{r} temporary PURSUE stays historical")
# Discovery-only identifiers are never promoted to canonical identity.
for bad in ("linkedin:0", "https://www.linkedin.com/jobs/view/0", "jobright:abc", "Test Co Test Role"):
    expect_error("UNKNOWN_JOB_ID", lambda bad=bad: fx.decide(bad, "PURSUE") if False else build_decision_mutation_plan(
        {"job_id": bad, "decision": "PURSUE", "reviewed_context_fingerprint": "0" * 64, "decision_run_id": "X",
         "decided_at": "2026-09-28T09:00:00-04:00", "supersedes_event_id": None}, fx.jobs, fx.log), f"fixture rejects {bad}")
check(all(j["Job_ID"] in roles for j in fx.jobs) and len(fx.jobs) == 5, "no Job_ID invented")
# Full replay of the entire fixture is idempotent.
before = fx.snapshot()
chain_ids: dict[str, list[str]] = {}
for r in roles:
    chain_ids[r] = derive_current_pursuit_state(fx.row(r), fx.log)["history_event_ids"]
replays = [
    ("TEST::EXPANSION", "PURSUE", "DOG_EXP_1", None), ("TEST::EXPANSION", "REJECT", "DOG_EXP_2", chain_ids["TEST::EXPANSION"][0]),
    ("TEST::JOBRIGHT", "PURSUE", "DOG_JR_1", None), ("TEST::JOBRIGHT", "REJECT", "DOG_JR_2", chain_ids["TEST::JOBRIGHT"][0]),
    ("TEST::DAIRYLAND", "REJECT", "DOG_DAIRY_1", None), ("TEST::MAYO", "REJECT", "DOG_MAYO_1", None),
    ("TEST::LIDS", "REJECT", "DOG_LIDS_1", None),
]
for job_id, decision, run, sup in replays:
    p = build_decision_mutation_plan(
        {"job_id": job_id, "decision": decision,
         "reviewed_context_fingerprint": compute_context_fingerprint(fx.row(job_id)),
         "decision_run_id": run, "decided_at": "2026-09-28T09:00:00-04:00", "supersedes_event_id": sup},
        fx.jobs, fx.log)
    check(p == {"jobs_mutations": [], "log_mutations": []}, f"replay of {run} must be idempotent")
check(fx.snapshot() == before, "fixture replay must not mutate")
check(run_five_role().log == fx.log, "fixture is deterministic across independent runs")
print("PASS 12: five-role dogfood fixture: seven events, all REJECT, PURSUEs historical, replay idempotent.")

# 13. Application Truth and submission are untouched.
check(fx.applications == [], "no APPLICATIONS rows")
for r in fx.log:
    check(r["Stage"] == "PURSUIT_DECISION", "only PURSUIT_DECISION LOG rows are produced")
history_path = ROOT / "docs" / "application" / "BORA_APPLICATION_HISTORY_V1.json"
if history_path.exists():
    for r in roles:
        check(r not in history_path.read_text(encoding="utf-8"), "application history must not contain decided roles")
src = (ROOT / "src" / "pursuit_decision.py").read_text(encoding="utf-8")
for forbidden in ("requests", "urllib", "smtplib", "googleapiclient", "selenium", "playwright", "submit("):
    check(forbidden not in src, f"pursuit_decision.py must contain no {forbidden} I/O or Application Truth writes")
print("PASS 13: no Application Truth, package, submission, or provider I/O introduced.")

print("ALL CAREER_OS_PURSUIT_DECISION_PERSISTENCE_V1 CHECKS PASSED")
