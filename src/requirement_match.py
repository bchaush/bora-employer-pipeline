"""Deterministic requirement → Evidence/Claim matching for Job Analysis v1.

Uses approved reusable claims and trusted Evidence records only.
Applies bounded semantic-boundary traps and conservative capability gating.

Generic lexical overlap alone cannot produce STRONG / SUPPORTED / PARTIAL.
JD anchors map only to existing canonical capabilities (no dynamic ontology).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Mapping, Sequence

from claim_validation import validate_claim
from schema_validation import build_draft202012_validator


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_MATCH_SCHEMA_PATH = ROOT / "schemas" / "evidence_match.schema.json"

MATCH_RESULTS = frozenset({"STRONG", "SUPPORTED", "PARTIAL", "NONE", "UNKNOWN"})

# Known Winter Walk claim capability tags (derived from approved claim wording
# + cited Evidence capabilities). Not a general ontology.
_CLAIM_CAPABILITIES: dict[str, frozenset[str]] = {
    "CLAIM_WW_001": frozenset({"requirements_elicitation", "scope_boundary"}),
    "CLAIM_WW_002": frozenset(
        {"fail_closed_controls", "send_controls", "approval_gating"}
    ),
    "CLAIM_WW_003": frozenset({"data_ingestion", "csv_intake", "import_logging"}),
    "CLAIM_WW_004": frozenset(
        {
            "form_to_evidence_mapping",
            "approval_sync",
            "audit_logging",
            "workflow_automation",
        }
    ),
    "CLAIM_WW_005": frozenset({"uat", "pilot_testing", "test_documentation"}),
    "CLAIM_WW_006": frozenset({"process_mapping"}),
    "CLAIM_EDU_UNWE_001": frozenset({"bachelors_degree_credential"}),
    "CLAIM_DCOMMERCE_001": frozenset({"excel_proficiency"}),
    "CLAIM_BULMARMA_001": frozenset({"excel_proficiency"}),
}

# Bounded JD-anchor → existing canonical capability mappings only.
_REQ_CAPABILITY_PATTERNS: tuple[tuple[re.Pattern[str], frozenset[str]], ...] = (
    (
        re.compile(
            r"requirements?\s+(?:gather(?:ing)?|elicitation|definition|collection)|"
            r"(?:gather|collect|clarify|document|elicit|translate|capture|turn|"
            r"convert)(?:ing)?\s+(?:\w+\s+){0,3}(?:requirements?|needs?)\b|"
            r"(?:turn|translate|capture|convert)(?:ing)?\s+"
            r"(?:\w+\s+){0,2}(?:user|stakeholder|business)\s+needs?\s+"
            r"(?:into\s+)?(?:functional\s+)?requirements?\b|"
            r"(?:stakeholder|business)\s+requirements?\b|"
            r"(?:stakeholder|business)\s+needs?\s+into\s+documented\s+requirements?\b|"
            r"clarify(?:ing)?\s+(?:\w+\s+){0,4}(?:requirements?|needs?|scope|changes?)\b|"
            r"scope\s+boundar|clarify(?:ing)?\s+scope",
            re.I,
        ),
        frozenset({"requirements_elicitation", "scope_boundary"}),
    ),
    (
        re.compile(
            r"form[- ]to[- ]evidence|evidence[_ ]log|approval[- ]?sync|"
            r"approval[- ]synchron|adoption[_ ]matrix|self[- ]report\s+form",
            re.I,
        ),
        frozenset({"form_to_evidence_mapping", "approval_sync"}),
    ),
    (
        re.compile(
            r"fail[- ]closed|kill\s+switch|live\s+(email\s+)?send|"
            r"follow[- ]up\s+send\s+control|controlled\s+(?:outbound\s+)?send",
            re.I,
        ),
        frozenset({"fail_closed_controls", "send_controls", "approval_gating"}),
    ),
    (
        re.compile(
            r"\bcsv\b|drive[- ]folder|"
            r"data\s+ingestion|data\s+import|import(?:ing)?\s+data|"
            r"ingest(?:ing)?\s+data|data\s+feeds?|spreadsheet\s+data\s+feeds?|"
            r"spreadsheet\s+feeds?|file\s+import|csv\s+import|import\s+log|"
            r"data\s+(?:intake|validation)\b|"
            r"(?:ingest|load|import)(?:ing)?\s+"
            r"(?:\w+\s+){0,4}"
            r"(?:structured\s+|tabular\s+|source\s+|operational\s+|incoming\s+|recurring\s+)?"
            r"(?:data|files?|datasets?|feeds?|csv|spreadsheets?)\b|"
            r"consolidat(?:e|ing)\s+(?:\w+\s+){0,3}"
            r"(?:incoming\s+)?(?:data|files?|datasets?|feeds?)\b|"
            r"incoming\s+datasets?\b",
            re.I,
        ),
        frozenset({"data_ingestion", "csv_intake", "import_logging"}),
    ),
    (
        re.compile(
            r"\buat\b|user\s+acceptance\s+test(?:ing)?|acceptance\s+testing|"
            r"acceptance[- ]test(?:ing|s| cycles)?|"
            r"pilot\s+test(?:ing)?|pilot\s+validation|pilot\s+result|"
            r"validat(?:e|ing)\s+(?:a\s+)?pilot\b|"
            r"user\s+testing|test\s+documentation",
            re.I,
        ),
        frozenset({"uat", "pilot_testing", "test_documentation"}),
    ),
    # R-7: bare "workflow automation" is insufficient; require operational context.
    (
        re.compile(
            r"(?:"
            r"(?:workflow|process)\s+automation|"
            r"automated\s+(?:workflow|process)"
            r").{0,80}(?:"
            r"evidence|approval|fail[- ]closed|controlled|operational|"
            r"self[- ]report|reconcil|validated\s+data|import\s+log|"
            r"data\s+(?:intake|ingestion|validation)"
            r")"
            r"|"
            r"(?:"
            r"evidence|approval|fail[- ]closed|controlled|operational|"
            r"self[- ]report|reconcil|validated\s+data"
            r").{0,80}(?:"
            r"(?:workflow|process)\s+automation|automated\s+(?:workflow|process)"
            r")",
            re.I,
        ),
        frozenset({"workflow_automation"}),
    ),
    # Process / workflow mapping — bounded; domain text like "Business Process"
    # alone cannot false-fire without mapping/documentation verbs.
    (
        re.compile(
            r"\bprocess\s+map(?:ping)?\b|\bworkflow\s+map(?:ping)?\b|"
            r"\bbusiness[- ]process\s+map(?:ping)?\b|"
            r"\bmap(?:ping)?\s+existing\s+business\s+processes?\b|"
            r"\bmap(?:ping)?\s+current[- ]state\s+workflows?\b|"
            r"\bmap(?:ping)?\s+operational\s+handoffs?\b|"
            r"\bmap(?:ping)?\s+(?:as[- ]is|to[- ]be)\s+processes?\b|"
            r"\bmap(?:ping)?\s+workflows?\b|"
            r"\bcreate(?:ing)?\s+workflow\s+maps?\b|"
            r"\bidentify(?:ing)?\s+process\s+steps?\s+and\s+bottlenecks?\b|"
            r"\bdocument(?:ing)?\s+business\s+processes?\b|"
            r"\bdocument(?:ing)?\s+(?:as[- ]is\s+|to[- ]be\s+|"
            r"current[- ]state\s+and\s+future[- ]state\s+)?"
            r"(?:workflows?|business\s+processes?)\b",
            re.I,
        ),
        frozenset({"process_mapping"}),
    ),
    (
        re.compile(
            r"\bbpmn(?:\s*2(?:\.0)?)?\b|\bbusiness\s+process\s+model(?:ing)?\s+notation\b|"
            r"formal\s+enterprise\s+process\s+model(?:ing)?\b|"
            r"enterprise\s+process\s+architect(?:ure)?\b|"
            r"business[- ]process\s+modeling\s+certification|"
            r"process\s+reengineering\s+leadership|"
            r"enterprise\s+process\s+reengineering",
            re.I,
        ),
        frozenset({"bpmn_modeling"}),
    ),
    (
        re.compile(
            r"\bsix\s+sigma\b|\blean\b|\bvalue\s+stream\s+mapping\b|"
            r"\blean\s+(?:six\s+sigma|process\s+engineering)\b|"
            r"lean\s+certification\b",
            re.I,
        ),
        frozenset({"lean_six_sigma"}),
    ),
    (
        re.compile(
            r"\bcelonis\b|\bui\s*path\s+process\s+mining\b|"
            r"process[- ]min(?:ing|e)(?:\s+telemetry)?\b|"
            r"automated\s+process\s+min(?:ing|e)\b",
            re.I,
        ),
        frozenset({"process_mining_telemetry"}),
    ),
    (
        re.compile(
            r"\bu\.?s\.?\s+regulator|us\s+regulator|sec\s+reporting|\bsox\b|"
            r"regulatory\s+reporting|fincen",
            re.I,
        ),
        frozenset({"us_regulatory_reporting"}),
    ),
    (
        re.compile(r"\bsalesforce\b|\bsfdc\b", re.I),
        frozenset({"salesforce_administration"}),
    ),
    (
        re.compile(r"\bworkday\b|\bservicenow\b|\bsnow\b|\bsap\b", re.I),
        frozenset({"enterprise_platform_specialization"}),
    ),
    (
        re.compile(r"\bgoogle\s+cloud\b|\bgcp\b|cloud\s+engineer", re.I),
        frozenset({"google_cloud_engineering"}),
    ),
    (
        re.compile(
            r"production\s+ml|machine\s+learning|ml\s+engineer|deep\s+learning|"
            r"\bmlops\b|model\s+deploy",
            re.I,
        ),
        frozenset({"production_ml"}),
    ),
    (
        re.compile(
            r"enterprise\s+qa|qa\s+ownership|qa\s+engineer|"
            r"quality\s+assurance\s+engineer",
            re.I,
        ),
        frozenset({"enterprise_qa_ownership"}),
    ),
    (
        re.compile(
            r"people[- ]management|managing\s+a\s+team|lead(?:ing)?\s+a\s+team|"
            r"direct\s+reports",
            re.I,
        ),
        frozenset({"people_management"}),
    ),
    (
        re.compile(
            r"cybersecurity|security\s+controls?|soc\s*2|infosec|"
            r"penetration\s+test",
            re.I,
        ),
        frozenset({"cybersecurity_controls"}),
    ),
    (
        re.compile(
            r"marketing\s+(?:workflow\s+)?automation|marketing\s+campaign|"
            r"paid\s+media|audience\s+funnel",
            re.I,
        ),
        frozenset({"marketing_automation"}),
    ),
    # CANDIDATE_SOURCE_INGESTION_V1: bachelor's-degree credential recognition.
    # Requires "bachelor" immediately followed by "degree"/"degrees" so a bare
    # "bachelor" (e.g. an unrelated proper noun) never matches; does not
    # attempt to recognize institutional-quality language ("top-tier
    # university") at all -- a requirement bundling both concepts will still
    # only ever be supported for the credential fact itself, never for
    # unevidenced institutional ranking.
    (
        re.compile(r"\bbachelor'?s?\s+degrees?\b", re.I),
        frozenset({"bachelors_degree_credential"}),
    ),
    # CANDIDATE_SOURCE_INGESTION_V1: Excel-proficiency recognition.
    # Negative lookahead on "excel in"/"excel at" excludes the ordinary
    # English verb usage ("excel in a fast-paced environment") from matching
    # the Microsoft Excel product/tool reference this capability represents.
    (
        re.compile(r"\bexcel\b(?!\s+(?:in|at)\b)", re.I),
        frozenset({"excel_proficiency"}),
    ),
    # REQUIREMENT_QUALIFIER_SEMANTICS_V1 (Q-1): institutional-quality
    # qualifier on a credential requirement. Emitted IN ADDITION TO
    # bachelors_degree_credential (a separate pattern above), never instead
    # of it -- a requirement bundling both concepts remains fully supported
    # for the credential fact itself, while this tag separately marks that
    # an institutional-ranking claim was also made.
    #
    # REQUIREMENT_QUALIFIER_SEMANTICS_V1 final Q-1 locality correction
    # (independent Cursor review, FALSE_CREDENTIAL_SOURCE_LINKAGE): two
    # prior versions both used an arbitrary bounded filler between the
    # credential word and "from" -- first {0,6} arbitrary tokens, then
    # {0,3} tokens additionally excluding clause-punctuation. Both were
    # still token-count-bounded arbitrary-content windows, and Cursor
    # demonstrated that ANY such window -- however short -- can be filled
    # by a real intervening noun phrase that is not the credential's
    # source: "Bachelor's degree required for candidates from top-tier
    # universities" ("required for candidates" is 3 tokens, contains no
    # punctuation, and fits inside {0,3} even though it names "candidates,"
    # not the degree, as what comes from the university). The root problem
    # was never the specific token count -- it was permitting ANY arbitrary
    # semantic material between the credential word and "from" at all. The
    # fix removes the arbitrary filler entirely. Between the credential
    # word and "from" this pattern now permits only one narrowly literal,
    # explicitly-tested credential-level modifier -- "(or higher)" -- and
    # nothing else; if "from" is not the very next thing after the
    # credential word (or after that one specific modifier), there is no
    # match. This directly encodes "the credential itself is described as
    # coming from this institution," not "an institution is mentioned
    # somewhere near a credential word": "required for candidates from...",
    # "preferred for graduates from...", "and experience with clients
    # from...", "preferred; experience ... from...", "required. Candidates
    # come from...", and "preferred, with customers from..." are all
    # rejected, because in every one of them something other than "from"
    # (or the one recognized modifier) immediately follows the credential
    # word. A known, accepted bounded limitation of this locality-only
    # design: "Bachelor's degree, from a top-tier university" (a comma
    # directly after the credential word, before "from") also does not
    # match -- an unusual formatting variant is missed in V1 rather than
    # risk manufacturing a false qualifier; this is an intentional
    # conservative trade-off, not an oversight. Still requires an
    # education-context noun (university/institution/college/school)
    # immediately after "top tier" so it cannot false-fire on unrelated
    # uses of "top-tier" (e.g. "top-tier customer service"). _norm()
    # already collapses "-" to " " before this runs, so "top tier" alone
    # covers both the hyphenated and unhyphenated source spellings. No
    # existing Claim carries this capability -- no evidence in this
    # repository currently establishes institutional ranking for any
    # candidate credential.
    (
        re.compile(
            r"\b(?:degrees?|bachelor'?s?|master'?s?|credentials?)\b"
            r"(?:\s*\(or\s+higher\))?\s+from\s+(?:an?\s+)?"
            r"top\s+tier\s+(?:universit(?:y|ies)|institutions?|colleges?|schools?)\b",
            re.I,
        ),
        frozenset({"institutional_quality_qualifier"}),
    ),
    # REQUIREMENT_QUALIFIER_SEMANTICS_V1 (Q-2): elevated Excel-proficiency
    # qualifier. Emitted IN ADDITION TO excel_proficiency (the pattern
    # above), never instead of it.
    #
    # REQUIREMENT_QUALIFIER_SEMANTICS_V1 final semantic correction
    # (independent Cursor review, SEMANTIC_PROXIMITY_FALSE_POSITIVE): an
    # earlier version allowed up to two arbitrary filler words between
    # "strong" and "excel," plus a required skill/proficiency noun right
    # after "excel." That still over-fired whenever the intervening filler
    # was itself the noun "strong" actually modifies -- e.g. "strong
    # interest in Excel skills development" ("interest in" sits in the
    # filler window, and "skills" still immediately follows "excel," so
    # both old constraints were satisfied even though "strong" modifies
    # "interest," not Excel proficiency). Same failure for "strong
    # preference for Excel skills training," "strong understanding of Excel
    # skills requirements," and "strong candidates with Excel skills." The
    # fix removes the arbitrary-filler window entirely: "strong" must now
    # be followed immediately (optionally through the literal brand word
    # "Microsoft" or "MS") by "excel," which must in turn be immediately
    # followed by a skill/proficiency noun. There is no wildcard filler
    # left for an intervening noun/preposition chain to hide in, so
    # "strong interest/preference/understanding/candidates ... Excel
    # skills" can never match regardless of what noun sits between "strong"
    # and "Excel" -- the construction must be the direct "strong [Microsoft]
    # Excel skills/proficiency/ability" phrase itself. This still matches
    # "strong Excel skills," "strong Microsoft Excel skills," and "strong
    # Excel proficiency," and still cannot match "strong communication/
    # analytical skills" (no "excel" present at all) or "strong familiarity
    # with Excel" (no skill/proficiency noun follows "excel"). V1
    # intentionally targets only this narrow, directly-adjacent
    # construction -- "advanced Excel", "expert Excel", and similar
    # intensity language remain unmatched; extending to those requires its
    # own demonstrated defect and evidence review, not silent expansion by
    # analogy. No existing Claim carries this capability -- current Excel
    # evidence establishes ordinary professional use, not independently
    # established strong/advanced/expert-tier proficiency.
    (
        re.compile(
            r"\bstrong\s+(?:(?:microsoft|ms)\s+)?excel\s+"
            r"(?:skills?|proficienc(?:y|ies)|abilit(?:y|ies))\b",
            re.I,
        ),
        frozenset({"excel_elevated_proficiency_qualifier"}),
    ),
    # COMPOUND_REQUIREMENT_SEMANTICS_V1: customer/client onboarding onto a
    # software platform/system/application/product, as an implementation
    # duty. Emitted additively alongside any other capability tags the
    # same requirement text also triggers (e.g. UAT) -- never in place of
    # them. Root cause: "Work alongside Implementation Managers to onboard
    # customers onto the platform, supporting everything from data
    # migration to UAT" previously inferred only {uat, pilot_testing,
    # test_documentation}, because no pattern recognized the onboarding
    # duty at all -- so the existing subset-check saw req_caps already
    # equal to claim_caps and reported SUPPORTED, even though onboarding
    # and data migration were never evidenced.
    #
    # BOUNDED CORRECTION (independent Cursor review, before commit): an
    # earlier version of this pattern fired on bare "onboard(ing)
    # customer(s)/client(s)" or "customer/client onboarding" with no
    # software/platform context requirement at all -- which over-fired on
    # entirely non-software onboarding duties that happen to share the
    # words "onboard"/"onboarding" + "customer"/"client": "client
    # onboarding for KYC/compliance", "client onboarding documentation at
    # a bank", "customer onboarding for account opening", "onboarding
    # wealth-management/consulting/advertising clients", bare "onboard
    # clients efficiently"/"onboard new customers"/"customer onboarding
    # process". None of those describe onboarding a customer *onto a
    # software system* -- they describe an entirely different (banking/
    # compliance/account-opening/relationship-management) onboarding
    # process this tag must never represent. The capability this milestone
    # actually needs to name is narrower than "customer onboarding" in
    # general: it is specifically "onboarding a customer/client onto a
    # platform/software/system/application/product." The tag itself was
    # renamed from the ambiguous `customer_onboarding` to
    # `customer_platform_onboarding` to make that scope explicit in the
    # capability name itself, since it was never committed and this is the
    # only opportunity to avoid locking in a misleadingly generic name.
    # The pattern now requires BOTH the customer/client onboarding
    # language AND an explicit software/platform/system/application/
    # product object, connected via a direct "onto"/"to" construction (with
    # only an optional article in between) -- not merely co-occurring
    # anywhere in the same sentence. This matches the frozen Atominvest
    # wording ("onboard customers onto the platform") and close variants
    # ("onboarding customers onto our platform", "onboard clients to the
    # software", "client onboarding onto the system", "customer onboarding
    # to the application") while refusing every reproduced non-software
    # onboarding case above, since none of them names a platform/software/
    # system/application/product as the destination of onboarding at all.
    # Conservative false negatives (a real software-onboarding duty phrased
    # without this exact "onto/to a platform-noun" construction) are an
    # accepted V1 limitation -- precision was prioritized over recall.
    # No existing Claim carries this capability -- no approved evidence in
    # this repository currently establishes customer/platform onboarding
    # work.
    (
        re.compile(
            r"\bonboard(?:ing)?\s+(?:new\s+)?(?:customers?|clients?)\s+"
            r"(?:onto|to)\s+(?:the\s+|our\s+|a\s+)?"
            r"(?:platform|software|system|application|product)\b|"
            r"\b(?:customer|client)\s+onboarding\s+"
            r"(?:onto|to)\s+(?:the\s+|our\s+|a\s+)?"
            r"(?:platform|software|system|application|product)\b",
            re.I,
        ),
        frozenset({"customer_platform_onboarding"}),
    ),
    # COMPOUND_REQUIREMENT_SEMANTICS_V1: data migration duty. Emitted
    # additively alongside any other capability tags the same requirement
    # text also triggers -- same root cause and rationale as
    # customer_platform_onboarding above ("...supporting everything from
    # data migration to UAT" left this duty entirely unrepresented).
    # Independent Cursor review found no material false-positive issue
    # with this pattern and one accepted conservative false negative
    # ("migrate customer records" -- "records," not "data," is named as
    # what is migrated); left unchanged in this correction, per explicit
    # scope. Bound to
    # the literal phrase "data migration" or "migrat(e/ing/ion) ... data"
    # (with a short bounded filler, e.g. "migrating customer data") so it
    # cannot false-fire on unrelated, non-data migration language (e.g.
    # "migrate the application to AWS", "system migration to a new
    # server", "migrating to a new office") -- none of those name "data"
    # as what is being migrated. No existing Claim carries this
    # capability -- no approved evidence in this repository currently
    # establishes customer/platform data-migration work.
    (
        re.compile(
            r"\bdata\s+migration\b|"
            r"\bmigrat(?:e|ing|ion)\s+(?:\w+\s+){0,2}data\b",
            re.I,
        ),
        frozenset({"data_migration"}),
    ),
    # EXPERIENCE_DURATION_QUALIFIER_VISIBILITY_V1 (final, corrected form):
    # marks that a Requirement contains a degree/credential condition
    # DIRECTLY, LOCALLY conjoined (via "and"/"plus", not "or") with an
    # explicit numeric years-of-experience condition -- e.g. "Bachelor's
    # degree plus a minimum of seven years of experience." Emitted
    # additively alongside whatever other capability tags the same
    # requirement text also triggers (e.g. bachelors_degree_credential) --
    # never in place of them.
    #
    # Root cause: frozen MIT's REQ_C_DEGREE_EXPERIENCE ("Bachelor's degree
    # plus a minimum of seven years of experience OR a master's degree and
    # minimum two years of experience OR equivalent") previously inferred
    # only {bachelors_degree_credential} -- the "minimum of seven years"
    # duration condition conjoined to it was entirely invisible, so
    # approving only a bare bachelor's-degree claim (zero years-of-
    # experience evidence at all) made the existing subset-check see
    # req_caps already equal to claim_caps and report SUPPORTED.
    #
    # BOUNDED CORRECTION (independent Cursor review, before commit,
    # OR_DISJUNCT_FALSE_PARTIAL): a first version of this tag matched any
    # "minimum/at least/N+ years of experience" phrase ANYWHERE in the
    # requirement text, with no connection to the credential at all. That
    # over-fired on the mirror-image case: an OR-disjoint alternative path
    # ("Bachelor's degree OR 5+ years of experience") where the duration
    # condition is a genuinely SEPARATE, independently-sufficient
    # alternative, not something the degree branch also requires -- an
    # approved bachelor's claim there should fully satisfy that branch,
    # not be demoted to PARTIAL merely because an unrelated duration
    # alternative exists elsewhere in the sentence. A sentence-wide "does
    # an AND/plus appear anywhere in this Requirement" gate (as
    # independently proposed and rejected) would still be unsafe: a
    # Requirement can contain both OR and AND while the duration remains
    # inside only one alternative branch (e.g. "Bachelor's degree OR 5+
    # years of experience, AND strong Excel skills" -- the trailing AND
    # connects to an unrelated Excel clause, not to the degree-vs-
    # experience alternative). The tag was therefore renamed from the
    # ambiguous `experience_duration_qualifier` to
    # `degree_experience_duration_conjunction` to make its narrower scope
    # explicit, and the pattern now requires the credential word itself to
    # be directly, locally followed by "and"/"plus" (never "or", and never
    # merely co-occurring anywhere in the sentence) before the duration
    # phrase -- mirroring the same local-connector-anchoring technique
    # already used for Q-1's institutional-quality-qualifier fix
    # (REQUIREMENT_QUALIFIER_SEMANTICS_V1). This correctly fires for the
    # frozen MIT text and for "Bachelor's degree AND minimum 5 years of
    # experience," and correctly does NOT fire for "Bachelor's degree OR
    # 5+ years of experience" (in any of its adversarial variants,
    # including ones with an unrelated trailing AND), because the word
    # immediately after the credential is "or," not "and"/"plus."
    #
    # This tag is a visibility/completeness guard, not a candidate-
    # duration evaluator: it does NOT mean "candidate has N years," does
    # NOT mean "candidate lacks N years" (candidate duration remains
    # CANDIDATE_EXPERIENCE_DURATION_NOT_YET_CANONICAL, unchanged), and
    # does NOT attempt to choose between OR-branches (that qualification-
    # path branch-selection question remains explicitly open, not solved
    # here) -- it only prevents an independently-supported credential
    # component from making a *locally, conjunctively attached* numeric-
    # duration component look satisfied when it sits unrepresented. No
    # existing Claim carries this capability -- no approved evidence in
    # this repository establishes any specific years-of-experience
    # threshold.
    #
    # Deliberately narrower than, and non-overlapping with, the generic
    # "N years of work experience" band phrasing EXPERIENCE_RANGE_
    # SEMANTICS_V1 already owns (that phrasing ends in "... work
    # experience"; this pattern requires bare "... years of experience,"
    # without "work"). Confirmed non-overlapping against every
    # EXPERIENCE_RANGE_SEMANTICS_V1 test phrase and every SAP-years
    # phrase. Supports digit and small written-number forms (one-ten,
    # matching the same style already used for senior-years detection in
    # job_decision.py). Bound to "minimum"/"at least"/"N+" duration
    # framing specifically so it cannot false-fire on unrelated numeric
    # mentions that are not years-of-experience conditions at all (e.g.
    # "managed seven projects," "minimum two certifications," "seven
    # years since graduation," "$5+ million budget," "five years of data
    # retention").
    (
        re.compile(
            r"\b(?:degrees?|bachelor'?s?|master'?s?|credentials?)\s+"
            r"(?:and|plus)\s+"
            r"(?:"
            r"(?:a\s+)?minimum\s+(?:of\s+)?"
            r"(?:\d+|one|two|three|four|five|six|seven|eight|nine|ten)"
            r"\s*\+?\s*years?\s+of\s+experience|"
            r"at\s+least\s+"
            r"(?:\d+|one|two|three|four|five|six|seven|eight|nine|ten)"
            r"\s*\+?\s*years?\s+of\s+experience|"
            r"\d+\+\s*years?\s+of\s+experience"
            r")\b",
            re.I,
        ),
        frozenset({"degree_experience_duration_conjunction"}),
    ),
)

# Forced NONE traps for known unsupported upgrades (no positive transfer).
_NONE_TRAPS: tuple[tuple[str, frozenset[str], str], ...] = (
    (
        "salesforce_unsupported",
        frozenset({"salesforce_administration"}),
        "No approved Evidence/Claim supports Salesforce administration.",
    ),
    (
        "enterprise_platform_unsupported",
        frozenset({"enterprise_platform_specialization"}),
        "No approved Evidence/Claim supports Workday/ServiceNow/SAP specialization. "
        "A named enterprise-platform requirement (e.g. a specific SAP module such as "
        "FI/CO) is never satisfied by generic transferable-capability overlap alone "
        "(e.g. 'requirements gathering' text coincidentally matching Winter Walk's "
        "requirements-elicitation capability) -- this trap fires on any capability "
        "overlap that includes a named-platform tag, before any claim is considered, "
        "regardless of what other generic capabilities are also present in the same "
        "requirement text.",
    ),
    (
        "google_cloud_vs_apps_script",
        frozenset({"google_cloud_engineering"}),
        "Google Cloud / cloud engineering is not supported by Google Apps Script evidence.",
    ),
    (
        "production_ml",
        frozenset({"production_ml"}),
        "Production ML / machine learning engineering is unsupported by current Evidence.",
    ),
    (
        "enterprise_qa_ownership",
        frozenset({"enterprise_qa_ownership"}),
        "UAT/pilot documentation does not establish enterprise QA ownership.",
    ),
    (
        "us_regulatory",
        frozenset({"us_regulatory_reporting"}),
        "Current trusted Claim/Evidence banks do not support U.S. regulatory "
        "reporting / SEC / SOX-style domain expertise. Winter Walk software "
        "controls are not regulatory-domain evidence.",
    ),
    (
        "people_management",
        frozenset({"people_management"}),
        "No approved Evidence/Claim supports people-management / team-leadership.",
    ),
    (
        "bpmn_modeling_unsupported",
        frozenset({"bpmn_modeling"}),
        "No approved Evidence/Claim supports BPMN / formal enterprise process "
        "modeling expertise.",
    ),
    (
        "lean_six_sigma_unsupported",
        frozenset({"lean_six_sigma"}),
        "No approved Evidence/Claim supports Lean / Six Sigma certification or "
        "formal-framework expertise.",
    ),
    (
        "process_mining_unsupported",
        frozenset({"process_mining_telemetry"}),
        "No approved Evidence/Claim supports automated process-mining / telemetry "
        "platforms (e.g. Celonis, UiPath Process Mining).",
    ),
    (
        "cybersecurity_unsupported",
        frozenset({"cybersecurity_controls"}),
        "No approved Evidence/Claim supports cybersecurity / infosec controls expertise.",
    ),
    (
        "marketing_automation_unsupported",
        frozenset({"marketing_automation"}),
        "Marketing automation / paid-media work is outside approved Claim capabilities.",
    ),
)


def _error(code: str, **fields: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {"code": code}
    payload.update(fields)
    return payload


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text.casefold().replace("-", " ")).strip()


def _requirement_blob(requirement: Mapping[str, Any]) -> str:
    parts = [
        str(requirement.get("text") or ""),
        str(requirement.get("source_text") or ""),
        str(requirement.get("domain") or ""),
        str(requirement.get("category") or ""),
    ]
    tech = requirement.get("technology")
    if isinstance(tech, list):
        parts.extend(str(item) for item in tech)
    return _norm(" ".join(parts))


def infer_requirement_capabilities(requirement: Mapping[str, Any]) -> frozenset[str]:
    blob = _requirement_blob(requirement)
    caps: set[str] = set()
    for pattern, tags in _REQ_CAPABILITY_PATTERNS:
        if pattern.search(blob):
            caps.update(tags)
    return frozenset(caps)


def claim_capabilities(claim: Mapping[str, Any]) -> frozenset[str]:
    claim_id = claim.get("claim_id")
    if isinstance(claim_id, str) and claim_id in _CLAIM_CAPABILITIES:
        return _CLAIM_CAPABILITIES[claim_id]
    return frozenset()


def load_reusable_claims(
    claim_index: Mapping[str, Any],
    evidence_index: Mapping[str, Any],
) -> list[Mapping[str, Any]]:
    """Return claim records that pass reusable validate_claim against Evidence."""
    reusable: list[Mapping[str, Any]] = []
    for claim in claim_index.values():
        if not isinstance(claim, Mapping):
            continue
        result = validate_claim(claim, evidence_index)
        if result.get("reusable") is True:
            reusable.append(claim)
    return reusable


def match_requirement(
    *,
    job_id: str,
    requirement: Mapping[str, Any],
    reusable_claims: Sequence[Mapping[str, Any]],
    evidence_index: Mapping[str, Any],
    match_index: int,
) -> dict[str, Any]:
    """Produce one evidence-match record for a requirement."""
    req_id = str(requirement.get("requirement_id"))
    match_id = f"MATCH_{job_id}_{req_id}_{match_index:02d}"
    req_text = str(requirement.get("text") or "")
    req_caps = infer_requirement_capabilities(requirement)

    # Forced NONE traps (including U.S. regulatory with current repository).
    for rule_id, trap_caps, explanation in _NONE_TRAPS:
        if req_caps.intersection(trap_caps):
            return {
                "match_id": match_id,
                "job_id": job_id,
                "requirement_id": req_id,
                "result": "NONE",
                "evidence_ids": [],
                "claim_ids": [],
                "explanation": (
                    f"[{rule_id}] raw={req_text!r}; "
                    f"canonical={sorted(req_caps)}; {explanation}"
                ),
                "transfer_note": None,
            }

    if not req_caps:
        relevance = requirement.get("relevance")
        result = "UNKNOWN" if relevance == "LOW" else "NONE"
        return {
            "match_id": match_id,
            "job_id": job_id,
            "requirement_id": req_id,
            "result": result,
            "evidence_ids": [],
            "claim_ids": [],
            "explanation": (
                f"raw={req_text!r}; No specific capability tags inferred; "
                "refusing generic lexical overmatch."
            ),
            "transfer_note": None,
        }

    best_claim: Mapping[str, Any] | None = None
    best_overlap: frozenset[str] = frozenset()
    for claim in reusable_claims:
        overlap = req_caps.intersection(claim_capabilities(claim))
        if len(overlap) > len(best_overlap):
            best_overlap = overlap
            best_claim = claim

    if best_claim is None or not best_overlap:
        relevance = requirement.get("relevance")
        result = "UNKNOWN" if relevance == "LOW" else "NONE"
        return {
            "match_id": match_id,
            "job_id": job_id,
            "requirement_id": req_id,
            "result": result,
            "evidence_ids": [],
            "claim_ids": [],
            "explanation": (
                f"raw={req_text!r}; canonical={sorted(req_caps)}; "
                "No approved Claim capability intersection."
            ),
            "transfer_note": None,
        }

    claim_id = best_claim.get("claim_id")
    claim_ids = [claim_id] if isinstance(claim_id, str) else []
    evidence_ids: list[str] = []
    cited = best_claim.get("evidence_ids")
    if isinstance(cited, list):
        for eid in cited:
            if isinstance(eid, str) and eid in evidence_index:
                evidence_ids.append(eid)
    evidence_ids = sorted(set(evidence_ids))

    claim_caps = claim_capabilities(best_claim)
    # Full coverage of inferred requirement capabilities → STRONG/SUPPORTED.
    # Partial capability intersection → PARTIAL with transfer note.
    if req_caps.issubset(claim_caps):
        state = best_claim.get("evidence_state")
        result = "STRONG" if state in {"VERIFIED", "SUPPORTED"} else "SUPPORTED"
        transfer_note = None
        explanation = (
            f"raw={req_text!r}; canonical={sorted(best_overlap)}; "
            f"provenance claim={claim_id} evidence={evidence_ids}."
        )
    else:
        result = "PARTIAL"
        transfer_note = (
            "Partial capability overlap only; not full equivalence to the "
            f"requested capabilities {sorted(req_caps)}."
        )
        explanation = (
            f"raw={req_text!r}; PARTIAL canonical overlap {sorted(best_overlap)}; "
            f"missing {sorted(req_caps - claim_caps)}; claim={claim_id}."
        )

    if result in {"STRONG", "SUPPORTED", "PARTIAL"} and not (claim_ids or evidence_ids):
        result = "NONE"
        transfer_note = None
        explanation = "Positive match rejected: missing Evidence/Claim provenance."

    return {
        "match_id": match_id,
        "job_id": job_id,
        "requirement_id": req_id,
        "result": result,
        "evidence_ids": evidence_ids,
        "claim_ids": claim_ids,
        "explanation": explanation,
        "transfer_note": transfer_note,
    }


def match_requirements(
    *,
    job_id: str,
    requirements: Sequence[Mapping[str, Any]],
    claim_index: Mapping[str, Any],
    evidence_index: Mapping[str, Any],
) -> dict[str, Any]:
    """Match all requirements; validate each evidence_match against schema."""
    validator = build_draft202012_validator(EVIDENCE_MATCH_SCHEMA_PATH)
    reusable = load_reusable_claims(claim_index, evidence_index)
    matches: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    for index, requirement in enumerate(requirements):
        if not isinstance(requirement, Mapping):
            errors.append(
                _error(
                    "MALFORMED_REQUIREMENT",
                    index=index,
                    detail="requirement must be a mapping",
                )
            )
            continue
        if (
            requirement.get("importance") == "UNCLEAR"
            and requirement.get("relevance") == "LOW"
            and not requirement.get("technology")
        ):
            continue

        match = match_requirement(
            job_id=job_id,
            requirement=requirement,
            reusable_claims=reusable,
            evidence_index=evidence_index,
            match_index=index,
        )
        schema_errors = [err.message for err in validator.iter_errors(match)]
        if schema_errors:
            errors.append(
                _error(
                    "EVIDENCE_MATCH_SCHEMA_INVALID",
                    requirement_id=requirement.get("requirement_id"),
                    details=schema_errors,
                )
            )
            continue
        if match["result"] in {"STRONG", "SUPPORTED", "PARTIAL"} and not (
            match["evidence_ids"] or match["claim_ids"]
        ):
            errors.append(
                _error(
                    "POSITIVE_MATCH_WITHOUT_PROVENANCE",
                    requirement_id=requirement.get("requirement_id"),
                    detail="positive match requires Evidence_ID and/or Claim_ID",
                )
            )
            continue
        matches.append(match)

    return {
        "valid": len(errors) == 0,
        "matches": matches,
        "errors": errors,
        "reusable_claim_count": len(reusable),
    }
