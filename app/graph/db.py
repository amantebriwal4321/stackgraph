"""FalkorDB connection. Every read and write in the product goes through here."""

from __future__ import annotations

import time

from falkordb import FalkorDB

from app.config import Settings


class DatabaseDown(RuntimeError):
    """Raised when FalkorDB cannot be reached. The product has no other store."""


def connect(settings: Settings, attempts: int = 30, pause: float = 1.0) -> FalkorDB:
    last_error: Exception | None = None
    for _ in range(attempts):
        try:
            if settings.falkordb_url:
                client = FalkorDB.from_url(settings.falkordb_url)
            else:
                client = FalkorDB(
                    host=settings.falkordb_host,
                    port=settings.falkordb_port,
                    username=settings.falkordb_username,
                    password=settings.falkordb_password,
                    ssl=settings.falkordb_ssl,
                    socket_timeout=10,
                    socket_connect_timeout=5,
                )
            client.list_graphs()
            return client
        except Exception as exc:  # noqa: BLE001 - connection retry
            last_error = exc
            time.sleep(pause)
    raise DatabaseDown(f"FalkorDB is not reachable: {last_error}")


def memory_graph_name(settings: Settings, user_id: str) -> str:
    return f"{settings.memory_prefix}{user_id}"
