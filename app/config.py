"""Runtime settings. An empty model key selects the rule based router."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _flag(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    falkordb_host: str
    falkordb_port: int
    falkordb_username: str | None
    falkordb_password: str | None
    falkordb_ssl: bool
    falkordb_url: str | None
    graph_name: str
    memory_prefix: str
    llm_base_url: str | None
    llm_api_key: str | None
    llm_model: str
    catalog_path: Path
    port: int

    @property
    def llm_enabled(self) -> bool:
        return bool(self.llm_api_key and self.llm_base_url)


def load_settings() -> Settings:
    base = os.environ.get("LLM_BASE_URL", "").strip() or None
    key = os.environ.get("LLM_API_KEY", "").strip() or None
    model = os.environ.get("LLM_MODEL", "").strip() or "gpt-4o-mini"
    url = os.environ.get("FALKORDB_URL", "").strip() or None
    return Settings(
        falkordb_host=os.environ.get("FALKORDB_HOST", "localhost"),
        falkordb_port=int(os.environ.get("FALKORDB_PORT", "6379")),
        falkordb_username=os.environ.get("FALKORDB_USERNAME", "").strip() or None,
        falkordb_password=os.environ.get("FALKORDB_PASSWORD", "").strip() or None,
        falkordb_ssl=_flag("FALKORDB_SSL", False),
        falkordb_url=url,
        graph_name=os.environ.get("STACKGRAPH_GRAPH", "ecosystem"),
        memory_prefix=os.environ.get("STACKGRAPH_MEMORY_PREFIX", "mem_"),
        llm_base_url=base,
        llm_api_key=key,
        llm_model=model,
        catalog_path=Path(os.environ.get("STACKGRAPH_CATALOG", ROOT / "seed" / "catalog.json")),
        port=int(os.environ.get("STACKGRAPH_PORT", "8091")),
    )
