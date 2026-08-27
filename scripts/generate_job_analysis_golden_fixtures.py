"""One-shot generator for Job Analysis Golden fixtures (remediated wording)."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "golden-tests" / "job_analysis"


def req(
    rid,
    text,
    importance,
    relevance,
    source_text,
    category="CORE",
    technology=None,
    domain=None,
    location="Minimum qualifications (required)",
    seniority_implication=None,
    experience_level=None,
):
    return {
        "requirement_id": rid,
        "job_id": "PLACEHOLDER",
        "text": text,
        "category": category,
        "importance": importance,
        "seniority_implication": seniority_implication,
        "technology": technology or [],
        "experience_level": experience_level,
        "domain": domain,
        "relevance": relevance,
        "source_text": source_text,
        "source_location": location,
    }


def write_fixture(fid, role_title, role_family, seniority, jd, requirements, expected):
    d = ROOT / fid
    if d.exists():
        shutil.rmtree(d)
    d.mkdir(parents=True, exist_ok=True)
    (d / "jd.txt").write_text(jd.strip() + "\n", encoding="utf-8")
    extraction = {
        "_role_title": role_title,
        "role_family": role_family,
        "seniority": seniority,
        "extraction_version": "golden_structured_v1",
        "requirements": requirements,
    }
    (d / "structured_extraction.json").write_text(
        json.dumps(extraction, indent=2) + "\n", encoding="utf-8"
    )
    expected = dict(expected)
    expected["fixture_id"] = fid
    (d / "expected.json").write_text(
        json.dumps(expected, indent=2) + "\n", encoding="utf-8"
    )
    print("wrote", fid)


def main() -> None:
    ROOT.mkdir(parents=True, exist_ok=True)

    # --- 1 PRIORITY: exceptional BSA, no material preferred gap ---
    write_fixture(
        "GT_BSA_STRONG",
        "Business Systems Analyst",
        "Business Systems",
        "EARLY_CAREER",
        """
Harborline Civic Systems — Business Systems Analyst (Synthetic Fixture)

Repository Golden Test data only. Not a real employer vacancy.

We need an early-career analyst to improve internal tooling used by operations
staff. You will sit with stakeholders, turn fuzzy asks into clear requirements,
and help ship reliable spreadsheet/CSV intakes with documented acceptance checks.

What you will do
- Meet with operations owners to gather and clarify business requirements
- Help design controlled operational workflow automation with approval checkpoints
- Own recurring CSV file imports and spreadsheet data feeds with intake validation
- Keep outbound follow-up sends behind fail-closed / kill-switch style controls
- Run user acceptance testing and write up pilot validation notes

Required
- Gather and clarify business requirements with nontechnical stakeholders
- Experience with controlled operational workflow automation tied to approval gates
- Hands-on CSV import / spreadsheet data-feed intake with validation
- Document user acceptance testing or pilot validation outcomes
- Support fail-closed controls for outbound operational communications

Nice to have
- Familiarity with Salesforce is a plus
""",
        [
            req(
                "REQ_BSA_REQ",
                "Gather and clarify business requirements with nontechnical stakeholders",
                "MANDATORY",
                "HIGH",
                "Gather and clarify business requirements with nontechnical stakeholders",
                category="REQUIREMENTS",
                domain="Business Systems",
            ),
            req(
                "REQ_BSA_WF",
                "Experience with controlled operational workflow automation tied to approval gates",
                "MANDATORY",
                "HIGH",
                "Experience with controlled operational workflow automation tied to approval gates",
                category="PROCESS",
                domain="Operations",
            ),
            req(
                "REQ_BSA_DATA",
                "Hands-on CSV import / spreadsheet data-feed intake with validation",
                "MANDATORY",
                "HIGH",
                "Hands-on CSV import / spreadsheet data-feed intake with validation",
                category="DATA",
                technology=["CSV"],
                domain="Data Operations",
            ),
            req(
                "REQ_BSA_UAT",
                "Document user acceptance testing or pilot validation outcomes",
                "MANDATORY",
                "HIGH",
                "Document user acceptance testing or pilot validation outcomes",
                category="TESTING",
            ),
            req(
                "REQ_BSA_CTRL",
                "Support fail-closed controls for outbound operational communications",
                "MANDATORY",
                "HIGH",
                "Support fail-closed controls for outbound operational communications",
                category="CONTROLS",
            ),
            req(
                "REQ_BSA_SF",
                "Familiarity with Salesforce",
                "PREFERRED",
                "MEDIUM",
                "Nice to have: Familiarity with Salesforce is a plus",
                category="PLATFORM",
                technology=["Salesforce"],
                location="Nice to have",
            ),
        ],
        {
            "purpose": "Exceptional early-career BSA fit; trivial preferred SF gap must not remove Priority.",
            "role_family": "Business Systems",
            "acceptable_decisions": ["PRIORITY_APPLY"],
            "forbidden_decisions": ["REJECT", "WATCH"],
            "key_matches": {
                "REQ_BSA_REQ": {
                    "result": "STRONG",
                    "require_provenance": True,
                    "acceptable_results": ["STRONG", "SUPPORTED"],
                },
                "REQ_BSA_DATA": {
                    "result": "STRONG",
                    "require_provenance": True,
                    "acceptable_results": ["STRONG", "SUPPORTED"],
                },
                "REQ_BSA_UAT": {
                    "result": "SUPPORTED",
                    "require_provenance": True,
                    "acceptable_results": ["STRONG", "SUPPORTED"],
                },
                "REQ_BSA_SF": {"result": "NONE"},
            },
            "expect_gap_substrings": ["Salesforce"],
            "semantic_boundaries": [
                "non-material preferred gap does not remove PRIORITY_APPLY"
            ],
            "known_limitations": ["NONE"],
            "notes": [],
        },
    )

    # --- 2 APPLY: strong + material preferred gap ---
    write_fixture(
        "GT_PREF_GAP_P1",
        "Business Systems Analyst",
        "Business Systems",
        "EARLY_CAREER",
        """
Lumen Municipal Ops — Business Systems Analyst (Synthetic Fixture)

Strong core systems fit. CRM platform depth is preferred, but not required.

Required
- Collect stakeholder requirements and document scope boundaries
- Build controlled operational workflow automation with approval checkpoints
- Import CSV / spreadsheet data feeds with logging and validation
- Facilitate user acceptance testing and capture pilot results
- Maintain fail-closed outbound send controls

Preferred qualifications
- Salesforce administration experience is preferred, but not required
""",
        [
            req(
                "REQ_P1_REQ",
                "Collect stakeholder requirements and document scope boundaries",
                "MANDATORY",
                "HIGH",
                "Collect stakeholder requirements and document scope boundaries",
                category="REQUIREMENTS",
            ),
            req(
                "REQ_P1_WF",
                "Build controlled operational workflow automation with approval checkpoints",
                "MANDATORY",
                "HIGH",
                "Build controlled operational workflow automation with approval checkpoints",
                category="PROCESS",
            ),
            req(
                "REQ_P1_DATA",
                "Import CSV / spreadsheet data feeds with logging and validation",
                "MANDATORY",
                "HIGH",
                "Import CSV / spreadsheet data feeds with logging and validation",
                category="DATA",
                technology=["CSV"],
            ),
            req(
                "REQ_P1_UAT",
                "Facilitate user acceptance testing and capture pilot results",
                "MANDATORY",
                "HIGH",
                "Facilitate user acceptance testing and capture pilot results",
                category="TESTING",
            ),
            req(
                "REQ_P1_CTRL",
                "Maintain fail-closed outbound send controls",
                "MANDATORY",
                "HIGH",
                "Maintain fail-closed outbound send controls",
                category="CONTROLS",
            ),
            req(
                "REQ_P1_SF",
                "Salesforce administration experience",
                "PREFERRED",
                "HIGH",
                "Salesforce administration experience is preferred, but not required",
                category="PLATFORM",
                technology=["Salesforce"],
                location="Preferred qualifications",
            ),
        ],
        {
            "purpose": "Strong fit with material HIGH preferred Salesforce gap -> APPLY; P-1 phrasing.",
            "role_family": "Business Systems",
            "acceptable_decisions": ["APPLY"],
            "forbidden_decisions": ["PRIORITY_APPLY", "REJECT"],
            "key_matches": {"REQ_P1_SF": {"result": "NONE"}},
            "expected_importance": {"REQ_P1_SF": "PREFERRED"},
            "expect_gap_substrings": ["Salesforce"],
            "semantic_boundaries": [
                "material preferred gap downgrades Priority to APPLY",
                "P-1 preferred-but-not-required remains PREFERRED",
            ],
            "known_limitations": ["NONE"],
            "notes": [],
        },
    )

    # --- 3 EFFICIENT: thinner Data Ops coverage ---
    write_fixture(
        "GT_DATAOPS_FIT",
        "Data Operations Analyst",
        "Data Operations",
        "EARLY_CAREER",
        """
Civic Ledger Ops — Data Operations Analyst (Synthetic Fixture)

Focus on recurring intake quality. SQL is preferred only; do not invent SQL evidence.

Required
- Ingest spreadsheet data feeds and CSV imports with validation logging
- Document pilot testing notes when intake rules change

Preferred
- SQL querying experience
- Dashboarding experience
""",
        [
            req(
                "REQ_DO_DATA",
                "Ingest spreadsheet data feeds and CSV imports with validation logging",
                "MANDATORY",
                "HIGH",
                "Ingest spreadsheet data feeds and CSV imports with validation logging",
                category="DATA",
                technology=["CSV"],
                domain="Data Operations",
            ),
            req(
                "REQ_DO_UAT",
                "Document pilot testing notes when intake rules change",
                "MANDATORY",
                "HIGH",
                "Document pilot testing notes when intake rules change",
                category="TESTING",
            ),
            req(
                "REQ_DO_SQL",
                "SQL querying experience",
                "PREFERRED",
                "MEDIUM",
                "Preferred: SQL querying experience",
                category="TECHNOLOGY",
                technology=["SQL"],
                location="Preferred",
            ),
            req(
                "REQ_DO_DASH",
                "Dashboarding experience",
                "PREFERRED",
                "MEDIUM",
                "Preferred: Dashboarding experience",
                category="REPORTING",
                location="Preferred",
            ),
        ],
        {
            "purpose": "Plausible lower-intensity Data Ops fit -> EFFICIENT_APPLY.",
            "role_family": "Data Operations",
            "acceptable_decisions": ["EFFICIENT_APPLY"],
            "forbidden_decisions": ["PRIORITY_APPLY", "REJECT"],
            "key_matches": {
                "REQ_DO_DATA": {
                    "result": "STRONG",
                    "require_provenance": True,
                    "acceptable_results": ["STRONG", "SUPPORTED"],
                },
                "REQ_DO_SQL": {"result": "NONE", "acceptable_results": ["NONE", "UNKNOWN"]},
            },
            "expect_gap_substrings": ["SQL"],
            "semantic_boundaries": ["do not invent SQL evidence"],
            "known_limitations": ["NONE"],
            "notes": [],
        },
    )

    # --- 4 Implementation APPLY-ish / good fit ---
    write_fixture(
        "GT_IMPL_FIT",
        "Implementation Analyst",
        "Implementation",
        "EARLY_CAREER",
        """
Northbridge Delivery — Implementation Analyst (Synthetic Fixture)

Customer implementation work: requirements, imports, acceptance testing, and
controlled workflow setup. ServiceNow depth is preferred at HIGH relevance.

Required
- Elicit customer requirements and clarify scope before build
- Import customer CSV datasets with import logging
- Configure operational workflow automation with approval controls
- Lead user acceptance testing sessions and document outcomes

Preferred
- ServiceNow configuration experience
""",
        [
            req(
                "REQ_IMPL_REQ",
                "Elicit customer requirements and clarify scope before build",
                "MANDATORY",
                "HIGH",
                "Elicit customer requirements and clarify scope before build",
                category="REQUIREMENTS",
                domain="Implementation",
            ),
            req(
                "REQ_IMPL_DATA",
                "Import customer CSV datasets with import logging",
                "MANDATORY",
                "HIGH",
                "Import customer CSV datasets with import logging",
                category="DATA",
                technology=["CSV"],
            ),
            req(
                "REQ_IMPL_WF",
                "Configure operational workflow automation with approval controls",
                "MANDATORY",
                "HIGH",
                "Configure operational workflow automation with approval controls",
                category="CONFIGURATION",
            ),
            req(
                "REQ_IMPL_UAT",
                "Lead user acceptance testing sessions and document outcomes",
                "MANDATORY",
                "HIGH",
                "Lead user acceptance testing sessions and document outcomes",
                category="TESTING",
            ),
            req(
                "REQ_IMPL_SNOW",
                "ServiceNow configuration experience",
                "PREFERRED",
                "HIGH",
                "Preferred: ServiceNow configuration experience",
                category="PLATFORM",
                technology=["ServiceNow"],
                location="Preferred",
            ),
        ],
        {
            "purpose": "Implementation fit with material ServiceNow preferred gap -> APPLY.",
            "role_family": "Implementation",
            "acceptable_decisions": ["APPLY"],
            "forbidden_decisions": ["PRIORITY_APPLY", "REJECT"],
            "key_matches": {
                "REQ_IMPL_REQ": {
                    "result": "STRONG",
                    "require_provenance": True,
                    "acceptable_results": ["STRONG", "SUPPORTED"],
                },
                "REQ_IMPL_SNOW": {"result": "NONE"},
            },
            "expect_gap_substrings": ["ServiceNow"],
            "semantic_boundaries": ["ServiceNow specialization unsupported"],
            "known_limitations": ["NONE"],
            "notes": [],
        },
    )

    # --- 5 P-2 process mapping ---
    write_fixture(
        "GT_PROCESS_MAP_P2",
        "Business Process Analyst",
        "Business Process",
        "EARLY_CAREER",
        """
Process Studio — Business Process Analyst (Synthetic Fixture)

Core mandatory work is generic business process mapping. Exposes P-2
evidence-model gap: vocabulary may be recognized, but no approved Claim owns it.

Required
- Map existing business processes and produce process maps for stakeholder review
- Gather requirements and clarify scope boundaries
- Document user acceptance testing outcomes
""",
        [
            req(
                "REQ_P2_MAP",
                "Map existing business processes and produce process maps for stakeholder review",
                "MANDATORY",
                "HIGH",
                "Map existing business processes and produce process maps for stakeholder review is required",
                category="PROCESS",
                domain="Business Process",
            ),
            req(
                "REQ_P2_REQ",
                "Gather requirements and clarify scope boundaries",
                "MANDATORY",
                "HIGH",
                "Gather requirements and clarify scope boundaries is required",
                category="REQUIREMENTS",
            ),
            req(
                "REQ_P2_UAT",
                "Document user acceptance testing outcomes",
                "MANDATORY",
                "HIGH",
                "Document user acceptance testing outcomes is required",
                category="TESTING",
            ),
        ],
        {
            "purpose": "P-2 process mapping remains NONE without Claim/Evidence changes -> REJECT.",
            "role_family": "Business Process",
            "acceptable_decisions": ["REJECT"],
            "forbidden_decisions": ["PRIORITY_APPLY", "APPLY", "EFFICIENT_APPLY"],
            "key_matches": {"REQ_P2_MAP": {"result": "NONE"}},
            "expect_gap_substrings": ["process"],
            "require_hard_blockers": True,
            "semantic_boundaries": [
                "P-2 process mapping has no approved Claim capability provenance"
            ],
            "known_limitations": ["P-2"],
            "notes": [],
        },
    )

    # --- 6 Platform reject ---
    write_fixture(
        "GT_PLATFORM_REJECT",
        "Salesforce Business Systems Analyst",
        "Business Systems",
        "EARLY_CAREER",
        """
CRM Factory — Salesforce Business Systems Analyst (Synthetic Fixture)

Salesforce administration is the central mandatory specialization.

Required
- Salesforce administration experience is required
- Gather business requirements from operations stakeholders
- Document user acceptance testing outcomes
""",
        [
            req(
                "REQ_PLAT_SF",
                "Salesforce administration experience",
                "MANDATORY",
                "HIGH",
                "Salesforce administration experience is required",
                category="PLATFORM",
                technology=["Salesforce"],
            ),
            req(
                "REQ_PLAT_REQ",
                "Gather business requirements from operations stakeholders",
                "MANDATORY",
                "HIGH",
                "Gather business requirements from operations stakeholders",
                category="REQUIREMENTS",
            ),
            req(
                "REQ_PLAT_UAT",
                "Document user acceptance testing outcomes",
                "MANDATORY",
                "HIGH",
                "Document user acceptance testing outcomes",
                category="TESTING",
            ),
        ],
        {
            "purpose": "Mandatory Salesforce specialization -> REJECT.",
            "role_family": "Business Systems",
            "acceptable_decisions": ["REJECT"],
            "forbidden_decisions": ["PRIORITY_APPLY", "APPLY", "EFFICIENT_APPLY"],
            "key_matches": {"REQ_PLAT_SF": {"result": "NONE"}},
            "require_hard_blockers": True,
            "semantic_boundaries": ["unsupported platform specialization blocks apply"],
            "known_limitations": ["NONE"],
            "notes": [],
        },
    )

    # --- 7 Senior reject ---
    write_fixture(
        "GT_SENIOR_REJECT",
        "Senior Business Systems Analyst",
        "Business Systems",
        "SENIOR",
        """
Senior Business Systems Analyst — Apex Systems Guild (Synthetic Fixture)

Requires 7+ years leading enterprise systems programs.

Required
- 7+ years leading enterprise systems programs
- Gather and clarify business requirements
- Configure operational workflow automation with approval controls
""",
        [
            req(
                "REQ_SEN_YEARS",
                "7+ years leading enterprise systems programs",
                "MANDATORY",
                "HIGH",
                "Requires 7+ years leading enterprise systems programs",
                category="SENIORITY",
                seniority_implication="SENIOR",
                experience_level="7+ years",
            ),
            req(
                "REQ_SEN_REQ",
                "Gather and clarify business requirements",
                "MANDATORY",
                "HIGH",
                "Gather and clarify business requirements",
                category="REQUIREMENTS",
            ),
            req(
                "REQ_SEN_WF",
                "Configure operational workflow automation with approval controls",
                "MANDATORY",
                "HIGH",
                "Configure operational workflow automation with approval controls",
                category="PROCESS",
            ),
        ],
        {
            "purpose": "Senior title/experience -> REJECT.",
            "role_family": "Business Systems",
            "acceptable_decisions": ["REJECT"],
            "forbidden_decisions": ["PRIORITY_APPLY", "APPLY", "EFFICIENT_APPLY"],
            "key_matches": {
                "REQ_SEN_REQ": {
                    "result": "STRONG",
                    "require_provenance": True,
                    "acceptable_results": ["STRONG", "SUPPORTED"],
                }
            },
            "require_hard_blockers": True,
            "semantic_boundaries": ["seniority defense-in-depth"],
            "known_limitations": ["NONE"],
            "notes": [],
        },
    )

    # --- 8 SWE reject ---
    write_fixture(
        "GT_SWE_REJECT",
        "Software Engineer",
        "Software Engineering",
        "MID",
        """
Bytebridge — Software Engineer (Synthetic Fixture)

Substantive software engineering. Shared vocabulary must not create APPLY.

Required
- Build and maintain backend services and APIs as a software engineer
- Write automated tests for production services
- Partner with stakeholders on technical requirements definition
""",
        [
            req(
                "REQ_SWE_CORE",
                "Build and maintain backend services and APIs as a software engineer",
                "MANDATORY",
                "HIGH",
                "Build and maintain backend services and APIs as a software engineer is required",
                category="SWE",
                domain="Software Engineering",
            ),
            req(
                "REQ_SWE_TEST",
                "Write automated tests for production services",
                "MANDATORY",
                "HIGH",
                "Write automated tests for production services is required",
                category="TESTING",
            ),
            req(
                "REQ_SWE_REQ",
                "Partner with stakeholders on technical requirements definition",
                "MANDATORY",
                "MEDIUM",
                "Partner with stakeholders on technical requirements definition is required",
                category="REQUIREMENTS",
            ),
        ],
        {
            "purpose": "Software Engineering confirmed mismatch -> REJECT.",
            "role_family": "Software Engineering",
            "acceptable_decisions": ["REJECT"],
            "forbidden_decisions": ["PRIORITY_APPLY", "APPLY", "EFFICIENT_APPLY"],
            "key_matches": {
                "REQ_SWE_CORE": {"result": "NONE", "acceptable_results": ["NONE", "UNKNOWN"]}
            },
            "semantic_boundaries": ["generic overlap cannot create APPLY for SWE"],
            "known_limitations": ["NONE"],
            "notes": [],
        },
    )

    # --- 9 ML reject ---
    write_fixture(
        "GT_ML_REJECT",
        "Machine Learning Engineer",
        "Machine Learning Engineering",
        "MID",
        """
ModelYard — Machine Learning Engineer (Synthetic Fixture)

Production ML / model deployment required. LLM API experiments are not equivalent.

Required
- Build production ML systems and machine learning pipelines
- Deploy models to production ML infrastructure
""",
        [
            req(
                "REQ_ML_PROD",
                "Build production ML systems and machine learning pipelines",
                "MANDATORY",
                "HIGH",
                "Build production ML systems and machine learning pipelines is required",
                category="ML",
                technology=["Python"],
            ),
            req(
                "REQ_ML_DEPLOY",
                "Deploy models to production ML infrastructure",
                "MANDATORY",
                "HIGH",
                "Deploy models to production ML infrastructure is required",
                category="ML",
            ),
        ],
        {
            "purpose": "Production ML -> REJECT.",
            "role_family": "Machine Learning Engineering",
            "acceptable_decisions": ["REJECT"],
            "forbidden_decisions": ["PRIORITY_APPLY", "APPLY", "EFFICIENT_APPLY"],
            "key_matches": {"REQ_ML_PROD": {"result": "NONE"}},
            "semantic_boundaries": ["LLM API use is not production ML"],
            "known_limitations": ["NONE"],
            "notes": [],
        },
    )

    # --- 10 Regulatory trap -> APPLY (material HIGH preferred) ---
    write_fixture(
        "GT_REGULATORY_TRAP",
        "Business Systems Analyst",
        "Business Systems",
        "EARLY_CAREER",
        """
Compliance Ops Desk — Business Systems Analyst (Synthetic Fixture)

Strong systems core. U.S. regulatory / SEC / SOX familiarity is a material preferred ask.
Do not invent foreign regulatory background.

Required
- Clarify stakeholder requirements for internal controls tooling
- Maintain controlled operational workflow automation with approval gates
- Run CSV imports and data-feed validation for recurring packages
- Document acceptance testing / pilot validation
- Support fail-closed outbound communication controls

Preferred
- Hands-on U.S. regulatory reporting packages (SEC / SOX-style controls)
""",
        [
            req(
                "REQ_REG_REQ",
                "Clarify stakeholder requirements for internal controls tooling",
                "MANDATORY",
                "HIGH",
                "Clarify stakeholder requirements for internal controls tooling",
                category="REQUIREMENTS",
            ),
            req(
                "REQ_REG_WF",
                "Maintain controlled operational workflow automation with approval gates",
                "MANDATORY",
                "HIGH",
                "Maintain controlled operational workflow automation with approval gates",
                category="PROCESS",
            ),
            req(
                "REQ_REG_DATA",
                "Run CSV imports and data-feed validation for recurring packages",
                "MANDATORY",
                "HIGH",
                "Run CSV imports and data-feed validation for recurring packages",
                category="DATA",
                technology=["CSV"],
            ),
            req(
                "REQ_REG_UAT",
                "Document acceptance testing / pilot validation",
                "MANDATORY",
                "HIGH",
                "Document acceptance testing / pilot validation",
                category="TESTING",
            ),
            req(
                "REQ_REG_CTRL",
                "Support fail-closed outbound communication controls",
                "MANDATORY",
                "HIGH",
                "Support fail-closed outbound communication controls",
                category="CONTROLS",
            ),
            req(
                "REQ_REG_US",
                "Hands-on U.S. regulatory reporting packages (SEC / SOX-style controls)",
                "PREFERRED",
                "HIGH",
                "Preferred: Hands-on U.S. regulatory reporting packages (SEC / SOX-style controls)",
                category="DOMAIN",
                domain="U.S. Regulatory Reporting",
                location="Preferred",
            ),
        ],
        {
            "purpose": "U.S. regulatory preferred HIGH = NONE; strong core -> APPLY not Priority.",
            "role_family": "Business Systems",
            "acceptable_decisions": ["APPLY"],
            "forbidden_decisions": ["PRIORITY_APPLY", "REJECT"],
            "key_matches": {"REQ_REG_US": {"result": "NONE"}},
            "expect_gap_substrings": ["regulatory"],
            "semantic_boundaries": [
                "software controls are not U.S. regulatory expertise"
            ],
            "known_limitations": ["NONE"],
            "notes": [],
        },
    )

    # --- 11 QA trap ---
    write_fixture(
        "GT_QA_TRAP",
        "Business Systems Analyst",
        "Business Systems",
        "EARLY_CAREER",
        """
Quality Bridge — Business Systems Analyst (Synthetic Fixture)

Core systems fit. Enterprise QA ownership is preferred and must stay NONE vs UAT.

Required
- Document requirements after stakeholder workshops
- Operate controlled workflow automation with approval sync points
- Validate CSV / file imports for production intakes
- Run user acceptance testing and archive pilot notes
- Keep fail-closed send controls healthy

Preferred
- Enterprise QA engineering ownership experience
""",
        [
            req(
                "REQ_QA_REQ",
                "Document requirements after stakeholder workshops",
                "MANDATORY",
                "HIGH",
                "Document requirements after stakeholder workshops",
                category="REQUIREMENTS",
            ),
            req(
                "REQ_QA_WF",
                "Operate controlled workflow automation with approval sync points",
                "MANDATORY",
                "HIGH",
                "Operate controlled workflow automation with approval sync points",
                category="PROCESS",
            ),
            req(
                "REQ_QA_DATA",
                "Validate CSV / file imports for production intakes",
                "MANDATORY",
                "HIGH",
                "Validate CSV / file imports for production intakes",
                category="DATA",
                technology=["CSV"],
            ),
            req(
                "REQ_QA_UAT",
                "Run user acceptance testing and archive pilot notes",
                "MANDATORY",
                "HIGH",
                "Run user acceptance testing and archive pilot notes",
                category="TESTING",
            ),
            req(
                "REQ_QA_CTRL",
                "Keep fail-closed send controls healthy",
                "MANDATORY",
                "HIGH",
                "Keep fail-closed send controls healthy",
                category="CONTROLS",
            ),
            req(
                "REQ_QA_ENT",
                "Enterprise QA engineering ownership experience",
                "PREFERRED",
                "HIGH",
                "Preferred: Enterprise QA engineering ownership experience",
                category="QA",
                location="Preferred",
            ),
        ],
        {
            "purpose": "Enterprise QA preferred HIGH = NONE; UAT supported; APPLY.",
            "role_family": "Business Systems",
            "acceptable_decisions": ["APPLY"],
            "forbidden_decisions": ["PRIORITY_APPLY", "REJECT"],
            "key_matches": {
                "REQ_QA_UAT": {
                    "result": "SUPPORTED",
                    "require_provenance": True,
                    "acceptable_results": ["STRONG", "SUPPORTED"],
                },
                "REQ_QA_ENT": {"result": "NONE"},
            },
            "expect_gap_substrings": ["Enterprise QA"],
            "semantic_boundaries": ["UAT != enterprise QA ownership"],
            "known_limitations": ["NONE"],
            "notes": [],
        },
    )

    # --- 12 Cloud reject ---
    write_fixture(
        "GT_CLOUD_REJECT",
        "Business Systems Analyst",
        "Business Systems",
        "EARLY_CAREER",
        """
Cloudrail Systems — Business Systems Analyst (Synthetic Fixture)

GCP/cloud engineering is mandatory and core. Apps Script is not equivalent.

Required
- Google Cloud / GCP infrastructure engineering experience is required
- Gather business requirements for internal tools
- Document user acceptance testing outcomes
""",
        [
            req(
                "REQ_CLOUD_GCP",
                "Google Cloud / GCP infrastructure engineering experience",
                "MANDATORY",
                "HIGH",
                "Google Cloud / GCP infrastructure engineering experience is required",
                category="TECHNOLOGY",
                technology=["Google Cloud", "GCP"],
            ),
            req(
                "REQ_CLOUD_REQ",
                "Gather business requirements for internal tools",
                "MANDATORY",
                "HIGH",
                "Gather business requirements for internal tools",
                category="REQUIREMENTS",
            ),
            req(
                "REQ_CLOUD_UAT",
                "Document user acceptance testing outcomes",
                "MANDATORY",
                "HIGH",
                "Document user acceptance testing outcomes",
                category="TESTING",
            ),
        ],
        {
            "purpose": "Mandatory GCP -> REJECT.",
            "role_family": "Business Systems",
            "acceptable_decisions": ["REJECT"],
            "forbidden_decisions": ["PRIORITY_APPLY", "APPLY", "EFFICIENT_APPLY"],
            "key_matches": {"REQ_CLOUD_GCP": {"result": "NONE"}},
            "require_hard_blockers": True,
            "semantic_boundaries": ["Apps Script != Google Cloud engineering"],
            "known_limitations": ["NONE"],
            "notes": [],
        },
    )

    # --- 13 Adjacent TechOps EFFICIENT (thinner) ---
    write_fixture(
        "GT_ADJ_TECHOPS",
        "Technical Operations Analyst",
        "Technical Operations",
        "EARLY_CAREER",
        """
Signal Desk — Technical Operations Analyst (Synthetic Fixture)

Adjacent family. Viable via duties, not exact BSA title. Lower-intensity coverage.

Required
- Support fail-closed controls for outbound operational messages
- Keep CSV intake imports logging reliably

Preferred
- Light SQL comfort
""",
        [
            req(
                "REQ_TO_CTRL",
                "Support fail-closed controls for outbound operational messages",
                "MANDATORY",
                "HIGH",
                "Support fail-closed controls for outbound operational messages",
                category="CONTROLS",
                domain="Technical Operations",
            ),
            req(
                "REQ_TO_DATA",
                "Keep CSV intake imports logging reliably",
                "MANDATORY",
                "HIGH",
                "Keep CSV intake imports logging reliably",
                category="DATA",
                technology=["CSV"],
            ),
            req(
                "REQ_TO_SQL",
                "Light SQL comfort",
                "PREFERRED",
                "MEDIUM",
                "Preferred: Light SQL comfort",
                category="TECHNOLOGY",
                technology=["SQL"],
                location="Preferred",
            ),
        ],
        {
            "purpose": "Adjacent Technical Operations with thinner coverage -> EFFICIENT_APPLY.",
            "role_family": "Technical Operations",
            "acceptable_decisions": ["EFFICIENT_APPLY"],
            "forbidden_decisions": ["PRIORITY_APPLY", "REJECT"],
            "key_matches": {
                "REQ_TO_CTRL": {
                    "result": "STRONG",
                    "require_provenance": True,
                    "acceptable_results": ["STRONG", "SUPPORTED"],
                },
                "REQ_TO_DATA": {
                    "result": "STRONG",
                    "require_provenance": True,
                    "acceptable_results": ["STRONG", "SUPPORTED"],
                },
            },
            "semantic_boundaries": ["adjacent family without exact title dependence"],
            "known_limitations": ["NONE"],
            "notes": [],
        },
    )

    # --- 14 Unrelated Analyst REJECT ---
    write_fixture(
        "GT_UNRELATED_ANALYST",
        "Marketing Media Analyst",
        "Marketing Analytics",
        "EARLY_CAREER",
        """
Audience Pulse — Marketing Media Analyst (Synthetic Fixture)

Well-specified unrelated marketing/media analytics role.

Required
- Analyze paid media campaign performance and audience funnel metrics
- Build marketing dashboards for campaign stakeholders
- Manage marketing workflow automation for nurture campaigns
""",
        [
            req(
                "REQ_MKT_MEDIA",
                "Analyze paid media campaign performance and audience funnel metrics",
                "MANDATORY",
                "HIGH",
                "Analyze paid media campaign performance and audience funnel metrics is required",
                category="MARKETING",
                domain="Media",
            ),
            req(
                "REQ_MKT_DASH",
                "Build marketing dashboards for campaign stakeholders",
                "MANDATORY",
                "HIGH",
                "Build marketing dashboards for campaign stakeholders is required",
                category="MARKETING",
            ),
            req(
                "REQ_MKT_WF",
                "Manage marketing workflow automation for nurture campaigns",
                "MANDATORY",
                "HIGH",
                "Manage marketing workflow automation for nurture campaigns is required",
                category="MARKETING",
            ),
        ],
        {
            "purpose": "Confirmed unrelated Analyst duties -> REJECT; marketing automation != STRONG.",
            "role_family": "Marketing Analytics",
            "acceptable_decisions": ["REJECT"],
            "forbidden_decisions": ["PRIORITY_APPLY", "APPLY", "EFFICIENT_APPLY"],
            "key_matches": {
                "REQ_MKT_MEDIA": {"result": "NONE", "acceptable_results": ["NONE", "UNKNOWN"]},
                "REQ_MKT_WF": {"result": "NONE", "acceptable_results": ["NONE", "UNKNOWN"]},
            },
            "semantic_boundaries": [
                "Analyst title insufficient",
                "marketing workflow automation must not gain STRONG",
            ],
            "known_limitations": ["NONE"],
            "notes": [],
        },
    )

    # --- 15 Vague -> WATCH ---
    write_fixture(
        "GT_VAGUE_JD",
        "Operations Analyst",
        "Business Operations",
        "EARLY_CAREER",
        """
Horizon Collective — Operations Analyst (Synthetic Fixture)

Passionate fast-paced team. Vague aspirational prose with little evaluable substance.

About you
- Self-starter who thrives in a fast-paced environment
- Excited about process, data, and making an impact
- Comfortable with vague priorities and evolving scope

Nice to have
- Some exposure to modern tools
""",
        [
            req(
                "REQ_V_NOISE",
                "Self-starter who thrives in a fast-paced environment",
                "UNCLEAR",
                "LOW",
                "Must be a self-starter and team player who thrives in a fast-paced environment",
                category="HR_NOISE",
                location="About you",
            ),
            req(
                "REQ_V_VAGUE",
                "Excited about process, data, and making an impact",
                "UNCLEAR",
                "LOW",
                "Excited about process, data, and making an impact",
                category="CULTURE",
                location="About you",
            ),
            req(
                "REQ_V_AMBIG",
                "Comfortable with vague priorities and evolving scope",
                "UNCLEAR",
                "MEDIUM",
                "Comfortable with vague priorities and evolving scope",
                category="AMBIGUOUS",
                location="About you",
            ),
            req(
                "REQ_V_TOOLS",
                "Some exposure to modern tools",
                "PREFERRED",
                "LOW",
                "Nice to have: some exposure to modern tools",
                category="TOOLS",
                location="Nice to have",
            ),
        ],
        {
            "purpose": "Information deficit vague JD -> WATCH (not REJECT).",
            "role_family": "Business Operations",
            "acceptable_decisions": ["WATCH"],
            "forbidden_decisions": ["PRIORITY_APPLY", "APPLY", "EFFICIENT_APPLY", "REJECT"],
            "key_matches": {
                "REQ_V_AMBIG": {"result": "NONE", "acceptable_results": ["NONE", "UNKNOWN"]}
            },
            "semantic_boundaries": [
                "insufficient information routes to WATCH not REJECT"
            ],
            "known_limitations": ["NONE"],
            "notes": [],
        },
    )

    print("fixtures", len(list(ROOT.glob("GT_*"))))


if __name__ == "__main__":
    main()
