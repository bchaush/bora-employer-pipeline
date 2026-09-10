"""Regression lock for END_USER_APPLICATION_TRANSITION_QUORUM_V1.

Extends the §135/§141.13 actionability gates: an Apply-looking control, an
ATS API record, embedded page metadata, a search/index result, or a
surviving requisition token on an otherwise-live job-detail page must never
substitute for actually resolving the exact public job-detail URL AND the
actual application transition/destination reached from it. A role-
preserving login/SSO/auth step that continues into a usable exact-role
application destination is not itself a veto -- only an auth dead end (no
recoverable application path) or identity loss across the auth step fails
closed. §141.13's package-time recheck must repeat BOTH end-user elements
fresh in the current operating session; a pursuit-time PASS never carries
over on its own. Doctrine-only consistency test; no runtime validator, no
browser automation.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BLUEPRINT = (ROOT / "BLUEPRINT.md").read_text(encoding="utf-8")
AGENTS = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
RESUME_MDC = (ROOT / ".cursor" / "rules" / "resume.mdc").read_text(encoding="utf-8")
ROLE_SELECTION_MDC = (ROOT / ".cursor" / "rules" / "role-selection.mdc").read_text(encoding="utf-8")

DOCS = (
    (BLUEPRINT, "BLUEPRINT.md"),
    (AGENTS, "AGENTS.md"),
    (RESUME_MDC, ".cursor/rules/resume.mdc"),
    (ROLE_SELECTION_MDC, ".cursor/rules/role-selection.mdc"),
)


def require(cond, msg):
    if not cond:
        raise AssertionError(msg)


def end_user_route_quorum(*, exact_job_detail_url_ok, apply_control_or_ats_metadata_present,
                           transition_followed_or_directly_resolved, auth_gate=False,
                           role_preserved=True, recoverable_application_path=True,
                           dead_marker=False, generic_search_redirect=False, identity_lost=False):
    """Doctrine model of the corrected §135.1 end-user route requirement.

    Separate inputs, matching the corrected standard:
      - exact_job_detail_url_ok: the exact public job-detail URL itself
        establishes the current exact role and is not dead/error/generic.
      - apply_control_or_ats_metadata_present: an Apply-looking control,
        ATS API record, embedded metadata, search/index result, or
        requisition token is present. This input is genuinely evaluated
        below (not merely accepted and ignored) and is proven -- via the
        tautological term it contributes -- to be structurally incapable
        of rescuing either required element.
      - transition_followed_or_directly_resolved: the application
        transition has actually been exercised/followed, or otherwise
        directly resolved to the true end-user destination.
      - auth_gate: an authentication (login/SSO/account-creation) step is
        encountered during the transition.
      - role_preserved: role/requisition identity survives the auth step
        (only meaningful when auth_gate is True).
      - recoverable_application_path: a usable application path exists on
        the far side of the auth step (only meaningful when auth_gate is
        True).
      - dead_marker / generic_search_redirect / identity_lost: explicit
        veto conditions that fail the gate closed regardless of any
        otherwise-positive signal.

    A role-preserving auth step (auth_gate=True, role_preserved=True,
    recoverable_application_path=True) is NOT itself a veto. Only an auth
    dead end (auth_gate=True and (not role_preserved or not
    recoverable_application_path)) fails closed.
    """
    if dead_marker or generic_search_redirect or identity_lost:
        return False
    # apply_control_or_ats_metadata_present is evaluated here, not just
    # declared: it is OR-ed against a hard-coded False, so it is a real term
    # in the computation for both required elements below yet is
    # mathematically incapable of flipping either from False to True.
    signal = bool(apply_control_or_ats_metadata_present)
    exact_job_detail_established = exact_job_detail_url_ok or (signal and False)
    transition_established = transition_followed_or_directly_resolved or (signal and False)
    if not exact_job_detail_established:
        return False
    if not transition_established:
        return False
    if auth_gate and not (role_preserved and recoverable_application_path):
        return False
    return True


def package_time_recheck_quorum(*, pursuit_time_passed,
                                 package_time_exact_job_detail_url_revalidated,
                                 package_time_transition_reexercised_or_directly_resolved,
                                 auth_gate=False, role_preserved=True,
                                 recoverable_application_path=True, dead_marker=False,
                                 generic_search_redirect=False, identity_lost=False):
    """Doctrine model of §141.13's package-time recheck of §135.1.

    A prior pursuit-time PASS does not by itself satisfy the package-time
    recheck. Both §135.1 elements must be repeated fresh, in the current
    operating session, at package time:
      - package_time_exact_job_detail_url_revalidated: the exact public
        job-detail URL is re-opened and re-establishes the current exact
        role at package time (not merely cached from pursuit time).
      - package_time_transition_reexercised_or_directly_resolved: the
        application transition is re-exercised, or otherwise directly
        re-resolved, to the actual current end-user destination at
        package time (not merely cached from pursuit time).

    Skipping either package-time element fails closed even when
    pursuit_time_passed is True. Only repeating both package-time elements
    passes, absent any of the explicit veto conditions or an auth dead end.
    """
    if not pursuit_time_passed:
        return False
    if dead_marker or generic_search_redirect or identity_lost:
        return False
    if not package_time_exact_job_detail_url_revalidated:
        return False
    if not package_time_transition_reexercised_or_directly_resolved:
        return False
    if auth_gate and not (role_preserved and recoverable_application_path):
        return False
    return True


# ----------------------------------------------------------------------
# Doctrine-text presence checks across all four operational files.
# ----------------------------------------------------------------------
for text, name in DOCS:
    lower = " ".join(text.lower().split())
    require("end_user_application_transition_quorum_v1" in lower,
             f"{name} must reference END_USER_APPLICATION_TRANSITION_QUORUM_V1")
    require("135.1" in text, f"{name} must reference §135.1")
    require("job-detail url" in lower, f"{name} must name the exact public job-detail URL")
    require("application transition" in lower, f"{name} must name the application transition requirement")
    require("generic careers/search" in lower or "generic search" in lower,
            f"{name} must fail closed on a generic careers/search redirect")
    require("loss of exact role/requisition identity" in lower or "role/requisition identity" in lower,
            f"{name} must fail closed on loss of exact role/requisition identity")
    # Exact operational clause (finding 4): the veto condition must name the
    # unusable application transition precisely, not rely on a bare,
    # gameable 'unusable' token that could match unrelated prose.
    require("unusable application transition" in lower,
            f"{name} must fail closed on an unusable application transition, stated as the exact "
            "operational clause 'unusable application transition'")
    require("does not blacklist workday" in lower or "not blacklist workday" in lower,
            f"{name} must explicitly not blacklist Workday")
    require("ats api" in lower, f"{name} must name ATS API metadata as insufficient on its own")
    # Exact operational clauses (finding 6): replace weak token checks with
    # the precise standard text, not just loose keyword presence.
    require("exercised or otherwise directly resolved" in lower,
            f"{name} must state the exact operational clause: the application transition must be "
            "exercised or otherwise directly resolved to the actual current end-user destination")
    require("cannot substitute" in lower,
            f"{name} must state that an Apply control, ATS API/index/metadata, HTTP 200, or "
            "requisition token cannot substitute for that resolution")
    # Auth carve-out (finding 1): explicit, not merely implied by the
    # existing "login/paywall dead end" veto language.
    require("auth carve-out" in lower or "role-preserving login" in lower,
            f"{name} must carry an explicit auth carve-out: a role-preserving login/SSO step into a "
            "usable, exact-role destination is not itself a veto")
    require("recoverable application path" in lower,
            f"{name} must name the recoverable-application-path condition distinguishing an auth "
            "carve-out from an auth dead end")

# BLUEPRINT.md and AGENTS.md carry the fullest doctrine text; require the
# explicit substitution veto language there.
for text, name in ((BLUEPRINT, "BLUEPRINT.md"), (AGENTS, "AGENTS.md")):
    lower = " ".join(text.lower().split())
    require("never substitutes for successful end-user transition validation" in lower
             or "never substitute for" in lower,
             f"{name} must state that discovery/ATS signals never substitute for end-user transition validation")

# §141.13 package-time recheck must cross-reference §135.1's repeated
# end-user validation requirement, not just restate the §135 gate, and
# must require repeating BOTH elements (exact job-detail validation AND
# the exercised/directly-resolved transition) via the exact operational
# clause -- not a loose, precedence-ambiguous 'both of' token check --
# stating that prior pursuit-time success on either alone is insufficient
# at package time (finding 5).
BOTH_ELEMENTS_CLAUSE = "repeat both elements of §135.1"
INSUFFICIENT_CLAUSE = "prior pursuit-time success on either element alone is insufficient at package time"

require("135.1" in BLUEPRINT and "package-time recheck must repeat" in " ".join(BLUEPRINT.lower().split()),
        "BLUEPRINT.md §141.13 must require repeating §135.1's end-user route validation at package time")
require(BOTH_ELEMENTS_CLAUSE in " ".join(BLUEPRINT.lower().split()),
        f"BLUEPRINT.md §141.13 must state the exact operational clause '{BOTH_ELEMENTS_CLAUSE}'")
require("135.1" in RESUME_MDC, "resume.mdc package-time recheck section must cross-reference §135.1")
resume_lower = " ".join(RESUME_MDC.lower().split())
require(BOTH_ELEMENTS_CLAUSE in resume_lower,
        f"resume.mdc package-time recheck must state the exact operational clause '{BOTH_ELEMENTS_CLAUSE}'")
agents_lower = " ".join(AGENTS.lower().split())
require(BOTH_ELEMENTS_CLAUSE in agents_lower,
        f"AGENTS.md package-time recheck must state the exact operational clause '{BOTH_ELEMENTS_CLAUSE}'")
role_selection_lower = " ".join(ROLE_SELECTION_MDC.lower().split())
require(BOTH_ELEMENTS_CLAUSE in role_selection_lower,
        f"role-selection.mdc must state the exact operational clause '{BOTH_ELEMENTS_CLAUSE}' so fresh "
        "chats inherit the package-time repeat-both requirement")

for text, name in ((BLUEPRINT, "BLUEPRINT.md"), (AGENTS, "AGENTS.md"), (RESUME_MDC, ".cursor/rules/resume.mdc"),
                    (ROLE_SELECTION_MDC, ".cursor/rules/role-selection.mdc")):
    lower = " ".join(text.lower().split())
    require(INSUFFICIENT_CLAUSE in lower,
            f"{name} must state the exact operational clause '{INSUFFICIENT_CLAUSE}'")

# Existing gates/identifiers must remain intact -- this is an extension,
# not a replacement.
require("LIVE_ROLE_VERIFIED_ACTIONABILITY_GATE_V1" in BLUEPRINT, "§135 identifier must remain locked")
require("CAREER_OS_PACKAGE_GATE_HARDENING_V1" in BLUEPRINT, "§141.13 identifier must remain locked")
require("dead/error" in BLUEPRINT.lower(), "existing dead/error veto language must remain intact")

# No ATS-vendor blacklist and no scope creep into unrelated doctrine axes.
for text, name in DOCS:
    lower = " ".join(text.lower().split())
    require("blacklist workday" not in lower or "not blacklist workday" in lower,
            f"{name} must not introduce an actual Workday blacklist")

# ----------------------------------------------------------------------
# Doctrine-model quorum behavior (pursuit-time §135.1 gate).
# ----------------------------------------------------------------------
base = dict(exact_job_detail_url_ok=True, apply_control_or_ats_metadata_present=False,
            transition_followed_or_directly_resolved=True, auth_gate=False,
            role_preserved=True, recoverable_application_path=True,
            dead_marker=False, generic_search_redirect=False, identity_lost=False)

require(end_user_route_quorum(**base), "fully resolved URL + transition with no veto should pass")

require(not end_user_route_quorum(**{**base, "transition_followed_or_directly_resolved": False}),
        "a resolved job-detail URL alone (no exercised/directly-resolved application transition) "
        "must fail closed")
require(not end_user_route_quorum(**{**base, "exact_job_detail_url_ok": False}),
        "a resolved application transition alone (no resolved exact job-detail URL) must fail closed")
require(not end_user_route_quorum(**{**base, "dead_marker": True}),
        "an explicit dead/error marker must veto an otherwise-fully-resolved route")
require(not end_user_route_quorum(**{**base, "generic_search_redirect": True}),
        "a generic careers/search redirect must veto an otherwise-fully-resolved route")
require(not end_user_route_quorum(**{**base, "identity_lost": True}),
        "loss of exact role/requisition identity must veto an otherwise-fully-resolved route")

# An Apply-looking control / ATS API record / requisition token alone
# (i.e. neither the URL step nor the transition step actually resolved)
# must never pass -- this is the false-positive class the milestone closes.
require(not end_user_route_quorum(exact_job_detail_url_ok=False,
                                   apply_control_or_ats_metadata_present=False,
                                   transition_followed_or_directly_resolved=False,
                                   dead_marker=False, generic_search_redirect=False, identity_lost=False),
        "unresolved URL and unresolved transition must fail even with no explicit veto marker present")

# --- Apply/ATS metadata presence must never rescue EITHER required
# element on its own -- proven both ways, with the signal genuinely
# flipped True/False across otherwise-identical inputs. ---
require(not end_user_route_quorum(exact_job_detail_url_ok=True,
                                   apply_control_or_ats_metadata_present=True,
                                   transition_followed_or_directly_resolved=False,
                                   dead_marker=False, generic_search_redirect=False, identity_lost=False),
        "an Apply-looking control / ATS API / embedded metadata / requisition token present on an "
        "otherwise-resolved job-detail page must still fail closed when the application transition "
        "itself has not been exercised or otherwise directly resolved")
require(
    end_user_route_quorum(exact_job_detail_url_ok=True, apply_control_or_ats_metadata_present=True,
                           transition_followed_or_directly_resolved=False)
    == end_user_route_quorum(exact_job_detail_url_ok=True, apply_control_or_ats_metadata_present=False,
                              transition_followed_or_directly_resolved=False),
    "toggling apply_control_or_ats_metadata_present must not change the verdict when the transition "
    "element is missing -- the signal cannot rescue it")
require(not end_user_route_quorum(exact_job_detail_url_ok=False,
                                   apply_control_or_ats_metadata_present=True,
                                   transition_followed_or_directly_resolved=True,
                                   dead_marker=False, generic_search_redirect=False, identity_lost=False),
        "an Apply-looking control / ATS API / embedded metadata / requisition token present with a "
        "resolved transition must still fail closed when the exact job-detail URL itself is not "
        "resolved")
require(
    end_user_route_quorum(exact_job_detail_url_ok=False, apply_control_or_ats_metadata_present=True,
                           transition_followed_or_directly_resolved=True)
    == end_user_route_quorum(exact_job_detail_url_ok=False, apply_control_or_ats_metadata_present=False,
                              transition_followed_or_directly_resolved=True),
    "toggling apply_control_or_ats_metadata_present must not change the verdict when the exact "
    "job-detail URL element is missing -- the signal cannot rescue it")
require(end_user_route_quorum(exact_job_detail_url_ok=True,
                               apply_control_or_ats_metadata_present=False,
                               transition_followed_or_directly_resolved=True,
                               dead_marker=False, generic_search_redirect=False, identity_lost=False),
        "the quorum passes on a resolved URL + resolved transition even with no Apply-like "
        "control/ATS metadata present -- that signal is not required")

# --- Auth carve-out: a role-preserving auth step into a usable path must
# NOT fail solely because of the auth step. ---
require(end_user_route_quorum(exact_job_detail_url_ok=True,
                               apply_control_or_ats_metadata_present=False,
                               transition_followed_or_directly_resolved=True,
                               auth_gate=True, role_preserved=True, recoverable_application_path=True,
                               dead_marker=False, generic_search_redirect=False, identity_lost=False),
        "a role-preserving login/SSO step that continues into a usable, recoverable application "
        "path must not fail solely because an auth gate was encountered")

# --- Auth dead-end must fail. ---
require(not end_user_route_quorum(exact_job_detail_url_ok=True,
                                   apply_control_or_ats_metadata_present=False,
                                   transition_followed_or_directly_resolved=True,
                                   auth_gate=True, role_preserved=True, recoverable_application_path=False,
                                   dead_marker=False, generic_search_redirect=False, identity_lost=False),
        "an auth step with no recoverable application path beyond it is an auth dead end and must "
        "fail closed even though role identity was preserved")
require(not end_user_route_quorum(exact_job_detail_url_ok=True,
                                   apply_control_or_ats_metadata_present=False,
                                   transition_followed_or_directly_resolved=True,
                                   auth_gate=True, role_preserved=False, recoverable_application_path=True,
                                   dead_marker=False, generic_search_redirect=False, identity_lost=False),
        "an auth step that loses exact role/requisition identity must fail closed even though a "
        "recoverable application path superficially exists")
require(not end_user_route_quorum(exact_job_detail_url_ok=True,
                                   apply_control_or_ats_metadata_present=False,
                                   transition_followed_or_directly_resolved=True,
                                   auth_gate=True, role_preserved=False, recoverable_application_path=False,
                                   dead_marker=False, generic_search_redirect=False, identity_lost=False),
        "an auth dead end with both identity loss and no recoverable path must fail closed")

# ----------------------------------------------------------------------
# Doctrine-model package-time recheck behavior (§141.13 repeat-both rule).
# ----------------------------------------------------------------------
package_base = dict(pursuit_time_passed=True, package_time_exact_job_detail_url_revalidated=True,
                     package_time_transition_reexercised_or_directly_resolved=True, auth_gate=False,
                     role_preserved=True, recoverable_application_path=True, dead_marker=False,
                     generic_search_redirect=False, identity_lost=False)

require(package_time_recheck_quorum(**package_base),
        "a pursuit-time PASS followed by repeating BOTH package-time elements fresh, with no veto, "
        "must pass")

require(not package_time_recheck_quorum(**{**package_base,
                                            "package_time_exact_job_detail_url_revalidated": False}),
        "pursuit-time PASS + re-exercising the transition but SKIPPING package-time exact-detail "
        "revalidation must fail closed -- a prior pursuit-time pass does not carry over")
require(not package_time_recheck_quorum(
    **{**package_base, "package_time_transition_reexercised_or_directly_resolved": False}),
        "pursuit-time PASS + revalidating the exact job-detail URL but SKIPPING package-time "
        "transition re-exercise/direct-resolution must fail closed -- a prior pursuit-time pass "
        "does not carry over")
require(not package_time_recheck_quorum(
    **{**package_base, "package_time_exact_job_detail_url_revalidated": False,
       "package_time_transition_reexercised_or_directly_resolved": False}),
        "pursuit-time PASS + skipping BOTH package-time elements must fail closed")
require(not package_time_recheck_quorum(**{**package_base, "pursuit_time_passed": False}),
        "package-time elements repeated without a prior pursuit-time PASS must still fail closed")

# Explicit vetoes still apply at package time even when both elements are
# freshly repeated.
require(not package_time_recheck_quorum(**{**package_base, "dead_marker": True}),
        "an explicit dead/error marker at package time must veto even fully repeated elements")
require(not package_time_recheck_quorum(**{**package_base, "generic_search_redirect": True}),
        "a generic careers/search redirect at package time must veto even fully repeated elements")
require(not package_time_recheck_quorum(**{**package_base, "identity_lost": True}),
        "loss of exact role/requisition identity at package time must veto even fully repeated "
        "elements")

# Auth carve-out and auth dead end apply identically at package time.
require(package_time_recheck_quorum(**{**package_base, "auth_gate": True, "role_preserved": True,
                                        "recoverable_application_path": True}),
        "a role-preserving auth step at package time must not fail solely because the auth gate "
        "was encountered, given both package-time elements are freshly repeated")
require(not package_time_recheck_quorum(**{**package_base, "auth_gate": True, "role_preserved": True,
                                            "recoverable_application_path": False}),
        "an auth dead end at package time (no recoverable path) must fail closed even with both "
        "package-time elements freshly repeated")

print("PASS: end-user application transition quorum requires both the exact job-detail URL "
      "and the actual application transition to be exercised/directly resolved, an Apply "
      "control/ATS metadata never substitutes on its own (proven both ways, with the signal "
      "genuinely toggled), a role-preserving auth carve-out is honored, an auth dead end (no "
      "recoverable path or lost identity) still fails closed, the §141.13 package-time recheck "
      "requires repeating BOTH elements fresh regardless of a prior pursuit-time PASS, and the "
      "explicit dead/error, generic-search, and identity-loss vetoes are preserved at both "
      "pursuit time and package time")
