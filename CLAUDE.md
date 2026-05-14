# ContentAlchemy — AI Content Marketing Assistant
## Claude Code Project Context

This file gives Claude Code full architectural context for building ContentAlchemy,
a multi-agent AI content marketing system. Read this before generating any code.

---

## Project Overview

ContentAlchemy is a production-ready multi-agent system that automates content creation
across multiple formats (research reports, SEO blogs, LinkedIn posts, AI images).
It uses LangGraph for agent orchestration, OpenAI GPT-4 as the primary LLM, and
Streamlit for the web interface.

---

## Folder Structure

```
contentalchemy/
├── src/
│   ├── agents/
│   │   ├── query_handler.py       # Routes requests to the right agent
│   │   ├── research_agent.py      # Deep web research + analysis
│   │   ├── blog_writer.py         # SEO-optimized long-form blog posts
│   │   ├── linkedin_writer.py     # LinkedIn posts with hashtag strategy
│   │   ├── image_generator.py     # DALL-E 3 image generation + prompt optimization
│   │   └── content_strategist.py  # Formats research into readable content
│   ├── core/
│   │   ├── config.py              # Centralized config, API keys, env loading
│   │   ├── router.py              # LLM-based intent classification & routing
│   │   └── workflow.py            # LangGraph graph definition & compilation
│   ├── integrations/
│   │   ├── openai_client.py       # GPT-4 + DALL-E 3 wrapper with retry logic
│   │   ├── serp_client.py         # SERP API wrapper for web search
│   │   ├── perplexity_client.py   # Perplexity Sonar fallback research client
│   │   └── image_clients.py       # Fallback image clients (Stability AI, etc.)
│   ├── web_app/
│   │   ├── streamlit_app.py       # Main Streamlit UI entry point
│   │   ├── components/            # Reusable Streamlit UI components
│   │   └── static/                # CSS, images, assets
│   ├── utils/
│   │   ├── content_optimization.py # SEO scoring, keyword density, meta tags
│   │   ├── quality_validation.py   # Content quality checks and scoring
│   │   └── export_tools.py         # Export to markdown, PDF, etc.
│   └── workflow/
│       ├── langgraph_workflow.py   # Full LangGraph StateGraph definition
│       └── state_management.py    # Conversation memory and session state
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── config/
│   ├── development.yaml
│   ├── production.yaml
│   └── services.yaml
├── docs/
│   ├── architecture.md
│   ├── api_documentation.md
│   └── deployment_guide.md
├── requirements.txt
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## The Six Agents

Build each agent as a Python class with a consistent interface: `run(state: AgentState) -> AgentState`.

### 1. Query Handler Agent (`query_handler.py`)
- **Role**: Classifier and router — the entry point for all user requests
- **Logic**: Uses GPT-4 with a classification prompt to detect intent
- **Output**: Sets `state["next_agent"]` to one of: `research`, `blog`, `linkedin`, `image`, `strategy`
- **Key method**: `classify_intent(user_message: str) -> str`
- **Also handles**: Follow-up detection (is this a refinement of the last request?)

### 2. Deep Research Agent (`research_agent.py`)
- **Role**: Conducts web research and synthesizes findings
- **Primary tool**: SERP API for Google search results
- **Fallback tool**: Perplexity Sonar API
- **Output**: Structured research report with sources, key findings, and summary
- **Key methods**: `search(query: str)`, `synthesize(results: list) -> str`
- **State fields it writes**: `state["research_output"]`, `state["sources"]`

### 3. SEO Blog Writer Agent (`blog_writer.py`)
- **Role**: Creates long-form, search-optimized blog posts (1500–2500 words)
- **Inputs**: Topic + optional research output from state
- **SEO features**: Keyword placement in H1/H2, meta description generation, internal link suggestions
- **Output format**: Markdown with frontmatter (title, meta_description, keywords, slug)
- **Key methods**: `write_blog(topic: str, research: str) -> str`, `generate_meta(content: str) -> dict`

### 4. LinkedIn Post Writer Agent (`linkedin_writer.py`)
- **Role**: Creates engaging professional LinkedIn posts (150–300 words)
- **Style**: Hook in first line, value-driven body, CTA, 5–8 relevant hashtags
- **Variations**: Can generate 3 tone variants (professional, conversational, thought-leadership)
- **Key methods**: `write_post(topic: str, tone: str) -> str`, `generate_hashtags(topic: str) -> list`

### 5. Image Generation Agent (`image_generator.py`)
- **Role**: Generates images via DALL-E 3 with optimized prompts
- **Prompt optimization**: Uses GPT-4 to expand user intent into a detailed DALL-E prompt
- **Fallback**: Stability AI API if DALL-E is unavailable
- **Output**: Image URL or base64, plus the prompt used
- **Key methods**: `optimize_prompt(user_intent: str) -> str`, `generate(prompt: str) -> dict`

### 6. Content Strategist Agent (`content_strategist.py`)
- **Role**: Formats and structures research into readable strategic content
- **Use case**: When user wants a content plan, content calendar, or formatted report
- **Output**: Structured markdown document with sections, key takeaways, and action items
- **Key methods**: `format_research(raw: str) -> str`, `create_content_plan(topic: str) -> str`

---

## LangGraph Workflow

Use `StateGraph` from `langgraph.graph`. The shared state is a TypedDict.

```python
# src/workflow/langgraph_workflow.py — reference pattern

from langgraph.graph import StateGraph, END
from typing import TypedDict, Optional, List

class AgentState(TypedDict):
    user_message: str
    conversation_history: List[dict]
    next_agent: Optional[str]
    research_output: Optional[str]
    sources: Optional[List[str]]
    final_content: Optional[str]
    content_type: Optional[str]       # "blog" | "linkedin" | "image" | "research" | "strategy"
    error: Optional[str]
    metadata: Optional[dict]          # SEO meta, image URL, hashtags, etc.

# Graph edges:
# START -> query_handler -> [research | blog | linkedin | image | strategy | END]
# research -> content_strategist (optional post-processing)
# All terminal agents -> END
```

**Conditional routing** is done via `add_conditional_edges` based on `state["next_agent"]`.

**Error handling**: Wrap each agent's `run()` in try/except. On failure, set `state["error"]`
and route to a graceful fallback response node.

---

## Core Configuration (`src/core/config.py`)

Load all secrets from environment variables. Never hardcode keys.

```python
# Required env vars (see .env.example)
OPENAI_API_KEY=
SERP_API_KEY=
PERPLEXITY_API_KEY=        # optional, fallback
STABILITY_API_KEY=         # optional, fallback image generation
```

Provide a `Settings` dataclass (or Pydantic BaseSettings) with sensible defaults:
- `DEFAULT_MODEL = "gpt-4-turbo-preview"`
- `IMAGE_MODEL = "dall-e-3"`
- `MAX_RESEARCH_RESULTS = 10`
- `BLOG_TARGET_WORD_COUNT = 2000`
- `LINKEDIN_MAX_CHARS = 3000`

---

## Integration Clients

### OpenAI Client (`openai_client.py`)
- Wrap `openai.ChatCompletion.create` and `openai.Image.generate`
- Add exponential backoff retry (3 attempts) for rate limit errors
- Log token usage per call for cost tracking

### SERP Client (`serp_client.py`)
- Use `serpapi` Python package or direct HTTP to `https://serpapi.com/search`
- Return structured list: `[{title, url, snippet}]`
- Cache results in memory (TTL 1 hour) to reduce API calls

### Perplexity Client (`perplexity_client.py`)
- Use Perplexity's OpenAI-compatible API endpoint
- Model: `"sonar-pro"` for research queries
- Returns cited response — extract and preserve source URLs

---

## Content Optimization (`src/utils/content_optimization.py`)

Implement these functions:
- `calculate_keyword_density(text: str, keyword: str) -> float` — target 1–3%
- `generate_meta_description(content: str) -> str` — max 160 chars, uses GPT-4
- `suggest_headings(content: str) -> list` — H2/H3 structure suggestions
- `score_readability(text: str) -> dict` — Flesch-Kincaid grade, avg sentence length

## Quality Validation (`src/utils/quality_validation.py`)

Implement:
- `validate_blog(content: str) -> dict` — checks word count, heading structure, meta presence
- `validate_linkedin(content: str) -> dict` — checks length, hashtag count, hook strength
- `score_content(content: str, content_type: str) -> int` — 0–100 quality score

---

## Streamlit UI (`src/web_app/streamlit_app.py`)

Layout:
- **Sidebar**: Content type selector, settings (tone, word count, target keywords)
- **Main area**: Chat interface (messages history) + content preview panel side-by-side
- **Bottom**: Input box + Submit button

State management: Use `st.session_state` for conversation history and generated content.

Key UI flows:
1. User types request → routed through LangGraph → result displayed in preview panel
2. User can click "Refine" to send follow-up with context preserved
3. Export buttons: Copy to clipboard, Download as .md or .txt

---

## Coding Standards

- **Python 3.11+**
- **Type hints everywhere** — use `TypedDict`, `Optional`, `List` from `typing`
- **Async where possible** — use `async/await` for all API calls
- **Logging**: Use Python's `logging` module, not `print()`. Log at DEBUG for API calls, INFO for agent transitions, ERROR for failures
- **Docstrings**: Every class and public method needs a one-line docstring
- **Error messages**: Always include the agent name and operation in error strings
- **No hardcoded strings**: All prompts go in a `prompts/` dict or separate `prompts.py` file per agent

---

## Prompt Engineering Guidelines

Structure all agent prompts with:
1. **Role**: "You are an expert [role]..."
2. **Task**: Clear description of what to produce
3. **Constraints**: Format, length, tone, platform rules
4. **Output format**: Specify exact structure (markdown, JSON, etc.)

For the Query Handler classifier prompt, use few-shot examples covering edge cases
(e.g., "write me something about AI" → ambiguous, ask for clarification).

---

## Testing Approach

- **Unit tests**: Each agent's core method with mocked API calls
- **Integration tests**: Full LangGraph workflow with mock LLM responses
- **E2E tests**: Streamlit app smoke test via `streamlit.testing`
- Target **80%+ coverage**

---

## Dependencies (requirements.txt)

```
langgraph>=0.1.0
langchain>=0.2.0
openai>=1.0.0
streamlit>=1.35.0
serpapi>=0.1.5
httpx>=0.27.0
pydantic>=2.0.0
python-dotenv>=1.0.0
tenacity>=8.2.0        # retry logic
pytest>=8.0.0
pytest-asyncio>=0.23.0
```

---

## Where to Start

Generate code in this order:
1. `src/core/config.py` — Settings and env loading
2. `src/workflow/state_management.py` — AgentState TypedDict
3. `src/integrations/openai_client.py` — Core LLM wrapper
4. `src/agents/query_handler.py` — Routing logic
5. `src/agents/research_agent.py` — Research capability
6. `src/agents/blog_writer.py` — Blog generation
7. `src/agents/linkedin_writer.py` — LinkedIn posts
8. `src/agents/image_generator.py` — Image generation
9. `src/agents/content_strategist.py` — Strategy formatting
10. `src/workflow/langgraph_workflow.py` — Wire everything together
11. `src/web_app/streamlit_app.py` — UI layer last
