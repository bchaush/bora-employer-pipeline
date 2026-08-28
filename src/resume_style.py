"""Deterministic résumé prose style checks (voice, filler, punctuation)."""

from __future__ import annotations

import re
from typing import Any


EM_DASH_PATTERN = re.compile(r"\u2014|(?<=\w)--(?=\w)")

AI_FILLER_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bspearheaded\b", re.I),
    re.compile(r"\borchestrated\b", re.I),
    re.compile(r"\brevolutionized\b", re.I),
    re.compile(r"\btransformed\b", re.I),
    re.compile(r"\bchampioned\b", re.I),
    re.compile(r"\bleveraged\b", re.I),
    re.compile(r"\bpioneered\b", re.I),
    re.compile(r"\bresults[- ]driven\b", re.I),
    re.compile(r"\bdynamic professional\b", re.I),
    re.compile(r"\bproven track record\b", re.I),
    re.compile(r"\bcutting[- ]edge\b", re.I),
    re.compile(r"\bseamless\b", re.I),
    re.compile(r"\binnovative solutions\b", re.I),
    re.compile(r"\brobust ecosystem\b", re.I),
    re.compile(r"\bholistic\b", re.I),
    re.compile(r"\bbest[- ]in[- ]class\b", re.I),
)


def _warning(code: str, **fields: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {"code": code}
    payload.update(fields)
    return payload


def validate_resume_prose_style(text: str, *, context: str | None = None) -> dict[str, Any]:
    """Return style violations for résumé prose. Warnings, not silent fixes."""
    warnings: list[dict[str, Any]] = []
    if not isinstance(text, str) or not text.strip():
        return {"valid": True, "warnings": warnings}

    if EM_DASH_PATTERN.search(text):
        warnings.append(
            _warning(
                "RESUME_STYLE_EM_DASH",
                context=context,
                detail="résumé prose should not use em dashes",
            )
        )

    for pattern in AI_FILLER_PATTERNS:
        match = pattern.search(text)
        if match:
            warnings.append(
                _warning(
                    "RESUME_STYLE_AI_FILLER",
                    context=context,
                    matched=match.group(0),
                    detail="generic inflated résumé phrasing detected",
                )
            )

    if text.count(";") >= 2:
        warnings.append(
            _warning(
                "RESUME_STYLE_EXCESS_SEMICOLONS",
                context=context,
                detail="avoid excessive semicolons in résumé prose",
            )
        )

    return {"valid": len(warnings) == 0, "warnings": warnings}


def validate_modules_style(modules: list[dict[str, Any]]) -> dict[str, Any]:
    warnings: list[dict[str, Any]] = []
    for module in modules:
        wording = module.get("wording")
        if isinstance(wording, str):
            result = validate_resume_prose_style(
                wording, context=str(module.get("module_id"))
            )
            warnings.extend(result.get("warnings", []))
    return {"valid": len(warnings) == 0, "warnings": warnings}
