"""SUPERVISED_PRODUCTION_V1_SLICE_1: Gmail -> DiscoveryLead -> JOBS/LOG.

`process_batch` is the single deterministic entry point for this slice. It
never performs Gmail or Google Sheets I/O -- the supervised connector layer
supplies the bounded raw-message observations (already read from Gmail) and
the current JOBS/LOG state (already read from the Sheet), then applies the
returned mutation plan and persists `next_state` for the following run.

run_id and processed_at are supplied by the caller rather than generated here
so the deterministic core stays free of wall-clock/uuid nondeterminism.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

SRC_PATH = Path(__file__).resolve().parent
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from discovery_lead import MalformedMessageError, extract_discovery_leads  # noqa: E402
from production_ledger import build_mutation_plan, empty_state  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PRODUCTION_LEDGER_MUTATION_SCHEMA_PATH = (
    ROOT / "schemas" / "production_ledger_mutation.schema.json"
)


def _malformed_message_lead_id(raw_message: Any) -> str:
    """Stable processing identity for malformed input, independent of batch order."""
    if isinstance(raw_message, Mapping):
        source = raw_message.get("source")
        source_message_id = raw_message.get("source_message_id")
        if isinstance(source, str) and isinstance(source_message_id, str) and source_message_id.strip():
            material = f"MALFORMED|{source}|{source_message_id.strip()}"
            digest = hashlib.sha256(material.encode("utf-8")).hexdigest()[:16]
            return f"LEAD_{digest.upper()}"
    try:
        fingerprint = json.dumps(raw_message, sort_keys=True, default=str)
    except TypeError:
        fingerprint = repr(raw_message)
    digest = hashlib.sha256(f"MALFORMED|{fingerprint}".encode("utf-8")).hexdigest()[:16]
    return f"LEAD_{digest.upper()}"


def process_batch(
    raw_messages: Sequence[Mapping[str, Any]],
    existing_state: Mapping[str, Any] | None,
    *,
    run_id: str,
    processed_at: str,
) -> dict[str, Any]:
    """Process one Gmail alert batch into a validated JOBS/LOG mutation plan.

    Returns {"jobs_mutations": [...], "log_mutations": [...], "next_state": {...}}.
    """

    from schema_validation import build_draft202012_validator  # local import; avoids cycle at module load

    all_leads: list[dict[str, Any]] = []
    for ordinal, raw_message in enumerate(raw_messages):
        try:
            leads = extract_discovery_leads(raw_message)
        except MalformedMessageError as exc:
            source = raw_message.get("source") if isinstance(raw_message, Mapping) else None
            all_leads.append(
                {
                    "discovery_lead_id": _malformed_message_lead_id(raw_message),
                    "source": source if source in ("GMAIL",) else "GMAIL",
                    "source_message_id": (
                        raw_message.get("source_message_id")
                        if isinstance(raw_message, Mapping)
                        and isinstance(raw_message.get("source_message_id"), str)
                        else None
                    ),
                    "raw_status": "MALFORMED",
                    "error_code": exc.error_code,
                    "error_message": str(exc),
                }
            )
            continue
        all_leads.extend(leads)

    plan = build_mutation_plan(
        all_leads,
        existing_state if existing_state is not None else empty_state(),
        run_id=run_id,
        processed_at=processed_at,
    )

    validator = build_draft202012_validator(PRODUCTION_LEDGER_MUTATION_SCHEMA_PATH)
    validator.validate(
        {
            "jobs_mutations": plan["jobs_mutations"],
            "log_mutations": plan["log_mutations"],
        }
    )

    return plan
