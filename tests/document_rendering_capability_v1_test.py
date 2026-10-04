"""Hermetic tests for CAREER_OS_DOCUMENT_RENDERING_CAPABILITY_V1.

PDFMINER_FORM_EXECUTION_EQUIVALENCE_V1: every fixture below is written as raw
PDF bytes with the standard library. The PREDICTED side is FORM_CALL_GRAPH_V1
as computed by the capability's own pre-scan code (src/rendered_pdf_inspection.py)
from the pinned pypdf reading; the OBSERVED side is what the pinned
pdfminer.six actually executes under PDFMINER_EXECUTION_BINDING_V1, observed by
wrapping the interpreter's Form-execution entry point (render_contents) and
delegating unchanged. No row carries a hand-written expected edge list.

A failing row is the SC36 STOP (RENDER_COORDINATE_SPACE_UNVERIFIED /
FORM_EXECUTION_MODEL): this test then exits non-zero and reports the row.

PARSER_AMBIGUITY_GATE_V1: the rejection rows (D1a to D5, P3 and the
PDF-null-parent P5 variant) are judged only by the REJECTION CRITERION on the
real capability code path; each has an admitted control judged by the PASS
criterion including the page content root. RAW_STREAM_BYTES_V1 is proven by
an audit of every stdlib zlib.decompress call made by the pinned pdfminer.six
during interpretation, compared with the pre-scan stream records.
"""

from __future__ import annotations

import ast
import hashlib
import importlib.util
import io
import json
import logging
import os
import re
import shutil
import stat
import struct
import subprocess
import sys
import tempfile
import types
import zipfile
import zlib
from pathlib import Path

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

DEPENDENCY_MODULES = ("pdfminer", "pypdf")
MISSING_DEPENDENCIES = tuple(name for name in DEPENDENCY_MODULES if importlib.util.find_spec(name) is None)

if not MISSING_DEPENDENCIES:
    import pdfminer  # noqa: E402
    import pdfminer.settings  # noqa: E402
    import pypdf  # noqa: E402
    from pdfminer.converter import PDFPageAggregator  # noqa: E402
    from pdfminer.layout import LTChar, LTContainer  # noqa: E402
    from pdfminer.pdfdocument import PDFDocument  # noqa: E402
    from pdfminer.pdfinterp import PDFPageInterpreter, PDFResourceManager  # noqa: E402
    from pdfminer.pdfpage import PDFPage  # noqa: E402
    from pdfminer.pdftypes import PDFStream, stream_value  # noqa: E402
    from pypdf import PdfReader  # noqa: E402
    from pypdf.errors import PdfReadError  # noqa: E402
    from pypdf.generic import IndirectObject  # noqa: E402

    import rendered_pdf_inspection  # noqa: E402
    from rendered_pdf_inspection import (  # noqa: E402
        EMPTY_SCOPE,
        PreScanOutcome,
        name_admissible,
        open_pdfminer_document,
        open_pypdf_reader,
        open_strict_shadow_reader,
        run_pre_scan,
    )
else:
    PdfReadError = Exception
    open_strict_shadow_reader = None

import document_render_adapter as adapter  # noqa: E402

logging.disable(logging.CRITICAL)

PINNED_PDFMINER_SIX = "20260107"
PINNED_PYPDF = "6.19.0"
HARNESS_EXECUTION_BOUND = 10000


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        print(f"FAIL: {message}")
        raise SystemExit(1)


# Raw PDF fixture writer -------------------------------------------------------


def build_pdf(objects: dict, root: int = 1, unlisted_body: bytes = b"") -> bytes:
    """unlisted_body is written before the cross-reference table and is not
    listed in it (used only by the STREAM_MISMATCH non-stream vector)."""
    out = bytearray(b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n")
    offsets = {}
    for number in sorted(objects):
        offsets[number] = len(out)
        out += b"%d 0 obj\n" % number + objects[number] + b"\nendobj\n"
    out += unlisted_body
    size = max(objects) + 1
    xref_at = len(out)
    out += b"xref\n0 %d\n" % size
    out += b"0000000000 65535 f \n"
    for number in range(1, size):
        if number in offsets:
            out += b"%010d 00000 n \n" % offsets[number]
        else:
            out += b"0000000000 65535 f \n"
    out += b"trailer\n<< /Size %d /Root %d 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (
        size,
        root,
        xref_at,
    )
    return bytes(out)


def stream(dictionary_body: bytes, data: bytes) -> bytes:
    return (
        b"<< "
        + dictionary_body
        + b" /Length %d >>\nstream\n" % len(data)
        + data
        + b"\nendstream"
    )


def flate_stream(dictionary_body: bytes, data: bytes) -> bytes:
    return stream(b"/Filter /FlateDecode " + dictionary_body, zlib.compress(data))


def text(label: bytes) -> bytes:
    return b"BT /F1 12 Tf 72 700 Td (" + label + b") Tj ET\n"


def form(content: bytes, resources: bytes = b"", bbox: bytes = b"/BBox [0 0 612 792]", subtype: bytes = b"/Subtype /Form") -> bytes:
    return stream(b"/Type /XObject " + subtype + b" " + bbox + b" " + resources, content)


FONT = b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"
CATALOG = b"<< /Type /Catalog /Pages 2 0 R >>"
MEDIABOX = b"/MediaBox [0 0 612 792]"
IMAGE = stream(
    b"/Type /XObject /Subtype /Image /Width 1 /Height 1 /ColorSpace /DeviceGray /BitsPerComponent 8",
    b"\x80",
)


def single_page(page_resources: bytes, content: bytes, extra: dict, pages_extra: bytes = b"") -> bytes:
    objects = {
        1: CATALOG,
        2: b"<< /Type /Pages /Kids [3 0 R] /Count 1 " + pages_extra + b" >>",
        3: b"<< /Type /Page /Parent 2 0 R " + MEDIABOX + b" " + page_resources + b" /Contents 5 0 R >>",
        4: FONT,
        5: stream(b"", content),
    }
    objects.update(extra)
    return build_pdf(objects)


def page_xobjects(entries: bytes) -> bytes:
    return b"/Resources << /Font << /F1 4 0 R >> /XObject << " + entries + b" >> >>"


# Fixtures ---------------------------------------------------------------------


STRICT = "STRICT_REREAD"
NULL = "NULL_RESOURCES"


def fixtures() -> list:
    """(row, pdf, rejection detail or None, admitted control flag)."""
    rows = []

    def add(row: str, pdf: bytes, rejection: str | None = None, control: bool = False) -> None:
        rows.append((row, pdf, rejection, control))

    g = form(text(b"G"))
    h = form(text(b"H"))

    # Classes (a) to (l).
    add("a_form_no_resources", single_page(page_xobjects(b"/Fa 10 0 R /Fb 11 0 R"), b"/Fa Do\n", {10: form(text(b"F") + b"/Fb Do\n"), 11: g}))
    add("b_direct_empty_resources", single_page(page_xobjects(b"/Fa 10 0 R /Fb 11 0 R"), b"/Fa Do\n", {10: form(text(b"F") + b"/Fb Do\n", b"/Resources << >>"), 11: g}))
    add("c_indirect_empty_resources", single_page(page_xobjects(b"/Fa 10 0 R /Fb 11 0 R"), b"/Fa Do\n", {10: form(text(b"F") + b"/Fb Do\n", b"/Resources 12 0 R"), 11: g, 12: b"<< >>"}))
    add("d_own_resources", single_page(page_xobjects(b"/Fa 10 0 R /Fb 11 0 R"), b"/Fa Do\n", {10: form(text(b"F") + b"/Fb Do\n", b"/Resources << /XObject << /Fb 12 0 R >> >>"), 11: g, 12: h}))
    add("e_form_no_bbox", single_page(page_xobjects(b"/Fa 10 0 R"), b"/Fa Do\n", {10: form(text(b"F"), bbox=b"")}))
    add(
        "f_indirect_target_and_direct_dict_entry",
        single_page(
            page_xobjects(b"/Fa 10 0 R /Fd << /Type /XObject /Subtype /Form /BBox [0 0 612 792] >>"),
            b"/Fa Do\n/Fd Do\n",
            {10: form(text(b"F"))},
        ),
    )
    add("g_non_stream_target", single_page(page_xobjects(b"/Fn 10 0 R"), b"/Fn Do\n", {10: b"<< /Type /XObject /Subtype /Form /BBox [0 0 612 792] >>"}))
    add("h_wrong_subtype_image", single_page(page_xobjects(b"/Im 10 0 R"), b"q 10 0 0 10 0 0 cm /Im Do Q\n", {10: IMAGE}))
    add("h_wrong_subtype_ps", single_page(page_xobjects(b"/Ps 10 0 R"), b"/Ps Do\n", {10: form(b"", subtype=b"/Subtype /PS")}))
    add(
        "i_shared_form_two_scopes",
        single_page(
            page_xobjects(b"/F1x 10 0 R /S 11 0 R /Q 12 0 R"),
            b"/S Do\n/F1x Do\n",
            {
                10: form(text(b"F") + b"/S Do\n", b"/Resources << /XObject << /S 11 0 R /Q 13 0 R >> >>"),
                11: form(text(b"S") + b"/Q Do\n"),
                12: form(text(b"Q1")),
                13: form(text(b"Q2")),
            },
        ),
    )
    add("j_self_recursive", single_page(page_xobjects(b"/Fa 10 0 R"), b"/Fa Do\n", {10: form(text(b"F") + b"/Fa Do\n")}))
    add("j_two_form_cycle", single_page(page_xobjects(b"/Fa 10 0 R /Fb 11 0 R"), b"/Fa Do\n", {10: form(text(b"F") + b"/Fb Do\n"), 11: form(text(b"G") + b"/Fa Do\n")}))
    add(
        "k_inherited_chain",
        single_page(
            page_xobjects(b"/Fa 10 0 R /Fb 11 0 R /Fc 12 0 R"),
            b"/Fa Do\n",
            {
                10: form(text(b"A") + b"/Fb Do\n"),
                11: form(text(b"B") + b"/Fc Do\n", b"/Resources << >>"),
                12: form(text(b"C")),
            },
        ),
    )
    add("l_own_beats_inherited", single_page(page_xobjects(b"/Fa 10 0 R /N 11 0 R"), b"/Fa Do\n", {10: form(text(b"F") + b"/N Do\n", b"/Resources << /XObject << /N 12 0 R >> >>"), 11: g, 12: h}))

    # FORM /Resources rows R1 to R11.
    def r_row(name: str, resources: bytes, extra: dict | None = None) -> None:
        objects = {10: form(text(b"F") + b"/N Do\n", resources), 11: g, 12: h}
        objects.update(extra or {})
        add(name, single_page(page_xobjects(b"/Fa 10 0 R /N 11 0 R"), b"/Fa Do\n", objects))

    r_row("R1_absent", b"")
    r_row("R2_null", b"/Resources null")
    r_row("R3_direct_empty", b"/Resources << >>")
    r_row("R4_indirect_empty", b"/Resources 13 0 R", {13: b"<< >>"})
    r_row("R5_direct_non_empty", b"/Resources << /XObject << /N 12 0 R >> >>")
    r_row("R6_indirect_non_empty", b"/Resources 13 0 R", {13: b"<< /XObject << /N 12 0 R >> >>"})
    r_row("R7_empty_array", b"/Resources [ ]")
    r_row("R7_non_empty_array", b"/Resources [ 1 2 ]")
    r_row("R8_name", b"/Resources /Foo")
    r_row("R9_zero", b"/Resources 0")
    r_row("R9_non_zero", b"/Resources 7")
    r_row("R10_stream", b"/Resources 13 0 R", {13: stream(b"/XObject << /N 12 0 R >>", b"")})
    r_row("R11_broken_reference", b"/Resources 99 0 R")

    # PAGE /Resources rows P1 to P7.
    parent_dict = b"/Resources << /XObject << /Fa 10 0 R >> >>"
    fa = {10: form(text(b"F"))}
    add("P1_direct_non_empty", single_page(b"/Resources << /XObject << /Fa 10 0 R >> >>", b"/Fa Do\n", fa))
    add("P2_direct_empty", single_page(b"/Resources << >>", b"/Fa Do\n", fa, parent_dict))
    add("P3_null_page_dict_parent", single_page(b"/Resources null", b"/Fa Do\n", fa, parent_dict), NULL)
    add("P3_control_absent_page_dict_parent", single_page(b"", b"/Fa Do\n", fa, parent_dict), control=True)
    add("P4_absent_page_dict_parent", single_page(b"", b"/Fa Do\n", fa, parent_dict))

    def grandparent(parent_value: bytes) -> bytes:
        return build_pdf(
            {
                1: CATALOG,
                2: b"<< /Type /Pages /Kids [20 0 R] /Count 1 " + parent_dict + b" >>",
                20: b"<< /Type /Pages /Parent 2 0 R /Kids [3 0 R] /Count 1 " + parent_value + b" >>",
                3: b"<< /Type /Page /Parent 20 0 R " + MEDIABOX + b" /Contents 5 0 R >>",
                4: FONT,
                5: stream(b"", b"/Fa Do\n"),
                10: form(text(b"F")),
            }
        )

    add("P5_grandparent", grandparent(b""))
    add("P5_parent_null_grandparent_dict", grandparent(b"/Resources null"), NULL)
    add("P5_control_parent_absent_grandparent_dict", grandparent(b""), control=True)
    add("P6_array", single_page(b"/Resources [ ]", b"/Fa Do\n", fa, parent_dict))
    add("P6_name", single_page(b"/Resources /Foo", b"/Fa Do\n", fa, parent_dict))
    add("P6_number", single_page(b"/Resources 3", b"/Fa Do\n", fa, parent_dict))
    add("P6_stream", single_page(b"/Resources 13 0 R", b"/Fa Do\n", {**fa, 13: stream(b"/XObject << /Fa 10 0 R >>", b"")}, parent_dict))
    add("P7_broken_reference", single_page(b"/Resources 99 0 R", b"/Fa Do\n", fa, parent_dict))

    # EXECUTION rows E1 to E9.
    add("E1_no_bbox", single_page(page_xobjects(b"/Fa 10 0 R"), b"/Fa Do\n", {10: form(text(b"F"), bbox=b"")}))
    add("E2_malformed_bbox", single_page(page_xobjects(b"/Fa 10 0 R"), b"/Fa Do\n", {10: form(text(b"F"), bbox=b"/BBox 5")}))
    add(
        "E3_direct_object_with_form_attributes",
        single_page(page_xobjects(b"/Fd << /Type /XObject /Subtype /Form /BBox [0 0 612 792] >>"), b"/Fd Do\n", {}),
    )
    add("E4_indirect_form", single_page(page_xobjects(b"/Fa 10 0 R"), b"/Fa Do\n", {10: form(text(b"F"))}))
    add("E5_non_stream_target", single_page(page_xobjects(b"/Fn 10 0 R"), b"/Fn Do\n", {10: b"[ 1 2 3 ]"}))
    add(
        "E6_wrong_subtypes",
        single_page(
            page_xobjects(b"/Im 10 0 R /Ps 11 0 R /Na 12 0 R /Un 13 0 R"),
            b"q 10 0 0 10 0 0 cm /Im Do Q\n/Ps Do\n/Na Do\n/Un Do\n",
            {
                10: IMAGE,
                11: form(b"", subtype=b"/Subtype /PS"),
                12: form(text(b"N"), subtype=b""),
                13: form(text(b"U"), subtype=b"/Subtype /Unknown"),
            },
        ),
    )
    add(
        "E7_shared_two_scopes_two_pages",
        build_pdf(
            {
                1: CATALOG,
                2: b"<< /Type /Pages /Kids [3 0 R 6 0 R] /Count 2 >>",
                3: b"<< /Type /Page /Parent 2 0 R " + MEDIABOX + b" " + page_xobjects(b"/S 11 0 R /Fo 10 0 R /Q 12 0 R") + b" /Contents 5 0 R >>",
                4: FONT,
                5: stream(b"", b"/S Do\n/Fo Do\n"),
                6: b"<< /Type /Page /Parent 2 0 R " + MEDIABOX + b" " + page_xobjects(b"/S 11 0 R /Q 13 0 R") + b" /Contents 7 0 R >>",
                7: stream(b"", b"/S Do\n"),
                10: form(text(b"O") + b"/S Do\n", b"/Resources << /XObject << /S 11 0 R /Q 13 0 R >> >>"),
                11: form(text(b"S") + b"/Q Do\n"),
                12: form(text(b"Q1")),
                13: form(text(b"Q2")),
            }
        ),
    )
    add("E8_self_recursive", single_page(page_xobjects(b"/Fa 10 0 R"), b"/Fa Do\n", {10: form(text(b"F") + b"/Fa Do\n")}))
    add("E9_mutual_recursion", single_page(page_xobjects(b"/Fa 10 0 R /Fb 11 0 R"), b"/Fa Do\n", {10: form(text(b"F") + b"/Fb Do\n"), 11: form(text(b"G") + b"/Fa Do\n")}))

    # PARSER-DIVERGENCE rows D1 to D5 (duplicate keys and raw-name collisions).
    add("D1a_duplicate_xobject_name_page", single_page(page_xobjects(b"/N 11 0 R /N 12 0 R"), b"/N Do\n", {11: g, 12: h}), STRICT)
    add(
        "D1b_duplicate_xobject_name_form",
        single_page(page_xobjects(b"/Fa 10 0 R"), b"/Fa Do\n", {10: form(text(b"F") + b"/N Do\n", b"/Resources << /XObject << /N 11 0 R /N 12 0 R >> >>"), 11: g, 12: h}),
        STRICT,
    )
    add(
        "D2a_duplicate_resources_page",
        build_pdf(
            {
                1: CATALOG,
                2: b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
                3: b"<< /Type /Page /Parent 2 0 R " + MEDIABOX + b" /Resources 13 0 R /Resources 14 0 R /Contents 5 0 R >>",
                4: FONT,
                5: stream(b"", b"/N Do\n"),
                11: g,
                12: h,
                13: b"<< /Font << /F1 4 0 R >> /XObject << /N 11 0 R >> >>",
                14: b"<< /Font << /F1 4 0 R >> /XObject << /N 12 0 R >> >>",
            }
        ),
        STRICT,
    )
    add(
        "D2b_duplicate_resources_form",
        single_page(
            page_xobjects(b"/Fa 10 0 R"),
            b"/Fa Do\n",
            {
                10: form(text(b"F") + b"/N Do\n", b"/Resources 13 0 R /Resources 14 0 R"),
                11: g,
                12: h,
                13: b"<< /XObject << /N 11 0 R >> >>",
                14: b"<< /XObject << /N 12 0 R >> >>",
            },
        ),
        STRICT,
    )
    add(
        "D3_duplicate_contents",
        build_pdf(
            {
                1: CATALOG,
                2: b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
                3: b"<< /Type /Page /Parent 2 0 R " + MEDIABOX + b" " + page_xobjects(b"/Ga 11 0 R /Hb 12 0 R") + b" /Contents 5 0 R /Contents 6 0 R >>",
                4: FONT,
                5: stream(b"", text(b"C1") + b"/Ga Do\n"),
                6: stream(b"", text(b"C2") + b"q /Hb Do Q\n"),
                11: g,
                12: h,
            }
        ),
        STRICT,
    )
    add("D4_subtype_form_then_image", single_page(page_xobjects(b"/X 10 0 R"), b"/X Do\n", {10: form(text(b"X"), subtype=b"/Subtype /Form /Subtype /Image")}), STRICT)
    add("D4_subtype_image_then_form", single_page(page_xobjects(b"/X 10 0 R"), b"/X Do\n", {10: form(text(b"X"), subtype=b"/Subtype /Image /Subtype /Form")}), STRICT)
    add("D5_invoke_E9", single_page(page_xobjects(b"/#C3#A9 11 0 R /#E9 12 0 R"), b"/#E9 Do\n", {11: g, 12: h}), STRICT)
    add("D5_invoke_C3A9", single_page(page_xobjects(b"/#C3#A9 11 0 R /#E9 12 0 R"), b"/#C3#A9 Do\n", {11: g, 12: h}), STRICT)

    # ADMITTED CONTROLS of the D rows: the same structure with the ambiguity removed.
    add("D1a_control", single_page(page_xobjects(b"/N 11 0 R /M 12 0 R"), b"/N Do\n", {11: g, 12: h}), control=True)
    add(
        "D1b_control",
        single_page(page_xobjects(b"/Fa 10 0 R"), b"/Fa Do\n", {10: form(text(b"F") + b"/N Do\n", b"/Resources << /XObject << /N 11 0 R /M 12 0 R >> >>"), 11: g, 12: h}),
        control=True,
    )
    add(
        "D2a_control",
        build_pdf(
            {
                1: CATALOG,
                2: b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
                3: b"<< /Type /Page /Parent 2 0 R " + MEDIABOX + b" /Resources 13 0 R /Contents 5 0 R >>",
                4: FONT,
                5: stream(b"", b"/N Do\n"),
                11: g,
                12: h,
                13: b"<< /Font << /F1 4 0 R >> /XObject << /N 11 0 R >> >>",
                14: b"<< /Font << /F1 4 0 R >> /XObject << /N 12 0 R >> >>",
            }
        ),
        control=True,
    )
    add(
        "D2b_control",
        single_page(
            page_xobjects(b"/Fa 10 0 R"),
            b"/Fa Do\n",
            {
                10: form(text(b"F") + b"/N Do\n", b"/Resources 13 0 R"),
                11: g,
                12: h,
                13: b"<< /XObject << /N 11 0 R >> >>",
                14: b"<< /XObject << /N 12 0 R >> >>",
            },
        ),
        control=True,
    )
    add(
        "D3_control",
        build_pdf(
            {
                1: CATALOG,
                2: b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
                3: b"<< /Type /Page /Parent 2 0 R " + MEDIABOX + b" " + page_xobjects(b"/Ga 11 0 R /Hb 12 0 R") + b" /Contents 5 0 R >>",
                4: FONT,
                5: stream(b"", text(b"C1") + b"/Ga Do\n"),
                6: stream(b"", text(b"C2") + b"q /Hb Do Q\n"),
                11: g,
                12: h,
            }
        ),
        control=True,
    )
    add("D4_control", single_page(page_xobjects(b"/X 10 0 R"), b"/X Do\n", {10: form(text(b"X"))}), control=True)
    add("D5_control_escaped_admissible", single_page(page_xobjects(b"/X#31 11 0 R /E 12 0 R"), b"/X1 Do\n", {11: g, 12: h}), control=True)
    add("D5_control_plain", single_page(page_xobjects(b"/X1 11 0 R /E 12 0 R"), b"/E Do\n", {11: g, 12: h}), control=True)
    return rows


# Prediction (capability graph code over the pinned pypdf reading) -------------


def predict(pdf: bytes, strict_reader_factory=open_strict_shadow_reader, document=None) -> dict:
    """The real S6.01b code path over one snapshot: the canonical strict=False
    reader, the pdfminer.six PDFDocument of PDFMINER_EXECUTION_BINDING_V1 and
    the strict shadow reader."""
    reader = open_pypdf_reader(pdf)
    if document is None:
        document = open_pdfminer_document(pdf)
    outcome = None
    evidence = None
    phase = None
    try:
        result = run_pre_scan(pdf, reader, document, strict_reader_factory=strict_reader_factory)
        graphs = list(result.pages)
        completed = list(result.pages)
        stream_records = result.stream_records
        exemptions = result.exemptions
    except PreScanOutcome as exc:
        outcome = (exc.reason, exc.detail)
        evidence = exc.evidence
        phase = exc.phase
        completed = list(exc.completed_pages)
        graphs = list(completed)
        stream_records = exc.stream_records
        exemptions = exc.exemptions
        failing = getattr(exc, "page_graph", None)
        if failing is not None:
            graphs.append(failing)
    edges = set()
    pages = {}
    for graph in graphs:
        edges |= graph.edges
        pages[graph.page_index] = {
            "content_stream_ids": list(graph.content_stream_ids),
            "scope": graph.page_scope_identity,
        }
    return {
        "edges": edges,
        "pages": pages,
        "outcome": outcome,
        "evidence": evidence,
        "phase": phase,
        "completed_pages": completed,
        "stream_records": stream_records,
        "exemptions": exemptions,
        "document": document,
    }


# Observation (instrumented pinned pdfminer.six) --------------------------------


class _HarnessBound(Exception):
    pass


class Observation:
    def __init__(self) -> None:
        self.page_index = None
        self.stack = []
        self.raw_edges = []
        self.page_roots = {}
        self.executions = 0


def _instrumented_class(observation: Observation):
    class ObservingInterpreter(PDFPageInterpreter):
        def render_contents(self, resources, streams, ctm=(1, 0, 0, 1, 0, 0)):
            if not observation.stack:
                owner = ("PAGE", observation.page_index)
                resolved = [stream_value(s) for s in streams]
                observation.page_roots[observation.page_index] = {
                    "streams": [(s.objid, s.genno) for s in resolved],
                    "resources": resources,
                }
                frame = {"owner": owner, "resources": resources, "xobj": None, "parent": None}
            else:
                xobj = streams[0]
                parent = observation.stack[-1]
                observation.executions += 1
                if observation.executions > HARNESS_EXECUTION_BOUND:
                    raise _HarnessBound()
                frame = {
                    "owner": ("FORM", (xobj.objid, xobj.genno)),
                    "resources": resources,
                    "xobj": xobj,
                    "parent": parent,
                }
                observation.raw_edges.append((parent, (xobj.objid, xobj.genno)))
            observation.stack.append(frame)
            try:
                return super().render_contents(resources, streams, ctm)
            finally:
                observation.stack.pop()

    return ObservingInterpreter


def _all_objects(document: PDFDocument) -> list:
    objects = []
    seen = set()
    for xref in document.xrefs:
        for objid in xref.get_objids():
            if objid in seen:
                continue
            seen.add(objid)
            try:
                genno = xref.get_pos(objid)[2]
                obj = document.getobj(objid)
            except Exception:
                continue
            objects.append(((objid, genno), obj))
    return objects


def _identity(resources, frame, objects) -> tuple:
    if resources is None:
        return EMPTY_SCOPE
    for key, obj in objects:
        if obj is resources:
            return ("INDIRECT",) + key
    for key, obj in objects:
        holder = obj.attrs if isinstance(obj, PDFStream) else obj
        if isinstance(holder, dict) and holder.get("Resources") is resources:
            return ("DIRECT",) + key
    parent = frame.get("parent") if frame else None
    if parent is not None and isinstance(resources, dict):
        inherited = parent["resources"]
        if (
            isinstance(inherited, dict)
            and resources is not inherited
            and resources.keys() == inherited.keys()
            and all(resources[k] is inherited[k] for k in resources)
        ):
            return parent["identity"]
    if isinstance(resources, dict) and not resources:
        return EMPTY_SCOPE
    return ("UNIDENTIFIED",)


def _chars(layout) -> list:
    out = []

    def walk(item):
        if isinstance(item, LTChar):
            out.append((item.get_text(), item.fontname, tuple(round(v, 6) for v in item.matrix), tuple(round(v, 6) for v in item.bbox)))
        elif isinstance(item, LTContainer):
            for child in item:
                walk(child)

    walk(layout)
    return out


def run_pdfminer(pdf: bytes, observe: bool, document: PDFDocument | None = None) -> dict:
    """PDFMINER_EXECUTION_BINDING_V1: PDFParser over the in-memory bytes,
    PDFDocument(parser) defaults, PDFPage.create_pages, PDFResourceManager(),
    PDFPageAggregator(rsrcmgr, laparams=None), PDFPageInterpreter. When
    document is given it is the PDFDocument the pre-scan used at S6.01b."""
    observation = Observation()
    if document is None:
        document = open_pdfminer_document(pdf)
    rsrcmgr = PDFResourceManager()
    device = PDFPageAggregator(rsrcmgr, laparams=None)
    interpreter_class = _instrumented_class(observation) if observe else PDFPageInterpreter
    interpreter = interpreter_class(rsrcmgr, device)
    chars = []
    bounded = False
    interpretation_exception = None
    for page_index, page in enumerate(PDFPage.create_pages(document)):
        observation.page_index = page_index
        try:
            interpreter.process_page(page)
        except _HarnessBound:
            bounded = True
            observation.stack.clear()
            break
        except Exception as exc:
            interpretation_exception = rendered_pdf_inspection.fail_exception_class(exc)
            observation.stack.clear()
            break
        chars.append(_chars(device.get_result()))
    result = {"chars": chars, "bounded": bounded, "interpretation_exception": interpretation_exception}
    if not observe:
        return result
    objects = _all_objects(document)
    edges = set()
    frames_done = {}

    def frame_identity(frame):
        key = id(frame)
        if key not in frames_done:
            if frame["parent"] is not None:
                frame_identity(frame["parent"])
            frame["identity"] = _identity(frame["resources"], frame, objects)
            frames_done[key] = frame["identity"]
        return frames_done[key]

    for parent, target in observation.raw_edges:
        edges.add((parent["owner"], target, frame_identity(parent)))
    pages = {}
    for page_index, root in observation.page_roots.items():
        pages[page_index] = {
            "content_stream_ids": root["streams"],
            "scope": _identity(root["resources"], None, objects),
        }
    result.update({"edges": edges, "pages": pages})
    return result


# Proof ------------------------------------------------------------------------


def _fmt(value) -> str:
    return json.dumps(value, default=list)


SC36_FAILURE = "RENDER_COORDINATE_SPACE_UNVERIFIED/FORM_EXECUTION_MODEL"


def page_root_failures(predicted: dict, observed: dict) -> list:
    failures = []
    for page_index, seen in observed["pages"].items():
        expected = predicted["pages"].get(page_index)
        if expected is None:
            failures.append({"page_index": page_index, "problem": "PAGE_NOT_PREDICTED"})
            continue
        extra_streams = [s for s in seen["content_stream_ids"] if s not in expected["content_stream_ids"]]
        if extra_streams:
            failures.append({"page_index": page_index, "problem": "CONTENT_STREAM_OUTSIDE_PREDICTION", "observed": extra_streams, "predicted": expected["content_stream_ids"]})
        if seen["scope"] != expected["scope"]:
            failures.append({"page_index": page_index, "problem": "PAGE_RESOURCES_OUTSIDE_PREDICTION", "observed": seen["scope"], "predicted": expected["scope"]})
    return failures


def judge_admitted(predicted: dict, observed: dict, control_identical: bool, is_control: bool) -> dict:
    """PASS criterion: every observed edge is predicted; for an admitted
    control also the page content root. An admitted structure that the gate
    rejects fails."""
    rejected = predicted["outcome"] is not None and predicted["outcome"][0] == "PARSER_AMBIGUITY"
    unpredicted_edges = sorted(observed["edges"] - predicted["edges"], key=_fmt)
    page_failures = page_root_failures(predicted, observed)
    passed = (
        not rejected
        and not unpredicted_edges
        and control_identical
        and (not is_control or not page_failures)
    )
    return {
        "pass": passed,
        "verdict": "PASS" if passed else SC36_FAILURE,
        "admitted_row_rejected_by_gate": rejected,
        "unpredicted_edges": unpredicted_edges,
        "page_root_failures": page_failures if is_control else [],
        "page_root_notes_admitted_row": [] if is_control else page_failures,
    }


def streams_decoded(document: PDFDocument) -> list:
    """Object numbers of pdfminer.six streams of this PDFDocument that have
    been decoded (PDFStream.decode sets data)."""
    decoded = []
    for xref in document.xrefs:
        for objid in xref.get_objids():
            try:
                obj = document.getobj(objid)
            except Exception:
                continue
            if isinstance(obj, PDFStream) and obj.data is not None:
                decoded.append(objid)
    return decoded


def judge_rejection(predicted: dict, expected_detail: str) -> dict:
    """REJECTION CRITERION on the real capability code path."""
    outcome_ok = predicted["outcome"] == ("PARSER_AMBIGUITY", expected_detail)
    before_p3 = predicted["phase"] in ("P0", "P1")
    no_raw_read = not predicted["stream_records"]
    prediction_unchanged = not predicted["edges"] and not predicted["completed_pages"]
    decoded = streams_decoded(predicted["document"])
    passed = outcome_ok and before_p3 and no_raw_read and prediction_unchanged and not decoded
    return {
        "pass": passed,
        "verdict": "PASS" if passed else SC36_FAILURE,
        "expected": ("PARSER_AMBIGUITY", expected_detail),
        "position_phase": predicted["phase"],
        "no_raw_stream_bytes_read": no_raw_read,
        "prediction_unchanged": prediction_unchanged,
        "pdfminer_streams_decoded": decoded,
    }


def run_row(row: str, pdf: bytes, rejection, is_control: bool, strict_reader_factory=open_strict_shadow_reader) -> dict:
    predicted = predict(pdf, strict_reader_factory)
    record = {
        "row": row,
        "rejection_row": rejection,
        "admitted_control": is_control,
        "pre_scan_outcome": predicted["outcome"],
        "pre_scan_evidence": predicted["evidence"],
        "exemptions": predicted["exemptions"],
        "predicted_edges": sorted(predicted["edges"], key=_fmt),
    }
    if rejection is not None:
        record.update(judge_rejection(predicted, rejection))
        return record
    if predicted["outcome"] is not None and predicted["outcome"][0] == "PARSER_AMBIGUITY":
        record.update(judge_admitted(predicted, {"edges": set(), "pages": {}}, True, is_control))
        return record
    observed = run_pdfminer(pdf, observe=True, document=predicted["document"])
    control_prediction = predict(pdf, strict_reader_factory)
    control = run_pdfminer(pdf, observe=False, document=control_prediction["document"])
    control_identical = (
        observed["chars"] == control["chars"]
        and observed["interpretation_exception"] == control["interpretation_exception"]
    )
    record.update(judge_admitted(predicted, observed, control_identical, is_control))
    record.update(
        {
            "observed_edges": sorted(observed["edges"], key=_fmt),
            "control_ltchar_identical": control_identical,
            "harness_bounded": observed["bounded"],
            "interpretation_exception": observed["interpretation_exception"],
        }
    )
    return record


def run_form_execution_equivalence(strict_reader_factory=open_strict_shadow_reader, only_rows=None) -> dict:
    report = {
        "binding": {
            "interpreter": sys.version.split()[0],
            "pdfminer_six_version": pdfminer.__version__,
            "pypdf_version": pypdf.__version__,
            "pdfminer_settings_STRICT": pdfminer.settings.STRICT,
            "pypdf_strict": False,
            "strict_shadow_reader_strict": True,
            "recursion_limit": sys.getrecursionlimit(),
        },
        "rows": [],
    }
    for row, pdf, rejection, is_control in fixtures():
        if only_rows is not None and row not in only_rows:
            continue
        report["rows"].append(run_row(row, pdf, rejection, is_control, strict_reader_factory))
    return report


# Tests ------------------------------------------------------------------------


def test_pinned_versions() -> None:
    assert_true(pdfminer.__version__ == PINNED_PDFMINER_SIX, f"pdfminer.six is {pdfminer.__version__}")
    assert_true(pypdf.__version__ == PINNED_PYPDF, f"pypdf is {pypdf.__version__}")


def test_fail_evidence_encoders() -> None:
    module = inspection_module()
    fail_evidence_string = module.fail_evidence_string
    fail_exception_class = module.fail_exception_class
    assert_true(fail_evidence_string('a"b%c\\d') == "a%22b%25c%5Cd", "escape set")
    assert_true(fail_evidence_string("\u00e9") == "%C3%A9", "non-ASCII escape")
    long_value = fail_evidence_string("\u00e9" * 200)
    assert_true(len(long_value) <= 256 and long_value.endswith("%~"), "truncation marker")
    assert_true(not long_value[:-2].endswith("%") and len(long_value[:-2]) % 3 == 0, "no split escape")
    assert_true(fail_exception_class(ValueError("x")) == "ValueError", "exception class")

    class Unprintable(Exception):
        def __str__(self):
            raise RuntimeError("no text")

    first_line = module._first_message_line
    assert_true(first_line(ValueError("one\ntwo")) == "one", "message source stops at LF")
    assert_true(first_line(ValueError("one\rtwo")) == "one", "message source stops at CR")
    assert_true(first_line(Unprintable()) == "", "message source of a raising str is empty")


def test_cycle_rows_rejected_before_interpretation() -> None:
    for row, pdf, _, _ in fixtures():
        if row in ("j_self_recursive", "j_two_form_cycle", "E8_self_recursive", "E9_mutual_recursion"):
            outcome = predict(pdf)["outcome"]
            assert_true(outcome == ("INSPECTION_LIMIT", "FORM_DEPTH"), f"{row}: pre-scan outcome {outcome}")


def test_form_execution_equivalence() -> None:
    report = run_form_execution_equivalence()
    out_path = Path(tempfile.gettempdir()) / "form_execution_equivalence_report.json"
    failing = [r for r in report["rows"] if not r["pass"]]
    rejection_rows = [r["row"] for r in report["rows"] if r["rejection_row"]]
    controls = [r["row"] for r in report["rows"] if r["admitted_control"]]
    print(json.dumps({"binding": report["binding"], "rows": len(report["rows"]), "rejection_rows": rejection_rows, "admitted_controls": controls, "failing_rows": [r["row"] for r in failing]}, indent=1))
    for r in failing:
        print(_fmt(r))
    if "--write-report" in sys.argv:
        out_path.write_text(json.dumps(report, indent=1, default=list), encoding="utf-8")
    assert_true(len(rejection_rows) == 11, f"rejection rows {rejection_rows}")
    assert_true(
        not failing,
        "PDFMINER_FORM_EXECUTION_EQUIVALENCE_V1 FAILED on the pinned pair: "
        f"{SC36_FAILURE}; SC36 STOP before any real inspection",
    )
    for r in report["rows"]:
        if r["rejection_row"] == STRICT:
            evidence = r["pre_scan_evidence"]
            assert_true(evidence["exception_class"] == "PdfReadError", f"{r['row']}: {evidence}")
        if r["rejection_row"] is None and r["row"] not in ("R11_broken_reference", "P7_broken_reference"):
            assert_true(not r["exemptions"], f"{r['row']}: unexpected exemption {r['exemptions']}")


def _row(name: str) -> bytes:
    for row, pdf, _, _ in fixtures():
        if row == name:
            return pdf
    raise KeyError(name)


def test_unresolved_reference_exemption_r11_p7() -> None:
    r11 = predict(_row("R11_broken_reference"))
    assert_true(r11["outcome"] is None, f"R11 admitted: {r11['outcome']}")
    assert_true(
        [e["object_id"] for e in r11["exemptions"]] == [(99, 0)] and r11["exemptions"][0]["phase"] == "P1",
        f"R11 exemption exactly (99, 0) in P1: {r11['exemptions']}",
    )
    page_scope = r11["pages"][0]["scope"]
    assert_true((("FORM", (10, 0)), (11, 0), page_scope) in r11["edges"], "R11 INHERIT: F invokes G under the page scope")
    assert_true(all(edge[1] != (12, 0) for edge in r11["edges"]), "R11 INHERIT: no edge to H")
    r11_row = run_row("R11_broken_reference", _row("R11_broken_reference"), None, False)
    assert_true(r11_row["pass"], f"R11 full PASS criterion: {r11_row}")

    p7 = predict(_row("P7_broken_reference"))
    assert_true(p7["outcome"] is None, f"P7 admitted: {p7['outcome']}")
    assert_true(
        [e["object_id"] for e in p7["exemptions"]] == [(99, 0)] and p7["exemptions"][0]["phase"] == "P1",
        f"P7 exemption exactly (99, 0) in P1: {p7['exemptions']}",
    )
    assert_true(p7["pages"][0]["scope"] == EMPTY_SCOPE, f"P7 EMPTY page scope: {p7['pages'][0]['scope']}")
    assert_true(not any(edge[0] == ("PAGE", 0) for edge in p7["edges"]), "P7: no page-level edge")
    p7_row = run_row("P7_broken_reference", _row("P7_broken_reference"), None, False)
    assert_true(p7_row["pass"], f"P7 full PASS criterion: {p7_row}")


def _font_page(font_resources: bytes, extra: dict) -> bytes:
    objects = {
        1: CATALOG,
        2: b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        3: b"<< /Type /Page /Parent 2 0 R " + MEDIABOX + b" /Resources << /Font " + font_resources + b" >> /Contents 5 0 R >>",
        5: stream(b"", text(b"A")),
    }
    objects.update(extra)
    return build_pdf(objects)


def font_structure_missing_object_vectors() -> dict:
    return {
        "dangling_font_entry": _font_page(b"<< /F1 99 0 R >>", {}),
        "dangling_font_value": _font_page(b"99 0 R", {}),
        "dangling_type0_descendant": _font_page(
            b"<< /F1 4 0 R >>",
            {4: b"<< /Type /Font /Subtype /Type0 /BaseFont /X /Encoding /Identity-H /DescendantFonts [99 0 R] >>"},
        ),
        "dangling_font_descriptor": _font_page(
            b"<< /F1 4 0 R >>",
            {4: b"<< /Type /Font /Subtype /Type1 /BaseFont /CustomSans /FontDescriptor 99 0 R >>"},
        ),
    }


def test_font_structure_missing_object_vectors_pass_s601b() -> None:
    for name, pdf in font_structure_missing_object_vectors().items():
        result = predict(pdf)
        assert_true(result["outcome"] is None, f"{name}: must not end at S6.01b, got {result['outcome']} {result['evidence']}")
        ids = {e["object_id"] for e in result["exemptions"]}
        assert_true(ids == {(99, 0)}, f"{name}: exemptions {result['exemptions']}")


class _PdfReadErrorSubclass(PdfReadError):
    pass


class FakeShadow:
    """A strict shadow reader that raises a chosen exception for one
    (object number, generation) and otherwise delegates to the real one."""

    def __init__(self, pdf: bytes, target: tuple, exc: BaseException) -> None:
        self.real = PdfReader(io.BytesIO(pdf), strict=True)
        self.target = target
        self.exc = exc

    @property
    def pages(self):
        return self.real.pages

    def get_object(self, reference):
        if (int(reference.idnum), int(reference.generation)) == self.target:
            raise self.exc
        return self.real.get_object(IndirectObject(reference.idnum, reference.generation, self.real))


class FakeDocument:
    """A pdfminer.six document whose getobj raises a chosen exception for one
    object number and otherwise delegates to the real one."""

    def __init__(self, pdf: bytes, objid: int, exc: BaseException) -> None:
        self.real = open_pdfminer_document(pdf)
        self.objid = objid
        self.exc = exc
        self.xrefs = self.real.xrefs

    def getobj(self, objid: int):
        if objid == self.objid:
            raise self.exc
        return self.real.getobj(objid)


def _assert_strict_reread(result: dict, label: str, object_id) -> None:
    assert_true(result["outcome"] == ("PARSER_AMBIGUITY", STRICT), f"{label}: {result['outcome']}")
    assert_true(result["evidence"]["object_id"] == object_id, f"{label}: evidence {result['evidence']}")
    assert_true(not result["exemptions"], f"{label}: exemptions {result['exemptions']}")


def test_exemption_negative_vectors() -> None:
    generation_mismatch = single_page(
        page_xobjects(b"/Fa 10 0 R /N 11 0 R"),
        b"/Fa Do\n",
        {10: form(text(b"F") + b"/N Do\n", b"/Resources 13 1 R"), 11: form(text(b"G")), 13: b"<< /XObject << /N 11 0 R >> >>"},
    )
    _assert_strict_reread(predict(generation_mismatch), "generation mismatch (13, 1)", [13, 1])

    missing_kid = build_pdf(
        {
            1: CATALOG,
            2: b"<< /Type /Pages /Kids [3 0 R 99 0 R] /Count 1 >>",
            3: b"<< /Type /Page /Parent 2 0 R " + MEDIABOX + b" /Contents 5 0 R >>",
            5: stream(b"", b""),
        }
    )
    kids = predict(missing_kid)
    _assert_strict_reread(kids, "missing /Kids object", None)
    assert_true(kids["phase"] == "P0" and kids["evidence"]["page_index"] is None, f"/Kids at P0: {kids}")

    r11 = _row("R11_broken_reference")
    exact = PdfReadError("Could not find object.")
    positive = predict(r11, lambda b: FakeShadow(b, (99, 0), PdfReadError("Could not find object.")))
    assert_true(positive["outcome"] is None and [e["object_id"] for e in positive["exemptions"]] == [(99, 0)], f"fake exact E3 exempt: {positive['outcome']}")
    negatives = {
        "PdfReadError subclass": _PdfReadErrorSubclass("Could not find object."),
        "PdfReadError other message": PdfReadError("Could not find object"),
        "PdfReadError extra argument": PdfReadError("Could not find object.", 1),
        "other exception class": ValueError("Could not find object."),
    }
    for label, exc in negatives.items():
        _assert_strict_reread(predict(r11, lambda b, exc=exc: FakeShadow(b, (99, 0), exc)), label, [99, 0])
    _assert_strict_reread(
        predict(r11, lambda b: FakeShadow(b, (10, 0), exact)),
        "E3 exception on a non-None canonical result",
        [10, 0],
    )

    class _NotFoundSubclass(rendered_pdf_inspection.PDFObjectNotFound):
        pass

    for label, exc in {
        "E4 PDFObjectNotFound subclass": _NotFoundSubclass(99),
        "E4 other exception": ValueError(99),
    }.items():
        _assert_strict_reread(predict(r11, document=FakeDocument(r11, 99, exc)), label, [99, 0])


def test_non_raising_fake_shadow_is_sc36_stop() -> None:
    d1_to_d4 = [
        "D1a_duplicate_xobject_name_page",
        "D1b_duplicate_xobject_name_form",
        "D2a_duplicate_resources_page",
        "D2b_duplicate_resources_form",
        "D3_duplicate_contents",
        "D4_subtype_form_then_image",
        "D4_subtype_image_then_form",
    ]
    report = run_form_execution_equivalence(lambda b: PdfReader(io.BytesIO(b)), set(d1_to_d4))
    assert_true(len(report["rows"]) == len(d1_to_d4), "all D1 to D4 rows run")
    for r in report["rows"]:
        assert_true(not r["pass"] and r["verdict"] == SC36_FAILURE, f"{r['row']}: non-raising shadow must be the SC36 STOP")


def test_fake_library_edge_outside_prediction_is_sc36_stop() -> None:
    predicted = predict(_row("R5_direct_non_empty"))
    observed = {"edges": set(predicted["edges"]), "pages": {k: dict(v) for k, v in predicted["pages"].items()}}
    assert_true(judge_admitted(predicted, observed, True, True)["pass"], "baseline equal observation passes")
    extra = dict(observed, edges=observed["edges"] | {(("PAGE", 0), (12, 0), predicted["pages"][0]["scope"])})
    assert_true(judge_admitted(predicted, extra, True, False)["verdict"] == SC36_FAILURE, "unpredicted edge")
    stray = {"edges": set(predicted["edges"]), "pages": {0: {"content_stream_ids": [(6, 0)], "scope": predicted["pages"][0]["scope"]}}}
    assert_true(judge_admitted(predicted, stray, True, True)["verdict"] == SC36_FAILURE, "stray page content stream")
    other_scope = {"edges": set(predicted["edges"]), "pages": {0: {"content_stream_ids": predicted["pages"][0]["content_stream_ids"], "scope": ("INDIRECT", 77, 0)}}}
    assert_true(judge_admitted(predicted, other_scope, True, True)["verdict"] == SC36_FAILURE, "page resources outside prediction")


def test_name_domain_vectors() -> None:
    assert_true(name_admissible("/X1") and name_admissible("/" + "A" * 127), "admissible names")
    for bad in ("/", "/" + "A" * 128, "/A#B", "/A(B", "/A/B", "/A\x01B", "/\u00e9", "/A B", "/A%B", "X1"):
        assert_true(not name_admissible(bad), f"inadmissible {bad!r}")

    def font_keys(entries: bytes) -> bytes:
        return single_page(b"/Resources << /Font << /F1 4 0 R " + entries + b" >> >>", text(b"A"), {})

    rejected = {
        "lone /#E9 resource key": single_page(page_xobjects(b"/#E9 11 0 R"), b"", {11: form(text(b"G"))}),
        "control character": font_keys(b"/A#01B 4 0 R"),
        "number sign": font_keys(b"/A#23B 4 0 R"),
        "delimiter as #28": font_keys(b"/A#28B 4 0 R"),
        "delimiter as #2F": font_keys(b"/A#2FB 4 0 R"),
        "128 characters": font_keys(b"/" + b"A" * 128 + b" 4 0 R"),
    }
    for label, pdf in rejected.items():
        result = predict(pdf)
        assert_true(result["outcome"] == ("PARSER_AMBIGUITY", "NAME_DOMAIN"), f"{label}: {result['outcome']}")
        assert_true(result["phase"] == "P1", f"{label}: judged in P1, got {result['phase']}")
    operand = predict(single_page(page_xobjects(b"/E 11 0 R"), b"/#E9 Do\n", {11: form(text(b"G"))}))
    assert_true(operand["outcome"] == ("PARSER_AMBIGUITY", "NAME_DOMAIN"), f"operand /#E9: {operand['outcome']}")
    assert_true(operand["phase"] == "P3" and operand["evidence"]["resource_name"] == "%C3%A9", f"operand /#E9 at P4: {operand}")
    admitted = {
        "127 characters": font_keys(b"/" + b"A" * 127 + b" 4 0 R"),
        "/X#31 invoked as /X1": _row("D5_control_escaped_admissible"),
    }
    for label, pdf in admitted.items():
        result = predict(pdf)
        assert_true(result["outcome"] is None, f"{label}: {result['outcome']}")


def test_stream_mismatch_vectors() -> None:
    abbreviated = single_page(b"", b"", {5: stream(b"/F /FlateDecode", zlib.compress(text(b"C")))})
    unlisted_stream = b"5 1 obj\n" + stream(b"", text(b"C")) + b"\nendobj\n"
    non_stream = build_pdf(
        {
            1: CATALOG,
            2: b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            3: b"<< /Type /Page /Parent 2 0 R " + MEDIABOX + b" /Contents 5 1 R >>",
            5: b"<< /NotAStream true >>",
        },
        unlisted_body=unlisted_stream,
    )
    abbreviated_parms = single_page(b"", b"", {5: flate_stream(b"/DP << /Predictor 12 >>", text(b"C"))})
    for label, pdf in {
        "/F /FlateDecode without /Filter": abbreviated,
        "pdfminer.six object is not a stream": non_stream,
        "/DP abbreviation honored only by pdfminer.six": abbreviated_parms,
    }.items():
        result = predict(pdf)
        assert_true(result["outcome"] == ("PARSER_AMBIGUITY", "STREAM_MISMATCH"), f"{label}: {result['outcome']} {result['evidence']}")
        assert_true(result["phase"] == "P3" and not result["stream_records"], f"{label}: before any decoding")
        assert_true(not streams_decoded(result["document"]), f"{label}: no pdfminer.six decoding")


class DecompressAudit:
    """Records every stdlib zlib.decompress call (input SHA-256, output length)
    made while active, delegating unchanged."""

    def __init__(self) -> None:
        self.calls = []

    def __enter__(self):
        self.original = zlib.decompress
        audit = self

        def audited(data, *args, **kwargs):
            try:
                out = audit.original(data, *args, **kwargs)
            except Exception as exc:
                audit.calls.append((hashlib.sha256(bytes(data)).hexdigest(), None, type(exc).__name__))
                raise
            audit.calls.append((hashlib.sha256(bytes(data)).hexdigest(), len(out), None))
            return out

        zlib.decompress = audited
        return self

    def __exit__(self, *exc_info) -> None:
        zlib.decompress = self.original


def raw_stream_fixture() -> bytes:
    fontfile = b"dup 65 /A put\n"
    to_unicode = (
        b"/CIDInit /ProcSet findresource begin 12 dict begin begincmap\n"
        b"1 begincodespacerange <00> <FF> endcodespacerange\n"
        b"1 beginbfchar <41> <0041> endbfchar\nendcmap end end\n"
    )
    return build_pdf(
        {
            1: CATALOG,
            2: b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            3: b"<< /Type /Page /Parent 2 0 R " + MEDIABOX
            + b" /Resources << /Font << /F1 4 0 R /F2 20 0 R >> /XObject << /Fa 10 0 R /Fo 11 0 R >> >> /Contents 5 0 R >>",
            4: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /ToUnicode 22 0 R >>",
            5: flate_stream(b"", text(b"A") + b"/Fa Do\n/Fo Do\nBT /F2 12 Tf 72 600 Td (A) Tj ET\n"),
            10: flate_stream(b"/Type /XObject /Subtype /Form /BBox [0 0 612 792]", text(b"B")),
            11: flate_stream(
                b"/Type /XObject /Subtype /Form /BBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >>",
                text(b"C"),
            ),
            20: b"<< /Type /Font /Subtype /Type1 /BaseFont /CustomSerif /FirstChar 65 /LastChar 65 /Widths [600] /FontDescriptor 21 0 R >>",
            21: b"<< /Type /FontDescriptor /FontName /CustomSerif /Flags 32 /FontBBox [0 0 600 700] /ItalicAngle 0 /Ascent 700 /Descent 0 /CapHeight 700 /StemV 80 /FontFile 23 0 R >>",
            22: flate_stream(b"", to_unicode),
            23: flate_stream(b"/Length1 %d /Length2 0 /Length3 0" % len(fontfile), fontfile),
        }
    )


def test_raw_stream_bytes_identity() -> None:
    pdf = raw_stream_fixture()
    result = predict(pdf)
    assert_true(result["outcome"] is None, f"raw-stream fixture admitted: {result['outcome']} {result['evidence']}")
    records = result["stream_records"]
    classes = {record["stream_class"] for record in records}
    assert_true(classes == {"PAGE_CONTENT", "FORM_CONTENT", "FONT"}, f"pre-scanned classes {classes}")
    assert_true(not streams_decoded(result["document"]), "S6.01b decoded no pdfminer.six stream")
    by_digest = {record["raw_sha256"]: record for record in records}
    with DecompressAudit() as audit:
        observed = run_pdfminer(pdf, observe=False, document=result["document"])
    assert_true(observed["interpretation_exception"] is None, f"interpretation: {observed['interpretation_exception']}")
    assert_true(audit.calls, "pdfminer.six decompressed at S6.09")
    matched = set()
    for digest, decoded_length, error in audit.calls:
        record = by_digest.get(digest)
        assert_true(record is not None, f"pdfminer.six decompressed bytes outside RAW_STREAM_BYTES_V1: {digest}")
        assert_true(error is None and decoded_length == record["decoded_length"], f"decoded length differs for {record}")
        matched.add(record["object_id"])
    expected = {(5, 0), (10, 0), (11, 0), (22, 0), (23, 0)}
    assert_true(matched == expected, f"every pre-scanned Flate stream decoded byte-identically: {sorted(matched)}")


SRC_TEXT = (SRC_PATH / "rendered_pdf_inspection.py").read_text(encoding="utf-8")


def test_static_source_rules() -> None:
    exempt = SRC_TEXT[SRC_TEXT.index("def _unresolved_reference_exempt"):SRC_TEXT.index("# -- scopes")]
    for required in (
        "if mirror_key != canonical_key:",
        "if canonical_result is not None:",
        "if type(exc) is not PdfReadError:",
        "if exc.args != STRICT_REREAD_MISSING_OBJECT_ARGS:",
        "self.document.getobj(canonical_key[0])",
        "return type(existence_exc) is PDFObjectNotFound",
    ):
        assert_true(required in exempt, f"exemption conjunction lacks {required!r}")
    assert_true(SRC_TEXT.count("_unresolved_reference_exempt(") == 2, "exemption called from exactly one site")
    assert_true(SRC_TEXT.count("self.shadow.get_object(") == 1, "one shadow get_object site")
    assert_true('if self.phase in ("P1", "P2"):\n            self._mirror(key, obj)' in SRC_TEXT, "mirror only in P1 and P2")
    assert_true(SRC_TEXT.count("Could not find object.") == 1, "E3 message only in its exact-args constant")
    for forbidden in (
        "isinstance(exc, PdfReadError)",
        "except PdfReadError",
        "isinstance(existence_exc, PDFObjectNotFound)",
        "except PDFObjectNotFound",
        "._data",
        ".get_data(",
        "apply_configuration",
        "zlib_maximum_output_length",
        "get_configuration",
        "pdfminer.settings",
        "setrecursionlimit",
        "fitz",
        "pdfplumber",
        "pypdfium2",
    ):
        assert_true(forbidden not in SRC_TEXT, f"forbidden construct {forbidden!r} in the capability source")
    assert_true(re.search(r"(?<!self)\.decode\(", SRC_TEXT) is None, "no pdfminer.six or pypdf stream decode call")
    assert_true(SRC_TEXT.count("strict=True") == 1, "strict=True only for the strict shadow reader")
    assert_true(re.search(r"\bexcept\s*:", SRC_TEXT) is None, "no bare except")


# =============================================================================
# Dependency-free vectors: the adapter, the evidence schema, the child protocol
# and the inspection entry loaded over inert stand-in modules when the pinned
# libraries are absent. The stand-ins exist only so the module body can be
# executed; they are removed from sys.modules after loading and no vector
# below calls a PDF library through them.
# =============================================================================

ENTRY_PATH = SRC_PATH / "rendered_pdf_inspection.py"
ADAPTER_PATH = SRC_PATH / "document_render_adapter.py"
EVALUATOR_PATH = SRC_PATH / "resume_page_utilization.py"
SCHEMA_PATH = ROOT / "schemas" / "rendered_document_evidence.schema.json"
REQUIREMENTS_IN = b"jsonschema\nreferencing\n"
REQUIREMENTS_LOCK = b"jsonschema==0 --hash=sha256:" + b"0" * 64 + b"\n"
FIXTURE_ENTRY = b"LINE_GROUP_BASELINE_TOLERANCE_Q = 20\nWORD_GAP_THRESHOLD_Q = 15\n"
FIXTURE_PDF = b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF\n"
NULL_TRIPLE = (None, None, None)
_INSPECTION_MODULE = None


def _stand_in_modules() -> dict:
    def kind(name, *bases, **members):
        return type(name, bases or (object,), members)

    return {
        "pdfminer": {},
        "pdfminer.converter": {"PDFPageAggregator": kind("PDFPageAggregator")},
        "pdfminer.layout": {name: kind(name) for name in ("LTChar", "LTCurve", "LTFigure", "LTImage")},
        "pdfminer.pdfdocument": {"PDFDocument": kind("PDFDocument")},
        "pdfminer.pdfinterp": {"PDFPageInterpreter": kind("PDFPageInterpreter"),
                               "PDFResourceManager": kind("PDFResourceManager")},
        "pdfminer.pdfpage": {"PDFPage": kind("PDFPage")},
        "pdfminer.pdftypes": {"resolve1": lambda value: value, "LITERALS_FLATE_DECODE": (),
                              "PDFStream": kind("PDFStream")},
        "pdfminer.psparser": {"PSLiteral": kind("PSLiteral")},
        "pdfminer.pdfexceptions": {"PDFObjectNotFound": kind("PDFObjectNotFound", Exception)},
        "pdfminer.pdfparser": {"PDFParser": kind("PDFParser")},
        "pypdf": {"PdfReader": kind("PdfReader")},
        "pypdf.errors": {"PdfReadError": kind("PdfReadError", Exception)},
        "pypdf.generic": {
            "ArrayObject": kind("ArrayObject", list),
            "BooleanObject": kind("BooleanObject"),
            "ByteStringObject": kind("ByteStringObject", bytes),
            "ContentStream": kind("ContentStream"),
            "DecodedStreamObject": kind("DecodedStreamObject"),
            "DictionaryObject": kind("DictionaryObject", dict, raw_get=dict.__getitem__),
            "IndirectObject": kind("IndirectObject"),
            "NameObject": kind("NameObject", str),
            "NullObject": kind("NullObject"),
            "StreamObject": kind("StreamObject"),
            "TextStringObject": kind("TextStringObject", str),
        },
    }


def inspection_module():
    """The inspection entry module: the real import when the pinned
    libraries are installed, else the same source executed over stand-ins."""
    global _INSPECTION_MODULE
    if _INSPECTION_MODULE is not None:
        return _INSPECTION_MODULE
    if not MISSING_DEPENDENCIES:
        _INSPECTION_MODULE = rendered_pdf_inspection
        return _INSPECTION_MODULE
    inserted = []
    try:
        for name, members in _stand_in_modules().items():
            if name in sys.modules:
                continue
            stand_in = types.ModuleType(name)
            stand_in.__dict__.update(members)
            sys.modules[name] = stand_in
            inserted.append(name)
        spec = importlib.util.spec_from_file_location("rendered_pdf_inspection_stand_in", ENTRY_PATH)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    finally:
        for name in inserted:
            sys.modules.pop(name, None)
    _INSPECTION_MODULE = module
    return module


def outcome_of(function, *args, **kwargs):
    """(status, reason, detail, slot) of a StageFailure, else None."""
    try:
        function(*args, **kwargs)
    except adapter.StageFailure as failure:
        outcome = failure.outcome
        return (outcome.status, outcome.reason, outcome.detail, outcome.slot)
    return None


def failure_of(function, *args, **kwargs):
    try:
        function(*args, **kwargs)
    except adapter.StageFailure as failure:
        return failure.outcome
    raise AssertionError("expected a StageFailure")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# Fixtures ----------------------------------------------------------------------

_W = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'
_XML = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
_REL_NS = 'xmlns="http://schemas.openxmlformats.org/package/2006/relationships"'
_OFFICE_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/"
_MAIN_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"
_STYLES_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"


def docx_fixture(paragraphs=("Hello world",), document_xml=None, extra_parts=(), extra_doc_rels="",
                 extra_overrides="") -> bytes:
    """A minimal stdlib-written WordprocessingML package: Arial document
    defaults and one default paragraph style (fixture data only)."""
    body = "".join("<w:p><w:r><w:t>%s</w:t></w:r></w:p>" % text for text in paragraphs)
    document = document_xml or "%s<w:document %s><w:body>%s</w:body></w:document>" % (_XML, _W, body)
    parts = [
        ("[Content_Types].xml",
         _XML + '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
         '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
         '<Default Extension="xml" ContentType="application/xml"/>'
         '<Override PartName="/word/document.xml" ContentType="%s"/>'
         '<Override PartName="/word/styles.xml" ContentType="%s"/>%s</Types>'
         % (_MAIN_TYPE, _STYLES_TYPE, extra_overrides)),
        ("_rels/.rels",
         _XML + '<Relationships %s><Relationship Id="rId1" Type="%sofficeDocument" Target="word/document.xml"/>'
         "</Relationships>" % (_REL_NS, _OFFICE_REL)),
        ("word/document.xml", document),
        ("word/_rels/document.xml.rels",
         _XML + '<Relationships %s><Relationship Id="rId1" Type="%sstyles" Target="styles.xml"/>%s'
         "</Relationships>" % (_REL_NS, _OFFICE_REL, extra_doc_rels)),
        ("word/styles.xml",
         _XML + "<w:styles %s><w:docDefaults><w:rPrDefault><w:rPr>"
         '<w:rFonts w:ascii="Arial" w:hAnsi="Arial" w:cs="Arial" w:eastAsia="Arial"/><w:lang w:val="en-US"/>'
         "</w:rPr></w:rPrDefault></w:docDefaults>"
         '<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/></w:style>'
         "</w:styles>" % _W),
    ]
    parts.extend(extra_parts)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, data in parts:
            archive.writestr(name, data)
    return buffer.getvalue()


def structure_map_fixture(content_type="SUMMARY_TEXT", text="Hello world") -> list:
    return [{"paragraph_index": 0, "content_type": content_type, "list_semantics": None, "paragraph_text": text}]


def fake_manifest(approve=True, **overrides) -> dict:
    """A manifest that satisfies every data rule of verify_manifest; all
    operator-recorded values are placeholders (no provisioning instrument
    exists), and the font tables are fixture data, not Gold evidence."""
    manifest = {key: "pre:" + key for key in adapter.MANIFEST_PRE_PROVISION_KEYS}
    manifest.update({key: "post:" + key for key in adapter.MANIFEST_POST_PROVISION_KEYS})
    extraction = dict(adapter.INSPECTION_LIMITS_V1)
    extraction.update(laparams=None, line_group_baseline_tolerance_q=20, word_gap_threshold_q=15,
                      traversal_max_operations=adapter.INSPECTION_LIMITS_V1["inspection_max_traversal_operations"])
    manifest.update(adapter.SPEC_IDS_V1)
    manifest.update({
        "docx_limits": dict(adapter.DOCX_LIMITS_V1),
        "extraction_spec": extraction,
        "text_overlap_ratio_numerator": 1,
        "text_overlap_ratio_denominator": 4,
        "pdf_export_filter": adapter.build_convert_to_argument(),
        "sandbox_flags": list(adapter.REQUIRED_SANDBOX_FLAGS),
        "sandbox_tmpfs_paths": ["/run", "/tmp"],
        "sandbox_tmpfs_size_bytes": 67108864,
        "sandbox_forbidden_canary_paths": ["/home", "/root"],
        "timeout_seconds": 60,
        "source_date_epoch": 0,
        "locale": "C.UTF-8",
        "timezone": "UTC",
        "operator_python_prefix": "/opt/render/python",
        "lock_review_digest": "0" * 64,
        "sandbox_expected_unreachable_errnos": {"AF_INET": ["ENETUNREACH"],
                                                "AF_INET6": ["EADDRNOTAVAIL", "ENETUNREACH"]},
        "sandbox_symlinks": [],
        "sandbox_path": "/usr/bin:/bin",
        "fontconfig_file": "/etc/fonts/fonts.conf",
        "sandbox_dirs": [],
        "sandbox_read_only_paths": [],
        "content_binding": {"roots": [], "exclusions": []},
        "canonical_families": ["ARIAL", "LIBERATION_SANS"],
        "docx_family_to_canonical": {"arial": "ARIAL", "liberation sans": "LIBERATION_SANS"},
        "pdf_basefont_to_canonical": {
            "LiberationSans": {"canonical_family_id": "LIBERATION_SANS", "face": "REGULAR"},
            "LiberationSans-Bold": {"canonical_family_id": "LIBERATION_SANS", "face": "BOLD"},
        },
        "approved_substitutions": {"ARIAL": ["LIBERATION_SANS"]},
        "marker_glyph_map": [],
    })
    manifest.update(overrides)
    if approve:
        manifest["approved_plan_digest"] = adapter.plan_digest(manifest, REQUIREMENTS_IN, REQUIREMENTS_LOCK)
    manifest["manifest_self_digest"] = adapter.manifest_digest(manifest)
    return manifest


def manifest_bytes(manifest: dict) -> bytes:
    return adapter.canonical_json_bytes(manifest)


def _drive_free(path: str) -> str:
    """The POSIX spelling of an absolute host path (the drive is dropped on
    Windows, where the path still resolves on the current drive)."""
    return os.path.splitdrive(os.path.abspath(path))[1].replace("\\", "/")


def write_tree(root: str, files: dict) -> None:
    for relative, data in files.items():
        full = os.path.join(root, *relative.split("/"))
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "wb") as handle:
            handle.write(data)


class BoundTree:
    """A temporary operator tree bound by one TREE root (fixture only)."""

    def __init__(self, temp: str) -> None:
        self.host = os.path.join(temp, "opt")
        write_tree(self.host, {"bin/bwrap": b"bwrap", "bin/soffice": b"soffice", "python/lib/site.py": b"#\n"})
        self.posix = _drive_free(self.host)
        self.root = {"id": "r1", "kind": "TREE", "path": self.posix,
                     "expected_digest": adapter.tree_digest(self.posix)}

    def manifest(self, **overrides) -> dict:
        values = {"content_binding": {"roots": [self.root], "exclusions": []},
                  "sandbox_read_only_paths": [self.posix]}
        values.update(overrides)
        return fake_manifest(**values)

    def runtime_paths(self):
        return adapter.RuntimePaths(self.posix + "/bin/bwrap", self.posix + "/bin/soffice", (self.posix + "/python",))


# Child frames built by the test (independent of the child emitter) -------------

def encode_line(frame: dict) -> bytes:
    return (json.dumps(frame, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")


def make_frame(seq, kind, stage, outcome, triple, evidence) -> dict:
    return {"protocol": "CHILD_PROTOCOL_V1", "seq": seq, "kind": kind, "stage": stage, "outcome": outcome,
            "status": triple[0], "reason": triple[1], "detail": triple[2], "evidence": evidence}


def attestation(entry_sha256: str, pdf_sha256: str, **overrides) -> dict:
    record = {"inspection_entry_sha256": entry_sha256, "received_pdf_sha256": pdf_sha256,
              "fd_state": [[0, "pipe"], [1, "pipe"], [2, "pipe"]], "tmpdir_entries": 0,
              "pycache_state": "ABSENT", "pycache_prefix_matches": 1}
    record.update(overrides)
    return record


def span(text, font="ABCDEF+LiberationSans", size_q=110, color=(0.0,), gap_before=False) -> dict:
    return {"font": font, "size_q": size_q, "color": list(color), "text": [text], "gap_before": gap_before}


def font_entry(basefont="ABCDEF+LiberationSans", **overrides) -> dict:
    entry = {"page_index": 0, "source": "PAGE", "form_path": [], "resource_name": "F1", "object_id": "5 0",
             "subtype": "TrueType", "basefont": basefont, "descendant_basefont": None, "descriptor_present": 1,
             "descriptor_fontname": basefont, "embedded": True, "embed_key": "FontFile2"}
    entry.update(overrides)
    return entry


def pass_evidence(stage: str, entry_sha256: str, pdf_sha256: str, lines=None, fonts=None, annotations=None):
    if stage == "S5.02":
        return {"start_attestation": attestation(entry_sha256, pdf_sha256)}
    if stage == "S5.03":
        return {"catalog_keys": ["Pages", "Type"], "info_keys": None, "metadata_present": 0}
    if stage == "S6":
        return {"page_count": 1, "prescan_font_entries": len(fonts if fonts is not None else [font_entry()]),
                "pages": [{"index": 0, "width_pt": 612.0, "height_pt": 792.0, "width_q": 6120, "height_q": 7920,
                           "rotation": 0, "non_text_content": 0}]}
    if stage == "S7":
        lines = lines if lines is not None else [{"bbox": [72.0, 728.0, 150.0, 740.0], "spans": [span("Hello world")]}]
        return {"pages": [{"index": 0, "lines": lines}]}
    if stage == "S9":
        fonts = fonts if fonts is not None else [font_entry()]
        return {"font_entries": fonts,
                "assertion": {"prescan_font_entries": len(fonts), "inventory_entries": len(fonts)}}
    return {"annotations": annotations or [], "duplicates": 0}


def child_stream(entry_sha256: str, pdf_sha256: str, overrides=None, stop_after=None, final=True,
                 final_triple=None, evidence_bytes_delta=0, lines=None, fonts=None, trailing=b"") -> bytes:
    """A CHILD_PROTOCOL_V1 stream: PASS frames for every stage unless
    overridden by {stage: (outcome, triple, evidence) or raw bytes}; the
    first FAIL frame ends the stages; FINAL mirrors it."""
    overrides = overrides or {}
    out = bytearray()
    seq = 0
    failed = None
    for stage in adapter.CHILD_STAGES:
        record = overrides.get(stage)
        if isinstance(record, bytes):
            out += record
            seq += 1
        else:
            if record is None:
                record = ("PASS", NULL_TRIPLE, pass_evidence(stage, entry_sha256, pdf_sha256, lines, fonts))
            outcome, triple, evidence = record
            out += encode_line(make_frame(seq, "STAGE", stage, outcome, triple, evidence))
            seq += 1
            if outcome == "FAIL":
                failed = triple
                break
        if stage == stop_after:
            break
    if final:
        triple = final_triple or failed or NULL_TRIPLE
        out += encode_line(make_frame(seq, "FINAL", None, "PASS" if triple == NULL_TRIPLE else "FAIL", triple,
                                      {"pdf_sha256": pdf_sha256, "inspection_entry_sha256": entry_sha256,
                                       "evidence_bytes": len(out) + evidence_bytes_delta}))
    return bytes(out) + trailing


ENTRY_SHA = sha256_hex(FIXTURE_ENTRY)
PDF_SHA = sha256_hex(FIXTURE_PDF)


def analyze(stream: bytes, returncode=0, timed_out=False, cap_killed=False):
    result = adapter.ProcessResult(returncode, stdout=stream, timed_out=timed_out, cap_killed=cap_killed)
    return adapter.analyze_child_stream(stream, result, ENTRY_SHA, PDF_SHA)


def source_model(text="Hello world", content_type="SUMMARY_TEXT", manifest=None):
    manifest = manifest or fake_manifest()
    package = adapter.docx_preflight(docx_fixture((text,)))
    return adapter.build_source_model(package, manifest, structure_map_fixture(content_type, text)), manifest


def terminal(stream: bytes, model=None, manifest=None, **result) -> tuple:
    if model is None:
        model, manifest = source_model()
    context = adapter.ParentContext(manifest, model)
    outcome = adapter.resolve_terminal(analyze(stream, **result), context)
    if outcome is None:
        return None
    return (outcome.status, outcome.reason, outcome.detail, outcome.slot)


# Adapter vectors ----------------------------------------------------------------

def _module_literals(path: Path, names) -> dict:
    tree = ast.parse(path.read_bytes())
    found = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            if node.targets[0].id in names:
                try:
                    found[node.targets[0].id] = ast.literal_eval(node.value)
                except ValueError:
                    found[node.targets[0].id] = ast.unparse(node.value)
    return found


def test_entry_and_adapter_constants_agree() -> None:
    names = ("INSPECTION_LIMITS_V1", "FAIL_FRAME_RESERVE_BYTES", "TEXT_CHUNK_MAX_CHARS", "PROTOCOL_ID",
             "CHILD_STAGES", "EXPECTED_FD_STATE", "FD_STATE_MAX_ENTRIES", "FORM_DEPTH_MAX",
             "FAIL_EVIDENCE_STRING_MAX_BYTES", "FAIL_EXCEPTION_CLASS_UNREPRESENTABLE")
    entry = _module_literals(ENTRY_PATH, names)
    for name in names:
        assert_true(name in entry, f"entry defines {name} as a literal")
        assert_true(entry[name] == getattr(adapter, name), f"{name} agrees between entry and adapter")
    assert_true(adapter.FAIL_FRAME_RESERVE_BYTES == max(adapter.FAIL_FRAME_STAGE_MAXIMA_V1.values()),
                "FAIL_FRAME_RESERVE_BYTES is the largest stage maximum")
    module = inspection_module()
    assert_true(module.CHILD_FRAME_LIMITS_V1 == adapter.CHILD_FRAME_LIMITS_V1, "CHILD_FRAME_LIMITS_V1 agrees")
    assert_true(module.S7_UNOBSERVABLE_ORDER_V1[0] == "TRACKER_FAILURE", "S7.01 order starts at TRACKER_FAILURE")


def test_entry_extraction_constants_govern_s2() -> None:
    real = adapter.entry_extraction_constants(ENTRY_PATH.read_bytes())
    assert_true(real == {"LINE_GROUP_BASELINE_TOLERANCE_Q": 20, "WORD_GAP_THRESHOLD_Q": 15},
                f"the committed entry carries the approved PRE_PROVISION_PLAN extraction constants: {real}")
    manifest = fake_manifest()
    assert_true(outcome_of(adapter.check_entry_extraction_constants, manifest, ENTRY_PATH.read_bytes()) is None,
                "the committed entry constants equal the manifest extraction_spec values")
    approved = json.loads((ROOT / "docs" / "rendering" / "RENDERING_ENVIRONMENT_V1.json").read_text(encoding="utf-8"))
    assert_true((approved["extraction_spec"]["line_group_baseline_tolerance_q"],
                 approved["extraction_spec"]["word_gap_threshold_q"]) == (20, 15),
                "the approved plan carries the same two values")
    unset = b"LINE_GROUP_BASELINE_TOLERANCE_Q = None\nWORD_GAP_THRESHOLD_Q = None\n"
    result = outcome_of(adapter.check_entry_extraction_constants, manifest, unset)
    assert_true(result == ("RENDER_ENVIRONMENT_UNVERIFIED", "EXTRACTION_SPEC", None, "S2.01"),
                f"an unset entry constant never verifies: {result}")
    assert_true(outcome_of(adapter.check_entry_extraction_constants, manifest, FIXTURE_ENTRY) is None,
                "entry constants equal to the manifest verify")
    other = b"LINE_GROUP_BASELINE_TOLERANCE_Q = 21\nWORD_GAP_THRESHOLD_Q = 15\n"
    result = outcome_of(adapter.check_entry_extraction_constants, manifest, other)
    assert_true(result == ("RENDER_ENVIRONMENT_UNVERIFIED", "EXTRACTION_SPEC", None, "S2.01"),
                "a differing entry constant is EXTRACTION_SPEC")


def _maximal_fail_frame_bytes(stage: str) -> int:
    longest = "A" * 254 + "%~"
    attestation_max = {"inspection_entry_sha256": "a" * 64, "received_pdf_sha256": "b" * 64,
                       "fd_state": [[10 ** 20 - 1, longest]] * 4, "tmpdir_entries": 10 ** 20 - 1,
                       "pycache_state": "PRESENT", "pycache_prefix_matches": 0}
    values = {"start_attestation": attestation_max, "page_index": 49, "count": 10 ** 20 - 1,
              "limit": 10 ** 20 - 1, "exception_class": "E" * 64, "exception_message": longest,
              "source": "FORM", "object_id": longest, "category": "Properties", "form_path": [longest] * 8,
              "resource_name": longest}
    best = 0
    for status, reasons, details in adapter.CHILD_FAIL_CLOSED_SET_V1[stage]:
        for reason in reasons:
            for detail in details:
                if (reason, detail) == ("INSPECTION_LIMIT", "EVIDENCE_BYTES"):
                    evidence = {}
                else:
                    slots = adapter.CHILD_SLOTS_V1[stage]
                    rule = adapter._SLOT_REASON_RULES.get(reason)
                    if rule is not None:
                        slots = rule[stage]
                    evidence = {"slot": max(slots, key=len)}
                    evidence.update({key: values[key] for key in adapter.FAIL_EVIDENCE_KEYS_V1[stage]})
                frame = make_frame(6, "STAGE", stage, "FAIL", (status, reason, detail), evidence)
                best = max(best, len(encode_line(frame)))
    return best


def test_fail_frame_maxima_bound_every_encodable_frame() -> None:
    for stage in adapter.CHILD_STAGES:
        size = _maximal_fail_frame_bytes(stage)
        assert_true(size <= adapter.FAIL_FRAME_STAGE_MAXIMA_V1[stage],
                    f"{stage}: maximal FAIL frame {size} within {adapter.FAIL_FRAME_STAGE_MAXIMA_V1[stage]}")
    longest_triple = max(
        ((status, reason, detail) for stage in adapter.CHILD_STAGES
         for status, reasons, details in adapter.CHILD_FAIL_CLOSED_SET_V1[stage]
         for reason in reasons for detail in details),
        key=lambda triple: len(json.dumps(list(triple))),
    )
    final = make_frame(6, "FINAL", None, "FAIL", longest_triple,
                       {"pdf_sha256": "a" * 64, "inspection_entry_sha256": "b" * 64,
                        "evidence_bytes": adapter.INSPECTION_LIMITS_V1["inspection_max_evidence_bytes"]})
    assert_true(len(encode_line(final)) <= adapter.FINAL_FRAME_LEGITIMATE_MAX_BYTES,
                f"maximal FINAL frame {len(encode_line(final))} within {adapter.FINAL_FRAME_LEGITIMATE_MAX_BYTES}")
    evidence_bytes = max(
        len(encode_line(make_frame(6, "STAGE", stage, "FAIL",
                                   ("RENDER_PDF_INSPECTION_FAILED", "INSPECTION_LIMIT", "EVIDENCE_BYTES"), {})))
        for stage in adapter.CHILD_STAGES
    )
    assert_true(evidence_bytes <= adapter.EVIDENCE_BYTES_FRAME_MAX_BYTES, "EVIDENCE_BYTES frame within its maximum")
    assert_true(adapter.FINAL_FRAME_MAX_BYTES >= adapter.FINAL_FRAME_LEGITIMATE_MAX_BYTES, "FINAL read allowance")


def test_text_uri_and_quantization_vectors() -> None:
    assert_true(adapter.tokenize("Hello\u00a0 wor\u00adld\u2011x") == ["Hello", "world-x"], "TEXT_NORMALIZATION_V1")
    assert_true(adapter.tokenize("\ufb01ne") == ["fine"], "NFKC ligature fold")
    vectors = {
        "HTTPS://Example.COM": "https://example.com/",
        "http://a.example:80/x": "http://a.example/x",
        "https://a.example:443": "https://a.example/",
        "https://a.example:8443/p?q#f": "https://a.example:8443/p?q#f",
        "https://a.example/%7euser/%2f": "https://a.example/~user/%2F",
        "mailto:bora%40example.com": "mailto:bora%40example.com",
        "javascript:alert(1)": None,
        "ftp://a.example/": None,
        "http://user@a.example/": None,
        " http://a.example/": None,
        "http://a.example/ x": None,
        "https://a.example:0/": None,
        "https://a.example:99999/": None,
        "http://\u00e4.example/": None,
        "http:/a.example": None,
        "": None,
    }
    module = inspection_module()
    for raw, expected in vectors.items():
        assert_true(adapter.canonicalize_uri(raw) == expected, f"adapter URI {raw!r} -> {expected!r}")
        assert_true(module.canonicalize_uri(raw) == expected, f"entry URI {raw!r} -> {expected!r}")
    for text in ("a\u00a0b", "x\u200by", "\u3000lead", "tab\tsep"):
        assert_true(module.tokenize(text) == adapter.tokenize(text), f"tokenize parity {text!r}")
    for value, expected in ((0.25, 2), (0.75, 8), (-0.25, -2), (612.0, 6120), (0.05, 1), (791.99, 7920)):
        assert_true(adapter.quantize(value) == expected, f"adapter quantize({value}) == {expected}")
        assert_true(module.quantize(value) == expected, f"entry quantize({value}) == {expected}")


def test_fail_string_and_identifier_grammar() -> None:
    for value, valid in (("abc", True), ("%41%~", True), ("%~", True), ("", True), ("a" * 256, True),
                         ("a" * 257, False), ("%4", False), ("%4g", False), ('"', False), ("\\", False),
                         ("abc\n", False), ("caf\u00e9", False), ("%a1", False)):
        assert_true(adapter.fail_string_valid(value) is valid, f"FAIL_EVIDENCE_STRING_V1 {value!r} -> {valid}")
    for value, valid in (("ValueError", True), ("<UNREPRESENTABLE>", True), ("_X1", True), ("1X", False),
                         ("A" * 65, False), ("Error\n", False), ("a.b", False)):
        assert_true(adapter.exception_class_valid(value) is valid, f"FAIL_EXCEPTION_CLASS_V1 {value!r} -> {valid}")
    assert_true(adapter._HEX64.match("a" * 64 + "\n") is None, "a digest with a trailing LF is not a digest")
    module = inspection_module()
    for text in ('a"b', "\u00e9" * 300, "plain", "%", "x\ny"):
        assert_true(adapter.fail_string_valid(module.fail_evidence_string(text)), f"entry encoder output valid {text!r}")


def test_docx_preflight_vectors() -> None:
    package = adapter.docx_preflight(docx_fixture())
    assert_true(type(package).__name__ == "DocxPackage", "the minimal fixture passes S1")
    vectors = [
        (b"", ("RENDER_DOCX_PACKAGE_INVALID", "NOT_ZIP_OR_CORRUPT", None, "S1.02")),
        (b"not a zip archive", ("RENDER_DOCX_PACKAGE_INVALID", "NOT_ZIP_OR_CORRUPT", None, "S1.02")),
        (b"PK\x03\x04" + b"\0" * 64, ("RENDER_DOCX_PACKAGE_INVALID", "NOT_ZIP_OR_CORRUPT", None, "S1.02")),
    ]
    for data, expected in vectors:
        assert_true(outcome_of(adapter.docx_preflight, data) == expected, f"S1 vector {data[:12]!r}")
    oversized = outcome_of(adapter.docx_preflight, b"\0" * (adapter.DOCX_LIMITS_V1["max_input_bytes"] + 1))
    assert_true(oversized is not None and oversized[0] == "RENDER_DOCX_LIMIT_EXCEEDED", f"input size limit: {oversized}")
    traversal = outcome_of(adapter.docx_preflight, docx_fixture(extra_parts=[("../evil.xml", "<x/>")]))
    assert_true(traversal is not None and traversal[:2] == ("RENDER_DOCX_PACKAGE_INVALID", "UNSAFE_PATH"),
                f"path traversal entry: {traversal}")
    dtd = docx_fixture(document_xml=_XML + '<!DOCTYPE x [<!ENTITY e "x">]><w:document %s><w:body/></w:document>' % _W)
    result = outcome_of(adapter.docx_preflight, dtd)
    assert_true(result is not None and result[:2] == ("RENDER_DOCX_PACKAGE_INVALID", "DTD_OR_ENTITY"),
                f"DTD in a part: {result}")
    macro = outcome_of(adapter.docx_preflight, docx_fixture(extra_parts=[("word/vbaProject.bin", b"\0")]))
    assert_true(macro is not None and macro[0] == "RENDER_DOCX_PACKAGE_INVALID", f"macro part: {macro}")
    external = docx_fixture(extra_doc_rels='<Relationship Id="rId9" Type="%simage" Target="file:///etc/passwd" '
                                           'TargetMode="External"/>' % _OFFICE_REL)
    result = outcome_of(adapter.docx_preflight, external)
    assert_true(result is not None and result[0] in ("RENDER_EXTERNAL_REFERENCE_DENIED", "RENDER_DOCX_PACKAGE_INVALID"),
                f"external non-hyperlink relationship: {result}")
    data = docx_fixture()
    before = bytes(data)
    adapter.docx_preflight(data)
    assert_true(data == before, "pre-flight never mutates the input bytes")


def test_manifest_vectors() -> None:
    base = fake_manifest()
    assert_true(adapter.verify_manifest(manifest_bytes(base)) == base, "the fixture manifest verifies")

    def reason(data) -> tuple:
        return outcome_of(adapter.verify_manifest, data)

    def unverified(name):
        return ("RENDER_ENVIRONMENT_UNVERIFIED", name, None, "S2.01")

    assert_true(reason(None) == unverified("MANIFEST_ABSENT"), "absent manifest")
    assert_true(reason(b"{") == unverified("MANIFEST_MALFORMED"), "malformed manifest")
    assert_true(reason(b"[]") == unverified("MANIFEST_MALFORMED"), "non-object manifest")
    assert_true(reason(b'{"a":1,"a":2}') == unverified("MANIFEST_MALFORMED"), "duplicate keys")
    assert_true(reason(manifest_bytes(fake_manifest(timeout_seconds=1.5))) == unverified("MANIFEST_NON_INTEGER"),
                "non-integer number")
    extra = dict(base, zz_unknown="x")
    assert_true(reason(manifest_bytes(extra)) == unverified("MANIFEST_KEY_UNPARTITIONED"), "unpartitioned key")
    missing = dict(base)
    del missing["timezone"]
    assert_true(reason(manifest_bytes(missing)) == unverified("MANIFEST_KEY_MISSING"), "missing key")
    assert_true(reason(manifest_bytes(fake_manifest(sandbox_path=None))) == unverified("POST_BINDING_UNPOPULATED"),
                "null POST_PROVISION_BINDING key")
    assert_true(reason(manifest_bytes(dict(base, manifest_self_digest="0" * 64))) == unverified("MANIFEST_SELF_DIGEST"),
                "self digest")
    for overrides, name in (
        ({"sandbox_dirs": ["/b", "/a"]}, "MANIFEST_SET_UNSORTED"),
        ({"docx_limits": dict(adapter.DOCX_LIMITS_V1, max_entries=1)}, "DOCX_LIMITS"),
        ({"extraction_spec": dict(base["extraction_spec"], laparams={})}, "EXTRACTION_SPEC"),
        ({"text_overlap_ratio_numerator": 2}, "TEXT_OVERLAP_RATIO"),
        ({"geometry_spec_id": "X"}, "SPEC_ID"),
        ({"pdf_export_filter": "pdf"}, "PDF_EXPORT_FILTER"),
        ({"sandbox_flags": list(adapter.REQUIRED_SANDBOX_FLAGS)[1:]}, "SANDBOX_FLAGS"),
        ({"sandbox_tmpfs_paths": ["/run", "/var"]}, "SANDBOX_TMPFS"),
        ({"sandbox_tmpfs_size_bytes": 0}, "SANDBOX_TMPFS"),
        ({"sandbox_expected_unreachable_errnos": {"AF_INET": ["EACCES"], "AF_INET6": ["ENETUNREACH"]}}, "ERRNO_SET"),
        ({"timeout_seconds": 0}, "TIMEOUT"),
        ({"pdf_basefont_to_canonical": {"X": {"canonical_family_id": "ARIAL", "face": "HEAVY"}}}, "FONT_TABLES"),
        ({"docx_family_to_canonical": {"arial": "UNKNOWN"}}, "FONT_TABLES"),
    ):
        result = reason(manifest_bytes(fake_manifest(**overrides)))
        assert_true(result == unverified(name), f"{sorted(overrides)} -> {name}: {result}")


def test_plan_digest_partition_vectors() -> None:
    base = fake_manifest()
    post_changed = fake_manifest(sandbox_path="/other", fontconfig_file="/x.conf")
    assert_true(adapter.pre_provision_plan_digest(base) == adapter.pre_provision_plan_digest(post_changed),
                "POST_PROVISION_BINDING fields do not affect pre_provision_plan_digest")
    pre_changed = fake_manifest(timezone="Europe/Berlin")
    assert_true(adapter.pre_provision_plan_digest(base) != adapter.pre_provision_plan_digest(pre_changed),
                "a PRE_PROVISION_PLAN field changes pre_provision_plan_digest")
    assert_true(adapter.plan_digest(base, REQUIREMENTS_IN, REQUIREMENTS_LOCK)
                != adapter.plan_digest(base, REQUIREMENTS_IN + b"x\n", REQUIREMENTS_LOCK),
                "requirements_in_sha256 is part of the plan digest")
    amended = dict(base, timezone="Europe/Berlin")
    amended["manifest_self_digest"] = adapter.manifest_digest(amended)
    plan = (REQUIREMENTS_IN, REQUIREMENTS_LOCK)
    result = outcome_of(adapter.verify_environment, manifest_bytes(amended), lambda m: None, plan, None, FIXTURE_ENTRY)
    assert_true(result == ("RENDER_ENVIRONMENT_UNVERIFIED", "PLAN_DIGEST", None, "S2.01"),
                f"PLAN_AMENDMENT_LOOP_V1: an amended PRE field invalidates the approval: {result}")
    for inputs in (None, (REQUIREMENTS_IN, None), (REQUIREMENTS_IN, b"other")):
        result = outcome_of(adapter.verify_environment, manifest_bytes(base), lambda m: None, inputs, None,
                            FIXTURE_ENTRY)
        assert_true(result == ("RENDER_ENVIRONMENT_UNVERIFIED", "PLAN_DIGEST", None, "S2.01"),
                    f"plan inputs {inputs!r:.40} -> PLAN_DIGEST")
    result = outcome_of(adapter.verify_environment, manifest_bytes(base), None, plan, None, FIXTURE_ENTRY)
    assert_true(result == ("RENDER_ENVIRONMENT_UNVERIFIED", "LIVE_VERIFICATION_UNAVAILABLE", None, "S2.01"),
                "an absent operator verifier fails closed")
    result = outcome_of(adapter.verify_environment, manifest_bytes(base), lambda m: "FONT_FILE_MISSING", plan, None,
                        FIXTURE_ENTRY)
    assert_true(result == ("RENDER_ENVIRONMENT_UNVERIFIED", "FONT_FILE_MISSING", None, "S2.01"),
                "the live verifier's reason is the S2.01 reason")

    def raising(_):
        raise OSError("probe")

    result = outcome_of(adapter.verify_environment, manifest_bytes(base), raising, plan, None, FIXTURE_ENTRY)
    assert_true(result == ("RENDER_ENVIRONMENT_UNVERIFIED", "LIVE_VERIFICATION_FAILED", None, "S2.01"),
                "a raising verifier fails closed")
    environment = adapter.verify_environment(manifest_bytes(base), lambda m: None, plan, None, FIXTURE_ENTRY)
    assert_true(environment.root_digests == [] and environment.manifest_digest == adapter.manifest_digest(base),
                "an empty binding verifies with no roots")


def tree_known_answer(host: str) -> str:
    """TREE_DIGEST_V1 by plain string assembly (TREE_DIGEST_EXTERNAL_V1 form)."""
    records = []
    for relpath, data in (("bin/bwrap", b"bwrap"), ("bin/soffice", b"soffice"), ("python/lib/site.py", b"#\n")):
        exec_bit = 1 if os.stat(os.path.join(host, *relpath.split("/"))).st_mode & stat.S_IXUSR else 0
        records.append(f'["F","{relpath}",{exec_bit},"{hashlib.sha256(data).hexdigest()}"]')
    if os.path.isdir(os.path.join(host, "share", "empty")):
        records.append('["D","share/empty"]')
    return hashlib.sha256(("[" + ",".join(records) + "]").encode("ascii")).hexdigest()


def test_content_binding_vectors() -> None:
    temp = tempfile.mkdtemp(prefix="render-binding-")
    try:
        tree = BoundTree(temp)
        tree_kat = tree_known_answer(tree.host)
        assert_true(adapter.tree_digest(tree.posix) == tree_kat,
                    f"TREE_DIGEST_V1 known answer: {adapter.tree_digest(tree.posix)} != {tree_kat}")
        os.makedirs(os.path.join(tree.host, "share", "empty"))
        assert_true(adapter.tree_digest(tree.posix) == tree_known_answer(tree.host) != tree_kat,
                    "TREE_DIGEST_V1 records an empty directory")
        os.rmdir(os.path.join(tree.host, "share", "empty"))
        os.rmdir(os.path.join(tree.host, "share"))
        plan = (REQUIREMENTS_IN, REQUIREMENTS_LOCK)
        manifest = tree.manifest()
        environment = adapter.verify_environment(manifest_bytes(manifest), lambda m: None, plan, None, FIXTURE_ENTRY)
        expected_binding = adapter.canonical_digest([["r1", tree_kat]])
        assert_true(environment.content_binding_digest == expected_binding, "content_binding_digest")
        assert_true(environment.runtime_manifest_digest == adapter.canonical_digest(
            {"spec": "RUNTIME_MANIFEST_BINDING_V1", "manifest_digest": adapter.manifest_digest(manifest),
             "content_binding_digest": expected_binding}), "runtime_manifest_digest")
        uncovered = tree.manifest(sandbox_read_only_paths=sorted([tree.posix, "/usr/share/uncovered"]))
        result = outcome_of(adapter.verify_environment, manifest_bytes(uncovered), lambda m: None, plan, None,
                            FIXTURE_ENTRY)
        assert_true(result == ("RENDER_CONTENT_BINDING_INCOMPLETE", "MOUNT_COVERAGE", None, "S2.02"),
                    f"an uncovered read-only mount: {result}")
        with open(os.path.join(tree.host, "bin", "soffice"), "ab") as handle:
            handle.write(b"!")
        result = outcome_of(adapter.verify_environment, manifest_bytes(manifest), lambda m: None, plan, None,
                            FIXTURE_ENTRY)
        assert_true(result == ("RENDER_CONTENT_BINDING_MISMATCH", "DIGEST", None, "S2.03"),
                    f"a one-byte change to a covered file: {result}")
        absent = {"id": "r0", "kind": "ABSENT", "path": tree.posix + "/absent", "expected_digest": adapter.ABSENT_ROOT_DIGEST}
        assert_true(adapter.root_digest(absent, (), {}) == adapter.ABSENT_ROOT_DIGEST, "ABSENT root")
        absent_present = dict(absent, path=tree.posix + "/bin")
        assert_true(_raises(adapter.ContentBindingFailure, adapter.root_digest, absent_present, (), {}),
                    "an ABSENT root that exists is a mismatch")
    finally:
        shutil.rmtree(temp, ignore_errors=True)


def _raises(kind, function, *args) -> bool:
    try:
        function(*args)
    except kind:
        return True
    return False


def test_sandbox_argv_profile_and_isolation() -> None:
    temp = tempfile.mkdtemp(prefix="render-argv-")
    try:
        tree = BoundTree(temp)
        manifest = tree.manifest()
        paths = tree.runtime_paths()
        render = adapter.build_argv_shared(manifest, adapter.PROFILE_RENDER)
        inspection = adapter.build_argv_shared(manifest, adapter.PROFILE_INSPECTION, paths.inspection_read_only_paths)
        for argv in (render, inspection):
            assert_true(argv[:len(adapter.REQUIRED_SANDBOX_FLAGS)] == list(adapter.REQUIRED_SANDBOX_FLAGS),
                        "required flags lead the argv")
            assert_true(argv[len(adapter.REQUIRED_SANDBOX_FLAGS)] == "--clearenv", "environment cleared")
            assert_true("--share-net" not in argv and "--bind-try" not in argv, "no network share, no optional binds")
            assert_true(argv[-2:] == ["--remount-ro", "/"], "root remounted read-only last")
        render_env = [item for index, item in enumerate(render) if index and render[index - 1] == "--setenv"]
        assert_true(sorted(render_env) == sorted(adapter.RENDER_ENV_NAMES), f"render env allowlist {render_env}")
        assert_true("FONTCONFIG_FILE" not in [item for index, item in enumerate(inspection)
                                              if index and inspection[index - 1] == "--setenv"],
                    "the inspection profile has no fontconfig")
        assert_true(adapter.ENTRY_FD_PLACEHOLDER in inspection and adapter.RUN_OUTPUT_PLACEHOLDER in render,
                    "per-run placeholders")
        digest_a = adapter.sandbox_profile_digest(manifest, adapter.PROFILE_RENDER)
        assert_true(digest_a == adapter.sandbox_profile_digest(tree.manifest(), adapter.PROFILE_RENDER),
                    "profile digest deterministic")
        assert_true(digest_a != adapter.sandbox_profile_digest(manifest, adapter.PROFILE_INSPECTION,
                                                               paths.inspection_read_only_paths),
                    "render and inspection profiles differ")
        assert_true(digest_a != adapter.sandbox_profile_digest(tree.manifest(timezone="Etc/GMT"),
                                                               adapter.PROFILE_RENDER),
                    "a profile input changes the digest")
        conversion = adapter.conversion_argv(paths.soffice_path, manifest)
        assert_true(conversion[0] == paths.soffice_path and "--headless" in conversion
                    and conversion[conversion.index("--convert-to") + 1] == adapter.build_convert_to_argument(),
                    "conversion argv")
        assert_true(adapter.inspection_argv(manifest) == [
            "/opt/render/python/bin/python", "-I", "-S", "-B", "-X",
            "pycache_prefix=" + adapter.INSPECTION_PYCACHE_PATH, adapter.SANDBOX_ENTRY_PATH], "inspection argv")
        assert_true(outcome_of(adapter.check_runtime_paths, manifest, paths) is None, "bound runtime paths pass")
        unbound = adapter.RuntimePaths("/usr/bin/bwrap", paths.soffice_path, paths.inspection_read_only_paths)
        assert_true(outcome_of(adapter.check_runtime_paths, manifest, unbound)
                    == ("RENDER_ISOLATION_UNAVAILABLE", "EXECUTABLE_UNBOUND", None, "S4.01"), "unbound bwrap")
        bad_mount = adapter.RuntimePaths(paths.bwrap_path, paths.soffice_path, ("/home/bora",))
        assert_true(outcome_of(adapter.check_runtime_paths, manifest, bad_mount)
                    == ("RENDER_ISOLATION_UNAVAILABLE", "INSPECTION_MOUNT_UNBOUND", None, "S4.02"),
                    "an inspection mount under a canary")
    finally:
        shutil.rmtree(temp, ignore_errors=True)


def test_temp_layout_snapshot_and_delivery() -> None:
    temp = tempfile.mkdtemp(prefix="render-layout-")
    try:
        layout = adapter.RunTempLayout(temp).__enter__()
        assert_true(sorted(os.listdir(layout.root)) == ["input", "output", "profile"], "per-run layout")
        result = failure_of(adapter.take_pdf_snapshot, layout.output_dir)
        assert_true((result.status, result.reason) == ("RENDER_SANDBOX_RUNTIME_INCOMPLETE", "OUTPUT_INVALID"),
                    f"missing output: {result}")
        output = os.path.join(layout.output_dir, adapter.OUTPUT_FILE_NAME)
        for data, label in ((b"", "EMPTY"), (b"PK\x03\x04", "SIGNATURE")):
            with open(output, "wb") as handle:
                handle.write(data)
            result = failure_of(adapter.take_pdf_snapshot, layout.output_dir)
            assert_true(result.reason == "OUTPUT_INVALID", f"{label}: {result}")
        with open(output, "wb") as handle:
            handle.write(FIXTURE_PDF)
        snapshot = adapter.take_pdf_snapshot(layout.output_dir)
        assert_true(snapshot == FIXTURE_PDF, "the snapshot is the raw PDF bytes, unchanged")
        os.mkdir(os.path.join(layout.output_dir, "extra"))
        result = failure_of(adapter.take_pdf_snapshot, layout.output_dir)
        assert_true(result.reason == "OUTPUT_INVALID", "an extra output entry is NOT_REGULAR")
        delivery = os.path.join(temp, "delivery")
        os.mkdir(delivery)
        path = adapter.deliver_pdf(snapshot, sha256_hex(snapshot), delivery)
        with open(path, "rb") as handle:
            assert_true(handle.read() == FIXTURE_PDF, "delivered bytes equal the snapshot")
        result = failure_of(adapter.deliver_pdf, snapshot, sha256_hex(snapshot), delivery)
        assert_true((result.status, result.slot) == ("RENDER_DELIVERY_BYTES_MISMATCH", "S12.01"),
                    "an existing delivery target is never overwritten")
        root = layout.root
        layout.__exit__(None, None, None)
        assert_true(layout.removed and not os.path.lexists(root), "the per-run root is removed")
    finally:
        shutil.rmtree(temp, ignore_errors=True)


# Evidence schema ----------------------------------------------------------------

_SCHEMA_VALIDATORS = {}


def schema_validator(definition: str):
    """jsonschema validator for one definition; JSON integers are exact
    integers here (a float such as 1.0 is not an integer)."""
    if definition in _SCHEMA_VALIDATORS:
        return _SCHEMA_VALIDATORS[definition]
    import jsonschema

    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator.check_schema(schema)
    checker = jsonschema.Draft202012Validator.TYPE_CHECKER.redefine(
        "integer", lambda _, value: isinstance(value, int) and not isinstance(value, bool)
    )
    strict = jsonschema.validators.extend(jsonschema.Draft202012Validator, type_checker=checker)
    target = dict(schema)
    if definition != "evidence_record":
        target["$ref"] = "#/$defs/" + definition
    validator = strict(target)
    _SCHEMA_VALIDATORS[definition] = validator
    return validator


def stdlib_frame_valid(frame) -> bool:
    try:
        adapter.validate_frame_shape(frame)
        if frame["kind"] == "STAGE" and frame["outcome"] == "FAIL":
            adapter.validate_fail_evidence(frame["stage"], frame, 0)
    except adapter.ProtocolDefect:
        return False
    return True


def schema_frame_valid(frame) -> bool:
    return schema_validator("child_frame").is_valid(frame)


def _fail(stage, status, reason, detail, **evidence):
    record = {"slot": evidence.pop("slot", adapter.CHILD_SLOTS_V1[stage][0])}
    record.update(evidence)
    if stage == "S5.02":
        record.setdefault("start_attestation", attestation(ENTRY_SHA, PDF_SHA))
    return make_frame(2, "STAGE", stage, "FAIL", (status, reason, detail), record)


def child_frame_fixtures() -> list:
    """(label, frame, expected validity) over the F4 and F1 closed-set
    vectors and the generic shape vectors."""
    rows = []
    limit = ("RENDER_PDF_INSPECTION_FAILED", "INSPECTION_LIMIT")
    rows.append(("S6 CROPBOX_DIFFERS", _fail("S6", "RENDER_PAGEBOX_MISMATCH", "CROPBOX_DIFFERS", None,
                                             slot="S6.05", page_index=0), True))
    rows.append(("S6 CROPBOX_DIFFERS/FOO", _fail("S6", "RENDER_PAGEBOX_MISMATCH", "CROPBOX_DIFFERS", "FOO",
                                                 slot="S6.05"), False))
    for stage in adapter.CHILD_STAGES:
        rows.append((f"{stage} MEMORY", _fail(stage, *limit, "MEMORY", slot=adapter.CHILD_SLOTS_V1[stage][0]), True))
        evidence_bytes = make_frame(2, "STAGE", stage, "FAIL", limit + ("EVIDENCE_BYTES",), {})
        rows.append((f"{stage} EVIDENCE_BYTES", evidence_bytes, stage != "S5.02"))
        for detail in ("ZLIB_ERROR", "FLATE_INCOMPLETE", "OBJECT_READ", "RAW_BYTES_READ", "CONTENT_PARSE"):
            slot = "S6.01b" if stage == "S6" else adapter.CHILD_SLOTS_V1[stage][0]
            rows.append((f"{stage} PRE_SCAN_READ/{detail}",
                         _fail(stage, "RENDER_PDF_INSPECTION_FAILED", "PRE_SCAN_READ", detail, slot=slot),
                         stage == "S6"))
        rows.append((f"{stage} INDIRECT_RESOLUTIONS",
                     _fail(stage, *limit, "INDIRECT_RESOLUTIONS", slot=adapter.CHILD_SLOTS_V1[stage][-1]),
                     stage in ("S6", "S7", "S9", "S10")))
        rows.append((f"{stage} TRACKER_FAILURE",
                     _fail(stage, "RENDER_TEXT_STATE_UNOBSERVABLE", "TRACKER_FAILURE", None,
                           slot=adapter.CHILD_SLOTS_V1[stage][0]), stage == "S7"))
        for reason, stages in (("PAGE_ENUMERATION", ("S6",)), ("FONT_TRAVERSAL", ("S9",)),
                               ("ANNOTATION_READ", ("S10",)), ("CHAR_EXTRACTION", ("S6", "S7"))):
            slot = {"PAGE_ENUMERATION": "S6.01"}.get(reason, adapter.CHILD_SLOTS_V1[stage][-1])
            rows.append((f"{stage} {reason}", _fail(stage, "RENDER_PDF_INSPECTION_FAILED", reason, None, slot=slot),
                         stage in stages))
        state_slot = {"S5.03": "S5.03", "S6": "S6.06a"}.get(stage, adapter.CHILD_SLOTS_V1[stage][0])
        rows.append((f"{stage} DOCUMENT_STATE_READ",
                     _fail(stage, "RENDER_PDF_INSPECTION_FAILED", "DOCUMENT_STATE_READ", None, slot=state_slot),
                     stage in ("S5.03", "S6")))
    rows.append(("S6 PAGE_FACTS at S6.06a", _fail("S6", "RENDER_PDF_INSPECTION_FAILED", "PAGE_FACTS", None,
                                                  slot="S6.06a"), False))
    rows.append(("S6 DOCUMENT_STATE_READ at S6.03", _fail("S6", "RENDER_PDF_INSPECTION_FAILED",
                                                          "DOCUMENT_STATE_READ", None, slot="S6.03"), False))
    rows.append(("S5.03 INDIRECT_RESOLUTIONS", _fail("S5.03", *limit, "INDIRECT_RESOLUTIONS", slot="S5.03"), False))
    rows.append(("S9 UNMAPPED_NAME_FORM (parent slot)", _fail("S9", "RENDER_FONT_SUBSTITUTION_UNAPPROVED",
                                                              "UNMAPPED_NAME_FORM", None, slot="S9.02"), False))
    rows.append(("S10 RENDER_LINK_FABRICATED (parent slot)", _fail("S10", "RENDER_LINK_FABRICATED", None, None,
                                                                   slot="S10.05"), False))
    rows.append(("S8 status in a child frame", _fail("S7", "RENDER_ATTRIBUTION_INCOMPLETE", "TOKEN_MISMATCH", None,
                                                     slot="S7.04"), False))
    rows.append(("S7 CHAR_UNOBSERVABLE", _fail("S7", "RENDER_ATTRIBUTION_INCOMPLETE", "CHAR_UNOBSERVABLE", None,
                                               slot="S7.04", page_index=0), True))
    rows.append(("unknown evidence key", _fail("S6", "RENDER_PAGE_ROTATION_DENIED", None, None, slot="S6.02",
                                               colour="red"), False))
    rows.append(("bad exception class", _fail("S6", "RENDER_PDF_INSPECTION_FAILED", "PAGE_FACTS", None, slot="S6.02",
                                              exception_class="a.b"), False))
    rows.append(("bad fail string", _fail("S9", "RENDER_FONT_TYPE3_DENIED", None, None, slot="S9.01",
                                          resource_name="a\"b"), False))
    rows.append(("page index out of range", _fail("S6", "RENDER_PAGE_ROTATION_DENIED", None, None, slot="S6.02",
                                                  page_index=50), False))
    rows.append(("bool count", _fail("S6", *limit, "PAGE_COUNT", slot="S6.01a", count=True), False))
    rows.append(("S5.02 without attestation", make_frame(0, "STAGE", "S5.02", "FAIL",
                                                         ("RENDER_SANDBOX_RUNTIME_INCOMPLETE", "OUTPUT_INVALID",
                                                          "ENCRYPTED"), {"slot": "S5.02"}), False))
    for stage in adapter.CHILD_STAGES:
        rows.append((f"{stage} PASS", make_frame(0, "STAGE", stage, "PASS", NULL_TRIPLE,
                                                 pass_evidence(stage, ENTRY_SHA, PDF_SHA)), True))
    final = make_frame(6, "FINAL", None, "PASS", NULL_TRIPLE,
                       {"pdf_sha256": PDF_SHA, "inspection_entry_sha256": ENTRY_SHA, "evidence_bytes": 10})
    rows.append(("FINAL PASS", final, True))
    rows.append(("FINAL FAIL mirror", dict(final, outcome="FAIL", status="RENDER_PAGE_ROTATION_DENIED"), True))
    rows.append(("FINAL FAIL unknown triple", dict(final, outcome="FAIL", status="RENDER_NOPE"), False))
    rows.append(("FINAL with stage", dict(final, stage="S6"), False))
    rows.append(("FINAL digest with LF", dict(final, evidence=dict(final["evidence"], pdf_sha256=PDF_SHA + "\n")), False))
    rows.append(("FINAL upper-case digest", dict(final, evidence=dict(final["evidence"], pdf_sha256=PDF_SHA.upper())),
                 False))
    rows.append(("seq as float", dict(final, seq=6.0), False))
    rows.append(("seq out of range", dict(final, seq=7), False))
    rows.append(("unknown frame key", dict(final, extra=1), False))
    rows.append(("missing frame key", {key: value for key, value in final.items() if key != "detail"}, False))
    rows.append(("wrong protocol", dict(final, protocol="CHILD_PROTOCOL_V2"), False))
    s7 = pass_evidence("S7", ENTRY_SHA, PDF_SHA)
    s7["pages"][0]["lines"][0]["spans"][0]["color"] = [0.0, 0.0]
    rows.append(("S7 two-component colour", make_frame(3, "STAGE", "S7", "PASS", NULL_TRIPLE, s7), False))
    s7 = pass_evidence("S7", ENTRY_SHA, PDF_SHA)
    s7["pages"][0]["lines"][0]["spans"][0]["text"] = ["x" * 1025]
    rows.append(("S7 chunk too long", make_frame(3, "STAGE", "S7", "PASS", NULL_TRIPLE, s7), False))
    s7 = pass_evidence("S7", ENTRY_SHA, PDF_SHA)
    s7["pages"][0]["lines"][0]["bbox"][0] = 1e16
    rows.append(("S7 coordinate out of range", make_frame(3, "STAGE", "S7", "PASS", NULL_TRIPLE, s7), False))
    s7 = pass_evidence("S7", ENTRY_SHA, PDF_SHA, lines=[{"bbox": [0.0, 0.0, 1.0, 1.0], "spans": []}])
    rows.append(("S7 line without spans", make_frame(3, "STAGE", "S7", "PASS", NULL_TRIPLE, s7), False))
    s6 = pass_evidence("S6", ENTRY_SHA, PDF_SHA)
    s6["pages"][0]["rotation"] = 90
    rows.append(("S6 rotation 90", make_frame(2, "STAGE", "S6", "PASS", NULL_TRIPLE, s6), False))
    s10 = pass_evidence("S10", ENTRY_SHA, PDF_SHA, annotations=[
        {"page_index": 0, "annot_index": 0, "subtype": "Link", "rect_ccs": [1.0, 2.0, 3.0, 4.0], "kind": "LINK_URI",
         "uri": "https://example.com/", "goto_page": None, "words_text": ["Hello"]}])
    rows.append(("S10 URI annotation", make_frame(5, "STAGE", "S10", "PASS", NULL_TRIPLE, s10), True))
    s10_bad = json.loads(json.dumps(s10))
    s10_bad["annotations"][0]["goto_page"] = 0
    rows.append(("S10 URI annotation with goto_page", make_frame(5, "STAGE", "S10", "PASS", NULL_TRIPLE, s10_bad),
                 False))
    s9 = pass_evidence("S9", ENTRY_SHA, PDF_SHA, fonts=[font_entry(embed_key="FontFile4")])
    rows.append(("S9 unknown embed key", make_frame(4, "STAGE", "S9", "PASS", NULL_TRIPLE, s9), False))
    s502 = pass_evidence("S5.02", ENTRY_SHA, PDF_SHA)
    s502["start_attestation"]["fd_state"] = [[0, "pipe"]] * 5
    rows.append(("S5.02 fd_state over four", make_frame(0, "STAGE", "S5.02", "PASS", NULL_TRIPLE, s502), False))
    return rows


def test_child_frame_validator_equals_schema() -> None:
    for label, frame, expected in child_frame_fixtures():
        stdlib = stdlib_frame_valid(frame)
        schema = schema_frame_valid(frame)
        assert_true(stdlib is expected, f"stdlib child-frame validator on {label}: {stdlib}, expected {expected}")
        assert_true(schema is expected, f"schema child_frame on {label}: {schema}, expected {expected}")
    non_monotonic = make_frame(0, "STAGE", "S5.02", "PASS", NULL_TRIPLE,
                               {"start_attestation": attestation(ENTRY_SHA, PDF_SHA,
                                                                 fd_state=[[1, "pipe"], [0, "pipe"]])})
    assert_true(not stdlib_frame_valid(non_monotonic), "fd_state must ascend (stream validator)")


def test_evidence_record_schema() -> None:
    record = adapter.new_evidence(sha256_hex(b"docx"))
    adapter.apply_outcome(record, adapter.Outcome("RENDER_ENVIRONMENT_UNVERIFIED", "MANIFEST_ABSENT", None, "S2.01"))
    validator = schema_validator("evidence_record")
    assert_true(adapter.validate_evidence_record(record) == [], "a failure record validates (stdlib)")
    assert_true(validator.is_valid(record), "a failure record validates (schema)")
    labels = {item["label"] for item in record["automated_checks"]} | {item["label"] for item in record["human_required"]}
    assert_true(labels == {"AUTOMATED", "HUMAN_REQUIRED"}, "every check is labelled")
    for label, mutate in (
        ("pass without fingerprint", lambda r: r.update(run_status=adapter.STATUS_PASS)),
        ("waived human review", lambda r: r.update(human_review_waived=1)),
        ("fingerprint on a failure", lambda r: r.update(render_semantic_fingerprint="a" * 64)),
        ("unknown status", lambda r: r.update(run_status="RENDER_OK")),
        ("missing human check", lambda r: r.update(human_required=r["human_required"][1:])),
        ("relabelled human check", lambda r: r["human_required"][0].update(label="AUTOMATED")),
        ("malformed digest", lambda r: r.update(docx_sha256="xyz")),
        ("extra key", lambda r: r.update(submit=1)),
        ("truth field", lambda r: r.update(application_truth="SUBMITTED")),
    ):
        candidate = json.loads(json.dumps(record))
        mutate(candidate)
        assert_true(adapter.validate_evidence_record(candidate) != [], f"stdlib rejects {label}")
        assert_true(not validator.is_valid(candidate), f"schema rejects {label}")
    property_names = set()
    pending = [json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))]
    while pending:
        node = pending.pop()
        if isinstance(node, dict):
            if isinstance(node.get("properties"), dict):
                property_names.update(node["properties"])
            pending.extend(node.values())
        elif isinstance(node, list):
            pending.extend(node)
    for name in property_names:
        assert_true("submit" not in name.lower() and "truth" not in name.lower(),
                    f"the evidence schema carries no authority field: {name}")
    assert_true(record["human_required"][8] == {"check": "FINAL_BORA_APPROVAL_AND_MANUAL_SUBMIT",
                                                "label": "HUMAN_REQUIRED"}, "submit stays a manual human step")


# Child protocol stream vectors ----------------------------------------------------

def test_stream_protocol_vectors() -> None:
    complete = child_stream(ENTRY_SHA, PDF_SHA)
    analysis = analyze(complete)
    assert_true(analysis.complete and analysis.abnormal is None, "a complete valid stream")
    final_line = complete[complete.rstrip(b"\n").rfind(b"\n") + 1:]
    partial = child_stream(ENTRY_SHA, PDF_SHA, stop_after="S7", final=False)
    for label, stream, result, expected in (
        ("missing FINAL", child_stream(ENTRY_SHA, PDF_SHA, final=False), {}, ("CHILD_PROTOCOL", "MISSING_FINAL")),
        ("garbage byte without LF", partial + b"x", {}, ("CHILD_PROTOCOL", "TRUNCATED_FRAME")),
        ("garbage byte with LF", partial + b"x\n", {}, ("CHILD_PROTOCOL", "NOT_JSON")),
        ("empty line", partial + b"\n", {}, ("CHILD_PROTOCOL", "NOT_JSON")),
        ("invalid UTF-8", partial + b'{"\xff":1}\n', {}, ("CHILD_PROTOCOL", "NOT_JSON")),
        ("trailing data after FINAL", child_stream(ENTRY_SHA, PDF_SHA, trailing=b"x"), {},
         ("CHILD_PROTOCOL", "TRAILING_DATA")),
        ("schema-invalid line after FINAL", child_stream(ENTRY_SHA, PDF_SHA, trailing=b"{}\n"), {},
         ("CHILD_PROTOCOL", "SCHEMA")),
        ("valid frame after FINAL", complete + final_line, {}, ("CHILD_PROTOCOL", "FRAME_ORDER")),
        ("wrong evidence_bytes", child_stream(ENTRY_SHA, PDF_SHA, evidence_bytes_delta=1), {},
         ("CHILD_PROTOCOL", "EVIDENCE_BYTES_MISMATCH")),
        ("non-zero exit", complete, {"returncode": 1}, ("CHILD_PROTOCOL", "EXIT_NONZERO")),
        ("signal", complete, {"returncode": -9}, ("CHILD_PROTOCOL", "SIGNAL")),
        ("stream end beats exit", child_stream(ENTRY_SHA, PDF_SHA, final=False), {"returncode": 1},
         ("CHILD_PROTOCOL", "MISSING_FINAL")),
        ("parent timeout", partial, {"timed_out": True, "returncode": None}, ("INSPECTION_LIMIT", "WALL_CLOCK")),
        ("NaN", child_stream(ENTRY_SHA, PDF_SHA, overrides={"S5.03": b'{"x":NaN}\n'}), {},
         ("CHILD_PROTOCOL", "NON_FINITE")),
        ("Infinity", child_stream(ENTRY_SHA, PDF_SHA, overrides={"S5.03": b'{"x":-Infinity}\n'}), {},
         ("CHILD_PROTOCOL", "NON_FINITE")),
        ("duplicate key", child_stream(ENTRY_SHA, PDF_SHA, overrides={"S5.03": b'{"a":1,"a":1}\n'}), {},
         ("CHILD_PROTOCOL", "DUPLICATE_KEY")),
        ("NaN beats duplicate key", child_stream(ENTRY_SHA, PDF_SHA, overrides={"S5.03": b'{"a":NaN,"a":1}\n'}), {},
         ("CHILD_PROTOCOL", "NON_FINITE")),
    ):
        analysis = analyze(stream, **result)
        observed = analysis.abnormal[1:] if analysis.abnormal else None
        assert_true(observed == expected, f"{label}: {analysis.abnormal}")
    gap = complete.replace(b'"seq":2', b'"seq":3', 1)
    analysis = analyze(gap)
    assert_true(analysis.abnormal is not None and analysis.abnormal[2] == "FRAME_ORDER", f"seq gap: {analysis.abnormal}")


def test_parent_child_partition_vectors() -> None:
    model, manifest = source_model()
    rotation = ("FAIL", ("RENDER_PAGE_ROTATION_DENIED", None, None), {"slot": "S6.02", "page_index": 0})
    wrong_text = [{"bbox": [72.0, 728.0, 150.0, 740.0], "spans": [span("Hello there")]}]

    def status(stream, **result):
        return terminal(stream, model, manifest, **result)

    # (1) S8 fails on the S6/S7 frames while the child is killed during S9.
    result = status(child_stream(ENTRY_SHA, PDF_SHA, lines=wrong_text, stop_after="S7", final=False),
                    timed_out=True, returncode=None)
    assert_true(result is not None and result[3] == "S8" and result[0] == "RENDER_ATTRIBUTION_INCOMPLETE",
                f"(1) the S8 status, not WALL_CLOCK: {result}")
    # (2) S9.05 fails on the validated S9 frame while the S10 frame is malformed.
    bold = [font_entry("ABCDEF+LiberationSans-Bold")]
    bold_lines = [{"bbox": [72.0, 728.0, 150.0, 740.0], "spans": [span("Hello world", font="ABCDEF+LiberationSans-Bold")]}]
    result = status(child_stream(ENTRY_SHA, PDF_SHA, fonts=bold, lines=bold_lines, overrides={"S10": b"{bad\n"}))
    assert_true(result == ("RENDER_FONT_SUBSTITUTION_UNAPPROVED", None, None, "S9.05"),
                f"(2) the S9.05 status, not CHILD_PROTOCOL: {result}")
    # (3) S9.03 fails on the inventory while S9.02 passes.
    result = status(child_stream(ENTRY_SHA, PDF_SHA, fonts=[font_entry("ABCDEF+Unmapped")]))
    assert_true(result == ("RENDER_FONT_SUBSTITUTION_UNAPPROVED", "UNMAPPED_NAME_FORM", None, "S9.03"),
                f"(3) S9.03: {result}")
    # (4) S9.02 child FAIL frame; S9.03 to S9.05 are never evaluated.
    not_embedded = ("FAIL", ("RENDER_FONT_NOT_EMBEDDED", None, None), {"slot": "S9.02", "page_index": 0})
    result = status(child_stream(ENTRY_SHA, PDF_SHA, fonts=[font_entry("ABCDEF+Unmapped")],
                                 overrides={"S9": not_embedded}))
    assert_true(result == ("RENDER_FONT_NOT_EMBEDDED", None, None, "S9.02"), f"(4) S9.02: {result}")
    # (5) every parent slot through S9.05 passes and the child is killed during S10.
    result = status(child_stream(ENTRY_SHA, PDF_SHA, stop_after="S9", final=False), timed_out=True, returncode=None)
    assert_true(result == ("RENDER_PDF_INSPECTION_FAILED", "INSPECTION_LIMIT", "WALL_CLOCK", "S10.00"),
                f"(5) WALL_CLOCK at S10: {result}")
    # (6) a validated FAIL frame then a missing FINAL, a non-zero exit or trailing bytes.
    for label, stream, result_kwargs in (
        ("missing FINAL", child_stream(ENTRY_SHA, PDF_SHA, overrides={"S6": rotation}, final=False), {}),
        ("non-zero exit", child_stream(ENTRY_SHA, PDF_SHA, overrides={"S6": rotation}), {"returncode": 3}),
        ("trailing bytes", child_stream(ENTRY_SHA, PDF_SHA, overrides={"S6": rotation}, trailing=b"zz"), {}),
    ):
        result = status(stream, **result_kwargs)
        assert_true(result == ("RENDER_PAGE_ROTATION_DENIED", None, None, "S6.02"), f"(6) {label}: {result}")
    # (7) an earlier parent-slot failure and a later validated child FAIL frame.
    result = status(child_stream(ENTRY_SHA, PDF_SHA, lines=wrong_text, overrides={"S9": not_embedded}))
    assert_true(result is not None and result[3] == "S8", f"(7) the parent slot wins: {result}")
    # (8) a complete valid stream passes COMPLETE_STREAM_GATE.
    assert_true(status(child_stream(ENTRY_SHA, PDF_SHA)) is None, "(8) complete stream, every slot passes")
    # (9) six PASS frames, parent slots passing, then an abnormal end.
    for label, stream, result_kwargs, expected in (
        ("non-zero exit", child_stream(ENTRY_SHA, PDF_SHA), {"returncode": 1}, ("CHILD_PROTOCOL", "EXIT_NONZERO")),
        ("missing FINAL", child_stream(ENTRY_SHA, PDF_SHA, final=False), {}, ("CHILD_PROTOCOL", "MISSING_FINAL")),
        ("wrong evidence_bytes", child_stream(ENTRY_SHA, PDF_SHA, evidence_bytes_delta=-1), {},
         ("CHILD_PROTOCOL", "EVIDENCE_BYTES_MISMATCH")),
        ("kill", child_stream(ENTRY_SHA, PDF_SHA, final=False), {"timed_out": True, "returncode": None},
         ("INSPECTION_LIMIT", "WALL_CLOCK")),
    ):
        result = status(stream, **result_kwargs)
        assert_true(result == ("RENDER_PDF_INSPECTION_FAILED",) + expected + ("PRE_S11",), f"(9) {label}: {result}")
    linked, linked_manifest = source_model()
    linked.occurrences.append({"dest_kind": "EXTERNAL_URI", "dest": "https://example.com/", "tokens": ["Hello"],
                               "paragraph_index": 0})
    result = terminal(child_stream(ENTRY_SHA, PDF_SHA), linked, linked_manifest, returncode=1)
    assert_true(result == ("RENDER_LINK_MISSING", None, None, "S10.06"), f"(9) S10.06 instead: {result}")
    # START CLASSIFICATION order on a validated S5.02 PASS frame.
    for overrides, detail in (
        ({"inspection_entry_sha256": "f" * 64}, "ENTRY_MISMATCH"),
        ({"fd_state": [[0, "pipe"], [1, "pipe"], [2, "pipe"], [3, "file"]]}, "FD_LEAK"),
        ({"pycache_state": "PRESENT"}, "PYCACHE_NOT_EMPTY"),
        ({"received_pdf_sha256": "e" * 64}, "SNAPSHOT_MISMATCH"),
    ):
        frame = ("PASS", NULL_TRIPLE, {"start_attestation": attestation(ENTRY_SHA, PDF_SHA, **overrides)})
        stream = child_stream(ENTRY_SHA, PDF_SHA, overrides={"S5.02": frame})
        if "inspection_entry_sha256" in overrides:
            stream = child_stream(ENTRY_SHA, PDF_SHA, overrides={"S5.02": frame}, final=False)
        result = status(stream)
        assert_true(result is not None and result[2] == detail and result[3] == "S5.02",
                    f"start classification {detail}: {result}")


# Inspection entry over stand-ins ---------------------------------------------------

def _char(module, text="H", x0=72.0, size=11.0, baseline=740.0, ncs="DeviceGray", ncolor=None, matrix=None):
    width = 6.0
    return {"text": text, "x0": x0, "x1": x0 + width, "y0": baseline - 2.0, "y1": baseline + 8.0,
            "fontname": "ABCDEF+LiberationSans", "size": size,
            "matrix": matrix or (size, 0.0, 0.0, size, x0, baseline), "ncolor": ncolor, "ncs": ncs}


def _s7_context(module, operations, chars, resources=None):
    ctx = module.ChildContext(FIXTURE_PDF, {"entry_bytes": FIXTURE_ENTRY, "descriptors": [], "tmpdir_entries": 0,
                                            "pycache_state": "ABSENT", "pycache_prefix_matches": 1}, 20, 15)
    facts = module.PageFacts(0)
    facts.width, facts.height = 612.0, 792.0
    facts.chars = chars
    ctx.page_facts = [facts]
    ctx.pages = [module.DictionaryObject()]
    ctx.prescan = types.SimpleNamespace(forms={}, page_operations=[operations], page_resources=[resources])
    return ctx


def _s7(module, operations, chars, resources=None):
    ctx = _s7_context(module, operations, chars, resources)
    try:
        evidence = module.stage_s7(ctx)
    except module.ChildFail as failure:
        return failure.triple, failure.evidence
    return NULL_TRIPLE, evidence


def test_traversal_hidden_text_matrix() -> None:
    module = inspection_module()
    name = module.NameObject
    dictionary = module.DictionaryObject

    def ops(*items):
        return [(list(operands), operator) for operands, operator in items]

    show = ([b"Hello"], b"Tj")
    font = ([name("/F1"), 11], b"Tf")
    gs_resources = dictionary({"/ExtGState": dictionary({
        "/Zero": dictionary({"/ca": 0}), "/Low": dictionary({"/ca": 0.05}), "/Mask": dictionary({"/SMask": name("/X")}),
        "/Blend": dictionary({"/BM": name("/Multiply")}), "/Normal": dictionary({"/BM": name("/Normal"), "/ca": 1}),
    })})
    hello = [_char(module, ch, 72.0 + 6.0 * index) for index, ch in enumerate("Hello")]
    rows = [
        ("clean", ops(font, show), hello, None, NULL_TRIPLE),
        ("Tr 3", ops(font, ([3], b"Tr"), show), hello, None, ("RENDER_HIDDEN_TEXT_DETECTED", "RENDER_MODE_INVISIBLE", None)),
        ("Tr 7", ops(font, ([7], b"Tr"), show), hello, None, ("RENDER_HIDDEN_TEXT_DETECTED", "RENDER_MODE_INVISIBLE", None)),
        ("ca 0", ops(font, ([name("/Zero")], b"gs"), show), hello, gs_resources,
         ("RENDER_HIDDEN_TEXT_DETECTED", "ZERO_OPACITY", None)),
        ("Tr 1", ops(font, ([1], b"Tr"), show), hello, None, ("RENDER_TEXT_POLICY_SUSPECT", "RENDER_MODE_NOT_FILL_ONLY", None)),
        ("ca 0.05", ops(font, ([name("/Low")], b"gs"), show), hello, gs_resources,
         ("RENDER_TEXT_POLICY_SUSPECT", "LOW_OPACITY", None)),
        ("q Tr 3 Q restores", ops(font, ([], b"q"), ([3], b"Tr"), ([], b"Q"), show), hello, None, NULL_TRIPLE),
        ("normal gs", ops(font, ([name("/Normal")], b"gs"), show), hello, gs_resources, NULL_TRIPLE),
        ("small text", ops(font, show), [_char(module, "H", size=3.5)], None, ("RENDER_TEXT_POLICY_SUSPECT", "SMALL_TEXT", None)),
        ("near white", ops(font, ([1], b"g"), show), [_char(module, "H", ncolor=0.95)], None,
         ("RENDER_TEXT_POLICY_SUSPECT", "NEAR_WHITE", None)),
        ("Q without q", ops(font, ([], b"Q"), show), hello, None,
         ("RENDER_TEXT_STATE_UNOBSERVABLE", "STACK_UNBALANCED", None)),
        ("missing gs", ops(font, ([name("/Nope")], b"gs"), show), hello, gs_resources,
         ("RENDER_TEXT_STATE_UNOBSERVABLE", "MISSING_RESOURCE", None)),
        ("bad Tr", ops(font, ([9], b"Tr"), show), hello, None, ("RENDER_TEXT_STATE_UNOBSERVABLE", "BAD_OPERAND", None)),
        ("show without Tf", ops(show), hello, None, ("RENDER_TEXT_STATE_UNOBSERVABLE", "BAD_OPERAND", None)),
        ("SMask", ops(font, ([name("/Mask")], b"gs"), show), hello, gs_resources,
         ("RENDER_TEXT_STATE_UNOBSERVABLE", "VISUAL_STATE_UNPROVABLE", None)),
        ("blend", ops(font, ([name("/Blend")], b"gs"), show), hello, gs_resources,
         ("RENDER_TEXT_STATE_UNOBSERVABLE", "VISUAL_STATE_UNPROVABLE", None)),
        ("pattern", ops(font, ([name("/Pattern")], b"cs"), ([name("/P0")], b"scn"), show), hello, None,
         ("RENDER_TEXT_STATE_UNOBSERVABLE", "PATTERN_FILL", None)),
        ("CMYK", ops(font, ([0, 0, 0, 1], b"k"), show), [_char(module, "H", ncs="DeviceCMYK", ncolor=(0, 0, 0, 1))], None,
         ("RENDER_TEXT_STATE_UNOBSERVABLE", "COLOR_UNOBSERVABLE", "CS_UNSUPPORTED")),
        ("rg with gray char", ops(font, ([0, 0, 0], b"rg"), show), [_char(module, "H", ncolor=0.0)], None,
         ("RENDER_TEXT_STATE_UNOBSERVABLE", "COLOR_UNOBSERVABLE", "NCOLOR_INCONSISTENT")),
        ("rg char without colour", ops(font, ([0, 0, 0], b"rg"), show), [_char(module, "H", ncs="DeviceRGB")], None,
         ("RENDER_TEXT_STATE_UNOBSERVABLE", "COLOR_UNOBSERVABLE", "NCOLOR_MISSING")),
        ("show without chars", ops(font, show), [], None, ("RENDER_TEXT_STATE_UNOBSERVABLE", "NO_CORRESPONDENCE", None)),
        ("counted chars without show", ops(font), hello, None,
         ("RENDER_TEXT_STATE_UNOBSERVABLE", "COLOR_UNOBSERVABLE", "NCOLOR_INCONSISTENT")),
        ("whitespace chars without show", ops(font), [_char(module, " ")], None,
         ("RENDER_TEXT_STATE_UNOBSERVABLE", "COLOR_UNOBSERVABLE", "NCOLOR_INCONSISTENT")),
        ("char colour space absent from the shows", ops(font, ([0, 0, 0], b"rg"), show),
         [_char(module, "H", ncs="DeviceGray", ncolor=0.0)], None,
         ("RENDER_TEXT_STATE_UNOBSERVABLE", "COLOR_UNOBSERVABLE", "NCOLOR_INCONSISTENT")),
        ("cs without colour", ops(font, ([name("/DeviceRGB")], b"cs"), show), [_char(module, "H", ncs="DeviceRGB")],
         None, ("RENDER_TEXT_STATE_UNOBSERVABLE", "COLOR_UNOBSERVABLE", "CS_WITHOUT_COLOR")),
        ("lone surrogate", ops(font, show), [_char(module, "\ud800")], None,
         ("RENDER_ATTRIBUTION_INCOMPLETE", "CHAR_UNOBSERVABLE", None)),
        ("rotated", ops(font, show), [_char(module, "H", matrix=(0.0, 11.0, -11.0, 0.0, 72.0, 740.0))], None,
         ("RENDER_ATTRIBUTION_INCOMPLETE", "NON_HORIZONTAL_TEXT", None)),
        ("negative size", ops(([name("/F1"), -11], b"Tf"), show), hello, None,
         ("RENDER_ATTRIBUTION_INCOMPLETE", "NON_HORIZONTAL_TEXT", None)),
        ("separator-only line", ops(font, show), [_char(module, " ")], None,
         ("RENDER_ATTRIBUTION_INCOMPLETE", "EMPTY_TOKEN_LINE", None)),
    ]
    for label, operations, chars, resources, expected in rows:
        triple, evidence = _s7(module, operations, chars, resources)
        assert_true(triple == expected, f"S7 matrix {label}: {triple}")
        if triple != NULL_TRIPLE:
            frame = make_frame(3, "STAGE", "S7", "FAIL", triple, evidence)
            assert_true(stdlib_frame_valid(frame) and schema_frame_valid(frame), f"S7 FAIL frame valid: {label}")
        else:
            adapter._validate_pass_evidence("S7", evidence)


def test_line_building_and_colour_normalization() -> None:
    module = inspection_module()
    chars = []
    for index, ch in enumerate("Hello"):
        chars.append(dict(_char(module, ch, 72.0 + 6.0 * index), color=(0.0,)))
    for index, ch in enumerate("world"):
        chars.append(dict(_char(module, ch, 110.0 + 6.0 * index), color=(0.0,)))
    chars.append(dict(_char(module, "x", 72.0, baseline=700.0), color=(0.0,)))
    lines, texts, words = module.build_page_lines(chars, 792.0, 20, 15)
    assert_true(texts == ["Hello world", "x"], f"LINE_GROUP_V1 and SPACE_INSERT_V1: {texts}")
    assert_true([item["text"] for item in words] == ["Hello", "world", "x"], f"word records: {words}")
    first = lines[0]
    assert_true(len(first["spans"]) == 1 and first["spans"][0]["text"] == ["Hello world"], f"one span: {first}")
    assert_true(first["bbox"][1] == 792.0 - 748.0 and first["bbox"][3] == 792.0 - 738.0, "CCS y = H - y")
    adapter._validate_pass_evidence("S7", {"pages": [{"index": 0, "lines": lines}]})
    parent = adapter.rendered_lines({"pages": [{"index": 0, "lines": lines}]})
    assert_true([line.tokens for line in parent] == [["Hello", "world"], ["x"]], "parent reads the same tokens")
    mixed = [dict(_char(module, "A", 72.0), color=(0.0,)), dict(_char(module, "B", 78.0, size=14.0), color=(0.0,))]
    lines, _, _ = module.build_page_lines(mixed, 792.0, 20, 15)
    assert_true(len(lines[0]["spans"]) == 2 and lines[0]["spans"][1]["gap_before"] is False, "SPAN_V1 split")
    normalize = module.normalize_ncolor
    gray = _char(module, "H", ncolor=None)
    assert_true(normalize(gray, {"DeviceGray"}, True, False) == ((0,), None), "initial gray is (0,)")
    assert_true(normalize(gray, {"DeviceGray"}, False, True) == (None, "NCOLOR_MISSING"), "missing colour")
    assert_true(normalize(dict(gray, ncolor=[0.5]), {"DeviceGray"}, False, True) == ((0.5,), None), "gray list")
    assert_true(normalize(dict(gray, ncolor=1.5), {"DeviceGray"}, False, True)[1] == "NCOLOR_INCONSISTENT", "range")
    rgb = _char(module, "H", ncs="DeviceRGB", ncolor=(1, 0, 0))
    assert_true(normalize(rgb, {"DeviceRGB"}, False, True) == ((1.0, 0.0, 0.0), None), "RGB")
    assert_true(normalize(rgb, {"DeviceRGB", "DeviceGray"}, False, False)[1] == "NCOLOR_INCONSISTENT", "mixed states")
    assert_true(normalize(dict(rgb, ncs="ICCBased"), {"DeviceRGB"}, False, True)[1] == "CS_UNSUPPORTED", "ICC")
    assert_true(module._near_white((0.939,)) is False and module._near_white((0.94,)) is True, "NEAR_WHITE 240 edge")
    assert_true(module._near_white((1.0, 1.0, 0.939)) is False and module._near_white((0.95, 1.0, 0.96)) is True,
                "NEAR_WHITE needs all three channels")
    geometry = module.text_geometry_violation
    assert_true(geometry([_char(module, "H")]) is None, "consistent geometry")
    assert_true(geometry([dict(_char(module, "H"), x0=80.0)]) == 0, "x0 against e")
    assert_true(geometry([dict(_char(module, "H"), x1=60.0)]) == 0, "reversed box")
    assert_true(geometry([_char(module, "H", matrix=(11.0, 0.0, 0.0, 11.0, 72.0, 760.0))]) == 0, "f outside y")
    assert_true(geometry([_char(module, "H", matrix=(11.0, float("nan"), 0.0, 11.0, 72.0, 740.0))]) == 0, "NaN b")
    assert_true(geometry([_char(module, "H", matrix=(0.0, 11.0, -11.0, 0.0, 0.0, 0.0))]) is None,
                "rotated characters are judged at S7.04, not here")


def test_child_emitter_and_start_attestation() -> None:
    module = inspection_module()
    observation = {"entry_bytes": FIXTURE_ENTRY, "descriptors": [(0, "pipe"), (1, "pipe"), (2, "pipe")],
                   "tmpdir_entries": 0, "pycache_state": "ABSENT", "pycache_prefix_matches": 1}
    record = module.start_attestation(observation, FIXTURE_PDF)
    assert_true(record == attestation(ENTRY_SHA, PDF_SHA), f"START_ATTESTATION_V1 record: {record}")
    assert_true(not module.start_state_violated(record), "a clean start")
    for change in ({"descriptors": [(0, "pipe"), (1, "pipe"), (2, "pipe"), (3, "file")]}, {"tmpdir_entries": 1},
                   {"pycache_state": "PRESENT"}, {"pycache_prefix_matches": 0}):
        violated = module.start_state_violated(module.start_attestation(dict(observation, **change), FIXTURE_PDF))
        assert_true(violated, f"start violation {change}")
    leak = module.start_attestation(dict(observation, descriptors=[(n, "file") for n in range(9)]), FIXTURE_PDF)
    assert_true(len(leak["fd_state"]) == 4, "fd_state truncated to four entries")
    if os.name == "posix":
        raw = module.observe_start(str(ENTRY_PATH))
        assert_true(raw["entry_bytes"] == ENTRY_PATH.read_bytes() and isinstance(raw["descriptors"], list),
                    "observe_start reads the entry and the descriptors")

    def staged(functions, limit=None):
        ctx = module.ChildContext(FIXTURE_PDF, observation, 20, 15)
        sink = io.BytesIO()
        emitter = module.FrameEmitter(sink, limit) if limit else module.FrameEmitter(sink)
        saved = module.STAGE_FUNCTIONS_V1
        module.STAGE_FUNCTIONS_V1 = functions
        try:
            triple = module.run_child(ctx, emitter)
        finally:
            module.STAGE_FUNCTIONS_V1 = saved
        return triple, sink.getvalue()

    def passing(stage):
        def function(ctx):
            if stage == "S5.02":
                ctx.attestation = module.start_attestation(ctx.observation, ctx.pdf_bytes)
                return {"start_attestation": ctx.attestation}
            return pass_evidence(stage, ENTRY_SHA, PDF_SHA)
        return function

    functions = tuple((stage, passing(stage)) for stage in adapter.CHILD_STAGES)
    triple, stream = staged(functions)
    assert_true(triple == module.NO_TRIPLE, "all stages pass")
    analysis = analyze(stream)
    assert_true(analysis.complete and not analysis.notes, f"the child stream satisfies the parent: {analysis.abnormal}")

    def page_facts_error(ctx):
        ctx.at("S6.03", "PAGE_FACTS", 0)
        raise ValueError("box read\nsecond line")

    triple, stream = staged(functions[:2] + (("S6", page_facts_error),) + functions[3:])
    assert_true(triple == ("RENDER_PDF_INSPECTION_FAILED", "PAGE_FACTS", None), f"mapped exception: {triple}")
    analysis = analyze(stream)
    frame = analysis.stage_frames["S6"]
    assert_true(frame["evidence"] == {"slot": "S6.03", "page_index": 0, "exception_class": "ValueError",
                                      "exception_message": "box read"}, f"exception evidence: {frame['evidence']}")
    assert_true(terminal(stream) == ("RENDER_PDF_INSPECTION_FAILED", "PAGE_FACTS", None, "S6.03"),
                "the parent reports the child's slot")

    def tracker(ctx):
        ctx.at("S7.01", "TRACKER_FAILURE", 0)
        raise KeyError("x")

    triple, _ = staged(functions[:3] + (("S7", tracker),) + functions[4:])
    assert_true(triple == ("RENDER_TEXT_STATE_UNOBSERVABLE", "TRACKER_FAILURE", None), "TRACKER_FAILURE mapping")

    def memory(ctx):
        ctx.at("S9.02", "FONT_TRAVERSAL", 0)
        raise MemoryError()

    triple, stream = staged(functions[:4] + (("S9", memory),) + functions[5:])
    assert_true(triple == ("RENDER_PDF_INSPECTION_FAILED", "INSPECTION_LIMIT", "MEMORY"), "MEMORY mapping")
    assert_true(analyze(stream).fail_frame["evidence"] == {"slot": "S9.02"}, "MEMORY evidence")

    def unmapped(ctx):
        ctx.at("S10.01", None)
        raise RuntimeError("no mapped reason")

    assert_true(_raises(RuntimeError, staged, functions[:5] + (("S10", unmapped),)),
                "an exception with no mapped reason is never invented into a status")

    def huge(ctx):
        return {"pages": [{"index": 0, "lines": [{"bbox": [0.0, 0.0, 1.0, 1.0],
                                                  "spans": [span("x" * 1000)] * 60}]}]}

    triple, stream = staged(functions[:3] + (("S7", huge),) + functions[4:], limit=module.FAIL_FRAME_RESERVE_BYTES + 3000)
    assert_true(triple == module.EVIDENCE_BYTES_TRIPLE, f"an over-budget PASS frame becomes EVIDENCE_BYTES: {triple}")
    analysis = analyze(stream)
    assert_true(analysis.fail_frame is not None and analysis.fail_frame["evidence"] == {} and analysis.final is not None,
                "EVIDENCE_BYTES frame and FINAL validate")
    assert_true(len(stream) <= module.FAIL_FRAME_RESERVE_BYTES + 3000 + adapter.FINAL_FRAME_MAX_BYTES,
                "the reserve keeps the FAIL frame inside the budget")
    nested = 1
    for _ in range(16):
        nested = [nested]
    assert_true(not module.frame_within_limits({"a": nested}, 10), "depth limit")
    assert_true(not module.frame_within_limits({"a": 10 ** 20}, 10), "integer digits limit")
    assert_true(module.frame_within_limits({"a": 10 ** 20 - 1}, 10), "twenty digits allowed")


# Orchestration with fakes ---------------------------------------------------------

class FakeRunner:
    """Records argv; the render call writes FIXTURE_PDF into the bound
    output directory, the inspection call returns a prepared stream."""

    def __init__(self, child_stdout=None, render_returncode=0, launched=True, timed_out=False):
        self.calls = []
        self.child_stdout = child_stdout
        self.render_returncode = render_returncode
        self.launched = launched
        self.timed_out = timed_out

    def run(self, argv, stdin_bytes=None, timeout=None, pass_fds=(), memory_limit=None, stdout_limit=None):
        self.calls.append({"argv": list(argv), "stdin": stdin_bytes, "timeout": timeout, "pass_fds": pass_fds,
                           "memory_limit": memory_limit, "stdout_limit": stdout_limit})
        if adapter.SANDBOX_ENTRY_PATH in argv:
            stdout = self.child_stdout(stdin_bytes) if self.child_stdout else b""
            return adapter.ProcessResult(0, stdout=stdout)
        if self.timed_out:
            return adapter.ProcessResult(None, timed_out=True)
        if not self.launched:
            return adapter.ProcessResult(None, launched=False)
        output = argv[argv.index(adapter.SANDBOX_OUTPUT_DIR) - 1]
        with open(os.path.join(output, adapter.OUTPUT_FILE_NAME), "wb") as handle:
            handle.write(FIXTURE_PDF)
        return adapter.ProcessResult(self.render_returncode)


def fake_dependencies(tree: BoundTree, temp: str, runner=None, **overrides):
    manifest = tree.manifest()
    paths = tree.runtime_paths()

    def prober(profile, argv, pass_fds):
        mounts = paths.inspection_read_only_paths if profile == adapter.PROFILE_INSPECTION else ()
        return {"ok": True, "profile_digest": adapter.sandbox_profile_digest(manifest, profile, mounts)}

    values = {
        "manifest_bytes": manifest_bytes(manifest),
        "live_verifier": lambda m: None,
        "plan_inputs": (REQUIREMENTS_IN, REQUIREMENTS_LOCK),
        "runtime_paths": paths,
        "isolation_prober": prober,
        "runner": runner or FakeRunner(lambda pdf: child_stream(ENTRY_SHA, sha256_hex(pdf))),
        "temp_parent": temp,
        "entry_reader": lambda: FIXTURE_ENTRY,
        "entry_binder": lambda data, digest: adapter.EntryDescriptor(None, {"binding": "FIXTURE"}),
    }
    values.update(overrides)
    return adapter.RenderDependencies(**values)


def test_orchestration_with_fakes() -> None:
    docx = docx_fixture()
    before = bytes(docx)
    smap = structure_map_fixture()
    record = adapter.render_document(docx, smap)
    assert_true((record["run_status"], record["reason"], record["slot"])
                == ("RENDER_ENVIRONMENT_UNVERIFIED", "MANIFEST_ABSENT", "S2.01"),
                f"no environment manifest fails closed at S2.01: {record['run_status']}/{record['reason']}")
    assert_true(schema_validator("evidence_record").is_valid(record), "the failure record validates")
    assert_true(adapter.render_document(b"nope", smap)["run_status"] == "RENDER_DOCX_PACKAGE_INVALID", "S1 first")
    temp = tempfile.mkdtemp(prefix="render-orchestration-")
    try:
        tree = BoundTree(temp)
        unset_entry = b"LINE_GROUP_BASELINE_TOLERANCE_Q = None\nWORD_GAP_THRESHOLD_Q = None\n"
        record = adapter.render_document(docx, smap, fake_dependencies(tree, temp, entry_reader=lambda: unset_entry))
        assert_true((record["run_status"], record["reason"]) == ("RENDER_ENVIRONMENT_UNVERIFIED", "EXTRACTION_SPEC"),
                    "an entry with unset constants fails closed at S2.01")
        assert_true(adapter.render_document(docx, None, fake_dependencies(tree, temp))["run_status"]
                    == "RENDER_STRUCTURE_MAP_REQUIRED", "S3.21 structure map required")
        assert_true(adapter.render_document(docx, smap, fake_dependencies(tree, temp, isolation_prober=None))["reason"]
                    == "PROBE_UNAVAILABLE", "no isolation prober fails closed at S4.01")
        assert_true(adapter.render_document(docx, smap, fake_dependencies(tree, temp, runtime_paths=None))["reason"]
                    == "RUNTIME_PATHS_UNAVAILABLE", "no runtime paths fail closed")
        record = adapter.render_document(docx, smap, fake_dependencies(tree, temp, runner=FakeRunner(timed_out=True)))
        assert_true((record["run_status"], record["slot"]) == ("RENDER_TIMEOUT", "S5.01"), "render timeout")
        record = adapter.render_document(docx, smap, fake_dependencies(tree, temp, runner=FakeRunner(render_returncode=2)))
        assert_true((record["reason"], record["detail"]) == ("RENDERER_RUNTIME_INCOMPLETE", "EXIT_NONZERO"),
                    "renderer non-zero exit")
        runner = FakeRunner(lambda pdf: child_stream(ENTRY_SHA, sha256_hex(pdf), overrides={"S6": (
            "FAIL", ("RENDER_PAGE_ROTATION_DENIED", None, None), {"slot": "S6.02", "page_index": 0})}))
        record = adapter.render_document(docx, smap, fake_dependencies(tree, temp, runner=runner))
        assert_true((record["run_status"], record["slot"]) == ("RENDER_PAGE_ROTATION_DENIED", "S6.02"),
                    "a child FAIL frame is the run status")
        assert_true(record["render_semantic_fingerprint"] is None and record["temp_root_removed"] == 1,
                    "no fingerprint on failure; temp root removed")
        delivery = os.path.join(temp, "delivery")
        os.mkdir(delivery)
        runner = FakeRunner(lambda pdf: child_stream(ENTRY_SHA, sha256_hex(pdf)))
        record = adapter.render_document(docx, smap, fake_dependencies(tree, temp, runner=runner), delivery)
        assert_true(record["run_status"] == adapter.STATUS_PASS, f"full fake run: {record['run_status']} "
                    f"{record['reason']} {record['slot']}")
        assert_true(record["delivered"] == 1 and record["pdf_sha256"] == PDF_SHA, "delivered the snapshot")
        with open(os.path.join(delivery, adapter.DELIVERED_PDF_NAME), "rb") as handle:
            assert_true(handle.read() == FIXTURE_PDF, "delivered bytes are the RAW PDF bytes")
        assert_true(record["utilization"]["label"] == "AUTOMATED_GEOMETRY_ONLY"
                    and record["utilization"]["visible_occupancy"] == "HUMAN_REQUIRED", "utilization labels")
        assert_true(record["human_review_waived"] == 0 and schema_validator("evidence_record").is_valid(record),
                    "the pass record validates and never waives review")
        child_call = runner.calls[-1]
        assert_true(child_call["stdin"] == FIXTURE_PDF and child_call["timeout"]
                    == adapter.INSPECTION_LIMITS_V1["inspection_timeout_seconds"], "the child receives the snapshot")
        assert_true(child_call["argv"][-len(adapter.inspection_argv(tree.manifest())):]
                    == adapter.inspection_argv(tree.manifest()), "inspection argv")
        again = adapter.render_document(docx, smap, fake_dependencies(tree, temp, runner=runner))
        assert_true(again["render_semantic_fingerprint"] == record["render_semantic_fingerprint"],
                    "RENDER_SEMANTIC_FINGERPRINT_V1 is deterministic")
        low = [{"bbox": [72.0, 72.0, 150.0, 84.0], "spans": [span("Hello world")]}]
        runner = FakeRunner(lambda pdf: child_stream(ENTRY_SHA, sha256_hex(pdf), lines=low))
        record = adapter.render_document(docx, smap, fake_dependencies(tree, temp, runner=runner))
        assert_true(record["run_status"] == adapter.STATUS_QA_FAILED and record["render_semantic_fingerprint"],
                    "the unchanged evaluator's utilization failure is QA_FAILED with a fingerprint")
        assert_true(any(item.get("kind") == "VALIDATOR_ERROR" for item in record["findings"]), "validator finding")
        assert_true(not [name for name in os.listdir(temp) if name.startswith("career-os-render-")],
                    "no per-run root survives")
    finally:
        shutil.rmtree(temp, ignore_errors=True)
    assert_true(docx == before, "the DOCX bytes are unchanged after every run")


def test_adapter_static_rules() -> None:
    text = ADAPTER_PATH.read_text(encoding="utf-8")
    tree = ast.parse(text)
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    for forbidden in ("socket", "http", "urllib3", "requests", "pypdf", "pdfminer", "fitz", "pdfplumber",
                      "pypdfium2", "lxml", "pursuit_decision", "identity", "claim", "evidence", "qualification",
                      "application", "googleapiclient", "gspread"):
        assert_true(forbidden not in imported, f"the adapter does not import {forbidden}")
    evaluator_imports = {alias.name for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)
                         and node.module == "resume_page_utilization" for alias in node.names}
    defined = {node.name for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.ClassDef))}
    assert_true("evaluate_resume_page_utilization" in evaluator_imports
                and "evaluate_resume_page_utilization" not in defined,
                "the frozen evaluator is imported, not reimplemented")
    assert_true(re.search(r"\bexcept\s*:", text) is None, "no bare except in the adapter")
    shell_keywords = [keyword for node in ast.walk(tree) if isinstance(node, ast.Call)
                      for keyword in node.keywords if keyword.arg == "shell"]
    assert_true(all(isinstance(keyword.value, ast.Constant) and keyword.value.value is False
                    for keyword in shell_keywords), "no shell invocation")
    evaluator = EVALUATOR_PATH.read_text(encoding="utf-8")
    assert_true("PAGE_UTILIZATION_FLOOR = 0.92" in evaluator, "evaluator floor unchanged")


def test_dpkg_option_syntax_v1_vectors() -> None:
    """DPKG_OPTION_SYNTAX_V1 (canonical capability contract, DPKG_CONFIG_CHECK_V1 proof (a)):
    the unquoted whitespace-separated form is admitted, every other rule is unchanged."""
    spec = importlib.util.spec_from_file_location("verify_document_rendering_environment_dpkg",
                                                  ROOT / "scripts" / "verify_document_rendering_environment.py")
    verifier = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(verifier)

    def parse(line: bytes):
        return verifier.parse_dpkg_config(line + b"\n", "/etc/dpkg/dpkg.cfg")

    def reason_of(callable_, *args):
        try:
            callable_(*args)
        except verifier.Rejected as exc:
            return exc.reason
        return None

    for line in (b"log /var/log/dpkg.log", b"log\t/var/log/dpkg.log", b"log /var/log/dpkg.log \t",
                 b"log=/var/log/dpkg.log", b"LOG   /var/log/dpkg.log"):
        assert_true(parse(line) == [["log", "/var/log/dpkg.log"]], "separator and equals forms agree: %r" % line)
    assert_true(parse(b"no-debsig") == [["no-debsig", None]], "valueless form unchanged")
    assert_true(parse(b"--NO-DEBSIG") == [["no-debsig", None]], "dashes and case unchanged")
    assert_true(parse(b"unsafe-io") == [["unsafe-io", None]], "valueless unsafe-io unchanged")
    assert_true(parse(b"path-exclude=/usr/share/fonts/*") == [["path-exclude", "/usr/share/fonts/*"]],
                "equals form unchanged")
    assert_true(parse(b"# c\n\nno-debsig\nlog /var/log/dpkg.log") == [["no-debsig", None],
                                                                   ["log", "/var/log/dpkg.log"]],
                "stock file shape, ordered")
    for line in (b"log ", b"log \t", b"log =/x", b'log "/x"', b"log '/x'", b" log /x", b"lo.g /x",
                 b"log=/x\x00"):
        assert_true(reason_of(parse, line) == "DPKG_CONFIG_MALFORMED", "malformed stays rejected: %r" % line)

    def record_for(text: bytes, sha: str = "0" * 64) -> dict:
        return {"files": [{"path": "/etc/dpkg/dpkg.cfg", "sha256": sha, "options": parse(text)}],
                "diversions": [], "statoverride": [], "policy_rc_d": {"path": "/usr/sbin/policy-rc.d",
                                                                      "sha256": "ABSENT"}}

    for line in (b"force-all x", b"--force-depends x", b"force-unsafe-io x", b"pre-invoke cmd", b"post-invoke cmd",
                 b"status-logger cmd", b"admindir /x", b"root /x", b"instdir /x", b"no-act x", b"dry-run x",
                 b"simulate x", b"no-triggers x", b"force-all", b"admindir=/x"):
        record = record_for(line)
        assert_true(reason_of(verifier.check_dpkg_record, record, record) == "DPKG_CONFIG_NEVER_APPROVABLE",
                    "never approvable even when listed, any separator: %r" % line)
    stock = record_for(b"no-debsig\nlog /var/log/dpkg.log")
    assert_true(reason_of(verifier.check_dpkg_record, stock, stock) is None, "stock pair admitted when approved exactly")
    missing_log = record_for(b"no-debsig")
    assert_true(reason_of(verifier.check_dpkg_record, stock, missing_log) == "DPKG_CONFIG_MISMATCH",
                "unapproved log entry is a mismatch")
    valued = record_for(b"no-debsig x")
    assert_true(reason_of(verifier.check_dpkg_record, valued, valued) == "DPKG_CONFIG_NO_DEBSIG_UNAPPROVED",
                "no-debsig carrying a value is never admitted")
    script = (ROOT / "scripts" / "provision_document_rendering_env.sh").read_text(encoding="utf-8")
    assert_true("RE_DPKG_LINE='^(-{0,2})([A-Za-z0-9_-]+)(=(.*)|[[:blank:]]+(.*))?$'" in script,
                "provisioning script carries the same three-form grammar")


_VERIFIER_CACHE: dict = {}


def verifier_module():
    if "module" not in _VERIFIER_CACHE:
        spec = importlib.util.spec_from_file_location("verify_document_rendering_environment_gate3",
                                                      ROOT / "scripts" / "verify_document_rendering_environment.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _VERIFIER_CACHE["module"] = module
    return _VERIFIER_CACHE["module"]


def test_pre_gate3_cli_dispatch() -> None:
    """The three pre-gate-(3) verifier modes dispatch from the CLI; nothing else changes."""
    import contextlib

    verifier = verifier_module()
    calls = []
    saved = (verifier.apt_proof_mode, verifier.process_proof_mode, verifier.post_evidence_mode)
    out, err = io.StringIO(), io.StringIO()
    try:
        verifier.apt_proof_mode = lambda root: calls.append(("apt", root)) or {"result": "PASS"}
        verifier.process_proof_mode = lambda root: calls.append(("process", root)) or {"result": "FAIL"}
        verifier.post_evidence_mode = lambda root, digest, path=None: calls.append(("post", digest, path)) or {
            "mode": "POST_EVIDENCE_PARTIAL"}
        digest = "a" * 64
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            codes = [verifier.main(["--apt-noninteractive-proof"]), verifier.main(["--process-creation-proof"]),
                     verifier.main(["--post-evidence", digest]),
                     verifier.main(["--post-evidence", digest, "--provisioning-evidence", "/e"]),
                     verifier.main(["--checkout-root", "/c", "--apt-noninteractive-proof"]),
                     verifier.main(["--post-evidence", "xyz"]), verifier.main(["--post-evidence", digest, "--bogus", "/e"]),
                     verifier.main(["--apt-noninteractive-proof", "extra"])]
    finally:
        verifier.apt_proof_mode, verifier.process_proof_mode, verifier.post_evidence_mode = saved
    assert_true(codes == [0, 1, 0, 0, 0, 2, 2, 2], f"exit codes by mode and malformed arguments: {codes}")
    assert_true([call[0] for call in calls] == ["apt", "process", "post", "post", "apt"], f"dispatch order: {calls}")
    assert_true(calls[3][1:] == (digest, "/e") and calls[2][2] is None, "post-evidence arguments")
    assert_true(str(calls[4][1]) == str(Path("/c")), "checkout root is passed to the mode")
    usage = err.getvalue()
    for token in ("--apt-noninteractive-proof", "--process-creation-proof", "--post-evidence"):
        assert_true(token in usage, f"usage names {token}")


APT_PROOF_PACKAGES = [{"name": "alpha", "architecture": "amd64", "role": "SANDBOX", "version": "1.0-1"},
                      {"name": "beta", "architecture": "all", "role": "FONT", "version": "2:3"}]


def apt_proof_manifest() -> dict:
    return {"apt_plan": {"install_flags": ["--yes", "--no-install-recommends", "--no-remove"],
                         "packages": APT_PROOF_PACKAGES},
            "operator_python_prefix": "/opt/career-os-render/python",
            "sandbox_forbidden_canary_paths": ["/home/codespace", "/root", "/workspaces"]}


class FakeApt:
    """A fake apt host. `extras` are resolved dependencies outside the plan; `controls_abort` models apt
    answering EOF to the prompt of the control run."""

    def __init__(self, extras=(), controls_abort=True, simulate_rc=0, simulate_text="", dpkg_changes=False,
                 download_rc=0, directory="/var/tmp/career-os-apt-proof-x", removal_works=True) -> None:
        self.extras, self.controls_abort, self.simulate_rc = list(extras), controls_abort, simulate_rc
        self.simulate_text, self.dpkg_changes, self.download_rc = simulate_text, dpkg_changes, download_rc
        self.directory, self.removal_works = directory, removal_works
        self.argvs, self.made, self.removed, self.snapshots = [], [], [], 0

    def runner(self, argv):
        self.argvs.append(list(argv))
        if "--version" in argv:
            return 0, "apt 2.7.14 (amd64)\nmore\n"
        if "--simulate" in argv:
            lines = ["Inst %s (v)" % name for name in ["alpha", "beta"] + self.extras]
            return self.simulate_rc, "\n".join(lines) + "\n" + self.simulate_text
        if "--yes" in argv:
            return self.download_rc, "Fetched 0 B\n"
        return (100, "Do you want to continue? [Y/n] Abort.\n") if self.controls_abort else (0, "Fetched 0 B\n")

    def snapshot(self):
        self.snapshots += 1
        return [["alpha", "amd64", "1.0-1", "install ok installed"]] + (
            [["gamma", "amd64", "9", "install ok installed"]] if self.dpkg_changes and self.snapshots > 1 else [])

    def make_dir(self):
        self.made.append(self.directory)
        return self.directory

    def remove_dir(self, path):
        self.removed.append(path)

    def exists(self, path):
        return not (self.removal_works and path in self.removed)


def run_apt_proof(fake: FakeApt, root: bool = True, manifest=None) -> dict:
    verifier = verifier_module()
    return verifier.apt_noninteractive_proof(manifest or apt_proof_manifest(), fake.runner, fake.snapshot,
                                             fake.make_dir, fake.remove_dir, lambda: 0 if root else 1000, fake.exists)


def test_apt_noninteractive_proof_vectors() -> None:
    """APT_NONINTERACTIVE_PROOF_V1 logic: exact argv forms, no apt-get update, no installation, fail-closed STOP."""
    import inspect

    verifier = verifier_module()
    planned = ["alpha=1.0-1", "beta=2:3"]
    flags = ["--yes", "--no-install-recommends", "--no-remove"]
    plan = apt_proof_manifest()["apt_plan"]
    assert_true(verifier.apt_proof_argv(plan, "SIMULATE") == ["/usr/bin/apt-get", "install"] + flags + ["--simulate"] + planned,
                "(a) is the governed argv plus --simulate")
    d = "/var/tmp/d"
    assert_true(verifier.apt_proof_argv(plan, "DOWNLOAD_ONLY", d) == ["/usr/bin/apt-get", "install"] + flags + [
        "--download-only", "-o", "Dir::Cache::archives=" + d] + planned, "(b) adds --download-only and the single -o delta")
    assert_true(verifier.apt_proof_argv(plan, "CONTROL", d) == ["/usr/bin/apt-get", "install", "--no-install-recommends",
                                                                "--no-remove", "--download-only", "-o",
                                                                "Dir::Cache::archives=" + d] + planned, "(c) is (b) without --yes")
    bad = {"install_flags": ["--yes"], "packages": APT_PROOF_PACKAGES}
    assert_true(outcome_reason(verifier, lambda: verifier.apt_proof_argv(bad, "SIMULATE")) == "APT_CONFIG_UNAPPROVED",
                "install flags other than the contract set are rejected")

    fake = FakeApt(extras=["delta"])
    record = run_apt_proof(fake)
    assert_true(record["result"] == "PASS" and record["control"] == "PASS", f"proof with an extra dependency: {record}")
    assert_true([run["label"] for run in record["runs"]] == ["VERSION", "SIMULATE", "DOWNLOAD_ONLY", "CONTROL_WITHOUT_YES"],
                "run order")
    assert_true(record["apt_get_version"] == "apt 2.7.14 (amd64)" and record["stdin"] == "/dev/null"
                and record["env"] == list(verifier.APT_PROOF_ENV), "version and closed environment recorded")
    assert_true(record["apt_update_executed"] is False and record["installs_anything"] is False, "no update, no install")
    assert_true(all("update" not in argv for argv in fake.argvs), "no argv carries an update verb")
    assert_true(sum(argv.count("-o") for argv in fake.argvs) == 2 and not any("-o" in a for a in fake.argvs[:2]),
                "the -o delta exists only in the (b) and (c) proof commands")
    assert_true(fake.made == [fake.directory] and fake.removed == [fake.directory]
                and record["disposable_directory_removed"] is True, "disposable directory created and removed")
    assert_true(record["extra_packages_in_resolution"] == 1 and record["dpkg_state_unchanged"] is True, "extras and snapshot")

    record = run_apt_proof(FakeApt())
    assert_true(record["result"] == "PASS" and record["control"] == "NOT_APPLICABLE"
                and [run["label"] for run in record["runs"]] == ["VERSION", "SIMULATE", "DOWNLOAD_ONLY"],
                "no extra package: the control is NOT_APPLICABLE and not run")

    for name, fake, expected in (
        ("simulate unresolvable (empty package index)", FakeApt(simulate_rc=100, simulate_text="E: Unable to locate package\n"),
         "SIMULATE_FAILED"),
        ("prompt text in the simulation", FakeApt(simulate_text="Do you want to continue? [Y/n]\n"), "SIMULATE_FAILED"),
        ("abort text in the simulation", FakeApt(simulate_text="Abort.\n"), "SIMULATE_FAILED"),
        ("download-only fails", FakeApt(download_rc=100), "DOWNLOAD_ONLY_FAILED"),
        ("dpkg state changes", FakeApt(dpkg_changes=True), "DOWNLOAD_ONLY_FAILED"),
        ("control does not abort", FakeApt(extras=["delta"], controls_abort=False), "CONTROL_NOT_ABORTED"),
        ("directory under a canary path", FakeApt(directory="/workspaces/x"), "DISPOSABLE_DIRECTORY_PLACEMENT"),
        ("directory under the operator prefix", FakeApt(directory="/opt/career-os-render/python/x"),
         "DISPOSABLE_DIRECTORY_PLACEMENT"),
        ("directory cannot be removed", FakeApt(removal_works=False), "DISPOSABLE_DIRECTORY_REMAINS"),
    ):
        record = run_apt_proof(fake)
        assert_true(record["result"] == "STOP" and record["reason"] == expected, f"{name}: {record['result']} {record.get('reason')}")
    unresolvable = FakeApt(simulate_rc=100)
    run_apt_proof(unresolvable)
    assert_true(not unresolvable.made and len(unresolvable.argvs) == 2,
                "an unresolvable simulation stops before any download and creates no directory")
    forced = FakeApt(dpkg_changes=True)
    run_apt_proof(forced)
    assert_true(forced.removed == [forced.directory], "the disposable directory is removed after a failed proof")
    refused = FakeApt()
    record = run_apt_proof(refused, root=False)
    assert_true(record["result"] == "STOP" and record["reason"] == "NOT_ROOT" and not refused.argvs,
                "not root: nothing is run")

    for function in (verifier.apt_proof_argv, verifier.real_apt_proof_dependencies):
        assert_true('"update"' not in inspect.getsource(function), f"{function.__name__} never names an update verb")
    assert_true(inspect.getsource(verifier.apt_noninteractive_proof).count('"update"') == 1,
                "the proof names the update verb only in its refuse-to-run guard")


def outcome_reason(verifier, callable_):
    try:
        callable_()
    except verifier.Rejected as exc:
        return exc.reason
    return None


PROOF_VECTOR_EVENTS = {
    "subprocess.run": "subprocess.Popen", "subprocess.Popen": "subprocess.Popen", "os.popen": "subprocess.Popen",
    "os.system": "os.system", "os.posix_spawn": "os.posix_spawn", "os.posix_spawnp": "os.posix_spawn",
    "os.spawnv": "os.fork", "os.spawnlp": "os.fork", "os.execv": "os.exec", "os.fork": "os.fork",
    "os.forkpty": "os.forkpty", "pty.spawn": "pty.spawn",
    "multiprocessing.util.spawnv_passfds": "_posixsubprocess.fork_exec",
    "_posixsubprocess.fork_exec": "_posixsubprocess.fork_exec", "swallowed os.fork": "os.fork",
}
PROOF_VECTOR_NAMES = (
    "subprocess.run", "subprocess.Popen", "os.popen", "os.system", "os.posix_spawn", "os.posix_spawnp", "os.spawnv",
    "os.spawnlp", "os.execv", "os.fork", "os.forkpty", "pty.spawn", "multiprocessing.util.spawnv_passfds",
    "_posixsubprocess.fork_exec", "swallowed os.fork",
)
FORK_EXEC_FAKE_ARGUMENTS = "(['/bin/sh', '-c', 'echo x > %s'], (b'/bin/sh',), True, (4,), '/', None, -1, -1, -1, -1, -1, -1, 3, 4, True, False, -1, None, None, None, -1, None)"


class FakeProcessHost:
    """Behaves like an interpreter that creates a marker for every vector, reports `events` under the
    enumeration hook and is blocked by the denying hook unless a defect is injected."""

    def __init__(self, defects=None, prefix_defect=None, empty_digest="", e2_digest="", e2_record=()) -> None:
        self.defects = defects or {}
        self.prefix_defect = prefix_defect
        self.empty_digest, self.e2_digest, self.e2_record = empty_digest, e2_digest, list(e2_record)
        self.calls = []

    def run(self, argv, environment, cwd):
        startup = argv[1:6]
        assert startup[:4] == ["-I", "-S", "-B", "-X"] and startup[4].startswith("pycache_prefix="), f"startup form {startup}"
        pycache = startup[4][len("pycache_prefix="):]
        assert os.path.isdir(pycache) and os.listdir(pycache) == [], "an empty pycache directory exists before launch"
        assert argv[6] == "-c" and len(argv) == 8, "the code is passed with -c only"
        code = argv[7]
        self.calls.append(code)
        if "_Captured" in code:
            marker = re.search(r"echo x > ([^']+)'", code).group(1)
            return 0, FORK_EXEC_FAKE_ARGUMENTS % marker.replace("\\", "\\\\") + "\n", ""
        if "_enumerate" in code:
            index = int(re.search(r"enumeration-(\d+)\.log", code).group(1))
            vector = PROOF_VECTOR_NAMES[index]
            event = self.defects.get(("events", vector), PROOF_VECTOR_EVENTS[vector])
            log = re.search(r"enumeration-%d\.log" % index, code)
            path = os.path.join(cwd, log.group(0))
            Path(path).write_text("os.open\n%s\n" % event, encoding="ascii")
            if ("no_marker", vector) not in self.defects:
                Path(cwd, "marker-%d" % index).write_text("", encoding="ascii")
            return 0, "", ""
        if "ProcessCreationDenied" in code and "venv.EnvBuilder" not in code and "runpy" not in code:
            index = int(re.search(r"marker-(\d+)", code).group(1))
            vector = PROOF_VECTOR_NAMES[index]
            event = PROOF_VECTOR_EVENTS[vector]
            if ("leak_marker", vector) in self.defects:
                Path(cwd, "marker-%d" % index).write_text("", encoding="ascii")
            if ("exit_zero", vector) in self.defects:
                return 0, "CTYPES_EVENTS={}\nDENIED_EVENTS=0\n", ""
            return 71, 'CTYPES_EVENTS={}\nPROVISIONING_ENV_VIOLATION PROCESS_CREATION [[1, "%s", "\'x\'"]]\n' % event, ""
        if "venv.EnvBuilder" in code:
            prefix = re.search(r"\.create\((?:'|\")(.+?)(?:'|\")\)", code).group(1).replace("\\\\", "\\")
            os.makedirs(os.path.join(prefix, "bin"))
            return 0, "E1_PREFIX_CREATED=%s\nCTYPES_EVENTS={}\nDENIED_EVENTS=0\nALLOWED_EVENTS=%s\n" % (
                prefix, self.empty_digest), ""
        if "runpy" in code:
            prefix = os.path.dirname(os.path.dirname(argv[0]))
            site = os.path.join(prefix, "lib", "python3.14", "site-packages")
            info = os.path.join(site, "careeros_proof-0.0.1.dist-info")
            os.makedirs(info)
            rows = ["careeros_proof/__init__.py,sha256=x,1", "careeros_proof-0.0.1.dist-info/RECORD,,"]
            if self.prefix_defect == "other_row":
                rows.append("../../../../outside.txt,sha256=x,1")
            Path(info, "RECORD").write_text("\n".join(rows) + "\n", encoding="utf-8")
            if self.prefix_defect == "bytecode":
                os.makedirs(os.path.join(site, "__pycache__"))
            if self.prefix_defect == "denied":
                return 71, 'CTYPES_EVENTS={}\nPROVISIONING_ENV_VIOLATION PROCESS_CREATION [[1, "subprocess.Popen", "\'lsb_release\'"]]\n', "x"
            if self.prefix_defect == "digest":
                return 0, "E2_PIP_STATUS=0\nCTYPES_EVENTS={}\nDENIED_EVENTS=0\nALLOWED_EVENTS=%s\n" % ("0" * 64), ""
            record = self.e2_record if self.prefix_defect != "record" else self.e2_record[:-1]
            return 0, ('E2_PIP_STATUS=0\nCTYPES_EVENTS={"ctypes.dlopen": 2}\nALLOWED_EVENTS_RECORD=%s\nDENIED_EVENTS=0\n'
                       "ALLOWED_EVENTS=%s\n" % (json.dumps(record), self.e2_digest)), ""
        raise AssertionError("unexpected launch")


def test_process_creation_proof_orchestration() -> None:
    """PROCESS_CREATION_PROOF_V1 orchestration with a fake interpreter: the exact vector list, enumeration
    before denial, the real HOOK_HEAD/HOOK_TAIL of the provisioning script, the proof-prefix E1/E2 forms."""
    verifier = verifier_module()
    script_text = (ROOT / "scripts" / "provision_document_rendering_env.sh").read_text(encoding="utf-8")
    assert_true(tuple(verifier.PROCESS_CREATION_PROOF_VECTORS) == PROOF_VECTOR_NAMES, "the vector list is the contract list")
    assert_true(tuple(verifier.DENIED_EVENT_SET) == ("subprocess.Popen", "os.system", "os.exec", "os.posix_spawn", "os.spawn",
                                                     "os.fork", "os.forkpty", "pty.spawn", "_posixsubprocess.fork_exec"),
                "the denied event set is the contract minimum")
    pip_dir = Path(tempfile.mkdtemp(prefix="career-os-fake-pip-"))
    (pip_dir / "__init__.py").write_text("", encoding="utf-8")
    scratch_root = tempfile.mkdtemp(prefix="career-os-proof-root-")

    prefix_capable = os.name == "posix"  # the RECORD row classes are Linux path logic
    approved = verifier.approved_sequence_of(verifier.extract_embedded(script_text, "HOOK_HEAD_E2"))
    e2_record = verifier.allowed_record_of(approved)
    empty_digest, e2_digest = verifier.canonical_digest([]), verifier.canonical_digest(e2_record)

    def new_host(*args, **kwargs):
        return FakeProcessHost(*args, empty_digest=empty_digest, e2_digest=e2_digest, e2_record=e2_record, **kwargs)

    def run(host, **kwargs):
        kwargs.setdefault("include_prefix_run", prefix_capable)
        kwargs.setdefault("include_sequence_vectors", False)
        kwargs.setdefault("chain_check", lambda: {"result": "PASS"})
        return verifier.process_creation_proof("/fake/python", script_text, host.run, scratch_root,
                                               str(pip_dir), **kwargs)

    try:
        host = new_host()
        record = run(host)
        assert_true(record["result"] == "PASS" and not record["failures"],
                    f"all vectors and the prefix run pass: {record['result']} {record['failures']} "
                    f"{[item for item in record['vectors'] if item.get('result') != 'PASS'][:1]} "
                    f"{record.get('proof_prefix_run')}")
        assert_true([item["vector"] for item in record["vectors"]] == list(PROOF_VECTOR_NAMES), "every vector, in order")
        assert_true(all(item["result"] == "PASS" for item in record["vectors"]), "every vector passes")
        assert_true(record["scratch_removed"] is True and os.listdir(scratch_root) == [], "scratch directory removed")
        if prefix_capable:
            assert_true(record["proof_prefix_run"]["result"] == "PASS"
                        and record["proof_prefix_run"]["record_row_classes"] == ["IN_SITE"]
                        and record["proof_prefix_run"]["e2"]["ctypes_event_counts"] == {"ctypes.dlopen": 2},
                        "proof-prefix run recorded with ctypes counts")
        governed = [code for code in host.calls if "ProcessCreationDenied" in code]
        assert_true(len(governed) == len(PROOF_VECTOR_NAMES) + (2 if prefix_capable else 0),
                    "15 denying runs plus the E1 and E2 governed runs")
        hook_head = verifier.extract_embedded(script_text, "HOOK_HEAD")
        hook_head_e2 = verifier.extract_embedded(script_text, "HOOK_HEAD_E2")
        for code in governed:
            assert_true(code.startswith(hook_head) or code.startswith(hook_head_e2),
                        "the real HOOK_HEAD or HOOK_HEAD_E2 statement is the first statement of every governed run")
        assert_true(sum(code.startswith(hook_head_e2) for code in governed) == (1 if prefix_capable else 0),
                    "only the E2 governed run carries the approved sequence")
        assert_true(record["approved_sequence"]["x0_and_e1"] == [] and record["approved_sequence"]["e2"] == approved
                    and len(approved) == 4, "approved sequences recorded: EMPTY for X0 and E1, four events for E2")
        for code in governed:
            assert_true("DENIED_EVENTS=0" in code and "ALLOWED_EVENTS=" in code, "the real HOOK_TAIL ends every governed run")
        enumerations = [index for index, code in enumerate(host.calls) if "_enumerate" in code]
        assert_true(len(enumerations) == 15, "one enumeration run per vector")
        for position, code in enumerate(host.calls):
            if "_enumerate" in code:
                assert_true("ProcessCreationDenied" not in code, "the enumeration hook is non-denying")
                assert_true("ProcessCreationDenied" in host.calls[position + 1], "denying run follows its enumeration run")

        record = run(new_host({("events", "os.fork"): "os.getpid"}))
        failing = [item for item in record["vectors"] if item["vector"] == "os.fork"][0]
        assert_true(record["result"] == "STOP" and failing["result"] == "STOP" and failing["reason"] == "EVENT_SET_INCOMPLETE",
                    "a marker without a denied-set event is the STOP (event set incomplete on this interpreter)")
        record = run(new_host({("leak_marker", "os.system"): True}))
        assert_true(record["result"] == "FAIL" and "os.system" in record["failures"], "marker present after denial fails")
        record = run(new_host({("exit_zero", "swallowed os.fork"): True}))
        assert_true(record["result"] == "FAIL" and "swallowed os.fork" in record["failures"],
                    "the swallowing vector must still end non-zero")
        record = run(new_host({("no_marker", "os.popen"): True}))
        assert_true(record["result"] == "FAIL" and "os.popen" in record["failures"], "an ineffective vector fails")
        for defect in (("denied", "bytecode", "other_row", "digest", "record") if prefix_capable else ()):
            record = run(new_host(prefix_defect=defect))
            assert_true(record["result"] == "FAIL" and "PROOF_PREFIX_RUN" in record["failures"], f"prefix defect {defect}")
        if prefix_capable:
            record = run(new_host(prefix_defect="denied"))
            assert_true(record["proof_prefix_run"]["e2"]["denied_events"][0][1] == "subprocess.Popen",
                        "denied events of the prefix run are named in the evidence")
        if prefix_capable:
            def failing_chain():
                raise verifier.Rejected("APT_UNEXPECTED_CHANGE", "HOST_TOOL_CHANGED", "TOOL_BYTES", path="/usr/bin/uname")

            record = run(new_host(), chain_check=failing_chain)
            assert_true(record["result"] == "FAIL" and record["proof_prefix_run"]["reason"] == "HELPER_CHAIN_CHECK"
                        and "e2" not in record["proof_prefix_run"], "a failing helper-chain check stops before E2 runs")
            record = run(new_host(), chain_check=None)
            assert_true(record["result"] == "FAIL" and record["proof_prefix_run"]["reason"] == "HELPER_CHAIN_CHECK_MISSING",
                        "the proof-prefix run requires the helper-chain check")
        record = run(new_host(), include_prefix_run=False)
        assert_true(record["result"] == "PASS" and "proof_prefix_run" not in record, "prefix run is optional in the function")
        assert_true(os.listdir(scratch_root) == [], "scratch removed after every run, including failures")
    finally:
        shutil.rmtree(scratch_root, ignore_errors=True)
        shutil.rmtree(pip_dir, ignore_errors=True)
    wheel_dir = tempfile.mkdtemp(prefix="career-os-wheel-")
    try:
        first = verifier.build_proof_wheel(wheel_dir)
        second = verifier.build_proof_wheel(wheel_dir)
        assert_true(first == second and first[1] == hashlib.sha256(Path(first[0]).read_bytes()).hexdigest(),
                    "the proof wheel is deterministic and hashed")
        with zipfile.ZipFile(first[0]) as archive:
            assert_true(sorted(archive.namelist()) == ["careeros_proof-0.0.1.dist-info/METADATA",
                                                       "careeros_proof-0.0.1.dist-info/RECORD",
                                                       "careeros_proof-0.0.1.dist-info/WHEEL",
                                                       "careeros_proof/__init__.py"], "wheel members")
    finally:
        shutil.rmtree(wheel_dir, ignore_errors=True)


def test_process_creation_proof_real_posix_vectors() -> None:
    """The same hook and FINAL_DENIED_CHECK code, the same fixed vector list, in subprocesses of the TEST
    interpreter (not proof for the pinned interpreter; the proof-prefix run needs the pinned pip and is not run here)."""
    if os.name != "posix" or not os.path.exists("/bin/sh"):
        return
    verifier = verifier_module()
    script_text = (ROOT / "scripts" / "provision_document_rendering_env.sh").read_text(encoding="utf-8")
    scratch_root = tempfile.mkdtemp(prefix="career-os-proof-real-")
    try:
        record = verifier.process_creation_proof(sys.executable, script_text, verifier.real_process_proof_runner,
                                                 scratch_root, None, include_prefix_run=False)
    finally:
        shutil.rmtree(scratch_root, ignore_errors=True)
    bad = [item for item in record["vectors"] if item.get("result") != "PASS"]
    assert_true(record["result"] == "PASS" and not bad and len(record["vectors"]) == 15,
                f"real vectors on the test interpreter: {record['result']} {bad}")
    assert_true(record["scratch_removed"] is True, "real proof scratch directory removed")


def build_fake_install(base: Path, manifest: dict, verifier):
    """A fake installed environment for the partial post-evidence mode: base interpreter, stdlib, operator
    prefix with pyvenv.cfg and one dist-info per approved distribution."""
    interpreter_file = base / "base" / "bin" / "python3.14"
    stdlib = base / "base" / "lib" / "python3.14"
    prefix = base / "prefix"
    interpreter_file.parent.mkdir(parents=True)
    stdlib.mkdir(parents=True)
    interpreter_file.write_bytes(b"\x7fELF fake interpreter")
    (stdlib / "os.py").write_text("# stdlib\n", encoding="utf-8")
    site = prefix / "lib" / "python3.14" / "site-packages"
    site.mkdir(parents=True)
    (prefix / "pyvenv.cfg").write_text("home = %s\ninclude-system-site-packages = false\n" % interpreter_file.parent,
                                       encoding="utf-8")
    for name, version in sorted(verifier.approved_installed_set(manifest)):
        module = name.replace("-", "_")
        (site / module).mkdir()
        (site / module / "__init__.py").write_text("# %s\n" % name, encoding="utf-8")
        info = site / ("%s-%s.dist-info" % (module, version))
        info.mkdir()
        (info / "METADATA").write_text("Metadata-Version: 2.1\nName: %s\nVersion: %s\n" % (name, version), encoding="utf-8")
        rows = ["%s/__init__.py,sha256=x,1" % module, "%s/METADATA,sha256=x,1" % info.name, "%s/RECORD,," % info.name]
        (info / "RECORD").write_text("\n".join(rows) + "\n", encoding="utf-8")
    return interpreter_file, stdlib, prefix, site


def fake_post_checkout(base: Path, verifier, **manifest_overrides):
    adapter_module = verifier.load_adapter()
    manifest = json.loads((ROOT / "docs" / "rendering" / "RENDERING_ENVIRONMENT_V1.json").read_text(encoding="utf-8"))
    for key in adapter_module.MANIFEST_POST_PROVISION_KEYS:
        manifest[key] = None  # the committed manifest is the populated runtime manifest; the fake checkout is pre-binding
    interpreter_file, stdlib, prefix, site = build_fake_install(base, manifest, verifier)
    interpreter = manifest["operator_base_interpreter"]
    interpreter["path"] = str(interpreter_file)
    interpreter["executable_sha256"] = hashlib.sha256(interpreter_file.read_bytes()).hexdigest()
    interpreter["stdlib_path"] = str(stdlib)
    interpreter["stdlib_tree_digest"] = verifier.tree_digest(str(stdlib), "STDLIB")
    interpreter["sys_path_isolated"] = [str(stdlib.parent / "python314.zip"), str(stdlib)]
    interpreter["sys_path_isolated_prefix"] = [str(stdlib.parent / "python314.zip"), str(stdlib)]
    manifest["operator_python_prefix"] = str(prefix)
    manifest.update(manifest_overrides)
    checkout = base / "checkout"
    (checkout / "docs" / "rendering").mkdir(parents=True)
    (checkout / "docs" / "rendering" / "RENDERING_ENVIRONMENT_V1.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    for name in ("requirements.in", "requirements-lock.txt"):
        shutil.copyfile(ROOT / name, checkout / name)
    digest = adapter_module.plan_digest(manifest, (checkout / "requirements.in").read_bytes(),
                                        (checkout / "requirements-lock.txt").read_bytes())
    return checkout, manifest, digest, site


def test_post_evidence_partial_vectors() -> None:
    """The deterministic partial POST evidence: derived values recompute under the adapter's own digest
    code, every remaining field is named, nothing empirical is fabricated, failures are closed."""
    committed = (ROOT / "docs" / "rendering" / "RENDERING_ENVIRONMENT_V1.json").read_bytes()
    populated = adapter.verify_manifest(committed)
    assert_true(all(populated[key] is not None for key in adapter.MANIFEST_POST_PROVISION_KEYS)
                and populated["manifest_self_digest"] == adapter.manifest_digest(populated),
                "the committed runtime manifest is fully populated and passes the S2.01 data rules")
    pre_binding = json.loads(committed.decode("utf-8"))
    for key in adapter.MANIFEST_POST_PROVISION_KEYS:
        pre_binding[key] = None
    real_manifest = json.dumps(pre_binding, indent=2, ensure_ascii=False).encode("utf-8")
    result = outcome_of(adapter.verify_manifest, real_manifest)
    assert_true(result is not None and result[1] == "POST_BINDING_UNPOPULATED",
                f"the runtime still rejects a manifest whose POST keys are null: {result}")
    if os.name != "posix":
        return  # the installed-environment path logic (RECORD row classes, site-packages walk) is Linux logic
    verifier = verifier_module()
    adapter_module = verifier.load_adapter()
    saved = verifier.dpkg_installed_version
    base = Path(tempfile.mkdtemp(prefix="career-os-post-evidence-"))
    try:
        checkout, manifest, digest, site = fake_post_checkout(base, verifier)
        versions = {(item["name"], item["architecture"]): item["version"] for item in manifest["apt_plan"]["packages"]}
        verifier.dpkg_installed_version = lambda name, architecture: versions.get((name, architecture))
        record = verifier.post_evidence(checkout, digest)
        assert_true(record["mode"] == "POST_EVIDENCE_PARTIAL" and record["plan_digest_verified"] is True
                    and record["approved_plan_digest"] == digest, "the approved PLAN_DIGEST is recomputed and verified")
        assert_true(record["post_binding_complete"] is False, "the record states that POST binding is not complete")
        post_keys = set(adapter_module.MANIFEST_POST_PROVISION_KEYS)
        assert_true(set(record["manifest_post_keys_still_null"]) == post_keys, "every POST key was null in the input")
        deferred = record["deferred"]
        covered = (set(deferred["empirical_post_fields"]) | set(deferred["provisioning_evidence_post_fields"])
                   | {"approved_plan_digest", "content_binding", "manifest_self_digest"})
        assert_true(covered == post_keys, "derived plus deferred fields are exactly the POST keys: %s" % (post_keys ^ covered))
        for field in ("canonical_families", "docx_family_to_canonical", "pdf_basefont_to_canonical",
                      "pdfminer_type0_name_form", "marker_glyph_map", "sandbox_read_only_paths", "sandbox_dirs",
                      "sandbox_symlinks", "sandbox_expected_unreachable_errnos", "approved_substitutions"):
            assert_true(field in deferred["empirical_post_fields"], f"{field} stays a real-render or sandbox value")
        derived = record["derived"]["content_binding_partial"]
        roots = derived["roots"]
        ids = [root["id"] for root in roots]
        assert_true(ids == sorted(ids) and len(ids) == len(set(ids)), "root ids are unique and sorted")
        kinds = {root["id"]: root["kind"] for root in roots}
        assert_true(kinds["f.base_interpreter"] == "FILE" and kinds["g.stdlib"] == "STDLIB_TREE"
                    and kinds["h.prefix_pyvenv_cfg"] == "FILE", "roots (f), (g) and (h)")
        dists = [root for root in roots if root["kind"] == "DIST_RECORD"]
        assert_true(len(dists) == len(verifier.approved_installed_set(manifest)) == 11, "a DIST_RECORD root per approved member")
        assert_true([root["path"] for root in roots if root["kind"] == "ABSENT"] and all(
            root["expected_digest"] == adapter_module.ABSENT_ROOT_DIGEST for root in roots if root["kind"] == "ABSENT"),
                    "ABSENT roots for the non-existent sys.path entries")
        assert_true(derived["runtime_sys_path"][-1] == str(site) and derived["runtime_sys_path"][:-1] ==
                    manifest["operator_base_interpreter"]["sys_path_isolated_prefix"], "runtime_sys_path appends the site-packages")
        distributions = verifier.installed_distributions(str(site))
        for root in roots:
            again = adapter_module.root_digest(root, (), {}, lambda name: (str(site), distributions[name][1]))
            assert_true(again == root["expected_digest"], f"root {root['id']} recomputes under the adapter digest code")
        assert_true(record["derived"]["approved_plan_digest"] == digest, "approved_plan_digest value")
        assert_true("provisioning_evidence" not in record, "no provisioning evidence unless supplied")
        again = verifier.post_evidence(checkout, digest, "EVIDENCE apt_get_version=apt 2.7.14\nEVIDENCE apt_install_argv=a b\n"
                                                         "EVIDENCE apt_installed_delta=x\nEVIDENCE apt_installed_delta=y\n"
                                                         "EVIDENCE result=PROVISIONED prefix=/p\nnoise\n")
        evidence = again["provisioning_evidence"]
        assert_true(evidence["line_counts"]["apt_installed_delta"] == 2 and evidence["apt_get_version"] == "apt 2.7.14"
                    and evidence["apt_install_argv"] == "a b" and evidence["result"].startswith("PROVISIONED"),
                    "provisioning evidence lines are parsed verbatim and counted")
        assert_true(again["derived"] == record["derived"], "the derived record is deterministic")

        def failure(**changes):
            return outcome_reason(verifier, lambda: verifier.post_evidence(checkout, changes.get("digest", digest)))

        assert_true(failure(digest="0" * 64) == "PLAN_DIGEST", "a different approved PLAN_DIGEST fails closed")
        (site / "rogue.py").write_text("x = 1\n", encoding="utf-8")
        assert_true(failure() == "UNBOUND_CODE", "an unlisted file in site-packages fails closed")
        (site / "rogue.py").unlink()
        verifier.dpkg_installed_version = lambda name, architecture: "0:wrong"
        assert_true(failure() == "APT_PIN", "an apt pin mismatch fails closed")
        verifier.dpkg_installed_version = lambda name, architecture: versions.get((name, architecture))
        victim = sorted(site.glob("*.dist-info"))[0]
        shutil.rmtree(victim)
        assert_true(failure() == "DEPENDENCY_SET", "a missing approved distribution fails closed")
        populated_checkout, _, populated_digest, _ = fake_post_checkout(base / "second", verifier, sandbox_path="/usr/bin")
        assert_true(outcome_reason(verifier, lambda: verifier.post_evidence(populated_checkout, populated_digest))
                    == "POST_KEYS_NOT_NULL", "the input manifest must have every POST key null")
    finally:
        verifier.dpkg_installed_version = saved
        shutil.rmtree(base, ignore_errors=True)


def test_process_creation_record_v2_sequence_vectors() -> None:
    """PROCESS_CREATION_RECORD_V2 on the real HOOK_HEAD / HOOK_HEAD_E2 / HOOK_TAIL code in subprocesses of the
    test interpreter, with synthetic audit events (no process is created): the exact approved sequence passes
    only under HOOK_HEAD_E2, X0 and E1 (EMPTY sequence) deny it, and every deviation fails closed."""
    verifier = verifier_module()
    script_text = (ROOT / "scripts" / "provision_document_rendering_env.sh").read_text(encoding="utf-8")
    hook_head = verifier.extract_embedded(script_text, "HOOK_HEAD")
    hook_head_e2 = verifier.extract_embedded(script_text, "HOOK_HEAD_E2")
    hook_tail = verifier.extract_embedded(script_text, "HOOK_TAIL")
    approved = verifier.approved_sequence_of(hook_head_e2)
    assert_true(verifier.approved_sequence_of(hook_head) == [], "X0 and E1 carry an EMPTY approved sequence")
    assert_true([item[0] for item in approved] == ["subprocess.Popen", "_posixsubprocess.fork_exec"] * 2,
                "E2 approved sequence is Popen/fork_exec for lsb_release then Popen/fork_exec for uname")
    assert_true(approved[0][1] == "('lsb_release', ['lsb_release', '-a'], None, None)"
                and approved[2][1] == "('uname', ['uname', '-rs'], None, None)", "exact helper argv, cwd None, env None")
    assert_true("(b'/usr/sbin/lsb_release', b'/usr/bin/lsb_release', b'/sbin/lsb_release', b'/bin/lsb_release')" in approved[1][1]
                and "(b'/usr/sbin/uname', b'/usr/bin/uname', b'/sbin/uname', b'/bin/uname')" in approved[3][1],
                "executable lists derived from the closed PATH in PATH order")
    constants = verifier.script_chain_constants(script_text)
    assert_true(verifier.canonical_digest([]) == constants["EMPTY_ALLOWED_SHA256"]
                and verifier.canonical_digest(verifier.allowed_record_of(approved)) == constants["E2_ALLOWED_SHA256"],
                "the allowed-record digests in the script are the canonical digests of the approved sequences")
    assert_true(hook_head.count("addaudithook") == 1 and hook_head_e2.count("addaudithook") == 1
                and hook_head.split("\n")[0].startswith("# PROCESS_CREATION_DENY_V1")
                and hook_head.split("\n")[1].startswith('__import__("sys").addaudithook('),
                "the hook is one statement and the first statement of the code")
    scratch = tempfile.mkdtemp(prefix="career-os-seq-vectors-")
    environment = {"PATH": os.environ.get("PATH", ""), "LANG": "C", "LC_ALL": "C", "PYTHONDONTWRITEBYTECODE": "1"}
    for name in ("SYSTEMROOT", "SYSTEMDRIVE", "TEMP", "TMP"):
        if name in os.environ:
            environment[name] = os.environ[name]
    try:
        results = verifier._sequence_vectors(sys.executable, scratch, verifier.real_process_proof_runner, environment,
                                             hook_head, hook_head_e2, hook_tail, approved,
                                             verifier.canonical_digest(verifier.allowed_record_of(approved)),
                                             verifier.canonical_digest([]))
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
    by_name = {item["case"]: item for item in results}
    assert_true(list(by_name) == ["exact_e2_sequence", "empty_sequence_no_events", "exact_sequence_under_empty_sequence",
                                  "missing_last_event", "additional_event", "repeated_first_event", "reordered_events",
                                  "different_argv", "different_executable_list", "different_executable", "cwd_set",
                                  "env_set", "other_process"], f"every vector case, in order: {list(by_name)}")
    bad = [item for item in results if item["result"] != "PASS"]
    assert_true(not bad, f"every sequence vector behaves as specified: {bad}")
    assert_true(by_name["missing_last_event"]["expected"] == "SEQUENCE" and by_name["exact_e2_sequence"]["expected"] == "PASS",
                "a missing event is its own failure and the exact sequence is the only E2 success")


FIXTURE_SHELL_SCRIPT = (
    "#!/bin/sh\nhelp () {\n\tcat <<- EOD\n\tUsage: fixture [options]\n\tEOD\n\texit\n}\nshow=false\n"
    "options=$(getopt --name fixture -o ha -l help,all -- \"$@\") || exit 2\neval set -- \"$options\"\n"
    "while [ $# -gt 0 ] ; do\n\tcase \"$1\" in\n\t\t-h|--help) help ;;\n\t\t-a|--all) show=true ;;\n\t\t*) break  ;;\n"
    "\tesac\n\tshift\ndone\n[ -f /usr/lib/os-release ] && os_release=/usr/lib/os-release\n"
    "[ -f /etc/os-release ] && os_release=/etc/os-release\n[ \"${os_release-x}\" != \"x\" ] && . \"$os_release\"\n"
    ": \"${ID=}\"\nID=\"$(printf \"%s\" \"$ID\" | cut -c1 | tr '[:lower:]' '[:upper:]')$(printf \"%s\" \"$ID\" | cut -c2-)\"\n"
    "if [ \"${NAME-x}\" != \"x\" ] ; then\n\tlower_id=$(printf \"%s\" \"$ID\" | tr '[:upper:]' '[:lower:]')\n"
    "\tlower_name=$(printf \"%s\" \"$NAME\" | tr '[:upper:]'  '[:lower:]')\nfi\n[ -t 1 ] && echo \"x\" >& 2\n"
    "if $show ; then\n\tprintf \"%s\\n\" \"$ID\"\nfi\n")


class FakeChainHost:
    """A fake host for the helper-chain capture and check: files by invoked path."""

    def __init__(self, shell_text=FIXTURE_SHELL_SCRIPT) -> None:
        self.files = {}
        self.links = {}
        self.owners_of = {}
        self.versions = {}
        data = {"/usr/bin/lsb_release": shell_text.encode("utf-8"), "/usr/bin/uname": b"ELF uname",
                "/usr/bin/dash": b"ELF dash", "/usr/bin/cut": b"ELF cut", "/usr/bin/getopt": b"ELF getopt",
                "/usr/bin/tr": b"ELF tr", "/usr/bin/cat": b"ELF cat", "/usr/lib/os-release": b'NAME="Ubuntu"\nID=ubuntu\n'}
        owners = {"/usr/bin/lsb_release": "lsb-release", "/usr/bin/uname": "coreutils", "/usr/bin/dash": "dash",
                  "/usr/bin/cut": "coreutils", "/usr/bin/getopt": "util-linux", "/usr/bin/tr": "coreutils",
                  "/usr/bin/cat": "coreutils", "/usr/lib/os-release": "base-files"}
        versions = {"lsb-release": "12.0-2", "coreutils": "9.4-3", "dash": "0.5.12-6", "util-linux": "2.39.3-9",
                    "base-files": "13ubuntu10.5"}
        self.files.update(data)
        self.owners_of.update(owners)
        self.versions.update(versions)
        self.links.update({"/bin/sh": "dash", "/etc/os-release": "../usr/lib/os-release"})
        self.real = {"/bin/sh": "/usr/bin/dash", "/etc/os-release": "/usr/lib/os-release"}

    def exists_path(self, path):
        return path in self.files or path in self.real

    def lexists(self, path):
        return self.exists_path(path)

    def islink(self, path):
        return path in self.links

    def isfile(self, path):
        return path in self.files

    def readlink(self, path):
        return self.links[path]

    def realpath(self, path):
        return self.real.get(path, path)

    def read_bytes(self, path):
        return self.files[self.real.get(path, path)]

    def owners(self, real_path):
        return [self.owners_of[real_path]] if real_path in self.owners_of else []

    def version(self, package):
        return self.versions[package]


def test_e2_helper_chain_static_analysis_capture_and_check() -> None:
    """E2_HELPER_CHAIN_V1: static derivation of the descendant set from the hash-bound helper script, the
    manifest record captured from a host without executing anything, and the hash-first check of every member."""
    verifier = verifier_module()
    script_text = (ROOT / "scripts" / "provision_document_rendering_env.sh").read_text(encoding="utf-8")
    counts = verifier.static_external_counts(FIXTURE_SHELL_SCRIPT)
    assert_true(counts == {"cat": 1, "getopt": 1, "cut": 2, "tr": 3}, f"static external command counts: {counts}")
    assert_true(verifier.parse_xtrace_counts("+ getopt --name x\n+ printf %s a\n++ cut -c1\n++ tr [:lower:] [:upper:]\n"
                                             "+ display_line a b\n+ ID=x\n", ("display_line",))
                == {"getopt": 1, "cut": 1, "tr": 1}, "xtrace parsing keeps only external commands")
    assert_true(verifier.compare_observation(counts, {"cut": 2, "tr": 3, "getopt": 1})["consistent"] is True
                and verifier.compare_observation(counts, {"cut": 3})["consistent"] is False
                and verifier.compare_observation(counts, {"sed": 1})["unexpected_commands"] == ["sed"],
                "an observation must use only derivable commands, each at most as often")

    host = FakeChainHost()
    chain = verifier.capture_e2_helper_chain(host, script_text, observed_counts={"getopt": 1, "cut": 2, "tr": 3})
    constants = verifier.script_chain_constants(script_text)
    assert_true([row[0] for row in verifier.chain_rows(chain)] == constants["E2_CHAIN_TOOLS"]
                and chain["absent_candidates"] == constants["E2_CHAIN_ABSENT"], "records follow the script's constants")
    assert_true([item["name"] for item in chain["descendants"]] == ["cut", "getopt", "tr"]
                and [item["multiplicity"] for item in chain["descendants"]] == [2, 1, 3]
                and chain["closed_list_covered"] == ["cat"], "descendants, multiplicities and closed-list coverage")
    assert_true(chain["interpreter"]["invoked_path"] == "/bin/sh" and chain["interpreter"]["realpath"] == "/usr/bin/dash"
                and chain["interpreter"]["link_string"] == "dash", "the shell named by the script's first line")
    assert_true([item["invoked_path"] for item in chain["data_files"]] == ["/usr/lib/os-release", "/etc/os-release"]
                and chain["data_files"][1]["link_string"] == "../usr/lib/os-release", "sourced data file and link binding")
    assert_true(chain["sequence"] == verifier.approved_sequence_of(verifier.extract_embedded(script_text, "HOOK_HEAD_E2")),
                "the sequence is the script's approved sequence")
    assert_true(chain["observation_evidence"]["consistent"] is True, "the observation cross-check is recorded")
    result = verifier.check_e2_helper_chain(json.loads(json.dumps(chain)), host, script_text)
    assert_true(result["result"] == "PASS" and result["members"] == constants["E2_CHAIN_TOOLS"], "the check passes on the captured host")

    def failure(callable_):
        return outcome_reason(verifier, callable_)

    def mutated(path, content=None, owner=None, version=None, link=None, present=None, lines=None):
        other = FakeChainHost()
        if content is not None:
            other.files[path] = content
        if owner is not None:
            other.owners_of[path] = owner
            other.versions.setdefault(owner, "1")
        if version is not None:
            other.versions[other.owners_of[path]] = version
        if link is not None:
            other.links[path] = link
        if present is not None:
            other.files[present] = b"x"
        return other

    def check(host_):
        return verifier.check_e2_helper_chain(json.loads(json.dumps(chain)), host_, script_text)

    assert_true(failure(lambda: check(mutated("/usr/bin/tr", content=b"ELF tr!"))) == "HOST_TOOL_CHANGED", "helper hash mismatch")
    assert_true(failure(lambda: check(mutated("/usr/bin/uname", content=b"ELF other"))) == "HOST_TOOL_CHANGED", "helper bytes differ")
    assert_true(failure(lambda: check(mutated("/usr/lib/os-release", content=b"x"))) == "HOST_TOOL_CHANGED", "data file hash mismatch")
    assert_true(failure(lambda: check(mutated("/usr/bin/cut", owner="othercoreutils"))) == "HOST_TOOL_PACKAGE", "owner package mismatch")
    assert_true(failure(lambda: check(mutated("/usr/bin/dash", version="0.5.13"))) == "HOST_TOOL_PACKAGE", "owner version mismatch")
    assert_true(failure(lambda: check(mutated("/etc/os-release", link="../elsewhere"))) == "HOST_TOOL_CHANGED", "link binding mismatch")
    for candidate in constants["E2_CHAIN_ABSENT"]:
        assert_true(failure(lambda: check(mutated(None, present=candidate))) == "HOST_TOOL_CHANGED",
                    f"an earlier PATH candidate that becomes present fails: {candidate}")
    tampered = json.loads(json.dumps(chain))
    tampered["sequence"][0][1] = tampered["sequence"][0][1].replace("-a", "-r")
    assert_true(failure(lambda: verifier.check_e2_helper_chain(tampered, host, script_text)) == "E2_HELPER_CHAIN", "sequence differs from the script")
    tampered = json.loads(json.dumps(chain))
    tampered["descendants"] = tampered["descendants"][:2]
    assert_true(failure(lambda: verifier.check_e2_helper_chain(tampered, host, script_text)) == "E2_HELPER_CHAIN", "tool list differs from the script")
    tampered = json.loads(json.dumps(chain))
    tampered["absent_candidates"] = tampered["absent_candidates"][:-1]
    assert_true(failure(lambda: verifier.check_e2_helper_chain(tampered, host, script_text)) == "E2_HELPER_CHAIN", "absent list differs from the script")

    assert_true(failure(lambda: verifier.capture_e2_helper_chain(FakeChainHost("#!/bin/bash\n" + FIXTURE_SHELL_SCRIPT[10:]), script_text))
                == "E2_HELPER_CHAIN", "a helper script that is not a /bin/sh script is not bound")
    assert_true(failure(lambda: verifier.capture_e2_helper_chain(
        FakeChainHost(FIXTURE_SHELL_SCRIPT.replace("os_release=/etc/os-release", "os_release=/etc/other")),
        script_text)) == "E2_HELPER_CHAIN", "an unexpected sourced data file is not bound")
    assert_true(failure(lambda: verifier.capture_e2_helper_chain(host, script_text, observed_counts={"sed": 1}))
                == "E2_HELPER_CHAIN", "an observation outside the derivation is a stop")
    assert_true(failure(lambda: verifier.capture_e2_helper_chain(mutated(None, present="/usr/sbin/tr"), script_text))
                in ("HOST_TOOL_CHANGED", "E2_HELPER_CHAIN"), "a preceding PATH candidate at capture time is refused")
    unowned = FakeChainHost()
    del unowned.owners_of["/usr/bin/getopt"]
    assert_true(failure(lambda: verifier.capture_e2_helper_chain(unowned, script_text)) == "E2_HELPER_CHAIN", "an unowned member is refused")


def test_provisioning_script_e2_helper_chain_static_rules() -> None:
    """Static rules of the provisioning script for E2_HELPER_CHAIN_V1."""
    verifier = verifier_module()
    script_text = (ROOT / "scripts" / "provision_document_rendering_env.sh").read_text(encoding="utf-8")
    constants = verifier.script_chain_constants(script_text)
    assert_true(constants["E2_CHAIN_TOOLS"] == ["/usr/bin/lsb_release", "/usr/bin/uname", "/bin/sh", "/usr/bin/cut",
                                                "/usr/bin/getopt", "/usr/bin/tr", "/usr/lib/os-release", "/etc/os-release"],
                "the admitted chain members")
    assert_true(constants["E2_CHAIN_ABSENT"] == ["/usr/sbin/cut", "/usr/sbin/getopt", "/usr/sbin/lsb_release", "/usr/sbin/tr",
                                                "/usr/sbin/uname"], "the required-absent earlier PATH candidates")
    functions = script_text[script_text.index("#BEGIN FUNCTIONS"):]
    assert_true(re.search(r"\b_x\b[^\n]*\b(lsb_release|uname|getopt)\b", functions) is None
                and "T_LSB" not in script_text, "the script never executes a chain member")
    step1 = functions[functions.index("_step1() {"):functions.index("_step2() {")]
    assert_true(step1.index("_host_tool_record") < step1.index("_chain_record") < step1.index("_create_private_tool"),
                "the chain is recorded in step 1 right after HOST_TOOL_RECORD_V1, before the private hash tool")
    recheck = functions[functions.index("_tool_recheck() {"):functions.index("# -- ELF facts")]
    assert_true("_chain_absent_check" in recheck and recheck.index("#T2_T3_END") < recheck.index("_chain_absent_check"),
                "the absent candidates are re-verified at every recheck")
    record_function = functions[functions.index("_chain_record() {"):functions.index("_chain_rows_json() {")]
    assert_true("_record_tool" in record_function and "UNOWNED" in record_function,
                "chain members go through the host-tool record and must be package-owned")
    governed = functions[functions.index("_governed() {"):functions.index("# -- APT_TRUST_MODEL_V1")]
    assert_true('ALLOWED_EVENTS=$expected_allowed' in governed and '"$label" == E2' in governed
                and "EMPTY_ALLOWED_SHA256" in governed and "E2_ALLOWED_SHA256" in governed,
                "every governed execution requires DENIED_EVENTS=0 and the approved ALLOWED_EVENTS digest")
    assert_true('E2_CODE="$HOOK_HEAD_E2$PROBE$E2_BODY$HOOK_TAIL"' in script_text
                and 'X0_CODE="$HOOK_HEAD$PROBE$X0_BODY$HOOK_TAIL"' in script_text
                and 'E1_CODE="$HOOK_HEAD$PROBE$E1_BODY$HOOK_TAIL"' in script_text,
                "X0 and E1 run under the EMPTY sequence, E2 under the approved sequence")
    assert_true("e2_hook_head.py" in script_text and "e2_chain_rows" in script_text and "e2_chain_absent" in script_text
                and "e2_allowed_sha256" in script_text, "step 2 hands the chain records and constants to X0")
    x0 = verifier.extract_embedded(script_text, "X0")
    for token in ("approved_sequence(", "chain_rows(", 'chain.get("sequence") != approved_events',
                  'proven["e2_allowed_sha256"]', 'proven["e2_chain_rows"]', 'proven["e2_chain_absent"]'):
        assert_true(token in x0, f"X0 verifies the manifest chain record: {token}")
    class GovernedAbort(Exception):
        pass

    def governed_abort_stub(*args):
        raise GovernedAbort(args)

    def digest_stub(value):
        return verifier.canonical_digest(value)

    namespace = {"json": json, "hashlib": hashlib, "os": os, "governed_abort": governed_abort_stub, "digest": digest_stub}
    functions_source = ast.parse(x0)
    wanted = [node for node in functions_source.body if isinstance(node, ast.FunctionDef)
              and node.name in ("approved_sequence", "chain_rows", "verify_e2_helper_chain")]
    assert_true(len(wanted) == 3, "X0 defines the three chain functions")
    exec(compile(ast.Module(body=wanted, type_ignores=[]), "x0-helpers", "exec"), namespace)
    sample = {"helpers": [{"invoked_path": "a", "realpath": "ra", "sha256": "s", "owner_packages": ["p", "q"],
                           "owner_versions": ["1", "2"], "link_string": ""}], "interpreter": {
        "invoked_path": "b", "realpath": "rb", "sha256": "t", "owner_packages": ["d"], "owner_versions": ["3"], "link_string": "dash"},
              "descendants": [], "data_files": []}
    assert_true(namespace["chain_rows"](sample) == verifier.chain_rows(sample), "X0 flattening equals the verifier flattening")
    head_text = verifier.extract_embedded(script_text, "HOOK_HEAD_E2")
    assert_true(namespace["approved_sequence"](head_text) == verifier.approved_sequence_of(head_text),
                "X0 reads the approved sequence from the same syntax tree")
    chain = verifier.capture_e2_helper_chain(FakeChainHost(), script_text)
    rows = verifier.chain_rows(chain)
    proven = {"e2_allowed_sha256": constants["E2_ALLOWED_SHA256"], "empty_allowed_sha256": constants["EMPTY_ALLOWED_SHA256"],
              "e2_chain_rows": json.dumps(rows), "e2_chain_absent": json.dumps(constants["E2_CHAIN_ABSENT"])}
    base = {"e2_helper_chain": json.loads(json.dumps(chain))}

    def x0_outcome(base_, proven_):
        try:
            namespace["verify_e2_helper_chain"](base_, proven_, head_text)
        except GovernedAbort as exc:
            return exc.args[0][1:3]
        return None

    assert_true(x0_outcome(base, proven) is None, "X0 accepts a manifest record equal to the live host record")
    changed_rows = [list(row) for row in rows]
    changed_rows[3][2] = "0" * 64
    assert_true(x0_outcome(base, dict(proven, e2_chain_rows=json.dumps(changed_rows))) == ("E2_HELPER_CHAIN", "TOOL_RECORD"),
                "a live hash that differs from the manifest record aborts before pip")
    changed_rows = [list(row) for row in rows]
    changed_rows[0][3] = "other-package"
    assert_true(x0_outcome(base, dict(proven, e2_chain_rows=json.dumps(changed_rows))) == ("E2_HELPER_CHAIN", "TOOL_RECORD"),
                "a live owner that differs aborts")
    assert_true(x0_outcome(base, dict(proven, e2_chain_absent=json.dumps(constants["E2_CHAIN_ABSENT"][:-1])))
                == ("E2_HELPER_CHAIN", "ABSENT_CANDIDATES"), "a different absent-candidate list aborts")
    assert_true(x0_outcome(base, dict(proven, e2_allowed_sha256="0" * 64)) == ("E2_HELPER_CHAIN", "ALLOWED_DIGEST"),
                "an allowed-record digest that differs from the approved sequence aborts")
    assert_true(x0_outcome(base, dict(proven, empty_allowed_sha256="0" * 64)) == ("E2_HELPER_CHAIN", "ALLOWED_DIGEST"),
                "an EMPTY-sequence digest that differs aborts")
    broken = json.loads(json.dumps(base))
    broken["e2_helper_chain"]["sequence"] = broken["e2_helper_chain"]["sequence"][:3]
    assert_true(x0_outcome(broken, proven) == ("E2_HELPER_CHAIN", "SEQUENCE"), "a manifest sequence that differs aborts")
    assert_true(x0_outcome({"e2_helper_chain": None}, proven) == ("PLAN_INCOMPLETE", "e2_helper_chain"),
                "a null helper-chain member is an incomplete plan")
    for head in (verifier.extract_embedded(script_text, "HOOK_HEAD"), head_text):
        assert_true(head.count("ProcessCreationDenied") >= 1 and "ALLOWED_EVENTS := []" in head
                    and "APPROVED_SEQUENCE :=" in head, "both heads carry the V2 record state")


MANIFEST_LIST_HARNESS = r'''#!/bin/bash
# Sources ONLY the provisioning script's function block and exercises the real _manifest_string_list.
set -u
export LC_ALL=C
SCRIPT=$1
MANIFEST=$2
eval "$(sed -n '/^#BEGIN FUNCTIONS/,/^#END FUNCTIONS/p' "$SCRIPT")"
MAIN_PID=$$
real_manifest=$(<"$MANIFEST")

run_case() {   # name, text, key, expectation (OK:<n> | ABORT:<detail>)
    local name=$1 text=$2 key=$3 want=$4 out rc
    out=$( ( MAIN_PID=$BASHPID; _manifest_string_list "$text" "$key" && { echo "ITEMS ${#LIST[@]}"; printf 'ITEM %s\n' "${LIST[@]}"; } ) 2>&1 )
    rc=$?
    echo "CASE $name | rc=$rc | $(printf '%s' "$out" | tr '\n' '~')"
}

run_case one_item '{"k": ["/a"]}' k x
run_case two_items_one_line '{"k": ["/a", "/bb"]}' k x
run_case multi_line_items $'{"k": [\n  "/usr/a1",\n  "/usr/bb22",\n  "/usr/ccc333"\n]}' k x
run_case empty_list '{"k": []}' k x
run_case real_sys_path_isolated "$real_manifest" sys_path_isolated x
run_case real_sys_path_isolated_prefix "$real_manifest" sys_path_isolated_prefix x
run_case missing_comma '{"k": ["/a" "/b"]}' k x
run_case unquoted_item '{"k": [/a]}' k x
run_case trailing_garbage '{"k": ["/a", ]}' k x
run_case missing_key '{"j": ["/a"]}' k x
run_case duplicate_key '{"k": ["/a"], "x": {"k": ["/b"]}}' k x
run_case control_character_item $'{"k": ["/a\x01b"]}' k x
run_case tab_character_item $'{"k": ["/a\tb"]}' k x
run_case backslash_item '{"k": ["/a\\b"]}' k x
run_case non_ascii_item $'{"k": ["/a\xc3\xa9"]}' k x

# BASH_REMATCH is overwritten by _printable (its own regex match): list advancement must not depend on it.
re_probe=$( [[ "/usr/x" =~ ^(/usr)/(x)$ ]]; _printable "abc"; echo "${BASH_REMATCH[0]}" )
echo "PROBE _printable_overwrites_BASH_REMATCH=$([[ "$re_probe" == abc ]] && echo yes || echo no)"
_printable_original=$(declare -f _printable)
eval "_printable_inner() ${_printable_original#_printable ()}"
_printable() { [[ "scramble" =~ ^(s)(c)(r)(a)(m)(b)(l)(e)$ ]]; _printable_inner "$1"; }
run_case scrambled_rematch_multi_item "$real_manifest" sys_path_isolated x
run_case scrambled_rematch_prefix "$real_manifest" sys_path_isolated_prefix x
'''


def test_manifest_list_parser_bash_rematch_regression() -> None:
    """Gate-(3) real stop: _manifest_string_list advanced with ${#BASH_REMATCH[0]} after _printable had overwritten
    BASH_REMATCH. The real function block is sourced into bash and driven through every parsing case."""
    bash = shutil.which("bash")
    if bash is None:
        return
    script_text = (ROOT / "scripts" / "provision_document_rendering_env.sh").read_text(encoding="utf-8")
    function_text = script_text[script_text.index("_manifest_string_list() {"):]
    function_text = function_text[:function_text.index("\n}\n") + 3]
    assert_true("matched=${#BASH_REMATCH[0]}" in function_text and "body=${body:matched}" in function_text
                and "${#BASH_REMATCH[0]}}" not in function_text,
                "the match length is captured before _printable runs and used for advancement")
    assert_true(function_text.index("matched=${#BASH_REMATCH[0]}") < function_text.index('_printable "$item"'),
                "the match length is captured BEFORE _printable runs")
    with tempfile.TemporaryDirectory(prefix="career-os-list-harness-") as scratch:
        harness = Path(scratch) / "harness.sh"
        harness.write_text(MANIFEST_LIST_HARNESS, encoding="utf-8", newline="\n")
        # The provisioning script parses the PRE_PROVISION_PLAN manifest; the committed file is the populated runtime
        # manifest, so the harness gets its pre-binding form (POST keys null, every PRE member byte-identical).
        pre_binding = json.loads((ROOT / "docs" / "rendering" / "RENDERING_ENVIRONMENT_V1.json").read_text(encoding="utf-8"))
        for key in adapter.MANIFEST_POST_PROVISION_KEYS:
            pre_binding[key] = None
        pre_manifest = Path(scratch) / "RENDERING_ENVIRONMENT_V1.json"
        pre_manifest.write_text(json.dumps(pre_binding, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
        completed = __import__("subprocess").run(
            [bash, str(harness), "scripts/provision_document_rendering_env.sh", str(pre_manifest)],
            cwd=str(ROOT), capture_output=True, timeout=900)
    output = completed.stdout.decode("utf-8", "replace")
    cases = {}
    for line in output.split("\n"):
        line = line.rstrip("\r")
        if line.startswith("CASE "):
            name, rc, body = (part.strip() for part in line[5:].split("|", 2))
            cases[name] = (rc, body.split("~"))
    manifest = json.loads((ROOT / "docs" / "rendering" / "RENDERING_ENVIRONMENT_V1.json").read_text(encoding="utf-8"))
    base = manifest["operator_base_interpreter"]

    def items(name):
        rc, body = cases[name]
        assert_true(rc == "rc=0" and body[0].startswith("ITEMS "), f"{name} parses: {rc} {body[:2]}")
        return int(body[0].split()[1]), [row[5:] for row in body[1:] if row.startswith("ITEM ")]

    count, parsed = items("one_item")
    assert_true(count == 1 and parsed == ["/a"], "one-item list parses")
    assert_true(items("two_items_one_line") == (2, ["/a", "/bb"]), "two items on one line parse")
    assert_true(items("multi_line_items") == (3, ["/usr/a1", "/usr/bb22", "/usr/ccc333"]), "multi-line items of different lengths parse")
    assert_true(items("empty_list") == (0, []), "an empty list parses to no items")
    assert_true(items("real_sys_path_isolated") == (len(base["sys_path_isolated"]), base["sys_path_isolated"])
                and len(base["sys_path_isolated"]) >= 3, "the real multi-item sys_path_isolated parses completely")
    assert_true(items("real_sys_path_isolated_prefix") == (len(base["sys_path_isolated_prefix"]), base["sys_path_isolated_prefix"]),
                "the real multi-item sys_path_isolated_prefix parses completely")
    assert_true(items("trailing_garbage") == (1, ["/a"]),
                "the unchanged item grammar still tolerates one trailing comma (not widened, not narrowed by the fix)")
    for name in ("missing_comma", "unquoted_item", "control_character_item", "tab_character_item",
                 "backslash_item", "non_ascii_item"):
        rc, body = cases[name]
        assert_true(rc != "rc=0" and "reason=SYS_PATH_UNBOUND detail=MANIFEST_LIST:k" in " ".join(body),
                    f"{name} still fails with the same error class: {rc} {body}")
    for name, detail in (("missing_key", "MANIFEST:k"), ("duplicate_key", "MANIFEST_DUPLICATE:k")):
        rc, body = cases[name]
        assert_true(rc != "rc=0" and ("detail=" + detail) in " ".join(body), f"{name} still fails: {rc} {body}")
    assert_true("PROBE _printable_overwrites_BASH_REMATCH=yes" in output.replace("\r", ""),
                "_printable does overwrite BASH_REMATCH, which the parser must not depend on")
    assert_true(items("scrambled_rematch_multi_item") == (len(base["sys_path_isolated"]), base["sys_path_isolated"])
                and items("scrambled_rematch_prefix") == (len(base["sys_path_isolated_prefix"]), base["sys_path_isolated_prefix"]),
                "a _printable that scrambles BASH_REMATCH further does not affect list advancement")


def test_tag_sequence_generator_v1_reproduces_sys_tags() -> None:
    """TAG_SEQUENCE_GENERATOR_V1 (canonical, corrected): `any` is excluded from the platforms given to BOTH
    cpython_tags and compatible_tags, and the result equals sys_tags() exactly; the verifier generator and the
    script's shared embedded derive_tags (X0 and E2) are checked against the real tags module of the test pip."""
    if sys.implementation.name != "cpython":
        return
    try:
        tags = importlib.import_module("pip._vendor.packaging.tags")
    except ImportError:
        print("SKIP tag generator regression: no pip in the test interpreter")
        return
    verifier = verifier_module()
    fields = verifier.derive_target_fields(tags.sys_tags(), "cp%d%d" % sys.version_info[:2])
    sequence, platforms, abi = fields["tag_sequence"], fields["platform_sequence"], fields["abi_tag"]
    python_version = "%d.%d.%d" % sys.version_info[:3]
    assert_true("any" in platforms, "platform_sequence still contains the literal platform any")
    corrected = verifier.generate_tag_sequence(tags, python_version, abi, platforms)
    assert_true(len(corrected) == len(sequence) and corrected == sequence,
                f"the corrected generator equals sys_tags() exactly ({len(corrected)} vs {len(sequence)})")
    major, minor = sys.version_info[:2]
    interpreter = "cp%d%d" % (major, minor)

    def compose(cpython_platforms, compatible_platforms):
        generated = list(tags.cpython_tags(python_version=(major, minor), abis=[abi], platforms=list(cpython_platforms)))
        generated += list(tags.compatible_tags(python_version=(major, minor), interpreter=interpreter,
                                               platforms=list(compatible_platforms)))
        return verifier.dedupe_tags(str(tag) for tag in generated)

    without_any = [item for item in platforms if item != "any"]
    old_full = compose(platforms, platforms)
    assert_true(old_full != sequence and len(old_full) > len(sequence)
                and all(tag.endswith("-any") and tag.startswith("cp") for tag in old_full if tag not in set(sequence)),
                "the old full-S generator does not match: it adds only cpython-specific *-any tags")
    one_call = compose(without_any, platforms)
    assert_true(one_call != sequence and set(one_call) == set(sequence),
                "excluding any from cpython_tags only gives the same set in a different order")
    assert_true(compose(without_any, without_any) == sequence, "excluding any from both calls reproduces sys_tags()")
    assert_true([item for item in platforms if item != "any"] == without_any
                and all(platforms.index(a) < platforms.index(b) for a, b in zip(without_any, without_any[1:])),
                "the relative order of the remaining platforms is preserved")
    if sys.version_info[:3] == (3, 14, 2) and len(platforms) == 40:
        assert_true(len(sequence) == 1226 and len(old_full) == 1240, "the pinned counts: 1226 actual, 1240 old generator")
    # the script's shared embedded derive_tags (X0 and E2 use the one function of the PROBE block)
    script_text = (ROOT / "scripts" / "provision_document_rendering_env.sh").read_text(encoding="utf-8")
    probe = ast.parse(verifier.extract_embedded(script_text, "PROBE"))
    wanted = [node for node in probe.body if isinstance(node, ast.FunctionDef) and node.name == "derive_tags"]
    assert_true(len(wanted) == 1, "one embedded derive_tags")

    def governed_abort_stub(*args):
        raise AssertionError(f"governed abort {args}")

    namespace = {"governed_abort": governed_abort_stub}
    exec(compile(ast.Module(body=wanted, type_ignores=[]), "probe-derive-tags", "exec"), namespace)
    embedded = namespace["derive_tags"](tags, python_version)
    assert_true(embedded["tag_sequence"] == sequence and embedded["platform_sequence"] == platforms
                and "any" in embedded["platform_sequence"] and embedded["abi_tag"] == abi,
                "the embedded derive_tags (X0 and E2) passes its self-check and records the full platform_sequence")
    assert_true(script_text.count("cpython_platforms = [item for item in platforms if item != \"any\"]") == 1
                and script_text.count("platforms=list(platforms)") == 0
                and script_text.count("platforms=list(cpython_platforms)") == 2,
                "both generator calls of the embedded code receive the platforms without any")


def test_manifest_e2_helper_chain_record() -> None:
    """The candidate manifest carries operator_base_interpreter.e2_helper_chain, consistent with the script."""
    verifier = verifier_module()
    script_text = (ROOT / "scripts" / "provision_document_rendering_env.sh").read_text(encoding="utf-8")
    manifest = json.loads((ROOT / "docs" / "rendering" / "RENDERING_ENVIRONMENT_V1.json").read_text(encoding="utf-8"))
    chain = manifest["operator_base_interpreter"].get("e2_helper_chain")
    assert_true(isinstance(chain, dict), "the manifest carries operator_base_interpreter.e2_helper_chain")
    assert_true(sorted(chain) == ["absent_candidates", "closed_list_covered", "data_files", "descendants", "helpers",
                                  "interpreter", "sequence"], f"chain members: {sorted(chain)}")
    constants = verifier.script_chain_constants(script_text)
    assert_true([row[0] for row in verifier.chain_rows(chain)] == constants["E2_CHAIN_TOOLS"], "records in the script's tool order")
    assert_true(chain["absent_candidates"] == constants["E2_CHAIN_ABSENT"], "absent candidates equal the script's list")
    assert_true(chain["sequence"] == verifier.approved_sequence_of(verifier.extract_embedded(script_text, "HOOK_HEAD_E2")),
                "the manifest sequence is the script's approved sequence")
    assert_true([item["name"] for item in chain["helpers"]] == ["lsb_release", "uname"]
                and [item["argv"] for item in chain["helpers"]] == [["lsb_release", "-a"], ["uname", "-rs"]],
                "helpers and exact argv")
    assert_true([(item["name"], item["multiplicity"]) for item in chain["descendants"]]
                == [("cut", 2), ("getopt", 1), ("tr", 3)], "descendant multiset")
    for entry in list(chain["helpers"]) + [chain["interpreter"]] + list(chain["descendants"]) + list(chain["data_files"]):
        assert_true(re.fullmatch(r"[0-9a-f]{64}", entry["sha256"]) is not None and entry["owner_packages"]
                    and len(entry["owner_packages"]) == len(entry["owner_versions"]) and all(entry["owner_versions"])
                    and entry["realpath"].startswith("/"), f"complete identity: {entry['invoked_path']}")
    assert_true(verifier.null_members(manifest["operator_base_interpreter"], "operator_base_interpreter") == [],
                "no null member remains in the base interpreter record")
    assert_true(manifest["provisioning_script_sha256"] == hashlib.sha256(
        (ROOT / "scripts" / "provision_document_rendering_env.sh").read_bytes()).hexdigest()
                and manifest["verifier_sha256"] == hashlib.sha256(
        (ROOT / "scripts" / "verify_document_rendering_environment.py").read_bytes()).hexdigest(),
                "the instrument hashes in the manifest equal the bytes")


# POST_APT_LD_SO_CACHE_V1 ---------------------------------------------------------------------------------------------

POST_APT_HARNESS_HEAD = r"""#!/bin/bash
# Sources ONLY the provisioning script's function block and drives the REAL _identity_external, _identity_decide,
# _post_apt_ld_so_cache and _libc_bin_trigger_check; only the host-touching helpers are replaced by canned values.
set -u
export LC_ALL=C
SCRIPT=$1
eval "$(sed -n '/^#BEGIN FUNCTIONS/,/^#END FUNCTIONS/p' "$SCRIPT")"
_x() { printf '%s\n' "$ID_INTERP"; }
_ph_files() { PH[$1]=$FAKE_INTERP_SHA; }
_tree_digest() { if [[ "$2" == STDLIB ]]; then REPLY=$FAKE_STDLIB; else REPLY=$FAKE_PIP; fi; TREE_FILES=(); }
_is_elf_file() { return 1; }
_native_closure() { NC_JSON=$FAKE_NC_JSON; NC_CACHE_SHA=$FAKE_CACHE; NC_COUNTS=$FAKE_COUNTS; REPLY=$FAKE_NC_DIGEST; }
_ph_string() { REPLY=$(printf '%s' "$1" | sha256sum | cut -c1-64); }
step() {   # label interp_sha stdlib pip nc_json nc_digest cache counts
    FAKE_INTERP_SHA=$2 FAKE_STDLIB=$3 FAKE_PIP=$4 FAKE_NC_JSON=$5 FAKE_NC_DIGEST=$6 FAKE_CACHE=$7 FAKE_COUNTS=$8
    _identity_external "$1"
    echo "STEP_OK $1"
}
apt_phase() {   # trigger_output complete(0|1)
    STATE=("adduser${TAB}all${TAB}3.137ubuntu1${TAB}install ok installed" "libc-bin${TAB}amd64${TAB}2.39-0ubuntu8.8${TAB}install ok installed")
    APT_INSTALL_OUTPUT=$1
    _libc_bin_trigger_check
    if [[ "$2" == 1 ]]; then APT_PHASE_COMPLETE=1; fi
}
"""


def post_apt_fixture():
    verifier = verifier_module()

    def h(name):
        return hashlib.sha256(name.encode()).hexdigest()

    interp = "/usr/local/python/3.14.2/bin/python3.14"
    stdlib = "/usr/local/python/3.14.2/lib/python3.14"
    pip = "/tmp"  # the harness only needs an existing real directory for the pip tree check (tree digests are canned)
    closure = {
        "files": [["/usr/lib/x86_64-linux-gnu/ld-linux-x86-64.so.2", h("ld")], ["/usr/lib/x86_64-linux-gnu/libc.so.6", h("libc")],
                  ["/usr/lib/x86_64-linux-gnu/libz.so.1.3", h("libz")], [interp, h("python")]],
        "links": [["/lib/x86_64-linux-gnu/libz.so.1", "libz.so.1.3"], ["/lib64/ld-linux-x86-64.so.2", "../lib/x86_64-linux-gnu/ld-linux-x86-64.so.2"]],
        "absent": ["/etc/ld.so.preload"],
        "loader_inputs": [["/etc/ld.so.cache", h("cache0")], ["/etc/ld.so.conf", h("conf")],
                          ["/etc/ld.so.conf.d/libc.conf", h("libc.conf")], ["/etc/ld.so.conf.d/x86_64-linux-gnu.conf", h("x86.conf")]],
        "loader": ["/usr/lib/x86_64-linux-gnu/ld-linux-x86-64.so.2", h("ld")],
        "system_dirs": ["/lib/x86_64-linux-gnu", "/usr/lib/x86_64-linux-gnu", "/lib", "/usr/lib"],
    }
    identity = {"executable_sha256": h("python"), "installer_pip_package_path": pip, "installer_pip_package_tree_digest": h("pip-tree"),
                "interpreter_path": interp, "interpreter_realpath": interp, "stdlib_path": stdlib, "stdlib_tree_digest": h("stdlib-tree")}
    approved = verifier.identity_digest(native_closure_digest=verifier.native_closure_digest(closure), **identity)
    return verifier, h, closure, identity, approved


def post_apt_variant(closure, mutate):
    result = json.loads(json.dumps(closure))
    mutate(result)
    return result


def post_apt_vectors():
    verifier, h, pre, identity, approved = post_apt_fixture()

    def with_cache(value, **kwargs):
        def mutate(c):
            c["loader_inputs"][0][1] = value
        return post_apt_variant(pre, mutate)

    def cache_plus(value, extra):
        def mutate(c):
            c["loader_inputs"][0][1] = value
            extra(c)
        return post_apt_variant(pre, mutate)

    new_cache, newer_cache = h("cache1"), h("cache2")
    good = {"closure": with_cache(new_cache)}
    vectors = []

    def add(name, steps, expect, apt=None, **extra):
        vectors.append(dict(name=name, steps=steps, expect=expect, apt=apt or {}, **extra))

    base_pre = ("PRE_APT", pre)
    # accepted
    add("cache_only_step4_accepted", [base_pre, ("STEP4", good["closure"])], "ACCEPT")
    add("same_cache_step6_accepted", [base_pre, ("STEP4", good["closure"]), ("STEP6", good["closure"])], "ACCEPT")
    add("no_change_step4_and_step6_normal_path", [base_pre, ("STEP4", pre), ("STEP6", pre)], "ACCEPT")
    # rejected
    add("cache_changes_again_before_step6", [base_pre, ("STEP4", good["closure"]), ("STEP6", with_cache(newer_cache))], "NATIVE_CLOSURE")
    add("cache_reverts_to_pre_value_at_step6", [base_pre, ("STEP4", good["closure"]), ("STEP6", pre)], "NATIVE_CLOSURE")
    add("cache_changes_at_step6_after_unchanged_step4", [base_pre, ("STEP4", pre), ("STEP6", with_cache(new_cache))], "NATIVE_CLOSURE")
    add("non_cache_file_hash_differs", [base_pre, ("STEP4", cache_plus(new_cache, lambda c: c["files"][1].__setitem__(1, h("libc-changed"))))], "NATIVE_CLOSURE")
    add("file_member_added", [base_pre, ("STEP4", cache_plus(new_cache, lambda c: c["files"].append(["/usr/lib/x86_64-linux-gnu/libnew.so.1", h("new")])))], "NATIVE_CLOSURE")
    add("link_target_differs", [base_pre, ("STEP4", cache_plus(new_cache, lambda c: c["links"][0].__setitem__(1, "libz.so.1.2")))], "NATIVE_CLOSURE")
    add("loader_hash_differs", [base_pre, ("STEP4", cache_plus(new_cache, lambda c: c.__setitem__("loader", [c["loader"][0], h("ld2")])))], "NATIVE_CLOSURE")
    add("loader_path_differs", [base_pre, ("STEP4", cache_plus(new_cache, lambda c: c.__setitem__("loader", ["/usr/lib64/ld.so", c["loader"][1]])))], "NATIVE_CLOSURE")
    add("system_dirs_differ", [base_pre, ("STEP4", cache_plus(new_cache, lambda c: c["system_dirs"].reverse()))], "NATIVE_CLOSURE")
    add("ld_so_conf_differs", [base_pre, ("STEP4", cache_plus(new_cache, lambda c: c["loader_inputs"][1].__setitem__(1, h("conf2"))))], "NATIVE_CLOSURE")
    add("conf_d_hash_differs", [base_pre, ("STEP4", cache_plus(new_cache, lambda c: c["loader_inputs"][2].__setitem__(1, h("libc.conf2"))))], "NATIVE_CLOSURE")
    add("conf_d_path_added", [base_pre, ("STEP4", cache_plus(new_cache, lambda c: c["loader_inputs"].append(["/etc/ld.so.conf.d/zz.conf", h("zz")])))], "NATIVE_CLOSURE")
    add("conf_d_path_removed", [base_pre, ("STEP4", cache_plus(new_cache, lambda c: c["loader_inputs"].pop()))], "NATIVE_CLOSURE")
    add("absent_set_differs", [base_pre, ("STEP4", cache_plus(new_cache, lambda c: c["absent"].append("/usr/lib/x86_64-linux-gnu/libz.so.1.3.x")))], "NATIVE_CLOSURE")
    add("non_identical_resolved_member_set", [base_pre, ("STEP4", cache_plus(new_cache, lambda c: (c["files"].pop(2), c["files"].append(["/opt/other/libz.so.1.3", h("other")]), c["links"].pop(0))))], "NATIVE_CLOSURE")
    add("interpreter_digest_differs", [base_pre, ("STEP4", good["closure"], dict(interp_sha=h("python-other")))], "EXECUTABLE_SHA256")
    add("stdlib_tree_differs", [base_pre, ("STEP4", good["closure"], dict(stdlib=h("stdlib-other")))], "IDENTITY_DIGEST")
    add("pip_tree_differs", [base_pre, ("STEP4", good["closure"], dict(pip=h("pip-other")))], "IDENTITY_DIGEST")
    add("libc_bin_trigger_missing", [base_pre, ("STEP4", good["closure"])], "NATIVE_CLOSURE", apt=dict(trigger=False))
    add("libc_bin_trigger_for_other_version", [base_pre, ("STEP4", good["closure"])], "NATIVE_CLOSURE", apt=dict(trigger="other"))
    add("apt_phase_not_complete", [base_pre, ("STEP4", good["closure"])], "NATIVE_CLOSURE", apt=dict(complete=False))
    add("identity_critical_apt_delta", [base_pre, ("STEP4", good["closure"])], "APT_UNEXPECTED_CHANGE", apt=dict(critical_delta=True))
    # PRE_APT behavior unchanged: no exception at PRE_APT, an unapproved PRE_APT closure is an identity mismatch
    add("pre_apt_cache_difference_not_admitted", [("PRE_APT", with_cache(new_cache))], "IDENTITY_DIGEST")
    add("pre_apt_other_difference_not_admitted", [("PRE_APT", cache_plus(pre["loader_inputs"][0][1], lambda c: c["files"][1].__setitem__(1, h("x"))))], "IDENTITY_DIGEST")
    return verifier, h, pre, identity, approved, vectors


def post_apt_python_outcome(verifier, h, pre, identity, approved, vector):
    """The verifier model of one vector; the outcome names the abort reason or ACCEPT."""
    apt = vector["apt"]
    accepted_cache = None
    pre_digest = verifier.native_closure_digest(pre)
    trigger = None
    if apt.get("trigger", True) is not False:
        state = [["adduser", "all", "3.137ubuntu1", "install ok installed"], ["libc-bin", "amd64", "2.39-0ubuntu8.8", "install ok installed"]]
        version = "2.39-0ubuntu8.8" if apt.get("trigger", True) is True else "2.39-0ubuntu8.7"
        trigger = verifier.libc_bin_trigger_record(state, "x\nProcessing triggers for libc-bin (%s) ...\ny" % version)
    delta = [{"package": "libc6" if apt.get("critical_delta") else "libreoffice-core-nogui", "change": "UPGRADED" if apt.get("critical_delta") else "ADDED"}]
    for step in vector["steps"]:
        label, closure = step[0], step[1]
        options = step[2] if len(step) > 2 else {}
        if options.get("interp_sha", identity["executable_sha256"]) != identity["executable_sha256"]:
            return "EXECUTABLE_SHA256"
        live = dict(identity, stdlib_tree_digest=options.get("stdlib", identity["stdlib_tree_digest"]),
                    installer_pip_package_tree_digest=options.get("pip", identity["installer_pip_package_tree_digest"]))
        live_closure_digest = verifier.native_closure_digest(closure)
        live_identity = verifier.identity_digest(native_closure_digest=live_closure_digest, **live)
        if label == "STEP6" and accepted_cache is not None and dict(closure["loader_inputs"])["/etc/ld.so.cache"] != accepted_cache:
            return "NATIVE_CLOSURE"
        if live_identity == approved:
            if label == "STEP4":
                accepted_cache = dict(closure["loader_inputs"])["/etc/ld.so.cache"]
            continue
        if live_closure_digest == pre_digest or label == "PRE_APT":
            return "IDENTITY_DIGEST"
        try:
            verifier.post_apt_ld_so_cache_admission(
                label, pre, closure, identity=live, approved_identity_digest=approved, apt_delta=delta,
                identity_critical={"libc6", "libc-bin"}, apt_plan_checks_passed=apt.get("complete", True),
                libc_bin_trigger=trigger, accepted_cache_sha256=accepted_cache)
        except verifier.Rejected as exc:
            return exc.args[1] if exc.args[1] in ("APT_UNEXPECTED_CHANGE", "IDENTITY_DIGEST") else exc.args[1]
        if label == "STEP4":
            accepted_cache = dict(closure["loader_inputs"])["/etc/ld.so.cache"]
    return "ACCEPT"


def post_apt_bash_script(verifier, h, pre, identity, approved, vectors):
    def q(text):
        assert "'" not in text
        return "'" + text + "'"

    def counts(closure):
        return "files=%d links=%d loader_inputs=%d absent=%d" % (len(closure["files"]), len(closure["links"]),
                                                                  len(closure["loader_inputs"]), len(closure["absent"]))

    lines = [POST_APT_HARNESS_HEAD]
    lines.append("COMMON_INIT() {")
    for name, value in (("ID_INTERP", identity["interpreter_path"]), ("ID_STDLIB", identity["stdlib_path"]), ("ID_PIP", identity["installer_pip_package_path"]),
                        ("APPROVED_INTERPRETER_SHA256", identity["executable_sha256"]), ("APPROVED_IDENTITY_DIGEST", approved),
                        ("APPROVED_PLAN_DIGEST", h("plan")), ("APT_TRANSACTION_SHA256", h("argv"))):
        lines.append("    %s=%s" % (name, q(value)))
    lines.append("}")
    for vector in vectors:
        if vector["name"] == "identity_critical_apt_delta":
            continue
        apt = vector["apt"]
        trigger = apt.get("trigger", True)
        output = "x\\nProcessing triggers for libc-bin (%s) ...\\ny" % ("2.39-0ubuntu8.8" if trigger is True else "2.39-0ubuntu8.7") if trigger is not False else "x\\ny"
        body = ["MAIN_PID=$BASHPID", "COMMON_INIT", "apt_phase $'%s' %d" % (output, 0 if apt.get("complete") is False else 1)]
        for step in vector["steps"]:
            label, closure = step[0], step[1]
            options = step[2] if len(step) > 2 else {}
            nc = verifier.canonical_json_bytes({"spec": "NATIVE_CLOSURE_V1", "closure": closure}).decode("utf-8")
            assert nc == json.dumps({"closure": closure, "spec": "NATIVE_CLOSURE_V1"}, sort_keys=True, separators=(",", ":"))
            body.append("step %s %s %s %s %s %s %s %s" % (
                label, q(options.get("interp_sha", identity["executable_sha256"])),
                q(options.get("stdlib", identity["stdlib_tree_digest"])), q(options.get("pip", identity["installer_pip_package_tree_digest"])),
                q(nc), q(verifier.native_closure_digest(closure)), q(dict(closure["loader_inputs"])["/etc/ld.so.cache"]),
                q(counts(closure))))
        lines.append("out=$( ( %s ) 2>&1 ); rc=$?" % "; ".join(body))
        lines.append('echo "VECTOR %s | rc=$rc | $(printf %%s "$out" | tr "\\n" "~")"' % vector["name"])
    return "\n".join(lines) + "\n"


def test_post_apt_ld_so_cache_v1_vectors() -> None:
    """POST_APT_LD_SO_CACHE_V1: the verifier model and the REAL provisioning-script functions (driven in bash with
    canned host values) accept exactly the cache-only change under every condition and fail closed on every other
    difference; PRE_APT behavior is unchanged."""
    verifier, h, pre, identity, approved, vectors = post_apt_vectors()
    # ---- verifier model, vector by vector
    for vector in vectors:
        outcome = post_apt_python_outcome(verifier, h, pre, identity, approved, vector)
        want = "ACCEPT" if vector["expect"] == "ACCEPT" else vector["expect"]
        assert_true(outcome == want, f"verifier model {vector['name']}: {outcome} != {want}")
    # ---- the verifier record of the admitted case
    state = [["libc-bin", "amd64", "2.39-0ubuntu8.8", "install ok installed"]]
    trigger = verifier.libc_bin_trigger_record(state, "Processing triggers for libc-bin (2.39-0ubuntu8.8) ...")
    assert_true(trigger == "Processing triggers for libc-bin (2.39-0ubuntu8.8) ...", "libc-bin trigger record")
    for bad_state, bad_output in ((state, "Processing triggers for libc-bin (2.39-0ubuntu8.7) ..."), (state, ""),
                                  ([], "Processing triggers for libc-bin (2.39-0ubuntu8.8) ..."),
                                  (state * 2, "Processing triggers for libc-bin (2.39-0ubuntu8.8) ..."),
                                  ([["libc-bin", "amd64", "2.39-0ubuntu8.8", "install ok unpacked"]],
                                   "Processing triggers for libc-bin (2.39-0ubuntu8.8) ..."),
                                  (state, "Processing triggers for libc-bin (2.39-0ubuntu8.8) ...x")):
        assert_true(verifier.libc_bin_trigger_record(bad_state, bad_output) is None, "no libc-bin trigger record: " + bad_output)
    new_closure = vectors[0]["steps"][1][1]
    delta = [{"package": "libreoffice-core-nogui", "change": "ADDED"}]
    kwargs = dict(identity=identity, approved_identity_digest=approved, apt_delta=delta, identity_critical={"libc6"},
                  apt_plan_checks_passed=True, libc_bin_trigger=trigger)
    record = verifier.post_apt_ld_so_cache_admission("STEP4", pre, new_closure, **kwargs)
    assert_true(record["spec"] == "POST_APT_LD_SO_CACHE_V1" and record["other_members_differing"] == 0
                and record["pre_apt_native_closure_digest"] == verifier.native_closure_digest(pre)
                and record["post_apt_native_closure_digest"] == verifier.native_closure_digest(new_closure)
                and record["pre_apt_native_closure_digest"] != record["post_apt_native_closure_digest"]
                and record["approved_identity_digest_compared_with_pre_apt_native_closure_digest"] == approved
                and record["post_apt_live_identity_digest"] != approved
                and record["old_ld_so_cache_sha256"] == dict(pre["loader_inputs"])["/etc/ld.so.cache"]
                and record["new_ld_so_cache_sha256"] == dict(new_closure["loader_inputs"])["/etc/ld.so.cache"]
                and record["pre_apt_members"] == record["post_apt_members"] == {"files": 4, "links": 2, "loader_inputs": 4, "absent": 1}
                and record["libc_bin_trigger"] == trigger,
                "the admitted-case record: PRE digest compared, live POST digests preserved as evidence")
    for label in ("PRE_APT", "STEP5", ""):
        try:
            verifier.post_apt_ld_so_cache_admission(label, pre, new_closure, **kwargs)
        except verifier.Rejected:
            pass
        else:
            assert_true(False, f"label {label!r} is never admitted")
    try:
        verifier.post_apt_ld_so_cache_admission("STEP4", pre, pre, **kwargs)
    except verifier.Rejected as exc:
        assert_true(exc.args[1] == "NATIVE_CLOSURE" and "NO_CACHE_DIFFERENCE" in exc.args[2], "an unchanged cache is not an exception case")
    else:
        assert_true(False, "identical closures are not an admitted exception")
    # ---- the real script functions in bash
    bash = shutil.which("bash")
    if bash is None:
        return
    with tempfile.TemporaryDirectory(prefix="career-os-postapt-harness-") as scratch:
        harness = Path(scratch) / "harness.sh"
        harness.write_text(post_apt_bash_script(verifier, h, pre, identity, approved, vectors), encoding="utf-8", newline="\n")
        completed = __import__("subprocess").run([bash, str(harness), "scripts/provision_document_rendering_env.sh"],
                                                 cwd=str(ROOT), capture_output=True, timeout=900)
    results = {}
    for line in completed.stdout.decode("utf-8", "replace").split("\n"):
        line = line.rstrip("\r")
        if line.startswith("VECTOR "):
            name, rc, body = (part.strip() for part in line[7:].split("|", 2))
            results[name] = (rc, body.split("~"))
    # an identity_critical delta aborts inside the apt phase (_apt_delta_and_checks) before any recheck exists: it is
    # covered by the verifier model and by the apt_phase_not_complete gating vector
    assert_true(sorted(results) == sorted(v["name"] for v in vectors if v["name"] != "identity_critical_apt_delta"),
                f"every drivable vector ran in bash: {sorted(results)}")
    reasons = {"NATIVE_CLOSURE": "reason=NATIVE_CLOSURE", "EXECUTABLE_SHA256": "reason=EXECUTABLE_SHA256", "IDENTITY_DIGEST": "reason=IDENTITY_DIGEST",
               "APT_UNEXPECTED_CHANGE": None}
    for vector in vectors:
        if vector["name"] not in results:
            continue
        rc, body = results[vector["name"]]
        text = " ".join(body)
        if vector["expect"] == "ACCEPT":
            assert_true(rc == "rc=0" and text.count("STEP_OK") == len(vector["steps"]), f"bash accepts {vector['name']}: {rc} {text[-300:]}")
        else:
            assert_true(rc == "rc=70" and reasons[vector["expect"]] in text and "STEP_OK " + vector["steps"][-1][0] not in text,
                        f"bash fails closed on {vector['name']}: {rc} {text[-400:]}")
    # ---- STEP4 and STEP6 evidence of the accepted case, taken from the real function output
    rc, body = results["same_cache_step6_accepted"]
    text = "\n".join(body)
    closure4 = vectors[0]["steps"][1][1]
    pre_digest, post_digest = verifier.native_closure_digest(pre), verifier.native_closure_digest(closure4)
    live_identity = verifier.identity_digest(native_closure_digest=post_digest, **identity)
    assert_true(f"EVIDENCE identity_PRE_APT=stdlib_tree_digest={identity['stdlib_tree_digest']}" in text
                and f"native_closure_digest={pre_digest} identity_digest={approved}" in text,
                "PRE_APT binds the complete closure and the approved identity unchanged")
    for label in ("STEP4", "STEP6"):
        assert_true(f"EVIDENCE identity_{label}=" in text and f"native_closure_digest={post_digest} identity_digest={live_identity}" in text,
                    f"the live POST_APT closure and identity digests are preserved as evidence at {label}")
        assert_true(f"post_apt_ld_so_cache_record=label={label} spec=POST_APT_LD_SO_CACHE_V1" in text, f"{label} record emitted")
    assert_true(text.count("post_apt_ld_so_cache_record=old_ld_so_cache_sha256=%s" % dict(pre["loader_inputs"])["/etc/ld.so.cache"]) == 2
                and text.count("post_apt_ld_so_cache_record=new_ld_so_cache_sha256=%s" % dict(closure4["loader_inputs"])["/etc/ld.so.cache"]) == 2
                and text.count(f"post_apt_ld_so_cache_record=pre_apt_native_closure_digest={pre_digest}") == 2
                and text.count(f"post_apt_ld_so_cache_record=post_apt_native_closure_digest={post_digest}") == 2
                and text.count(f"approved_identity_digest_compared_with_pre_apt_native_closure_digest={approved}") == 2
                and text.count("post_apt_ld_so_cache_record=other_members_differing=0") == 2
                and text.count("post_apt_ld_so_cache_record=pre_apt_members=files=4 links=2 loader_inputs=4 absent=1") == 2
                and text.count("post_apt_ld_so_cache_record=libc_bin_trigger=Processing triggers for libc-bin (2.39-0ubuntu8.8) ...") == 2,
                "the POST_APT_LD_SO_CACHE_RECORD carries digests, old/new cache hashes, member counts and the libc-bin trigger")
    # ---- STEP4 normal (no cache change) records no exception and PRE_APT stays unchanged
    rc, body = results["no_change_step4_and_step6_normal_path"]
    assert_true(rc == "rc=0" and "post_apt_ld_so_cache_record" not in " ".join(body), "no cache change, no exception record")
    # ---- parsed back by the verifier from the real script evidence
    by_key = verifier.parse_provisioning_evidence(text)
    records = verifier.parse_post_apt_ld_so_cache_records(by_key, pre_digest, h("plan"))
    assert_true([item["label"] for item in records] == ["STEP4", "STEP6"], "the verifier parses the script records")
    for tamper, mutate in (("pre digest", lambda t: t.replace(f"pre_apt_native_closure_digest={pre_digest}", "pre_apt_native_closure_digest=" + "0" * 64)),
                           ("equal cache", lambda t: t.replace("new_ld_so_cache_sha256=" + dict(closure4["loader_inputs"])["/etc/ld.so.cache"],
                                                              "new_ld_so_cache_sha256=" + dict(pre["loader_inputs"])["/etc/ld.so.cache"])),
                           ("members differ", lambda t: t.replace("other_members_differing=0", "other_members_differing=1")),
                           ("no trigger", lambda t: t.replace("libc_bin_trigger=Processing", "libc_bin_trigger=Skipped"))):
        try:
            verifier.parse_post_apt_ld_so_cache_records(verifier.parse_provisioning_evidence(mutate(text)), pre_digest, h("plan"))
        except verifier.Rejected:
            pass
        else:
            assert_true(False, "tampered record is refused: " + tamper)
    try:
        verifier.parse_post_apt_ld_so_cache_records(by_key, pre_digest, h("other-plan"))
    except verifier.Rejected:
        pass
    else:
        assert_true(False, "a record for another plan digest is refused")
    assert_true(verifier.parse_post_apt_ld_so_cache_records({}, pre_digest, h("plan")) == [], "no record, no admitted case")


def test_post_apt_ld_so_cache_v1_static_rules() -> None:
    """The script and verifier carry exactly one exception, no origin/package/generated-file/loader-input exception,
    and the exception is unreachable before the apt phase completed."""
    script = (ROOT / "scripts" / "provision_document_rendering_env.sh").read_text(encoding="utf-8")
    verifier_text = (ROOT / "scripts" / "verify_document_rendering_environment.py").read_text(encoding="utf-8")
    decide = script[script.index("_identity_decide() {"):]
    decide = decide[:decide.index("\n}\n") + 3]
    admit = script[script.index("_post_apt_ld_so_cache() {"):]
    admit = admit[:admit.index("\n}\n") + 3]
    step3 = script[script.index("_step3_apt() {"):]
    step3 = step3[:step3.index("\n}\n") + 3]
    assert_true(script.count("_post_apt_ld_so_cache ") == 1 and decide.count("_post_apt_ld_so_cache ") == 1,
                "the admission function is called from exactly one place")
    assert_true(step3.index("_apt_delta_and_checks") < step3.index("_libc_bin_trigger_check") < step3.index("APT_PHASE_COMPLETE=1")
                and "APT_INSTALL_OUTPUT=$out" in step3 and step3.count("APT_PHASE_COMPLETE=1") == 1,
                "the exception prerequisites are set only after the apt delta and plan checks completed")
    assert_true('[[ -n "${APT_PHASE_COMPLETE-}" && -n "${APT_LIBC_BIN_TRIGGER-}" ]] || return 1' in admit
                and 'label" == STEP4 || "$label" == STEP6' in admit
                and '[[ "$expected" == "$NC_JSON" ]] || return 1' in admit
                and 'NC_CACHE_SHA" == "$ACCEPTED_CACHE_SHA' in admit,
                "the admission requires the completed apt phase, the libc-bin trigger, STEP4/STEP6 only, exact equality and the STEP4 value")
    assert_true("NC_CACHE_SHA=${PH[/etc/ld.so.cache]-}" in script and "PRE_NC_JSON=$NC_JSON" in decide
                and decide.index("PRE_NC_JSON=$NC_JSON") > decide.index('"$PROVEN_IDENTITY" != "$APPROVED_IDENTITY_DIGEST"'),
                "PRE_APT retains the member-level closure and the live cache hash is taken from the loader-input hashes")
    for forbidden in ("approved origin", "origin approved", "package origin", "generated file", "generated-file"):
        assert_true(forbidden.lower() not in (decide + admit).lower(), f"no {forbidden} exception in the script")
    assert_true("ld.so.conf" not in admit and "ld.so.preload" not in admit,
                "no loader input other than the cache is named by the exception (they are covered by closure equality)")
    function = next(node for node in ast.parse(verifier_text).body
                    if isinstance(node, ast.FunctionDef) and node.name == "post_apt_ld_so_cache_admission")
    code = "\n".join(ast.unparse(node) for node in function.body[1:])
    for forbidden in ("origin", "generated", "package_owner"):
        assert_true(forbidden not in code.lower(), f"no {forbidden} exception in the verifier model code")
    manifest = json.loads((ROOT / "docs" / "rendering" / "RENDERING_ENVIRONMENT_V1.json").read_text(encoding="utf-8"))
    assert_true("ld_so_cache" not in json.dumps(manifest) and "post_apt" not in json.dumps(manifest),
                "no manifest key was added for the exception")


# OPERATOR BINDING, PROOFS AND FIRST-RENDER DRIVER (dependency-free vectors) -----------------------------------------


def synthetic_font(family: str, subfamily: str, postscript: str, variable: bool = False) -> bytes:
    """A minimal sfnt with a name table (platform 3, language 0x409) and optionally an fvar table."""
    records = [(1, family), (2, subfamily), (6, postscript)]
    strings = b""
    name_records = b""
    for name_id, text in records:
        encoded = text.encode("utf-16-be")
        name_records += struct.pack(">HHHHHH", 3, 1, 0x409, name_id, len(encoded), len(strings))
        strings += encoded
    name_table = struct.pack(">HHH", 0, len(records), 6 + 12 * len(records)) + name_records + strings
    tables = [(b"name", name_table)] + ([(b"fvar", b"\x00" * 16)] if variable else [])
    header = struct.pack(">IHHHH", 0x00010000, len(tables), 0, 0, 0)
    offset = 12 + 16 * len(tables)
    directory, body = b"", b""
    for tag, data in tables:
        directory += tag + struct.pack(">III", 0, offset + len(body), len(data))
        body += data
    return header + directory + body


GOVERNED_FONT_FILES = {
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf": ("Liberation Sans", "Regular", "LiberationSans"),
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf": ("Liberation Sans", "Bold", "LiberationSans-Bold"),
    "/usr/share/fonts/truetype/liberation/LiberationSans-Italic.ttf": ("Liberation Sans", "Italic", "LiberationSans-Italic"),
    "/usr/share/fonts/truetype/liberation/LiberationSans-BoldItalic.ttf": ("Liberation Sans", "Bold Italic",
                                                                          "LiberationSans-BoldItalic"),
}


def governed_font_bytes() -> dict:
    data = {path: synthetic_font(*facts) for path, facts in GOVERNED_FONT_FILES.items()}
    data["/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf"] = synthetic_font(
        "Liberation Serif", "Regular", "LiberationSerif")
    return data


class FakeOperatorHost:
    """A dictionary filesystem with the OperatorHost methods the pure derivations use."""

    def __init__(self, files=(), dirs=(), links=None):
        self.files = dict.fromkeys(files, b"") if not isinstance(files, dict) else dict(files)
        self.dirs = set(dirs)
        self.links = dict(links or {})

    def realpath(self, path):
        pending = list(reversed([part for part in path.split("/") if part]))
        resolved, hops = "", 0
        while pending:
            part = pending.pop()
            candidate = resolved + "/" + part
            if candidate in self.links:
                hops += 1
                assert hops < 40
                target = self.links[candidate]
                if target.startswith("/"):
                    resolved = ""
                pending.extend(reversed([item for item in target.split("/") if item]))
            elif part == "..":
                resolved = resolved.rsplit("/", 1)[0]
            elif part != ".":
                resolved = candidate
        return resolved or "/"

    def read_bytes(self, path):
        return self.files[self.realpath(path)]

    def lexists(self, path):
        return path in self.files or path in self.dirs or path in self.links

    def isfile(self, path):
        return self.realpath(path) in self.files

    def isdir(self, path):
        return self.realpath(path) in self.dirs

    def islink(self, path):
        return path in self.links

    def readlink(self, path):
        return self.links[path]

    def listdir(self, path):
        base = path.rstrip("/") + "/"
        names = {item[len(base):].split("/")[0] for item in list(self.files) + list(self.dirs) + list(self.links)
                 if item.startswith(base) and item != path}
        return sorted(names)


def live_like_host() -> FakeOperatorHost:
    files = {path: b"x" for path in adapter.SANDBOX_FILE_MOUNTS_V1}
    files.update({"/usr/lib/libreoffice/program/soffice": b"#!/bin/sh", "/usr/bin/bwrap": b"x",
                  "/usr/local/python/3.14.2/bin/python3.14": b"x"})
    files.update(governed_font_bytes())
    dirs = set(adapter.SANDBOX_TREE_MOUNTS_V1) | {"/usr/local/python/3.14.2/lib/python3.14", "/usr/lib", "/usr/bin",
                                                   "/opt/career-os-render/python/bin"}
    links = {"/bin": "usr/bin", "/lib": "usr/lib", "/lib64": "usr/lib64", "/usr/bin/soffice": "../lib/libreoffice/program/soffice",
             "/opt/career-os-render/python/bin/python": "python3.14",
             "/opt/career-os-render/python/bin/python3.14": "/usr/local/python/3.14.2/bin/python3.14"}
    return FakeOperatorHost(files, dirs, links)


def operator_manifest_skeleton() -> dict:
    return {"sandbox_forbidden_canary_paths": ["/home/user", "/root", "/workspaces"],
            "operator_python_prefix": "/opt/career-os-render/python",
            "operator_base_interpreter": {"path": "/usr/local/python/3.14.2/bin/python3.14",
                                          "stdlib_path": "/usr/local/python/3.14.2/lib/python3.14",
                                          "python_version": "3.14.2"}}


def expect_operator_failure(function, *args, **kwargs):
    try:
        function(*args, **kwargs)
    except adapter.OperatorFailure as failure:
        return (failure.status, failure.reason, failure.detail)
    return None


def test_operator_font_tables_and_probe_vectors() -> None:
    fonts = adapter.provisioned_font_records(sorted(governed_font_bytes()), lambda path: governed_font_bytes()[path])
    assert_true([record["face"] for record in fonts] == ["BOLD", "BOLD_ITALIC", "ITALIC", "REGULAR"]
                and all(record["family"] == "Liberation Sans" for record in fonts)
                and len({record["sha256"] for record in fonts}) == 4,
                "only the governed family's four faces are provisioned fonts (Liberation Serif is skipped)")
    bad = dict(governed_font_bytes())
    path = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
    bad[path] = synthetic_font("Liberation Sans", "Bold", "LiberationSans-Bold", variable=True)
    assert_true(expect_operator_failure(adapter.provisioned_font_records, sorted(bad), bad.__getitem__)[0]
                == "RENDER_FONT_VARIABLE_DENIED", "a variable font is denied")
    missing = dict(governed_font_bytes())
    del missing[path]
    assert_true(expect_operator_failure(adapter.provisioned_font_records, sorted(missing), missing.__getitem__)
                == ("RENDER_FONT_MANIFEST_INCOMPLETE", "NAME_TABLE_UNMAPPED", "FACE_SET"), "a missing face fails")
    odd = dict(governed_font_bytes())
    odd[path] = synthetic_font("Liberation Sans", "Black", "LiberationSans-Black")
    assert_true(expect_operator_failure(adapter.provisioned_font_records, sorted(odd), odd.__getitem__)[1] == "NAME_TABLE_UNMAPPED",
                "an unknown subfamily fails")
    duplicate = dict(governed_font_bytes())
    duplicate[path] = synthetic_font("Liberation Sans", "Bold", "LiberationSans")
    assert_true(expect_operator_failure(adapter.provisioned_font_records, sorted(duplicate), duplicate.__getitem__)[2] == "POSTSCRIPT_NAMES",
                "a duplicate PostScript name fails")
    assert_true(expect_operator_failure(adapter.parse_font_file, b"not a font")[1] == "NAME_TABLE_UNMAPPED", "a non-sfnt file fails")

    def observation(names=None, span_names=None, type0=False):
        base = [("LiberationSans", "AAAAAA+"), ("LiberationSans-Bold", "BAAAAA+"), ("LiberationSans-Italic", "CAAAAA+"),
                ("LiberationSans-BoldItalic", "DAAAAA+")]
        entries = [{"subtype": "Type0" if type0 else "TrueType", "inventory": "/" + prefix + name,
                    "descendant": ("/" + prefix + name) if type0 else None, "descriptor": "/" + prefix + name}
                   for name, prefix in base]
        return {"fonts": names if names is not None else entries,
                "span_names": span_names if span_names is not None else [prefix + name for name, prefix in base]}

    tables = adapter.build_font_tables(fonts, observation())
    assert_true(tables["canonical_families"] == ["Arial", "Liberation Sans"]
                and tables["docx_family_to_canonical"] == {"arial": "Arial", "liberation sans": "Liberation Sans"}
                and tables["approved_substitutions"] == {"Liberation Sans": ["Arial"]} and tables["marker_glyph_map"] == []
                and tables["pdf_basefont_to_canonical"]["LiberationSans-BoldItalic"]
                == {"canonical_family_id": "Liberation Sans", "face": "BOLD_ITALIC"}
                and tables["pdfminer_type0_name_form"] == "NO_TYPE0_FONT_OBSERVED" and len(tables["pdf_basefont_to_canonical"]) == 4,
                "the tables come only from the doctrine pair and the real name forms")
    assert_true(adapter.build_font_tables(fonts, observation(type0=True))["pdfminer_type0_name_form"]
                == "PARENT_BASEFONT_EQUALS_DESCENDANT_BASEFONT", "the Type0 name form is pinned from the observation")
    assert_true(expect_operator_failure(adapter.build_font_tables, fonts, observation(span_names=["AAAAAA+LiberationSans,Bold"]))
                == ("RENDER_FONT_MANIFEST_INCOMPLETE", "ALIAS_FORM_MISSING", None), "an unmapped pdfminer form is never guessed")
    assert_true(expect_operator_failure(adapter.build_font_tables, fonts, observation(
        span_names=["AAAAAA+LiberationSans", "BAAAAA+LiberationSans-Bold"]))[2] == "FACE_NOT_OBSERVED",
                "a face not observed through pdfminer.six fails")
    mixed = observation()
    mixed["fonts"][1]["descriptor"] = "/BAAAAA+LiberationSans-Italic"
    assert_true(expect_operator_failure(adapter.build_font_tables, fonts, mixed)[0] == "RENDER_FONT_INVENTORY_MISMATCH",
                "descriptor and inventory names of one font must map to one identity")
    assert_true(expect_operator_failure(adapter.strip_pdf_name_form, "/AAAAAA+Liberation Sans")[2] == "NAME_FORM_ASCII",
                "a name with a space is unusable evidence")
    assert_true(adapter.strip_pdf_name_form("/ABCDEF+LiberationSans") == "LiberationSans"
                and adapter.strip_pdf_name_form("LiberationSans") == "LiberationSans", "FONT_NAME_FORM_V1 strip")

    probe = {"ok": True, "connects": {"AF_INET": "ENETUNREACH", "AF_INET6": "EADDRNOTAVAIL"}, "control": "CONNECTED"}
    assert_true(adapter.errno_sets_from_probe(probe) == {"AF_INET": ["ENETUNREACH"], "AF_INET6": ["EADDRNOTAVAIL"]},
                "the errno sets are exactly the observed values (narrowing only)")
    for broken in (dict(probe, connects={"AF_INET": "ECONNREFUSED", "AF_INET6": "ENETUNREACH"}),
                   dict(probe, connects={"AF_INET": "ENETUNREACH", "AF_INET6": "ETIMEDOUT"}),
                   dict(probe, connects={"AF_INET": "CONNECTED", "AF_INET6": "ENETUNREACH"}),
                   dict(probe, control="ECONNREFUSED"), dict(probe, ok=False, failures=[{"check": "CANARY_VISIBLE"}]),
                   {"ok": True, "connects": {"AF_INET": "ENETUNREACH"}, "control": "CONNECTED"}, {"ok": True}):
        assert_true(expect_operator_failure(adapter.errno_sets_from_probe, broken) is not None
                    and expect_operator_failure(adapter.errno_sets_from_probe, broken)[0] == "RENDER_ISOLATION_UNAVAILABLE",
                    f"a wrong network probe result fails closed: {broken}")


def evidence_fixture() -> str:
    lines = ["EVIDENCE apt_preinstall_snapshot=adduser\tall\t3.137ubuntu1\tinstall ok installed\t0",
             "EVIDENCE apt_preinstall_snapshot=apt\tamd64\t2.8.3\tinstall ok installed\t1",
             "EVIDENCE apt_get_version=apt 2.8.3 (amd64)", "EVIDENCE apt_install_argv=/usr/bin/apt-get install",
             "EVIDENCE os_release=ubuntu 24.04", "EVIDENCE no_debsig_admission=COMPLETE", "EVIDENCE apt_path=Dir::State /var/lib/apt",
             "EVIDENCE apt_effective_source=deb\thttp://x\tnoble\tmain", "EVIDENCE apt_config=Acquire::Foo=1",
             "EVIDENCE dpkg_config_record=O\tlog\t=/var/log/dpkg.log", "EVIDENCE apt_update_line=Hit:1 http://x noble InRelease",
             "EVIDENCE apt_inrelease=http://x noble /var/lib/apt/lists/x " + "a" * 64, "EVIDENCE apt_origin=apt amd64 2.8.3 http://x noble main;",
             "EVIDENCE result=PROVISIONED prefix=/opt/x plan_digest=" + "b" * 64 + " (the verifier decides)"]
    return "\n".join(lines) + "\n"


def test_operator_apt_records_and_post_manifest_assembly() -> None:
    by_key = adapter.parse_evidence_lines(evidence_fixture())
    snapshot, delta, source = adapter.apt_records_from_evidence(by_key, "c" * 64)
    assert_true(snapshot == [["adduser", "all", "3.137ubuntu1", "install ok installed", 0],
                             ["apt", "amd64", "2.8.3", "install ok installed", 1]] and delta == []
                and source["spec"] == "APT_SOURCE_RECORD_V1" and source["provisioning_evidence_sha256"] == "c" * 64
                and source["records"]["apt_get_version"] == ["apt 2.8.3 (amd64)"], "apt records come only from the evidence")
    with_delta = adapter.parse_evidence_lines(evidence_fixture() + "EVIDENCE apt_installed_delta=zlib1g|amd64|UPGRADED|1|2\n")
    assert_true(adapter.apt_records_from_evidence(with_delta, "c" * 64)[1] == [
        {"package": "zlib1g", "architecture": "amd64", "change": "UPGRADED", "version_before": "1", "version_after": "2"}],
                "a delta entry is recorded exactly")
    for mutation in (lambda t: t.replace("EVIDENCE result=PROVISIONED", "EVIDENCE result=ABORTED"),
                     lambda t: t.replace("EVIDENCE apt_get_version=apt 2.8.3 (amd64)\n", ""),
                     lambda t: t.replace("\tinstall ok installed\t1", "\tinstall ok installed\t2"),
                     lambda t: "".join(line + "\n" for line in t.split("\n") if "apt_preinstall_snapshot" not in line),
                     lambda t: t + "EVIDENCE apt_installed_delta=bad|line\n",
                     lambda t: t + "EVIDENCE apt_preinstall_snapshot=apt\tamd64\t2.8.3\tinstall ok installed\t1\n"):
        assert_true(expect_operator_failure(adapter.apt_records_from_evidence,
                                            adapter.parse_evidence_lines(mutation(evidence_fixture())), "c" * 64) is not None,
                    "a missing or malformed apt record fails closed")

    pre = fake_manifest(approve=False)
    for key in adapter.MANIFEST_POST_PROVISION_KEYS:
        pre[key] = None
    values = {key: "v:" + key for key in adapter.MANIFEST_POST_PROVISION_KEYS if key != "manifest_self_digest"}
    values.update(canonical_families=["b", "a", "a"], sandbox_read_only_paths=["/z", "/a"], sandbox_dirs=[])
    manifest = adapter.assemble_post_manifest(pre, values)
    again = adapter.assemble_post_manifest(pre, dict(values))
    assert_true(manifest == again and adapter.manifest_text(manifest) == adapter.manifest_text(again)
                and manifest["manifest_self_digest"] == adapter.manifest_digest(manifest)
                and manifest["canonical_families"] == ["a", "b"] and manifest["sandbox_read_only_paths"] == ["/a", "/z"]
                and adapter.pre_provision_plan_digest(manifest) == adapter.pre_provision_plan_digest(pre)
                and all(manifest[key] == pre[key] for key in adapter.MANIFEST_PRE_PROVISION_KEYS)
                and all(manifest[key] is not None for key in manifest), "assembly is deterministic and leaves PRE members byte-identical")
    assert_true(adapter.manifest_text(manifest).endswith("}\n") and "\r" not in adapter.manifest_text(manifest),
                "canonical file form")
    runtime_digest = adapter.canonical_digest({"spec": "RUNTIME_MANIFEST_BINDING_V1", "manifest_digest": adapter.manifest_digest(manifest),
                                               "content_binding_digest": "d" * 64})
    assert_true(runtime_digest == adapter.canonical_digest({"spec": "RUNTIME_MANIFEST_BINDING_V1",
                                                            "manifest_digest": adapter.manifest_digest(again),
                                                            "content_binding_digest": "d" * 64}),
                "the runtime-manifest digest is deterministic")
    for label, mutate in (("missing key", lambda v: v.pop("sandbox_path")), ("null value", lambda v: v.update(sandbox_path=None)),
                          ("extra PRE key", lambda v: v.update(locale="C")), ("unknown key", lambda v: v.update(extra=1))):
        broken = dict(values)
        mutate(broken)
        result = expect_operator_failure(adapter.assemble_post_manifest, pre, broken)
        assert_true(result is not None and result[1] == "POST_BINDING_UNPOPULATED", f"{label} is never defaulted: {result}")
    populated = dict(pre, sandbox_path="/usr/bin")
    assert_true(expect_operator_failure(adapter.assemble_post_manifest, populated, values)[1] == "POST_KEYS_NOT_NULL",
                "a manifest whose POST key is already populated is not recaptured")


def test_operator_sandbox_and_root_derivation() -> None:
    host = live_like_host()
    manifest = operator_manifest_skeleton()
    fonts = adapter.provisioned_font_records(sorted(governed_font_bytes()), host.read_bytes)
    base_closure = {"files": [["/usr/local/python/3.14.2/bin/python3.14", "1" * 64], ["/usr/lib/x86_64-linux-gnu/libc.so.6", "2" * 64]],
                    "links": [["/lib64/ld-linux-x86-64.so.2", "../lib/x86_64-linux-gnu/ld-linux-x86-64.so.2"],
                              ["/lib/x86_64-linux-gnu/libz.so.1", "libz.so.1.3"]],
                    "loader_inputs": [["/etc/ld.so.cache", "3" * 64]], "absent": ["/etc/ld.so.preload"], "loader": ["/x", "4" * 64],
                    "system_dirs": ["/lib"]}
    prefix_closure = dict(base_closure, files=base_closure["files"] + [["/opt/career-os-render/python/lib/python3.14/site-packages/x.so", "5" * 64]])
    host.dirs |= {"/lib", "/lib64", "/usr/lib64", "/usr/lib/x86_64-linux-gnu"}
    sandbox = adapter.derive_sandbox(host, manifest, fonts, [base_closure, prefix_closure])
    assert_true(sandbox["sandbox_read_only_paths"] == sorted(sandbox["sandbox_read_only_paths"])
                and len(set(sandbox["sandbox_read_only_paths"])) == len(sandbox["sandbox_read_only_paths"])
                and all(font["path"] in sandbox["sandbox_read_only_paths"] for font in fonts)
                and "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf" not in sandbox["sandbox_read_only_paths"]
                and not any(path in adapter._FORBIDDEN_WHOLE_BINDS for path in sandbox["sandbox_read_only_paths"])
                and sandbox["sandbox_probe_interpreter_path"] == "/usr/local/python/3.14.2/bin/python3.14"
                and sandbox["sandbox_dirs"] == [] and sandbox["sandbox_path"] == "/usr/bin"
                and sandbox["fontconfig_file"] == "/etc/fonts/fonts.conf", "the enumeration is the policy plus the governed fonts only")
    links = {item["path"]: item["target"] for item in sandbox["sandbox_symlinks"]}
    assert_true(links["/bin"] == "usr/bin" and links["/lib64"] == "usr/lib64"
                and links["/usr/lib64/ld-linux-x86-64.so.2"] == "../lib/x86_64-linux-gnu/ld-linux-x86-64.so.2"
                and links["/usr/lib/x86_64-linux-gnu/libz.so.1"] == "libz.so.1.3"
                and links["/opt/career-os-render/python/bin/python"] == "python3.14"
                and links["/opt/career-os-render/python/bin/python3.14"] == "/usr/local/python/3.14.2/bin/python3.14"
                and not any(path.startswith("/lib/") for path in links)
                and [item["path"] for item in sandbox["sandbox_symlinks"]] == sorted(links),
                "the scaffold links sit at the real parent directories, sorted, never through a scaffold symlink")
    for label, mutate in (("missing tree", lambda h: h.dirs.discard("/usr/lib/libreoffice")),
                          ("missing file", lambda h: h.files.pop("/etc/passwd")),
                          ("mistyped tree", lambda h: (h.dirs.discard("/etc/fonts"), h.files.update({"/etc/fonts": b""}))),
                          ("missing bwrap", lambda h: h.files.pop("/usr/bin/bwrap")),
                          ("missing soffice", lambda h: h.files.pop("/usr/lib/libreoffice/program/soffice"))):
        broken = live_like_host()
        broken.dirs |= {"/lib", "/lib64", "/usr/lib64", "/usr/lib/x86_64-linux-gnu"}
        mutate(broken)
        result = expect_operator_failure(adapter.derive_sandbox, broken, manifest, fonts, [base_closure])
        assert_true(result is not None and result[0] == "RENDER_ISOLATION_UNAVAILABLE" and result[1] == "MOUNT_MISSING",
                    f"{label} fails closed: {result}")
    canary = dict(manifest, sandbox_forbidden_canary_paths=["/usr/lib"])
    assert_true(expect_operator_failure(adapter.derive_sandbox, host, canary, fonts, [base_closure])[1] == "FORBIDDEN_MOUNT",
                "a mount under a canary path fails")
    conflict = dict(base_closure, links=[["/lib/x86_64-linux-gnu/libz.so.1", "a"], ["/usr/lib/x86_64-linux-gnu/libz.so.1", "b"]])
    assert_true(expect_operator_failure(adapter.derive_sandbox_symlinks, host, "/opt/career-os-render/python", [conflict])[1]
                == "SCAFFOLD_CONFLICT", "one path with two targets fails")

    populated = dict(manifest)
    populated.update(sandbox)
    roots = adapter.build_content_roots(host, populated, sandbox, fonts, base_closure, prefix_closure, ["pdfminer-six", "pypdf"],
                                        ["/usr/local/python/3.14.2/lib/python314.zip"], "/opt/career-os-render/python/lib/python3.14/site-packages")
    by_id = {root["id"]: root for root in roots}
    paths_by_kind = {(root["kind"], root["path"]) for root in roots}
    assert_true(len(by_id) == len(roots) and [root["id"] for root in roots] == sorted(by_id, key=lambda item: item.encode("utf-8"))
                and {"a.soffice_tree", "a.soffice_executable", "c.bubblewrap_executable", "f.base_interpreter", "g.stdlib",
                     "h.prefix_pyvenv_cfg", "k.site_packages", "e.dist.pdfminer-six", "e.dist.pypdf"} <= set(by_id)
                and by_id["g.stdlib"]["kind"] == "STDLIB_TREE" and ("ABSENT", "/etc/ld.so.preload") in paths_by_kind
                and ("LINK", "/lib/x86_64-linux-gnu/libz.so.1") in paths_by_kind
                and ("FILE", "/etc/ld.so.cache") in paths_by_kind and ("ABSENT", "/usr/local/python/3.14.2/lib/python314.zip") in paths_by_kind,
                "every contract root class is produced exactly once per (kind, path)")
    for mount in sandbox["sandbox_read_only_paths"]:
        assert_true(("FILE", mount) in paths_by_kind or ("TREE", mount) in paths_by_kind or ("STDLIB_TREE", mount) in paths_by_kind,
                    f"every sandbox mount is covered by a root: {mount}")
    populated["content_binding"] = {"roots": [dict(root, expected_digest="0" * 64) for root in roots], "exclusions": []}
    inspection = adapter.derive_inspection_paths(populated)
    assert_true(inspection == tuple(sorted(inspection)) and "/usr/local/python/3.14.2/bin/python3.14" in inspection
                and "/usr/local/python/3.14.2/lib/python3.14" in inspection
                and "/opt/career-os-render/python/lib/python3.14/site-packages" in inspection
                and "/opt/career-os-render/python/pyvenv.cfg" in inspection and "/etc/ld.so.cache" in inspection
                and "/usr/lib/x86_64-linux-gnu/libc.so.6" in inspection
                and "/opt/career-os-render/python/lib/python3.14/site-packages/x.so" not in inspection
                and "/lib/x86_64-linux-gnu/libz.so.1" not in inspection and not any(path.startswith("/usr/lib/libreoffice") for path in inspection),
                "the inspection mounts are derived from the roots: interpreter, stdlib, pyvenv.cfg, site-packages, closure files")
    paths = adapter.runtime_paths_from_manifest(populated)
    assert_true(paths.bwrap_path == "/usr/bin/bwrap" and paths.soffice_path == "/usr/lib/libreoffice/program/soffice"
                and paths.inspection_read_only_paths == inspection, "runtime paths come from the manifest roots")
    no_soffice = dict(populated, content_binding={"roots": [r for r in populated["content_binding"]["roots"]
                                                           if r["id"] != "a.soffice_executable"], "exclusions": []})
    assert_true(expect_operator_failure(adapter.runtime_paths_from_manifest, no_soffice)[1] == "CONTENT_BINDING_SHAPE",
                "a missing pinned executable root fails")


def test_operator_content_root_digests_on_a_real_tree() -> None:
    with tempfile.TemporaryDirectory(prefix="career-os-roots-") as scratch:
        tree = os.path.join(scratch, "tree")
        os.makedirs(os.path.join(tree, "sub"))
        Path(tree, "a.txt").write_bytes(b"alpha")
        Path(tree, "sub", "b.txt").write_bytes(b"bravo")
        outside = os.path.join(scratch, "outside.txt")
        Path(outside).write_bytes(b"outside")
        covered_link = os.path.join(scratch, "covered_target.txt")
        Path(covered_link).write_bytes(b"covered")
        symlinks_ok = True
        try:
            os.symlink(outside, os.path.join(tree, "escape"))
            os.symlink("a.txt", os.path.join(tree, "inside"))
            os.symlink(covered_link, os.path.join(tree, "covered"))
        except (OSError, NotImplementedError):
            symlinks_ok = False
        if not symlinks_ok:
            return
        single = os.path.join(scratch, "single.bin")
        Path(single).write_bytes(b"single")
        link = os.path.join(scratch, "link")
        os.symlink("single.bin", link)
        roots = [{"id": "k.tree", "kind": "TREE", "path": tree}, {"id": "b.file", "kind": "FILE", "path": single},
                 {"id": "b.covered", "kind": "FILE", "path": covered_link}, {"id": "i.link", "kind": "LINK", "path": link},
                 {"id": "j.absent", "kind": "ABSENT", "path": os.path.join(scratch, "nothing")}]
        computed, exclusions = adapter.compute_root_digests(roots, [covered_link, single])
        by_id = {root["id"]: root for root in computed}
        assert_true(exclusions == [{"root_id": "k.tree", "relpath": "escape", "reason": "SYMLINK_TARGET_OUTSIDE_MOUNTS"}]
                    and by_id["j.absent"]["expected_digest"] == adapter.ABSENT_ROOT_DIGEST
                    and by_id["b.file"]["expected_digest"] == sha256_hex(b"single")
                    and by_id["i.link"]["expected_digest"] == adapter.canonical_digest(["L", link, "single.bin"]),
                    "a symlink leaving every mount is an exact-relpath exclusion; file, link and absent digests follow the rules")
        again, again_exclusions = adapter.compute_root_digests(roots, [covered_link, single])
        assert_true(again == computed and again_exclusions == exclusions, "root digests are deterministic")
        manifest = fake_manifest(approve=False)
        manifest["sandbox_read_only_paths"] = sorted([single, covered_link])
        manifest["content_binding"] = {"roots": computed, "exclusions": exclusions}
        digest, pairs = adapter.verify_content_binding(manifest)
        assert_true(digest == adapter.canonical_digest(pairs) and [pair[0] for pair in pairs] == sorted(pair[0] for pair in pairs),
                    "the content-binding digest is over the sorted (id, digest) pairs")
        Path(single).write_bytes(b"single!")
        assert_true(outcome_of(adapter.verify_content_binding, manifest)[:2] == ("RENDER_CONTENT_BINDING_MISMATCH", "DIGEST"),
                    "changed root bytes fail closed")
        Path(single).write_bytes(b"single")
        Path(tree, "a.txt").write_bytes(b"alphX")
        assert_true(outcome_of(adapter.verify_content_binding, manifest)[:2] == ("RENDER_CONTENT_BINDING_MISMATCH", "DIGEST"),
                    "a changed byte inside a TREE root fails closed")
        Path(tree, "a.txt").write_bytes(b"alpha")
        Path(scratch, "nothing").write_bytes(b"appeared")
        assert_true(outcome_of(adapter.verify_content_binding, manifest)[:2] == ("RENDER_CONTENT_BINDING_MISMATCH", "PRESENT"),
                    "an ABSENT root that appears fails closed")
        Path(scratch, "nothing").unlink()
        missing_root = dict(manifest, sandbox_read_only_paths=sorted([single, os.path.join(scratch, "unrooted")]))
        assert_true(outcome_of(adapter.verify_content_binding, missing_root)[:2] == ("RENDER_CONTENT_BINDING_INCOMPLETE", "MOUNT_COVERAGE"),
                    "a mount without a root fails closed")


def test_operator_prober_checks_and_verification_record() -> None:
    manifest = fake_manifest(approve=False)
    manifest.update(sandbox_read_only_paths=["/usr/bin/sh"], sandbox_probe_interpreter_path="/usr/local/python/bin/python3",
                    sandbox_expected_unreachable_errnos={"AF_INET": ["ENETUNREACH"], "AF_INET6": ["ENETUNREACH"]},
                    sandbox_forbidden_canary_paths=["/home/user"], sandbox_tmpfs_paths=["/sandbox/home", "/tmp"])
    shared = adapter.build_argv_shared(manifest, adapter.PROFILE_RENDER)
    argv = ["/usr/bin/bwrap"] + shared

    class Completed:
        def __init__(self, stdout, returncode=0, stderr=b""):
            self.stdout, self.returncode, self.stderr = stdout, returncode, stderr

    def prober_with(result, returncode=0, raises=None):
        def run(command, **kwargs):
            if raises:
                raise raises
            assert command[0] == "/usr/bin/bwrap" and "<RUN_INPUT_DIR>" not in command and kwargs["shell"] is False
            assert command[-5:-2] == ["-I", "-S", "-B"] or "--probe" in command
            return Completed(json.dumps(result).encode("utf-8"), returncode)
        return adapter.make_operator_isolation_prober(manifest, "/checkout/verify.py", run=run)

    good = {"ok": True, "failures": [], "connects": {"AF_INET": "ENETUNREACH", "AF_INET6": "ENETUNREACH"}, "control": "CONNECTED"}
    report = prober_with(good)(adapter.PROFILE_RENDER, argv, ())
    assert_true(report["ok"] is True and report["profile_digest"] == adapter.sandbox_profile_digest(manifest, adapter.PROFILE_RENDER),
                "a passing probe returns the profile digest of the shared argv (placeholders kept)")
    for label, result in (("visible canary", {"ok": False, "failures": [{"check": "CANARY_VISIBLE", "path": "/home/user"}]}),
                          ("writable read-only mount", {"ok": False, "failures": [{"check": "WRITE_DENIAL", "created": 1}]}),
                          ("wrong connect errno", {"ok": False, "failures": [{"check": "CONNECT", "observed": "ECONNREFUSED"}]}),
                          ("broken control", {"ok": False, "failures": [{"check": "CONTROL"}]})):
        report = prober_with(result)(adapter.PROFILE_RENDER, argv, ())
        assert_true(report["ok"] is False and report["reason"] == "SELF_TEST_FAILED", f"{label} fails the self-test")
    assert_true(prober_with(dict(good, ok=True), returncode=1)(adapter.PROFILE_RENDER, argv, ())["ok"] is False,
                "a non-zero probe exit is a failure even with ok true")
    assert_true(prober_with(good)(adapter.PROFILE_RENDER, ["/usr/bin/bwrap"] + shared[:-1], ())["reason"] == "PROFILE_MISMATCH",
                "an argv that differs from the adapter's builder is PROFILE_MISMATCH")
    assert_true(prober_with(good, raises=subprocess.TimeoutExpired("x", 1))(adapter.PROFILE_RENDER, argv, ())["reason"] == "PROBE_FAILED",
                "a probe timeout is a failure")

    assert_true(expect_operator_failure(adapter.check_soffice_version, "LibreOffice 24.2.7.1 420(Build:2)", "LibreOffice 24.2.7.2 420(Build:2)")[1]
                == "RENDERER_VERSION" and adapter.check_soffice_version("v", "v") is None, "the pinned version must match exactly")
    assert_true(expect_operator_failure(adapter.check_canary_unreadable, 0, "READABLE")[1] == "CANARY_READABLE"
                and expect_operator_failure(adapter.check_canary_unreadable, 1, "ABSENT:2")[1] == "CANARY_READABLE"
                and adapter.check_canary_unreadable(0, "ABSENT:2") is None, "a readable planted canary fails")

    steps = [{"step": name, "result": "PASS", "evidence": {"manifest_digest": "m" * 64, "content_binding_digest": "c" * 64,
                                                            "runtime_manifest_digest": "r" * 64}}
             for name in adapter.REQUIRED_VERIFICATION_STEPS]
    record = {"spec": adapter.OPERATOR_VERIFICATION_SPEC_ID, "result": "PASS", "steps": steps, "attachments": []}
    record["evidence_digest"] = adapter.evidence_digest(dict(record))
    assert_true(adapter.operator_evidence_is_pass(record) is True, "a complete passing record is a pass")
    assert_true(adapter.verification_matches_manifest(record, {"manifest_digest": "m" * 64, "content_binding_digest": "c" * 64,
                                                               "runtime_manifest_digest": "r" * 64}) is True
                and adapter.verification_matches_manifest(record, {"manifest_digest": "m" * 64, "content_binding_digest": "c" * 64,
                                                                   "runtime_manifest_digest": "x" * 64}) is False,
                "the record is bound to one runtime manifest")
    partial = dict(record, steps=steps[:-1])
    partial["evidence_digest"] = adapter.evidence_digest({k: v for k, v in partial.items() if k != "evidence_digest"})
    failed_step = dict(record, steps=steps[:3] + [dict(steps[3], result="FAIL")] + steps[4:])
    reordered = dict(record, steps=[steps[1], steps[0]] + steps[2:])
    tampered = dict(record, result="PASS", attachments=[{"name": "x", "sha256": "0" * 64}])
    failed_run = dict(record, result="FAIL", failed_step="soffice_version_in_sandbox")
    no_evidence = dict(record, steps=[{"step": s["step"], "result": "PASS"} for s in steps])
    for label, bad in (("partial", partial), ("failed step", failed_step), ("reordered", reordered), ("tampered", tampered),
                       ("failed run", failed_run), ("no evidence", no_evidence), ("not a dict", None), ("empty", {})):
        assert_true(adapter.operator_evidence_is_pass(bad) is False, f"{label} verifier evidence is never a pass")

    # the render driver refuses an incomplete manifest, a missing or failing verification record and a wrong DOCX
    with tempfile.TemporaryDirectory(prefix="career-os-driver-") as scratch:
        root = Path(scratch)
        (root / "requirements.in").write_bytes(REQUIREMENTS_IN)
        (root / "requirements-lock.txt").write_bytes(REQUIREMENTS_LOCK)
        docx = root / "input.docx"
        docx.write_bytes(b"placeholder")
        incomplete = manifest_bytes(fake_manifest(**{"sandbox_path": None}))
        refused = lambda *a, **k: None  # noqa: E731 - governed check stub (the test interpreter is not governed)
        assert_true(expect_operator_failure(adapter.run_first_render, root, incomplete, str(docx), sha256_hex(b"placeholder"),
                                            str(root / "out"), None, None, governed=refused)[1] == "OPERATOR_VERIFICATION_NOT_PASS",
                    "no verification record: the driver refuses")
        assert_true(expect_operator_failure(adapter.run_first_render, root, incomplete, str(docx), sha256_hex(b"placeholder"),
                                            str(root / "out"), None, failed_run, governed=refused)[1] == "OPERATOR_VERIFICATION_NOT_PASS",
                    "a failing verification record: the driver refuses")
        assert_true(expect_operator_failure(adapter.run_first_render, root, incomplete, str(docx), "0" * 64, str(root / "out"),
                                            None, record, governed=refused)[1] == "INPUT_SHA256", "a different DOCX: the driver refuses")
        try:
            adapter.run_first_render(root, incomplete, str(docx), sha256_hex(b"placeholder"), str(root / "out"), None, record, governed=refused)
        except adapter.StageFailure as failure:
            assert_true(failure.outcome.status == "RENDER_ENVIRONMENT_UNVERIFIED" and failure.outcome.reason == "POST_BINDING_UNPOPULATED",
                        "an incomplete runtime manifest stops the driver at S2.01")
        else:
            assert_true(False, "the driver must not run against an incomplete runtime manifest")
        assert_true(not (root / "out").exists(), "nothing is created before the manifest is verified")
    assert_true(expect_operator_failure(adapter.check_governed_mode)[1] == "INTERPRETER_MODE", "the test interpreter is not the governed mode")
    assert_true(adapter.operator_main([]) == 2 and adapter.operator_main(["--unknown"]) == 2, "an unknown command is a usage error")


def test_operator_fixtures_entry_constant_and_static_rules() -> None:
    tables = {"canonical_families": ["Arial", "Liberation Sans"],
              "docx_family_to_canonical": {"arial": "Arial", "liberation sans": "Liberation Sans"}}
    manifest = fake_manifest(**tables)
    manifest["pdf_basefont_to_canonical"] = {}
    for kind in ("EXECUTABILITY", "EXECUTABILITY_FULL", "FONT_PROBE"):
        first, first_map = adapter.build_fixture_docx(kind)
        second, second_map = adapter.build_fixture_docx(kind)
        assert_true(first == second and first_map == second_map, f"{kind} fixture is deterministic")
        package = adapter.docx_preflight(first)
        if first_map is not None:
            model = adapter.build_source_model(package, manifest, first_map)
            assert_true(len(model.structure_map) == len(first_map) and len(model.paragraphs) == len(first_map),
                        f"the {kind} structure map matches the source model paragraph by paragraph")
    full, full_map = adapter.build_fixture_docx("EXECUTABILITY_FULL")
    short, short_map = adapter.build_fixture_docx("EXECUTABILITY")
    assert_true(len(full_map) == len(short_map) + adapter.FULL_FIXTURE_EXTRA_BULLETS and len(full) > len(short),
                "the constructed full-page fixture adds the calibrated bullets to the under-filled one")
    entry = ENTRY_PATH.read_bytes()
    site = "/opt/career-os-render/python/lib/python3.14/site-packages"
    good = {"content_binding": {"runtime_sys_path": ["/a", "/b", site]}}
    assert_true(adapter.entry_runtime_path_matches(good, entry) is True
                and adapter.entry_runtime_path_matches({"content_binding": {"runtime_sys_path": ["/a", "/other"]}}, entry) is False
                and adapter.entry_runtime_path_matches(good, b"X = 1\n") is False,
                "the entry's single explicit sys.path addition equals the last runtime_sys_path element")
    assert_true('if __name__ == "__main__" and os.path.isdir(RUNTIME_SITE_PACKAGES)' in entry.decode("utf-8")
                and entry.decode("utf-8").index("sys.path.append(RUNTIME_SITE_PACKAGES)") < entry.decode("utf-8").index("from pdfminer"),
                "the entry adds the site-packages path only when run, before any pinned-library import")
    text = ADAPTER_PATH.read_text(encoding="utf-8")
    section = text[text.index("# OPERATOR BINDING, PROOFS AND FIRST-RENDER DRIVER"):]
    tree = ast.parse(section)
    imported = {alias.name.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names}
    assert_true(not imported & {"socket", "http", "urllib", "ctypes"}, "the operator code imports no network or ctypes module")
    assert_true(re.search(r"\bshell\s*=\s*True", section) is None and "os.system" not in section and "os.popen" not in section,
                "no shell invocation in the operator code")
    assert_true(all(isinstance(node.value, ast.Constant) and node.value.value is False
                    for node in ast.walk(tree) if isinstance(node, ast.keyword) and node.arg == "shell"), "every shell keyword is False")
    forbidden_calls = ("apt-get", "dpkg -i", "pip install", "ldconfig", "chmod", "chown", "os.remove", "shutil.rmtree(prefix")
    assert_true(not any(item in section.replace("/usr/bin/dpkg-query", "") for item in forbidden_calls),
                "the operator code mutates neither apt, the prefix nor the host")
    for command in ("--capture-post-binding", "--operator-verify", "--render"):
        assert_true(command in section, f"the operator CLI offers {command}")
    verifier_text = (ROOT / "scripts" / "verify_document_rendering_environment.py").read_text(encoding="utf-8")
    manifest_file = json.loads((ROOT / "docs" / "rendering" / "RENDERING_ENVIRONMENT_V1.json").read_text(encoding="utf-8"))
    assert_true(hashlib.sha256(verifier_text.encode("utf-8")).hexdigest() == manifest_file["verifier_sha256"]
                or hashlib.sha256((ROOT / "scripts" / "verify_document_rendering_environment.py").read_bytes()).hexdigest()
                == manifest_file["verifier_sha256"], "the operator code left the plan-bound verifier bytes unchanged")


def _open_action_pdf(open_action: bytes, extra: dict | None = None) -> bytes:
    """One page (object 3) in the page tree, an orphan page (6) and a plain
    object (4) outside it; the catalog carries the given /OpenAction value."""
    catalog = CATALOG[:-3] + (b" /OpenAction " + open_action + b" >>" if open_action else b" >>")
    objects = {
        1: catalog,
        2: b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        3: b"<< /Type /Page /Parent 2 0 R " + MEDIABOX + b" /Contents 5 0 R >>",
        4: b"<< /Foo /Bar >>",
        5: stream(b"", b""),
        6: b"<< /Type /Page /Parent 2 0 R " + MEDIABOX + b" >>",
        7: b"[3 0 R /XYZ null null 0]",
    }
    objects.update(extra or {})
    return build_pdf(objects)


def test_open_action_destination_v1_vectors() -> None:
    module = inspection_module()
    observation = {"entry_bytes": FIXTURE_ENTRY, "descriptors": [], "tmpdir_entries": 0,
                   "pycache_state": "ABSENT", "pycache_prefix_matches": 1}

    def run(pdf: bytes, reader=None):
        ctx = module.ChildContext(pdf, observation, 20, 15)
        ctx.reader = reader if reader is not None else module.open_pypdf_reader(pdf)
        return ctx, module.execute_stage(ctx, "S5.03", module.stage_s5_03)

    unsupported = ("FAIL", ("RENDER_DOCUMENT_STATE_UNSUPPORTED", "OPEN_ACTION_PRESENT", None))

    def verdict(open_action: bytes, extra: dict | None = None):
        _, (outcome, triple, _evidence) = run(_open_action_pdf(open_action, extra))
        return outcome, triple if outcome == "FAIL" else None

    # admitted: the exact [page /XYZ null null 0] destination array
    for label, value in (("integer zero", b"[3 0 R /XYZ null null 0]"), ("real zero", b"[3 0 R /XYZ null null 0.0]"),
                         ("negative real zero", b"[3 0 R /XYZ null null -0.0]"),
                         ("indirect array", b"7 0 R")):
        _, (outcome, triple, evidence) = run(_open_action_pdf(value))
        assert_true(outcome == "PASS" and "OpenAction" in evidence["catalog_keys"],
                    f"/OpenAction admitted: {label}: {outcome} {triple}")
    for label, value in (("absent", b""), ("direct null", b"null")):
        _, (outcome, _triple, evidence) = run(_open_action_pdf(value))
        assert_true(outcome == "PASS", f"/OpenAction {label} remains not present: {outcome}")

    page = b"3 0 R"
    negatives = [
        ("dictionary", b"<< /Type /Action /S /GoTo /D [3 0 R /XYZ null null 0] >>"),
        ("JavaScript", b"<< /S /JavaScript /JS (app.alert(1)) >>"),
        ("URI", b"<< /S /URI /URI (https://example.invalid/) >>"),
        ("Launch", b"<< /S /Launch /F (cmd.exe) >>"),
        ("GoToR", b"<< /S /GoToR /F (other.pdf) /D [0 /XYZ null null 0] >>"),
        ("SubmitForm", b"<< /S /SubmitForm /F (https://example.invalid/) >>"),
        ("ImportData", b"<< /S /ImportData /F (data.fdf) >>"),
        ("Named", b"<< /S /Named /N /NextPage >>"),
        ("/Fit", b"[" + page + b" /Fit]"),
        ("/FitH", b"[" + page + b" /FitH null]"),
        ("/FitV", b"[" + page + b" /FitV null]"),
        ("/FitR", b"[" + page + b" /FitR 0 0 100 100]"),
        ("/FitB", b"[" + page + b" /FitB]"),
        ("/FitBH", b"[" + page + b" /FitBH null]"),
        ("/FitBV", b"[" + page + b" /FitBV null]"),
        ("/Fit with five elements", b"[" + page + b" /Fit null null 0]"),
        ("length 4", b"[" + page + b" /XYZ null null]"),
        ("length 6", b"[" + page + b" /XYZ null null 0 0]"),
        ("empty array", b"[]"),
        ("page absent from the page tree", b"[6 0 R /XYZ null null 0]"),
        ("page of another document (unknown object)", b"[99 0 R /XYZ null null 0]"),
        ("page generation mismatch", b"[3 1 R /XYZ null null 0]"),
        ("non-page indirect object", b"[4 0 R /XYZ null null 0]"),
        ("direct page object", b"[<< /Type /Page /Parent 2 0 R >> /XYZ null null 0]"),
        ("null first element", b"[null /XYZ null null 0]"),
        ("integer first element", b"[0 /XYZ null null 0]"),
        ("non-null element 2", b"[" + page + b" /XYZ 10 null 0]"),
        ("non-null element 3", b"[" + page + b" /XYZ null 10 0]"),
        ("non-zero integer zoom", b"[" + page + b" /XYZ null null 1]"),
        ("non-zero real zoom", b"[" + page + b" /XYZ null null 0.5]"),
        ("boolean zoom", b"[" + page + b" /XYZ null null true]"),
        ("null zoom", b"[" + page + b" /XYZ null null null]"),
        ("name zoom", b"[" + page + b" /XYZ null null /Zero]"),
        ("string mode", b"[" + page + b" (XYZ) null null 0]"),
        ("non-array scalar", b"42"),
        ("name value", b"/XYZ"),
        ("missing indirect object", b"99 0 R"),
        ("indirect to a non-array object", b"4 0 R"),
        ("array with a missing indirect element", b"[" + page + b" /XYZ 99 0 R null 0]"),
    ]
    for label, value in negatives:
        result = verdict(value)
        assert_true(result == unsupported, f"/OpenAction not admitted: {label}: {result}")

    # a raising read stays a read failure, never an admission or a presence verdict
    pdf = _open_action_pdf(b"[3 0 R /XYZ null null 0]")
    real = module.open_pypdf_reader(pdf)

    class RaisingPages:
        trailer = real.trailer

        @property
        def pages(self):
            raise RuntimeError("page tree read")

    ctx, (outcome, triple, evidence) = run(pdf, RaisingPages())
    assert_true(outcome == "FAIL" and triple == ("RENDER_PDF_INSPECTION_FAILED", "DOCUMENT_STATE_READ", None)
                and evidence["slot"] == "S5.03", f"raising page enumeration: {outcome} {triple} {evidence}")

    class RaisingElement(module.ArrayObject):
        def __iter__(self):
            raise RuntimeError("element read")

    raising_root = module.DictionaryObject({module.NameObject("/OpenAction"):
                                            RaisingElement([module.NullObject()] * 5)})
    ctx = module.ChildContext(pdf, observation, 20, 15)
    ctx.reader = types.SimpleNamespace(trailer=module.DictionaryObject({module.NameObject("/Root"): raising_root}),
                                       pages=[])
    outcome, triple, evidence = module.execute_stage(ctx, "S5.03", module.stage_s5_03)
    assert_true(outcome == "FAIL" and triple == ("RENDER_PDF_INSPECTION_FAILED", "DOCUMENT_STATE_READ", None),
                f"raising element read: {outcome} {triple}")

    # no other denied catalog key acquired an exception
    for key in (b"/AA << >>", b"/Names << >>", b"/AcroForm << >>", b"/Outlines 4 0 R"):
        catalog = CATALOG[:-3] + b" " + key + b" /OpenAction [3 0 R /XYZ null null 0] >>"
        _, (outcome, triple, _evidence) = run(build_pdf({
            1: catalog, 2: b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            3: b"<< /Type /Page /Parent 2 0 R " + MEDIABOX + b" >>", 4: b"<< >>"}))
        assert_true(outcome == "FAIL" and triple[0] == "RENDER_DOCUMENT_STATE_UNSUPPORTED"
                    and triple[1] != "OPEN_ACTION_PRESENT", f"other catalog key still denied: {key}: {triple}")


# ORDER_INDEPENDENT_LINKAGE_V1 vectors --------------------------------------------

LINK_URLS = {
    "email": "mailto:person@example.org",
    "linkedin": "https://www.linkedin.com/in/example-person",
    "github": "https://github.com/example-person",
    "project": "https://github.com/example-person/example-project",
}
LINK_LABELS = {"email": "person@example.org", "linkedin": "LinkedIn", "github": "GitHub", "project": "GitHub"}


def link_occurrence(key, label=None, dest=None):
    text = label if label is not None else LINK_LABELS[key]
    return {"dest_kind": "EXTERNAL_URI", "dest": dest or LINK_URLS[key], "tokens": adapter.tokenize(text), "paragraph_index": 0}


def link_annotation(key, y, x=100.0, page=0, label=None, uri=None):
    text = label if label is not None else LINK_LABELS[key]
    return {"annot_index": 0, "page_index": page, "kind": "LINK_URI", "uri": uri or LINK_URLS[key], "goto_page": None,
            "words_text": text.split(), "rect_ccs": [x, y, x + 40.0, y + 10.0]}


def goto_annotation(page_target, y, label, page=0, x=100.0):
    return {"annot_index": 0, "page_index": page, "kind": "LINK_GOTO", "uri": None, "goto_page": page_target,
            "words_text": label.split(), "rect_ccs": [x, y, x + 40.0, y + 10.0]}


def run_linkage(occurrences, annotations, bookmarks=None, lines=None):
    model = types.SimpleNamespace(occurrences=occurrences, bookmark_paragraph=bookmarks or {})
    line_objects = lines or []
    try:
        return ("PASS", adapter.link_linkage(model, {"annotations": annotations}, line_objects))
    except adapter.StageFailure as failure:
        return ("FAIL", failure.outcome.status)


def former_source_order_matcher(occurrences, annotations):
    """A retained copy of the former source-order pointer matcher, used only to prove that the reordered vector is
    sensitive to the removed assumption (it returns the status the former algorithm produced)."""
    pending = [dict(item, tokens=adapter.tokenize(" ".join(item["words_text"]))) for item in annotations]
    pointer = 0
    for occurrence in occurrences:
        def dest_match(annotation, uri=occurrence["dest"]):
            return annotation["kind"] == "LINK_URI" and annotation["uri"] == uri
        found = None
        for count in range(1, len(pending) - pointer + 1):
            candidate = pending[pointer + count - 1]
            if not dest_match(candidate):
                break
            collected = [token for entry in pending[pointer:pointer + count] for token in entry["tokens"]]
            if collected == occurrence["tokens"]:
                found = count
                break
        if found is None:
            if any(dest_match(annotation) for annotation in pending[pointer + 1:]):
                return "RENDER_LINK_ORDER_MISMATCH"
            return "RENDER_LINK_MISSING"
        pointer += found
    return "PASS" if pointer == len(pending) else "RENDER_LINK_FABRICATED"


def test_order_independent_link_linkage() -> None:
    keys = ("email", "linkedin", "github", "project")
    source = [link_occurrence(key) for key in keys]
    # Reading order on one page: contact links on the top line (left to right), the project link lower on the page.
    placed = {"email": link_annotation("email", 700.0, 100.0), "linkedin": link_annotation("linkedin", 700.0, 200.0),
              "github": link_annotation("github", 700.0, 300.0), "project": link_annotation("project", 200.0, 400.0)}

    def hyperlinks_of(result):
        assert_true(result[0] == "PASS", f"expected PASS: {result}")
        return result[1]

    # (1) four links whose PDF order equals the source order.
    same_order = hyperlinks_of(run_linkage(source, [placed[key] for key in keys]))
    assert_true([item["dest"] for item in same_order] == [LINK_URLS[key] for key in keys], "(1) source-occurrence order")
    # (2) the LibreOffice-observed order: the first source link, then the remaining links in reverse source order.
    observed = [placed["email"], placed["project"], placed["github"], placed["linkedin"]]
    assert_true(hyperlinks_of(run_linkage(source, observed)) == same_order, "(2) reordered annotations give the identical logical list")
    assert_true(former_source_order_matcher(source, observed) == "RENDER_LINK_ORDER_MISMATCH",
                "(12) the former source-order matcher fails the reordered vector")
    assert_true(former_source_order_matcher(source, [placed[key] for key in keys]) == "PASS",
                "(12) the former matcher still accepts the source-ordered vector, so the regression is not vacuous")
    # (3) all annotations reversed.
    assert_true(hyperlinks_of(run_linkage(source, [placed[key] for key in reversed(keys)])) == same_order, "(3) fully reversed order")
    # (4) a correct label with a wrong URI.
    wrong_uri = [dict(placed[key]) for key in keys]
    wrong_uri[2] = link_annotation("github", 700.0, 300.0, uri="https://github.com/someone-else")
    assert_true(run_linkage(source, wrong_uri) == ("FAIL", "RENDER_LINK_DESTINATION_SUBSTITUTED"), "(4) wrong URI with correct text")
    # (5) a correct URI with a wrong visible label.
    wrong_label = [dict(placed[key]) for key in keys]
    wrong_label[1] = link_annotation("linkedin", 700.0, 200.0, label="Profile")
    assert_true(run_linkage(source, wrong_label) == ("FAIL", "RENDER_LINK_ATTRIBUTION_AMBIGUOUS"), "(5) correct URI with wrong text")
    # (6) a missing link; (7) an extra link.
    assert_true(run_linkage(source, [placed[key] for key in keys[:-1]]) == ("FAIL", "RENDER_LINK_MISSING"), "(6) missing link")
    extra = [placed[key] for key in keys] + [link_annotation("github", 600.0, 100.0, uri="https://example.org/extra", label="Extra")]
    assert_true(run_linkage(source, extra) == ("FAIL", "RENDER_LINK_FABRICATED"), "(7) extra link is fabricated")
    # (8) identical duplicate source occurrences: exact cardinality and the ordinal rule.
    twin_source = [link_occurrence("github"), link_occurrence("github")]
    upper, lower = link_annotation("github", 700.0, 100.0), link_annotation("github", 300.0, 100.0)
    for order in ([upper, lower], [lower, upper]):
        result = hyperlinks_of(run_linkage(twin_source, order))
        assert_true(result[0]["page_rects"] != result[1]["page_rects"] and result[0]["page_rects"][0][2] > result[1]["page_rects"][0][2],
                    "(8) the first source occurrence takes the first group in reading order whatever the array order")
    assert_true(run_linkage(twin_source, [upper]) == ("FAIL", "RENDER_LINK_MISSING"), "(8) cardinality shortfall fails")
    # (9) an additional identical annotation (not an exact-rect duplicate) is ambiguous, never an arbitrary choice.
    assert_true(run_linkage([link_occurrence("github")], [upper, lower]) == ("FAIL", "RENDER_LINK_ATTRIBUTION_AMBIGUOUS"),
                "(9) ambiguous duplicate annotations")
    # A partial-token run is never a candidate group.
    partial_source = [link_occurrence("github", label="Open GitHub profile")]
    partial = [link_annotation("github", 700.0, 100.0, label="Open GitHub")]
    assert_true(run_linkage(partial_source, partial) == ("FAIL", "RENDER_LINK_ATTRIBUTION_AMBIGUOUS"), "partial-token match fails")
    # A wrapped hyperlink: two rects on two lines form one candidate group in reading order, whatever the array order.
    wrapped_source = [link_occurrence("github", label="Open GitHub profile")]
    first_rect = link_annotation("github", 700.0, 100.0, label="Open GitHub")
    second_rect = link_annotation("github", 688.0, 100.0, label="profile")
    for order in ([first_rect, second_rect], [second_rect, first_rect]):
        result = hyperlinks_of(run_linkage(wrapped_source, order))
        assert_true(len(result[0]["page_rects"]) == 2 and result[0]["page_rects"][0][2] > result[0]["page_rects"][1][2],
                    "a wrapped hyperlink is one logical link with page_rects in reading order")
    # An annotation is never reused by two occurrences with different labels at one destination.
    one_annotation = [link_occurrence("github", label="GitHub"), link_occurrence("github", label="Source")]
    assert_true(run_linkage(one_annotation, [link_annotation("github", 700.0, 100.0)])[0] == "FAIL", "one annotation is never reused")
    # (10) internal GoTo links remain matched by page; a substituted internal destination fails.
    line = types.SimpleNamespace(paragraph_index=3, page_index=1)
    internal = [{"dest_kind": "INTERNAL_ANCHOR", "dest": "_Ref1", "tokens": adapter.tokenize("See below"), "paragraph_index": 0}]
    ok = run_linkage(internal, [goto_annotation(1, 500.0, "See below")], bookmarks={"_Ref1": 3}, lines=[line])
    assert_true(ok[0] == "PASS" and ok[1][0]["goto_page"] == 1, "(10) internal GoTo matched by page")
    wrong_page = run_linkage(internal, [goto_annotation(0, 500.0, "See below")], bookmarks={"_Ref1": 3}, lines=[line])
    assert_true(wrong_page == ("FAIL", "RENDER_LINK_DESTINATION_SUBSTITUTED") or wrong_page == ("FAIL", "RENDER_LINK_ATTRIBUTION_AMBIGUOUS"),
                f"a substituted internal destination fails: {wrong_page}")
    # (11) mixed external and internal links in a reordered PDF.
    mixed_source = [link_occurrence("github"), internal[0], link_occurrence("email")]
    mixed = [link_annotation("email", 700.0, 300.0), goto_annotation(1, 500.0, "See below"), link_annotation("github", 700.0, 100.0)]
    mixed_result = run_linkage(mixed_source, mixed, bookmarks={"_Ref1": 3}, lines=[line])
    assert_true(mixed_result[0] == "PASS" and [item["dest_kind"] for item in mixed_result[1]] ==
                ["EXTERNAL_URI", "INTERNAL_ANCHOR", "EXTERNAL_URI"], "(11) mixed external and internal links")
    # RENDER_LINK_ORDER_MISMATCH is reserved: the adapter never emits it.
    source_text = (ROOT / "src" / "document_render_adapter.py").read_text(encoding="utf-8")
    assert_true(source_text.count("RENDER_LINK_ORDER_MISMATCH") == 1, "RENDER_LINK_ORDER_MISMATCH stays a reserved name only")


DEPENDENCY_FREE_TESTS = (
    test_operator_font_tables_and_probe_vectors,
    test_operator_apt_records_and_post_manifest_assembly,
    test_operator_sandbox_and_root_derivation,
    test_operator_content_root_digests_on_a_real_tree,
    test_operator_prober_checks_and_verification_record,
    test_operator_fixtures_entry_constant_and_static_rules,
    test_post_apt_ld_so_cache_v1_vectors,
    test_post_apt_ld_so_cache_v1_static_rules,
    test_tag_sequence_generator_v1_reproduces_sys_tags,
    test_manifest_list_parser_bash_rematch_regression,
    test_manifest_e2_helper_chain_record,
    test_process_creation_record_v2_sequence_vectors,
    test_e2_helper_chain_static_analysis_capture_and_check,
    test_provisioning_script_e2_helper_chain_static_rules,
    test_pre_gate3_cli_dispatch,
    test_apt_noninteractive_proof_vectors,
    test_process_creation_proof_orchestration,
    test_process_creation_proof_real_posix_vectors,
    test_post_evidence_partial_vectors,
    test_dpkg_option_syntax_v1_vectors,
    test_static_source_rules,
    test_fail_evidence_encoders,
    test_entry_and_adapter_constants_agree,
    test_entry_extraction_constants_govern_s2,
    test_fail_frame_maxima_bound_every_encodable_frame,
    test_text_uri_and_quantization_vectors,
    test_fail_string_and_identifier_grammar,
    test_docx_preflight_vectors,
    test_manifest_vectors,
    test_plan_digest_partition_vectors,
    test_content_binding_vectors,
    test_sandbox_argv_profile_and_isolation,
    test_temp_layout_snapshot_and_delivery,
    test_child_frame_validator_equals_schema,
    test_evidence_record_schema,
    test_stream_protocol_vectors,
    test_parent_child_partition_vectors,
    test_traversal_hidden_text_matrix,
    test_line_building_and_colour_normalization,
    test_child_emitter_and_start_attestation,
    test_orchestration_with_fakes,
    test_adapter_static_rules,
    test_order_independent_link_linkage,
)

DEPENDENCY_TESTS = (
    test_pinned_versions,
    test_cycle_rows_rejected_before_interpretation,
    test_form_execution_equivalence,
    test_unresolved_reference_exemption_r11_p7,
    test_font_structure_missing_object_vectors_pass_s601b,
    test_exemption_negative_vectors,
    test_non_raising_fake_shadow_is_sc36_stop,
    test_fake_library_edge_outside_prediction_is_sc36_stop,
    test_name_domain_vectors,
    test_stream_mismatch_vectors,
    test_raw_stream_bytes_identity,
    test_open_action_destination_v1_vectors,
)


def operator_link_regression(argv: list) -> int:
    """OPERATOR-gated regression of ORDER_INDEPENDENT_LINKAGE_V1: a four-link Gold-style DOCX (email, LinkedIn, GitHub profile and
    project GitHub) goes through the pinned LibreOffice build and the real inspection, whose PDF link annotations are not in source
    order. Usage (governed interpreter): --operator-link-regression --verification-evidence PATH --work-dir DIR."""
    options = dict(zip(argv[1::2], argv[2::2]))
    verification = json.loads(Path(options["--verification-evidence"]).read_text(encoding="utf-8"))
    work = Path(options["--work-dir"])
    work.mkdir(parents=True, exist_ok=True)
    manifest_bytes = (ROOT / "docs" / "rendering" / "RENDERING_ENVIRONMENT_V1.json").read_bytes()
    adapter.add_governed_site_path(adapter.operator_site_packages(adapter.verify_manifest(manifest_bytes)))
    links = [("person@example.org", "mailto:person@example.org"), ("LinkedIn", "https://www.linkedin.com/in/example-person"),
             ("GitHub", "https://github.com/example-person"), ("GitHub", "https://github.com/example-person/example-project")]
    family = '<w:rFonts w:ascii="Liberation Sans" w:hAnsi="Liberation Sans"/>'

    def run(text):
        return '<w:r><w:rPr>%s</w:rPr><w:t xml:space="preserve">%s</w:t></w:r>' % (family, text)

    def link(index):
        return '<w:hyperlink r:id="rId%d">%s</w:hyperlink>' % (10 + index, run(links[index][0]))

    first = run("Contact: ") + link(0) + run(" | ") + link(1) + run(" | ") + link(2)
    second = run("Project: ") + link(3)
    document = ('%s<w:document %s xmlns:r="%s"><w:body><w:p>%s</w:p><w:p>%s</w:p></w:body></w:document>'
                % (_XML, _W, "http://schemas.openxmlformats.org/officeDocument/2006/relationships", first, second))
    rels = "".join('<Relationship Id="rId%d" Type="%shyperlink" Target="%s" TargetMode="External"/>' % (10 + i, _OFFICE_REL, url)
                   for i, (_label, url) in enumerate(links))
    docx_bytes = docx_fixture(document_xml=document, extra_doc_rels=rels)
    structure_map = [{"paragraph_index": 0, "content_type": "CONTACT_LINE", "list_semantics": None,
                      "paragraph_text": "Contact: person@example.org | LinkedIn | GitHub"},
                     {"paragraph_index": 1, "content_type": "PROJECT_HEADER", "list_semantics": None, "paragraph_text": "Project: GitHub"}]
    docx_path, map_path = work / "four_links.docx", work / "four_links.structure_map.json"
    docx_path.write_bytes(docx_bytes)
    map_path.write_text(json.dumps(structure_map), encoding="utf-8")
    outcome = adapter.run_first_render(ROOT, manifest_bytes, str(docx_path), hashlib.sha256(docx_bytes).hexdigest(), str(work / "render"),
                                       str(map_path), verification_record=verification)
    record = outcome["record"]
    print(json.dumps({"run_status": record["run_status"], "reason": record["reason"], "delivered": record["delivered"],
                      "fingerprint": record.get("render_semantic_fingerprint")}, sort_keys=True))
    assert_true(record["reason"] is None and record["delivered"] == 1 and record["run_status"] in (adapter.STATUS_PASS, adapter.STATUS_QA_FAILED),
                f"the real renderer delivered a four-link PDF without a link status: {record['run_status']} {record['reason']}")
    from pypdf import PdfReader
    reader = PdfReader(outcome["pdf_path"])
    pdf_links = []
    for annotation in reader.pages[0].get("/Annots", []):
        pdf_links.append(str(annotation.get_object()["/A"]["/URI"]))
    expected = [url for _label, url in links]
    print(json.dumps({"source_order": expected, "pdf_annotation_order": pdf_links}))
    assert_true(sorted(pdf_links) == sorted(expected), "all four genuine URI annotations are present with exact destinations")
    assert_true(pdf_links != expected, "the pinned LibreOffice build emits the annotations out of source order and the renderer still accepts them")
    print(json.dumps({"operator_link_regression": "PASS"}))
    return 0


def main() -> None:
    if "--operator-link-regression" in sys.argv:
        raise SystemExit(operator_link_regression(sys.argv[1:]))
    for test in DEPENDENCY_FREE_TESTS:
        test()
    print(f"PASS: {len(DEPENDENCY_FREE_TESTS)} dependency-free vector groups")
    if MISSING_DEPENDENCIES:
        print("BLOCKED_DEPENDENCY_NOT_INSTALLED: %s absent; %d pinned-library vector groups not run: %s"
              % (", ".join(MISSING_DEPENDENCIES), len(DEPENDENCY_TESTS),
                 ", ".join(test.__name__ for test in DEPENDENCY_TESTS)))
        raise SystemExit(2)
    for test in DEPENDENCY_TESTS:
        test()
    print("PASS: document_rendering_capability_v1_test")


if __name__ == "__main__":
    main()
