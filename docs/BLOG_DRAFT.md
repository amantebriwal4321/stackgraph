# Asking a graph instead of a README

I wanted a small agent that could answer the questions I actually ask when a dependency looks old. What should I use instead of moment. What else breaks if express is the thing being removed. Who maintains the libraries a framework sits on. And I wanted the answer to show the path, because a confident paragraph with no edges is how you ship a wrong migration.

The hackathon constraint made the design obvious. FalkorDB had to be the product, not a cache beside one. If the database is down, Stackgraph returns 503. The seed file is only how the corpus gets in.

## The corpus

I did not want a fake social network with package names stuck on it. `scripts/build_catalog.py` takes an editorial list of 70 public packages, 54 from npm and 16 from PyPI, and fetches each latest document. Descriptions, versions, licenses, and repos are stored as properties. A dependency edge is created only when the other side is also in the corpus.

That rule sounds strict until you see what the registries put in those fields. The first PyPI parse treated every `requires_dist` entry as a runtime dependency. Pandas then appeared to depend on pytest and SQLAlchemy, because those lines are extras. The marker sits after a semicolon and contains the word extra. Skipping those lines dropped the catalog from 49 dependency edges to 38. The remaining pandas edge is numpy, which is what I wanted the blast radius query to mean.

npm peer dependencies stayed. They are how a lot of this ecosystem actually couples. `next` 16.4.1, fetched with the rest of the catalog at 2026-10-15T18:16:27Z, peers react, react-dom, and `@playwright/test`. I checked the registry document by hand because Playwright looked like a mistake. It is on the peer list. The maintainer answer for next therefore includes Microsoft. That is the graph being literal. The UI is supposed to make that visible, not sand it off.

Alternative edges are different. The registries do not publish "use dayjs instead". Those pairs live in `seed/editorial.py` with a short reason, and the loader writes the edge in both directions so an undirected traversal can see them. The Moment deprecation signal is also editorial, and it points at Moment's own project status page. The score on that signal is a flag. I did not invent a download chart.

Scout is the other writer. For every tool it counts distinct tools that reach it by a `DEPENDS_ON` path of 1 to 3 hops, and if the count is above zero it MERGEs a `blast_radius` signal. On the loaded corpus that was 19 signals. Express came back as 4: `@feathersjs/express`, sails, `@nestjs/platform-express`, and `@nestjs/core` one hop further out. Moment came back as 1, which is sequelize's runtime dependency on moment. Advisor does not recompute that in prose. It reads the Signal node scout wrote, which is the whole coordination trick. Two agents, one graph, no side channel.

## Queries that survived contact with the server

PageRank is a procedure call:

```
CALL algo.pageRank('Tool', 'DEPENDS_ON')
YIELD node, score
```

On the demo graph the answer printed react (0.0337), typescript (0.0272), and express (0.0192). Two earlier calls on a copy of the load, after one scout pass, matched each other at react 0.033911, typescript 0.027305, express 0.019278. A call before any scout signals existed had react at 0.037603. I did not isolate the shift, and I am not calling the scores popularity.

Label propagation is the other procedure, on `ALTERNATIVE_TO`, with `maxIterations` 10. For the moment question it grouped moment with date-fns, dayjs, and luxon. The community id is whatever the procedure emitted on that run. I would not persist it as a business key.

`shortestPath` was the query that broke. I wrote the pattern I would write in Neo4j, assigning the path in a `MATCH`. FalkorDB answered: "FalkorDB currently only supports shortestPaths in WITH or RETURN clauses". Moving the call into `RETURN` fixed the next to react path. It is one `DEPENDS_ON` hop, and the relationship property says the kind is peer. There is a directed fallback if the mixed relationship pattern is rejected. It was not rejected on this server.

The other timeout was self inflicted. An overview query matched every Tool and then optionally matched every edge without aggregating first. The image default includes `TIMEOUT 1000`. The server returned "Query timed out". Collapsing the tool count with `WITH` before the edge matches made `/api/health` cheap. On that graph the count was 70 tools, 38 dependency edges, 122 directed alternative edges, 62 maintainers, 23 categories.

`GRAPH.DELETE` on a graph that does not exist yet returns "Invalid graph operation on empty key". The tests catch that and move on.

## The router, and the sentence that fooled it

With no API key the advisor is a router over those queries. It loads tool names and aliases from the graph, so "remix" resolves to `@remix-run/react` only because that alias was stored on the node. The first version treated any sentence containing "i use" as a memory write. "What should I use instead of moment?" contains those two words. The answer I got was "Saved in the user memory graph: USES moment", which is a terrible reply to an alternatives question. Questions are now classified before statements. "I use next and I prefer zod over yup" is still a write, split on "and", with the note "over yup" on the `PREFERS` edge.

Memory is a second graph, `mem_` plus the user id, because a FalkorDB edge cannot leave its graph. The preference points at a Tool node that is only a reference: name, ecosystem, `ref: true`. The transcript is `Session` to `Question` to `Answer`, and `USED_PATH` hangs off the answer onto the nodes the reply used. Restarting the API process does not clear it. The compose file mounts a volume at `/var/lib/falkordb/data`. I almost mounted `/data`, which in this image is a symlink to that directory. The server writes to the real directory. A volume has to land there or a restart looks like amnesia.

The model path is optional and untested against a live key here. If a base URL and key are set, the advisor still runs the router, then asks an OpenAI compatible endpoint to call the same tools. A failed call leaves the router text in place. The demo everyone can run is the router.

## What I would change next

The maintainer nodes are GitHub handles I associated with the packages in the editorial file. They are not a live read of the npm maintainer array. A refresh should update version and description without pretending it re-checked who owns the package.

TypeScript ranks high because several packages peer it. If `algo.pageRank` is missing, the fallback is in-degree: direct dependents in this corpus.

Seventy packages is a demo, not a registry mirror. The interesting part is that the answers stay inside the edges you can click. When the path is one hop, the UI should say one hop. When the only package that depends on moment in this corpus is sequelize, the blast radius is 1, not a story about the entire date ecosystem falling over.
