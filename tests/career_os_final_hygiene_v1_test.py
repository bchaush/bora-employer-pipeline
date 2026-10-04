"""Regression tests for CAREER_OS_FINAL_HYGIENE_V1.

Dependency-free. Covers: the canonicalized cloud adapter (exact recovered bytes, profile, honesty fields, canonical reuse, fail-closed
runtime verification, sidecar), the two canonical resume standards, the claim-wording review and its advisory meaning-shift flags,
the future-package persistence inventory, and the recovery pointer. The summary-centering regression lives with the other Gold
grammar checks in pursue_to_gold_package_v1_test.py.

All fixture content is SYNTHETIC.
"""

from __future__ import annotations

import hashlib
import importlib
import json
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))
sys.dont_write_bytecode = True

import gold_package_handoff as handoff  # noqa: E402

ADAPTER_PATH = ROOT / "src" / "career_os_cloud_operate_v1.py"
# SHA-256 of the exact bytes recovered from the live Drive adapter (Drive ID 19l9MNv7eF_PsFaFStiD9ZLFB45qf4rSd). Line endings are
# normalized to LF before hashing so a Windows autocrlf checkout does not change the identity.
RECOVERED_ADAPTER_SHA256 = "f10513d6ac36c58c31885c2ae35d52fb26b9f6218b6ba9f4aefb2206d3c275dc"
POINTER_PATH = ROOT / "docs" / "CAREER_OS_RECOVERY_POINTER_V1.md"
STANDARDS_PATH = ROOT / "docs" / "resume" / "BORA_RESUME_STANDARDS_V1.json"


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        print(f"FAIL: {message}")
        sys.stdout.flush()
        raise SystemExit(1)


def adapter_source() -> str:
    return ADAPTER_PATH.read_bytes().replace(b"\r\n", b"\n").decode("utf-8")


def test_adapter_exact_recovered_bytes() -> None:
    digest = hashlib.sha256(ADAPTER_PATH.read_bytes().replace(b"\r\n", b"\n")).hexdigest()
    assert_true(digest == RECOVERED_ADAPTER_SHA256, "the canonical adapter is byte-identical to the recovered live adapter: %s" % digest)
    print("PASS: the canonical cloud adapter is byte-identical to the recovered live Drive adapter.")


def test_adapter_profile_and_honesty() -> None:
    adapter = importlib.import_module("career_os_cloud_operate_v1")
    assert_true(adapter.PROFILE_ID == "CHATGPT_CLOUD_OPERATIONAL_RENDER_V1", "operational profile id")
    source = adapter_source()
    for needle in ('"operator_equivalent":False', '"submission_authority":"BORA_ONLY"', '"human_review":result[\'manifest\'][\'human_review\']',
                   '"human_review_waived": 0', '"label": "HUMAN_REQUIRED"', "VISUAL_REVIEW_OF_RAW_PDF_AND_DOCX",
                   "not byte-identical to the historical OPERATOR environment"):
        assert_true(needle in source, "adapter source keeps %s" % needle)
    # Canonical reuse and the retained checks.
    for needle in ("pursue_to_gold_package", "generate_gold_resume_stage", "load_validated_claim_repository", "load_validated_evidence_repository",
                   "validate_claim_lineage", "approved_identity_from_canonical_records", "gold_resume_docx_builder", "gold_resume_qa",
                   "fonts_from_manifest", "PAGE_GEOMETRY_MISMATCH", "(612.0, 792.0)", "FONT_IDENTITY_MISMATCH", "TEXT_EXTRACTION_PARITY_FAILED",
                   "ZERO_OPACITY_GRAPHICS_STATE", "TEXT_RENDER_MODE_3", "CANDIDATE_TRUTH_REPOSITORY_INVALID", "post_render_qa"):
        assert_true(needle in source or needle in (ROOT / "src" / "pursue_to_gold_package.py").read_text(encoding="utf-8"), "adapter/canonical path keeps %s" % needle)
    assert_true("document_render_adapter" not in source and "operator_verify" not in source, "the historical OPERATOR renderer machinery is not reproduced")
    print("PASS: the adapter keeps the operational profile, honesty fields, canonical reuse and the QA checks it was recovered with.")


def test_adapter_runtime_verification_fails_closed() -> None:
    adapter = importlib.import_module("career_os_cloud_operate_v1")
    root = Path(tempfile.mkdtemp(prefix="cloud-adapter-test-"))
    try:
        (root / "runtime_files.sha256").write_text("", encoding="utf-8")

        def attempt(manifest: dict) -> str:
            (root / "RUNTIME_MANIFEST.json").write_text(json.dumps(manifest), encoding="utf-8")
            try:
                adapter.verify_runtime(root)
            except RuntimeError as error:
                return str(error)
            return "NO_ERROR"

        assert_true(attempt({"spec": "WRONG"}) == "RUNTIME_MANIFEST_SPEC_MISMATCH", "wrong runtime spec fails closed")
        assert_true(attempt({"spec": "CAREER_OS_RUNTIME_BUNDLE_V1", "canonical_main_sha": "0" * 40}) == "RUNTIME_CANONICAL_SHA_MISMATCH", "wrong canonical SHA fails closed")
        good = {"spec": "CAREER_OS_RUNTIME_BUNDLE_V1", "canonical_main_sha": adapter.EXPECTED_MAIN_SHA}
        assert_true(attempt(good) == "NO_ERROR", "an empty-file-list bundle with matching identity verifies")
        (root / "runtime_files.sha256").write_text("%s  missing.txt\n" % ("0" * 64), encoding="utf-8")
        assert_true(attempt(good).startswith("RUNTIME_FILE_DIGEST_MISMATCH:missing.txt"), "a missing or altered runtime file fails closed")
    finally:
        shutil.rmtree(root, ignore_errors=True)
    print("PASS: runtime bundle verification fails closed on spec, canonical SHA and file digest.")


def test_adapter_run_request_sidecar() -> None:
    adapter = importlib.import_module("career_os_cloud_operate_v1")
    import pursue_to_gold_package as ptg

    out = Path(tempfile.mkdtemp(prefix="cloud-adapter-run-"))
    original_deps, original_stage = adapter.make_cloud_operate_deps, ptg.generate_gold_resume_stage
    seen = {}
    try:
        request_path = out / "request.json"
        request_path.write_text(json.dumps({"job_id": "FIXTURE::JOB"}), encoding="utf-8")
        adapter.make_cloud_operate_deps = lambda root, fonts, *, work_dir: "DEPS"

        def fake_stage(request, deps):
            seen["request"], seen["deps"] = request, deps
            package = out / "package"
            package.mkdir()
            return {"manifest": {"package_generation_id": "PGP_V1::fixture", "human_review": "REQUIRED_PENDING"}, "output_dir": str(package),
                    "post_render_qa": {"passed": True}}

        ptg.generate_gold_resume_stage = fake_stage
        adapter.run_request(str(request_path), str(out / "runtime"), str(out / "fonts"), str(out / "output"))
        assert_true(seen["deps"] == "DEPS" and seen["request"]["output_root"] == str(out / "output"), "run_request calls the canonical Gold resume stage with the cloud deps")
        sidecar = json.loads((out / "package" / "cloud_operate_manifest.json").read_text(encoding="utf-8"))
        assert_true(sidecar["profile"] == "CHATGPT_CLOUD_OPERATIONAL_RENDER_V1", "sidecar profile")
        assert_true(sidecar["operator_equivalent"] is False, "sidecar never claims OPERATOR equivalence")
        assert_true(sidecar["human_review"] == "REQUIRED_PENDING", "human visual review stays required")
        assert_true(sidecar["submission_authority"] == "BORA_ONLY", "submission stays Bora-only")
        assert_true("not byte-identical" in sidecar["note"], "runtime honesty note is preserved")
    finally:
        adapter.make_cloud_operate_deps, ptg.generate_gold_resume_stage = original_deps, original_stage
        shutil.rmtree(out, ignore_errors=True)
    print("PASS: run_request reuses the canonical Gold resume stage and writes an honest, Bora-only, human-review-required sidecar.")


def test_standards_record() -> None:
    record = json.loads(STANDARDS_PATH.read_text(encoding="utf-8"))
    content = record["standards"]["RESUME_CONTENT_STANDARD_V1"]
    fmt = record["standards"]["RESUME_FORMAT_STANDARD_V1"]
    assert_true(content["text"] == "Every experience section must prioritize recruiter-readable business/process impact over internal implementation detail; "
                "where verified evidence supports it, at least one bullet should state the outcome, risk reduced, time/quality/process improvement, "
                "or decision value created by the work.", "content standard is verbatim")
    assert_true(content["truth_clause"] == "Preserve truth. Never invent impact metrics or unsupported outcomes.", "truth clause is verbatim")
    assert_true(fmt["mechanics"] == [
        "BORA CHAUSH centered;", "contact line centered;", "candidate summary centered;",
        "Education school + right-aligned date on the same paragraph using a right tab stop;", "degree on the next line;",
        "Work Experience Title | Employer + right-aligned date using a right tab stop;", "no tables for Education/Work alignment;",
        "preserve one-page Gold section order, typography hierarchy, rules, hyperlinks and ≥92% utilization floor."], "format mechanics are verbatim")
    assert_true(record["consumed_by"]["operating_profile"] == "CHATGPT_CLOUD_OPERATIONAL_RENDER_V1", "the cloud lane names the standards it uses")
    # The mechanical items are enforced by the generator: centered name, contact and summary; right tabs; no tables.
    import pursue_to_gold_package_v1_test as gold
    import gold_resume_qa as qa

    parsed = qa.parse_docx(gold.build_fixture().docx_bytes)
    paragraphs = parsed["paragraphs"]
    assert_true(all(paragraphs[index]["centered"] for index in range(3)), "name, contact line and summary are centered")
    assert_true(b"<w:tbl>" not in parsed["raw_parts"]["word/document.xml"], "no tables are used for alignment")
    print("PASS: the two live resume standards are canonical, verbatim and enforced by the generator.")


def test_claim_wording_review_and_flags() -> None:
    import pursue_to_gold_package_v1_test as gold

    model, claims = gold.fixture_model(), gold.fixture_claims()
    review = handoff.claim_wording_review(model, claims)
    assert_true(review["spec"] == "GOLD_CLAIM_WORDING_REVIEW_V1" and review["human_review"] == "REQUIRED_PENDING", "review spec and pending human review")
    first = next(row for row in review["rows"] if row["location"] == "work:SYN_EXP_A:0")
    assert_true(first["candidate_text"] == gold.BULLETS["A1"], "candidate-facing text is shown verbatim")
    assert_true(first["cited_claims"] == [{"claim_id": "SYN_CLAIM_A1", "approved_claim_wording": claims["SYN_CLAIM_A1"]["wording"]}], "exact cited claim wording is shown beside it")
    assert_true(review["flagged_rows"] == 0, "faithful fixture bullets raise no advisory flag: %s" % [r for r in review["rows"] if r["advisory_flags"]])
    # Known failure class: still claim-linked, but the meaning is inverted.
    claim = {"claim_id": "C1", "wording": "Reduced manual reconciliation effort before month-end reporting."}
    assert_true(handoff.meaning_shift_flags("Increased manual reconciliation effort before month-end reporting.", claim["wording"]),
                "an inverted direction is flagged")
    assert_true(handoff.meaning_shift_flags("Automated reconciliation before month-end reporting.", claim["wording"]), "manual-to-automated inversion is flagged")
    assert_true(handoff.meaning_shift_flags("Reconciled transactions without errors.", "Reconciled transactions with documented errors."), "negation/with-without difference is flagged")
    assert_true(not handoff.meaning_shift_flags(claim["wording"], claim["wording"]), "identical wording is never flagged")
    inverted = json.loads(json.dumps(model))
    inverted["work"][0]["bullets"][0]["text"] = "Increased manual reconciliation effort before month-end reporting."
    claims["SYN_CLAIM_A1"]["wording"] = claim["wording"]
    flagged = handoff.claim_wording_review(inverted, claims)
    assert_true(flagged["flagged_rows"] == 1 and flagged["rows"][[r["location"] for r in flagged["rows"]].index("work:SYN_EXP_A:0")]["advisory_flags"], "the inverted bullet is surfaced in the review artifact")
    print("PASS: the claim-wording review pairs each bullet with its exact approved claim wording and flags the known inversion class.")


def test_package_persistence_inventory() -> None:
    root = Path(tempfile.mkdtemp(prefix="persist-test-"))
    try:
        package = root / "PGP_V1_fixture"
        package.mkdir()
        docx, pdf = b"docx-bytes", b"%PDF-fixture"
        for name in handoff.PACKAGE_FILES:
            (package / name).write_bytes({"resume.docx": docx, "resume.pdf": pdf}.get(name, b"{}\n"))
        (package / "manifest.json").write_text(json.dumps({"artifacts": [
            {"role": "resume_docx", "sha256": hashlib.sha256(docx).hexdigest()}, {"role": "resume_pdf", "sha256": hashlib.sha256(pdf).hexdigest()}]}), encoding="utf-8")
        (package / "cloud_operate_manifest.json").write_bytes(b"{}\n")
        inventory = handoff.package_persistence_inventory(package)
        names = [item["name"] for item in inventory["files"]]
        assert_true(inventory["complete"] and set(names) == set(handoff.PACKAGE_FILES) | set(handoff.CLOUD_LANE_FILES), "inventory covers every future package output: %s" % inventory["problems"])
        for required in ("resume.docx", "resume.pdf", "crosswalk.json", "pre_render_qa.json", "post_render_qa.json", "manifest.json", "cloud_operate_manifest.json"):
            assert_true(required in names, "inventory requires %s" % required)
        reported = {item["name"]: {"sha256": item["sha256"]} for item in inventory["files"]}
        assert_true(handoff.verify_persisted(inventory, reported)["status"] == "PERSISTED_COMPLETE", "exact hashes persist completely")
        assert_true(handoff.verify_persisted(inventory, {k: v for k, v in reported.items() if k != "resume.pdf"})["missing"] == ["resume.pdf"], "a missing file fails")
        assert_true(handoff.verify_persisted(inventory, {**reported, "resume.docx": {"sha256": "0" * 64}})["hash_mismatch"] == ["resume.docx"], "a hash mismatch fails")
        gap = handoff.verify_persisted(inventory, {**reported, "resume.docx": {"status": handoff.UNSUPPORTED_BY_CONNECTOR, "reason": "connector rejects DOCX bytes"}})
        assert_true(gap["status"] == "PERSISTED_WITH_RECORDED_GAPS" and gap["unsupported_recorded"][0]["name"] == "resume.docx", "an unsupported byte type is recorded honestly")
        silent = handoff.verify_persisted(inventory, {**reported, "resume.docx": {"status": handoff.UNSUPPORTED_BY_CONNECTOR}})
        assert_true(silent["status"] == "PERSISTENCE_FAILED", "an unsupported claim without a reason is a failure")
        (package / "resume.pdf").write_bytes(b"tampered")
        assert_true("MANIFEST_HASH_MISMATCH:resume.pdf" in handoff.package_persistence_inventory(package)["problems"], "files that disagree with the manifest are rejected")
        (package / "resume.pdf").write_bytes(pdf)
        (package / "stray.txt").write_bytes(b"x")
        assert_true("UNEXPECTED:stray.txt" in handoff.package_persistence_inventory(package)["problems"], "an unexpected file is rejected")
        (package / "stray.txt").unlink()
        (package / "crosswalk.json").unlink()
        assert_true("MISSING:crosswalk.json" in handoff.package_persistence_inventory(package)["problems"], "a missing package file is rejected")
    finally:
        shutil.rmtree(root, ignore_errors=True)
    print("PASS: the persistence inventory fixes the exact future package outputs, preserves exact hashes and records unsupported byte types honestly.")


def test_recovery_pointer() -> None:
    text = POINTER_PATH.read_text(encoding="utf-8")
    for needle in ("`OPERATE`", "1hublU84-xrWYKc8faO965oJVrdhyCL7stzug1C0GTNI", "Career OS — Production Ledger V1", "CAREER_OS_OPERATE_MODE_V1",
                   "`SETTINGS` tab is the live operating authority", "CHATGPT_CLOUD_OPERATIONAL_RENDER_V1", "engineering fallback only", "Cover-letter runtime",
                   "Bora alone decides `PURSUE` / `WATCH` / `REJECT`", "Bora alone submits externally", "outrank every historical continuity file",
                   "project_state.json", "CURRENT_EXECUTION_CHECKPOINT.json", "CURRENT_MILESTONE.md", "BORA_RESUME_STANDARDS_V1.json"):
        assert_true(needle in text, "recovery pointer states %s" % needle)
    assert_true("Historical / superseded" in (ROOT / "docs" / "CAREER_OS_OPERATOR_V1.md").read_text(encoding="utf-8"), "old routing is marked historical")
    print("PASS: the recovery pointer states the current operating facts and marks stale routing historical.")


TESTS = (test_adapter_exact_recovered_bytes, test_adapter_profile_and_honesty, test_adapter_runtime_verification_fails_closed,
         test_adapter_run_request_sidecar, test_standards_record, test_claim_wording_review_and_flags, test_package_persistence_inventory,
         test_recovery_pointer)


def main() -> None:
    for test in TESTS:
        test()
    print(f"PASS: {len(TESTS)} groups of career_os_final_hygiene_v1_test")


if __name__ == "__main__":
    main()
