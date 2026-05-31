# Deployment Guide

How to run the AI Content Assistant locally, in Docker, and notes for cloud
deployment. Configuration values referenced here are defined in
[`core/config.py`](../src/ai_content_assistant/core/config.py) and
[`.env.example`](../.env.example).

---

## 1. Prerequisites

- **Python 3.13** (pinned in `.python-version`)
- **UV** package manager — `pip install uv`
- API keys:
  - `OPENAI_API_KEY` *(required)*
  - `SERP_API_KEY` *(required)*
  - `PERPLEXITY_API_KEY` *(optional — research fallback)*
  - `STABILITY_API_KEY` *(optional — image fallback)*

---

## 2. Environment Configuration

```bash
cp .env.example .env
# edit .env and fill in at least OPENAI_API_KEY and SERP_API_KEY
```

The app **fails fast at startup** if a required key is missing or empty
(`Settings` validation in `core/config.py`). Optional keys may be left blank —
the corresponding fallback is simply disabled and the system degrades gracefully.

Model selection is environment-driven:

```ini
DEFAULT_MODEL=gpt-4o        # heavy generation
FAST_MODEL=gpt-4o-mini      # classification, meta, hashtags
IMAGE_MODEL=gpt-image-1     # or dall-e-3
```

> **Image model caveat:** `gpt-image-1` may require a **verified OpenAI
> organization**. If image generation returns an organization-verification error,
> either verify your org in the OpenAI dashboard or set `IMAGE_MODEL=dall-e-3`.

---

## 3. Local Development

```bash
# Install dependencies (creates .venv)
uv sync
# On corporate networks with SSL inspection:
#   uv sync --native-tls

# Launch the Streamlit app
uv run streamlit run src/ai_content_assistant/web_app/streamlit_app.py
```

The app serves on **http://localhost:8501**.

### Running tests

```bash
uv run pytest tests/ -q                                   # all 40 tests
uv run pytest tests/ --cov=src/ai_content_assistant       # with coverage
uv run pytest tests/unit/ -v                              # unit only
uv run pytest tests/integration/ -v                       # mocked-API integration
```

All API calls are mocked in tests — no keys required to run the suite.

---

## 4. Docker Deployment

The [`Dockerfile`](../Dockerfile) is a two-stage build (UV builder → lean
`python:3.13-slim` runtime) and includes a Streamlit health check on
`/_stcore/health`.

```bash
# Build and start (reads keys from .env via docker-compose)
docker compose up --build

# Run detached
docker compose up -d

# Logs
docker compose logs -f

# Stop
docker compose down
```

[`docker-compose.yml`](../docker-compose.yml):
- Maps host **8501 → 8501**
- Loads secrets from `.env` (`env_file`)
- Mounts `./config` read-only into the container
- `restart: unless-stopped` with the same health check

To build the image directly:

```bash
docker build --target runtime -t ai-content-assistant:latest .
docker run -p 8501:8501 --env-file .env ai-content-assistant:latest
```

---

## 5. SSL on Corporate Networks

Environments with TLS inspection can break outbound HTTPS to OpenAI/SERP. A helper
exports the Windows trust store to a CA bundle:

```bash
uv run python scripts/export_win_certs.py
# then set the printed path in .env:
#   SSL_CERT_FILE=/absolute/path/to/certs/ca_bundle.pem
```

Note: the OpenAI client deliberately uses the synchronous SDK on an executor
thread to sidestep an async httpx/SSL issue under Streamlit's event loop on
Windows (see `integrations/openai_client.py`).

---

## 6. Configuration Profiles

`config/development.yaml` and `config/production.yaml` hold environment-specific
settings; `config/services.yaml` holds API base URLs, model names, and timeouts.
Select the profile with the `ENV` variable (`development` | `production`).

---

## 7. Cloud Deployment Notes

The app is stateless at the graph level (the compiled graph is a singleton; all
request state lives in `AgentState`), so it scales horizontally **once session
state is externalized**:

- **Session state** is currently in-memory (`st.session_state`, per browser
  session). For multiple replicas behind a load balancer, move conversation
  history/session data to Redis or PostgreSQL, or pin sessions with sticky routing.
- **Caches** (SERP TTL cache, research synthesis cache) are per-process; a shared
  cache (Redis) avoids duplicate spend across replicas.
- **Secrets** should come from the platform secret manager, not a baked-in `.env`.
- **Health check** — point the platform probe at `/_stcore/health` (already wired
  in the Dockerfile/compose).
- Reference targets from the project brief: LangGraph Cloud, Modal (GPU image
  generation), Vercel (frontend), with LangSmith/Helicone for observability.

---

## 8. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| App won't start, `ValidationError` | Missing `OPENAI_API_KEY`/`SERP_API_KEY` | Fill them in `.env` |
| Image generation error mentioning verification | `gpt-image-1` org not verified | Verify org, or `IMAGE_MODEL=dall-e-3` |
| SSL / certificate errors | Corporate TLS inspection | Run `export_win_certs.py`, set `SSL_CERT_FILE` |
| Research returns nothing | SERP failing and no Perplexity key | Add `PERPLEXITY_API_KEY` or check `SERP_API_KEY` |
| "Rate limit reached" in UI | `max_requests_per_hour` (20) hit | Wait, or raise `MAX_REQUESTS_PER_HOUR` |
| Empty content + friendly error | Model returned empty output | Retry; `_make_node` surfaces this explicitly |
