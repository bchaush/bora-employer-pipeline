from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
BLUEPRINT = (ROOT / "BLUEPRINT.md").read_text(encoding="utf-8")
RULE = (ROOT / ".cursor" / "rules" / "role-selection.mdc").read_text(encoding="utf-8")
CONTRACT = json.loads(
    (ROOT / "milestone_contracts" / "feature" / "discovery-recency-hard-cutoff-v1.json").read_text(encoding="utf-8")
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


# --- 0-7 / 8-14 / 15-21 bands are unchanged (direct regression: 21-day survives) ---
require("0-7 days = GOLD_WINDOW" in BLUEPRINT, "GOLD_WINDOW band drifted")
require("8-14 days = STRETCH_WINDOW" in BLUEPRINT, "STRETCH_WINDOW band drifted")
require(
    "15-21 days = FAR_STRETCH_WINDOW" in BLUEPRINT,
    "FAR_STRETCH_WINDOW band drifted -- a role at 21 days must still survive as FAR_STRETCH_WINDOW, not be suppressed",
)
require("`GOLD_WINDOW` = 0-7 days" in RULE, "GOLD_WINDOW band drifted in rule")
require("`STRETCH_WINDOW` = 8-14 days" in RULE, "STRETCH_WINDOW band drifted in rule")
require("`FAR_STRETCH_WINDOW` = 15-21 days" in RULE, "FAR_STRETCH_WINDOW band drifted in rule")

# --- 22-day hard cutoff (direct regression: 22-day suppresses) ---
require("22+ days = SUPPRESSED_WINDOW" in BLUEPRINT, "22+ day SUPPRESSED_WINDOW hard cutoff missing from BLUEPRINT")
require("`SUPPRESSED_WINDOW` = 22+ days" in RULE, "22+ day SUPPRESSED_WINDOW hard cutoff missing from rule")
require(
    "suppressed from normal Bora-facing serious discovery and package generation"
    in BLUEPRINT.replace("\n", " "),
    "hard cutoff must suppress from normal Bora-facing serious discovery and package generation",
)
require(
    "suppressed from normal Bora-facing\n  serious discovery and package generation" in RULE
    or "suppressed from normal Bora-facing" in RULE,
    "rule must teach the same hard-cutoff suppression",
)

# --- old EXCEPTION_ONLY_WINDOW escape hatch is fully retired, not just renamed ---
require("EXCEPTION_ONLY_WINDOW" not in BLUEPRINT, "old EXCEPTION_ONLY_WINDOW label must be fully retired from BLUEPRINT")
require("EXCEPTION_ONLY_WINDOW" not in RULE, "old EXCEPTION_ONLY_WINDOW label must be fully retired from rule")
require(
    "no automatic strength-based escape hatch" in RULE,
    "rule must state there is no automatic strength-based rescue at 22+ days",
)
require(
    "not an automatic strength-based escape hatch" in BLUEPRINT.replace("\n", " "),
    "BLUEPRINT must state there is no automatic strength-based rescue at 22+ days",
)

# --- explicit per-role Bora override is the only path past the cutoff ---
require(
    "only an explicit Bora override of the recency cutoff for that specific role" in BLUEPRINT.replace("\n", " "),
    "BLUEPRINT must preserve the explicit per-role Bora override as the only path past the hard cutoff",
)
require(
    "only an explicit Bora override" in RULE and "of the recency cutoff for that specific role" in RULE,
    "rule must preserve the explicit per-role Bora override as the only path past the hard cutoff",
)

# --- UNKNOWN/unpublished posting age stays UNKNOWN_WINDOW, never treated as 22+ ---
require(
    "never itself treated as `SUPPRESSED_WINDOW`" in BLUEPRINT.replace("\n", " "),
    "UNKNOWN_WINDOW must never be treated as SUPPRESSED_WINDOW merely because the date is missing",
)
require(
    "treated as `SUPPRESSED_WINDOW` merely because the date is missing" in RULE,
    "rule must preserve UNKNOWN_WINDOW neutrality against the hard cutoff",
)

# --- Pursuit Truth scope only; no qualification/actionability/start-horizon/package/schema drift ---
require(
    "0-2 days = VERY_FRESH" in BLUEPRINT
    and "3-7 days = FRESH" in BLUEPRINT
    and "8-14 days = AGING" in BLUEPRINT
    and "15+ days = STALE_LEANING" in BLUEPRINT,
    "existing Freshness day-band vocabulary must remain unchanged",
)
require(
    "presentation/governance vocabulary only" in BLUEPRINT and "not a schema enum" in BLUEPRINT,
    "window overlay must remain presentation/governance only, never a schema/runtime enum",
)
require("**Final Locked Blueprint v3.13**" in BLUEPRINT, "pinned Blueprint banner must remain v3.13")

# --- motivating live example: PCG Apprentice Business Analyst JR102087 at 29 days ---
require("PCG" in BLUEPRINT and "JR102087" in BLUEPRINT, "PCG JR102087 motivating example missing")
require("29 days" in BLUEPRINT, "PCG JR102087 29-day posting age missing")
require(
    "strong/good fit and was historically submitted" in BLUEPRINT.replace("\n", " "),
    "PCG JR102087 must be recorded as strong/good fit and historically submitted",
)
require(
    "would now suppress it under this `SUPPRESSED_WINDOW` hard" in BLUEPRINT,
    "PCG JR102087 must be recorded as a case a comparable future normal run would now suppress on recency",
)

# --- old EXCEPTION_ONLY-era unbounded rescue language must be fully retired ---
require(
    "outranks age-band assumptions" not in BLUEPRINT.replace("\n", " "),
    "BLUEPRINT must not claim first-party verified live/actionable evidence outranks age-band assumptions without bound",
)
require(
    "16-day-old or older" not in BLUEPRINT.replace("\n", " "),
    "BLUEPRINT must not retain the unbounded '16-day-old or older ... may still deserve pursuit' rescue language",
)
require(
    "outranks age-band assumptions" not in RULE.replace("\n", " "),
    "rule must not carry the unbounded 'outranks age-band assumptions' rescue language",
)
require(
    "16-day-old or older" not in RULE.replace("\n", " "),
    "rule must not carry the unbounded '16-day-old or older' rescue language",
)

# --- strength/verified-live influence is narrowly bounded to FAR_STRETCH_WINDOW (15-21 days) only ---
require(
    "may influence ranking/pursuit strength only within the `FAR_STRETCH_WINDOW`" in BLUEPRINT.replace("\n", " "),
    "BLUEPRINT must narrowly scope strength/verified-live influence to the 15-21 FAR_STRETCH_WINDOW only",
)
require(
    "never extends\nto or rescues `SUPPRESSED_WINDOW`" in BLUEPRINT
    or "never extends" in BLUEPRINT.replace("\n", " ") and "rescues `SUPPRESSED_WINDOW`" in BLUEPRINT.replace("\n", " "),
    "BLUEPRINT must explicitly state the FAR_STRETCH allowance never extends to or rescues SUPPRESSED_WINDOW",
)
require(
    "no degree of fit/value\nstrength, lifts the 22-day hard cutoff" in BLUEPRINT
    or "no degree of fit/value" in BLUEPRINT.replace("\n", " ") and "lifts the 22-day hard cutoff" in BLUEPRINT.replace("\n", " "),
    "BLUEPRINT must state no degree of fit/value strength lifts the 22-day hard cutoff",
)

# --- hard cutoff is pinned into §138.8 serious-role promotion wiring, not just §138.5 ---
require(
    "the §138.5 recency hard cutoff" in BLUEPRINT.replace("\n", " "),
    "BLUEPRINT §138.8 promotion wiring must explicitly require the §138.5 recency hard cutoff to PASS",
)
require(
    "never promoted on the strength of fit/value" in BLUEPRINT.replace("\n", " "),
    "BLUEPRINT §138.8 must state a SUPPRESSED_WINDOW role is never promoted on fit/value or verified-live evidence strength",
)
require(
    "the §138.5 recency hard cutoff" in RULE.replace("\n", " "),
    "rule §138.8 quick-reference must explicitly require the §138.5 recency hard cutoff to PASS",
)
require(
    "never promoted on\n  the strength of fit/value" in RULE
    or "never promoted on" in RULE.replace("\n", " ") and "the strength of fit/value" in RULE.replace("\n", " "),
    "rule must state a SUPPRESSED_WINDOW role is never promoted on fit/value or verified-live evidence strength",
)
require(
    "Promotion under the §138.5 recency\n  visibility gate additionally requires the §138.5 recency hard cutoff to"
    in RULE
    or "Promotion under the §138.5 recency" in RULE.replace("\n", " ")
    and "additionally requires the §138.5 recency hard cutoff to" in RULE.replace("\n", " "),
    "rule §138.8 quick-reference must pin the hard cutoff as part of the recency visibility gate, not an optional extra",
)

# --- contract sanity ---
require(CONTRACT["milestone_id"] == "DISCOVERY_RECENCY_HARD_CUTOFF_V1", "contract milestone_id drifted")
require(
    "0-7 days remains GOLD_WINDOW" in CONTRACT["acceptance_conditions"],
    "contract must preserve the GOLD_WINDOW band as an acceptance condition",
)
require(
    any("22 days or more is suppressed" in c for c in CONTRACT["acceptance_conditions"]),
    "contract must state the 22+ day suppression rule",
)
require(
    any("UNKNOWN" in c and "22+" in c for c in CONTRACT["acceptance_conditions"]),
    "contract must state UNKNOWN is never treated as 22+ merely because the date is missing",
)
require("src/" in CONTRACT["forbidden_paths"] and "schemas/" in CONTRACT["forbidden_paths"], "runtime/schema boundaries missing from contract")

print("PASS: discovery recency hard cutoff (22+ days suppressed, 21 days survives, UNKNOWN neutral, per-role override only) is locked")
