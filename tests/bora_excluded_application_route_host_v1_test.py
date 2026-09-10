from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
BLUEPRINT = (ROOT / "BLUEPRINT.md").read_text(encoding="utf-8")
RULE = (ROOT / ".cursor" / "rules" / "role-selection.mdc").read_text(encoding="utf-8")
CONTRACT = json.loads(
    (ROOT / "milestone_contracts" / "feature" / "bora-excluded-application-route-host-v1.json").read_text(
        encoding="utf-8"
    )
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


require("138.6.1 Bora-specific excluded application-route host" in BLUEPRINT, "Blueprint excluded-host section missing")
require(
    "`massanf.taleo.net` is recorded as a Bora-specific excluded\napplication-route host" in BLUEPRINT,
    "massanf.taleo.net exclusion statement missing",
)
require(
    "If a role's only current\napplication route depends on `massanf.taleo.net`, current first-party\nactionability fails, and this routes through the existing §135/§138.6\nactionability consequence" in BLUEPRINT,
    "suppression rule for massanf.taleo.net-only routes missing",
)
require(
    "This creates no new\ngate and does not amend §138.8; package generation for such a role\nremains blocked under the existing actionability/package gates" in BLUEPRINT,
    "corrected architecture wording (no new §138.8 gate) missing",
)
require(
    "This exclusion does\nnot blacklist MassDOT, MassCareers, Massachusetts government employers,\nor Taleo globally" in BLUEPRINT,
    "non-blacklist boundary missing",
)
require(
    "a different, verified working official ATS/application\nroute for the same or another Massachusetts-government role may still be\nevaluated normally" in BLUEPRINT,
    "alternate-route pass-through clause missing",
)
require(
    "not\na universal claim that Taleo or the employer is globally unavailable" in BLUEPRINT,
    "non-universal-claim clause missing",
)
require(
    "The\nexclusion remains active until Bora explicitly revokes it after a\nsuccessful direct usability re-test of `massanf.taleo.net`" in BLUEPRINT,
    "revocation condition missing",
)
require(
    "MassDOT — IT Data Analyst I, requisition\n260005JH, is the motivating cold-start failure" in BLUEPRINT,
    "MassDOT 260005JH motivating example missing",
)
require(
    "This subsection creates no new, competing actionability axis and changes\nno Qualification Truth, Employer Truth, Candidate Truth, Match Truth,\nauthorization, resume/package doctrine, schema, or runtime behavior" in BLUEPRINT,
    "scope-containment clause missing",
)
require(
    "actionability consequence: `WATCH`/no serious application effort, unless\nan independent blocker already produces `REJECT`" in BLUEPRINT,
    "Blueprint WATCH/no-serious-effort + independent REJECT consequence wording missing",
)

require(
    "Bora-specific excluded application-route host (§138.6.1)" in RULE,
    "role-selection.mdc quick-reference pointer to §138.6.1 missing",
)
require("`massanf.taleo.net` is excluded" in RULE, "quick-reference exclusion statement missing")
require(
    "does not blacklist MassDOT,\n  MassCareers, Massachusetts government employers, or Taleo globally" in RULE,
    "quick-reference non-blacklist boundary missing",
)
require(
    "a\n  different verified working official application route may still pass" in RULE,
    "quick-reference alternate-route pass-through missing",
)
require(
    "Remains active until Bora explicitly revokes it after a successful\n  direct usability re-test" in RULE,
    "quick-reference revocation condition missing",
)
require("260005JH" in RULE, "quick-reference MassDOT requisition pointer missing")
require("alwaysApply: true" in RULE, "role-selection rule must remain always-on")
require(
    "actionability consequence: `WATCH`/no serious application effort,\n  unless an independent blocker already produces `REJECT`" in RULE,
    "role-selection.mdc WATCH/no-serious-effort + independent REJECT consequence wording missing",
)
require(
    "This creates\n  no new gate and does not amend §138.8" in RULE,
    "role-selection.mdc must explicitly deny creating a new §138.8 gate",
)

# Guard against regressions where this host rule is mis-described as a new
# serious-discovery promotion/suppression gate rather than routing through
# the existing §135/§138.6 actionability consequence.
_FORBIDDEN_RULE_PHRASES = (
    "suppressed before Bora-facing serious discovery",
    "suppressed before serious Bora-facing discovery",
    "new serious-discovery",
    "new promotion gate",
    "new suppression gate",
)
for _phrase in _FORBIDDEN_RULE_PHRASES:
    require(
        _phrase not in RULE,
        f"role-selection.mdc must not describe this host rule as a new serious-discovery promotion/suppression gate (found: {_phrase!r})",
    )
for _phrase in _FORBIDDEN_RULE_PHRASES:
    require(
        _phrase not in BLUEPRINT,
        f"BLUEPRINT.md §138.6.1 must not describe this host rule as a new serious-discovery promotion/suppression gate (found: {_phrase!r})",
    )

require(
    CONTRACT["baseline_sha"] == "582ee79370ed075a3e7caa063025a6a4e6097fa8",
    "contract baseline drifted",
)
require(
    "src/" in CONTRACT["forbidden_paths"] and "schemas/" in CONTRACT["forbidden_paths"],
    "runtime/schema boundaries missing from contract",
)
require(
    "massanf.taleo.net is explicitly recorded as a Bora-specific excluded application-route host based on direct user usability evidence"
    in CONTRACT["acceptance_conditions"],
    "contract acceptance condition for host exclusion missing",
)
require(
    "MassDOT, MassCareers, and Massachusetts government employers are not globally blacklisted; a different verified working official ATS/application route may still be evaluated normally"
    in CONTRACT["acceptance_conditions"],
    "contract acceptance condition for non-blacklist boundary missing",
)

require("**Final Locked Blueprint v3.13**" in BLUEPRINT, "pinned Blueprint banner drifted")

print(
    "PASS: massanf.taleo.net excluded application-route host locked, "
    "MassDOT/MassCareers/Taleo non-blacklist boundaries preserved, "
    "260005JH recorded as motivating cold-start failure"
)
