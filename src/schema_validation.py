"""Shared Draft 2020-12 JSON Schema validation for pipeline records.

Always attaches the shared job-url FormatChecker from job_url_format so
tests and future production code cannot accidentally validate with a plain
FormatChecker() and silently skip job-url enforcement on job records.

URL acceptance rules remain defined only in job_url_format.py.

Local schema $ref resolution uses a registry of schemas under schemas/.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping, Union

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from job_url_format import build_job_format_checker


ROOT = Path(__file__).resolve().parents[1]
SCHEMAS_DIR = ROOT / "schemas"

SchemaInput = Union[Mapping[str, Any], Path, str]


def load_draft202012_schema(schema: SchemaInput) -> dict[str, Any]:
    """Load a schema mapping from a dict/mapping or JSON file path."""
    if isinstance(schema, Mapping):
        return dict(schema)

    path = Path(schema)
    with path.open(encoding="utf-8") as handle:
        loaded = json.load(handle)

    if not isinstance(loaded, dict):
        raise TypeError(
            f"JSON Schema at {path} must be an object, got {type(loaded).__name__}."
        )
    return loaded


@lru_cache(maxsize=1)
def build_local_schema_registry() -> Registry:
    """Register every schema under schemas/ by its canonical $id."""
    registry: Registry = Registry()
    if not SCHEMAS_DIR.is_dir():
        return registry

    for path in sorted(SCHEMAS_DIR.glob("*.json")):
        loaded = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(loaded, dict):
            continue
        schema_id = loaded.get("$id")
        if not isinstance(schema_id, str) or not schema_id.strip():
            continue
        registry = registry.with_resource(
            schema_id,
            Resource.from_contents(loaded),
        )
    return registry


def build_draft202012_validator(
    schema: SchemaInput,
    *,
    check_schema: bool = False,
) -> Draft202012Validator:
    """Build a Draft 2020-12 validator with shared job-url format enforcement.

    Parameters
    ----------
    schema:
        Schema object or path to a schema JSON file.
    check_schema:
        When True, also run Draft202012Validator.check_schema on the schema.
    """
    schema_obj = load_draft202012_schema(schema)

    if check_schema:
        Draft202012Validator.check_schema(schema_obj)

    return Draft202012Validator(
        schema_obj,
        format_checker=build_job_format_checker(),
        registry=build_local_schema_registry(),
    )
