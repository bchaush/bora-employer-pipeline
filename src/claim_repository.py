"""Repository-wide Claim Bank identity/integrity validation.

Validates the claim storage area as an authoritative source for Claim_ID
discovery and retrieval.

Deliberately separate from claim-scoped semantic/lineage validation:
- claim_validation / claim_lineage / claim_semantic_guard: one claim vs Evidence;
- this module: structural trustworthiness of the claim repository files.

Returns a plain validation result dict (valid / index / errors). Claim records
retain persisted ``human_approval`` as a human-governed field; this module does
not mint a sealed trust object.

No trusted claim index is returned when repository validation fails.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Optional

from schema_validation import build_draft202012_validator


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CLAIM_ROOT = ROOT / "claims"
CLAIM_SCHEMA_PATH = ROOT / "schemas" / "claim.schema.json"


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
    }


def discover_claim_files(claim_root: Path) -> list[Path]:
    """Discover claim JSON files under claim_root.

    Convention (v1):
    - Recursively include every ``*.json`` file under ``claim_root``.
    - Every such file is treated as a candidate individual claim record.
    - Ordering is deterministic by POSIX-style relative path (case-sensitive
      string sort), not OS directory iteration order.
    """
    root = claim_root.resolve()
    if not root.exists():
        return []
    if not root.is_dir():
        raise NotADirectoryError(f"claim_root is not a directory: {root}")

    files = [path for path in root.rglob("*.json") if path.is_file()]
    files.sort(key=lambda path: path.relative_to(root).as_posix())
    return files


def _relative_posix(path: Path, claim_root: Path) -> str:
    try:
        return path.resolve().relative_to(claim_root.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def validate_claim_repository(
    claim_root: Optional[Path] = None,
    *,
    schema_path: Optional[Path] = None,
) -> dict[str, Any]:
    """Validate Claim Bank repository identity and structural integrity.

    Enforces:
    - strict JSON parse (duplicate object keys rejected);
    - canonical claim schema on every record;
    - globally unique Claim_ID;
    - filename stem exactly equals claim_id;
    - fail closed: any error => valid=False and index=None.

    An existing readable empty claim root is structurally valid:
    ``valid=True``, ``records_checked=0``, ``index={}``.
    """
    root = Path(claim_root) if claim_root is not None else DEFAULT_CLAIM_ROOT
    schema = Path(schema_path) if schema_path is not None else CLAIM_SCHEMA_PATH

    result = _empty_result()

    if not root.exists():
        result["errors"].append(
            _error(
                "CLAIM_ROOT_MISSING",
                path=str(root),
                detail="claim root directory does not exist",
            )
        )
        return result

    if not root.is_dir():
        result["errors"].append(
            _error(
                "CLAIM_ROOT_NOT_DIRECTORY",
                path=str(root),
                detail="claim root path exists but is not a directory",
            )
        )
        return result

    files = discover_claim_files(root)
    result["records_checked"] = len(files)
    result["discovered_paths"] = [_relative_posix(path, root) for path in files]

    validator = build_draft202012_validator(schema)
    provisional_index: dict[str, Mapping[str, Any]] = {}
    first_path_by_id: dict[str, str] = {}

    for path in files:
        rel = _relative_posix(path, root)
        stem = path.stem

        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            result["errors"].append(
                _error(
                    "CLAIM_FILE_READ_ERROR",
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
                    "CLAIM_JSON_DUPLICATE_KEY",
                    path=rel,
                    key=exc.key,
                    detail=f"duplicate JSON object key {exc.key!r}; no last-key-wins",
                )
            )
            continue
        except json.JSONDecodeError as exc:
            result["errors"].append(
                _error(
                    "CLAIM_JSON_PARSE_ERROR",
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
                    "CLAIM_UNSUPPORTED_RECORD_SHAPE",
                    path=rel,
                    detail=(
                        "claim JSON root must be a single record object; "
                        f"got {type(loaded).__name__}"
                    ),
                )
            )
            continue

        schema_errors = [error.message for error in validator.iter_errors(loaded)]
        if schema_errors:
            result["errors"].append(
                _error(
                    "CLAIM_SCHEMA_INVALID",
                    path=rel,
                    claim_id=loaded.get("claim_id")
                    if isinstance(loaded.get("claim_id"), str)
                    else None,
                    details=schema_errors,
                )
            )

        claim_id = loaded.get("claim_id")

        if not isinstance(claim_id, str) or claim_id == "":
            continue

        if claim_id != stem:
            result["errors"].append(
                _error(
                    "CLAIM_FILENAME_ID_MISMATCH",
                    path=rel,
                    claim_id=claim_id,
                    filename_stem=stem,
                    detail=(
                        f"filename stem {stem!r} must exactly equal "
                        f"claim_id {claim_id!r}"
                    ),
                )
            )

        if claim_id in first_path_by_id:
            result["errors"].append(
                _error(
                    "DUPLICATE_CLAIM_ID",
                    claim_id=claim_id,
                    path=rel,
                    first_path=first_path_by_id[claim_id],
                    detail=(
                        f"claim_id {claim_id!r} appears in multiple files; "
                        "no last-write-wins"
                    ),
                )
            )
        else:
            first_path_by_id[claim_id] = rel
            provisional_index[claim_id] = loaded

    if result["errors"]:
        result["valid"] = False
        result["index"] = None
        return result

    ordered_index = {
        claim_id: provisional_index[claim_id]
        for claim_id in sorted(provisional_index.keys())
    }
    result["valid"] = True
    result["index"] = ordered_index
    return result


def load_validated_claim_repository(
    claim_root: Optional[Path] = None,
    *,
    schema_path: Optional[Path] = None,
) -> dict[str, Any]:
    """Alias for validate_claim_repository (load + validate)."""
    return validate_claim_repository(claim_root, schema_path=schema_path)
