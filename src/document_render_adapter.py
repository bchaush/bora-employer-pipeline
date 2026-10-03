"""Core adapter of CAREER_OS_DOCUMENT_RENDERING_CAPABILITY_V1.

The adapter is the parent process of the capability. It imports only the
standard library and the frozen evaluator src/resume_page_utilization.py; it
never imports pypdf, pdfminer.six or src/rendered_pdf_inspection.py, whose
bytes it only reads as ENTRY_BYTES and delivers to the inspection sandbox.

Implemented here, in STATUS_ORDER_V1 order: S1 DOCX pre-flight (UNTRUSTED
INPUT POLICY, DOCX_LIMITS_V1, PART_ALLOWLIST_V1); the S2 environment
verification interface (MANIFEST_PARTITION_V1, DIGEST_SPEC_V1,
CONTENT_BINDING_V1); the S3 source model (TEXT_NORMALIZATION_V1,
PARAGRAPH_IDENTITY_MODEL_V1, STYLE_NUMBERING_RESOLUTION_V1,
LIST_MARKER_MODEL_V1, FONT_CANONICALIZATION_V1 docx side,
HYPERLINK_OCCURRENCE_MODEL_V1 source side, structure map V1-V6); the S4 and
S5 sandbox argv and profile builders, the conversion argv, the per-run
temporary layout, the timeout and process-group model, PDF_BYTES_BINDING_V1
and ENTRY_DESCRIPTOR_BINDING_V1; CHILD_PROTOCOL_V1 parent validation with
EVIDENCE_CAP_RULE_V1, CHILD_FRAME_LIMITS_V1 and CHILD_PARENT_PARTITION_V1;
the parent-evaluated slots S8, S9.03-S9.05 and S10.06-S10.07; S11 payload,
findings and the frozen evaluator call; RENDER_SEMANTIC_FINGERPRINT_V1;
evidence assembly and validation; S12 delivery.

Every external effect (environment verification, sandbox self-tests, process
launches) is injected, so the same code paths run against fakes in the
hermetic tests. A run without a verified environment stops at S2.01.
"""

from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import math
import os
import re
import shutil
import stat
import struct
import subprocess
import sys
import tempfile
import threading
import unicodedata
import urllib.parse
import xml.etree.ElementTree as ET
import zipfile
import zlib
from decimal import ROUND_HALF_EVEN, Decimal, localcontext
from pathlib import Path

_SRC_DIR = Path(__file__).resolve().parent
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from resume_page_utilization import (  # noqa: E402
    MEANINGFUL_CONTENT_TYPES,
    evaluate_resume_page_utilization,
)

INSPECTION_ENTRY_PATH = _SRC_DIR / "rendered_pdf_inspection.py"
EVIDENCE_SCHEMA_PATH = _SRC_DIR.parent / "schemas" / "rendered_document_evidence.schema.json"

# Run statuses ---------------------------------------------------------------

STAGE_STATUSES = (
    # S1
    "RENDER_DOCX_LIMIT_EXCEEDED",
    "RENDER_DOCX_PACKAGE_INVALID",
    "RENDER_EMBEDDED_FONT_DENIED",
    "RENDER_EXTERNAL_REFERENCE_DENIED",
    "RENDER_MEDIA_TYPE_MISMATCH",
    "RENDER_EMBEDDED_VECTOR_DENIED",
    "RENDER_MEDIA_TYPE_UNSUPPORTED",
    # S2
    "RENDER_ENVIRONMENT_UNVERIFIED",
    "RENDER_CONTENT_BINDING_INCOMPLETE",
    "RENDER_CONTENT_BINDING_UNSUPPORTED_ENTRY",
    "RENDER_CONTENT_BINDING_MISMATCH",
    # S3
    "RENDER_TRACKED_CHANGES_PRESENT",
    "RENDER_TEXT_CONSTRUCT_UNSUPPORTED",
    "RENDER_ALTERNATE_CONTENT_UNSUPPORTED",
    "RENDER_FIELD_UNSUPPORTED",
    "RENDER_HIDDEN_TEXT_DETECTED",
    "RENDER_STYLE_CHAIN_UNSUPPORTED",
    "RENDER_LIST_RESOLUTION_UNSUPPORTED",
    "RENDER_LIST_NUMFMT_UNSUPPORTED",
    "RENDER_LIST_MARKER_UNSUPPORTED",
    "RENDER_LIST_MARKER_UNMAPPED",
    "RENDER_CASE_TRANSFORM_UNSUPPORTED",
    "RENDER_FONT_DECLARATION_UNMAPPED",
    "RENDER_LINK_SOURCE_CONSTRUCT_UNSUPPORTED",
    "RENDER_LINK_SOURCE_UNSUPPORTED",
    "RENDER_LINK_SOURCE_UNRESOLVED",
    "RENDER_LINK_URI_UNSUPPORTED",
    "RENDER_STRUCTURE_MAP_REQUIRED",
    "RENDER_STRUCTURE_MAP_INVALID",
    "RENDER_STRUCTURE_MAP_TEXT_MISMATCH",
    "RENDER_LIST_SEMANTICS_MISMATCH",
    "RENDER_STRUCTURE_MAP_INCOMPLETE",
    # S4
    "RENDER_ISOLATION_UNAVAILABLE",
    # S5
    "RENDER_TIMEOUT",
    "RENDER_SANDBOX_RUNTIME_INCOMPLETE",
    "RENDER_DOCUMENT_STATE_UNSUPPORTED",
    "RENDER_PDF_INSPECTION_FAILED",
    # S6
    "RENDER_COORDINATE_SPACE_UNVERIFIED",
    "RENDER_PAGE_ROTATION_DENIED",
    "RENDER_PAGEBOX_MISMATCH",
    "RENDER_PAGE_SIZE_UNSUPPORTED",
    # S7
    "RENDER_TEXT_STATE_UNOBSERVABLE",
    "RENDER_TEXT_POLICY_SUSPECT",
    "RENDER_ATTRIBUTION_INCOMPLETE",
    # S8
    "RENDER_LIST_MARKER_MISMATCH",
    "RENDER_TEXT_LOSS_DETECTED",
    # S9
    "RENDER_FONT_SUBSTITUTION_UNAPPROVED",
    "RENDER_FONT_TYPE3_DENIED",
    "RENDER_FONT_NOT_EMBEDDED",
    "RENDER_FONT_INVENTORY_MISMATCH",
    "RENDER_LIST_MARKER_FONT_UNAPPROVED",
    "RENDER_FONT_FACE_MISMATCH",
    # S10
    "RENDER_ANNOTATION_UNSUPPORTED",
    "RENDER_LINK_KIND_UNSUPPORTED",
    "RENDER_LINK_ATTRIBUTION_AMBIGUOUS",
    "RENDER_LINK_DESTINATION_SUBSTITUTED",
    "RENDER_LINK_ORDER_MISMATCH",
    "RENDER_LINK_MISSING",
    "RENDER_LINK_FABRICATED",
    # S11
    "RENDER_QA_AUTOMATED_PASS_HUMAN_REVIEW_REQUIRED",
    "RENDER_QA_AUTOMATED_FAILED",
    # S12
    "RENDER_DELIVERY_BYTES_MISMATCH",
)
OUT_OF_PIPELINE_STATUSES = (
    "RENDER_NONDETERMINISTIC",
    "RENDER_FONT_MANIFEST_INCOMPLETE",
    "RENDER_FONT_VARIABLE_DENIED",
    "RENDER_DEPENDENCY_LOCK_REJECTED",
)
RUN_STATUSES = STAGE_STATUSES + OUT_OF_PIPELINE_STATUSES

STATUS_PASS = "RENDER_QA_AUTOMATED_PASS_HUMAN_REVIEW_REQUIRED"
STATUS_QA_FAILED = "RENDER_QA_AUTOMATED_FAILED"

# Contract-fixed values ------------------------------------------------------

DOCX_LIMITS_V1 = {
    "max_input_bytes": 10485760,
    "max_entries": 512,
    "max_entry_uncompressed_bytes": 20971520,
    "max_total_uncompressed_bytes": 52428800,
    "max_compression_ratio": 100,
    "max_xml_part_bytes": 8388608,
    "max_xml_depth": 64,
    "max_xml_elements": 1000000,
}

# Identical to INSPECTION_LIMITS_V1 of the inspection entry; the hermetic
# tests compare the two literals without importing the entry.
INSPECTION_LIMITS_V1 = {
    "inspection_max_pdf_bytes": 16777216,
    "inspection_max_pages": 50,
    "inspection_max_chars_per_page": 50000,
    "inspection_timeout_seconds": 120,
    "inspection_memory_limit_bytes": 2147483648,
    "inspection_max_annots_array_length": 1024,
    "inspection_max_link_annotations_per_page": 512,
    "inspection_max_uri_bytes": 2048,
    "inspection_max_dest_array_length": 16,
    "inspection_max_resource_dict_entries": 256,
    "inspection_max_fonts_per_page": 64,
    "inspection_max_content_streams_per_page": 256,
    "inspection_max_catalog_keys": 256,
    "inspection_max_decoded_content_bytes_per_page": 2097152,
    "inspection_max_decoded_content_bytes_per_document": 16777216,
    "inspection_max_decoded_other_stream_bytes_per_document": 16777216,
    "inspection_max_content_operators_per_page": 250000,
    "inspection_max_content_operators_per_document": 1000000,
    "inspection_max_traversal_operations": 1000000,
    "inspection_max_info_keys": 64,
    "inspection_max_indirect_resolutions": 1000000,
    "inspection_max_evidence_bytes": 33554432,
}

CHILD_FRAME_LIMITS_V1 = {
    "child_max_json_depth": 16,
    "child_max_array_elements": 4000000,
    "child_max_object_members": 64,
    "child_max_frame_elements": 8000000,
    "child_max_string_bytes": 4096,
    "child_max_integer_digits": 20,
    "child_max_frame_bytes": INSPECTION_LIMITS_V1["inspection_max_evidence_bytes"],
    "child_fail_frame_max_bytes": 3342,
}
FAIL_FRAME_RESERVE_BYTES = 3342
FINAL_FRAME_MAX_BYTES = 1024
FD_STATE_MAX_ENTRIES = 4
FAIL_EVIDENCE_STRING_MAX_BYTES = 256
FAIL_EXCEPTION_CLASS_UNREPRESENTABLE = "<UNREPRESENTABLE>"
FORM_DEPTH_MAX = 8

TEXT_OVERLAP_RATIO_NUMERATOR = 1
TEXT_OVERLAP_RATIO_DENOMINATOR = 4
OVERFLOW_EPSILON = Decimal("0.01")
DUPLICATE_RECT_TOLERANCE = Decimal("0.5")
UTILIZATION_FLOOR = 0.92
BORDERLINE_CEILING = 0.93

SPEC_IDS_V1 = {
    "geometry_spec_id": "PAGE_GEOMETRY_SPEC_V1",
    "text_normalization_spec_id": "TEXT_NORMALIZATION_V1",
    "quantization_spec_id": "COORDINATE_QUANTIZATION_V1",
    "font_inventory_record_spec_id": "FONT_INVENTORY_RECORD_V1",
    "annotation_record_spec_id": "ANNOTATION_RECORD_V1",
}

PDF_EXPORT_OPTIONS_V1 = {
    "ExportBookmarks": ("boolean", "false"),
    "ExportBookmarksToPDFDestination": ("boolean", "false"),
    "ExportNotes": ("boolean", "false"),
    "ExportNotesPages": ("boolean", "false"),
    "ExportFormFields": ("boolean", "false"),
    "ExportPlaceholders": ("boolean", "false"),
    "ExportLinksRelativeFsys": ("boolean", "false"),
    "ConvertOOoTargetToPDFTarget": ("boolean", "false"),
    "UseTaggedPDF": ("boolean", "false"),
    "PDFUACompliance": ("boolean", "false"),
    "Linearize": ("boolean", "false"),
    "Encrypt": ("boolean", "false"),
    "EmbedStandardFonts": ("boolean", "true"),
    "ReduceImageResolution": ("boolean", "false"),
    "SelectPdfVersion": ("long", "0"),
    "OpenBookmarkLevels": ("long", "-1"),
    "AllowDuplicateFieldNames": ("boolean", "false"),
}

REQUIRED_SANDBOX_FLAGS = (
    "--unshare-net",
    "--unshare-pid",
    "--unshare-ipc",
    "--unshare-uts",
    "--new-session",
    "--die-with-parent",
    "--cap-drop",
    "ALL",
)
RENDER_ENV_NAMES = ("HOME", "TMPDIR", "PATH", "LANG", "LC_ALL", "TZ", "SOURCE_DATE_EPOCH", "FONTCONFIG_FILE")
INSPECTION_ENV_NAMES = ("HOME", "TMPDIR", "PATH", "LANG", "LC_ALL", "TZ", "SOURCE_DATE_EPOCH")
SANDBOX_TMP_PATH = "/tmp"
RUN_INPUT_PLACEHOLDER = "<RUN_INPUT_DIR>"
RUN_OUTPUT_PLACEHOLDER = "<RUN_OUTPUT_DIR>"
RUN_PROFILE_PLACEHOLDER = "<RUN_PROFILE_DIR>"
ENTRY_FD_PLACEHOLDER = "<ENTRY_FD>"
SANDBOX_INPUT_DIR = "/sandbox/input"
SANDBOX_OUTPUT_DIR = "/sandbox/output"
SANDBOX_PROFILE_DIR = "/sandbox/profile"
SANDBOX_ENTRY_PATH = "/entry/inspection_entry.py"
INPUT_FILE_NAME = "input.docx"
OUTPUT_FILE_NAME = "input.pdf"
DELIVERED_PDF_NAME = "rendered.pdf"
EXPECTED_UNREACHABLE_ERRNOS_V1 = {
    "AF_INET": ("ENETUNREACH",),
    "AF_INET6": ("ENETUNREACH", "EADDRNOTAVAIL", "EAFNOSUPPORT"),
}
ABSENT_ROOT_DIGEST = "08b6a0bc6906cd596f1458be5ac2911c478709b27e4f3c52e8edd0293e2f4c56"

CHILD_STAGES = ("S5.02", "S5.03", "S6", "S7", "S9", "S10")

MANIFEST_PRE_PROVISION_KEYS = (
    "annotation_record_spec_id", "apt_plan", "artifact_targets", "bubblewrap_version",
    "dependency_lock_review", "dependency_model", "docx_limits", "extraction_spec",
    "font_inventory_record_spec_id", "geometry_spec_id", "installer_pip_package_path",
    "installer_pip_package_tree_digest", "installer_pip_version", "libreoffice_version", "locale",
    "lock_artifacts", "lock_review_digest", "operator_base_interpreter", "operator_python_prefix",
    "pdf_export_filter", "pdfminer_six_version", "provisioning_script_path",
    "provisioning_script_sha256", "pypdf_version", "quantization_spec_id",
    "sandbox_capability_mechanism", "sandbox_flags", "sandbox_forbidden_canary_paths",
    "sandbox_tmpfs_paths", "sandbox_tmpfs_size_bytes", "source_date_epoch", "temp_root_policy",
    "text_normalization_spec_id", "text_overlap_ratio_denominator",
    "text_overlap_ratio_numerator", "timeout_seconds", "timezone", "verifier_path",
    "verifier_sha256",
)
MANIFEST_POST_PROVISION_KEYS = (
    "approved_plan_digest", "approved_substitutions", "apt_installed_delta",
    "apt_preinstall_snapshot", "apt_source_record", "canonical_families", "content_binding",
    "docx_family_to_canonical", "fontconfig_file", "manifest_self_digest", "marker_glyph_map",
    "pdf_basefont_to_canonical", "pdfminer_type0_name_form", "sandbox_dirs",
    "sandbox_expected_unreachable_errnos", "sandbox_path", "sandbox_probe_interpreter_path",
    "sandbox_read_only_paths", "sandbox_symlinks",
)
MANIFEST_SET_KEYS = (
    "sandbox_read_only_paths", "sandbox_dirs", "sandbox_tmpfs_paths",
    "sandbox_forbidden_canary_paths", "canonical_families",
)

# Namespaces (expanded-name matching only) -----------------------------------

NS_W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS_R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
NS_A = "http://schemas.openxmlformats.org/drawingml/2006/main"
NS_MC = "http://schemas.openxmlformats.org/markup-compatibility/2006"
NS_V = "urn:schemas-microsoft-com:vml"
NS_O = "urn:schemas-microsoft-com:office:office"
NS_WPS = "http://schemas.microsoft.com/office/word/2010/wordprocessingShape"
NS_XLINK = "http://www.w3.org/1999/xlink"
NS_CT = "http://schemas.openxmlformats.org/package/2006/content-types"
NS_PR = "http://schemas.openxmlformats.org/package/2006/relationships"
STRICT_NAMESPACE_PREFIX = b"http://purl.oclc.org/ooxml/"


def w(local: str) -> str:
    return "{" + NS_W + "}" + local


def r_attr(local: str) -> str:
    return "{" + NS_R + "}" + local


REL_TYPE_OFFICE_DOCUMENT = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument"
CONTENT_TYPES_PART = "[Content_Types].xml"
MAIN_PART = "word/document.xml"

ALLOWED_CONTENT_TYPES_V1 = frozenset(
    (
        "application/vnd.openxmlformats-package.relationships+xml",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.numbering+xml",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.settings+xml",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.fonttable+xml",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.websettings+xml",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.header+xml",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.footnotes+xml",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.endnotes+xml",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.comments+xml",
        "application/vnd.openxmlformats-officedocument.theme+xml",
        "application/vnd.openxmlformats-package.core-properties+xml",
        "application/vnd.openxmlformats-officedocument.extended-properties+xml",
        "image/png",
        "image/jpeg",
        "image/gif",
    )
)
STORY_CONTENT_TYPES = frozenset(
    "application/vnd.openxmlformats-officedocument.wordprocessingml." + suffix + "+xml"
    for suffix in ("header", "footer", "footnotes", "endnotes", "comments")
)
CT_STYLES = "application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"
CT_NUMBERING = "application/vnd.openxmlformats-officedocument.wordprocessingml.numbering+xml"
CT_THEME = "application/vnd.openxmlformats-officedocument.theme+xml"
CT_SETTINGS = "application/vnd.openxmlformats-officedocument.wordprocessingml.settings+xml"


# Outcomes -------------------------------------------------------------------


class Outcome:
    """One STATUS_ORDER_V1 result: a status with its reason, detail and slot."""

    __slots__ = ("status", "reason", "detail", "slot", "evidence")

    def __init__(self, status, reason=None, detail=None, slot=None, evidence=None):
        self.status = status
        self.reason = reason
        self.detail = detail
        self.slot = slot
        self.evidence = evidence if evidence is not None else {}

    def as_dict(self) -> dict:
        return {
            "status": self.status,
            "reason": self.reason,
            "detail": self.detail,
            "slot": self.slot,
            "evidence": self.evidence,
        }

    def triple(self) -> tuple:
        return (self.status, self.reason, self.detail)

    def __repr__(self) -> str:
        return "Outcome(%r, %r, %r, slot=%r)" % (self.status, self.reason, self.detail, self.slot)


class StageFailure(Exception):
    def __init__(self, outcome: Outcome) -> None:
        super().__init__(outcome.status, outcome.reason, outcome.detail)
        self.outcome = outcome


def fail(status, reason=None, detail=None, slot=None, **evidence):
    raise StageFailure(Outcome(status, reason, detail, slot, evidence))


# Canonical JSON and digests (DIGEST_SPEC_V1) ---------------------------------


def canonical_json_bytes(value) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode("utf-8")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_digest(value) -> str:
    return sha256_hex(canonical_json_bytes(value))


class DuplicateKeyError(ValueError):
    pass


class NonFiniteError(ValueError):
    pass


def _reject_duplicates(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateKeyError(key)
        result[key] = value
    return result


def _reject_constant(name):
    raise NonFiniteError(name)


def strict_json_loads(text: str):
    """Strict JSON: duplicate keys at any depth and NaN/Infinity are rejected."""
    return json.loads(text, object_pairs_hook=_reject_duplicates, parse_constant=_reject_constant)


def _contains_non_integer_number(value) -> bool:
    pending = [value]
    while pending:
        item = pending.pop()
        if isinstance(item, bool) or isinstance(item, float):
            return True
        if isinstance(item, dict):
            pending.extend(item.values())
        elif isinstance(item, list):
            pending.extend(item)
    return False


# TEXT_NORMALIZATION_V1 --------------------------------------------------------

DELETED_CHARACTERS = frozenset("\u00ad\u200b\u200c\u200d\u2060\ufeff")
SEPARATOR_CHARACTERS = frozenset(
    "\t\n\r\x0b\x0c \u00a0\u1680\u2028\u2029\u202f\u205f\u3000"
    + "".join(chr(code) for code in range(0x2000, 0x200B))
)


def normalize_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text)
    normalized = "".join(ch for ch in normalized if ch not in DELETED_CHARACTERS)
    return normalized.replace("\u2010", "-").replace("\u2011", "-")


def tokenize(text: str) -> list:
    tokens = []
    current = []
    for ch in normalize_text(text):
        if ch in SEPARATOR_CHARACTERS:
            if current:
                tokens.append("".join(current))
                current = []
        else:
            current.append(ch)
    if current:
        tokens.append("".join(current))
    return tokens


def is_counted_text(text: str) -> bool:
    """A character text is COUNTED when it holds a code point that is neither
    a separator nor a deleted character."""
    return any(ch not in SEPARATOR_CHARACTERS and ch not in DELETED_CHARACTERS for ch in text)


# URI_CANONICALIZATION_V1 ----------------------------------------------------

_PCT_TRIPLET = re.compile(r"%([0-9A-Fa-f]{2})")
_UNRESERVED = frozenset("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~")
_SCHEME_PREFIX = re.compile(r"^([A-Za-z][A-Za-z0-9+.\-]*):")


def _percent_rule(text: str) -> str:
    def replace(match):
        character = chr(int(match.group(1), 16))
        if character in _UNRESERVED:
            return character
        return "%" + match.group(1).upper()

    return _PCT_TRIPLET.sub(replace, text)


def canonicalize_uri(raw):
    """The canonical string, or None when RENDER_LINK_URI_UNSUPPORTED."""
    if not isinstance(raw, str) or raw == "":
        return None
    for ch in raw:
        code = ord(ch)
        if unicodedata.category(ch) == "Cc" or ch == " " or ch == "\\":
            return None
        if 0xD800 <= code <= 0xDFFF:
            return None
    if raw != raw.strip():
        return None
    try:
        parts = urllib.parse.urlsplit(raw)
    except ValueError:
        return None
    scheme = parts.scheme.lower()
    if scheme not in ("http", "https", "mailto"):
        return None
    if scheme == "mailto":
        return "mailto:" + _percent_rule(raw[len(parts.scheme) + 1:])
    prefix = scheme + "://"
    if raw[:len(prefix)].lower() != prefix:
        return None
    netloc = parts.netloc
    if "@" in netloc or "[" in netloc or "]" in netloc:
        return None
    try:
        parts.port
        hostname = parts.hostname
    except ValueError:
        return None
    host_text, port_text = netloc, None
    if ":" in netloc:
        host_text, port_text = netloc.rsplit(":", 1)
    if host_text == "" or hostname is None or not host_text.isascii():
        return None
    port = None
    if port_text is not None:
        if port_text == "" or not port_text.isdigit():
            return None
        port = int(port_text)
        if not 1 <= port <= 65535:
            return None
        if (scheme, port) in (("http", 80), ("https", 443)):
            port = None
    rest = raw[len(prefix) + len(netloc):]
    if rest == "" or rest[0] in "?#":
        rest = "/" + rest
    authority = host_text.lower() + ("" if port is None else ":" + str(port))
    return scheme + "://" + _percent_rule(authority) + _percent_rule(rest)


def uri_scheme_allowed(target: str) -> bool:
    match = _SCHEME_PREFIX.match(target.strip())
    return bool(match) and match.group(1).lower() in ("http", "https", "mailto")


# COORDINATE_QUANTIZATION_V1 and NUMERIC_NORMALIZATION_V1 ----------------------


def numeric(value) -> float:
    """NUMERIC_NORMALIZATION_V1 for parent-side values: a real number other
    than bool, converted once to a finite binary64; ValueError otherwise."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("not a real number")
    converted = float(value)
    if not math.isfinite(converted):
        raise ValueError("non-finite")
    return converted


def quantize(value) -> int:
    converted = numeric(value)
    with localcontext() as context:
        context.prec = 100
        return int((Decimal(converted) * 10).to_integral_value(rounding=ROUND_HALF_EVEN))


# FAIL_EVIDENCE_STRING_V1 grammar (parent-side check) ---------------------------

_FAIL_STRING_PATTERN = re.compile(r"^(?:[\x20-\x21\x23-\x24\x26-\x5b\x5d-\x7e]|%[0-9A-F]{2})*(?:%~)?\Z")
_IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,63}\Z")


def fail_string_valid(value) -> bool:
    return (
        isinstance(value, str)
        and len(value) <= FAIL_EVIDENCE_STRING_MAX_BYTES
        and _FAIL_STRING_PATTERN.match(value) is not None
    )


def exception_class_valid(value) -> bool:
    return isinstance(value, str) and (
        value == FAIL_EXCEPTION_CLASS_UNREPRESENTABLE or _IDENTIFIER_PATTERN.match(value) is not None
    )


# =============================================================================
# S1 DOCX PRE-FLIGHT
# =============================================================================

_SIG_LOCAL = b"PK\x03\x04"
_SIG_CENTRAL = b"PK\x01\x02"
_SIG_EOCD = b"PK\x05\x06"
_SIG_ZIP64_LOCATOR = b"PK\x06\x07"
_SIG_DESCRIPTOR = b"PK\x07\x08"
_PERMITTED_FLAG_BITS = (1 << 1) | (1 << 2) | (1 << 3) | (1 << 11)


class ZipEntry:
    __slots__ = (
        "index", "name_bytes", "name", "version_made_by", "flags", "method", "crc",
        "compressed_size", "uncompressed_size", "external_attr", "local_offset",
        "disk_start", "data_start", "is_directory",
    )

    def __init__(self) -> None:
        self.name = None
        self.data_start = None
        self.is_directory = False


def _s1(status, reason, detail=None, **evidence):
    fail(status, reason, detail, "S1", **evidence)


def _package_invalid(reason, detail=None, slot="S1.03", **evidence):
    fail("RENDER_DOCX_PACKAGE_INVALID", reason, detail, slot, **evidence)


def _limit_exceeded(reason, slot, **evidence):
    fail("RENDER_DOCX_LIMIT_EXCEEDED", reason, None, slot, **evidence)


def _parse_central_directory(data: bytes):
    """ZIP-1. Returns (entries, cd_offset)."""
    size = len(data)
    window_start = max(0, size - 65557)
    window = data[window_start:]
    positions = []
    search = 0
    while True:
        found = window.find(_SIG_EOCD, search)
        if found < 0:
            break
        positions.append(window_start + found)
        search = found + 1
    if not positions:
        _package_invalid("NOT_ZIP_OR_CORRUPT", slot="S1.02")
    eocd = positions[-1]
    if eocd + 22 > size:
        _package_invalid("NOT_ZIP_OR_CORRUPT", slot="S1.02")
    (disk, cd_disk, entries_disk, entries_total, cd_size, cd_offset, comment_length) = struct.unpack(
        "<HHHHIIH", data[eocd + 4: eocd + 22]
    )
    zip64 = eocd >= 20 and data[eocd - 20: eocd - 16] == _SIG_ZIP64_LOCATOR
    zip64 = zip64 or 0xFFFF in (disk, cd_disk, entries_disk, entries_total)
    zip64 = zip64 or 0xFFFFFFFF in (cd_size, cd_offset)
    if not zip64 and cd_offset + cd_size <= size:
        cursor = cd_offset
        end = min(cd_offset + cd_size, size)
        while cursor + 46 <= end and data[cursor: cursor + 4] == _SIG_CENTRAL:
            fields = struct.unpack("<HHHHHHIIIHHHHHII", data[cursor + 4: cursor + 46])
            if 0xFFFFFFFF in (fields[7], fields[8], fields[15]) or fields[12] == 0xFFFF:
                zip64 = True
                break
            cursor += 46 + fields[9] + fields[10] + fields[11]
    if zip64:
        _package_invalid("UNSUPPORTED_ZIP_FEATURE", "ZIP64")
    if len(positions) != 1:
        _package_invalid("EOCD_AMBIGUOUS")
    if eocd + 22 + comment_length != size:
        _package_invalid("EOCD_TRAILING_DATA")
    if disk != 0 or cd_disk != 0 or entries_disk != entries_total:
        _package_invalid("MULTI_DISK")
    if cd_offset + cd_size != eocd:
        _package_invalid("CD_EXTENT_MISMATCH")
    entries = []
    cursor = cd_offset
    while cursor < eocd:
        if cursor + 46 > eocd or data[cursor: cursor + 4] != _SIG_CENTRAL:
            _package_invalid("CD_EXTENT_MISMATCH")
        fields = struct.unpack("<HHHHHHIIIHHHHHII", data[cursor + 4: cursor + 46])
        record_length = 46 + fields[9] + fields[10] + fields[11]
        if cursor + record_length > eocd:
            _package_invalid("CD_EXTENT_MISMATCH")
        entry = ZipEntry()
        entry.index = len(entries)
        entry.version_made_by = fields[0]
        entry.flags = fields[2]
        entry.method = fields[3]
        entry.crc = fields[6]
        entry.compressed_size = fields[7]
        entry.uncompressed_size = fields[8]
        entry.disk_start = fields[12]
        entry.external_attr = fields[14]
        entry.local_offset = fields[15]
        entry.name_bytes = data[cursor + 46: cursor + 46 + fields[9]]
        entries.append(entry)
        cursor += record_length
    if cursor != eocd:
        _package_invalid("CD_EXTENT_MISMATCH")
    if len(entries) != entries_total:
        _package_invalid("EOCD_COUNT_MISMATCH")
    offsets = set()
    names = set()
    for entry in entries:
        if entry.local_offset in offsets or entry.name_bytes in names:
            _package_invalid("DUPLICATE_ENTRY", index=entry.index)
        offsets.add(entry.local_offset)
        names.add(entry.name_bytes)
    return entries, cd_offset


def _check_local_headers(data: bytes, entries: list) -> None:
    """ZIP-2, reasons in listed order."""
    headers = {}
    for entry in entries:
        offset = entry.local_offset
        if offset + 30 > len(data) or data[offset: offset + 4] != _SIG_LOCAL:
            _package_invalid("LOCAL_CENTRAL_NAME_MISMATCH", index=entry.index)
        fields = struct.unpack("<HHHHHIIIHH", data[offset + 4: offset + 30])
        name = data[offset + 30: offset + 30 + fields[8]]
        if name != entry.name_bytes:
            _package_invalid("LOCAL_CENTRAL_NAME_MISMATCH", index=entry.index)
        headers[entry.index] = fields
        entry.data_start = offset + 30 + fields[8] + fields[9]
    for entry in entries:
        fields = headers[entry.index]
        if fields[1] != entry.flags or fields[2] != entry.method:
            _package_invalid("LOCAL_CENTRAL_FIELD_MISMATCH", index=entry.index)
        if not entry.flags & (1 << 3):
            if (fields[5], fields[6], fields[7]) != (entry.crc, entry.compressed_size, entry.uncompressed_size):
                _package_invalid("LOCAL_CENTRAL_FIELD_MISMATCH", index=entry.index)


def _check_tiling(data: bytes, entries: list, cd_offset: int) -> None:
    """ZIP-3 exact tiling of [0, cd_offset)."""
    ordered = sorted(entries, key=lambda item: item.local_offset)
    expected = 0
    for entry in ordered:
        if entry.local_offset != expected:
            _package_invalid("OVERLAPPING_OR_HIDDEN_DATA", index=entry.index)
        end = entry.data_start + entry.compressed_size
        if entry.flags & (1 << 3):
            if data[end: end + 4] == _SIG_DESCRIPTOR:
                values = data[end + 4: end + 16]
                descriptor_length = 16
            else:
                values = data[end: end + 12]
                descriptor_length = 12
            if len(values) != 12 or struct.unpack("<III", values) != (
                entry.crc, entry.compressed_size, entry.uncompressed_size
            ):
                _package_invalid("OVERLAPPING_OR_HIDDEN_DATA", index=entry.index)
            end += descriptor_length
        expected = end
    if expected != cd_offset:
        _package_invalid("OVERLAPPING_OR_HIDDEN_DATA")


def _check_methods_and_types(entries: list) -> None:
    """ZIP-4 then ZIP-5."""
    for entry in entries:
        if entry.method not in (0, 8):
            _package_invalid("UNSUPPORTED_ZIP_FEATURE", "METHOD", index=entry.index)
        if entry.flags & ~_PERMITTED_FLAG_BITS & 0xFFFF:
            _package_invalid("UNSUPPORTED_ZIP_FEATURE", "FLAGS", index=entry.index)
        if entry.method == 0 and entry.flags & 0b110:
            _package_invalid("UNSUPPORTED_ZIP_FEATURE", "FLAGS", index=entry.index)
    for entry in entries:
        if entry.version_made_by >> 8 == 3:
            file_type = (entry.external_attr >> 16) & 0o170000
            if file_type not in (0, 0o100000, 0o040000):
                _package_invalid("UNSUPPORTED_ENTRY_TYPE", index=entry.index)


def name_key1(name: str) -> str:
    return unicodedata.normalize("NFKC", name).casefold()


def name_key2(name: str) -> str:
    return unicodedata.normalize("NFKC", urllib.parse.unquote(name)).casefold()


def _check_names(entries: list) -> None:
    """NAME-1 to NAME-4 (S1.04)."""
    for entry in entries:
        try:
            if entry.flags & (1 << 11):
                entry.name = entry.name_bytes.decode("utf-8")
            else:
                if not entry.name_bytes.isascii():
                    raise UnicodeDecodeError("ascii", entry.name_bytes, 0, 1, "non-ascii")
                entry.name = entry.name_bytes.decode("ascii")
        except UnicodeDecodeError:
            _package_invalid("NAME_ENCODING", slot="S1.04", index=entry.index)
    for entry in entries:
        name = entry.name
        body = name
        if name.endswith("/") and entry.uncompressed_size == 0 and entry.compressed_size == 0:
            entry.is_directory = True
            body = name[:-1]
        unsafe = (
            name == ""
            or name.startswith("/")
            or "\\" in name
            or any(ord(ch) < 0x20 for ch in name)
            or re.match(r"^[A-Za-z]:", name) is not None
            or any(segment in ("", ".", "..") for segment in body.split("/"))
        )
        if unsafe:
            _package_invalid("UNSAFE_PATH", slot="S1.04", index=entry.index)
    seen1 = {}
    seen2 = {}
    for entry in entries:
        key1 = name_key1(entry.name.rstrip("/") if entry.is_directory else entry.name)
        key2 = name_key2(entry.name.rstrip("/") if entry.is_directory else entry.name)
        if key1 in seen1 or key2 in seen2 or key2 in seen1 or key1 in seen2:
            _package_invalid("DUPLICATE_OR_COLLIDING_NAME", slot="S1.04", index=entry.index)
        seen1[key1] = entry
        seen2[key2] = entry
    if sum(1 for entry in entries if entry.name == CONTENT_TYPES_PART) != 1:
        _package_invalid("CONTENT_TYPES_PART", slot="S1.04")


def _check_declared_limits(entries: list) -> None:
    """S1.05 on declared sizes, reasons in listed order."""
    limits = DOCX_LIMITS_V1
    if len(entries) > limits["max_entries"]:
        _limit_exceeded("ENTRIES", "S1.05", count=len(entries))
    for entry in entries:
        if entry.uncompressed_size > limits["max_entry_uncompressed_bytes"]:
            _limit_exceeded("ENTRY_BYTES", "S1.05", index=entry.index)
    if sum(entry.uncompressed_size for entry in entries) > limits["max_total_uncompressed_bytes"]:
        _limit_exceeded("TOTAL_BYTES", "S1.05")
    for entry in entries:
        if _ratio_exceeded(entry.uncompressed_size, entry.compressed_size):
            _limit_exceeded("RATIO", "S1.05", index=entry.index)


def _ratio_exceeded(uncompressed: int, compressed: int) -> bool:
    if compressed == 0:
        return uncompressed != 0
    return uncompressed > DOCX_LIMITS_V1["max_compression_ratio"] * compressed


class DocxPackage:
    """The pre-flighted package: entries by name, content types, relationships
    and the XML parts parsed under xml_part_checks_v1."""

    def __init__(self, data: bytes, entries: list) -> None:
        self.data = data
        self.entries = entries
        self.files = {entry.name: entry for entry in entries if not entry.is_directory}
        self.by_key1 = {name_key1(name): name for name in self.files}
        self.content_types = {}
        self.relationships = {}
        self.rels_source = {}
        self.xml = {}
        self.bytes_cache = {}

    def read(self, name: str, slot: str) -> bytes:
        """Bounded streaming read of an entry; the actual size must equal the
        declared size (xml_part_checks_v1 (a))."""
        if name in self.bytes_cache:
            return self.bytes_cache[name]
        entry = self.files[name]
        cap = DOCX_LIMITS_V1["max_entry_uncompressed_bytes"]
        raw = self.data[entry.data_start: entry.data_start + entry.compressed_size]
        if entry.method == 0:
            content = raw
        else:
            decompressor = zlib.decompressobj(-15)
            try:
                content = decompressor.decompress(raw, cap + 1)
            except zlib.error:
                _package_invalid("NOT_ZIP_OR_CORRUPT", slot=slot, part=name)
            if len(content) <= cap and (not decompressor.eof or decompressor.unused_data):
                _package_invalid("NOT_ZIP_OR_CORRUPT", slot=slot, part=name)
        if len(content) > cap or len(content) != entry.uncompressed_size:
            _limit_exceeded("ENTRY_BYTES", slot, part=name, actual=len(content))
        if _ratio_exceeded(len(content), entry.compressed_size):
            _limit_exceeded("RATIO", slot, part=name)
        if (zlib.crc32(content) & 0xFFFFFFFF) != entry.crc:
            _package_invalid("NOT_ZIP_OR_CORRUPT", slot=slot, part=name)
        self.bytes_cache[name] = content
        return content

    def resolve_entry(self, name: str):
        return self.by_key1.get(name_key1(name))

    def owning_rels(self, part: str) -> str:
        directory, _, base = part.rpartition("/")
        return (directory + "/" if directory else "") + "_rels/" + base + ".rels"

    def relationships_of(self, part: str) -> list:
        return self.relationships.get(self.owning_rels(part), [])


def xml_part_checks(package: DocxPackage, name: str, slot: str, main: bool = False):
    """xml_part_checks_v1 (a) to (h); returns the parsed root."""
    if name in package.xml:
        return package.xml[name]
    content = package.read(name, slot)
    limits = DOCX_LIMITS_V1
    if len(content) > limits["max_xml_part_bytes"]:
        _limit_exceeded("XML_BYTES", slot, part=name)
    if b"<!DOCTYPE" in content or b"<!ENTITY" in content:
        _package_invalid("DTD_OR_ENTITY", slot=slot, part=name)
    if content.startswith((b"\xfe\xff", b"\xff\xfe", b"\x00\x00\xfe\xff")):
        _package_invalid("XML_ENCODING", slot=slot, part=name)
    declaration = re.match(rb"^(?:\xef\xbb\xbf)?<\?xml[^>]*?encoding\s*=\s*[\"']([^\"']*)[\"']", content)
    if declaration and declaration.group(1).lower() not in (b"utf-8", b"utf8"):
        _package_invalid("XML_ENCODING", slot=slot, part=name)
    try:
        root = ET.fromstring(content)
    except ET.ParseError:
        _package_invalid("XML_MALFORMED", slot=slot, part=name)
    depth_exceeded = False
    count = 0
    pending = [(root, 1)]
    while pending:
        element, depth = pending.pop()
        count += 1
        if depth > limits["max_xml_depth"]:
            depth_exceeded = True
            break
        pending.extend((child, depth + 1) for child in element)
    if depth_exceeded:
        _limit_exceeded("XML_DEPTH", slot, part=name)
    if count > limits["max_xml_elements"]:
        _limit_exceeded("XML_ELEMENTS", slot, part=name)
    if STRICT_NAMESPACE_PREFIX in content or (main and root.tag != w("document")):
        _package_invalid("STRICT_OR_UNKNOWN_NAMESPACE", slot=slot, part=name)
    package.xml[name] = root
    return root


def _extension(name: str) -> str:
    base = name.rpartition("/")[2]
    if "." not in base:
        return ""
    return base.rpartition(".")[2].casefold()


def _check_content_types(package: DocxPackage) -> None:
    """S1.06: xml_part_checks_v1 then CT-1 to CT-4."""
    root = xml_part_checks(package, CONTENT_TYPES_PART, "S1.06")
    defaults = {}
    overrides = {}
    if root.tag != "{%s}Types" % NS_CT:
        _package_invalid("CONTENT_TYPES_INVALID", "ROOT", slot="S1.06")
    for child in root:
        if child.tag == "{%s}Default" % NS_CT:
            extension = child.get("Extension")
            value = child.get("ContentType")
            if extension is None or value is None:
                _package_invalid("CONTENT_TYPES_INVALID", "ATTRIBUTE", slot="S1.06")
            key = extension.casefold()
            if key in defaults:
                _package_invalid("CONTENT_TYPES_INVALID", "DUPLICATE_DEFAULT_OR_OVERRIDE", slot="S1.06")
            defaults[key] = value
        elif child.tag == "{%s}Override" % NS_CT:
            part = child.get("PartName")
            value = child.get("ContentType")
            if part is None or value is None:
                _package_invalid("CONTENT_TYPES_INVALID", "ATTRIBUTE", slot="S1.06")
            key = name_key1(part[1:] if part.startswith("/") else part)
            if key in overrides:
                _package_invalid("CONTENT_TYPES_INVALID", "DUPLICATE_DEFAULT_OR_OVERRIDE", slot="S1.06")
            overrides[key] = value
        else:
            _package_invalid("CONTENT_TYPES_INVALID", "ELEMENT", slot="S1.06")
    for key in overrides:
        if key not in package.by_key1:
            _package_invalid("CONTENT_TYPES_INVALID", "OVERRIDE_TARGET_MISSING", slot="S1.06")
    for value in list(defaults.values()) + list(overrides.values()):
        if ";" in value:
            _package_invalid("CONTENT_TYPES_INVALID", "PARAMETERS", slot="S1.06")
    for entry in package.entries:
        if entry.is_directory or entry.name == CONTENT_TYPES_PART:
            continue
        value = overrides.get(name_key1(entry.name))
        if value is None:
            value = defaults.get(_extension(entry.name))
        if value is None:
            _package_invalid("CONTENT_TYPES_INVALID", "UNRESOLVED_TYPE", slot="S1.06", part=entry.name)
        package.content_types[entry.name] = value.lower()


_RELS_NAME = re.compile(r"^(?:(.*)/)?_rels/([^/]*)\.rels\Z")


def _rels_source(name: str):
    match = _RELS_NAME.match(name)
    if match is None:
        return None
    directory, base = match.group(1), match.group(2)
    if directory is None and base == "":
        return ""
    if base == "":
        return None
    return (directory + "/" if directory else "") + base


def _resolve_internal_target(source: str, target: str):
    """REL-2: (detail, resolved part name); detail is None on success."""
    for match in re.finditer(r"%(..)?", target):
        pair = match.group(1)
        if pair is None or not re.match(r"^[0-9A-Fa-f]{2}$", pair):
            return "TARGET_ENCODING", None
        character = chr(int(pair, 16))
        if character in "/\\." or ord(character) < 0x20 or ord(character) == 0x7F:
            return "TARGET_ENCODING", None
    decoded = urllib.parse.unquote(target)
    if "%" in decoded:
        return "TARGET_ENCODING", None
    if "\\" in decoded or decoded.startswith("/") or "?" in decoded or "#" in decoded:
        return "TARGET_FORM", None
    base = source.rpartition("/")[0] if source else ""
    stack = [segment for segment in base.split("/") if segment] if base else []
    for segment in decoded.split("/"):
        if segment in ("", "."):
            continue
        if segment == "..":
            if not stack:
                return "PARENT_TRAVERSAL", None
            stack.pop()
        else:
            stack.append(segment)
    return None, "/".join(stack)


def is_hyperlink_type(rel_type: str) -> bool:
    return rel_type.endswith("/hyperlink")


def _check_relationships(package: DocxPackage) -> None:
    """S1.07: each .rels part in ascending name, then REL-3 once."""
    rels_parts = sorted(
        (name for name in package.files if _rels_source(name) is not None),
        key=lambda name: name_key1(name).encode("utf-8", "surrogatepass"),
    )
    for name in rels_parts:
        root = xml_part_checks(package, name, "S1.07")
        source = _rels_source(name)
        package.rels_source[name] = source
        relationships = []
        ids = set()
        for child in root:
            if child.tag != "{%s}Relationship" % NS_PR:
                continue
            rel_id, rel_type, target = child.get("Id"), child.get("Type"), child.get("Target")
            mode = child.get("TargetMode")
            if rel_id is None or rel_type is None or target is None:
                _package_invalid("RELATIONSHIP_INVALID", "ATTRIBUTE", slot="S1.07", part=name)
            if rel_id in ids:
                _package_invalid("RELATIONSHIP_INVALID", "DUPLICATE_ID", slot="S1.07", part=name)
            if mode not in (None, "Internal", "External"):
                _package_invalid("RELATIONSHIP_INVALID", "TARGET_MODE", slot="S1.07", part=name)
            ids.add(rel_id)
            relationships.append(
                {"id": rel_id, "type": rel_type, "target": target,
                 "external": mode == "External", "resolved": None}
            )
        for relationship in relationships:
            if relationship["external"] or is_hyperlink_type(relationship["type"]):
                continue
            detail, resolved = _resolve_internal_target(source, relationship["target"])
            if detail is not None:
                _package_invalid("RELATIONSHIP_INVALID", detail, slot="S1.07", part=name)
            actual = package.resolve_entry(resolved)
            if actual is None:
                _package_invalid("RELATIONSHIP_INVALID", "INTERNAL_TARGET_MISSING", slot="S1.07", part=name)
            relationship["resolved"] = actual
        package.relationships[name] = relationships
    office = [
        relationship
        for relationship in package.relationships.get("_rels/.rels", [])
        if relationship["type"] == REL_TYPE_OFFICE_DOCUMENT
    ]
    if len(office) != 1 or office[0]["external"] or office[0]["resolved"] != MAIN_PART:
        _package_invalid("MAIN_PART", slot="S1.07")


_FONT_EXTENSIONS = (".odttf", ".ttf", ".otf", ".ttc", ".eot", ".fntdata", ".woff", ".woff2")
_FONT_CONTENT_TYPES = (
    "application/vnd.openxmlformats-officedocument.obfuscatedfont",
    "application/vnd.ms-package.obfuscated-opentype",
    "application/vnd.ms-fontobject",
    "application/font-sfnt",
)


def _all_relationships(package: DocxPackage):
    for name in sorted(package.relationships, key=lambda item: name_key1(item).encode("utf-8", "surrogatepass")):
        for relationship in package.relationships[name]:
            yield name, relationship


def _check_embedded_fonts_abc(package: DocxPackage) -> None:
    for entry in package.entries:
        if entry.is_directory:
            continue
        key = name_key1(entry.name)
        if key.startswith("word/fonts/") or key.endswith(_FONT_EXTENSIONS):
            fail("RENDER_EMBEDDED_FONT_DENIED", "PART_NAME", None, "S1.08", part=entry.name)
    for entry in package.entries:
        content_type = package.content_types.get(entry.name)
        if content_type is None:
            continue
        if content_type in _FONT_CONTENT_TYPES or content_type.startswith(
            ("font/", "application/x-font", "application/x-fontdata")
        ):
            fail("RENDER_EMBEDDED_FONT_DENIED", "CONTENT_TYPE", None, "S1.08", part=entry.name)
    for name, relationship in _all_relationships(package):
        if relationship["type"].endswith("/font"):
            fail("RENDER_EMBEDDED_FONT_DENIED", "RELATIONSHIP", None, "S1.08", part=name)


def _check_active_content(package: DocxPackage) -> None:
    """S1.09: MACRO_CONTENT, OLE_OR_ACTIVEX, ATTACHED_TEMPLATE."""
    for entry in package.entries:
        content_type = package.content_types.get(entry.name, "")
        if (
            name_key1(entry.name).rpartition("/")[2] == "vbaproject.bin"
            or "macroenabled" in content_type
            or "vbaproject" in content_type
            or "vbadata" in content_type
        ):
            _package_invalid("MACRO_CONTENT", slot="S1.09", part=entry.name)
    for _, relationship in _all_relationships(package):
        if relationship["type"].lower().endswith(("/vbaproject", "/wordvbadata")):
            _package_invalid("MACRO_CONTENT", slot="S1.09")
    for entry in package.entries:
        content_type = package.content_types.get(entry.name, "")
        if "oleobject" in content_type or "activex" in content_type:
            _package_invalid("OLE_OR_ACTIVEX", slot="S1.09", part=entry.name)
    for _, relationship in _all_relationships(package):
        if relationship["type"].lower().endswith(
            ("/oleobject", "/control", "/activexcontrol", "/activexcontrolbinary", "/package")
        ):
            _package_invalid("OLE_OR_ACTIVEX", slot="S1.09")
    for _, relationship in _all_relationships(package):
        if relationship["type"].endswith("/attachedTemplate"):
            _package_invalid("ATTACHED_TEMPLATE", slot="S1.09")


def _check_external_relationships(package: DocxPackage) -> None:
    """S1.10 relationship-level external references."""
    for name, relationship in _all_relationships(package):
        if not relationship["external"]:
            continue
        if not is_hyperlink_type(relationship["type"]):
            fail("RENDER_EXTERNAL_REFERENCE_DENIED", "EXTERNAL_RELATIONSHIP", None, "S1.10", part=name)
        if not uri_scheme_allowed(relationship["target"]):
            fail("RENDER_EXTERNAL_REFERENCE_DENIED", "TARGET_SCHEME", None, "S1.10", part=name)


_RASTER_ACCEPTED = ("png", "jpeg", "gif")
_DECLARED_FORMATS = {
    "image/png": "png",
    "image/jpeg": "jpeg",
    "image/gif": "gif",
    "image/svg+xml": "svg",
    "image/x-emf": "emf",
    "image/emf": "emf",
    "application/x-emf": "emf",
    "image/x-wmf": "wmf",
    "image/wmf": "wmf",
    "application/x-wmf": "wmf",
    "application/pdf": "pdf",
    "application/postscript": "eps",
    "image/x-eps": "eps",
    "application/eps": "eps",
    "image/bmp": "bmp",
    "image/x-bmp": "bmp",
    "image/x-ms-bmp": "bmp",
    "image/tiff": "tiff",
    "image/webp": "webp",
}
_VECTOR_FORMATS = ("svg", "emf", "wmf", "pdf", "eps")
_OTHER_RASTER_FORMATS = ("bmp", "tiff", "webp")


def _magic_format(content: bytes):
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if content.startswith(b"\xff\xd8\xff"):
        return "jpeg"
    if content.startswith((b"GIF87a", b"GIF89a")):
        return "gif"
    if content.startswith(b"%PDF"):
        return "pdf"
    if content.startswith((b"%!PS", b"\xc5\xd0\xd3\xc6")):
        return "eps"
    if content.startswith((b"\xd7\xcd\xc6\x9a", b"\x01\x00\x09\x00", b"\x02\x00\x09\x00")):
        return "wmf"
    if content[:4] == b"\x01\x00\x00\x00" and content[40:44] == b" EMF":
        return "emf"
    head = content[:256].lstrip()
    if head.startswith(b"<svg") or (head.startswith(b"<?xml") and b"<svg" in content[:4096]):
        return "svg"
    if content.startswith(b"BM"):
        return "bmp"
    if content.startswith((b"II*\x00", b"MM\x00*")):
        return "tiff"
    if content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        return "webp"
    return None


def _declared_format(content_type: str):
    if content_type in _DECLARED_FORMATS:
        return _DECLARED_FORMATS[content_type]
    if content_type.endswith("+xml") and "svg" in content_type:
        return "svg"
    return None


def _check_media(package: DocxPackage) -> None:
    """S1.11 media_classification per part, ascending name."""
    scope = set()
    for _, relationship in _all_relationships(package):
        if relationship["type"].endswith("/image") and relationship["resolved"]:
            scope.add(relationship["resolved"])
    for name, content_type in package.content_types.items():
        if (
            name_key1(name).startswith("word/media/")
            or content_type.startswith("image/")
            or content_type in ("application/x-emf", "application/x-wmf", "application/pdf")
            or (content_type.endswith("+xml") and "svg" in content_type)
        ):
            scope.add(name)
    for name in sorted(scope, key=lambda item: name_key1(item).encode("utf-8", "surrogatepass")):
        declared = _declared_format(package.content_types.get(name, ""))
        magic = _magic_format(package.read(name, "S1.11"))
        evidence = {"part": name, "declared": declared, "magic": magic, "extension": _extension(name)}
        if declared != magic and (
            (declared is not None and magic is not None)
            or declared in _RASTER_ACCEPTED
            or magic in _RASTER_ACCEPTED
        ):
            fail("RENDER_MEDIA_TYPE_MISMATCH", None, None, "S1.11", **evidence)
        if declared in _VECTOR_FORMATS or magic in _VECTOR_FORMATS or declared is None or magic is None:
            fail("RENDER_EMBEDDED_VECTOR_DENIED", None, None, "S1.11", **evidence)
        if declared in _OTHER_RASTER_FORMATS:
            fail("RENDER_MEDIA_TYPE_UNSUPPORTED", None, None, "S1.11", **evidence)


def _check_allowlist_and_reachability(package: DocxPackage) -> None:
    """S1.12 PART_ALLOWLIST_V1 then S1.13 reachability."""
    for entry in package.entries:
        if entry.is_directory or entry.name == CONTENT_TYPES_PART:
            continue
        if package.content_types[entry.name] not in ALLOWED_CONTENT_TYPES_V1:
            _package_invalid("PART_TYPE_NOT_ALLOWED", slot="S1.12", part=entry.name)
    reachable = {"_rels/.rels"} if "_rels/.rels" in package.files else set()
    sources = {""}
    changed = True
    while changed:
        changed = False
        for rels_name, source in package.rels_source.items():
            if source not in sources:
                continue
            if rels_name not in reachable:
                reachable.add(rels_name)
                changed = True
            for relationship in package.relationships.get(rels_name, []):
                target = relationship["resolved"]
                if target and target not in sources:
                    sources.add(target)
                    reachable.add(target)
                    changed = True
    for entry in package.entries:
        if entry.is_directory or entry.name == CONTENT_TYPES_PART:
            continue
        if entry.name not in reachable:
            _package_invalid("PART_UNREACHABLE", slot="S1.13", part=entry.name)


_EMBED_DECLARATIONS = frozenset(
    w(local)
    for local in (
        "embedRegular", "embedBold", "embedItalic", "embedBoldItalic",
        "embedTrueTypeFonts", "embedSystemFonts",
    )
)


def _sorted_xml_parts(package: DocxPackage) -> list:
    return sorted(package.xml, key=lambda item: name_key1(item).encode("utf-8", "surrogatepass"))


def _check_xml_declarations(package: DocxPackage) -> None:
    """S1.14 xml checks, S1.15 font declarations, S1.16 constructs."""
    for name in sorted(package.files, key=lambda item: name_key1(item).encode("utf-8", "surrogatepass")):
        if name in package.xml or not package.content_types.get(name, "").endswith("+xml"):
            continue
        xml_part_checks(package, name, "S1.14", main=name == MAIN_PART)
    if MAIN_PART not in package.xml:
        xml_part_checks(package, MAIN_PART, "S1.14", main=True)
    for name in _sorted_xml_parts(package):
        for element in package.xml[name].iter():
            if element.tag in _EMBED_DECLARATIONS or w("fontKey") in element.attrib:
                fail("RENDER_EMBEDDED_FONT_DENIED", "DECLARATION", None, "S1.15", part=name)
    construct_rules = (
        ("ALTCHUNK", (w("altChunk"),), ("/aFChunk",)),
        ("SUBDOC", (w("subDoc"),), ("/subDocument",)),
        ("EXTERNAL_DATA", (w("externalData"),), ()),
        ("MAIL_MERGE", (w("mailMerge"), w("odso"), w("dataSource")),
         ("/mailMergeSource", "/mailMergeHeaderSource", "/recipientData")),
    )
    for reason, tags, rel_suffixes in construct_rules:
        for name in _sorted_xml_parts(package):
            for element in package.xml[name].iter():
                if element.tag in tags:
                    _package_invalid(reason, slot="S1.16", part=name)
        for _, relationship in _all_relationships(package):
            if rel_suffixes and relationship["type"].endswith(rel_suffixes):
                _package_invalid(reason, slot="S1.16")


_R_URL_LOCALS = frozenset(("link", "href", "pict", "dm", "lo", "qs", "cs", "embed", "id"))
_VO_URL_LOCALS = frozenset(("src", "href", "althref"))


def _check_url_attributes(package: DocxPackage) -> None:
    """S1.17 denied_url_valued_attributes."""
    for name in _sorted_xml_parts(package):
        if name.endswith(".rels") or name == CONTENT_TYPES_PART:
            continue
        relationships = {item["id"]: item for item in package.relationships_of(name)}
        for element in package.xml[name].iter():
            for attribute, value in element.attrib.items():
                namespace, _, local = attribute[1:].partition("}") if attribute.startswith("{") else ("", "", attribute)
                if namespace == NS_R and local in _R_URL_LOCALS:
                    relationship = relationships.get(value)
                    if relationship is not None and relationship["external"] and not (
                        is_hyperlink_type(relationship["type"]) and uri_scheme_allowed(relationship["target"])
                    ):
                        fail("RENDER_EXTERNAL_REFERENCE_DENIED", "R_" + local.upper(), None, "S1.17", part=name)
                elif namespace in (NS_V, NS_O) and local in _VO_URL_LOCALS:
                    fail("RENDER_EXTERNAL_REFERENCE_DENIED", "VML_" + local.upper(), None, "S1.17", part=name)
                elif namespace == NS_XLINK:
                    fail("RENDER_EXTERNAL_REFERENCE_DENIED", "XLINK", None, "S1.17", part=name)
                elif attribute == w("instr"):
                    match = _SCHEME_PREFIX.match(value.strip())
                    if match and match.group(1).lower() not in ("http", "https", "mailto"):
                        fail("RENDER_EXTERNAL_REFERENCE_DENIED", "SCHEME", None, "S1.17", part=name)


def docx_preflight(data: bytes) -> DocxPackage:
    """S1.01 to S1.17 over the exact caller-supplied bytes."""
    if not isinstance(data, (bytes, bytearray)):
        _package_invalid("NOT_ZIP_OR_CORRUPT", slot="S1.02")
    data = bytes(data)
    if len(data) > DOCX_LIMITS_V1["max_input_bytes"]:
        _limit_exceeded("INPUT_BYTES", "S1.01", size=len(data))
    import zipfile

    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            archive.infolist()
    except (zipfile.BadZipFile, zipfile.LargeZipFile, OSError, ValueError, EOFError, struct.error):
        _package_invalid("NOT_ZIP_OR_CORRUPT", slot="S1.02")
    entries, cd_offset = _parse_central_directory(data)
    _check_local_headers(data, entries)
    _check_tiling(data, entries, cd_offset)
    _check_methods_and_types(entries)
    _check_names(entries)
    _check_declared_limits(entries)
    package = DocxPackage(data, entries)
    _check_content_types(package)
    _check_relationships(package)
    _check_embedded_fonts_abc(package)
    _check_active_content(package)
    _check_external_relationships(package)
    _check_media(package)
    _check_allowlist_and_reachability(package)
    _check_xml_declarations(package)
    _check_url_attributes(package)
    return package


# =============================================================================
# S2 PINNED ENVIRONMENT
# =============================================================================

FACES = ("REGULAR", "BOLD", "ITALIC", "BOLD_ITALIC")
_PDF_NAME_KEY = re.compile(r"^[\x21-\x7e]+\Z")


def build_convert_to_argument() -> str:
    """PDF_EXPORT_FILTER_V1 convert_to_argument."""
    options = {name: {"type": kind, "value": value} for name, (kind, value) in PDF_EXPORT_OPTIONS_V1.items()}
    return "pdf:writer_pdf_Export:" + json.dumps(options, sort_keys=True, separators=(",", ":"))


def manifest_digest(manifest: dict) -> str:
    """DIGEST_SPEC_V1 manifest_digest (manifest_self_digest removed)."""
    return canonical_digest({key: value for key, value in manifest.items() if key != "manifest_self_digest"})


def _unverified(reason: str, **evidence):
    fail("RENDER_ENVIRONMENT_UNVERIFIED", reason, None, "S2.01", **evidence)


def _is_int(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _check_font_tables(manifest: dict) -> None:
    families = manifest["canonical_families"]
    if not isinstance(families, list) or not all(isinstance(item, str) for item in families):
        _unverified("FONT_TABLES", key="canonical_families")
    family_set = set(families)
    docx_map = manifest["docx_family_to_canonical"]
    if not isinstance(docx_map, dict) or any(value not in family_set for value in docx_map.values()):
        _unverified("FONT_TABLES", key="docx_family_to_canonical")
    pdf_map = manifest["pdf_basefont_to_canonical"]
    if not isinstance(pdf_map, dict):
        _unverified("FONT_TABLES", key="pdf_basefont_to_canonical")
    for key, value in pdf_map.items():
        if (
            not _PDF_NAME_KEY.match(key)
            or not isinstance(value, dict)
            or set(value) != {"canonical_family_id", "face"}
            or value["canonical_family_id"] not in family_set
            or value["face"] not in FACES
        ):
            _unverified("FONT_TABLES", key="pdf_basefont_to_canonical")
    substitutions = manifest["approved_substitutions"]
    if not isinstance(substitutions, dict) or any(
        key not in family_set or not isinstance(value, list) or any(item not in family_set for item in value)
        for key, value in substitutions.items()
    ):
        _unverified("FONT_TABLES", key="approved_substitutions")
    glyphs = manifest["marker_glyph_map"]
    if not isinstance(glyphs, list):
        _unverified("FONT_TABLES", key="marker_glyph_map")
    seen = set()
    for entry in glyphs:
        if (
            not isinstance(entry, dict)
            or set(entry) != {"canonical_family_id", "code_point", "expected"}
            or entry["canonical_family_id"] not in family_set
            or not _is_int(entry["code_point"])
            or not isinstance(entry["expected"], str)
            or (entry["canonical_family_id"], entry["code_point"]) in seen
        ):
            _unverified("FONT_TABLES", key="marker_glyph_map")
        seen.add((entry["canonical_family_id"], entry["code_point"]))


def verify_manifest(manifest_bytes) -> dict:
    """The contract-defined S2.01 checks that need no live installation."""
    if manifest_bytes is None:
        _unverified("MANIFEST_ABSENT")
    try:
        manifest = strict_json_loads(bytes(manifest_bytes).decode("utf-8"))
    except (UnicodeDecodeError, ValueError, TypeError):
        _unverified("MANIFEST_MALFORMED")
    if not isinstance(manifest, dict):
        _unverified("MANIFEST_MALFORMED")
    if _contains_non_integer_number(manifest):
        _unverified("MANIFEST_NON_INTEGER")
    known = set(MANIFEST_PRE_PROVISION_KEYS) | set(MANIFEST_POST_PROVISION_KEYS)
    for key in sorted(manifest):
        if key not in known:
            _unverified("MANIFEST_KEY_UNPARTITIONED", key=key)
    for key in sorted(known):
        if key not in manifest:
            _unverified("MANIFEST_KEY_MISSING", key=key)
    for key in MANIFEST_POST_PROVISION_KEYS:
        if manifest[key] is None:
            _unverified("POST_BINDING_UNPOPULATED", key=key)
    if manifest["manifest_self_digest"] != manifest_digest(manifest):
        _unverified("MANIFEST_SELF_DIGEST")
    for key in MANIFEST_SET_KEYS:
        value = manifest[key]
        if (
            not isinstance(value, list)
            or not all(isinstance(item, str) for item in value)
            or value != sorted(set(value))
        ):
            _unverified("MANIFEST_SET_UNSORTED", key=key)
    if manifest["docx_limits"] != DOCX_LIMITS_V1:
        _unverified("DOCX_LIMITS")
    spec = manifest["extraction_spec"]
    expected_keys = set(INSPECTION_LIMITS_V1) | {
        "laparams", "line_group_baseline_tolerance_q", "word_gap_threshold_q", "traversal_max_operations",
    }
    if (
        not isinstance(spec, dict)
        or set(spec) != expected_keys
        or spec["laparams"] is not None
        or any(spec[key] != value or not _is_int(spec[key]) for key, value in INSPECTION_LIMITS_V1.items())
        or spec["traversal_max_operations"] != INSPECTION_LIMITS_V1["inspection_max_traversal_operations"]
        or not _is_int(spec["line_group_baseline_tolerance_q"])
        or spec["line_group_baseline_tolerance_q"] < 0
        or not _is_int(spec["word_gap_threshold_q"])
        or spec["word_gap_threshold_q"] < 0
    ):
        _unverified("EXTRACTION_SPEC")
    if (manifest["text_overlap_ratio_numerator"], manifest["text_overlap_ratio_denominator"]) != (
        TEXT_OVERLAP_RATIO_NUMERATOR, TEXT_OVERLAP_RATIO_DENOMINATOR,
    ):
        _unverified("TEXT_OVERLAP_RATIO")
    for key, value in SPEC_IDS_V1.items():
        if manifest[key] != value:
            _unverified("SPEC_ID", key=key)
    if manifest["pdf_export_filter"] != build_convert_to_argument():
        _unverified("PDF_EXPORT_FILTER")
    if manifest["sandbox_flags"] != list(REQUIRED_SANDBOX_FLAGS):
        _unverified("SANDBOX_FLAGS")
    tmpfs = manifest["sandbox_tmpfs_paths"]
    if len(tmpfs) != 2 or SANDBOX_TMP_PATH not in tmpfs:
        _unverified("SANDBOX_TMPFS")
    size = manifest["sandbox_tmpfs_size_bytes"]
    if not _is_int(size) or size <= 0:
        _unverified("SANDBOX_TMPFS")
    errnos = manifest["sandbox_expected_unreachable_errnos"]
    if not isinstance(errnos, dict) or set(errnos) != set(EXPECTED_UNREACHABLE_ERRNOS_V1):
        _unverified("ERRNO_SET")
    if not isinstance(manifest["sandbox_symlinks"], list) or any(
        not isinstance(item, dict) or set(item) != {"path", "target"}
        or not isinstance(item["path"], str) or not isinstance(item["target"], str)
        for item in manifest["sandbox_symlinks"]
    ):
        _unverified("SANDBOX_SYMLINKS")
    for family, allowed in EXPECTED_UNREACHABLE_ERRNOS_V1.items():
        value = errnos[family]
        if not isinstance(value, list) or not value or not set(value) <= set(allowed) or value != sorted(set(value)):
            _unverified("ERRNO_SET", family=family)
    if not _is_int(manifest["timeout_seconds"]) or manifest["timeout_seconds"] <= 0:
        _unverified("TIMEOUT")
    if not isinstance(manifest["sandbox_path"], str) or not isinstance(manifest["fontconfig_file"], str):
        _unverified("SANDBOX_ENVIRONMENT")
    _check_font_tables(manifest)
    return manifest


class ContentBindingFailure(Exception):
    def __init__(self, status: str, reason: str, relpath: str) -> None:
        super().__init__(status, reason, relpath)
        self.status = status
        self.reason = reason
        self.relpath = relpath


def _file_sha256(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _path_covered(path: str, covered: tuple) -> bool:
    normalized = os.path.normpath(path)
    for item in covered:
        base = os.path.normpath(item)
        if normalized == base or normalized.startswith(base.rstrip(os.sep) + os.sep):
            return True
    return False


def tree_digest(root: str, covered: tuple = (), exclusions: tuple = (), stdlib: bool = False) -> str:
    """TREE_DIGEST_V1 (and the STDLIB_TREE variant)."""
    records = []
    pending = [""]
    while pending:
        relative = pending.pop()
        directory = os.path.join(root, relative) if relative else root
        with os.scandir(directory) as iterator:
            children = list(iterator)
        if not children and relative:
            records.append(["D", relative])
        for child in children:
            child_rel = (relative + "/" if relative else "") + child.name
            if child_rel in exclusions:
                continue
            if stdlib and (child.name == "__pycache__" and child.is_dir(follow_symlinks=False)):
                continue
            if stdlib and not relative and child.name in ("site-packages", "dist-packages"):
                continue
            mode = child.stat(follow_symlinks=False).st_mode
            if stat.S_ISLNK(mode):
                link = os.readlink(child.path)
                target = os.path.realpath(child.path)
                inside = _path_covered(target, (root,))
                if stdlib and not inside:
                    if not os.path.isfile(target):
                        raise ContentBindingFailure("RENDER_CONTENT_BINDING_UNSUPPORTED_ENTRY", "LINK_TARGET", child_rel)
                    records.append(["LT", child_rel, link, _file_sha256(target)])
                    continue
                if not inside and not _path_covered(target, covered):
                    raise ContentBindingFailure("RENDER_CONTENT_BINDING_INCOMPLETE", "SYMLINK_OUTSIDE_COVERAGE", child_rel)
                records.append(["L", child_rel, link])
            elif stat.S_ISDIR(mode):
                pending.append(child_rel)
            elif stat.S_ISREG(mode):
                records.append(["F", child_rel, 1 if mode & stat.S_IXUSR else 0, _file_sha256(child.path)])
            else:
                raise ContentBindingFailure("RENDER_CONTENT_BINDING_UNSUPPORTED_ENTRY", "ENTRY_TYPE", child_rel)
    records.sort(key=lambda record: record[1].encode("utf-8", "surrogatepass"))
    return canonical_digest(records)


def _default_dist_resolver(name: str):
    import importlib.metadata

    distribution = importlib.metadata.distribution(name)
    site = str(distribution.locate_file(""))
    files = [str(item).replace(os.sep, "/") for item in (distribution.files or [])]
    return site, files


def root_digest(root: dict, covered: tuple, exclusions: dict, dist_resolver=None) -> str:
    """The computed digest of one CONTENT_BINDING_V1 root."""
    kind, path = root["kind"], root["path"]
    excluded = tuple(sorted(exclusions.get(root["id"], ())))
    if kind == "ABSENT":
        if os.path.lexists(path):
            raise ContentBindingFailure("RENDER_CONTENT_BINDING_MISMATCH", "PRESENT", path)
        return ABSENT_ROOT_DIGEST
    if kind == "LINK":
        if not os.path.islink(path):
            raise ContentBindingFailure("RENDER_CONTENT_BINDING_MISMATCH", "NOT_LINK", path)
        return canonical_digest(["L", path, os.readlink(path)])
    if kind == "FILE":
        real = os.path.realpath(path)
        if not os.path.isfile(real):
            raise ContentBindingFailure("RENDER_CONTENT_BINDING_MISMATCH", "NOT_FILE", path)
        return _file_sha256(real)
    if kind in ("TREE", "STDLIB_TREE"):
        if not os.path.isdir(path) or os.path.islink(path):
            raise ContentBindingFailure("RENDER_CONTENT_BINDING_MISMATCH", "NOT_TREE", path)
        return tree_digest(path, covered, excluded, stdlib=kind == "STDLIB_TREE")
    if kind == "DIST_RECORD":
        site, files = (dist_resolver or _default_dist_resolver)(path)
        records = []
        for relative in sorted(files, key=lambda item: item.encode("utf-8", "surrogatepass")):
            if relative.endswith(".pyc") or "/__pycache__/" in relative or relative in excluded:
                continue
            full = os.path.join(site, relative)
            if os.path.islink(full) or not os.path.isfile(full):
                continue
            mode = os.stat(full).st_mode
            records.append(["F", relative, 1 if mode & stat.S_IXUSR else 0, _file_sha256(full)])
        return canonical_digest(records)
    raise ContentBindingFailure("RENDER_CONTENT_BINDING_UNSUPPORTED_ENTRY", "ROOT_KIND", path)


class VerifiedEnvironment:
    """The outcome of S2: the verified manifest and its digests."""

    def __init__(self, manifest: dict, content_binding_digest: str, root_digests: list) -> None:
        self.manifest = manifest
        self.manifest_digest = manifest_digest(manifest)
        self.content_binding_digest = content_binding_digest
        self.root_digests = root_digests
        self.runtime_manifest_digest = canonical_digest(
            {
                "spec": "RUNTIME_MANIFEST_BINDING_V1",
                "manifest_digest": self.manifest_digest,
                "content_binding_digest": content_binding_digest,
            }
        )


def verify_content_binding(manifest: dict, dist_resolver=None) -> tuple:
    """S2.02 mount coverage then S2.03 per root in ascending root_id."""
    binding = manifest["content_binding"]
    if not isinstance(binding, dict) or not isinstance(binding.get("roots"), list):
        _unverified("CONTENT_BINDING_SHAPE")
    roots = sorted(binding["roots"], key=lambda item: item["id"])
    exclusions = {}
    for item in binding.get("exclusions", []):
        exclusions.setdefault(item["root_id"], []).append(item["relpath"])
    mounts = tuple(manifest["sandbox_read_only_paths"])
    tree_paths = tuple(root["path"] for root in roots if root["kind"] in ("TREE", "STDLIB_TREE"))
    exact_paths = {root["path"] for root in roots if root["kind"] in ("FILE", "LINK")}
    for mount in sorted(mounts):
        if mount not in exact_paths and not _path_covered(mount, tree_paths):
            fail("RENDER_CONTENT_BINDING_INCOMPLETE", "MOUNT_COVERAGE", None, "S2.02", path=mount)
    covered = tree_paths + mounts + tuple(exact_paths)
    computed = []
    for root in roots:
        try:
            digest = root_digest(root, covered, exclusions, dist_resolver)
        except ContentBindingFailure as failure:
            fail(failure.status, failure.reason, None, "S2.03", root_id=root["id"], relpath=failure.relpath)
        except OSError:
            fail("RENDER_CONTENT_BINDING_MISMATCH", "UNREADABLE", None, "S2.03", root_id=root["id"])
        if digest != root["expected_digest"]:
            fail("RENDER_CONTENT_BINDING_MISMATCH", "DIGEST", None, "S2.03", root_id=root["id"])
        computed.append([root["id"], digest])
    return canonical_digest(computed), computed


def pre_provision_plan_digest(manifest: dict) -> str:
    return canonical_digest(
        {"spec": "PRE_PROVISION_PLAN_V1", "fields": {key: manifest[key] for key in MANIFEST_PRE_PROVISION_KEYS}}
    )


def plan_digest(manifest: dict, requirements_in: bytes, requirements_lock: bytes) -> str:
    return canonical_digest(
        {
            "spec": "PROVISIONING_PLAN_V1",
            "lock_review_digest": manifest["lock_review_digest"],
            "requirements_in_sha256": sha256_hex(requirements_in),
            "requirements_lock_sha256": sha256_hex(requirements_lock),
            "pre_provision_plan_digest": pre_provision_plan_digest(manifest),
        }
    )


ENTRY_EXTRACTION_CONSTANTS = {
    "LINE_GROUP_BASELINE_TOLERANCE_Q": "line_group_baseline_tolerance_q",
    "WORD_GAP_THRESHOLD_Q": "word_gap_threshold_q",
}


def entry_extraction_constants(entry_bytes: bytes) -> dict:
    """The module-level extraction constants of ENTRY_BYTES, read by AST
    (the entry is never imported by the parent)."""
    import ast

    found = {}
    tree = ast.parse(entry_bytes)
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            name = node.targets[0].id
            if name in ENTRY_EXTRACTION_CONSTANTS and isinstance(node.value, ast.Constant):
                found[name] = node.value.value
    return found


def check_entry_extraction_constants(manifest: dict, entry_bytes: bytes) -> None:
    """The child receives only the PDF bytes, so the two extraction
    parameters it applies are constants of the entry; they must equal the
    manifest values (an unset constant never verifies)."""
    constants = entry_extraction_constants(entry_bytes)
    for constant, key in ENTRY_EXTRACTION_CONSTANTS.items():
        value = constants.get(constant)
        if not _is_int(value) or value != manifest["extraction_spec"][key]:
            _unverified("EXTRACTION_SPEC", key=key)


def verify_environment(manifest_bytes, live_verifier=None, plan_inputs=None, dist_resolver=None,
                       entry_bytes=None) -> VerifiedEnvironment:
    """S2.01 to S2.03. plan_inputs is (requirements.in bytes,
    requirements-lock.txt bytes). live_verifier(manifest) is the injected
    operator-side check of the live installation (versions, fonts, locale,
    reconciliation); it returns None when it matches, else a reason."""
    manifest = verify_manifest(manifest_bytes)
    check_entry_extraction_constants(manifest, entry_bytes if entry_bytes is not None else b"")
    if (
        plan_inputs is None
        or any(not isinstance(item, (bytes, bytearray)) for item in plan_inputs)
        or plan_digest(manifest, *plan_inputs) != manifest["approved_plan_digest"]
    ):
        _unverified("PLAN_DIGEST")
    if live_verifier is None:
        _unverified("LIVE_VERIFICATION_UNAVAILABLE")
    try:
        live_reason = live_verifier(manifest)
    except Exception as exc:
        _unverified("LIVE_VERIFICATION_FAILED", exception_class=type(exc).__name__)
    if live_reason is not None:
        _unverified(str(live_reason))
    binding_digest, computed = verify_content_binding(manifest, dist_resolver)
    return VerifiedEnvironment(manifest, binding_digest, computed)


# =============================================================================
# S3 SOURCE MODEL
# =============================================================================

_MARKER_TAGS = frozenset(
    w(local) for local in ("bookmarkStart", "bookmarkEnd", "permStart", "permEnd", "commentRangeStart", "commentRangeEnd")
)
_TRACKED_CHANGE_TAGS = frozenset(
    w(local)
    for local in (
        "ins", "del", "moveFrom", "moveTo", "moveFromRangeStart", "moveFromRangeEnd",
        "moveToRangeStart", "moveToRangeEnd", "cellIns", "cellDel", "cellMerge",
        "customXmlInsRangeStart", "customXmlDelRangeStart", "customXmlMoveFromRangeStart",
        "customXmlMoveToRangeStart",
    )
)
_TEXT_BOX_TAGS = frozenset((w("txbxContent"), "{%s}txbx" % NS_WPS, "{%s}textbox" % NS_V))
_ALTERNATE_TEXT_TAGS = frozenset(w(local) for local in ("t", "instrText", "fldChar", "fldSimple", "hyperlink", "p", "sym"))
_ALTERNATE_CONTENT = "{%s}AlternateContent" % NS_MC
_EAST_ASIAN_RANGES = ((0x0590, 0x08FF), (0x3000, 0x9FFF), (0xAC00, 0xD7AF), (0xF900, 0xFAFF), (0xFF00, 0xFFEF))
_FALSE_VALUES = ("0", "false", "off")
STYLE_CHAIN_MAX_DEPTH = 20


def _local_change_marker(tag: str) -> bool:
    return tag.startswith("{" + NS_W + "}") and tag.endswith("Change")


class SourceParagraph:
    __slots__ = (
        "index", "surface", "element", "table", "runs", "text", "tokens", "list_semantics",
        "level", "marker_code_point", "marker_expected", "marker_identity", "expected_identities",
        "style_chain", "table_chain",
    )

    def __init__(self, index, surface, element, table):
        self.index = index
        self.surface = surface
        self.element = element
        self.table = table
        self.runs = []
        self.text = ""
        self.tokens = []
        self.list_semantics = None
        self.level = None
        self.marker_code_point = None
        self.marker_expected = None
        self.marker_identity = None
        self.expected_identities = set()
        self.style_chain = []
        self.table_chain = []


class RunRecord:
    __slots__ = ("element", "text")

    def __init__(self, element):
        self.element = element
        self.text = ""


class SourceModel:
    """The S3 result: the indexed paragraph sequence S, the validated
    structure map M and the hyperlink source occurrences."""

    def __init__(self):
        self.paragraphs = []
        self.structure_map = []
        self.occurrences = []
        self.orphan_relationships = []
        self.bookmark_paragraph = {}
        self.auto_hyphenation = False


class _ChainError(Exception):
    def __init__(self, status, reason):
        super().__init__(status, reason)
        self.status = status
        self.reason = reason


class _Styles:
    def __init__(self, root):
        self.styles = {}
        self.default_paragraph = None
        self.default_table = None
        self.doc_rpr = None
        self.doc_ppr = None
        if root is None:
            return
        for style in root.findall(w("style")):
            style_id = style.get(w("styleId"))
            if style_id is None:
                continue
            self.styles.setdefault(style_id, style)
            if style.get(w("default")) in ("1", "true", "on"):
                if style.get(w("type")) == "paragraph" and self.default_paragraph is None:
                    self.default_paragraph = style_id
                if style.get(w("type")) == "table" and self.default_table is None:
                    self.default_table = style_id
        defaults = root.find(w("docDefaults"))
        if defaults is not None:
            rpr_default = defaults.find(w("rPrDefault"))
            ppr_default = defaults.find(w("pPrDefault"))
            self.doc_rpr = rpr_default.find(w("rPr")) if rpr_default is not None else None
            self.doc_ppr = ppr_default.find(w("pPr")) if ppr_default is not None else None

    def chain(self, style_id) -> list:
        """The w:basedOn chain, nearest first."""
        chain = []
        seen = set()
        current = style_id
        while current is not None:
            if current in seen:
                raise _ChainError("RENDER_STYLE_CHAIN_UNSUPPORTED", "CYCLE")
            style = self.styles.get(current)
            if style is None:
                raise _ChainError("RENDER_STYLE_CHAIN_UNSUPPORTED", "MISSING_STYLE")
            seen.add(current)
            chain.append(style)
            if len(chain) > STYLE_CHAIN_MAX_DEPTH:
                raise _ChainError("RENDER_STYLE_CHAIN_UNSUPPORTED", "DEPTH")
            based = style.find(w("basedOn"))
            current = based.get(w("val")) if based is not None else None
        return chain

    def paragraph_chain(self, paragraph) -> list:
        ppr = paragraph.find(w("pPr"))
        pstyle = ppr.find(w("pStyle")) if ppr is not None else None
        style_id = pstyle.get(w("val")) if pstyle is not None else self.default_paragraph
        if style_id is None:
            raise _ChainError("RENDER_STYLE_CHAIN_UNSUPPORTED", "MISSING_STYLE")
        return self.chain(style_id)

    def table_chain(self, table) -> list:
        if table is None:
            return []
        tblpr = table.find(w("tblPr"))
        tblstyle = tblpr.find(w("tblStyle")) if tblpr is not None else None
        style_id = tblstyle.get(w("val")) if tblstyle is not None else self.default_table
        chain = self.chain(style_id) if style_id is not None else []
        holders = chain + ([tblpr] if tblpr is not None else [])
        for holder in holders:
            for conditional in holder.iter(w("tblStylePr")):
                if conditional.find(w("rPr")) is not None or conditional.find(w("pPr")) is not None:
                    raise _ChainError("RENDER_STYLE_CHAIN_UNSUPPORTED", "TABLE_CONDITIONAL_FORMATTING")
        return chain

    def run_chain(self, run) -> list:
        rpr = run.find(w("rPr"))
        rstyle = rpr.find(w("rStyle")) if rpr is not None else None
        return self.chain(rstyle.get(w("val"))) if rstyle is not None else []


def _rpr(holder):
    if holder is None:
        return None
    if holder.tag == w("rPr"):
        return holder
    return holder.find(w("rPr"))


def _toggle(levels: list, local: str):
    """First-defined-wins toggle (w:b, w:i, w:caps, w:smallCaps, w:vanish)."""
    for rpr in levels:
        if rpr is None:
            continue
        element = rpr.find(w(local))
        if element is not None:
            return element.get(w("val")) not in _FALSE_VALUES
    return False


def _face(levels: list) -> str:
    bold, italic = _toggle(levels, "b"), _toggle(levels, "i")
    if bold and italic:
        return "BOLD_ITALIC"
    if bold:
        return "BOLD"
    if italic:
        return "ITALIC"
    return "REGULAR"


def _slot_value(levels: list, slot: str):
    """('THEME', name) or ('LITERAL', family) of the first level defining
    the slot, theme beating literal on the same w:rFonts; None if none."""
    for rpr in levels:
        if rpr is None:
            continue
        fonts = rpr.find(w("rFonts"))
        if fonts is None:
            continue
        theme = fonts.get(w(slot + "Theme"))
        if theme is not None:
            return ("THEME", theme)
        literal = fonts.get(w(slot))
        if literal is not None:
            return ("LITERAL", literal)
    return None


def _hint_denied(levels: list) -> bool:
    for rpr in levels:
        if rpr is None:
            continue
        fonts = rpr.find(w("rFonts"))
        if fonts is not None and fonts.get(w("hint")) in ("eastAsia", "cs"):
            return True
    return False


def normalize_family(name: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", name).split()).casefold()


def _theme_fonts(root) -> dict:
    fonts = {}
    if root is None:
        return fonts
    for scheme_name, prefix in (("majorFont", "major"), ("minorFont", "minor")):
        for element in root.iter("{%s}%s" % (NS_A, scheme_name)):
            latin = element.find("{%s}latin" % NS_A)
            if latin is not None and latin.get("typeface"):
                fonts[prefix + "Ascii"] = latin.get("typeface")
                fonts[prefix + "HAnsi"] = latin.get("typeface")
    return fonts


def _east_asian(text: str) -> bool:
    return any(low <= ord(ch) <= high for ch in text for low, high in _EAST_ASIAN_RANGES)


_HYPERLINK_EXTERNAL = re.compile(r'^(?i:HYPERLINK)[ \t]+"([^"\\]*)"\Z')
_HYPERLINK_INTERNAL = re.compile(r'^(?i:HYPERLINK)[ \t]+\\l[ \t]+"([^"\\]*)"\Z')


def _field_type(instruction: str) -> str:
    parts = instruction.split()
    return parts[0].upper() if parts else ""


def _scan_fields(root) -> list:
    """Fields of one part in document order: (type, instruction)."""
    found = []
    stack = []
    for element in root.iter():
        if element.tag == w("fldChar"):
            kind = element.get(w("fldCharType"))
            if kind == "begin":
                stack.append({"instr": [], "result": False})
            elif kind == "separate" and stack:
                stack[-1]["result"] = True
            elif kind == "end" and stack:
                field = stack.pop()
                instruction = "".join(field["instr"])
                found.append((_field_type(instruction), instruction))
        elif element.tag == w("instrText") and stack and not stack[-1]["result"]:
            stack[-1]["instr"].append(element.text or "")
        elif element.tag == w("fldSimple"):
            instruction = element.get(w("instr"), "")
            found.append((_field_type(instruction), instruction))
    for field in stack:
        instruction = "".join(field["instr"])
        found.append((_field_type(instruction), instruction))
    return found


def _s3(status, reason=None, slot=None, **evidence):
    fail(status, reason, None, slot, **evidence)


class _SourceBuilder:
    def __init__(self, package: DocxPackage, manifest: dict, structure_map):
        self.package = package
        self.manifest = manifest
        self.structure_map = structure_map
        self.document = package.xml[MAIN_PART]
        self.model = SourceModel()
        self.doc_rels = {item["id"]: item for item in package.relationships_of(MAIN_PART)}
        self.parts = {}
        for relationship in self.doc_rels.values():
            target = relationship["resolved"]
            if target and target in package.xml:
                self.parts.setdefault(relationship["type"].rpartition("/")[2], []).append(target)
        self.styles = _Styles(self._part("styles"))
        self.numbering = self._part("numbering")
        self.theme = _theme_fonts(self._part("theme"))
        self.docx_map = manifest["docx_family_to_canonical"]
        self.glyph_map = {
            (entry["canonical_family_id"], entry["code_point"]): entry["expected"]
            for entry in manifest["marker_glyph_map"]
        }

    def _part(self, kind):
        names = self.parts.get(kind, [])
        return self.package.xml[names[0]] if names else None

    def story_parts(self) -> list:
        names = [
            name for name in _sorted_xml_parts(self.package)
            if self.package.content_types.get(name) in STORY_CONTENT_TYPES
        ]
        return names

    def text_parts(self) -> list:
        return [MAIN_PART] + self.story_parts()

    # S3.01 to S3.07 ----------------------------------------------------

    def check_constructs(self) -> None:
        for name in _sorted_xml_parts(self.package):
            if name.endswith(".rels") or name == CONTENT_TYPES_PART:
                continue
            for element in self.package.xml[name].iter():
                if element.tag in _TRACKED_CHANGE_TAGS or _local_change_marker(element.tag):
                    _s3("RENDER_TRACKED_CHANGES_PRESENT", slot="S3.01", part=name)
        self.index_paragraphs()
        for name in self.story_parts():
            for text in self.package.xml[name].iter(w("t")):
                if tokenize(text.text or ""):
                    _s3("RENDER_TEXT_CONSTRUCT_UNSUPPORTED", "HEADER_FOOTER_NOTE_OR_COMMENT_TEXT", "S3.03", part=name)
        for name in self.text_parts():
            for element in self.package.xml[name].iter():
                if element.tag in _TEXT_BOX_TAGS:
                    _s3("RENDER_TEXT_CONSTRUCT_UNSUPPORTED", "TEXT_BOX", "S3.04", part=name)
        for name in self.text_parts():
            for element in self.package.xml[name].iter(_ALTERNATE_CONTENT):
                for branch in element:
                    if any(node.tag in _ALTERNATE_TEXT_TAGS for node in branch.iter()):
                        _s3("RENDER_ALTERNATE_CONTENT_UNSUPPORTED", None, "S3.05", part=name,
                            branch=branch.tag.rpartition("}")[2])
        for name in self.text_parts():
            for field_type, _ in _scan_fields(self.package.xml[name]):
                if field_type != "HYPERLINK":
                    _s3("RENDER_FIELD_UNSUPPORTED", None, "S3.06", part=name,
                        field_type=field_type[:64])
        for name in self.text_parts():
            if next(self.package.xml[name].iter(w("sym")), None) is not None:
                _s3("RENDER_TEXT_CONSTRUCT_UNSUPPORTED", "SYMBOL_GLYPH", "S3.07", part=name)

    def index_paragraphs(self) -> None:
        """PARAGRAPH_IDENTITY_MODEL_V1 under BLOCK_CHILD_TABLE_V1 (S3.02)."""
        body = self.document.find(w("body"))
        if body is None:
            _s3("RENDER_TEXT_CONSTRUCT_UNSUPPORTED", "BLOCK_CONTAINER", "S3.02", element="document")
        paragraphs = self.model.paragraphs

        def deny(child):
            _s3("RENDER_TEXT_CONSTRUCT_UNSUPPORTED", "BLOCK_CONTAINER", "S3.02",
                element=child.tag.rpartition("}")[2])

        def walk(container, level, surface, table, in_sdt):
            children = list(container)
            for position, child in enumerate(children):
                tag = child.tag
                if tag in _MARKER_TAGS:
                    continue
                if level in ("body", "tc") and tag == w("p"):
                    paragraphs.append(SourceParagraph(len(paragraphs), surface, child, table))
                elif level in ("body", "tc") and tag == w("tbl"):
                    walk(child, "tbl", "TABLE_CELL", child, False)
                elif tag == w("sdt"):
                    for part in child:
                        if part.tag in (w("sdtPr"), w("sdtEndPr")):
                            continue
                        if part.tag == w("sdtContent"):
                            walk(part, level, surface, table, True)
                        else:
                            deny(part)
                elif level in ("body", "tc") and tag == _ALTERNATE_CONTENT:
                    continue
                elif level == "body" and tag == w("sectPr") and not in_sdt and position == len(children) - 1:
                    continue
                elif level == "tbl" and tag in (w("tblPr"), w("tblGrid")) and not in_sdt:
                    continue
                elif level == "tbl" and tag == w("tr"):
                    walk(child, "tr", surface, table, False)
                elif level == "tr" and tag in (w("tblPrEx"), w("trPr")) and not in_sdt:
                    continue
                elif level == "tr" and tag == w("tc"):
                    walk(child, "tc", surface, table, False)
                elif level == "tc" and tag == w("tcPr") and not in_sdt:
                    continue
                else:
                    deny(child)

        walk(body, "body", "BODY", None, False)

    # Counted text and hyperlink occurrences -----------------------------

    def collect_text(self) -> list:
        issues = []
        field_stack = []
        link_stack = []
        occurrences = self.model.occurrences

        def counting():
            return all(field["result"] for field in field_stack)

        def active_occurrences():
            return link_stack + [field["occurrence"] for field in field_stack if field["occurrence"]]

        def append_text(run_record, text):
            if not counting():
                return
            run_record.text += text
            current.append(text)
            for occurrence in active_occurrences():
                occurrence["text"] += text

        def new_occurrence(source_kind, paragraph_index):
            occurrence = {
                "source_kind": source_kind, "paragraph_index": paragraph_index, "text": "",
                "dest_kind": None, "target": None, "bookmark": None, "rel_id": None,
            }
            occurrences.append(occurrence)
            return occurrence

        def visit_run(run, paragraph):
            record = RunRecord(run)
            paragraph.runs.append(record)
            for child in run:
                tag = child.tag
                if tag == w("fldChar"):
                    kind = child.get(w("fldCharType"))
                    if kind == "begin":
                        nested = bool(field_stack) or bool(link_stack)
                        field_stack.append({"instr": [], "result": False, "occurrence": None, "nested": nested})
                    elif kind == "separate" and field_stack:
                        field = field_stack[-1]
                        field["result"] = True
                        instruction = "".join(field["instr"]).strip()
                        if _field_type(instruction) == "HYPERLINK":
                            if field["nested"]:
                                issues.append(("RENDER_LINK_SOURCE_UNSUPPORTED", "FIELD_SHAPE"))
                            occurrence = new_occurrence("FIELD_COMPLEX", paragraph.index)
                            self._parse_hyperlink_field(instruction, occurrence, issues)
                            field["occurrence"] = occurrence
                    elif kind == "end" and field_stack:
                        field = field_stack.pop()
                        if not field["result"] and _field_type("".join(field["instr"])) == "HYPERLINK":
                            issues.append(("RENDER_LINK_SOURCE_UNSUPPORTED", "FIELD_SHAPE"))
                elif tag == w("instrText"):
                    if field_stack and not field_stack[-1]["result"]:
                        field_stack[-1]["instr"].append(child.text or "")
                elif tag == w("t"):
                    append_text(record, child.text or "")
                elif tag in (w("tab"), w("ptab"), w("br"), w("cr")):
                    append_text(record, " ")
                elif tag == w("noBreakHyphen"):
                    append_text(record, "\u2011")
                elif tag == w("softHyphen"):
                    append_text(record, "\u00ad")

        def visit(node, paragraph):
            tag = node.tag
            if tag == w("r"):
                visit_run(node, paragraph)
            elif tag == w("hyperlink"):
                if link_stack or any(field["occurrence"] for field in field_stack):
                    issues.append(("RENDER_LINK_SOURCE_UNSUPPORTED", "NESTED"))
                occurrence = new_occurrence("ELEMENT", paragraph.index)
                self._hyperlink_element(node, occurrence, issues)
                link_stack.append(occurrence)
                for child in node:
                    visit(child, paragraph)
                link_stack.pop()
            elif tag == w("fldSimple"):
                instruction = node.get(w("instr"), "").strip()
                field = {"instr": [], "result": True, "occurrence": None, "nested": False}
                if _field_type(instruction) == "HYPERLINK":
                    if field_stack or link_stack:
                        issues.append(("RENDER_LINK_SOURCE_UNSUPPORTED", "FIELD_SHAPE"))
                    field["occurrence"] = new_occurrence("FIELD_SIMPLE", paragraph.index)
                    self._parse_hyperlink_field(instruction, field["occurrence"], issues)
                field_stack.append(field)
                for child in node:
                    visit(child, paragraph)
                field_stack.pop()
            elif tag in (w("customXml"), w("smartTag"), w("bdo"), w("dir"), w("sdtContent")):
                for child in node:
                    visit(child, paragraph)
            elif tag == w("sdt"):
                for child in node:
                    if child.tag == w("sdtContent"):
                        visit(child, paragraph)

        for paragraph in self.model.paragraphs:
            current = []
            for child in paragraph.element:
                visit(child, paragraph)
            paragraph.text = "".join(current)
            paragraph.tokens = tokenize(paragraph.text)
            for bookmark in paragraph.element.iter(w("bookmarkStart")):
                name = bookmark.get(w("name"))
                if name is not None:
                    self.model.bookmark_paragraph.setdefault(name, paragraph.index)
        if field_stack:
            for field in field_stack:
                if _field_type("".join(field["instr"])) == "HYPERLINK" or field["occurrence"]:
                    issues.append(("RENDER_LINK_SOURCE_UNSUPPORTED", "FIELD_SHAPE"))
        for occurrence in occurrences:
            occurrence["tokens"] = tokenize(occurrence.pop("text"))
        return issues

    def _hyperlink_element(self, node, occurrence, issues) -> None:
        rel_id = node.get(r_attr("id"))
        anchor = node.get(w("anchor"))
        if node.get(w("docLocation")) is not None or (rel_id is None) == (anchor is None):
            issues.append(("RENDER_LINK_SOURCE_UNSUPPORTED", "ELEMENT_SHAPE"))
            return
        if rel_id is not None:
            occurrence["dest_kind"] = "EXTERNAL_URI"
            occurrence["rel_id"] = rel_id
        else:
            occurrence["dest_kind"] = "INTERNAL_ANCHOR"
            occurrence["bookmark"] = anchor

    def _parse_hyperlink_field(self, instruction, occurrence, issues) -> None:
        external = _HYPERLINK_EXTERNAL.match(instruction)
        internal = _HYPERLINK_INTERNAL.match(instruction)
        if external:
            occurrence["dest_kind"] = "EXTERNAL_URI"
            occurrence["target"] = external.group(1)
        elif internal:
            occurrence["dest_kind"] = "INTERNAL_ANCHOR"
            occurrence["bookmark"] = internal.group(1)
        else:
            issues.append(("RENDER_LINK_SOURCE_UNSUPPORTED", "FIELD_SHAPE"))

    # Style, list and font resolution ------------------------------------

    def run_levels(self, paragraph, run, run_chain) -> list:
        direct = _rpr(run)
        return (
            [direct]
            + [_rpr(style) for style in run_chain]
            + [_rpr(style) for style in paragraph.style_chain]
            + [_rpr(style) for style in paragraph.table_chain]
            + [self.styles.doc_rpr]
        )

    def check_hidden_text(self) -> None:
        """S3.08: w:vanish on a run (style levels used where their chains
        resolve; a broken chain is reported at S3.09)."""
        for paragraph in self.model.paragraphs:
            for record in paragraph.runs:
                try:
                    levels = self.run_levels(
                        paragraph_proxy(self.styles, paragraph), record.element, self.styles.run_chain(record.element)
                    )
                except _ChainError:
                    levels = [_rpr(record.element)]
                if _toggle(levels, "vanish"):
                    _s3("RENDER_HIDDEN_TEXT_DETECTED", None, "S3.08", paragraph_index=paragraph.index)

    def check_style_chains(self) -> None:
        """S3.09."""
        for paragraph in self.model.paragraphs:
            try:
                paragraph.style_chain = self.styles.paragraph_chain(paragraph.element)
                paragraph.table_chain = self.styles.table_chain(paragraph.table)
                for record in paragraph.runs:
                    self.styles.run_chain(record.element)
            except _ChainError as error:
                _s3(error.status, error.reason, "S3.09", paragraph_index=paragraph.index)

    def resolve_lists(self) -> None:
        """S3.10 STYLE_NUMBERING_RESOLUTION_V1 N1 to N8."""
        for paragraph in self.model.paragraphs:
            try:
                self._resolve_list(paragraph)
            except _ChainError as error:
                _s3(error.status, error.reason, "S3.10", paragraph_index=paragraph.index)

    def _resolve_list(self, paragraph) -> None:
        for style in paragraph.table_chain:
            ppr = style.find(w("pPr"))
            if ppr is not None and ppr.find(w("numPr")) is not None:
                raise _ChainError("RENDER_LIST_RESOLUTION_UNSUPPORTED", "TABLE_STYLE_NUMPR")
        holders = [paragraph.element.find(w("pPr"))] + [style.find(w("pPr")) for style in paragraph.style_chain]
        num_id = ilvl = None
        for holder in holders:
            numpr = holder.find(w("numPr")) if holder is not None else None
            if numpr is None:
                continue
            if num_id is None and numpr.find(w("numId")) is not None:
                num_id = numpr.find(w("numId")).get(w("val"))
            if ilvl is None and numpr.find(w("ilvl")) is not None:
                ilvl = numpr.find(w("ilvl")).get(w("val"))
        if num_id is None or num_id.strip() == "0":
            return
        if not re.match(r"^-?[0-9]+$", num_id.strip()):
            raise _ChainError("RENDER_LIST_RESOLUTION_UNSUPPORTED", "NUM_MISSING")
        num_value = int(num_id)
        level = 0
        if ilvl is not None:
            if not re.match(r"^[0-9]+$", ilvl.strip()) or not 0 <= int(ilvl) <= 8:
                raise _ChainError("RENDER_LIST_RESOLUTION_UNSUPPORTED", "ILVL_RANGE")
            level = int(ilvl)
        if self.numbering is None:
            raise _ChainError("RENDER_LIST_RESOLUTION_UNSUPPORTED", "NUMBERING_PART_MISSING")
        nums = [item for item in self.numbering.findall(w("num")) if item.get(w("numId")) == num_id.strip()]
        if not nums:
            raise _ChainError("RENDER_LIST_RESOLUTION_UNSUPPORTED", "NUM_MISSING")
        if len(nums) > 1:
            raise _ChainError("RENDER_LIST_RESOLUTION_UNSUPPORTED", "DUPLICATE_DEFINITION")
        abstract_ref = nums[0].find(w("abstractNumId"))
        abstract_id = abstract_ref.get(w("val")) if abstract_ref is not None else None
        abstracts = [
            item for item in self.numbering.findall(w("abstractNum"))
            if abstract_id is not None and item.get(w("abstractNumId")) == abstract_id
        ]
        if not abstracts:
            raise _ChainError("RENDER_LIST_RESOLUTION_UNSUPPORTED", "ABSTRACTNUM_MISSING")
        if len(abstracts) > 1:
            raise _ChainError("RENDER_LIST_RESOLUTION_UNSUPPORTED", "DUPLICATE_DEFINITION")
        abstract = abstracts[0]
        if abstract.find(w("numStyleLink")) is not None or abstract.find(w("styleLink")) is not None:
            raise _ChainError("RENDER_LIST_RESOLUTION_UNSUPPORTED", "NUM_STYLE_LINK")
        chain_ids = {style.get(w("styleId")) for style in paragraph.style_chain}
        for lvl in abstract.findall(w("lvl")):
            pstyle = lvl.find(w("pStyle"))
            if pstyle is not None and pstyle.get(w("val")) in chain_ids:
                raise _ChainError("RENDER_LIST_RESOLUTION_UNSUPPORTED", "LVL_PSTYLE_LINK")
        levels = [lvl for lvl in abstract.findall(w("lvl")) if lvl.get(w("ilvl")) == str(level)]
        if not levels:
            raise _ChainError("RENDER_LIST_RESOLUTION_UNSUPPORTED", "LVL_MISSING")
        if len(levels) > 1:
            raise _ChainError("RENDER_LIST_RESOLUTION_UNSUPPORTED", "DUPLICATE_DEFINITION")
        resolved = levels[0]
        overrides = [item for item in nums[0].findall(w("lvlOverride")) if item.get(w("ilvl")) == str(level)]
        if len(overrides) > 1:
            raise _ChainError("RENDER_LIST_RESOLUTION_UNSUPPORTED", "DUPLICATE_DEFINITION")
        if overrides and overrides[0].find(w("lvl")) is not None:
            resolved = overrides[0].find(w("lvl"))
        paragraph.level = resolved
        fmt = resolved.find(w("numFmt"))
        paragraph.list_semantics = {
            "ilvl": level,
            "numFmt": fmt.get(w("val")) if fmt is not None else None,
            "numId": num_value,
        }

    def marker_levels(self, paragraph) -> list:
        lvl_rpr = _rpr(paragraph.level)
        rstyle = lvl_rpr.find(w("rStyle")) if lvl_rpr is not None else None
        char_chain = self.styles.chain(rstyle.get(w("val"))) if rstyle is not None else []
        ppr = paragraph.element.find(w("pPr"))
        return (
            [lvl_rpr]
            + [_rpr(style) for style in char_chain]
            + [_rpr(ppr)]
            + [_rpr(style) for style in paragraph.style_chain]
            + [_rpr(style) for style in paragraph.table_chain]
            + [self.styles.doc_rpr]
        )

    def family_id(self, slot_value):
        """canonical_family_id of a slot value, or None when unmapped."""
        if slot_value is None:
            return None
        kind, value = slot_value
        if kind == "THEME":
            value = self.theme.get(value)
            if value is None:
                return None
        return self.docx_map.get(normalize_family(value))

    def check_list_markers(self) -> None:
        """S3.11 NUMFMT, S3.12 MARKER_UNSUPPORTED, S3.13 MARKER_UNMAPPED."""
        listed = [paragraph for paragraph in self.model.paragraphs if paragraph.level is not None]
        for paragraph in listed:
            if paragraph.list_semantics["numFmt"] != "bullet":
                _s3("RENDER_LIST_NUMFMT_UNSUPPORTED", None, "S3.11", paragraph_index=paragraph.index)
        for paragraph in listed:
            level = paragraph.level
            text_element = level.find(w("lvlText"))
            text = text_element.get(w("val")) if text_element is not None else None
            suffix = level.find(w("suff"))
            if level.find(w("lvlPicBulletId")) is not None:
                _s3("RENDER_LIST_MARKER_UNSUPPORTED", "PICTURE_BULLET", "S3.12", paragraph_index=paragraph.index)
            if text is None or "%" in text or len(text) != 1:
                _s3("RENDER_LIST_MARKER_UNSUPPORTED", "LVL_TEXT", "S3.12", paragraph_index=paragraph.index)
            if suffix is not None and suffix.get(w("val")) == "nothing":
                _s3("RENDER_LIST_MARKER_UNSUPPORTED", "SUFFIX_NOTHING", "S3.12", paragraph_index=paragraph.index)
            try:
                levels = self.marker_levels(paragraph)
            except _ChainError as error:
                _s3(error.status, error.reason, "S3.12", paragraph_index=paragraph.index)
            if _hint_denied(levels):
                _s3("RENDER_LIST_MARKER_UNSUPPORTED", "HINT", "S3.12", paragraph_index=paragraph.index)
            code_point = ord(text)
            paragraph.marker_code_point = code_point
            slot = "ascii" if code_point < 0x80 else "hAnsi"
            family = self.family_id(_slot_value(levels, slot))
            if family is not None:
                paragraph.marker_identity = (family, _face(levels))
                expected = self.glyph_map.get((family, code_point))
                if expected is None and not 0xE000 <= code_point <= 0xF8FF:
                    expected = chr(code_point)
                if expected is not None:
                    if len(tokenize(expected)) != 1:
                        _s3("RENDER_LIST_MARKER_UNSUPPORTED", "MARKER_TOKEN", "S3.12", paragraph_index=paragraph.index)
                    paragraph.marker_expected = tokenize(expected)[0]
            if not paragraph.tokens:
                _s3("RENDER_LIST_MARKER_UNSUPPORTED", "EMPTY_LIST_ITEM", "S3.12", paragraph_index=paragraph.index)
        for paragraph in listed:
            if paragraph.marker_identity is not None and paragraph.marker_expected is None:
                _s3("RENDER_LIST_MARKER_UNMAPPED", None, "S3.13", paragraph_index=paragraph.index,
                    code_point=paragraph.marker_code_point)

    def counted_runs(self, paragraph):
        for record in paragraph.runs:
            if is_counted_text(record.text):
                yield record

    def check_scripts_and_cases(self) -> None:
        """S3.14 EAST_ASIAN_OR_COMPLEX_SCRIPT, then S3.15 CASE_TRANSFORM."""
        for paragraph in self.model.paragraphs:
            for record in self.counted_runs(paragraph):
                levels = self.run_levels(paragraph, record.element, self.styles.run_chain(record.element))
                if _east_asian(record.text) or _hint_denied(levels):
                    _s3("RENDER_TEXT_CONSTRUCT_UNSUPPORTED", "EAST_ASIAN_OR_COMPLEX_SCRIPT", "S3.14",
                        paragraph_index=paragraph.index)
        for paragraph in self.model.paragraphs:
            for record in self.counted_runs(paragraph):
                levels = self.run_levels(paragraph, record.element, self.styles.run_chain(record.element))
                if _toggle(levels, "caps") or _toggle(levels, "smallCaps"):
                    _s3("RENDER_CASE_TRANSFORM_UNSUPPORTED", None, "S3.15", paragraph_index=paragraph.index)

    def check_font_declarations(self) -> None:
        """S3.16: every counted run slot and every collected declaration
        maps through docx_family_to_canonical."""
        for paragraph in self.model.paragraphs:
            for record in self.counted_runs(paragraph):
                levels = self.run_levels(paragraph, record.element, self.styles.run_chain(record.element))
                face = _face(levels)
                counted = [ch for ch in normalize_text(record.text) if ch not in SEPARATOR_CHARACTERS]
                slots = []
                if any(ord(ch) < 0x80 for ch in counted):
                    slots.append("ascii")
                if any(ord(ch) >= 0x80 for ch in counted):
                    slots.append("hAnsi")
                for slot in slots:
                    family = self.family_id(_slot_value(levels, slot))
                    if family is None:
                        _s3("RENDER_FONT_DECLARATION_UNMAPPED", "RUN_SLOT", "S3.16",
                            paragraph_index=paragraph.index, font_slot=slot)
                    paragraph.expected_identities.add((family, face))
            for fonts in self._declared_font_elements(paragraph):
                for slot in ("ascii", "hAnsi"):
                    theme = fonts.get(w(slot + "Theme"))
                    literal = fonts.get(w(slot))
                    value = ("THEME", theme) if theme is not None else ("LITERAL", literal) if literal is not None else None
                    if value is not None and self.family_id(value) is None:
                        _s3("RENDER_FONT_DECLARATION_UNMAPPED", "DECLARATION", "S3.16",
                            paragraph_index=paragraph.index, font_slot=slot)
            if paragraph.level is not None:
                if paragraph.marker_identity is None:
                    _s3("RENDER_FONT_DECLARATION_UNMAPPED", "MARKER", "S3.16", paragraph_index=paragraph.index)
                paragraph.expected_identities.add(paragraph.marker_identity)

    def _declared_font_elements(self, paragraph):
        holders = [record.element for record in paragraph.runs]
        for record in paragraph.runs:
            holders.extend(self.styles.run_chain(record.element))
        holders.extend(paragraph.style_chain)
        holders.extend(paragraph.table_chain)
        ppr = paragraph.element.find(w("pPr"))
        if ppr is not None:
            holders.append(ppr)
        if paragraph.level is not None:
            holders.append(paragraph.level)
        found = []
        for holder in holders:
            rpr = _rpr(holder)
            if rpr is not None and rpr.find(w("rFonts")) is not None:
                found.append(rpr.find(w("rFonts")))
        if self.styles.doc_rpr is not None and self.styles.doc_rpr.find(w("rFonts")) is not None:
            found.append(self.styles.doc_rpr.find(w("rFonts")))
        return found

    def check_links(self, issues: list) -> None:
        """S3.17 to S3.20 (HYPERLINK_OCCURRENCE_MODEL_V1 source side)."""
        external_links = {
            rel_id for rel_id, item in self.doc_rels.items()
            if item["external"] and is_hyperlink_type(item["type"])
        }
        referenced = set()
        for name in self.text_parts():
            relationships = {item["id"]: item for item in self.package.relationships_of(name)}
            for element in self.package.xml[name].iter():
                for attribute, value in element.attrib.items():
                    if not attribute.startswith("{" + NS_R + "}"):
                        continue
                    relationship = relationships.get(value)
                    if relationship is None or not (relationship["external"] and is_hyperlink_type(relationship["type"])):
                        continue
                    referenced.add((name, value))
                    in_scope = name == MAIN_PART and element.tag == w("hyperlink") and attribute == r_attr("id")
                    if not in_scope:
                        _s3("RENDER_LINK_SOURCE_CONSTRUCT_UNSUPPORTED", None, "S3.17", part=name,
                            element=element.tag.rpartition("}")[2])
        for status, reason in issues:
            _s3(status, reason, "S3.18")
        for occurrence in self.model.occurrences:
            if occurrence["dest_kind"] == "EXTERNAL_URI" and occurrence["rel_id"] is not None:
                if occurrence["rel_id"] not in external_links:
                    _s3("RENDER_LINK_SOURCE_UNRESOLVED", "RELATIONSHIP", "S3.19",
                        paragraph_index=occurrence["paragraph_index"])
                occurrence["target"] = self.doc_rels[occurrence["rel_id"]]["target"]
            if occurrence["dest_kind"] == "INTERNAL_ANCHOR" and occurrence["bookmark"] not in self.model.bookmark_paragraph:
                _s3("RENDER_LINK_SOURCE_UNRESOLVED", "BOOKMARK", "S3.19",
                    paragraph_index=occurrence["paragraph_index"])
        for occurrence in self.model.occurrences:
            occurrence["dest"] = None
            if occurrence["dest_kind"] == "EXTERNAL_URI":
                canonical = canonicalize_uri(occurrence["target"])
                if canonical is None:
                    _s3("RENDER_LINK_URI_UNSUPPORTED", None, "S3.20", paragraph_index=occurrence["paragraph_index"])
                occurrence["dest"] = canonical
            else:
                occurrence["dest"] = occurrence["bookmark"]
        self.model.orphan_relationships = sorted(
            rel_id for rel_id in external_links if (MAIN_PART, rel_id) not in referenced
        )

    def check_structure_map(self) -> None:
        """S3.21 to S3.25 (structure map V1 to V5; V6 admits any string)."""
        structure_map = self.structure_map
        if structure_map is None:
            _s3("RENDER_STRUCTURE_MAP_REQUIRED", None, "S3.21")
        if not isinstance(structure_map, list):
            _s3("RENDER_STRUCTURE_MAP_INVALID", "SHAPE", "S3.22")
        for entry in structure_map:
            if not _structure_entry_shape_ok(entry):
                _s3("RENDER_STRUCTURE_MAP_INVALID", "SHAPE", "S3.22")
        previous = -1
        count = len(self.model.paragraphs)
        for entry in structure_map:
            index = entry["paragraph_index"]
            if index <= previous or not 0 <= index < count:
                _s3("RENDER_STRUCTURE_MAP_INVALID", "ORDER_OR_RANGE", "S3.22")
            previous = index
        for entry in structure_map:
            if tokenize(entry["paragraph_text"]) != self.model.paragraphs[entry["paragraph_index"]].tokens:
                _s3("RENDER_STRUCTURE_MAP_TEXT_MISMATCH", None, "S3.23", paragraph_index=entry["paragraph_index"])
        for entry in structure_map:
            if entry["list_semantics"] != self.model.paragraphs[entry["paragraph_index"]].list_semantics:
                _s3("RENDER_LIST_SEMANTICS_MISMATCH", None, "S3.24", paragraph_index=entry["paragraph_index"])
        mapped = {entry["paragraph_index"] for entry in structure_map}
        for paragraph in self.model.paragraphs:
            if paragraph.tokens and paragraph.index not in mapped:
                _s3("RENDER_STRUCTURE_MAP_INCOMPLETE", None, "S3.25", paragraph_index=paragraph.index)
        self.model.structure_map = [dict(entry) for entry in structure_map]

    def build(self) -> SourceModel:
        self.check_constructs()
        issues = self.collect_text()
        self.check_hidden_text()
        self.check_style_chains()
        self.resolve_lists()
        self.check_list_markers()
        self.check_scripts_and_cases()
        self.check_font_declarations()
        self.check_links(issues)
        self.check_structure_map()
        settings = self._part("settings")
        self.model.auto_hyphenation = bool(
            settings is not None and _toggle([settings], "autoHyphenation")
        )
        return self.model


class paragraph_proxy:
    """A paragraph view whose style chains are resolved on demand (S3.08
    runs before S3.09 assigns them)."""

    def __init__(self, styles: _Styles, paragraph: SourceParagraph):
        self.style_chain = styles.paragraph_chain(paragraph.element)
        self.table_chain = styles.table_chain(paragraph.table)


def _structure_entry_shape_ok(entry) -> bool:
    if not isinstance(entry, dict) or set(entry) != {"paragraph_index", "content_type", "list_semantics", "paragraph_text"}:
        return False
    if not _is_int(entry["paragraph_index"]) or not isinstance(entry["content_type"], str):
        return False
    if not isinstance(entry["paragraph_text"], str):
        return False
    semantics = entry["list_semantics"]
    if semantics is None:
        return True
    return (
        isinstance(semantics, dict)
        and set(semantics) == {"ilvl", "numFmt", "numId"}
        and _is_int(semantics["ilvl"])
        and semantics["numFmt"] == "bullet"
        and _is_int(semantics["numId"])
    )


def build_source_model(package: DocxPackage, manifest: dict, structure_map) -> SourceModel:
    """S3.01 to S3.25 over the pre-flighted package and verified manifest."""
    return _SourceBuilder(package, manifest, structure_map).build()


# =============================================================================
# S4 / S5 SANDBOX, CONVERSION, PDF BYTES AND ENTRY BINDING
# =============================================================================

PROFILE_RENDER = "RENDER"
PROFILE_INSPECTION = "INSPECTION"
INSPECTION_PYCACHE_PATH = SANDBOX_TMP_PATH + "/pycache"
PROCESS_STDERR_MAX_BYTES = 65536
RENDER_STDOUT_MAX_BYTES = 65536
_FORBIDDEN_WHOLE_BINDS = ("/", "/etc", "/home", "/root", "/workspaces", "/var", "/run", "/mnt", "/opt", "/srv")


class RuntimePaths:
    """Absolute host paths of the pinned executables and the inspection
    read-only mounts. Each must be covered by a CONTENT_BINDING_V1 root;
    the adapter re-checks that coverage before building any argv."""

    def __init__(self, bwrap_path: str, soffice_path: str, inspection_read_only_paths: tuple) -> None:
        self.bwrap_path = bwrap_path
        self.soffice_path = soffice_path
        self.inspection_read_only_paths = tuple(sorted(set(inspection_read_only_paths)))


def _isolation(reason: str, slot: str = "S4.01", **evidence):
    fail("RENDER_ISOLATION_UNAVAILABLE", reason, None, slot, **evidence)


def home_path(manifest: dict) -> str:
    homes = [path for path in manifest["sandbox_tmpfs_paths"] if path != SANDBOX_TMP_PATH]
    return homes[0]


def env_allowlist(manifest: dict, profile: str) -> list:
    """[[name, value], ...] sorted by name."""
    values = {
        "HOME": home_path(manifest),
        "TMPDIR": SANDBOX_TMP_PATH,
        "PATH": manifest["sandbox_path"],
        "LANG": manifest["locale"],
        "LC_ALL": manifest["locale"],
        "TZ": manifest["timezone"],
        "SOURCE_DATE_EPOCH": str(manifest["source_date_epoch"]),
        "FONTCONFIG_FILE": manifest["fontconfig_file"],
    }
    names = RENDER_ENV_NAMES if profile == PROFILE_RENDER else INSPECTION_ENV_NAMES
    return sorted([name, values[name]] for name in names)


def _root_covers(manifest: dict, path: str) -> bool:
    for root in manifest["content_binding"]["roots"]:
        if root["kind"] in ("FILE", "LINK") and root["path"] == path:
            return True
        if root["kind"] in ("TREE", "STDLIB_TREE") and _posix_under(path, root["path"]):
            return True
    return False


def _posix_under(path: str, base: str) -> bool:
    return path == base or path.startswith(base.rstrip("/") + "/")


def check_runtime_paths(manifest: dict, paths: RuntimePaths) -> None:
    """S4.01 data checks that precede every self-test launch."""
    canaries = manifest["sandbox_forbidden_canary_paths"]
    probe = manifest["sandbox_probe_interpreter_path"]
    if any(_posix_under(probe, canary) for canary in canaries):
        _isolation("PROBE_INTERPRETER_UNDER_CANARY")
    for mount in manifest["sandbox_read_only_paths"]:
        if mount in _FORBIDDEN_WHOLE_BINDS or any(_posix_under(mount, canary) for canary in canaries):
            _isolation("FORBIDDEN_MOUNT", path=mount)
    for label, path in (("BWRAP", paths.bwrap_path), ("SOFFICE", paths.soffice_path)):
        if not path.startswith("/") or not _root_covers(manifest, path):
            _isolation("EXECUTABLE_UNBOUND", executable=label)
    for mount in paths.inspection_read_only_paths:
        if (
            not mount.startswith("/")
            or mount in _FORBIDDEN_WHOLE_BINDS
            or any(_posix_under(mount, canary) for canary in canaries)
            or not _root_covers(manifest, mount)
        ):
            _isolation("INSPECTION_MOUNT_UNBOUND", "S4.02", path=mount)


def build_argv_shared(manifest: dict, profile: str, inspection_paths: tuple = ()) -> list:
    """The ordered bubblewrap argument list of SANDBOX_PROFILE_V1 with the
    per-run placeholders (probe segments are never part of it)."""
    argv = list(REQUIRED_SANDBOX_FLAGS)
    argv.append("--clearenv")
    for name, value in env_allowlist(manifest, profile):
        argv += ["--setenv", name, value]
    argv += ["--proc", "/proc", "--dev", "/dev"]
    for directory in manifest["sandbox_dirs"]:
        argv += ["--dir", directory]
    for link in sorted(manifest["sandbox_symlinks"], key=lambda item: item["path"]):
        argv += ["--symlink", link["target"], link["path"]]
    mounts = manifest["sandbox_read_only_paths"] if profile == PROFILE_RENDER else list(inspection_paths)
    for path in mounts:
        argv += ["--ro-bind", path, path]
    size = str(manifest["sandbox_tmpfs_size_bytes"])
    for path in manifest["sandbox_tmpfs_paths"]:
        argv += ["--size", size, "--tmpfs", path]
    if profile == PROFILE_RENDER:
        argv += ["--bind", RUN_INPUT_PLACEHOLDER, SANDBOX_INPUT_DIR]
        argv += ["--bind", RUN_OUTPUT_PLACEHOLDER, SANDBOX_OUTPUT_DIR]
        argv += ["--bind", RUN_PROFILE_PLACEHOLDER, SANDBOX_PROFILE_DIR]
    else:
        argv += ["--ro-bind-data", ENTRY_FD_PLACEHOLDER, SANDBOX_ENTRY_PATH]
    argv += ["--remount-ro", "/"]
    return argv


def sandbox_profile_digest(manifest: dict, profile: str, inspection_paths: tuple = ()) -> str:
    return canonical_digest(
        {
            "spec": "SANDBOX_PROFILE_V1",
            "argv_shared": build_argv_shared(manifest, profile, inspection_paths),
            "bwrap_version": manifest["bubblewrap_version"],
            "env_allowlist": env_allowlist(manifest, profile),
            "capability_mechanism": manifest["sandbox_capability_mechanism"],
        }
    )


def substitute_placeholders(argv_shared: list, run_dirs: dict = None, entry_fd: int = None) -> list:
    substituted = []
    for item in argv_shared:
        if run_dirs and item in run_dirs:
            substituted.append(run_dirs[item])
        elif item == ENTRY_FD_PLACEHOLDER and entry_fd is not None:
            substituted.append(str(entry_fd))
        else:
            substituted.append(item)
    return substituted


def conversion_argv(soffice_path: str, manifest: dict) -> list:
    return [
        soffice_path,
        "--headless",
        "--norestore",
        "--nologo",
        "--nolockcheck",
        "--nodefault",
        "-env:UserInstallation=file://" + SANDBOX_PROFILE_DIR,
        "--convert-to",
        manifest["pdf_export_filter"],
        "--outdir",
        SANDBOX_OUTPUT_DIR,
        SANDBOX_INPUT_DIR + "/" + INPUT_FILE_NAME,
    ]


def inspection_argv(manifest: dict) -> list:
    return [
        manifest["operator_python_prefix"].rstrip("/") + "/bin/python",
        "-I", "-S", "-B", "-X", "pycache_prefix=" + INSPECTION_PYCACHE_PATH,
        SANDBOX_ENTRY_PATH,
    ]


_PROFILE_REGISTRY = (
    '<?xml version="1.0" encoding="UTF-8"?>\n'
    '<oor:items xmlns:oor="http://openoffice.org/2001/registry" '
    'xmlns:xs="http://www.w3.org/2001/XMLSchema" '
    'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">\n'
    '<item oor:path="/org.openoffice.Office.Common/Security/Scripting">'
    '<prop oor:name="MacroSecurityLevel" oor:op="fuse"><value>3</value></prop></item>\n'
    '<item oor:path="/org.openoffice.Office.Common/Security/Scripting">'
    '<prop oor:name="DisableMacrosExecution" oor:op="fuse"><value>true</value></prop></item>\n'
    "</oor:items>\n"
)


class RunTempLayout:
    """One bounded per-run root holding the input, output and LibreOffice
    profile directories; removed in a finally path after every run."""

    def __init__(self, parent: str = None) -> None:
        self.parent = parent
        self.root = None
        self.removed = False

    def __enter__(self) -> "RunTempLayout":
        self.root = tempfile.mkdtemp(prefix="career-os-render-", dir=self.parent)
        for name in ("input", "output", "profile"):
            os.mkdir(os.path.join(self.root, name), 0o700)
        user_dir = os.path.join(self.profile_dir, "user")
        os.mkdir(user_dir, 0o700)
        with open(os.path.join(user_dir, "registrymodifications.xcu"), "w", encoding="utf-8") as handle:
            handle.write(_PROFILE_REGISTRY)
        return self

    @property
    def input_dir(self) -> str:
        return os.path.join(self.root, "input")

    @property
    def output_dir(self) -> str:
        return os.path.join(self.root, "output")

    @property
    def profile_dir(self) -> str:
        return os.path.join(self.root, "profile")

    def run_dirs(self) -> dict:
        return {
            RUN_INPUT_PLACEHOLDER: self.input_dir,
            RUN_OUTPUT_PLACEHOLDER: self.output_dir,
            RUN_PROFILE_PLACEHOLDER: self.profile_dir,
        }

    def __exit__(self, *exc_info) -> bool:
        if self.root is not None:
            shutil.rmtree(self.root, ignore_errors=True)
            self.removed = not os.path.lexists(self.root)
        return False


class ProcessResult:
    def __init__(self, returncode, stdout=b"", stderr=b"", timed_out=False, cap_killed=False, launched=True):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
        self.timed_out = timed_out
        self.cap_killed = cap_killed
        self.launched = launched

    @property
    def signal(self):
        """The terminating signal the parent did not send, else None."""
        if self.returncode is not None and self.returncode < 0 and not (self.timed_out or self.cap_killed):
            return -self.returncode
        return None


class ProcessRunner:
    """argv-list process launches with a fresh session (process group),
    a wall-clock deadline with group kill, an optional RLIMIT_AS and
    bounded reads of stdout and stderr. Never shell=True."""

    def run(self, argv, stdin_bytes=None, timeout=None, pass_fds=(), memory_limit=None, stdout_limit=RENDER_STDOUT_MAX_BYTES):
        preexec = None
        if memory_limit is not None:
            def preexec():
                import resource

                resource.setrlimit(resource.RLIMIT_AS, (memory_limit, memory_limit))
        try:
            process = subprocess.Popen(
                argv,
                stdin=subprocess.PIPE if stdin_bytes is not None else subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env={},
                close_fds=True,
                pass_fds=tuple(pass_fds),
                start_new_session=True,
                preexec_fn=preexec,
                shell=False,
            )
        except OSError:
            return ProcessResult(None, launched=False)
        received = bytearray()
        errors = bytearray()
        state = {"cap": False}

        def pump_stdout():
            while len(received) < stdout_limit:
                chunk = process.stdout.read(min(65536, stdout_limit - len(received)))
                if not chunk:
                    return
                received.extend(chunk)
            if process.stdout.read(1):
                state["cap"] = True
                self._kill(process)

        def pump_stderr():
            while True:
                chunk = process.stderr.read(65536)
                if not chunk:
                    return
                if len(errors) < PROCESS_STDERR_MAX_BYTES:
                    errors.extend(chunk[: PROCESS_STDERR_MAX_BYTES - len(errors)])

        def feed_stdin():
            try:
                process.stdin.write(stdin_bytes)
            except OSError:
                pass
            finally:
                try:
                    process.stdin.close()
                except OSError:
                    pass

        threads = [threading.Thread(target=pump_stdout, daemon=True), threading.Thread(target=pump_stderr, daemon=True)]
        if stdin_bytes is not None:
            threads.append(threading.Thread(target=feed_stdin, daemon=True))
        for thread in threads:
            thread.start()
        timed_out = False
        try:
            process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            self._kill(process)
            process.wait()
        for thread in threads:
            thread.join(timeout=5)
        return ProcessResult(
            process.returncode, bytes(received), bytes(errors), timed_out=timed_out, cap_killed=state["cap"],
        )

    @staticmethod
    def _kill(process) -> None:
        try:
            os.killpg(process.pid, 9)
        except (AttributeError, OSError):
            try:
                process.kill()
            except OSError:
                pass


def _output_invalid(sub_check: str):
    fail("RENDER_SANDBOX_RUNTIME_INCOMPLETE", "OUTPUT_INVALID", sub_check, "S5.02", sub_check=sub_check)


_O_FLAGS = (
    os.O_RDONLY
    | getattr(os, "O_NOFOLLOW", 0)
    | getattr(os, "O_NONBLOCK", 0)
    | getattr(os, "O_CLOEXEC", 0)
    | getattr(os, "O_BINARY", 0)
)


def read_identity_checked(path: str, limit: int, on_fail) -> bytes:
    """PDF_BYTES_BINDING_V1 step (2): lstat, a single open, fstat identity,
    read to end of file plus one empty read."""
    try:
        before = os.lstat(path)
    except FileNotFoundError:
        on_fail("MISSING")
    except OSError:
        on_fail("NOT_REGULAR")
    if not stat.S_ISREG(before.st_mode):
        on_fail("NOT_REGULAR")
    if before.st_size > limit:
        on_fail("OVERSIZE")
    try:
        descriptor = os.open(path, _O_FLAGS)
    except FileNotFoundError:
        on_fail("MISSING")
    except OSError:
        on_fail("NOT_REGULAR")
    try:
        after = os.fstat(descriptor)
        if not stat.S_ISREG(after.st_mode) or (after.st_dev, after.st_ino) != (before.st_dev, before.st_ino):
            on_fail("NOT_REGULAR")
        if after.st_size > limit:
            on_fail("OVERSIZE")
        chunks = []
        total = 0
        try:
            while True:
                chunk = os.read(descriptor, 1 << 20)
                if not chunk:
                    break
                total += len(chunk)
                if total > limit:
                    on_fail("OVERSIZE")
                chunks.append(chunk)
            if os.read(descriptor, 1):
                on_fail("READ")
        except OSError:
            on_fail("READ")
    finally:
        os.close(descriptor)
    return b"".join(chunks)


def take_pdf_snapshot(output_dir: str) -> bytes:
    """PDF_SNAPSHOT plus the parent-evaluated VALID_OUTPUT_V1 sub-checks
    MISSING, NOT_REGULAR, OVERSIZE, EMPTY and SIGNATURE."""
    entries = sorted(os.listdir(output_dir)) if os.path.isdir(output_dir) else []
    if entries and entries != [OUTPUT_FILE_NAME]:
        _output_invalid("NOT_REGULAR" if OUTPUT_FILE_NAME in entries else "MISSING")
    snapshot = read_identity_checked(
        os.path.join(output_dir, OUTPUT_FILE_NAME), INSPECTION_LIMITS_V1["inspection_max_pdf_bytes"], _output_invalid
    )
    if not snapshot:
        _output_invalid("EMPTY")
    if snapshot[:5] != b"%PDF-":
        _output_invalid("SIGNATURE")
    return snapshot


def deliver_pdf(snapshot: bytes, pdf_sha256: str, delivery_dir: str) -> str:
    """PDF_BYTES_BINDING_V1 step (6) and S12.01."""
    path = os.path.join(delivery_dir, DELIVERED_PDF_NAME)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_BINARY", 0)

    def mismatch(sub_check):
        fail("RENDER_DELIVERY_BYTES_MISMATCH", None, None, "S12.01", sub_check=sub_check)

    try:
        descriptor = os.open(path, flags, 0o644)
    except OSError:
        mismatch("CREATE")
    try:
        view = memoryview(snapshot)
        while view:
            written = os.write(descriptor, view)
            view = view[written:]
    finally:
        os.close(descriptor)
    reread = read_identity_checked(path, len(snapshot), mismatch)
    if len(reread) != len(snapshot) or sha256_hex(reread) != pdf_sha256:
        mismatch("REREAD")
    return path


class EntryBindingError(Exception):
    pass


class EntryDescriptor:
    def __init__(self, fd: int, evidence: dict) -> None:
        self.fd = fd
        self.evidence = evidence

    def close(self) -> None:
        if self.fd is not None:
            os.close(self.fd)
            self.fd = None


def bind_entry_descriptor(entry_bytes: bytes, entry_sha256: str) -> EntryDescriptor:
    """ENTRY_DESCRIPTOR_BINDING_V1 steps (1) to (6); the caller performs
    step (7) and maps EntryBindingError to its slot."""
    fd = None
    try:
        import fcntl

        evidence = {}
        memfd_create = getattr(os, "memfd_create", None)
        if memfd_create is not None:
            fd = memfd_create("inspection_entry", os.MFD_CLOEXEC | os.MFD_ALLOW_SEALING)
            _write_all(fd, entry_bytes)
            seals = fcntl.F_SEAL_SEAL | fcntl.F_SEAL_SHRINK | fcntl.F_SEAL_GROW | fcntl.F_SEAL_WRITE
            fcntl.fcntl(fd, fcntl.F_ADD_SEALS, seals)
            observed = fcntl.fcntl(fd, fcntl.F_GET_SEALS)
            if observed & seals != seals:
                raise EntryBindingError("SEALS")
            evidence.update({"kind": "MEMFD", "seals": observed})
        else:
            private = tempfile.mkdtemp(prefix="career-os-entry-")
            path = os.path.join(private, "entry")
            fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_EXCL | getattr(os, "O_CLOEXEC", 0), 0o400)
            os.unlink(path)
            os.rmdir(private)
            _write_all(fd, entry_bytes)
            if os.fstat(fd).st_nlink != 0:
                raise EntryBindingError("NLINK")
            evidence.update({"kind": "UNLINKED_TEMP", "st_nlink": 0})
        if os.lseek(fd, 0, os.SEEK_SET) != 0 or os.lseek(fd, 0, os.SEEK_CUR) != 0:
            raise EntryBindingError("OFFSET")
        info = os.fstat(fd)
        if info.st_size != len(entry_bytes):
            raise EntryBindingError("SIZE")
        content = bytearray()
        while len(content) < info.st_size:
            chunk = os.pread(fd, info.st_size - len(content), len(content))
            if not chunk:
                break
            content.extend(chunk)
        if os.pread(fd, 1, info.st_size) or bytes(content) != entry_bytes or sha256_hex(bytes(content)) != entry_sha256:
            raise EntryBindingError("CONTENT")
        if os.lseek(fd, 0, os.SEEK_SET) != 0:
            raise EntryBindingError("OFFSET")
        evidence.update({"size": info.st_size, "sha256": entry_sha256, "st_dev": info.st_dev, "st_ino": info.st_ino})
        return EntryDescriptor(fd, evidence)
    except (ImportError, OSError, AttributeError, EntryBindingError) as exc:
        if fd is not None:
            os.close(fd)
        raise EntryBindingError(type(exc).__name__) from exc


def _write_all(fd: int, data: bytes) -> None:
    view = memoryview(data)
    while view:
        written = os.write(fd, view)
        view = view[written:]


# =============================================================================
# CHILD_PROTOCOL_V1 (parent validation)
# =============================================================================

PROTOCOL_ID = "CHILD_PROTOCOL_V1"
RESOURCE_CATEGORIES_V1 = ("ExtGState", "ColorSpace", "Pattern", "Shading", "XObject", "Font", "Properties")
_CATALOG_REASONS = (
    "CATALOG_MALFORMED", "ACROFORM_PRESENT", "OPEN_ACTION_PRESENT", "CATALOG_AA_PRESENT", "NAMES_PRESENT",
    "AF_PRESENT", "COLLECTION_PRESENT", "PERMS_PRESENT", "REQUIREMENTS_PRESENT", "OUTLINES_PRESENT",
    "URI_BASE_PRESENT",
)
_LIMIT = ("RENDER_PDF_INSPECTION_FAILED", ("INSPECTION_LIMIT",))

CHILD_FAIL_CLOSED_SET_V1 = {
    "S5.02": (
        ("RENDER_SANDBOX_RUNTIME_INCOMPLETE", ("OUTPUT_INVALID",), ("ENCRYPTED", "PYPDF_OPEN", "PDFMINER_OPEN")),
        ("RENDER_SANDBOX_RUNTIME_INCOMPLETE", ("INSPECTION_RUNTIME_INCOMPLETE",), ("START_STATE",)),
        _LIMIT + (("MEMORY",),),
    ),
    "S5.03": (
        ("RENDER_DOCUMENT_STATE_UNSUPPORTED", _CATALOG_REASONS, (None,)),
        _LIMIT + (("CATALOG_KEYS", "INFO_KEYS", "MEMORY", "EVIDENCE_BYTES"),),
        ("RENDER_PDF_INSPECTION_FAILED", ("DOCUMENT_STATE_READ",), (None,)),
    ),
    "S6": (
        ("RENDER_COORDINATE_SPACE_UNVERIFIED", ("STACK_PAGE_COUNT", "STACK_PAGE_SIZE", "STACK_TEXT_GEOMETRY"), (None,)),
        _LIMIT + ((
            "PAGE_COUNT", "FORM_DEPTH", "FORM_EXECUTIONS", "RESOURCE_ENTRIES", "FONT_COUNT", "CONTENT_FILTER",
            "DECODED_CONTENT_BYTES", "DECODED_OTHER_BYTES", "CONTENT_OPERATORS_PAGE",
            "CONTENT_OPERATORS_DOCUMENT", "INDIRECT_RESOLUTIONS", "CHAR_COUNT", "MEMORY", "EVIDENCE_BYTES",
        ),),
        ("RENDER_PDF_INSPECTION_FAILED", ("PRE_SCAN_READ",),
         ("ZLIB_ERROR", "FLATE_INCOMPLETE", "OBJECT_READ", "RAW_BYTES_READ", "CONTENT_PARSE")),
        ("RENDER_PDF_INSPECTION_FAILED", ("PAGE_ENUMERATION", "PAGE_FACTS", "DOCUMENT_STATE_READ", "CHAR_EXTRACTION"),
         (None,)),
        ("RENDER_PAGE_ROTATION_DENIED", (None,), (None,)),
        ("RENDER_PAGEBOX_MISMATCH", ("BOX_MALFORMED",), (None, "MEDIABOX_ABSENT")),
        ("RENDER_PAGEBOX_MISMATCH", ("BOX_REVERSED", "NONZERO_ORIGIN", "CROPBOX_DIFFERS", "USER_UNIT",
                                     "VISIBLE_RECT_SIZE"), (None,)),
        ("RENDER_DOCUMENT_STATE_UNSUPPORTED", ("PAGE_AA_PRESENT",), (None,)),
        ("RENDER_PAGE_SIZE_UNSUPPORTED", (None,), (None,)),
        ("RENDER_PDF_INSPECTION_FAILED", ("PARSER_AMBIGUITY",),
         ("STRICT_REREAD", "NULL_RESOURCES", "NAME_DOMAIN", "STREAM_MISMATCH")),
    ),
    "S7": (
        _LIMIT + (("CONTENT_STREAMS", "INDIRECT_RESOLUTIONS", "MEMORY", "EVIDENCE_BYTES"),),
        ("RENDER_TEXT_STATE_UNOBSERVABLE", (
            "TRACKER_FAILURE", "STACK_UNBALANCED", "MISSING_RESOURCE", "BAD_OPERAND", "FORM_LIMIT",
            "ANNOTATION_APPEARANCE", "PATTERN_FILL", "VISUAL_STATE_UNPROVABLE", "NO_CORRESPONDENCE",
        ), (None,)),
        ("RENDER_TEXT_STATE_UNOBSERVABLE", ("COLOR_UNOBSERVABLE",),
         ("CS_UNSUPPORTED", "CS_WITHOUT_COLOR", "NCOLOR_MISSING", "NCOLOR_INCONSISTENT")),
        ("RENDER_HIDDEN_TEXT_DETECTED", ("RENDER_MODE_INVISIBLE", "ZERO_OPACITY"), (None,)),
        ("RENDER_TEXT_POLICY_SUSPECT", ("RENDER_MODE_NOT_FILL_ONLY", "LOW_OPACITY", "SMALL_TEXT", "NEAR_WHITE"),
         (None,)),
        ("RENDER_ATTRIBUTION_INCOMPLETE", ("CHAR_UNOBSERVABLE", "NON_HORIZONTAL_TEXT", "EMPTY_TOKEN_LINE"), (None,)),
        ("RENDER_PDF_INSPECTION_FAILED", ("CHAR_EXTRACTION",), (None,)),
    ),
    "S9": (
        ("RENDER_FONT_SUBSTITUTION_UNAPPROVED", ("FONT_STRUCTURE_MALFORMED",), (
            "RESOURCES_MALFORMED", "FONT_DICT_MALFORMED", "FONT_REF_UNRESOLVED", "FONT_ENTRY_NOT_DICT",
            "SUBTYPE_INVALID", "DESCENDANTS_INVALID", "DESCENDANT_ENTRY_INVALID", "DESCRIPTOR_MALFORMED",
            "FONTNAME_MALFORMED",
        )),
        ("RENDER_FONT_TYPE3_DENIED", (None,), (None,)),
        ("RENDER_FONT_NOT_EMBEDDED", (None, "DESCRIPTOR_INCOMPLETE"), (None,)),
        _LIMIT + (("INDIRECT_RESOLUTIONS", "MEMORY", "EVIDENCE_BYTES"),),
        ("RENDER_PDF_INSPECTION_FAILED", ("FONT_TRAVERSAL",), (None,)),
    ),
    "S10": (
        _LIMIT + (("ANNOTS_ARRAY_LENGTH", "ANNOT_COUNT", "DEST_LENGTH", "URI_LENGTH", "INDIRECT_RESOLUTIONS",
                   "MEMORY", "EVIDENCE_BYTES"),),
        ("RENDER_ANNOTATION_UNSUPPORTED", ("ANNOTS_NOT_ARRAY", "ENTRY_NOT_DICT", "SUBTYPE_MISSING", "NON_LINK",
                                           "RECT_MALFORMED"), (None,)),
        ("RENDER_COORDINATE_SPACE_UNVERIFIED", ("STACK_ANNOTATION",), (None,)),
        ("RENDER_LINK_KIND_UNSUPPORTED", ("ADDITIONAL_ACTIONS", "DEST_AND_ACTION", "NO_DESTINATION",
                                          "ACTION_MALFORMED", "ACTION_CHAIN", "ACTION_TYPE_UNSUPPORTED",
                                          "DEST_UNSUPPORTED"), (None,)),
        ("RENDER_LINK_URI_UNSUPPORTED", (None, "URI_BYTES_UNAVAILABLE", "URI_NON_ASCII"), (None,)),
        ("RENDER_LINK_ATTRIBUTION_AMBIGUOUS", (None,), (None,)),
        ("RENDER_PDF_INSPECTION_FAILED", ("ANNOTATION_READ",), (None,)),
    ),
}

CHILD_SLOTS_V1 = {
    "S5.02": ("S5.02",),
    "S5.03": ("S5.03",),
    "S6": ("S6.01", "S6.01a", "S6.01b", "S6.02", "S6.03", "S6.04", "S6.05", "S6.06", "S6.06a", "S6.07",
           "S6.08", "S6.09", "S6.09a", "S6.10"),
    "S7": ("S7.00", "S7.01", "S7.02", "S7.03", "S7.04"),
    "S9": ("S9.00", "S9.01", "S9.01a", "S9.02"),
    "S10": ("S10.00", "S10.01", "S10.02", "S10.03", "S10.04", "S10.05"),
}
STAGE_FIRST_SLOT = {"S5.02": "S5.02", "S5.03": "S5.03", "S6": "S6.00", "S7": "S7.00", "S9": "S9.00",
                    "S10": "S10.00", None: "PRE_S11"}

FAIL_EVIDENCE_KEYS_V1 = {
    "S5.02": ("start_attestation", "exception_class", "exception_message"),
    "S5.03": ("count", "limit", "exception_class", "exception_message"),
    "S6": ("page_index", "count", "limit", "exception_class", "exception_message", "source", "object_id",
           "category", "form_path", "resource_name"),
    "S7": ("page_index", "count", "limit", "exception_class", "exception_message", "object_id", "form_path",
           "resource_name"),
    "S9": ("page_index", "count", "limit", "exception_class", "exception_message", "source", "object_id",
           "form_path", "resource_name"),
    "S10": ("page_index", "count", "limit", "exception_class", "exception_message", "object_id"),
}
FAIL_FRAME_STAGE_MAXIMA_V1 = {"S5.02": 2028, "S5.03": 642, "S6": 3342, "S7": 3297, "S9": 3322, "S10": 940}
FINAL_FRAME_LEGITIMATE_MAX_BYTES = 424
EVIDENCE_BYTES_FRAME_MAX_BYTES = 197
_SLOT_REASON_RULES = {
    "PAGE_ENUMERATION": {"S6": ("S6.01",)},
    "PAGE_FACTS": {"S6": ("S6.02", "S6.03", "S6.04", "S6.05", "S6.06", "S6.07", "S6.08")},
    "DOCUMENT_STATE_READ": {"S5.03": ("S5.03",), "S6": ("S6.06a",)},
    "PRE_SCAN_READ": {"S6": ("S6.01b",)},
    "PARSER_AMBIGUITY": {"S6": ("S6.01b",)},
}
_HEX64 = re.compile(r"^[0-9a-f]{64}\Z")
_SAFE_INTEGER = 2 ** 53
TEXT_CHUNK_MAX_CHARS = 1024


class ProtocolDefect(Exception):
    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


def triple_permitted(stage: str, status, reason, detail) -> bool:
    for entry_status, reasons, details in CHILD_FAIL_CLOSED_SET_V1.get(stage, ()):
        if status == entry_status and reason in reasons and detail in details:
            return True
    return False


# Iterative scanner -----------------------------------------------------------

_SCANNER_ORDER = ("NESTING_DEPTH", "ELEMENT_COUNT", "MEMBER_COUNT", "STRING_LENGTH", "INTEGER_DIGITS", "FRAME_ELEMENTS")


def _utf8_length(code_point: int) -> int:
    if code_point < 0x80:
        return 1
    if code_point < 0x800:
        return 2
    return 3


def scan_frame_line(line: bytes, limits: dict = None):
    """CHILD_FRAME_LIMITS_V1 iterative byte scanner; the first excess in
    byte order is returned (scanner order among simultaneous excesses)."""
    limits = limits or CHILD_FRAME_LIMITS_V1
    max_depth = limits["child_max_json_depth"]
    max_elements = limits["child_max_array_elements"]
    max_members = limits["child_max_object_members"]
    max_total = limits["child_max_frame_elements"]
    max_string = limits["child_max_string_bytes"]
    max_digits = limits["child_max_integer_digits"]
    stack = []
    total = 0
    index = 0
    length = len(line)
    while index < length:
        byte = line[index]
        flags = set()
        if byte == 0x22:
            top = stack[-1] if stack else None
            if top is not None and top[0] == "o" and top[2]:
                top[1] += 1
                if top[1] > max_members:
                    flags.add("MEMBER_COUNT")
            else:
                total += 1
                if top is not None and top[0] == "a":
                    top[1] += 1
                    if top[1] > max_elements:
                        flags.add("ELEMENT_COUNT")
                if total > max_total:
                    flags.add("FRAME_ELEMENTS")
            string_bytes = 0
            index += 1
            while index < length and not flags:
                byte = line[index]
                if byte == 0x22:
                    break
                if byte == 0x5C and index + 1 < length:
                    escaped = line[index + 1]
                    if escaped == 0x75:
                        hex_digits = line[index + 2:index + 6]
                        try:
                            code_point = int(hex_digits, 16)
                        except ValueError:
                            code_point = 0
                        added = _utf8_length(code_point)
                        step = 6
                        if 0xD800 <= code_point <= 0xDBFF and line[index + 6:index + 8] == b"\\u":
                            try:
                                low = int(line[index + 8:index + 12], 16)
                            except ValueError:
                                low = 0
                            if 0xDC00 <= low <= 0xDFFF:
                                added = 4
                                step = 12
                        string_bytes += added
                        index += step
                    else:
                        string_bytes += 1
                        index += 2
                else:
                    string_bytes += 1
                    index += 1
                if string_bytes > max_string:
                    flags.add("STRING_LENGTH")
            if flags:
                return next(name for name in _SCANNER_ORDER if name in flags)
            index += 1
            continue
        if byte in (0x7B, 0x5B):
            total += 1
            top = stack[-1] if stack else None
            if top is not None and top[0] == "a":
                top[1] += 1
                if top[1] > max_elements:
                    flags.add("ELEMENT_COUNT")
            if len(stack) + 1 > max_depth:
                flags.add("NESTING_DEPTH")
            if total > max_total:
                flags.add("FRAME_ELEMENTS")
            stack.append(["o" if byte == 0x7B else "a", 0, True])
        elif byte in (0x7D, 0x5D):
            if stack:
                stack.pop()
        elif byte == 0x2C:
            if stack and stack[-1][0] == "o":
                stack[-1][2] = True
        elif byte == 0x3A:
            if stack and stack[-1][0] == "o":
                stack[-1][2] = False
        elif byte == 0x2D or 0x30 <= byte <= 0x39 or byte in (0x74, 0x66, 0x6E, 0x4E, 0x49):
            total += 1
            top = stack[-1] if stack else None
            if top is not None and top[0] == "a":
                top[1] += 1
                if top[1] > max_elements:
                    flags.add("ELEMENT_COUNT")
            if total > max_total:
                flags.add("FRAME_ELEMENTS")
            digits = 0
            integer_part = True
            while index < length and line[index] not in b' \t\r,]}:"[{':
                current = line[index]
                if 0x30 <= current <= 0x39 and integer_part:
                    digits += 1
                    if digits > max_digits:
                        flags.add("INTEGER_DIGITS")
                        break
                elif current in b".eE":
                    integer_part = False
                index += 1
            if flags:
                return next(name for name in _SCANNER_ORDER if name in flags)
            continue
        if flags:
            return next(name for name in _SCANNER_ORDER if name in flags)
        index += 1
    return None


# Strict parse ---------------------------------------------------------------

def parse_frame_line(line: bytes):
    """NOT_JSON, NON_FINITE and DUPLICATE_KEY, in that order."""
    if not line:
        raise ProtocolDefect("NOT_JSON")
    try:
        text = line.decode("utf-8")
    except UnicodeDecodeError:
        raise ProtocolDefect("NOT_JSON")
    seen = {"non_finite": False, "duplicate": False, "surrogate": False}

    def on_constant(name):
        seen["non_finite"] = True
        return None

    def on_pairs(pairs):
        keys = [key for key, _ in pairs]
        if len(keys) != len(set(keys)):
            seen["duplicate"] = True
        for key, value in pairs:
            if isinstance(key, str) and _has_lone_surrogate(key):
                seen["surrogate"] = True
            if isinstance(value, str) and _has_lone_surrogate(value):
                seen["surrogate"] = True
        return dict(pairs)

    try:
        value = json.loads(text, object_pairs_hook=on_pairs, parse_constant=on_constant)
    except RecursionError:
        raise ProtocolDefect("PARSER_RECURSION")
    except MemoryError:
        raise ProtocolDefect("PARSER_MEMORY")
    except ValueError:
        raise ProtocolDefect("NOT_JSON")
    if seen["surrogate"] or _contains_lone_surrogate(value):
        raise ProtocolDefect("NOT_JSON")
    if seen["non_finite"]:
        raise ProtocolDefect("NON_FINITE")
    if seen["duplicate"]:
        raise ProtocolDefect("DUPLICATE_KEY")
    return value


def _has_lone_surrogate(text: str) -> bool:
    return any(0xD800 <= ord(ch) <= 0xDFFF for ch in text)


def _contains_lone_surrogate(value) -> bool:
    pending = [value]
    while pending:
        item = pending.pop()
        if isinstance(item, str):
            if _has_lone_surrogate(item):
                return True
        elif isinstance(item, list):
            pending.extend(item)
        elif isinstance(item, dict):
            pending.extend(item.keys())
            pending.extend(item.values())
    return False


# Typed schema ---------------------------------------------------------------

def _schema(condition: bool) -> None:
    if not condition:
        raise ProtocolDefect("SCHEMA")


def _t_int(value, low=None, high=None) -> bool:
    if not _is_int(value) or len(str(abs(value))) > CHILD_FRAME_LIMITS_V1["child_max_integer_digits"]:
        return False
    if low is not None and value < low:
        return False
    if high is not None and value > high:
        return False
    return True


def _t_q(value) -> bool:
    return _t_int(value, -_SAFE_INTEGER, _SAFE_INTEGER)


def _t_num(value) -> bool:
    return (isinstance(value, (int, float)) and not isinstance(value, bool)
            and math.isfinite(value) and abs(value) <= 1e15)


def _t_flag(value) -> bool:
    return _is_int(value) and value in (0, 1)


def _t_fstr(value) -> bool:
    return fail_string_valid(value)


def _t_opt_fstr(value) -> bool:
    return value is None or fail_string_valid(value)


def _t_chunks(value) -> bool:
    return isinstance(value, list) and all(
        isinstance(item, str) and len(item) <= TEXT_CHUNK_MAX_CHARS for item in value
    )


def _t_rect(value) -> bool:
    return isinstance(value, list) and len(value) == 4 and all(_t_num(item) for item in value)


def _keys(value, required, optional=()) -> bool:
    return isinstance(value, dict) and set(required) <= set(value) <= set(required) | set(optional)


def validate_start_attestation(value) -> None:
    _schema(_keys(value, ("inspection_entry_sha256", "received_pdf_sha256", "fd_state", "tmpdir_entries",
                          "pycache_state", "pycache_prefix_matches")))
    _schema(isinstance(value["inspection_entry_sha256"], str) and _HEX64.match(value["inspection_entry_sha256"]))
    _schema(isinstance(value["received_pdf_sha256"], str) and _HEX64.match(value["received_pdf_sha256"]))
    fd_state = value["fd_state"]
    _schema(isinstance(fd_state, list) and len(fd_state) <= FD_STATE_MAX_ENTRIES)
    previous = -1
    for entry in fd_state:
        _schema(isinstance(entry, list) and len(entry) == 2 and _t_int(entry[0], 0) and _t_fstr(entry[1]))
        _schema(entry[0] > previous)
        previous = entry[0]
    _schema(_t_int(value["tmpdir_entries"], 0))
    _schema(value["pycache_state"] in ("ABSENT", "PRESENT"))
    _schema(_t_flag(value["pycache_prefix_matches"]))


EXPECTED_FD_STATE = [[0, "pipe"], [1, "pipe"], [2, "pipe"]]


def classify_start(attestation: dict, entry_sha256: str, pdf_sha256: str):
    """START CLASSIFICATION (1) to (4); None when no violation."""
    if attestation["inspection_entry_sha256"] != entry_sha256:
        return ("RENDER_SANDBOX_RUNTIME_INCOMPLETE", "INSPECTION_RUNTIME_INCOMPLETE", "ENTRY_MISMATCH")
    if attestation["fd_state"] != EXPECTED_FD_STATE:
        return ("RENDER_SANDBOX_RUNTIME_INCOMPLETE", "INSPECTION_RUNTIME_INCOMPLETE", "FD_LEAK")
    if (
        attestation["tmpdir_entries"] != 0
        or attestation["pycache_state"] != "ABSENT"
        or attestation["pycache_prefix_matches"] != 1
    ):
        return ("RENDER_SANDBOX_RUNTIME_INCOMPLETE", "INSPECTION_RUNTIME_INCOMPLETE", "PYCACHE_NOT_EMPTY")
    if attestation["received_pdf_sha256"] != pdf_sha256:
        return ("RENDER_SANDBOX_RUNTIME_INCOMPLETE", "OUTPUT_INVALID", "SNAPSHOT_MISMATCH")
    return None


def validate_fail_evidence(stage: str, frame: dict, line_length: int) -> None:
    """FAIL_EVIDENCE_KEYS_V1 and FAIL_FRAME_MAXIMUM_V1."""
    evidence = frame["evidence"]
    _schema(line_length <= FAIL_FRAME_RESERVE_BYTES)
    if frame["reason"] == "INSPECTION_LIMIT" and frame["detail"] == "EVIDENCE_BYTES":
        _schema(evidence == {})
        return
    _schema(isinstance(evidence, dict) and "slot" in evidence)
    optional = FAIL_EVIDENCE_KEYS_V1[stage]
    required = ("slot", "start_attestation") if stage == "S5.02" else ("slot",)
    _schema(_keys(evidence, required, optional))
    slot = evidence["slot"]
    _schema(slot in CHILD_SLOTS_V1[stage])
    rule = _SLOT_REASON_RULES.get(frame["reason"])
    if rule is not None:
        _schema(slot in rule.get(stage, ()))
    for key, value in evidence.items():
        if key == "slot":
            continue
        if key == "start_attestation":
            validate_start_attestation(value)
        elif key == "page_index":
            _schema(value is None or _t_int(value, 0, INSPECTION_LIMITS_V1["inspection_max_pages"] - 1))
        elif key in ("count", "limit"):
            _schema(_t_int(value, 0))
        elif key == "exception_class":
            _schema(exception_class_valid(value))
        elif key in ("exception_message", "resource_name"):
            _schema(_t_fstr(value))
        elif key == "object_id":
            _schema(_t_opt_fstr(value))
        elif key == "source":
            _schema(value in ("PAGE", "FORM"))
        elif key == "category":
            _schema(value is None or value in RESOURCE_CATEGORIES_V1)
        elif key == "form_path":
            _schema(isinstance(value, list) and len(value) <= FORM_DEPTH_MAX and all(_t_fstr(item) for item in value))


def _validate_pass_evidence(stage: str, evidence) -> None:
    max_pages = INSPECTION_LIMITS_V1["inspection_max_pages"]
    if stage == "S5.02":
        _schema(_keys(evidence, ("start_attestation",)))
        validate_start_attestation(evidence["start_attestation"])
    elif stage == "S5.03":
        _schema(_keys(evidence, ("catalog_keys", "info_keys", "metadata_present")))
        _schema(isinstance(evidence["catalog_keys"], list)
                and len(evidence["catalog_keys"]) <= INSPECTION_LIMITS_V1["inspection_max_catalog_keys"]
                and all(_t_fstr(item) for item in evidence["catalog_keys"]))
        info = evidence["info_keys"]
        _schema(info is None or (isinstance(info, list)
                                 and len(info) <= INSPECTION_LIMITS_V1["inspection_max_info_keys"]
                                 and all(_t_fstr(item) for item in info)))
        _schema(_t_flag(evidence["metadata_present"]))
    elif stage == "S6":
        _schema(_keys(evidence, ("page_count", "pages", "prescan_font_entries")))
        _schema(_t_int(evidence["page_count"], 1, max_pages))
        _schema(_t_int(evidence["prescan_font_entries"], 0))
        pages = evidence["pages"]
        _schema(isinstance(pages, list) and len(pages) == evidence["page_count"])
        for position, page in enumerate(pages):
            _schema(_keys(page, ("index", "width_pt", "height_pt", "width_q", "height_q", "rotation",
                                 "non_text_content")))
            _schema(page["index"] == position and _is_int(page["index"]))
            _schema(_t_num(page["width_pt"]) and _t_num(page["height_pt"]))
            _schema(_t_q(page["width_q"]) and _t_q(page["height_q"]) and _t_int(page["rotation"], 0, 0))
            _schema(_t_flag(page["non_text_content"]))
    elif stage == "S7":
        _schema(_keys(evidence, ("pages",)))
        pages = evidence["pages"]
        _schema(isinstance(pages, list) and len(pages) <= max_pages)
        for position, page in enumerate(pages):
            _schema(_keys(page, ("index", "lines")) and page["index"] == position and _is_int(page["index"]))
            _schema(isinstance(page["lines"], list))
            for line in page["lines"]:
                _schema(_keys(line, ("bbox", "spans")) and _t_rect(line["bbox"]))
                _schema(isinstance(line["spans"], list) and line["spans"])
                for span in line["spans"]:
                    _schema(_keys(span, ("font", "size_q", "color", "text", "gap_before")))
                    _schema(_t_opt_fstr(span["font"]) and _t_q(span["size_q"]))
                    _schema(isinstance(span["color"], list) and len(span["color"]) in (1, 3)
                            and all(_t_num(item) for item in span["color"]))
                    _schema(_t_chunks(span["text"]) and isinstance(span["gap_before"], bool))
    elif stage == "S9":
        _schema(_keys(evidence, ("font_entries", "assertion")))
        _schema(_keys(evidence["assertion"], ("prescan_font_entries", "inventory_entries")))
        _schema(_t_int(evidence["assertion"]["prescan_font_entries"], 0)
                and _t_int(evidence["assertion"]["inventory_entries"], 0))
        _schema(isinstance(evidence["font_entries"], list))
        for entry in evidence["font_entries"]:
            _schema(_keys(entry, ("page_index", "source", "form_path", "resource_name", "object_id", "subtype",
                                  "basefont", "descendant_basefont", "descriptor_present",
                                  "descriptor_fontname", "embedded", "embed_key")))
            _schema(_t_int(entry["page_index"], 0, max_pages - 1) and entry["source"] in ("PAGE", "FORM"))
            _schema(isinstance(entry["form_path"], list) and len(entry["form_path"]) <= FORM_DEPTH_MAX
                    and all(_t_fstr(item) for item in entry["form_path"]))
            _schema(_t_fstr(entry["resource_name"]) and _t_opt_fstr(entry["object_id"]))
            for key in ("subtype", "basefont", "descendant_basefont", "descriptor_fontname"):
                _schema(_t_opt_fstr(entry[key]))
            _schema(_t_flag(entry["descriptor_present"]) and isinstance(entry["embedded"], bool))
            _schema(entry["embed_key"] in (None, "FontFile", "FontFile2", "FontFile3"))
    elif stage == "S10":
        _schema(_keys(evidence, ("annotations", "duplicates")) and _t_int(evidence["duplicates"], 0))
        _schema(isinstance(evidence["annotations"], list))
        for record in evidence["annotations"]:
            _schema(_keys(record, ("page_index", "annot_index", "subtype", "rect_ccs", "kind", "uri", "goto_page",
                                   "words_text")))
            _schema(_t_int(record["page_index"], 0, max_pages - 1) and _t_int(record["annot_index"], 0))
            _schema(record["subtype"] == "Link" and _t_rect(record["rect_ccs"]))
            _schema(record["kind"] in ("LINK_URI", "LINK_GOTO"))
            if record["kind"] == "LINK_URI":
                _schema(isinstance(record["uri"], str) and len(record["uri"]) <= TEXT_CHUNK_MAX_CHARS * 4
                        and record["goto_page"] is None)
            else:
                _schema(record["uri"] is None and _t_int(record["goto_page"], 0, max_pages - 1))
            _schema(_t_chunks(record["words_text"]))


def validate_frame_shape(frame) -> None:
    """The per-frame typed checks (equivalent to schema child_frame)."""
    _schema(_keys(frame, ("protocol", "seq", "kind", "stage", "outcome", "status", "reason", "detail", "evidence")))
    _schema(frame["protocol"] == PROTOCOL_ID)
    _schema(_t_int(frame["seq"], 0, 6))
    _schema(frame["kind"] in ("STAGE", "FINAL") and frame["outcome"] in ("PASS", "FAIL"))
    _schema(isinstance(frame["evidence"], dict))
    triple = (frame["status"], frame["reason"], frame["detail"])
    if frame["kind"] == "FINAL":
        _schema(frame["stage"] is None)
        _schema(_keys(frame["evidence"], ("pdf_sha256", "inspection_entry_sha256", "evidence_bytes")))
        evidence = frame["evidence"]
        _schema(isinstance(evidence["pdf_sha256"], str) and _HEX64.match(evidence["pdf_sha256"]))
        _schema(isinstance(evidence["inspection_entry_sha256"], str)
                and _HEX64.match(evidence["inspection_entry_sha256"]))
        _schema(_t_int(evidence["evidence_bytes"], 0, INSPECTION_LIMITS_V1["inspection_max_evidence_bytes"]))
        if frame["outcome"] == "PASS":
            _schema(triple == (None, None, None))
        else:
            _schema(any(triple_permitted(stage, *triple) for stage in CHILD_STAGES))
        return
    stage = frame["stage"]
    _schema(stage in CHILD_STAGES)
    if frame["outcome"] == "PASS":
        _schema(triple == (None, None, None))
        _validate_pass_evidence(stage, frame["evidence"])
    else:
        _schema(triple_permitted(stage, *triple))


class StreamAnalysis:
    def __init__(self) -> None:
        self.frames = []
        self.stage_frames = {}
        self.fail_frame = None
        self.final = None
        self.start_violation = None
        self.abnormal = None
        self.abnormal_stage = None
        self.complete = False
        self.notes = []

    def validated_pass(self, stage: str) -> bool:
        frame = self.stage_frames.get(stage)
        return frame is not None and frame["outcome"] == "PASS"


class _LineContext:
    def __init__(self, entry_sha256: str, pdf_sha256: str) -> None:
        self.entry_sha256 = entry_sha256
        self.pdf_sha256 = pdf_sha256
        self.expected_seq = 0
        self.stage_index = 0
        self.attestation = None
        self.fail_triple = None
        self.final_seen = False


def _check_line(line: bytes, start: int, context: _LineContext, analysis: StreamAnalysis):
    """GROUP 1 of CHILD_PROTOCOL_DETAIL_ORDER_V1 for one complete line;
    returns the validated frame or raises ProtocolDefect."""
    try:
        detail = scan_frame_line(line)
        if detail is not None:
            raise ProtocolDefect(detail)
        frame = parse_frame_line(line)
        validate_frame_shape(frame)
        line_length = len(line) + 1
        _schema(line_length <= CHILD_FRAME_LIMITS_V1["child_max_frame_bytes"])
        if frame["kind"] == "STAGE":
            stage = frame["stage"]
            if frame["outcome"] == "FAIL":
                validate_fail_evidence(stage, frame, line_length)
            if stage == "S5.02":
                attestation = frame["evidence"]["start_attestation"]
                violation = classify_start(attestation, context.entry_sha256, context.pdf_sha256)
                if frame["detail"] == "START_STATE":
                    _schema(violation is not None)
        else:
            evidence = frame["evidence"]
            _schema(evidence["pdf_sha256"] == context.pdf_sha256)
            _schema(context.attestation is not None
                    and evidence["inspection_entry_sha256"] == context.attestation["inspection_entry_sha256"])
            if frame["outcome"] == "FAIL":
                _schema(context.fail_triple == (frame["status"], frame["reason"], frame["detail"]))
            else:
                _schema(context.fail_triple is None)
        if context.final_seen or frame["seq"] != context.expected_seq:
            raise ProtocolDefect("FRAME_ORDER")
        if frame["kind"] == "STAGE":
            if context.fail_triple is not None or context.stage_index >= len(CHILD_STAGES):
                raise ProtocolDefect("FRAME_ORDER")
            if frame["stage"] != CHILD_STAGES[context.stage_index]:
                raise ProtocolDefect("FRAME_ORDER")
        else:
            if context.fail_triple is None and context.stage_index != len(CHILD_STAGES):
                raise ProtocolDefect("FRAME_ORDER")
            if frame["evidence"]["evidence_bytes"] != start:
                raise ProtocolDefect("EVIDENCE_BYTES_MISMATCH")
        return frame
    except RecursionError:
        raise ProtocolDefect("PARSER_RECURSION")
    except MemoryError:
        raise ProtocolDefect("PARSER_MEMORY")


def _accept(frame: dict, context: _LineContext, analysis: StreamAnalysis) -> None:
    context.expected_seq += 1
    analysis.frames.append(frame)
    if frame["kind"] == "STAGE":
        stage = frame["stage"]
        analysis.stage_frames[stage] = frame
        context.stage_index += 1
        if stage == "S5.02":
            context.attestation = frame["evidence"]["start_attestation"]
            analysis.start_violation = classify_start(context.attestation, context.entry_sha256, context.pdf_sha256)
        if frame["outcome"] == "FAIL":
            context.fail_triple = (frame["status"], frame["reason"], frame["detail"])
            analysis.fail_frame = frame
    else:
        context.final_seen = True
        analysis.final = frame


def _final_syntax_valid(line: bytes) -> bool:
    try:
        if scan_frame_line(line) is not None:
            return False
        frame = parse_frame_line(line)
        validate_frame_shape(frame)
        return frame["kind"] == "FINAL"
    except (ProtocolDefect, RecursionError, MemoryError):
        return False


def _child_protocol(detail: str) -> tuple:
    return ("RENDER_PDF_INSPECTION_FAILED", "CHILD_PROTOCOL", detail)


WALL_CLOCK_TRIPLE = ("RENDER_PDF_INSPECTION_FAILED", "INSPECTION_LIMIT", "WALL_CLOCK")
CAP_EXCEEDED_TRIPLE = ("RENDER_PDF_INSPECTION_FAILED", "INSPECTION_LIMIT", "EVIDENCE_BYTES")
CHILD_NO_START_TRIPLE = ("RENDER_SANDBOX_RUNTIME_INCOMPLETE", "INSPECTION_RUNTIME_INCOMPLETE", "CHILD_NO_START")


def analyze_child_stream(data: bytes, result: ProcessResult, entry_sha256: str, pdf_sha256: str) -> StreamAnalysis:
    """CHILD_PROTOCOL_V1 parent validation of one complete child run:
    EVIDENCE_CAP_RULE_V1, CHILD_PROTOCOL_DETAIL_ORDER_V1 and the
    validated prefix of ORDERING AND PREFIX CONSUMPTION."""
    analysis = StreamAnalysis()
    cap = INSPECTION_LIMITS_V1["inspection_max_evidence_bytes"]
    final_max = FINAL_FRAME_MAX_BYTES
    if not data:
        analysis.abnormal = WALL_CLOCK_TRIPLE if result.timed_out else CHILD_NO_START_TRIPLE
        analysis.abnormal_stage = "S5.02"
        return analysis
    data = data[: cap + final_max + 1]
    lines = []
    position = 0
    while True:
        newline = data.find(b"\n", position)
        if newline < 0:
            break
        lines.append((position, newline))
        position = newline + 1
    tail = data[position:]
    cap_exceeded = False
    if len(data) > cap:
        counted = [item for item in lines if item[1] + 1 <= cap]
        boundary_start = counted[-1][1] + 1 if counted else 0
        boundary_end = data.find(b"\n", boundary_start, boundary_start + final_max)
        admitted = (
            boundary_end >= 0
            and boundary_end + 1 == len(data)
            and _final_syntax_valid(data[boundary_start:boundary_end])
        )
        if admitted:
            lines = counted + [(boundary_start, boundary_end)]
            tail = b""
        else:
            lines = counted
            tail = b""
            cap_exceeded = True
    context = _LineContext(entry_sha256, pdf_sha256)
    defect = None
    for start, end in lines:
        try:
            frame = _check_line(data[start:end], start, context, analysis)
        except ProtocolDefect as error:
            if analysis.fail_frame is not None:
                analysis.notes.append("POST_FAIL_" + error.detail)
                break
            defect = error.detail
            break
        _accept(frame, context, analysis)
        if analysis.final is not None and analysis.fail_frame is not None:
            break
    validated_stages = len(analysis.stage_frames)
    next_stage = CHILD_STAGES[validated_stages] if validated_stages < len(CHILD_STAGES) else None
    if defect is not None:
        event = _child_protocol(defect)
    elif cap_exceeded:
        event = WALL_CLOCK_TRIPLE if result.timed_out and not result.cap_killed else CAP_EXCEEDED_TRIPLE
    elif result.timed_out:
        event = WALL_CLOCK_TRIPLE
    elif analysis.final is None:
        event = _child_protocol("TRUNCATED_FRAME" if tail else "MISSING_FINAL")
    elif tail:
        event = _child_protocol("TRAILING_DATA")
    elif result.returncode is None or (result.returncode != 0 and result.signal is None):
        event = _child_protocol("EXIT_NONZERO")
    elif result.signal is not None:
        event = _child_protocol("SIGNAL")
    else:
        event = None
    if analysis.fail_frame is not None:
        if event is not None:
            analysis.notes.append("POST_FAIL_" + event[2])
        return analysis
    if event is not None:
        analysis.abnormal = event
        analysis.abnormal_stage = next_stage
        return analysis
    analysis.complete = analysis.final is not None and validated_stages == len(CHILD_STAGES)
    return analysis


# =============================================================================
# Rendered evidence (parent view of validated frames)
# =============================================================================

_SUBSET_PREFIX = re.compile(r"^[A-Z]{6}\+")
SUPPORTED_FONT_SUBTYPES = ("Type1", "MMType1", "TrueType", "Type0", "Type3")


def decode_fail_string(value):
    """The octets of a FAIL_EVIDENCE_STRING_V1 value; None if truncated."""
    if value is None or value.endswith("%~"):
        return None
    octets = bytearray()
    index = 0
    while index < len(value):
        if value[index] == "%":
            octets.append(int(value[index + 1:index + 3], 16))
            index += 3
        else:
            octets.append(ord(value[index]))
            index += 1
    return bytes(octets)


def pdf_name_form(value):
    """FONT_NAME_FORM_V1: ASCII U+0021-U+007E, one subset prefix stripped;
    None when the name is absent or not admissible."""
    octets = decode_fail_string(value)
    if not octets or any(not 0x21 <= byte <= 0x7E for byte in octets):
        return None
    return _SUBSET_PREFIX.sub("", str(octets, "ascii"), count=1)


class RenderedSpan:
    __slots__ = ("font", "size_q", "color", "text", "gap_before")

    def __init__(self, record: dict) -> None:
        self.font = record["font"]
        self.size_q = record["size_q"]
        self.color = record["color"]
        self.text = "".join(record["text"])
        self.gap_before = record["gap_before"]


class RenderedLine:
    __slots__ = ("page_index", "bbox", "bbox_q", "bottom_pt", "spans", "text", "tokens", "marker",
                 "paragraph_index", "content_type", "remaining_spans")

    def __init__(self, page_index: int, record: dict) -> None:
        self.page_index = page_index
        self.bbox = list(record["bbox"])
        self.bbox_q = [quantize(value) for value in self.bbox]
        self.bottom_pt = self.bbox[3]
        self.spans = [RenderedSpan(span) for span in record["spans"]]
        self.text = "".join((" " if span.gap_before else "") + span.text for span in self.spans)
        self.tokens = tokenize(self.text)
        self.marker = None
        self.paragraph_index = None
        self.content_type = None
        self.remaining_spans = self.spans


def rendered_lines(s7_evidence: dict) -> list:
    lines = []
    for page in s7_evidence["pages"]:
        for record in page["lines"]:
            lines.append(RenderedLine(page["index"], record))
    return lines


# S8 ATTRIBUTION -----------------------------------------------------------------

def _s8(status, reason=None, **evidence):
    fail(status, reason, None, "S8", **evidence)


def _span_tokens(spans) -> list:
    return tokenize("".join((" " if index and span.gap_before else "") + span.text for index, span in enumerate(spans)))


def split_marker(line: RenderedLine, expected: str):
    """LIST_MARKER_MODEL_V1 marker_span_rule; returns the remaining tokens."""
    for position, span in enumerate(line.spans):
        tokens = tokenize(span.text)
        if not tokens:
            continue
        if tokens == [expected]:
            line.marker = {"token": expected, "font": span.font}
            line.remaining_spans = line.spans[position + 1:]
            return _span_tokens(line.remaining_spans)
        if tokens[0] == expected:
            normalized = normalize_text(span.text).lstrip("".join(SEPARATOR_CHARACTERS))
            after = normalized[len(expected):len(expected) + 1]
            if normalized.startswith(expected) and after and after in SEPARATOR_CHARACTERS:
                line.marker = {"token": expected, "font": span.font}
                line.remaining_spans = line.spans
                return line.tokens[1:]
            _s8("RENDER_LIST_MARKER_MISMATCH", "MARKER_NOT_SEPARABLE")
        if tokens[0].startswith(expected):
            _s8("RENDER_LIST_MARKER_MISMATCH", "MARKER_NOT_SEPARABLE")
        _s8("RENDER_LIST_MARKER_MISMATCH", None)
    _s8("RENDER_LIST_MARKER_MISMATCH", None)


def _is_strict_subsequence(shorter: list, longer: list) -> bool:
    if len(shorter) >= len(longer):
        return False
    iterator = iter(longer)
    return all(any(token == candidate for candidate in iterator) for token in shorter)


def attribute_lines(model: SourceModel, lines: list) -> None:
    """S8 ATTRIBUTION_ALGORITHM_V1 with LIST_MARKER_MODEL_V1 removal and
    TEXT_LOSS_SEQUENCES_V1 classification."""
    for line in lines:
        if not line.tokens:
            _s8("RENDER_ATTRIBUTION_INCOMPLETE", "EMPTY_TOKEN_LINE", page_index=line.page_index)

    def loss_or(reason):
        declared = []
        for entry in model.structure_map:
            paragraph = model.paragraphs[entry["paragraph_index"]]
            if not paragraph.tokens:
                continue
            if paragraph.list_semantics is not None:
                declared.append(paragraph.marker_expected)
            declared.extend(paragraph.tokens)
        rendered = [token for line in lines for token in line.tokens]
        if _is_strict_subsequence(rendered, declared):
            _s8("RENDER_TEXT_LOSS_DETECTED")
        _s8("RENDER_ATTRIBUTION_INCOMPLETE", reason)

    pointer = 0
    for entry in model.structure_map:
        paragraph = model.paragraphs[entry["paragraph_index"]]
        declared = paragraph.tokens
        if not declared:
            continue
        accumulated = []
        offset = 0
        while True:
            if pointer + offset >= len(lines):
                loss_or("MISSING_RENDERED_LINES")
            line = lines[pointer + offset]
            if offset == 0 and paragraph.list_semantics is not None:
                remaining = split_marker(line, paragraph.marker_expected)
            else:
                remaining = line.tokens
            accumulated = accumulated + remaining
            if accumulated == declared:
                for attributed in lines[pointer:pointer + offset + 1]:
                    attributed.paragraph_index = paragraph.index
                    attributed.content_type = entry["content_type"]
                pointer += offset + 1
                break
            if len(accumulated) < len(declared) and accumulated == declared[: len(accumulated)]:
                offset += 1
                continue
            first = next(i for i in range(min(len(accumulated), len(declared)) + 1)
                         if i >= len(accumulated) or i >= len(declared) or accumulated[i] != declared[i])
            last_index = len(accumulated) - 1
            if (
                first == last_index
                and first < len(declared)
                and accumulated[first].endswith("-")
                and declared[first] != accumulated[first][:-1]
                and declared[first].startswith(accumulated[first][:-1])
            ):
                _s8("RENDER_ATTRIBUTION_INCOMPLETE", "HYPHENATION_OBSERVED", paragraph_index=paragraph.index)
            loss_or("TOKEN_MISMATCH")
    if pointer < len(lines):
        _s8("RENDER_ATTRIBUTION_INCOMPLETE", "UNATTRIBUTED_LINES")


# S9.03 to S9.05 ---------------------------------------------------------------

def _identity(table: dict, name):
    entry = table.get(name) if name is not None else None
    return (entry["canonical_family_id"], entry["face"]) if entry is not None else None


def font_inventory_records(manifest: dict, s9_evidence: dict) -> list:
    """S9.03 (UNSUPPORTED_FONT_SUBTYPE, BASEFONT_MISSING, UNMAPPED_NAME_FORM
    per font in inventory order) and FONT_INVENTORY_RECORD_V1."""
    table = manifest["pdf_basefont_to_canonical"]
    records = []
    for entry in s9_evidence["font_entries"]:
        where = {"page_index": entry["page_index"], "resource_name": entry["resource_name"]}
        subtype_octets = decode_fail_string(entry["subtype"])
        subtype = str(subtype_octets, "latin-1") if subtype_octets is not None else None
        if subtype not in SUPPORTED_FONT_SUBTYPES:
            fail("RENDER_FONT_SUBSTITUTION_UNAPPROVED", "UNSUPPORTED_FONT_SUBTYPE", None, "S9.03", **where)
        if entry["basefont"] is None:
            fail("RENDER_FONT_SUBSTITUTION_UNAPPROVED", "BASEFONT_MISSING", None, "S9.03", **where)
        names = {"inventory": pdf_name_form(entry["basefont"])}
        if subtype == "Type0" and entry["descendant_basefont"] is not None:
            names["descendant"] = pdf_name_form(entry["descendant_basefont"])
        if entry["descriptor_fontname"] is not None:
            names["descriptor"] = pdf_name_form(entry["descriptor_fontname"])
        for name in names.values():
            if name is None or name not in table:
                fail("RENDER_FONT_SUBSTITUTION_UNAPPROVED", "UNMAPPED_NAME_FORM", None, "S9.03", **where)
        records.append({
            "page_index": entry["page_index"],
            "source": entry["source"],
            "form_path": entry["form_path"],
            "resource_name": entry["resource_name"],
            "object_id": entry["object_id"],
            "subtype": subtype,
            "inventory_name_raw": str(decode_fail_string(entry["basefont"]), "ascii"),
            "inventory_name": names["inventory"],
            "descendant_name": names.get("descendant"),
            "descriptor_name": names.get("descriptor"),
            "embedded": entry["embedded"],
            "embed_key": entry["embed_key"],
            "canonical": dict(zip(("canonical_family_id", "face"), _identity(table, names["inventory"]))),
            "_identities": {_identity(table, name) for name in names.values()},
        })
    return records


def check_inventory(manifest: dict, records: list, lines: list) -> None:
    """S9.04: DESCRIPTOR_NAME per font, then per-page span identities as a
    subset of the page's inventory identities."""
    table = manifest["pdf_basefont_to_canonical"]
    for record in records:
        if len(record["_identities"]) != 1:
            fail("RENDER_FONT_INVENTORY_MISMATCH", "DESCRIPTOR_NAME", None, "S9.04",
                 page_index=record["page_index"], resource_name=record["resource_name"])
    inventory = {}
    for record in records:
        inventory.setdefault(record["page_index"], set()).update(record["_identities"])
    for line in lines:
        for span in line.spans:
            identity = _identity(table, pdf_name_form(span.font))
            if identity is None:
                fail("RENDER_FONT_SUBSTITUTION_UNAPPROVED", "UNMAPPED_NAME_FORM", None, "S9.04",
                     page_index=line.page_index)
            if identity not in inventory.get(line.page_index, set()):
                fail("RENDER_FONT_INVENTORY_MISMATCH", None, None, "S9.04", page_index=line.page_index)


def check_span_identities(manifest: dict, model: SourceModel, lines: list) -> None:
    """S9.05: marker rule, then every other attributed span."""
    table = manifest["pdf_basefont_to_canonical"]
    substitutions = manifest["approved_substitutions"]

    def approved(identity, expected_set):
        for family, face in expected_set:
            if identity == (family, face):
                return True
            if identity[1] == face and identity[0] in substitutions.get(family, []):
                return True
        return False

    for line in lines:
        paragraph = model.paragraphs[line.paragraph_index]
        marker_span_font = line.marker["font"] if line.marker else None
        skip_first_counted = line.marker is not None
        if line.marker is not None:
            identity = _identity(table, pdf_name_form(marker_span_font))
            if identity is None or not approved(identity, {paragraph.marker_identity}):
                fail("RENDER_LIST_MARKER_FONT_UNAPPROVED", None, None, "S9.05", paragraph_index=paragraph.index)
        for span in line.spans:
            if skip_first_counted and tokenize(span.text):
                skip_first_counted = False
                continue
            identity = _identity(table, pdf_name_form(span.font))
            if identity is not None and approved(identity, paragraph.expected_identities):
                continue
            if identity is not None and any(identity[0] == family for family, _ in paragraph.expected_identities):
                fail("RENDER_FONT_FACE_MISMATCH", None, None, "S9.05", paragraph_index=paragraph.index)
            fail("RENDER_FONT_SUBSTITUTION_UNAPPROVED", None, None, "S9.05", paragraph_index=paragraph.index)


# S10.06 and S10.07 --------------------------------------------------------------

def link_linkage(model: SourceModel, s10_evidence: dict, lines: list) -> list:
    """HYPERLINK_OCCURRENCE_MODEL_V1 linkage_algorithm and
    internal_anchor_rule; returns the logical hyperlink list."""
    annotations = []
    for record in s10_evidence["annotations"]:
        annotations.append(dict(record, tokens=tokenize(" ".join(record["words_text"]))))
    first_page = {}
    for line in lines:
        if line.paragraph_index is not None:
            first_page.setdefault(line.paragraph_index, line.page_index)
    hyperlinks = []
    pointer = 0
    for occurrence in model.occurrences:
        expected_tokens = occurrence["tokens"]
        if occurrence["dest_kind"] == "EXTERNAL_URI":
            def dest_match(annotation, uri=occurrence["dest"]):
                return annotation["kind"] == "LINK_URI" and annotation["uri"] == uri
            goto_page = None
        else:
            paragraph_index = model.bookmark_paragraph.get(occurrence["dest"])
            goto_page = first_page.get(paragraph_index)
            if goto_page is None:
                fail("RENDER_LINK_ATTRIBUTION_AMBIGUOUS", "ANCHOR_UNATTRIBUTED", None, "S10.06")

            def dest_match(annotation, page=goto_page):
                return annotation["kind"] == "LINK_GOTO" and annotation["goto_page"] == page

        def match_from(start):
            collected = []
            for count in range(1, len(annotations) - start + 1):
                candidate = annotations[start + count - 1]
                if not dest_match(candidate):
                    return None
                collected = collected + candidate["tokens"]
                if collected == expected_tokens:
                    return count
                if collected != expected_tokens[: len(collected)]:
                    return None
            return None

        count = match_from(pointer) if pointer < len(annotations) else None
        if count is None:
            if pointer >= len(annotations):
                fail("RENDER_LINK_MISSING", None, None, "S10.06")
            head = annotations[pointer]
            if head["tokens"] == expected_tokens and not dest_match(head):
                fail("RENDER_LINK_DESTINATION_SUBSTITUTED", None, None, "S10.06")
            if dest_match(head) and head["tokens"] != expected_tokens:
                fail("RENDER_LINK_ATTRIBUTION_AMBIGUOUS", None, None, "S10.06")
            if any(match_from(later) is not None for later in range(pointer + 1, len(annotations))):
                fail("RENDER_LINK_ORDER_MISMATCH", None, None, "S10.06")
            fail("RENDER_LINK_MISSING", None, None, "S10.06")
        consumed = annotations[pointer:pointer + count]
        pointer += count
        hyperlinks.append({
            "dest_kind": occurrence["dest_kind"],
            "dest": occurrence["dest"],
            "goto_page": goto_page,
            "page_rects": [[item["page_index"]] + [quantize(value) for value in item["rect_ccs"]] for item in consumed],
            "tokens": expected_tokens,
        })
    if pointer < len(annotations):
        fail("RENDER_LINK_FABRICATED", None, None, "S10.07", count=len(annotations) - pointer)
    return hyperlinks


# Terminal resolution --------------------------------------------------------

class ParentContext:
    """Inputs of the parent-evaluated slots, filled as slots pass."""

    def __init__(self, manifest: dict, model: SourceModel) -> None:
        self.manifest = manifest
        self.model = model
        self.lines = None
        self.font_records = None
        self.hyperlinks = None


def _frame_outcome(frame: dict) -> Outcome:
    evidence = frame["evidence"]
    slot = evidence.get("slot") or STAGE_FIRST_SLOT[frame["stage"]]
    detail_evidence = {key: value for key, value in evidence.items() if key not in ("slot", "start_attestation")}
    return Outcome(frame["status"], frame["reason"], frame["detail"], slot, detail_evidence)


def resolve_terminal(analysis: StreamAnalysis, context: ParentContext):
    """Walk the slots of STATUS_ORDER_V1 over the validated prefix;
    returns None when every slot through S10.07 passed and
    COMPLETE_STREAM_GATE holds, else the single terminal Outcome."""

    def child_stage(stage):
        frame = analysis.stage_frames.get(stage)
        if frame is None:
            triple = analysis.abnormal
            return Outcome(triple[0], triple[1], triple[2], STAGE_FIRST_SLOT[stage])
        if stage == "S5.02" and analysis.start_violation is not None:
            status, reason, detail = analysis.start_violation
            return Outcome(status, reason, detail, "S5.02", {"sub_check": detail})
        if frame["outcome"] == "FAIL":
            return _frame_outcome(frame)
        return None

    def parent_slot(function):
        try:
            function()
        except StageFailure as failure:
            return failure.outcome
        return None

    manifest, model = context.manifest, context.model
    for stage in ("S5.02", "S5.03", "S6", "S7"):
        outcome = child_stage(stage)
        if outcome is not None:
            return outcome
    context.lines = rendered_lines(analysis.stage_frames["S7"]["evidence"])
    outcome = parent_slot(lambda: attribute_lines(model, context.lines))
    if outcome is not None:
        return outcome
    outcome = child_stage("S9")
    if outcome is not None:
        return outcome

    def s9_parent():
        context.font_records = font_inventory_records(manifest, analysis.stage_frames["S9"]["evidence"])
        check_inventory(manifest, context.font_records, context.lines)
        check_span_identities(manifest, model, context.lines)

    outcome = parent_slot(s9_parent)
    if outcome is not None:
        return outcome
    outcome = child_stage("S10")
    if outcome is not None:
        return outcome

    def s10_parent():
        context.hyperlinks = link_linkage(model, analysis.stage_frames["S10"]["evidence"], context.lines)

    outcome = parent_slot(s10_parent)
    if outcome is not None:
        return outcome
    if not analysis.complete:
        triple = analysis.abnormal or _child_protocol("MISSING_FINAL")
        return Outcome(triple[0], triple[1], triple[2], "PRE_S11")
    return None


# S11 PAYLOAD AND FINDINGS -------------------------------------------------------

def _decimal(value) -> Decimal:
    return Decimal(value)


def build_payload(s6_evidence: dict, lines: list) -> dict:
    first = s6_evidence["pages"][0]
    return {
        "page_size": "US_LETTER",
        "page_width_pt": first["width_pt"],
        "page_height_pt": first["height_pt"],
        "page_count": s6_evidence["page_count"],
        "objects": [{"content_type": line.content_type, "bottom_pt": line.bottom_pt} for line in lines],
    }


def boundary_findings(s6_evidence: dict, lines: list) -> list:
    findings = []
    widths = {page["index"]: page["width_pt"] for page in s6_evidence["pages"]}
    epsilon = OVERFLOW_EPSILON
    for index, line in enumerate(lines):
        left, top, right, _ = (_decimal(value) for value in line.bbox)
        width = _decimal(widths[line.page_index])
        for edge, excursion in (("LEFT", left < -epsilon), ("RIGHT", right > width + epsilon), ("TOP", top < -epsilon)):
            if excursion:
                findings.append({"kind": "BOUNDARY_EXCURSION", "edge": edge, "page_index": line.page_index,
                                 "line_index": index})
    return findings


def overlap_findings(lines: list) -> list:
    """TEXT_OVERLAP_MAX_RATIO_V1 on integer tenths."""
    findings = []
    for first_index, first in enumerate(lines):
        for second_index in range(first_index + 1, len(lines)):
            second = lines[second_index]
            if first.page_index != second.page_index:
                continue
            a, b = first.bbox_q, second.bbox_q
            width = min(a[2], b[2]) - max(a[0], b[0])
            height = min(a[3], b[3]) - max(a[1], b[1])
            if width <= 0 or height <= 0:
                continue
            intersection = width * height
            smaller = min((a[2] - a[0]) * (a[3] - a[1]), (b[2] - b[0]) * (b[3] - b[1]))
            if TEXT_OVERLAP_RATIO_DENOMINATOR * intersection > TEXT_OVERLAP_RATIO_NUMERATOR * smaller:
                findings.append({"kind": "TEXT_OVERLAP", "page_index": first.page_index,
                                 "line_indexes": [first_index, second_index]})
    return findings


def evaluate_results(s5_03_evidence: dict, s6_evidence: dict, lines: list) -> dict:
    """S11: payload, the unchanged evaluator, findings and the run status."""
    payload = build_payload(s6_evidence, lines)
    result = evaluate_resume_page_utilization(payload)
    findings = [dict(error, kind="VALIDATOR_ERROR") for error in result["errors"]]
    geometric = boundary_findings(s6_evidence, lines) + overlap_findings(lines)
    findings.extend(geometric)
    fraction = result["meaningful_content_bottom_fraction"]
    informational = []
    for page in s6_evidence["pages"]:
        if page["non_text_content"]:
            informational.append({"kind": "NON_TEXT_CONTENT_PRESENT", "page_index": page["index"],
                                  "label": "HUMAN_REQUIRED"})
    informational.append({"kind": "OUT_OF_PAGE_TEXT_UNOBSERVABLE", "label": "HUMAN_REQUIRED"})
    informational.append({"kind": "PDF_INFO_RECORDED", "info_keys": s5_03_evidence["info_keys"],
                          "metadata_present": s5_03_evidence["metadata_present"], "label": "HUMAN_REQUIRED"})
    borderline = fraction is not None and UTILIZATION_FLOOR <= fraction < BORDERLINE_CEILING
    if borderline:
        informational.append({"kind": "BORDERLINE_HUMAN_CONFIRM", "fraction": fraction, "label": "HUMAN_REQUIRED"})
    status = STATUS_PASS if result["valid"] and not geometric else STATUS_QA_FAILED
    return {
        "status": status,
        "payload": payload,
        "validator": result,
        "findings": findings,
        "informational": informational,
        "utilization": {
            "label": "AUTOMATED_GEOMETRY_ONLY",
            "visible_occupancy": "HUMAN_REQUIRED",
            "bottom_pt_definition": "FONT_BBOX_BOTTOM_INCLUDING_DESCENT",
            "meaningful_content_bottom_fraction": fraction,
            "borderline_human_confirm": 1 if borderline else 0,
        },
    }


# RENDER_SEMANTIC_FINGERPRINT_V1 --------------------------------------------------

def attribution_digest(model: SourceModel, lines: list) -> str:
    return canonical_digest({
        "spec": "ATTRIBUTION_DIGEST_V1",
        "source_paragraphs": [
            {"index": paragraph.index, "surface": paragraph.surface, "tokens": paragraph.tokens}
            for paragraph in model.paragraphs
        ],
        "structure_map": sorted(model.structure_map, key=lambda entry: entry["paragraph_index"]),
        "line_attribution": [
            {"content_type": line.content_type, "paragraph_index": line.paragraph_index, "status": "OK"}
            for line in lines
        ],
    })


def semantic_fingerprint(docx_sha256: str, environment: VerifiedEnvironment, s6_evidence: dict, lines: list,
                         hyperlinks: list, model: SourceModel) -> tuple:
    table = environment.manifest["pdf_basefont_to_canonical"]
    lines_by_page = {}
    identities = set()
    for line in lines:
        fonts = sorted({_identity(table, pdf_name_form(span.font)) for span in line.spans})
        identities.update(fonts)
        marker = None
        if line.marker is not None:
            marker = {"token": line.marker["token"], "font": list(_identity(table, pdf_name_form(line.marker["font"])))}
        lines_by_page.setdefault(line.page_index, []).append({
            "bbox_q": line.bbox_q,
            "fonts": [list(item) for item in fonts],
            "sizes_q": sorted({span.size_q for span in line.spans}),
            "tokens": line.tokens,
            "marker": marker,
        })
    digest = attribution_digest(model, lines)
    fingerprint_object = {
        "spec": "RENDER_SEMANTIC_FINGERPRINT_V1",
        "docx_sha256": docx_sha256,
        "manifest_digest": environment.manifest_digest,
        "page_count": s6_evidence["page_count"],
        "pages": [
            {"index": page["index"], "width_q": page["width_q"], "height_q": page["height_q"],
             "rotation": page["rotation"], "lines": lines_by_page.get(page["index"], [])}
            for page in s6_evidence["pages"]
        ],
        "hyperlinks": hyperlinks,
        "font_identities": [list(item) for item in sorted(identities)],
        "attribution_digest": digest,
        "content_binding_digest": environment.content_binding_digest,
    }
    return canonical_digest(fingerprint_object), digest


# Evidence record -------------------------------------------------------------

AUTOMATED_CHECKS_V1 = (
    "DOCX_PREFLIGHT", "PINNED_ENVIRONMENT_AND_CONTENT_BINDING", "SANDBOX_MINIMAL_VIEW_AND_NETWORK_SELF_TEST",
    "CONVERSION_AND_PARSEABLE_PDF", "PAGE_COUNT_AND_PAGE_GEOMETRY", "TEXT_BOUNDARY_LEFT_RIGHT_TOP",
    "TEXT_OVERLAP", "TEXT_EXTRACTION_PARITY", "HYPERLINK_OCCURRENCE_PARITY", "FONT_EMBEDDING_AND_IDENTITY",
    "LIST_MARKERS", "RENDERED_TEXT_STATE", "PAGE_UTILIZATION_GEOMETRY_ONLY", "READING_ORDER_TEXT",
    "RENDER_SEMANTIC_FINGERPRINT", "DOCUMENT_STATE_KEYS",
)
HUMAN_REQUIRED_CHECKS_V1 = (
    "VISUAL_REVIEW_OF_RAW_PDF_AND_DOCX", "ARTIFACT_IS_THE_SUBMITTED_ONE", "HYPERLINK_DESTINATIONS_LIVE_AND_CORRECT",
    "VISIBLE_MEANINGFUL_OCCUPANCY", "INTERNAL_ANCHOR_POSITION_AND_AMBIGUOUS_LINKS", "BORDERLINE_UTILIZATION",
    "APPROVED_FONT_SUBSTITUTION_VISUAL", "CONTENT_TYPE_MAP_HONESTY", "FINAL_BORA_APPROVAL_AND_MANUAL_SUBMIT",
    "GLYPH_LEVEL_FONT_FALLBACK", "LIST_MARKER_APPEARANCE", "NON_TEXT_GEOMETRY", "PDF_METADATA_AND_UNINSPECTED_CONSTRUCTS",
)


def new_evidence(docx_sha256) -> dict:
    return {
        "spec": "RENDERED_DOCUMENT_EVIDENCE_V1",
        "run_status": None,
        "reason": None,
        "detail": None,
        "slot": None,
        "failure_evidence": {},
        "docx_sha256": docx_sha256,
        "pdf_sha256": None,
        "manifest_digest": None,
        "content_binding_digest": None,
        "runtime_manifest_digest": None,
        "sandbox_profile_digest": None,
        "inspection_profile_digest": None,
        "inspection_entry_sha256": None,
        "entry_fd_evidence": None,
        "render_semantic_fingerprint": None,
        "attribution_digest": None,
        "utilization": None,
        "findings": [],
        "informational": [],
        "child_protocol_notes": [],
        "orphan_relationships": [],
        "auto_hyphenation": 0,
        "delivered": 0,
        "temp_root_removed": None,
        "automated_checks": [{"check": name, "label": "AUTOMATED"} for name in AUTOMATED_CHECKS_V1],
        "human_required": [{"check": name, "label": "HUMAN_REQUIRED"} for name in HUMAN_REQUIRED_CHECKS_V1],
        "human_review_waived": 0,
    }


def _evidence_safe(value):
    """Evidence values are JSON-typed; anything else is dropped to its
    class name so evidence assembly never fails."""
    if value is None or isinstance(value, (str, int, float)):
        return value
    if isinstance(value, (list, tuple)):
        return [_evidence_safe(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _evidence_safe(item) for key, item in value.items()}
    return type(value).__name__


def apply_outcome(evidence: dict, outcome: Outcome) -> dict:
    evidence["run_status"] = outcome.status
    evidence["reason"] = outcome.reason
    evidence["detail"] = outcome.detail
    evidence["slot"] = outcome.slot
    evidence["failure_evidence"] = _evidence_safe(outcome.evidence)
    return evidence


_EVIDENCE_KEYS = tuple(new_evidence(None).keys())


def validate_evidence_record(record) -> list:
    """Stdlib structural validation of an evidence record (the runtime
    counterpart of schemas/rendered_document_evidence.schema.json
    definition evidence_record); returns a list of problems."""
    problems = []
    if not isinstance(record, dict):
        return ["record must be an object"]
    if set(record) != set(_EVIDENCE_KEYS):
        problems.append("keys")
        return problems
    if record["spec"] != "RENDERED_DOCUMENT_EVIDENCE_V1":
        problems.append("spec")
    if record["run_status"] not in RUN_STATUSES:
        problems.append("run_status")
    for key in ("docx_sha256", "pdf_sha256", "manifest_digest", "content_binding_digest", "runtime_manifest_digest",
                "sandbox_profile_digest", "inspection_profile_digest", "inspection_entry_sha256",
                "render_semantic_fingerprint", "attribution_digest"):
        value = record[key]
        if value is not None and not (isinstance(value, str) and _HEX64.match(value)):
            problems.append(key)
    if record["run_status"] == STATUS_PASS and (
        record["render_semantic_fingerprint"] is None or record["utilization"] is None
    ):
        problems.append("pass_without_fingerprint")
    if record["render_semantic_fingerprint"] is not None and record["run_status"] not in (STATUS_PASS, STATUS_QA_FAILED):
        problems.append("fingerprint_on_failure")
    if record["human_review_waived"] != 0:
        problems.append("human_review_waived")
    if [item["check"] for item in record["human_required"]] != list(HUMAN_REQUIRED_CHECKS_V1):
        problems.append("human_required")
    if any(item["label"] != "HUMAN_REQUIRED" for item in record["human_required"]):
        problems.append("human_required_label")
    if any(item["label"] != "AUTOMATED" for item in record["automated_checks"]):
        problems.append("automated_label")
    try:
        canonical_json_bytes(record)
    except (TypeError, ValueError):
        problems.append("not_canonical_json")
    return problems


# =============================================================================
# ORCHESTRATION
# =============================================================================

class RenderDependencies:
    """Every external effect of a run. live_verifier(manifest) and
    isolation_prober(profile, argv, pass_fds) are operator-side
    instruments; the adapter fails closed when they are absent."""

    def __init__(self, manifest_bytes=None, live_verifier=None, plan_inputs=None, runtime_paths=None,
                 isolation_prober=None, runner=None, temp_parent=None, dist_resolver=None, entry_reader=None,
                 entry_binder=None):
        self.manifest_bytes = manifest_bytes
        self.live_verifier = live_verifier
        self.plan_inputs = plan_inputs
        self.runtime_paths = runtime_paths
        self.isolation_prober = isolation_prober
        self.runner = runner or ProcessRunner()
        self.temp_parent = temp_parent
        self.dist_resolver = dist_resolver
        self.entry_reader = entry_reader or (lambda: INSPECTION_ENTRY_PATH.read_bytes())
        self.entry_binder = entry_binder or bind_entry_descriptor


def _self_test(deps: RenderDependencies, profile: str, argv: list, pass_fds: tuple, expected_digest: str, slot: str):
    if deps.isolation_prober is None:
        _isolation("PROBE_UNAVAILABLE", slot)
    try:
        report = deps.isolation_prober(profile, argv, pass_fds)
    except Exception as exc:
        _isolation("PROBE_FAILED", slot, exception_class=type(exc).__name__)
    if not isinstance(report, dict) or report.get("ok") is not True:
        reason = report.get("reason") if isinstance(report, dict) else None
        _isolation(reason if isinstance(reason, str) else "SELF_TEST_FAILED", slot)
    if report.get("profile_digest") != expected_digest:
        _isolation("PROFILE_MISMATCH", slot)


def run_pipeline(docx_bytes: bytes, structure_map, deps: RenderDependencies, delivery_dir=None) -> dict:
    """One render run in STATUS_ORDER_V1 order; returns the evidence record."""
    docx_sha256 = sha256_hex(docx_bytes) if isinstance(docx_bytes, (bytes, bytearray)) else None
    evidence = new_evidence(docx_sha256)
    layout = None
    try:
        package = docx_preflight(bytes(docx_bytes))
        entry_bytes = deps.entry_reader()
        entry_sha256 = sha256_hex(entry_bytes)
        environment = verify_environment(
            deps.manifest_bytes, deps.live_verifier, deps.plan_inputs, deps.dist_resolver, entry_bytes
        )
        manifest = environment.manifest
        evidence["manifest_digest"] = environment.manifest_digest
        evidence["content_binding_digest"] = environment.content_binding_digest
        evidence["runtime_manifest_digest"] = environment.runtime_manifest_digest
        model = build_source_model(package, manifest, structure_map)
        evidence["orphan_relationships"] = model.orphan_relationships
        evidence["auto_hyphenation"] = 1 if model.auto_hyphenation else 0

        paths = deps.runtime_paths
        if paths is None:
            _isolation("RUNTIME_PATHS_UNAVAILABLE")
        check_runtime_paths(manifest, paths)
        render_digest = sandbox_profile_digest(manifest, PROFILE_RENDER)
        inspection_digest = sandbox_profile_digest(manifest, PROFILE_INSPECTION, paths.inspection_read_only_paths)
        evidence["sandbox_profile_digest"] = render_digest
        evidence["inspection_profile_digest"] = inspection_digest
        evidence["inspection_entry_sha256"] = entry_sha256
        render_shared = build_argv_shared(manifest, PROFILE_RENDER)
        inspection_shared = build_argv_shared(manifest, PROFILE_INSPECTION, paths.inspection_read_only_paths)
        _self_test(deps, PROFILE_RENDER, [paths.bwrap_path] + render_shared, (), render_digest, "S4.01")
        try:
            probe_descriptor = deps.entry_binder(entry_bytes, entry_sha256)
        except EntryBindingError:
            _isolation("ENTRY_FD_UNSEALED", "S4.02")
        try:
            argv = [paths.bwrap_path] + substitute_placeholders(inspection_shared, entry_fd=probe_descriptor.fd)
            _self_test(deps, PROFILE_INSPECTION, argv, (probe_descriptor.fd,), inspection_digest, "S4.02")
        finally:
            probe_descriptor.close()

        layout = RunTempLayout(deps.temp_parent).__enter__()
        with open(os.path.join(layout.input_dir, INPUT_FILE_NAME), "wb") as handle:
            handle.write(bytes(docx_bytes))
        render_argv = (
            [paths.bwrap_path]
            + substitute_placeholders(render_shared, run_dirs=layout.run_dirs())
            + conversion_argv(paths.soffice_path, manifest)
        )
        render = deps.runner.run(render_argv, timeout=manifest["timeout_seconds"], pass_fds=())
        if render.timed_out:
            fail("RENDER_TIMEOUT", None, None, "S5.01")
        if not render.launched:
            fail("RENDER_SANDBOX_RUNTIME_INCOMPLETE", "RENDERER_RUNTIME_INCOMPLETE", "START", "S5.02")
        if render.returncode != 0:
            fail("RENDER_SANDBOX_RUNTIME_INCOMPLETE", "RENDERER_RUNTIME_INCOMPLETE", "EXIT_NONZERO", "S5.02",
                 returncode=render.returncode)
        snapshot = take_pdf_snapshot(layout.output_dir)
        pdf_sha256 = sha256_hex(snapshot)
        evidence["pdf_sha256"] = pdf_sha256

        try:
            descriptor = deps.entry_binder(entry_bytes, entry_sha256)
        except EntryBindingError:
            fail("RENDER_SANDBOX_RUNTIME_INCOMPLETE", "INSPECTION_RUNTIME_INCOMPLETE", "ENTRY_FD_UNSEALED", "S5.02")
        evidence["entry_fd_evidence"] = descriptor.evidence
        try:
            child_argv = (
                [paths.bwrap_path]
                + substitute_placeholders(inspection_shared, entry_fd=descriptor.fd)
                + inspection_argv(manifest)
            )
            child = deps.runner.run(
                child_argv,
                stdin_bytes=snapshot,
                timeout=INSPECTION_LIMITS_V1["inspection_timeout_seconds"],
                pass_fds=(descriptor.fd,),
                memory_limit=INSPECTION_LIMITS_V1["inspection_memory_limit_bytes"],
                stdout_limit=INSPECTION_LIMITS_V1["inspection_max_evidence_bytes"] + FINAL_FRAME_MAX_BYTES + 1,
            )
        finally:
            descriptor.close()
        analysis = analyze_child_stream(child.stdout, child, entry_sha256, pdf_sha256)
        evidence["child_protocol_notes"] = list(analysis.notes)
        context = ParentContext(manifest, model)
        outcome = resolve_terminal(analysis, context)
        if outcome is not None:
            return apply_outcome(evidence, outcome)

        frames = analysis.stage_frames
        results = evaluate_results(frames["S5.03"]["evidence"], frames["S6"]["evidence"], context.lines)
        fingerprint, digest = semantic_fingerprint(
            docx_sha256, environment, frames["S6"]["evidence"], context.lines, context.hyperlinks, model
        )
        evidence["render_semantic_fingerprint"] = fingerprint
        evidence["attribution_digest"] = digest
        evidence["utilization"] = results["utilization"]
        evidence["findings"] = _evidence_safe(results["findings"])
        evidence["informational"] = _evidence_safe(results["informational"])
        outcome = Outcome(results["status"], None, None, "S11")
        if delivery_dir is not None:
            deliver_pdf(snapshot, pdf_sha256, delivery_dir)
            evidence["delivered"] = 1
        return apply_outcome(evidence, outcome)
    except StageFailure as failure:
        if failure.outcome.status == "RENDER_DELIVERY_BYTES_MISMATCH":
            evidence["render_semantic_fingerprint"] = None
            evidence["attribution_digest"] = None
            evidence["utilization"] = None
        return apply_outcome(evidence, failure.outcome)
    finally:
        if layout is not None:
            layout.__exit__(None, None, None)
            evidence["temp_root_removed"] = 1 if layout.removed else 0


def render_document(docx_bytes: bytes, structure_map, deps: RenderDependencies = None, delivery_dir=None) -> dict:
    """Public entry point: the validated evidence record of one run."""
    record = run_pipeline(docx_bytes, structure_map, deps or RenderDependencies(), delivery_dir)
    problems = validate_evidence_record(record)
    if problems:
        raise AssertionError("evidence record invalid: %s" % ", ".join(problems))
    return record


# =============================================================================
# OPERATOR BINDING, PROOFS AND FIRST-RENDER DRIVER (operator-run only)
# =============================================================================
#
# POST_PROVISION_BINDING_CAPTURE_V1. Everything below runs only on the provisioned OPERATOR host, under the operator
# prefix interpreter in GOVERNED_RUNTIME_MODE_V1 (`-I -S -B -X pycache_prefix=<empty directory>`), and only from the
# command line at the end of this module. It is orchestration: it derives, measures and verifies; it installs
# nothing, never mutates the operator prefix, apt or the host, and never changes a PRE_PROVISION_PLAN field. The
# render driver calls the existing run_pipeline unchanged. The hermetic tests exercise the pure derivations and the
# fail-closed behavior with fakes; the operator proofs below are never replaced by a mock.
#
# The code lives in this module (not in scripts/verify_document_rendering_environment.py) because the verifier's
# SHA-256 is a PRE_PROVISION_PLAN field (verifier_sha256): changing the verifier would change PLAN_DIGEST.

OPERATOR_CAPTURE_SPEC_ID = "POST_PROVISION_BINDING_CAPTURE_V1"
GOVERNED_PRIMARY_FAMILY = "Liberation Sans"      # CANONICAL_FONT_AUTHORITY_V1 (doctrine record, primary_font)
GOVERNED_FALLBACK_FAMILY = "Arial"               # CANONICAL_FONT_AUTHORITY_V1 (doctrine record, fallback_font)
BWRAP_EXECUTABLE = "/usr/bin/bwrap"
SOFFICE_LAUNCHER = "/usr/bin/soffice"
SANDBOX_PATH_VALUE = "/usr/bin"
FONTCONFIG_FILE_PATH = "/etc/fonts/fonts.conf"
RUNTIME_SITE_PACKAGES_CONSTANT = "RUNTIME_SITE_PACKAGES"
MERGED_USR_LINKS = ("bin", "lib", "lib64")
GOVERNED_FACES = ("REGULAR", "BOLD", "ITALIC", "BOLD_ITALIC")
_SUBFAMILY_FACE = {"Regular": "REGULAR", "Bold": "BOLD", "Italic": "ITALIC", "Bold Italic": "BOLD_ITALIC"}
OPERATOR_PROBE_ENV = {"PATH": "/usr/sbin:/usr/bin:/sbin:/bin", "LANG": "C", "LC_ALL": "C"}

# SANDBOX_ENUMERATION_POLICY_V1: the system-package trees and exact files the pinned LibreOffice launch chain needs,
# established by a real `strace -f` of the pinned conversion on the provisioned OPERATOR and re-proven by the
# executability proof. Whole-directory entries are system-package trees listed by exact path (CONTENT_BINDING_V1);
# nothing else is ever bound, and /, /etc, /home, /root, /workspaces, /var, /run, /mnt, /opt and /srv never are.
SANDBOX_TREE_MOUNTS_V1 = (
    "/etc/fonts", "/etc/libreoffice", "/usr/lib/libreoffice", "/usr/lib/x86_64-linux-gnu", "/usr/share/fontconfig",
    "/usr/share/liblangtag", "/usr/share/libreoffice", "/var/lib/libreoffice",
)
SANDBOX_FILE_MOUNTS_V1 = (
    "/etc/group", "/etc/ld.so.cache", "/etc/nsswitch.conf", "/etc/passwd", "/usr/bin/basename", "/usr/bin/dash",
    "/usr/bin/dirname", "/usr/bin/grep", "/usr/bin/ls", "/usr/bin/sed", "/usr/bin/sh", "/usr/bin/uname",
    "/usr/share/locale/locale.alias", "/usr/share/zoneinfo/UTC",
)
LIBREOFFICE_TREE = "/usr/lib/libreoffice"
SOFFICE_EXECUTABLE = "/usr/lib/libreoffice/program/soffice"


class OperatorFailure(Exception):
    """A named fail-closed operator outcome (status, reason, detail)."""

    def __init__(self, status: str, reason: str, detail=None, **evidence) -> None:
        super().__init__(status, reason, detail)
        self.status = status
        self.reason = reason
        self.detail = detail
        self.evidence = evidence

    def triple(self) -> tuple:
        return (self.status, self.reason, self.detail)


def _op_fail(status: str, reason: str, detail=None, **evidence):
    raise OperatorFailure(status, reason, detail, **evidence)


class OperatorHost:
    """The live host: real files and real processes. The hermetic tests substitute a fake with the same methods."""

    def read_bytes(self, path: str) -> bytes:
        with open(path, "rb") as handle:
            return handle.read()

    def lexists(self, path: str) -> bool:
        return os.path.lexists(path)

    def isfile(self, path: str) -> bool:
        return os.path.isfile(path)

    def isdir(self, path: str) -> bool:
        return os.path.isdir(path)

    def islink(self, path: str) -> bool:
        return os.path.islink(path)

    def readlink(self, path: str) -> str:
        return os.readlink(path)

    def realpath(self, path: str) -> str:
        return os.path.realpath(path)

    def listdir(self, path: str) -> list:
        return sorted(os.listdir(path))

    def run(self, argv, env=None, timeout=300, stdin_bytes=None):
        completed = subprocess.run(list(argv), input=stdin_bytes, capture_output=True, env=dict(env or {}),
                                   timeout=timeout, shell=False, close_fds=True)
        return completed.returncode, completed.stdout, completed.stderr


# -- apt evidence (pure) ---------------------------------------------------------------------------------------------

APT_SOURCE_RECORD_KEYS = (
    "apt_get_version", "apt_install_argv", "os_release", "no_debsig_admission", "apt_path", "apt_effective_source",
    "apt_source_file", "apt_trusted_keyring", "apt_config", "dpkg_config_record", "dpkg_config_record_f0",
    "apt_update_line", "apt_inrelease", "apt_origin",
)


def parse_evidence_lines(text: str) -> dict:
    """The `EVIDENCE key=value` lines of the provisioning run log, by key, values verbatim and in order."""
    by_key = {}
    for line in text.split("\n"):
        line = line.rstrip("\r")
        if line.startswith("EVIDENCE ") and "=" in line:
            key, _, value = line[len("EVIDENCE "):].partition("=")
            by_key.setdefault(key, []).append(value)
    return by_key


def apt_records_from_evidence(by_key: dict, evidence_sha256: str) -> tuple:
    """(apt_preinstall_snapshot, apt_installed_delta, apt_source_record) of a PASSED provisioning run, from its
    EVIDENCE lines only. A malformed or missing record is a failure; nothing is defaulted."""
    snapshot, seen = [], set()
    for line in by_key.get("apt_preinstall_snapshot", ()):
        fields = line.split("\t")
        if len(fields) != 5 or fields[4] not in ("0", "1") or not all(fields[:4]):
            _op_fail("RENDER_ENVIRONMENT_UNVERIFIED", "APT_EVIDENCE", "PREINSTALL_SNAPSHOT", line=line[:80])
        key = (fields[0], fields[1])
        if key in seen:
            _op_fail("RENDER_ENVIRONMENT_UNVERIFIED", "APT_EVIDENCE", "PREINSTALL_DUPLICATE", package=fields[0])
        seen.add(key)
        snapshot.append([fields[0], fields[1], fields[2], fields[3], int(fields[4])])
    if not snapshot:
        _op_fail("RENDER_ENVIRONMENT_UNVERIFIED", "APT_EVIDENCE", "PREINSTALL_EMPTY")
    snapshot.sort(key=lambda row: (row[0].encode("utf-8"), row[1].encode("utf-8")))
    delta, seen = [], set()
    for line in by_key.get("apt_installed_delta", ()):
        fields = line.split("|")
        if len(fields) != 5 or fields[2] not in ("ADDED", "UPGRADED", "DOWNGRADED", "REMOVED", "STATUS_CHANGED"):
            _op_fail("RENDER_ENVIRONMENT_UNVERIFIED", "APT_EVIDENCE", "DELTA", line=line[:80])
        key = (fields[0], fields[1])
        if key in seen:
            _op_fail("RENDER_ENVIRONMENT_UNVERIFIED", "APT_EVIDENCE", "DELTA_DUPLICATE", package=fields[0])
        seen.add(key)
        delta.append({"package": fields[0], "architecture": fields[1], "change": fields[2],
                      "version_before": fields[3] or None, "version_after": fields[4] or None})
    delta.sort(key=lambda row: (row["package"].encode("utf-8"), row["architecture"].encode("utf-8")))
    records = {}
    for key in APT_SOURCE_RECORD_KEYS:
        values = list(by_key.get(key, ()))
        if not values and key not in ("dpkg_config_record_f0", "apt_source_file", "apt_trusted_keyring"):
            _op_fail("RENDER_ENVIRONMENT_UNVERIFIED", "APT_EVIDENCE", "SOURCE_RECORD_MISSING", key=key)
        records[key] = values
    if by_key.get("result", [""])[-1][:11] != "PROVISIONED":
        _op_fail("RENDER_ENVIRONMENT_UNVERIFIED", "APT_EVIDENCE", "RUN_NOT_PROVISIONED")
    source_record = {"spec": "APT_SOURCE_RECORD_V1", "provisioning_evidence_sha256": evidence_sha256,
                     "records": records}
    return snapshot, delta, source_record


# -- fonts (pure) ----------------------------------------------------------------------------------------------------

def parse_font_file(data: bytes) -> dict:
    """The sfnt facts of one font file: family (name ID 1), subfamily (ID 2), PostScript name (ID 6) and whether
    an fvar table (a variable font) exists. Platform 3 (Windows) records are preferred, platform 1 is the fallback."""
    if len(data) < 12 or data[:4] not in (b"\x00\x01\x00\x00", b"true", b"OTTO", b"ttcf"):
        _op_fail("RENDER_FONT_MANIFEST_INCOMPLETE", "NAME_TABLE_UNMAPPED", "NOT_SFNT")
    if data[:4] == b"ttcf":
        _op_fail("RENDER_FONT_MANIFEST_INCOMPLETE", "NAME_TABLE_UNMAPPED", "COLLECTION")
    table_count = struct.unpack(">H", data[4:6])[0]
    tables = {}
    for index in range(table_count):
        record = data[12 + 16 * index: 28 + 16 * index]
        if len(record) != 16:
            _op_fail("RENDER_FONT_MANIFEST_INCOMPLETE", "NAME_TABLE_UNMAPPED", "TABLE_DIRECTORY")
        offset, length = struct.unpack(">II", record[8:16])
        tables[record[:4].decode("latin-1")] = (offset, length)
    if "name" not in tables:
        _op_fail("RENDER_FONT_MANIFEST_INCOMPLETE", "NAME_TABLE_UNMAPPED", "NO_NAME_TABLE")
    offset, length = tables["name"]
    name_table = data[offset:offset + length]
    if len(name_table) < 6:
        _op_fail("RENDER_FONT_MANIFEST_INCOMPLETE", "NAME_TABLE_UNMAPPED", "NAME_TABLE_SHORT")
    count, string_offset = struct.unpack(">HH", name_table[2:6])
    found = {}
    for index in range(count):
        record = name_table[6 + 12 * index: 18 + 12 * index]
        if len(record) != 12:
            _op_fail("RENDER_FONT_MANIFEST_INCOMPLETE", "NAME_TABLE_UNMAPPED", "NAME_RECORD")
        platform, _encoding, language, name_id, size, start = struct.unpack(">HHHHHH", record)
        raw = name_table[string_offset + start: string_offset + start + size]
        if platform == 3:
            text = raw.decode("utf-16-be", "strict")
            rank = 0 if language == 0x409 else 1
        elif platform == 1:
            text = raw.decode("mac_roman", "strict")
            rank = 2
        else:
            continue
        if name_id in (1, 2, 6) and (name_id not in found or rank < found[name_id][0]):
            found[name_id] = (rank, text)
    if not all(key in found for key in (1, 2, 6)):
        _op_fail("RENDER_FONT_MANIFEST_INCOMPLETE", "NAME_TABLE_UNMAPPED", "NAME_IDS")
    return {"family": found[1][1], "subfamily": found[2][1], "postscript": found[6][1], "variable": "fvar" in tables}


def font_face_of(subfamily: str) -> str:
    face = _SUBFAMILY_FACE.get(subfamily)
    if face is None:
        _op_fail("RENDER_FONT_MANIFEST_INCOMPLETE", "NAME_TABLE_UNMAPPED", "SUBFAMILY", subfamily=subfamily[:64])
    return face


def provisioned_font_records(font_paths: list, read_bytes) -> list:
    """The governed font files: every given file whose family is the governed primary family. Each record is
    {path, sha256, postscript, family, face}. A variable font, a duplicate PostScript name or a missing face
    fails closed (RENDER_FONT_VARIABLE_DENIED / RENDER_FONT_MANIFEST_INCOMPLETE)."""
    records = []
    for path in sorted(font_paths):
        data = read_bytes(path)
        facts = parse_font_file(data)
        if facts["variable"]:
            _op_fail("RENDER_FONT_VARIABLE_DENIED", "FVAR_TABLE", None, path=path)
        if facts["family"] != GOVERNED_PRIMARY_FAMILY:
            continue
        records.append({"path": path, "sha256": sha256_hex(data), "postscript": facts["postscript"],
                        "family": facts["family"], "face": font_face_of(facts["subfamily"])})
    if sorted(record["face"] for record in records) != sorted(GOVERNED_FACES):
        _op_fail("RENDER_FONT_MANIFEST_INCOMPLETE", "NAME_TABLE_UNMAPPED", "FACE_SET",
                 faces=sorted(record["face"] for record in records))
    names = [record["postscript"] for record in records]
    if len(set(names)) != len(names) or any(_PDF_NAME_KEY.match(name) is None for name in names):
        _op_fail("RENDER_FONT_MANIFEST_INCOMPLETE", "NAME_TABLE_UNMAPPED", "POSTSCRIPT_NAMES")
    return records


def normalize_declared_family(name: str) -> str:
    """The string normalization of the docx side (NFKC, whitespace collapsed, casefold) of FONT_CANONICALIZATION_V1."""
    return " ".join(unicodedata.normalize("NFKC", name).split()).casefold()


def strip_pdf_name_form(value) -> str:
    """FONT_NAME_FORM_V1 for one observed name: the str, one leading slash removed, one subset prefix removed; a
    value outside U+0021-U+007E is unusable evidence (never repaired)."""
    if not isinstance(value, str):
        _op_fail("RENDER_FONT_MANIFEST_INCOMPLETE", "NAME_TABLE_UNMAPPED", "NAME_FORM_TYPE")
    text = value[1:] if value.startswith("/") else value
    text = _SUBSET_PREFIX.sub("", text, count=1)
    if _PDF_NAME_KEY.match(text) is None:
        _op_fail("RENDER_FONT_MANIFEST_INCOMPLETE", "NAME_TABLE_UNMAPPED", "NAME_FORM_ASCII")
    return text


def build_font_tables(fonts: list, observation: dict) -> dict:
    """The canonical font identity tables from the governed font records and one real font-probe observation
    ({"fonts": [{"inventory": str, "descendant": str|None, "descriptor": str|None, "subtype": str}],
      "span_names": [str...]}). The tables are never invented: every name form a real render emitted must be a
    PostScript name of a governed provisioned font and every governed face must be observed through both
    libraries, else RENDER_FONT_MANIFEST_INCOMPLETE (ALIAS_FORM_MISSING / NAME_TABLE_UNMAPPED)."""
    identity = {record["postscript"]: {"canonical_family_id": record["family"], "face": record["face"]}
                for record in fonts}
    pdf_map = dict(identity)
    pypdf_forms, pdfminer_forms, type0 = set(), set(), []
    for font in observation["fonts"]:
        for key in ("inventory", "descendant", "descriptor"):
            if font.get(key) is not None:
                pypdf_forms.add(strip_pdf_name_form(font[key]))
        if font.get("subtype") == "Type0":
            type0.append(font)
    for name in observation["span_names"]:
        pdfminer_forms.add(strip_pdf_name_form(name))
    for form in sorted(pypdf_forms | pdfminer_forms):
        if form not in identity:
            _op_fail("RENDER_FONT_MANIFEST_INCOMPLETE", "ALIAS_FORM_MISSING", None, form=form)
    for record in fonts:
        for label, forms in (("pypdf", pypdf_forms), ("pdfminer", pdfminer_forms)):
            if record["postscript"] not in forms:
                _op_fail("RENDER_FONT_MANIFEST_INCOMPLETE", "NAME_TABLE_UNMAPPED", "FACE_NOT_OBSERVED",
                         library=label, face=record["face"])
    for font in observation["fonts"]:
        names = {strip_pdf_name_form(font[key]) for key in ("inventory", "descendant", "descriptor")
                 if font.get(key) is not None}
        if len({json.dumps(identity[name], sort_keys=True) for name in names}) != 1:
            _op_fail("RENDER_FONT_INVENTORY_MISMATCH", "DESCRIPTOR_NAME", None, names=sorted(names))
    if not type0:
        form = "NO_TYPE0_FONT_OBSERVED"
    else:
        parent = {strip_pdf_name_form(font["inventory"]) for font in type0}
        descendant = {strip_pdf_name_form(font["descendant"]) for font in type0 if font.get("descendant")}
        form = "PARENT_BASEFONT_EQUALS_DESCENDANT_BASEFONT" if parent == descendant else "UNPINNED"
        if form == "UNPINNED":
            _op_fail("RENDER_FONT_MANIFEST_INCOMPLETE", "ALIAS_FORM_MISSING", "TYPE0_NAME_FORM")
    families = sorted({GOVERNED_PRIMARY_FAMILY, GOVERNED_FALLBACK_FAMILY})
    return {
        "canonical_families": families,
        "docx_family_to_canonical": {normalize_declared_family(name): name for name in families},
        "pdf_basefont_to_canonical": {key: pdf_map[key] for key in sorted(pdf_map)},
        "approved_substitutions": {GOVERNED_PRIMARY_FAMILY: [GOVERNED_FALLBACK_FAMILY]},
        "marker_glyph_map": [],
        "pdfminer_type0_name_form": form,
    }


def errno_sets_from_probe(result: dict) -> dict:
    """sandbox_expected_unreachable_errnos from one in-sandbox probe result: only an observed value inside the
    contract-defined set is accepted, and the manifest set is exactly that observed value (narrowing only)."""
    if isinstance(result, dict) and result.get("ok") is not True:
        _op_fail("RENDER_ISOLATION_UNAVAILABLE", "SELF_TEST_FAILED", "PROBE", failures=result.get("failures"))
    connects = result.get("connects") if isinstance(result, dict) else None
    if not isinstance(connects, dict) or set(connects) != set(EXPECTED_UNREACHABLE_ERRNOS_V1):
        _op_fail("RENDER_ISOLATION_UNAVAILABLE", "PROBE_OUTPUT", "CONNECTS")
    sets = {}
    for family, allowed in EXPECTED_UNREACHABLE_ERRNOS_V1.items():
        observed = connects[family]
        if observed not in allowed:
            _op_fail("RENDER_ISOLATION_UNAVAILABLE", "SELF_TEST_FAILED", "CONNECT", family=family, observed=observed)
        sets[family] = [observed]
    if result.get("control") != "CONNECTED":
        _op_fail("RENDER_ISOLATION_UNAVAILABLE", "SELF_TEST_FAILED", "CONTROL")
    return sets


# -- sandbox enumeration, closures and content-binding roots ----------------------------------------------------------

def _under(path: str, base: str) -> bool:
    return path == base or path.startswith(base.rstrip("/") + "/")


def derive_sandbox_symlinks(host, prefix: str, closures: list) -> list:
    """The read-only root scaffold symlinks: the merged-/usr links of the host root, the loader and soname links of
    the native closures (placed at the REAL parent directory of each recorded link path, never through a scaffold
    symlink) and the interpreter links of the operator prefix launcher. Sorted by path; a path with two targets is
    a failure."""
    found = {}

    def add(path: str, target: str) -> None:
        if path in found and found[path] != target:
            _op_fail("RENDER_ISOLATION_UNAVAILABLE", "SCAFFOLD_CONFLICT", None, path=path)
        found[path] = target

    for name in MERGED_USR_LINKS:
        path = "/" + name
        if host.islink(path):
            add(path, host.readlink(path))
    for closure in closures:
        for link_path, target in closure["links"]:
            parent = host.realpath(link_path.rsplit("/", 1)[0] or "/")
            add(parent.rstrip("/") + "/" + link_path.rsplit("/", 1)[1], target)
    bin_dir = prefix.rstrip("/") + "/bin"
    for name in host.listdir(bin_dir):
        path = bin_dir + "/" + name
        if name.isascii() and name.startswith("python") and host.islink(path):
            add(path, host.readlink(path))
    return [{"path": path, "target": found[path]} for path in sorted(found)]


def derive_sandbox(host, manifest: dict, fonts: list, closures: list) -> dict:
    """SANDBOX_ENUMERATION_POLICY_V1 applied to the live host: every policy path must exist with its kind; the
    governed font files and the base interpreter are added by exact path. Fails closed on a missing or mistyped
    path and on any mount under a canary path."""
    canaries = manifest["sandbox_forbidden_canary_paths"]
    interpreter = manifest["operator_base_interpreter"]
    base_real = host.realpath(interpreter["path"])
    trees = list(SANDBOX_TREE_MOUNTS_V1) + [interpreter["stdlib_path"]]
    files = list(SANDBOX_FILE_MOUNTS_V1) + [base_real] + [record["path"] for record in fonts]
    for path in trees:
        if not host.isdir(path) or host.islink(path):
            _op_fail("RENDER_ISOLATION_UNAVAILABLE", "MOUNT_MISSING", "TREE", path=path)
    for path in files:
        if not host.lexists(path) or not host.isfile(host.realpath(path)):
            _op_fail("RENDER_ISOLATION_UNAVAILABLE", "MOUNT_MISSING", "FILE", path=path)
    mounts = sorted(set(trees) | set(files))
    for mount in mounts:
        if mount in _FORBIDDEN_WHOLE_BINDS or any(_posix_under(mount, canary) for canary in canaries):
            _op_fail("RENDER_ISOLATION_UNAVAILABLE", "FORBIDDEN_MOUNT", None, path=mount)
    if not host.isfile(SOFFICE_EXECUTABLE) or not _under(host.realpath(SOFFICE_LAUNCHER), LIBREOFFICE_TREE):
        _op_fail("RENDER_ISOLATION_UNAVAILABLE", "MOUNT_MISSING", "SOFFICE", path=SOFFICE_EXECUTABLE)
    if not host.isfile(BWRAP_EXECUTABLE):
        _op_fail("RENDER_ISOLATION_UNAVAILABLE", "MOUNT_MISSING", "BWRAP", path=BWRAP_EXECUTABLE)
    return {
        "sandbox_read_only_paths": mounts,
        "sandbox_dirs": [],
        "sandbox_symlinks": derive_sandbox_symlinks(host, manifest["operator_python_prefix"], closures),
        "sandbox_path": SANDBOX_PATH_VALUE,
        "sandbox_probe_interpreter_path": base_real,
        "fontconfig_file": FONTCONFIG_FILE_PATH,
    }


def root_id_of(kind: str, path: str) -> str:
    return "%s:%s" % (kind.lower(), path)


def build_content_roots(host, manifest: dict, sandbox: dict, fonts: list, closure_base: dict, closure_prefix: dict,
                        distributions: list, absent_paths: list, site_packages: str) -> list:
    """The CONTENT_BINDING_V1 roots (without expected digests), by (kind, path); ids are the sortable strings
    documented below. a: soffice tree and executable; b: every other sandbox mount; c: bubblewrap; d/f: base
    interpreter file (also the probe interpreter); e: DIST_RECORD per approved distribution; g: stdlib; h: prefix
    pyvenv.cfg; i: native closure members (i.prefix for native_closure_prefix, i.base only for base-only members);
    j: ABSENT; k: the operator-prefix site-packages tree (an inspection mount)."""
    interpreter = manifest["operator_base_interpreter"]
    prefix = manifest["operator_python_prefix"]
    base_real = host.realpath(interpreter["path"])
    roots = {}

    def add(group: str, kind: str, path: str, label: str = None) -> None:
        key = (kind, path)
        if key not in roots:
            roots[key] = {"id": "%s.%s" % (group, label or root_id_of(kind, path)), "kind": kind, "path": path}

    add("a", "TREE", LIBREOFFICE_TREE, "soffice_tree")
    add("a", "FILE", SOFFICE_EXECUTABLE, "soffice_executable")
    add("c", "FILE", BWRAP_EXECUTABLE, "bubblewrap_executable")
    add("f", "FILE", base_real, "base_interpreter")
    add("g", "STDLIB_TREE", interpreter["stdlib_path"], "stdlib")
    add("h", "FILE", prefix.rstrip("/") + "/pyvenv.cfg", "prefix_pyvenv_cfg")
    add("k", "TREE", site_packages, "site_packages")
    # The closure members are added before the sandbox mounts so that a member that is also a mount (for example
    # /etc/ld.so.cache) keeps its i.prefix id, from which the inspection mounts are derived.
    for closure, group in ((closure_prefix, "i.prefix"), (closure_base, "i.base")):
        for path, _digest in closure["files"] + closure["loader_inputs"]:
            add(group, "FILE", path)
        for path, _target in closure["links"]:
            add(group, "LINK", path)
        for path in closure["absent"]:
            add(group, "ABSENT", path)
    for mount in sandbox["sandbox_read_only_paths"]:
        add("b", "TREE" if host.isdir(mount) else "FILE", mount)
    for name in distributions:
        add("e", "DIST_RECORD", name, "dist." + name)
    for path in sorted(set(absent_paths)):
        add("j", "ABSENT", path)
    return [roots[key] for key in sorted(roots, key=lambda item: roots[item]["id"].encode("utf-8"))]


def compute_root_digests(roots: list, sandbox_mounts: list, dist_resolver=None) -> tuple:
    """(roots with expected_digest, exclusions): every digest is computed by the adapter's own root_digest. A
    symlink of a TREE whose target lies outside every mount and root is recorded as an exact-relpath exclusion
    (CONTENT_BINDING_V1 `exclusions`, evidence and part of manifest_digest) and the root is recomputed."""
    tree_paths = tuple(root["path"] for root in roots if root["kind"] in ("TREE", "STDLIB_TREE"))
    exact = {root["path"] for root in roots if root["kind"] in ("FILE", "LINK")}
    covered = tree_paths + tuple(sandbox_mounts) + tuple(exact)
    exclusions = {}
    result = []
    for root in roots:
        for _attempt in range(512):
            try:
                digest = root_digest(root, covered, exclusions, dist_resolver)
            except ContentBindingFailure as failure:
                if failure.reason == "SYMLINK_OUTSIDE_COVERAGE":
                    exclusions.setdefault(root["id"], []).append(failure.relpath)
                    continue
                _op_fail(failure.status, failure.reason, None, root_id=root["id"], relpath=failure.relpath)
            else:
                break
        else:
            _op_fail("RENDER_CONTENT_BINDING_INCOMPLETE", "EXCLUSION_LIMIT", None, root_id=root["id"])
        result.append(dict(root, expected_digest=digest))
    flat = [{"root_id": root_id, "relpath": relpath,
             "reason": "SYMLINK_TARGET_OUTSIDE_MOUNTS"}
            for root_id in sorted(exclusions) for relpath in sorted(set(exclusions[root_id]))]
    return result, flat


def derive_inspection_paths(manifest: dict) -> tuple:
    """The inspection-profile read-only mounts, DERIVED from the content-binding roots (INSPECTION_PROFILE_V1 (c)):
    the interpreter file, the standard-library tree, the prefix pyvenv.cfg, the approved site-packages tree and every
    FILE root of native_closure_prefix (its members and loader inputs). Links are scaffold symlinks, not mounts."""
    wanted = {"f.base_interpreter", "g.stdlib", "h.prefix_pyvenv_cfg", "k.site_packages"}
    paths = set()
    trees = [root["path"] for root in manifest["content_binding"]["roots"] if root["id"] in ("g.stdlib", "k.site_packages")]
    for root in manifest["content_binding"]["roots"]:
        if root["id"] in wanted:
            paths.add(root["path"])
        elif root["id"].startswith("i.prefix.file:") and not any(_posix_under(root["path"], tree) for tree in trees):
            paths.add(root["path"])
    return tuple(sorted(paths))


def runtime_paths_from_manifest(manifest: dict) -> RuntimePaths:
    """RuntimePaths of a populated manifest: the pinned executables are the FILE roots a.soffice_executable and
    c.bubblewrap_executable; the inspection mounts are derived from the roots."""
    by_id = {root["id"]: root for root in manifest["content_binding"]["roots"]}
    for key in ("a.soffice_executable", "c.bubblewrap_executable"):
        if key not in by_id:
            _op_fail("RENDER_ENVIRONMENT_UNVERIFIED", "CONTENT_BINDING_SHAPE", key)
    return RuntimePaths(by_id["c.bubblewrap_executable"]["path"], by_id["a.soffice_executable"]["path"],
                        derive_inspection_paths(manifest))


def absent_candidate_paths(manifest: dict, fs, site_packages: str, launch_checks: list) -> list:
    """CONTENT_BINDING_V1 (j): every non-existent entry of sys_path_isolated, sys_path_isolated_prefix and
    runtime_sys_path, the python*.zip location of each list and every STARTUP_PATH_INPUTS_V1 candidate of the given
    launch forms (launch path, real path, permitted candidate) that does not exist."""
    interpreter = manifest["operator_base_interpreter"]
    entries = list(interpreter["sys_path_isolated"]) + list(interpreter["sys_path_isolated_prefix"]) + [site_packages]
    absent = {entry for entry in entries if not fs.lexists(entry)}
    stdlib_parent = interpreter["stdlib_path"].rstrip("/").rsplit("/", 1)[0]
    prefix_lib = manifest["operator_python_prefix"].rstrip("/") + "/lib"
    for parent in (stdlib_parent, prefix_lib):
        for entry in fs.listdir(parent):
            if entry.startswith("python") and entry.endswith(".zip"):
                _op_fail("RENDER_ENVIRONMENT_UNVERIFIED", "SYS_PATH_UNBOUND", "ZIP_PRESENT", path=parent + "/" + entry)
    for zip_entry in ("python%s%s.zip" % tuple(interpreter["python_version"].split(".")[:2]),):
        absent.add(stdlib_parent + "/" + zip_entry)
        absent.add(prefix_lib + "/" + zip_entry)
    verifier = load_verifier()
    for launch, real, permitted in launch_checks:
        absent.update(verifier.check_startup_path_inputs(launch, real, fs, permitted))
    return sorted(absent)


def runtime_sys_path_of(manifest: dict, site_packages: str) -> list:
    """The governed runtime sys.path: the validated prefix entries followed by the single explicit addition."""
    return list(manifest["operator_base_interpreter"]["sys_path_isolated_prefix"]) + [site_packages]


class _FsView:
    """The verifier's filesystem facts over an OperatorHost (so the same functions run on fakes and on the host)."""

    def __init__(self, host) -> None:
        self.host = host

    def lexists(self, path):
        return self.host.lexists(path)

    def listdir(self, path):
        return self.host.listdir(path) if self.host.isdir(path) else []

    def realpath(self, path):
        return self.host.realpath(path)

    def isdir(self, path):
        return self.host.isdir(path)


def load_verifier():
    """The operator verifier module, loaded by file path (its bytes are PRE_PROVISION_PLAN-bound and unchanged)."""
    name = "document_render_verifier"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, _SRC_DIR.parent / "scripts" / "verify_document_rendering_environment.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def compute_native_closures(host, manifest: dict, site_packages: str) -> tuple:
    """(NATIVE_CLOSURE_V1 of operator_base_interpreter, native_closure_prefix) over the live host with the
    verifier's own model. The base closure's digest must equal the plan value; the prefix closure is the closure
    of root set i-iv (the interpreter, the standard-library ELF files and the approved site-packages ELF files)."""
    verifier = load_verifier()
    interpreter = manifest["operator_base_interpreter"]
    real = host.realpath(interpreter["path"])
    fs = verifier.RealFilesystem()
    loader = fs.elf(real)["interp"]
    returncode, stdout, _stderr = host.run([loader, "--help"], env=OPERATOR_PROBE_ENV, timeout=60)
    if returncode != 0:
        _op_fail("BASE_INTERPRETER_MISMATCH", "NATIVE_UNRESOLVED", "LOADER_DIRS")
    fs._loader_help = stdout.decode("utf-8", "replace")
    stdlib = interpreter["stdlib_path"]
    pip = manifest["installer_pip_package_path"]
    base = verifier.compute_native_closure([real] + verifier.elf_files_under(stdlib, stdlib=True)
                                           + verifier.elf_files_under(pip), fs)
    if verifier.native_closure_digest(base) != interpreter["native_closure_digest"]:
        _op_fail("BASE_INTERPRETER_MISMATCH", "NATIVE_CLOSURE", "POST_PROVISION")
    prefix_closure = verifier.compute_native_closure(
        [real] + verifier.elf_files_under(stdlib, stdlib=True) + verifier.elf_files_under(site_packages), fs)
    return base, prefix_closure


def assemble_post_manifest(pre_manifest: dict, values: dict) -> dict:
    """The runtime manifest: PRE_PROVISION_PLAN members byte-for-byte as in PRE_MANIFEST, every POST_PROVISION_BINDING
    member from VALUES (none null, none missing, none extra), set members sorted, manifest_self_digest computed. A
    changed PRE member is impossible by construction and is checked (PLAN_AMENDMENT_LOOP_V1 otherwise)."""
    post_keys = tuple(key for key in MANIFEST_POST_PROVISION_KEYS if key != "manifest_self_digest")
    if set(values) != set(post_keys):
        _op_fail("RENDER_ENVIRONMENT_UNVERIFIED", "POST_BINDING_UNPOPULATED", None,
                 missing=sorted(set(post_keys) - set(values)), extra=sorted(set(values) - set(post_keys)))
    for key in post_keys:
        if values[key] is None:
            _op_fail("RENDER_ENVIRONMENT_UNVERIFIED", "POST_BINDING_UNPOPULATED", key)
        if pre_manifest.get(key) is not None:
            _op_fail("RENDER_ENVIRONMENT_UNVERIFIED", "POST_KEYS_NOT_NULL", key)
    manifest = {}
    for key in pre_manifest:
        manifest[key] = values[key] if key in values else pre_manifest[key]
    for key in MANIFEST_SET_KEYS:
        if key in values:
            manifest[key] = sorted(set(values[key]))
    manifest["manifest_self_digest"] = None
    manifest["manifest_self_digest"] = manifest_digest(manifest)
    for key in MANIFEST_PRE_PROVISION_KEYS:
        if manifest[key] != pre_manifest[key]:
            _op_fail("RENDER_ENVIRONMENT_UNVERIFIED", "PLAN_AMENDMENT_REQUIRED", key)
    if pre_provision_plan_digest(manifest) != pre_provision_plan_digest(pre_manifest):
        _op_fail("RENDER_ENVIRONMENT_UNVERIFIED", "PLAN_AMENDMENT_REQUIRED", "PRE_PROVISION_PLAN_DIGEST")
    return manifest


def manifest_text(manifest: dict) -> str:
    """The canonical file form of the manifest: indent 2, ensure_ascii false, LF, one trailing newline."""
    return json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"


# -- verifier-generated fixtures ---------------------------------------------------------------------------------------

_FIXTURE_FAMILY = GOVERNED_PRIMARY_FAMILY
FULL_FIXTURE_EXTRA_BULLETS = 50
_FIXTURE_W = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" ' \
             'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"'
_FIXTURE_XML = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'


def _fixture_run(text: str, bold: bool = False, italic: bool = False) -> str:
    properties = '<w:rFonts w:ascii="%s" w:hAnsi="%s"/>' % (_FIXTURE_FAMILY, _FIXTURE_FAMILY)
    properties += "<w:b/>" if bold else ""
    properties += "<w:i/>" if italic else ""
    return '<w:r><w:rPr>%s</w:rPr><w:t xml:space="preserve">%s</w:t></w:r>' % (properties, text)


def _fixture_zip(parts: list) -> bytes:
    """A deterministic stdlib zip (fixed timestamps and order, deflate)."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, text in parts:
            info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, text.encode("utf-8"))
    return buffer.getvalue()


def build_fixture_docx(kind: str) -> tuple:
    """(docx bytes, structure map) of a verifier-generated synthetic fixture, from a fixed template with stdlib
    zipfile (never a Bora document). EXECUTABILITY: a name line, a heading, two bullet items, a paragraph with one
    external hyperlink and a paragraph exercising bold, italic and bold-italic. FONT_PROBE: one paragraph per
    face of the governed font."""
    ct = ('<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
          '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
          '<Default Extension="xml" ContentType="application/xml"/>'
          '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.'
          'wordprocessingml.document.main+xml"/>'
          '<Override PartName="/word/numbering.xml" ContentType="' + CT_NUMBERING + '"/>'
          '<Override PartName="/word/styles.xml" ContentType="' + CT_STYLES + '"/></Types>')
    root_rels = ('<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                 '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/'
                 'officeDocument" Target="word/document.xml"/></Relationships>')
    doc_rels = ('<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/'
                'numbering" Target="numbering.xml"/>'
                '<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/'
                'styles" Target="styles.xml"/>'
                '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/'
                'hyperlink" Target="https://example.com/" TargetMode="External"/></Relationships>')
    numbering = ('<w:numbering %s><w:abstractNum w:abstractNumId="0"><w:multiLevelType w:val="hybridMultilevel"/>'
                 '<w:lvl w:ilvl="0"><w:start w:val="1"/><w:numFmt w:val="bullet"/><w:lvlText w:val="•"/>'
                 '<w:lvlJc w:val="left"/><w:pPr><w:ind w:left="720" w:hanging="360"/></w:pPr><w:rPr>'
                 '<w:rFonts w:ascii="%s" w:hAnsi="%s" w:hint="default"/></w:rPr></w:lvl></w:abstractNum>'
                 '<w:num w:numId="1"><w:abstractNumId w:val="0"/></w:num></w:numbering>'
                 % (_FIXTURE_W, _FIXTURE_FAMILY, _FIXTURE_FAMILY))

    styles = ('<w:styles %s><w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="%s" w:hAnsi="%s"/><w:sz w:val="22"/>'
              '</w:rPr></w:rPrDefault></w:docDefaults><w:style w:type="paragraph" w:default="1" w:styleId="Normal">'
              '<w:name w:val="Normal"/></w:style></w:styles>' % (_FIXTURE_W, _FIXTURE_FAMILY, _FIXTURE_FAMILY))

    def paragraph(runs: str, listed: bool = False) -> str:
        properties = '<w:pPr><w:numPr><w:ilvl w:val="0"/><w:numId w:val="1"/></w:numPr></w:pPr>' if listed else ""
        return "<w:p>%s%s</w:p>" % (properties, runs)

    if kind in ("EXECUTABILITY", "EXECUTABILITY_FULL"):
        # EXECUTABILITY_FULL adds bullets until one tightly-margined page is full (the constructed >=92% document of
        # the real-LibreOffice proof); EXECUTABILITY stays under-filled (the proof that the page-utilization check
        # fails an under-filled document).
        extra = FULL_FIXTURE_EXTRA_BULLETS if kind == "EXECUTABILITY_FULL" else 0
        rows = [
            (paragraph(_fixture_run("Alex Example", bold=True)), "CONTACT_LINE", "Alex Example", False),
            (paragraph(_fixture_run("Experience Summary", bold=True)), "SECTION_HEADING", "Experience Summary", False),
            (paragraph(_fixture_run("Delivered quarterly reporting for operations teams"), listed=True), "BULLET_TEXT",
             "Delivered quarterly reporting for operations teams", True),
            (paragraph(_fixture_run("Maintained reference data and reconciliation checks"), listed=True), "BULLET_TEXT",
             "Maintained reference data and reconciliation checks", True),
        ]
        for index in range(extra):
            text_line = "Prepared reconciliation schedule number %d for the monthly operations review" % (index + 1)
            rows.append((paragraph(_fixture_run(text_line), listed=True), "BULLET_TEXT", text_line, True))
        rows.append((paragraph(_fixture_run("Portfolio at ") + '<w:hyperlink r:id="rId2">' + _fixture_run("Example Site")
                               + "</w:hyperlink>"), "SUMMARY_TEXT", "Portfolio at Example Site", False))
        rows.append((paragraph(_fixture_run("Regular ") + _fixture_run("Bold ", bold=True) + _fixture_run("Italic ", italic=True)
                               + _fixture_run("BoldItalic", bold=True, italic=True)), "SUMMARY_TEXT",
                     "Regular Bold Italic BoldItalic", False))
        body = "".join(row[0] for row in rows)
        structure_map = [
            {"paragraph_index": index, "content_type": row[1],
             "list_semantics": {"ilvl": 0, "numFmt": "bullet", "numId": 1} if row[3] else None, "paragraph_text": row[2]}
            for index, row in enumerate(rows)
        ]
        margin = "720" if extra else "1440"
    elif kind == "FONT_PROBE":
        body = "".join([
            paragraph(_fixture_run("Probe Regular")),
            paragraph(_fixture_run("Probe Bold", bold=True)),
            paragraph(_fixture_run("Probe Italic", italic=True)),
            paragraph(_fixture_run("Probe BoldItalic", bold=True, italic=True)),
        ])
        structure_map = None
        margin = "1440"
    else:
        raise ValueError(kind)
    document = ("<w:document %s><w:body>%s<w:sectPr><w:pgSz w:w='12240' w:h='15840'/><w:pgMar w:top='%s' "
                "w:right='1440' w:bottom='%s' w:left='1440' w:header='360' w:footer='360' w:gutter='0'/>"
                "</w:sectPr></w:body></w:document>" % (_FIXTURE_W, body, margin, margin)).replace("'", chr(34))
    data = _fixture_zip([
        ("[Content_Types].xml", _FIXTURE_XML + ct), ("_rels/.rels", _FIXTURE_XML + root_rels),
        ("word/_rels/document.xml.rels", _FIXTURE_XML + doc_rels), ("word/document.xml", _FIXTURE_XML + document),
        ("word/numbering.xml", _FIXTURE_XML + numbering), ("word/styles.xml", _FIXTURE_XML + styles),
    ])
    return data, structure_map


# The font probe: run by the operator-prefix interpreter over a real LibreOffice PDF; collects, per font entry, the
# pypdf name forms (inventory BaseFont, Type0 descendant BaseFont, FontDescriptor FontName) and the pdfminer.six
# LTChar.fontname of every character. It reads and prints; it assigns no library configuration.
FONT_PROBE_CODE = r'''
import io, json, sys
sys.path.append(sys.argv[2])
from pypdf import PdfReader
from pdfminer.converter import PDFPageAggregator
from pdfminer.layout import LTChar
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfinterp import PDFPageInterpreter, PDFResourceManager
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfparser import PDFParser
data = open(sys.argv[1], "rb").read()
reader = PdfReader(io.BytesIO(data))
fonts = []
for page in reader.pages:
    resources = page.get("/Resources")
    resources = resources.get_object() if resources is not None else {}
    font_dict = resources.get("/Font")
    font_dict = font_dict.get_object() if font_dict is not None else {}
    for key in sorted(font_dict):
        font = font_dict[key].get_object()
        subtype = str(font.get("/Subtype"))[1:]
        entry = {"subtype": subtype, "inventory": str(font.get("/BaseFont")), "descendant": None, "descriptor": None}
        holder = font
        if subtype == "Type0":
            descendant = font["/DescendantFonts"].get_object()[0].get_object()
            entry["descendant"] = str(descendant.get("/BaseFont"))
            holder = descendant
        descriptor = holder.get("/FontDescriptor")
        if descriptor is not None:
            entry["descriptor"] = str(descriptor.get_object().get("/FontName"))
        fonts.append(entry)
manager = PDFResourceManager()
device = PDFPageAggregator(manager, laparams=None)
interpreter = PDFPageInterpreter(manager, device)
names = []
def walk(obj):
    if isinstance(obj, LTChar):
        names.append(obj.fontname)
    elif hasattr(obj, "__iter__"):
        for item in obj:
            walk(item)
for page in PDFPage.create_pages(PDFDocument(PDFParser(io.BytesIO(data)))):
    interpreter.process_page(page)
    walk(device.get_result())
print(json.dumps({"fonts": fonts, "span_names": sorted(set(names)), "pages": len(reader.pages)}, sort_keys=True))
'''

SANDBOX_CANARY_CODE = ("import sys\n"
                       "try:\n    open(sys.argv[1], 'rb').read(1)\nexcept OSError as exc:\n"
                       "    print('ABSENT:%s' % exc.errno)\nelse:\n    print('READABLE')\n")


# -- sandboxed runs ---------------------------------------------------------------------------------------------------

def make_operator_isolation_prober(manifest: dict, verifier_host_path: str, inspection_paths: tuple = (),
                                   expected_errnos=None, timeout: int = 90, temp_parent=None, run=None):
    """The adapter's isolation_prober(profile, argv, pass_fds) for the real operator host. The probe is the verifier's
    own stdlib-only probe entry, executed inside exactly the profile the adapter built; the single permitted delta is
    the read-only bind of the probe file. The per-run placeholders of the render profile are replaced by real, empty,
    disposable directories (a bubblewrap bind needs a real source); the digest the prober returns is the digest of the
    shared argv with the placeholders, equal for the probe and the real profile."""
    verifier = load_verifier()
    paths = tuple(inspection_paths)
    run = run or subprocess.run

    def prober(profile, argv, pass_fds):
        shared = build_argv_shared(manifest, profile, paths)
        expected = substitute_placeholders(shared, entry_fd=pass_fds[0] if pass_fds else None)
        if list(argv[1:]) != expected:
            return {"ok": False, "reason": "PROFILE_MISMATCH"}
        spec = {"expected_errnos": expected_errnos or manifest["sandbox_expected_unreachable_errnos"],
                "canaries": manifest["sandbox_forbidden_canary_paths"], "home": home_path(manifest),
                "tmpdir": SANDBOX_TMP_PATH,
                "read_only_paths": list(manifest["sandbox_read_only_paths"] if profile == PROFILE_RENDER else paths)}
        with RunTempLayout(temp_parent) as layout:
            substituted = substitute_placeholders(shared, run_dirs=layout.run_dirs(),
                                                  entry_fd=pass_fds[0] if pass_fds else None)
            command = [argv[0]] + verifier.probe_argv_segments(
                substituted, verifier_host_path, manifest["sandbox_probe_interpreter_path"], spec)
            try:
                completed = run(command, capture_output=True, timeout=timeout, pass_fds=tuple(pass_fds),
                                env={}, close_fds=True, shell=False)
            except (OSError, subprocess.TimeoutExpired):
                return {"ok": False, "reason": "PROBE_FAILED"}
        try:
            result = json.loads(completed.stdout.decode("utf-8"))
        except (UnicodeDecodeError, ValueError):
            return {"ok": False, "reason": "PROBE_OUTPUT", "stderr": completed.stderr.decode("utf-8", "replace")[:600]}
        if completed.returncode != 0 or result.get("ok") is not True:
            return {"ok": False, "reason": "SELF_TEST_FAILED", "result": result}
        return {"ok": True, "reason": None, "result": result,
                "profile_digest": sandbox_profile_digest(manifest, profile, paths)}

    return prober


def run_probe_for_errnos(manifest: dict, verifier_host_path: str, bwrap_path: str, timeout: int = 90) -> dict:
    """One in-sandbox probe of the RENDER profile with the contract-defined (widest) errno sets, returning the raw
    probe result; the manifest sets are then narrowed to the observed values (errno_sets_from_probe)."""
    verifier = load_verifier()
    shared = build_argv_shared(manifest, PROFILE_RENDER)
    spec = {"expected_errnos": {key: list(value) for key, value in EXPECTED_UNREACHABLE_ERRNOS_V1.items()},
            "canaries": manifest["sandbox_forbidden_canary_paths"], "home": home_path(manifest),
            "tmpdir": SANDBOX_TMP_PATH, "read_only_paths": list(manifest["sandbox_read_only_paths"])}
    with RunTempLayout(None) as layout:
        substituted = substitute_placeholders(shared, run_dirs=layout.run_dirs())
        command = [bwrap_path] + verifier.probe_argv_segments(
            substituted, verifier_host_path, manifest["sandbox_probe_interpreter_path"], spec)
        try:
            completed = subprocess.run(command, capture_output=True, timeout=timeout, env={}, close_fds=True, shell=False)
        except (OSError, subprocess.TimeoutExpired):
            _op_fail("RENDER_ISOLATION_UNAVAILABLE", "PROBE_FAILED", "ERRNO_CAPTURE")
    try:
        return json.loads(completed.stdout.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        _op_fail("RENDER_ISOLATION_UNAVAILABLE", "PROBE_OUTPUT", "ERRNO_CAPTURE",
                 stderr=completed.stderr.decode("utf-8", "replace")[:600])


def sandbox_convert(manifest: dict, bwrap_path: str, soffice_path: str, docx_bytes: bytes, runner=None) -> bytes:
    """One real LibreOffice conversion inside the RENDER profile (the same argv builders as run_pipeline); returns
    the produced PDF bytes or fails with RENDER_SANDBOX_RUNTIME_INCOMPLETE."""
    runner = runner or ProcessRunner()
    with RunTempLayout(None) as layout:
        with open(os.path.join(layout.input_dir, INPUT_FILE_NAME), "wb") as handle:
            handle.write(docx_bytes)
        argv = ([bwrap_path] + substitute_placeholders(build_argv_shared(manifest, PROFILE_RENDER),
                                                       run_dirs=layout.run_dirs())
                + conversion_argv(soffice_path, manifest))
        result = runner.run(argv, timeout=manifest["timeout_seconds"])
        if result.timed_out or not result.launched or result.returncode != 0:
            _op_fail("RENDER_SANDBOX_RUNTIME_INCOMPLETE", "RENDERER_RUNTIME_INCOMPLETE", "CONVERT",
                     returncode=result.returncode, stderr=result.stderr.decode("utf-8", "replace")[:600])
        try:
            with open(os.path.join(layout.output_dir, OUTPUT_FILE_NAME), "rb") as handle:
                pdf = handle.read()
        except OSError:
            _op_fail("RENDER_SANDBOX_RUNTIME_INCOMPLETE", "OUTPUT_INVALID", "MISSING")
    if not pdf.startswith(b"%PDF-"):
        _op_fail("RENDER_SANDBOX_RUNTIME_INCOMPLETE", "OUTPUT_INVALID", "MAGIC")
    return pdf


def run_font_probe(manifest: dict, bwrap_path: str, soffice_path: str, prefix_python: str, site_packages: str) -> dict:
    """Render the font-probe DOCX through LibreOffice inside the RENDER profile and read the real PDF with the pinned
    pypdf and pdfminer.six under the operator-prefix interpreter (governed form). Returns the observation."""
    docx, _structure = build_fixture_docx("FONT_PROBE")
    pdf = sandbox_convert(manifest, bwrap_path, soffice_path, docx)
    with tempfile.TemporaryDirectory(prefix="career-os-font-probe-") as scratch:
        pdf_path = os.path.join(scratch, "probe.pdf")
        with open(pdf_path, "wb") as handle:
            handle.write(pdf)
        cache = os.path.join(scratch, "pycache")
        os.mkdir(cache, 0o700)
        completed = subprocess.run(
            [prefix_python, "-I", "-S", "-B", "-X", "pycache_prefix=" + cache, "-c", FONT_PROBE_CODE, pdf_path,
             site_packages], capture_output=True, timeout=120, env={}, shell=False)
    if completed.returncode != 0:
        _op_fail("RENDER_FONT_MANIFEST_INCOMPLETE", "ALIAS_FORM_MISSING", "FONT_PROBE_FAILED",
                 stderr=completed.stderr.decode("utf-8", "replace")[-600:])
    observation = json.loads(completed.stdout.decode("utf-8"))
    observation["probe_pdf_sha256"] = sha256_hex(pdf)
    observation["probe_docx_sha256"] = sha256_hex(docx)
    return observation


# -- capture, verification and render orchestration -------------------------------------------------------------------

OPERATOR_MANIFEST_RELPATH = "docs/rendering/RENDERING_ENVIRONMENT_V1.json"
OPERATOR_REQUIREMENTS_IN_RELPATH = "requirements.in"
OPERATOR_REQUIREMENTS_LOCK_RELPATH = "requirements-lock.txt"
OPERATOR_VERIFIER_RELPATH = "scripts/verify_document_rendering_environment.py"
OPERATOR_TEST_RELPATH = "tests/document_rendering_capability_v1_test.py"
OPERATOR_VERIFICATION_SPEC_ID = "OPERATOR_VERIFICATION_V1"


def check_governed_mode() -> None:
    """The operator code refuses to run outside GOVERNED_RUNTIME_MODE_V1 (a consistency check; the mode is enforced
    by the launch form)."""
    if (sys.flags.isolated != 1 or sys.flags.no_site != 1 or sys.flags.dont_write_bytecode != 1
            or not getattr(sys, "pycache_prefix", None)):
        _op_fail("RENDER_ENVIRONMENT_UNVERIFIED", "INTERPRETER_MODE")


def operator_site_packages(manifest: dict) -> str:
    return get_site_packages(manifest["operator_python_prefix"], manifest["operator_base_interpreter"]["python_version"])


def get_site_packages(prefix: str, python_version: str) -> str:
    return prefix.rstrip("/") + "/lib/python%s/site-packages" % ".".join(python_version.split(".")[:2])


def add_governed_site_path(site_packages: str) -> None:
    """GOVERNED_RUNTIME_MODE_V1: exactly one path, the approved site-packages directory, appended after the entries
    the interpreter validated."""
    if site_packages not in sys.path:
        sys.path.append(site_packages)


def entry_runtime_path_matches(manifest: dict, entry_bytes: bytes) -> bool:
    """The inspection entry's RUNTIME_SITE_PACKAGES constant (read by AST, the entry is never imported) equals the last
    element of content_binding.runtime_sys_path."""
    import ast

    for node in ast.parse(entry_bytes).body:
        if (isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name)
                and node.targets[0].id == RUNTIME_SITE_PACKAGES_CONSTANT and isinstance(node.value, ast.Constant)):
            return node.value.value == manifest["content_binding"]["runtime_sys_path"][-1]
    return False


def read_plan_files(root: Path) -> tuple:
    return ((root / OPERATOR_REQUIREMENTS_IN_RELPATH).read_bytes(), (root / OPERATOR_REQUIREMENTS_LOCK_RELPATH).read_bytes())


def capture_post_binding(root: Path, approved_plan_digest: str, evidence_text: str, host=None,
                         verifier_host_path: str = None) -> dict:
    """POST_PROVISION_BINDING_CAPTURE_V1: derive and measure every POST_PROVISION_BINDING key on the provisioned host
    and return the populated runtime manifest with its digests. Nothing is defaulted; the PRE_PROVISION_PLAN of the
    input manifest is unchanged by construction (PLAN_AMENDMENT_LOOP_V1 otherwise)."""
    host = host or OperatorHost()
    check_governed_mode()
    pre_bytes = (root / OPERATOR_MANIFEST_RELPATH).read_bytes()
    pre = strict_json_loads(pre_bytes.decode("utf-8"))
    for key in MANIFEST_POST_PROVISION_KEYS:
        if pre.get(key) is not None:
            _op_fail("RENDER_ENVIRONMENT_UNVERIFIED", "POST_KEYS_NOT_NULL", key)
    plan_inputs = read_plan_files(root)
    if plan_digest(pre, *plan_inputs) != approved_plan_digest:
        _op_fail("RENDER_ENVIRONMENT_UNVERIFIED", "PLAN_DIGEST")
    verifier = load_verifier()
    interpreter = pre["operator_base_interpreter"]
    prefix = pre["operator_python_prefix"]
    site = operator_site_packages(pre)
    add_governed_site_path(site)
    by_key = parse_evidence_lines(evidence_text)
    if ("plan_digest=" + approved_plan_digest) not in by_key.get("result", [""])[-1]:
        _op_fail("RENDER_ENVIRONMENT_UNVERIFIED", "APT_EVIDENCE", "RESULT_PLAN_DIGEST")
    evidence_sha = sha256_hex(evidence_text.encode("utf-8"))
    snapshot, delta, source_record = apt_records_from_evidence(by_key, evidence_sha)
    live_reason = verifier.make_live_verifier()(pre)
    if live_reason is not None:
        _op_fail("RENDER_ENVIRONMENT_UNVERIFIED", str(live_reason), "LIVE_VERIFICATION")
    distributions = sorted(verifier.installed_distributions(site))
    base_closure, prefix_closure = compute_native_closures(host, pre, site)
    font_package = [item["name"] for item in pre["apt_plan"]["packages"] if item.get("role") == "FONT"]
    if len(font_package) != 1:
        _op_fail("RENDER_FONT_MANIFEST_INCOMPLETE", "NAME_TABLE_UNMAPPED", "FONT_PACKAGE")
    returncode, stdout, _stderr = host.run(["/usr/bin/dpkg-query", "-L", font_package[0]], env=OPERATOR_PROBE_ENV)
    if returncode != 0:
        _op_fail("RENDER_FONT_MANIFEST_INCOMPLETE", "NAME_TABLE_UNMAPPED", "DPKG_LISTING")
    font_paths = [line for line in stdout.decode("utf-8").split("\n")
                  if line.startswith("/usr/share/fonts/") and line.endswith(".ttf")]
    fonts = provisioned_font_records(font_paths, host.read_bytes)
    sandbox = derive_sandbox(host, pre, fonts, [base_closure, prefix_closure])
    verifier_path = verifier_host_path or str(root / OPERATOR_VERIFIER_RELPATH)
    provisional = dict(pre)
    provisional.update(sandbox)
    provisional["sandbox_expected_unreachable_errnos"] = {key: list(value) for key, value in
                                                          EXPECTED_UNREACHABLE_ERRNOS_V1.items()}
    probe_result = run_probe_for_errnos(provisional, verifier_path, BWRAP_EXECUTABLE)
    errnos = errno_sets_from_probe(probe_result)
    provisional["sandbox_expected_unreachable_errnos"] = errnos
    observation = run_font_probe(provisional, BWRAP_EXECUTABLE, SOFFICE_EXECUTABLE, prefix.rstrip("/") + "/bin/python", site)
    tables = build_font_tables(fonts, observation)
    base_real = host.realpath(interpreter["path"])
    absent = absent_candidate_paths(pre, _FsView(host), site, [
        (interpreter["path"], base_real, None),
        (prefix.rstrip("/") + "/bin/python", base_real, prefix.rstrip("/") + "/pyvenv.cfg"),
    ])
    roots = build_content_roots(host, pre, sandbox, fonts, base_closure, prefix_closure, distributions, absent, site)
    roots, exclusions = compute_root_digests(roots, sandbox["sandbox_read_only_paths"])
    recorded = {path: digest for closure in (base_closure, prefix_closure) for path, digest in closure["files"] + closure["loader_inputs"]}
    for root in roots:
        if root["kind"] == "FILE" and root["path"] in recorded and root["expected_digest"] != recorded[root["path"]]:
            _op_fail("RENDER_CONTENT_BINDING_MISMATCH", "CLOSURE_ROOT", None, root_id=root["id"])
    cache_root = next((root for root in roots if root["kind"] == "FILE" and root["path"] == "/etc/ld.so.cache"), None)
    if cache_root is None:
        _op_fail("RENDER_CONTENT_BINDING_INCOMPLETE", "LOADER_INPUT", "/etc/ld.so.cache")
    values = {
        "approved_plan_digest": approved_plan_digest,
        "apt_installed_delta": delta,
        "apt_preinstall_snapshot": snapshot,
        "apt_source_record": source_record,
        "content_binding": {"exclusions": exclusions, "native_closure_prefix": prefix_closure, "roots": roots,
                            "runtime_sys_path": runtime_sys_path_of(pre, site)},
    }
    values.update(tables)
    values.update({key: sandbox[key] for key in ("sandbox_dirs", "sandbox_path", "sandbox_probe_interpreter_path",
                                                 "sandbox_read_only_paths", "sandbox_symlinks", "fontconfig_file")})
    values["sandbox_expected_unreachable_errnos"] = errnos
    manifest = assemble_post_manifest(pre, values)
    text = manifest_text(manifest)
    entry_bytes = INSPECTION_ENTRY_PATH.read_bytes()
    environment = verify_environment(text.encode("utf-8"), verifier.make_live_verifier(), plan_inputs, None, entry_bytes)
    if not entry_runtime_path_matches(manifest, entry_bytes):
        _op_fail("RENDER_ENVIRONMENT_UNVERIFIED", "ENTRY_RUNTIME_PATH")
    return {
        "manifest": manifest, "manifest_text": text,
        "digests": {"manifest_file_sha256": sha256_hex(text.encode("utf-8")), "manifest_digest": environment.manifest_digest,
                    "content_binding_digest": environment.content_binding_digest,
                    "runtime_manifest_digest": environment.runtime_manifest_digest,
                    "pre_provision_plan_digest": pre_provision_plan_digest(manifest),
                    "plan_digest": plan_digest(manifest, *plan_inputs)},
        "evidence": {
            "spec": OPERATOR_CAPTURE_SPEC_ID, "provisioning_evidence_sha256": evidence_sha,
            "populated_post_keys": sorted(values), "root_count": len(roots), "exclusions": exclusions,
            "root_ids": [root["id"] for root in roots], "fonts": [dict(record) for record in fonts],
            "font_probe": observation, "probe_result": probe_result, "errnos": errnos,
            "sandbox_read_only_paths": sandbox["sandbox_read_only_paths"],
            "inspection_read_only_paths": list(derive_inspection_paths(manifest)),
            "native_closure_prefix_digest": verifier.native_closure_digest(prefix_closure),
            "native_closure_base_digest": verifier.native_closure_digest(base_closure),
            "ld_so_cache_sha256_bound": cache_root["expected_digest"],
            "pre_provision_fields_unchanged": True,
        },
    }


def real_render_dependencies(root: Path, manifest_bytes: bytes, temp_parent=None) -> RenderDependencies:
    """RenderDependencies of the real operator host for a populated manifest: the verifier's live verifier, the
    manifest-derived runtime paths and the real isolation prober. A manifest with a null POST key never gets here
    (verify_manifest fails at S2.01 first)."""
    verifier = load_verifier()
    manifest = verify_manifest(manifest_bytes)
    paths = runtime_paths_from_manifest(manifest)
    return RenderDependencies(
        manifest_bytes=manifest_bytes, live_verifier=verifier.make_live_verifier(), plan_inputs=read_plan_files(root),
        runtime_paths=paths,
        isolation_prober=make_operator_isolation_prober(manifest, str(root / OPERATOR_VERIFIER_RELPATH),
                                                        paths.inspection_read_only_paths, temp_parent=temp_parent),
        temp_parent=temp_parent)


def evidence_digest(record: dict) -> str:
    return canonical_digest(record)


def check_soffice_version(observed: str, pinned: str) -> None:
    """The in-sandbox `soffice --version` line must equal the pinned libreoffice_version exactly."""
    if observed != pinned:
        _op_fail("RENDER_SANDBOX_RUNTIME_INCOMPLETE", "RENDERER_VERSION", None, observed=str(observed)[:120], pinned=pinned)


def check_canary_unreadable(returncode: int, output: str) -> None:
    """The planted canary file (outside every enumerated mount) must be absent inside the sandbox."""
    if returncode != 0 or not output.startswith("ABSENT:"):
        _op_fail("RENDER_ISOLATION_UNAVAILABLE", "CANARY_READABLE", None, output=output[:80])


REQUIRED_VERIFICATION_STEPS = (
    "governed_runtime_mode", "environment_and_content_binding", "apt_pins_installed_set_fileset",
    "inspection_entry_runtime_path", "isolation_minimality_and_network", "planted_canary_unreadable",
    "soffice_version_in_sandbox", "executability_fixture_and_determinism", "font_manifest_completeness",
    "operator_fixture_suite_on_prefix_interpreter",
)


def operator_evidence_is_pass(record) -> bool:
    """True only for a COMPLETE passing OPERATOR_VERIFICATION_V1 record: the spec id, every required step present,
    in order, each PASS with evidence, no failed step, and an evidence_digest that matches. A partial, failed,
    reordered or tampered record is never a pass."""
    if not isinstance(record, dict) or record.get("spec") != OPERATOR_VERIFICATION_SPEC_ID or record.get("result") != "PASS":
        return False
    if record.get("failed_step") is not None:
        return False
    steps = record.get("steps")
    if not isinstance(steps, list) or [item.get("step") for item in steps] != list(REQUIRED_VERIFICATION_STEPS):
        return False
    if any(item.get("result") != "PASS" or "evidence" not in item for item in steps):
        return False
    body = {key: value for key, value in record.items() if key != "evidence_digest"}
    return record.get("evidence_digest") == evidence_digest(body)


def _verify_step(record: dict, name: str, function) -> object:
    """One operator verification step: PASS with its evidence, or FAIL with the named triple, and the run stops."""
    try:
        evidence = function()
    except (OperatorFailure, StageFailure) as failure:
        triple = failure.triple() if isinstance(failure, OperatorFailure) else (
            failure.outcome.status, failure.outcome.reason, failure.outcome.detail)
        record["steps"].append({"step": name, "result": "FAIL", "failure": list(triple),
                                "failure_evidence": _evidence_safe(getattr(failure, "evidence", {}))})
        record["result"] = "FAIL"
        record["failed_step"] = name
        raise
    record["steps"].append({"step": name, "result": "PASS", "evidence": _evidence_safe(evidence)})
    return evidence


def run_executability_fixture(root: Path, manifest_bytes: bytes, delivery_dir=None, kind: str = "EXECUTABILITY") -> dict:
    """The real executability proof body: the benign synthetic fixture rendered through the full pipeline (S1-S12) of
    the adapter; the evidence record must come from a completed inspection (a PDF, a fingerprint, the two profile
    digests and a removed temp root)."""
    docx, structure_map = build_fixture_docx(kind)
    deps = real_render_dependencies(root, manifest_bytes)
    record = render_document(docx, structure_map, deps, delivery_dir)
    needed = ("pdf_sha256", "render_semantic_fingerprint", "sandbox_profile_digest", "inspection_profile_digest",
              "manifest_digest", "content_binding_digest", "runtime_manifest_digest", "inspection_entry_sha256")
    if record["run_status"] not in (STATUS_PASS, STATUS_QA_FAILED) or any(record[key] is None for key in needed) \
            or record["temp_root_removed"] != 1:
        _op_fail("RENDER_SANDBOX_RUNTIME_INCOMPLETE", "EXECUTABILITY_FIXTURE", record["run_status"],
                 run_reason=record["reason"], run_detail=record["detail"], run_slot=record["slot"],
                 failure_evidence=record["failure_evidence"])
    record["fixture_docx_sha256"] = sha256_hex(docx)
    record["fixture_kind"] = kind
    return record


def sandbox_run(manifest: dict, bwrap_path: str, command: list, timeout: int = 90) -> ProcessResult:
    """One command inside the RENDER profile with real, empty per-run directories."""
    with RunTempLayout(None) as layout:
        argv = [bwrap_path] + substitute_placeholders(build_argv_shared(manifest, PROFILE_RENDER),
                                                      run_dirs=layout.run_dirs()) + list(command)
        return ProcessRunner().run(argv, timeout=timeout)


def run_operator_verification(root: Path, manifest_bytes: bytes, host=None, attachments=(), run_suite: bool = True,
                              suite_timeout: int = 900) -> dict:
    """The complete operator verifier over a populated runtime manifest: every step is a real execution on the
    provisioned host. Returns the evidence record; result is PASS only when every step passed (a failing step
    raises after being recorded, so no partial record can be read as a pass)."""
    host = host or OperatorHost()
    record = {"spec": OPERATOR_VERIFICATION_SPEC_ID, "result": "PASS", "steps": []}
    verifier = load_verifier()
    plan_inputs = read_plan_files(root)
    entry_bytes = INSPECTION_ENTRY_PATH.read_bytes()
    state = {}

    def governed():
        check_governed_mode()
        return {"isolated": sys.flags.isolated, "no_site": sys.flags.no_site, "dont_write_bytecode": sys.flags.dont_write_bytecode,
                "pycache_prefix_set": 1, "executable": sys.executable}

    def environment():
        manifest = verify_manifest(manifest_bytes)
        add_governed_site_path(operator_site_packages(manifest))
        env = verify_environment(manifest_bytes, verifier.make_live_verifier(), plan_inputs, None, entry_bytes)
        state["manifest"] = manifest
        state["environment"] = env
        return {"approved_plan_digest": manifest["approved_plan_digest"], "manifest_digest": env.manifest_digest,
                "content_binding_digest": env.content_binding_digest,
                "runtime_manifest_digest": env.runtime_manifest_digest, "root_count": len(env.root_digests),
                "pre_provision_plan_digest": pre_provision_plan_digest(manifest),
                "plan_digest": plan_digest(manifest, *plan_inputs)}

    def apt_and_set():
        manifest = state["manifest"]
        pins = []
        for item in manifest["apt_plan"]["packages"]:
            installed = verifier.dpkg_installed_version(item["name"], item["architecture"])
            if installed != item["version"]:
                _op_fail("RENDER_ENVIRONMENT_UNVERIFIED", "APT_PIN", None, package=item["name"], installed=installed)
            pins.append([item["name"], item["architecture"], item["version"]])
        site = operator_site_packages(manifest)
        distributions = verifier.installed_distributions(site)
        verifier.reconcile_fileset(verifier.site_files(site), {name: item[1] for name, item in distributions.items()},
                                   site, manifest["operator_python_prefix"])
        return {"apt_pins": pins, "apt_installed_delta": manifest["apt_installed_delta"],
                "installed_distributions": sorted("%s==%s" % (name, item[0]) for name, item in distributions.items()),
                "fileset_reconciliation": "PASS", "apt_source_record_sha256": canonical_digest(manifest["apt_source_record"])}

    def entry_path():
        if not entry_runtime_path_matches(state["manifest"], entry_bytes):
            _op_fail("RENDER_ENVIRONMENT_UNVERIFIED", "ENTRY_RUNTIME_PATH")
        return {"inspection_entry_sha256": sha256_hex(entry_bytes),
                "runtime_sys_path": state["manifest"]["content_binding"]["runtime_sys_path"]}

    def isolation():
        manifest = state["manifest"]
        paths = runtime_paths_from_manifest(manifest)
        check_runtime_paths(manifest, paths)
        prober = make_operator_isolation_prober(manifest, str(root / OPERATOR_VERIFIER_RELPATH),
                                                paths.inspection_read_only_paths)
        render_shared = [paths.bwrap_path] + build_argv_shared(manifest, PROFILE_RENDER)
        render_report = prober(PROFILE_RENDER, render_shared, ())
        if render_report.get("ok") is not True:
            _op_fail("RENDER_ISOLATION_UNAVAILABLE", render_report.get("reason") or "SELF_TEST_FAILED", "RENDER",
                     report=render_report)
        entry = bind_entry_descriptor(entry_bytes, sha256_hex(entry_bytes))
        try:
            inspection_shared = [paths.bwrap_path] + substitute_placeholders(
                build_argv_shared(manifest, PROFILE_INSPECTION, paths.inspection_read_only_paths), entry_fd=entry.fd)
            inspection_report = prober(PROFILE_INSPECTION, inspection_shared, (entry.fd,))
        finally:
            entry.close()
        if inspection_report.get("ok") is not True:
            _op_fail("RENDER_ISOLATION_UNAVAILABLE", inspection_report.get("reason") or "SELF_TEST_FAILED", "INSPECTION",
                     report=inspection_report)
        state["paths"] = paths
        return {"render_profile_digest": render_report["profile_digest"],
                "inspection_profile_digest": inspection_report["profile_digest"],
                "render_probe": render_report["result"], "inspection_probe": inspection_report["result"]}

    def canary():
        manifest = state["manifest"]
        with tempfile.NamedTemporaryFile(prefix="career-os-canary-", dir="/var/tmp", delete=False) as handle:
            handle.write(os.urandom(32))
            planted = handle.name
        try:
            result = sandbox_run(manifest, state["paths"].bwrap_path,
                                 [manifest["sandbox_probe_interpreter_path"], "-I", "-S", "-B", "-c", SANDBOX_CANARY_CODE, planted])
        finally:
            os.unlink(planted)
        output = result.stdout.decode("utf-8", "replace").strip()
        check_canary_unreadable(result.returncode, output)
        return {"planted_canary_readable": 0, "observed": output}

    def soffice_version():
        manifest = state["manifest"]
        result = sandbox_run(manifest, state["paths"].bwrap_path, [state["paths"].soffice_path, "--version"])
        observed = result.stdout.decode("utf-8", "replace").strip()
        if result.returncode != 0:
            _op_fail("RENDER_SANDBOX_RUNTIME_INCOMPLETE", "RENDERER_VERSION", "EXIT", returncode=result.returncode)
        check_soffice_version(observed, manifest["libreoffice_version"])
        return {"in_sandbox_version": observed}

    def executability():
        under = run_executability_fixture(root, manifest_bytes, kind="EXECUTABILITY")
        if under["run_status"] != STATUS_QA_FAILED or not any(
                finding.get("code") == "RESUME_PAGE_UNDERUTILIZED" for finding in under["findings"]):
            _op_fail("RENDER_SANDBOX_RUNTIME_INCOMPLETE", "EXECUTABILITY_FIXTURE", "UNDERFILLED_NOT_FAILED",
                     run_status=under["run_status"])
        renders = [run_executability_fixture(root, manifest_bytes, kind="EXECUTABILITY_FULL") for _ in range(3)]
        for record_item in renders:
            if record_item["run_status"] != STATUS_PASS:
                _op_fail("RENDER_SANDBOX_RUNTIME_INCOMPLETE", "EXECUTABILITY_FIXTURE", "FULL_PAGE_NOT_PASS",
                         run_status=record_item["run_status"], utilization=record_item["utilization"])
        first = renders[0]
        for other in renders[1:]:
            for key in ("render_semantic_fingerprint", "attribution_digest", "sandbox_profile_digest",
                        "inspection_profile_digest", "runtime_manifest_digest", "docx_sha256"):
                if first[key] != other[key]:
                    _op_fail("RENDER_NONDETERMINISTIC", key, None)
        state["fixture"] = first
        return {"underfilled": {"run_status": under["run_status"], "findings": under["findings"],
                                "fixture_docx_sha256": under["fixture_docx_sha256"], "pdf_sha256": under["pdf_sha256"]},
                "full_page": {"run_status": first["run_status"], "fixture_docx_sha256": first["fixture_docx_sha256"],
                              "pdf_sha256": first["pdf_sha256"], "utilization": first["utilization"],
                              "render_semantic_fingerprint": first["render_semantic_fingerprint"],
                              "attribution_digest": first["attribution_digest"],
                              "sandbox_profile_digest": first["sandbox_profile_digest"],
                              "inspection_profile_digest": first["inspection_profile_digest"],
                              "manifest_digest": first["manifest_digest"],
                              "content_binding_digest": first["content_binding_digest"],
                              "runtime_manifest_digest": first["runtime_manifest_digest"],
                              "inspection_entry_sha256": first["inspection_entry_sha256"],
                              "temp_root_removed": first["temp_root_removed"]},
                "fresh_renders": 3, "fingerprints_identical": 1,
                "raw_pdf_bytes_identical_informational": 1 if len({item["pdf_sha256"] for item in renders}) == 1 else 0}

    def fonts_complete():
        manifest = state["manifest"]
        font_paths = [path for path in manifest["sandbox_read_only_paths"] if path.endswith(".ttf")]
        fonts = provisioned_font_records(font_paths, host.read_bytes)
        observation = run_font_probe(manifest, state["paths"].bwrap_path, state["paths"].soffice_path,
                                     manifest["operator_python_prefix"].rstrip("/") + "/bin/python",
                                     operator_site_packages(manifest))
        tables = build_font_tables(fonts, observation)
        for key, value in tables.items():
            if manifest[key] != value:
                _op_fail("RENDER_FONT_MANIFEST_INCOMPLETE", "ALIAS_FORM_MISSING", key)
        return {"font_files": [record["path"] for record in fonts], "probe_pdf_sha256": observation["probe_pdf_sha256"],
                "pypdf_and_pdfminer_forms_in_table": 1}

    def suite():
        manifest = state["manifest"]
        prefix_python = manifest["operator_python_prefix"].rstrip("/") + "/bin/python"
        with tempfile.TemporaryDirectory(prefix="career-os-suite-") as scratch:
            completed = subprocess.run([prefix_python, "-I", "-B", str(root / OPERATOR_TEST_RELPATH)], capture_output=True,
                                       timeout=suite_timeout, env={"HOME": scratch, "TMPDIR": scratch, "LC_ALL": "C.UTF-8"},
                                       cwd=str(root), shell=False)
        output = completed.stdout.decode("utf-8", "replace")
        if completed.returncode != 0 or "PASS: document_rendering_capability_v1_test" not in output \
                or "BLOCKED_DEPENDENCY_NOT_INSTALLED" in output:
            _op_fail("RENDER_ENVIRONMENT_UNVERIFIED", "OPERATOR_FIXTURE_SUITE", completed.returncode,
                     tail=output[-600:], stderr=completed.stderr.decode("utf-8", "replace")[-600:])
        passes = [line for line in output.split("\n") if line.startswith("PASS:")]
        return {"exit_status": completed.returncode, "pass_lines": passes, "stdout_sha256": sha256_hex(output.encode("utf-8")),
                "interpreter": prefix_python}

    steps = [("governed_runtime_mode", governed), ("environment_and_content_binding", environment),
             ("apt_pins_installed_set_fileset", apt_and_set), ("inspection_entry_runtime_path", entry_path),
             ("isolation_minimality_and_network", isolation), ("planted_canary_unreadable", canary),
             ("soffice_version_in_sandbox", soffice_version), ("executability_fixture_and_determinism", executability),
             ("font_manifest_completeness", fonts_complete)]
    if run_suite:
        steps.append(("operator_fixture_suite_on_prefix_interpreter", suite))
    for name, function in steps:
        try:
            _verify_step(record, name, function)
        except (OperatorFailure, StageFailure):
            break
    record["attachments"] = [{"name": name, "sha256": sha256_hex(Path(path).read_bytes())} for name, path in attachments]
    record["evidence_digest"] = evidence_digest({key: value for key, value in record.items() if key != "evidence_digest"})
    return record


def verification_matches_manifest(record: dict, environment_digests: dict) -> bool:
    """The passing verification record was produced for exactly this runtime manifest (manifest, content-binding
    and runtime-manifest digests)."""
    step = next((item for item in record["steps"] if item["step"] == "environment_and_content_binding"), None)
    evidence = step["evidence"] if step else {}
    return all(evidence.get(key) == environment_digests.get(key)
               for key in ("manifest_digest", "content_binding_digest", "runtime_manifest_digest"))


def run_first_render(root: Path, manifest_bytes: bytes, docx_path: str, expected_docx_sha256: str, out_dir: str,
                     structure_map_path: str, verification_record=None, governed=None) -> dict:
    """The first governed render: the supplied DOCX bytes and structure map through the existing run_pipeline with the
    real operator dependencies; the delivered PDF and the evidence record are written under OUT_DIR and never
    altered. Refuses to run against an incomplete runtime manifest (S2.01) or a different DOCX."""
    (governed or check_governed_mode)()
    if not operator_evidence_is_pass(verification_record):
        _op_fail("RENDER_ENVIRONMENT_UNVERIFIED", "OPERATOR_VERIFICATION_NOT_PASS")
    data = Path(docx_path).read_bytes()
    if sha256_hex(data) != expected_docx_sha256:
        _op_fail("RENDER_ENVIRONMENT_UNVERIFIED", "INPUT_SHA256", None, observed=sha256_hex(data))
    structure_map = strict_json_loads(Path(structure_map_path).read_text(encoding="utf-8")) if structure_map_path else None
    manifest = verify_manifest(manifest_bytes)
    add_governed_site_path(operator_site_packages(manifest))
    environment = verify_environment(manifest_bytes, load_verifier().make_live_verifier(), read_plan_files(root), None,
                                     INSPECTION_ENTRY_PATH.read_bytes())
    if not verification_matches_manifest(verification_record, {
            "manifest_digest": environment.manifest_digest, "content_binding_digest": environment.content_binding_digest,
            "runtime_manifest_digest": environment.runtime_manifest_digest}):
        _op_fail("RENDER_ENVIRONMENT_UNVERIFIED", "VERIFICATION_RECORD_MISMATCH")
    os.makedirs(out_dir, mode=0o700, exist_ok=False)
    deps = real_render_dependencies(root, manifest_bytes)
    record = render_document(data, structure_map, deps, out_dir)
    evidence_path = os.path.join(out_dir, "rendered_document_evidence.json")
    with open(evidence_path, "wb") as handle:
        handle.write(canonical_json_bytes(record))
    return {"record": record, "input_sha256": sha256_hex(data), "evidence_path": evidence_path,
            "evidence_sha256": sha256_hex(Path(evidence_path).read_bytes()),
            "pdf_path": os.path.join(out_dir, DELIVERED_PDF_NAME) if record["delivered"] else None,
            "pdf_sha256": record["pdf_sha256"]}


def operator_main(argv: list) -> int:
    """Command line of the operator code: --capture-post-binding, --operator-verify, --render."""
    import argparse

    sys.modules.setdefault("document_render_adapter", sys.modules[__name__])
    commands = ("--capture-post-binding", "--operator-verify", "--render")
    if not argv or argv[0] not in commands:
        sys.stderr.write("usage: document_render_adapter.py (%s) ...\n" % " | ".join(commands))
        return 2
    command, rest = argv[0], argv[1:]
    parser = argparse.ArgumentParser(prog="document_render_adapter.py " + command)
    parser.add_argument("--root", default=str(_SRC_DIR.parent))
    if command == "--capture-post-binding":
        parser.add_argument("--approved-plan-digest", required=True)
        parser.add_argument("--provisioning-evidence", required=True)
        parser.add_argument("--out-manifest", required=True)
        parser.add_argument("--out-evidence", required=True)
    elif command == "--operator-verify":
        parser.add_argument("--manifest", required=True)
        parser.add_argument("--out-evidence", required=True)
        parser.add_argument("--attach", action="append", default=[], metavar="NAME=PATH")
        parser.add_argument("--no-suite", action="store_true")
    else:
        parser.add_argument("--manifest", required=True)
        parser.add_argument("--verification-evidence", required=True)
        parser.add_argument("--docx", required=True)
        parser.add_argument("--expect-docx-sha256", required=True)
        parser.add_argument("--structure-map", default=None)
        parser.add_argument("--out-dir", required=True)
    args = parser.parse_args(rest)
    root = Path(args.root)
    try:
        if command == "--capture-post-binding":
            result = capture_post_binding(root, args.approved_plan_digest,
                                          Path(args.provisioning_evidence).read_text(encoding="utf-8"))
            Path(args.out_manifest).write_text(result["manifest_text"], encoding="utf-8", newline="\n")
            Path(args.out_evidence).write_bytes(canonical_json_bytes(
                {"digests": result["digests"], "evidence": result["evidence"]}))
            sys.stdout.write(json.dumps({"result": "PASS", "digests": result["digests"]}, sort_keys=True, indent=1) + "\n")
            return 0
        if command == "--operator-verify":
            attachments = [tuple(item.split("=", 1)) for item in args.attach]
            record = run_operator_verification(root, Path(args.manifest).read_bytes(), attachments=attachments,
                                               run_suite=not args.no_suite)
            Path(args.out_evidence).write_bytes(canonical_json_bytes(record))
            sys.stdout.write(json.dumps({"result": record["result"], "evidence_digest": record["evidence_digest"],
                                         "failed_step": record.get("failed_step")}, indent=1) + "\n")
            return 0 if record["result"] == "PASS" else 1
        outcome = run_first_render(root, Path(args.manifest).read_bytes(), args.docx, args.expect_docx_sha256, args.out_dir,
                                   args.structure_map,
                                   verification_record=json.loads(Path(args.verification_evidence).read_text(encoding="utf-8")))
        summary = {key: outcome[key] for key in ("input_sha256", "evidence_path", "evidence_sha256", "pdf_path", "pdf_sha256")}
        summary["run_status"] = outcome["record"]["run_status"]
        summary["reason"] = outcome["record"]["reason"]
        sys.stdout.write(json.dumps(summary, sort_keys=True, indent=1) + "\n")
        return 0 if outcome["record"]["run_status"] in (STATUS_PASS, STATUS_QA_FAILED) else 1
    except (OperatorFailure, StageFailure) as failure:
        triple = failure.triple() if isinstance(failure, OperatorFailure) else (
            failure.outcome.status, failure.outcome.reason, failure.outcome.detail)
        sys.stdout.write(json.dumps({"result": "FAIL", "failure": list(triple),
                                     "evidence": _evidence_safe(getattr(failure, "evidence", {}))}, sort_keys=True, indent=1) + "\n")
        return 1


if __name__ == "__main__":
    sys.exit(operator_main(sys.argv[1:]))
