"""Run the documented Cypher and shape rows plus paths for the advisor."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.graph import cypher
from app.graph.serialize import paths_from_result, rows_from_result


@dataclass
class Call:
    graph: str
    query: str
    params: dict
    rows: list[dict] = field(default_factory=list)
    paths: list[dict] = field(default_factory=list)
    error: str = ""

    def public(self) -> dict:
        data = {
            "graph": self.graph,
            "query": self.query,
            "params": self.params,
            "rendered": render(self.query, self.params),
        }
        if self.error:
            data["error"] = self.error
        return data


def literal(value) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return str(value)
    if isinstance(value, str):
        return "'" + value.replace("\\", "\\\\").replace("'", "\\'") + "'"
    if isinstance(value, (list, tuple)):
        return "[" + ", ".join(literal(item) for item in value) + "]"
    if isinstance(value, dict):
        body = ", ".join(f"{key}: {literal(item)}" for key, item in value.items())
        return "{" + body + "}"
    return literal(str(value))


def render(query: str, params: dict) -> str:
    rendered = query
    for key in sorted(params, key=len, reverse=True):
        rendered = rendered.replace(f"${key}", literal(params[key]))
    return rendered


def _call(graph, graph_name: str, query: str, params: dict | None = None, path_label: str = "") -> Call:
    params = params or {}
    try:
        result = graph.query(query, params)
    except Exception as exc:  # noqa: BLE001 - caller decides if this query is optional
        return Call(graph=graph_name, query=query, params=params, error=str(exc))
    return Call(
        graph=graph_name,
        query=query,
        params=params,
        rows=rows_from_result(result),
        paths=paths_from_result(result, path_label),
    )


def tool_directory(graph, graph_name: str) -> Call:
    return _call(graph, graph_name, cypher.TOOL_NAMES)


def alternatives(graph, graph_name: str, name: str) -> Call:
    call = _call(graph, graph_name, cypher.ALTERNATIVES, {"name": name})
    grouped: dict[str, dict] = {}
    for row in call.rows:
        if not row.get("name"):
            continue
        item = grouped.setdefault(
            row["name"],
            {
                "id": row.get("id"),
                "name": row.get("name"),
                "ecosystem": row.get("ecosystem"),
                "summary": row.get("summary") or "",
                "reason": row.get("reason") or "",
                "maintainer": row.get("maintainer") or "",
                "handle": row.get("handle") or "",
                "categories": [],
            },
        )
        category = row.get("category")
        if category and category not in item["categories"]:
            item["categories"].append(category)
    call.rows = list(grouped.values())
    call.paths = [
        {
            "label": f"{name} alternative {item['name']}",
            "nodes": [
                {"id": f"name:{name}", "labels": ["Tool"], "name": name, "properties": {}},
                {
                    "id": item["id"],
                    "labels": ["Tool"],
                    "name": item["name"],
                    "properties": {"ecosystem": item["ecosystem"]},
                },
            ],
            "edges": [
                {
                    "type": "ALTERNATIVE_TO",
                    "from": f"name:{name}",
                    "to": item["id"],
                    "properties": {"reason": item["reason"]},
                    "forward": True,
                }
            ],
        }
        for item in call.rows
    ]
    return call


def blast(graph, graph_name: str, name: str) -> tuple[Call, Call]:
    paths = _call(graph, graph_name, cypher.BLAST_PATHS, {"name": name}, path_label=f"depends on {name}")
    count = _call(graph, graph_name, cypher.BLAST_COUNT, {"name": name})
    return paths, count


def signals(graph, graph_name: str, name: str) -> Call:
    call = _call(graph, graph_name, cypher.SIGNALS, {"name": name})
    call.paths = []
    for row in call.rows:
        call.paths.append(
            {
                "label": f"{row.get('kind')} signal on {name}",
                "nodes": [
                    {
                        "id": row.get("id"),
                        "labels": ["Signal"],
                        "name": row.get("kind") or "signal",
                        "properties": {"source": row.get("source"), "score": row.get("score")},
                    },
                    {"id": f"name:{name}", "labels": ["Tool"], "name": name, "properties": {}},
                ],
                "edges": [
                    {
                        "type": "ABOUT",
                        "from": row.get("id"),
                        "to": f"name:{name}",
                        "properties": {},
                        "forward": True,
                    }
                ],
            }
        )
    return call


def shortest_path(graph, graph_name: str, from_name: str, to_name: str) -> Call:
    call = _call(
        graph,
        graph_name,
        cypher.SHORTEST_PATH,
        {"from_name": from_name, "to_name": to_name},
        path_label=f"{from_name} to {to_name}",
    )
    if call.error or not call.paths:
        directed = _call(
            graph,
            graph_name,
            cypher.SHORTEST_PATH_DEPENDS,
            {"from_name": from_name, "to_name": to_name},
            path_label=f"{from_name} to {to_name}",
        )
        if not directed.error:
            return directed
    return call


def page_rank(graph, graph_name: str) -> Call:
    call = _call(graph, graph_name, cypher.PAGERANK)
    if call.error:
        call = _call(graph, graph_name, cypher.DEGREE)
        call.paths = [
            {
                "label": "in degree along DEPENDS_ON, used because PageRank failed",
                "nodes": [
                    {
                        "id": row.get("id"),
                        "labels": ["Tool"],
                        "name": row.get("name"),
                        "properties": {"score": row.get("score"), "ecosystem": row.get("ecosystem")},
                    }
                    for row in call.rows
                ],
                "edges": [],
            }
        ]
        return call
    call.paths = [
        {
            "label": "PageRank order on DEPENDS_ON",
            "nodes": [
                {
                    "id": row.get("id"),
                    "labels": ["Tool"],
                    "name": row.get("name"),
                    "properties": {"score": row.get("score"), "ecosystem": row.get("ecosystem")},
                }
                for row in call.rows
            ],
            "edges": [],
        }
    ]
    return call


def communities(graph, graph_name: str) -> Call:
    return _call(graph, graph_name, cypher.LABEL_PROPAGATION)


def maintainers(graph, graph_name: str, name: str) -> Call:
    call = _call(graph, graph_name, cypher.MAINTAINERS, {"name": name})
    if call.error:
        # List concatenation is the piece most likely to differ between builds.
        fallback = """
        MATCH (root:Tool {name: $name})
        OPTIONAL MATCH (root)-[:DEPENDS_ON*1..2]->(dep:Tool)
        WITH collect(DISTINCT root) + collect(DISTINCT dep) AS tools
        UNWIND tools AS t
        OPTIONAL MATCH (m:Maintainer)-[:MAINTAINS]->(t)
        RETURN DISTINCT t.id AS id, t.name AS name, t.ecosystem AS ecosystem,
               m.name AS maintainer, m.handle AS handle, m.url AS url
        ORDER BY t.name
        """.strip()
        call = _call(graph, graph_name, fallback, {"name": name})
    seen = []
    paths_nodes = []
    for row in call.rows:
        if row.get("name") and row["name"] not in seen:
            seen.append(row["name"])
            paths_nodes.append(
                {
                    "id": row.get("id"),
                    "labels": ["Tool"],
                    "name": row.get("name"),
                    "properties": {
                        "maintainer": row.get("maintainer"),
                        "handle": row.get("handle"),
                        "ecosystem": row.get("ecosystem"),
                    },
                }
            )
    call.paths = [{"label": f"maintainers reachable from {name}", "nodes": paths_nodes, "edges": []}]
    return call


def direct_deps(graph, graph_name: str, name: str) -> Call:
    return _call(graph, graph_name, cypher.DIRECT_DEPS, {"name": name})


def profile(graph, graph_name: str, name: str) -> Call:
    return _call(graph, graph_name, cypher.TOOL_PROFILE, {"name": name})


def overview(graph, graph_name: str) -> Call:
    return _call(graph, graph_name, cypher.OVERVIEW)


def scout_status(graph, graph_name: str) -> Call:
    return _call(graph, graph_name, cypher.SCOUT_RUNS)


def recall_prefs(graph, graph_name: str, user: str) -> Call:
    call = _call(graph, graph_name, cypher.RECALL_PREFS, {"user": user})
    call.paths = [
        {
            "label": f"{user} {row.get('rel')} {row.get('tool')}",
            "nodes": [
                {"id": f"user:{user}", "labels": ["User"], "name": user, "properties": {}},
                {"id": f"tool:{row.get('tool')}", "labels": ["Tool"], "name": row.get("tool"), "properties": {}},
            ],
            "edges": [
                {
                    "type": row.get("rel") or "PREFERS",
                    "from": f"user:{user}",
                    "to": f"tool:{row.get('tool')}",
                    "properties": {"note": row.get("note") or ""},
                    "forward": True,
                }
            ],
        }
        for row in call.rows
        if row.get("tool")
    ]
    return call


def recall_history(graph, graph_name: str, user: str) -> Call:
    return _call(graph, graph_name, cypher.RECALL_HISTORY, {"user": user})
