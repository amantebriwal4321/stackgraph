"""Scout writes blast radius signals back onto tools. Advisor reads those nodes."""

from __future__ import annotations

import uuid

from app.graph import cypher
from app.graph.queries import Call, _call, tool_directory
from app.agents.memory import now_iso


def run_scout(graph, graph_name: str) -> dict:
    directory = tool_directory(graph, graph_name)
    if directory.error:
        return {
            "ok": False,
            "error": directory.error,
            "signals_written": 0,
            "cypher": [directory.public()],
            "rows": [],
        }
    ts = now_iso()
    calls: list[Call] = []
    rows = []
    for tool in directory.rows:
        counted = _call(graph, graph_name, cypher.BLAST_COUNT, {"name": tool["name"]})
        if counted.error or not counted.rows:
            continue
        dependents = counted.rows[0].get("dependents") or 0
        if not dependents:
            continue
        count = int(dependents)
        noun = "tool" if count == 1 else "tools"
        verb = "reaches" if count == 1 else "reach"
        detail = (
            f"Scout counted {count} {noun} that {verb} {tool['name']} "
            "by a DEPENDS_ON path of 1 to 3 hops in the ecosystem graph."
        )
        written = _call(
            graph,
            graph_name,
            cypher.SCOUT_WRITE_SIGNAL,
            {
                "tool_id": tool["id"],
                "id": f"scout:blast:{tool['id']}",
                "score": int(dependents),
                "ts": ts,
                "detail": detail,
            },
        )
        calls.append(written)
        if written.rows:
            rows.extend(written.rows)
    run = _call(
        graph,
        graph_name,
        cypher.SCOUT_WRITE_RUN,
        {
            "id": "run" + uuid.uuid4().hex[:12],
            "ts": ts,
            "signals_written": len(rows),
        },
    )
    calls.append(run)
    # One copy of the count query stands in for the per-tool loop. The writes are listed in full.
    shown = [
        {
            "graph": graph_name,
            "query": cypher.BLAST_COUNT,
            "params": {"name": "<each tool name>"},
            "rendered": cypher.BLAST_COUNT,
        }
    ]
    shown.extend(call.public() for call in calls)
    return {
        "ok": run.error == "" and all(call.error == "" for call in calls),
        "error": run.error,
        "signals_written": len(rows),
        "ts": ts,
        "cypher": shown,
        "rows": rows,
        "agents": ["scout"],
    }
