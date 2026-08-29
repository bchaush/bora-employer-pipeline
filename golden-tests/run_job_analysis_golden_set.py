"""Job Analysis v1 Golden Set runner.

Loads golden-tests/job_analysis fixtures, validates structured expected
behavior against schema, runs analyze_job, and asserts Blueprint-aligned
expectations. Distinguishes Golden coverage from unit/adversarial tests.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
GOLDEN_ROOT = ROOT / "golden-tests" / "job_analysis"
SCHEMA_PATH = ROOT / "schemas" / "job_analysis_golden_case.schema.json"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from claim_repository import validate_claim_repository  # noqa: E402
from evidence_repository import validate_evidence_repository  # noqa: E402
from experience_repository import validate_experience_repository  # noqa: E402
from job_analysis import analyze_job  # noqa: E402
from schema_validation import build_draft202012_validator  # noqa: E402


POSITIVE = frozenset({"PRIORITY_APPLY", "APPLY", "EFFICIENT_APPLY"})


def fail(message: str) -> None:
    print(f"FAIL: {message}")
    raise SystemExit(1)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def discover_fixtures() -> list[Path]:
    if not GOLDEN_ROOT.is_dir():
        fail(f"missing golden root {GOLDEN_ROOT}")
    fixtures = sorted(
        p for p in GOLDEN_ROOT.iterdir() if p.is_dir() and p.name.startswith("GT_")
    )
    if not fixtures:
        fail("no GT_* fixtures found")
    return fixtures


def assert_repository_regression() -> tuple[dict[str, Any], dict[str, Any]]:
    exp = validate_experience_repository()
    ev = validate_evidence_repository()
    cl = validate_claim_repository()
    if not (exp.get("valid") is True and exp.get("records_checked") == 4):
        fail(f"Experience regression failed: {exp}")
    if not (
        ev.get("valid") is True
        and ev.get("records_checked") == 36
        and ev.get("experience_registry_status")
        == "EXPERIENCE_REFERENCE_INTEGRITY_ENFORCED"
    ):
        fail(f"Evidence regression failed: {ev}")
    if not (cl.get("valid") is True and cl.get("records_checked") == 13):
        fail(f"Claim regression failed: {cl}")
    reusable_count = sum(
        1 for claim in cl["index"].values() if claim.get("human_approval") is True
    )
    if reusable_count != 11:
        fail(f"expected 11 reusable claims, got {reusable_count}")
    for claim in cl["index"].values():
        claim_id = claim.get("claim_id", "")
        if isinstance(claim_id, str) and (
            claim_id.startswith("CLAIM_WW_") or claim_id.startswith("CLAIM_MM_")
        ):
            if claim.get("human_approval") is not True:
                fail(f"{claim_id} must be approved/reusable gate")
    print(
        "PASS 0: repository regression "
        "(4 Experience / 36 Evidence / 13 Claims / 11 reusable)."
    )
    return ev["index"], cl["index"]


def evaluate_fixture(
    fixture_dir: Path,
    *,
    evidence_index: dict[str, Any],
    claim_index: dict[str, Any],
    expected_validator: Any,
) -> dict[str, Any]:
    fixture_id = fixture_dir.name
    jd_path = fixture_dir / "jd.txt"
    extraction_path = fixture_dir / "structured_extraction.json"
    expected_path = fixture_dir / "expected.json"

    for path in (jd_path, extraction_path, expected_path):
        if not path.is_file():
            fail(f"{fixture_id}: missing {path.name}")

    expected = load_json(expected_path)
    schema_errors = [e.message for e in expected_validator.iter_errors(expected)]
    if schema_errors:
        fail(f"{fixture_id}: expected.json schema invalid: {schema_errors}")

    if expected.get("fixture_id") != fixture_id:
        fail(
            f"{fixture_id}: expected.fixture_id "
            f"{expected.get('fixture_id')!r} must match directory name"
        )

    extraction = load_json(extraction_path)
    job_input = {
        "company": f"Synthetic Golden Co ({fixture_id})",
        "role": extraction.get("_role_title")
        or expected.get("notes", [None])[0]
        or fixture_id.replace("_", " "),
        "jd_text": jd_path.read_text(encoding="utf-8"),
        "fixture_key": fixture_id,
        "structured_extraction": {
            k: v for k, v in extraction.items() if not str(k).startswith("_")
        },
    }
    # Prefer explicit role title from extraction metadata.
    meta_role = extraction.get("_role_title")
    if isinstance(meta_role, str) and meta_role.strip():
        job_input["role"] = meta_role.strip()

    result = analyze_job(
        job_input,
        claim_index=claim_index,
        evidence_index=evidence_index,
    )
    if result.get("valid") is not True:
        fail(f"{fixture_id}: analyze_job invalid: {result.get('errors')}")

    analysis = result["analysis"]
    decision = analysis["decision"]
    acceptable = set(expected["acceptable_decisions"])
    forbidden = set(expected.get("forbidden_decisions") or [])

    row = {
        "fixture": fixture_id,
        "role_family": analysis.get("role_family"),
        "expected": sorted(acceptable),
        "actual": decision,
        "pass": decision in acceptable,
        "semantic_boundaries": expected.get("semantic_boundaries") or [],
        "known_limitations": expected.get("known_limitations") or [],
    }

    errors: list[str] = []
    if decision not in acceptable:
        errors.append(
            f"decision {decision!r} not in acceptable {sorted(acceptable)}"
        )
    if decision in forbidden:
        errors.append(f"decision {decision!r} is forbidden")

    if expected.get("require_hard_blockers") and not result.get("hard_blockers"):
        # Seniority / mandatory blockers may be expressed only in rationale.
        rationale = analysis.get("decision_rationale") or ""
        if decision != "REJECT" and "Hard blocker" not in rationale:
            errors.append("expected hard blockers / reject path")

    match_by_req = {
        m["requirement_id"]: m for m in analysis.get("evidence_matches") or []
    }
    for req_id, expectation in (expected.get("key_matches") or {}).items():
        match = match_by_req.get(req_id)
        if match is None:
            errors.append(f"missing match for {req_id}")
            continue
        allowed = set(expectation.get("acceptable_results") or [])
        if expectation.get("result"):
            allowed.add(expectation["result"])
        if match.get("result") not in allowed:
            errors.append(
                f"{req_id} result={match.get('result')!r} not in {sorted(allowed)}"
            )
        if expectation.get("require_provenance"):
            if match.get("result") in {"STRONG", "SUPPORTED", "PARTIAL"}:
                if not (match.get("evidence_ids") or match.get("claim_ids")):
                    errors.append(f"{req_id} positive match missing provenance")

    for req_id, importance in (expected.get("expected_importance") or {}).items():
        req = next(
            (
                r
                for r in analysis.get("requirements") or []
                if r.get("requirement_id") == req_id
            ),
            None,
        )
        if req is None:
            errors.append(f"missing requirement {req_id} for importance check")
        elif req.get("importance") != importance:
            errors.append(
                f"{req_id} importance={req.get('importance')!r} "
                f"expected {importance!r}"
            )

    gaps = " | ".join(analysis.get("gaps") or [])
    for needle in expected.get("expect_gap_substrings") or []:
        if needle.casefold() not in gaps.casefold():
            errors.append(f"expected gap substring {needle!r} not found")

    unknowns = " | ".join(analysis.get("unknowns") or [])
    for needle in expected.get("expect_unknown_substrings") or []:
        if needle.casefold() not in unknowns.casefold():
            errors.append(f"expected unknown substring {needle!r} not found")

    # Safety: no positive match without provenance in this analysis.
    for match in analysis.get("evidence_matches") or []:
        if match.get("result") in {"STRONG", "SUPPORTED", "PARTIAL"}:
            if not (match.get("evidence_ids") or match.get("claim_ids")):
                errors.append(
                    f"{match.get('requirement_id')} positive without provenance"
                )

    row["errors"] = errors
    row["pass"] = row["pass"] and not errors
    row["rationale"] = analysis.get("decision_rationale")
    return row


def test_malformed_expected_rejected(expected_validator: Any) -> None:
    bad = {
        "fixture_id": "GT_BAD",
        "purpose": "malformed",
        "role_family": "Business Systems",
        "acceptable_decisions": ["APPLY"],
        "key_matches": {"REQ_X": {"result": "MAYBE"}},
        "semantic_boundaries": ["x"],
        "known_limitations": ["NONE"],
    }
    if not list(expected_validator.iter_errors(bad)):
        fail("malformed expected.json must fail schema validation")
    print("PASS: malformed golden expected payload rejected by schema.")


def main() -> None:
    evidence_index, claim_index = assert_repository_regression()
    expected_validator = build_draft202012_validator(SCHEMA_PATH, check_schema=True)
    test_malformed_expected_rejected(expected_validator)

    rows: list[dict[str, Any]] = []
    for fixture_dir in discover_fixtures():
        row = evaluate_fixture(
            fixture_dir,
            evidence_index=evidence_index,
            claim_index=claim_index,
            expected_validator=expected_validator,
        )
        rows.append(row)
        status = "PASS" if row["pass"] else "FAIL"
        print(
            f"{status}: {row['fixture']} | family={row['role_family']} | "
            f"expected={row['expected']} | actual={row['actual']}"
        )
        if row["errors"]:
            for err in row["errors"]:
                print(f"  - {err}")

    print("\n=== GOLDEN RESULT MATRIX ===")
    print(
        f"{'Fixture':<28} {'Family':<22} {'Expected':<28} "
        f"{'Actual':<16} {'Status'}"
    )
    for row in rows:
        status = "PASS" if row["pass"] else "FAIL"
        expected = ",".join(row["expected"])
        family = str(row["role_family"] or "null")
        print(
            f"{row['fixture']:<28} {family:<22} {expected:<28} "
            f"{row['actual']:<16} {status}"
        )

    positive = [r for r in rows if r["actual"] in POSITIVE]
    rejected = [r for r in rows if r["actual"] == "REJECT"]
    watch = [r for r in rows if r["actual"] == "WATCH"]
    undecided = [r for r in rows if r["actual"] == "UNDECIDED"]
    failed = [r for r in rows if not r["pass"]]

    print("\n=== SUMMARY ===")
    print(f"fixtures={len(rows)}")
    print(f"positive_routing={len(positive)} {[r['fixture'] for r in positive]}")
    print(f"rejected={len(rejected)} {[r['fixture'] for r in rejected]}")
    print(f"watch={len(watch)} {[r['fixture'] for r in watch]}")
    print(f"undecided={len(undecided)} {[r['fixture'] for r in undecided]}")
    print(
        "known_limitations_noted="
        f"{sorted({lim for r in rows for lim in r['known_limitations'] if lim != 'NONE'})}"
    )

    if failed:
        print(f"FAILED fixtures: {[r['fixture'] for r in failed]}")
        raise SystemExit(1)

    print("PASS: job analysis golden set completed successfully.")


if __name__ == "__main__":
    main()
