"""Repository-wide Experience Registry integrity validation.

Validates the Experience Registry as the canonical identity source for
Experience_IDs used by evidence records.

Answers only: does this experience_id exist, and what real experience
does it identify?

Deliberately separate from:
- evidence repository integrity (facts about an experience);
- claim-scoped lineage validation.

No trusted index is returned when Experience Registry validation fails.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Optional

from schema_validation import build_draft202012_validator


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EXPERIENCE_ROOT = ROOT / "experiences"
EXPERIENCE_SCHEMA_PATH = ROOT / "schemas" / "experience.schema.json"


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


def discover_experience_files(experience_root: Path) -> list[Path]:
    """Discover experience JSON files under experience_root.

    Convention (v1):
    - Recursively include every ``*.json`` file under ``experience_root``.
    - Every such file is treated as a candidate individual experience record.
    - Ordering is deterministic by POSIX-style relative path (case-sensitive
      string sort), not OS directory iteration order.
    """
    root = experience_root.resolve()
    if not root.exists():
        return []
    if not root.is_dir():
        raise NotADirectoryError(f"experience_root is not a directory: {root}")

    files = [path for path in root.rglob("*.json") if path.is_file()]
    files.sort(key=lambda path: path.relative_to(root).as_posix())
    return files


def _relative_posix(path: Path, experience_root: Path) -> str:
    try:
        return path.resolve().relative_to(experience_root.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def validate_experience_repository(
    experience_root: Optional[Path] = None,
    *,
    schema_path: Optional[Path] = None,
) -> dict[str, Any]:
    """Validate the complete Experience Registry and build a trusted index.

    An existing readable empty experience root is structurally valid: it returns
    ``valid=True``, ``records_checked=0``, and an empty trusted ``index={}``.
    Application-level sufficiency (non-empty registry) is enforced separately.

    Returns a mapping with:
    - valid: True only when every discovered file passes all invariants
    - records_checked: number of discovered JSON files
    - index: experience_id -> record when valid; otherwise None
    - errors: list of machine-readable error dicts
    - discovered_paths: deterministic relative POSIX paths checked
    """
    root = (
        Path(experience_root)
        if experience_root is not None
        else DEFAULT_EXPERIENCE_ROOT
    )
    schema = Path(schema_path) if schema_path is not None else EXPERIENCE_SCHEMA_PATH

    result = _empty_result()

    if not root.exists():
        result["errors"].append(
            _error(
                "EXPERIENCE_ROOT_MISSING",
                path=str(root),
                detail="experience root directory does not exist",
            )
        )
        return result

    if not root.is_dir():
        result["errors"].append(
            _error(
                "EXPERIENCE_ROOT_NOT_DIRECTORY",
                path=str(root),
                detail="experience root path exists but is not a directory",
            )
        )
        return result

    files = discover_experience_files(root)
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
                    "EXPERIENCE_FILE_READ_ERROR",
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
                    "EXPERIENCE_JSON_DUPLICATE_KEY",
                    path=rel,
                    key=exc.key,
                    detail=f"duplicate JSON object key {exc.key!r}; no last-key-wins",
                )
            )
            continue
        except json.JSONDecodeError as exc:
            result["errors"].append(
                _error(
                    "EXPERIENCE_JSON_PARSE_ERROR",
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
                    "EXPERIENCE_UNSUPPORTED_RECORD_SHAPE",
                    path=rel,
                    detail=(
                        "experience JSON root must be a single record object; "
                        f"got {type(loaded).__name__}"
                    ),
                )
            )
            continue

        schema_errors = [error.message for error in validator.iter_errors(loaded)]
        if schema_errors:
            result["errors"].append(
                _error(
                    "EXPERIENCE_SCHEMA_INVALID",
                    path=rel,
                    experience_id=loaded.get("experience_id")
                    if isinstance(loaded.get("experience_id"), str)
                    else None,
                    details=schema_errors,
                )
            )

        experience_id = loaded.get("experience_id")
        if not isinstance(experience_id, str) or experience_id == "":
            continue

        if experience_id != stem:
            result["errors"].append(
                _error(
                    "EXPERIENCE_FILENAME_ID_MISMATCH",
                    path=rel,
                    experience_id=experience_id,
                    filename_stem=stem,
                    detail=(
                        f"filename stem {stem!r} must exactly equal "
                        f"experience_id {experience_id!r}"
                    ),
                )
            )

        if experience_id in first_path_by_id:
            result["errors"].append(
                _error(
                    "DUPLICATE_EXPERIENCE_ID",
                    experience_id=experience_id,
                    path=rel,
                    first_path=first_path_by_id[experience_id],
                    detail=(
                        f"experience_id {experience_id!r} appears in multiple files; "
                        "no last-write-wins"
                    ),
                )
            )
        else:
            first_path_by_id[experience_id] = rel
            provisional_index[experience_id] = loaded

    if result["errors"]:
        result["valid"] = False
        result["index"] = None
        return result

    ordered_index = {
        experience_id: provisional_index[experience_id]
        for experience_id in sorted(provisional_index.keys())
    }
    result["valid"] = True
    result["index"] = ordered_index
    return result


def load_validated_experience_repository(
    experience_root: Optional[Path] = None,
    *,
    schema_path: Optional[Path] = None,
) -> dict[str, Any]:
    """Alias for validate_experience_repository (load + validate + index)."""
    return validate_experience_repository(
        experience_root,
        schema_path=schema_path,
    )
