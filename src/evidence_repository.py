"""Repository-wide Evidence Repository integrity validation.

Validates the complete evidence storage area as an authoritative source
for downstream claim creation/retrieval.

This is deliberately separate from claim-scoped lineage validation:
- claim_lineage / claim_validation: cited Evidence_IDs for one claim;
- this module: structural trustworthiness of the full evidence repository.

No trusted index is returned when repository validation fails.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Optional

from schema_validation import build_draft202012_validator


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EVIDENCE_ROOT = ROOT / "evidence"
EVIDENCE_SCHEMA_PATH = ROOT / "schemas" / "evidence.schema.json"

# No authoritative Experience Registry exists yet. experience_id is only
# schema-checked as a non-empty string until a registry is approved.
EXPERIENCE_REGISTRY_STATUS = "EXPERIENCE_REGISTRY_DECISION_REQUIRED"


class DuplicateJsonKeyError(ValueError):
    """Raised when a JSON object contains a repeated key (no last-key-wins)."""

    def __init__(self, key: str) -> None:
        self.key = key
        super().__init__(f"duplicate JSON object key: {key!r}")


def _object_pairs_no_duplicates(
    pairs: list[tuple[str, Any]],
) -> dict[str, Any]:
    """Build a dict from JSON object pairs; fail closed on duplicate keys."""
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateJsonKeyError(key)
        result[key] = value
    return result


def _loads_strict_json(text: str) -> Any:
    """Parse JSON without silently resolving duplicate object keys."""
    return json.loads(text, object_pairs_hook=_object_pairs_no_duplicates)


def _error(code: str, **fields: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {"code": code}
    payload.update(fields)
    return payload


def _empty_result(*, records_checked: int = 0) -> dict[str, Any]:
    return {
        "valid": False,
        "records_checked": records_checked,
        "index": None,
        "errors": [],
        "discovered_paths": [],
        "experience_registry_status": EXPERIENCE_REGISTRY_STATUS,
    }


def discover_evidence_files(evidence_root: Path) -> list[Path]:
    """Discover evidence JSON files under evidence_root.

    Convention (v1):
    - Recursively include every ``*.json`` file under ``evidence_root``.
    - Every such file is treated as a candidate individual evidence record.
    - Ordering is deterministic by POSIX-style relative path (case-sensitive
      string sort), not OS directory iteration order.
    """
    root = evidence_root.resolve()
    if not root.exists():
        return []
    if not root.is_dir():
        raise NotADirectoryError(f"evidence_root is not a directory: {root}")

    files = [path for path in root.rglob("*.json") if path.is_file()]
    files.sort(key=lambda path: path.relative_to(root).as_posix())
    return files


def _relative_posix(path: Path, evidence_root: Path) -> str:
    try:
        return path.resolve().relative_to(evidence_root.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def validate_evidence_repository(
    evidence_root: Optional[Path] = None,
    *,
    schema_path: Optional[Path] = None,
) -> dict[str, Any]:
    """Validate the complete Evidence Repository and build a trusted index.

    An existing readable empty evidence root is structurally valid: it returns
    ``valid=True``, ``records_checked=0``, and an empty trusted ``index={}``.
    Non-empty / sufficiency requirements for a milestone or caller are enforced
    separately, not by this generic structural validator.

    Returns a mapping with:
    - valid: True only when every discovered file passes all invariants
      (including the empty-repository case above)
    - records_checked: number of discovered JSON files
    - index: evidence_id -> record when valid; otherwise None
    - errors: list of machine-readable error dicts
    - discovered_paths: deterministic relative POSIX paths checked
    - experience_registry_status: EXPERIENCE_REGISTRY_DECISION_REQUIRED
      until an authoritative Experience Registry exists
    """
    root = Path(evidence_root) if evidence_root is not None else DEFAULT_EVIDENCE_ROOT
    schema = Path(schema_path) if schema_path is not None else EVIDENCE_SCHEMA_PATH

    result = _empty_result()

    if not root.exists():
        result["errors"].append(
            _error(
                "EVIDENCE_ROOT_MISSING",
                path=str(root),
                detail="evidence root directory does not exist",
            )
        )
        return result

    if not root.is_dir():
        result["errors"].append(
            _error(
                "EVIDENCE_ROOT_NOT_DIRECTORY",
                path=str(root),
                detail="evidence root path exists but is not a directory",
            )
        )
        return result

    files = discover_evidence_files(root)
    result["records_checked"] = len(files)
    result["discovered_paths"] = [_relative_posix(path, root) for path in files]

    validator = build_draft202012_validator(schema)
    provisional_index: dict[str, Mapping[str, Any]] = {}
    # Track first path for each evidence_id for duplicate reporting.
    first_path_by_id: dict[str, str] = {}

    for path in files:
        rel = _relative_posix(path, root)
        stem = path.stem

        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            result["errors"].append(
                _error(
                    "EVIDENCE_FILE_READ_ERROR",
                    path=rel,
                    detail=str(exc),
                )
            )
            continue

        try:
            loaded = _loads_strict_json(text)
        except DuplicateJsonKeyError as exc:
            result["errors"].append(
                _error(
                    "EVIDENCE_JSON_DUPLICATE_KEY",
                    path=rel,
                    key=exc.key,
                    detail=f"duplicate JSON object key {exc.key!r}; no last-key-wins",
                )
            )
            continue
        except json.JSONDecodeError as exc:
            result["errors"].append(
                _error(
                    "EVIDENCE_JSON_PARSE_ERROR",
                    path=rel,
                    detail=f"JSON parse failed: {exc.msg} (line {exc.lineno})",
                    line=exc.lineno,
                    column=exc.colno,
                )
            )
            continue

        if not isinstance(loaded, dict):
            result["errors"].append(
                _error(
                    "EVIDENCE_UNSUPPORTED_RECORD_SHAPE",
                    path=rel,
                    detail=(
                        "evidence JSON root must be a single record object; "
                        f"got {type(loaded).__name__}"
                    ),
                )
            )
            continue

        schema_errors = [error.message for error in validator.iter_errors(loaded)]
        if schema_errors:
            result["errors"].append(
                _error(
                    "EVIDENCE_SCHEMA_INVALID",
                    path=rel,
                    evidence_id=loaded.get("evidence_id")
                    if isinstance(loaded.get("evidence_id"), str)
                    else None,
                    details=schema_errors,
                )
            )
            # Continue collecting additional repository invariants where possible.

        evidence_id = loaded.get("evidence_id")
        if not isinstance(evidence_id, str) or evidence_id == "":
            # Schema invalid already covers this when schema ran; still no index entry.
            continue

        if evidence_id != stem:
            result["errors"].append(
                _error(
                    "EVIDENCE_FILENAME_ID_MISMATCH",
                    path=rel,
                    evidence_id=evidence_id,
                    filename_stem=stem,
                    detail=(
                        f"filename stem {stem!r} must exactly equal "
                        f"evidence_id {evidence_id!r}"
                    ),
                )
            )

        if evidence_id in first_path_by_id:
            result["errors"].append(
                _error(
                    "DUPLICATE_EVIDENCE_ID",
                    evidence_id=evidence_id,
                    path=rel,
                    first_path=first_path_by_id[evidence_id],
                    detail=(
                        f"evidence_id {evidence_id!r} appears in multiple files; "
                        "no last-write-wins"
                    ),
                )
            )
        else:
            first_path_by_id[evidence_id] = rel
            # Only stage into provisional index when this file has no errors so far
            # for this iteration; final index is returned only if result has zero
            # errors overall.
            provisional_index[evidence_id] = loaded

    if result["errors"]:
        result["valid"] = False
        result["index"] = None
        return result

    # Deterministic index key order for consumers that iterate keys.
    ordered_index = {
        evidence_id: provisional_index[evidence_id]
        for evidence_id in sorted(provisional_index.keys())
    }
    result["valid"] = True
    result["index"] = ordered_index
    return result


def load_validated_evidence_repository(
    evidence_root: Optional[Path] = None,
    *,
    schema_path: Optional[Path] = None,
) -> dict[str, Any]:
    """Alias for validate_evidence_repository (load + validate + index)."""
    return validate_evidence_repository(
        evidence_root,
        schema_path=schema_path,
    )
