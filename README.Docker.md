# Docker

The whole stack runs through `compose.yaml`: frontend, API, Python crawler, Redis, and SearXNG on the `search-net` bridge network.

## Start the stack

From the repository root:

```bash
docker compose up --build
```

Stop with `Ctrl+C`, or `docker compose down` to remove containers.

## Host ports

| Host | Container | Service |
| --- | --- | --- |
| `5173` | `80` | `search_frontend` (nginx serving the Vite build) |
| `5000` | `8080` | `search_api` (.NET 10) |
| `6379` | `6379` | `search_redis` |
| `8080` | `8080` | `searxng` |

The crawler has no published ports; it talks to Redis and SearXNG on the Docker network.

## Images

| Compose service | How it is built |
| --- | --- |
| `frontend` | Multi-stage: `node:22-alpine` runs `npm run build`, then `nginx:alpine` serves `dist/` on port 80. Context: `./search-frontend`. |
| `api` | Multi-stage: `mcr.microsoft.com/dotnet/sdk:10.0` publish, then `mcr.microsoft.com/dotnet/aspnet:10.0`. Listens on `8080`. Context: `./api/SearchEngineAPI/SearchEngineAPI`. |
| `crawler` | `python:3.11-slim`, installs `requirements.txt`, runs `python main.py`. Context: `./crawler`. |
| `redis` | `redis:alpine` |
| `searxng` | `searxng/searxng:latest`, config mounted from `./searxng` |

## Environment

Set in `compose.yaml` (or override with a `.env` file next to it):

| Variable | Used by | Purpose |
| --- | --- | --- |
| `ConnectionStrings__Redis` | API | Redis endpoint inside the network (`redis:6379`). |
| `AdminSettings__SecretKey` / `ADMIN_SECRET_KEY` | API | Bearer token for `DELETE /api/admin/flush`. Compose default: `mi_secreto_bearer_super_seguro_123`. |
| `REDIS_HOST` / `REDIS_PORT` | Crawler | Redis connection. |
| `SEARXNG_URL` | Crawler | SearXNG base URL (`http://searxng:8080`). |
| `SEARXNG_BASE_URL` / `SEARXNG_SECRET` | SearXNG | Public URL and instance secret. |

## Building a single image

Useful if you only need one service, or are pushing to a registry:

```bash
docker build -t crawler-engine-frontend ./search-frontend
docker build -t crawler-engine-api ./api/SearchEngineAPI/SearchEngineAPI
docker build -t crawler-engine-worker ./crawler
```

If the target host uses a different CPU architecture than your machine:

```bash
docker build --platform=linux/amd64 -t crawler-engine-api ./api/SearchEngineAPI/SearchEngineAPI
```

Then push to your registry (`docker push ...`). See Docker's [getting started](https://docs.docker.com/go/get-started-sharing/) docs for sharing images.
