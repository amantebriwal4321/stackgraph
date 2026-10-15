"""Turn query rows into an answer. Every sentence has to come from those rows."""

from __future__ import annotations


def _score(value) -> str:
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def _missing(name: str) -> str:
    return (
        f"No tool named {name} is in the ecosystem graph. "
        "The corpus is the committed seed of public npm and PyPI packages."
    )


def alternatives(name: str, rows: list[dict], signal_rows: list[dict], community: tuple | None) -> str:
    if not rows:
        return f"The graph has no ALTERNATIVE_TO edges from {name}."
    parts = [f"Alternatives stored on ALTERNATIVE_TO edges from {name}:"]
    for row in rows:
        maintainer = row.get("maintainer") or "unknown maintainer"
        handle = row.get("handle") or ""
        handle_bit = f" ({handle})" if handle else ""
        reason = row.get("reason") or "no reason recorded"
        categories = ", ".join(row.get("categories") or []) or "no category"
        parts.append(
            f"{row['name']} [{row.get('ecosystem')}], maintainer {maintainer}{handle_bit}, "
            f"category {categories}. Edge reason: {reason}."
        )
    text = " ".join(parts)
    text += " " + _signal_sentence(name, signal_rows)
    if community and community[0] is not None:
        cid, members = community
        shown = ", ".join(members[:12]) if members else "no other tool"
        text += (
            f" Label propagation on ALTERNATIVE_TO puts {name} in community {cid} with {shown}."
        )
    return text.strip()


def impact(name: str, count_rows: list[dict], paths: list[dict], signal_rows: list[dict], scout: dict | None) -> str:
    if not count_rows:
        return _missing(name)
    dependents = count_rows[0].get("dependents") or 0
    names = []
    for path in paths:
        nodes = path.get("nodes") or []
        if nodes:
            starter = nodes[0].get("name")
            if starter and starter != name and starter not in names:
                names.append(starter)
    noun = "tool reaches" if int(dependents or 0) == 1 else "tools reach"
    if not names:
        body = (
            f"No tool in this corpus reaches {name} by a DEPENDS_ON path of 1 to 3 hops. "
            f"Dependent count from the graph: {dependents}."
        )
    else:
        body = (
            f"{dependents} {noun} {name} by a DEPENDS_ON path of 1 to 3 hops: "
            + ", ".join(names)
            + "."
        )
    body += " " + _signal_sentence(name, signal_rows)
    if scout and scout.get("ts"):
        body += (
            f" Scout last wrote {scout.get('signals_written')} blast radius signal(s) at {scout.get('ts')}."
        )
    return body.strip()


def path_answer(from_name: str, to_name: str, paths: list[dict], error: str = "") -> str:
    if error:
        return f"The shortest path query failed: {error}"
    if not paths:
        return (
            f"No path of DEPENDS_ON or ALTERNATIVE_TO edges (up to 8 hops) connects {from_name} to {to_name}."
        )
    path = paths[0]
    nodes = [node.get("name") or "?" for node in path.get("nodes") or []]
    edges = path.get("edges") or []
    steps = []
    for index, node in enumerate(nodes):
        steps.append(node)
        if index < len(edges):
            edge = edges[index]
            label = edge.get("type") or "EDGE"
            kind = (edge.get("properties") or {}).get("kind")
            if kind:
                label = f"{label} ({kind})"
            steps.append(f"-{label}->")
    return "Shortest path: " + " ".join(steps) + "."


def critical(rows: list[dict], algorithm: str) -> str:
    if not rows:
        return "The centrality query returned no tools."
    bits = [f"{row.get('name')} ({_score(row.get('score'))})" for row in rows[:8]]
    if algorithm == "pagerank":
        lead = (
            "PageRank on Tool nodes, following DEPENDS_ON edges. "
            "A higher score means more rank flowed toward that tool across dependency edges. "
        )
    else:
        lead = (
            "PageRank was not available, so this is in-degree on DEPENDS_ON: "
            "how many tools list that tool as a direct dependency. "
        )
    return lead + "Top of this graph: " + ", ".join(bits) + "."


def maintainers(name: str, rows: list[dict], from_memory: bool) -> str:
    if not rows:
        return _missing(name)
    lead = f"Maintainers for {name} and tools it DEPENDS_ON within 2 hops."
    if from_memory:
        lead = (
            f"Starting point {name} came from the user memory graph. "
            "Maintainers for that tool and tools it DEPENDS_ON within 2 hops."
        )
    lines = [lead]
    for row in rows:
        who = row.get("maintainer") or "no maintainer node"
        handle = row.get("handle") or ""
        handle_bit = f" (handle {handle})" if handle else ""
        lines.append(f"{row.get('name')} [{row.get('ecosystem')}] is maintained by {who}{handle_bit}.")
    return " ".join(lines)


def signals_answer(name: str, rows: list[dict]) -> str:
    if not rows:
        return f"No Signal nodes point at {name}."
    return _signal_sentence(name, rows)


def about(name: str, profile_rows: list[dict], dep_rows: list[dict], alt_rows: list[dict], signal_rows: list[dict]) -> str:
    if not profile_rows or not profile_rows[0].get("name"):
        return _missing(name)
    row = profile_rows[0]
    categories = row.get("categories") or []
    if isinstance(categories, str):
        categories = [categories]
    bits = [
        f"{row['name']} is a {row.get('ecosystem')} package in the corpus.",
        f"Summary from the registry snapshot: {row.get('summary') or 'none stored'}.",
        f"Version {row.get('version') or 'unknown'}, license {row.get('license') or 'not recorded'}.",
        f"Maintainer {row.get('maintainer') or 'unknown'} ({row.get('handle') or 'no handle'}).",
        "Categories: " + (", ".join(c for c in categories if c) or "none") + ".",
    ]
    if dep_rows:
        deps = ", ".join(f"{item['name']} ({item.get('kind')})" for item in dep_rows)
        bits.append(f"Direct DEPENDS_ON edges: {deps}.")
    else:
        bits.append("No direct DEPENDS_ON edges to other tools in this corpus.")
    if alt_rows:
        bits.append("Alternatives: " + ", ".join(item["name"] for item in alt_rows) + ".")
    bits.append(_signal_sentence(name, signal_rows))
    return " ".join(bits)


def memory_write(writes: list[tuple[str, str, str]]) -> str:
    if not writes:
        return "No corpus tool name was found in that memory statement, so nothing was written."
    bits = []
    for relation, tool, note in writes:
        extra = f" ({note})" if note else ""
        bits.append(f"{relation} {tool}{extra}")
    return "Saved in the user memory graph: " + "; ".join(bits) + "."


def recall(pref_rows: list[dict], history_rows: list[dict], mode: str) -> str:
    parts = []
    if mode in {"prefs", "both"}:
        if not pref_rows:
            parts.append("No PREFERS or USES edges are stored for this user.")
        else:
            bits = []
            for row in pref_rows:
                note = f" ({row['note']})" if row.get("note") else ""
                bits.append(f"{row.get('rel')} {row.get('tool')}{note}")
            parts.append("Memory graph edges: " + "; ".join(bits) + ".")
    if mode in {"history", "both"}:
        if not history_rows:
            parts.append("No earlier questions are stored for this user.")
        else:
            recent = history_rows[0]
            parts.append(
                f"Most recent stored question at {recent.get('ts')}: {recent.get('question')}"
            )
    return " ".join(parts)


def community(name: str, cid, members: list[str]) -> str:
    if cid is None:
        return f"{name} was not in the label propagation result."
    shown = ", ".join(members) if members else "no other tool"
    return f"Label propagation on ALTERNATIVE_TO puts {name} in community {cid} with {shown}."


def help_text(counts: dict | None) -> str:
    count_bit = ""
    if counts:
        count_bit = (
            f" The ecosystem graph currently has {counts.get('tools', 0)} tools, "
            f"{counts.get('depends_on', 0)} DEPENDS_ON edges, "
            f"{counts.get('alternative_to', 0)} ALTERNATIVE_TO edges, "
            f"and {counts.get('signals', 0)} signals."
        )
    return (
        "Ask about alternatives, what depends on a tool, a path between two tools, "
        "who maintains a tool and its dependencies, or which tool PageRank marks as critical. "
        "Say what you use or prefer and a later question can read it back from your memory graph."
        + count_bit
    )


def _signal_sentence(name: str, rows: list[dict]) -> str:
    if not rows:
        return f"No signals are stored on {name}."
    bits = []
    for row in rows:
        agent = row.get("agent") or row.get("origin") or "unknown"
        bits.append(
            f"{row.get('kind')} from {agent} (source {row.get('source')}, score {_score(row.get('score'))}): "
            f"{row.get('detail')}"
        )
    text = "Signals on " + name + ": " + " | ".join(bits)
    if not text.endswith("."):
        text += "."
    return text
