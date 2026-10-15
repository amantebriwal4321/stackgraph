import os

import pytest

os.environ.setdefault("FALKORDB_HOST", "localhost")
os.environ.setdefault("FALKORDB_PORT", "6379")
os.environ.setdefault("STACKGRAPH_GRAPH", "sg_test_eco")
os.environ.setdefault("LLM_API_KEY", "")
os.environ.setdefault("LLM_BASE_URL", "")

from app.config import load_settings  # noqa: E402
from app.graph.db import connect  # noqa: E402
from app.graph.seed import load_catalog, read_catalog  # noqa: E402


@pytest.fixture(scope="session")
def client():
    settings = load_settings()
    return connect(settings, attempts=5, pause=0.5)


@pytest.fixture
def settings():
    base = load_settings()
    return base.__class__(
        **{
            **base.__dict__,
            "graph_name": "sg_test_eco",
            "llm_api_key": None,
            "llm_base_url": None,
        }
    )


def _reset(client, name: str):
    graph = client.select_graph(name)
    try:
        graph.delete()
    except Exception:
        pass
    return client.select_graph(name)


@pytest.fixture
def eco(client, settings):
    graph = _reset(client, settings.graph_name)
    catalog = read_catalog(settings.catalog_path)
    load_catalog(graph, catalog)
    return graph


@pytest.fixture
def mem(client):
    return _reset(client, "mem_sgtest")
