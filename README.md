# Search Engine Crawler

A containerized search pipeline: a C# API accepts a query, Redis coordinates work and cache, and a Python worker crawls the web. Results are stored in Redis so the API can return them to the client.

## How it works

1. A client calls the C# API with a search term (`GET /api/search?q=...`).
2. The API looks up a Redis cache key (`crawl:{term}`).
3. **Cache miss:** the API pushes the term onto the Redis list `queue:crawling` and responds with `202 Accepted` (job pending).
4. The Python worker blocks on that queue (`BRPOP`), crawls the term, and writes processed page data back to Redis under `crawl:{term}` (1-hour TTL).
5. **Cache hit:** the API deserializes the cached crawl results, filters them against the query, and returns them to the user.

SearXNG supplies the initial result URLs. The Python crawler then fetches those pages (and a limited set of outbound links), extracts title, description, headings, and cleaned text, and skips a blocklist of noisy domains.

```
Client  -->  .NET API  -->  Redis queue (queue:crawling)
                 ^                    |
                 |                    v
                 |              Python worker
                 |                    |
                 |              SearXNG /search
                 |                    |
                 +------ Redis cache (crawl:*) <--+
```

## Services

| Service | Role |
| --- | --- |
| **search_api** | ASP.NET Core API. Enqueues jobs, reads cache, returns results. Host port `5000` maps to container port `8080`. |
| **search_worker** | Python asyncio crawler. Listens to `queue:crawling`, crawls, writes `crawl:*`. |
| **search_redis** | Job queue, result cache, and short-lived processing locks. Port `6379`. |
| **searxng** | Meta-search backend the worker queries for seed URLs. Port `8080`. |

All services share the Docker network `search-net` (see `compose.yaml`).

## Redis keys

| Key | Type | Purpose |
| --- | --- | --- |
| `queue:crawling` | List | Async job queue. API `LPUSH`es terms; worker `BRPOP`s them. |
| `crawl:{term}` | String (JSON) | Cached crawl payload. Term is lowercased with spaces as `_`. TTL 3600s. |
| `processing:{term}` | String | NX lock so duplicate jobs for the same term are skipped while a crawl is in progress. |

## API

Base URL when running with Compose: `http://localhost:5000`

### Search

```http
GET /api/search?q=laptop
```

- Missing `q`: `400 Bad Request`.
- No cache yet: `202 Accepted` and the term is queued for the Python worker. Call the same URL again after the crawl finishes.
- Cache present: `200 OK` with filtered crawl results (title, description, and body text matched against the query words).

### Redis health check

```http
GET /test-redis
```

Pings Redis and attempts to read a sample cache key.

### Flush cache (admin)

```http
DELETE /api/admin/flush
Authorization: Bearer <ADMIN_SECRET_KEY>
```

Flushes Redis database 0. Set `ADMIN_SECRET_KEY` in the environment (Compose default is shown in `compose.yaml`).

## Run locally

Requires Docker and Docker Compose.

```bash
docker compose up --build
```

- API: http://localhost:5000
- SearXNG: http://localhost:8080
- Redis: localhost:6379

Typical first-search flow:

1. `GET http://localhost:5000/api/search?q=your+term` → `202` while the worker crawls.
2. Repeat the request → `200` with cached, filtered results.

## Project layout

```
.
├── compose.yaml
├── api/SearchEngineAPI/SearchEngineAPI   # C# API + Dockerfile
├── crawler                               # Python worker (main.py, crawler.py)
└── searxng/settings.yml                  # SearXNG config
```

- `api/.../Program.cs` — search, queue push, cache read, admin flush.
- `crawler/main.py` — Redis listener, SearXNG seed query, save-to-cache.
- `crawler/crawler.py` — concurrent page fetch and HTML extraction.
