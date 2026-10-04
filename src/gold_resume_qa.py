"""Executable Gold resume QA (PURSUE_TO_GOLD_PACKAGE_V1, model-built reconciliation).

This is executable validation over the actual artifacts, not JSON-record doctrine checks: the PRE-RENDER checks parse
the generated DOCX package itself (paragraphs, runs, relationships, section properties) and compare it with the
approved model, the approved Candidate Truth and the canonical Gold doctrine; the POST-RENDER checks read the
renderer's evidence record and the delivered PDF. A check list is returned in full; the result passes only when every
check passes. Human visual review always remains pending.
"""

from __future__ import annotations

import hashlib
import json
import re
import zipfile
import io
import xml.etree.ElementTree as ET
from typing import Any, Callable, Mapping, Optional, Sequence

from gold_resume_docx_builder import (
    CANONICAL_CONTENT_TYPES,
    CONTACT_SEPARATOR,
    CT_BULLET,
    CT_CONTACT,
    CT_EDUCATION,
    CT_EMPLOYMENT,
    CT_HEADING,
    CT_NAME,
    CT_PROJECT,
    CT_SKILLS,
    CT_SUMMARY,
    GoldBuild,
    GoldBuildError,
    GoldMetrics,
    PAGE_FILL_TARGET,
    SECTION_HEADINGS,
    SKILLS_ROW_LABELS,
    canonical_json_bytes,
    expected_links,
    model_digest,
)

QA_ID = "GOLD_RESUME_QA_V1"
UTILIZATION_FLOOR = 0.92
RENDER_PASS_STATUS = "RENDER_QA_AUTOMATED_PASS_HUMAN_REVIEW_REQUIRED"
RENDER_QA_FAILED_STATUS = "RENDER_QA_AUTOMATED_FAILED"
LETTER_WIDTH_PT, LETTER_HEIGHT_PT = 612.0, 792.0
ALLOWED_PARTS = frozenset({"[Content_Types].xml", "_rels/.rels", "word/document.xml", "word/_rels/document.xml.rels",
                           "word/numbering.xml", "word/styles.xml"})
SUMMARY_HEADING_LABELS = frozenset({"PROFESSIONAL SUMMARY", "SUMMARY", "PROFILE", "PROFESSIONAL PROFILE", "OBJECTIVE",
                                    "CAREER OBJECTIVE", "ABOUT ME", "EXECUTIVE SUMMARY", "SUMMARY OF QUALIFICATIONS"})
ROSTER_OMISSION_REASONS = frozenset({"TRUTH_APPROVAL_REQUIRED", "NOT_RELEVANT_PER_CROSSWALK"})
ACCEPTABLE_EVIDENCE_STATES = frozenset({"VERIFIED", "SUPPORTED", "OBSERVED"})
DATE_RANGE = re.compile(r"^[A-Z][a-z]{2} \d{4} - ([A-Z][a-z]{2} \d{4}|Present)$")
# Internal Career OS / governance vocabulary that must never reach candidate-facing text unless the exact term is
# independently job-relevant (at minimum the BORA_PACKAGE_SPAWN_GATE_V1 terms).
JARGON_TERMS = ("human approval", "operating system", "fail-closed", "fail closed", "queue-level eligibility",
                "deterministic boundary", "candidate truth", "evidencematch", "evidence match", "claim_id", "evidence_id",
                "career os", "evidence system", "governance", "claim lineage", "kill switch")
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
REL = "{http://schemas.openxmlformats.org/package/2006/relationships}"


def _check(name: str, passed: bool, detail: str = "") -> dict:
    return {"check": name, "passed": bool(passed), "detail": detail}


def _digest(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _result(checks: list, extra: Optional[dict] = None) -> dict:
    result = {"qa_id": QA_ID, "passed": all(item["passed"] for item in checks), "checks": checks,
              "failed_checks": [item["check"] for item in checks if not item["passed"]],
              "human_visual_review": "REQUIRED_PENDING"}
    result.update(extra or {})
    result["result_digest"] = _digest({key: value for key, value in result.items() if key != "result_digest"})
    return result


# DOCX parsing -----------------------------------------------------------------------------------

def parse_docx(docx_bytes: bytes) -> dict:
    """Paragraph, run, relationship and section facts of a generated DOCX (the artifact itself, not the model)."""
    archive = zipfile.ZipFile(io.BytesIO(docx_bytes))
    names = [info.filename for info in archive.infolist()]
    document = ET.fromstring(archive.read("word/document.xml"))
    rels = ET.fromstring(archive.read("word/_rels/document.xml.rels"))
    relationships = {}
    for rel in rels.findall(REL + "Relationship"):
        relationships[rel.get("Id")] = {"type": rel.get("Type").rsplit("/", 1)[-1], "target": rel.get("Target"),
                                        "external": rel.get("TargetMode") == "External"}
    body = document.find(W + "body")
    paragraphs = []
    for paragraph in body.findall(W + "p"):
        properties = paragraph.find(W + "pPr")
        facts = {"runs": [], "text": "", "centered": False, "tab_right": None, "border_bottom": False, "bullet": False, "right_indent": 0}
        if properties is not None:
            jc = properties.find(W + "jc")
            facts["centered"] = jc is not None and jc.get(W + "val") == "center"
            tabs = properties.find(W + "tabs")
            if tabs is not None:
                tab = tabs.find(W + "tab")
                facts["tab_right"] = int(tab.get(W + "pos")) if tab is not None and tab.get(W + "val") == "right" else None
            facts["border_bottom"] = properties.find(W + "pBdr") is not None and properties.find(W + "pBdr").find(W + "bottom") is not None
            facts["bullet"] = properties.find(W + "numPr") is not None
            indent = properties.find(W + "ind")
            facts["right_indent"] = int(indent.get(W + "right", "0")) if indent is not None else 0
        pieces = []

        def read_run(run: ET.Element, link_id: Optional[str]) -> None:
            run_properties = run.find(W + "rPr")
            fonts = run_properties.find(W + "rFonts") if run_properties is not None else None
            size = run_properties.find(W + "sz") if run_properties is not None else None
            text = ""
            for child in run:
                if child.tag == W + "t":
                    text += child.text or ""
                elif child.tag == W + "tab":
                    text += "\t"
            facts["runs"].append({"text": text, "bold": run_properties is not None and run_properties.find(W + "b") is not None,
                                  "size": int(size.get(W + "val")) if size is not None else None,
                                  "ascii": fonts.get(W + "ascii") if fonts is not None else None,
                                  "hansi": fonts.get(W + "hAnsi") if fonts is not None else None,
                                  "theme_font": fonts is not None and any(key.endswith("Theme") for key in fonts.attrib),
                                  "link": link_id})
            pieces.append(text)

        for child in paragraph:
            if child.tag == W + "r":
                read_run(child, None)
            elif child.tag == W + "hyperlink":
                for run in child.findall(W + "r"):
                    read_run(run, child.get(R + "id"))
        facts["text"] = "".join(pieces).replace("\t", " ")
        paragraphs.append(facts)
    section = body.find(W + "sectPr")
    size = section.find(W + "pgSz")
    margins = section.find(W + "pgMar")
    styles = ET.fromstring(archive.read("word/styles.xml"))
    default_fonts = styles.find(W + "docDefaults").find(W + "rPrDefault").find(W + "rPr").find(W + "rFonts")
    return {"names": names, "relationships": relationships, "paragraphs": paragraphs,
            "page": (int(size.get(W + "w")), int(size.get(W + "h"))),
            "margins": {key: int(margins.get(W + key)) for key in ("top", "right", "bottom", "left")},
            "default_font": (default_fonts.get(W + "ascii"), default_fonts.get(W + "hAnsi")),
            "raw_parts": {name: archive.read(name) for name in names}}


def derive_structure_map(parsed: Mapping[str, Any]) -> list:
    """The structure map that the DOCX paragraphs themselves imply (text, order, list semantics); content types are
    compared against the generated map by the binding check."""
    return [{"paragraph_index": index, "paragraph_text": paragraph["text"],
             "list_semantics": {"ilvl": 0, "numFmt": "bullet", "numId": 1} if paragraph["bullet"] else None}
            for index, paragraph in enumerate(parsed["paragraphs"])]


# Text inventory and lineage -----------------------------------------------------------------

def candidate_facing_texts(model: Mapping[str, Any]) -> list:
    texts = [("summary", model["summary"]["text"], model["summary"].get("claim_ids", []))]
    for row in model["skills"]:
        texts.append(("skills:" + row["label"], row["label"] + ": " + ", ".join(row["items"]), row.get("claim_ids", [])))
    for entry in model["work"]:
        for number, bullet in enumerate(entry["bullets"]):
            texts.append(("work:%s:%d" % (entry["experience_id"], number), bullet["text"], bullet.get("claim_ids", [])))
    project = model.get("project")
    if project:
        for number, bullet in enumerate(project["bullets"]):
            texts.append(("project:%s:%d" % (project["experience_id"], number), bullet["text"], bullet.get("claim_ids", [])))
    return texts


def _all_visible_text(model: Mapping[str, Any]) -> str:
    parts = [model["contact"]["name"], model["summary"]["text"]]
    for school in model["education"]:
        parts += [school["school"], school["date_range"], school["degree_line"]]
    parts += [row["label"] + ": " + ", ".join(row["items"]) for row in model["skills"]]
    for entry in model["work"]:
        parts += [entry["title"], entry["employer"], entry["date_range"]] + [bullet["text"] for bullet in entry["bullets"]]
    project = model.get("project")
    if project:
        parts += [project["name"], project["tech_label"]] + [bullet["text"] for bullet in project["bullets"]]
    return "\n".join(parts)


def jargon_hits(text: str, job_relevant_terms: Sequence[str] = ()) -> list:
    lowered = text.lower()
    relevant = {term.lower() for term in job_relevant_terms}
    return sorted(term for term in JARGON_TERMS if term in lowered and term not in relevant)


def _numbers(text: str) -> set:
    return set(re.findall(r"\d[\d,]*(?:\.\d+)?%?\+?", text))


def check_lineage(model: Mapping[str, Any], claims: Mapping[str, Any]) -> list:
    """Every candidate-facing factual text binds to approved claims; numbers are grounded in the cited claim wording."""
    problems = []
    for name, text, claim_ids in candidate_facing_texts(model):
        if not claim_ids:
            problems.append("%s: no claim lineage" % name)
            continue
        grounded = ""
        for claim_id in claim_ids:
            claim = claims.get(claim_id)
            if claim is None:
                problems.append("%s: unknown claim %s" % (name, claim_id))
                continue
            if claim.get("human_approval") is not True:
                problems.append("%s: claim %s is not human-approved" % (name, claim_id))
            if claim.get("evidence_state") not in ACCEPTABLE_EVIDENCE_STATES:
                problems.append("%s: claim %s evidence state %s" % (name, claim_id, claim.get("evidence_state")))
            contexts = claim.get("allowed_contexts", [])
            if isinstance(contexts, list) and "resume" not in contexts:
                problems.append("%s: claim %s not allowed in resume context" % (name, claim_id))
            lowered = text.lower()
            for forbidden in claim.get("forbidden_contexts", []) if isinstance(claim.get("forbidden_contexts"), list) else []:
                if forbidden.lower() in lowered:
                    problems.append("%s: forbidden context phrase %r from %s" % (name, forbidden, claim_id))
            grounded += " " + claim.get("wording", "")
        ungrounded = _numbers(text) - _numbers(grounded)
        if ungrounded:
            problems.append("%s: numbers not grounded in cited claims: %s" % (name, sorted(ungrounded)))
    return problems


def check_identity(model: Mapping[str, Any], identity: Mapping[str, Any]) -> list:
    problems = []
    contact, approved = model["contact"], identity["contact"]
    for key in ("name", "location", "phone", "email"):
        if (contact.get(key) or None) != (approved.get(key) or None):
            problems.append("contact.%s differs from the approved record" % key)
    approved_links = {(link["label"], link["url"]) for link in approved.get("profile_links", [])}
    model_links = [(link["label"], link["url"]) for link in contact.get("profile_links", [])]
    for link in model_links:
        if link not in approved_links:
            problems.append("profile link %s is not an approved contact link" % (link,))
    approved_schools = {school["school"]: school for school in identity["education"]}
    for school in model["education"]:
        record = approved_schools.get(school["school"])
        if record is None:
            problems.append("education %s is not approved" % school["school"])
        elif (record["date_range"], record["degree_line"]) != (school["date_range"], school["degree_line"]):
            problems.append("education %s date or degree differs from the approved record" % school["school"])
    for entry in model["work"]:
        record = identity["experiences"].get(entry["experience_id"])
        expected = (record["title"], record["employer"], record["date_range"]) if record else None
        if expected != (entry["title"], entry["employer"], entry["date_range"]):
            problems.append("work entry %s title, employer or dates differ from the approved record" % entry["experience_id"])
    project = model.get("project")
    if project:
        record = identity["experiences"].get(project["experience_id"])
        if record is None or record.get("project_name") != project["name"] or record.get("project_tech_label") != project["tech_label"]:
            problems.append("project %s differs from the approved record" % project["experience_id"])
        if project.get("link"):
            approved_project = identity.get("project_links", {}).get(project["experience_id"])
            if approved_project != {"label": project["link"]["label"], "url": project["link"]["url"]}:
                problems.append("project link is not an approved project link")
    return problems


# PRE-RENDER QA ----------------------------------------------------------------------------------

def artifact_grammar_checks(parsed: Mapping[str, Any], types: Sequence[str], metrics: GoldMetrics, *, has_project: bool,
                            omissions: Mapping[str, str], expected_pairs: Sequence[tuple], roster: Sequence[str], bulmarma_exception: bool = False) -> list:
    """Gold grammar checks over the DOCX artifact itself (parsed paragraphs, runs, relationships, section properties)
    and its structure-map content types. These need no model, so the sparse legacy first render can be run through
    them as a negative regression."""
    checks = []
    paragraphs = list(parsed["paragraphs"])
    types = list(types)
    # Package rules (renderer-preflight compatible; no legacy baggage).
    names = set(parsed["names"])
    external_ok = all(rel["type"] == "hyperlink" and rel["external"] and rel["target"].split(":", 1)[0].lower() in ("https", "http", "mailto")
                      for rel in parsed["relationships"].values() if rel["external"])
    checks.append(_check("PACKAGE_PARTS_CANONICAL", names == ALLOWED_PARTS and not any(name.startswith("customXml") for name in names),
                         "parts=%s" % sorted(names)))
    checks.append(_check("NO_UNSUPPORTED_EXTERNAL_RELATIONSHIP", external_ok))
    checks.append(_check("METRICS_MATCH_DOCTRINE", parsed["page"] == (metrics.page_width_twips, metrics.page_height_twips) and parsed["margins"] ==
                         {"top": metrics.margin_top_twips, "right": metrics.margin_right_twips, "bottom": metrics.margin_bottom_twips,
                          "left": metrics.margin_left_twips}, "page=%s margins=%s" % (parsed["page"], parsed["margins"])))
    runs = [run for paragraph in paragraphs for run in paragraph["runs"]]
    fonts_ok = all(run["ascii"] == metrics.font_family and run["hansi"] == metrics.font_family and not run["theme_font"] for run in runs) \
        and parsed["default_font"] == (metrics.font_family, metrics.font_family)
    checks.append(_check("FONT_RULES_LIBERATION_SANS", fonts_ok))
    # No summary heading; a natural summary directly below the contact line.
    summary_ok = len(paragraphs) > 3 and types[2:3] == [CT_SUMMARY] and bool(paragraphs[2]["text"].strip()) \
        and not any(paragraph["text"].strip().upper() in SUMMARY_HEADING_LABELS for paragraph in paragraphs)
    checks.append(_check("SUMMARY_PRESENT_NO_HEADING", summary_ok, "types[:4]=%s" % types[:4]))
    # Section order.
    heading_texts = [p["text"] for p, kind in zip(paragraphs, types) if kind == CT_HEADING]
    expected_order = list(SECTION_HEADINGS) if has_project else list(SECTION_HEADINGS[:3])
    checks.append(_check("SECTION_ORDER_EXACT", heading_texts == expected_order, "found=%s" % heading_texts))
    heading_ok = bool(heading_texts)
    for paragraph, kind in zip(paragraphs, types):
        if kind == CT_HEADING:
            run = paragraph["runs"][0]
            heading_ok = heading_ok and run["bold"] and run["size"] == metrics.heading_half_points and paragraph["border_bottom"]
    checks.append(_check("HEADING_GRAMMAR_BOLD_RULE_SIZE", heading_ok))
    # Name and contact grammar.
    name_ok = bool(types) and types[0] == CT_NAME and paragraphs[0]["centered"] and paragraphs[0]["runs"][0]["bold"] \
        and paragraphs[0]["runs"][0]["size"] == metrics.name_half_points
    checks.append(_check("NAME_CENTERED_BOLD_SIZE", name_ok))
    contact_ok = len(types) > 1 and types[1] == CT_CONTACT and paragraphs[1]["centered"] and CONTACT_SEPARATOR in paragraphs[1]["text"]
    checks.append(_check("CONTACT_LINE_GRAMMAR", contact_ok, paragraphs[1]["text"] if len(paragraphs) > 1 else ""))
    # Skills rows.
    skill_texts = [p["text"] for p, kind in zip(paragraphs, types) if kind == CT_SKILLS]
    labels_ok = len(skill_texts) == 3 and all(text.startswith(label + ": ") for text, label in zip(skill_texts, SKILLS_ROW_LABELS))
    checks.append(_check("SKILLS_THREE_RECRUITER_ROWS", labels_ok, "rows=%d" % len(skill_texts)))
    # Work headers: Title | Employer, bold left, right tab, date range. Education: school + date, degree line below.
    work_headers = [p for p, kind in zip(paragraphs, types) if kind == CT_EMPLOYMENT]
    work_ok = bool(work_headers)
    for paragraph in work_headers:
        left, right = paragraph["runs"][0], paragraph["runs"][-1]["text"]
        work_ok = work_ok and left["bold"] and paragraph["tab_right"] == metrics.text_width_twips and left["text"].count(" | ") == 1 \
            and bool(DATE_RANGE.match(right))
    checks.append(_check("WORK_HEADER_TITLE_PIPE_EMPLOYER_RIGHT_DATE", work_ok))
    education = [p for p, kind in zip(paragraphs, types) if kind == CT_EDUCATION]
    school_count = len(education) // 2
    edu_ok = len(education) % 2 == 0 and 1 <= school_count <= 2
    for position in range(0, len(education) - 1, 2):
        header, degree = education[position], education[position + 1]
        edu_ok = edu_ok and header["tab_right"] is not None and header["runs"][0]["bold"] and bool(DATE_RANGE.match(header["runs"][-1]["text"]))             and degree["tab_right"] is None and bool(degree["text"].strip())
    checks.append(_check("EDUCATION_GRAMMAR", edu_ok, "education paragraphs=%d" % len(education)))
    # Roster policy over the artifact text.
    document_text = "\n".join(paragraph["text"] for paragraph in paragraphs).lower()
    roster_problems = []
    for name in roster:
        if name.lower() not in document_text and omissions.get(name) not in ROSTER_OMISSION_REASONS:
            roster_problems.append("%s missing without a recorded omission" % name)
    if "bulmarma" in document_text and not bulmarma_exception:
        roster_problems.append("Bulmarma included without a crosswalk exception")
    checks.append(_check("ROSTER_POLICY", not roster_problems, "; ".join(roster_problems)))
    # MarketMind heading grammar: plain 'Name - Technology label' with a right-side GitHub hyperlink.
    project_paragraphs = [p for p, kind in zip(paragraphs, types) if kind == CT_PROJECT]
    marketmind_ok = bool(project_paragraphs) == has_project
    for paragraph in project_paragraphs:
        marketmind_ok = marketmind_ok and " - " in paragraph["runs"][0]["text"] and paragraph["runs"][0]["bold"] and paragraph["tab_right"] is not None \
            and paragraph["runs"][-1]["link"] is not None and paragraph["runs"][-1]["text"] == "GitHub"
    checks.append(_check("MARKETMIND_HEADING_GRAMMAR", marketmind_ok))
    # Hyperlinks: genuine relationships and the exact expected (label, destination) set, never styled text alone.
    found = []
    for paragraph in paragraphs:
        for run in paragraph["runs"]:
            if run["link"]:
                rel = parsed["relationships"].get(run["link"])
                found.append((run["text"], rel["target"] if rel and rel["type"] == "hyperlink" and rel["external"] else None))
    checks.append(_check("HYPERLINK_OBJECTS_GENUINE_AND_EXACT", sorted(found) == sorted(expected_pairs) and bool(expected_pairs), "found=%s" % sorted(found)))
    plain_link_text = any(run["text"] == label and run["link"] is None for paragraph in paragraphs for run in paragraph["runs"]
                          for label, _url in expected_pairs if label in ("LinkedIn", "GitHub"))
    checks.append(_check("NO_STYLED_TEXT_WITHOUT_LINK_OBJECT", not plain_link_text))
    return checks


def pre_render_qa(model: Mapping[str, Any], build: GoldBuild, *, metrics: GoldMetrics, claims: Mapping[str, Any],
                  identity: Mapping[str, Any], rebuild: Callable[[], GoldBuild], roster: Sequence[str],
                  job_relevant_terms: Sequence[str] = ()) -> dict:
    try:
        parsed = parse_docx(build.docx_bytes)
    except Exception as error:  # a package the QA cannot read is a failed package
        return _result([_check("DOCX_PARSEABLE", False, type(error).__name__)])
    checks = [_check("DOCX_PARSEABLE", True)]
    types = [entry["content_type"] for entry in build.structure_map]
    expected = expected_links(model)
    expected_pairs = sorted((link.label, link.url) for link in expected)
    omissions = {item["roster_entry"]: item["reason"] for item in model.get("roster_omissions", [])}
    checks += artifact_grammar_checks(parsed, types, metrics, has_project=bool(model.get("project")), omissions=omissions,
                                      expected_pairs=expected_pairs, roster=roster,
                                      bulmarma_exception=bool(model.get("crosswalk_exception", {}).get("bulmarma_requirement_ids")))
    paragraphs = parsed["paragraphs"]
    # Model-to-artifact binding of identity text.
    contact_parts = [part for part in (model["contact"].get("location"), model["contact"].get("phone")) if part]
    contact_parts += [model["contact"]["email"]] if model["contact"].get("email") else []
    contact_parts += [link["label"] for link in model["contact"].get("profile_links", [])]
    checks.append(_check("CONTACT_LINE_MATCHES_MODEL", paragraphs[1]["text"] == CONTACT_SEPARATOR.join(contact_parts)))
    checks.append(_check("SKILLS_ROW_LABELS_MATCH_MODEL", [row["label"] for row in model["skills"]] == list(SKILLS_ROW_LABELS)))
    approved_pairs = {(link["label"], link["url"]) for link in identity["contact"].get("profile_links", [])}
    approved_pairs.add((identity["contact"].get("email"), "mailto:" + (identity["contact"].get("email") or "")))
    approved_pairs |= {(value["label"], value["url"]) for value in identity.get("project_links", {}).values()}
    checks.append(_check("HYPERLINK_ALLOWLIST_APPROVED", all(pair in approved_pairs for pair in expected_pairs),
                         "unapproved=%s" % [pair for pair in expected_pairs if pair not in approved_pairs]))
    problems = check_lineage(model, claims)
    checks.append(_check("CANDIDATE_TRUTH_LINEAGE", not problems, "; ".join(problems[:6])))
    identity_problems = check_identity(model, identity)
    checks.append(_check("APPROVED_IDENTITY_VALUES", not identity_problems, "; ".join(identity_problems[:6])))
    hits = jargon_hits(_all_visible_text(model), job_relevant_terms)
    checks.append(_check("RECRUITER_JARGON_PROHIBITION", not hits, "hits=%s" % hits))
    try:
        again = rebuild()
        deterministic = again.docx_bytes == build.docx_bytes and again.structure_map == build.structure_map
    except GoldBuildError:
        deterministic = False
    checks.append(_check("DOCX_BYTES_DETERMINISTIC", deterministic))
    derived = derive_structure_map(parsed)
    bound = len(derived) == len(build.structure_map) and all(
        entry["paragraph_index"] == item["paragraph_index"] and entry["paragraph_text"] == item["paragraph_text"]
        and entry["list_semantics"] == item["list_semantics"] and entry["content_type"] in CANONICAL_CONTENT_TYPES
        for entry, item in zip(build.structure_map, derived))
    checks.append(_check("STRUCTURE_MAP_BOUND_TO_DOCX_AND_MODEL", bound))
    checks.append(_check("STRUCTURE_MAP_CANONICAL_VOCABULARY", set(types) <= set(CANONICAL_CONTENT_TYPES)))
    estimated = build.layout.get("estimated_bottom_fraction", 0)
    checks.append(_check("PREDICTED_PAGE_FILL_IN_WINDOW", UTILIZATION_FLOOR <= estimated, "estimated=%s" % estimated))
    return _result(checks, {"model_digest": model_digest(model), "docx_sha256": hashlib.sha256(build.docx_bytes).hexdigest(),
                            "structure_map_digest": _digest(build.structure_map), "expected_links": [[l.label, l.url] for l in expected]})


# POST-RENDER QA ---------------------------------------------------------------------------------

def read_pdf_facts(pdf_bytes: bytes) -> dict:
    """Page count, page sizes and genuine link annotations of the delivered PDF, read with the pinned pypdf."""
    try:
        from pypdf import PdfReader
    except ImportError as error:
        raise GoldBuildError("PDF_FACTS_UNAVAILABLE", "pypdf not importable") from error
    reader = PdfReader(io.BytesIO(pdf_bytes))
    pages, links = [], []
    for page in reader.pages:
        box = page.mediabox
        pages.append((float(box.width), float(box.height)))
        for annotation in page.get("/Annots", []) or []:
            annotation = annotation.get_object()
            if annotation.get("/Subtype") != "/Link":
                continue
            action = annotation.get("/A")
            action = action.get_object() if action is not None else None
            if action is not None and action.get("/S") == "/URI":
                links.append(str(action.get("/URI")))
            else:
                links.append("NON_URI_LINK")
    return {"page_count": len(pages), "pages": pages, "links": links}


def post_render_qa(record: Mapping[str, Any], *, pdf_facts: Mapping[str, Any], expected: Sequence[Any], runs_compared: int = 1) -> dict:
    checks = []
    status = record.get("run_status")
    checks.append(_check("RENDERER_PASS", status == RENDER_PASS_STATUS and record.get("delivered") == 1 and record.get("reason") is None,
                         "run_status=%s reason=%s" % (status, record.get("reason"))))
    pages = pdf_facts.get("pages", [])
    letter = len(pages) == 1 and abs(pages[0][0] - LETTER_WIDTH_PT) <= 1.0 and abs(pages[0][1] - LETTER_HEIGHT_PT) <= 1.0
    checks.append(_check("ONE_US_LETTER_PAGE", pdf_facts.get("page_count") == 1 and letter, "pages=%s" % pages))
    utilization = (record.get("utilization") or {}).get("meaningful_content_bottom_fraction")
    checks.append(_check("UTILIZATION_AT_OR_ABOVE_FLOOR", isinstance(utilization, (int, float)) and utilization >= UTILIZATION_FLOOR,
                         "utilization=%s floor=%s" % (utilization, UTILIZATION_FLOOR)))
    checks.append(_check("NO_RENDERER_FINDINGS", not record.get("findings")))
    checks.append(_check("ATTRIBUTION_PASS", record.get("attribution_digest") is not None and record.get("render_semantic_fingerprint") is not None))
    automated = {item.get("check") for item in record.get("automated_checks", [])}
    checks.append(_check("FONT_PROOF_PRESENT_AND_RENDERER_PASS", "FONT_EMBEDDING_AND_IDENTITY" in automated and status == RENDER_PASS_STATUS))
    expected_urls = sorted(link.url if hasattr(link, "url") else link[1] for link in expected)
    pdf_links = sorted(pdf_facts.get("links", []))
    checks.append(_check("PDF_LINK_SET_EXACT_ORDER_INDEPENDENT", pdf_links == expected_urls, "pdf=%s expected=%s" % (pdf_links, expected_urls)))
    checks.append(_check("NO_FABRICATED_PDF_LINK", "NON_URI_LINK" not in pdf_links and len(pdf_links) == len(expected_urls)))
    human = {item.get("check") for item in record.get("human_required", [])}
    checks.append(_check("HUMAN_VISUAL_REVIEW_STILL_REQUIRED", "VISUAL_REVIEW_OF_RAW_PDF_AND_DOCX" in human and record.get("human_review_waived") == 0))
    return _result(checks, {"utilization": utilization, "render_semantic_fingerprint": record.get("render_semantic_fingerprint"),
                            "runs_compared": runs_compared})
