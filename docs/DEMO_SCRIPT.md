# Demo script

About three minutes. Start from a machine where `docker compose up -d` has already finished and <http://127.0.0.1:8091> loads. The header should show FalkorDB `ecosystem`, `rule router`, a tool count, and a scout signal count. No model key is required.

1. Say what the screen is. The left side is the question. The right side is the Cypher and the path. Both come from FalkorDB. If that database is stopped, this page cannot answer.

2. Click `What should I use instead of moment?`. Wait for the green answer. Point at the `ALTERNATIVE_TO` chips for dayjs, date-fns, and luxon, then at the deprecation signal whose source is the Moment project status page. Mention that label propagation on those edges names the community the procedure returned.

3. Click `What breaks if express is deprecated?`. The answer lists tools that reach express through `DEPENDS_ON` in 1 to 3 hops, including `@nestjs/platform-express`, sails, and `@feathersjs/express`. Point at the blast radius signal and say scout wrote it. The Cypher block is the path query, not a paragraph the model invented.

4. Click `Run scout`. A short note says how many signals were written. The evidence panel shows the `MERGE` that stores `blast_radius`. This is the second agent. It only shares state by writing nodes the advisor reads.

5. Click `Who maintains the libraries that next depends on?`. The answer names Vercel for next and Meta Open Source for react and react-dom. `next` 16.4.1 also peers `@playwright/test`, so Microsoft shows up. That edge is the registry peer dependency, not a guess.

6. Click `Show the path from next to react`. The path is one hop. The edge kind is peer.

7. Click `Which dependency is most critical in this graph?`. PageRank on `Tool` along `DEPENDS_ON` ranks the corpus. Read the top names off the screen. The scores are the procedure output for this graph.

8. Click `I use next and I prefer zod over yup`. Then click `What do I prefer?`. The second answer reads `USES` and `PREFERS` from the memory graph `mem_demo`.

9. If there is time, restart only the API container (`docker compose restart api`) and ask `What do I prefer?` again. The preference is still there because it lives in FalkorDB, on a volume, not in the Python process.
