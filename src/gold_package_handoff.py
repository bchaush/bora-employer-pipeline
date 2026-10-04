"""Deterministic human-handoff helpers for a generated Gold resume package.

Two small, pure, dependency-free helpers; neither judges semantics, calls a model, performs I/O beyond reading a package
directory, or creates any approval or submission authority.

1. claim_wording_review: the side-by-side human review artifact. For every candidate-facing text it lists the exact text next to the
   exact approved claim wording it cites, so Bora can see whether a claim-linked bullet still means what the claim means. It also
   raises advisory, deterministic flags for the known meaning-shift class (a direction or negation that differs between the bullet and
   its cited claim wording). Flags never fail a package; they point the human reviewer at the line. Written as claim_wording_review.json.

2. package_persistence_inventory / verify_persisted: the exact artifact inventory a normal operating run must persist to the role's
   Drive application folder, with exact SHA-256 hashes. The bytes are transferred by the ChatGPT Drive connector, not by repository
   code; this module only fixes WHAT must be persisted and checks what the connector reports back. A byte type the connector cannot
   upload is recorded as UNSUPPORTED_BY_CONNECTOR with a reason rather than worked around.
"""

from __future__ import annotations

import hashlib
import json
import re
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
UNSUPPORTED_BY_CONNECTOR = "UNSUPPORTED_BY_CONNECTOR"

# Opposite-direction word pairs (stems). A flag is raised when the claim wording carries one side and the bullet carries only the other.
_OPPOSITE_STEMS = (
    ("increas", "decreas"), ("increas", "reduc"), ("increas", "lower"), ("rais", "lower"), ("improv", "worsen"),
    ("before", "after"), ("manual", "automat"), ("approv", "reject"), ("internal", "external"), ("with", "without"),
)
_NEGATIONS = ("no", "not", "never", "without", "cannot", "unable")


def _words(text: str) -> list:
    return re.findall(r"[a-z]+", text.lower())


def _has_stem(words: list, stem: str) -> bool:
    return any(word == stem if stem in ("with", "no", "not") else word.startswith(stem) for word in words)


def meaning_shift_flags(text: str, wording: str) -> list:
    """Advisory, deterministic flags: opposite-direction terms or negation present on one side only. Never a verdict."""
    bullet_words, claim_words = _words(text), _words(wording)
    flags = []
    for first, second in _OPPOSITE_STEMS:
        for claim_side, bullet_side in ((first, second), (second, first)):
            if _has_stem(claim_words, claim_side) and _has_stem(bullet_words, bullet_side) \
                    and not _has_stem(bullet_words, claim_side) and not _has_stem(claim_words, bullet_side):
                flags.append("DIRECTION_DIFFERS:claim=%s,bullet=%s" % (claim_side, bullet_side))
    bullet_negated = any(word in _NEGATIONS for word in bullet_words)
    claim_negated = any(word in _NEGATIONS for word in claim_words)
    if bullet_negated != claim_negated:
        flags.append("NEGATION_DIFFERS:claim=%s,bullet=%s" % (claim_negated, bullet_negated))
    return sorted(set(flags))


def claim_wording_review(model: Mapping[str, Any], claims: Mapping[str, Any]) -> dict:
    """Candidate-facing text -> exact cited approved claim wording, derived only from the resume model and the claim bank."""
    from gold_resume_qa import candidate_facing_texts

    rows = []
    for location, text, claim_ids in candidate_facing_texts(model):
        cited = []
        flags: list = []
        for claim_id in claim_ids:
            claim = claims.get(claim_id) or {}
            wording = claim.get("wording")
            cited.append({"claim_id": claim_id, "approved_claim_wording": wording})
            if wording is not None:
                flags += ["%s:%s" % (claim_id, flag) for flag in meaning_shift_flags(text, wording)]
        rows.append({"location": location, "candidate_text": text, "cited_claims": cited, "advisory_flags": sorted(flags)})
    return {"spec": REVIEW_SPEC, "job_id": model.get("job_id"), "human_review": "REQUIRED_PENDING",
            "flagged_rows": sum(1 for row in rows if row["advisory_flags"]), "rows": rows}


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def package_persistence_inventory(package_dir: Any) -> dict:
    """The exact files to persist for one generated package, with byte sizes and SHA-256. Fails closed (problems list) when a required file
    is missing, an unexpected file is present, or the manifest's DOCX/PDF hashes disagree with the files on disk."""
    package_dir = Path(package_dir)
    present = {path.name for path in package_dir.iterdir() if path.is_file()} if package_dir.is_dir() else set()
    problems = ["MISSING:" + name for name in PACKAGE_FILES if name not in present]
    problems += ["UNEXPECTED:" + name for name in sorted(present - set(PACKAGE_FILES) - set(CLOUD_LANE_FILES))]
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


def verify_persisted(inventory: Mapping[str, Any], persisted: Mapping[str, Mapping[str, Any]]) -> dict:
    """Compare what the Drive connector reports (name -> {"sha256": ...} or {"status": UNSUPPORTED_BY_CONNECTOR, "reason": ...}) with the
    inventory. A recorded unsupported byte type is an honest, visible gap; a missing, unexplained or hash-mismatched file is a failure."""
    if not inventory.get("complete"):
        return {"status": "PERSISTENCE_FAILED", "missing": [], "hash_mismatch": [], "unsupported_recorded": [], "inventory_problems": list(inventory.get("problems", []))}
    missing, mismatch, unsupported = [], [], []
    for item in inventory["files"]:
        report: Optional[Mapping[str, Any]] = persisted.get(item["name"])
        if report is None:
            missing.append(item["name"])
        elif report.get("status") == UNSUPPORTED_BY_CONNECTOR:
            if report.get("reason"):
                unsupported.append({"name": item["name"], "reason": report["reason"]})
            else:
                missing.append(item["name"])
        elif report.get("sha256") != item["sha256"]:
            mismatch.append(item["name"])
    status = "PERSISTENCE_FAILED" if missing or mismatch else ("PERSISTED_WITH_RECORDED_GAPS" if unsupported else "PERSISTED_COMPLETE")
    return {"status": status, "missing": sorted(missing), "hash_mismatch": sorted(mismatch), "unsupported_recorded": unsupported, "inventory_problems": []}
