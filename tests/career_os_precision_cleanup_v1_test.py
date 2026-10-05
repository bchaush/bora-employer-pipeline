from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.dont_write_bytecode = True

import gold_resume_docx_builder as builder
import gold_resume_qa as qa
import pursue_to_gold_package as ptg
from claim_repository import load_validated_claim_repository
from evidence_repository import load_validated_evidence_repository
from experience_repository import load_validated_experience_repository


def ok(cond, msg):
    if not cond:
        print("FAIL:", msg)
        raise SystemExit(1)


claims = load_validated_claim_repository(ROOT / "claims")
evidence = load_validated_evidence_repository(ROOT / "evidence")
experiences = load_validated_experience_repository(ROOT / "experiences")
library = json.loads((ROOT / "docs" / "resume" / "BORA_APPROVED_RESUME_LANGUAGE_V1.json").read_text(encoding="utf-8"))
identity = ptg.approved_identity_from_canonical_records(
    ROOT, claims=claims["index"], evidence=evidence["index"], experiences=experiences.index
)
ok(claims["valid"] and evidence["valid"] and experiences.valid, "canonical truth repositories validate")
ok(library["status"] == "CURRENT_APPROVED" and library["approval"]["approved"] is True, "approved language is current")

bullet = {x["bullet_id"]: x for x in library["bullets"]}
summary = {x["summary_id"]: x for x in library["summaries"]}

# 1. Exact approved language / row-scoped skills.
model = {
    "model_id": "PRECISION_BULMARMA_V1",
    "job_id": "PRECISION::FIXTURE",
    "contact": copy.deepcopy(identity["contact"]),
    "summary": {"text": summary["S004"]["text"], "claim_ids": summary["S004"]["claim_ids"]},
    "education": copy.deepcopy(identity["education"]),
    "skills": [
        {"label": "Process & quality", "items": ["Data reconciliation", "Data validation", "Process mapping", "UAT documentation"],
         "claim_ids": ["CLAIM_DCOMMERCE_001", "CLAIM_WW_003", "CLAIM_MM_005", "CLAIM_WW_006", "CLAIM_WW_005"]},
        {"label": "Technical", "items": ["Microsoft Excel", "SQL (SQLite)", "Python", "Pandas"],
         "claim_ids": ["CLAIM_BULMARMA_001", "CLAIM_DCOMMERCE_001", "CLAIM_LOANIQ_SQL_001", "CLAIM_MM_001", "CLAIM_LOANIQ_STACK_001"]},
        {"label": "Operations", "items": ["Financial reporting", "Regulatory reporting", "Budget and cash-flow reporting", "Trend analysis"],
         "claim_ids": ["CLAIM_DCOMMERCE_001", "CLAIM_BULMARMA_001", "CLAIM_DCOMMERCE_002", "CLAIM_TELUS_002"]},
    ],
    "work": [
        {"experience_id": "EXP_WW_001", "title": identity["experiences"]["EXP_WW_001"]["title"],
         "employer": identity["experiences"]["EXP_WW_001"]["employer"], "date_range": identity["experiences"]["EXP_WW_001"]["date_range"],
         "bullets": [
             {"text": bullet["B010"]["text"], "claim_ids": bullet["B010"]["claim_ids"]},
             {"text": bullet["B012"]["text"], "claim_ids": bullet["B012"]["claim_ids"]},
             {"text": bullet["B014"]["text"], "claim_ids": bullet["B014"]["claim_ids"]},
             {"text": bullet["B013"]["text"], "claim_ids": bullet["B013"]["claim_ids"]},
         ]},
        {"experience_id": "EXP_TELUS_001", "title": identity["experiences"]["EXP_TELUS_001"]["title"],
         "employer": identity["experiences"]["EXP_TELUS_001"]["employer"], "date_range": identity["experiences"]["EXP_TELUS_001"]["date_range"],
         "bullets": [
             {"text": bullet["B008"]["text"], "claim_ids": bullet["B008"]["claim_ids"]},
             {"text": bullet["B009"]["text"], "claim_ids": bullet["B009"]["claim_ids"]},
         ]},
        {"experience_id": "EXP_BULMARMA_001", "title": identity["experiences"]["EXP_BULMARMA_001"]["title"],
         "employer": identity["experiences"]["EXP_BULMARMA_001"]["employer"], "date_range": identity["experiences"]["EXP_BULMARMA_001"]["date_range"],
         "bullets": [{"text": bullet["B016"]["text"], "claim_ids": bullet["B016"]["claim_ids"]}]},
        {"experience_id": "EXP_DCOMMERCE_001", "title": identity["experiences"]["EXP_DCOMMERCE_001"]["title"],
         "employer": identity["experiences"]["EXP_DCOMMERCE_001"]["employer"], "date_range": identity["experiences"]["EXP_DCOMMERCE_001"]["date_range"],
         "bullets": [
             {"text": bullet["B001"]["text"], "claim_ids": bullet["B001"]["claim_ids"]},
             {"text": bullet["B002"]["text"], "claim_ids": bullet["B002"]["claim_ids"]},
         ]},
    ],
    "project": {
        "experience_id": "EXP_MM_001",
        "name": identity["experiences"]["EXP_MM_001"]["project_name"],
        "tech_label": identity["experiences"]["EXP_MM_001"]["project_tech_label"],
        "link": identity["project_links"]["EXP_MM_001"],
        "bullets": [
            {"text": bullet["B003"]["text"], "claim_ids": bullet["B003"]["claim_ids"]},
            {"text": bullet["B004"]["text"], "claim_ids": bullet["B004"]["claim_ids"]},
            {"text": bullet["B005"]["text"], "claim_ids": bullet["B005"]["claim_ids"]},
            {"text": bullet["B007"]["text"], "claim_ids": bullet["B007"]["claim_ids"]},
        ],
    },
    "crosswalk_exception": {"bulmarma_requirement_ids": ["REQ_FINANCE"]},
}
ok(not qa.approved_language_problems(model, library), "full real model uses only approved language")

# Known production failure must fail.
bad = copy.deepcopy(model)
bad["work"][0]["bullets"][0] = {
    "text": "Block live email execution when test mode, follow-up, or master-sending gates are disabled.",
    "claim_ids": ["CLAIM_WW_002"],
}
ok(any("not exact approved bullet language" in x for x in qa.approved_language_problems(bad, library)), "inverted WW_002 fails")

# Embedded control characters fail regardless of claim lineage.
bad = copy.deepcopy(model)
bad["work"][0]["bullets"][0]["text"] += "\nsecond line"
ok(qa.candidate_control_character_problems(bad), "embedded newline fails")

# Row-specific skill gate.
bad = copy.deepcopy(model)
bad["skills"][0]["items"][0] = "SQL (SQLite)"
ok(any("not approved for row Process & quality" in x for x in qa.approved_language_problems(bad, library)), "row-mismatched SQL fails")
bad = copy.deepcopy(model)
bad["skills"][1]["items"][1] = "Advanced SQL"
ok(any("Advanced SQL" in x for x in qa.approved_language_problems(bad, library)), "Advanced SQL fails")
ok(("Technical", "SQL (SQLite)") in {(x["row"], x["text"]) for x in library["skills"]}, "approved SQL (SQLite) exists")
ok(("Technical", "TypeScript") in {(x["row"], x["text"]) for x in library["skills"]}, "Market Empire TypeScript skill exists")

# 2. Real Gold pre-render with Bulmarma and exactly one project remains one-page-capable.
metrics = builder.load_gold_metrics(ROOT)[0]
fonts = builder.FontMetrics.synthetic(0.49, 0.53)
build = builder.build_gold_docx(model, metrics, fonts)
pre = qa.pre_render_qa(
    model, build, metrics=metrics, claims=claims["index"], identity=identity,
    rebuild=lambda: builder.build_gold_docx(model, metrics, fonts),
    roster=ptg.display_roster(builder.load_doctrine_roster(ROOT), identity),
    approved_language=library,
)
ok(pre["passed"], "Bulmarma + one project full resume passes pre-render QA: " + json.dumps([x for x in pre["checks"] if not x["passed"]]))
ok(build.layout["estimated_bottom_fraction"] >= 0.92, "predicted page fill stays at or above 92 percent")
ok(sum(1 for _ in [model["project"]] if _) == 1, "exactly one project slot is populated")

# 3. Pinned evidence and certainty boundaries.
ok(claims["index"]["CLAIM_BULMARMA_001"]["human_approval"] is True, "Bulmarma is approved")
ok(claims["index"]["CLAIM_BULMARMA_001"]["evidence_state"] == "OBSERVED", "Bulmarma remains OBSERVED")
ok(claims["index"]["CLAIM_EDU_BRANDEIS_001"]["evidence_state"] == "OBSERVED", "Brandeis awarded claim remains OBSERVED")
ok("8778cbbd453cc654529c3bf1d70bfc2a848158a8" in json.dumps(evidence["index"]["LOANIQ_SQL_001"]), "LoanIQ evidence is pinned")
ok("c86338d0ba6f891ae09bf39fc5f135eb1ad2b5c4" in json.dumps(evidence["index"]["MARKET_EMPIRE_TECH_001"]), "Market Empire evidence is pinned")

print("PASS: CAREER_OS_PRECISION_CLEANUP_V1 real-data regressions")
