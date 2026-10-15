"""Rule based intent router used when no model key is configured."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

EXAMPLES = [
    "What should I use instead of moment?",
    "What breaks if express is deprecated?",
    "Who maintains the libraries that next depends on?",
    "Show the path from next to react",
    "Which dependency is most critical in this graph?",
    "I use next and I prefer zod over yup",
    "What do I prefer?",
]

_NAME_CHARS = set("abcdefghijklmnopqrstuvwxyz0123456789@/_.-")


@dataclass
class Plan:
    intent: str
    names: list[str] = field(default_factory=list)
    writes: list[tuple[str, str, str]] = field(default_factory=list)
    recall: str = "both"


def alias_index(rows: list[dict]) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for row in rows:
        name = row.get("name")
        if not name:
            continue
        pairs.append((str(name).lower(), name))
        aliases = row.get("aliases") or []
        if isinstance(aliases, str):
            aliases = [aliases]
        for alias in aliases:
            if alias:
                pairs.append((str(alias).lower(), name))
    pairs.sort(key=lambda item: len(item[0]), reverse=True)
    return pairs


def mentions(text: str, index: list[tuple[str, str]]) -> list[str]:
    hay = text.lower()
    occupied = [False] * len(hay)
    found_at: list[tuple[int, str]] = []
    for alias, canonical in index:
        start = 0
        while True:
            at = hay.find(alias, start)
            if at < 0:
                break
            end = at + len(alias)
            before_ok = at == 0 or hay[at - 1] not in _NAME_CHARS
            after_ok = end == len(hay) or hay[end] not in _NAME_CHARS
            if before_ok and after_ok and not any(occupied[at:end]):
                for pos in range(at, end):
                    occupied[pos] = True
                found_at.append((at, canonical))
            start = at + 1
    found_at.sort()
    ordered: list[str] = []
    for _pos, name in found_at:
        if name not in ordered:
            ordered.append(name)
    return ordered


def memory_writes(question: str, index: list[tuple[str, str]]) -> list[tuple[str, str, str]]:
    writes: list[tuple[str, str, str]] = []
    for clause in re.split(r"\band\b", question, flags=re.IGNORECASE):
        found = mentions(clause, index)
        lower = clause.lower()
        if "prefer" in lower and found:
            note = f"over {found[1]}" if " over " in lower and len(found) > 1 else ""
            writes.append(("PREFERS", found[0], note))
        elif re.search(r"\buse\b", lower) and found:
            for name in found:
                writes.append(("USES", name, ""))
    return writes


def classify(question: str, index: list[tuple[str, str]]) -> Plan:
    text = question.strip()
    lower = text.lower()
    names = mentions(text, index)

    if any(
        phrase in lower
        for phrase in (
            "what do i prefer",
            "what did i ask",
            "what do i use",
            "my preference",
            "what do you remember",
            "my stack",
            "what have i asked",
        )
    ):
        if any(phrase in lower for phrase in ("what do i prefer", "my preference")):
            recall = "prefs"
        elif any(phrase in lower for phrase in ("what did i ask", "what have i asked", "last")):
            recall = "history"
        else:
            recall = "both"
        return Plan(intent="recall", names=names, recall=recall)

    question_like = "?" in lower or lower.startswith(
        ("what ", "who ", "which ", "show ", "how ", "where ")
    )
    if not question_like and any(phrase in lower for phrase in ("i prefer", "i use", "we use", "remember that")):
        return Plan(intent="memory_write", names=names, writes=memory_writes(text, index))

    if "path" in lower or "how is" in lower and "connected" in lower:
        return Plan(intent="path", names=names)

    if any(phrase in lower for phrase in ("most critical", "page rank", "pagerank", "centrality", "most important")):
        return Plan(intent="critical", names=names)

    if any(phrase in lower for phrase in ("who maintains", "maintainer", "maintainers")):
        return Plan(intent="maintainers", names=names)

    if any(phrase in lower for phrase in ("what breaks", "blast radius", "who depends", "dependents")):
        return Plan(intent="impact", names=names)

    if any(phrase in lower for phrase in ("instead of", "alternative", "replace", "swap")):
        return Plan(intent="alternatives", names=names)

    if any(phrase in lower for phrase in ("cluster", "community", "sit with")):
        return Plan(intent="community", names=names)

    if any(phrase in lower for phrase in ("signal", "legacy", "deprecated", "health of")):
        return Plan(intent="signals", names=names)

    if names:
        return Plan(intent="about", names=names)
    return Plan(intent="help", names=[])
