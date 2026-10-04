"""PURSUE_TO_GOLD_PACKAGE_V1 local runtime (model-built Gold resume path).

Turns exactly one currently valid Bora PURSUE into a local, unsubmitted Gold resume stage: derived pursuit state ->
package-time actionability attestation -> canonical JD requirements -> canonical Requirement/EvidenceMatch ->
JD-to-evidence crosswalk -> approved Candidate Truth and claim/evidence lineage -> approved role-tailored Gold resume
model -> deterministic Gold DOCX and structure map from the SAME model -> the canonically released renderer, called
only through its public interface -> executable Gold QA -> local outputs and a deterministic manifest.

The runtime is pure apart from reading canonical repository records and writing the caller-designated local output
directory. It performs no JOBS, LOG, Application Truth, Drive, Sheets or Gmail I/O, mutates none of its inputs, never
submits, and creates no submission authority. Human visual review always remains pending.

Cover-letter boundary: the cover-letter pair is not produced here (the Gold cover-letter DOCX carries parts that the
released preflight rejects). generate_gold_package therefore fails closed with PACKAGE_CAPABILITY_BLOCKED and emits
no output; it never degrades to a resume-only package. generate_gold_resume_stage is the resume stage that tests and
the OPERATOR regression exercise; its manifest records that the cover-letter pair was not produced.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Mapping, Optional, Sequence

from gold_resume_docx_builder import (
    FontMetrics,
    GoldBuildError,
    GoldMetrics,
    build_gold_docx,
    canonical_json_bytes,
    expected_links,
    fonts_from_manifest,
    load_doctrine_roster,
    load_gold_metrics,
    model_digest,
)
from gold_resume_qa import post_render_qa, pre_render_qa, read_pdf_facts
from pursuit_decision import PursuitDecisionError, compute_context_fingerprint, derive_current_pursuit_state
from schema_validation import build_draft202012_validator

ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = ROOT / "schemas"
REQUEST_SCHEMA = SCHEMAS / "gold_package_request.schema.json"
MANIFEST_SCHEMA = SCHEMAS / "gold_package_manifest.schema.json"
MODEL_SCHEMA = SCHEMAS / "gold_resume_model.schema.json"
REQUIREMENT_SCHEMA = SCHEMAS / "requirement.schema.json"
EVIDENCE_MATCH_SCHEMA = SCHEMAS / "evidence_match.schema.json"
PACKAGE_CAPABILITY_BLOCKED = "PACKAGE_CAPABILITY_BLOCKED"
PACKAGE_ID_PREFIX = "PGP_V1::"
STAGE_STATUS = "GOLD_RESUME_STAGE_READY_COVER_LETTER_PAIR_NOT_PRODUCED"


class PackageError(Exception):
    """Fail-closed package outcome with a stable CODE; no output is left behind."""

    def __init__(self, code: str, detail: str = "", report: Optional[Mapping[str, Any]] = None) -> None:
        super().__init__(code, detail)
        self.code = code
        self.detail = detail
        self.report = dict(report or {})


@dataclass
class PackageDeps:
    """Every external effect, injected. Production wiring is make_governed_deps; tests inject deterministic fakes."""

    load_claims: Callable[[], Mapping[str, Any]]
    validate_lineage: Callable[[Mapping[str, Any]], list]
    identity_provider: Callable[[], Mapping[str, Any]]
    fonts: FontMetrics
    render: Callable[[bytes, list, str], tuple]  # (docx_bytes, structure_map, out_dir) -> (record, pdf_bytes or None)
    renderer_identity: Callable[[], Mapping[str, str]]
    pdf_facts: Callable[[bytes], Mapping[str, Any]] = read_pdf_facts
    current_state: Optional[Callable[[str], tuple]] = None  # job_id -> (jobs_row, decision_log_rows) re-read at the end
    doctrine_root: Path = ROOT
    roster: Optional[Sequence[str]] = None  # default: the canonical doctrine roster (tests may inject a synthetic one)


def _digest(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _validator(path: Path):
    return build_draft202012_validator(path)


def _schema_errors(path: Path, instance: Any) -> list:
    return sorted(error.message for error in _validator(path).iter_errors(instance))


# Gates ------------------------------------------------------------------------------------------

def run_gates(request: Mapping[str, Any]) -> dict:
    """Request validation, subject, derived PURSUE, attestation bindings, requirements, EvidenceMatch and crosswalk.
    Everything here is pure and fails closed before any package work."""
    errors = _schema_errors(REQUEST_SCHEMA, request)
    if errors:
        raise PackageError("REQUEST_INVALID", errors[0])
    job_id = request["job_id"]
    rows = [row for row in request["jobs_rows"] if row.get("Job_ID") == job_id]
    if len(rows) != 1:
        raise PackageError("UNKNOWN_JOB_ID", "job_id must match exactly one canonical JOBS row")
    row = rows[0]
    try:
        state = derive_current_pursuit_state(row, request["decision_log_rows"])
        fingerprint = compute_context_fingerprint(row)
    except PursuitDecisionError as error:
        raise PackageError("PURSUIT_STATE_DERIVATION_FAILED", str(error)) from error
    if state.get("state") != "PURSUE" or state.get("authorizes_pursuit") is not True:
        raise PackageError("PURSUIT_NOT_AUTHORIZED", "derived state is %s" % state.get("state"))
    attestation = request["attestation"]
    if attestation["job_id"] != job_id:
        raise PackageError("ATTESTATION_JOB_MISMATCH")
    if attestation["latest_event_id"] != state["latest_event_id"]:
        raise PackageError("ATTESTATION_EVENT_MISMATCH")
    if attestation["decision_context_fingerprint"] != fingerprint:
        raise PackageError("ATTESTATION_FINGERPRINT_MISMATCH")
    if not row.get("Official_URL") or attestation["application_destination_url"] != row["Official_URL"]:
        raise PackageError("ATTESTATION_DESTINATION_MISMATCH")
    if not all(attestation["semantic_quorum"].values()) or attestation["dead_state_veto"] is not False:
        raise PackageError("ATTESTATION_QUORUM_NOT_POSITIVE")
    requirements = sorted(request["requirements"], key=lambda item: str(item.get("requirement_id")))
    for requirement in requirements:
        errors = _schema_errors(REQUIREMENT_SCHEMA, requirement)
        if errors:
            raise PackageError("REQUIREMENT_INVALID", errors[0])
        if requirement["job_id"] != job_id:
            raise PackageError("REQUIREMENT_JOB_MISMATCH")
    requirement_ids = {requirement["requirement_id"] for requirement in requirements}
    matches = sorted(request["evidence_matches"], key=lambda item: str(item.get("match_id")))
    for match in matches:
        errors = _schema_errors(EVIDENCE_MATCH_SCHEMA, match)
        if errors:
            raise PackageError("EVIDENCE_MATCH_INVALID", errors[0])
        if match["job_id"] != job_id or match["requirement_id"] not in requirement_ids:
            raise PackageError("EVIDENCE_MATCH_BINDING_MISMATCH")
    by_requirement: dict = {}
    for match in matches:
        by_requirement.setdefault(match["requirement_id"], []).append(match)
    crosswalk = []
    for requirement in requirements:
        entries = by_requirement.get(requirement["requirement_id"], [])
        crosswalk.append({"requirement_id": requirement["requirement_id"],
                          "results": sorted({entry["result"] for entry in entries}) or ["UNMATCHED"],
                          "claim_ids": sorted({claim for entry in entries for claim in entry["claim_ids"]}),
                          "evidence_ids": sorted({evidence for entry in entries for evidence in entry["evidence_ids"]})})
    return {"job_id": job_id, "row": row, "state": state, "fingerprint": fingerprint, "attestation": attestation,
            "requirements": requirements, "matches": matches, "crosswalk": crosswalk}


def package_generation_id(*, job_id: str, latest_event_id: str, fingerprint: str, doctrine_digest: str, model_digest_value: str,
                          jd_digest: str, match_digest: str, attestation_digest: str, package_run_id: str) -> str:
    return PACKAGE_ID_PREFIX + _digest({
        "Job_ID": job_id, "latest_event_id": latest_event_id, "decision_context_fingerprint": fingerprint,
        "resume_gold_doctrine_digest": doctrine_digest, "resume_model_digest": model_digest_value,
        "cover_letter_gold_sha256": None, "cover_letter_opt_out_record_digest": None,
        "jd_requirements_digest": jd_digest, "evidence_match_digest": match_digest,
        "actionability_attestation_digest": attestation_digest, "package_run_id": package_run_id})


# Resume stage -----------------------------------------------------------------------------------

def generate_gold_resume_stage(request: Mapping[str, Any], deps: PackageDeps) -> dict:
    """The resume stage. Returns the manifest, the output directory and both QA reports; raises PackageError with no
    output left behind on any failure."""
    frozen_request = copy.deepcopy(request)
    gates = run_gates(frozen_request)
    model = frozen_request["resume_model"]
    errors = _schema_errors(MODEL_SCHEMA, model)
    if errors:
        raise PackageError("RESUME_MODEL_INVALID", errors[0])
    if model["job_id"] != gates["job_id"]:
        raise PackageError("RESUME_MODEL_JOB_MISMATCH")
    claims = deps.load_claims()
    for claim_id in sorted({claim for _name, _text, ids in _texts(model) for claim in ids}):
        claim = claims.get(claim_id)
        if claim is None:
            raise PackageError("CLAIM_NOT_FOUND", claim_id)
        lineage_errors = deps.validate_lineage(claim)
        if lineage_errors:
            raise PackageError("CLAIM_LINEAGE_INVALID", "%s: %s" % (claim_id, lineage_errors[0]))
    identity = deps.identity_provider()
    try:
        metrics, doctrine_digests = load_gold_metrics(deps.doctrine_root)
        build = build_gold_docx(model, metrics, deps.fonts)
    except GoldBuildError as error:
        raise PackageError("GOLD_BUILD_FAILED_" + error.code, error.detail) from error
    pre = pre_render_qa(model, build, metrics=metrics, claims=claims, identity=identity,
                        rebuild=lambda: build_gold_docx(model, metrics, deps.fonts), roster=list(deps.roster) if deps.roster is not None else load_doctrine_roster(deps.doctrine_root),
                        job_relevant_terms=tuple(frozen_request.get("job_relevant_terms", [])))
    if not pre["passed"]:
        raise PackageError("GOLD_PRE_RENDER_QA_FAILED", ",".join(pre["failed_checks"]), pre)
    staging = Path(tempfile.mkdtemp(prefix="gold-stage-", dir=_ensure_dir(frozen_request["output_root"])))
    try:
        render_dir = str(staging / "render")
        record, pdf_bytes = deps.render(build.docx_bytes, build.structure_map, render_dir)
        if not pdf_bytes:
            raise PackageError("RENDER_NOT_DELIVERED", "%s / %s" % (record.get("run_status"), record.get("reason")), {"record": record})
        post = post_render_qa(record, pdf_facts=deps.pdf_facts(pdf_bytes), expected=expected_links(model))
        if not post["passed"]:
            raise PackageError("GOLD_POST_RENDER_QA_FAILED", ",".join(post["failed_checks"]), post)
        # Stale-input detection immediately before writing outputs.
        if deps.current_state is not None:
            fresh_row, fresh_log = deps.current_state(gates["job_id"])
            try:
                fresh = derive_current_pursuit_state(fresh_row, fresh_log)
                fresh_fingerprint = compute_context_fingerprint(fresh_row)
            except PursuitDecisionError as error:
                raise PackageError("STALE_INPUT_DETECTED", str(error)) from error
            if fresh.get("state") != "PURSUE" or fresh.get("latest_event_id") != gates["state"]["latest_event_id"] \
                    or fresh_fingerprint != gates["fingerprint"]:
                raise PackageError("STALE_INPUT_DETECTED", "pursuit context changed during package generation")
        doctrine_digest = _digest(doctrine_digests)
        jd_digest = _digest(gates["requirements"])
        match_digest = _digest(gates["matches"])
        attestation_digest = _digest(gates["attestation"])
        generation_id = package_generation_id(
            job_id=gates["job_id"], latest_event_id=gates["state"]["latest_event_id"], fingerprint=gates["fingerprint"],
            doctrine_digest=doctrine_digest, model_digest_value=model_digest(model), jd_digest=jd_digest, match_digest=match_digest,
            attestation_digest=attestation_digest, package_run_id=frozen_request["package_run_id"])
        renderer = dict(deps.renderer_identity())
        manifest = {
            "spec": "GOLD_PACKAGE_MANIFEST_V1", "package_generation_id": generation_id, "package_run_id": frozen_request["package_run_id"],
            "job_id": gates["job_id"], "latest_event_id": gates["state"]["latest_event_id"],
            "decision_context_fingerprint": gates["fingerprint"], "gold_doctrine_digests": doctrine_digests,
            "gold_doctrine_digest": doctrine_digest, "resume_model_digest": model_digest(model),
            "structure_map_digest": _digest(build.structure_map), "expected_links_digest": _digest([[l.label, l.url] for l in build.expected_links]),
            "jd_requirements_digest": jd_digest, "evidence_match_digest": match_digest, "crosswalk_digest": _digest(gates["crosswalk"]),
            "attestation_digest": attestation_digest, "cover_letter_gold_sha256": None, "cover_letter_opt_out_digest": None,
            "renderer": {"adapter_sha256": renderer["adapter_sha256"], "operator_verification_evidence_digest": renderer["operator_verification_evidence_digest"]},
            "artifacts": [{"role": "resume_docx", "format": "DOCX", "sha256": hashlib.sha256(build.docx_bytes).hexdigest(), "byte_size": len(build.docx_bytes)},
                          {"role": "resume_pdf", "format": "PDF", "sha256": hashlib.sha256(pdf_bytes).hexdigest(), "byte_size": len(pdf_bytes)}],
            "pre_render_qa_digest": pre["result_digest"], "post_render_qa_digest": post["result_digest"],
            "package_status": STAGE_STATUS, "human_review": "REQUIRED_PENDING", "submission_authority": "NONE"}
        manifest_errors = _schema_errors(MANIFEST_SCHEMA, manifest)
        if manifest_errors:
            raise PackageError("MANIFEST_INVALID", manifest_errors[0])
        manifest_bytes = canonical_json_bytes(manifest) + b"\n"
        final_dir = Path(frozen_request["output_root"]) / generation_id.replace("::", "_")
        if final_dir.exists():
            existing = final_dir / "manifest.json"
            if existing.exists() and existing.read_bytes() == manifest_bytes:
                shutil.rmtree(staging)
                return {"manifest": manifest, "output_dir": str(final_dir), "pre_render_qa": pre, "post_render_qa": post, "replayed": True}
            raise PackageError("CONFLICTING_REPLAY", "package_generation_id already exists with different content")
        _write(staging / "resume.docx", build.docx_bytes)
        _write(staging / "resume.pdf", pdf_bytes)
        _write(staging / "structure_map.json", canonical_json_bytes(build.structure_map) + b"\n")
        _write(staging / "resume_model.json", canonical_json_bytes(model) + b"\n")
        _write(staging / "crosswalk.json", canonical_json_bytes(gates["crosswalk"]) + b"\n")
        _write(staging / "rendered_document_evidence.json", canonical_json_bytes(record) + b"\n")
        _write(staging / "pre_render_qa.json", canonical_json_bytes(pre) + b"\n")
        _write(staging / "post_render_qa.json", canonical_json_bytes(post) + b"\n")
        _write(staging / "layout_report.json", canonical_json_bytes(build.layout) + b"\n")
        shutil.rmtree(staging / "render", ignore_errors=True)
        _write(staging / "manifest.json", manifest_bytes)
        os.replace(str(staging), str(final_dir))
        return {"manifest": manifest, "output_dir": str(final_dir), "pre_render_qa": pre, "post_render_qa": post, "replayed": False}
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def generate_gold_package(request: Mapping[str, Any], deps: PackageDeps) -> dict:
    """The full package contract: the resume stage plus the cover-letter pair. The cover-letter pair cannot be produced
    through the released renderer today, so after the gates pass this fails closed with PACKAGE_CAPABILITY_BLOCKED, emits
    no output and never degrades to a resume-only package. A cover-letter opt-out record is never authority by itself:
    no existing authoritative Bora-controlled approval surface can be consumed here, so one is refused as well."""
    run_gates(copy.deepcopy(request))
    if request.get("cover_letter_opt_out") is not None:
        raise PackageError(PACKAGE_CAPABILITY_BLOCKED, "COVER_LETTER_OPT_OUT_PROVENANCE_UNAVAILABLE")
    raise PackageError(PACKAGE_CAPABILITY_BLOCKED, "COVER_LETTER_PAIR_NOT_PRODUCIBLE_THROUGH_RELEASED_RENDERER")


def _texts(model: Mapping[str, Any]) -> list:
    from gold_resume_qa import candidate_facing_texts
    return candidate_facing_texts(model)


def _ensure_dir(path: str) -> str:
    os.makedirs(path, exist_ok=True)
    return path


def _write(path: Path, data: bytes) -> None:
    path.write_bytes(data)


# Production wiring ------------------------------------------------------------------------------

def default_identity_from_master(root: Path) -> dict:
    """The approved identity currently held by canonical records: the protected resume master. It carries no approved
    GitHub link and no Gold-grammar education display strings, so a Gold model built from it fails identity QA until
    Bora approves those records; nothing is invented here."""
    master = json.loads((Path(root) / "resume" / "master" / "RESUME_MASTER_WW_V1.json").read_text(encoding="utf-8"))
    contact = master["contact"]
    links = []
    linkedin = contact.get("linkedin") or ""
    if linkedin.startswith(("https://", "http://")):
        links.append({"label": "LinkedIn", "url": linkedin})
    return {"contact": {"name": contact["name"], "location": contact.get("location"), "phone": contact.get("phone"),
                        "email": contact["email"], "profile_links": links},
            "education": [{"school": item["school_name"], "date_range": item["date_range"], "degree_line": item["degree_name"]}
                          for item in master["education"]],
            "experiences": {}, "project_links": {}}


def governed_render_function(root: Path, *, verification_record: Mapping[str, Any], work_dir: str) -> Callable[[bytes, list, str], tuple]:
    """The released renderer through its public interface (run_first_render under the governed interpreter): writes the
    DOCX and structure map to WORK_DIR, renders into the fresh OUT_DIR and returns (record, delivered PDF bytes or None)."""
    import document_render_adapter as adapter

    root = Path(root)
    manifest_bytes = (root / "docs" / "rendering" / "RENDERING_ENVIRONMENT_V1.json").read_bytes()

    def render(docx_bytes: bytes, structure_map: list, out_dir: str) -> tuple:
        os.makedirs(work_dir, exist_ok=True)
        docx_path = os.path.join(work_dir, "input.docx")
        map_path = os.path.join(work_dir, "structure_map.json")
        Path(docx_path).write_bytes(docx_bytes)
        Path(map_path).write_text(json.dumps(structure_map, ensure_ascii=False), encoding="utf-8")
        outcome = adapter.run_first_render(root, manifest_bytes, docx_path, hashlib.sha256(docx_bytes).hexdigest(), out_dir, map_path,
                                           verification_record=dict(verification_record))
        pdf = Path(outcome["pdf_path"]).read_bytes() if outcome["pdf_path"] else None
        return outcome["record"], pdf

    return render


def make_governed_deps(root: Path, *, verification_record: Mapping[str, Any], work_dir: str,
                       current_state: Optional[Callable[[str], tuple]] = None) -> PackageDeps:
    """Production dependencies: canonical claim/evidence repositories, the released renderer through its public
    interface (run_first_render under the governed interpreter) and pypdf link facts. Requires the OPERATOR runtime."""
    from claim_lineage import validate_claim_lineage
    from claim_repository import load_validated_claim_repository
    from evidence_repository import load_validated_evidence_repository

    root = Path(root)
    manifest_bytes = (root / "docs" / "rendering" / "RENDERING_ENVIRONMENT_V1.json").read_bytes()
    manifest = json.loads(manifest_bytes.decode("utf-8"))
    claims_result = load_validated_claim_repository(root / "claims")
    evidence_result = load_validated_evidence_repository(root / "evidence")
    if not claims_result["valid"] or not evidence_result["valid"]:
        raise PackageError("CANDIDATE_TRUTH_REPOSITORY_INVALID")
    fonts = fonts_from_manifest(manifest, lambda path: Path(path).read_bytes())
    adapter_sha = hashlib.sha256((root / "src" / "document_render_adapter.py").read_bytes()).hexdigest()

    def lineage(claim: Mapping[str, Any]) -> list:
        result = validate_claim_lineage(claim, evidence_result["index"])
        return [] if result.get("valid") else [str(item) for item in result.get("errors", [])] or ["LINEAGE_INVALID"]

    render = governed_render_function(root, verification_record=verification_record, work_dir=work_dir)

    return PackageDeps(load_claims=lambda: claims_result["index"], validate_lineage=lineage,
                       identity_provider=lambda: default_identity_from_master(root), fonts=fonts, render=render,
                       renderer_identity=lambda: {"adapter_sha256": adapter_sha,
                                                  "operator_verification_evidence_digest": verification_record["evidence_digest"]},
                       current_state=current_state, doctrine_root=root)
