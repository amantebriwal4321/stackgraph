# Deploy

The hosted demo is <https://stackgraph.onrender.com>, deployed from `Dockerfile.render` on Render's free plan (Singapore). Local `docker compose up -d` is the setup judges can run without accounts.

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

## Render, one container

`Dockerfile.render` uses `falkordb/falkordb` as its base image. The process starts FalkorDB on localhost inside the container, then starts the API on the `PORT` value Render injects. On startup the API MERGEs `seed/catalog.json` and runs scout. No FalkorDB Cloud account is required. Leave `LLM_API_KEY` empty so the rule router is used.

Local check:

```
docker build -f Dockerfile.render -t stackgraph-render .
docker run -e PORT=8091 -p 8091:8091 stackgraph-render
```

Open <http://127.0.0.1:8091/api/health>. `falkordb` should be `up` and `mode` should be `fallback`.

On Render:

1. Push the repo to a public remote Render can see.
2. New Web Service. Environment: Docker. Root directory: the repo root.
3. Set the Dockerfile path to `Dockerfile.render`.
4. Do not set `FALKORDB_HOST`. The entrypoint forces localhost. Do not publish a Redis port. Only the HTTP port Render assigns is public.
5. Deploy. The first boot installs nothing extra at runtime. The image already contains Python, the app, and the seed.
6. Open `/api/health` on the host Render prints. Put that `https://` URL in the submission form once it exists. This repo does not invent one.

The free web service sleeps, and its disk goes away when the instance is replaced. The seed loads again on the next boot. Preferences written to the memory graph do not survive a new container. The compose file with a named volume is the setup that keeps memory across restarts.

## Render plus FalkorDB Cloud

Use the root `Dockerfile` only if FalkorDB runs somewhere else.

1. New Web Service, Docker, root `Dockerfile` (not `Dockerfile.render`).
2. The API process in that image listens on 8091, not on `PORT`.
3. Environment from the FalkorDB Cloud dashboard: `FALKORDB_HOST`, `FALKORDB_PORT`, `FALKORDB_PASSWORD`, and `FALKORDB_USERNAME` if one is shown. Set `STACKGRAPH_GRAPH` to `ecosystem`. Leave `LLM_API_KEY` empty.
4. Deploy and check `/api/health`.

Free web services on Render sleep. Combined with the FalkorDB free tier idle stop described above, a judge who opens the URL a day later may find both sides down. The README local setup is the reliable path.
