"""Regression tests for CAREER_OS_RUN_CONTRACT_V1 QA gates (CLAIM_OWNER_ON_PAGE, MANDATORY_EVIDENCE_ON_PAGE).

Real canonical claim/evidence/experience data and the real approved-language library. No network, no rendering.
"""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.dont_write_bytecode = True

import gold_resume_docx_builder as builder  # noqa: E402
import gold_resume_qa as qa  # noqa: E402
import pursue_to_gold_package as ptg  # noqa: E402
from claim_repository import load_validated_claim_repository  # noqa: E402
from evidence_repository import load_validated_evidence_repository  # noqa: E402
from experience_repository import load_validated_experience_repository  # noqa: E402


def ok(cond, msg):
    if not cond:
        print("FAIL:", msg)
        raise SystemExit(1)


claims = load_validated_claim_repository(ROOT / "claims")["index"]
evidence = load_validated_evidence_repository(ROOT / "evidence")["index"]
experiences = load_validated_experience_repository(ROOT / "experiences").index
library = json.loads((ROOT / "docs" / "resume" / "BORA_APPROVED_RESUME_LANGUAGE_V1.json").read_text(encoding="utf-8"))
identity = ptg.approved_identity_from_canonical_records(ROOT, claims=claims, evidence=evidence, experiences=experiences)
bullet = {item["bullet_id"]: item for item in library["bullets"]}
summary = {item["summary_id"]: item for item in library["summaries"]}
metrics = builder.load_gold_metrics(ROOT)[0]
fonts = builder.FontMetrics.synthetic(0.49, 0.53)
roster = ptg.display_roster(builder.load_doctrine_roster(ROOT), identity)


def entry(experience_id, bullet_ids):
    record = identity["experiences"][experience_id]
    return {"experience_id": experience_id, "title": record["title"], "employer": record["employer"], "date_range": record["date_range"],
            "bullets": [{"text": bullet[key]["text"], "claim_ids": bullet[key]["claim_ids"]} for key in bullet_ids]}


def skill_rows(technical):
    return [
        {"label": "Process & quality", "items": ["Data reconciliation", "Data validation", "Process mapping", "UAT documentation"],
         "claim_ids": ["CLAIM_DCOMMERCE_001", "CLAIM_WW_003", "CLAIM_MM_005", "CLAIM_WW_006", "CLAIM_WW_005"]},
        {"label": "Technical", "items": technical,
         "claim_ids": ["CLAIM_BULMARMA_001", "CLAIM_DCOMMERCE_001", "CLAIM_LOANIQ_SQL_001", "CLAIM_MM_001", "CLAIM_LOANIQ_STACK_001"]},
        {"label": "Operations", "items": ["Financial reporting", "Regulatory reporting", "Budget and cash-flow reporting", "Trend analysis"],
         "claim_ids": ["CLAIM_DCOMMERCE_001", "CLAIM_BULMARMA_001", "CLAIM_DCOMMERCE_002", "CLAIM_TELUS_002"]},
    ]


def corrected_model():
    """Real-data fixture: LoanIQ is the single project with approved B017+B018; MarketMind is removed; the summary's owners are all rendered."""
    loan = identity["experiences"]["EXP_LOANIQ_001"]
    return {
        "model_id": "RUN_CONTRACT_CORRECTED_V1", "job_id": "RUN_CONTRACT::FIXTURE", "contact": copy.deepcopy(identity["contact"]),
        "summary": {"text": summary["S001"]["text"], "claim_ids": summary["S001"]["claim_ids"]},
        "education": copy.deepcopy(identity["education"]),
        "skills": skill_rows(["Microsoft Excel", "SQL (SQLite)", "Python", "Pandas"]),
        "work": [entry("EXP_WW_001", ["B010", "B012", "B014", "B013"]), entry("EXP_TELUS_001", ["B008", "B009"]),
                 entry("EXP_BULMARMA_001", ["B016"]), entry("EXP_DCOMMERCE_001", ["B001", "B002"])],
        "project": {"experience_id": "EXP_LOANIQ_001", "name": loan["project_name"], "tech_label": loan["project_tech_label"],
                    "link": identity["project_links"]["EXP_LOANIQ_001"],
                    "bullets": [{"text": bullet[key]["text"], "claim_ids": bullet[key]["claim_ids"]} for key in ("B017", "B018")]},
        "crosswalk_exception": {"bulmarma_requirement_ids": ["REQ_FINANCE"]},
        "roster_omissions": [{"roster_entry": "MarketMind", "reason": "NOT_RELEVANT_PER_CROSSWALK"}],
    }


def run(model, crosswalk=()):
    build = builder.build_gold_docx(model, metrics, fonts)
    return build, qa.pre_render_qa(model, build, metrics=metrics, claims=claims, evidence=evidence, identity=identity,
                                   rebuild=lambda: builder.build_gold_docx(model, metrics, fonts), roster=roster, approved_language=library,
                                   crosswalk=list(crosswalk))


def check_failed(result, name):
    return name in result["failed_checks"]


def mandatory(claim_ids, results=("STRONG",), importance="MANDATORY"):
    return [{"requirement_id": "REQ_SQL", "importance": importance, "results": list(results), "claim_ids": list(claim_ids), "evidence_ids": []}]


def without_loaniq(model):
    """The pre-correction production shape: MarketMind is the single project and EXP_LOANIQ_001 is absent from the page."""
    bad = copy.deepcopy(model)
    mm = identity["experiences"]["EXP_MM_001"]
    bad["project"] = {"experience_id": "EXP_MM_001", "name": mm["project_name"], "tech_label": mm["project_tech_label"],
                      "link": identity["project_links"]["EXP_MM_001"],
                      "bullets": [{"text": bullet[key]["text"], "claim_ids": bullet[key]["claim_ids"]} for key in ("B003", "B004", "B005", "B007")]}
    bad["roster_omissions"] = []
    return bad


# 1. Corrected real-data fixture passes both gates and is one-page-capable.
good = corrected_model()
ok(not qa.approved_language_problems(good, library, claims, evidence), "corrected fixture uses only approved language")
build, result = run(good, mandatory(["CLAIM_LOANIQ_SQL_001"]))
ok(result["passed"], "corrected fixture passes pre-render QA: " + json.dumps([c for c in result["checks"] if not c["passed"]]))
ok(build.layout["estimated_bottom_fraction"] >= 0.92, "corrected fixture is one-page-capable")
names = [c["check"] for c in result["checks"]]
ok("CLAIM_OWNER_ON_PAGE" in names and "MANDATORY_EVIDENCE_ON_PAGE" in names, "stable check names are present")

# 2. Fracto-style: S001 renders but EXP_LOANIQ_001 is absent.
fracto = without_loaniq(good)
fracto["skills"] = skill_rows(["Microsoft Excel", "Python"])
_, result = run(fracto)
ok(check_failed(result, "CLAIM_OWNER_ON_PAGE"), "S001 without LoanIQ fails CLAIM_OWNER_ON_PAGE")
ok("CLAIM_LOANIQ_SQL_001" in [c for c in result["checks"] if c["check"] == "CLAIM_OWNER_ON_PAGE"][0]["detail"], "the failure names the unowned LoanIQ claim")

# 3. J.Jill-style: S003 plus SQL/Pandas skills without LoanIQ.
jjill = without_loaniq(good)
jjill["summary"] = {"text": summary["S003"]["text"], "claim_ids": summary["S003"]["claim_ids"]}
_, result = run(jjill)
ok(check_failed(result, "CLAIM_OWNER_ON_PAGE"), "S003 + SQL/Pandas without LoanIQ fails CLAIM_OWNER_ON_PAGE")
detail = [c for c in result["checks"] if c["check"] == "CLAIM_OWNER_ON_PAGE"][0]["detail"]
ok("skill 'SQL (SQLite)'" in detail or "skill 'Pandas'" in detail or "CLAIM_MM_003" in detail, "the failure names a skill or summary claim without a rendered owner")
skills_only = without_loaniq(good)
_, result = run(skills_only)
ok(any("skill 'Pandas'" in p for p in qa.claim_owner_on_page_problems(skills_only, claims, evidence, identity, library)),
   "a Pandas skill item fails without its LoanIQ owner even though unrelated row-level claims are owned")
# Unrelated row-level claims cannot rescue a skill item.
ok(not any("Excel" in p for p in qa.claim_owner_on_page_problems(skills_only, claims, evidence, identity, library)),
   "Excel is owned by rendered Bulmarma/D Commerce so it is not flagged")

# 4. Summary with no / unknown owner fails.
unknown = copy.deepcopy(good)
unknown["summary"] = {"text": summary["S001"]["text"], "claim_ids": ["CLAIM_DOES_NOT_EXIST"]}
ok(any("no canonical evidence owner" in p for p in qa.claim_owner_on_page_problems(unknown, claims, evidence, identity, library)),
   "an unknown summary claim has no owner and fails")

# 5. Education owners count; the mapping is derived from the approved identity, not hard-coded.
kinds = qa.rendered_owner_kinds(good, identity)
ok(kinds.get("EXP_EDU_BRANDEIS_001") == "EDUCATION" and kinds.get("EXP_LOANIQ_001") == "PROJECT" and kinds.get("EXP_WW_001") == "WORK",
   "rendered owners come from work/project experience_id and the identity's school mapping")
ok(identity["education_experience_ids"] == {"Brandeis University": "EXP_EDU_BRANDEIS_001", "University of National and World Economy": "EXP_EDU_UNWE_001"},
   "school -> education experience_id is derived from the approved overlay")
no_edu_map = copy.deepcopy(identity)
no_edu_map["education_experience_ids"] = {}
ok(any("CLAIM_EDU_BRANDEIS_001" in p for p in qa.claim_owner_on_page_problems(good, claims, evidence, no_edu_map, library)),
   "without a derivable education owner the education claim fails")

# 6. MANDATORY_EVIDENCE_ON_PAGE.
skill_only = without_loaniq(good)
_, result = run(skill_only, mandatory(["CLAIM_LOANIQ_SQL_001"]))
ok(check_failed(result, "MANDATORY_EVIDENCE_ON_PAGE"), "mandatory SQL with the LoanIQ claim only in skills/summary fails MANDATORY_EVIDENCE_ON_PAGE")
problems = qa.mandatory_evidence_on_page_problems(good, mandatory(["CLAIM_LOANIQ_SQL_001"]), claims, evidence, identity)
ok(problems == [], "the same crosswalk passes when a rendered project bullet cites the claim")
ok(qa.mandatory_evidence_on_page_problems(good, mandatory([]), claims, evidence, identity), "positive mandatory match with no claim_ids fails")
ok(not qa.mandatory_evidence_on_page_problems(good, mandatory([], results=("NONE",)), claims, evidence, identity), "a NONE result is not a positive match")
ok(not qa.mandatory_evidence_on_page_problems(good, mandatory([], importance="PREFERRED"), claims, evidence, identity), "non-mandatory requirements are not gated")
ok(not qa.mandatory_evidence_on_page_problems(good, mandatory(["CLAIM_EDU_BRANDEIS_001"], results=("SUPPORTED",)), claims, evidence, identity),
   "a rendered education owner satisfies a mandatory education requirement")
ok(qa.mandatory_evidence_on_page_problems(good, mandatory(["CLAIM_MM_001"], results=("PARTIAL",)), claims, evidence, identity),
   "a mandatory claim whose owner is not rendered fails")
ok(qa.mandatory_evidence_on_page_problems(good, [{"requirement_id": "R", "results": ["STRONG"], "claim_ids": ["CLAIM_WW_001"]}], claims, evidence, identity),
   "a crosswalk entry without importance fails closed")
try:
    qa.pre_render_qa(good, build, metrics=metrics, claims=claims, evidence=evidence, identity=identity,
                     rebuild=lambda: build, roster=roster, approved_language=library)
    ok(False, "crosswalk must be a required keyword")
except TypeError:
    pass

# 7. The existing B017-under-Winter-Walk placement remains a failure.
wrong = copy.deepcopy(good)
wrong["work"][0]["bullets"][0] = {"text": bullet["B017"]["text"], "claim_ids": bullet["B017"]["claim_ids"]}
ok(any("CLAIM_LOANIQ_SQL_001 is not evidenced by that experience" in p for p in qa.approved_language_problems(wrong, library, claims, evidence)),
   "B017 under Winter Walk still fails")
_, result = run(wrong)
ok(check_failed(result, "APPROVED_RESUME_LANGUAGE_EXACT"), "B017 under Winter Walk fails pre-render QA")

# 8. run_gates carries requirement importance into the crosswalk.
import inspect  # noqa: E402
ok('"importance": requirement["importance"]' in inspect.getsource(ptg.run_gates), "run_gates records requirement importance on each crosswalk entry")

print("PASS: CAREER_OS_RUN_CONTRACT_V1 QA gates (CLAIM_OWNER_ON_PAGE, MANDATORY_EVIDENCE_ON_PAGE)")
