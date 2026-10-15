from falkordb import FalkorDB

from app.agents.advisor import ask
from app.agents.scout import run_scout


QUESTIONS = [
    "What should I use instead of moment?",
    "What breaks if express is deprecated?",
    "Who maintains the libraries that next depends on?",
    "Show the path from next to react",
    "Which dependency is most critical in this graph?",
]


def test_five_questions_return_cypher_and_paths(client, settings, eco):
    for question in QUESTIONS:
        result = ask(client, settings, question, user_id="sgtest", session_id="sessionone")
        assert result["mode"] == "fallback"
        assert result["answer"]
        assert result["cypher"], question
        assert any(item["query"].strip() for item in result["cypher"])
        assert result["paths"], question
        assert "mem_sgtest" == result["memory_graph"]


def test_moment_answer_mentions_dayjs_and_signal(client, settings, eco):
    result = ask(client, settings, "What should I use instead of moment?", user_id="sgtest")
    assert "dayjs" in result["answer"]
    assert "legacy" in result["answer"].lower() or "deprecation" in result["answer"].lower()


def test_scout_signal_is_visible_to_advisor(client, settings, eco):
    scout = run_scout(eco, settings.graph_name)
    assert scout["ok"]
    assert scout["signals_written"] >= 1
    result = ask(client, settings, "What breaks if express is deprecated?", user_id="sgtest")
    assert "scout" in result["agents"]
    assert "blast_radius" in result["answer"] or "Scout" in result["answer"]


def test_new_connection_reads_saved_preference(client, settings, eco):
    ask(client, settings, "I prefer zod over yup", user_id="sgtest", session_id="sessiontwo")
    fresh = FalkorDB(host=settings.falkordb_host, port=settings.falkordb_port)
    result = ask(fresh, settings, "What do I prefer?", user_id="sgtest", session_id="sessiontwo")
    assert "zod" in result["answer"]
    assert "PREFERS" in result["answer"]
