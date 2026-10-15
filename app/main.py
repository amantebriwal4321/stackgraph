"""HTTP API and the single page UI. FalkorDB is required for every route that answers."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.agents.advisor import ask
from app.agents.router import EXAMPLES
from app.agents.scout import run_scout
from app.config import load_settings
from app.graph.db import DatabaseDown, connect
from app.graph.queries import overview, scout_status
from app.graph.seed import load_catalog, read_catalog

STATIC = Path(__file__).resolve().parent / "static"
log = logging.getLogger("stackgraph")


class AskBody(BaseModel):
    question: str = Field(min_length=2, max_length=2000)
    user_id: str = "demo"
    session_id: str | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = load_settings()
    logging.basicConfig(level=logging.INFO)
    try:
        client = connect(settings)
    except DatabaseDown as exc:
        log.error("%s", exc)
        raise
    graph = client.select_graph(settings.graph_name)
    catalog = read_catalog(settings.catalog_path)
    loaded = load_catalog(graph, catalog)
    scout = run_scout(graph, settings.graph_name)
    log.info("seed tools=%s scout_signals=%s", loaded.get("tools"), scout.get("signals_written"))
    app.state.settings = settings
    app.state.db = client
    yield
    closer = getattr(client, "close", None)
    if closer:
        closer()


app = FastAPI(title="Stackgraph", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


@app.get("/favicon.ico", include_in_schema=False)
@app.get("/favicon.svg", include_in_schema=False)
def favicon():
    return FileResponse(STATIC / "favicon.svg", media_type="image/svg+xml")


@app.get("/api/health")
def health():
    settings = app.state.settings
    graph = app.state.db.select_graph(settings.graph_name)
    counted = overview(graph, settings.graph_name)
    scout = scout_status(graph, settings.graph_name)
    if counted.error:
        raise HTTPException(status_code=503, detail=counted.error)
    return {
        "ok": True,
        "falkordb": "up",
        "graph": settings.graph_name,
        "mode": "llm" if settings.llm_enabled else "fallback",
        "model": settings.llm_model if settings.llm_enabled else None,
        "counts": counted.rows[0] if counted.rows else {},
        "scout": scout.rows[0] if scout.rows else None,
    }


@app.get("/api/examples")
def examples():
    return {"examples": EXAMPLES}


@app.post("/api/ask")
def ask_route(body: AskBody):
    try:
        return ask(
            app.state.db,
            app.state.settings,
            body.question,
            user_id=body.user_id,
            session_id=body.session_id,
        )
    except Exception as exc:  # noqa: BLE001 - surface graph failures to the UI
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.post("/api/scout")
def scout_route():
    settings = app.state.settings
    graph = app.state.db.select_graph(settings.graph_name)
    result = run_scout(graph, settings.graph_name)
    if not result.get("ok"):
        raise HTTPException(status_code=503, detail=result.get("error") or "scout failed")
    return result


@app.get("/api/memory/{user_id}")
def memory_route(user_id: str):
    from app.agents.memory import clean_user
    from app.graph.db import memory_graph_name
    from app.graph.queries import recall_history, recall_prefs

    settings = app.state.settings
    user = clean_user(user_id)
    graph_name = memory_graph_name(settings, user)
    graph = app.state.db.select_graph(graph_name)
    prefs = recall_prefs(graph, graph_name, user)
    history = recall_history(graph, graph_name, user)
    if prefs.error:
        raise HTTPException(status_code=503, detail=prefs.error)
    return {
        "user_id": user,
        "graph": graph_name,
        "preferences": prefs.rows,
        "history": history.rows,
        "cypher": [prefs.public(), history.public()],
    }
