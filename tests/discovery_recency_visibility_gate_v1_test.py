from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
BLUEPRINT = (ROOT / "BLUEPRINT.md").read_text(encoding="utf-8")
RULE = (ROOT / ".cursor" / "rules" / "role-selection.mdc").read_text(encoding="utf-8")
CONTRACT = json.loads((ROOT / "milestone_contracts" / "feature" / "discovery-recency-visibility-gate-v1.json").read_text(encoding="utf-8"))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


require("**Bora-facing recency visibility gate (fail closed).**" in BLUEPRINT, "Blueprint visibility gate missing")
require("reliable employer/official-ATS posting date" in BLUEPRINT, "posting-date anchor missing")
require("dated application-intake window" in BLUEPRINT, "application-window anchor missing")
require("résumé-upload form" in BLUEPRINT and "does **not** satisfy this gate" in BLUEPRINT, "live apply/upload must not rescue unanchored recency")
require("suppress\nthe role from Bora-facing discovery" in BLUEPRINT, "unanchored role must be suppressed")
require("do not generate a package" in BLUEPRINT, "unanchored role must not be packaged")
require("no longer accepting applications" in BLUEPRINT, "explicit closure signal missing")
require("newer first-party employer/official-ATS source explicitly says applications are currently\nopen again" in BLUEPRINT, "closure override must require newer first-party reopening")
require("Closure-state evidence and posting-age provenance are distinct" in BLUEPRINT, "closure/date provenance separation missing")
require("`discovered_date`" in BLUEPRINT and "`date_first_seen`" in BLUEPRINT, "discovery timestamps must remain non-authoritative")
require("aggregator age" in BLUEPRINT and "social-platform age" in BLUEPRINT, "non-authoritative age sources must be rejected")
require("First-party actionability is necessary but" in BLUEPRINT and "not sufficient by itself" in BLUEPRINT, "live route must not bypass recency visibility")
require("Only roles that pass the §138.5" in BLUEPRINT, "serious-role output must be gated")
require("Freshness remains\n`UNKNOWN` and Discovery Window remains `UNKNOWN_WINDOW`" in BLUEPRINT, "dated application-window rescue must not fabricate posting date")
require("never convert the\napplication-window date into an employer posting date" in BLUEPRINT, "application-window date must never become employer posting date")
require("live Apply/upload route cannot rescue a role whose recency is unanchored" in BLUEPRINT, "§138.6 must explicitly block live-route rescue")
require("not Qualification Truth" in BLUEPRINT, "visibility gate must remain outside Qualification Truth")
require("recency-unverified" in BLUEPRINT, "internal recency-unverified state must remain available")

require("alwaysApply: true" in RULE, "role-selection rule must remain always-on")
require("Bora-facing recency visibility gate (§138.5)" in RULE, "always-on visibility pointer missing")
require("live Apply button" in RULE and "insufficient" in RULE, "quick-reference must reject live-route-only rescue")
require("suppress the role" in RULE and "do not package it" in RULE, "quick-reference must fail closed")
require("closed/expired/filled/no longer accepting applications" in RULE, "quick-reference closure states missing")
require("Closure status never upgrades" in RULE, "quick-reference must separate closure from age provenance")
for token in (
    "0-7 days = GOLD_WINDOW",
    "8-14 days = STRETCH_WINDOW",
    "15-21 days = FAR_STRETCH_WINDOW",
    "22+ days = EXCEPTION_ONLY_WINDOW",
):
    require(token in BLUEPRINT, f"prior discovery window drifted: {token}")

require("**Final Locked Blueprint v3.13**" in BLUEPRINT, "pinned Blueprint banner drifted")
require(CONTRACT["baseline_sha"] == "df185c1c8341cf25e23a253bc63cf328b7410fa8", "contract baseline drifted")
require("src/" in CONTRACT["forbidden_paths"] and "schemas/" in CONTRACT["forbidden_paths"], "runtime/schema boundaries missing")

print("PASS: Bora-facing recency visibility fails closed without authoritative recency and suppresses closed roles")
