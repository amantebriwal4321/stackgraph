"""Advisor answers from the ecosystem graph and writes the user memory graph."""

from __future__ import annotations

from app.agents import format
from app.agents.memory import clean_session, clean_user, now_iso, remember, save_turn
from app.agents.router import classify, alias_index
from app.config import Settings
from app.graph.db import memory_graph_name as mem_name
from app.graph.queries import (
    alternatives,
    blast,
    communities,
    direct_deps,
    maintainers,
    overview,
    page_rank,
    profile,
    recall_history,
    recall_prefs,
    scout_status,
    shortest_path,
    signals,
    tool_directory,
)
from app.llm.client import tool_loop


def _community_for(call, name: str):
    if call is None or call.error:
        return None
    cid = None
    for row in call.rows:
        if row.get("name") == name:
            cid = row.get("communityId")
            break
    if cid is None:
        return None
    members = [
        row["name"]
        for row in call.rows
        if row.get("communityId") == cid and row.get("name") and row["name"] != name
    ]
    return cid, members


def _pack(calls, paths, answer: str, intent: str, tools: list[str], agents: list[str]) -> dict:
    return {
        "answer": answer.strip(),
        "intent": intent,
        "cypher": [call.public() for call in calls if call is not None],
        "paths": paths,
        "tools": tools,
        "agents": agents,
    }


def _rules(eco, mem, settings: Settings, question: str, user: str, plan, by_name: dict) -> dict:
    gname = settings.graph_name
    mname = mem_name(settings, user)
    calls = []
    paths = []
    tools: list[str] = []
    agents = ["advisor"]

    def take(call):
        if call is None:
            return call
        calls.append(call)
        paths.extend(call.paths or [])
        return call

    if plan.intent == "alternatives":
        if not plan.names:
            return _pack(calls, paths, format.help_text(None), "help", tools, agents)
        name = plan.names[0]
        tools += ["find_alternatives", "signals_for", "community_for"]
        alt = take(alternatives(eco, gname, name))
        sig = take(signals(eco, gname, name))
        comm = take(communities(eco, gname))
        grouped = None if comm.error else _community_for(comm, name)
        answer = format.alternatives(name, alt.rows, sig.rows, grouped)
        if any((row.get("agent") == "scout") for row in sig.rows):
            agents.append("scout")
        return _pack(calls, paths, answer, plan.intent, tools, agents)

    if plan.intent == "impact":
        if not plan.names:
            return _pack(calls, paths, "Name a tool in the corpus.", "impact", tools, agents)
        name = plan.names[0]
        tools += ["blast_radius", "signals_for"]
        path_call, count_call = blast(eco, gname, name)
        take(path_call)
        take(count_call)
        sig = take(signals(eco, gname, name))
        scout = take(scout_status(eco, gname))
        scout_row = scout.rows[0] if scout.rows else None
        if scout_row:
            agents.append("scout")
        if any(row.get("agent") == "scout" for row in sig.rows) and "scout" not in agents:
            agents.append("scout")
        answer = format.impact(name, count_call.rows, path_call.paths, sig.rows, scout_row)
        return _pack(calls, paths, answer, plan.intent, tools, agents)

    if plan.intent == "path":
        tools.append("shortest_path")
        if len(plan.names) < 2:
            return _pack(calls, paths, "Name two tools in the corpus to connect.", "path", tools, agents)
        call = take(shortest_path(eco, gname, plan.names[0], plan.names[1]))
        answer = format.path_answer(plan.names[0], plan.names[1], call.paths, call.error)
        return _pack(calls, paths, answer, plan.intent, tools, agents)

    if plan.intent == "critical":
        tools.append("page_rank")
        call = take(page_rank(eco, gname))
        algorithm = "degree" if "in degree" in (call.paths[0]["label"] if call.paths else "") else "pagerank"
        if "DEGREE" in call.query or "count(DISTINCT d)" in call.query:
            algorithm = "degree"
        answer = format.critical(call.rows, algorithm)
        return _pack(calls, paths, answer, plan.intent, tools, agents)

    if plan.intent == "maintainers":
        tools.append("maintainers_for")
        from_memory = False
        starts = list(plan.names[:1])
        if not starts:
            prefs = take(recall_prefs(mem, mname, user))
            starts = [row["tool"] for row in prefs.rows if row.get("rel") == "USES" and row.get("tool")]
            if not starts:
                starts = [row["tool"] for row in prefs.rows if row.get("rel") == "PREFERS" and row.get("tool")]
            from_memory = bool(starts)
            tools.append("recall_memory")
        if not starts:
            return _pack(
                calls,
                paths,
                "Name a tool, or tell me what you use, and I can look up maintainers from the graph.",
                "maintainers",
                tools,
                agents,
            )
        chunks = []
        for name in starts[:4]:
            call = take(maintainers(eco, gname, name))
            chunks.append(format.maintainers(name, call.rows, from_memory))
        return _pack(calls, paths, " ".join(chunks), plan.intent, tools, agents)

    if plan.intent == "memory_write":
        tools.append("remember")
        ts = now_iso()
        written = []
        for relation, tool_name, note in plan.writes:
            tool = by_name.get(tool_name)
            if not tool:
                continue
            call = remember(mem, mname, user, tool, relation, note, ts)
            take(call)
            written.append((relation, tool_name, note))
        prefs = take(recall_prefs(mem, mname, user))
        tools.append("recall_memory")
        answer = format.memory_write(written) + " " + format.recall(prefs.rows, [], "prefs")
        return _pack(calls, paths, answer, plan.intent, tools, agents)

    if plan.intent == "recall":
        tools.append("recall_memory")
        pref_rows = []
        hist_rows = []
        if plan.recall in {"prefs", "both"}:
            pref_rows = take(recall_prefs(mem, mname, user)).rows
        if plan.recall in {"history", "both"}:
            hist_rows = take(recall_history(mem, mname, user)).rows
        if plan.recall == "both" and not plan.names:
            # "who maintains my stack" is maintainers. Plain "my stack" still lands here.
            pass
        answer = format.recall(pref_rows, hist_rows, plan.recall)
        if plan.names and any(phrase in question.lower() for phrase in ("maintains", "maintainer")):
            pass
        return _pack(calls, paths, answer, plan.intent, tools, agents)

    if plan.intent == "signals":
        if not plan.names:
            return _pack(calls, paths, "Name a tool to read signals for.", "signals", tools, agents)
        name = plan.names[0]
        tools.append("signals_for")
        sig = take(signals(eco, gname, name))
        if any(row.get("agent") == "scout" for row in sig.rows):
            agents.append("scout")
        return _pack(calls, paths, format.signals_answer(name, sig.rows), plan.intent, tools, agents)

    if plan.intent == "community":
        if not plan.names:
            return _pack(calls, paths, "Name a tool to cluster.", "community", tools, agents)
        name = plan.names[0]
        tools.append("community_for")
        comm = take(communities(eco, gname))
        grouped = _community_for(comm, name)
        if comm.error:
            answer = f"Label propagation failed: {comm.error}"
        elif grouped is None:
            answer = format.community(name, None, [])
        else:
            answer = format.community(name, grouped[0], grouped[1])
        return _pack(calls, paths, answer, plan.intent, tools, agents)

    if plan.intent == "about":
        name = plan.names[0]
        tools += ["profile", "direct_dependencies", "find_alternatives", "signals_for"]
        prof = take(profile(eco, gname, name))
        deps = take(direct_deps(eco, gname, name))
        alt = take(alternatives(eco, gname, name))
        sig = take(signals(eco, gname, name))
        if any(row.get("agent") == "scout" for row in sig.rows):
            agents.append("scout")
        answer = format.about(name, prof.rows, deps.rows, alt.rows, sig.rows)
        return _pack(calls, paths, answer, plan.intent, tools, agents)

    counted = take(overview(eco, gname))
    counts = counted.rows[0] if counted.rows else None
    tools.append("explain_overview")
    return _pack(calls, paths, format.help_text(counts), "help", tools, agents)


def _execute_for_model(eco, mem, settings, user, by_name):
    gname = settings.graph_name
    mname = mem_name(settings, user)

    def execute(name: str, args: dict):
        if name == "find_alternatives":
            call = alternatives(eco, gname, args.get("name", ""))
            return {"rows": call.rows}, call
        if name == "blast_radius":
            paths, count = blast(eco, gname, args.get("name", ""))
            sig = signals(eco, gname, args.get("name", ""))
            return {"dependents": count.rows, "signals": sig.rows, "paths": len(paths.paths)}, paths
        if name == "shortest_path":
            call = shortest_path(eco, gname, args.get("from_name", ""), args.get("to_name", ""))
            return {"paths": call.paths, "error": call.error}, call
        if name == "page_rank":
            call = page_rank(eco, gname)
            return {"rows": call.rows}, call
        if name == "maintainers_for":
            call = maintainers(eco, gname, args.get("name", ""))
            return {"rows": call.rows}, call
        if name == "signals_for":
            call = signals(eco, gname, args.get("name", ""))
            return {"rows": call.rows}, call
        if name == "recall_memory":
            kind = args.get("kind") or "both"
            prefs = recall_prefs(mem, mname, user)
            hist = recall_history(mem, mname, user) if kind != "prefs" else None
            payload = {"preferences": prefs.rows}
            if hist is not None:
                payload["history"] = hist.rows
            return payload, prefs
        return {"error": f"unknown tool {name}"}, None

    return execute


def ask(db, settings: Settings, question: str, user_id: str = "demo", session_id: str | None = None) -> dict:
    user = clean_user(user_id)
    session = clean_session(session_id)
    eco = db.select_graph(settings.graph_name)
    mem = db.select_graph(mem_name(settings, user))
    directory = tool_directory(eco, settings.graph_name)
    if directory.error:
        raise RuntimeError(directory.error)
    index = alias_index(directory.rows)
    by_name = {row["name"]: row for row in directory.rows}
    plan = classify(question, index)
    result = _rules(eco, mem, settings, question, user, plan, by_name)
    mode = "fallback"
    if settings.llm_enabled:
        try:
            execute = _execute_for_model(eco, mem, settings, user, by_name)
            text, bundles = tool_loop(settings, question, execute)
            extra_calls = [bundle for bundle in bundles if bundle is not None]
            if text and extra_calls:
                result["answer"] = text
                result["cypher"].extend(call.public() for call in extra_calls)
                for call in extra_calls:
                    result["paths"].extend(call.paths or [])
                result["tools"] = sorted(set(result["tools"] + ["llm"]))
                mode = "llm"
            else:
                result["answer"] += " The model returned no graph tool call, so this is the rule router answer."
        except Exception as exc:  # noqa: BLE001 - demo must still answer
            result["answer"] += f" The model call failed ({exc.__class__.__name__}), so this is the rule router answer."
    ts = now_iso()
    memory_calls = save_turn(
        mem,
        mem_name(settings, user),
        user,
        session,
        question,
        result["answer"],
        result["intent"],
        mode,
        result["cypher"],
        result["paths"],
        ts,
    )
    result["cypher"].extend(call.public() for call in memory_calls)
    result.update(
        {
            "mode": mode,
            "user_id": user,
            "session_id": session,
            "memory_graph": mem_name(settings, user),
        }
    )
    return result
