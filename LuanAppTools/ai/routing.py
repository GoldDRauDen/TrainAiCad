"""Operational model selection; engineering classification remains source-grounded."""

from LuanAppTools.core.settings import DEFAULT_MODELS


def route_model(code, attempt, issues=(), models=None):
    models = models or DEFAULT_MODELS
    difficulty = code.get("difficulty", "hard")
    if difficulty not in ("easy", "medium", "hard") or not code.get(
        "difficulty_evidence"
    ):
        difficulty = "hard"
    if attempt == 1:
        return dict(models[difficulty])
    # A single retry: never Haiku -> Sonnet -> Opus as three solves.
    if difficulty == "hard" and issues:
        return dict(models["exceptional"])
    return {
        "model": models["medium"]["model"],
        "effort": "high" if difficulty == "easy" else "max",
    }


def independent_groups(codes):
    """At most three explicitly independent easy codes; all others stand alone."""
    groups = []
    easy = []
    for code in codes:
        if (
            code.get("difficulty") == "easy"
            and code.get("independent") is True
            and not code.get("data_ids")
        ):
            easy.append(code)
            if len(easy) == 3:
                groups.append(easy)
                easy = []
        else:
            if easy:
                groups.append(easy)
                easy = []
            groups.append([code])
    if easy:
        groups.append(easy)
    return groups
