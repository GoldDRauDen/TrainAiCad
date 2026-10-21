"""Trace an exporter/guard error message back to the `if` condition that raised it.

The pinned repository's tools/*.py are parsed (never executed). Every `fail("...")` call
and every `out.append("CODE")` becomes a message pattern plus the condition guarding it, so
the model is told exactly which fields must change instead of guessing.
"""
from __future__ import annotations

import ast
import re
from dataclasses import dataclass

MIN_LITERAL = 12
MAX_PER_SEGMENT = 3
MAX_ADVICE = 6
MAX_CONDITION = 500
_PREFIX = re.compile(r"^(?:ValueError:\s*)?(?:(?:canonical|export|geometry):\s*)?")


@dataclass(frozen=True)
class Gate:
    where: str
    pattern: re.Pattern
    literal: int
    condition: str


def summarize_error(error):
    """Keep the one line that explains a failure; a Python traceback is mostly noise."""
    text = str(error).strip()
    if "Traceback (most recent call last)" in text:
        text = text.splitlines()[-1].strip()
    return text


def _message(node):
    """(regex source, literal text) for a str / f-string / `+` concatenation, else None."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return re.escape(node.value), node.value
    if isinstance(node, ast.JoinedStr):
        pattern, literal = [], []
        for part in node.values:
            if isinstance(part, ast.Constant):
                pattern.append(re.escape(part.value))
                literal.append(part.value)
            else:
                pattern.append(".+?")
        return "".join(pattern), "".join(literal)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left, right = _message(node.left), _message(node.right)
        if left and right:
            return left[0] + right[0], left[1] + right[1]
    return None


def _condition(parents, node):
    child = node
    while child in parents:
        parent = parents[child]
        if isinstance(parent, ast.If):
            test = ast.unparse(parent.test)
            text = test if any(child is stmt for stmt in parent.body) else f"not ({test})"
            return text[:MAX_CONDITION]
        child = parent
    return None


def _is_sink(call):
    if isinstance(call.func, ast.Name) and call.func.id == "fail":
        return "fail"
    if isinstance(call.func, ast.Attribute) and call.func.attr == "append":
        return "append"
    return None


class GateIndex:
    def __init__(self, gates):
        self.gates = list(gates)

    @classmethod
    def from_sources(cls, sources):
        gates, seen = [], set()
        for name, text in sorted(sources.items()):
            try:
                tree = ast.parse(text)
            except SyntaxError:
                continue
            parents = {child: parent for parent in ast.walk(tree) for child in ast.iter_child_nodes(parent)}
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call) or not node.args or _is_sink(node) is None:
                    continue
                message = _message(node.args[0])
                if message is None:
                    continue
                pattern, literal = message
                if _is_sink(node) == "append" and not re.search(r"[A-Z][A-Z_]{7,}", literal):
                    continue
                condition = _condition(parents, node)
                if condition is None or len(literal.strip()) < MIN_LITERAL:
                    continue
                key = (pattern, condition)
                if key in seen:
                    continue
                seen.add(key)
                try:
                    compiled = re.compile(pattern, re.S)
                except re.error:
                    continue
                gates.append(Gate(f"{name}:{node.lineno}", compiled, len(literal), condition))
        return cls(gates)

    @classmethod
    def from_repo(cls, repo):
        return cls.from_sources({name: repo.read(name) for name in repo.hashes
                                 if name.startswith("tools/") and name.endswith(".py")})

    def advise(self, error):
        advice, seen = [], set()
        for segment in _segments(error):
            hits = sorted((g for g in self.gates if g.pattern.search(segment)), key=lambda g: -g.literal)
            for gate in hits[:MAX_PER_SEGMENT]:
                if (gate.where, gate.condition) not in seen:
                    seen.add((gate.where, gate.condition))
                    advice.append({"gate": gate.where, "fires_when": gate.condition})
        return advice[:MAX_ADVICE]


def _segments(error):
    text = summarize_error(error)
    return [_PREFIX.sub("", piece.strip(), count=1) for piece in text.split(" | ") if piece.strip()]


def describe_failure(error, index):
    """One line for the next attempt: the failure plus the condition(s) that produced it."""
    summary = summarize_error(error)
    advice = index.advise(summary) if index is not None else []
    if not advice:
        return summary
    return summary + " || " + " ; ".join(f"{a['gate']} fires when {a['fires_when']}" for a in advice)
