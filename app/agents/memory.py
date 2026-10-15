"""Per-user memory graph. Edges cannot cross FalkorDB graphs, so tool refs are copied."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from app.graph import cypher
from app.graph.queries import Call, _call

_LABELS = {"Tool", "Signal", "Maintainer", "Category", "User", "PathNode"}
_REMEMBER = {"PREFERS": cypher.REMEMBER_PREFERS, "USES": cypher.REMEMBER_USES}


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def clean_user(user_id: str | None) -> str:
    raw = (user_id or "demo").strip().lower()
    cleaned = "".join(ch for ch in raw if ch.isalnum())
    return (cleaned or "demo")[:24]


def clean_session(session_id: str | None) -> str:
    if session_id and session_id.isalnum() and 8 <= len(session_id) <= 40:
        return session_id
    return "s" + uuid.uuid4().hex[:16]


def remember(graph, graph_name: str, user: str, tool: dict, relation: str, note: str, ts: str) -> Call:
    query = _REMEMBER[relation]
    return _call(
        graph,
        graph_name,
        query,
        {
            "user": user,
            "tool_id": tool["id"],
            "tool_name": tool["name"],
            "ecosystem": tool.get("ecosystem") or "",
            "ts": ts,
            "note": note,
        },
    )


def save_turn(
    graph,
    graph_name: str,
    user: str,
    session: str,
    question: str,
    answer: str,
    intent: str,
    mode: str,
    cypher_calls: list[dict],
    paths: list[dict],
    ts: str,
) -> list[Call]:
    qid = "q" + uuid.uuid4().hex[:12]
    aid = "a" + uuid.uuid4().hex[:12]
    saved = _call(
        graph,
        graph_name,
        cypher.SAVE_TURN,
        {
            "user": user,
            "session": session,
            "ts": ts,
            "qid": qid,
            "question": question,
            "intent": intent,
            "aid": aid,
            "answer": answer,
            "mode": mode,
            "cypher_json": json.dumps(cypher_calls)[:8000],
        },
    )
    calls = [saved]
    order = 0
    seen = set()
    for path in paths:
        nodes = path.get("nodes") or []
        edges = path.get("edges") or []
        for index, node in enumerate(nodes):
            label = "PathNode"
            for candidate in node.get("labels") or []:
                if candidate in _LABELS and candidate != "PathNode":
                    label = candidate
                    break
            node_id = str(node.get("id") or f"{label}:{node.get('name')}")
            key = (label, node_id)
            if key in seen:
                continue
            seen.add(key)
            via = ""
            if index < len(edges):
                via = edges[index].get("type") or ""
            query = f"""
            MATCH (a:Answer {{id: $aid}})
            MERGE (n:{label} {{id: $id}})
            SET n.name = $name, n.ref = true
            CREATE (a)-[:USED_PATH {{ord: $ord, via: $via}}]->(n)
            """.strip()
            calls.append(
                _call(
                    graph,
                    graph_name,
                    query,
                    {
                        "aid": aid,
                        "id": node_id,
                        "name": node.get("name") or "",
                        "ord": order,
                        "via": via,
                    },
                )
            )
            order += 1
            if order >= 40:
                return calls
    return calls
