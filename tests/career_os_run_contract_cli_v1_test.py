"""Live-shape regression tests for CAREER_OS_RUN_CONTRACT_V1_6 (V1_5 plus slate Ledger Job_IDs, posting source tiers and confirm-write).

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
    value = {"job_id": job_id, "company": COMPANY, "role": ROLE, "official_url": official_url, "source": "EMPLOYER_SITE (careers.example, opened live)",
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
        # What a Sheets read really returns: trailing blank cells dropped, blank cells as null, empty rows.
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
        spaced=raw_values(ledger([job_row(Role_Status=" ")]))
        assert_true(readback(tmp,spaced,"spaced.json")[0]==0 and
                    json.loads((tmp/"spaced.json").read_text())["JOBS"][0]["Role_Status"]==" ","whitespace values are kept exactly, never trimmed")
        assert_true(built["NETWORK"]==[] and "JOBS rows=1 blank_rows_skipped=1" in out,"NETWORK header-only tab and counts")
        assert_true(run.load_ledger(str(tmp/"ledger-rb.json"))["JOBS"][0]==job_row(),"output satisfies the strict Ledger loader")
        for kept in ("259\n"," 259","259 ","25.9","MTA::17407"):
            code,out=readback(tmp,raw_values(ledger([job_row(Role_Status=kept)])),"kept.json")
            assert_true(code==0 and json.loads((tmp/"kept.json").read_text())["JOBS"][0]["Role_Status"]==kept,
                        "only a cell that is digits and nothing else is refused: %r is kept exactly"%kept)
        code,out=readback(tmp,raw_values(led,network=[["NET::A","N","C","T","https://x.example/a","OTHER","INFO_CHAT","","SENT",
                                                         "2026-10-06","2026-10-06","2026-10-13","42"]]),"net.json")
        assert_true(code==0,"NETWORK Notes may be a bare number")
        import career_os_network_v1 as net
        assert_true(net.load_ledger_with_network(str(tmp/"ledger-rb.json"))["NETWORK"]==[],"network commands accept it")
        cases=[]
        bad=raw_values(led); bad["JOBS"][0][3]="Source"; cases.append((bad,"READBACK_HEADER_MISMATCH"))
        bad=raw_values(led); bad["APPLICATIONS"][1][2]=20261005; cases.append((bad,"READBACK_CELL_TYPE"))
        bad=raw_values(led); bad["LOG"][1]=bad["LOG"][1]+["stray"]; cases.append((bad,"READBACK_ROW_TOO_LONG"))
        bad=raw_values(led); bad["LOG"][1]=bad["LOG"][1]+[""]; cases.append((bad,"READBACK_ROW_TOO_LONG"))
        bad=raw_values(led); bad["LOG"][1]=bad["LOG"][1]+[None]; cases.append((bad,"READBACK_ROW_TOO_LONG"))
        bad=raw_values(led); bad["JOBS"][0][0]=" Job_ID "; cases.append((bad,"READBACK_HEADER_MISMATCH"))
        bad=raw_values(led); bad["JOBS"][0]=bad["JOBS"][0]+[""]; cases.append((bad,"READBACK_HEADER_MISMATCH"))
        bad=raw_values(led); del bad["LOG"]; cases.append((bad,"READBACK_INVALID"))
        bad=raw_values(led); bad["SETTINGS"]=[["Key"]]; cases.append((bad,"READBACK_INVALID"))
        bad=raw_values(ledger([job_row(),job_row()])); cases.append((bad,"READBACK_DUPLICATE_JOB_ID"))
        # The 2026-10-06 incident: empty cells read back as shared-string indexes ("259", "261", "267").
        bad=raw_values(ledger([job_row(Role_Status="261")])); cases.append((bad,"READBACK_SUSPECT_NUMERIC_CELL"))
        bad=raw_values(led); bad["APPLICATIONS"][1][4]="259"; cases.append((bad,"READBACK_SUSPECT_NUMERIC_CELL"))
        bad=raw_values(led); bad["LOG"][1][6]="267"; cases.append((bad,"READBACK_SUSPECT_NUMERIC_CELL"))
        for value,expected in cases:
            code,out=readback(tmp,value,"bad.json")
            assert_true(code==run.EXIT_ERROR and failure(out)["code"]==expected,"readback fails closed with "+expected)
    print("PASS: readback turns raw Sheets values into the exact Ledger file and fails closed on anything ambiguous.")


XLSX_MAIN="http://schemas.openxmlformats.org/spreadsheetml/2006/main"


def _col(number):
    letters=""
    while number:
        number,rest=divmod(number-1,26)
        letters=chr(65+rest)+letters
    return letters


def make_xlsx(path, tabs, refs=True):
    """A minimal real .xlsx, shaped like a Google Sheets export. tabs: {name: [[cell, ...], ...]}; a cell is a str (shared
    string), None (absent), or a tuple: ("inline", text) ("str", text) ("rich", [parts]) ("num", v) ("bool", v) ("blank",)
    ("badindex",) ("raw", xml)."""
    shared,index={},[]
    def sid(text):
        if text not in shared:
            shared[text]=len(index); index.append(("t",text))
        return shared[text]
    def esc(text):
        return text.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
    sheets=[]
    for name,rows in tabs.items():
        xml_rows=[]
        for r,row in enumerate(rows,start=1):
            cells=[]
            for c,cell in enumerate(row,start=1):
                ref=' r="%s%d"'%(_col(c),r) if refs else ""
                if cell is None:
                    continue
                if isinstance(cell,str):
                    cells.append('<c%s t="s"><v>%d</v></c>'%(ref,sid(cell)))
                elif cell[0]=="inline":
                    cells.append('<c%s t="inlineStr"><is><t xml:space="preserve">%s</t></is></c>'%(ref,esc(cell[1])))
                elif cell[0]=="str":
                    cells.append('<c%s t="str"><f>A1</f><v>%s</v></c>'%(ref,esc(cell[1])))
                elif cell[0]=="rich":
                    index.append(("r",cell[1])); cells.append('<c%s t="s"><v>%d</v></c>'%(ref,len(index)-1))
                elif cell[0]=="num":
                    cells.append('<c%s><v>%s</v></c>'%(ref,cell[1]))
                elif cell[0]=="bool":
                    cells.append('<c%s t="b"><v>%s</v></c>'%(ref,cell[1]))
                elif cell[0]=="blank":
                    cells.append('<c%s s="1"/>'%ref)
                elif cell[0]=="badindex":
                    cells.append('<c%s t="s"><v>99999</v></c>'%ref)
                elif cell[0]=="raw":
                    cells.append(cell[1])
            xml_rows.append('<row r="%d">%s</row>'%(r,"".join(cells)))
        sheets.append((name,'<?xml version="1.0" encoding="UTF-8"?><worksheet xmlns="%s"><sheetData>%s</sheetData></worksheet>'%(XLSX_MAIN,"".join(xml_rows))))
    def si(item):
        if item[0]=="t":
            return '<si><t xml:space="preserve">%s</t></si>'%esc(item[1])
        return '<si>%s<rPh><t>IGNORED</t></rPh></si>'%"".join('<r><rPr/><t xml:space="preserve">%s</t></r>'%esc(part) for part in item[1])
    workbook=('<?xml version="1.0" encoding="UTF-8"?><workbook xmlns="%s" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>%s</sheets></workbook>'
              %(XLSX_MAIN,"".join('<sheet name="%s" sheetId="%d" r:id="rId%d"/>'%(esc(n),i,i) for i,(n,_x) in enumerate(sheets,start=1))))
    rels=('<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">%s</Relationships>'
          %"".join('<Relationship Id="rId%d" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet%d.xml"/>'%(i,i)
                   for i in range(1,len(sheets)+1)))
    with zipfile.ZipFile(path,"w") as archive:
        archive.writestr("xl/workbook.xml",workbook)
        archive.writestr("xl/_rels/workbook.xml.rels",rels)
        archive.writestr("xl/sharedStrings.xml",'<?xml version="1.0" encoding="UTF-8"?><sst xmlns="%s">%s</sst>'%(XLSX_MAIN,"".join(si(x) for x in index)))
        for i,(_name,xml) in enumerate(sheets,start=1):
            archive.writestr("xl/worksheets/sheet%d.xml"%i,xml)
    return path


def xlsx_tabs(led, network=()):
    tabs={"SETTINGS":[["Key","Value"],["CANONICAL_MAIN_SHA","x"]]}
    for name,headers in (("JOBS",run.JOBS_HEADERS),("APPLICATIONS",run.APPLICATIONS_HEADERS),("LOG",run.LOG_HEADERS)):
        tabs[name]=[list(headers)]+[[row[h] if row[h]!="" else None for h in headers] for row in led[name]]
    tabs["NETWORK"]=[list(run.NETWORK_HEADERS)]+[list(row) for row in network]
    return tabs


def readback_xlsx(tmp, tabs, name="ledger-x.json", refs=True):
    return invoke(["readback","--xlsx",make_xlsx(tmp/"ledger.xlsx",tabs,refs=refs),"--out",tmp/name,"--receipt",tmp/"readback-x.json"])


def test_readback_from_xlsx_export():
    with tempfile.TemporaryDirectory() as raw_dir:
        tmp=Path(raw_dir)
        led=ledger([job_row(Role_Status=" ",Company="Café Résumé — Co & <Partners>")],[app_row()],[log_row()])
        tabs=xlsx_tabs(led)
        # Export realities: styled blank cells, a blank row, a styled blank past the header, an inline string, a formula string,
        # rich text with a phonetic run, and empty shared strings (the 2026-10-06 "261" incident) all read back exactly.
        tabs["JOBS"][1][1]=("inline",led["JOBS"][0][run.JOBS_HEADERS[1]])
        tabs["JOBS"][1][2]=("str",led["JOBS"][0][run.JOBS_HEADERS[2]])
        first=led["APPLICATIONS"][0][run.APPLICATIONS_HEADERS[0]]
        tabs["APPLICATIONS"][1][0]=("rich",[first[:4],first[4:]])
        tabs["APPLICATIONS"][1]=[cell if cell is not None else ("blank",) for cell in tabs["APPLICATIONS"][1]]+[("blank",),("blank",)]
        tabs["LOG"][1]=[cell if cell is not None else "" for cell in tabs["LOG"][1]]
        tabs["LOG"].insert(1,[("blank",)]*3)  # an interior blank row is skipped and counted
        tabs["LOG"].append([("blank",)]*3)  # trailing blank rows are not content at all
        tabs["JOBS"].append([])
        code,out=readback_xlsx(tmp,tabs)
        assert_true(code==0 and "LEDGER FILE READY" in out and "source: xlsx" in out,"readback --xlsx builds the Ledger file: "+out)
        built=json.loads((tmp/"ledger-x.json").read_text(encoding="utf-8"))
        assert_true(built["JOBS"]==led["JOBS"] and built["APPLICATIONS"]==led["APPLICATIONS"] and built["LOG"]==led["LOG"] and built["NETWORK"]==[],
                    "xlsx readback equals the Ledger exactly")
        assert_true("LOG rows=1 blank_rows_skipped=1" in out and "APPLICATIONS rows=1 blank_rows_skipped=0" in out and "NETWORK rows=0" in out,"blank rows are skipped and counted; NETWORK is read")
        code,raw_out=readback(tmp,raw_values(led,network=[]),"ledger-raw.json")
        assert_true(code==0 and (tmp/"ledger-raw.json").read_bytes()==(tmp/"ledger-x.json").read_bytes(),
                    "the same Ledger via --raw and --xlsx gives byte-identical ledger.json")
        dense={name:[[cell if cell is not None else "" for cell in row] for row in rows] for name,rows in xlsx_tabs(led).items()}
        assert_true(readback_xlsx(tmp,dense,"norefs.json",refs=False)[0]==0 and
                    json.loads((tmp/"norefs.json").read_text(encoding="utf-8"))["LOG"]==led["LOG"],"cells without r= references are read by position")
        receipt=json.loads((tmp/"readback-x.json").read_text())
        assert_true(receipt["source"]=="xlsx" and receipt["source_sha256"]==sha((tmp/"ledger.xlsx").read_bytes()),"receipt binds the exact .xlsx")
        cases=[]
        bad=xlsx_tabs(led); bad["APPLICATIONS"][1][2]=("num","46301"); cases.append((bad,"READBACK_CELL_TYPE"))
        bad=xlsx_tabs(led); bad["LOG"][1][1]=("bool","1"); cases.append((bad,"READBACK_CELL_TYPE"))
        bad=xlsx_tabs(led); bad["LOG"][1][1]=("raw",'<c r="B2" t="e"><v>#REF!</v></c>'); cases.append((bad,"READBACK_CELL_TYPE"))
        bad=xlsx_tabs(led); bad["LOG"][1][1]=("raw",'<c r="B2" t="d"><v>2026-10-06</v></c>'); cases.append((bad,"READBACK_CELL_TYPE"))
        for broken in ("99999","-1","-0"," 1","1 ","+1","1.0","01","٣","","x","1"*5000,"9"*10):
            bad=xlsx_tabs(led); bad["JOBS"][1][4]=("raw",'<c r="E2" t="s"><v>%s</v></c>'%broken); cases.append((bad,"READBACK_XLSX_INVALID"))
        bad=xlsx_tabs(led); bad["JOBS"][1][4]=("raw",'<c r="E2" t="s"/>'); cases.append((bad,"READBACK_XLSX_INVALID"))
        # Resource bounds: sparse or huge coordinates are refused before any grid is built.
        bad=xlsx_tabs(led); bad["LOG"][1][1]=("raw",'</row><row r="100000000"><c r="A100000000" t="inlineStr"><is><t>x</t></is></c>'); cases.append((bad,"READBACK_XLSX_INVALID"))
        bad=xlsx_tabs(led); bad["LOG"][1][1]=("raw",'</row><row r="100001"><c r="A100001" t="inlineStr"><is><t>x</t></is></c>'); cases.append((bad,"READBACK_XLSX_INVALID"))
        for row_attribute in ("0","-5","1e9","abc","٣"):
            bad=xlsx_tabs(led); bad["LOG"][1][1]=("raw",'</row><row r="%s"><c t="inlineStr"><is><t>x</t></is></c>'%row_attribute); cases.append((bad,"READBACK_XLSX_INVALID"))
        bad=xlsx_tabs(led); bad["LOG"][1][1]=("raw",'<c r="AAA2" t="inlineStr"><is><t>x</t></is></c>'); cases.append((bad,"READBACK_XLSX_INVALID"))
        bad=xlsx_tabs(led); bad["LOG"][1][1]=("raw",'<c r="B%s" t="inlineStr"><is><t>x</t></is></c>'%("1"*5000)); cases.append((bad,"READBACK_XLSX_INVALID"))
        bad=xlsx_tabs(led); bad["LOG"][1][1]=("raw",'</row><row r="%s"><c t="inlineStr"><is><t>x</t></is></c>'%("1"*5000)); cases.append((bad,"READBACK_XLSX_INVALID"))
        bad=xlsx_tabs(led); bad["LOG"][1][1]=("raw",'<c r="B7" t="inlineStr"><is><t>x</t></is></c>'); cases.append((bad,"READBACK_XLSX_INVALID"))
        bad=xlsx_tabs(led); bad["LOG"][1]=bad["LOG"][1]+["stray"]; cases.append((bad,"READBACK_ROW_TOO_LONG"))
        bad=xlsx_tabs(led); bad["LOG"][1]=bad["LOG"][1]+[("blank",),("inline"," ")]; cases.append((bad,"READBACK_ROW_TOO_LONG"))
        bad=xlsx_tabs(led); bad["JOBS"][0][0]=" Job_ID"; cases.append((bad,"READBACK_HEADER_MISMATCH"))
        bad=xlsx_tabs(led); bad["JOBS"].insert(0,[]); cases.append((bad,"READBACK_HEADER_MISMATCH"))
        bad=xlsx_tabs(led); del bad["LOG"]; cases.append((bad,"READBACK_INVALID"))
        bad=xlsx_tabs(led); bad["APPLICATIONS"]=[]; cases.append((bad,"READBACK_INVALID"))
        bad=xlsx_tabs(ledger([job_row(),job_row()])); cases.append((bad,"READBACK_DUPLICATE_JOB_ID"))
        bad=xlsx_tabs(ledger([job_row(Role_Status="261")])); cases.append((bad,"READBACK_SUSPECT_NUMERIC_CELL"))
        for value,expected in cases:
            code,out=readback_xlsx(tmp,value,"bad.json")
            assert_true(code==run.EXIT_ERROR and failure(out)["code"]==expected,"readback --xlsx fails closed with "+expected+": "+out)
        saved=run.XLSX_MAX_CELLS
        try:
            run.XLSX_MAX_CELLS=25
            code,out=readback_xlsx(tmp,xlsx_tabs(led),"capped.json")
            assert_true(code==run.EXIT_ERROR and failure(out)["code"]=="READBACK_XLSX_INVALID","the per-tab cell bound is enforced")
            run.XLSX_MAX_CELLS=150
            wide=xlsx_tabs(led); wide["LOG"].extend([[None]*100+[("inline","x")] for _ in range(3)])
            code,out=readback_xlsx(tmp,wide,"wide.json")
            assert_true(code==run.EXIT_ERROR and failure(out)["code"]=="READBACK_XLSX_INVALID" and "expand" in failure(out)["detail"],
                        "the materialized-grid bound is checked before the grid is built: "+out)
        finally:
            run.XLSX_MAX_CELLS=saved
        good=(tmp/"ledger.xlsx")
        make_xlsx(good,xlsx_tabs(led))
        corrupt=bytearray(good.read_bytes())
        with zipfile.ZipFile(good) as archive:
            info=archive.getinfo("xl/worksheets/sheet2.xml")
        start=info.header_offset+30+len(info.filename.encode())+len(info.extra)
        corrupt[start:start+8]=b"\xff"*8  # damage stored member bytes: a CRC failure on read
        write(tmp/"corrupt.xlsx",bytes(corrupt))
        code,out=invoke(["readback","--xlsx",tmp/"corrupt.xlsx","--out",tmp/"c.json","--receipt",tmp/"c-r.json"])
        assert_true(code==run.EXIT_ERROR and failure(out)["code"]=="READBACK_XLSX_INVALID","a corrupt member is a controlled refusal: "+out)
        # Failure details never echo more than 40 characters of any input value, on either source.
        long_text,long_digits="Z"*5000,"7"*5000
        def bounded(out,expected):
            detail=failure(out)
            return detail["code"]==expected and long_text[:41] not in detail["detail"] and long_digits[:41] not in detail["detail"] \
                and len(detail["detail"])<400
        echo_cases=[]
        bad=xlsx_tabs(led); bad["JOBS"][0][0]=long_text; echo_cases.append(("x",bad,"READBACK_HEADER_MISMATCH"))
        bad=xlsx_tabs(led); bad["JOBS"][0]=bad["JOBS"][0]+[long_text]; echo_cases.append(("x",bad,"READBACK_HEADER_MISMATCH"))
        bad=xlsx_tabs(ledger([job_row(Role_Status=long_digits)])); echo_cases.append(("x",bad,"READBACK_SUSPECT_NUMERIC_CELL"))
        bad=xlsx_tabs(ledger([job_row(job_id=long_text),job_row(job_id=long_text)])); echo_cases.append(("x",bad,"READBACK_DUPLICATE_JOB_ID"))
        bad=xlsx_tabs(led); bad["LOG"][1][1]=("raw",'<c r="B2" t="%s"><v>1</v></c>'%long_text); echo_cases.append(("x",bad,"READBACK_CELL_TYPE"))
        bad=raw_values(led); bad["JOBS"][0][0]=long_text; echo_cases.append(("r",bad,"READBACK_HEADER_MISMATCH"))
        bad=raw_values(ledger([job_row(Role_Status=long_digits)])); echo_cases.append(("r",bad,"READBACK_SUSPECT_NUMERIC_CELL"))
        bad=raw_values(led); bad[long_text]=[["x"]]; echo_cases.append(("r",bad,"READBACK_INVALID"))
        for source,value,expected in echo_cases:
            code,out=readback_xlsx(tmp,value,"echo.json") if source=="x" else readback(tmp,value,"echo.json")
            assert_true(code==run.EXIT_ERROR and bounded(out,expected),"%s failure detail is bounded (%s): %s"%(expected,source,out[:300]))
        dup=make_xlsx(tmp/"dup.xlsx",xlsx_tabs(led))
        with zipfile.ZipFile(dup) as archive:
            parts={name:archive.read(name) for name in archive.namelist()}
        parts["xl/workbook.xml"]=parts["xl/workbook.xml"].replace(b'name="SETTINGS"',('name="%s"'%long_text).encode()).replace(
            b'name="EVIDENCE"',b"").replace(b"</sheets>",('<sheet name="%s" sheetId="99" r:id="rId1"/></sheets>'%long_text).encode())
        with zipfile.ZipFile(dup,"w") as archive:
            for name,data in parts.items():
                archive.writestr(name,data)
        code,out=invoke(["readback","--xlsx",dup,"--out",tmp/"d.json","--receipt",tmp/"d-r.json"])
        assert_true(code==run.EXIT_ERROR and bounded(out,"READBACK_XLSX_INVALID"),"duplicate long tab name is bounded: "+out[:300])
        # The reviewer's case: an oversized worksheet relationship target pointing at a missing part.
        with zipfile.ZipFile(tmp/"ledger.xlsx") as archive:
            parts={name:archive.read(name) for name in archive.namelist()}
        rels=dict(parts); rels["xl/_rels/workbook.xml.rels"]=parts["xl/_rels/workbook.xml.rels"].replace(
            b'Target="worksheets/sheet2.xml"',('Target="%s"'%long_text).encode())
        with zipfile.ZipFile(tmp/"rels.xlsx","w") as archive:
            for name,data in rels.items():
                archive.writestr(name,data)
        code,out=invoke(["readback","--xlsx",tmp/"rels.xlsx","--out",tmp/"rl.json","--receipt",tmp/"rl-r.json"])
        assert_true(code==run.EXIT_ERROR and bounded(out,"READBACK_XLSX_INVALID"),"oversized relationship target is bounded: "+out[:300])
        # Sweep: every attribute value and text node of every part, replaced in turn by 5000 letters or digits, ends in a bounded,
        # controlled outcome (no crash, no echoed long value).
        import re
        for name,data in parts.items():
            spots=[m.span(1) for m in re.finditer(rb'="([^"]*)"',data)]+[m.span(1) for m in re.finditer(rb'>([^<]+)<',data)]
            for start,end in spots:
                for value in (long_text.encode(),long_digits.encode()):
                    changed=dict(parts); changed[name]=data[:start]+value+data[end:]
                    with zipfile.ZipFile(tmp/"sweep.xlsx","w") as archive:
                        for part_name,part_data in changed.items():
                            archive.writestr(part_name,part_data)
                    code,out=invoke(["readback","--xlsx",tmp/"sweep.xlsx","--out",tmp/"sw.json","--receipt",tmp/"sw-r.json"])
                    if code:
                        detail=failure(out)["detail"]
                        assert_true(long_text[:41] not in detail and long_digits[:41] not in detail and len(detail)<400,
                                    "sweep %s: bounded detail: %s"%(name,detail[:200]))
        write(tmp/"not.xlsx",b"not a zip")
        code,out=invoke(["readback","--xlsx",tmp/"not.xlsx","--out",tmp/"n.json","--receipt",tmp/"n-r.json"])
        assert_true(code==run.EXIT_ERROR and failure(out)["code"]=="READBACK_XLSX_INVALID","a non-xlsx file is refused")
        for argv in (["readback","--out",tmp/"n.json","--receipt",tmp/"n-r.json"],
                     ["readback","--xlsx",tmp/"ledger.xlsx","--raw",tmp/"raw.json","--out",tmp/"n.json","--receipt",tmp/"n-r.json"]):
            code,out=invoke(argv)
            assert_true(code==run.EXIT_ERROR and failure(out)["code"]=="ARGUMENT_ERROR","exactly one of --xlsx or --raw")
    print("PASS: readback --xlsx reads the whole Drive export exactly and fails closed on non-text, broken or misplaced cells.")


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


def test_record_external_submit():
    with tempfile.TemporaryDirectory() as raw_dir:
        tmp=Path(raw_dir)
        job=job_row(Bora_Decision="PURSUE")
        screened=log_row(Run_ID="SLATE::1",Stage="SLATE_SCREENED",Status="REVIEW_READY")
        path=write(tmp/"ledger.json",ledger([job],[],[screened]))

        def go(*extra, ledger_path=path, confirmed=True):
            argv=["record-external-submit","--ledger",ledger_path,"--job-id",JOB_ID,"--channel","Handshake Quick apply",
                  "--applied-date","2026-10-06","--resume-note","Bora's own Handshake resume",
                  "--evidence-note","Handshake shows Applied on October 6, 2026","--receipt",tmp/"ext.json"]+list(extra)
            if confirmed:
                argv.append("--bora-confirmed")
            return invoke(argv)

        code,out=go(confirmed=False)
        assert_true(failure(out)["code"]=="BORA_CONFIRMATION_REQUIRED","external submit needs Bora's confirmation")
        code,out=go()
        assert_true(code==0 and "APPLICATIONS_ROW_VALUES" in out,"external submit records: "+out)
        rec=json.loads((tmp/"ext.json").read_text())
        app=rec["applications_row"]; log=rec["log_row"]
        assert_true(set(app)==set(run.APPLICATIONS_HEADERS) and set(log)==set(run.LOG_HEADERS),"exact live shapes")
        assert_true(app["Resume_Version"]=="EXTERNAL_NO_CAREER_OS_PACKAGE","Resume_Version is the fixed label, so it can never carry a hash")
        assert_true("resume used: Bora's own Handshake resume" in app["Outcome"],"the resume note is kept in Outcome")
        assert_true(app["Cover_Letter_Version"]=="NOT_RECORDED" and rec["jobs_row"]=={"Job_ID":JOB_ID,"Application_Status":"SUBMITTED"},
                    "only Application_Status changes in JOBS; nothing invented about a cover letter")
        assert_true(app["Outcome"].endswith("Handshake shows Applied on October 6, 2026"),"Bora's evidence note is kept")
        done=ledger([dict(job,Application_Status="SUBMITTED")],[app],[screened,log])
        done_path=write(tmp/"done.json",done)
        code,out=go(ledger_path=done_path)
        assert_true(failure(out)["code"]=="ALREADY_RECORDED","a second record for the same job is refused")
        log_only=ledger([job],[],[screened,dict(log,Run_ID="RECORD_EXTERNAL_SUBMIT::%s::2026-10-01"%JOB_ID,Timestamp="2026-10-01")])
        code,out=go(ledger_path=write(tmp/"log-only.json",log_only))
        assert_true(failure(out)["code"]=="ALREADY_RECORDED","an earlier application LOG event on another date also blocks (job-level)")
        hexs="a"*64
        for flag,value in (("--resume-note","my resume | sha256:"+hexs),("--resume-note","SHA256 x"),("--resume-note","SHA-256: "+hexs),
                           ("--resume-note","sha_256 "+hexs),("--resume-note","digest "+hexs),("--resume-note","md5 "+"b"*32),
                           ("--channel","Handshake\rQuick"),("--evidence-note","line1\rline2"),("--resume-note","tab\there"),
                           ("--channel","Handshake\u0085Quick"),("--evidence-note","a\u2028b"),("--evidence-note","a\u2029b"),
                           ("--resume-note","zero\u200bwidth"),("--channel","   "),
                           ("--resume-note","SHA\u00b2\u2075\u2076: "+"\uff41"*64),("--resume-note","sha\u2082\u2085\u2086: "+"\uff41"*64),
                           ("--resume-note","\uff33\uff28\uff21\uff12\uff15\uff16: "+"\uff41"*64),("--evidence-note","receipt "+"\uff10"*40),
                           ("--channel","sha256 portal")):
            argv=["record-external-submit","--ledger",path,"--job-id",JOB_ID,"--channel","Handshake","--applied-date","2026-10-06",
                  "--resume-note","own resume","--evidence-note","Handshake shows Applied","--bora-confirmed","--receipt",tmp/"bad.json"]
            argv[argv.index(flag)+1]=value
            code,out=invoke(argv)
            assert_true(failure(out)["code"]=="FIELD_INVALID","refused %s=%r"%(flag,value))
        for bad_date in ("2026-99-99","2026-02-30","2026-10-6","06/10/2026"):
            argv=["record-external-submit","--ledger",path,"--job-id",JOB_ID,"--channel","Handshake","--applied-date",bad_date,
                  "--resume-note","own resume","--evidence-note","Handshake shows Applied","--bora-confirmed","--receipt",tmp/"bad.json"]
            code,out=invoke(argv)
            assert_true(failure(out)["code"]=="APPLIED_DATE_INVALID","refused applied date %r"%bad_date)
        code,out=invoke(["record-external-submit","--ledger",path,"--job-id",JOB_ID,"--channel","Handshake Quick apply (Brandeis)",
                         "--applied-date","2026-10-06","--resume-note","My own résumé, v3 — Oct 2026","--evidence-note",
                         "Handshake: Applied on October 6, 2026","--bora-confirmed","--receipt",tmp/"ok.json"])
        assert_true(code==0,"ordinary notes with accents, dashes, digits and punctuation are accepted: "+out)
        code,out=invoke(["record-external-submit","--ledger",path,"--job-id","NOPE","--channel","x","--applied-date","2026-10-06",
                         "--resume-note","x","--evidence-note","x","--bora-confirmed","--receipt",tmp/"x.json"])
        assert_true(failure(out)["code"]=="JOB_UNRESOLVED","unknown job refused")
        slate={"spec":"CAREER_OS_RUN_SLATE_RECEIPT_V1","slate":[{"job_id":JOB_ID,"tracking_status":"NEW"}]}
        code,out=invoke(["closeout","--slate-receipt",write(tmp/"slate.json",slate),"--ledger",done_path,
                         "--folders",write(tmp/"folders.json",{}),"--plans",write(tmp/"plans.json",[]),"--receipt",tmp/"close.json"])
        assert_true(code==0 and out.strip().endswith("CAREER_OS_RUN_CLOSEOUT: COMPLETE"),"closeout accepts an external submission: "+out)
        fake=ledger([dict(job,Application_Status="SUBMITTED")],[dict(app,Resume_Version="resume.pdf")],[screened])
        code,out=invoke(["closeout","--slate-receipt",tmp/"slate.json","--ledger",write(tmp/"fake.json",fake),
                         "--folders",tmp/"folders.json","--plans",tmp/"plans.json","--receipt",tmp/"close2.json"])
        assert_true(code==run.EXIT_STOP and "PLAN_NOT_SUPPLIED" in out,"an ordinary submission without a plan still fails closeout")
    print("PASS: record-external-submit records Bora's outside-package applications honestly and closeout accepts only those.")


def real_package_deps():
    """PackageDeps over this repository's Candidate Truth with the host Liberation Sans fonts (None when they are not installed or not
    the pinned bytes); used in place of the cloud runtime loader, which needs a released runtime ZIP."""
    import gold_resume_docx_builder as builder
    import pursue_to_gold_package as ptg
    from claim_repository import load_validated_claim_repository
    from evidence_repository import load_validated_evidence_repository
    manifest=json.loads((ROOT/"docs"/"rendering"/"RENDERING_ENVIRONMENT_V1.json").read_text(encoding="utf-8"))
    try:
        fonts=builder.fonts_from_manifest(manifest,lambda path: Path(path).read_bytes())
    except Exception:
        return None
    claims=load_validated_claim_repository(ROOT/"claims"); evidence=load_validated_evidence_repository(ROOT/"evidence")
    assert_true(claims["valid"] and evidence["valid"],"Candidate Truth repositories are valid")
    language=json.loads((ROOT/"docs"/"resume"/"BORA_APPROVED_RESUME_LANGUAGE_V1.json").read_text(encoding="utf-8"))
    return ptg.PackageDeps(load_claims=lambda:claims["index"],load_evidence=lambda:evidence["index"],approved_language=lambda:language,
                           validate_lineage=lambda claim:[],
                           identity_provider=lambda:ptg.approved_identity_from_canonical_records(ROOT,claims=claims["index"],evidence=evidence["index"]),
                           fonts=fonts,render=None,renderer_identity=None,pdf_facts=None,current_state=None,doctrine_root=ROOT,roster=None)


def test_resume_model():
    import gold_resume_qa as qa
    import pursue_to_gold_package as ptg
    from claim_repository import load_validated_claim_repository
    from evidence_repository import load_validated_evidence_repository
    language=json.loads((ROOT/"docs"/"resume"/"BORA_APPROVED_RESUME_LANGUAGE_V1.json").read_text(encoding="utf-8"))
    claims=load_validated_claim_repository(ROOT/"claims")["index"]; evidence=load_validated_evidence_repository(ROOT/"evidence")["index"]
    identity=ptg.approved_identity_from_canonical_records(ROOT,claims=claims,evidence=evidence)
    bullets={item["bullet_id"]:item for item in language["bullets"]}
    summaries={item["summary_id"]:item for item in language["summaries"]}
    # The recipes only ever name approved, jargon-free language, never Bulmarma or the always-failing entries.
    for name,recipe in run.RESUME_RECIPES.items():
        ids=[i for _e,group in run.RESUME_WORK for i in group]+list(recipe["project_bullets"])
        for bullet_id in ids:
            assert_true(bullet_id in bullets and not qa.jargon_hits(bullets[bullet_id]["text"]),"%s %s approved and jargon-free"%(name,bullet_id))
        for summary_id in recipe["summaries"]:
            assert_true(summary_id in summaries and not qa.jargon_hits(summaries[summary_id]["text"]),"%s %s approved and jargon-free"%(name,summary_id))
        assert_true(not {"B011","B015","B016"}&set(ids) and "S005" not in recipe["summaries"],"%s never uses B011/B015/B016/S005"%name)
    for name,summary_id in (("MARKETMIND","S002"),("MARKETMIND","S003"),("MARKET_EMPIRE","S002")):
        model=run.build_resume_model(JOB_ID,name,summary_id,[],identity,language)
        assert_true([entry["employer"] for entry in model["work"]]==["Winter Walk","TELUS Digital","D Commerce Bank"],"work is newest first")
        assert_true(model["summary"]["text"]==summaries[summary_id]["text"] and model["job_id"]==JOB_ID,"summary text is the approved one")
        texts={(item["text"],tuple(item["claim_ids"])) for item in language["bullets"]}
        assert_true(all((b["text"],tuple(b["claim_ids"])) in texts for entry in model["work"]+[model["project"]] for b in entry["bullets"]),
                    "every bullet is exact approved language with its claim binding")
        assert_true(qa.approved_language_problems(model,language,claims,evidence)==[],"approved-language check passes: %s"%name)
        assert_true(qa.jargon_hits(qa._all_visible_text(model))==[],"no recruiter jargon: %s"%name)
        if name=="MARKET_EMPIRE":
            assert_true(model["project"]["name"]=="Market Empire" and model["roster_omissions"]==[{"roster_entry":"MarketMind","reason":"NOT_RELEVANT_PER_CROSSWALK"}],
                        "Market Empire replaces MarketMind with a recorded omission")
        else:
            assert_true(model["project"]["name"]=="MarketMind" and "roster_omissions" not in model,"MarketMind is the default project")
    ordered=run.build_resume_model(JOB_ID,"MARKET_EMPIRE","S002",["B013","B022","B009"],identity,language)
    ww=[b["text"] for b in ordered["work"][0]["bullets"]]; project=[b["text"] for b in ordered["project"]["bullets"]]
    assert_true(ww[0]==bullets["B013"]["text"] and project[0]==bullets["B022"]["text"] and ordered["work"][1]["bullets"][0]["text"]==bullets["B009"]["text"]
                and len(ww)==4 and len(project)==5,"--order moves listed bullets first within their own entry and drops nothing")
    for args,code in (((JOB_ID,"LOANIQ","S002",[]),"RESUME_MODEL_PROJECT_INVALID"),((JOB_ID,"MARKET_EMPIRE","S003",[]),"RESUME_MODEL_SUMMARY_INVALID"),
                      ((JOB_ID,"MARKETMIND","S005",[]),"RESUME_MODEL_SUMMARY_INVALID"),((JOB_ID,"MARKETMIND","S002",["B011"]),"RESUME_MODEL_ORDER_INVALID"),
                      ((JOB_ID,"MARKETMIND","S002",["B019"]),"RESUME_MODEL_ORDER_INVALID"),((JOB_ID,"MARKETMIND","S002",["B013","B013"]),"RESUME_MODEL_ORDER_INVALID")):
        try:
            run.build_resume_model(*args,identity,language); got=None
        except run.RunError as error:
            got=error.code
        assert_true(got==code,"build_resume_model %s -> %s (got %s)"%(args[1:],code,got))
    # The full command: page fill and the canonical pre-render QA, with the real fonts when the host has the pinned bytes.
    deps=real_package_deps()
    if deps is None:
        print("NOTE: pinned Liberation Sans not on this host; the resume-model page-fill/QA run is covered where the fonts exist.")
    else:
        real=cloud.make_cloud_operate_deps
        cloud.make_cloud_operate_deps=lambda *a,**k: deps
        try:
            with tempfile.TemporaryDirectory() as raw:
                tmp=Path(raw)
                for name,summary_id,order in (("MARKETMIND","S002",""),("MARKETMIND","S003",""),("MARKET_EMPIRE","S002",""),
                                              ("MARKET_EMPIRE","S002","B013,B022")):
                    argv=["resume-model","--job-id",JOB_ID,"--project",name,"--summary",summary_id,"--runtime-root",tmp,"--font-dir",tmp,
                          "--expected-main-sha",MAIN_SHA,"--out",tmp/"model.json","--receipt",tmp/"rm.json"]+(["--order",order] if order else [])
                    code,out=invoke(argv)
                    assert_true(code==0 and "CAREER_OS_RUN_RESUME_MODEL: READY" in out,"resume-model READY for %s %s %s: %s"%(name,summary_id,order,out))
                    fill=float(out.split("page_fill: ")[1].split()[0])
                    assert_true(fill>=0.935,"page fill meets the doctrine target: %s"%fill)
                    receipt=json.loads((tmp/"rm.json").read_text())
                    assert_true(receipt["model_sha256"]==sha((tmp/"model.json").read_bytes()),"receipt binds the model bytes")
                code,out=invoke(["resume-model","--job-id","bad\nid","--project","MARKETMIND","--summary","S002","--runtime-root",tmp,"--font-dir",tmp,
                                 "--expected-main-sha",MAIN_SHA,"--out",tmp/"m.json","--receipt",tmp/"r.json"])
                assert_true(code==run.EXIT_ERROR and failure(out)["code"]=="RESUME_MODEL_JOB_INVALID","a multi-line job id is refused")
        finally:
            cloud.make_cloud_operate_deps=real
    # package --resume-model replaces the request model, bound to the same job; QA failures name the failing checks.
    real=cloud.run_request; cloud.run_request=fake_run_request
    try:
        with tempfile.TemporaryDirectory() as raw:
            tmp=Path(raw)
            led=write(tmp/"ledger.json",ledger([job_row()],[],[log_row()]))
            model=run.build_resume_model(JOB_ID,"MARKETMIND","S002",[],identity,language)
            SEEN_REQUESTS.clear()
            code,out=invoke(package_argv(tmp,request_file(tmp),led)+["--resume-model",write(tmp/"model.json",model)])
            assert_true(code==0 and SEEN_REQUESTS[-1]["resume_model"]==model,"package uses the --resume-model file as the resume model")
            other=dict(model,job_id="OTHER::JOB")
            shutil.rmtree(tmp/"out")
            code,out=invoke(package_argv(tmp,request_file(tmp),led)+["--resume-model",write(tmp/"other.json",other)])
            assert_true(code==run.EXIT_ERROR and failure(out)["code"]=="RESUME_MODEL_JOB_MISMATCH","a model for another job is refused")
    finally:
        cloud.run_request=real
    class QaError(Exception):
        def __init__(self):
            super().__init__("GOLD_PRE_RENDER_QA_FAILED")
            self.code="GOLD_PRE_RENDER_QA_FAILED"; self.detail="ROSTER_POLICY,RECRUITER_JARGON_PROHIBITION"
            self.report={"checks":[{"check":"ROSTER_POLICY","passed":False,"detail":"Bulmarma included without a crosswalk exception"},
                                   {"check":"RECRUITER_JARGON_PROHIBITION","passed":False,"detail":"hits=['kill switch']"},
                                   {"check":"DOCX_PARSEABLE","passed":True,"detail":""}]}
    def failing_run_request(*_args):
        raise QaError()
    cloud.run_request=failing_run_request
    try:
        with tempfile.TemporaryDirectory() as raw:
            tmp=Path(raw)
            code,out=invoke(package_argv(tmp,request_file(tmp),write(tmp/"ledger.json",ledger([job_row()],[],[log_row()]))))
            detail=failure(out)["detail"]
            assert_true(code==run.EXIT_ERROR and failure(out)["code"]=="GOLD_PRE_RENDER_QA_FAILED" and "hits=['kill switch']" in detail
                        and "Bulmarma included" in detail and "DOCX_PARSEABLE" not in detail,"package failure names each failed check and why: "+detail)
    finally:
        cloud.run_request=real
    print("PASS: resume-model builds only approved one-page recipes (MarketMind or Market Empire) that pass page fill and pre-render QA.")


def test_tracked_ids_source_tiers_and_confirm_write():
    with tempfile.TemporaryDirectory() as raw_dir:
        tmp=Path(raw_dir)
        # The 2026-10-06 Entegris incident: screened under a new id, matched by URL, then decide used the screening id.
        ledger_id="ENTEGRIS::LAB-AUTOMATION-AI-ENGINEERING-COOP-REQ-14498"
        tracked=job_row(job_id=ledger_id,Bora_Decision="REJECT")
        code,out=run_slate(tmp,[role(job_id="ENTEGRIS::REQ-14498")],ledger([tracked]))
        line=[l for l in out.splitlines() if "ALREADY_TRACKED" in l][0]
        assert_true(code==0 and line.startswith(ledger_id+" | ") and "screened_as=ENTEGRIS::REQ-14498" in line,
                    "a tracked role is printed under its Ledger Job_ID: "+line)
        same=[l for l in run_slate(tmp,[role(job_id=ledger_id)],ledger([tracked]))[1].splitlines() if "ALREADY_TRACKED" in l][0]
        assert_true("screened_as" not in same,"no screened_as note when the ids already match")
        code,out=run_slate(tmp,[role(job_id="ENTEGRIS::REQ-14498")],ledger([tracked]))
        slate_receipt=tmp/"slate.json"
        led_path=write(tmp/"closeout-ledger.json",ledger([job_row(job_id=ledger_id,Bora_Decision="PURSUE")]))
        code,out=invoke(["closeout","--slate-receipt",slate_receipt,"--ledger",led_path,"--folders",write(tmp/"folders.json",{}),
                         "--receipt",tmp/"close.json"])
        assert_true("MISSING: %s: PURSUE_PACKAGE_NOT_PERSISTED_COMPLETE"%ledger_id in out,"closeout names the Ledger Job_ID: "+out)
        # Source tiers: every screened role says how its posting was verified.
        for good in ("EMPLOYER_SITE","SCHOOL_PORTAL (Babson; employer contact dkent@ae-ventures.com matches ae-ventures.com/careers)",
                     "JOB_BOARD (LinkedIn repost; Bora verified)"):
            assert_true(run_slate(tmp,[role(source=good)],ledger([]))[0]==0,"source tier accepted: "+good)
        for bad in ("MANUAL_URL","FIRST_PARTY","school_portal","EMPLOYER_SITES","Handshake"):
            code,out=run_slate(tmp,[role(source=bad)],ledger([]))
            assert_true(code==run.EXIT_ERROR and failure(out)["code"]=="SLATE_INVALID" and "source must start with" in failure(out)["detail"],
                        "untiered source refused: "+bad)
        # confirm-write: every printed row must be in a fresh readback exactly.
        code,out=run_slate(tmp,[role()],ledger([]))
        rows=json.loads((tmp/"slate.json").read_text())["jobs_rows"]
        good_row={k:("" if v is None else v) for k,v in rows[0].items()}
        after=write(tmp/"after.json",ledger([good_row]))
        code,out=invoke(["confirm-write","--ledger",after,"--written",tmp/"slate.json","--receipt",tmp/"cw.json"])
        assert_true(code==0 and "CONFIRM_WRITE: PASS" in out and "JOBS 'FIXTURE::DATA-ANALYST'" in out,"slate rows confirmed: "+out)
        typo=dict(good_row,Official_URL=good_row["Official_URL"]+"x")
        code,out=invoke(["confirm-write","--ledger",write(tmp/"typo.json",ledger([typo])),"--written",tmp/"slate.json","--receipt",tmp/"cw.json"])
        assert_true(code==run.EXIT_ERROR and failure(out)["code"]=="WRITE_NOT_CONFIRMED" and "Official_URL" in failure(out)["detail"],
                    "a mistyped cell is caught and named: "+out)
        code,out=invoke(["confirm-write","--ledger",write(tmp/"none.json",ledger([])),"--written",tmp/"slate.json","--receipt",tmp/"cw.json"])
        assert_true(code==run.EXIT_ERROR and "found 0 rows" in failure(out)["detail"],"a missing row is caught")
        # decide: the one JOBS cell plus the exact LOG row; a shortened fingerprint inside Notes is caught.
        base=write(tmp/"base.json",ledger([job_row(First_Seen=AS_OF)],[],[log_row()]))
        assert_true(invoke(["decide","--ledger",base,"--job-id",JOB_ID,"--decision","PURSUE","--decided-at","2026-10-06T19:06:03-04:00",
                            "--receipt",tmp/"decide.json"])[0]==0,"decide")
        rec=json.loads((tmp/"decide.json").read_text())
        good=ledger([job_row(First_Seen=AS_OF,Bora_Decision="PURSUE")],[],[log_row(),rec["log_row"]])
        code,out=invoke(["confirm-write","--ledger",write(tmp/"d-ok.json",good),"--written",tmp/"decide.json","--receipt",tmp/"cw.json"])
        assert_true(code==0 and out.count("confirmed: ")==2,"decide cell and LOG row confirmed: "+out)
        fp=rec["request"]["reviewed_context_fingerprint"]
        mangled=dict(rec["log_row"],Notes=rec["log_row"]["Notes"].replace(fp,fp[:40]+fp[52:]))
        bad=ledger([job_row(First_Seen=AS_OF,Bora_Decision="PURSUE")],[],[log_row(),mangled])
        code,out=invoke(["confirm-write","--ledger",write(tmp/"d-bad.json",bad),"--written",tmp/"decide.json","--receipt",tmp/"cw.json"])
        assert_true(code==run.EXIT_ERROR and "Notes differ" in failure(out)["detail"],"a shortened fingerprint in the LOG row is caught: "+out)
        wrong_cell=ledger([job_row(First_Seen=AS_OF,Bora_Decision="WATCH")],[],[log_row(),rec["log_row"]])
        code,out=invoke(["confirm-write","--ledger",write(tmp/"d-cell.json",wrong_cell),"--written",tmp/"decide.json","--receipt",tmp/"cw.json"])
        assert_true(code==run.EXIT_ERROR and "Bora_Decision" in failure(out)["detail"],"a wrong decision cell is caught")
        # Two receipts at once, and receipts that write nothing are refused.
        assert_true(run_slate(tmp,[role(job_id="OTHER::JOB",official_url="https://careers.example/other")],ledger([]))[0]==0,"second slate")
        other={k:("" if v is None else v) for k,v in json.loads((tmp/"slate.json").read_text())["jobs_rows"][0].items()}
        both=ledger([other,job_row(First_Seen=AS_OF,Bora_Decision="PURSUE")],[],[log_row(),rec["log_row"]])
        code,out=invoke(["confirm-write","--ledger",write(tmp/"both.json",both),"--written",tmp/"slate.json","--written",tmp/"decide.json",
                         "--receipt",tmp/"cw.json"])
        assert_true(code==0 and out.count("confirmed: ")==3,"several receipts are confirmed together: "+out)
        code,out=invoke(["confirm-write","--ledger",base,"--written",tmp/"cw.json","--receipt",tmp/"cw2.json"])
        assert_true(code==run.EXIT_ERROR and failure(out)["code"]=="CONFIRM_WRITE_RECEIPT_UNSUPPORTED","a non-write receipt is refused")
    print("PASS: tracked roles use their Ledger Job_ID, every source carries a verification tier, and confirm-write proves each write.")


def test_local_only():
    source=(ROOT/"src"/"career_os_run_v1.py").read_text(encoding="utf-8")
    for forbidden in ("import requests","urllib","http.client","googleapiclient","socket","subprocess","smtplib"):
        assert_true(forbidden not in source,"no network/process import: "+forbidden)
    runbook=(ROOT/"docs"/"CAREER_OS_OPERATE_MODE_V1.md").read_text(encoding="utf-8")
    for needle in ("career_os_run_v1.py readback","career_os_run_v1.py decide","career_os_run_v1.py pursuit-state","--as-of",
                   "Never hand-build, retype or partly read ledger.json","career_os_run_v1.py record-external-submit","--xlsx ledger.xlsx",
                   "never parse it yourself","they never block package","career_os_run_v1.py resume-model","--resume-model run_output_model/model.json",
                   "MARKET_EMPIRE","Never assemble the resume model by hand","career_os_run_v1.py confirm-write","SCHOOL_PORTAL",
                   "never keep a role outside the Ledger","use that Ledger Job_ID in every later command"):
        assert_true(needle in runbook,"runbook documents "+needle)
    config=json.loads((ROOT/"docs"/"CAREER_OS_OPERATE_MODE_V1.json").read_text(encoding="utf-8"))["run_contract"]
    assert_true(config["contract_id"]==run.RUN_CONTRACT_ID and config["state_machine"][0]=="readback" and "decide" in config["state_machine"]
                and config["state_machine"].index("resume-model")==config["state_machine"].index("package")-1,
                "config names the current contract with readback and decide")
    print("PASS: run-contract CLI remains pure/local and the runbook/config document readback, decide and slate dates.")


def main():
    assert_true(len(run.JOBS_HEADERS)==20 and len(run.APPLICATIONS_HEADERS)==10 and len(run.LOG_HEADERS)==9,"live header counts")
    for test in (test_preflight_live_settings,test_slate_dedupe_and_score_rules,test_package_ledger_binding_and_persistence,
                 test_record_submit_live_shapes,test_closeout_slate_authority_and_sha_parse,test_end_to_end_live_shapes,
                 test_readback_normalizes_sheet_values,test_readback_from_xlsx_export,test_decide_and_pursuit_state,test_record_external_submit,test_resume_model,test_tracked_ids_source_tiers_and_confirm_write,test_local_only):
        test()
    print("PASS: 13 groups of CAREER_OS_RUN_CONTRACT_V1_6 live-shape tests")


if __name__=="__main__":
    main()
