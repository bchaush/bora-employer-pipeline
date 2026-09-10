from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
BLUEPRINT = (ROOT / "BLUEPRINT.md").read_text(encoding="utf-8")
RULE = (ROOT / ".cursor" / "rules" / "role-selection.mdc").read_text(encoding="utf-8")
CONTRACT = json.loads((ROOT / "milestone_contracts" / "feature" / "discovery-start-horizon-gate-v1.json").read_text(encoding="utf-8"))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


require("138.14 Start horizon gate" in BLUEPRINT, "Blueprint start horizon gate section missing")
require("**0-30 days = TARGETED near-term\nwindow**" in BLUEPRINT, "0-30 day TARGETED window missing")
require(
    "actively target — Career OS should actively seek out and\nprioritize discovery/application effort toward roles expected to start\nwithin this window" in BLUEPRINT,
    "active-target rationale for 0-30 day window missing",
)
require("**31-60\ndays = acceptable around-target window**" in BLUEPRINT, "31-60 day acceptable window missing")
require("**more\nthan 60 days = suppressed from Bora-facing serious discovery and package\ngeneration**" in BLUEPRINT, "suppression rule for >60 days missing")
require("unless Bora explicitly requests a future-start pipeline for\nthat role" in BLUEPRINT, "future-start pipeline override missing")
require("or explicitly overrides the timing gate for that specific role" in BLUEPRINT, "explicit per-role override missing")
require(
    "An unstated or unreliably inferred start date remains `UNKNOWN` and is\nnever suppressed merely because the employer omitted a start date" in BLUEPRINT,
    "UNKNOWN start date preservation missing",
)
require("`UNKNOWN` is not treated as far-future" in BLUEPRINT, "UNKNOWN must not be treated as far-future")
require(
    "A near application deadline or a\nrecently posted/fresh role (§138.5) cannot rescue a role with a known\nstart date more than 60 days out" in BLUEPRINT,
    "deadline/freshness cannot rescue clause missing",
)
require(
    "posting freshness and start-date horizon\nare independent axes, and freshness never overrides a known far-future\nstart" in BLUEPRINT,
    "independence of freshness and start-horizon missing",
)

require("Brattle — Research Analyst (Economics and\nFinance), known intended start July 2027" in BLUEPRINT, "Brattle motivating example missing")
require("evaluated on 2026-09-09, the known start date is far more than 60 days" in BLUEPRINT, "Brattle evaluation date missing")
require("carries a September 14,\n2026 application deadline" in BLUEPRINT, "Brattle application deadline detail missing")
require("The near deadline does not rescue the known\nfar-future start" in BLUEPRINT, "Brattle deadline-does-not-rescue conclusion missing")

require(
    "changes Qualification Truth, Employer Truth, Candidate Truth, Match Truth,\nauthorization, or actionability (§135/§138.6)" in BLUEPRINT,
    "start horizon gate must remain scoped to Pursuit/discovery timing doctrine only",
)

require(
    "Only roles that pass the §138.5\nBora-facing recency visibility gate AND the §138.14 start horizon gate may\nbe promoted into this serious-role output" in BLUEPRINT,
    "§138.8 must require BOTH the recency visibility gate and the start horizon gate before serious-role promotion",
)
require(
    "a role suppressed under either\ngate does not enter serious-role output or package generation regardless of\nits status under the other gate" in BLUEPRINT,
    "§138.8 must state that failing either gate suppresses the role regardless of the other gate's status",
)
require(
    "promotion into serious-role output\n  requires passing BOTH the §138.5 recency visibility gate AND the §138.14\n  start horizon gate; failing either one suppresses the role regardless of\n  the other" in RULE,
    "role-selection.mdc quick-reference must restate the §138.8/§138.14 cross-gate dependency",
)
require(
    "Promotion under the §138.5 recency visibility gate additionally requires the §138.5 recency hard cutoff to PASS"
    in BLUEPRINT.replace("\n", " "),
    "§138.8 must additionally require the §138.5 recency hard cutoff to PASS as part of the recency visibility gate",
)

require("alwaysApply: true" in RULE, "role-selection rule must remain always-on")
require("Start horizon gate (§138.14)" in RULE, "always-on start horizon pointer missing")
require(
    "0-30 days from the\n  current operating date = TARGETED near-term window (actively target —" in RULE,
    "quick-reference TARGETED near-term window missing",
)
require("31-60 days =\n  acceptable around-target window" in RULE, "quick-reference around-target window missing")
require("more than 60 days = suppress from\n  Bora-facing serious discovery and package generation" in RULE, "quick-reference suppression rule missing")
require("`UNKNOWN` and is never suppressed merely because it was omitted" in RULE, "quick-reference UNKNOWN preservation missing")
require(
    "A near\n  application deadline or recent posting never rescues a known far-future\n  start" in RULE,
    "quick-reference deadline-cannot-rescue missing",
)
require("Brattle" in RULE and "July 2027" in RULE, "quick-reference Brattle pointer missing")

for token in (
    "0-7 days = GOLD_WINDOW",
    "8-14 days = STRETCH_WINDOW",
    "15-21 days = FAR_STRETCH_WINDOW",
    "22+ days = SUPPRESSED_WINDOW",
):
    require(token in BLUEPRINT, f"prior discovery window drifted: {token}")

require(
    "**Bora-facing recency visibility gate (fail closed).**" in BLUEPRINT,
    "prior recency visibility gate must remain unchanged",
)
require(
    "REMOTE**, **CONTRACT/CONTRACT-TO-HIRE/TEMPORARY**, and" in BLUEPRINT,
    "prior work-format preference lock must remain unchanged",
)
require(
    "Any explicit dead/error-page state (including page-not-found," in BLUEPRINT,
    "prior live actionability semantic quorum lock must remain unchanged",
)

require("**Final Locked Blueprint v3.13**" in BLUEPRINT, "pinned Blueprint banner drifted")
require(CONTRACT["baseline_sha"] == "e22a80c852d0266785cdbb315b328fe3eebfa432", "contract baseline drifted")
require("src/" in CONTRACT["forbidden_paths"] and "schemas/" in CONTRACT["forbidden_paths"], "runtime/schema boundaries missing")

print("PASS: Start horizon gate locks 0-30/31-60/>60 bands, preserves UNKNOWN, blocks deadline rescue, and records Brattle example")
