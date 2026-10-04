"""Deterministic model-built Gold resume DOCX builder (PURSUE_TO_GOLD_PACKAGE_V1, model-built reconciliation).

The builder turns an approved structured Gold resume model into OOXML directly. It never clones, resaves or reads the
historical Gold Word exemplar and it emits only the parts the canonically released renderer's preflight admits:
[Content_Types].xml, _rels/.rels, word/document.xml, word/_rels/document.xml.rels, word/styles.xml and
word/numbering.xml. There is no customXml, theme, settings, macro, OLE or external-data part; the only external
relationships are genuine hyperlink relationships to http, https and mailto targets.

Every numeric presentation value (page size, margins, type sizes, font) is read from the canonical Gold doctrine
record BORA_SPY_POND_GOLD_REFERENCE_V1; no second Gold standard exists here. The structure map is produced by the same
code path, from the same model, as the DOCX paragraphs, using only the existing canonical renderer vocabulary.

Wrapping is solved deterministically before rendering. The released renderer fails closed when a rendered line ends
in a literal source hyphen (RENDER_ATTRIBUTION_INCOMPLETE / HYPHENATION_OBSERVED) and treats any other split of a
source token as a token mismatch, so for every wrapping paragraph a bounded presentation-only right indent is chosen
from Liberation Sans advance widths such that no predicted line ends at a literal '-', '/', en dash or em dash with a
documented safety margin. Approved wording is never changed and no punctuation is substituted. A bounded vertical
density step is chosen the same way so the predicted page fill lands inside the doctrine window; when no bounded
adjustment exists the build fails closed (it never adds filler and never lowers a floor).
"""

from __future__ import annotations

import hashlib
import html
import io
import json
import re
import struct
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

BUILDER_ID = "GOLD_RESUME_DOCX_BUILDER_V1"
SECTION_HEADINGS = ("EDUCATION", "SKILLS", "WORK EXPERIENCE", "RELEVANT PROJECT")
SKILLS_ROW_LABELS = ("Process & quality", "Technical", "Operations")
CONTACT_SEPARATOR = " | "
ALLOWED_HYPERLINK_SCHEMES = ("https", "http", "mailto")

# Existing canonical renderer structure-map vocabulary (src/resume_page_utilization.MEANINGFUL_CONTENT_TYPES).
CT_CONTACT = "CONTACT_LINE"
CT_HEADING = "SECTION_HEADING"
CT_SUMMARY = "SUMMARY_TEXT"
CT_EDUCATION = "EDUCATION_LINE"
CT_EMPLOYMENT = "EMPLOYMENT_HEADER"
CT_BULLET = "BULLET_TEXT"
CT_PROJECT = "PROJECT_HEADER"
CT_SKILLS = "SKILLS_LINE"
# The candidate name is the single renderer-nonmeaningful label (the structure map admits any string; only the
# eight canonical meaningful types count toward page utilization).
CT_NAME = "NAME"
CANONICAL_CONTENT_TYPES = (CT_CONTACT, CT_HEADING, CT_SUMMARY, CT_EDUCATION, CT_EMPLOYMENT, CT_BULLET, CT_PROJECT, CT_SKILLS, CT_NAME)

UNSAFE_BREAK_CHARACTERS = "-/–—"
HYPHEN_SAFETY_FACTORS = (0.97, 1.0, 1.03)
RIGHT_INDENT_STEP_TWIPS = 60
RIGHT_INDENT_MAX_TWIPS = 3000
BODY_LINE_PITCH_240THS = (247, 252, 258, 264)
SPACING_SCALES = (1.0, 1.5, 2.0, 2.5, 3.0)
PAGE_FILL_TARGET = 0.935
PAGE_FILL_CEILING = 0.965
# Calibrated against the real Liberation Sans render (see tests/pursue_to_gold_package_v1_test.py operator regression).
BOTTOM_CALIBRATION_PT = 6.0

HEADING_RULE_SIZE_EIGHTHS = 4
HEADING_RULE_COLOR = "444444"
LINK_COLOR = "000000"
NS_W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS_R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"


class GoldBuildError(Exception):
    """Fail-closed build condition; CODE is a stable machine-readable reason."""

    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(code, detail)
        self.code = code
        self.detail = detail


# Doctrine metrics -------------------------------------------------------------------------------

@dataclass(frozen=True)
class GoldMetrics:
    page_width_twips: int
    page_height_twips: int
    margin_left_twips: int
    margin_right_twips: int
    margin_top_twips: int
    margin_bottom_twips: int
    name_half_points: int
    body_half_points: int
    heading_half_points: int
    font_family: str
    fallback_font: str

    @property
    def text_width_twips(self) -> int:
        return self.page_width_twips - self.margin_left_twips - self.margin_right_twips

    @classmethod
    def from_doctrine(cls, spy_pond_record: Mapping[str, Any]) -> "GoldMetrics":
        visual = spy_pond_record["visual_metrics"]
        if visual["page_size"] != "US_LETTER" or visual["columns"] != 1:
            raise GoldBuildError("DOCTRINE_UNSUPPORTED", "page size or column count")
        margins = visual["margins_inches"]
        typography = visual["typography"]
        return cls(
            page_width_twips=12240,
            page_height_twips=15840,
            margin_left_twips=round(margins["left"] * 1440),
            margin_right_twips=round(margins["right"] * 1440),
            margin_top_twips=round(margins["top"] * 1440),
            margin_bottom_twips=round(margins["bottom"] * 1440),
            name_half_points=round(typography["name"]["size_pt"] * 2),
            body_half_points=round(typography["body_and_contact"]["size_pt"] * 2),
            heading_half_points=round(typography["section_headings"]["size_pt"] * 2),
            font_family=typography["primary_font"],
            fallback_font=typography["fallback_font"],
        )


# Font metrics ------------------------------------------------------------------------------------

class FontMetrics:
    """Advance widths and line height for the regular and bold Liberation Sans faces, read from font bytes with the
    standard library only. A synthetic table (fixed em width) exists for dependency-free tests."""

    def __init__(self, regular: "_Face", bold: "_Face") -> None:
        self._regular = regular
        self._bold = bold

    @classmethod
    def from_font_bytes(cls, regular_bytes: bytes, bold_bytes: bytes) -> "FontMetrics":
        return cls(_Face.parse(regular_bytes), _Face.parse(bold_bytes))

    @classmethod
    def synthetic(cls, regular_em: float = 0.5, bold_em: float = 0.54, line_height_em: float = 1.149) -> "FontMetrics":
        return cls(_Face.synthetic(regular_em, line_height_em), _Face.synthetic(bold_em, line_height_em))

    def width(self, text: str, size_pt: float, bold: bool = False) -> float:
        return (self._bold if bold else self._regular).width(text, size_pt)

    def line_height(self, size_pt: float) -> float:
        return self._regular.line_height(size_pt)


class _Face:
    def __init__(self, advances, cmap, units_per_em, line_height_units, fixed_em: Optional[float]) -> None:
        self._advances = advances
        self._cmap = cmap
        self._upm = units_per_em
        self._line_units = line_height_units
        self._fixed_em = fixed_em

    @classmethod
    def synthetic(cls, em: float, line_height_em: float) -> "_Face":
        return cls(None, None, 1000, round(line_height_em * 1000), em)

    @classmethod
    def parse(cls, data: bytes) -> "_Face":
        try:
            count = struct.unpack(">H", data[4:6])[0]
            tables = {}
            for index in range(count):
                tag, _checksum, offset, length = struct.unpack(">4sIII", data[12 + 16 * index:28 + 16 * index])
                tables[tag] = (offset, length)
            head, hhea, hmtx, cmap_table = tables[b"head"][0], tables[b"hhea"][0], tables[b"hmtx"][0], tables[b"cmap"][0]
            upm = struct.unpack(">H", data[head + 18:head + 20])[0]
            ascent, descent, gap = struct.unpack(">hhh", data[hhea + 4:hhea + 10])
            metric_count = struct.unpack(">H", data[hhea + 34:hhea + 36])[0]
            advances = [struct.unpack(">H", data[hmtx + 4 * i:hmtx + 4 * i + 2])[0] for i in range(metric_count)]
            cmap = _read_cmap_format4(data, cmap_table)
        except (KeyError, struct.error, IndexError) as error:
            raise GoldBuildError("FONT_BYTES_UNREADABLE", type(error).__name__) from error
        if not cmap:
            raise GoldBuildError("FONT_BYTES_UNREADABLE", "no format 4 cmap")
        return cls(advances, cmap, upm, ascent - descent + gap, None)

    def width(self, text: str, size_pt: float) -> float:
        if self._fixed_em is not None:
            return len(text) * self._fixed_em * size_pt
        total = 0
        for character in text:
            glyph = self._cmap.get(ord(character))
            if glyph is None:
                raise GoldBuildError("FONT_GLYPH_MISSING", "U+%04X" % ord(character))
            total += self._advances[min(glyph, len(self._advances) - 1)]
        return total * size_pt / self._upm

    def line_height(self, size_pt: float) -> float:
        return self._line_units * size_pt / self._upm


def _read_cmap_format4(data: bytes, cmap_offset: int) -> dict:
    table_count = struct.unpack(">H", data[cmap_offset + 2:cmap_offset + 4])[0]
    for index in range(table_count):
        platform, encoding, offset = struct.unpack(">HHI", data[cmap_offset + 4 + 8 * index:cmap_offset + 12 + 8 * index])
        base = cmap_offset + offset
        if (platform, encoding) not in ((3, 1), (0, 3)) or struct.unpack(">H", data[base:base + 2])[0] != 4:
            continue
        segments = struct.unpack(">H", data[base + 6:base + 8])[0] // 2
        ends = struct.unpack(">%dH" % segments, data[base + 14:base + 14 + 2 * segments])
        starts = struct.unpack(">%dH" % segments, data[base + 16 + 2 * segments:base + 16 + 4 * segments])
        deltas = struct.unpack(">%dh" % segments, data[base + 16 + 4 * segments:base + 16 + 6 * segments])
        range_base = base + 16 + 6 * segments
        range_offsets = struct.unpack(">%dH" % segments, data[range_base:range_base + 2 * segments])
        mapping = {}
        for segment in range(segments):
            for code in range(starts[segment], ends[segment] + 1):
                if code == 0xFFFF:
                    continue
                if range_offsets[segment] == 0:
                    glyph = (code + deltas[segment]) & 0xFFFF
                else:
                    position = range_base + 2 * segment + range_offsets[segment] + 2 * (code - starts[segment])
                    glyph = struct.unpack(">H", data[position:position + 2])[0]
                    glyph = (glyph + deltas[segment]) & 0xFFFF if glyph else 0
                mapping[code] = glyph
        return mapping
    return {}


# Deterministic wrapping prediction and the hyphen-safe solver -------------------------------------

_BREAK_TOKEN = re.compile(r"[^\s\-/–—]+[\-/–—]?\s*|[\-/–—]\s*|\s+")


def predict_lines(text: str, width_pt: float, size_pt: float, fonts: FontMetrics, bold: bool = False) -> list:
    """Greedy line breaking at spaces and after '-', '/', en dash and em dash (the break opportunities the renderer's
    line breaker can use); returns the predicted lines without trailing spaces."""
    lines, current = [], ""
    for token in _BREAK_TOKEN.findall(text):
        candidate = current + token
        if not current or fonts.width(candidate.rstrip(), size_pt, bold) <= width_pt:
            current = candidate
        else:
            lines.append(current.rstrip())
            current = token
    if current:
        lines.append(current.rstrip())
    return lines


def _line_ends_unsafe(lines: Sequence[str]) -> bool:
    """True when a non-final predicted line ends inside a source token at a literal break character; a standalone dash token
    that is separated from its neighbours by spaces is a whole token and is not a hazard."""
    return any(len(line) > 1 and line[-1] in UNSAFE_BREAK_CHARACTERS and not line[-2].isspace() for line in lines[:-1])


def solve_right_indent(text: str, width_pt: float, size_pt: float, fonts: FontMetrics) -> int:
    """Smallest bounded right indent (twips) such that no predicted line ends at a literal break character for any
    width in HYPHEN_SAFETY_FACTORS; 0 when the paragraph already satisfies the condition."""
    for indent in range(0, RIGHT_INDENT_MAX_TWIPS + 1, RIGHT_INDENT_STEP_TWIPS):
        available = width_pt - indent / 20.0
        if available <= 0:
            break
        if all(not _line_ends_unsafe(predict_lines(text, available * factor, size_pt, fonts)) for factor in HYPHEN_SAFETY_FACTORS):
            return indent
    raise GoldBuildError("LAYOUT_UNSOLVABLE", "no bounded right indent avoids a literal line-end break: " + text[:60])


# Model access and expected links --------------------------------------------------------------

@dataclass(frozen=True)
class ExpectedLink:
    label: str
    url: str


def expected_links(model: Mapping[str, Any]) -> list:
    """The hyperlink occurrences of the model, in source order: email, profile links, then the project link."""
    contact = model["contact"]
    links = []
    if contact.get("email"):
        links.append(ExpectedLink(contact["email"], "mailto:" + contact["email"]))
    for link in contact.get("profile_links", []):
        links.append(ExpectedLink(link["label"], link["url"]))
    project = model.get("project")
    if project and project.get("link"):
        links.append(ExpectedLink(project["link"]["label"], project["link"]["url"]))
    for link in links:
        scheme = link.url.split(":", 1)[0].lower()
        if scheme not in ALLOWED_HYPERLINK_SCHEMES:
            raise GoldBuildError("LINK_SCHEME_NOT_ALLOWED", link.url)
    return links


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def model_digest(model: Mapping[str, Any]) -> str:
    return hashlib.sha256(canonical_json_bytes(model)).hexdigest()


# Paragraph specification ----------------------------------------------------------------------

@dataclass
class _Para:
    content_type: str
    runs: list  # (text, bold, size_half_points or None, link_rid or None)
    map_text: str
    align: Optional[str] = None
    tab_right: bool = False
    bullet: bool = False
    heading_rule: bool = False
    keep_next: bool = False
    before: int = 0
    after: int = 0
    body_line: bool = False
    wrap_text: Optional[str] = None  # text that may wrap (multi-line candidates)
    size_pt: float = 10.5
    bold_measure: bool = False
    right_indent: int = 0
    lines: int = 1
    left_text: Optional[str] = None
    right_text: Optional[str] = None
    link_labels: list = field(default_factory=list)


@dataclass
class GoldBuild:
    docx_bytes: bytes
    structure_map: list
    expected_links: list
    layout: dict


def _xml(text: str) -> str:
    return html.escape(text, quote=False)


# The builder ------------------------------------------------------------------------------------

def build_gold_docx(model: Mapping[str, Any], metrics: GoldMetrics, fonts: FontMetrics) -> GoldBuild:
    """Build the Gold DOCX, its structure map and its layout report from one approved model."""
    links = expected_links(model)
    link_ids = {}
    link_order = []
    for index, link in enumerate(links):
        link_ids[index] = "rId%d" % (3 + index)
        link_order.append((link_ids[index], link.url))
    body_pt = metrics.body_half_points / 2.0
    heading_pt = metrics.heading_half_points / 2.0
    name_pt = metrics.name_half_points / 2.0
    full_width_pt = metrics.text_width_twips / 20.0
    bullet_width_pt = (metrics.text_width_twips - 360) / 20.0
    link_counter = [0]

    def next_link(label: str) -> str:
        position = link_counter[0]
        link_counter[0] += 1
        if position >= len(links) or links[position].label != label:
            raise GoldBuildError("LINK_ORDER_INTERNAL", label)
        return link_ids[position]

    paras = []
    contact = model["contact"]
    paras.append(_Para(CT_NAME, [(contact["name"], True, metrics.name_half_points, None)], contact["name"], align="center",
                       after=30, size_pt=name_pt, bold_measure=True, wrap_text=None))
    # Contact line: location | phone | email | profile links
    runs, plain = [], []
    leading = [part for part in (contact.get("location"), contact.get("phone")) if part]
    if leading:
        runs.append((CONTACT_SEPARATOR.join(leading) + (CONTACT_SEPARATOR if (contact.get("email") or contact.get("profile_links")) else ""), False, None, None))
        plain.append(CONTACT_SEPARATOR.join(leading))
    first_link = True
    link_texts = []
    if contact.get("email"):
        link_texts.append(contact["email"])
    for link in contact.get("profile_links", []):
        link_texts.append(link["label"])
    for text in link_texts:
        if not first_link:
            runs.append((CONTACT_SEPARATOR, False, None, None))
        runs.append((text, False, None, next_link(text)))
        first_link = False
    map_text = CONTACT_SEPARATOR.join(plain + link_texts)
    paras.append(_Para(CT_CONTACT, runs, map_text, align="center", after=30, size_pt=body_pt, left_text=map_text))
    # Summary: no heading
    summary = model["summary"]["text"]
    paras.append(_Para(CT_SUMMARY, [(summary, False, None, None)], summary, align="center", after=22, size_pt=body_pt, wrap_text=summary, body_line=True))

    def heading(text: str) -> None:
        paras.append(_Para(CT_HEADING, [(text, True, metrics.heading_half_points, None)], text, heading_rule=True, keep_next=True,
                           before=65, after=25, size_pt=heading_pt, bold_measure=True, left_text=text))

    def header_line(left: str, right: str, content_type: str, before: int, after: int, extra_link: Optional[str] = None) -> None:
        runs = [(left, True, None, None), ("\t", False, None, None)]
        if right:
            runs.append((right, False, None, None))
        map_text = left + " " + right if right else left
        paras.append(_Para(content_type, runs, map_text, tab_right=True, keep_next=True, before=before, after=after, size_pt=body_pt,
                           left_text=left, right_text=right, bold_measure=True))

    heading(SECTION_HEADINGS[0])
    for school in model["education"]:
        header_line(school["school"], school["date_range"], CT_EDUCATION, 5, 0)
        paras.append(_Para(CT_EDUCATION, [(school["degree_line"], False, None, None)], school["degree_line"], after=22, size_pt=body_pt,
                           left_text=school["degree_line"]))
    heading(SECTION_HEADINGS[1])
    for row in model["skills"]:
        text = row["label"] + ": " + ", ".join(row["items"])
        paras.append(_Para(CT_SKILLS, [(text, False, None, None)], text, after=22, size_pt=body_pt, wrap_text=text, body_line=True))
    heading(SECTION_HEADINGS[2])
    for entry in model["work"]:
        header_line(entry["title"] + " | " + entry["employer"], entry["date_range"], CT_EMPLOYMENT, 12, 5)
        for bullet in entry["bullets"]:
            paras.append(_Para(CT_BULLET, [(bullet["text"], False, None, None)], bullet["text"], bullet=True, after=22, size_pt=body_pt,
                               wrap_text=bullet["text"], body_line=True))
    project = model.get("project")
    if project:
        heading(SECTION_HEADINGS[3])
        title = project["name"] + " - " + project["tech_label"]
        runs = [(title, True, None, None), ("\t", False, None, None)]
        project_label = project["link"]["label"] if project.get("link") else ""
        if project_label:
            runs.append((project_label, False, None, next_link(project_label)))
        paras.append(_Para(CT_PROJECT, runs, title + (" " + project_label if project_label else ""), tab_right=True, keep_next=True,
                           before=9, after=9, size_pt=body_pt, left_text=title, right_text=project_label, bold_measure=True))
        for bullet in project["bullets"]:
            paras.append(_Para(CT_BULLET, [(bullet["text"], False, None, None)], bullet["text"], bullet=True, after=22, size_pt=body_pt,
                               wrap_text=bullet["text"], body_line=True))
    if link_counter[0] != len(links):
        raise GoldBuildError("LINK_COUNT_INTERNAL", "%d of %d links placed" % (link_counter[0], len(links)))

    # Fit checks for single-line paragraphs; hyphen-safe indents for wrapping paragraphs.
    for para in paras:
        if para.wrap_text is not None:
            width = bullet_width_pt if para.bullet else full_width_pt
            para.right_indent = solve_right_indent(para.wrap_text, width, para.size_pt, fonts)
            width -= para.right_indent / 20.0
            para.lines = len(predict_lines(para.wrap_text, width, para.size_pt, fonts))
        else:
            if para.tab_right:
                needed = fonts.width(para.left_text, para.size_pt, True) + fonts.width(para.right_text or "", para.size_pt, False) + 12.0
            else:
                needed = fonts.width(para.left_text or para.map_text, para.size_pt, para.bold_measure)
            if needed > full_width_pt * min(HYPHEN_SAFETY_FACTORS):
                raise GoldBuildError("LAYOUT_LINE_OVERFLOW", "single-line paragraph does not fit: " + para.map_text[:60])

    density = _choose_density(paras, metrics, fonts, body_pt)
    xml_paragraphs = [_paragraph_xml(para, metrics, density, link_ids) for para in paras]
    document = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<w:document xmlns:w="%s" xmlns:r="%s"><w:body>%s<w:sectPr><w:pgSz w:w="%d" w:h="%d"/>'
                '<w:pgMar w:top="%d" w:right="%d" w:bottom="%d" w:left="%d" w:header="720" w:footer="720" w:gutter="0"/></w:sectPr>'
                '</w:body></w:document>') % (NS_W, NS_R, "".join(xml_paragraphs), metrics.page_width_twips, metrics.page_height_twips,
                                               metrics.margin_top_twips, metrics.margin_right_twips, metrics.margin_bottom_twips,
                                               metrics.margin_left_twips)
    structure_map = []
    for index, para in enumerate(paras):
        structure_map.append({"paragraph_index": index, "content_type": para.content_type, "paragraph_text": para.map_text,
                              "list_semantics": {"ilvl": 0, "numFmt": "bullet", "numId": 1} if para.bullet else None})
    parts = _package_parts(document, metrics, link_order)
    layout = {
        "builder_id": BUILDER_ID,
        "density_step": density["step"],
        "line_pitch_240ths": density["line"],
        "spacing_scale": density["scale"],
        "estimated_bottom_fraction": density["estimated_bottom_fraction"],
        "right_indents_twips": {str(index): para.right_indent for index, para in enumerate(paras) if para.right_indent},
        "predicted_lines": {str(index): para.lines for index, para in enumerate(paras) if para.wrap_text is not None},
    }
    return GoldBuild(_zip_bytes(parts), structure_map, links, layout)


def _paragraph_height_pt(para: _Para, metrics: GoldMetrics, density: Mapping[str, Any], fonts: FontMetrics) -> float:
    natural = fonts.line_height(para.size_pt)
    pitch = natural * (density["line"] / 240.0 if para.body_line else 1.0)
    before = para.before * density["scale"] / 20.0
    after = para.after * density["scale"] / 20.0
    return before + para.lines * pitch + after


def _choose_density(paras: list, metrics: GoldMetrics, fonts: FontMetrics, body_pt: float) -> dict:
    page_pt = metrics.page_height_twips / 20.0
    top_pt = metrics.margin_top_twips / 20.0
    step = 0
    best = None
    for line in BODY_LINE_PITCH_240THS:
        for scale in SPACING_SCALES:
            candidate = {"step": step, "line": line, "scale": scale}
            total = top_pt + sum(_paragraph_height_pt(para, metrics, candidate, fonts) for para in paras) - paras[-1].after * scale / 20.0
            fraction = (total + BOTTOM_CALIBRATION_PT) / page_pt
            candidate["estimated_bottom_fraction"] = round(fraction, 4)
            if fraction > PAGE_FILL_CEILING:
                if best is None:
                    raise GoldBuildError("LAYOUT_OVERFLOW", "predicted page fill %.3f exceeds %.3f at the tightest density" % (fraction, PAGE_FILL_CEILING))
                return best
            if fraction >= PAGE_FILL_TARGET:
                return candidate
            best = candidate
            step += 1
    raise GoldBuildError("LAYOUT_UNDERFILLED", "predicted page fill %.3f stays below %.3f at the loosest density" % (best["estimated_bottom_fraction"], PAGE_FILL_TARGET))


def _run_xml(text: str, bold: bool, size_half_points: Optional[int], link: bool, family: str) -> str:
    properties = '<w:rFonts w:ascii="%s" w:hAnsi="%s"/>' % (family, family)
    if bold:
        properties += "<w:b/>"
    if link:
        properties += '<w:color w:val="%s"/><w:u w:val="single"/>' % LINK_COLOR
    if size_half_points:
        properties += '<w:sz w:val="%d"/>' % size_half_points
    if text == "\t":
        return "<w:r><w:rPr>%s</w:rPr><w:tab/></w:r>" % properties
    return '<w:r><w:rPr>%s</w:rPr><w:t xml:space="preserve">%s</w:t></w:r>' % (properties, _xml(text))


def _paragraph_xml(para: _Para, metrics: GoldMetrics, density: Mapping[str, Any], link_ids: Mapping[int, str]) -> str:
    family = metrics.font_family
    properties = ""
    if para.keep_next:
        properties += "<w:keepNext/>"
    if para.bullet:
        properties += '<w:numPr><w:ilvl w:val="0"/><w:numId w:val="1"/></w:numPr>'
    if para.heading_rule:
        properties += '<w:pBdr><w:bottom w:val="single" w:sz="%d" w:space="1" w:color="%s"/></w:pBdr>' % (HEADING_RULE_SIZE_EIGHTHS, HEADING_RULE_COLOR)
    if para.tab_right:
        properties += '<w:tabs><w:tab w:val="right" w:pos="%d"/></w:tabs>' % metrics.text_width_twips
    before = round(para.before * density["scale"])
    after = round(para.after * density["scale"])
    spacing = '<w:spacing w:before="%d" w:after="%d"' % (before, after)
    if para.body_line:
        spacing += ' w:line="%d" w:lineRule="auto"' % density["line"]
    properties += spacing + "/>"
    if para.right_indent:
        properties += '<w:ind w:right="%d"/>' % para.right_indent
    if para.align:
        properties += '<w:jc w:val="%s"/>' % para.align
    runs = []
    for text, bold, size, rid in para.runs:
        run = _run_xml(text, bold, size, rid is not None, family)
        runs.append('<w:hyperlink r:id="%s">%s</w:hyperlink>' % (rid, run) if rid else run)
    return "<w:p><w:pPr>%s</w:pPr>%s</w:p>" % (properties, "".join(runs))


# Package parts --------------------------------------------------------------------------------

def _package_parts(document: str, metrics: GoldMetrics, link_order: list) -> list:
    family = metrics.font_family
    content_types = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                     '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                     '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                     '<Default Extension="xml" ContentType="application/xml"/>'
                     '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
                     '<Override PartName="/word/numbering.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.numbering+xml"/>'
                     '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>'
                     '</Types>')
    root_rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                 '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                 '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
                 '</Relationships>')
    relationships = ('<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/numbering" Target="numbering.xml"/>'
                     '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>')
    for rid, url in link_order:
        relationships += ('<Relationship Id="%s" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink" Target="%s" TargetMode="External"/>'
                          % (rid, html.escape(url, quote=True)))
    document_rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                     '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">%s</Relationships>' % relationships)
    styles = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
              '<w:styles xmlns:w="%s" xmlns:r="%s"><w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="%s" w:hAnsi="%s"/>'
              '<w:sz w:val="%d"/></w:rPr></w:rPrDefault><w:pPrDefault><w:pPr><w:spacing w:after="0" w:line="240" w:lineRule="auto"/></w:pPr>'
              '</w:pPrDefault></w:docDefaults><w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/></w:style>'
              '</w:styles>') % (NS_W, NS_R, family, family, metrics.body_half_points)
    numbering = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                 '<w:numbering xmlns:w="%s" xmlns:r="%s"><w:abstractNum w:abstractNumId="0"><w:multiLevelType w:val="hybridMultilevel"/>'
                 '<w:lvl w:ilvl="0"><w:start w:val="1"/><w:numFmt w:val="bullet"/><w:lvlText w:val="•"/><w:lvlJc w:val="left"/>'
                 '<w:pPr><w:ind w:left="360" w:hanging="360"/></w:pPr><w:rPr><w:rFonts w:ascii="%s" w:hAnsi="%s" w:hint="default"/></w:rPr></w:lvl>'
                 '</w:abstractNum><w:num w:numId="1"><w:abstractNumId w:val="0"/></w:num></w:numbering>') % (NS_W, NS_R, family, family)
    return [("[Content_Types].xml", content_types), ("_rels/.rels", root_rels), ("word/_rels/document.xml.rels", document_rels),
            ("word/document.xml", document), ("word/numbering.xml", numbering), ("word/styles.xml", styles)]


def _zip_bytes(parts: list) -> bytes:
    """Byte-deterministic archive: fixed entry order, fixed 1980-01-01 timestamps, stored (uncompressed), fixed attributes."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, text in parts:
            info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_STORED
            info.create_system = 3
            info.external_attr = 0o644 << 16
            archive.writestr(info, text.encode("utf-8"))
    return buffer.getvalue()


def load_pinned_font_files(manifest: Mapping[str, Any]) -> dict:
    """The canonical runtime manifest's pinned Liberation Sans font files: {basename: (path, expected_sha256)}."""
    pinned = {}
    for root in manifest["content_binding"]["roots"]:
        path = root.get("path", "")
        if root.get("kind") == "FILE" and path.startswith("/usr/share/fonts/truetype/liberation/LiberationSans-") and path.endswith(".ttf"):
            pinned[path.rsplit("/", 1)[1]] = (path, root["expected_digest"])
    return pinned


def fonts_from_manifest(manifest: Mapping[str, Any], read_bytes) -> FontMetrics:
    """FontMetrics from the Regular and Bold font files named by the manifest, each SHA-256 verified before use."""
    pinned = load_pinned_font_files(manifest)
    faces = {}
    for name in ("LiberationSans-Regular.ttf", "LiberationSans-Bold.ttf"):
        if name not in pinned:
            raise GoldBuildError("FONT_NOT_PINNED", name)
        path, expected = pinned[name]
        data = read_bytes(path)
        if hashlib.sha256(data).hexdigest() != expected:
            raise GoldBuildError("FONT_DIGEST_MISMATCH", name)
        faces[name] = data
    return FontMetrics.from_font_bytes(faces["LiberationSans-Regular.ttf"], faces["LiberationSans-Bold.ttf"])


def load_doctrine_roster(root: Path) -> list:
    """The default evidence roster of the canonical Spy Pond Gold doctrine record."""
    record = json.loads((Path(root) / "docs" / "resume" / "BORA_SPY_POND_GOLD_REFERENCE_V1.json").read_text(encoding="utf-8"))
    return list(record["presentation_grammar"]["evidence_roster"]["default_included"])


def load_gold_metrics(root: Path) -> tuple:
    """GoldMetrics and the doctrine digests, read from the canonical records under ROOT."""
    spy_path = Path(root) / "docs" / "resume" / "BORA_SPY_POND_GOLD_REFERENCE_V1.json"
    quality_path = Path(root) / "docs" / "resume" / "BORA_GOLD_QUALITY_REFERENCE_V1.json"
    spy_bytes, quality_bytes = spy_path.read_bytes(), quality_path.read_bytes()
    digests = {"BORA_SPY_POND_GOLD_REFERENCE_V1": hashlib.sha256(spy_bytes).hexdigest(),
               "BORA_GOLD_QUALITY_REFERENCE_V1": hashlib.sha256(quality_bytes).hexdigest()}
    return GoldMetrics.from_doctrine(json.loads(spy_bytes.decode("utf-8"))), digests
