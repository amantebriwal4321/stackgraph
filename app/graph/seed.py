"""Load seed/catalog.json into a FalkorDB graph. Idempotent MERGE only."""

from __future__ import annotations

import json
from pathlib import Path


def read_catalog(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _run(graph, query: str, params: dict | None = None):
    graph.query(query, params or {})


def load_catalog(graph, catalog: dict) -> dict:
    for category in catalog["categories"]:
        _run(
            graph,
            "MERGE (c:Category {id: $id}) SET c.name = $name",
            category,
        )
    for maintainer in catalog["maintainers"]:
        _run(
            graph,
            """
            MERGE (m:Maintainer {id: $id})
            SET m.name = $name, m.handle = $handle, m.url = $url
            """,
            maintainer,
        )
    for tool in catalog["tools"]:
        _run(
            graph,
            """
            MERGE (t:Tool {id: $id})
            SET t.name = $name, t.ecosystem = $ecosystem, t.package = $package,
                t.summary = $summary, t.license = $license, t.repo = $repo,
                t.version = $version, t.legacy = $legacy, t.origin = $origin,
                t.aliases = $aliases, t.ref = false
            """,
            {
                "id": tool["id"],
                "name": tool["name"],
                "ecosystem": tool["ecosystem"],
                "package": tool["package"],
                "summary": tool.get("summary") or "",
                "license": tool.get("license") or "",
                "repo": tool.get("repo") or "",
                "version": tool.get("version") or "",
                "legacy": bool(tool.get("legacy", False)),
                "origin": tool.get("origin") or "public",
                "aliases": tool.get("aliases") or [],
            },
        )
        _run(
            graph,
            """
            MATCH (t:Tool {id: $tool}), (m:Maintainer {id: $maintainer})
            MERGE (m)-[:MAINTAINS]->(t)
            """,
            {"tool": tool["id"], "maintainer": tool["maintainer"]},
        )
        for category_id in tool["categories"]:
            _run(
                graph,
                """
                MATCH (t:Tool {id: $tool}), (c:Category {id: $category})
                MERGE (t)-[:IN_CATEGORY]->(c)
                """,
                {"tool": tool["id"], "category": category_id},
            )

    by_name = {tool["name"]: tool["id"] for tool in catalog["tools"]}
    for edge in catalog["dependencies"]:
        _run(
            graph,
            """
            MATCH (src:Tool {id: $src}), (dst:Tool {id: $dst})
            MERGE (src)-[r:DEPENDS_ON]->(dst)
            SET r.kind = $kind, r.spec = $spec
            """,
            {
                "src": by_name[edge["from"]],
                "dst": by_name[edge["to"]],
                "kind": edge["kind"],
                "spec": edge.get("spec") or "",
            },
        )
    for edge in catalog["alternatives"]:
        reason = edge["reason"]
        pair = (by_name[edge["from"]], by_name[edge["to"]])
        for src, dst in (pair, (pair[1], pair[0])):
            _run(
                graph,
                """
                MATCH (src:Tool {id: $src}), (dst:Tool {id: $dst})
                MERGE (src)-[r:ALTERNATIVE_TO]->(dst)
                SET r.reason = $reason
                """,
                {"src": src, "dst": dst, "reason": reason},
            )
    for signal in catalog["signals"]:
        _run(
            graph,
            """
            MATCH (t:Tool {id: $tool})
            MERGE (s:Signal {id: $id})
            SET s.kind = $kind, s.source = $source, s.score = $score,
                s.detail = $detail, s.origin = $origin, s.agent = 'seed', s.ts = ''
            MERGE (s)-[:ABOUT]->(t)
            """,
            {
                "tool": by_name[signal["tool"]],
                "id": signal["id"],
                "kind": signal["kind"],
                "source": signal["source"],
                "score": signal["score"],
                "detail": signal["detail"],
                "origin": signal["origin"],
            },
        )
    for statement in (
        "CREATE INDEX FOR (t:Tool) ON (t.name)",
        "CREATE INDEX FOR (t:Tool) ON (t.id)",
        "CREATE INDEX FOR (u:User) ON (u.id)",
    ):
        try:
            graph.query(statement)
        except Exception:
            # Index already exists, or this server build uses another form.
            pass
    counts = graph.query("MATCH (t:Tool) RETURN count(t) AS tools").result_set
    return {"tools": counts[0][0] if counts else 0}
