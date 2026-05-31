# API Documentation — Agents & Services

Reference for every agent's public interface, the shared state contract, the
integration clients, and the workflow facade. Signatures below match the source;
file links point at the implementation.

---

## Shared Types

[`workflow/state_management.py`](../src/ai_content_assistant/workflow/state_management.py)

```python
ContentType = Literal["blog", "linkedin", "image", "research", "strategy"]

class ConversationMessage(TypedDict):
    role: str
    content: str

class AgentState(TypedDict):
    user_message: str
    conversation_history: Annotated[list[ConversationMessage], _merge_history]
    next_agent: Optional[str]
    research_output: Optional[str]
    sources: Optional[list[str]]
    final_content: Optional[str]
    content_type: Optional[ContentType]
    error: Optional[str]
    metadata: Optional[dict]
```

Helpers:
- `create_initial_state(user_message: str) -> AgentState`
- `append_to_history(state, role, content) -> AgentState` — sliding-window capped at 5

---

## Workflow Facade

[`core/workflow.py`](../src/ai_content_assistant/core/workflow.py) — the surface the Streamlit app calls.

### `async process_request(user_message: str, session_state: dict) -> AgentState`
Runs the full graph and returns the final state. Threads the last 5 UI messages
as history and packs sidebar settings (`tone`, `word_count`, `keywords`,
`content_type_hint`) into `metadata`.

### `async stream_request(user_message: str, session_state: dict)`
Async generator yielding `(node_name, state_delta)` as each node completes — used
to drive the live progress panel.

Lower level ([`workflow/langgraph_workflow.py`](../src/ai_content_assistant/workflow/langgraph_workflow.py)):
- `build_graph()` — compile the `StateGraph`
- `get_graph()` — lazy singleton accessor
- `async run_workflow(user_message, conversation_history=None, metadata=None) -> AgentState`
- `async stream_workflow(user_message, conversation_history=None, metadata=None)`

---

## Agents

Every agent exposes `async run(state: AgentState) -> AgentState`. Additional public
methods are listed below.

### Query Handler — [`agents/query_handler.py`](../src/ai_content_assistant/agents/query_handler.py)
Entry point; classifies intent and routes.

| Method | Signature | Notes |
|---|---|---|
| `classify_intent` | `async (user_message: str) -> str` | JSON mode; returns one of the valid agents, defaults to `research` |
| `detect_followup` | `async (state) -> bool` | True if message refines the prior turn |
| `resolve_followup` | `async (state) -> str` | Rewrites a follow-up into a self-contained request |

**Writes:** `next_agent`, `content_type`, `metadata["is_followup"]`. Honors a
sidebar `content_type_hint` when present. Classification + follow-up detection run
concurrently.

### Deep Research — [`agents/research_agent.py`](../src/ai_content_assistant/agents/research_agent.py)

| Method | Signature | Notes |
|---|---|---|
| `extract_search_query` | `async (user_message: str) -> str` | Distills a clean SERP query (fast model) |
| `search` | `async (query: str) -> list[dict]` | SERP → Perplexity fallback; `[{title, url, snippet}]` |
| `synthesize` | `async (query, results) -> str` | Cached by `MD5(query+URLs)`, 1 hr / 200 entries |

**Writes:** `research_output`, `sources`, `final_content`, `content_type`
(`research`, or `strategy` preserved for the strategist). Reuses existing
`research_output` when `metadata["is_followup"]` is set.

### SEO Blog Writer — [`agents/blog_writer.py`](../src/ai_content_assistant/agents/blog_writer.py)

| Method | Signature | Notes |
|---|---|---|
| `write_blog` | `async (topic, research=None, word_count=None, tone="professional", keywords="") -> AsyncIterator[str]` | Streamed Markdown |
| `generate_meta` | `async (content: str) -> dict` | `{title, meta_description, keywords, slug}` |

**Writes:** `final_content` (full Markdown), and `metadata` with SEO meta +
`quality_score`, `quality_issues`, `readability`. Research context is truncated to
the first 3000 chars.

### LinkedIn Writer — [`agents/linkedin_writer.py`](../src/ai_content_assistant/agents/linkedin_writer.py)

| Method | Signature | Notes |
|---|---|---|
| `write_post` | `async (topic, tone="professional") -> str` | Truncated to ≤ `linkedin_max_chars` at a sentence boundary |
| `generate_hashtags` | `async (topic) -> list[str]` | 5–8 hashtags (fast model, JSON) |
| `generate_variants` | `async (topic) -> dict` | 3 tone variants in one call |

**Writes:** `final_content` (post + hashtags), `metadata["hashtags"]`,
`metadata["variants"]`, quality fields. Post/hashtags/variants run in parallel.

### Image Generator — [`agents/image_generator.py`](../src/ai_content_assistant/agents/image_generator.py)

| Method | Signature | Notes |
|---|---|---|
| `optimize_prompt` | `async (user_intent: str) -> str` | Expands intent into a detailed prompt (fast model) |
| `generate` | `async (prompt: str) -> dict` | `{url, revised_prompt, source}`; Stability fallback if key set |

**Writes:** `final_content` (image URL or `data:` URI), `metadata["image_url"]`,
`metadata["prompt_used"]`, `metadata["image_source"]`. Runs `check_image_prompt`
and `async_check_moderation` before generating.

> **Note:** `gpt-image-1` returns base64 (rendered as a `data:` URI); `dall-e-3`
> returns an HTTPS URL. The preview panel handles both. `gpt-image-1` may require a
> **verified OpenAI organization** — set `IMAGE_MODEL=dall-e-3` if your org is unverified.

### Content Strategist — [`agents/content_strategist.py`](../src/ai_content_assistant/agents/content_strategist.py)

| Method | Signature | Notes |
|---|---|---|
| `format_research` | `async (raw: str) -> str` | Structures raw research into strategic Markdown |
| `create_content_plan` | `async (topic, research=None) -> str` | Content calendar / plan |

**Writes:** `final_content`. If `research_output` exists it formats it; otherwise
it builds a plan from scratch.

---

## Integration Clients

### OpenAI — [`integrations/openai_client.py`](../src/ai_content_assistant/integrations/openai_client.py)
Singleton `openai_client`.

| Method | Signature |
|---|---|
| `chat_complete` | `async (messages, model=None, temperature=0.7, max_tokens=1000, json_mode=False) -> tuple[str, dict]` |
| `chat_stream` | `async (messages, model=None, max_tokens=3500) -> AsyncIterator[str]` |
| `generate_image` | `async (prompt, size="1024x1024", quality="auto") -> {url, revised_prompt}` |

Retries 3× on `RateLimitError`; logs token usage; returns `(content, usage_dict)`.

### SERP — [`integrations/serp_client.py`](../src/ai_content_assistant/integrations/serp_client.py)
Singleton `serp_client`. `async search(query, num_results) -> list[{title, url, snippet}]`.
TTL cache: 1 hr / 100 entries.

### Perplexity — [`integrations/perplexity_client.py`](../src/ai_content_assistant/integrations/perplexity_client.py)
Singleton `perplexity_client`. `async research(query) -> tuple[str, list[str]]`
(`(answer, urls)`). Uses `sonar-pro`; returns `("", [])` if `PERPLEXITY_API_KEY` unset.

### Stability AI — [`integrations/image_clients.py`](../src/ai_content_assistant/integrations/image_clients.py)
Singleton `stability_client`. `async generate(prompt, width=1024, height=1024) -> str`
(base64 PNG). Raises `RuntimeError` without `STABILITY_API_KEY`.

---

## Utilities

### Quality validation — [`utils/quality_validation.py`](../src/ai_content_assistant/utils/quality_validation.py)
- `validate_blog(content) -> {passed, score, issues}`
- `validate_linkedin(content) -> {passed, score, issues}`
- `score_content(content, content_type) -> int` (0–100)

### Content optimization — [`utils/content_optimization.py`](../src/ai_content_assistant/utils/content_optimization.py)
- `calculate_keyword_density(text, keyword) -> float`
- `score_readability(text) -> {flesch_kincaid_grade, avg_sentence_length}`
- `suggest_headings(content) -> list[str]`
- `async generate_meta_description(content, keyword=None) -> str` (≤ 160 chars)

### Guardrails — [`utils/guardrails.py`](../src/ai_content_assistant/utils/guardrails.py)
- `check_input_length(text)` → raises `InputTooLongError`
- `detect_pii(text) -> list[str]` (non-raising)
- `check_moderation(text)` / `async_check_moderation(text)` → raises `ContentFlaggedError`
- `check_image_prompt(prompt)` → raises `ImageSafetyError`

### Export — [`utils/export_tools.py`](../src/ai_content_assistant/utils/export_tools.py)
- `to_markdown(content, metadata=None) -> str` (adds YAML frontmatter)
- `to_plain_text(content) -> str` (strips Markdown)
- `generate_filename(content_type, topic) -> str` (timestamped slug)

---

## Configuration

[`core/config.py`](../src/ai_content_assistant/core/config.py) — singleton `settings`,
loaded from environment/`.env` via `pydantic-settings`.

| Setting | Default | Required |
|---|---|---|
| `openai_api_key` | — | ✅ |
| `serp_api_key` | — | ✅ |
| `perplexity_api_key` | `None` | optional (research fallback) |
| `stability_api_key` | `None` | optional (image fallback) |
| `default_model` | `gpt-4o` | |
| `fast_model` | `gpt-4o-mini` | |
| `image_model` | `gpt-image-1` | |
| `max_research_results` | `10` | |
| `blog_target_word_count` | `2000` | |
| `linkedin_max_chars` | `3000` | |
| `max_input_length` | `2000` | |
| `max_requests_per_hour` | `20` | |
| `env` | `development` | |
| `log_level` | `INFO` | |
