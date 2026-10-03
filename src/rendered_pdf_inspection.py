"""Inspection child entry of CAREER_OS_DOCUMENT_RENDERING_CAPABILITY_V1.

This module is delivered to the inspection sandbox as the single entry file
(ENTRY_DESCRIPTOR_BINDING_V1) and therefore imports only the standard library
and the public modules of the pinned pypdf and pdfminer.six.

Implemented here: PRE_SCAN_V1 (stage S6.01b) with PRE_SCAN_WALK_V1,
PRE_SCAN_TRAVERSAL_V1, FORM_DEPTH_RULE, EFFECTIVE_FORM_RESOURCES_V1,
PAGE_EFFECTIVE_RESOURCES_V1, FORM_STREAM_SET_V1, PRE_SCAN_READ_V1,
FORM_CALL_GRAPH_V1, PRE_SCAN_ORDER_V1, RAW_STREAM_BYTES_V1 and
PARSER_AMBIGUITY_GATE_V1 (STRICT_REREAD with
STRICT_REREAD_UNRESOLVED_REFERENCE_EXEMPTION_V1, NULL_RESOURCES, NAME_DOMAIN
and STREAM_MISMATCH), plus the FAIL_FRAME_EVIDENCE_V1 string and
exception-class encoders. The FORM_CALL_GRAPH_V1 prediction is the input of
PDFMINER_FORM_EXECUTION_EQUIVALENCE_V1; it is computed from the pinned pypdf
reading only and is never derived from, or widened to, an observed
pdfminer.six execution. The strict shadow reader and the pdfminer.six object
reads of S6.01b supply no fact, count, edge, scope or prediction.

Also implemented here: the child stages of CHILD_PROTOCOL_V1 (S5.02 with
START_ATTESTATION_V1, S5.03 DOCUMENT_STATE_V1, S6 page structure, S7
PAGE_CONTENT_TRAVERSAL_V1 / HIDDEN_TEXT_RENDERED_V1 with LINE_GROUP_V1,
SPACE_INSERT_V1 and SPAN_V1, S9.00a-S9.02 FONT_STRUCTURE_V1 and embedding,
S10.00-S10.05 link annotations), the frame emitter and the entry main.
"""

from __future__ import annotations

import hashlib
import io
import os
import sys
import zlib

FD_STATE_MAX_ENTRIES = 4
INSPECTION_PYCACHE_NAME = "pycache"


def _fd_type(target: str) -> str:
    for kind in ("pipe", "socket", "anon_inode"):
        if target.startswith(kind + ":"):
            return kind
    return "file"


def observe_start(entry_path: str) -> dict:
    """START_ATTESTATION_V1 raw observations, made before any pinned-library
    import: the entry bytes, the open descriptors (the listing's own
    descriptor is closed again when listdir returns, so its readlink fails
    and it is excluded), the TMPDIR entry count and the pycache state."""
    try:
        with open(entry_path, "rb") as handle:
            entry_bytes = handle.read()
    except OSError:
        entry_bytes = b""
    descriptors = []
    try:
        names = os.listdir("/proc/self/fd")
    except OSError:
        names = []
    for name in names:
        if not name.isdigit():
            continue
        try:
            target = os.readlink("/proc/self/fd/" + name)
        except OSError:
            continue
        descriptors.append((int(name), _fd_type(target)))
    descriptors.sort()
    tmpdir = os.environ.get("TMPDIR", "/tmp")
    pycache = os.path.join(tmpdir, INSPECTION_PYCACHE_NAME)
    try:
        tmpdir_entries = len(os.listdir(tmpdir))
    except OSError:
        # An unlistable TMPDIR is never reported as empty.
        tmpdir_entries = 1
    return {
        "entry_bytes": entry_bytes,
        "descriptors": descriptors,
        "tmpdir_entries": tmpdir_entries,
        "pycache_state": "PRESENT" if os.path.lexists(pycache) else "ABSENT",
        "pycache_prefix_matches": 1 if getattr(sys, "pycache_prefix", None) == pycache else 0,
    }


START_OBSERVATION = observe_start(__file__) if __name__ == "__main__" else None

# GOVERNED_RUNTIME_MODE_V1: under `-I -S` the entry adds exactly one path, the approved site-packages directory of the
# operator prefix, appended after the entries the interpreter itself validated. The operator verification compares this
# constant with the last element of content_binding.runtime_sys_path. Imported (not run) by the hermetic tests, the
# module never changes sys.path.
RUNTIME_SITE_PACKAGES = "/opt/career-os-render/python/lib/python3.14/site-packages"
if __name__ == "__main__" and os.path.isdir(RUNTIME_SITE_PACKAGES) and RUNTIME_SITE_PACKAGES not in sys.path:
    sys.path.append(RUNTIME_SITE_PACKAGES)

import json
import math
import re
import unicodedata
import urllib.parse
from decimal import ROUND_HALF_EVEN, Decimal, localcontext

from pdfminer.converter import PDFPageAggregator
from pdfminer.layout import LTChar, LTCurve, LTFigure, LTImage
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfinterp import PDFPageInterpreter, PDFResourceManager
from pdfminer.pdfpage import PDFPage
from pdfminer.pdftypes import resolve1
from pdfminer.psparser import PSLiteral
from pdfminer.pdfexceptions import PDFObjectNotFound
from pdfminer.pdfparser import PDFParser
from pdfminer.pdftypes import LITERALS_FLATE_DECODE, PDFStream
from pypdf import PdfReader
from pypdf.errors import PdfReadError
from pypdf.generic import (
    ArrayObject,
    BooleanObject,
    ByteStringObject,
    ContentStream,
    DecodedStreamObject,
    DictionaryObject,
    IndirectObject,
    NameObject,
    NullObject,
    StreamObject,
    TextStringObject,
)

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

# LINE_GROUP_V1 and SPACE_INSERT_V1 parameters. The child receives only the
# PDF bytes, so these must equal the manifest extraction_spec values
# line_group_baseline_tolerance_q and word_gap_threshold_q (the adapter
# checks the equality at S2.01; an unset value never verifies). They are the
# values of the PRE_PROVISION_PLAN approved at gate (2) (integer tenths of a
# point) and are pinned against the real render by the operator verification.
LINE_GROUP_BASELINE_TOLERANCE_Q = 20
WORD_GAP_THRESHOLD_Q = 15

FORM_DEPTH_MAX = 8
RESOURCE_CATEGORIES_V1 = (
    "XObject",
    "Font",
    "ColorSpace",
    "ExtGState",
    "Pattern",
    "Shading",
    "Properties",
)
FONT_STREAM_KEYS_V1 = ("/FontFile", "/FontFile2", "/FontFile3")

STATUS_PDF_INSPECTION_FAILED = "RENDER_PDF_INSPECTION_FAILED"
REASON_INSPECTION_LIMIT = "INSPECTION_LIMIT"
REASON_PRE_SCAN_READ = "PRE_SCAN_READ"
REASON_PARSER_AMBIGUITY = "PARSER_AMBIGUITY"

DETAIL_STRICT_REREAD = "STRICT_REREAD"
DETAIL_NULL_RESOURCES = "NULL_RESOURCES"
DETAIL_NAME_DOMAIN = "NAME_DOMAIN"
DETAIL_STREAM_MISMATCH = "STREAM_MISMATCH"

# The one pinned pypdf 6.19.0 raise site of (E3): the strict branch of
# PdfReader.get_object in which the strict=False reader returns None.
STRICT_REREAD_MISSING_OBJECT_ARGS = ("Could not find object.",)

# ADMISSIBLE pypdf names: 1 to 127 characters after the slash, each in
# U+0021 to U+007E other than the number sign and the PDF delimiters.
NAME_MAX_CHARACTERS = 127
NAME_EXCLUDED_CHARACTERS = frozenset("#()<>[]{}/%")

EMPTY_SCOPE = ("EMPTY",)


# FAIL_FRAME_EVIDENCE_V1 encoders -------------------------------------------

FAIL_EVIDENCE_STRING_MAX_BYTES = 256
FAIL_EVIDENCE_TRUNCATION_MARKER = "%~"
FAIL_EXCEPTION_CLASS_UNREPRESENTABLE = "<UNREPRESENTABLE>"


def fail_evidence_string(value: str) -> str:
    """FAIL_EVIDENCE_STRING_V1: percent-escape to printable ASCII, cap at 256
    bytes, truncating at a whole escape and appending the "%~" marker."""
    octets = value.encode("utf-8", "surrogatepass")
    pieces = []
    for octet in octets:
        if 0x20 <= octet <= 0x7E and octet not in (0x22, 0x25, 0x5C):
            pieces.append(chr(octet))
        else:
            pieces.append("%{:02X}".format(octet))
    encoded = "".join(pieces)
    if len(encoded) <= FAIL_EVIDENCE_STRING_MAX_BYTES:
        return encoded
    k = FAIL_EVIDENCE_STRING_MAX_BYTES - len(FAIL_EVIDENCE_TRUNCATION_MARKER)
    kept = []
    used = 0
    for piece in pieces:
        if used + len(piece) > k:
            break
        kept.append(piece)
        used += len(piece)
    return "".join(kept) + FAIL_EVIDENCE_TRUNCATION_MARKER


def fail_exception_class(exc: BaseException) -> str:
    """FAIL_EXCEPTION_CLASS_V1: an identifier of 1 to 64 characters."""
    name = type(exc).__name__
    if (
        1 <= len(name) <= 64
        and name.isascii()
        and name.isidentifier()
    ):
        return name
    return FAIL_EXCEPTION_CLASS_UNREPRESENTABLE


def _first_message_line(exc: BaseException) -> str:
    """EXCEPTION MESSAGE SOURCE: str(exception) up to its first LF or CR; the
    empty string when str(exception) raises or does not return a str."""
    try:
        text = str(exc)
    except Exception:
        return ""
    if not isinstance(text, str):
        return ""
    for index, character in enumerate(text):
        if character in "\n\r":
            return text[:index]
    return text


def name_admissible(name: object) -> bool:
    """NAME_DOMAIN: a pypdf name whose str without the leading slash has 1 to
    127 characters, each in U+0021 to U+007E other than the number sign and
    the PDF delimiters."""
    text = str(name)
    if not text.startswith("/"):
        return False
    body = text[1:]
    if not 1 <= len(body) <= NAME_MAX_CHARACTERS:
        return False
    return all(
        "\x21" <= character <= "\x7e" and character not in NAME_EXCLUDED_CHARACTERS
        for character in body
    )


# PRE_SCAN_V1 ----------------------------------------------------------------


class PreScanOutcome(Exception):
    """A deterministic S6.01b outcome (INSPECTION_LIMIT or PRE_SCAN_READ)."""

    def __init__(self, reason: str, detail: str, evidence: dict) -> None:
        super().__init__(reason, detail)
        self.status = STATUS_PDF_INSPECTION_FAILED
        self.reason = reason
        self.detail = detail
        self.evidence = evidence


class CapabilityStop(Exception):
    """A contract STOP condition reached on the pinned stack; never a run
    status and never mapped by PRE_SCAN_READ_V1."""


def _is_plain_dict(obj: object) -> bool:
    return isinstance(obj, DictionaryObject) and not isinstance(obj, StreamObject)


def _name_order_key(name: str) -> bytes:
    return str(name).encode("utf-8", "surrogatepass")


def _miner_predictor_one(params: object) -> bool:
    if params is None:
        return True
    if not isinstance(params, dict):
        return False
    if not params:
        return True
    if set(params) != {"Predictor"}:
        return False
    predictor = params["Predictor"]
    return type(predictor) in (int, float) and predictor == 1


def _miner_filters_agree(filters: object, flate: bool) -> bool:
    """STREAM_MISMATCH: the pdfminer.six get_filters() list agrees with the
    pypdf reading that passed CONTENT_FILTER."""
    if not isinstance(filters, list):
        return False
    if not flate:
        return len(filters) == 0
    if len(filters) != 1:
        return False
    entry = filters[0]
    if not isinstance(entry, tuple) or len(entry) != 2:
        return False
    miner_filter, params = entry
    return miner_filter in LITERALS_FLATE_DECODE and _miner_predictor_one(params)


def _object_id(ref: IndirectObject) -> tuple:
    return (int(ref.idnum), int(ref.generation))


def _limit(detail: str, page_index, count: int, limit: int, **extra) -> PreScanOutcome:
    evidence = {"page_index": page_index, "count": count, "limit": limit}
    evidence.update(extra)
    return PreScanOutcome(REASON_INSPECTION_LIMIT, detail, evidence)


class _FormRecord:
    __slots__ = (
        "object_id",
        "stream",
        "own_resources",
        "own_scope_identity",
        "static_height",
        "reach",
        "font_set",
        "discovery_page",
        "operations",
    )

    def __init__(self, object_id: tuple, stream: StreamObject) -> None:
        self.object_id = object_id
        self.stream = stream
        self.own_resources = None
        self.own_scope_identity = None
        self.static_height = 0
        self.reach = frozenset()
        self.font_set = frozenset()
        self.discovery_page = None
        self.operations = None


class PageGraph:
    """FORM_CALL_GRAPH_V1 prediction for one page."""

    __slots__ = (
        "page_index",
        "page_scope_identity",
        "content_stream_ids",
        "edges",
        "execution_count",
        "font_entries",
    )

    def __init__(self, page_index: int) -> None:
        self.page_index = page_index
        self.page_scope_identity = EMPTY_SCOPE
        self.content_stream_ids = []
        self.edges = set()
        self.execution_count = 0
        self.font_entries = 0


class PreScanResult:
    __slots__ = (
        "pages",
        "form_stream_set",
        "indirect_resolutions",
        "stream_records",
        "exemptions",
        "page_operations",
        "page_resources",
        "forms",
    )

    def __init__(self) -> None:
        self.pages = []
        self.form_stream_set = []
        self.indirect_resolutions = 0
        self.stream_records = []
        self.exemptions = []
        self.page_operations = []
        self.page_resources = []
        self.forms = {}


def open_strict_shadow_reader(pdf_bytes: bytes) -> PdfReader:
    """PARSER_AMBIGUITY_GATE_V1 (A): the STRICT SHADOW READER over the same
    in-memory snapshot bytes with the documented strict argument set to True."""
    return PdfReader(io.BytesIO(pdf_bytes), strict=True)


class _PreScan:
    def __init__(
        self,
        pdf_bytes: bytes,
        reader: PdfReader,
        document: PDFDocument,
        limits: dict,
        strict_reader_factory,
    ) -> None:
        self.pdf_bytes = pdf_bytes
        self.reader = reader
        self.document = document
        self.strict_reader_factory = strict_reader_factory
        self.shadow = None
        self.phase = None
        self.stream_records = []
        self.exemptions = []
        self.limits = limits
        self.resolved = set()
        self.forms = {}
        self.form_stream_set = []
        self.font_streams_done = set()
        self.decoded_content_document = 0
        self.decoded_other_document = 0
        self.operators_document = 0
        self.page_index = None
        self.completed_pages = []

    # -- reads -----------------------------------------------------------

    def _read_error(self, detail: str, exc: BaseException) -> PreScanOutcome:
        if isinstance(exc, MemoryError):
            return _limit("MEMORY", self.page_index, 0, 0)
        return PreScanOutcome(
            REASON_PRE_SCAN_READ,
            detail,
            {
                "page_index": self.page_index,
                "exception_class": fail_exception_class(exc),
                "exception_message": fail_evidence_string(_first_message_line(exc)),
            },
        )

    def _ambiguity(self, detail: str, **evidence) -> PreScanOutcome:
        record = {"page_index": self.page_index}
        record.update(evidence)
        return PreScanOutcome(REASON_PARSER_AMBIGUITY, detail, record)

    def _strict_reread(self, exc: BaseException, object_id) -> PreScanOutcome:
        return self._ambiguity(
            DETAIL_STRICT_REREAD,
            object_id=None if object_id is None else list(object_id),
            exception_class=fail_exception_class(exc),
            exception_message=fail_evidence_string(_first_message_line(exc)),
        )

    def resolve(self, value: object) -> object:
        """Capability-issued get_object; counts distinct (num, gen) pairs. The
        canonical result is returned unchanged (an unresolvable reference stays
        Python None, distinct from a pypdf NullObject)."""
        if not isinstance(value, IndirectObject):
            return value
        key = _object_id(value)
        if key not in self.resolved:
            self.resolved.add(key)
            limit = self.limits["inspection_max_indirect_resolutions"]
            if len(self.resolved) > limit:
                raise _limit(
                    "INDIRECT_RESOLUTIONS", self.page_index, limit + 1, limit
                )
        try:
            obj = value.get_object()
        except (PreScanOutcome, CapabilityStop):
            raise
        except BaseException as exc:
            if not isinstance(exc, Exception):
                raise
            raise self._read_error("OBJECT_READ", exc) from None
        if self.phase in ("P1", "P2"):
            self._mirror(key, obj)
        return obj

    def _mirror(self, canonical_key: tuple, canonical_result: object) -> None:
        """The shadow get_object of the same (object number, generation) that
        immediately follows a capability-issued canonical get_object of P1 or
        P2; it adds nothing to INDIRECT_RESOLUTIONS and supplies no value."""
        shadow_reference = IndirectObject(canonical_key[0], canonical_key[1], self.shadow)
        try:
            self.shadow.get_object(shadow_reference)
        except BaseException as exc:
            if not isinstance(exc, Exception):
                raise
            mirror_key = (int(shadow_reference.idnum), int(shadow_reference.generation))
            if self._unresolved_reference_exempt(canonical_key, mirror_key, canonical_result, exc):
                self.exemptions.append(
                    {"phase": self.phase, "page_index": self.page_index, "object_id": canonical_key}
                )
                return
            raise self._strict_reread(exc, canonical_key) from None

    def _unresolved_reference_exempt(self, canonical_key, mirror_key, canonical_result, exc) -> bool:
        """STRICT_REREAD_UNRESOLVED_REFERENCE_EXEMPTION_V1: exactly (E1) to (E4),
        judged in order for this one lookup and never cached."""
        # (E1) SAME REFERENCE
        if mirror_key != canonical_key:
            return False
        # (E2) CANONICAL UNRESOLVED RESULT
        if canonical_result is not None:
            return False
        # (E3) EXACT PINNED MISSING-OBJECT FAILURE
        if type(exc) is not PdfReadError:
            return False
        if exc.args != STRICT_REREAD_MISSING_OBJECT_ARGS:
            return False
        # (E4) PRIMARY-ENGINE AGREEMENT; the getobj result is evidence only.
        try:
            self.document.getobj(canonical_key[0])
        except Exception as existence_exc:
            return type(existence_exc) is PDFObjectNotFound
        return False

    def read(self, fn, detail: str = "OBJECT_READ"):
        try:
            return fn()
        except (PreScanOutcome, CapabilityStop):
            raise
        except BaseException as exc:
            if not isinstance(exc, Exception):
                raise
            raise self._read_error(detail, exc) from None

    def get(self, dictionary: DictionaryObject, key: str):
        """Resolved value of key, or None when the key is absent."""
        if not self.read(lambda: key in dictionary):
            return None
        raw = self.read(lambda: dictionary.raw_get(key))
        return self.resolve(raw)

    # -- scopes ----------------------------------------------------------

    def page_scope(self, page) -> tuple:
        """PAGE_EFFECTIVE_RESOURCES_V1 over the pinned pypdf page-tree reading."""
        if not self.read(lambda: "/Resources" in page):
            return EMPTY_SCOPE, None
        raw = self.read(lambda: page.raw_get("/Resources"))
        obj = self.resolve(raw)
        if isinstance(obj, NullObject):
            raise self._ambiguity(DETAIL_NULL_RESOURCES, source="PAGE")
        if not _is_plain_dict(obj):
            return EMPTY_SCOPE, None
        return self._page_scope_identity(page, raw, obj), obj

    def _page_scope_identity(self, page, raw, obj) -> tuple:
        if isinstance(raw, IndirectObject):
            return ("INDIRECT",) + _object_id(raw)
        inherited_ref = getattr(obj, "indirect_reference", None)
        if isinstance(inherited_ref, IndirectObject):
            return ("INDIRECT",) + _object_id(inherited_ref)
        page_ref = getattr(page, "indirect_reference", None)
        if not isinstance(page_ref, IndirectObject):
            return ("DIRECT", None)
        node = self.resolve(page_ref)
        node_ref = page_ref
        for _ in range(64):
            if not isinstance(node, DictionaryObject):
                break
            if self.read(lambda: "/Resources" in node) and self.read(
                lambda: node.raw_get("/Resources")
            ) is raw:
                return ("DIRECT",) + _object_id(node_ref)
            if not self.read(lambda: "/Parent" in node):
                break
            parent_raw = self.read(lambda: node.raw_get("/Parent"))
            if not isinstance(parent_raw, IndirectObject):
                break
            node_ref = parent_raw
            node = self.resolve(parent_raw)
        return ("DIRECT", None)

    def form_resources(self, record: _FormRecord) -> None:
        """EFFECTIVE_FORM_RESOURCES_V1: OWN only for a non-stream dictionary
        with at least one key, INHERIT in every other case."""
        stream = record.stream
        if not self.read(lambda: "/Resources" in stream):
            return
        raw = self.read(lambda: stream.raw_get("/Resources"))
        obj = self.resolve(raw)
        if _is_plain_dict(obj) and self.read(lambda: len(obj)) >= 1:
            record.own_resources = obj
            if isinstance(raw, IndirectObject):
                record.own_scope_identity = ("INDIRECT",) + _object_id(raw)
            else:
                record.own_scope_identity = ("DIRECT",) + record.object_id

    def form_target(self, entry_raw) -> tuple:
        """(object id, stream) when an XObject entry names an indirect stream
        with Subtype /Form, else (None, None)."""
        target = self.resolve(entry_raw)
        if not isinstance(entry_raw, IndirectObject):
            return None, None
        if not isinstance(target, StreamObject):
            return None, None
        subtype = self.get(target, "/Subtype")
        if subtype is None or self.read(lambda: subtype != "/Form"):
            return None, None
        return _object_id(entry_raw), target

    # -- P1 --------------------------------------------------------------

    def dictionary_check(self, dictionary, source, object_id, category) -> None:
        count = self.read(lambda: len(dictionary))
        limit = self.limits["inspection_max_resource_dict_entries"]
        if count > limit:
            raise _limit(
                "RESOURCE_ENTRIES",
                self.page_index,
                count,
                limit,
                source=source,
                object_id=object_id,
                category=category,
            )
        for key in self.read(lambda: list(dictionary.keys())):
            if not name_admissible(key):
                raise self._ambiguity(
                    DETAIL_NAME_DOMAIN,
                    source=source,
                    object_id=object_id,
                    category=category,
                    resource_name=fail_evidence_string(str(key)[1:] if str(key).startswith("/") else str(key)),
                )

    def operation_names_check(self, operands) -> None:
        """NAME_DOMAIN for every pypdf NameObject returned as or inside an
        operand of a produced operation."""
        pending = [operands]
        while pending:
            value = pending.pop()
            if isinstance(value, NameObject):
                if not name_admissible(value):
                    text = str(value)
                    raise self._ambiguity(
                        DETAIL_NAME_DOMAIN,
                        resource_name=fail_evidence_string(text[1:] if text.startswith("/") else text),
                    )
            elif isinstance(value, dict):
                pending.extend(value.keys())
                pending.extend(value.values())
            elif isinstance(value, (list, tuple)):
                pending.extend(value)

    def walk_scope(self, resources, scope_font_id, source, object_id, depth, path, page_fonts, page_scopes):
        """PRE_SCAN_TRAVERSAL_V1 for one scope; returns (height, reach, own fonts)."""
        self.dictionary_check(resources, source, object_id, None)
        height = 0
        reach = set()
        own_fonts = set()
        for category in RESOURCE_CATEGORIES_V1:
            sub = self.get(resources, "/" + category)
            if not _is_plain_dict(sub):
                continue
            self.dictionary_check(sub, source, object_id, category)
            if category == "XObject":
                names = sorted(self.read(lambda: list(sub.keys())), key=_name_order_key)
                for name in names:
                    entry_raw = self.read(lambda: sub.raw_get(name))
                    form_id, stream = self.form_target(entry_raw)
                    if form_id is None:
                        continue
                    child_height, child_reach = self.visit_form_entry(
                        form_id, stream, depth, path, page_fonts, page_scopes
                    )
                    height = max(height, child_height + 1)
                    reach |= child_reach
            elif category == "Font":
                names = sorted(self.read(lambda: list(sub.keys())), key=_name_order_key)
                for name in names:
                    entry_raw = self.read(lambda: sub.raw_get(name))
                    if isinstance(entry_raw, IndirectObject):
                        own_fonts.add(("OBJ",) + _object_id(entry_raw))
                    else:
                        own_fonts.add(("DIRECT", scope_font_id, str(name)))
        return height, reach, own_fonts

    def visit_form_entry(self, form_id, stream, depth, path, page_fonts, page_scopes):
        target_depth = depth + 1
        if form_id in path or target_depth > FORM_DEPTH_MAX:
            raise _limit(
                "FORM_DEPTH", self.page_index, target_depth, FORM_DEPTH_MAX,
                object_id=list(form_id),
            )
        record = self.forms.get(form_id)
        if record is not None:
            if target_depth + record.static_height > FORM_DEPTH_MAX:
                raise _limit(
                    "FORM_DEPTH",
                    self.page_index,
                    target_depth + record.static_height,
                    FORM_DEPTH_MAX,
                    object_id=list(form_id),
                )
            self._add_reach(record.reach, page_fonts, page_scopes)
            return record.static_height, set(record.reach)
        record = _FormRecord(form_id, stream)
        record.discovery_page = self.page_index
        self.forms[form_id] = record
        self.form_stream_set.append(form_id)
        self.form_resources(record)
        if record.own_resources is None:
            record.static_height = 0
            record.reach = frozenset()
            return 0, set()
        height, reach, own_fonts = self.walk_scope(
            record.own_resources,
            form_id,
            "FORM",
            list(form_id),
            target_depth,
            path | {form_id},
            page_fonts,
            page_scopes,
        )
        record.static_height = height
        record.font_set = frozenset(own_fonts)
        reach.add(form_id)
        record.reach = frozenset(reach)
        self._add_reach(record.reach, page_fonts, page_scopes)
        return height, set(record.reach)

    def _add_reach(self, reach, page_fonts, page_scopes) -> None:
        for member in reach:
            page_scopes.add(member)
            page_fonts |= self.forms[member].font_set

    # -- P2 to P4 --------------------------------------------------------

    def content_stream_refs(self, page) -> list:
        """The page /Contents enumeration (P2 of PRE_SCAN_ORDER_V1)."""
        if not self.read(lambda: "/Contents" in page):
            return []
        raw = self.read(lambda: page.raw_get("/Contents"))
        value = self.resolve(raw)
        if isinstance(value, StreamObject):
            if isinstance(raw, IndirectObject):
                return [(_object_id(raw), value)]
            return []
        if isinstance(value, ArrayObject):
            refs = []
            for element in self.read(lambda: list(value)):
                stream = self.resolve(element)
                if isinstance(element, IndirectObject) and isinstance(stream, StreamObject):
                    refs.append((_object_id(element), stream))
            return refs
        return []

    def font_streams(self, page_scope_resources, page_scopes) -> list:
        """FontFile, FontFile2, FontFile3, ToUnicode and Encoding/CMap streams
        of the effective /Font resources, fonts in P1 order by resource name."""
        scopes = []
        if page_scope_resources is not None:
            scopes.append(page_scope_resources)
        for form_id in self.form_stream_set:
            if form_id in page_scopes and self.forms[form_id].own_resources is not None:
                scopes.append(self.forms[form_id].own_resources)
        found = []
        for resources in scopes:
            fonts = self.get(resources, "/Font")
            if not _is_plain_dict(fonts):
                continue
            names = sorted(self.read(lambda: list(fonts.keys())), key=_name_order_key)
            for name in names:
                font = self.resolve(self.read(lambda: fonts.raw_get(name)))
                if not _is_plain_dict(font):
                    continue
                descriptors = []
                descriptor = self.get(font, "/FontDescriptor")
                if _is_plain_dict(descriptor):
                    descriptors.append(descriptor)
                descendants = self.get(font, "/DescendantFonts")
                if isinstance(descendants, ArrayObject):
                    for element in self.read(lambda: list(descendants)):
                        child = self.resolve(element)
                        if _is_plain_dict(child):
                            child_descriptor = self.get(child, "/FontDescriptor")
                            if _is_plain_dict(child_descriptor):
                                descriptors.append(child_descriptor)
                for descriptor in descriptors:
                    for key in FONT_STREAM_KEYS_V1:
                        self._add_stream(descriptor, key, found)
                self._add_stream(font, "/ToUnicode", found)
                self._add_stream(font, "/Encoding", found)
        return found

    def _add_stream(self, dictionary, key, found) -> None:
        if not self.read(lambda: key in dictionary):
            return
        raw = self.read(lambda: dictionary.raw_get(key))
        stream = self.resolve(raw)
        if not isinstance(raw, IndirectObject) or not isinstance(stream, StreamObject):
            return
        stream_id = _object_id(raw)
        if stream_id in self.font_streams_done:
            return
        self.font_streams_done.add(stream_id)
        found.append((stream_id, stream))

    def filter_check(self, stream_id, stream) -> bool:
        """CONTENT_FILTER; returns True when the stream is Flate-encoded."""
        filt = self.get(stream, "/Filter")
        flate = False
        if filt is None or isinstance(filt, NullObject):
            flate = False
        elif self.read(lambda: filt == "/FlateDecode"):
            flate = True
        elif isinstance(filt, ArrayObject) and self.read(lambda: len(filt)) == 1:
            only = self.resolve(self.read(lambda: filt[0]))
            if self.read(lambda: only == "/FlateDecode"):
                flate = True
            else:
                raise self._filter_violation(stream_id)
        else:
            raise self._filter_violation(stream_id)
        parms = self.get(stream, "/DecodeParms")
        if parms is not None and not isinstance(parms, NullObject):
            if not _is_plain_dict(parms):
                raise self._filter_violation(stream_id)
            for key in self.read(lambda: list(parms.keys())):
                if key != "/Predictor":
                    raise self._filter_violation(stream_id)
                predictor = self.get(parms, "/Predictor")
                if self.read(lambda: predictor != 1):
                    raise self._filter_violation(stream_id)
        return flate

    def _filter_violation(self, stream_id) -> PreScanOutcome:
        return _limit("CONTENT_FILTER", self.page_index, 1, 0, object_id=list(stream_id))

    def raw_bytes(self, stream_id: tuple, flate: bool) -> bytes:
        """RAW_STREAM_BYTES_V1: PDFStream.get_rawdata() of the object that the
        pinned pdfminer.six PDFDocument.getobj returns for the stream's object
        number, after STREAM_MISMATCH; nothing is decoded here."""
        miner_stream = self.read(lambda: self.document.getobj(stream_id[0]), "RAW_BYTES_READ")
        if not isinstance(miner_stream, PDFStream):
            raise self._ambiguity(DETAIL_STREAM_MISMATCH, object_id=list(stream_id))
        filters = self.read(lambda: miner_stream.get_filters(), "RAW_BYTES_READ")
        if not _miner_filters_agree(filters, flate):
            raise self._ambiguity(DETAIL_STREAM_MISMATCH, object_id=list(stream_id))
        raw = self.read(lambda: miner_stream.get_rawdata(), "RAW_BYTES_READ")
        if not isinstance(raw, bytes):
            raise PreScanOutcome(
                REASON_PRE_SCAN_READ,
                "RAW_BYTES_READ",
                {"page_index": self.page_index, "object_id": list(stream_id)},
            )
        return raw

    def record_stream(self, stream_id, stream_class, raw: bytes, decoded: bytes) -> None:
        self.stream_records.append(
            {
                "object_id": stream_id,
                "stream_class": stream_class,
                "raw_sha256": hashlib.sha256(raw).hexdigest(),
                "raw_length": len(raw),
                "decoded_length": len(decoded),
            }
        )

    def decode(self, raw: bytes, flate: bool, remaining: int) -> tuple:
        """(decoded bytes, over_budget) with at most remaining + 1 bytes."""
        if not flate:
            if len(raw) > remaining:
                return raw[: remaining + 1], True
            return raw, False
        decompressor = zlib.decompressobj()
        try:
            out = decompressor.decompress(raw, remaining + 1)
        except zlib.error as exc:
            raise self._read_error("ZLIB_ERROR", exc) from None
        except MemoryError:
            raise _limit("MEMORY", self.page_index, 0, 0) from None
        if len(out) > remaining:
            return out, True
        if not decompressor.eof:
            raise PreScanOutcome(
                REASON_PRE_SCAN_READ,
                "FLATE_INCOMPLETE",
                {"page_index": self.page_index},
            )
        return out, False

    def parse(self, decoded: bytes) -> list:
        def run():
            carrier = DecodedStreamObject()
            carrier.set_data(decoded)
            return list(ContentStream(carrier, self.reader).operations)

        return self.read(run, "CONTENT_PARSE")

    # -- P5 --------------------------------------------------------------

    def page_graph(self, graph: PageGraph, page_resources, page_operations) -> None:
        """FORM_CALL_GRAPH_V1: the node graph is built first (every node once,
        edges in operation order), then FORM_DEPTH is judged over the whole
        graph in depth-first order, then FORM_EXECUTIONS."""
        root = (("PAGE", graph.page_index), graph.page_scope_identity)
        scope_dicts = {graph.page_scope_identity: page_resources}

        def scope_targets(scope_identity, operations):
            resources = scope_dicts.get(scope_identity)
            xobjects = self.get(resources, "/XObject") if resources is not None else None
            targets = []
            for operands, operator in operations:
                if operator != b"Do":
                    continue
                if not _is_plain_dict(xobjects) or not operands:
                    targets.append(None)
                    continue
                name = operands[0]
                if not self.read(lambda: name in xobjects):
                    targets.append(None)
                    continue
                form_id, _ = self.form_target(self.read(lambda: xobjects.raw_get(name)))
                targets.append(form_id)
            return targets

        def node_operations(node):
            owner = node[0]
            if owner[0] == "PAGE":
                return page_operations
            return self.forms[owner[1]].operations

        def target_node(form_id, invoker_scope):
            record = self.forms[form_id]
            if record.own_resources is not None:
                scope_dicts[record.own_scope_identity] = record.own_resources
                return (("FORM", form_id), record.own_scope_identity)
            return (("FORM", form_id), invoker_scope)

        edge_lists = {}
        pending = [root]
        while pending:
            node = pending.pop()
            if node in edge_lists:
                continue
            targets = []
            for form_id in scope_targets(node[1], node_operations(node)):
                if form_id is None:
                    continue
                target = target_node(form_id, node[1])
                graph.edges.add((node[0], form_id, node[1]))
                targets.append(target)
                if target not in edge_lists:
                    pending.append(target)
            edge_lists[node] = targets

        heights = {}

        def depth_first(node, depth, active):
            height = 0
            for target in edge_lists[node]:
                form_id = target[0][1]
                target_depth = depth + 1
                if form_id in active or target_depth > FORM_DEPTH_MAX:
                    raise self._graph_outcome(
                        graph, "FORM_DEPTH", target_depth, FORM_DEPTH_MAX, form_id
                    )
                if target in heights:
                    if target_depth + heights[target] > FORM_DEPTH_MAX:
                        raise self._graph_outcome(
                            graph,
                            "FORM_DEPTH",
                            target_depth + heights[target],
                            FORM_DEPTH_MAX,
                            form_id,
                        )
                else:
                    depth_first(target, target_depth, active | {form_id})
                height = max(height, heights[target] + 1)
            heights[node] = height

        depth_first(root, 0, frozenset())

        bound = self.limits["inspection_max_traversal_operations"]
        counts = {}

        def executions(node):
            if node in counts:
                return counts[node]
            total = min(len(node_operations(node)), bound + 1)
            for target in edge_lists[node]:
                total = min(total + executions(target), bound + 1)
                if total > bound:
                    break
            counts[node] = total
            return total

        graph.execution_count = executions(root)
        if graph.execution_count > bound:
            raise self._graph_outcome(graph, "FORM_EXECUTIONS", bound + 1, bound, None)

    def _graph_outcome(self, graph, detail, count, limit, form_id) -> PreScanOutcome:
        extra = {} if form_id is None else {"object_id": list(form_id)}
        outcome = _limit(detail, graph.page_index, count, limit, **extra)
        outcome.page_graph = graph
        return outcome

    # -- driver ----------------------------------------------------------

    def run(self) -> PreScanResult:
        result = PreScanResult()
        pages = self.read(lambda: list(self.reader.pages), "OBJECT_READ")
        limits = self.limits

        # P0: construction and page enumeration of the strict shadow reader;
        # never exempted.
        self.phase = "P0"
        try:
            self.shadow = self.strict_reader_factory(self.pdf_bytes)
            list(self.shadow.pages)
        except BaseException as exc:
            if not isinstance(exc, Exception):
                raise
            raise self._strict_reread(exc, None) from None

        for page_index, page in enumerate(pages):
            self.page_index = page_index
            graph = PageGraph(page_index)
            page_fonts = set()
            page_scopes = set()
            first_form = len(self.form_stream_set)

            # P1
            self.phase = "P1"
            scope_identity, page_resources = self.page_scope(page)
            graph.page_scope_identity = scope_identity
            if page_resources is not None:
                _, _, own_fonts = self.walk_scope(
                    page_resources, "PAGE", "PAGE", None, 0, frozenset(),
                    page_fonts, page_scopes,
                )
                page_fonts |= own_fonts
            font_limit = limits["inspection_max_fonts_per_page"]
            if len(page_fonts) > font_limit:
                raise _limit("FONT_COUNT", page_index, font_limit + 1, font_limit)
            graph.font_entries = len(page_fonts)

            # P2
            self.phase = "P2"
            content = self.content_stream_refs(page)
            graph.content_stream_ids = [stream_id for stream_id, _ in content]
            new_forms = self.form_stream_set[first_form:]
            content_streams = list(content) + [
                (form_id, self.forms[form_id].stream) for form_id in new_forms
            ]
            other_streams = self.font_streams(page_resources, page_scopes)
            flate = {}
            for stream_id, stream in content_streams + other_streams:
                flate[stream_id] = self.filter_check(stream_id, stream)

            # P3 / P4
            self.phase = "P3"
            decoded_page = 0
            operators_page = 0
            page_operations = []
            content_count = len(content)
            for position, (stream_id, stream) in enumerate(content_streams):
                raw = self.raw_bytes(stream_id, flate[stream_id])
                page_budget = limits["inspection_max_decoded_content_bytes_per_page"] - decoded_page
                doc_budget = (
                    limits["inspection_max_decoded_content_bytes_per_document"]
                    - self.decoded_content_document
                )
                decoded, over = self.decode(raw, flate[stream_id], min(page_budget, doc_budget))
                decoded_page += len(decoded)
                self.decoded_content_document += len(decoded)
                if over or decoded_page > limits["inspection_max_decoded_content_bytes_per_page"]:
                    if decoded_page > limits["inspection_max_decoded_content_bytes_per_page"]:
                        raise _limit(
                            "DECODED_CONTENT_BYTES", page_index,
                            limits["inspection_max_decoded_content_bytes_per_page"] + 1,
                            limits["inspection_max_decoded_content_bytes_per_page"],
                        )
                    raise _limit(
                        "DECODED_CONTENT_BYTES", page_index,
                        limits["inspection_max_decoded_content_bytes_per_document"] + 1,
                        limits["inspection_max_decoded_content_bytes_per_document"],
                    )
                self.record_stream(
                    stream_id, "PAGE_CONTENT" if position < content_count else "FORM_CONTENT",
                    raw, decoded,
                )
                operations = self.parse(decoded)
                for operands, _operator in operations:
                    operators_page += 1
                    self.operators_document += 1
                    if operators_page > limits["inspection_max_content_operators_per_page"]:
                        raise _limit(
                            "CONTENT_OPERATORS_PAGE", page_index, operators_page,
                            limits["inspection_max_content_operators_per_page"],
                        )
                    if self.operators_document > limits["inspection_max_content_operators_per_document"]:
                        raise _limit(
                            "CONTENT_OPERATORS_DOCUMENT", page_index, self.operators_document,
                            limits["inspection_max_content_operators_per_document"],
                        )
                    self.operation_names_check(operands)
                if position < content_count:
                    page_operations.extend(operations)
                else:
                    self.forms[stream_id].operations = operations
            for stream_id, stream in other_streams:
                raw = self.raw_bytes(stream_id, flate[stream_id])
                budget = (
                    limits["inspection_max_decoded_other_stream_bytes_per_document"]
                    - self.decoded_other_document
                )
                decoded, over = self.decode(raw, flate[stream_id], budget)
                self.decoded_other_document += len(decoded)
                if over:
                    raise _limit(
                        "DECODED_OTHER_BYTES", page_index,
                        limits["inspection_max_decoded_other_stream_bytes_per_document"] + 1,
                        limits["inspection_max_decoded_other_stream_bytes_per_document"],
                    )
                self.record_stream(stream_id, "FONT", raw, decoded)

            # P5
            self.phase = "P5"
            self.page_graph(graph, page_resources, page_operations)
            result.pages.append(graph)
            result.page_operations.append(page_operations)
            result.page_resources.append(page_resources)
            self.completed_pages.append(graph)
        self.phase = None
        result.forms = dict(self.forms)
        result.form_stream_set = list(self.form_stream_set)
        result.indirect_resolutions = len(self.resolved)
        result.stream_records = list(self.stream_records)
        result.exemptions = list(self.exemptions)
        return result


def open_pypdf_reader(pdf_bytes: bytes) -> PdfReader:
    """PDFMINER_EXECUTION_BINDING_V1: PdfReader over the snapshot bytes with
    its default strict=False."""
    return PdfReader(io.BytesIO(pdf_bytes))


def open_pdfminer_document(pdf_bytes: bytes) -> PDFDocument:
    """PDFMINER_EXECUTION_BINDING_V1: PDFParser over the in-memory snapshot
    bytes and PDFDocument(parser) with its default arguments."""
    return PDFDocument(PDFParser(io.BytesIO(pdf_bytes)))


def run_pre_scan(
    pdf_bytes: bytes,
    reader: PdfReader,
    document: PDFDocument,
    limits: dict | None = None,
    strict_reader_factory=open_strict_shadow_reader,
) -> PreScanResult:
    """PRE_SCAN_V1 (S6.01b) over one snapshot: reader is the canonical
    strict=False pypdf reader and document the pdfminer.six PDFDocument of
    PDFMINER_EXECUTION_BINDING_V1, both over pdf_bytes. Raises PreScanOutcome
    for a deterministic INSPECTION_LIMIT, PRE_SCAN_READ or PARSER_AMBIGUITY
    outcome; the outcome carries the page graphs completed before it
    (completed_pages), the stream records and the exempted lookups."""
    scan = _PreScan(
        pdf_bytes, reader, document, dict(limits or INSPECTION_LIMITS_V1), strict_reader_factory
    )
    try:
        return scan.run()
    except PreScanOutcome as outcome:
        outcome.completed_pages = list(scan.completed_pages)
        outcome.stream_records = list(scan.stream_records)
        outcome.exemptions = list(scan.exemptions)
        outcome.phase = scan.phase
        raise


# =============================================================================
# CHILD_PROTOCOL_V1: frames, stages S5.02 to S10 and the entry main
# =============================================================================

PROTOCOL_ID = "CHILD_PROTOCOL_V1"
CHILD_STAGES = ("S5.02", "S5.03", "S6", "S7", "S9", "S10")
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
TEXT_CHUNK_MAX_CHARS = 1024
EXPECTED_FD_STATE = [[0, "pipe"], [1, "pipe"], [2, "pipe"]]

NO_TRIPLE = (None, None, None)
MEMORY_TRIPLE = (STATUS_PDF_INSPECTION_FAILED, REASON_INSPECTION_LIMIT, "MEMORY")
EVIDENCE_BYTES_TRIPLE = (STATUS_PDF_INSPECTION_FAILED, REASON_INSPECTION_LIMIT, "EVIDENCE_BYTES")
STATUS_RUNTIME_INCOMPLETE = "RENDER_SANDBOX_RUNTIME_INCOMPLETE"
STATUS_TEXT_UNOBSERVABLE = "RENDER_TEXT_STATE_UNOBSERVABLE"

TOLERANCE_001 = Decimal("0.01")
TOLERANCE_1E6 = Decimal("0.000001")
DUPLICATE_TOLERANCE = Decimal("0.5")
SMALL_TEXT_SIZE = Decimal("4.0")


class ChildFail(Exception):
    """One child-evaluated failing check: a CHILD_FAIL_CLOSED_SET_V1 triple
    and its FAIL_EVIDENCE_KEYS_V1 evidence (slot included)."""

    def __init__(self, status, reason, detail, evidence: dict) -> None:
        super().__init__(status, reason, detail)
        self.triple = (status, reason, detail)
        self.evidence = evidence


def _cfail(status, reason, detail, slot, **evidence) -> ChildFail:
    record = {"slot": slot}
    record.update(evidence)
    return ChildFail(status, reason, detail, record)


def _is_int(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _object_id_text(object_id) -> object:
    if object_id is None:
        return None
    return "%d %d" % (int(object_id[0]), int(object_id[1]))


def _name_text(name) -> str:
    """A pypdf name without its slash, encoded by FAIL_EVIDENCE_STRING_V1."""
    text = str(name)
    return fail_evidence_string(text[1:] if text.startswith("/") else text)


def _chunks(text: str) -> list:
    return [text[index:index + TEXT_CHUNK_MAX_CHARS] for index in range(0, len(text), TEXT_CHUNK_MAX_CHARS)]


# TEXT_NORMALIZATION_V1 (the same tables as the adapter; the entry is a single
# self-contained file) ----------------------------------------------------------

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
    return any(ch not in SEPARATOR_CHARACTERS and ch not in DELETED_CHARACTERS for ch in text)


def is_separator_text(text: str) -> bool:
    return bool(text) and all(ch in SEPARATOR_CHARACTERS for ch in text)


# URI_CANONICALIZATION_V1 (identical to the adapter's pure function) -------------

_PCT_TRIPLET = re.compile(r"%([0-9A-Fa-f]{2})")
_UNRESERVED = frozenset("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~")


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


# NUMERIC_NORMALIZATION_V1 and COORDINATE_QUANTIZATION_V1 ------------------------

def normalize_number(value):
    """The finite binary64 of a library real number, else None (never
    defaulted, clamped or repaired)."""
    if value is None or isinstance(value, (bool, BooleanObject, str, bytes, bytearray, list, tuple, dict)):
        return None
    if not isinstance(value, (int, float, Decimal)) and not hasattr(value, "__float__"):
        return None
    try:
        converted = float(value)
    except Exception:
        return None
    if not math.isfinite(converted):
        return None
    return converted


def _is_real_number(value) -> bool:
    """A real number object, finite or not (S6.09 judges non-finite values)."""
    if value is None or isinstance(value, (bool, BooleanObject, str, bytes, bytearray, list, tuple, dict)):
        return False
    return isinstance(value, (int, float, Decimal)) or hasattr(value, "__float__")


def quantize(value: float) -> int:
    with localcontext() as context:
        context.prec = 100
        return int((Decimal(value) * 10).to_integral_value(rounding=ROUND_HALF_EVEN))


def _dec(value: float) -> Decimal:
    return Decimal(value)


def _abs_diff(a: float, b: float) -> Decimal:
    with localcontext() as context:
        context.prec = 100
        return abs(Decimal(a) - Decimal(b))


# Frame limits and emitter ------------------------------------------------------

def _float_integer_digits(value: float) -> int:
    text = repr(abs(value))
    count = 0
    for ch in text:
        if not ch.isdigit():
            break
        count += 1
    return count


def frame_within_limits(frame: dict, line_bytes: int) -> bool:
    """CHILD_FRAME_LIMITS_V1 judged on the frame object exactly as the
    parent's byte scanner counts the serialized line."""
    limits = CHILD_FRAME_LIMITS_V1
    if line_bytes > limits["child_max_frame_bytes"]:
        return False
    total = 0
    pending = [(frame, 1)]
    while pending:
        value, depth = pending.pop()
        total += 1
        if isinstance(value, dict):
            if depth > limits["child_max_json_depth"] or len(value) > limits["child_max_object_members"]:
                return False
            for key, item in value.items():
                if len(key.encode("utf-8")) > limits["child_max_string_bytes"]:
                    return False
                pending.append((item, depth + 1))
        elif isinstance(value, list):
            if depth > limits["child_max_json_depth"] or len(value) > limits["child_max_array_elements"]:
                return False
            pending.extend((item, depth + 1) for item in value)
        elif isinstance(value, str):
            if len(value.encode("utf-8")) > limits["child_max_string_bytes"]:
                return False
        elif isinstance(value, bool) or value is None:
            continue
        elif isinstance(value, int):
            if len(str(abs(value))) > limits["child_max_integer_digits"]:
                return False
        elif isinstance(value, float):
            if _float_integer_digits(value) > limits["child_max_integer_digits"]:
                return False
        if total > limits["child_max_frame_elements"]:
            return False
    return True


def _frame(seq: int, kind: str, stage, outcome: str, triple: tuple, evidence: dict) -> dict:
    return {
        "protocol": PROTOCOL_ID,
        "seq": seq,
        "kind": kind,
        "stage": stage,
        "outcome": outcome,
        "status": triple[0],
        "reason": triple[1],
        "detail": triple[2],
        "evidence": evidence,
    }


def encode_frame(frame: dict) -> bytes:
    text = json.dumps(frame, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    return (text + "\n").encode("utf-8")


class FrameEmitter:
    """Writes and flushes one frame per stage (stage-by-stage flush). A PASS
    frame that would leave less than FAIL_FRAME_RESERVE_BYTES of the
    evidence budget, or that exceeds CHILD_FRAME_LIMITS_V1, is replaced by
    the reserved-budget EVIDENCE_BYTES FAIL frame (never used at S5.02)."""

    def __init__(self, stream, evidence_limit: int = INSPECTION_LIMITS_V1["inspection_max_evidence_bytes"]) -> None:
        self.stream = stream
        self.evidence_limit = evidence_limit
        self.written = 0
        self.seq = 0

    def _write(self, data: bytes) -> None:
        self.stream.write(data)
        self.stream.flush()
        self.written += len(data)
        self.seq += 1

    def stage(self, stage: str, outcome: str, triple: tuple, evidence: dict) -> tuple:
        frame = _frame(self.seq, "STAGE", stage, outcome, triple, evidence)
        try:
            data = encode_frame(frame)
        except (TypeError, ValueError, UnicodeEncodeError):
            data = None
        if outcome == "PASS":
            budget = self.evidence_limit - FAIL_FRAME_RESERVE_BYTES
            within = data is not None and self.written + len(data) <= budget
        else:
            within = (
                data is not None
                and len(data) <= CHILD_FRAME_LIMITS_V1["child_fail_frame_max_bytes"]
                and self.written + len(data) <= self.evidence_limit
            )
        within = within and frame_within_limits(frame, len(data))
        if not within and stage != "S5.02":
            triple = EVIDENCE_BYTES_TRIPLE
            outcome = "FAIL"
            data = encode_frame(_frame(self.seq, "STAGE", stage, outcome, triple, {}))
        self._write(data)
        return NO_TRIPLE if outcome == "PASS" else triple

    def final(self, triple: tuple, pdf_sha256: str, entry_sha256: str) -> None:
        outcome = "PASS" if triple == NO_TRIPLE else "FAIL"
        evidence = {
            "pdf_sha256": pdf_sha256,
            "inspection_entry_sha256": entry_sha256,
            "evidence_bytes": self.written,
        }
        self._write(encode_frame(_frame(self.seq, "FINAL", None, outcome, triple, evidence)))


# Child context ------------------------------------------------------------------

class ChildContext:
    def __init__(self, pdf_bytes: bytes, observation: dict, line_tolerance_q: int, word_gap_q: int,
                 limits: dict | None = None) -> None:
        self.pdf_bytes = pdf_bytes
        self.pdf_sha256 = _sha256(pdf_bytes)
        self.observation = observation
        self.entry_sha256 = _sha256(observation["entry_bytes"])
        self.line_tolerance_q = line_tolerance_q
        self.word_gap_q = word_gap_q
        self.limits = dict(limits or INSPECTION_LIMITS_V1)
        self.stage = None
        self.slot = None
        self.exc_reason = None
        self.page_index = None
        self.attestation = None
        self.reader = None
        self.document = None
        self.pages = None
        self.miner_pages = None
        self.prescan = None
        self.page_facts = []
        self.traversals = []
        self.page_words = []
        self.resolved = set()

    def at(self, slot: str, exc_reason, page_index=None) -> None:
        self.slot = slot
        self.exc_reason = exc_reason
        self.page_index = page_index

    def resolve(self, value):
        """get_object of the pinned pypdf; distinct (num, gen) pairs count
        toward inspection_max_indirect_resolutions."""
        if not isinstance(value, IndirectObject):
            return value
        key = _object_id(value)
        if key not in self.resolved:
            self.resolved.add(key)
            limit = self.limits["inspection_max_indirect_resolutions"]
            if len(self.resolved) > limit:
                raise _cfail(STATUS_PDF_INSPECTION_FAILED, REASON_INSPECTION_LIMIT, "INDIRECT_RESOLUTIONS",
                             self.slot, page_index=self.page_index, count=limit + 1, limit=limit)
        return value.get_object()

    def lookup(self, dictionary, key):
        """(present, resolved value) of a dictionary key."""
        if dictionary is None or key not in dictionary:
            return False, None
        return True, self.resolve(dictionary.raw_get(key))


def _absent_or_null(value) -> bool:
    return value is None or isinstance(value, NullObject)


def _plain_get(dictionary, key):
    """Resolved value through get_object without resolution counting (the
    S5.03 and S6 page-fact reads)."""
    raw = dictionary.raw_get(key)
    return raw.get_object() if isinstance(raw, IndirectObject) else raw


def start_attestation(observation: dict, pdf_bytes: bytes) -> dict:
    return {
        "inspection_entry_sha256": _sha256(observation["entry_bytes"]),
        "received_pdf_sha256": _sha256(pdf_bytes),
        "fd_state": [
            [number, fail_evidence_string(kind)]
            for number, kind in observation["descriptors"][:FD_STATE_MAX_ENTRIES]
        ],
        "tmpdir_entries": observation["tmpdir_entries"],
        "pycache_state": observation["pycache_state"],
        "pycache_prefix_matches": observation["pycache_prefix_matches"],
    }


def start_state_violated(attestation: dict) -> bool:
    return (
        attestation["fd_state"] != EXPECTED_FD_STATE
        or attestation["tmpdir_entries"] != 0
        or attestation["pycache_state"] != "ABSENT"
        or attestation["pycache_prefix_matches"] != 1
    )


def _exception_evidence(exc: BaseException) -> dict:
    return {
        "exception_class": fail_exception_class(exc),
        "exception_message": fail_evidence_string(_first_message_line(exc)),
    }


# S5.02 VALID_OUTPUT_V1 library opens and START_ATTESTATION_V1 -------------------

def stage_s5_02(ctx: ChildContext) -> dict:
    ctx.at("S5.02", None)
    attestation = start_attestation(ctx.observation, ctx.pdf_bytes)
    ctx.attestation = attestation
    if start_state_violated(attestation):
        raise _cfail(STATUS_RUNTIME_INCOMPLETE, "INSPECTION_RUNTIME_INCOMPLETE", "START_STATE", "S5.02",
                     start_attestation=attestation)

    def output_invalid(detail, exc=None) -> ChildFail:
        extra = _exception_evidence(exc) if exc is not None else {}
        return _cfail(STATUS_RUNTIME_INCOMPLETE, "OUTPUT_INVALID", detail, "S5.02",
                      start_attestation=attestation, **extra)

    try:
        reader = open_pypdf_reader(ctx.pdf_bytes)
        encrypted = "/Encrypt" in reader.trailer
    except MemoryError:
        raise
    except Exception as exc:
        raise output_invalid("PYPDF_OPEN", exc) from None
    if encrypted:
        raise output_invalid("ENCRYPTED")
    try:
        page_count = len(list(reader.pages))
    except MemoryError:
        raise
    except Exception as exc:
        raise output_invalid("PYPDF_OPEN", exc) from None
    if page_count < 1:
        raise output_invalid("PYPDF_OPEN")
    try:
        document = open_pdfminer_document(ctx.pdf_bytes)
        miner_count = len(list(PDFPage.create_pages(document)))
    except MemoryError:
        raise
    except Exception as exc:
        raise output_invalid("PDFMINER_OPEN", exc) from None
    if miner_count < 1:
        raise output_invalid("PDFMINER_OPEN")
    ctx.reader = reader
    ctx.document = document
    return {"start_attestation": attestation}


# S5.03 DOCUMENT_STATE_V1 ----------------------------------------------------------

CATALOG_DENIED_KEYS_V1 = (
    ("/AcroForm", "ACROFORM_PRESENT"),
    ("/OpenAction", "OPEN_ACTION_PRESENT"),
    ("/AA", "CATALOG_AA_PRESENT"),
    ("/Names", "NAMES_PRESENT"),
    ("/AF", "AF_PRESENT"),
    ("/Collection", "COLLECTION_PRESENT"),
    ("/Perms", "PERMS_PRESENT"),
    ("/Requirements", "REQUIREMENTS_PRESENT"),
    ("/Outlines", "OUTLINES_PRESENT"),
    ("/URI", "URI_BASE_PRESENT"),
)
STATUS_DOCUMENT_STATE = "RENDER_DOCUMENT_STATE_UNSUPPORTED"


def _present_non_null(dictionary, key) -> bool:
    if key not in dictionary:
        return False
    return not _absent_or_null(_plain_get(dictionary, key))


def _open_action_destination_admitted(ctx: ChildContext, root) -> bool:
    """OPEN_ACTION_DESTINATION_V1: the catalog /OpenAction is admitted only
    as the plain destination array [page /XYZ null null 0] whose page is in
    the enumerated page tree of this document. Every other shape, including
    any action dictionary, a missing or null-resolving indirect object, is
    not admitted. A raising read propagates to DOCUMENT_STATE_READ."""
    raw = root.raw_get("/OpenAction")
    value = raw.get_object() if isinstance(raw, IndirectObject) else raw
    if not isinstance(value, ArrayObject) or len(value) != 5:
        return False
    elements = list(value)
    first = elements[0]
    if not isinstance(first, IndirectObject):
        return False
    page_ids = set()
    for page in ctx.reader.pages:
        reference = getattr(page, "indirect_reference", None)
        if isinstance(reference, IndirectObject):
            page_ids.add(_object_id(reference))
    if _object_id(first) not in page_ids:
        return False
    mode, left, top, zoom = (_plain_resolver(element) for element in elements[1:])
    if not isinstance(mode, NameObject) or mode != "/XYZ":
        return False
    if not isinstance(left, NullObject) or not isinstance(top, NullObject):
        return False
    if not _is_real_number(zoom):
        return False
    try:
        return float(zoom) == 0.0
    except Exception:
        return False


def _open_action_present(ctx: ChildContext, root) -> bool:
    """True when the catalog /OpenAction is present and not admitted."""
    if "/OpenAction" not in root:
        return False
    raw = root.raw_get("/OpenAction")
    if isinstance(raw, NullObject):
        return False
    return not _open_action_destination_admitted(ctx, root)


def stage_s5_03(ctx: ChildContext) -> dict:
    ctx.at("S5.03", "DOCUMENT_STATE_READ")
    limits = ctx.limits
    trailer = ctx.reader.trailer
    root = _plain_get(trailer, "/Root") if "/Root" in trailer else None
    if _absent_or_null(root) or not _is_plain_dict(root):
        raise _cfail(STATUS_DOCUMENT_STATE, "CATALOG_MALFORMED", None, "S5.03")
    count = len(root)
    if count > limits["inspection_max_catalog_keys"]:
        raise _cfail(STATUS_PDF_INSPECTION_FAILED, REASON_INSPECTION_LIMIT, "CATALOG_KEYS", "S5.03",
                     count=count, limit=limits["inspection_max_catalog_keys"])
    for key, reason in CATALOG_DENIED_KEYS_V1:
        if key == "/OpenAction":
            if _open_action_present(ctx, root):
                raise _cfail(STATUS_DOCUMENT_STATE, reason, None, "S5.03")
        elif _present_non_null(root, key):
            raise _cfail(STATUS_DOCUMENT_STATE, reason, None, "S5.03")
    info_keys = None
    if "/Info" in trailer:
        info = _plain_get(trailer, "/Info")
        if _is_plain_dict(info):
            info_count = len(info)
            if info_count > limits["inspection_max_info_keys"]:
                raise _cfail(STATUS_PDF_INSPECTION_FAILED, REASON_INSPECTION_LIMIT, "INFO_KEYS", "S5.03",
                             count=info_count, limit=limits["inspection_max_info_keys"])
            info_keys = [_name_text(key) for key in list(info.keys())]
    return {
        "catalog_keys": [_name_text(key) for key in list(root.keys())],
        "info_keys": info_keys,
        "metadata_present": 1 if _present_non_null(root, "/Metadata") else 0,
    }


# S6 PDF PAGE STRUCTURE --------------------------------------------------------------

STATUS_PAGEBOX = "RENDER_PAGEBOX_MISMATCH"
STATUS_COORDINATE = "RENDER_COORDINATE_SPACE_UNVERIFIED"
PAGE_TREE_DEPTH_MAX = 64


class _BoxMalformed(Exception):
    def __init__(self, detail=None) -> None:
        super().__init__(detail)
        self.detail = detail


def inherited_value(page, key: str):
    """MEDIABOX_RESOLUTION_V1 walk: (present, raw value) from the page
    dictionary, else the nearest ancestor on the /Parent chain."""
    node = page
    seen = set()
    for _ in range(PAGE_TREE_DEPTH_MAX + 1):
        if not isinstance(node, DictionaryObject):
            raise _BoxMalformed()
        if key in node:
            return True, node.raw_get(key)
        if "/Parent" not in node:
            return False, None
        parent_raw = node.raw_get("/Parent")
        if isinstance(parent_raw, IndirectObject):
            identity = _object_id(parent_raw)
            if identity in seen:
                raise _BoxMalformed()
            seen.add(identity)
            node = parent_raw.get_object()
        else:
            node = parent_raw
    raise _BoxMalformed()


def rect_numbers(raw, resolver):
    """RECT_NORMALIZATION_V1 input: exactly four normalized numbers, else None."""
    value = resolver(raw)
    if not isinstance(value, ArrayObject) or len(value) != 4:
        return None
    numbers = []
    for element in list(value):
        number = normalize_number(resolver(element))
        if number is None:
            return None
        numbers.append(number)
    return numbers


def _plain_resolver(value):
    return value.get_object() if isinstance(value, IndirectObject) else value


class PageFacts:
    __slots__ = ("index", "width", "height", "x0", "y0", "x1", "y1", "non_text", "chars")

    def __init__(self, index: int) -> None:
        self.index = index
        self.width = None
        self.height = None
        self.x0 = self.y0 = self.x1 = self.y1 = None
        self.non_text = False
        self.chars = []


def _char_record(item) -> dict:
    """The exact LTChar reads of char_source; values stay raw here."""
    matrix = item.matrix
    graphicstate = item.graphicstate
    ncs = item.ncs
    return {
        "text": item.get_text(),
        "x0": item.x0,
        "x1": item.x1,
        "y0": item.y0,
        "y1": item.y1,
        "fontname": item.fontname,
        "size": item.size,
        "matrix": tuple(matrix) if isinstance(matrix, (list, tuple)) else None,
        "ncolor": graphicstate.ncolor,
        "ncs": ncs.name if ncs is not None else None,
    }


def interpret_page(resource_manager, miner_page) -> tuple:
    """S6.09 PDFPageAggregator(laparams=None) result flattened depth-first:
    (char records in emission order, non-text content present)."""
    device = PDFPageAggregator(resource_manager, laparams=None)
    interpreter = PDFPageInterpreter(resource_manager, device)
    interpreter.process_page(miner_page)
    layout = device.get_result()
    chars = []
    non_text = False
    pending = [iter(layout)]
    while pending:
        try:
            item = next(pending[-1])
        except StopIteration:
            pending.pop()
            continue
        if isinstance(item, LTChar):
            chars.append(_char_record(item))
        elif isinstance(item, LTFigure):
            pending.append(iter(item))
        elif isinstance(item, (LTImage, LTCurve)):
            non_text = True
    return chars, non_text


def text_geometry_violation(chars: list):
    """STACK_TEXT_GEOMETRY: index of the first deciding character or None."""
    for position, char in enumerate(chars):
        matrix = char["matrix"]
        if matrix is None or len(matrix) != 6 or not all(_is_real_number(v) for v in matrix):
            continue
        floats = []
        for value in matrix:
            try:
                floats.append(float(value))
            except Exception:
                floats.append(float("nan"))
        if not math.isfinite(floats[1]) or not math.isfinite(floats[2]):
            return position
        if quantize(floats[1]) != 0 or quantize(floats[2]) != 0:
            continue
        box = []
        for key in ("x0", "x1", "y0", "y1"):
            value = char[key]
            if not _is_real_number(value):
                box = None
                break
            try:
                box.append(float(value))
            except Exception:
                box.append(float("nan"))
        if box is None:
            continue
        if not all(math.isfinite(v) for v in box + floats):
            return position
        x0, x1, y0, y1 = box
        if x1 < x0 or y1 < y0:
            return position
        if _abs_diff(x0, floats[4]) > TOLERANCE_001:
            return position
        with localcontext() as context:
            context.prec = 100
            f = Decimal(floats[5])
            if f < Decimal(y0) - TOLERANCE_001 or f > Decimal(y1) + TOLERANCE_001:
                return position
    return None


def _prescan_evidence(outcome: PreScanOutcome) -> dict:
    evidence = {}
    for key, value in outcome.evidence.items():
        if key == "object_id":
            value = _object_id_text(value)
        evidence[key] = value
    return evidence


def stage_s6(ctx: ChildContext) -> dict:
    limits = ctx.limits
    ctx.at("S6.01", "PAGE_ENUMERATION")
    pages = list(ctx.reader.pages)
    miner_pages = list(PDFPage.create_pages(ctx.document))
    if len(pages) != len(miner_pages):
        raise _cfail(STATUS_COORDINATE, "STACK_PAGE_COUNT", None, "S6.01")
    ctx.at("S6.01a", None)
    if len(pages) > limits["inspection_max_pages"]:
        raise _cfail(STATUS_PDF_INSPECTION_FAILED, REASON_INSPECTION_LIMIT, "PAGE_COUNT", "S6.01a",
                     count=len(pages), limit=limits["inspection_max_pages"])
    ctx.pages = pages
    ctx.miner_pages = miner_pages

    ctx.at("S6.01b", None)
    try:
        ctx.prescan = run_pre_scan(ctx.pdf_bytes, ctx.reader, ctx.document, limits)
    except PreScanOutcome as outcome:
        raise ChildFail(outcome.status, outcome.reason, outcome.detail,
                        dict({"slot": "S6.01b"}, **_prescan_evidence(outcome))) from None

    resource_manager = None
    records = []
    for index, (page, miner_page) in enumerate(zip(pages, miner_pages)):
        facts = PageFacts(index)

        ctx.at("S6.02", "PAGE_FACTS", index)
        rotate_error = None
        try:
            present, raw = inherited_value(page, "/Rotate")
            rotation = normalize_number(_plain_resolver(raw)) if present else 0.0
            if rotation != 0:
                raise _cfail("RENDER_PAGE_ROTATION_DENIED", None, None, "S6.02", page_index=index)
        except _BoxMalformed as error:
            rotate_error = error

        ctx.at("S6.03", "PAGE_FACTS", index)
        if rotate_error is not None:
            raise _cfail(STATUS_PAGEBOX, "BOX_MALFORMED", None, "S6.03", page_index=index)
        try:
            media_present, media_raw = inherited_value(page, "/MediaBox")
            crop_present, crop_raw = inherited_value(page, "/CropBox")
        except _BoxMalformed:
            raise _cfail(STATUS_PAGEBOX, "BOX_MALFORMED", None, "S6.03", page_index=index) from None
        if not media_present:
            raise _cfail(STATUS_PAGEBOX, "BOX_MALFORMED", "MEDIABOX_ABSENT", "S6.03", page_index=index)
        media = rect_numbers(media_raw, _plain_resolver)
        if media is None:
            raise _cfail(STATUS_PAGEBOX, "BOX_MALFORMED", None, "S6.03", page_index=index)
        crop = None
        if crop_present and not _absent_or_null(_plain_resolver(crop_raw)):
            crop = rect_numbers(crop_raw, _plain_resolver)
            if crop is None:
                raise _cfail(STATUS_PAGEBOX, "BOX_MALFORMED", None, "S6.03", page_index=index)
        for box in (media, crop):
            if box is not None and not (box[0] < box[2] and box[1] < box[3]):
                raise _cfail(STATUS_PAGEBOX, "BOX_REVERSED", None, "S6.03", page_index=index)
        x0, y0, x1, y1 = media
        width = x1 - x0
        height = y1 - y0

        ctx.at("S6.04", "PAGE_FACTS", index)
        if _abs_diff(x0, 0.0) > TOLERANCE_001 or _abs_diff(y0, 0.0) > TOLERANCE_001:
            raise _cfail(STATUS_PAGEBOX, "NONZERO_ORIGIN", None, "S6.04", page_index=index)

        ctx.at("S6.05", "PAGE_FACTS", index)
        if crop is not None and any(_abs_diff(a, b) > TOLERANCE_001 for a, b in zip(crop, media)):
            raise _cfail(STATUS_PAGEBOX, "CROPBOX_DIFFERS", None, "S6.05", page_index=index)

        ctx.at("S6.06", "PAGE_FACTS", index)
        if "/UserUnit" in page:
            unit = normalize_number(_plain_get(page, "/UserUnit"))
            if unit is None or unit != 1:
                raise _cfail(STATUS_PAGEBOX, "USER_UNIT", None, "S6.06", page_index=index)

        ctx.at("S6.06a", "DOCUMENT_STATE_READ", index)
        if _present_non_null(page, "/AA"):
            raise _cfail(STATUS_DOCUMENT_STATE, "PAGE_AA_PRESENT", None, "S6.06a", page_index=index)

        ctx.at("S6.07", "PAGE_FACTS", index)
        if crop is not None:
            crop_width = crop[2] - crop[0]
            crop_height = crop[3] - crop[1]
            if round(crop_width, 2) != round(width, 2) or round(crop_height, 2) != round(height, 2):
                raise _cfail(STATUS_PAGEBOX, "VISIBLE_RECT_SIZE", None, "S6.07", page_index=index)

        ctx.at("S6.08", "PAGE_FACTS", index)
        miner_box = miner_page.mediabox
        miner_numbers = None
        if isinstance(miner_box, (list, tuple)) and len(miner_box) == 4:
            miner_numbers = [normalize_number(resolve1(value)) for value in miner_box]
        if (
            miner_numbers is None
            or any(value is None for value in miner_numbers)
            or any(_abs_diff(a, b) > TOLERANCE_001 for a, b in zip(miner_numbers, media))
            or _abs_diff(miner_numbers[2] - miner_numbers[0], width) > TOLERANCE_001
            or _abs_diff(miner_numbers[3] - miner_numbers[1], height) > TOLERANCE_001
            or miner_page.rotate != 0
        ):
            raise _cfail(STATUS_COORDINATE, "STACK_PAGE_SIZE", None, "S6.08", page_index=index)

        ctx.at("S6.09", "CHAR_EXTRACTION", index)
        if resource_manager is None:
            resource_manager = PDFResourceManager()
        chars, non_text = interpret_page(resource_manager, miner_page)
        if text_geometry_violation(chars) is not None:
            raise _cfail(STATUS_COORDINATE, "STACK_TEXT_GEOMETRY", None, "S6.09", page_index=index)

        ctx.at("S6.09a", "CHAR_EXTRACTION", index)
        if len(chars) > limits["inspection_max_chars_per_page"]:
            raise _cfail(STATUS_PDF_INSPECTION_FAILED, REASON_INSPECTION_LIMIT, "CHAR_COUNT", "S6.09a",
                         page_index=index, count=len(chars), limit=limits["inspection_max_chars_per_page"])

        facts.width, facts.height = width, height
        facts.x0, facts.y0, facts.x1, facts.y1 = x0, y0, x1, y1
        facts.non_text = non_text
        facts.chars = chars
        records.append(facts)

    ctx.at("S6.10", None)
    first = records[0]
    if round(first.width, 2) != 612.0 or round(first.height, 2) != 792.0:
        raise _cfail("RENDER_PAGE_SIZE_UNSUPPORTED", None, None, "S6.10", page_index=0)
    ctx.page_facts = records
    return {
        "page_count": len(records),
        "pages": [
            {
                "index": facts.index,
                "width_pt": facts.width,
                "height_pt": facts.height,
                "width_q": quantize(facts.width),
                "height_q": quantize(facts.height),
                "rotation": 0,
                "non_text_content": 1 if facts.non_text else 0,
            }
            for facts in records
        ],
        "prescan_font_entries": sum(graph.font_entries for graph in ctx.prescan.pages),
    }

# S7 RENDERED TEXT EVIDENCE ------------------------------------------------------------

S7_UNOBSERVABLE_ORDER_V1 = (
    "TRACKER_FAILURE", "STACK_UNBALANCED", "MISSING_RESOURCE", "BAD_OPERAND", "FORM_LIMIT",
    "ANNOTATION_APPEARANCE", "PATTERN_FILL", "VISUAL_STATE_UNPROVABLE", "COLOR_UNOBSERVABLE",
    "NO_CORRESPONDENCE",
)
FILL_SPACES_V1 = ("DeviceGray", "DeviceRGB")
SHOW_OPERATORS = (b"Tj", b"TJ", b"'", b'"')


class TextState:
    """The PAGE_CONTENT_TRAVERSAL_V1 state unit saved and restored by q/Q."""

    __slots__ = (
        "tr", "ca", "stroke_ca", "smask", "blend", "alpha_is_shape", "transfer", "group",
        "fill_is_pattern", "fill_cs", "fill_color_state", "font_size", "hscale", "font_from_gs",
    )

    def __init__(self) -> None:
        self.tr = 0
        self.ca = 1.0
        self.stroke_ca = 1.0
        self.smask = False
        self.blend = False
        self.alpha_is_shape = False
        self.transfer = False
        self.group = False
        self.fill_is_pattern = False
        self.fill_cs = "DeviceGray"
        self.fill_color_state = "PAGE_INITIAL"
        self.font_size = None
        self.hscale = 100.0
        self.font_from_gs = False

    def copy(self) -> "TextState":
        clone = TextState()
        for name in self.__slots__:
            setattr(clone, name, getattr(self, name))
        return clone

    def visual_flag(self) -> bool:
        return (self.smask or self.blend or self.alpha_is_shape or self.transfer or self.group
                or self.font_from_gs)


class PageTraversal:
    __slots__ = ("issues", "shows", "form_scopes", "mirrored", "operations", "annotation_appearance")

    def __init__(self) -> None:
        self.issues = {}
        self.shows = []
        self.form_scopes = []
        self.mirrored = False
        self.operations = 0
        self.annotation_appearance = False

    def issue(self, reason: str, **evidence) -> None:
        self.issues.setdefault(reason, evidence)


def _string_byte_length(value) -> int:
    if isinstance(value, ByteStringObject):
        return len(value)
    if isinstance(value, TextStringObject):
        return len(value.original_bytes)
    if isinstance(value, (bytes, bytearray)):
        return len(value)
    if isinstance(value, str):
        return len(value)
    return 0


def _show_non_empty(operator: bytes, operands) -> bool:
    if operator == b"TJ":
        array = operands[0] if operands else None
        if not isinstance(array, (list, tuple)):
            return False
        return any(
            isinstance(item, (str, bytes, bytearray)) and _string_byte_length(item) > 0 for item in array
        )
    if not operands:
        return False
    return _string_byte_length(operands[-1]) > 0


def _all_numeric(operands) -> bool:
    return bool(operands) and all(normalize_number(value) is not None for value in operands)


class _Traversal:
    def __init__(self, ctx: ChildContext, page_index: int, forms: dict, bound: int) -> None:
        self.ctx = ctx
        self.page_index = page_index
        self.forms = forms
        self.bound = bound
        self.result = PageTraversal()
        self.executed_scopes = set()

    def category(self, resources, name: str):
        if resources is None:
            return None
        present, value = self.ctx.lookup(resources, name)
        return value if present and _is_plain_dict(value) else None

    def run(self, operations, resources, state: TextState, depth: int, active: frozenset, path: list):
        result = self.result
        saved = []
        for operands, operator in operations:
            result.operations += 1
            if result.operations > self.bound:
                result.issue("FORM_LIMIT", page_index=self.page_index)
                return state
            if operator == b"q":
                saved.append(state.copy())
            elif operator == b"Q":
                if not saved:
                    result.issue("STACK_UNBALANCED", page_index=self.page_index)
                else:
                    state = saved.pop()
            elif operator == b"Tr":
                value = operands[0] if len(operands) == 1 else None
                if not _is_int(value) or not 0 <= value <= 7:
                    result.issue("BAD_OPERAND", page_index=self.page_index)
                else:
                    state.tr = int(value)
            elif operator == b"gs":
                self.graphics_state(operands, resources, state)
            elif operator == b"g":
                state.fill_cs, state.fill_color_state, state.fill_is_pattern = "DeviceGray", "SET", False
            elif operator == b"rg":
                state.fill_cs, state.fill_color_state, state.fill_is_pattern = "DeviceRGB", "SET", False
            elif operator == b"k":
                state.fill_cs, state.fill_color_state, state.fill_is_pattern = "DeviceCMYK", "SET", False
            elif operator == b"cs":
                self.color_space(operands, resources, state)
            elif operator in (b"sc", b"scn"):
                if operands and isinstance(operands[-1], NameObject):
                    if operator == b"scn":
                        state.fill_is_pattern = True
                elif _all_numeric(operands):
                    state.fill_color_state = "SET"
                    state.fill_is_pattern = False
            elif operator == b"Tf":
                size = normalize_number(operands[1]) if len(operands) == 2 else None
                if size is None:
                    result.issue("BAD_OPERAND", page_index=self.page_index)
                else:
                    state.font_size = size
            elif operator == b"Tz":
                scale = normalize_number(operands[0]) if len(operands) == 1 else None
                if scale is None:
                    result.issue("BAD_OPERAND", page_index=self.page_index)
                else:
                    state.hscale = scale
            elif operator in SHOW_OPERATORS:
                if _show_non_empty(operator, operands):
                    self.show(state)
            elif operator == b"Do":
                self.invoke(operands, resources, state, depth, active, path)
        if saved:
            result.issue("STACK_UNBALANCED", page_index=self.page_index)
        return state

    def graphics_state(self, operands, resources, state: TextState) -> None:
        result = self.result
        table = self.category(resources, "/ExtGState")
        name = operands[0] if operands else None
        if table is None or not isinstance(name, NameObject) or name not in table:
            result.issue("MISSING_RESOURCE", page_index=self.page_index)
            return
        entry = self.ctx.resolve(table.raw_get(name))
        if not _is_plain_dict(entry):
            result.issue("MISSING_RESOURCE", page_index=self.page_index)
            return
        for key in list(entry.keys()):
            value = self.ctx.resolve(entry.raw_get(key))
            if key in ("/ca", "/CA"):
                number = normalize_number(value)
                if number is None or not 0.0 <= number <= 1.0:
                    result.issue("BAD_OPERAND", page_index=self.page_index)
                elif key == "/ca":
                    state.ca = number
                else:
                    state.stroke_ca = number
            elif key == "/SMask":
                state.smask = value != "/None"
            elif key == "/BM":
                mode = value
                if isinstance(value, ArrayObject):
                    mode = self.ctx.resolve(value[0]) if len(value) else None
                state.blend = mode not in ("/Normal", "/Compatible")
            elif key == "/AIS":
                state.alpha_is_shape = isinstance(value, BooleanObject) and bool(value)
            elif key in ("/TR", "/TR2"):
                state.transfer = value not in ("/Identity", "/Default")
            elif key == "/Font":
                state.font_from_gs = True

    def color_space(self, operands, resources, state: TextState) -> None:
        name = operands[0] if operands else None
        if not isinstance(name, NameObject):
            self.result.issue("BAD_OPERAND", page_index=self.page_index)
            return
        if name in ("/DeviceGray", "/DeviceRGB"):
            state.fill_cs = str(name)[1:]
        elif name == "/Pattern":
            state.fill_cs = "OTHER"
            state.fill_is_pattern = True
        elif name == "/DeviceCMYK":
            state.fill_cs = "OTHER"
        else:
            table = self.category(resources, "/ColorSpace")
            if table is None or name not in table:
                self.result.issue("MISSING_RESOURCE", page_index=self.page_index)
                return
            value = self.ctx.resolve(table.raw_get(name))
            head = value
            if isinstance(value, ArrayObject):
                head = self.ctx.resolve(value[0]) if len(value) else None
            if head == "/Pattern":
                state.fill_is_pattern = True
            state.fill_cs = "OTHER"
        state.fill_color_state = "INITIAL_OF_CS"

    def show(self, state: TextState) -> None:
        result = self.result
        if state.font_size is None:
            result.issue("BAD_OPERAND", page_index=self.page_index)
        elif state.font_size <= 0 or state.hscale <= 0:
            result.mirrored = True
        result.shows.append(state.copy())

    def invoke(self, operands, resources, state: TextState, depth: int, active: frozenset, path: list) -> None:
        result = self.result
        table = self.category(resources, "/XObject")
        name = operands[0] if operands else None
        if table is None or not isinstance(name, NameObject) or name not in table:
            result.issue("MISSING_RESOURCE", page_index=self.page_index)
            return
        entry_raw = table.raw_get(name)
        target = self.ctx.resolve(entry_raw)
        if not isinstance(target, StreamObject):
            result.issue("FORM_LIMIT", page_index=self.page_index)
            return
        present, subtype = self.ctx.lookup(target, "/Subtype")
        if present and subtype == "/Image":
            return
        if not present or subtype != "/Form" or not isinstance(entry_raw, IndirectObject):
            result.issue("FORM_LIMIT", page_index=self.page_index)
            return
        form_id = _object_id(entry_raw)
        record = self.forms.get(form_id)
        if depth + 1 > FORM_DEPTH_MAX or form_id in active:
            result.issue("FORM_LIMIT", page_index=self.page_index, object_id=_object_id_text(form_id))
            return
        if record is None or record.operations is None:
            result.issue("TRACKER_FAILURE", page_index=self.page_index, object_id=_object_id_text(form_id))
            return
        form_state = state.copy()
        present, group = self.ctx.lookup(target, "/Group")
        if present and _is_plain_dict(group):
            group_present, group_subtype = self.ctx.lookup(group, "/S")
            if group_present and group_subtype == "/Transparency":
                form_state.group = True
        form_path = path + [str(name)[1:]]
        if record.own_resources is not None:
            form_resources = record.own_resources
            if form_id not in self.executed_scopes:
                self.executed_scopes.add(form_id)
                result.form_scopes.append((form_id, form_path))
        else:
            form_resources = resources
        self.run(record.operations, form_resources, form_state, depth + 1, active | {form_id}, form_path)


def traverse_page(ctx: ChildContext, page_index: int, page) -> PageTraversal:
    """PAGE_CONTENT_TRAVERSAL_V1 over the pre-scanned parsed operations of the
    page (the same operations FORM_CALL_GRAPH_V1 counted at S6.01b)."""
    prescan = ctx.prescan
    traversal = _Traversal(ctx, page_index, prescan.forms, ctx.limits["inspection_max_traversal_operations"])
    try:
        traversal.run(prescan.page_operations[page_index], prescan.page_resources[page_index], TextState(), 0,
                      frozenset(), [])
        present, annots = ctx.lookup(page, "/Annots")
        if present and isinstance(annots, ArrayObject) and len(annots) <= ctx.limits["inspection_max_annots_array_length"]:
            for element in list(annots):
                annotation = ctx.resolve(element)
                if isinstance(annotation, DictionaryObject) and "/AP" in annotation:
                    traversal.result.annotation_appearance = True
                    break
    except (ChildFail, MemoryError):
        raise
    except Exception as exc:
        traversal.result.issue("TRACKER_FAILURE", page_index=page_index, **_exception_evidence(exc))
    return traversal.result


def normalize_ncolor(char: dict, show_spaces: set, all_initial: bool, all_set: bool):
    """NCOLOR_NORMALIZATION_V1: (color tuple, None) or (None, detail)."""
    space = char["ncs"]
    ncolor = char["ncolor"]
    if space not in FILL_SPACES_V1:
        return None, "CS_UNSUPPORTED"
    if space not in show_spaces:
        return None, "NCOLOR_INCONSISTENT"
    if ncolor is None:
        if space == "DeviceGray" and all_initial:
            return (0,), None
        return None, "NCOLOR_MISSING"
    if not all_set:
        return None, "NCOLOR_INCONSISTENT"
    if space == "DeviceGray":
        if isinstance(ncolor, (list, tuple)):
            if len(ncolor) != 1:
                return None, "NCOLOR_INCONSISTENT"
            ncolor = ncolor[0]
        value = normalize_number(ncolor)
        if value is None or not 0.0 <= value <= 1.0:
            return None, "NCOLOR_INCONSISTENT"
        return (value,), None
    if not isinstance(ncolor, (list, tuple)) or len(ncolor) != 3:
        return None, "NCOLOR_INCONSISTENT"
    values = tuple(normalize_number(item) for item in ncolor)
    if any(value is None or not 0.0 <= value <= 1.0 for value in values):
        return None, "NCOLOR_INCONSISTENT"
    return values, None


def _char_unobservable(char: dict) -> bool:
    text = char["text"]
    if not isinstance(text, str) or text == "" or any(0xD800 <= ord(ch) <= 0xDFFF for ch in text):
        return True
    matrix = char["matrix"]
    if matrix is None or len(matrix) != 6 or any(normalize_number(value) is None for value in matrix):
        return True
    return any(normalize_number(char[key]) is None for key in ("x0", "x1", "y0", "y1", "size"))


def _non_horizontal(char: dict) -> bool:
    matrix = [normalize_number(value) for value in char["matrix"]]
    return not (
        quantize(matrix[1]) == 0
        and quantize(matrix[2]) == 0
        and quantize(matrix[0]) > 0
        and quantize(matrix[3]) > 0
        and quantize(normalize_number(char["size"])) > 0
    )


def _near_white(color: tuple) -> bool:
    channels = []
    for component in color:
        with localcontext() as context:
            context.prec = 100
            channels.append(int((Decimal(component) * 255).to_integral_value(rounding=ROUND_HALF_EVEN)))
    if len(channels) == 1:
        channels = channels * 3
    return all(channel >= 240 for channel in channels)


def build_page_lines(chars: list, height: float, tolerance_q: int, gap_q: int) -> tuple:
    """LINE_GROUP_V1, SPACE_INSERT_V1 and SPAN_V1 over one page's characters
    (each carrying its normalized color); returns (line evidence, line
    texts, words)."""
    groups = []
    current = None
    for char in chars:
        baseline = quantize(normalize_number(char["matrix"][5]))
        if current is None or abs(baseline - current[0]) > tolerance_q:
            current = (baseline, [])
            groups.append(current)
        current[1].append(char)
    lines = []
    texts = []
    words = []
    for _, members in groups:
        spans = []
        span = None
        span_key = None
        previous = None
        word = None
        bbox = None
        line_text = []
        for char in members:
            x0 = normalize_number(char["x0"])
            x1 = normalize_number(char["x1"])
            box = [x0, height - normalize_number(char["y1"]), x1, height - normalize_number(char["y0"])]
            bbox = box if bbox is None else [min(bbox[0], box[0]), min(bbox[1], box[1]),
                                             max(bbox[2], box[2]), max(bbox[3], box[3])]
            separator = is_separator_text(char["text"])
            boundary = (
                previous is not None
                and not previous["separator"]
                and not separator
                and quantize(x0) - previous["x1_q"] > gap_q
            )
            fontname = char["fontname"]
            key = (fontname if isinstance(fontname, str) else None, quantize(normalize_number(char["size"])),
                   char["color"])
            if span is None or key != span_key:
                span = {
                    "font": fail_evidence_string(key[0]) if key[0] is not None else None,
                    "size_q": key[1],
                    "color": list(key[2]),
                    "text": [],
                    "gap_before": bool(boundary and spans),
                }
                span_key = key
                spans.append(span)
            elif boundary:
                span["text"].append(" ")
            if boundary:
                line_text.append(" ")
            span["text"].append(char["text"])
            line_text.append(char["text"])
            counted = is_counted_text(char["text"])
            if counted:
                if word is not None and previous is not None and previous["counted"] and not boundary:
                    word["text"].append(char["text"])
                    word["box"] = [min(word["box"][0], box[0]), min(word["box"][1], box[1]),
                                   max(word["box"][2], box[2]), max(word["box"][3], box[3])]
                else:
                    word = {"text": [char["text"]], "box": list(box)}
                    words.append(word)
            else:
                word = None
            previous = {"separator": separator, "x1_q": quantize(x1), "counted": counted}
        for item in spans:
            item["text"] = _chunks("".join(item["text"]))
        lines.append({"bbox": bbox, "spans": spans})
        texts.append("".join(line_text))
    page_words = [
        {
            "text": "".join(item["text"]),
            "center": ((item["box"][0] + item["box"][2]) / 2, (item["box"][1] + item["box"][3]) / 2),
        }
        for item in words
    ]
    return lines, texts, page_words


def stage_s7(ctx: ChildContext) -> dict:
    limits = ctx.limits
    ctx.at("S7.00", "TRACKER_FAILURE")
    for index, page in enumerate(ctx.pages):
        ctx.page_index = index
        present, contents = ctx.lookup(page, "/Contents")
        if present and isinstance(contents, ArrayObject) and len(contents) > limits["inspection_max_content_streams_per_page"]:
            raise _cfail(STATUS_PDF_INSPECTION_FAILED, REASON_INSPECTION_LIMIT, "CONTENT_STREAMS", "S7.00",
                         page_index=index, count=len(contents), limit=limits["inspection_max_content_streams_per_page"])

    ctx.at("S7.01", "TRACKER_FAILURE")
    traversals = []
    for index, page in enumerate(ctx.pages):
        ctx.page_index = index
        traversal = traverse_page(ctx, index, page)
        if traversal.annotation_appearance:
            traversal.issue("ANNOTATION_APPEARANCE", page_index=index)
        for show in traversal.shows:
            if show.fill_is_pattern:
                traversal.issue("PATTERN_FILL", page_index=index)
            if show.visual_flag():
                traversal.issue("VISUAL_STATE_UNPROVABLE", page_index=index)
        traversals.append(traversal)
    ctx.traversals = traversals

    ctx.at("S7.01", "CHAR_EXTRACTION")
    colors = []
    color_issue = []
    for facts, traversal in zip(ctx.page_facts, traversals):
        detail = None
        for show in traversal.shows:
            if show.fill_cs not in FILL_SPACES_V1:
                detail = "CS_UNSUPPORTED"
                break
            if show.fill_color_state == "INITIAL_OF_CS":
                detail = "CS_WITHOUT_COLOR"
                break
        show_spaces = {show.fill_cs for show in traversal.shows}
        all_initial = all(show.fill_color_state == "PAGE_INITIAL" for show in traversal.shows)
        all_set = all(show.fill_color_state == "SET" for show in traversal.shows)
        page_colors = []
        for char in facts.chars:
            color, char_detail = normalize_ncolor(char, show_spaces, all_initial, all_set)
            page_colors.append(color)
            if detail is None and char_detail is not None:
                detail = char_detail
        colors.append(page_colors)
        color_issue.append(detail)
        if bool(facts.chars) != bool(traversal.shows):
            traversal.issue("NO_CORRESPONDENCE", page_index=facts.index)

    for reason in S7_UNOBSERVABLE_ORDER_V1:
        for index, traversal in enumerate(traversals):
            if reason == "COLOR_UNOBSERVABLE":
                if color_issue[index] is not None:
                    raise _cfail(STATUS_TEXT_UNOBSERVABLE, "COLOR_UNOBSERVABLE", color_issue[index], "S7.01",
                                 page_index=index)
                continue
            evidence = traversal.issues.get(reason)
            if evidence is not None:
                raise _cfail(STATUS_TEXT_UNOBSERVABLE, reason, None, "S7.01", **evidence)

    ctx.at("S7.02", "CHAR_EXTRACTION")
    for reason, test in (
        ("RENDER_MODE_INVISIBLE", lambda s: s.tr in (3, 7)),
        ("ZERO_OPACITY", lambda s: (s.tr in (0, 4) and s.ca == 0) or (s.tr in (1, 5) and s.stroke_ca == 0)
         or (s.tr in (2, 6) and s.ca == 0 and s.stroke_ca == 0)),
    ):
        for index, traversal in enumerate(traversals):
            if any(test(show) for show in traversal.shows):
                raise _cfail("RENDER_HIDDEN_TEXT_DETECTED", reason, None, "S7.02", page_index=index)

    ctx.at("S7.03", "CHAR_EXTRACTION")
    for index, traversal in enumerate(traversals):
        if any(show.tr in (1, 4, 5, 6) for show in traversal.shows):
            raise _cfail("RENDER_TEXT_POLICY_SUSPECT", "RENDER_MODE_NOT_FILL_ONLY", None, "S7.03", page_index=index)
    for index, traversal in enumerate(traversals):
        if any(show.tr in (0, 2) and 10 * _dec(show.ca) < 1 for show in traversal.shows):
            raise _cfail("RENDER_TEXT_POLICY_SUSPECT", "LOW_OPACITY", None, "S7.03", page_index=index)
    for facts in ctx.page_facts:
        for char in facts.chars:
            size = normalize_number(char["size"])
            if is_counted_text(char["text"]) and size is not None and _dec(size) < SMALL_TEXT_SIZE:
                raise _cfail("RENDER_TEXT_POLICY_SUSPECT", "SMALL_TEXT", None, "S7.03", page_index=facts.index)
    for facts, page_colors in zip(ctx.page_facts, colors):
        for char, color in zip(facts.chars, page_colors):
            if is_counted_text(char["text"]) and color is not None and _near_white(color):
                raise _cfail("RENDER_TEXT_POLICY_SUSPECT", "NEAR_WHITE", None, "S7.03", page_index=facts.index)

    ctx.at("S7.04", "CHAR_EXTRACTION")
    for facts in ctx.page_facts:
        if any(_char_unobservable(char) for char in facts.chars):
            raise _cfail("RENDER_ATTRIBUTION_INCOMPLETE", "CHAR_UNOBSERVABLE", None, "S7.04", page_index=facts.index)
    for facts, traversal in zip(ctx.page_facts, traversals):
        if traversal.mirrored or any(_non_horizontal(char) for char in facts.chars):
            raise _cfail("RENDER_ATTRIBUTION_INCOMPLETE", "NON_HORIZONTAL_TEXT", None, "S7.04",
                         page_index=facts.index)
    pages = []
    ctx.page_words = []
    for facts, page_colors in zip(ctx.page_facts, colors):
        chars = [dict(char, color=color) for char, color in zip(facts.chars, page_colors)]
        lines, texts, words = build_page_lines(chars, facts.height, ctx.line_tolerance_q, ctx.word_gap_q)
        if any(not tokenize(text) for text in texts):
            raise _cfail("RENDER_ATTRIBUTION_INCOMPLETE", "EMPTY_TOKEN_LINE", None, "S7.04", page_index=facts.index)
        pages.append({"index": facts.index, "lines": lines})
        ctx.page_words.append(words)
    return {"pages": pages}

# S9 FONTS (S9.00a to S9.02) ------------------------------------------------------------

STATUS_FONT_STRUCTURE = "RENDER_FONT_SUBSTITUTION_UNAPPROVED"
STRUCTURED_SUBTYPES_V1 = ("/Type1", "/MMType1", "/TrueType", "/Type0")
EMBED_KEYS_V1 = ("/FontFile", "/FontFile2", "/FontFile3")


class FontEntry:
    __slots__ = ("page_index", "source", "form_path", "resource_name", "object_id", "font", "subtype",
                 "descendant", "descriptor")

    def __init__(self, page_index, source, form_path, resource_name, object_id, font, subtype) -> None:
        self.page_index = page_index
        self.source = source
        self.form_path = form_path
        self.resource_name = resource_name
        self.object_id = object_id
        self.font = font
        self.subtype = subtype
        self.descendant = None
        self.descriptor = None

    def where(self) -> dict:
        return {
            "page_index": self.page_index,
            "source": self.source,
            "form_path": [fail_evidence_string(name) for name in self.form_path],
            "resource_name": _name_text(self.resource_name),
            "object_id": _object_id_text(self.object_id),
        }


def _structure_fail(detail: str, slot: str, **evidence) -> ChildFail:
    return _cfail(STATUS_FONT_STRUCTURE, "FONT_STRUCTURE_MALFORMED", detail, slot, **evidence)


def font_inventory(ctx: ChildContext) -> list:
    """FONT_SOURCES_V1 inventory with FONT_STRUCTURE_V1 pass A (S9.00): per
    page the PAGE scope, then the OWN form scopes in first-execution order,
    each scope's fonts by ascending resource name."""
    entries = []
    for page_index, page in enumerate(ctx.pages):
        ctx.page_index = page_index
        seen = set()
        scopes = []
        present, resources = ctx.lookup(page, "/Resources")
        if present:
            if _absent_or_null(resources) or not _is_plain_dict(resources):
                raise _structure_fail("RESOURCES_MALFORMED", "S9.00", page_index=page_index, source="PAGE",
                                      form_path=[])
            scopes.append(("PAGE", [], resources))
        traversal = ctx.traversals[page_index]
        for form_id, form_path in traversal.form_scopes:
            scopes.append(("FORM", form_path, ctx.prescan.forms[form_id].own_resources))
        for source, form_path, scope_resources in scopes:
            path_evidence = [fail_evidence_string(name) for name in form_path]
            font_present, fonts = ctx.lookup(scope_resources, "/Font")
            if not font_present:
                continue
            if _absent_or_null(fonts) or not _is_plain_dict(fonts):
                raise _structure_fail("FONT_DICT_MALFORMED", "S9.00", page_index=page_index, source=source,
                                      form_path=path_evidence)
            for name in sorted(list(fonts.keys()), key=_name_order_key):
                entry_raw = fonts.raw_get(name)
                object_id = _object_id(entry_raw) if isinstance(entry_raw, IndirectObject) else None
                if object_id is not None and object_id in seen:
                    continue
                where = {"page_index": page_index, "source": source, "form_path": path_evidence,
                         "resource_name": _name_text(name), "object_id": _object_id_text(object_id)}
                font = ctx.resolve(entry_raw)
                if _absent_or_null(font):
                    raise _structure_fail("FONT_REF_UNRESOLVED", "S9.00", **where)
                if not isinstance(font, DictionaryObject):
                    raise _structure_fail("FONT_ENTRY_NOT_DICT", "S9.00", **where)
                subtype_present, subtype = ctx.lookup(font, "/Subtype")
                if not subtype_present or not isinstance(subtype, NameObject):
                    raise _structure_fail("SUBTYPE_INVALID", "S9.00", **where)
                if object_id is not None:
                    seen.add(object_id)
                entries.append(FontEntry(page_index, source, list(form_path), name, object_id, font, str(subtype)))
    return entries


def _name_value(ctx: ChildContext, dictionary, key: str):
    if dictionary is None:
        return None
    present, value = ctx.lookup(dictionary, key)
    return _name_text(value) if present and isinstance(value, NameObject) else None


def _raw_stream_length(ctx: ChildContext, raw) -> int:
    """Raw (encoded) length through RAW_STREAM_BYTES_V1's public pdfminer.six
    path; nothing is decoded."""
    if not isinstance(raw, IndirectObject):
        return 0
    stream = ctx.document.getobj(int(raw.idnum))
    if not isinstance(stream, PDFStream):
        return 0
    data = stream.get_rawdata()
    return len(data) if isinstance(data, bytes) else 0


def stage_s9(ctx: ChildContext) -> dict:
    ctx.at("S9.00", "FONT_TRAVERSAL")
    entries = font_inventory(ctx)

    ctx.at("S9.01", "FONT_TRAVERSAL")
    for entry in entries:
        if entry.subtype == "/Type3":
            raise _cfail("RENDER_FONT_TYPE3_DENIED", None, None, "S9.01", **entry.where())

    ctx.at("S9.01a", "FONT_TRAVERSAL")
    for entry in entries:
        ctx.page_index = entry.page_index
        if entry.subtype not in STRUCTURED_SUBTYPES_V1:
            continue
        target = entry.font
        if entry.subtype == "/Type0":
            present, descendants = ctx.lookup(entry.font, "/DescendantFonts")
            if not present or not isinstance(descendants, ArrayObject) or len(descendants) != 1:
                raise _structure_fail("DESCENDANTS_INVALID", "S9.01a", **entry.where())
            descendant = ctx.resolve(list(descendants)[0])
            if _absent_or_null(descendant) or not isinstance(descendant, DictionaryObject):
                raise _structure_fail("DESCENDANT_ENTRY_INVALID", "S9.01a", **entry.where())
            entry.descendant = descendant
            target = descendant
        present, descriptor = ctx.lookup(target, "/FontDescriptor")
        if present:
            if _absent_or_null(descriptor) or not isinstance(descriptor, DictionaryObject):
                raise _structure_fail("DESCRIPTOR_MALFORMED", "S9.01a", **entry.where())
            entry.descriptor = descriptor
            name_present, font_name = ctx.lookup(descriptor, "/FontName")
            if name_present and not isinstance(font_name, NameObject):
                raise _structure_fail("FONTNAME_MALFORMED", "S9.01a", **entry.where())

    ctx.at("S9.02", "FONT_TRAVERSAL")
    records = []
    for entry in entries:
        ctx.page_index = entry.page_index
        embedded = False
        embed_key = None
        if entry.subtype in STRUCTURED_SUBTYPES_V1:
            descriptor = entry.descriptor
            if descriptor is None:
                raise _cfail("RENDER_FONT_NOT_EMBEDDED", None, None, "S9.02", **entry.where())
            if "/FontName" not in descriptor:
                raise _cfail("RENDER_FONT_NOT_EMBEDDED", "DESCRIPTOR_INCOMPLETE", None, "S9.02", **entry.where())
            for key in EMBED_KEYS_V1:
                if key not in descriptor:
                    continue
                raw = descriptor.raw_get(key)
                stream = ctx.resolve(raw)
                if isinstance(stream, StreamObject) and _raw_stream_length(ctx, raw) > 0:
                    embedded = True
                    embed_key = key[1:]
                    break
            if not embedded:
                raise _cfail("RENDER_FONT_NOT_EMBEDDED", None, None, "S9.02", **entry.where())
        record = entry.where()
        record.update({
            "subtype": _name_text(entry.subtype),
            "basefont": _name_value(ctx, entry.font, "/BaseFont"),
            "descendant_basefont": _name_value(ctx, entry.descendant, "/BaseFont"),
            "descriptor_present": 1 if entry.descriptor is not None else 0,
            "descriptor_fontname": _name_value(ctx, entry.descriptor, "/FontName"),
            "embedded": embedded,
            "embed_key": embed_key,
        })
        records.append(record)
    # S9.00a: a non-failing consistency assertion, carried as evidence only.
    return {
        "font_entries": records,
        "assertion": {
            "prescan_font_entries": sum(graph.font_entries for graph in ctx.prescan.pages),
            "inventory_entries": len(records),
        },
    }


# S10 LINKS (S10.00 to S10.05) ------------------------------------------------------------

STATUS_ANNOTATION = "RENDER_ANNOTATION_UNSUPPORTED"
STATUS_LINK_KIND = "RENDER_LINK_KIND_UNSUPPORTED"
STATUS_LINK_URI = "RENDER_LINK_URI_UNSUPPORTED"
STATUS_LINK_AMBIGUOUS = "RENDER_LINK_ATTRIBUTION_AMBIGUOUS"


class AnnotationRecord:
    __slots__ = ("page_index", "annot_index", "annotation", "rect_ccs", "kind", "uri", "goto_page",
                 "uri_object", "uri_bytes", "words")

    def __init__(self, page_index: int, annot_index: int, annotation, rect_ccs: list) -> None:
        self.page_index = page_index
        self.annot_index = annot_index
        self.annotation = annotation
        self.rect_ccs = rect_ccs
        self.kind = None
        self.uri = None
        self.goto_page = None
        self.uri_object = None
        self.uri_bytes = None
        self.words = []

    def destination(self) -> tuple:
        return (self.kind, self.uri if self.kind == "LINK_URI" else self.goto_page)


def _annotation_rect_ccs(numbers: list, facts: PageFacts) -> list:
    a, b, c, d = numbers
    x0, y0, x1, y1 = min(a, c), min(b, d), max(a, c), max(b, d)
    return [x0 - facts.x0, facts.y1 - y1, x1 - facts.x0, facts.y1 - y0]


def _miner_name(value):
    value = resolve1(value)
    if isinstance(value, PSLiteral):
        name = value.name
        return str(name, "latin-1") if isinstance(name, (bytes, bytearray)) else name
    return None


def _uri_bytes(ctx: ChildContext, record: AnnotationRecord, slot: str) -> bytes:
    """The original bytes of the URI string object, read once; URI_LENGTH is
    judged at that first read, before the ASCII check."""
    if record.uri_bytes is not None:
        return record.uri_bytes
    value = record.uri_object
    if isinstance(value, ByteStringObject):
        data = bytes(value)
    elif isinstance(value, TextStringObject) and hasattr(value, "original_bytes"):
        data = value.original_bytes
    else:
        raise _cfail(STATUS_LINK_URI, "URI_BYTES_UNAVAILABLE", None, slot, page_index=record.page_index)
    limit = ctx.limits["inspection_max_uri_bytes"]
    if len(data) > limit:
        raise _cfail(STATUS_PDF_INSPECTION_FAILED, REASON_INSPECTION_LIMIT, "URI_LENGTH", slot,
                     page_index=record.page_index, count=len(data), limit=limit)
    record.uri_bytes = bytes(data)
    return record.uri_bytes


def _pypdf_uri_object(ctx: ChildContext, annotation):
    present, action = ctx.lookup(annotation, "/A")
    if not present or not _is_plain_dict(action):
        return None
    uri_present, uri = ctx.lookup(action, "/URI")
    return uri if uri_present else None


def _action_precedence(ctx: ChildContext, record: AnnotationRecord, page_numbers: dict) -> None:
    """ACTION_PRECEDENCE_V1 (S10.03)."""
    annotation = record.annotation
    where = {"page_index": record.page_index}

    def kind_fail(reason):
        return _cfail(STATUS_LINK_KIND, reason, None, "S10.03", **where)

    if "/AA" in annotation:
        raise kind_fail("ADDITIONAL_ACTIONS")
    has_dest = "/Dest" in annotation
    has_action = "/A" in annotation
    if has_dest and has_action:
        raise kind_fail("DEST_AND_ACTION")
    if not has_dest and not has_action:
        raise kind_fail("NO_DESTINATION")
    if has_action:
        _, action = ctx.lookup(annotation, "/A")
        if not _is_plain_dict(action):
            raise kind_fail("ACTION_MALFORMED")
        if "/Next" in action:
            raise kind_fail("ACTION_CHAIN")
        s_present, action_type = ctx.lookup(action, "/S")
        if not s_present or not isinstance(action_type, NameObject):
            raise kind_fail("ACTION_MALFORMED")
        if action_type not in ("/URI", "/GoTo"):
            raise kind_fail("ACTION_TYPE_UNSUPPORTED")
        specific = "/URI" if action_type == "/URI" else "/D"
        for key in list(action.keys()):
            if key not in ("/Type", "/S", specific):
                raise kind_fail("ACTION_MALFORMED")
        if "/Type" in action:
            _, type_value = ctx.lookup(action, "/Type")
            if type_value != "/Action":
                raise kind_fail("ACTION_MALFORMED")
        if specific not in action:
            raise kind_fail("ACTION_MALFORMED")
        _, value = ctx.lookup(action, specific)
        if action_type == "/URI":
            if not isinstance(value, (TextStringObject, ByteStringObject)):
                raise kind_fail("ACTION_MALFORMED")
            record.kind = "LINK_URI"
            record.uri_object = value
            return
        destination = value
    else:
        _, destination = ctx.lookup(annotation, "/Dest")
    if isinstance(destination, ArrayObject):
        limit = ctx.limits["inspection_max_dest_array_length"]
        if len(destination) > limit:
            raise _cfail(STATUS_PDF_INSPECTION_FAILED, REASON_INSPECTION_LIMIT, "DEST_LENGTH", "S10.03",
                         page_index=record.page_index, count=len(destination), limit=limit)
        first = list(destination)[0] if len(destination) else None
        if isinstance(first, IndirectObject) and _object_id(first) in page_numbers:
            record.kind = "LINK_GOTO"
            record.goto_page = page_numbers[_object_id(first)]
            return
    raise kind_fail("DEST_UNSUPPORTED")


def _inside(center: tuple, rect: list) -> bool:
    return rect[0] <= center[0] <= rect[2] and rect[1] <= center[1] <= rect[3]


def stage_s10(ctx: ChildContext) -> dict:
    limits = ctx.limits
    ctx.at("S10.00", "ANNOTATION_READ")
    page_arrays = []
    for index, page in enumerate(ctx.pages):
        ctx.page_index = index
        present, value = ctx.lookup(page, "/Annots")
        entries = None
        if isinstance(value, ArrayObject):
            length = len(value)
            if length > limits["inspection_max_annots_array_length"]:
                raise _cfail(STATUS_PDF_INSPECTION_FAILED, REASON_INSPECTION_LIMIT, "ANNOTS_ARRAY_LENGTH", "S10.00",
                             page_index=index, count=length, limit=limits["inspection_max_annots_array_length"])
            entries = []
            dictionaries = 0
            for element in list(value):
                target = ctx.resolve(element)
                entries.append(target)
                if isinstance(target, DictionaryObject):
                    dictionaries += 1
                    if dictionaries > limits["inspection_max_link_annotations_per_page"]:
                        raise _cfail(STATUS_PDF_INSPECTION_FAILED, REASON_INSPECTION_LIMIT, "ANNOT_COUNT",
                                     "S10.00", page_index=index, count=dictionaries,
                                     limit=limits["inspection_max_link_annotations_per_page"])
        page_arrays.append((present, entries))

    ctx.at("S10.01", "ANNOTATION_READ")
    records = []
    for index, (present, entries) in enumerate(page_arrays):
        ctx.page_index = index
        if not present:
            continue
        if entries is None:
            raise _cfail(STATUS_ANNOTATION, "ANNOTS_NOT_ARRAY", None, "S10.01", page_index=index)
        for annot_index, annotation in enumerate(entries):
            where = {"page_index": index}
            if not _is_plain_dict(annotation):
                raise _cfail(STATUS_ANNOTATION, "ENTRY_NOT_DICT", None, "S10.01", **where)
            subtype_present, subtype = ctx.lookup(annotation, "/Subtype")
            if not subtype_present or not isinstance(subtype, NameObject):
                raise _cfail(STATUS_ANNOTATION, "SUBTYPE_MISSING", None, "S10.01", **where)
            if subtype != "/Link":
                raise _cfail(STATUS_ANNOTATION, "NON_LINK", None, "S10.01", **where)
            numbers = rect_numbers(annotation.raw_get("/Rect"), ctx.resolve) if "/Rect" in annotation else None
            if numbers is None:
                raise _cfail(STATUS_ANNOTATION, "RECT_MALFORMED", None, "S10.01", **where)
            records.append(AnnotationRecord(index, annot_index, annotation,
                                            _annotation_rect_ccs(numbers, ctx.page_facts[index])))

    ctx.at("S10.02", "ANNOTATION_READ")
    by_page = {}
    for record in records:
        by_page.setdefault(record.page_index, []).append(record)
    for index, miner_page in enumerate(ctx.miner_pages):
        ctx.page_index = index

        def mismatch():
            return _cfail(STATUS_COORDINATE, "STACK_ANNOTATION", None, "S10.02", page_index=index)

        miner_annots = resolve1(miner_page.annots)
        miner_list = [] if miner_annots is None else miner_annots
        if not isinstance(miner_list, list):
            raise mismatch()
        present, entries = page_arrays[index]
        expected = entries if entries is not None else []
        if len(miner_list) != len(expected):
            raise mismatch()
        page_records = {record.annot_index: record for record in by_page.get(index, [])}
        for position, item in enumerate(miner_list):
            record = page_records.get(position)
            if record is None:
                continue
            miner = resolve1(item)
            if not isinstance(miner, dict) or _miner_name(miner.get("Subtype")) != "Link":
                raise mismatch()
            miner_rect = resolve1(miner.get("Rect"))
            numbers = None
            if isinstance(miner_rect, (list, tuple)) and len(miner_rect) == 4:
                numbers = [normalize_number(resolve1(value)) for value in miner_rect]
            if numbers is None or any(value is None for value in numbers):
                raise mismatch()
            miner_ccs = _annotation_rect_ccs(numbers, ctx.page_facts[index])
            if any(_abs_diff(a, b) > TOLERANCE_1E6 for a, b in zip(miner_ccs, record.rect_ccs)):
                raise mismatch()
            miner_action = resolve1(miner.get("A"))
            if isinstance(miner_action, dict) and "URI" in miner_action:
                miner_uri = resolve1(miner_action.get("URI"))
                record.uri_object = _pypdf_uri_object(ctx, record.annotation)
                if record.uri_object is None:
                    raise mismatch()
                if not isinstance(record.uri_object, (TextStringObject, ByteStringObject)):
                    raise mismatch()
                if _uri_bytes(ctx, record, "S10.02") != miner_uri:
                    raise mismatch()

    ctx.at("S10.03", "ANNOTATION_READ")
    page_numbers = {}
    for index, page in enumerate(ctx.pages):
        reference = getattr(page, "indirect_reference", None)
        if isinstance(reference, IndirectObject):
            page_numbers[_object_id(reference)] = index
    for record in records:
        ctx.page_index = record.page_index
        _action_precedence(ctx, record, page_numbers)

    ctx.at("S10.04", "ANNOTATION_READ")
    for record in records:
        ctx.page_index = record.page_index
        if record.kind != "LINK_URI":
            continue
        data = _uri_bytes(ctx, record, "S10.04")
        if any(octet > 0x7F for octet in data):
            raise _cfail(STATUS_LINK_URI, "URI_NON_ASCII", None, "S10.04", page_index=record.page_index)
        canonical = canonicalize_uri(str(data, "ascii"))
        if canonical is None:
            raise _cfail(STATUS_LINK_URI, None, None, "S10.04", page_index=record.page_index)
        record.uri = canonical

    ctx.at("S10.05", "ANNOTATION_READ")
    kept = []
    duplicates = 0
    for record in records:
        duplicate = any(
            other.page_index == record.page_index
            and other.destination() == record.destination()
            and all(_abs_diff(a, b) <= DUPLICATE_TOLERANCE for a, b in zip(other.rect_ccs, record.rect_ccs))
            for other in kept
        )
        if duplicate:
            duplicates += 1
        else:
            kept.append(record)
    for record in kept:
        ctx.page_index = record.page_index
        record.words = [word for word in ctx.page_words[record.page_index] if _inside(word["center"], record.rect_ccs)]
        if not record.words:
            raise _cfail(STATUS_LINK_AMBIGUOUS, None, None, "S10.05", page_index=record.page_index)
        for word in record.words:
            for other in kept:
                if (
                    other is not record
                    and other.page_index == record.page_index
                    and other.destination() != record.destination()
                    and _inside(word["center"], other.rect_ccs)
                ):
                    raise _cfail(STATUS_LINK_AMBIGUOUS, None, None, "S10.05", page_index=record.page_index)
        if any(len(word["text"]) > TEXT_CHUNK_MAX_CHARS for word in record.words):
            raise ChildFail(*EVIDENCE_BYTES_TRIPLE, {})
    return {
        "annotations": [
            {
                "page_index": record.page_index,
                "annot_index": record.annot_index,
                "subtype": "Link",
                "rect_ccs": list(record.rect_ccs),
                "kind": record.kind,
                "uri": record.uri,
                "goto_page": record.goto_page,
                "words_text": [word["text"] for word in record.words],
            }
            for record in kept
        ],
        "duplicates": duplicates,
    }


# Stage runner and entry main ------------------------------------------------------------

STAGE_FUNCTIONS_V1 = (
    ("S5.02", stage_s5_02),
    ("S5.03", stage_s5_03),
    ("S6", stage_s6),
    ("S7", stage_s7),
    ("S9", stage_s9),
    ("S10", stage_s10),
)
STAGES_WITH_PAGE_EVIDENCE = ("S6", "S7", "S9", "S10")


def execute_stage(ctx: ChildContext, stage: str, function) -> tuple:
    """(outcome, triple, evidence) of one stage; an exception is mapped by
    INSPECTION_EXCEPTION_MAPPING_V1 at the slot that performed the read."""
    ctx.stage = stage
    try:
        return "PASS", NO_TRIPLE, function(ctx)
    except ChildFail as failure:
        return "FAIL", failure.triple, failure.evidence
    except MemoryError:
        evidence = {"slot": ctx.slot}
        if stage == "S5.02":
            evidence["start_attestation"] = ctx.attestation or start_attestation(ctx.observation, ctx.pdf_bytes)
        return "FAIL", MEMORY_TRIPLE, evidence
    except Exception as exc:
        if ctx.exc_reason is None:
            raise
        evidence = {"slot": ctx.slot}
        if stage in STAGES_WITH_PAGE_EVIDENCE:
            evidence["page_index"] = ctx.page_index
        evidence.update(_exception_evidence(exc))
        if ctx.exc_reason == "TRACKER_FAILURE":
            return "FAIL", (STATUS_TEXT_UNOBSERVABLE, "TRACKER_FAILURE", None), evidence
        return "FAIL", (STATUS_PDF_INSPECTION_FAILED, ctx.exc_reason, None), evidence


def run_child(ctx: ChildContext, emitter: FrameEmitter) -> tuple:
    """Stages strictly in order, each flushed before the next starts; the
    first failing check ends the run and FINAL mirrors its triple."""
    for stage, function in STAGE_FUNCTIONS_V1:
        outcome, triple, evidence = execute_stage(ctx, stage, function)
        written = emitter.stage(stage, outcome, triple, evidence)
        if written != NO_TRIPLE:
            emitter.final(written, ctx.pdf_sha256, ctx.entry_sha256)
            return written
    emitter.final(NO_TRIPLE, ctx.pdf_sha256, ctx.entry_sha256)
    return NO_TRIPLE


def main() -> int:
    observation = START_OBSERVATION if START_OBSERVATION is not None else observe_start(__file__)
    if not _is_int(LINE_GROUP_BASELINE_TOLERANCE_Q) or not _is_int(WORD_GAP_THRESHOLD_Q):
        return 2
    pdf_bytes = sys.stdin.buffer.read()
    context = ChildContext(pdf_bytes, observation, LINE_GROUP_BASELINE_TOLERANCE_Q, WORD_GAP_THRESHOLD_Q)
    run_child(context, FrameEmitter(sys.stdout.buffer))
    return 0


if __name__ == "__main__":
    sys.exit(main())
