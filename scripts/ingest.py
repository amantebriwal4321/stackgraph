"""Load seed/catalog.json into FalkorDB, or rebuild it from the public registries.

    python scripts/ingest.py
    python scripts/ingest.py refresh

refresh fetches npm and PyPI, rewrites seed/catalog.json, then MERGEs that file
into the ecosystem graph. The default command does not touch the network.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.config import load_settings  # noqa: E402
from app.graph.db import connect  # noqa: E402
from app.graph.seed import load_catalog, read_catalog  # noqa: E402


def main(argv: list[str]) -> None:
    if len(argv) > 1 and argv[1] == "refresh":
        from scripts.build_catalog import main as build

        build()
    settings = load_settings()
    client = connect(settings, attempts=15)
    graph = client.select_graph(settings.graph_name)
    catalog = read_catalog(settings.catalog_path)
    loaded = load_catalog(graph, catalog)
    print(f"graph {settings.graph_name} tools {loaded['tools']}")


if __name__ == "__main__":
    main(sys.argv)
