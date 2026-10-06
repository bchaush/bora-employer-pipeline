"""Live-shape regression tests for CAREER_OS_RUN_CONTRACT_V1_2 (V1_1 behaviour plus readback, decide, pursuit-state, slate dates).

Fixtures use the exact Production Ledger headers:
- JOBS: 20 columns
- APPLICATIONS: 10 columns
- LOG: 9 columns

All tests are local-only. Cloud rendering/font verification are stubbed only where a real renderer is irrelevant.
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
JOB_ID = "FIXTURE::DATA-ANALYST"
COMPANY = "Fixture Co"
ROLE = "Data Analyst"
URL = "https://careers.example/jobs/fixture-data-analyst"
FOLDER = "2026-10-05 — Fixture Co — Data Analyst"
AS_OF = "2026-10-06T09:40:00-04:00"


def assert_true(condition, message):
    if not condition:
        print("FAIL: " + message)
        raise SystemExit(1)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write(path: Path, value) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(value if isinstance(value, bytes) else json.dumps(value, sort_keys=True).encode("utf-8"))
    return path


def invoke(argv):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = run.main([str(x) for x in argv])
    return code, out.getvalue()


def failure(output):
    rows = [line for line in output.splitlines() if line.startswith(run.FAILURE_MARKER)]
    assert_true(len(rows) == 1, "exactly one failure row")
    return json.loads(rows[0][len(run.FAILURE_MARKER):])


def blank(headers):
    return {key: "" for key in headers}


def job_row(job_id=JOB_ID, company=COMPANY, role=ROLE, official_url=URL, **overrides):
    row = blank(run.JOBS_HEADERS)
    row.update({"Job_ID": job_id, "Company": company, "Role": role, "Discovery_Source": "MANUAL_URL",
                "Discovery_URL": official_url, "Official_URL": official_url, "Pipeline_State": "REVIEW_READY",
                "Freshness_State": "PASS", "Geography_State": "PASS", "OPT_Screen_State": "PASS",
                "Candidate_Condition_State": "PASS", "Threshold_State": "PASS", "Role_Status": "VERIFIED_LIVE",
                "Match_State": "ANALYZED", "Decision": "PURSUE", "Bora_Decision": "", "Package_Status": "",
                "Application_Status": ""})
    row.update(overrides)
    return row


def app_row(job_id=JOB_ID, resume_version="", **overrides):
    row = blank(run.APPLICATIONS_HEADERS)
    row.update({"Application_ID": "APP::%s::2026-10-05" % job_id, "Job_ID": job_id, "Applied_Date": "2026-10-05",
                "Resume_Version": resume_version, "Cover_Letter_Version": "NONE", "Channel": "Company careers",
                "Current_Status": "SUBMITTED", "Last_Update": "2026-10-05",
                "Next_Action": "Monitor for employer response", "Outcome": "Bora confirmed; no separate receipt"})
    row.update(overrides)
    return row


def log_row(job_id=JOB_ID, **overrides):
    row = blank(run.LOG_HEADERS)
    row.update({"Run_ID": "RUN::1", "Timestamp": "2026-10-05", "Stage": "APPLICATION_RECORDED",
                "Source": "CAREER_OS_RUN_V1", "Job_ID": job_id, "Status": "SUBMITTED",
                "Error_Code": "", "Engine_Baseline": "", "Notes": "fixture"})
    row.update(overrides)
    return row


def ledger(jobs=None, applications=None, logs=None):
    return {"JOBS": list(jobs or []), "APPLICATIONS": list(applications or []), "LOG": list(logs or [])}


def role(job_id=JOB_ID, official_url=URL, **overrides):
    value = {"job_id": job_id, "company": COMPANY, "role": ROLE, "official_url": official_url, "source": "MANUAL_URL",
             "location_arrangement": "Remote", "Geography_State": "PASS", "work_authorization_text": "No sponsorship language stated.",
             "OPT_Screen_State": "HUMAN_REQUIRED", "mandatory_gaps": [], "recommendation": "PURSUE",
             "reasons": ["Requirements align with approved evidence."]}
    value.update(overrides)
    return value


def run_slate(tmp, roles, ledger_value):
    return invoke(["slate", "--screening", write(tmp/"screening.json", roles),
                   "--ledger", write(tmp/"ledger.json", ledger_value),
                   "--as-of", AS_OF, "--receipt", tmp/"slate.json"])


def make_runtime(tmp):
    root = tmp/"runtime"
    write(root/"RUNTIME_MANIFEST.json", {"spec":"CAREER_OS_RUNTIME_BUNDLE_V1","canonical_main_sha":MAIN_SHA})
    write(root/"runtime_files.sha256", b"")
    return root


def test_preflight_live_settings():
    real_fonts = cloud.verify_fonts
    cloud.verify_fonts = lambda root, font_dir: object()
    try:
        with tempfile.TemporaryDirectory() as raw:
            tmp=Path(raw)
            root=make_runtime(tmp)
            runtime_zip=write(tmp/"runtime.zip", b"runtime-zip")
            fonts_zip=write(tmp/"fonts.zip", b"fonts-zip")
            adapter=write(tmp/"adapter.py", b"adapter")
            config=write(tmp/"config.json", b"config")
            runbook=write(tmp/"runbook.md", b"runbook")
            settings={
                "CANONICAL_MAIN_SHA":MAIN_SHA,
                "RUNTIME_BUNDLE_SHA256":sha(b"runtime-zip"),
                "CLOUD_ADAPTER_SHA256":sha(b"adapter"),
                "OPERATE_MODE_CONFIG_SHA256":sha(b"config"),
                "OPERATE_MODE_RUNBOOK_SHA256":sha(b"runbook"),
                "GOVERNED_FONTS_SHA256":sha(b"fonts-zip"),
                "CLOUD_RENDER_PROFILE":"CHATGPT_CLOUD_OPERATIONAL_RENDER_V1",
            }
            def go(value=settings, rz=runtime_zip, fz=fonts_zip):
                return invoke(["preflight","--runtime-root",root,"--expected-main-sha",MAIN_SHA,"--font-dir",tmp/"fonts",
                               "--settings",write(tmp/"settings.json",value),"--adapter",adapter,"--config",config,"--runbook",runbook,
                               "--runtime-zip",rz,"--fonts-zip",fz,"--receipt",tmp/"preflight.json"])
            code,out=go()
            assert_true(code==0 and "RUN CONTRACT PREFLIGHT: PASS" in out,"live-key preflight passes")
            for key in settings:
                bad=dict(settings); bad[key]="0"*64 if key!="CLOUD_RENDER_PROFILE" else "OTHER"
                code,_=go(bad)
                assert_true(code==run.EXIT_STOP,"preflight stops on "+key)
            code,_=go(rz=write(tmp/"runtime-tampered.zip",b"tampered"))
            assert_true(code==run.EXIT_STOP,"runtime zip bytes are actually hashed")
            code,_=go(fz=write(tmp/"fonts-tampered.zip",b"tampered-fonts"))
            assert_true(code==run.EXIT_STOP,"fonts zip bytes are actually hashed")
            missing=dict(settings); missing.pop("CLOUD_RENDER_PROFILE")
            assert_true(go(missing)[0]==run.EXIT_STOP,"render profile is required")
    finally:
        cloud.verify_fonts=real_fonts
    print("PASS: preflight uses live SETTINGS keys and hashes actual runtime/fonts ZIP bytes.")


def test_slate_dedupe_and_score_rules():
    with tempfile.TemporaryDirectory() as raw:
        tmp=Path(raw)
        existing=job_row(Bora_Decision="PURSUE",Package_Status="READY",Application_Status="SUBMITTED")
        code,out=run_slate(tmp,[role()],ledger([existing]))
        assert_true(code==0 and "ALREADY_TRACKED" in out,"existing Job_ID dedupes")
        receipt=json.loads((tmp/"slate.json").read_text())
        assert_true(receipt["jobs_rows"]==[] and receipt["slate"][0]["tracking_status"]=="ALREADY_TRACKED","no duplicate JOBS row")
        other=job_row(job_id="OTHER",official_url=URL)
        code,_=run_slate(tmp,[role()],ledger([other]))
        assert_true(code==0 and json.loads((tmp/"slate.json").read_text())["slate"][0]["tracking_status"]=="ALREADY_TRACKED","Official_URL dedupes")
        code,_=run_slate(tmp,[role(reasons=["82/100 fit"])],ledger())
        assert_true(code==run.EXIT_ERROR,"fit score rejected")
        code,_=run_slate(tmp,[role(reasons=["Requires 100% onsite attendance"])],ledger())
        assert_true(code==0,"factual percentage accepted")
        code,_=run_slate(tmp,[role(Geography_State="UNKNOWN",location_arrangement="Onsite, location unknown",recommendation="PURSUE")],ledger())
        assert_true(code==run.EXIT_ERROR,"unknown onsite requires HOLD")
        code,_=run_slate(tmp,[role(Geography_State="UNKNOWN",location_arrangement="Onsite",recommendation="HOLD")],ledger())
        assert_true(code==0,"unknown onsite HOLD accepted")
        row=json.loads((tmp/"slate.json").read_text())["jobs_rows"][0]
        assert_true(set(row)==set(run.JOBS_HEADERS) and row["Bora_Decision"] is None,"new JOBS output uses exact 20 live headers")
        assert_true(row["First_Seen"]==AS_OF and row["Last_Verified"]==AS_OF,"slate stamps First_Seen and Last_Verified with --as-of")
        for bad in ("2026-10-06","2026-10-06T09:40:00",""):
            code,out=invoke(["slate","--screening",tmp/"screening.json","--ledger",tmp/"ledger.json","--as-of",bad,"--receipt",tmp/"s2.json"])
            assert_true(code==run.EXIT_ERROR and failure(out)["code"]=="TIMESTAMP_INVALID","slate refuses --as-of without a UTC offset: %r"%bad)
    print("PASS: slate dedupes from Ledger and preserves fit/HOLD boundaries.")


SEEN_REQUESTS=[]


def fake_run_request(request_path, runtime_root, font_dir, output_root, expected_main_sha):
    SEEN_REQUESTS.append(json.loads(Path(request_path).read_text(encoding="utf-8")))
    package=Path(output_root)/"PGP_fixture"; package.mkdir(parents=True,exist_ok=True)
    for name in handoff.PACKAGE_FILES: package.joinpath(name).write_bytes(b"{}\n")
    package.joinpath("resume.pdf").write_bytes(b"%PDF fixture")
    package.joinpath("resume.docx").write_bytes(b"PK docx")
    package.joinpath(handoff.REVIEW_FILE).write_text(json.dumps({"spec":handoff.REVIEW_SPEC,"rows":[]}),encoding="utf-8")
    package.joinpath("manifest.json").write_text(json.dumps({"artifacts":[]}),encoding="utf-8")
    package.joinpath("cloud_operate_manifest.json").write_text("{}",encoding="utf-8")
    inventory=handoff.package_persistence_inventory(package)
    package.joinpath(handoff.INVENTORY_FILE).write_text(json.dumps(inventory),encoding="utf-8")
    return {"output_dir":str(package),"manifest":{"package_generation_id":"PGP_fixture"},"package_inventory":inventory}


def request_file(tmp, official_url=URL):
    row=job_row(official_url=official_url)
    return write(tmp/"request.json",{"job_id":JOB_ID,"jobs_rows":[row]})


def package_argv(tmp, request, ledger_path):
    return ["package","--request",request,"--ledger",ledger_path,"--runtime-root",tmp/"runtime","--font-dir",tmp/"fonts",
            "--output-root",tmp/"out","--expected-main-sha",MAIN_SHA,"--company",COMPANY,"--role",ROLE,
            "--target-folder-name",FOLDER]


def test_package_ledger_binding_and_persistence():
    real=cloud.run_request; cloud.run_request=fake_run_request
    try:
        with tempfile.TemporaryDirectory() as raw:
            tmp=Path(raw)
            good_ledger=write(tmp/"ledger.json",ledger([job_row()]))
            SEEN_REQUESTS.clear()
            good_ledger=write(tmp/"ledger.json",ledger([job_row(),job_row(job_id="OTHER")],[],[log_row()]))
            code,out=invoke(package_argv(tmp,request_file(tmp),good_ledger))
            assert_true(code==0 and "UPLOAD THESE 3 FILES" in out,"package passes with exact Ledger identity")
            seen=SEEN_REQUESTS[-1]
            assert_true(seen["jobs_rows"]==[job_row()] and seen["decision_log_rows"]==[log_row()],
                        "the pursuit gate receives the live JOBS row and LOG rows from the same Ledger file")
            persist=tmp/"out"/"persist"
            assert_true(sorted(p.name for p in persist.iterdir())==sorted(["Bora_Chaush_Fixture_Co_Data_Analyst_Resume.pdf",
                                                                          "Bora_Chaush_Fixture_Co_Data_Analyst_Resume.docx",
                                                                          "package_bundle.zip"]),"exactly three persist files")
            plan=tmp/"out"/"persist_plan.json"
            downloaded=tmp/"downloaded"; shutil.copytree(persist,downloaded)
            verify=tmp/"verify.json"
            code,_=invoke(["verify-persisted","--plan",plan,"--downloaded-dir",downloaded,"--receipt",verify])
            assert_true(code==0,"exact readback verifies")
            (downloaded/"package_bundle.zip").write_bytes(b"tamper")
            assert_true(invoke(["verify-persisted","--plan",plan,"--downloaded-dir",downloaded,"--receipt",verify])[0]!=0,"tamper fails")
        with tempfile.TemporaryDirectory() as raw:
            tmp=Path(raw)
            missing=job_row(official_url="")
            code,out=invoke(package_argv(tmp,request_file(tmp),write(tmp/"ledger.json",ledger([missing]))))
            assert_true(code==run.EXIT_ERROR and failure(out)["code"]=="OFFICIAL_URL_MISSING_IN_LEDGER","blank live Official_URL fails")
        with tempfile.TemporaryDirectory() as raw:
            tmp=Path(raw)
            mismatched=job_row(official_url="https://careers.example/other")
            code,out=invoke(package_argv(tmp,request_file(tmp),write(tmp/"ledger.json",ledger([mismatched]))))
            assert_true(code==run.EXIT_ERROR and failure(out)["code"]=="REQUEST_LEDGER_IDENTITY_MISMATCH","request/Ledger identity mismatch fails")
    finally:
        cloud.run_request=real
    print("PASS: package is Ledger-bound; persistence is exact three-file hash verification.")


def test_record_submit_live_shapes():
    real=cloud.run_request; cloud.run_request=fake_run_request
    try:
        with tempfile.TemporaryDirectory() as raw:
            tmp=Path(raw)
            led=write(tmp/"ledger.json",ledger([job_row()]))
            assert_true(invoke(package_argv(tmp,request_file(tmp),led))[0]==0,"fixture package")
            plan=tmp/"out"/"persist_plan.json"
            downloaded=tmp/"downloaded"; shutil.copytree(tmp/"out"/"persist",downloaded)
            verified=tmp/"verify.json"
            assert_true(invoke(["verify-persisted","--plan",plan,"--downloaded-dir",downloaded,"--receipt",verified])[0]==0,"fixture persisted")
            submit=tmp/"submit.json"
            argv=["record-submit","--plan",plan,"--persist-receipt",verified,"--job-id",JOB_ID,"--company",COMPANY,"--role",ROLE,
                  "--channel","Company careers","--applied-date","2026-10-05","--bora-confirmed","--receipt",submit]
            assert_true(invoke(argv)[0]==0,"record-submit succeeds")
            rec=json.loads(submit.read_text())
            app=rec["applications_row"]; log=rec["log_row"]
            assert_true(set(app)==set(run.APPLICATIONS_HEADERS) and len(app)==10,"APPLICATIONS output exact 10 live columns")
            assert_true(set(log)==set(run.LOG_HEADERS) and len(log)==9,"LOG output exact 9 live columns")
            pdf=next(x for x in json.loads(plan.read_text())["files"] if x["role"]=="resume_pdf")
            assert_true(app["Application_ID"]=="APP::%s::2026-10-05"%JOB_ID,"Application_ID format")
            assert_true(app["Resume_Version"]=="%s | sha256:%s"%(pdf["name"],pdf["sha256"]),"Resume_Version embeds plan SHA")
            assert_true(app["Cover_Letter_Version"]=="NONE" and app["Next_Action"]=="Monitor for employer response","live application defaults")
            assert_true(rec["jobs_row"]=={"Job_ID":JOB_ID,"Application_Status":"SUBMITTED"},"JOBS write only Application_Status")
    finally:
        cloud.run_request=real
    print("PASS: record-submit emits exact live APPLICATIONS/LOG shapes and plan-derived resume hash.")


def test_closeout_slate_authority_and_sha_parse():
    with tempfile.TemporaryDirectory() as raw:
        tmp=Path(raw)
        pdf_sha="7"*64
        plan={"spec":run.PLAN_SPEC,"job_id":JOB_ID,"company":COMPANY,"role":ROLE,"target_folder_name":FOLDER,
              "files":[{"role":"resume_pdf","name":"resume.pdf","byte_size":1,"sha256":pdf_sha},
                       {"role":"resume_docx","name":"resume.docx","byte_size":1,"sha256":"8"*64},
                       {"role":"package_bundle","name":"package_bundle.zip","byte_size":1,"sha256":"9"*64}]}
        slate={"spec":"CAREER_OS_RUN_SLATE_RECEIPT_V1","slate":[{"job_id":JOB_ID,"tracking_status":"NEW"}]}
        jobs=job_row(Bora_Decision="PURSUE",Package_Status="READY",Application_Status="SUBMITTED")
        apps=app_row(resume_version="resume.pdf | sha256:"+pdf_sha)
        led=ledger([jobs],[apps],[log_row()])
        args=["closeout","--slate-receipt",write(tmp/"slate.json",slate),"--ledger",write(tmp/"ledger.json",led),
              "--folders",write(tmp/"folders.json",{JOB_ID:["resume.pdf"]}),"--plans",write(tmp/"plans.json",[plan]),
              "--receipt",tmp/"closeout.json"]
        code,out=invoke(args)
        assert_true(code==0 and out.strip().endswith("CAREER_OS_RUN_CLOSEOUT: COMPLETE"),"bare SHA parsed from Resume_Version")
        code,out=invoke(["closeout","--slate-receipt",tmp/"slate.json","--ledger",tmp/"ledger.json",
                         "--folders",tmp/"folders.json","--plans",write(tmp/"none.json",[]),"--receipt",tmp/"closeout2.json"])
        assert_true(code==run.EXIT_STOP and "PLAN_NOT_SUPPLIED" in out,"new submitted role without plan is incomplete")
        tracked={"spec":"CAREER_OS_RUN_SLATE_RECEIPT_V1","slate":[{"job_id":JOB_ID,"tracking_status":"ALREADY_TRACKED","tracked_job_id":JOB_ID}]}
        code,out=invoke(["closeout","--slate-receipt",write(tmp/"tracked.json",tracked),"--ledger",tmp/"ledger.json",
                         "--folders",tmp/"folders.json","--plans",tmp/"none.json","--receipt",tmp/"closeout3.json"])
        assert_true(code==0,"historical already-tracked submitted role may close without plan when app+folder are durable")
    print("PASS: closeout is slate-authoritative, parses Resume_Version SHA, and never silently skips a required new-role plan.")


def test_end_to_end_live_shapes():
    real_run=cloud.run_request
    real_fonts=cloud.verify_fonts
    cloud.run_request=fake_run_request
    cloud.verify_fonts=lambda root,font_dir: object()
    try:
        with tempfile.TemporaryDirectory() as raw:
            tmp=Path(raw)
            root=make_runtime(tmp)
            runtime_zip=write(tmp/"runtime.zip",b"runtime")
            fonts_zip=write(tmp/"fonts.zip",b"fonts")
            adapter=write(tmp/"adapter.py",b"adapter"); config=write(tmp/"config.json",b"config"); runbook=write(tmp/"runbook.md",b"runbook")
            settings={"CANONICAL_MAIN_SHA":MAIN_SHA,"RUNTIME_BUNDLE_SHA256":sha(b"runtime"),"CLOUD_ADAPTER_SHA256":sha(b"adapter"),
                      "OPERATE_MODE_CONFIG_SHA256":sha(b"config"),"OPERATE_MODE_RUNBOOK_SHA256":sha(b"runbook"),
                      "GOVERNED_FONTS_SHA256":sha(b"fonts"),"CLOUD_RENDER_PROFILE":"CHATGPT_CLOUD_OPERATIONAL_RENDER_V1"}
            assert_true(invoke(["preflight","--runtime-root",root,"--expected-main-sha",MAIN_SHA,"--font-dir",tmp/"fonts",
                                "--settings",write(tmp/"settings.json",settings),"--adapter",adapter,"--config",config,"--runbook",runbook,
                                "--runtime-zip",runtime_zip,"--fonts-zip",fonts_zip,"--receipt",tmp/"preflight.json"])[0]==0,"e2e preflight")
            empty=ledger()
            assert_true(run_slate(tmp,[role()],empty)[0]==0,"e2e slate")
            slate_receipt=tmp/"slate.json"
            live_job=job_row(Bora_Decision="PURSUE")
            live_ledger=write(tmp/"ledger-live.json",ledger([live_job]))
            assert_true(invoke(package_argv(tmp,request_file(tmp),live_ledger))[0]==0,"e2e package")
            plan=tmp/"out"/"persist_plan.json"
            downloaded=tmp/"downloaded"; shutil.copytree(tmp/"out"/"persist",downloaded)
            verified=tmp/"verified.json"
            assert_true(invoke(["verify-persisted","--plan",plan,"--downloaded-dir",downloaded,"--receipt",verified])[0]==0,"e2e persist")
            submit=tmp/"submit.json"
            assert_true(invoke(["record-submit","--plan",plan,"--persist-receipt",verified,"--job-id",JOB_ID,"--company",COMPANY,"--role",ROLE,
                                "--channel","Company careers","--applied-date","2026-10-05","--bora-confirmed","--receipt",submit])[0]==0,"e2e record")
            rec=json.loads(submit.read_text())
            final_job=copy.deepcopy(live_job); final_job.update(rec["jobs_row"]); final_job["Package_Status"]="READY"
            final_ledger=ledger([final_job],[rec["applications_row"]],[rec["log_row"]])
            code,out=invoke(["closeout","--slate-receipt",slate_receipt,"--ledger",write(tmp/"final-ledger.json",final_ledger),
                             "--folders",write(tmp/"folders.json",{JOB_ID:["resume.pdf","resume.docx","package_bundle.zip"]}),
                             "--plans",write(tmp/"plans.json",[json.loads(plan.read_text())]),"--receipt",tmp/"closeout.json"])
            assert_true(code==0 and out.strip().endswith("CAREER_OS_RUN_CLOSEOUT: COMPLETE"),"live-shape end-to-end closes COMPLETE")
    finally:
        cloud.run_request=real_run
        cloud.verify_fonts=real_fonts
    print("PASS: preflight -> slate -> package -> verify -> record-submit -> closeout works end-to-end on exact live shapes.")


def raw_values(led, network=None):
    raw={name:[list(headers)]+[[row[h] for h in headers] for row in led[name]]
         for name,headers in (("JOBS",run.JOBS_HEADERS),("APPLICATIONS",run.APPLICATIONS_HEADERS),("LOG",run.LOG_HEADERS))}
    if network is not None:
        raw["NETWORK"]=[list(run.NETWORK_HEADERS)]+network
    return raw


def readback(tmp, raw, name="ledger-rb.json"):
    return invoke(["readback","--raw",write(tmp/"raw.json",raw),"--out",tmp/name,"--receipt",tmp/"readback.json"])


def test_readback_normalizes_sheet_values():
    with tempfile.TemporaryDirectory() as raw_dir:
        tmp=Path(raw_dir)
        led=ledger([job_row()],[app_row()],[log_row()])
        raw=raw_values(led,network=[])
        # What a Sheets read really returns: trailing blank cells dropped, blank cells as null, padded header, empty rows.
        raw["JOBS"][0]=raw["JOBS"][0]+["",""]
        raw["JOBS"][1]=[cell if cell!="" else None for cell in raw["JOBS"][1]]
        while raw["JOBS"][1] and raw["JOBS"][1][-1] in ("",None):
            raw["JOBS"][1].pop()
        raw["JOBS"].append([])
        raw["LOG"].append(["","",""])
        code,out=readback(tmp,raw)
        assert_true(code==0 and "LEDGER FILE READY" in out,"readback builds the Ledger file: "+out)
        built=json.loads((tmp/"ledger-rb.json").read_text())
        assert_true(built["JOBS"]==[job_row()] and built["APPLICATIONS"]==[app_row()] and built["LOG"]==[log_row()],
                    "short rows are padded, nulls become \"\", blank rows are skipped")
        assert_true(built["NETWORK"]==[] and "JOBS rows=1 blank_rows_skipped=1" in out,"NETWORK header-only tab and counts")
        assert_true(run.load_ledger(str(tmp/"ledger-rb.json"))["JOBS"][0]==job_row(),"output satisfies the strict Ledger loader")
        import career_os_network_v1 as net
        assert_true(net.load_ledger_with_network(str(tmp/"ledger-rb.json"))["NETWORK"]==[],"network commands accept it")
        cases=[]
        bad=raw_values(led); bad["JOBS"][0][3]="Source"; cases.append((bad,"READBACK_HEADER_MISMATCH"))
        bad=raw_values(led); bad["APPLICATIONS"][1][2]=20261005; cases.append((bad,"READBACK_CELL_TYPE"))
        bad=raw_values(led); bad["LOG"][1]=bad["LOG"][1]+["stray"]; cases.append((bad,"READBACK_ROW_TOO_LONG"))
        bad=raw_values(led); del bad["LOG"]; cases.append((bad,"READBACK_INVALID"))
        bad=raw_values(led); bad["SETTINGS"]=[["Key"]]; cases.append((bad,"READBACK_INVALID"))
        bad=raw_values(ledger([job_row(),job_row()])); cases.append((bad,"READBACK_DUPLICATE_JOB_ID"))
        for value,expected in cases:
            code,out=readback(tmp,value,"bad.json")
            assert_true(code==run.EXIT_ERROR and failure(out)["code"]==expected,"readback fails closed with "+expected)
    print("PASS: readback turns raw Sheets values into the exact Ledger file and fails closed on anything ambiguous.")


def test_decide_and_pursuit_state():
    with tempfile.TemporaryDirectory() as raw_dir:
        tmp=Path(raw_dir)
        new_job=job_row(Last_Verified="",Freshness_State="",Candidate_Condition_State="",Threshold_State="",Role_Status="",
                        First_Seen=AS_OF)
        led=ledger([new_job],[],[log_row()])
        assert_true(readback(tmp,raw_values(led))[0]==0,"readback")
        path=tmp/"ledger-rb.json"

        def state():
            code,out=invoke(["pursuit-state","--ledger",path,"--job-id",JOB_ID,"--receipt",tmp/"state.json"])
            assert_true(code==0,"pursuit-state runs: "+out)
            return json.loads((tmp/"state.json").read_text())

        def decide(decision, at):
            return invoke(["decide","--ledger",path,"--job-id",JOB_ID,"--decision",decision,"--decided-at",at,
                           "--reason-note","fixture","--receipt",tmp/"decide.json"])

        def apply():
            rec=json.loads((tmp/"decide.json").read_text())
            current=json.loads(path.read_text())
            current["JOBS"][0]["Bora_Decision"]=rec["jobs_update"]["Bora_Decision"]
            current["LOG"].append(rec["log_row"])
            assert_true(set(rec["log_row"])==set(run.LOG_HEADERS) and rec["log_row"]["Error_Code"]=="","LOG row is the exact 9-column shape")
            # Write it back the way the sheet will return it: as raw values, then readback again.
            assert_true(readback(tmp,raw_values(current))[0]==0,"re-readback after writing the decision")

        assert_true(state()["state"]=="NO_DECISION","no decision yet")
        code,out=decide("MAYBE","2026-10-06T09:41:00-04:00")
        assert_true(failure(out)["code"]=="INVALID_DECISION","invalid decision refused")
        code,out=decide("PURSUE","2026-10-06 09:41")
        assert_true(failure(out)["code"]=="TIMESTAMP_INVALID","naive decided-at refused")
        code,out=decide("PURSUE","2026-10-06T09:41:00-04:00")
        assert_true(code==0 and "JOBS_UPDATE" in out,"decide PURSUE: "+out)
        apply()
        current=state()
        assert_true(current["state"]=="PURSUE" and current["authorizes_pursuit"] is True,
                    "blank cells read back as \"\" keep the fingerprint stable, so PURSUE authorizes")
        code,out=decide("PURSUE","2026-10-06T09:42:00-04:00")
        assert_true(failure(out)["code"]=="ALREADY_DECIDED","a repeat decision is refused")
        first_event=current["latest_event_id"]
        changed=json.loads(path.read_text()); changed["JOBS"][0]["Role_Status"]="VERIFIED_LIVE"
        assert_true(readback(tmp,raw_values(changed))[0]==0,"context changed")
        assert_true(state()["state"]=="STALE_RECONFIRMATION_REQUIRED","a changed context needs Bora's reconfirmation")
        code,out=decide("PURSUE","2026-10-06T09:43:00-04:00")
        assert_true(code==0,"Bora reconfirms PURSUE: "+out)
        rec=json.loads((tmp/"decide.json").read_text())
        assert_true(rec["request"]["supersedes_event_id"]==first_event,"reconfirmation supersedes the latest event automatically")
        apply()
        assert_true(state()["authorizes_pursuit"] is True,"reconfirmed PURSUE authorizes")
        code,out=decide("REJECT","2026-10-06T09:44:00-04:00")
        assert_true(code==0,"Bora can change his mind"); apply()
        final=state()
        assert_true(final["state"]=="REJECT" and final["authorizes_pursuit"] is False,"REJECT never authorizes")
        code,out=invoke(["pursuit-state","--ledger",path,"--job-id","NOPE","--receipt",tmp/"s.json"])
        assert_true(failure(out)["code"]=="JOB_UNRESOLVED","unknown job fails")
    print("PASS: decide/pursuit-state use the same canonical Ledger file, supersede correctly and never authorize a stale or non-PURSUE state.")


def test_local_only():
    source=(ROOT/"src"/"career_os_run_v1.py").read_text(encoding="utf-8")
    for forbidden in ("import requests","urllib","http.client","googleapiclient","socket","subprocess","smtplib"):
        assert_true(forbidden not in source,"no network/process import: "+forbidden)
    runbook=(ROOT/"docs"/"CAREER_OS_OPERATE_MODE_V1.md").read_text(encoding="utf-8")
    for needle in ("career_os_run_v1.py readback","career_os_run_v1.py decide","career_os_run_v1.py pursuit-state","--as-of",
                   "Never hand-build ledger.json"):
        assert_true(needle in runbook,"runbook documents "+needle)
    config=json.loads((ROOT/"docs"/"CAREER_OS_OPERATE_MODE_V1.json").read_text(encoding="utf-8"))["run_contract"]
    assert_true(config["contract_id"]==run.RUN_CONTRACT_ID and config["state_machine"][0]=="readback" and "decide" in config["state_machine"],
                "config names contract V1_2 with readback and decide")
    print("PASS: run-contract CLI remains pure/local and the runbook/config document readback, decide and slate dates.")


def main():
    assert_true(len(run.JOBS_HEADERS)==20 and len(run.APPLICATIONS_HEADERS)==10 and len(run.LOG_HEADERS)==9,"live header counts")
    for test in (test_preflight_live_settings,test_slate_dedupe_and_score_rules,test_package_ledger_binding_and_persistence,
                 test_record_submit_live_shapes,test_closeout_slate_authority_and_sha_parse,test_end_to_end_live_shapes,
                 test_readback_normalizes_sheet_values,test_decide_and_pursuit_state,test_local_only):
        test()
    print("PASS: 9 groups of CAREER_OS_RUN_CONTRACT_V1_2 live-shape tests")


if __name__=="__main__":
    main()
