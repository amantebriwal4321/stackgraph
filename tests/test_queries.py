from app.graph import cypher
from app.graph.queries import alternatives, blast, maintainers, page_rank, shortest_path


def test_overview_counts_finish(eco):
    from app.graph.queries import overview

    call = overview(eco, "sg_test_eco")
    assert call.error == ""
    assert call.rows[0]["tools"] == 70
    assert call.rows[0]["depends_on"] >= 1


def test_moment_alternatives_include_dayjs(eco):
    call = alternatives(eco, "sg_test_eco", "moment")
    assert call.error == ""
    names = {row["name"] for row in call.rows}
    assert {"dayjs", "date-fns", "luxon"} <= names
    assert call.query == cypher.ALTERNATIVES
    assert call.paths


def test_express_blast_radius_uses_dependency_edges(eco):
    paths, count = blast(eco, "sg_test_eco", "express")
    assert paths.error == ""
    assert count.error == ""
    assert count.rows[0]["dependents"] >= 1
    starters = {path["nodes"][0]["name"] for path in paths.paths}
    assert "@nestjs/platform-express" in starters or "sails" in starters or "@feathersjs/express" in starters


def test_shortest_path_next_to_react(eco):
    call = shortest_path(eco, "sg_test_eco", "next", "react")
    assert call.error == ""
    assert call.paths
    names = [node["name"] for node in call.paths[0]["nodes"]]
    assert names[0] == "next"
    assert names[-1] == "react"


def test_centrality_returns_ordered_tools(eco):
    call = page_rank(eco, "sg_test_eco")
    assert call.error == ""
    assert len(call.rows) >= 3
    scores = [row["score"] for row in call.rows]
    assert scores == sorted(scores, reverse=True)


def test_maintainers_of_next_include_react(eco):
    call = maintainers(eco, "sg_test_eco", "next")
    assert call.error == ""
    names = {row["name"] for row in call.rows}
    assert "next" in names
    assert "react" in names
