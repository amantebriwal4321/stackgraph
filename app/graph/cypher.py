"""Cypher the advisor and scout actually run.

These strings are the queries the README documents. Parameters use the
FalkorDB `$name` form.
"""

TOOL_NAMES = """
MATCH (t:Tool)
RETURN t.name AS name, t.aliases AS aliases, t.ecosystem AS ecosystem, t.id AS id
""".strip()

ALTERNATIVES = """
MATCH (t:Tool {name: $name})-[rel:ALTERNATIVE_TO]->(alt:Tool)
OPTIONAL MATCH (m:Maintainer)-[:MAINTAINS]->(alt)
OPTIONAL MATCH (alt)-[:IN_CATEGORY]->(c:Category)
RETURN alt.id AS id, alt.name AS name, alt.ecosystem AS ecosystem,
       alt.summary AS summary, rel.reason AS reason,
       m.name AS maintainer, m.handle AS handle, c.name AS category
ORDER BY alt.name
""".strip()

BLAST_PATHS = """
MATCH (t:Tool {name: $name})
MATCH p = (dep:Tool)-[:DEPENDS_ON*1..3]->(t)
RETURN p
LIMIT 25
""".strip()

BLAST_COUNT = """
MATCH (t:Tool {name: $name})
OPTIONAL MATCH (dep:Tool)-[:DEPENDS_ON*1..3]->(t)
RETURN t.id AS id, t.name AS name, count(DISTINCT dep) AS dependents
""".strip()

SIGNALS = """
MATCH (s:Signal)-[:ABOUT]->(t:Tool {name: $name})
RETURN s.id AS id, s.kind AS kind, s.source AS source, s.score AS score,
       s.ts AS ts, s.detail AS detail, s.origin AS origin, s.agent AS agent
ORDER BY s.kind
""".strip()

SHORTEST_PATH = """
MATCH (a:Tool {name: $from_name}), (b:Tool {name: $to_name})
RETURN shortestPath((a)-[:DEPENDS_ON|ALTERNATIVE_TO*1..8]-(b)) AS p
""".strip()

SHORTEST_PATH_DEPENDS = """
MATCH (a:Tool {name: $from_name}), (b:Tool {name: $to_name})
RETURN shortestPath((a)-[:DEPENDS_ON*1..8]->(b)) AS p
""".strip()

PAGERANK = """
CALL algo.pageRank('Tool', 'DEPENDS_ON')
YIELD node, score
RETURN node.id AS id, node.name AS name, node.ecosystem AS ecosystem, score
ORDER BY score DESC
LIMIT 10
""".strip()

DEGREE = """
MATCH (t:Tool)
OPTIONAL MATCH (d:Tool)-[:DEPENDS_ON]->(t)
RETURN t.id AS id, t.name AS name, t.ecosystem AS ecosystem, count(DISTINCT d) AS score
ORDER BY score DESC, t.name
LIMIT 10
""".strip()

LABEL_PROPAGATION = """
CALL algo.labelPropagation({nodeLabels: ['Tool'], relationshipTypes: ['ALTERNATIVE_TO'], maxIterations: 10})
YIELD node, communityId
RETURN node.id AS id, node.name AS name, communityId
ORDER BY communityId, node.name
""".strip()

MAINTAINERS = """
MATCH (root:Tool {name: $name})
OPTIONAL MATCH (root)-[:DEPENDS_ON*1..2]->(dep:Tool)
WITH root, collect(DISTINCT dep) AS deps
WITH [root] + deps AS tools
UNWIND tools AS t
OPTIONAL MATCH (m:Maintainer)-[:MAINTAINS]->(t)
RETURN DISTINCT t.id AS id, t.name AS name, t.ecosystem AS ecosystem,
       m.name AS maintainer, m.handle AS handle, m.url AS url
ORDER BY t.name
""".strip()

DIRECT_DEPS = """
MATCH (t:Tool {name: $name})-[rel:DEPENDS_ON]->(dep:Tool)
OPTIONAL MATCH (m:Maintainer)-[:MAINTAINS]->(dep)
RETURN dep.id AS id, dep.name AS name, dep.ecosystem AS ecosystem,
       rel.kind AS kind, rel.spec AS spec, m.name AS maintainer, m.handle AS handle
ORDER BY dep.name
""".strip()

TOOL_PROFILE = """
MATCH (t:Tool {name: $name})
OPTIONAL MATCH (m:Maintainer)-[:MAINTAINS]->(t)
OPTIONAL MATCH (t)-[:IN_CATEGORY]->(c:Category)
RETURN t.id AS id, t.name AS name, t.ecosystem AS ecosystem, t.summary AS summary,
       t.license AS license, t.version AS version, t.repo AS repo, t.legacy AS legacy,
       m.name AS maintainer, m.handle AS handle, collect(DISTINCT c.name) AS categories
""".strip()

OVERVIEW = """
MATCH (t:Tool)
WITH count(t) AS tools
OPTIONAL MATCH ()-[d:DEPENDS_ON]->()
WITH tools, count(d) AS depends_on
OPTIONAL MATCH ()-[a:ALTERNATIVE_TO]->()
WITH tools, depends_on, count(a) AS alternative_to
OPTIONAL MATCH (s:Signal)
WITH tools, depends_on, alternative_to, count(s) AS signals
OPTIONAL MATCH (m:Maintainer)
WITH tools, depends_on, alternative_to, signals, count(m) AS maintainers
OPTIONAL MATCH (c:Category)
RETURN tools, depends_on, alternative_to, signals, maintainers, count(c) AS categories
""".strip()

SCOUT_RUNS = """
MATCH (r:AgentRun {agent: 'scout'})
RETURN r.id AS id, r.ts AS ts, r.signals_written AS signals_written
ORDER BY r.ts DESC
LIMIT 1
""".strip()

SCOUT_WRITE_SIGNAL = """
MATCH (t:Tool {id: $tool_id})
MERGE (s:Signal {id: $id})
SET s.kind = 'blast_radius', s.source = 'scout', s.origin = 'derived',
    s.score = $score, s.ts = $ts, s.agent = 'scout', s.detail = $detail
MERGE (s)-[:ABOUT]->(t)
RETURN s.id AS id, t.name AS tool, s.score AS score
""".strip()

SCOUT_WRITE_RUN = """
CREATE (r:AgentRun {id: $id, agent: 'scout', ts: $ts, signals_written: $signals_written})
RETURN r.id AS id
""".strip()

RECALL_PREFS = """
MATCH (u:User {id: $user})-[r:PREFERS|USES]->(t:Tool)
RETURN type(r) AS rel, t.name AS tool, t.ecosystem AS ecosystem, r.ts AS ts, r.note AS note
ORDER BY r.ts DESC
""".strip()

RECALL_HISTORY = """
MATCH (u:User {id: $user})-[:HAS_SESSION]->(:Session)-[:ASKED]->(q:Question)-[:ANSWERED_WITH]->(a:Answer)
RETURN q.text AS question, a.text AS answer, q.ts AS ts, q.intent AS intent
ORDER BY q.ts DESC
LIMIT 8
""".strip()

SAVE_TURN = """
MERGE (u:User {id: $user})
MERGE (s:Session {id: $session})
ON CREATE SET s.started_at = $ts
MERGE (u)-[:HAS_SESSION]->(s)
CREATE (q:Question {id: $qid, text: $question, ts: $ts, intent: $intent})
CREATE (a:Answer {id: $aid, text: $answer, ts: $ts, mode: $mode, cypher_json: $cypher_json})
CREATE (s)-[:ASKED]->(q)
CREATE (q)-[:ANSWERED_WITH]->(a)
RETURN q.id AS question_id, a.id AS answer_id
""".strip()

REMEMBER_PREFERS = """
MERGE (u:User {id: $user})
MERGE (t:Tool {id: $tool_id})
SET t.name = $tool_name, t.ecosystem = $ecosystem, t.ref = true
MERGE (u)-[r:PREFERS]->(t)
SET r.ts = $ts, r.note = $note
RETURN u.id AS user, t.name AS tool, r.note AS note
""".strip()

REMEMBER_USES = """
MERGE (u:User {id: $user})
MERGE (t:Tool {id: $tool_id})
SET t.name = $tool_name, t.ecosystem = $ecosystem, t.ref = true
MERGE (u)-[r:USES]->(t)
SET r.ts = $ts, r.note = $note
RETURN u.id AS user, t.name AS tool, r.note AS note
""".strip()
