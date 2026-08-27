"""One-shot generator for Job Analysis Golden fixtures. Not a runtime dependency."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "golden-tests" / "job_analysis"
ROOT.mkdir(parents=True, exist_ok=True)


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


CORE_REQS = [
    req(
        "REQ_CORE_REQ",
        "Experience gathering requirements and clarifying scope boundaries",
        "MANDATORY",
        "HIGH",
        "Experience gathering requirements and clarifying scope boundaries is required",
        domain="Business Systems",
        category="REQUIREMENTS",
    ),
    req(
        "REQ_CORE_WF",
        "Experience with workflow automation and approval-synchronized evidence mapping",
        "MANDATORY",
        "HIGH",
        "Experience with workflow automation and approval-synchronized evidence mapping is required",
        domain="Business Process",
        category="PROCESS",
    ),
    req(
        "REQ_CORE_DATA",
        "Hands-on CSV / Drive-folder data ingestion with import logging",
        "MANDATORY",
        "HIGH",
        "Hands-on CSV / Drive-folder data ingestion with import logging is required",
        technology=["CSV"],
        domain="Data Operations",
        category="DATA",
    ),
    req(
        "REQ_CORE_UAT",
        "Comfort documenting UAT or pilot test outcomes",
        "MANDATORY",
        "HIGH",
        "Comfort documenting UAT or pilot test outcomes is required",
        domain="Implementation",
        category="TESTING",
    ),
    req(
        "REQ_CORE_CTRL",
        "Support fail-closed operational controls for outbound communications",
        "MANDATORY",
        "HIGH",
        "Support fail-closed operational controls for outbound follow-up communications",
        domain="Technical Operations",
        category="CONTROLS",
    ),
]


def main() -> None:
    write_fixture(
        "GT_BSA_STRONG",
        "Business Systems Analyst",
        "Business Systems",
        "EARLY_CAREER",
        """
Harborline Internal Tools — Business Systems Analyst (Synthetic Fixture)

This is repository Golden Test data only. It is not a claim about a real employer.

About the role
Early-career Business Systems Analyst supporting internal operating workflows,
requirements clarification, data intake quality, and UAT documentation with
nontechnical stakeholders.

Responsibilities
- Gather stakeholder requirements and clarify scope boundaries
- Automate workflow handoffs and keep approval-synchronized evidence mapping current
- Maintain CSV / Drive-folder intake with import logging
- Support fail-closed controls for outbound operational communications
- Document UAT / pilot outcomes

Minimum qualifications (required)
- Experience gathering requirements and clarifying scope boundaries
- Experience with workflow automation and approval-synchronized evidence mapping
- Hands-on CSV / Drive-folder data ingestion with import logging
- Comfort documenting UAT or pilot test outcomes
- Support fail-closed operational controls for outbound follow-up communications

Preferred qualifications
- Salesforce administration experience
""",
        CORE_REQS
        + [
            req(
                "REQ_PREF_SF",
                "Salesforce administration experience",
                "PREFERRED",
                "MEDIUM",
                "Preferred qualifications: Salesforce administration experience",
                category="PLATFORM",
                technology=["Salesforce"],
                domain="CRM",
                location="Preferred qualifications",
            ),
        ],
        {
            "purpose": "Strong early-career Business Systems fit with one preferred unsupported tool.",
            "role_family": "Business Systems",
            "acceptable_decisions": ["PRIORITY_APPLY", "APPLY", "EFFICIENT_APPLY"],
            "forbidden_decisions": ["REJECT"],
            "key_matches": {
                "REQ_CORE_REQ": {
                    "result": "STRONG",
                    "require_provenance": True,
                    "acceptable_results": ["STRONG", "SUPPORTED"],
                },
                "REQ_CORE_WF": {
                    "result": "STRONG",
                    "require_provenance": True,
                    "acceptable_results": ["STRONG", "SUPPORTED"],
                },
                "REQ_CORE_DATA": {
                    "result": "STRONG",
                    "require_provenance": True,
                    "acceptable_results": ["STRONG", "SUPPORTED"],
                },
                "REQ_CORE_UAT": {
                    "result": "SUPPORTED",
                    "require_provenance": True,
                    "acceptable_results": ["STRONG", "SUPPORTED"],
                },
                "REQ_CORE_CTRL": {
                    "result": "STRONG",
                    "require_provenance": True,
                    "acceptable_results": ["STRONG", "SUPPORTED"],
                },
                "REQ_PREF_SF": {"result": "NONE"},
            },
            "expect_gap_substrings": ["Salesforce"],
            "require_hard_blockers": False,
            "semantic_boundaries": ["preferred Salesforce gap must not auto-reject"],
            "known_limitations": ["NONE"],
            "notes": ["Positive routing expected for Business Systems family."],
        },
    )

    write_fixture(
        "GT_IMPL_FIT",
        "Implementation Analyst",
        "Implementation",
        "EARLY_CAREER",
        """
Northbridge Delivery — Implementation Analyst (Synthetic Fixture)

Early-career implementation role supporting customer requirements, CSV data
import, configuration handoffs, UAT documentation, and troubleshooting of
workflow automation issues.

Responsibilities
- Elicit customer requirements and clarify scope boundaries
- Import customer CSV datasets with import logging
- Configure workflow automation and approval-synchronized evidence mapping
- Document UAT / pilot results and support handoff troubleshooting

Minimum qualifications (required)
- Experience gathering requirements and clarifying scope boundaries
- Hands-on CSV / Drive-folder data ingestion with import logging
- Experience with workflow automation and approval-synchronized evidence mapping
- Comfort documenting UAT or pilot test outcomes
""",
        [
            req(
                "REQ_IMPL_REQ",
                "Experience gathering requirements and clarifying scope boundaries",
                "MANDATORY",
                "HIGH",
                "Experience gathering requirements and clarifying scope boundaries is required",
                category="REQUIREMENTS",
                domain="Implementation",
            ),
            req(
                "REQ_IMPL_DATA",
                "Hands-on CSV / Drive-folder data ingestion with import logging",
                "MANDATORY",
                "HIGH",
                "Hands-on CSV / Drive-folder data ingestion with import logging is required",
                category="DATA",
                technology=["CSV"],
                domain="Data Migration",
            ),
            req(
                "REQ_IMPL_WF",
                "Experience with workflow automation and approval-synchronized evidence mapping",
                "MANDATORY",
                "HIGH",
                "Experience with workflow automation and approval-synchronized evidence mapping is required",
                category="CONFIGURATION",
                domain="Implementation",
            ),
            req(
                "REQ_IMPL_UAT",
                "Comfort documenting UAT or pilot test outcomes",
                "MANDATORY",
                "HIGH",
                "Comfort documenting UAT or pilot test outcomes is required",
                category="TESTING",
                domain="QA/UAT",
            ),
        ],
        {
            "purpose": "Early-career Implementation Analyst fit using supported requirements/data/UAT evidence.",
            "role_family": "Implementation",
            "acceptable_decisions": ["PRIORITY_APPLY", "APPLY", "EFFICIENT_APPLY"],
            "forbidden_decisions": ["REJECT"],
            "key_matches": {
                "REQ_IMPL_REQ": {
                    "result": "STRONG",
                    "require_provenance": True,
                    "acceptable_results": ["STRONG", "SUPPORTED"],
                },
                "REQ_IMPL_DATA": {
                    "result": "STRONG",
                    "require_provenance": True,
                    "acceptable_results": ["STRONG", "SUPPORTED"],
                },
                "REQ_IMPL_WF": {
                    "result": "STRONG",
                    "require_provenance": True,
                    "acceptable_results": ["STRONG", "SUPPORTED"],
                },
                "REQ_IMPL_UAT": {
                    "result": "SUPPORTED",
                    "require_provenance": True,
                    "acceptable_results": ["STRONG", "SUPPORTED"],
                },
            },
            "semantic_boundaries": [
                "implementation family remains viable without exact BSA title"
            ],
            "known_limitations": ["NONE"],
            "notes": [],
        },
    )

    write_fixture(
        "GT_DATAOPS_FIT",
        "Data Operations Analyst",
        "Data Operations",
        "EARLY_CAREER",
        """
Civic Ledger Ops — Data Operations Analyst (Synthetic Fixture)

Role emphasizing recurring CSV intake quality, import logging, spreadsheet
validation, and operational reporting support. SQL is preferred only; do not
invent SQL evidence.

Responsibilities
- Run recurring CSV / Drive-folder data ingestion with import logging
- Validate spreadsheet intake quality before downstream use
- Support operational reporting packages from cleaned intakes
- Document pilot test / UAT checks for intake changes

Minimum qualifications (required)
- Hands-on CSV / Drive-folder data ingestion with import logging
- Experience gathering requirements and clarifying scope boundaries for intake workflows
- Comfort documenting UAT or pilot test outcomes for data-quality checks

Preferred qualifications
- SQL querying experience
""",
        [
            req(
                "REQ_DO_DATA",
                "Hands-on CSV / Drive-folder data ingestion with import logging",
                "MANDATORY",
                "HIGH",
                "Hands-on CSV / Drive-folder data ingestion with import logging is required",
                category="DATA",
                technology=["CSV"],
                domain="Data Operations",
            ),
            req(
                "REQ_DO_REQ",
                "Experience gathering requirements and clarifying scope boundaries for intake workflows",
                "MANDATORY",
                "HIGH",
                "Experience gathering requirements and clarifying scope boundaries for intake workflows is required",
                category="REQUIREMENTS",
                domain="Data Operations",
            ),
            req(
                "REQ_DO_UAT",
                "Comfort documenting UAT or pilot test outcomes for data-quality checks",
                "MANDATORY",
                "HIGH",
                "Comfort documenting UAT or pilot test outcomes for data-quality checks is required",
                category="TESTING",
                domain="Data Quality",
            ),
            req(
                "REQ_DO_SQL",
                "SQL querying experience",
                "PREFERRED",
                "MEDIUM",
                "Preferred qualifications: SQL querying experience",
                category="TECHNOLOGY",
                technology=["SQL"],
                domain="Data Operations",
                location="Preferred qualifications",
            ),
        ],
        {
            "purpose": "Data Operations fit grounded in CSV intake evidence; SQL preferred gap allowed.",
            "role_family": "Data Operations",
            "acceptable_decisions": ["PRIORITY_APPLY", "APPLY", "EFFICIENT_APPLY"],
            "forbidden_decisions": ["REJECT"],
            "key_matches": {
                "REQ_DO_DATA": {
                    "result": "STRONG",
                    "require_provenance": True,
                    "acceptable_results": ["STRONG", "SUPPORTED"],
                },
                "REQ_DO_REQ": {
                    "result": "STRONG",
                    "require_provenance": True,
                    "acceptable_results": ["STRONG", "SUPPORTED"],
                },
                "REQ_DO_UAT": {
                    "result": "SUPPORTED",
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

    write_fixture(
        "GT_PROCESS_MAP_P2",
        "Business Process Analyst",
        "Business Process",
        "EARLY_CAREER",
        """
Process Studio — Business Process Analyst (Synthetic Fixture)

Core mandatory work is generic business process mapping. This fixture exposes
known P-2 safe-direction limitation: current Claims/Evidence do not authorize
generic process-mapping capability.

Minimum qualifications (required)
- Map existing business processes and produce process maps for stakeholder review
- Experience gathering requirements and clarifying scope boundaries
- Comfort documenting UAT or pilot test outcomes
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
                "Experience gathering requirements and clarifying scope boundaries",
                "MANDATORY",
                "HIGH",
                "Experience gathering requirements and clarifying scope boundaries is required",
                category="REQUIREMENTS",
            ),
            req(
                "REQ_P2_UAT",
                "Comfort documenting UAT or pilot test outcomes",
                "MANDATORY",
                "HIGH",
                "Comfort documenting UAT or pilot test outcomes is required",
                category="TESTING",
            ),
        ],
        {
            "purpose": "Expose P-2: generic business process mapping fails closed to NONE; core mandatory HIGH NONE blocks positive apply.",
            "role_family": "Business Process",
            "acceptable_decisions": ["REJECT"],
            "forbidden_decisions": ["PRIORITY_APPLY", "APPLY", "EFFICIENT_APPLY"],
            "key_matches": {
                "REQ_P2_MAP": {"result": "NONE"},
                "REQ_P2_REQ": {
                    "result": "STRONG",
                    "require_provenance": True,
                    "acceptable_results": ["STRONG", "SUPPORTED"],
                },
                "REQ_P2_UAT": {
                    "result": "SUPPORTED",
                    "require_provenance": True,
                    "acceptable_results": ["STRONG", "SUPPORTED"],
                },
            },
            "expect_gap_substrings": ["process"],
            "require_hard_blockers": True,
            "semantic_boundaries": [
                "P-2 process mapping remains NONE without Claim/Evidence changes"
            ],
            "known_limitations": ["P-2"],
            "notes": ["Conservative REJECT is expected while P-2 remains deferred."],
        },
    )

    write_fixture(
        "GT_PREF_GAP_P1",
        "Business Systems Analyst",
        "Business Systems",
        "EARLY_CAREER",
        """
Lumen Ops — Business Systems Analyst (Synthetic Fixture)

Strong core Business Systems fit. Salesforce is preferred, but not required.

Minimum qualifications (required)
- Experience gathering requirements and clarifying scope boundaries
- Experience with workflow automation and approval-synchronized evidence mapping
- Hands-on CSV / Drive-folder data ingestion with import logging
- Comfort documenting UAT or pilot test outcomes
- Support fail-closed operational controls for outbound follow-up communications

Preferred qualifications
- Salesforce administration experience is preferred, but not required
""",
        CORE_REQS
        + [
            req(
                "REQ_P1_SF",
                "Salesforce administration experience",
                "PREFERRED",
                "MEDIUM",
                "Salesforce administration experience is preferred, but not required",
                category="PLATFORM",
                technology=["Salesforce"],
                domain="CRM",
                location="Preferred qualifications",
            ),
        ],
        {
            "purpose": "Preferred skill gap must not auto-reject; surfaces P-1 phrasing handling.",
            "role_family": "Business Systems",
            "acceptable_decisions": ["PRIORITY_APPLY", "APPLY", "EFFICIENT_APPLY"],
            "forbidden_decisions": ["REJECT"],
            "key_matches": {
                "REQ_CORE_REQ": {
                    "result": "STRONG",
                    "require_provenance": True,
                    "acceptable_results": ["STRONG", "SUPPORTED"],
                },
                "REQ_P1_SF": {"result": "NONE"},
            },
            "expected_importance": {"REQ_P1_SF": "PREFERRED"},
            "expect_gap_substrings": ["Salesforce"],
            "semantic_boundaries": [
                "preferred gap does not auto-reject",
                "P-1 preferred-but-not-required phrasing",
            ],
            "known_limitations": ["NONE"],
            "notes": [
                "P-1 bounded hardening: preferred, but not required -> PREFERRED."
            ],
        },
    )

    write_fixture(
        "GT_PLATFORM_REJECT",
        "Salesforce Business Systems Analyst",
        "Business Systems",
        "EARLY_CAREER",
        """
CRM Factory — Salesforce Business Systems Analyst (Synthetic Fixture)

Salesforce administration is the central mandatory specialization for this role.

Minimum qualifications (required)
- Salesforce administration experience is required
- Experience gathering requirements and clarifying scope boundaries
- Comfort documenting UAT or pilot test outcomes
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
                domain="CRM",
            ),
            req(
                "REQ_PLAT_REQ",
                "Experience gathering requirements and clarifying scope boundaries",
                "MANDATORY",
                "HIGH",
                "Experience gathering requirements and clarifying scope boundaries is required",
                category="REQUIREMENTS",
            ),
            req(
                "REQ_PLAT_UAT",
                "Comfort documenting UAT or pilot test outcomes",
                "MANDATORY",
                "HIGH",
                "Comfort documenting UAT or pilot test outcomes is required",
                category="TESTING",
            ),
        ],
        {
            "purpose": "Mandatory core platform specialization (Salesforce) must REJECT.",
            "role_family": "Business Systems",
            "acceptable_decisions": ["REJECT"],
            "forbidden_decisions": ["PRIORITY_APPLY", "APPLY", "EFFICIENT_APPLY"],
            "key_matches": {"REQ_PLAT_SF": {"result": "NONE"}},
            "expect_gap_substrings": ["Salesforce"],
            "require_hard_blockers": True,
            "semantic_boundaries": [
                "unsupported platform specialization blocks positive routing"
            ],
            "known_limitations": ["NONE"],
            "notes": [],
        },
    )

    write_fixture(
        "GT_SENIOR_REJECT",
        "Senior Business Systems Analyst",
        "Business Systems",
        "SENIOR",
        """
Senior Business Systems Analyst — Apex Systems Guild (Synthetic Fixture)

Requires 7+ years leading enterprise systems programs.

Minimum qualifications (required)
- 7+ years leading enterprise systems programs
- Experience gathering requirements and clarifying scope boundaries
- Experience with workflow automation and approval-synchronized evidence mapping
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
                "Experience gathering requirements and clarifying scope boundaries",
                "MANDATORY",
                "HIGH",
                "Experience gathering requirements and clarifying scope boundaries is required",
                category="REQUIREMENTS",
            ),
            req(
                "REQ_SEN_WF",
                "Experience with workflow automation and approval-synchronized evidence mapping",
                "MANDATORY",
                "HIGH",
                "Experience with workflow automation and approval-synchronized evidence mapping is required",
                category="PROCESS",
            ),
        ],
        {
            "purpose": "Clearly senior title/experience must REJECT.",
            "role_family": "Business Systems",
            "acceptable_decisions": ["REJECT"],
            "forbidden_decisions": ["PRIORITY_APPLY", "APPLY", "EFFICIENT_APPLY"],
            "key_matches": {
                "REQ_SEN_REQ": {
                    "result": "STRONG",
                    "require_provenance": True,
                    "acceptable_results": ["STRONG", "SUPPORTED"],
                },
            },
            "require_hard_blockers": True,
            "semantic_boundaries": ["seniority defense-in-depth"],
            "known_limitations": ["NONE"],
            "notes": [],
        },
    )

    write_fixture(
        "GT_SWE_REJECT",
        "Software Engineer",
        "Software Engineering",
        "MID",
        """
Bytebridge — Software Engineer (Synthetic Fixture)

Substantive software engineering role. Generic overlap words such as
requirements, testing, APIs, data, and stakeholders must not produce APPLY.

Minimum qualifications (required)
- Build and maintain backend services and APIs as a software engineer
- Write automated tests for production services
- Partner with stakeholders on technical requirements definition
- Work with data pipelines supporting application features
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
                domain="Software Engineering",
            ),
            req(
                "REQ_SWE_REQ",
                "Partner with stakeholders on technical requirements definition",
                "MANDATORY",
                "MEDIUM",
                "Partner with stakeholders on technical requirements definition is required",
                category="REQUIREMENTS",
            ),
            req(
                "REQ_SWE_DATA",
                "Work with data pipelines supporting application features",
                "MANDATORY",
                "MEDIUM",
                "Work with data pipelines supporting application features is required",
                category="DATA",
            ),
        ],
        {
            "purpose": "Software Engineering role must REJECT despite generic shared vocabulary.",
            "role_family": "Software Engineering",
            "acceptable_decisions": ["REJECT"],
            "forbidden_decisions": ["PRIORITY_APPLY", "APPLY", "EFFICIENT_APPLY"],
            "key_matches": {
                "REQ_SWE_CORE": {
                    "result": "NONE",
                    "acceptable_results": ["NONE", "UNKNOWN"],
                },
            },
            "semantic_boundaries": [
                "generic lexical overlap cannot create APPLY for SWE"
            ],
            "known_limitations": ["NONE"],
            "notes": [],
        },
    )

    write_fixture(
        "GT_ML_REJECT",
        "Machine Learning Engineer",
        "Machine Learning Engineering",
        "MID",
        """
ModelYard — Machine Learning Engineer (Synthetic Fixture)

Requires production ML systems and model deployment. LLM API experimentation
is not equivalent.

Minimum qualifications (required)
- Build production ML systems and machine learning pipelines
- Deploy models to production ML infrastructure
- Experience gathering requirements and clarifying scope boundaries
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
                domain="Machine Learning",
            ),
            req(
                "REQ_ML_DEPLOY",
                "Deploy models to production ML infrastructure",
                "MANDATORY",
                "HIGH",
                "Deploy models to production ML infrastructure is required",
                category="ML",
                domain="Machine Learning",
            ),
            req(
                "REQ_ML_REQ",
                "Experience gathering requirements and clarifying scope boundaries",
                "MANDATORY",
                "MEDIUM",
                "Experience gathering requirements and clarifying scope boundaries is required",
                category="REQUIREMENTS",
            ),
        ],
        {
            "purpose": "Production ML / model deployment must REJECT; not equivalent to LLM API use.",
            "role_family": "Machine Learning Engineering",
            "acceptable_decisions": ["REJECT"],
            "forbidden_decisions": ["PRIORITY_APPLY", "APPLY", "EFFICIENT_APPLY"],
            "key_matches": {
                "REQ_ML_PROD": {"result": "NONE"},
                "REQ_ML_DEPLOY": {
                    "result": "NONE",
                    "acceptable_results": ["NONE", "UNKNOWN"],
                },
            },
            "semantic_boundaries": ["MarketMind/LLM API use is not production ML"],
            "known_limitations": ["NONE"],
            "notes": [],
        },
    )

    write_fixture(
        "GT_REGULATORY_TRAP",
        "Business Systems Analyst",
        "Business Systems",
        "EARLY_CAREER",
        """
Compliance Ops Desk — Business Systems Analyst (Synthetic Fixture)

Strong core systems fit plus preferred U.S. regulatory / SEC / SOX familiarity.
Current repository must not invent foreign regulatory background.

Minimum qualifications (required)
- Experience gathering requirements and clarifying scope boundaries
- Experience with workflow automation and approval-synchronized evidence mapping
- Hands-on CSV / Drive-folder data ingestion with import logging
- Comfort documenting UAT or pilot test outcomes
- Support fail-closed operational controls for outbound follow-up communications

Preferred qualifications
- Familiarity with U.S. regulatory reporting packages (SEC / SOX-style controls)
""",
        CORE_REQS
        + [
            req(
                "REQ_REG_US",
                "Familiarity with U.S. regulatory reporting packages (SEC / SOX-style controls)",
                "PREFERRED",
                "MEDIUM",
                "Familiarity with U.S. regulatory reporting packages (SEC / SOX-style controls)",
                category="DOMAIN",
                domain="U.S. Regulatory Reporting",
                location="Preferred qualifications",
            ),
        ],
        {
            "purpose": "U.S. regulatory requirement must be NONE with current trusted repository.",
            "role_family": "Business Systems",
            "acceptable_decisions": ["PRIORITY_APPLY", "APPLY", "EFFICIENT_APPLY"],
            "forbidden_decisions": ["REJECT"],
            "key_matches": {
                "REQ_REG_US": {"result": "NONE"},
                "REQ_CORE_CTRL": {
                    "result": "STRONG",
                    "require_provenance": True,
                    "acceptable_results": ["STRONG", "SUPPORTED"],
                },
            },
            "expect_gap_substrings": ["regulatory"],
            "semantic_boundaries": [
                "Winter Walk software controls are not U.S. regulatory expertise"
            ],
            "known_limitations": ["NONE"],
            "notes": [],
        },
    )

    write_fixture(
        "GT_QA_TRAP",
        "Business Systems Analyst",
        "Business Systems",
        "EARLY_CAREER",
        """
Quality Bridge — Business Systems Analyst (Synthetic Fixture)

Core systems fit. Enterprise QA engineering ownership is preferred only and
must not be satisfied by Winter Walk UAT evidence.

Minimum qualifications (required)
- Experience gathering requirements and clarifying scope boundaries
- Experience with workflow automation and approval-synchronized evidence mapping
- Hands-on CSV / Drive-folder data ingestion with import logging
- Comfort documenting UAT or pilot test outcomes
- Support fail-closed operational controls for outbound follow-up communications

Preferred qualifications
- Enterprise QA engineering ownership experience is a bonus
""",
        CORE_REQS
        + [
            req(
                "REQ_QA_ENT",
                "Enterprise QA engineering ownership experience",
                "PREFERRED",
                "MEDIUM",
                "Enterprise QA engineering ownership experience is a bonus",
                category="QA",
                location="Preferred qualifications",
            ),
        ],
        {
            "purpose": "Enterprise QA ownership must remain NONE; UAT is not equivalent.",
            "role_family": "Business Systems",
            "acceptable_decisions": ["PRIORITY_APPLY", "APPLY", "EFFICIENT_APPLY"],
            "forbidden_decisions": ["REJECT"],
            "key_matches": {
                "REQ_CORE_UAT": {
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

    write_fixture(
        "GT_CLOUD_REJECT",
        "Business Systems Analyst",
        "Business Systems",
        "EARLY_CAREER",
        """
Cloudrail Systems — Business Systems Analyst (Synthetic Fixture)

Google Cloud infrastructure engineering is a core mandatory requirement.
Apps Script evidence must not count as equivalent.

Minimum qualifications (required)
- Exposure to Google Cloud infrastructure / GCP engineering is required
- Experience gathering requirements and clarifying scope boundaries
- Comfort documenting UAT or pilot test outcomes
""",
        [
            req(
                "REQ_CLOUD_GCP",
                "Exposure to Google Cloud infrastructure / GCP engineering",
                "MANDATORY",
                "HIGH",
                "Exposure to Google Cloud infrastructure / GCP engineering is required",
                category="TECHNOLOGY",
                technology=["Google Cloud", "GCP"],
                domain="Cloud",
            ),
            req(
                "REQ_CLOUD_REQ",
                "Experience gathering requirements and clarifying scope boundaries",
                "MANDATORY",
                "HIGH",
                "Experience gathering requirements and clarifying scope boundaries is required",
                category="REQUIREMENTS",
            ),
            req(
                "REQ_CLOUD_UAT",
                "Comfort documenting UAT or pilot test outcomes",
                "MANDATORY",
                "HIGH",
                "Comfort documenting UAT or pilot test outcomes is required",
                category="TESTING",
            ),
        ],
        {
            "purpose": "Mandatory GCP/cloud engineering must REJECT; Apps Script is not equivalent.",
            "role_family": "Business Systems",
            "acceptable_decisions": ["REJECT"],
            "forbidden_decisions": ["PRIORITY_APPLY", "APPLY", "EFFICIENT_APPLY"],
            "key_matches": {"REQ_CLOUD_GCP": {"result": "NONE"}},
            "expect_gap_substrings": ["Google Cloud"],
            "require_hard_blockers": True,
            "semantic_boundaries": ["Apps Script != Google Cloud engineering"],
            "known_limitations": ["NONE"],
            "notes": [],
        },
    )

    write_fixture(
        "GT_ADJ_TECHOPS",
        "Technical Operations Analyst",
        "Technical Operations",
        "EARLY_CAREER",
        """
Signal Desk — Technical Operations Analyst (Synthetic Fixture)

Adjacent Blueprint family. Viable through substantive requirements, not exact
Business Systems title dependence.

Minimum qualifications (required)
- Support fail-closed operational controls for outbound follow-up communications
- Hands-on CSV / Drive-folder data ingestion with import logging
- Experience gathering requirements and clarifying scope boundaries
- Comfort documenting UAT or pilot test outcomes
""",
        [
            req(
                "REQ_TO_CTRL",
                "Support fail-closed operational controls for outbound follow-up communications",
                "MANDATORY",
                "HIGH",
                "Support fail-closed operational controls for outbound follow-up communications is required",
                category="CONTROLS",
                domain="Technical Operations",
            ),
            req(
                "REQ_TO_DATA",
                "Hands-on CSV / Drive-folder data ingestion with import logging",
                "MANDATORY",
                "HIGH",
                "Hands-on CSV / Drive-folder data ingestion with import logging is required",
                category="DATA",
                technology=["CSV"],
            ),
            req(
                "REQ_TO_REQ",
                "Experience gathering requirements and clarifying scope boundaries",
                "MANDATORY",
                "HIGH",
                "Experience gathering requirements and clarifying scope boundaries is required",
                category="REQUIREMENTS",
            ),
            req(
                "REQ_TO_UAT",
                "Comfort documenting UAT or pilot test outcomes",
                "MANDATORY",
                "HIGH",
                "Comfort documenting UAT or pilot test outcomes is required",
                category="TESTING",
            ),
        ],
        {
            "purpose": "High-value adjacent Technical Operations family remains viable without exact-title dependence.",
            "role_family": "Technical Operations",
            "acceptable_decisions": [
                "PRIORITY_APPLY",
                "APPLY",
                "EFFICIENT_APPLY",
                "WATCH",
            ],
            "forbidden_decisions": [],
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
                "REQ_TO_REQ": {
                    "result": "STRONG",
                    "require_provenance": True,
                    "acceptable_results": ["STRONG", "SUPPORTED"],
                },
                "REQ_TO_UAT": {
                    "result": "SUPPORTED",
                    "require_provenance": True,
                    "acceptable_results": ["STRONG", "SUPPORTED"],
                },
            },
            "semantic_boundaries": ["adjacent family viability without exact title"],
            "known_limitations": ["NONE"],
            "notes": [
                "WATCH allowed only if substantive coverage is insufficient; positive preferred."
            ],
        },
    )

    write_fixture(
        "GT_UNRELATED_ANALYST",
        "Marketing Media Analyst",
        "Marketing Analytics",
        "EARLY_CAREER",
        """
Audience Pulse — Marketing Media Analyst (Synthetic Fixture)

Title contains Analyst but work is unrelated marketing/media analytics.

Minimum qualifications (required)
- Analyze paid media campaign performance and audience funnel metrics
- Build marketing dashboards for campaign stakeholders
- Recommend media mix changes based on engagement process insights
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
                domain="Media",
            ),
            req(
                "REQ_MKT_PROC",
                "Recommend media mix changes based on engagement process insights",
                "MANDATORY",
                "MEDIUM",
                "Recommend media mix changes based on engagement process insights is required",
                category="MARKETING",
            ),
        ],
        {
            "purpose": "Unrelated Analyst title must not APPLY via generic stakeholder/process vocabulary.",
            "role_family": "Marketing Analytics",
            "acceptable_decisions": ["REJECT", "WATCH", "UNDECIDED"],
            "forbidden_decisions": ["PRIORITY_APPLY", "APPLY", "EFFICIENT_APPLY"],
            "key_matches": {
                "REQ_MKT_MEDIA": {
                    "result": "NONE",
                    "acceptable_results": ["NONE", "UNKNOWN"],
                },
                "REQ_MKT_DASH": {
                    "result": "NONE",
                    "acceptable_results": ["NONE", "UNKNOWN"],
                },
            },
            "semantic_boundaries": ["Analyst title alone is insufficient for APPLY"],
            "known_limitations": ["NONE"],
            "notes": [],
        },
    )

    write_fixture(
        "GT_VAGUE_JD",
        "Operations Analyst",
        "Business Operations",
        "EARLY_CAREER",
        """
Horizon Collective — Operations Analyst (Synthetic Fixture)

We are a passionate, fast-paced team building the future of collaborative work.
Ideal teammates thrive in ambiguity, love stakeholders, and bring positive energy.

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
            "purpose": "Vague aspirational JD must keep UNCLEAR/UNKNOWN visible; no manufactured certainty.",
            "role_family": "Business Operations",
            "acceptable_decisions": ["WATCH", "UNDECIDED", "REJECT"],
            "forbidden_decisions": ["PRIORITY_APPLY", "APPLY", "EFFICIENT_APPLY"],
            "key_matches": {
                "REQ_V_AMBIG": {
                    "result": "NONE",
                    "acceptable_results": ["NONE", "UNKNOWN"],
                },
                "REQ_V_TOOLS": {
                    "result": "NONE",
                    "acceptable_results": ["NONE", "UNKNOWN"],
                },
            },
            "semantic_boundaries": [
                "do not manufacture certainty from vague JD prose"
            ],
            "known_limitations": ["NONE"],
            "notes": [
                "HR noise may be skipped; remaining ambiguity must not become positive apply."
            ],
        },
    )

    print("fixtures", len(list(ROOT.glob("GT_*"))))


if __name__ == "__main__":
    main()
