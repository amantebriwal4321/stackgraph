"""Tool-calling loop against an OpenAI-compatible /chat/completions endpoint.

No key and no base URL means this module is never called. The advisor then
uses the rule router.
"""

from __future__ import annotations

import json

import httpx

from app.config import Settings

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "find_alternatives",
            "description": "ALTERNATIVE_TO neighbors of a tool in the ecosystem graph.",
            "parameters": {
                "type": "object",
                "properties": {"name": {"type": "string"}},
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "blast_radius",
            "description": "Tools that reach a tool through DEPENDS_ON, 1 to 3 hops, plus signals.",
            "parameters": {
                "type": "object",
                "properties": {"name": {"type": "string"}},
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "shortest_path",
            "description": "Shortest DEPENDS_ON or ALTERNATIVE_TO path between two tools.",
            "parameters": {
                "type": "object",
                "properties": {
                    "from_name": {"type": "string"},
                    "to_name": {"type": "string"},
                },
                "required": ["from_name", "to_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "page_rank",
            "description": "PageRank of Tool nodes along DEPENDS_ON.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "maintainers_for",
            "description": "Maintainers of a tool and its dependency closure (2 hops).",
            "parameters": {
                "type": "object",
                "properties": {"name": {"type": "string"}},
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "signals_for",
            "description": "Signal nodes about a tool, including scout blast radius.",
            "parameters": {
                "type": "object",
                "properties": {"name": {"type": "string"}},
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "recall_memory",
            "description": "Read PREFERS, USES, and recent questions from the user memory graph.",
            "parameters": {
                "type": "object",
                "properties": {"kind": {"type": "string", "enum": ["prefs", "history", "both"]}},
            },
        },
    },
]


def complete(settings: Settings, messages: list[dict], tools: list[dict] | None) -> dict:
    url = settings.llm_base_url.rstrip("/") + "/chat/completions"
    payload: dict = {
        "model": settings.llm_model,
        "messages": messages,
        "temperature": 0,
    }
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = "auto"
    response = httpx.post(
        url,
        headers={"Authorization": f"Bearer {settings.llm_api_key}"},
        json=payload,
        timeout=60.0,
    )
    response.raise_for_status()
    return response.json()


def tool_loop(settings: Settings, question: str, execute) -> tuple[str, list]:
    """Let the model call graph tools. `execute(name, args)` returns a JSON-ready dict and a bundle."""

    system = (
        "You are the Stackgraph advisor. Call tools to read a FalkorDB graph before you answer. "
        "Use only facts that appear in tool results. Do not invent download counts, CVE ids, dates, "
        "or package names. If a signal agent is scout, say that scout wrote it. Keep the reply under 180 words."
    )
    messages: list[dict] = [
        {"role": "system", "content": system},
        {"role": "user", "content": question},
    ]
    bundles = []
    for _ in range(4):
        data = complete(settings, messages, TOOLS)
        message = data["choices"][0]["message"]
        messages.append(message)
        calls = message.get("tool_calls") or []
        if not calls:
            return (message.get("content") or "").strip(), bundles
        for call in calls:
            name = call["function"]["name"]
            raw_args = call["function"].get("arguments") or "{}"
            args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
            payload, bundle = execute(name, args or {})
            bundles.append(bundle)
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call["id"],
                    "content": json.dumps(payload)[:12000],
                }
            )
    data = complete(settings, messages, None)
    message = data["choices"][0]["message"]
    return (message.get("content") or "").strip(), bundles
