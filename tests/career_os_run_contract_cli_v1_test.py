"""Regression tests for the CAREER_OS_RUN_CONTRACT_V1 operator CLI (src/career_os_run_v1.py).

Dependency-free; all fixtures are SYNTHETIC and local. The cloud adapter's run_request and verify_fonts are replaced with deterministic
fakes where a real renderer or font bytes would be needed; nothing touches Drive, Sheets, the web or any submission surface.
"""

from __future__ import annotations

import contextlib
import copy
import hashlib
import io
import json
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.dont_write_bytecode = True

import career_os_cloud_operate_v1 as cloud  # noqa: E402
import career_os_run_v1 as run  # noqa: E402
import gold_package_handoff as handoff  # noqa: E402

MAIN_SHA = "a" * 40


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        print("FAIL: " + message)
        sys.stdout.flush()
        raise SystemExit(1)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def invoke(argv: list) -> tuple:
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        code = run.main([str(item) for item in argv])
    return code, buffer.getvalue()


def fenced_blocks(output: str) -> list:
    return [part for part in output.split("```") if part.startswith("text\n")]


def failure(output: str) -> dict:
    lines = [line for line in output.splitlines() if line.startswith(run.FAILURE_MARKER)]
    assert_true(len(lines) == 1, "exactly one machine-readable failure line: %r" % output)
    return json.loads(lines[0][len(run.FAILURE_MARKER):])


def write(path: Path, value) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(value if isinstance(value, bytes) else json.dumps(value, sort_keys=True).encode("utf-8"))
    return path


# Slate ------------------------------------------------------------------------------------------

def role(job_id="J1", **overrides) -> dict:
    value = {"job_id": job_id, "company": "Fixture Co", "role": "Data Analyst", "official_url": "https://careers.example/" + job_id,
             "source": "MANUAL_URL", "location_arrangement": "Remote", "Geography_State": "PASS",
             "work_authorization_text": "Employer sponsors work authorization.", "OPT_Screen_State": "PASS", "mandatory_gaps": [],
             "recommendation": "PURSUE", "reasons": ["Requirements match SQL and reporting evidence."]}
    value.update(overrides)
    return value


def slate_run(tmp: Path, roles) -> tuple:
    screening = write(tmp / "screening.json", roles)
    return invoke(["slate", "--screening", screening, "--receipt", tmp / "slate_receipt.json"])


def test_slate() -> None:
    with tempfile.TemporaryDirectory() as raw:
        tmp = Path(raw)
        code, output = slate_run(tmp, [role("J1"), role("J2", recommendation="WATCH", reasons=["100% onsite requirement; salary up 5%."])])
        assert_true(code == 0 and len(fenced_blocks(output)) == 1, "a valid slate prints exactly one fenced block: " + output)
        receipt = json.loads((tmp / "slate_receipt.json").read_text(encoding="utf-8"))
        rows = receipt["jobs_rows"]
        assert_true([row["Job_ID"] for row in rows] == ["J1", "J2"], "one JOBS row object per role")
        for row in rows:
            assert_true(set(row) == {"Job_ID", "Company", "Role", "Official_URL", "Discovery_Source", "Geography_State", "OPT_Screen_State",
                                     "Match_State", "Decision", "Bora_Decision"}, "exact owned JOBS row keys")
            assert_true(row["Bora_Decision"] is None and row["Match_State"] == "ANALYZED", "no Bora authority is created")
        assert_true(rows[1]["Decision"] == "WATCH", "the system recommendation populates Decision")
        before = (tmp / "slate_receipt.json").read_bytes()
        slate_run(tmp, [role("J1"), role("J2", recommendation="WATCH", reasons=["100% onsite requirement; salary up 5%."])])
        assert_true((tmp / "slate_receipt.json").read_bytes() == before, "the slate receipt is deterministic")

        bad_cases = {
            "extra key": [role(fit_score="85")],
            "missing key": [{key: value for key, value in role().items() if key != "reasons"}],
            "bad recommendation": [role(recommendation="MAYBE")],
            "duplicate job id": [role("J1"), role("J1")],
            "empty array": [],
            "N/100 fit": [role(reasons=["82/100 fit"])],
            "fit score phrase": [role(reasons=["Strong fit score"])],
            "match score phrase": [role(reasons=["match score high"])],
            "score colon": [role(reasons=["Score: high"])],
            "fit percentage": [role(reasons=["85% fit for the role"])],
            "match percentage": [role(mandatory_gaps=["Overall match 90%"])],
            "letter grade fit": [role(reasons=["A fit"])],
            "fit grade": [role(reasons=["fit grade B+"])],
            "unknown geography not HOLD": [role(Geography_State="UNKNOWN", recommendation="PURSUE")],
            "unknown geography WATCH": [role(Geography_State="UNKNOWN", recommendation="WATCH")],
            "onsite with unknown location": [role(location_arrangement="Onsite, location unknown", recommendation="PURSUE")],
        }
        for label, roles in bad_cases.items():
            code, output = slate_run(tmp, roles)
            assert_true(code == run.EXIT_ERROR and failure(output)["code"] == "SLATE_INVALID", "slate rejects: " + label)
        code, output = slate_run(tmp, [role(Geography_State="UNKNOWN", recommendation="HOLD", location_arrangement="Onsite")])
        assert_true(code == 0, "unknown geography with HOLD is accepted: " + output)
        code, output = slate_run(tmp, [role(reasons=["Requires 100% onsite presence", "Salary band up 5%", "Credit Score Analyst scope matches evidence"])])
        assert_true(code == 0, "ordinary factual percentages and unrelated words are not fit scores: " + output)
    print("PASS: slate enforces exact keys, recommendation enum, no fit-score content, UNKNOWN onsite geography HOLD, and owned JOBS rows without Bora authority.")


# Preflight --------------------------------------------------------------------------------------

def make_runtime(tmp: Path) -> Path:
    root = tmp / "runtime"
    write(root / "RUNTIME_MANIFEST.json", {"spec": "CAREER_OS_RUNTIME_BUNDLE_V1", "canonical_main_sha": MAIN_SHA})
    write(root / "runtime_files.sha256", b"")
    return root


def test_preflight() -> None:
    real_fonts = cloud.verify_fonts
    cloud.verify_fonts = lambda root, font_dir: object()
    try:
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            root = make_runtime(tmp)
            adapter, config, runbook = write(tmp / "adapter.py", b"adapter"), write(tmp / "config.json", b"config"), write(tmp / "runbook.md", b"runbook")
            zip_sha = "c" * 64
            settings = {run.SETTINGS_CANONICAL_MAIN: MAIN_SHA, run.SETTINGS_RUNTIME_SHA: zip_sha, run.SETTINGS_ADAPTER_SHA: sha(b"adapter"),
                        run.SETTINGS_CONFIG_SHA: sha(b"config"), run.SETTINGS_RUNBOOK_SHA: sha(b"runbook"),
                        run.SETTINGS_PROFILE: "CHATGPT_CLOUD_OPERATIONAL_RENDER_V1"}

            def go(settings_value, expected=MAIN_SHA, runtime_zip=zip_sha, runbook_path=runbook) -> tuple:
                return invoke(["preflight", "--runtime-root", root, "--expected-main-sha", expected, "--font-dir", tmp / "fonts",
                               "--settings", write(tmp / "settings.json", settings_value), "--adapter", adapter, "--config", config,
                               "--runbook", runbook_path, "--runtime-zip-sha", runtime_zip, "--receipt", tmp / "preflight_receipt.json"])

            code, output = go(settings)
            receipt = json.loads((tmp / "preflight_receipt.json").read_text(encoding="utf-8"))
            assert_true(code == 0 and receipt["status"] == "PASS" and "RUN CONTRACT PREFLIGHT: PASS" in output and len(fenced_blocks(output)) == 1,
                        "a fully matching preflight passes: " + output)
            rows_form = [{"Key": key, "Value": value} for key, value in settings.items()]
            code, _ = go(rows_form)
            assert_true(code == 0, "SETTINGS Key/Value rows are accepted")

            mismatches = {
                "SETTINGS canonical main": dict(settings, **{run.SETTINGS_CANONICAL_MAIN: "b" * 40}),
                "SETTINGS runtime sha": dict(settings, **{run.SETTINGS_RUNTIME_SHA: "d" * 64}),
                "SETTINGS adapter sha": dict(settings, **{run.SETTINGS_ADAPTER_SHA: "e" * 64}),
                "SETTINGS config sha": dict(settings, **{run.SETTINGS_CONFIG_SHA: "f" * 64}),
                "SETTINGS runbook sha": dict(settings, **{run.SETTINGS_RUNBOOK_SHA: "0" * 64}),
                "cloud profile": dict(settings, **{run.SETTINGS_PROFILE: "OTHER_PROFILE"}),
                "missing SETTINGS key": {key: value for key, value in settings.items() if key != run.SETTINGS_ADAPTER_SHA},
            }
            for label, value in mismatches.items():
                code, output = go(value)
                receipt = json.loads((tmp / "preflight_receipt.json").read_text(encoding="utf-8"))
                assert_true(code == run.EXIT_STOP and receipt["status"] == "STOP" and "RUN CONTRACT PREFLIGHT: STOP" in output,
                            "preflight STOPs on identity mismatch: " + label)
                assert_true(failure(output)["code"] == "PREFLIGHT_STOP", "machine-readable failure for: " + label)
            code, output = go(settings, runtime_zip="1" * 64)
            assert_true(code == run.EXIT_STOP, "an observed runtime ZIP SHA that differs from SETTINGS STOPs")
            code, output = go(settings, expected="9" * 40)
            assert_true(code == run.EXIT_STOP and "RUNTIME_VERIFIED" in output, "an expected main that differs from the runtime manifest STOPs")
            code, output = go(settings, runbook_path=write(tmp / "runbook2.md", b"edited"))
            assert_true(code == run.EXIT_STOP, "an edited runbook STOPs")
            cloud.verify_fonts = real_fonts
            code, output = go(settings)
            assert_true(code == run.EXIT_STOP and "GOVERNED_FONTS_VERIFIED" in output, "a font verification failure STOPs")
    finally:
        cloud.verify_fonts = real_fonts
    print("PASS: preflight verifies runtime and fonts, compares SETTINGS to observed artifacts, and STOPs on any identity mismatch.")


# Package / verify-persisted / record-submit / closeout ----------------------------------------

JOB_ID = "JOB::FIXTURE::1"
COMPANY, ROLE, FOLDER = "J.Jill", "Data Analyst / BI", "J.Jill - Data Analyst"


def fake_run_request_factory(tmp: Path):
    def fake(request_path, runtime_root, font_dir, output_root, expected_main_sha):
        package = Path(output_root) / "PGP_V1_fixture"
        package.mkdir(parents=True)
        pdf, docx = b"%PDF-1.7 fixture", b"PK fixture docx"
        for name in handoff.PACKAGE_FILES:
            package.joinpath(name).write_bytes(b"{}\n")
        package.joinpath("resume.pdf").write_bytes(pdf)
        package.joinpath("resume.docx").write_bytes(docx)
        package.joinpath(handoff.REVIEW_FILE).write_bytes(json.dumps({"spec": handoff.REVIEW_SPEC, "rows": [
            {"location": "summary", "candidate_text": "text", "cited_claims": [{"claim_id": "C1", "approved_claim_wording": "wording"}]}]}).encode())
        manifest = {"artifacts": [{"role": "resume_docx", "sha256": sha(docx)}, {"role": "resume_pdf", "sha256": sha(pdf)}]}
        package.joinpath("manifest.json").write_bytes(json.dumps(manifest).encode())
        package.joinpath("cloud_operate_manifest.json").write_bytes(b"{}\n")
        inventory = handoff.package_persistence_inventory(package)
        package.joinpath(handoff.INVENTORY_FILE).write_bytes(json.dumps(inventory).encode())
        print("noise printed by run_request")
        return {"output_dir": str(package), "manifest": {"package_generation_id": "PGP_V1::fixture"}, "package_inventory": inventory}
    return fake


def make_request(tmp: Path) -> Path:
    return write(tmp / "request.json", {"job_id": JOB_ID, "jobs_rows": [{"Job_ID": JOB_ID, "Company": COMPANY, "Role": ROLE}]})


def package_args(tmp: Path, request: Path, company=COMPANY, role_name=ROLE) -> list:
    return ["package", "--request", request, "--runtime-root", tmp / "rt", "--font-dir", tmp / "fonts", "--output-root", tmp / "out",
            "--expected-main-sha", MAIN_SHA, "--company", company, "--role", role_name, "--target-folder-name", FOLDER]


def test_package_and_persist() -> None:
    real = cloud.run_request
    with tempfile.TemporaryDirectory() as raw:
        tmp = Path(raw)
        cloud.run_request = fake_run_request_factory(tmp)
        try:
            request = make_request(tmp)
            code, output = invoke(package_args(tmp, request, company="Other Co"))
            assert_true(code == run.EXIT_ERROR and failure(output)["code"] == "ROLE_IDENTITY_MISMATCH", "company/role must equal the JOBS row")
            code, output = invoke(package_args(tmp, request))
            assert_true(code == 0 and len(fenced_blocks(output)) == 1 and "UPLOAD THESE 3 FILES" in output and "CLAIM REVIEW TABLE" in output,
                        "package prints the claim table and the upload block in one fenced block: " + output)
            assert_true("noise printed by run_request" not in output, "adapter stdout does not leak into the operator block")
            persist = tmp / "out" / "persist"
            names = sorted(path.name for path in persist.iterdir())
            assert_true(names == sorted(["Bora_Chaush_J_Jill_Data_Analyst_BI_Resume.pdf", "Bora_Chaush_J_Jill_Data_Analyst_BI_Resume.docx", "package_bundle.zip"]),
                        "persist/ contains exactly the three sanitized files: %s" % names)
            plan_path = tmp / "out" / "persist_plan.json"
            plan = json.loads(plan_path.read_text(encoding="utf-8"))
            assert_true(plan_path.parent != persist and plan["job_id"] == JOB_ID and plan["target_folder_name"] == FOLDER, "the plan lives outside persist/ and names the job and folder")
            for item in plan["files"]:
                data = (persist / item["name"]).read_bytes()
                assert_true(item["byte_size"] == len(data) and item["sha256"] == sha(data), "plan size and SHA-256 match: " + item["name"])
            with zipfile.ZipFile(persist / "package_bundle.zip") as archive:
                members = archive.namelist()
            assert_true(handoff.INVENTORY_FILE in members and "cloud_operate_manifest.json" in members and "manifest.json" in members
                        and all(name.endswith(".json") for name in members), "the bundle holds every JSON artifact and no PDF/DOCX")
            first = (persist / "package_bundle.zip").read_bytes()
            assert_true(deterministic_zip_equal(persist), "the bundle bytes are deterministic")
            code, output = invoke(package_args(tmp, request))
            assert_true(code == run.EXIT_ERROR and failure(output)["code"] == "PERSIST_DIR_NOT_CLEAN", "a populated persist/ is never silently overwritten")
            assert_true(first == (persist / "package_bundle.zip").read_bytes(), "the refused rerun left the bundle untouched")

            # verify-persisted
            downloaded = tmp / "downloaded"
            shutil.copytree(persist, downloaded)
            verify = ["verify-persisted", "--plan", plan_path, "--downloaded-dir", downloaded, "--receipt", tmp / "out" / "persist_verified.json"]
            code, output = invoke(verify)
            assert_true(code == 0 and "PERSISTED_COMPLETE" in output and '"Package_Status": "READY"' in output and len(fenced_blocks(output)) == 1,
                        "exact readback emits PERSISTED_COMPLETE and Package_Status=READY: " + output)
            victim = downloaded / next(item["name"] for item in plan["files"] if item["role"] == "resume_docx")
            original = victim.read_bytes()
            victim.write_bytes(original + b"x")
            code, output = invoke(verify)
            assert_true(code == run.EXIT_ERROR and failure(output)["code"] == "PERSISTENCE_FAILED" and "PERSISTED_COMPLETE" not in output, "a hash mismatch fails")
            victim.write_bytes(original[:-1] + bytes([original[-1] ^ 1]))
            code, output = invoke(verify)
            assert_true(code == run.EXIT_ERROR, "a same-size hash mismatch fails")
            victim.write_bytes(original)
            victim.unlink()
            code, output = invoke(verify)
            assert_true(code == run.EXIT_ERROR and "missing" in failure(output)["detail"], "a missing file fails")
            victim.write_bytes(original)
            (downloaded / "extra.txt").write_bytes(b"extra")
            code, output = invoke(verify)
            assert_true(code == run.EXIT_ERROR and "extra.txt" in failure(output)["detail"], "an unexpected fourth file fails")
            (downloaded / "extra.txt").unlink()
            # unsupported gaps are never marked complete under the exact bundle shape
            inventory = handoff.persist_plan_inventory(plan)
            reported = {item["name"]: {"sha256": item["sha256"], "byte_size": item["byte_size"]} for item in plan["files"]}
            reported[plan["files"][1]["name"]] = {"status": handoff.UNSUPPORTED_BY_CONNECTOR, "reason": "connector rejects DOCX"}
            assert_true(handoff.verify_persisted(inventory, reported, exact=True)["status"] == "PERSISTENCE_FAILED", "an exact bundle has no recorded-gap success")
            assert_true(handoff.verify_persisted(inventory, {key: {"sha256": value["sha256"], "byte_size": value["byte_size"] + 1} for key, value in
                                                              {item["name"]: item for item in plan["files"]}.items()}, exact=True)["size_mismatch"],
                        "a size mismatch is reported")
            bad_plan = copy.deepcopy(plan)
            bad_plan["files"] = bad_plan["files"][:2]
            code, output = invoke(["verify-persisted", "--plan", write(tmp / "bad_plan.json", bad_plan), "--downloaded-dir", downloaded, "--receipt", tmp / "r.json"])
            assert_true(code == run.EXIT_ERROR and failure(output)["code"] == "PLAN_INVALID", "a plan that is not exactly three files is rejected")
            code, output = invoke(verify)
            assert_true(code == 0, "restored bytes verify again")
        finally:
            cloud.run_request = real
    print("PASS: package emits exactly three persist files plus an outside plan; verify-persisted is exact on names, sizes and SHA-256.")


def deterministic_zip_equal(persist: Path) -> bool:
    with zipfile.ZipFile(persist / "package_bundle.zip") as archive:
        members = {name: archive.read(name) for name in archive.namelist()}
    return run.deterministic_zip(members) == (persist / "package_bundle.zip").read_bytes()


def prepare_verified(tmp: Path) -> tuple:
    real = cloud.run_request
    cloud.run_request = fake_run_request_factory(tmp)
    try:
        request = make_request(tmp)
        assert_true(invoke(package_args(tmp, request))[0] == 0, "fixture package")
    finally:
        cloud.run_request = real
    plan_path = tmp / "out" / "persist_plan.json"
    downloaded = tmp / "downloaded"
    shutil.copytree(tmp / "out" / "persist", downloaded)
    receipt = tmp / "out" / "persist_verified.json"
    assert_true(invoke(["verify-persisted", "--plan", plan_path, "--downloaded-dir", downloaded, "--receipt", receipt])[0] == 0, "fixture verify")
    return plan_path, receipt


def test_record_submit() -> None:
    with tempfile.TemporaryDirectory() as raw:
        tmp = Path(raw)
        plan_path, persisted = prepare_verified(tmp)
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        pdf_sha = next(item["sha256"] for item in plan["files"] if item["role"] == "resume_pdf")
        base = ["record-submit", "--plan", plan_path, "--persist-receipt", persisted, "--job-id", JOB_ID, "--company", COMPANY, "--role", ROLE,
                "--channel", "Company careers site", "--applied-date", "2026-10-05", "--receipt", tmp / "submit_receipt.json"]
        code, output = invoke(base)
        assert_true(code == run.EXIT_ERROR and failure(output)["code"] == "ARGUMENT_ERROR", "neither --bora-confirmed nor --receipt-file is refused")
        proof = write(tmp / "confirmation.txt", b"Thank you for applying")
        code, output = invoke(base + ["--bora-confirmed", "--receipt-file", proof])
        assert_true(code == run.EXIT_ERROR and failure(output)["code"] == "ARGUMENT_ERROR", "both proofs together are refused")
        code, output = invoke(base + ["--bora-confirmed"])
        assert_true(code == 0 and len(fenced_blocks(output)) == 1, "Bora confirmation records the submission: " + output)
        receipt = json.loads((tmp / "submit_receipt.json").read_text(encoding="utf-8"))
        application = receipt["applications_row"]
        assert_true(application["Resume_SHA256"] == pdf_sha, "the resume PDF SHA is derived from the plan")
        assert_true(application["Submission_Evidence"] == "BORA_CONFIRMED_NO_SEPARATE_RECEIPT_ARTIFACT" and application["Submission_Receipt_SHA256"] is None,
                    "Bora confirmation records that no separate receipt artifact exists")
        assert_true(receipt["jobs_row"] == {"Job_ID": JOB_ID, "Application_Status": "SUBMITTED"} and receipt["log_row"]["Stage"] == "APPLICATION_RECORDED",
                    "APPLICATIONS/JOBS/LOG row values are emitted")
        code, output = invoke(base + ["--receipt-file", proof])
        receipt = json.loads((tmp / "submit_receipt.json").read_text(encoding="utf-8"))
        assert_true(code == 0 and receipt["applications_row"]["Submission_Receipt_SHA256"] == sha(b"Thank you for applying")
                    and receipt["applications_row"]["Submission_Evidence"] == "RECEIPT_FILE", "a receipt file contributes its SHA-256")
        code, output = invoke(base + ["--receipt-file", tmp / "missing.txt"])
        assert_true(code == run.EXIT_ERROR and failure(output)["code"] == "INPUT_UNREADABLE", "a missing receipt file fails")
        code, output = invoke(base + ["--receipt-file", write(tmp / "empty.txt", b"")])
        assert_true(code == run.EXIT_ERROR and failure(output)["code"] == "SUBMISSION_RECEIPT_EMPTY", "an empty receipt file fails")
        wrong = list(base)
        wrong[wrong.index("--company") + 1] = "Other Co"
        code, output = invoke(wrong + ["--bora-confirmed"])
        assert_true(code == run.EXIT_ERROR and failure(output)["code"] == "PLAN_IDENTITY_MISMATCH", "explicit identity must equal the plan")
        bad_date = list(base)
        bad_date[bad_date.index("--applied-date") + 1] = "10/05/2026"
        assert_true(failure(invoke(bad_date + ["--bora-confirmed"])[1])["code"] == "APPLIED_DATE_INVALID", "applied date must be ISO")
        broken = json.loads(persisted.read_text(encoding="utf-8"))
        broken["status"] = "PERSISTENCE_FAILED"
        swapped = list(base)
        swapped[swapped.index("--persist-receipt") + 1] = write(tmp / "broken_receipt.json", broken)
        assert_true(failure(invoke(swapped + ["--bora-confirmed"])[1])["code"] == "PERSISTENCE_NOT_VERIFIED",
                    "recording is refused without a PERSISTED_COMPLETE receipt bound to the plan")
    print("PASS: record-submit requires exactly one of --bora-confirmed / --receipt-file, a verified persistence receipt, and derives the PDF SHA from the plan.")


def test_closeout() -> None:
    with tempfile.TemporaryDirectory() as raw:
        tmp = Path(raw)
        pdf_sha = "7" * 64
        plan = {"spec": run.PLAN_SPEC, "job_id": "S1", "company": "A", "role": "B", "target_folder_name": "Folder S1",
                "files": [{"role": "resume_pdf", "name": "a.pdf", "byte_size": 1, "sha256": pdf_sha},
                          {"role": "resume_docx", "name": "a.docx", "byte_size": 1, "sha256": "8" * 64},
                          {"role": "package_bundle", "name": "package_bundle.zip", "byte_size": 1, "sha256": "9" * 64}]}
        batch = [{"job_id": "S1"}, {"job_id": "P1"}, {"job_id": "H1", "target_folder_name": "Historical"}, {"job_id": "W1"}]
        jobs = [{"Job_ID": "S1", "Bora_Decision": "PURSUE", "Application_Status": "SUBMITTED"},
                {"Job_ID": "P1", "Bora_Decision": "PURSUE", "Package_Status": "READY"},
                {"Job_ID": "H1", "Decision": "PURSUE", "Application_Status": "SUBMITTED"},
                {"Job_ID": "W1", "Decision": "WATCH"}]
        ledger = {"JOBS": jobs, "APPLICATIONS": [{"Job_ID": "S1", "Resume_SHA256": pdf_sha}, {"Job_ID": "H1", "Resume_SHA256": "whatever"}]}
        folders = {"Folder S1": ["a.pdf"], "Historical": [{"name": "old.pdf"}]}

        def go(batch_value=batch, ledger_value=ledger, folders_value=folders, plans=(plan,)) -> tuple:
            return invoke(["closeout", "--batch", write(tmp / "batch.json", batch_value), "--ledger", write(tmp / "ledger.json", ledger_value),
                           "--folders", write(tmp / "folders.json", folders_value), "--plans", write(tmp / "plans.json", list(plans)),
                           "--receipt", tmp / "closeout_receipt.json"])

        code, output = go()
        assert_true(code == 0 and output.strip().splitlines()[-1] == "CAREER_OS_RUN_CLOSEOUT: COMPLETE" and len(fenced_blocks(output)) == 1,
                    "a fully durable batch (including a historical no-plan submission) is COMPLETE: " + output)

        def incomplete(label, expected, **kwargs) -> None:
            code, output = go(**kwargs)
            assert_true(code == run.EXIT_STOP and output.strip().splitlines()[-1] == "CAREER_OS_RUN_CLOSEOUT: INCOMPLETE", "INCOMPLETE: " + label)
            assert_true(expected in output, "%s names %s: %s" % (label, expected, output))

        incomplete("role without a JOBS row", "X9: JOBS_ROW_MISSING", batch_value=batch + [{"job_id": "X9"}])
        incomplete("JOBS row without durable state", "E1: JOBS_DURABLE_STATE_MISSING", batch_value=batch + [{"job_id": "E1"}],
                   ledger_value={**ledger, "JOBS": jobs + [{"Job_ID": "E1"}]})
        incomplete("PURSUE not persisted", "P1: PURSUE_PACKAGE_NOT_PERSISTED_COMPLETE",
                   ledger_value={**ledger, "JOBS": [dict(row, Package_Status=None) if row["Job_ID"] == "P1" else row for row in jobs]})
        incomplete("submitted without APPLICATIONS row", "S1: APPLICATIONS_ROW_MISSING", ledger_value={**ledger, "APPLICATIONS": [ledger["APPLICATIONS"][1]]})
        incomplete("submitted with empty folder", "S1: ROLE_FOLDER_MISSING_OR_EMPTY", folders_value={"Folder S1": [], "Historical": ["old.pdf"]})
        incomplete("historical role with empty folder", "H1: ROLE_FOLDER_MISSING_OR_EMPTY", folders_value={"Folder S1": ["a.pdf"], "Historical": []})
        incomplete("APPLICATIONS SHA differs from plan", "S1: APPLICATIONS_RESUME_SHA_MISMATCH_WITH_PLAN",
                   ledger_value={**ledger, "APPLICATIONS": [{"Job_ID": "S1", "Resume_SHA256": "6" * 64}, ledger["APPLICATIONS"][1]]})
        incomplete("historical role without APPLICATIONS row", "H1: APPLICATIONS_ROW_MISSING", ledger_value={**ledger, "APPLICATIONS": [ledger["APPLICATIONS"][0]]})
        receipt = json.loads((tmp / "closeout_receipt.json").read_text(encoding="utf-8"))
        assert_true(receipt["status"] == "INCOMPLETE" and receipt["missing"] == ["H1: APPLICATIONS_ROW_MISSING"], "the receipt records deterministic missing items")
        code, output = invoke(["closeout", "--batch", write(tmp / "b.json", {}), "--ledger", tmp / "ledger.json", "--folders", tmp / "folders.json", "--receipt", tmp / "r.json"])
        assert_true(code == run.EXIT_ERROR and failure(output)["code"] == "BATCH_INVALID", "a malformed batch is a failure block")
    print("PASS: closeout is COMPLETE only when every role is durable, persisted, recorded and folder-backed, with the exact final status line.")


def test_module_is_local_only() -> None:
    source = (ROOT / "src" / "career_os_run_v1.py").read_text(encoding="utf-8")
    for forbidden in ("import requests", "urllib", "http.client", "googleapiclient", "socket", "subprocess", "smtplib"):
        assert_true(forbidden not in source, "the run CLI contains no network or process call: " + forbidden)
    print("PASS: the run CLI is pure and local.")


def main() -> None:
    tests = [test_slate, test_preflight, test_package_and_persist, test_record_submit, test_closeout, test_module_is_local_only]
    for test in tests:
        test()
    print("PASS: %d groups of career_os_run_contract_cli_v1_test" % len(tests))


if __name__ == "__main__":
    main()
