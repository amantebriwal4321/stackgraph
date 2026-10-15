# Submission draft

Paste these into the hackathon form.

## Title

Stackgraph

## One liner

An agent that answers dependency questions by running Cypher on a FalkorDB graph of public package metadata, and writes what you asked into a per user memory graph.

## Description

Stackgraph is a small dev tool corpus (npm and PyPI packages) loaded into FalkorDB. You ask things like what to use instead of moment, what reaches express, who maintains the packages next depends on, or which tool PageRank ranks highest. The advisor runs a fixed set of Cypher queries, including shortestPath, PageRank, and label propagation, and the UI shows the query and the node path.

A second agent, scout, counts multi hop dependents and writes Signal nodes back onto the same graph. Later answers cite those signals. Preferences and the transcript go to a separate FalkorDB graph per user (`mem_<user>`), so memory survives an API restart.

FalkorDB is the only store. The seed JSON is an ingest file. With the database stopped, `/api/ask` returns 503.

No model key is required. Set an OpenAI compatible base URL and key only if you want the model to call the same graph tools.

## Tracks

* Agents That Act on Connected Data (primary)
* Agent Memory and Coordination (secondary)

## How FalkorDB is used

The `ecosystem` graph holds Tool, Category, Maintainer, Signal, and AgentRun nodes, with DEPENDS_ON, ALTERNATIVE_TO, IN_CATEGORY, MAINTAINS, and ABOUT edges. Scout writes blast radius signals there. Advisor reads them. Each user gets a memory graph for User, Session, Question, Answer, PREFERS, USES, and USED_PATH. The compose file runs `falkordb/falkordb:latest` and mounts a volume at the image data directory. There is no other database.

## Cypher and algorithms

See the README section "Cypher and algorithms". The strings the process runs are in `app/graph/cypher.py`. Algorithms: `algo.pageRank` on Tool / DEPENDS_ON, `algo.labelPropagation` on Tool / ALTERNATIVE_TO, and `shortestPath` over DEPENDS_ON and ALTERNATIVE_TO. Variable length `DEPENDS_ON*1..3` is the blast radius walk.

## AI disclosure

Cursor's coding agent (Grok 4.7) drafted the repository. Aman Tebriwal owns the project and needs to be able to explain the model, the queries, and the architecture. Registry fields were fetched from public npm and PyPI. Alternative edges are editorial. The judged demo path does not call a model.

## Links

* Repo: <https://github.com/amantebriwal4321/stackgraph>
* Live app: <https://stackgraph.onrender.com> (Render free plan, one container running FalkorDB and the API. First load after idle can take about a minute.) Local UI is <http://127.0.0.1:8091> after `docker compose up -d`.
* Demo video: record from `docs/DEMO_SCRIPT.md`
* Blog: `docs/BLOG_DRAFT.md`

## Data

Public registry metadata plus a curated alternative list and one public Moment status signal. Scout scores are counts inside this corpus. No private data, no scraped credentials, no invented download totals.
