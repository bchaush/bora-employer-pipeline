"""Tests for PURSUE_TO_GOLD_PACKAGE_V1: deterministic model-built Gold resume production.

Covers the Gold model schema, the deterministic DOCX builder (OOXML, genuine hyperlinks, structure map from the same
model, hyphen-safe layout solver), executable pre-render and post-render Gold QA, the first-render negative regression,
the pursuit orchestration gates, idempotency, no-mutation and the cover-letter boundary.

All fixture content below is SYNTHETIC test data. It is embedded in this test file, is never imported by the runtime and
is never Candidate Truth: no fixture fact, name, date, link or claim describes Bora, and no currently unapproved Bora
record is promoted by it.

Dependency-free groups run everywhere. With --operator-gold-regression the same four-link Gold fixture is rendered
through the real canonical renderer (pinned LibreOffice build, real inspection) on the OPERATOR; see operator_main.
"""

from __future__ import annotations

import copy
import hashlib
import io
import json
import os
import re
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.dont_write_bytecode = True

import document_render_adapter as adapter  # noqa: E402

if "--operator-gold-regression" in sys.argv:
    # The governed interpreter form (-I -S -B) has no site-packages; the adapter adds the manifest-named operator prefix exactly as
    # run_first_render does, before any jsonschema- or pypdf-dependent module is imported.
    _manifest_bytes = (ROOT / "docs" / "rendering" / "RENDERING_ENVIRONMENT_V1.json").read_bytes()
    adapter.add_governed_site_path(adapter.operator_site_packages(adapter.verify_manifest(_manifest_bytes)))

import gold_resume_docx_builder as builder  # noqa: E402
import gold_resume_qa as qa  # noqa: E402
import pursue_to_gold_package as ptg  # noqa: E402
from pursuit_decision import build_decision_mutation_plan, compute_context_fingerprint  # noqa: E402
from schema_validation import build_draft202012_validator  # noqa: E402

JOB_ID = "FIXTURE::JOB_0001"
ROSTER = ("Fixture Workspace Studio", "Fixture Digital Services", "Fixture Commerce Bank", "Fixture Prototype")
EMAIL = "jordan@example.org"
LINKEDIN = "https://www.linkedin.com/in/jordan-example"
GITHUB = "https://github.com/jordan-example"
PROJECT_LINK = "https://github.com/jordan-example/screening-prototype"


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        print(f"FAIL: {message}")
        sys.stdout.flush()
        raise SystemExit(1)


# Synthetic fixtures -------------------------------------------------------------------------------

BULLETS = {
    "A1": "Clarified scope, requirements, and operating limits for an internal workspace tool before implementation began, so the team agreed on boundaries early.",
    "A2": "Mapped a manual support workflow into a structured process covering evidence tracking, review, follow-up, and approval checkpoints for the whole team.",
    "A3": "Built a Drive-to-Workbook CSV intake workflow with automated Success, Held, and Failed run logging that held failed-quality data before trusted outputs were updated.",
    "A4": "Documented 10 passing pilot/UAT checks covering import validation, applicability checks, and related functional scenarios for the new workbook.",
    "B1": "Reviewed 500+ user cases weekly against written policy, identifying violations and behavioral patterns across structured and unstructured data.",
    "B2": "Tracked and categorized enforcement decisions for consistency and trend analysis, collaborating with policy, operations, and analytics teams.",
    "C1": "Prepared structured financial reports in Excel for regulatory submission and reconciled 1,000+ monthly transactions in Excel.",
    "C2": "Extracted and processed data for daily, weekly, and monthly reports prepared to regulator requirements.",
    "P1": "Built a Python/Streamlit prototype for preliminary coffee-shop market-screening using documented heuristic scoring boundaries.",
    "P2": "Integrated Google Places nearby-search and U.S. Census ACS demographic data into the screening workflow through external APIs.",
    "P3": "Implemented a 3.5-mile geofence, a local 50-request daily limit, and retry with degraded fallback when external fetches fail.",
    "P4": "Separated deterministic scoring from an optional narrative layer so explanations cannot alter official scores, thresholds, or status.",
    "P5": "Built an automated pytest validation suite for the screening pipeline and documented limitations so outputs are not presented as validated predictions.",
    "S": "Early-career business analyst with a master's degree in business analytics and a finance and accounting foundation. Hands-on experience analyzing operational data, mapping workflows, validating data quality, and documenting requirements and test results. Builds clear, practical reports and Python/Streamlit prototypes, and works well with cross-functional teams.",
    "K1": "Data analysis, process mapping, requirements clarification, data validation, UAT/QA documentation, issue identification, continuous improvement",
    "K2": "Microsoft Excel, Google Workspace, Python, Streamlit, REST/API integration, pytest",
    "K3": "Reporting and reconciliation, trend analysis, cross-functional collaboration, structured case review, rule-based analysis, time-sensitive decisions",
}


def claim_for(key: str) -> dict:
    return {"claim_id": "SYN_CLAIM_" + key, "wording": BULLETS[key] + " (synthetic source wording)", "evidence_ids": ["SYN_EVID_" + key],
            "evidence_state": "VERIFIED", "allowed_contexts": ["resume", "interview"], "forbidden_contexts": ["enterprise software architecture"],
            "human_approval": True, "date": "2026-01-01", "version": "1"}


def fixture_claims() -> dict:
    return {"SYN_CLAIM_" + key: claim_for(key) for key in BULLETS}


def fixture_evidence() -> dict:
    mapping = {"A1": "SYN_EXP_A", "A2": "SYN_EXP_A", "A3": "SYN_EXP_A", "A4": "SYN_EXP_A",
               "B1": "SYN_EXP_B", "B2": "SYN_EXP_B", "C1": "SYN_EXP_C", "C2": "SYN_EXP_C",
               "P1": "SYN_EXP_P", "P2": "SYN_EXP_P", "P3": "SYN_EXP_P", "P4": "SYN_EXP_P", "P5": "SYN_EXP_P"}
    return {"SYN_EVID_" + key: {"evidence_id": "SYN_EVID_" + key, "experience_id": experience_id}
            for key, experience_id in mapping.items()}


def fixture_language() -> dict:
    model = fixture_model()
    bullets = [{"bullet_id": "SYN_%s" % key, "text": BULLETS[key], "claim_ids": ["SYN_CLAIM_" + key]}
               for key in ("A1", "A2", "A3", "A4", "B1", "B2", "C1", "C2", "P1", "P2", "P3", "P4", "P5")]
    skills = [{"skill_id": "SYN_%s_%d" % (row["label"], index), "row": row["label"], "text": item, "claim_ids": row["claim_ids"]}
              for row in model["skills"] for index, item in enumerate(row["items"])]
    return {"record_id": "SYNTHETIC_APPROVED_LANGUAGE", "status": "CURRENT_APPROVED", "approval": {"approved": True},
            "bullets": bullets, "summaries": [{"summary_id": "SYN", "role_family": "fixture", "text": BULLETS["S"], "claim_ids": ["SYN_CLAIM_S"]}],
            "skills": skills}


def bullet(key: str) -> dict:
    return {"text": BULLETS[key], "claim_ids": ["SYN_CLAIM_" + key]}


def fixture_model() -> dict:
    return {
        "model_id": "FIXTURE_MODEL_V1", "job_id": JOB_ID,
        "contact": {"name": "Jordan Example", "location": "Springfield, IL", "phone": "+1 555 010 0199", "email": EMAIL,
                    "profile_links": [{"label": "LinkedIn", "url": LINKEDIN}, {"label": "GitHub", "url": GITHUB}]},
        "summary": {"text": BULLETS["S"], "claim_ids": ["SYN_CLAIM_S"]},
        "education": [{"school": "Example State University", "date_range": "Aug 2025 - Aug 2026",
                       "degree_line": "Master of Science in Business Analytics | GPA: 3.635"},
                      {"school": "Sample Institute of Economics", "date_range": "Sep 2021 - Jun 2025",
                       "degree_line": "Bachelor of Science in Finance and Accounting"}],
        "skills": [{"label": "Process & quality", "items": BULLETS["K1"].split(", "), "claim_ids": ["SYN_CLAIM_K1"]},
                   {"label": "Technical", "items": BULLETS["K2"].split(", "), "claim_ids": ["SYN_CLAIM_K2"]},
                   {"label": "Operations", "items": BULLETS["K3"].split(", "), "claim_ids": ["SYN_CLAIM_K3"]}],
        "work": [
            {"experience_id": "SYN_EXP_A", "title": "Operations Analyst Intern", "employer": "Fixture Workspace Studio",
             "date_range": "Jun 2026 - Aug 2026", "bullets": [bullet(k) for k in ("A1", "A2", "A3", "A4")]},
            {"experience_id": "SYN_EXP_B", "title": "Policy Review Analyst", "employer": "Fixture Digital Services",
             "date_range": "Nov 2024 - May 2025", "bullets": [bullet(k) for k in ("B1", "B2")]},
            {"experience_id": "SYN_EXP_C", "title": "Junior Reporting Specialist", "employer": "Fixture Commerce Bank",
             "date_range": "Aug 2021 - Sep 2022", "bullets": [bullet(k) for k in ("C1", "C2")]}],
        "project": {"experience_id": "SYN_EXP_P", "name": "Fixture Prototype", "tech_label": "Python / Streamlit Market-Screening Prototype",
                    "link": {"label": "GitHub", "url": PROJECT_LINK}, "bullets": [bullet(k) for k in ("P1", "P2", "P3", "P4", "P5")]}}


def fixture_identity() -> dict:
    model = fixture_model()
    return {"contact": {"name": "Jordan Example", "location": "Springfield, IL", "phone": "+1 555 010 0199", "email": EMAIL,
                        "profile_links": [{"label": "LinkedIn", "url": LINKEDIN}, {"label": "GitHub", "url": GITHUB}]},
            "education": copy.deepcopy(model["education"]),
            "experiences": {**{entry["experience_id"]: {"title": entry["title"], "employer": entry["employer"], "date_range": entry["date_range"]}
                               for entry in model["work"]},
                            "SYN_EXP_P": {"project_name": "Fixture Prototype", "project_tech_label": "Python / Streamlit Market-Screening Prototype"}},
            "project_links": {"SYN_EXP_P": {"label": "GitHub", "url": PROJECT_LINK}}}


def model_without_commerce() -> dict:
    """The fixture with the Commerce roster entry removed and bullets re-allocated so the page still fills (no filler is invented)."""
    model = fixture_model()
    model["work"] = model["work"][:2]
    model["work"][1]["bullets"] = [bullet(k) for k in ("B1", "B2", "A3", "A4")]
    return model


def metrics() -> builder.GoldMetrics:
    return builder.load_gold_metrics(ROOT)[0]


def synthetic_fonts() -> builder.FontMetrics:
    return builder.FontMetrics.synthetic(0.49, 0.53)


def build_fixture(model=None, fonts=None):
    model = model if model is not None else fixture_model()
    return build_gold(model, fonts)


def build_gold(model, fonts=None):
    return builder.build_gold_docx(model, metrics(), fonts or synthetic_fonts())


def run_pre_qa(model=None, build=None, claims=None, identity=None, roster=ROSTER, fonts=None, terms=()):
    model = model if model is not None else fixture_model()
    fonts = fonts or synthetic_fonts()
    build = build or build_gold(model, fonts)
    return qa.pre_render_qa(model, build, metrics=metrics(), claims=claims if claims is not None else fixture_claims(), evidence=fixture_evidence(),
                            identity=identity if identity is not None else fixture_identity(),
                            rebuild=lambda: build_gold(model, fonts), roster=roster, job_relevant_terms=terms, approved_language=fixture_language())


def failed(result) -> set:
    return set(result["failed_checks"])


def tampered(build, transform):
    """A GoldBuild whose document.xml is transformed, for negative QA vectors."""
    archive = zipfile.ZipFile(io.BytesIO(build.docx_bytes))
    parts = [(info.filename, archive.read(info.filename).decode("utf-8")) for info in archive.infolist()]
    parts = [(name, transform(text) if name == "word/document.xml" else text) for name, text in parts]
    return builder.GoldBuild(builder._zip_bytes(parts), build.structure_map, build.expected_links, build.layout)


# Pursuit fixtures -------------------------------------------------------------------------------

def make_job(job_id: str = JOB_ID, **overrides) -> dict:
    row = {"Job_ID": job_id, "Company": "Fixture Co", "Role": "Fixture Role", "Discovery_Source": "MANUAL_URL",
           "Discovery_URL": "https://discovery.example/x", "Official_URL": "https://careers.example/" + job_id.replace("::", "_"),
           "First_Seen": "2026-09-27T10:00:00+00:00", "Last_Verified": "2026-09-27T12:00:00+00:00", "Pipeline_State": "REVIEW_READY",
           "Freshness_State": "PASS", "Geography_State": "PASS", "OPT_Screen_State": "PASS", "Candidate_Condition_State": "PASS",
           "Threshold_State": "PASS", "Role_Status": "VERIFIED_LIVE", "Match_State": "ANALYZED", "Decision": "WATCH", "Bora_Decision": None}
    row.update(overrides)
    return row


def decide(row: dict, log: list, decision: str, counter: int) -> None:
    from pursuit_decision import derive_current_pursuit_state
    latest = derive_current_pursuit_state(row, log)["latest_event_id"]
    request = {"job_id": row["Job_ID"], "decision": decision, "reviewed_context_fingerprint": compute_context_fingerprint(row),
               "decision_run_id": "RUN_%d" % counter, "decided_at": "2026-09-28T09:00:00-04:00",
               "supersedes_event_id": latest, "reason_note": None}
    plan = build_decision_mutation_plan(request, [row], log)
    log.extend(plan["log_mutations"])


def pursue_state(decisions=("PURSUE",)):
    row, log = make_job(), []
    for counter, decision in enumerate(decisions, start=1):
        decide(row, log, decision, counter)
    return row, log


def requirement(requirement_id: str = "REQ_1") -> dict:
    return {"requirement_id": requirement_id, "job_id": JOB_ID, "text": "Analyze operational data and document workflows",
            "category": "RESPONSIBILITY", "importance": "MANDATORY", "seniority_implication": None, "technology": [],
            "experience_level": None, "domain": None, "relevance": "HIGH", "source_text": "Analyze operational data and document workflows",
            "source_location": "Responsibilities", "source_semantic_role": "ROLE_RESPONSIBILITY",
            "source_semantic_role_basis": "fixture", "explicit_prerequisite_language_present": False, "duplicated_under_requirements": False,
            "source_semantic_role_classifier_version": "SOURCE_SEMANTIC_ROLE_CLASSIFIER_V1"}


def evidence_match() -> dict:
    return {"match_id": "MATCH_1", "job_id": JOB_ID, "requirement_id": "REQ_1", "result": "STRONG", "evidence_ids": ["SYN_EVID_A3"],
            "claim_ids": ["SYN_CLAIM_A3"], "explanation": "fixture", "transfer_note": None, "evaluation_path": None}


def attestation(row: dict, log: list) -> dict:
    from pursuit_decision import derive_current_pursuit_state
    state = derive_current_pursuit_state(row, log)
    return {"job_id": row["Job_ID"], "latest_event_id": state["latest_event_id"], "decision_context_fingerprint": compute_context_fingerprint(row),
            "role_requisition_identity": "FIXTURE-REQ-1", "application_destination_url": row["Official_URL"],
            "semantic_quorum": {"matching_role_title_identity": True, "matching_requisition_identity": True,
                                "substantive_current_jd_content": True, "current_actionable_application_route": True},
            "dead_state_veto": False, "rechecked_at": "2026-09-28T10:00:00-04:00", "recheck_provenance": "operator reopen of the first-party posting",
            "role_status": "VERIFIED_LIVE", "source_verification_status": "VERIFIED_DIRECT"}


def make_request(output_root: str, decisions=("PURSUE",), **overrides) -> dict:
    row, log = pursue_state(decisions)
    request = {"job_id": JOB_ID, "jobs_rows": [row], "decision_log_rows": log, "attestation": attestation(row, log),
               "requirements": [requirement()], "evidence_matches": [evidence_match()], "resume_model": fixture_model(),
               "package_run_id": "RUN_FIXTURE_1", "output_root": output_root}
    request.update(overrides)
    return request


PASS_RECORD = {"run_status": qa.RENDER_PASS_STATUS, "delivered": 1, "reason": None, "utilization": {"meaningful_content_bottom_fraction": 0.941},
               "findings": [], "attribution_digest": "a" * 64, "render_semantic_fingerprint": "b" * 64,
               "automated_checks": [{"check": "FONT_EMBEDDING_AND_IDENTITY", "label": "AUTOMATED"}],
               "human_required": [{"check": "VISUAL_REVIEW_OF_RAW_PDF_AND_DOCX", "label": "HUMAN_REQUIRED"}], "human_review_waived": 0}


class FakeRenderer:
    def __init__(self, record=None, pdf=b"%PDF-1.7 fixture"):
        self.record, self.pdf, self.calls = record or PASS_RECORD, pdf, []

    def __call__(self, docx_bytes, structure_map, out_dir):
        self.calls.append((hashlib.sha256(docx_bytes).hexdigest(), len(structure_map), out_dir))
        return copy.deepcopy(self.record), self.pdf


def fixture_pdf_facts(extra=None, drop=None, order=None):
    urls = [EMAIL and "mailto:" + EMAIL, LINKEDIN, GITHUB, PROJECT_LINK]
    if drop is not None:
        urls.pop(drop)
    urls = list(extra or []) + urls
    if order is not None:
        urls = [urls[index] for index in order]
    return {"page_count": 1, "pages": [(612.0, 792.0)], "links": urls}


def make_deps(renderer=None, facts=None, row_log=None, claims=None, lineage=None, identity=None):
    renderer = renderer or FakeRenderer()
    return ptg.PackageDeps(
        load_claims=lambda: claims if claims is not None else fixture_claims(), load_evidence=lambda: fixture_evidence(), approved_language=lambda: fixture_language(), validate_lineage=lineage or (lambda claim: []),
        identity_provider=lambda: identity if identity is not None else fixture_identity(), fonts=synthetic_fonts(), render=renderer,
        renderer_identity=lambda: {"adapter_sha256": "c" * 64, "operator_verification_evidence_digest": "d" * 64},
        pdf_facts=lambda pdf: facts or fixture_pdf_facts(), current_state=(lambda job_id: row_log) if row_log else None,
        doctrine_root=ROOT, roster=ROSTER), renderer


def expect_package_error(code: str, function, *args):
    try:
        function(*args)
    except ptg.PackageError as error:
        assert_true(error.code == code, f"expected {code}, got {error.code} ({error.detail})")
        return error
    assert_true(False, f"expected PackageError {code}")


def tree_listing(path: str) -> list:
    return sorted(str(p.relative_to(path)) for p in Path(path).rglob("*"))


# Test groups --------------------------------------------------------------------------------------

def test_model_schema_vectors() -> None:
    validator = build_draft202012_validator(ROOT / "schemas" / "gold_resume_model.schema.json", check_schema=True)
    assert_true(not list(validator.iter_errors(fixture_model())), "the fixture model validates")
    mutations = {
        "two skills rows": lambda m: m["skills"].pop(),
        "unknown skills label": lambda m: m["skills"][0].update(label="Internal taxonomy"),
        "three schools": lambda m: m["education"].append(copy.deepcopy(m["education"][0])),
        "no claim lineage on a bullet": lambda m: m["work"][0]["bullets"][0].update(claim_ids=[]),
        "unsupported link scheme": lambda m: m["project"]["link"].update(url="file:///c:/secret.txt"),
        "additional property": lambda m: m.update(extra_field=1),
        "missing summary": lambda m: m.pop("summary"),
        "bad email": lambda m: m["contact"].update(email="not-an-email"),
    }
    for label, mutate in mutations.items():
        model = fixture_model()
        mutate(model)
        assert_true(list(validator.iter_errors(model)), f"schema must reject: {label}")
    print("PASS: Gold resume model schema accepts the fixture and rejects each structural violation.")


def test_deterministic_docx_and_renderer_preflight() -> None:
    first, second = build_fixture(), build_fixture()
    assert_true(first.docx_bytes == second.docx_bytes and first.structure_map == second.structure_map and first.layout == second.layout,
                "identical model gives identical DOCX bytes, map and layout")
    archive = zipfile.ZipFile(io.BytesIO(first.docx_bytes))
    names = [info.filename for info in archive.infolist()]
    assert_true(names == ["[Content_Types].xml", "_rels/.rels", "word/_rels/document.xml.rels", "word/document.xml", "word/numbering.xml", "word/styles.xml"],
                f"fixed entry order, no legacy parts: {names}")
    assert_true(all(info.date_time == (1980, 1, 1, 0, 0, 0) and info.compress_type == zipfile.ZIP_STORED for info in archive.infolist()),
                "fixed timestamps and stored entries")
    assert_true(not any("customXml" in name or "theme" in name for name in names), "no customXml or theme part")
    other = fixture_model()
    other["summary"]["text"] = other["summary"]["text"] + " Additional sentence."
    assert_true(build_gold(other).docx_bytes != first.docx_bytes, "a changed model changes the bytes")
    # The released renderer's own preflight and source model accept the generated package and map.
    manifest = adapter.verify_manifest((ROOT / "docs" / "rendering" / "RENDERING_ENVIRONMENT_V1.json").read_bytes())
    package = adapter.docx_preflight(first.docx_bytes)
    model = adapter.build_source_model(package, manifest, first.structure_map)
    assert_true(len(model.paragraphs) == len(first.structure_map) and len(model.occurrences) == 4,
                f"preflight, source model and structure map accept the build with four hyperlink occurrences: {len(model.occurrences)}")
    # The legacy exemplar's baggage is rejected by that same preflight (why the clone path is retired).
    legacy = io.BytesIO()
    with zipfile.ZipFile(legacy, "w") as zout:
        for name, text in [(n, archive.read(n)) for n in names] + [("customXml/item1.xml", b"<x/>")]:
            zout.writestr(name, text)
    try:
        adapter.docx_preflight(legacy.getvalue())
        assert_true(False, "a customXml part must fail preflight")
    except adapter.StageFailure as failure:
        assert_true(failure.outcome.status == "RENDER_DOCX_PACKAGE_INVALID", "customXml is a preflight failure")
    print("PASS: DOCX bytes are deterministic, carry only canonical parts and pass the released renderer preflight and source model.")


def test_gold_grammar_pre_render_pass() -> None:
    result = run_pre_qa()
    assert_true(result["passed"], f"positive fixture passes pre-render QA: {[c for c in result['checks'] if not c['passed']]}")
    names = {check["check"] for check in result["checks"]}
    for required in ("SUMMARY_PRESENT_NO_HEADING", "SECTION_ORDER_EXACT", "SKILLS_THREE_RECRUITER_ROWS", "WORK_HEADER_TITLE_PIPE_EMPLOYER_RIGHT_DATE",
                     "EDUCATION_GRAMMAR", "ROSTER_POLICY", "MARKETMIND_HEADING_GRAMMAR", "HYPERLINK_OBJECTS_GENUINE_AND_EXACT",
                     "HYPERLINK_ALLOWLIST_APPROVED", "CANDIDATE_TRUTH_LINEAGE", "RECRUITER_JARGON_PROHIBITION", "DOCX_BYTES_DETERMINISTIC",
                     "STRUCTURE_MAP_BOUND_TO_DOCX_AND_MODEL", "FONT_RULES_LIBERATION_SANS", "METRICS_MATCH_DOCTRINE"):
        assert_true(required in names, f"pre-render QA runs {required}")
    parsed = qa.parse_docx(build_fixture().docx_bytes)
    paragraphs = parsed["paragraphs"]
    assert_true(paragraphs[0]["text"] == "Jordan Example" and paragraphs[0]["centered"], "centered name")
    assert_true(paragraphs[1]["text"] == "Springfield, IL | +1 555 010 0199 | jordan@example.org | LinkedIn | GitHub" and paragraphs[1]["centered"],
                "centered contact line grammar with human-readable labels")
    assert_true(paragraphs[2]["text"].startswith("Early-career business analyst"), "summary directly below the contact line with no heading")
    assert_true(paragraphs[2]["centered"], "candidate summary is centered (RESUME_FORMAT_STANDARD_V1)")
    headings = [p["text"] for p in paragraphs if p["border_bottom"]]
    assert_true(headings == ["EDUCATION", "SKILLS", "WORK EXPERIENCE", "RELEVANT PROJECT"], f"exact section order: {headings}")
    headers = [p for p in paragraphs if p["tab_right"] is not None]
    assert_true(len(headers) == 2 + 3 + 1 and all(p["runs"][0]["bold"] for p in headers), "school, work and project headers: bold left, right-aligned date or link")
    assert_true(any(p["text"].startswith("Operations Analyst Intern | Fixture Workspace Studio Jun 2026 - Aug 2026") for p in headers), "Title | Employer + right-aligned date")
    metrics_value = metrics()
    assert_true((metrics_value.margin_left_twips, metrics_value.margin_top_twips, metrics_value.margin_bottom_twips) == (1037, 662, 461)
                and metrics_value.name_half_points == 37 and metrics_value.body_half_points == 21 and metrics_value.heading_half_points == 22,
                "metrics are read from the canonical doctrine record")
    print("PASS: the positive Gold fixture satisfies every executable pre-render check and the Gold grammar of the artifact.")


def test_pre_render_negative_mutations() -> None:
    build = build_fixture()

    def fails(label, transform, expected):
        result = run_pre_qa(build=tampered(build, transform))
        assert_true(expected in failed(result), f"{label}: expected {expected}, failed={sorted(failed(result))}")

    def insert_summary_heading(x):
        marker = "</w:p>"
        position = x.index(marker, x.index(marker) + 1) + len(marker)
        return x[:position] + '<w:p><w:r><w:rPr><w:rFonts w:ascii="Liberation Sans" w:hAnsi="Liberation Sans"/></w:rPr><w:t>PROFESSIONAL SUMMARY</w:t></w:r></w:p>' + x[position:]

    fails("summary heading inserted", insert_summary_heading, "SUMMARY_PRESENT_NO_HEADING")
    fails("heading text changed", lambda x: x.replace(">SKILLS<", ">TECHNICAL SKILLS<"), "SECTION_ORDER_EXACT")
    fails("heading rule removed", lambda x: re.sub(r"<w:pBdr>.*?</w:pBdr>", "", x), "HEADING_GRAMMAR_BOLD_RULE_SIZE")
    fails("name not centered", lambda x: x.replace("<w:jc w:val=\"center\"/>", "", 1), "NAME_CENTERED_BOLD_SIZE")
    centered = "<w:jc w:val=\"center\"/>"
    # Name, contact and summary are the first three centered paragraphs; drop only the third (the summary).
    fails("summary not centered", lambda x: centered.join(x.split(centered, 3)[:3]) + x.split(centered, 3)[3], "SUMMARY_PRESENT_NO_HEADING")
    fails("date no longer right-aligned", lambda x: x.replace("<w:tabs><w:tab w:val=\"right\" w:pos=\"10166\"/></w:tabs>", "", 1), "EDUCATION_GRAMMAR")
    fails("font changed", lambda x: x.replace("Liberation Sans", "Calibri", 2), "FONT_RULES_LIBERATION_SANS")
    fails("theme font attribute", lambda x: x.replace('w:ascii="Liberation Sans"', 'w:asciiTheme="minorHAnsi" w:ascii="Liberation Sans"', 1), "FONT_RULES_LIBERATION_SANS")
    fails("margins changed", lambda x: x.replace('w:left="1037"', 'w:left="1440"'), "METRICS_MATCH_DOCTRINE")
    fails("a hyperlink wrapper removed", lambda x: re.sub(r'<w:hyperlink r:id="rId5">(.*?)</w:hyperlink>', r"\1", x, count=1), "HYPERLINK_OBJECTS_GENUINE_AND_EXACT")
    # Model-level violations.
    model = fixture_model()
    model["skills"].pop()
    assert_true("SKILLS_THREE_RECRUITER_ROWS" in failed(run_pre_qa(model=model)), "two skills rows fail")
    model = fixture_model()
    model["skills"][0]["label"] = "Core strengths"
    assert_true("SKILLS_ROW_LABELS_MATCH_MODEL" in failed(run_pre_qa(model=model)) or "SKILLS_THREE_RECRUITER_ROWS" in failed(run_pre_qa(model=model)), "non-canonical skills label fails")
    model = fixture_model()
    model["work"][0]["date_range"] = "Summer 2026"
    result = run_pre_qa(model=model, identity={**fixture_identity(), "experiences": {**fixture_identity()["experiences"], "SYN_EXP_A": {"title": "Operations Analyst Intern", "employer": "Fixture Workspace Studio", "date_range": "Summer 2026"}}})
    assert_true("WORK_HEADER_TITLE_PIPE_EMPLOYER_RIGHT_DATE" in failed(result), "a non-grammar date range fails the work header grammar")
    print("PASS: pre-render QA rejects every tampered artifact and model vector it is responsible for.")


def test_hyperlinks_genuine_and_allowlisted() -> None:
    build = build_fixture()
    parsed = qa.parse_docx(build.docx_bytes)
    targets = sorted(rel["target"] for rel in parsed["relationships"].values() if rel["type"] == "hyperlink")
    assert_true(targets == sorted(["mailto:" + EMAIL, LINKEDIN, GITHUB, PROJECT_LINK]), f"four genuine hyperlink relationships: {targets}")
    assert_true(all(rel["external"] for rel in parsed["relationships"].values() if rel["type"] == "hyperlink"), "all external TargetMode")
    labels = sorted(run["text"] for p in parsed["paragraphs"] for run in p["runs"] if run["link"])
    assert_true(labels == sorted([EMAIL, "LinkedIn", "GitHub", "GitHub"]), f"human-readable labels, no raw URLs: {labels}")
    assert_true("https://" not in " ".join(p["text"] for p in parsed["paragraphs"]), "no raw URL text is displayed")
    # An unapproved destination fails the allowlist; a GitHub profile absent from the approved record is a data gap.
    identity = fixture_identity()
    identity["contact"]["profile_links"] = [{"label": "LinkedIn", "url": LINKEDIN}]
    result = run_pre_qa(identity=identity)
    assert_true({"HYPERLINK_ALLOWLIST_APPROVED", "APPROVED_IDENTITY_VALUES"} <= failed(result), "an unapproved GitHub profile target is blocked")
    identity = fixture_identity()
    identity["project_links"] = {}
    assert_true("HYPERLINK_ALLOWLIST_APPROVED" in failed(run_pre_qa(identity=identity)), "an unapproved project link is blocked")
    wrong = tampered(build, lambda x: x)
    archive = zipfile.ZipFile(io.BytesIO(wrong.docx_bytes))
    parts = [(n, archive.read(n).decode("utf-8")) for n in archive.namelist()]
    parts = [(n, t.replace(GITHUB + '"', "https://github.com/someone-else" + '"', 1) if n.endswith("document.xml.rels") else t) for n, t in parts]
    swapped = builder.GoldBuild(builder._zip_bytes(parts), build.structure_map, build.expected_links, build.layout)
    assert_true("HYPERLINK_OBJECTS_GENUINE_AND_EXACT" in failed(run_pre_qa(build=swapped)), "a substituted relationship target fails")
    model = fixture_model()
    model["contact"]["profile_links"][0]["url"] = "ftp://example.org/x"
    try:
        builder.expected_links(model)
        assert_true(False, "a non-http(s)/mailto scheme must be refused")
    except builder.GoldBuildError as error:
        assert_true(error.code == "LINK_SCHEME_NOT_ALLOWED", "unsupported scheme refused at build time")
    print("PASS: hyperlinks are genuine OOXML relationships with exact destinations and labels, and only approved targets pass.")


def test_structure_map_from_the_same_model() -> None:
    build = build_fixture()
    canonical = {"CONTACT_LINE", "SECTION_HEADING", "SUMMARY_TEXT", "EDUCATION_LINE", "EMPLOYMENT_HEADER", "BULLET_TEXT", "PROJECT_HEADER", "SKILLS_LINE"}
    kinds = {entry["content_type"] for entry in build.structure_map}
    assert_true(kinds == canonical | {"NAME"}, f"only the canonical vocabulary plus the nonmeaningful name: {kinds}")
    from resume_page_utilization import MEANINGFUL_CONTENT_TYPES
    assert_true(canonical == set(MEANINGFUL_CONTENT_TYPES), "the vocabulary equals the renderer's meaningful types")
    parsed = qa.parse_docx(build.docx_bytes)
    assert_true([e["paragraph_text"] for e in build.structure_map] == [p["text"] for p in parsed["paragraphs"]], "map text equals the DOCX paragraphs in order")
    assert_true(all(e["list_semantics"] == ({"ilvl": 0, "numFmt": "bullet", "numId": 1} if e["content_type"] == "BULLET_TEXT" else None) for e in build.structure_map),
                "bullet list semantics match")
    other = fixture_model()
    other["work"][0]["bullets"][0]["text"] = other["work"][0]["bullets"][0]["text"] + " Extra."
    changed = build_gold(other)
    assert_true(changed.structure_map != build.structure_map and builder.model_digest(other) != builder.model_digest(fixture_model()),
                "the map follows the model: a changed model changes both map and digest")
    drifted = builder.GoldBuild(build.docx_bytes, [dict(entry, paragraph_text=entry["paragraph_text"] + "x") if index == 5 else entry
                                                   for index, entry in enumerate(build.structure_map)], build.expected_links, build.layout)
    assert_true("STRUCTURE_MAP_BOUND_TO_DOCX_AND_MODEL" in failed(run_pre_qa(build=drifted)), "an independently drifted map fails the binding check")
    print("PASS: the structure map is generated from the same model, uses only canonical roles and is bound to the DOCX paragraphs.")


def test_layout_solver_vectors() -> None:
    fonts = synthetic_fonts()
    width = (metrics().text_width_twips - 360) / 20.0
    # Find a width where the literal hyphen of a compound lands at a line end (the nearby-search class of failure).
    text = "Integrated Google Places nearby-search and U.S. Census ACS demographic data into a coffee-shop market-screening workflow."
    hazardous = None
    for candidate in range(150, 330, 2):
        if builder._line_ends_unsafe(builder.predict_lines(text, float(candidate), 10.5, fonts)):
            hazardous = float(candidate)
            break
    assert_true(hazardous is not None, "a width exists where the compound hyphen lands at the line end")
    indent = builder.solve_right_indent(text, hazardous, 10.5, fonts)
    assert_true(indent > 0 and indent % builder.RIGHT_INDENT_STEP_TWIPS == 0, f"a bounded presentation-only indent is chosen: {indent}")
    for factor in builder.HYPHEN_SAFETY_FACTORS:
        lines = builder.predict_lines(text, (hazardous - indent / 20.0) * factor, 10.5, fonts)
        assert_true(not builder._line_ends_unsafe(lines), f"no unsafe line end at safety factor {factor}: {lines}")
    assert_true(builder.solve_right_indent(text, hazardous, 10.5, fonts) == indent, "the solver is deterministic")
    assert_true(builder.solve_right_indent("short line", 300.0, 10.5, fonts) == 0, "a paragraph that already satisfies the condition gets no indent")
    assert_true(not builder._line_ends_unsafe(["alpha beta -", "gamma"]), "a standalone spaced dash token is not a line-end hazard")
    assert_true(builder._line_ends_unsafe(["alpha beta-", "gamma"]) and builder._line_ends_unsafe(["alpha pilot/", "UAT"]), "an in-token hyphen or slash at a line end is a hazard")
    # Slash and dash break opportunities are treated like hyphens (pilot/UAT, en dash): every hazardous width gets a safe indent.
    for compound in ("Documented import validation and applicability pilot/UAT checks covering related functional scenarios",
                     "Prepared monthly variance reports–covering trends and exceptions for operations teams across the quarter"):
        found = False
        for candidate in range(150, 330):
            if builder._line_ends_unsafe(builder.predict_lines(compound, float(candidate), 10.5, fonts)):
                solved = builder.solve_right_indent(compound, float(candidate), 10.5, fonts)
                assert_true(solved > 0 and not builder._line_ends_unsafe(builder.predict_lines(compound, candidate - solved / 20.0, 10.5, fonts)),
                            f"slash and dash break hazards are solved: {compound[:30]}")
                found = True
                break
        assert_true(found, "a hazardous width exists for the slash or dash vector")
    # The solver changes presentation only: the model text and the structure map text are untouched.
    build = build_fixture()
    assert_true(all(int(index) >= 0 and value % builder.RIGHT_INDENT_STEP_TWIPS == 0 for index, value in build.layout["right_indents_twips"].items()),
                "the layout report lists bounded presentation-only indents")
    assert_true([e["paragraph_text"] for e in build.structure_map][2] == fixture_model()["summary"]["text"], "approved wording is never altered")
    # Impossible layout fails closed: an unbreakable chain of hyphenated pieces always ends a line at a hyphen.
    impossible = "-".join(["abcdefghij"] * 80)
    try:
        builder.solve_right_indent(impossible, 200.0, 10.5, fonts)
        assert_true(False, "an impossible layout must fail closed")
    except builder.GoldBuildError as error:
        assert_true(error.code == "LAYOUT_UNSOLVABLE", f"impossible layout fails closed: {error.code}")
    model = fixture_model()
    model["work"][0]["bullets"][0]["text"] = impossible
    model["work"][0]["bullets"][0]["claim_ids"] = ["SYN_CLAIM_A1"]
    try:
        build_gold(model)
        assert_true(False, "the build must fail closed on an unsolvable paragraph")
    except builder.GoldBuildError as error:
        assert_true(error.code == "LAYOUT_UNSOLVABLE", "the build fails closed")
    print("PASS: the hyphen-safe layout solver is deterministic, bounded, presentation-only and fails closed when impossible.")


def test_density_and_page_fill_fail_closed() -> None:
    build = build_fixture()
    estimate = build.layout["estimated_bottom_fraction"]
    assert_true(builder.PAGE_FILL_TARGET <= estimate <= builder.PAGE_FILL_CEILING, f"predicted page fill inside the window: {estimate}")
    thin = fixture_model()
    thin["work"] = thin["work"][:1]
    thin["work"][0]["bullets"] = thin["work"][0]["bullets"][:1]
    thin["project"]["bullets"] = thin["project"]["bullets"][:1]
    try:
        build_gold(thin)
        assert_true(False, "thin content must not be padded")
    except builder.GoldBuildError as error:
        assert_true(error.code == "LAYOUT_UNDERFILLED", f"underfilled content fails closed, never padded: {error.code}")
    heavy = fixture_model()
    heavy["work"] = heavy["work"] + [copy.deepcopy(heavy["work"][0])]
    heavy["work"][-1]["experience_id"] = "SYN_EXP_A2"
    heavy["project"]["bullets"] = heavy["project"]["bullets"] + [bullet("P1"), bullet("P2")]
    try:
        build_gold(heavy)
        assert_true(False, "overfull content must not shrink type")
    except builder.GoldBuildError as error:
        assert_true(error.code == "LAYOUT_OVERFLOW", f"overflowing content fails closed: {error.code}")
    print("PASS: page-fill density is solved inside the doctrine window and underfilled or overflowing content fails closed.")


def test_claim_lineage_vectors() -> None:
    claims = fixture_claims()
    assert_true("CANDIDATE_TRUTH_LINEAGE" not in failed(run_pre_qa(claims=claims)), "approved lineage passes")
    unapproved = copy.deepcopy(claims)
    unapproved["SYN_CLAIM_C1"]["human_approval"] = False
    assert_true("CANDIDATE_TRUTH_LINEAGE" in failed(run_pre_qa(claims=unapproved)), "a claim without human approval is blocked")
    unknown = copy.deepcopy(claims)
    unknown.pop("SYN_CLAIM_B1")
    assert_true("CANDIDATE_TRUTH_LINEAGE" in failed(run_pre_qa(claims=unknown)), "an unknown claim id is blocked")
    state = copy.deepcopy(claims)
    state["SYN_CLAIM_B2"]["evidence_state"] = "UNKNOWN"
    assert_true("CANDIDATE_TRUTH_LINEAGE" in failed(run_pre_qa(claims=state)), "an UNKNOWN evidence state is never upgraded")
    context = copy.deepcopy(claims)
    context["SYN_CLAIM_A2"]["allowed_contexts"] = ["interview"]
    assert_true("CANDIDATE_TRUTH_LINEAGE" in failed(run_pre_qa(claims=context)), "a claim not allowed in resume context is blocked")
    model = fixture_model()
    model["work"][2]["bullets"][0]["text"] = model["work"][2]["bullets"][0]["text"].replace("1,000+", "5,000+")
    assert_true("CANDIDATE_TRUTH_LINEAGE" in failed(run_pre_qa(model=model)), "a manufactured metric is blocked")
    model = fixture_model()
    model["work"][0]["bullets"][0]["text"] += " Led enterprise software architecture."
    assert_true("CANDIDATE_TRUTH_LINEAGE" in failed(run_pre_qa(model=model)), "a forbidden-context phrase is blocked")
    model = fixture_model()
    model["summary"]["claim_ids"] = []
    assert_true("CANDIDATE_TRUTH_LINEAGE" in failed(run_pre_qa(model=model)), "a factual statement with no lineage is blocked")
    exemplar = copy.deepcopy(claims)
    exemplar.pop("SYN_CLAIM_C2")
    assert_true("CANDIDATE_TRUTH_LINEAGE" in failed(run_pre_qa(claims=exemplar)), "exemplar wording without a claim record is never accepted")
    print("PASS: claim lineage requires approved, resume-allowed, grounded claims for every factual statement.")


def test_jargon_prohibition() -> None:
    for term in ("operating system", "human approval", "fail-closed", "Candidate Truth", "EvidenceMatch", "queue-level eligibility", "deterministic boundary"):
        model = fixture_model()
        model["summary"]["text"] = model["summary"]["text"] + " Experience with a " + term + " design."
        result = run_pre_qa(model=model, claims={**fixture_claims(), "SYN_CLAIM_S": {**claim_for("S"), "wording": BULLETS["S"] + " Experience with a " + term + " design."}})
        assert_true("RECRUITER_JARGON_PROHIBITION" in failed(result), f"internal vocabulary is blocked: {term}")
    model = fixture_model()
    model["summary"]["text"] += " Familiar with an operating system migration."
    result = run_pre_qa(model=model, claims={**fixture_claims(), "SYN_CLAIM_S": {**claim_for("S"), "wording": BULLETS["S"] + " Familiar with an operating system migration."}},
                        terms=("operating system",))
    assert_true("RECRUITER_JARGON_PROHIBITION" not in failed(result), "an independently job-relevant term is allowed")
    assert_true("RECRUITER_JARGON_PROHIBITION" not in failed(run_pre_qa()), "clean recruiter-natural text passes")
    print("PASS: internal Career OS and governance vocabulary is rejected unless independently job-relevant.")


def test_truth_gaps_fail_closed_or_omit() -> None:
    # GPA: the exact approved value is used; a rounded 3.64 is not an approved display.
    model = fixture_model()
    model["education"][0]["degree_line"] = "Master of Science in Business Analytics | GPA: 3.64"
    assert_true("APPROVED_IDENTITY_VALUES" in failed(run_pre_qa(model=model)), "silently rounding 3.635 to 3.64 is blocked")
    assert_true("3.635" in fixture_model()["education"][0]["degree_line"], "the exact approved GPA value is emitted")
    # Employer alias: the canonical employer name unless an approved alias exists.
    model = fixture_model()
    model["work"][1]["employer"] = "Fixture Digital"
    assert_true("APPROVED_IDENTITY_VALUES" in failed(run_pre_qa(model=model)), "an unapproved employer alias is blocked")
    # An education entry whose claim is not approved is simply absent from the approved identity: blocked.
    identity = fixture_identity()
    identity["education"] = identity["education"][:1]
    assert_true("APPROVED_IDENTITY_VALUES" in failed(run_pre_qa(identity=identity)), "an education entry without an approved record is blocked")
    # An unapproved claim for a roster entry blocks its bullets; omission with a recorded reason is the permitted path.
    claims = fixture_claims()
    claims["SYN_CLAIM_C1"]["human_approval"] = False
    claims["SYN_CLAIM_C2"]["human_approval"] = False
    assert_true("CANDIDATE_TRUTH_LINEAGE" in failed(run_pre_qa(claims=claims)), "unapproved claims are not used automatically")
    model = model_without_commerce()
    model["roster_omissions"] = [{"roster_entry": "Fixture Commerce Bank", "reason": "TRUTH_APPROVAL_REQUIRED"}]
    result = run_pre_qa(model=model, claims=claims)
    assert_true("ROSTER_POLICY" not in failed(result) and "CANDIDATE_TRUTH_LINEAGE" not in failed(result), "a blocked roster entry is omitted with a recorded reason")
    # Omission never invents filler: thin remaining content fails the page-fill solver instead (covered by the density test).
    print("PASS: current Candidate Truth gaps (GPA, employer alias, unapproved claims and education, links) fail closed or omit with a recorded reason.")


def test_roster_policy() -> None:
    model = model_without_commerce()
    assert_true("ROSTER_POLICY" in failed(run_pre_qa(model=model)), "a missing default roster entry without an omission fails")
    model["roster_omissions"] = [{"roster_entry": "Fixture Commerce Bank", "reason": "NOT_RELEVANT_PER_CROSSWALK"}]
    assert_true("ROSTER_POLICY" not in failed(run_pre_qa(model=model)), "an omission with a crosswalk reason satisfies the policy")
    model = fixture_model()
    model["work"][2].update(employer="Bulmarma 2008 Ltd", title="Reporting Intern", date_range="Jan 2020 - Mar 2020")
    identity = fixture_identity()
    identity["experiences"]["SYN_EXP_C"] = {"title": "Reporting Intern", "employer": "Bulmarma 2008 Ltd", "date_range": "Jan 2020 - Mar 2020"}
    model["roster_omissions"] = [{"roster_entry": "Fixture Commerce Bank", "reason": "NOT_RELEVANT_PER_CROSSWALK"}]
    result = run_pre_qa(model=model, identity=identity)
    assert_true("ROSTER_POLICY" in failed(result) and "Bulmarma" in next(c["detail"] for c in result["checks"] if c["check"] == "ROSTER_POLICY"), "Bulmarma is not automatic")
    model["crosswalk_exception"] = {"bulmarma_requirement_ids": ["REQ_1"]}
    assert_true("ROSTER_POLICY" not in failed(run_pre_qa(model=model, identity=identity)), "Bulmarma enters only through a crosswalk exception")
    record = json.loads((ROOT / "docs" / "resume" / "BORA_SPY_POND_GOLD_REFERENCE_V1.json").read_text(encoding="utf-8"))
    assert_true(builder.load_doctrine_roster(ROOT) == record["presentation_grammar"]["evidence_roster"]["default_included"], "the production roster is the doctrine roster")
    assert_true("ROSTER_POLICY" in failed(run_pre_qa(roster=builder.load_doctrine_roster(ROOT))), "the synthetic fixture does not satisfy the real doctrine roster")
    print("PASS: roster policy follows the doctrine default roster, recorded omissions and the Bulmarma crosswalk exception.")


def legacy_first_render_docx() -> tuple:
    """The sparse scratch first-render fixture (EDUCATION -> EXPERIENCE -> PROJECTS -> SKILLS) rebuilt inline as a NEGATIVE
    regression: no summary, wrong order, one education line, flat skills, comma work headers, plain project heading, no links."""
    texts = [("CONTACT_LINE", "Jordan Example | jordan@example.org | +1 555 010 0199 | Springfield, IL | linkedin.com/in/jordan-example"),
             ("SECTION_HEADING", "EDUCATION"), ("EDUCATION_LINE", "Business Analytics (M.S.), Example State University, Fall 2025 - Summer 2026"),
             ("SECTION_HEADING", "EXPERIENCE"), ("EMPLOYMENT_HEADER", "Fixture Workspace Studio, Operations Analyst Intern, Jun 2026 - Aug 2026"),
             ("BULLET_TEXT", BULLETS["A1"]), ("SECTION_HEADING", "PROJECTS"), ("PROJECT_HEADER", "Fixture Prototype, Python / Streamlit"),
             ("BULLET_TEXT", BULLETS["P1"]), ("SECTION_HEADING", "SKILLS"), ("SKILLS_LINE", "Excel, Python, Streamlit, process mapping")]
    run = '<w:r><w:rPr><w:rFonts w:ascii="Liberation Sans" w:hAnsi="Liberation Sans"/></w:rPr><w:t xml:space="preserve">%s</w:t></w:r>'
    body = "".join("<w:p>" + (run % text) + "</w:p>" for _kind, text in texts)
    document = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document xmlns:w="%s" xmlns:r="%s"><w:body>%s<w:sectPr>'
                '<w:pgSz w:w="12240" w:h="15840"/><w:pgMar w:top="720" w:right="720" w:bottom="720" w:left="720" w:header="360" w:footer="360" w:gutter="0"/>'
                '</w:sectPr></w:body></w:document>') % (builder.NS_W, builder.NS_R, body)
    parts = builder._package_parts(document, metrics(), [])
    structure_map = [{"paragraph_index": i, "content_type": kind, "paragraph_text": text, "list_semantics": None} for i, (kind, text) in enumerate(texts)]
    return builder._zip_bytes(parts), structure_map


def test_first_render_negative_regression() -> None:
    docx_bytes, structure_map = legacy_first_render_docx()
    parsed = qa.parse_docx(docx_bytes)
    checks = qa.artifact_grammar_checks(parsed, [entry["content_type"] for entry in structure_map], metrics(), has_project=True, omissions={},
                                        expected_pairs=[(EMAIL, "mailto:" + EMAIL), ("LinkedIn", LINKEDIN), ("GitHub", GITHUB), ("GitHub", PROJECT_LINK)],
                                        roster=ROSTER)
    failed_names = {check["check"] for check in checks if not check["passed"]}
    for expected in ("SUMMARY_PRESENT_NO_HEADING", "SECTION_ORDER_EXACT", "SKILLS_THREE_RECRUITER_ROWS", "WORK_HEADER_TITLE_PIPE_EMPLOYER_RIGHT_DATE",
                     "EDUCATION_GRAMMAR", "ROSTER_POLICY", "MARKETMIND_HEADING_GRAMMAR", "HYPERLINK_OBJECTS_GENUINE_AND_EXACT", "METRICS_MATCH_DOCTRINE",
                     "NAME_CENTERED_BOLD_SIZE"):
        assert_true(expected in failed_names, f"the first-render negative fixture must fail {expected}: {sorted(failed_names)}")
    assert_true(not all(check["passed"] for check in checks), "the sparse first render never qualifies as Gold")
    post = qa.post_render_qa({**PASS_RECORD, "run_status": qa.RENDER_QA_FAILED_STATUS, "findings": [{"code": "RESUME_PAGE_UNDERUTILIZED"}],
                              "utilization": {"meaningful_content_bottom_fraction": 0.553674}},
                             pdf_facts={"page_count": 1, "pages": [(612.0, 792.0)], "links": []}, expected=build_fixture().expected_links)
    assert_true({"UTILIZATION_AT_OR_ABOVE_FLOOR", "PDF_LINK_SET_EXACT_ORDER_INDEPENDENT", "RENDERER_PASS"} <= failed(post),
                f"about 0.55 utilization and zero links fail post-render QA: {sorted(failed(post))}")
    # The legacy package itself is renderer-compatible, so the failure is Gold QA, not preflight.
    manifest = adapter.verify_manifest((ROOT / "docs" / "rendering" / "RENDERING_ENVIRONMENT_V1.json").read_bytes())
    adapter.build_source_model(adapter.docx_preflight(docx_bytes), manifest, structure_map)
    print("PASS: the sparse first Career OS render fails Gold QA for every known characteristic.")


def test_post_render_qa_vectors() -> None:
    expected = build_fixture().expected_links
    ok = qa.post_render_qa(PASS_RECORD, pdf_facts=fixture_pdf_facts(), expected=expected)
    assert_true(ok["passed"], f"a clean render passes: {ok['failed_checks']}")
    assert_true(ok["human_visual_review"] == "REQUIRED_PENDING", "human visual review stays pending")
    for order in ((0, 1, 2, 3), (0, 3, 2, 1), (3, 2, 1, 0)):
        assert_true(qa.post_render_qa(PASS_RECORD, pdf_facts=fixture_pdf_facts(order=order), expected=expected)["passed"], f"link set equality is independent of PDF annotation order {order}")
    cases = {
        "missing link": (PASS_RECORD, fixture_pdf_facts(drop=3), "PDF_LINK_SET_EXACT_ORDER_INDEPENDENT"),
        "fabricated link": (PASS_RECORD, fixture_pdf_facts(extra=["https://example.org/fabricated"]), "NO_FABRICATED_PDF_LINK"),
        "two pages": (PASS_RECORD, {**fixture_pdf_facts(), "page_count": 2, "pages": [(612.0, 792.0)] * 2}, "ONE_US_LETTER_PAGE"),
        "a4 page": (PASS_RECORD, {**fixture_pdf_facts(), "pages": [(595.0, 842.0)]}, "ONE_US_LETTER_PAGE"),
        "low utilization": ({**PASS_RECORD, "utilization": {"meaningful_content_bottom_fraction": 0.9199}}, fixture_pdf_facts(), "UTILIZATION_AT_OR_ABOVE_FLOOR"),
        "renderer failure": ({**PASS_RECORD, "run_status": "RENDER_ATTRIBUTION_INCOMPLETE", "reason": "HYPHENATION_OBSERVED", "delivered": 0}, fixture_pdf_facts(), "RENDERER_PASS"),
        "renderer findings": ({**PASS_RECORD, "findings": [{"code": "X"}]}, fixture_pdf_facts(), "NO_RENDERER_FINDINGS"),
        "attribution missing": ({**PASS_RECORD, "attribution_digest": None}, fixture_pdf_facts(), "ATTRIBUTION_PASS"),
        "review waived": ({**PASS_RECORD, "human_review_waived": 1}, fixture_pdf_facts(), "HUMAN_VISUAL_REVIEW_STILL_REQUIRED"),
    }
    for label, (record, facts, expected_check) in cases.items():
        result = qa.post_render_qa(record, pdf_facts=facts, expected=expected)
        assert_true(not result["passed"] and expected_check in failed(result), f"{label}: expected {expected_check}, got {sorted(failed(result))}")
    assert_true(qa.UTILIZATION_FLOOR == 0.92, "the canonical 0.92 floor is unchanged")
    print("PASS: post-render QA enforces renderer PASS, one Letter page, the 0.92 floor, exact order-independent link set and pending human review.")


def test_pursuit_gates() -> None:
    with tempfile.TemporaryDirectory() as root:
        deps, renderer = make_deps()
        for decisions, code in ((("WATCH",), "PURSUIT_NOT_AUTHORIZED"), (("REJECT",), "PURSUIT_NOT_AUTHORIZED"), ((), "PURSUIT_NOT_AUTHORIZED")):
            request = make_request(root, decisions=decisions) if decisions else {**make_request(root), "decision_log_rows": []}
            if not decisions:
                request["attestation"] = {**request["attestation"], "latest_event_id": "NONE"}
            expect_package_error(code, ptg.generate_gold_resume_stage, request, deps)
        row, log = pursue_state(("PURSUE",))
        stale_row = {**row, "Last_Verified": "2026-10-01T12:00:00+00:00"}
        request = make_request(root)
        request["jobs_rows"] = [stale_row]
        expect_package_error("PURSUIT_NOT_AUTHORIZED", ptg.generate_gold_resume_stage, request, deps)
        display_only = make_request(root, decisions=("WATCH",))
        display_only["jobs_rows"][0]["Bora_Decision"] = "PURSUE"
        expect_package_error("PURSUIT_NOT_AUTHORIZED", ptg.generate_gold_resume_stage, display_only, deps)
        request = make_request(root)
        request["job_id"] = "UNKNOWN::JOB"
        expect_package_error("UNKNOWN_JOB_ID", ptg.generate_gold_resume_stage, request, deps)
        request = make_request(root)
        request["jobs_rows"].append(copy.deepcopy(request["jobs_rows"][0]))
        expect_package_error("UNKNOWN_JOB_ID", ptg.generate_gold_resume_stage, request, deps)
        assert_true(not renderer.calls and not tree_listing(root), "no render and no output before the gates pass")
        # Stale or cross-context attestation fails closed before any package work.
        for field, value, code in (("job_id", "OTHER::JOB", "ATTESTATION_JOB_MISMATCH"), ("latest_event_id", "PDE_V1::other", "ATTESTATION_EVENT_MISMATCH"),
                                   ("decision_context_fingerprint", "f" * 64, "ATTESTATION_FINGERPRINT_MISMATCH"),
                                   ("application_destination_url", "https://careers.example/other", "ATTESTATION_DESTINATION_MISMATCH")):
            request = make_request(root)
            request["attestation"][field] = value
            expect_package_error(code, ptg.generate_gold_resume_stage, request, deps)
        request = make_request(root)
        request["attestation"]["semantic_quorum"]["matching_requisition_identity"] = False
        expect_package_error("ATTESTATION_QUORUM_NOT_POSITIVE", ptg.generate_gold_resume_stage, request, deps)
        request = make_request(root)
        request["attestation"]["dead_state_veto"] = True
        expect_package_error("ATTESTATION_QUORUM_NOT_POSITIVE", ptg.generate_gold_resume_stage, request, deps)
        request = make_request(root)
        del request["attestation"]["recheck_provenance"]
        expect_package_error("REQUEST_INVALID", ptg.generate_gold_resume_stage, request, deps)
        request = make_request(root)
        request["evidence_matches"][0]["job_id"] = "OTHER::JOB"
        expect_package_error("EVIDENCE_MATCH_BINDING_MISMATCH", ptg.generate_gold_resume_stage, request, deps)
        request = make_request(root)
        request["requirements"][0]["job_id"] = "OTHER::JOB"
        expect_package_error("REQUIREMENT_JOB_MISMATCH", ptg.generate_gold_resume_stage, request, deps)
        assert_true(not renderer.calls and not tree_listing(root), "every gate failure leaves no render and no output")
    print("PASS: the pursuit gates (WATCH, REJECT, none, stale, display-only, unknown job, attestation bindings) fail closed before package work.")


def test_stage_success_idempotency_and_no_mutation() -> None:
    with tempfile.TemporaryDirectory() as root:
        deps, renderer = make_deps()
        request = make_request(root)
        before = copy.deepcopy(request)
        result = ptg.generate_gold_resume_stage(request, deps)
        assert_true(request == before, "the request (JOBS row, LOG rows, model) is not mutated")
        manifest = result["manifest"]
        assert_true(manifest["package_status"] == ptg.STAGE_STATUS and manifest["submission_authority"] == "NONE" and manifest["human_review"] == "REQUIRED_PENDING",
                    "no submission authority and human review pending")
        assert_true(manifest["cover_letter_gold_sha256"] is None and manifest["cover_letter_opt_out_digest"] is None, "the cover-letter pair is recorded as not produced")
        assert_true(not list(build_draft202012_validator(ROOT / "schemas" / "gold_package_manifest.schema.json").iter_errors(manifest)), "manifest validates")
        listing = tree_listing(root)
        assert_true(sorted(Path(p).name for p in listing if Path(root, p).is_file()) == sorted(
            ["claim_wording_review.json", "crosswalk.json", "layout_report.json", "manifest.json", "post_render_qa.json", "pre_render_qa.json", "rendered_document_evidence.json",
             "resume.docx", "resume.pdf", "resume_model.json", "structure_map.json"]), f"outputs are local files only: {listing}")
        out = Path(result["output_dir"])
        assert_true(hashlib.sha256((out / "resume.docx").read_bytes()).hexdigest() == manifest["artifacts"][0]["sha256"], "artifact hashes are bound in the manifest")
        assert_true(manifest["package_generation_id"].startswith("PGP_V1::") and out.name == manifest["package_generation_id"].replace("::", "_"), "deterministic collision-safe identity in the path")
        # Idempotent replay: identical id, manifest and files, no duplicate output.
        again = ptg.generate_gold_resume_stage(make_request(root), make_deps()[0])
        assert_true(again["replayed"] and again["manifest"] == manifest and tree_listing(root) == listing, "an exact replay yields the identical package and no duplicate output")
        # Same package_generation_id with a conflicting payload fails closed.
        original = (out / "manifest.json").read_bytes()
        (out / "manifest.json").write_bytes(original + b" ")
        expect_package_error("CONFLICTING_REPLAY", ptg.generate_gold_resume_stage, make_request(root), make_deps()[0])
        (out / "manifest.json").write_bytes(original)
        # A changed pursuit context, JD or model yields a new identity and never overwrites the prior package.
        changed = make_request(root, package_run_id="RUN_FIXTURE_2")
        other = ptg.generate_gold_resume_stage(changed, make_deps()[0])
        assert_true(other["manifest"]["package_generation_id"] != manifest["package_generation_id"] and (out / "manifest.json").read_bytes() == original, "a new run id gives a new identity")
        # Truth axes: nothing outside the output directory was created or changed.
        assert_true(all(Path(p).parts[0].startswith("PGP_V1_") for p in tree_listing(root) if len(Path(p).parts) == 1), "only package directories exist")
        assert_true(len(renderer.calls) >= 1, "the canonical renderer was called through the injected public interface")
    print("PASS: the resume stage is deterministic, idempotent, conflict-safe, non-mutating and local-only, with no submission authority.")


def test_no_partial_output_and_stale_input() -> None:
    with tempfile.TemporaryDirectory() as root:
        row, log = pursue_state(("PURSUE",))
        deps, _renderer = make_deps(row_log=(row, log))
        # Stale input: the pursuit context changed while the package was being generated.
        stale_row = {**row, "Pipeline_State": "SUBMITTED_ELSEWHERE"}
        deps_stale, _ = make_deps(row_log=(stale_row, log))
        expect_package_error("STALE_INPUT_DETECTED", ptg.generate_gold_resume_stage, make_request(root), deps_stale)
        assert_true(not tree_listing(root), "a stale-input failure leaves no partial output")
        withdrawn_row, withdrawn_log = pursue_state(("PURSUE", "REJECT"))
        deps_withdrawn, _ = make_deps(row_log=(withdrawn_row, withdrawn_log))
        expect_package_error("STALE_INPUT_DETECTED", ptg.generate_gold_resume_stage, make_request(root), deps_withdrawn)
        assert_true(not tree_listing(root), "a withdrawn pursuit leaves no partial output")
        # Pre-render QA failure, renderer failure and post-render QA failure each leave nothing behind.
        bad_claims = fixture_claims()
        bad_claims["SYN_CLAIM_A1"]["human_approval"] = False
        expect_package_error("GOLD_PRE_RENDER_QA_FAILED", ptg.generate_gold_resume_stage, make_request(root), make_deps(claims=bad_claims)[0])
        failing_record = {**PASS_RECORD, "run_status": "RENDER_ATTRIBUTION_INCOMPLETE", "reason": "HYPHENATION_OBSERVED", "delivered": 0}
        expect_package_error("RENDER_NOT_DELIVERED", ptg.generate_gold_resume_stage, make_request(root), make_deps(renderer=FakeRenderer(failing_record, pdf=None))[0])
        expect_package_error("GOLD_POST_RENDER_QA_FAILED", ptg.generate_gold_resume_stage, make_request(root), make_deps(facts=fixture_pdf_facts(drop=1))[0])
        expect_package_error("CLAIM_LINEAGE_INVALID", ptg.generate_gold_resume_stage, make_request(root), make_deps(lineage=lambda claim: ["BROKEN"])[0])
        model_request = make_request(root)
        model_request["resume_model"]["skills"].pop()
        expect_package_error("REQUEST_INVALID", ptg.generate_gold_resume_stage, model_request, make_deps()[0])
        assert_true(not tree_listing(root), "every fail-closed path leaves no partial resume output and no partial manifest")
    print("PASS: stale-input, lineage, pre-render, renderer and post-render failures each leave no partial output.")


def test_cover_letter_boundary() -> None:
    with tempfile.TemporaryDirectory() as root:
        deps, renderer = make_deps()
        error = expect_package_error(ptg.PACKAGE_CAPABILITY_BLOCKED, ptg.generate_gold_package, make_request(root), deps)
        assert_true("COVER_LETTER_PAIR_NOT_PRODUCIBLE" in error.detail, "the full package fails closed while the cover-letter pair cannot be produced")
        optout = make_request(root, cover_letter_opt_out={"job_id": JOB_ID, "latest_event_id": "x", "decision_context_fingerprint": "a" * 64, "approval_record_id": "claimed"})
        error = expect_package_error(ptg.PACKAGE_CAPABILITY_BLOCKED, ptg.generate_gold_package, optout, deps)
        assert_true("OPT_OUT_PROVENANCE_UNAVAILABLE" in error.detail, "a caller-supplied opt-out record is never authority (no resume-only degradation)")
        assert_true(not renderer.calls and not tree_listing(root), "no render and no output on the blocked package path")
        expect_package_error("PURSUIT_NOT_AUTHORIZED", ptg.generate_gold_package, make_request(root, decisions=("WATCH",)), deps)
    print("PASS: the full package contract fails closed on the cover-letter boundary and never degrades to a resume-only package.")


def test_font_metrics_parser() -> None:
    synthetic = builder.FontMetrics.synthetic(0.5, 0.6)
    assert_true(abs(synthetic.width("abcd", 10.0) - 20.0) < 1e-9 and synthetic.width("abcd", 10.0, True) > synthetic.width("abcd", 10.0), "synthetic widths")
    manifest = json.loads((ROOT / "docs" / "rendering" / "RENDERING_ENVIRONMENT_V1.json").read_text(encoding="utf-8"))
    pinned = builder.load_pinned_font_files(manifest)
    assert_true({"LiberationSans-Regular.ttf", "LiberationSans-Bold.ttf"} <= set(pinned) and all(len(v[1]) == 64 for v in pinned.values()), "the manifest pins Liberation Sans file digests")
    try:
        builder.fonts_from_manifest(manifest, lambda path: b"not a font")
        assert_true(False, "a font whose digest does not match the manifest must be refused")
    except builder.GoldBuildError as error:
        assert_true(error.code == "FONT_DIGEST_MISMATCH", "font digest verification")
    try:
        builder.FontMetrics.from_font_bytes(b"\x00" * 64, b"\x00" * 64)
        assert_true(False, "unreadable font bytes fail closed")
    except builder.GoldBuildError as error:
        assert_true(error.code == "FONT_BYTES_UNREADABLE", "unreadable font bytes")
    host = Path("/usr/share/fonts/truetype/liberation")
    if (host / "LiberationSans-Regular.ttf").exists() and (host / "LiberationSans-Bold.ttf").exists():
        real = builder.fonts_from_manifest(manifest, lambda path: Path(path).read_bytes())
        # H, e, l, l, o advance widths are 1479, 1139, 455, 455, 1139 font units of 2048 per em.
        assert_true(abs(real.width("Hello", 10.5) - (1479 + 1139 + 455 + 455 + 1139) * 10.5 / 2048) < 1e-6, "real Liberation Sans advance widths")
        assert_true(abs(real.line_height(10.5) - 12.0740) < 0.001, "real Liberation Sans line height")
        assert_true(real.width("Hello", 10.5, True) > real.width("Hello", 10.5), "bold is wider than regular")
        print("PASS: font metrics parser verified on the host Liberation Sans bytes.")
    else:
        print("PASS: font metrics synthetic/refusal vectors (host Liberation Sans bytes not present; verified in the OPERATOR regression).")


DEPENDENCY_FREE_TESTS = (
    test_model_schema_vectors,
    test_deterministic_docx_and_renderer_preflight,
    test_gold_grammar_pre_render_pass,
    test_pre_render_negative_mutations,
    test_hyperlinks_genuine_and_allowlisted,
    test_structure_map_from_the_same_model,
    test_layout_solver_vectors,
    test_density_and_page_fill_fail_closed,
    test_claim_lineage_vectors,
    test_jargon_prohibition,
    test_truth_gaps_fail_closed_or_omit,
    test_roster_policy,
    test_first_render_negative_regression,
    test_post_render_qa_vectors,
    test_pursuit_gates,
    test_stage_success_idempotency_and_no_mutation,
    test_no_partial_output_and_stale_input,
    test_cover_letter_boundary,
    test_font_metrics_parser,
)


# OPERATOR-gated real regression -------------------------------------------------------------------

def operator_main(argv: list) -> int:
    """--operator-gold-regression --verification-evidence PATH --work-dir DIR: the four-link Gold fixture through the real canonical
    renderer on the OPERATOR (governed interpreter, pinned LibreOffice build, real inspection), three times."""
    options = dict(zip(argv[1::2], argv[2::2]))
    verification = json.loads(Path(options["--verification-evidence"]).read_text(encoding="utf-8"))
    work = Path(options["--work-dir"])
    work.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((ROOT / "docs" / "rendering" / "RENDERING_ENVIRONMENT_V1.json").read_text(encoding="utf-8"))
    fonts = builder.fonts_from_manifest(manifest, lambda path: Path(path).read_bytes())
    model = fixture_model()
    metrics_value = metrics()
    build = builder.build_gold_docx(model, metrics_value, fonts)
    pre = qa.pre_render_qa(model, build, metrics=metrics_value, claims=fixture_claims(), evidence=fixture_evidence(), identity=fixture_identity(),
                           rebuild=lambda: builder.build_gold_docx(model, metrics_value, fonts), roster=ROSTER, approved_language=fixture_language())
    print(json.dumps({"pre_render_qa_passed": pre["passed"], "failed": pre["failed_checks"], "layout": build.layout}, sort_keys=True))
    assert_true(pre["passed"], "pre-render Gold QA passes with the real pinned fonts")
    render = ptg.governed_render_function(ROOT, verification_record=verification, work_dir=str(work / "inputs"))
    fingerprints, records = [], []
    for attempt in range(3):
        record, pdf = render(build.docx_bytes, build.structure_map, str(work / ("render_%d" % attempt)))
        records.append(record)
        print(json.dumps({"attempt": attempt, "run_status": record["run_status"], "reason": record["reason"], "delivered": record["delivered"],
                          "utilization": (record.get("utilization") or {}).get("meaningful_content_bottom_fraction"),
                          "fingerprint": record.get("render_semantic_fingerprint")}, sort_keys=True))
        assert_true(pdf is not None, "the canonical renderer delivered the PDF (reordered annotations accepted)")
        facts = qa.read_pdf_facts(pdf)
        post = qa.post_render_qa(record, pdf_facts=facts, expected=build.expected_links)
        print(json.dumps({"pdf_links_in_pdf_order": facts["links"], "post_render_qa": post["checks"]}, sort_keys=True))
        assert_true(post["passed"], f"post-render Gold QA passes: {post['failed_checks']}")
        fingerprints.append(record["render_semantic_fingerprint"])
        if attempt == 0:
            Path(work / "fixture_gold_resume.pdf").write_bytes(pdf)
            Path(work / "fixture_gold_resume.docx").write_bytes(build.docx_bytes)
    assert_true(len(set(fingerprints)) == 1, "the required repeated renders produce one semantic fingerprint")
    # Production wiring smoke: the canonical claim and evidence repositories load, the protected master supplies the identity, and
    # a fixture model whose claims are not canonical is refused with no output (synthetic fixtures never become Candidate Truth).
    production = ptg.make_governed_deps(ROOT, verification_record=verification, work_dir=str(work / "production_inputs"))
    assert_true(len(production.load_claims()) > 0 and production.identity_provider()["contact"]["name"], "production deps load canonical truth")
    production_root = str(work / "production_out")
    expect_package_error("CLAIM_NOT_FOUND", ptg.generate_gold_resume_stage, make_request(production_root), production)
    assert_true(not [p for p in tree_listing(production_root) if p.startswith("PGP_V1_")], "no package is produced from a non-canonical fixture")
    print(json.dumps({"operator_gold_regression": "PASS", "fingerprint": fingerprints[0], "pdf_link_count": len(facts["links"])}, sort_keys=True))
    return 0


def main() -> None:
    if "--operator-gold-regression" in sys.argv:
        raise SystemExit(operator_main(sys.argv[1:]))
    for test in DEPENDENCY_FREE_TESTS:
        test()
    print(f"PASS: {len(DEPENDENCY_FREE_TESTS)} dependency-free groups of pursue_to_gold_package_v1_test")


if __name__ == "__main__":
    main()
