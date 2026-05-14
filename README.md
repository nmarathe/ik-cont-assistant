# AI Content Assistant

A production-ready multi-agent AI system for content marketing — research, SEO blogs, LinkedIn posts, and AI-generated images — powered by LangGraph, OpenAI GPT-4o, and Streamlit.

---

## Architecture

```
User → Streamlit UI → LangGraph Workflow
                             │
                    ┌────────▼────────┐
                    │  Query Handler  │  (classifies intent)
                    └────────┬────────┘
                             │
           ┌─────────────────┼──────────────────────┐
           │                 │                       │
    ┌──────▼──────┐  ┌───────▼──────┐  ┌────────────▼───────┐
    │  Research   │  │  Blog Writer │  │  LinkedIn Writer   │
    │   Agent     │  │              │  │                    │
    └──────┬──────┘  └──────────────┘  └────────────────────┘
           │
    ┌──────▼──────────┐    ┌──────────────┐   ┌───────────────┐
    │Content Strategist│   │Image Generator│   │ Error Handler │
    └─────────────────┘    └──────────────┘   └───────────────┘
```

### Tech Stack

| Component | Primary Tech | Alternative | Purpose |
|-----------|-------------|-------------|---------|
| Multi-Agent System | LangGraph | CrewAI, AutoGen | Agent orchestration |
| Language Model | OpenAI GPT-4o | Claude Sonnet, Gemini | Content generation |
| Fast Model | GPT-4o-mini | — | Classification, metadata |
| Research Engine | SERP API | Perplexity Sonar | Web search |
| Image Generation | DALL-E 3 | Stability AI | Visual content |
| Web Interface | Streamlit | Gradio, React | User interaction |
| Package Manager | UV | pip, Poetry | Dependency management |

---

## Prerequisites

- **Python 3.13+**
- **UV** — `pip install uv`
- API Keys (see below)

---

## Setup

```bash
# 1. Clone and enter the project
git clone <repo-url>
cd ik-cont-assistant

# 2. Copy and fill in environment variables
cp .env.example .env
# Edit .env with your API keys

# 3. Install dependencies
uv sync --native-tls

# 4. Launch the app
uv run streamlit run src/ai_content_assistant/web_app/streamlit_app.py
```

Open `http://localhost:8501` in your browser.

---

## API Keys

| Key | Where to Get | Required? |
|-----|-------------|-----------|
| `OPENAI_API_KEY` | platform.openai.com/api-keys | **Yes** |
| `SERP_API_KEY` | serpapi.com | **Yes** |
| `PERPLEXITY_API_KEY` | perplexity.ai/settings/api | No (fallback) |
| `STABILITY_API_KEY` | platform.stability.ai | No (image fallback) |

---

## Usage Examples

| Request | Agent Triggered | Output |
|---------|----------------|--------|
| `Research AI trends in 2025` | Research Agent | Structured report with sources |
| `Write a blog post about machine learning for beginners` | Blog Writer | 2000-word SEO blog with frontmatter |
| `Create a LinkedIn post about my product launch` | LinkedIn Writer | Post + 3 tone variants + hashtags |
| `Generate an image of a futuristic office` | Image Generator | DALL-E 3 image |
| `Create a content calendar for Q3` | Content Strategist | 4-week content plan |

---

## Agent Reference

| Agent | Model | max_tokens | JSON Mode |
|-------|-------|-----------|-----------|
| Query Handler (classify) | gpt-4o-mini | 10 | Yes |
| Query Handler (follow-up) | gpt-4o-mini | 20 | Yes |
| Research Synthesis | gpt-4o | 1500 | No |
| Blog Writer | gpt-4o | 3500 | No (streamed) |
| Blog Meta Extractor | gpt-4o-mini | 200 | Yes |
| LinkedIn Post | gpt-4o | 600 | No |
| LinkedIn Hashtags | gpt-4o-mini | 100 | Yes |
| LinkedIn Variants | gpt-4o | 1500 | Yes |
| DALL-E Prompt Optimizer | gpt-4o-mini | 300 | No |
| Content Strategist | gpt-4o | 1500 | No |

---

## Token Optimization

- **Two-tier model routing**: `gpt-4o-mini` for lightweight tasks, `gpt-4o` for generation
- **JSON mode** for all structured outputs — eliminates verbose parsing
- **Conversation history cap**: Only the last 5 messages are passed to agents
- **Research caching**: SERP results cached for 1 hour; synthesis results cached by query hash
- **Follow-up detection**: Existing research is reused on refinement requests
- **Streaming**: Blog and research outputs stream progressively

---

## Running Tests

```bash
# All tests with coverage
uv run pytest tests/ --cov=src/ai_content_assistant --cov-report=term-missing

# Unit tests only
uv run pytest tests/unit/ -v

# Integration tests (mocked APIs)
uv run pytest tests/integration/ -v
```

---

## Docker Deployment

```bash
# Build and start
docker compose up --build

# Run in background
docker compose up -d

# View logs
docker compose logs -f

# Stop
docker compose down
```

The app will be available at `http://localhost:8501`.

> **Note**: Copy `.env.example` to `.env` and fill in your API keys before running Docker.

---

## Troubleshooting

| Issue | Cause | Fix |
|-------|-------|-----|
| `ValidationError: openai_api_key` | Missing `.env` | `cp .env.example .env` and fill in keys |
| `httpx.ConnectError` on SERP | Network/key issue | Verify `SERP_API_KEY`; Perplexity auto-activates as fallback |
| `openai.RateLimitError` | API quota | Retry is automatic (3 attempts); check OpenAI usage dashboard |
| `uv sync` SSL error | Corporate proxy/cert | Add `--native-tls` flag: `uv sync --native-tls` |
| Image URL expired | DALL-E URLs expire | Regenerate the image (URLs valid for ~1 hour) |

---

## Project Structure

```
src/ai_content_assistant/
├── agents/              Six specialized agents + companion prompt files
├── core/                Config, router, workflow facade
├── integrations/        OpenAI, SERP, Perplexity, Stability AI clients
├── utils/               Content optimization, quality validation, export
├── web_app/             Streamlit app + UI components
└── workflow/            AgentState TypedDict + LangGraph graph

config/                  Per-environment YAML config
tests/                   Unit, integration, and e2e test suites
Dockerfile               Multi-stage production container image
docker-compose.yml       Single-command deployment
```

---

## Contributing

- Code style: `uv run ruff check src/ tests/`
- All public methods require type hints
- New agents must implement `async def run(self, state: AgentState) -> AgentState`
- New features require unit tests with mocked API calls
