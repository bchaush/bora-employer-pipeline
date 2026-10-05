"""Deterministic human-handoff helpers for a generated Gold resume package.

Two small, pure, dependency-free helpers; neither judges semantics, calls a model, performs I/O beyond reading a package
directory, or creates any approval or submission authority.

1. claim_wording_review: the side-by-side human review artifact. For every candidate-facing text it lists the exact text, the cited claim
   ID(s) and the exact approved claim wording, so Bora can see whether a claim-linked bullet still means what the claim means. It makes
   no semantic judgment of any kind: the visible side-by-side is the control. Written as claim_wording_review.json.

2. package_persistence_inventory / verify_persisted: the exact artifact inventory a normal operating run must persist to the role's
   Drive application folder, with exact SHA-256 hashes. The bytes are transferred by the ChatGPT Drive connector, not by repository
   code; this module only fixes WHAT must be persisted and checks what the connector reports back. A byte type the connector cannot
   upload is recorded as UNSUPPORTED_BY_CONNECTOR with a reason rather than worked around.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Optional

REVIEW_FILE = "claim_wording_review.json"
REVIEW_SPEC = "GOLD_CLAIM_WORDING_REVIEW_V1"

# Files pursue_to_gold_package.generate_gold_resume_stage writes into every package directory.
PACKAGE_FILES = (
    "resume.docx",
    "resume.pdf",
    "manifest.json",
    "crosswalk.json",
    "pre_render_qa.json",
    "post_render_qa.json",
    "rendered_document_evidence.json",
    REVIEW_FILE,
    "structure_map.json",
    "resume_model.json",
    "layout_report.json",
)
# Written next to the package by the CHATGPT_CLOUD_OPERATIONAL_RENDER_V1 lane (career_os_cloud_operate_v1.run_request) only.
CLOUD_LANE_FILES = ("cloud_operate_manifest.json",)
INVENTORY_FILE = "package_inventory.json"
META_FILES = (INVENTORY_FILE,)
UNSUPPORTED_BY_CONNECTOR = "UNSUPPORTED_BY_CONNECTOR"


def claim_wording_review(model: Mapping[str, Any], claims: Mapping[str, Any]) -> dict:
    """Candidate-facing text -> exact cited approved claim wording, derived only from the resume model and the claim bank."""
    from gold_resume_qa import candidate_facing_texts

    rows = []
    for location, text, claim_ids in candidate_facing_texts(model):
        cited = []
        for claim_id in claim_ids:
            claim = claims.get(claim_id) or {}
            wording = claim.get("wording")
            cited.append({"claim_id": claim_id, "approved_claim_wording": wording})
        rows.append({"location": location, "candidate_text": text, "cited_claims": cited})
    return {"spec": REVIEW_SPEC, "job_id": model.get("job_id"), "human_review": "REQUIRED_PENDING", "rows": rows}


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def format_claim_wording_review_table(review: Mapping[str, Any]) -> str:
    lines = ["location | candidate text | claim ID | approved claim wording"]
    for row in review.get("rows", []):
        cited = row.get("cited_claims", []) or [{"claim_id": "", "approved_claim_wording": ""}]
        for claim in cited:
            values = [row.get("location", ""), row.get("candidate_text", ""), claim.get("claim_id", ""), claim.get("approved_claim_wording", "")]
            lines.append(" | ".join(str(value).replace("\n", " ").replace("\r", " ") for value in values))
    return "\n".join(lines)


def package_persistence_inventory(package_dir: Any) -> dict:
    """The exact files to persist for one generated package, with byte sizes and SHA-256. Fails closed (problems list) when a required file
    is missing, an unexpected file is present, or the manifest's DOCX/PDF hashes disagree with the files on disk."""
    package_dir = Path(package_dir)
    present = {path.name for path in package_dir.iterdir() if path.is_file()} if package_dir.is_dir() else set()
    problems = ["MISSING:" + name for name in PACKAGE_FILES if name not in present]
    problems += ["UNEXPECTED:" + name for name in sorted(present - set(PACKAGE_FILES) - set(CLOUD_LANE_FILES) - set(META_FILES))]
    files = []
    for name in [*PACKAGE_FILES, *CLOUD_LANE_FILES]:
        if name in present:
            data = (package_dir / name).read_bytes()
            files.append({"name": name, "byte_size": len(data), "sha256": _sha(data), "lane": "CLOUD" if name in CLOUD_LANE_FILES else "PACKAGE"})
    if "manifest.json" in present and "resume.docx" in present and "resume.pdf" in present:
        manifest = json.loads((package_dir / "manifest.json").read_text(encoding="utf-8"))
        by_name = {item["name"]: item["sha256"] for item in files}
        for artifact in manifest.get("artifacts", []):
            name = {"resume_docx": "resume.docx", "resume_pdf": "resume.pdf"}.get(artifact.get("role"))
            if name and artifact.get("sha256") != by_name.get(name):
                problems.append("MANIFEST_HASH_MISMATCH:" + name)
    return {"package_dir_name": package_dir.name, "files": files, "problems": sorted(problems), "complete": not problems}


PERSIST_BUNDLE_ROLES = ("resume_pdf", "resume_docx", "package_bundle")


def persist_plan_inventory(plan: Mapping[str, Any]) -> dict:
    """The inventory of the exact three-file persist bundle (resume PDF, resume DOCX, package_bundle.zip) named by a persist plan.
    Anything other than exactly those three roles, each once, is an inventory problem rather than a silent partial bundle."""
    files = [dict(item) for item in plan.get("files", [])]
    problems = []
    if sorted(item.get("role") for item in files) != sorted(PERSIST_BUNDLE_ROLES):
        problems.append("BUNDLE_ROLES_NOT_EXACTLY_THREE")
    if len({item.get("name") for item in files}) != len(files):
        problems.append("BUNDLE_DUPLICATE_NAME")
    return {"package_dir_name": plan.get("target_folder_name"), "files": files, "problems": sorted(problems), "complete": not problems}


def verify_persisted(inventory: Mapping[str, Any], persisted: Mapping[str, Mapping[str, Any]], *, exact: bool = False) -> dict:
    """Compare what the Drive connector reports (name -> {"sha256": ...} or {"status": UNSUPPORTED_BY_CONNECTOR, "reason": ...}) with the
    inventory. A recorded unsupported byte type is an honest, visible gap; a missing, unexplained or hash-mismatched file is a failure."""
    if not inventory.get("complete"):
        return {"status": "PERSISTENCE_FAILED", "missing": [], "hash_mismatch": [], "size_mismatch": [], "unexpected": [], "unsupported_recorded": [], "inventory_problems": list(inventory.get("problems", []))}
    missing, mismatch, size_mismatch, unsupported = [], [], [], []
    for item in inventory["files"]:
        report: Optional[Mapping[str, Any]] = persisted.get(item["name"])
        if report is None:
            missing.append(item["name"])
        elif report.get("status") == UNSUPPORTED_BY_CONNECTOR:
            # An exact bundle has no honest gaps: an unsupported byte type means the bundle is not persisted.
            if report.get("reason") and not exact:
                unsupported.append({"name": item["name"], "reason": report["reason"]})
            else:
                missing.append(item["name"])
        elif report.get("sha256") != item["sha256"]:
            mismatch.append(item["name"])
        elif "byte_size" in report and "byte_size" in item and report["byte_size"] != item["byte_size"]:
            size_mismatch.append(item["name"])
    unexpected = sorted(set(persisted) - {item["name"] for item in inventory["files"]}) if exact else []
    failed = missing or mismatch or size_mismatch or unexpected
    status = "PERSISTENCE_FAILED" if failed else ("PERSISTED_WITH_RECORDED_GAPS" if unsupported else "PERSISTED_COMPLETE")
    return {"status": status, "missing": sorted(missing), "hash_mismatch": sorted(mismatch), "size_mismatch": sorted(size_mismatch), "unexpected": unexpected,
            "unsupported_recorded": unsupported, "inventory_problems": []}
