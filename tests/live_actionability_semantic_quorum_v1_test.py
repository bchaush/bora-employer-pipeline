"""Regression lock for LIVE_ACTIONABILITY_SEMANTIC_QUORUM_V1.

Reproduces the Point32Health R9102 false-positive class: HTTP 200 plus a
surviving requisition token must never pass when positive role/title or
substantive-current-JD identity is absent, or when an explicit dead-page
marker is present. Doctrine-only consistency test; no runtime validator.
"""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
BLUEPRINT = (ROOT / "BLUEPRINT.md").read_text(encoding="utf-8")
AGENTS = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
RESUME_MDC = (ROOT / ".cursor" / "rules" / "resume.mdc").read_text(encoding="utf-8")
RECORD = json.loads((ROOT / "docs" / "resume" / "BORA_PACKAGE_SPAWN_GATE_V1.json").read_text(encoding="utf-8"))


def semantic_quorum(*, http_200, title_match, req_match, jd_present, route_present, dead_marker):
    return bool(title_match and req_match and jd_present and route_present and not dead_marker)


def require(cond, msg):
    if not cond:
        raise AssertionError(msg)


require(not semantic_quorum(http_200=True, title_match=False, req_match=True, jd_present=False, route_present=False, dead_marker=True),
        "Point32Health-style HTTP-200 dead page must fail closed")
require(not semantic_quorum(http_200=True, title_match=True, req_match=True, jd_present=True, route_present=True, dead_marker=True),
        "explicit dead/error marker must veto otherwise-positive signals")
require(semantic_quorum(http_200=True, title_match=True, req_match=True, jd_present=True, route_present=True, dead_marker=False),
        "all positive semantic signals with no dead marker should pass this doctrine model")
require(semantic_quorum(http_200=False, title_match=True, req_match=True, jd_present=True, route_present=True, dead_marker=False),
        "HTTP 200 must not become a required positive quorum member")
for text, name in ((BLUEPRINT, "BLUEPRINT.md"), (AGENTS, "AGENTS.md"), (RESUME_MDC, ".cursor/rules/resume.mdc")):
    lower = " ".join(text.lower().split())
    require("http 200" in lower, f"{name} must say HTTP 200 alone is insufficient")
    require("requisition token" in lower or "requisition string" in lower, f"{name} must reject token-only verification")
    require("role/title identity" in lower, f"{name} must require positive role/title identity")
    require("substantive current job-description content" in lower, f"{name} must require substantive current JD content")
    require("dead/error" in lower, f"{name} must make explicit dead/error state fail closed")

failures = RECORD["reproduced_failures"]
require("point32health" in failures, "package gate record must capture Point32Health reproduced failure")
require("HTTP 200" in failures["point32health"]["description"] and "TITLE_MATCH=False" in failures["point32health"]["description"], "record must preserve HTTP-200 and TITLE_MATCH=False false-positive details")
quorum = RECORD["package_gate_disqualifying_conditions"].get("semantic_quorum", "")
for token in ("role/title identity", "requisition identity", "substantive current JD", "application route"):
    require(token in quorum, f"record semantic_quorum must include {token}")
require("veto" in quorum.lower(), "explicit dead/error marker must be a veto in the package record")

require("Santander" in BLUEPRINT and "DraftKings" in BLUEPRINT, "prior package-gate failure history must remain intact")
require("GOLD_REFERENCE_ARTIFACT_REQUIRED" in BLUEPRINT, "gold artifact stop condition must remain intact")

# Every positive quorum member must fail independently when absent.
base=dict(http_200=True, title_match=True, req_match=True, jd_present=True, route_present=True, dead_marker=False)
for missing in ("title_match", "req_match", "jd_present", "route_present"):
    case=dict(base); case[missing]=False
    require(not semantic_quorum(**case), f"missing {missing} must fail closed independently")

for text, name in ((BLUEPRINT, "BLUEPRINT.md"), (AGENTS, "AGENTS.md"), (RESUME_MDC, ".cursor/rules/resume.mdc")):
    lower=" ".join(text.lower().split())
    require("matching requisition identity" in lower, f"{name} must require matching requisition identity")
    require("current actionable application route" in lower, f"{name} must require current application route")
require("Point32Health" in BLUEPRINT and "R9102" in BLUEPRINT and "TITLE_MATCH=False" in BLUEPRINT,
        "BLUEPRINT must cite the Point32Health R9102 TITLE_MATCH=False reproduced failure")
for text, name in ((AGENTS, "AGENTS.md"), (RESUME_MDC, ".cursor/rules/resume.mdc")):
    require("Point32Health" in text and "R9102" in text and "TITLE_MATCH=False" in text,
            f"{name} must cite the Point32Health R9102 TITLE_MATCH=False reproduced failure")
conditions=" ".join(RECORD["package_gate_disqualifying_conditions"]["conditions"]).lower()
require("http-200 response" in conditions and "dead/error state" in conditions,
        "record must explicitly disqualify HTTP-200 dead/error pages")
require("missing positive role/title identity" in conditions and "requisition token" in conditions,
        "record must explicitly disqualify missing title identity even when token survives")

print("PASS: live actionability semantic quorum blocks HTTP-200/token-only dead-page false positives")