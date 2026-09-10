from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
BLUEPRINT = (ROOT / "BLUEPRINT.md").read_text(encoding="utf-8")
RULE = (ROOT / ".cursor" / "rules" / "role-selection.mdc").read_text(encoding="utf-8")
AGENTS = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
CONTRACT = json.loads(
    (ROOT / "milestone_contracts" / "feature" / "employer-exclusion-source-ladder-v1.json").read_text(
        encoding="utf-8"
    )
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def extract(text: str, start_marker: str, end_marker: str) -> str:
    start = text.index(start_marker)
    end = text.index(end_marker, start)
    return text[start:end]


def normalize(text: str) -> str:
    return " ".join(text.split())


# Scoped blocks used to check forbidden phrases only where they matter,
# rather than across the whole file (which would either miss a real
# regression hidden by re-wrapping, or falsely flag legitimate §138.6.1
# Taleo wording that is allowed to say a route-host exclusion creates no
# new gate).
BLUEPRINT_MGB_BLOCK = normalize(
    extract(
        BLUEPRINT,
        "**138.6.2 Bora-specific excluded employer family",
        "**138.7 Remote authenticity",
    )
)
BLUEPRINT_TALEO_BLOCK = normalize(
    extract(
        BLUEPRINT,
        "**138.6.1 Bora-specific excluded application-route host",
        "**138.6.2 Bora-specific excluded employer family",
    )
)
RULE_MGB_BLOCK = normalize(
    extract(
        RULE,
        "* Bora-specific excluded employer family (§138.6.2,",
        "* Discovery-source ladder (§18.1,",
    )
)
RULE_TALEO_BLOCK = normalize(
    extract(
        RULE,
        "* Bora-specific excluded application-route host (§138.6.1):",
        "* Bora-specific excluded employer family (§138.6.2,",
    )
)


# --- §138.6.2 Bora-specific excluded employer family (MGB) ---

require(
    "138.6.2 Bora-specific excluded employer family" in BLUEPRINT,
    "Blueprint MGB exclusion section missing",
)
require(
    "the Mass General Brigham system is recorded as a\nBora-specific excluded employer family" in BLUEPRINT,
    "MGB family exclusion statement missing",
)
require(
    "including Mass General\nBrigham, Massachusetts General Hospital / The General Hospital Corporation,\nBrigham and Women's Hospital, and other MGB-system entities/affiliates/\naliases the first-party source itself identifies as part of that system"
    in BLUEPRINT,
    "MGB alias/system-family coverage clause missing",
)
require(
    "the role does not enter serious Bora-facing discovery or package generation."
    in BLUEPRINT,
    "MGB serious-discovery/package suppression statement missing",
)
require(
    "not a claim that Mass General\nBrigham is a bad employer" in BLUEPRINT,
    "MGB not-a-bad-employer clause missing",
)
require(
    "This does not create an unsupported global\nMGB-affiliate list: only entities a first-party source itself identifies as\npart of the Mass General Brigham system are covered, never a name-similarity\nguess."
    in BLUEPRINT,
    "MGB no-unsupported-global-affiliate-list clause missing",
)
require(
    "The exclusion remains active for the whole employer family until\nBora explicitly overrides it for one specific role or explicitly revokes the\nfamily exclusion; an explicit per-role override does not revoke the family\nexclusion for any other MGB-system role."
    in BLUEPRINT,
    "MGB override/revocation clause missing",
)
require(
    "Historical Submitted Application\nTruth, Employer Truth, Candidate Truth, Match Truth, and Qualification\nTruth for any already-submitted Mass General Brigham system application are\nnot rewritten by this exclusion."
    in BLUEPRINT,
    "MGB historical-truth non-rewrite clause missing",
)
require(
    "This subsection creates no new, competing actionability axis and changes no\nQualification Truth, Employer Truth, Candidate Truth, Match Truth,\nauthorization, resume/package doctrine, schema, or runtime behavior"
    in BLUEPRINT,
    "MGB scope-containment clause missing",
)

# --- Correction: §138.6.2 must honestly integrate into §138.8, not falsely
# claim "no new gate" / equivalence to §138.5/§138.14. Scoped to the
# §138.6.2 block specifically (see BLUEPRINT_MGB_BLOCK above) so this
# cannot collide with the legitimate, differently-scoped §138.6.1 Taleo
# wording that says the same thing about a genuinely different, unchanged
# gate. ---

require(
    "This creates no new gate and does not amend" not in BLUEPRINT_MGB_BLOCK,
    "BLUEPRINT.md §138.6.2 must not repeat the false 'creates no new gate' claim for the MGB exclusion",
)
require(
    "the same way §138.5/§138.14 already suppress roles, without redefining those gates"
    not in BLUEPRINT_MGB_BLOCK,
    "BLUEPRINT.md §138.6.2 must not repeat the false §138.5/§138.14 equivalence claim for the MGB exclusion",
)
require(
    "This is integrated into §138.8 serious-role\npromotion as a distinct third check" in BLUEPRINT,
    "MGB §138.8 integration clause missing from §138.6.2",
)
require(
    "AND this §138.6.2 employer-family-exclusion\ncheck PASS" in BLUEPRINT,
    "MGB three-check PASS requirement missing from §138.6.2",
)
require(
    "This check is strictly a Pursuit Truth criterion" in BLUEPRINT,
    "MGB Pursuit-Truth-only clause missing from §138.6.2",
)
require(
    "its exclusion reason is labeled `BORA_EXCLUDED_EMPLOYER`\nand must never be presented as, or trigger, a Qualification Truth REJECT"
    in BLUEPRINT,
    "MGB BORA_EXCLUDED_EMPLOYER audit-label clause missing from §138.6.2",
)
require(
    "any independent REJECT verdict caused by a separate blocker"
    in BLUEPRINT,
    "MGB independent-REJECT preservation clause missing from §138.6.2",
)

# --- §138.8 integration ---

require(
    "Promotion into this serious-role output additionally requires the §138.6.2\nBora-specific employer-family-exclusion check to PASS"
    in BLUEPRINT,
    "§138.8 must require the §138.6.2 employer-family-exclusion check to pass",
)
require(
    "skipped once the §138.5 and §138.14 gates both pass" in BLUEPRINT,
    "§138.8 must state the employer-family-exclusion check cannot be skipped after recency+start pass",
)
require(
    "Only roles that pass the §138.5\nBora-facing recency visibility gate AND the §138.14 start horizon gate may\nbe promoted into this serious-role output; a role suppressed under either\ngate does not enter serious-role output or package generation regardless of\nits status under the other gate"
    in BLUEPRINT,
    "§138.8's original recency/start-horizon locked sentence must be preserved verbatim (shared with discovery_start_horizon_gate_v1_test.py)",
)
require(
    "BORA_EXCLUDED_EMPLOYER`\nand is never presented as a Qualification Truth REJECT" in BLUEPRINT,
    "§138.8 must restate the BORA_EXCLUDED_EMPLOYER audit-label / non-REJECT clause",
)

# --- §18.1 discovery-source ladder ---

require(
    "18.1 Discovery-source ladder — DISCOVERY_SOURCE_LADDER_V1" in BLUEPRINT,
    "Blueprint discovery-source ladder section missing or still carries the coupled exclusion identifier",
)
require(
    "EMPLOYER_EXCLUSION_DISCOVERY_SOURCE_LADDER_V1" not in BLUEPRINT,
    "BLUEPRINT.md §18.1 must not reuse the milestone-wide identifier as its own subsection ID (misleading cross-ID coupling)",
)
require(
    "a distinct identifier naming the source-\nladder ordering only, with no cross-ID coupling to the exclusion\nidentifier)" in AGENTS,
    "AGENTS.md must state §18.1's identifier is distinct from the employer-exclusion identifier",
)
require(
    "LinkedIn\nFree and Brandeis Handshake are preferred first-wave discovery surfaces,\nalongside targeted direct employer/official ATS searches"
    in BLUEPRINT,
    "preferred first-wave discovery surfaces clause missing",
)
require(
    "Simplify Free,\nBuilt In, HigherEdJobs, Idealist, staffing/recruiting firms, company lists,\nreferrals, recruiter outreach, and other credible job sources remain valid\nsecondary/specialized discovery channels"
    in BLUEPRINT,
    "explicit secondary/specialized discovery-channel classification missing",
)
require(
    "Generic aggregators and generic search/index\nsnippet results remain the lowest-confidence tier: lead generation only."
    in BLUEPRINT,
    "generic aggregator lowest-confidence clause missing",
)
require(
    "Discovery source and verification/application source remain separate fields\n(§18)" in BLUEPRINT,
    "discovery/verification source separation clause missing",
)
require(
    "by itself never establishes Employer Truth, an authoritative\nposting-date/intake-recency anchor, current first-party application\nactionability, or package-time semantic quorum"
    in BLUEPRINT,
    "LinkedIn/Handshake non-compensation clause missing",
)
require(
    "LinkedIn/Handshake posting\nage alone cannot satisfy the §138.5 recency-anchor requirement." in BLUEPRINT,
    "LinkedIn/Handshake recency-anchor non-satisfaction clause missing",
)
require(
    "Serious-role\npromotion still requires the existing §138.5 Bora-facing recency visibility\ngate, the §138.14 start horizon gate, the §138.6.2 employer-family-exclusion\ncheck PASS, §135/§138.6 first-party actionability, and the package-time\nfirst-party recheck"
    in BLUEPRINT,
    "serious-role promotion gate-stack cross-reference missing §138.6.2",
)

# --- role-selection.mdc quick reference ---

require(
    "Bora-specific excluded employer family (§138.6.2," in RULE,
    "role-selection.mdc quick-reference pointer to §138.6.2 missing",
)
require(
    "Mass General Brigham system roles --" in RULE,
    "quick-reference MGB roles statement missing",
)
require(
    "Pursuit/preference exclusion only, not a claim that Mass\n  General Brigham is a bad employer" in RULE,
    "quick-reference MGB preference-only clause missing",
)
require(
    "No unsupported global MGB-affiliate list" in RULE,
    "quick-reference MGB no-unsupported-affiliate-list clause missing",
)
require(
    "Remains active for the\n  whole employer family until Bora explicitly overrides one specific role\n  or explicitly revokes the family exclusion"
    in RULE,
    "quick-reference MGB override/revocation clause missing",
)
require(
    "a per-role override does not\n  revoke the family exclusion for any other MGB-system role -- it applies\n  only to that one specific role."
    in RULE,
    "quick-reference MGB per-role-override non-cascade clause missing",
)
require(
    "Historical Submitted Application Truth\n  for any already-submitted Mass General Brigham system application is not\n  rewritten."
    in RULE,
    "quick-reference MGB historical-truth non-rewrite clause missing",
)
require(
    "Integrated into\n  §138.8\n  serious-role promotion as a required third check" in RULE
    or "Integrated into §138.8\n  serious-role promotion as a required third check" in RULE,
    "quick-reference §138.8 integration clause missing",
)
require(
    "requires all three to PASS, and this employer-family-exclusion check\n  cannot be skipped once recency and start-horizon pass" in RULE,
    "quick-reference cannot-be-skipped clause missing",
)
require(
    "`BORA_EXCLUDED_EMPLOYER`, never presented as a Qualification Truth\n  REJECT" in RULE,
    "quick-reference BORA_EXCLUDED_EMPLOYER audit-label clause missing",
)
require(
    "Discovery-source ladder (§18.1, `DISCOVERY_SOURCE_LADDER_V1` -- source-\n  ladder ordering only, a distinct identifier from\n  `BORA_EXCLUDED_EMPLOYER_FAMILY_V1` above, with no cross-ID coupling)" in RULE,
    "role-selection.mdc quick-reference pointer to §18.1 with distinct identifier missing",
)
require(
    "Simplify Free, Built In,\n  HigherEdJobs, Idealist, staffing/recruiting firms, company lists,\n  referrals, recruiter outreach, and other credible job sources remain\n  valid secondary/specialized discovery channels"
    in RULE,
    "quick-reference secondary/specialized discovery-channel classification missing",
)
require(
    "cannot satisfy the §138.5 recency-anchor requirement. Serious-role" in RULE,
    "quick-reference discovery-source non-compensation clause missing",
)

# --- §18.1 quick-reference bullet's own gate-stack sentence must name
# §138.6.2 explicitly, not just recency+start-horizon+actionability+recheck
# (the §138.6.2 bullet mentioning §138.8 integration is not enough on its
# own -- the §18.1 bullet a reader lands on first must be unmistakable too,
# mirroring the §138.8-block check above). ---

RULE_18_1_BLOCK = extract(
    RULE,
    "* Discovery-source ladder (§18.1,",
    "* Start horizon gate (§138.14):",
)
require(
    "the §138.6.2 employer-family-exclusion check\n  PASS" in RULE_18_1_BLOCK,
    "role-selection.mdc §18.1 quick-reference gate-stack sentence must name the §138.6.2 employer-family-exclusion check",
)

# --- §138.8 quick-reference bullet itself must state the three-check
# requirement, not just the old two-check recency+start formula (the
# §138.6.2 bullet mentioning integration is not enough on its own -- the
# §138.8 bullet a reader lands on first must be unmistakable too). ---

RULE_138_8_BLOCK = extract(
    RULE,
    "* Serious-role output standard (§138.8):",
    "**Disambiguation (§138.8):**",
)
require(
    "requires passing BOTH the §138.5 recency visibility gate AND the §138.14\n  start horizon gate; failing either one suppresses the role regardless of\n  the other"
    in RULE_138_8_BLOCK,
    "role-selection.mdc §138.8 bullet must preserve the original recency+start-horizon sentence verbatim (shared with discovery_start_horizon_gate_v1_test.py)",
)
require(
    "Promotion additionally requires the §138.6.2 Bora-specific\n  employer-family-exclusion check to PASS as a required third check"
    in RULE_138_8_BLOCK,
    "role-selection.mdc §138.8 bullet must explicitly require the §138.6.2 employer-family-exclusion check as a third check",
)
require(
    "this is a three-check requirement, not a two-check one" in normalize(RULE_138_8_BLOCK),
    "role-selection.mdc §138.8 bullet must state the three-check (not two-check) framing explicitly",
)
require(
    "the employer-family-exclusion check cannot be skipped\n  once the §138.5 and §138.14 gates both pass" in RULE_138_8_BLOCK,
    "role-selection.mdc §138.8 bullet must state the third check cannot be skipped after recency+start pass",
)
require(
    "labeled `BORA_EXCLUDED_EMPLOYER`, never presented as a Qualification\n  Truth REJECT" in RULE_138_8_BLOCK,
    "role-selection.mdc §138.8 bullet must restate the BORA_EXCLUDED_EMPLOYER audit-label clause",
)

require("alwaysApply: true" in RULE, "role-selection rule must remain always-on")

# Guard against regressions where the MGB employer-family exclusion is
# mis-described as an unsupported global blacklist, or falsely claimed
# equivalent to §138.5/§138.14 ("creates no new gate"), rather than the
# honest §138.8-integrated required third check it actually is. This check
# is scoped to the §138.6.2 MGB block specifically (normalized to collapse
# line-wrap so re-wrapping can't hide a regression) -- it must NOT be
# applied file-wide, because the legitimate §138.6.1 Taleo route-host
# exclusion is correctly described as creating no new gate (it routes
# through the existing §135/§138.6 actionability consequence, not a new
# §138.8 check) and existing regression tests require that wording.
require(
    "creates no new gate" not in BLUEPRINT_MGB_BLOCK,
    "BLUEPRINT.md §138.6.2 must not repeat the false 'creates no new gate' claim for the MGB exclusion",
)
require(
    "MGB-affiliate blacklist" not in BLUEPRINT_MGB_BLOCK,
    "BLUEPRINT.md §138.6.2 must not describe the MGB exclusion as a blacklist",
)
require(
    "creates no new gate" not in RULE_MGB_BLOCK,
    "role-selection.mdc §138.6.2 bullet must not repeat the false 'creates no new gate' claim for the MGB exclusion",
)
require(
    "MGB-affiliate blacklist" not in RULE_MGB_BLOCK,
    "role-selection.mdc §138.6.2 bullet must not describe the MGB exclusion as a blacklist",
)
require(
    "MGB-affiliate blacklist" not in AGENTS,
    "AGENTS.md must not describe the MGB exclusion as a blacklist",
)

# The legitimate §138.6.1 Taleo wording is untouched by the above and is
# still required to say it creates no new gate (existing, unmodified
# doctrine -- routes through §135/§138.6, not a new §138.8 check).
require(
    "creates no new gate" in RULE_TALEO_BLOCK,
    "role-selection.mdc §138.6.1 Taleo wording must still say the route-host exclusion creates no new gate",
)
require(
    "creates no new gate" in BLUEPRINT_TALEO_BLOCK,
    "BLUEPRINT.md §138.6.1 Taleo wording must still say the route-host exclusion creates no new gate",
)

# --- AGENTS.md operational pointer ---

require(
    "BORA_EXCLUDED_EMPLOYER_FAMILY_V1" in AGENTS,
    "AGENTS.md pointer to BORA_EXCLUDED_EMPLOYER_FAMILY_V1 missing",
)
require(
    "DISCOVERY_SOURCE_LADDER_V1" in AGENTS,
    "AGENTS.md pointer to DISCOVERY_SOURCE_LADDER_V1 missing",
)
require(
    "not a claim that Mass General Brigham is a bad employer" in AGENTS,
    "AGENTS.md not-a-bad-employer clause missing",
)
require(
    "This exclusion is integrated into §138.8 serious-role\npromotion as a required third check" in AGENTS,
    "AGENTS.md §138.8 integration clause missing",
)
require(
    "the employer-family-exclusion check cannot be skipped\nonce recency and start-horizon pass" in AGENTS,
    "AGENTS.md cannot-be-skipped clause missing",
)
require(
    "its reason is labeled `BORA_EXCLUDED_EMPLOYER`\nand must never be presented as a Qualification Truth REJECT" in AGENTS,
    "AGENTS.md BORA_EXCLUDED_EMPLOYER audit-label clause missing",
)
require(
    "a per-role override does not\nrevoke the family exclusion for any other MGB-system role" in AGENTS,
    "AGENTS.md per-role-override non-cascade clause missing",
)
require(
    "Simplify Free, Built In, HigherEdJobs, Idealist, staffing/\nrecruiting firms, company lists, referrals, recruiter outreach, and other\ncredible job sources remain valid secondary/specialized discovery"
    in AGENTS,
    "AGENTS.md secondary/specialized discovery-channel classification missing",
)
require(
    "serious-role promotion still requires the\nexisting §138.5/§138.14/§135/§138.6 gates, the §138.6.2\nemployer-family-exclusion check PASS, and the package-time first-party\nrecheck above."
    in AGENTS,
    "AGENTS.md discovery-ladder gate-stack cross-reference missing §138.6.2",
)

# --- historical truth / verification hierarchy assertions shared across files ---

require(
    "Historical Submitted Application Truth for\nany already-submitted Mass General Brigham system application is not\nrewritten."
    in AGENTS,
    "AGENTS.md historical-truth non-rewrite clause missing",
)

# --- milestone contract sanity ---

require(
    CONTRACT["baseline_sha"] == "cfeaf0b2ebfdb29c52c0bd1891dd88d8ae412579",
    "contract baseline drifted",
)
require(
    "src/" in CONTRACT["forbidden_paths"] and "schemas/" in CONTRACT["forbidden_paths"],
    "runtime/schema boundaries missing from contract",
)
require(
    "Mass General Brigham system roles are Bora-specific employer-family exclusions and do not enter serious Bora-facing discovery or package generation unless Bora explicitly overrides or revokes the exclusion"
    in CONTRACT["acceptance_conditions"],
    "contract acceptance condition for MGB exclusion missing",
)
require(
    "LinkedIn or Handshake posting age alone cannot satisfy the authoritative recency-anchor requirement"
    in CONTRACT["acceptance_conditions"],
    "contract acceptance condition for recency-anchor non-compensation missing",
)
require(
    "serious-role promotion still requires the existing authoritative recency gate, start-horizon gate, the §138.6.2 employer-family-exclusion check PASS, exact first-party semantic actionability quorum, and package-time recheck"
    in CONTRACT["acceptance_conditions"],
    "contract acceptance condition gate-stack must name the §138.6.2 employer-family-exclusion check",
)

require("**Final Locked Blueprint v3.13**" in BLUEPRINT, "pinned Blueprint banner drifted")

print(
    "PASS: Mass General Brigham system employer-family exclusion locked "
    "(§138.6.2, integrated into §138.8 as a required third check), "
    "LinkedIn Free / Brandeis Handshake discovery-source ladder sharpened "
    "(§18.1, distinct identifier), verification hierarchy non-compensation "
    "and BORA_EXCLUDED_EMPLOYER audit-label semantics preserved"
)
