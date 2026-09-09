from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
BLUEPRINT = (ROOT / "BLUEPRINT.md").read_text(encoding="utf-8")
RULE = (ROOT / ".cursor" / "rules" / "role-selection.mdc").read_text(encoding="utf-8")


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        print(f"FAIL: {message}")
        raise SystemExit(1)


for token in (
    "0-7 days = GOLD_WINDOW",
    "8-14 days = STRETCH_WINDOW",
    "15-21 days = FAR_STRETCH_WINDOW",
    "22+ days = EXCEPTION_ONLY_WINDOW",
    "UNKNOWN_WINDOW",
    "REMOTE",
    "CONTRACT/CONTRACT-TO-HIRE/TEMPORARY",
    "PART_TIME",
    "discovery/pursuit preferences, not hard filters",
):
    assert_true(token in BLUEPRINT, f"BLUEPRINT missing locked token: {token}")

for token in (
    "`GOLD_WINDOW` = 0-7 days",
    "`STRETCH_WINDOW` = 8-14 days",
    "`FAR_STRETCH_WINDOW` = 15-21 days",
    "`EXCEPTION_ONLY_WINDOW` = 22+ days",
    "Locked work-format preferences",
    "remote + contract",
    "remote + part-time",
):
    assert_true(token in RULE, f"role-selection rule missing locked token: {token}")

assert_true("alwaysApply: true" in RULE, "cross-chat role-selection pointer must remain always-on")
assert_true("unusually strong, strategically exceptional, first-party verified-live role" in RULE, "EXCEPTION_ONLY quick-ref must preserve the older-role escape hatch")
assert_true("never substitute `discovered_date` or" in RULE and "`date_first_seen`" in RULE, "quick-ref must preserve posting-date UNKNOWN/no-substitution rule")
assert_true("not hard" in RULE and "fixed Lane A/B/C hierarchy" in RULE, "quick-ref work-format preferences must remain non-hard and non-hierarchical")
assert_true("Boston/" in RULE and "Greater Boston contract, temporary, and part-time" in RULE, "quick-ref must preserve Boston non-remote preferred work formats")
assert_true("0-2 days = VERY_FRESH" in BLUEPRINT and "3-7 days = FRESH" in BLUEPRINT and "8-14 days = AGING" in BLUEPRINT and "15+ days = STALE_LEANING" in BLUEPRINT, "existing Freshness day-band vocabulary must remain unchanged")
assert_true("presentation/governance vocabulary only" in BLUEPRINT and "not a schema enum" in BLUEPRINT, "window overlay must remain presentation/governance only")
assert_true("not ranked above one another as a universal rule" in BLUEPRINT, "primary lanes must not become a universal hierarchy")
assert_true("§138.11" in BLUEPRINT and "fixed Lane A > Lane B > Lane C hierarchy" in BLUEPRINT, "work-format preference must reconcile with employment-type principle")
assert_true("**Discovery Window**" in BLUEPRINT and "`FAR_STRETCH_WINDOW`" in BLUEPRINT and "`EXCEPTION_ONLY_WINDOW`" in BLUEPRINT, "serious-role output must surface the new window overlay alongside Freshness")
assert_true("Freshness, Discovery Window" in RULE, "always-on quick-reference must surface Discovery Window in serious-role output")
assert_true("no universal magical employer cutoff" in BLUEPRINT, "age windows must not be misrepresented as employer hiring cutoffs")
assert_true("never override fit" in RULE and "authorization, first-party actionability" in RULE, "rule must preserve truth/actionability boundary")
assert_true("must never rescue a weak match" in BLUEPRINT, "BLUEPRINT must preserve qualification boundary")
assert_true("unusually strong accessible full-time/hybrid/onsite opportunity" in BLUEPRINT, "work-format preferences must not suppress an unusually strong accessible role")
assert_true("discovered_date" in BLUEPRINT and "date_first_seen" in BLUEPRINT, "posting-date UNKNOWN guard must forbid discovery-date substitution")
assert_true("unavailable or unreliable, preserve" in BLUEPRINT and "date_first_seen" in BLUEPRINT, "unreliable employer posting date must remain UNKNOWN")
assert_true("**Final Locked Blueprint v3.13**" in BLUEPRINT, "pinned Blueprint banner must remain v3.13")

print("PASS: discovery recency + work-format priority doctrine is locked and truth boundaries are preserved")
sys.stdout.flush()
