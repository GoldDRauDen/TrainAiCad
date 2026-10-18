"""A part may fall back to VIEWS_ONLY only after a real flat attempt when printed arithmetic closes.

The repository's HOLISTIC_ENGINEERING_CHALLENGE section 3 treats printed or handwritten flat arithmetic that
closes a part dimension, followed by a direct downgrade to VIEWS_ONLY, as an anomaly that reopens the source.
This module checks, from the dimensions the intake recorded per view and from the host tool history, whether
that situation exists and whether the model has since tried (and failed) to build the flat. It can only reject
a VIEWS_ONLY; it never creates or relaxes a PASS.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass
from itertools import combinations
from typing import Sequence

from .contract import FLAT_ARITHMETIC

TOLERANCE = 0.005  # printed arithmetic and dimension matching (two decimals)
EXTENT_TOLERANCE = 0.011  # the repository's bend-closure tolerance (tools/holistic_engineering_guard.py)

_TERM = re.compile(r"([+\-−–]?)\s*(\d+(?:\.\d+)?)")
_GATE_TOKEN = re.compile(r"[A-Z][A-Z0-9]*(?:_[A-Z0-9]+){2,}")


@dataclass(frozen=True)
class Equation:
    note_id: str
    text: str
    positive: tuple[float, ...]
    negative: tuple[float, ...]
    result: float


@dataclass(frozen=True)
class ClosedEquation:
    equation: Equation
    matches: tuple[str, ...]


@dataclass(frozen=True)
class Attempt:
    failed: bool
    gate: str | None
    extents: tuple[float, float] | None


class ViewsOnlyRejected(ValueError):
    pass


def _number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        return None
    return float(value)


def _positive_number(value):
    number = _number(value)
    return number if number is not None and number > 0 else None


def _text(value):
    return format(value, "g")


def parse_equations(note_id: str, text: str) -> list[Equation]:
    equations = []
    for found in FLAT_ARITHMETIC.finditer(str(text)):
        left, right = found.group(0).split("=")
        positive, negative = [], []
        for sign, digits in _TERM.findall(left):
            (negative if sign in ("-", "−", "–") else positive).append(float(digits))
        result = float(right)
        if abs(sum(positive) - sum(negative) - result) < TOLERANCE:
            equations.append(Equation(note_id, found.group(0), tuple(positive), tuple(negative), result))
    return equations


def _match_term(term, dimensions, thickness):
    if any(abs(d - term) < TOLERANCE for d in dimensions):
        return _text(term)
    for a, b in combinations(dimensions, 2):
        if abs(a + b - term) < TOLERANCE:
            return f"{_text(term)}={_text(max(a, b))}+{_text(min(a, b))}"
    if thickness is not None:
        for d in dimensions:
            if abs(d + thickness - term) < TOLERANCE:
                return f"{_text(term)}={_text(d)}+t"
            if abs(d - thickness - term) < TOLERANCE:
                return f"{_text(term)}={_text(d)}-t"
    return None


def match_terms(positive: Sequence[float], dimensions: Sequence[float], thickness) -> tuple[str, ...] | None:
    """How each printed term is explained by the printed dimensions, or None when any term is not."""
    known = [n for n in (_number(d) for d in dimensions) if n is not None]
    t = _positive_number(thickness)
    matches = []
    for term in positive:
        found = _match_term(float(term), known, t)
        if found is None:
            return None
        matches.append(found)
    return tuple(matches)


def closed_equations(notes: Sequence[dict], views: Sequence[dict], thickness) -> list[ClosedEquation]:
    dimensions = [d for view in views for d in (view.get("dimensions") or [])]
    closed = []
    for note in notes:
        for equation in parse_equations(str(note.get("id", "")), note.get("text", "")):
            matches = match_terms(equation.positive, dimensions, thickness)
            if matches is not None:
                closed.append(ClosedEquation(equation, matches))
    return closed


def _gate_name(result):
    gates = result.get("gates")
    if isinstance(gates, list):
        for gate in gates:
            if isinstance(gate, dict) and isinstance(gate.get("gate"), str) and gate["gate"]:
                return gate["gate"]
    token = _GATE_TOKEN.search(str(result.get("error", "")))
    return token.group(0) if token else None


def _extents(part):
    for entity in part.get("entities") or []:
        if isinstance(entity, dict) and entity.get("role") == "outer" and entity.get("type") == "LWPOLYLINE":
            points = [v for v in entity.get("vertices") or [] if isinstance(v, (list, tuple)) and len(v) >= 2]
            xs = [n for n in (_number(v[0]) for v in points) if n is not None]
            ys = [n for n in (_number(v[1]) for v in points) if n is not None]
            if len(xs) >= 2 and len(ys) >= 2:
                return (max(xs) - min(xs), max(ys) - min(ys))
            return None
    return None


def attempt_log(history: Sequence[dict]) -> list[Attempt]:
    """One entry per validate call of a part that is not VIEWS_ONLY (a flat the model tried to build)."""
    attempts = []
    for entry in history:
        request = entry.get("request") or {}
        part = (request.get("arguments") or {}).get("part")
        if request.get("name") != "validate" or not isinstance(part, dict) or part.get("status") == "VIEWS_ONLY":
            continue
        result = entry.get("result") or {}
        failed = "error" in result
        attempts.append(Attempt(failed, _gate_name(result) if failed else None, _extents(part)))
    return attempts


def _message(closed):
    printed = "; ".join(f"{c.equation.text} [{', '.join(c.matches)}]" for c in closed)
    results = ", ".join(_text(c.equation.result) for c in closed)
    return (
        f"VIEWS_ONLY_ADMISSION: printed flat arithmetic closes against this code's views ({printed}) but no flat "
        f"attempt that failed a named repository gate and reproduces {results} was validated. "
        "HOLISTIC_ENGINEERING_CHALLENGE §3 reopens the source when printed flat arithmetic closes; §7 keeps a "
        "local uncertainty local. Build the flat (status PASS, or PREVIEW with a FLAG for what is unproved) and "
        "validate it; submit VIEWS_ONLY only if that attempt fails a named gate and its outer extent reproduces the "
        "printed result. When a flat attempt already passed validate, submit that flat instead."
    )


def admit_views_only(part: dict, closed: Sequence[ClosedEquation], attempts: Sequence[Attempt]) -> None:
    if part.get("status") != "VIEWS_ONLY" or not closed:
        return
    results = [c.equation.result for c in closed]
    for attempt in attempts:
        if (attempt.failed and attempt.gate and attempt.extents and
                any(abs(extent - result) < EXTENT_TOLERANCE for extent in attempt.extents for result in results)):
            return
    raise ViewsOnlyRejected(_message(closed))


@dataclass(frozen=True)
class ClosureContext:
    notes: tuple[dict, ...]
    views: tuple[dict, ...]

    def admit(self, part: dict, history: Sequence[dict]) -> None:
        closed = closed_equations(self.notes, self.views, part.get("thickness_mm"))
        admit_views_only(part, closed, attempt_log(history))
