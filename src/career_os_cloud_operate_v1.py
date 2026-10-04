from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable, Mapping, Optional

PROFILE_ID = "CHATGPT_CLOUD_OPERATIONAL_RENDER_V1"
EXPECTED_MAIN_SHA = "c28314c49cb608db801059dd82b210bb7205d475"


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def verify_runtime(root: Path, expected_main_sha: str = EXPECTED_MAIN_SHA) -> dict:
    root = Path(root)
    manifest_path = root / "RUNTIME_MANIFEST.json"
    sums_path = root / "runtime_files.sha256"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("spec") != "CAREER_OS_RUNTIME_BUNDLE_V1":
        raise RuntimeError("RUNTIME_MANIFEST_SPEC_MISMATCH")
    if manifest.get("canonical_main_sha") != expected_main_sha:
        raise RuntimeError("RUNTIME_CANONICAL_SHA_MISMATCH")
    failures = []
    count = 0
    for line in sums_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        digest, rel = line.split(None, 1)
        rel = rel.strip()
        if rel.startswith("*"):
            rel = rel[1:]
        if rel.startswith("./"):
            rel = rel[2:]
        p = root / rel
        count += 1
        if not p.is_file() or _sha(p.read_bytes()) != digest:
            failures.append(rel)
    if failures:
        raise RuntimeError("RUNTIME_FILE_DIGEST_MISMATCH:" + ",".join(failures[:10]))
    return {"manifest": manifest, "verified_file_count": count}


def _font_reader(font_dir: Path) -> Callable[[str], bytes]:
    font_dir = Path(font_dir)
    def read(path: str) -> bytes:
        p = font_dir / Path(path).name
        if not p.is_file():
            raise FileNotFoundError(str(p))
        return p.read_bytes()
    return read


def verify_fonts(root: Path, font_dir: Path):
    sys.path.insert(0, str(Path(root) / "src"))
    import gold_resume_docx_builder as builder
    manifest = json.loads((Path(root) / "docs" / "rendering" / "RENDERING_ENVIRONMENT_V1.json").read_text(encoding="utf-8"))
    return builder.fonts_from_manifest(manifest, _font_reader(Path(font_dir)))


def _fontconfig(font_dir: Path, work_dir: Path) -> Path:
    cache = work_dir / "fontcache"
    cache.mkdir(parents=True, exist_ok=True)
    path = work_dir / "fontconfig.xml"
    xml = f'''<?xml version="1.0"?>\n<!DOCTYPE fontconfig SYSTEM "urn:fontconfig:fonts.dtd">\n<fontconfig>\n  <dir>{font_dir}</dir>\n  <cachedir>{cache}</cachedir>\n  <config><rescan><int>0</int></rescan></config>\n</fontconfig>\n'''
    path.write_text(xml, encoding="utf-8")
    return path


def _normalized(text: str) -> str:
    return " ".join(re.findall(r"[A-Za-z0-9@.+:/_-]+", text.lower()))


def _paragraphs_present(structure_map: list, pdf_text: str) -> bool:
    hay = _normalized(pdf_text)
    # All meaningful paragraph text should survive. We use token-order subsequence rather than exact spacing/wrapping.
    hay_tokens = hay.split()
    for item in structure_map:
        text = str(item.get("paragraph_text") or "").strip()
        if not text:
            continue
        tokens = _normalized(text).split()
        if not tokens:
            continue
        pos = 0
        for token in hay_tokens:
            if pos < len(tokens) and token == tokens[pos]:
                pos += 1
        if pos != len(tokens):
            return False
    return True


def _hidden_text_findings(pdf_bytes: bytes) -> list[dict]:
    from io import BytesIO
    from pypdf import PdfReader
    findings = []
    reader = PdfReader(BytesIO(pdf_bytes), strict=True)
    for page_index, page in enumerate(reader.pages):
        resources = page.get("/Resources") or {}
        try:
            resources = resources.get_object()
        except Exception:
            pass
        ext = resources.get("/ExtGState") if hasattr(resources, "get") else None
        if ext is not None:
            try:
                ext = ext.get_object()
            except Exception:
                pass
            if hasattr(ext, "items"):
                for name, state in ext.items():
                    try:
                        state = state.get_object()
                    except Exception:
                        pass
                    if hasattr(state, "get") and (state.get("/ca") == 0 or state.get("/CA") == 0):
                        findings.append({"code": "ZERO_OPACITY_GRAPHICS_STATE", "page": page_index, "state": str(name)})
        try:
            content = page.get_contents()
            operations = getattr(content, "operations", []) if content is not None else []
            for operands, operator in operations:
                if operator == b"Tr" and operands and int(operands[0]) == 3:
                    findings.append({"code": "TEXT_RENDER_MODE_3", "page": page_index})
        except Exception as exc:
            findings.append({"code": "HIDDEN_TEXT_SCAN_ERROR", "page": page_index, "detail": exc.__class__.__name__})
    return findings


def make_cloud_renderer(root: Path, font_dir: Path, *, work_dir: Path):
    root, font_dir, work_dir = Path(root), Path(font_dir), Path(work_dir)
    sys.path.insert(0, str(root / "src"))
    import gold_resume_qa as qa
    import pdfplumber

    font_hashes = {p.name: _sha(p.read_bytes()) for p in sorted(font_dir.glob("*.ttf"))}

    def render(docx_bytes: bytes, structure_map: list, out_dir: str):
        target = Path(out_dir)
        target.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="career-os-cloud-render-", dir=str(work_dir)) as temp:
            tmp = Path(temp)
            docx = tmp / "resume.docx"
            docx.write_bytes(docx_bytes)
            profile = tmp / "lo-profile"
            profile.mkdir()
            fc = _fontconfig(font_dir, tmp)
            env = os.environ.copy()
            env["FONTCONFIG_FILE"] = str(fc)
            cmd = ["libreoffice", "--headless", f"-env:UserInstallation=file://{profile}", "--convert-to", "pdf", "--outdir", str(tmp), str(docx)]
            proc = subprocess.run(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60, check=False)
            pdf_path = tmp / "resume.pdf"
            if proc.returncode != 0 or not pdf_path.is_file():
                record = {"run_status": "RENDER_QA_FAILED", "delivered": 0, "reason": "CLOUD_LIBREOFFICE_FAILED", "findings": [{"code": "LIBREOFFICE_FAILED", "exit_code": proc.returncode}], "human_review_waived": 0}
                return record, b""
            lo_version = subprocess.run(["libreoffice", "--version"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, check=False).stdout.strip()
            raw_pdf_bytes = pdf_path.read_bytes()
            # LibreOffice writes a random trailer /ID. Normalize only volatile metadata/ID so
            # identical Career OS input produces byte-identical operational PDF bytes.
            from io import BytesIO
            from pypdf import PdfReader, PdfWriter
            from pypdf.generic import ArrayObject, ByteStringObject
            reader = PdfReader(BytesIO(raw_pdf_bytes), strict=True)
            writer = PdfWriter(clone_from=reader)
            writer.metadata = {
                "/Creator": "Writer",
                "/Producer": lo_version if 'lo_version' in locals() else "Career OS Cloud LibreOffice",
                "/CreationDate": "D:20000101000000Z",
            }
            stable_id = hashlib.sha256(docx_bytes).digest()[:16]
            writer._ID = ArrayObject([ByteStringObject(stable_id), ByteStringObject(stable_id)])
            buffer = BytesIO()
            writer.write(buffer)
            pdf_bytes = buffer.getvalue()
            normalized_pdf = tmp / "resume.normalized.pdf"
            normalized_pdf.write_bytes(pdf_bytes)
            facts = qa.read_pdf_facts(pdf_bytes)
            findings = []
            if facts.get("page_count") != 1 or facts.get("pages") != [(612.0, 792.0)]:
                findings.append({"code": "PAGE_GEOMETRY_MISMATCH", "facts": facts})
            hidden = _hidden_text_findings(pdf_bytes)
            findings.extend(hidden)
            with pdfplumber.open(normalized_pdf) as pdf:
                page = pdf.pages[0]
                chars = [c for c in page.chars if str(c.get("text", "")).strip()]
                text = page.extract_text() or ""
                bottom = max((float(c["bottom"]) for c in chars), default=0.0)
                utilization = bottom / float(page.height) if page.height else 0.0
                font_names = sorted({str(c.get("fontname")) for c in chars})
            if not font_names or any("LiberationSans" not in name.replace("+", "") for name in font_names):
                findings.append({"code": "FONT_IDENTITY_MISMATCH", "fonts": font_names})
            if not _paragraphs_present(structure_map, text):
                findings.append({"code": "TEXT_EXTRACTION_PARITY_FAILED"})
            semantic = {"text": _normalized(text), "page_count": facts.get("page_count"), "pages": facts.get("pages"), "links": sorted(facts.get("links", [])), "fonts": font_names, "utilization_q": round(utilization, 6)}
            env_evidence = {"profile": PROFILE_ID, "python": sys.version.split()[0], "platform": platform.platform(), "libreoffice": lo_version, "font_hashes": font_hashes, "docx_sha256": _sha(docx_bytes), "pdf_sha256": _sha(pdf_bytes), "structure_map_sha256": _sha(_canonical_bytes(structure_map))}
            record = {
                "run_status": qa.RENDER_PASS_STATUS if not findings else "RENDER_QA_FAILED",
                "delivered": 1,
                "reason": None if not findings else "CLOUD_OPERATIONAL_QA_FINDING",
                "utilization": {"meaningful_content_bottom_fraction": utilization},
                "findings": findings,
                "attribution_digest": _sha(_canonical_bytes(env_evidence)),
                "render_semantic_fingerprint": _sha(_canonical_bytes(semantic)),
                "automated_checks": [
                    {"check": "FONT_EMBEDDING_AND_IDENTITY", "label": "AUTOMATED"},
                    {"check": "CLOUD_TEXT_EXTRACTION_PARITY", "label": "AUTOMATED"},
                    {"check": "CLOUD_HIDDEN_TEXT_OPERATOR_SCAN", "label": "AUTOMATED"},
                    {"check": "CLOUD_RUNTIME_ENVIRONMENT_CAPTURE", "label": "AUTOMATED"},
                ],
                "human_required": [{"check": "VISUAL_REVIEW_OF_RAW_PDF_AND_DOCX", "label": "HUMAN_REQUIRED"}],
                "human_review_waived": 0,
                "cloud_operational_profile": PROFILE_ID,
                "cloud_environment": env_evidence,
            }
            (target / "cloud_render_record.json").write_bytes(_canonical_bytes(record) + b"\n")
            return record, pdf_bytes
    return render


def make_cloud_operate_deps(root: Path, font_dir: Path, *, work_dir: Path, current_state: Optional[Callable[[str], tuple]] = None):
    root, font_dir = Path(root), Path(font_dir)
    sys.path.insert(0, str(root / "src"))
    import pursue_to_gold_package as ptg
    import gold_resume_docx_builder as builder
    from claim_lineage import validate_claim_lineage
    from claim_repository import load_validated_claim_repository
    from evidence_repository import load_validated_evidence_repository

    verify_runtime(root)
    manifest = json.loads((root / "docs" / "rendering" / "RENDERING_ENVIRONMENT_V1.json").read_text(encoding="utf-8"))
    claims_result = load_validated_claim_repository(root / "claims")
    evidence_result = load_validated_evidence_repository(root / "evidence")
    if not claims_result["valid"] or not evidence_result["valid"]:
        raise RuntimeError("CANDIDATE_TRUTH_REPOSITORY_INVALID")
    fonts = builder.fonts_from_manifest(manifest, _font_reader(font_dir))
    def lineage(claim: Mapping[str, Any]) -> list:
        result = validate_claim_lineage(claim, evidence_result["index"])
        return [] if result.get("valid") else [str(x) for x in result.get("errors", [])] or ["LINEAGE_INVALID"]
    renderer = make_cloud_renderer(root, font_dir, work_dir=Path(work_dir))
    adapter_sha = _sha(Path(__file__).read_bytes())
    font_evidence = _sha(_canonical_bytes({p.name: _sha(p.read_bytes()) for p in sorted(font_dir.glob("*.ttf"))}))
    return ptg.PackageDeps(
        load_claims=lambda: claims_result["index"],
        validate_lineage=lineage,
        identity_provider=lambda: ptg.approved_identity_from_canonical_records(root, claims=claims_result["index"], evidence=evidence_result["index"]),
        fonts=fonts,
        render=renderer,
        renderer_identity=lambda: {"adapter_sha256": adapter_sha, "operator_verification_evidence_digest": font_evidence},
        pdf_facts=lambda pdf: __import__("gold_resume_qa").read_pdf_facts(pdf),
        current_state=current_state,
        doctrine_root=root,
        roster=None,
    )


def run_request(request_path: str, runtime_root: str, font_dir: str, output_root: str) -> dict:
    root=Path(runtime_root); fonts=Path(font_dir); out=Path(output_root); out.mkdir(parents=True,exist_ok=True)
    sys.path.insert(0,str(root/'src'))
    import pursue_to_gold_package as ptg
    request=json.loads(Path(request_path).read_text(encoding='utf-8'))
    request['output_root']=str(out)
    deps=make_cloud_operate_deps(root,fonts,work_dir=out)
    result=ptg.generate_gold_resume_stage(request,deps)
    sidecar={"spec":"CAREER_OS_CLOUD_OPERATE_RESULT_V1","profile":PROFILE_ID,"canonical_main_sha":EXPECTED_MAIN_SHA,"package_generation_id":result['manifest']['package_generation_id'],"human_review":result['manifest']['human_review'],"submission_authority":"BORA_ONLY","operator_equivalent":False,"note":"Operational cloud render; canonical Gold logic and governed font bytes, but not byte-identical to the historical OPERATOR environment."}
    Path(result['output_dir'],'cloud_operate_manifest.json').write_bytes(_canonical_bytes(sidecar)+b'\n')
    return result


if __name__ == '__main__':
    if len(sys.argv) != 5:
        raise SystemExit('usage: career_os_cloud_operate_v1.py REQUEST.json RUNTIME_ROOT FONT_DIR OUTPUT_ROOT')
    result=run_request(*sys.argv[1:])
    print(json.dumps({"output_dir":result['output_dir'],"manifest":result['manifest'],"post_render_qa":result['post_render_qa']},indent=2,sort_keys=True))
