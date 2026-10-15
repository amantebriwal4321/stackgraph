# Deploy

There is no hosted URL in this repo. Local `docker compose up -d` is the setup judges can run without accounts. A public deploy needs two accounts Aman creates. Do not invent a hostname.

## Local

Follow the setup section in the README. The UI binds to port 8091. FalkorDB has no password in the compose file. Do not expose port 6379 on a public host without adding a password in the image environment and setting `FALKORDB_PASSWORD` on the API.

## FalkorDB Cloud

Free tier notes below are from FalkorDB's free tier doc (fetched 15 Oct 2026): <https://docs.falkordb.com/cloud/free-tier.html>.

* Sign up at <https://app.falkordb.cloud/signup>. The doc says the free tier does not require a credit card.
* Create a free instance. The doc says 100 MB RAM, also the max graph size, on AWS or GCP.
* The doc says a free instance that is idle for 1 day is stopped, and deleted after 7 days. It also says the free tier has no snapshots and no backups. Export an RDB if you need a copy. Do not treat a free instance as durable storage for the demo.
* The same doc says the free tier does not include TLS. Leave `FALKORDB_SSL` unset or `false` unless the dashboard shows otherwise.
* Copy the host, port, username, and password from the instance page.

The API reads `FALKORDB_HOST`, `FALKORDB_PORT`, `FALKORDB_USERNAME`, `FALKORDB_PASSWORD`, and optional `FALKORDB_URL`.

## Render

Render can build the Dockerfile. This is a web service, not a static site.

1. Push the repo to a public remote Render can see.
2. New Web Service, Docker runtime, root directory the repo root.
3. The container listens on 8091. Set Render's port to 8091 if it asks, or set `PORT` only if you also change the process command. The image command already passes port 8091.
4. Environment:
   * `FALKORDB_HOST` from the cloud dashboard
   * `FALKORDB_PORT` from the dashboard
   * `FALKORDB_PASSWORD` from the dashboard
   * `FALKORDB_USERNAME` if the dashboard shows one
   * `STACKGRAPH_GRAPH` = `ecosystem`
   * Leave `LLM_API_KEY` empty for the rule router
5. Deploy. The first request loads `seed/catalog.json` and runs scout. Open `/api/health` and confirm `falkordb` is `up` and `mode` is `fallback`.
6. Put the resulting `https://` host into the submission form. Until that exists, the submission link is the local setup.

Free web services on Render sleep. Combined with FalkorDB free tier idle stop, a judge who opens the URL a day later may find both sides down. The README local setup is the reliable path.
