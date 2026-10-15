"""Turn FalkorDB nodes, edges, and paths into JSON the UI can draw."""

from __future__ import annotations

from falkordb.edge import Edge
from falkordb.node import Node
from falkordb.path import Path


def _props(value) -> dict:
    if not value:
        return {}
    out = {}
    for key, item in dict(value).items():
        out[str(key)] = _plain(item)
    return out


def _plain(value):
    if isinstance(value, Node):
        return node_dict(value)
    if isinstance(value, Edge):
        return edge_dict(value)
    if isinstance(value, Path):
        return path_dict(value)["nodes"]
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def node_dict(node: Node) -> dict:
    props = _props(node.properties)
    labels = list(node.labels or [])
    name = props.get("name") or props.get("id") or ""
    node_id = props.get("id") or f"{labels[0] if labels else 'node'}:{node.id}"
    return {
        "id": str(node_id),
        "internal_id": node.id,
        "labels": labels,
        "name": name,
        "properties": props,
    }


def edge_dict(edge: Edge, source: dict | None = None, target: dict | None = None) -> dict:
    return {
        "type": edge.relation,
        "from": None if source is None else source["id"],
        "to": None if target is None else target["id"],
        "properties": _props(edge.properties),
    }


def path_dict(path: Path, label: str = "") -> dict:
    nodes = [node_dict(node) for node in path.nodes()]
    edges = []
    raw_edges = path.edges()
    for index, edge in enumerate(raw_edges):
        left = nodes[index]
        right = nodes[index + 1] if index + 1 < len(nodes) else None
        src_id = edge.src_node.id if isinstance(edge.src_node, Node) else edge.src_node
        forward = left.get("internal_id") == src_id
        if forward:
            source, target = left, right
        else:
            source, target = right, left
        edges.append(
            {
                "type": edge.relation,
                "from": None if source is None else source["id"],
                "to": None if target is None else target["id"],
                "properties": _props(edge.properties),
                "forward": forward,
            }
        )
    for node in nodes:
        node.pop("internal_id", None)
    return {"label": label, "nodes": nodes, "edges": edges}


def rows_from_result(result) -> list[dict]:
    headers = []
    for column in result.header or []:
        if isinstance(column, (list, tuple)):
            headers.append(str(column[1] if len(column) > 1 else column[0]))
        else:
            headers.append(str(column))
    rows = []
    for raw in result.result_set or []:
        row = {}
        for index, value in enumerate(raw):
            key = headers[index] if index < len(headers) else f"col_{index}"
            row[key] = _plain(value)
        rows.append(row)
    return rows


def paths_from_result(result, label: str) -> list[dict]:
    found = []
    for raw in result.result_set or []:
        for value in raw:
            if isinstance(value, Path):
                found.append(path_dict(value, label=label))
    return found
