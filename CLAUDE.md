# Content Assistant — AI Content Marketing Assistant
## Claude Code Project Context

This file gives Claude Code full architectural context for the Content Assistant project.
The codebase is **fully implemented**. Read this before modifying any code.

---

## Project Overview

Content Assistant is a production-ready multi-agent system that automates content creation
across multiple formats (research reports, SEO blogs, LinkedIn posts, AI images).
It uses LangGraph for agent orchestration, OpenAI GPT-4o as the primary LLM, and
Streamlit for the web interface.

**Package name**: `ai-content-assistant` (Python package: `ai_content_assistant`)
**Python version**: 3.13
**Package manager**: UV (`uv sync --native-tls` to install, `uv run` to execute)

---

## Folder Structure

```
ik-cont-assistant/
├── src/ai_content_assistant/
│   ├── agents/
│   │   ├── query_handler.py       # Classifier and router — entry point for all requests
│   │   ├── query_prompts.py       # System prompts for classification and follow-up detection
│   │   ├── research_agent.py      # Web research via SERP + synthesis via GPT-4o
│   │   ├── research_prompts.py    # Query extraction and synthesis prompts
│   │   ├── blog_writer.py         # SEO-optimized blog posts (streamed, 2000+ words)
│   │   ├── blog_prompts.py        # Blog generation and meta extraction prompts
│   │   ├── linkedin_writer.py     # LinkedIn posts with tone variants + hashtags
│   │   ├── linkedin_prompts.py    # Post, hashtag, and variants prompts
│   │   ├── image_generator.py     # DALL-E 3 image generation + prompt optimization
│   │   ├── image_prompts.py       # Prompt optimizer system prompt
│   │   ├── content_strategist.py  # Formats research into strategic content plans
│   │   └── strategist_prompts.py  # Research formatting and content plan prompts
│   ├── core/
│   │   ├── config.py              # Pydantic BaseSettings, env loading, logging config
│   │   ├── router.py              # LangGraph conditional routing functions + error handler
│   │   └── workflow.py            # process_request / stream_request Streamlit facades
│   ├── integrations/
│   │   ├── openai_client.py       # GPT-4o + DALL-E 3 wrapper with retry and streaming
│   │   ├── serp_client.py         # SERP API wrapper with TTL caching
│   │   ├── perplexity_client.py   # Perplexity Sonar fallback research client
│   │   └── image_clients.py       # Stability AI fallback image client
│   ├── web_app/
│   │   ├── streamlit_app.py       # Main Streamlit entry point
│   │   ├── components/
│   │   │   ├── sidebar.py         # Content type, tone, word count, keywords controls
│   │   │   ├── chat_panel.py      # Chat history and input area
│   │   │   └── content_preview.py # Generated content display + export buttons
│   │   └── static/
│   │       └── style.css
│   ├── utils/
│   │   ├── content_optimization.py # Keyword density, readability scoring, meta generation
│   │   ├── quality_validation.py   # Blog/LinkedIn validation + 0-100 quality score
│   │   ├── guardrails.py           # Input length, PII detection, OpenAI moderation, image safety
│   │   └── export_tools.py         # Export to Markdown (with frontmatter) or plain text
│   └── workflow/
│       ├── langgraph_workflow.py   # LangGraph StateGraph definition, build_graph, run/stream
│       └── state_management.py    # AgentState TypedDict, history reducer, helpers
├── tests/
│   ├── unit/
│   │   ├── agents/
│   │   │   ├── test_query_handler.py
│   │   │   └── test_blog_writer.py
│   │   ├── utils/
│   │   │   ├── test_quality_validation.py
│   │   │   └── test_content_optimization.py
│   │   ├── test_config.py
│   │   └── test_state_management.py
│   ├── integration/
│   │   └── test_workflow.py        # Full LangGraph workflow with mocked APIs
│   └── e2e/
│       └── test_streamlit_smoke.py # Import, instantiation, and graph-build smoke tests
├── config/
│   ├── development.yaml
│   ├── production.yaml
│   └── services.yaml               # API base URLs, model names, timeouts
├── pyproject.toml                  # Project metadata + dependencies (managed by UV)
├── uv.lock
├── Dockerfile
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## The Six Agents

All agents are Python classes with a consistent async interface: `run(state: AgentState) -> AgentState`.

### 1. Query Handler Agent (`query_handler.py`)
- **Role**: Classifier and router — the entry point for all user requests
- **Logic**: Uses `gpt-4o-mini` (JSON mode) to classify intent
- **Output**: Sets `state["next_agent"]` to one of: `research`, `blog`, `linkedin`, `image`, `content_strategist`
- **Key methods**: `classify_intent(user_message: str) -> str`, `detect_followup(state) -> bool`
- **Also handles**: Follow-up detection — runs classification and follow-up check in parallel

### 2. Deep Research Agent (`research_agent.py`)
- **Role**: Conducts web research and synthesizes findings
- **Primary tool**: SERP API; automatic fallback to Perplexity Sonar on exception
- **Output**: Structured research report with sources
- **Key methods**: `search(query: str) -> list[dict]`, `synthesize(query, results) -> str`
- **State fields written**: `state["research_output"]`, `state["sources"]`
- **Caching**: Synthesis results cached by MD5(query + URLs), 1-hour TTL, 200-entry max
- **Follow-up behavior**: Reuses existing `research_output` when `is_followup=True`

### 3. SEO Blog Writer Agent (`blog_writer.py`)
- **Role**: Creates long-form, search-optimized blog posts (2000+ words)
- **Inputs**: Topic + optional research output from state (first 3000 chars)
- **Output format**: Streamed Markdown with YAML frontmatter (title, meta_description, keywords, slug)
- **Key methods**: `write_blog(topic, research) -> AsyncIterator[str]`, `generate_meta(content) -> dict`
- **Post-processing**: Validates blog, scores readability, adds metadata to state

### 4. LinkedIn Post Writer Agent (`linkedin_writer.py`)
- **Role**: Creates engaging professional LinkedIn posts (≤3000 chars)
- **Style**: Hook in first line, value-driven body, CTA, 5–8 relevant hashtags
- **Tone variants**: Generates 3 variants (professional, conversational, casual) in one call
- **Key methods**: `write_post(topic, tone) -> str`, `generate_hashtags(topic) -> list[str]`, `generate_variants(topic) -> dict`
- **Parallelism**: All 3 tasks (post, hashtags, variants) run in parallel

### 5. Image Generation Agent (`image_generator.py`)
- **Role**: Generates images via DALL-E 3 with optimized prompts
- **Prompt optimization**: Uses `gpt-4o-mini` to expand brief intent into detailed DALL-E prompt
- **Fallback**: Stability AI if `STABILITY_API_KEY` is configured
- **Key methods**: `optimize_prompt(user_intent) -> str`, `generate(prompt) -> dict`
- **State fields written**: `state["metadata"]["image_url"]`, `state["metadata"]["prompt_used"]`, `state["metadata"]["image_source"]`

### 6. Content Strategist Agent (`content_strategist.py`)
- **Role**: Formats and structures research into readable strategic content
- **Use case**: Content plans, content calendars, formatted research reports
- **Key methods**: `format_research(raw) -> str`, `create_content_plan(topic, research) -> str`
- **Logic**: If `research_output` exists, formats it; otherwise creates a new content plan from scratch

---

## LangGraph Workflow

`StateGraph` from `langgraph.graph`. Shared state is a `TypedDict` with a custom history reducer.

```python
# src/ai_content_assistant/workflow/state_management.py

from typing import TypedDict, Optional, Annotated, Literal

ContentType = Literal["blog", "linkedin", "image", "research", "strategy"]

class AgentState(TypedDict):
    user_message: str
    conversation_history: Annotated[list[ConversationMessage], _merge_history]  # capped at 5
    next_agent: Optional[str]
    research_output: Optional[str]
    sources: Optional[list[str]]
    final_content: Optional[str]
    content_type: Optional[ContentType]
    error: Optional[str]
    metadata: Optional[dict]   # SEO meta, image URL, hashtags, quality score, variants, etc.
```

**Graph topology** (`langgraph_workflow.py`):
```
START → query_handler
query_handler → (conditional) research | blog | linkedin | image | content_strategist | error_handler
research → (conditional) content_strategist | END
blog | linkedin | image | content_strategist | error_handler → END
```

**Routing**: `route_after_query_handler()` and `route_after_research()` in `core/router.py`.
**Error handling**: Every agent's `run()` is wrapped in `_make_node()` which catches all exceptions,
sets `state["error"]`, and routes to `error_handler` which converts errors to user-friendly messages.

---

## Core Configuration (`src/core/config.py`)

All secrets loaded from environment variables via `pydantic-settings`. Never hardcode keys.

```python
class Settings(BaseSettings):
    # Required
    openai_api_key: str
    serp_api_key: str

    # Optional (fallbacks)
    perplexity_api_key: Optional[str] = None
    stability_api_key: Optional[str] = None

    # Model routing (two-tier strategy)
    default_model: str = "gpt-4o"          # heavy generation
    fast_model: str = "gpt-4o-mini"        # classification, metadata, hashtags
    image_model: str = "dall-e-3"

    # Content generation defaults
    max_research_results: int = 10
    blog_target_word_count: int = 2000
    linkedin_max_chars: int = 3000

    # Guardrails
    max_input_length: int = 2000
    max_requests_per_hour: int = 20

    env: str = "development"
    log_level: str = "INFO"
```

Module-level singleton: `settings = Settings()` — import this everywhere, don't re-instantiate.

---

## Integration Clients

All clients expose module-level singletons (e.g., `openai_client`, `serp_client`).

### OpenAI Client (`openai_client.py`)
- `chat_complete(messages, model, temperature, max_tokens, json_mode) -> tuple[str, dict]`
- `chat_stream(messages, model, max_tokens) -> AsyncIterator[str]`
- `generate_image(prompt, size, quality) -> dict`
- Retry: `@retry` from `tenacity`, 3 attempts, exponential backoff on `RateLimitError`
- Logs token usage per call

### SERP Client (`serp_client.py`)
- `search(query, num_results) -> list[dict]` — returns `[{title, url, snippet}]`
- TTL cache: 1-hour, 100-entry max, keyed by MD5(query:num_results)

### Perplexity Client (`perplexity_client.py`)
- `research(query) -> tuple[str, list[str]]` — returns `(answer_text, source_urls)`
- Uses `sonar-pro` model via Perplexity's OpenAI-compatible endpoint
- Gracefully returns `("", [])` if `PERPLEXITY_API_KEY` is not set

### Stability AI Client (`image_clients.py`)
- `generate(prompt, width, height) -> str` — returns base64-encoded PNG
- Raises `RuntimeError` if `STABILITY_API_KEY` is not configured

---

## Guardrails (`src/utils/guardrails.py`)

Called from `streamlit_app.py` before every request and from `image_generator.py` before generation.

- `check_input_length(text)` — raises `InputTooLongError` if `len > max_input_length`
- `detect_pii(text) -> list[str]` — regex detection for email, phone, SSN, credit card (non-raising)
- `check_moderation(text)` / `async_check_moderation(text)` — OpenAI Moderation API, raises `ContentFlaggedError`
- `check_image_prompt(prompt)` — deny-list keyword check, raises `ImageSafetyError`

---

## Content Optimization (`src/utils/content_optimization.py`)

- `calculate_keyword_density(text, keyword) -> float` — keyword frequency as % of word count
- `score_readability(text) -> dict` — `{flesch_kincaid_grade, avg_sentence_length}`
- `suggest_headings(content) -> list[str]` — extracts existing H2/H3 headings
- `generate_meta_description(content, keyword) -> str` — async, gpt-4o-mini, max 160 chars

## Quality Validation (`src/utils/quality_validation.py`)

- `validate_blog(content) -> dict` — `{passed, score, issues}` — checks word count (1500+), H1, H2s (3+), frontmatter
- `validate_linkedin(content) -> dict` — `{passed, score, issues}` — checks length (≤3000), hashtags (5–8), hook
- `score_content(content, content_type) -> int` — 0–100 quality score

---

## Streamlit UI (`src/web_app/streamlit_app.py`)

Layout: sidebar (settings) + two-column (chat history | content preview).

- **Input validation**: `_validate_input()` runs guardrails + rate limiting before every submit
- **Workflow execution**: `_run_workflow()` calls `stream_request()` via `asyncio.run_coroutine_threadsafe`; streams `(node_name, delta)` to `st.status()` for live progress
- **Preview panel**: Quality score badge, source links, LinkedIn tone variants, export buttons (.md + .txt)
- **State management**: `st.session_state` for messages, agent_history, current_state, tone, word_count, keywords

---

## Coding Standards

- **Python 3.13**
- **Type hints everywhere** — use `TypedDict`, `Optional`, `Annotated` from `typing`
- **Async for all API calls** — use `async/await`
- **Logging**: `logging` module only. DEBUG for API calls, INFO for agent transitions, ERROR for failures
- **Docstrings**: One-line docstring on every class and public method
- **Error messages**: Always include the agent name and operation in error strings
- **Prompts**: All system prompts live in companion `*_prompts.py` files per agent, not inline

---

## Prompt Engineering Guidelines

All agent prompts follow this structure:
1. **Role**: "You are an expert [role]..."
2. **Task**: Clear description of what to produce
3. **Constraints**: Format, length, tone, platform rules
4. **Output format**: Specify exact structure (Markdown, JSON, etc.)

Prompts are stored as module-level string constants in `*_prompts.py` companion files.
Never inline prompts in agent `run()` methods.

---

## Testing Approach

- **Unit tests** (22 tests): Core config, state management, 2 agents, 2 utility modules — all with mocked API calls
- **Integration tests** (3 tests): Full LangGraph workflow with mocked LLM and SERP clients
- **E2E tests** (3 tests): Streamlit import smoke tests + graph compilation check
- **Total: 28 tests**

```bash
# All tests with coverage
uv run pytest tests/ --cov=src/ai_content_assistant --cov-report=term-missing

# Unit tests only
uv run pytest tests/unit/ -v

# Integration tests (mocked APIs)
uv run pytest tests/integration/ -v
```

**Not yet covered by unit tests**: LinkedInWriter, ImageGenerator, ContentStrategist, ResearchAgent,
integration clients, guardrails, export tools. These are covered only at integration/e2e level.

---

## Dependencies (`pyproject.toml`)

```
langgraph, langchain, langchain-openai
openai
streamlit
google-search-results      # serpapi
httpx
pydantic, pydantic-settings
python-dotenv, pyyaml
tenacity                   # retry logic
cachetools                 # TTL cache for SERP and synthesis results
pytest, pytest-asyncio, pytest-cov, ruff  (dev)
```
