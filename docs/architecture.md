# Architecture & Technical Design

This document covers the system architecture, design decisions and trade-offs,
service-integration patterns, the quality-validation pipeline, and scalability
considerations for the **AI Content Assistant**.

---

## 1. System Overview

The Content Assistant is a multi-agent content-marketing system that turns a
single natural-language request into research reports, SEO blog posts, LinkedIn
posts, AI images, or strategic content plans. It is built on:

- **LangGraph** — agent orchestration via a compiled `StateGraph`
- **OpenAI GPT-4o / GPT-4o-mini** — generation and lightweight classification
- **SERP API** (+ Perplexity Sonar fallback) — web research
- **gpt-image-1 / DALL·E 3** (+ Stability AI fallback) — image generation
- **Streamlit** — conversational web UI

```
                         ┌──────────────────────────┐
        user request →   │      Streamlit UI         │
                         │  (chat + preview panel)   │
                         └────────────┬─────────────┘
                                      │ stream_request()
                                      ▼
                         ┌──────────────────────────┐
                         │   LangGraph StateGraph    │
                         └────────────┬─────────────┘
                                      ▼
                               query_handler
            ┌──────────┬──────────┬───┴────┬───────────────┬───────────────┐
            ▼          ▼          ▼        ▼               ▼               ▼
        research     blog     linkedin   image     content_strategist  error_handler
            │                                              ▲
            └───── (content_type == "strategy") ───────────┘
```

See [`workflow/langgraph_workflow.py`](../src/ai_content_assistant/workflow/langgraph_workflow.py)
for the concrete graph definition.

---

## 2. The Six Agents

All agents implement the same async contract: `async run(state: AgentState) -> AgentState`.

| Agent | File | Role | Primary model |
|---|---|---|---|
| Query Handler | `agents/query_handler.py` | Classify intent, detect/resolve follow-ups, set `next_agent` | `gpt-4o-mini` (JSON mode) |
| Deep Research | `agents/research_agent.py` | Web search + synthesis, with caching | SERP + `gpt-4o` |
| SEO Blog Writer | `agents/blog_writer.py` | Long-form streamed Markdown + SEO meta | `gpt-4o` |
| LinkedIn Writer | `agents/linkedin_writer.py` | Post + hashtags + 3 tone variants (parallel) | `gpt-4o` / `gpt-4o-mini` |
| Image Generator | `agents/image_generator.py` | Prompt optimization + image generation | `gpt-image-1` |
| Content Strategist | `agents/content_strategist.py` | Format research / build content plans | `gpt-4o` |

---

## 3. State Management

Shared state is an `AgentState` `TypedDict`
([`workflow/state_management.py`](../src/ai_content_assistant/workflow/state_management.py)):

```python
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

**Design decision — sliding-window history.** `conversation_history` uses a
custom LangGraph reducer (`_merge_history`) that appends new turns and keeps only
the last **5** (`_MAX_HISTORY`). Agents return *only* the new messages; LangGraph
merges them. This bounds token cost on long sessions at the cost of long-range
recall — an acceptable trade-off for a single-session content tool.

**`metadata` as a typed catch-all.** Rather than widening the state schema for
every agent-specific field (SEO meta, image URL, hashtags, quality score, tone
variants, `is_followup`), they live in `metadata`. Trade-off: less type safety,
but a stable graph schema and zero churn when an agent adds an output.

---

## 4. Routing & Control Flow

Routing logic is isolated in [`core/router.py`](../src/ai_content_assistant/core/router.py)
as pure functions returning the next node name:

- `route_after_query_handler` — validates `next_agent` against a **whitelist**
  (`research`/`blog`/`linkedin`/`image`/`content_strategist`); unknown values
  degrade gracefully to `research`. Short-circuits to `error_handler` if an error is set.
- `route_after_research` — forwards to `content_strategist` when
  `content_type == "strategy"`, otherwise ends.
- `route_after_agent` — terminal agents route to `error_handler` if they set
  `state["error"]`, else `END`.

**Design decision — strategy is research-first.** A `strategy` request is
classified by the query handler but routed first to `research`; the
`content_type == "strategy"` flag is preserved so `route_after_research` then
hands findings to the strategist. This reuses the research path instead of
duplicating search logic in the strategist.

---

## 5. Error Handling & Fallbacks

Resilience is layered:

1. **Node wrapper** — `_make_node()` wraps every agent's `run()` in try/except.
   On exception it sets `state["error"]`. It also catches *silent* failures:
   a terminal content agent that returns empty `final_content` is converted into
   an explicit error rather than a blank screen.
   ([`langgraph_workflow.py:30-55`](../src/ai_content_assistant/workflow/langgraph_workflow.py#L30-L55))
2. **Error handler node** — `handle_error` converts any `state["error"]` into a
   friendly `final_content` message and clears the flag so the graph terminates cleanly.
3. **Service fallbacks**
   - **Research:** SERP API → Perplexity Sonar on exception/empty results
     ([`research_agent.py:40-52`](../src/ai_content_assistant/agents/research_agent.py#L40-L52)).
   - **Images:** `gpt-image-1`/DALL·E → Stability AI *only if* `STABILITY_API_KEY`
     is configured; otherwise a clear `RuntimeError` is surfaced to the user
     ([`image_generator.py:34-52`](../src/ai_content_assistant/agents/image_generator.py#L34-L52)).
4. **Retry** — OpenAI calls retry 3× with exponential backoff on `RateLimitError`
   via `tenacity` ([`openai_client.py:37-42`](../src/ai_content_assistant/integrations/openai_client.py#L37-L42)).

**Trade-off:** fallbacks are best-effort and key-gated. There is no automatic
cross-provider failover for the primary LLM (GPT-4o) — a deliberate scope choice,
since the alternatives (Claude, Gemini) are listed as options rather than wired in.

---

## 6. Content Quality & Enhancement Pipeline

After generation, blog and LinkedIn agents run validation and enrich `metadata`:

- **Validation** ([`utils/quality_validation.py`](../src/ai_content_assistant/utils/quality_validation.py))
  - `validate_blog` — word count ≥ 1500, H1 present, ≥ 3 H2s, YAML frontmatter
  - `validate_linkedin` — ≤ 3000 chars, 5–8 hashtags, non-trivial hook
  - `score_content` — 0–100 score surfaced in the preview panel
- **Optimization** ([`utils/content_optimization.py`](../src/ai_content_assistant/utils/content_optimization.py))
  - `calculate_keyword_density`, `score_readability` (Flesch–Kincaid),
    `suggest_headings`, `generate_meta_description`
- **SEO metadata** — `BlogWriter.generate_meta` extracts title/description/keywords/slug.

**Design decision — heuristic scoring over ML.** Readability uses a syllable
heuristic instead of a heavyweight NLP dependency. Cheaper and dependency-free;
slightly less accurate on edge cases.

---

## 7. Guardrails

Applied in the UI before submit and in the image agent before generation
([`utils/guardrails.py`](../src/ai_content_assistant/utils/guardrails.py)):

- `check_input_length` — rejects input over `max_input_length` (2000)
- `detect_pii` — non-raising regex scan (email/phone/SSN/credit card) → UI warning
- `check_moderation` / `async_check_moderation` — OpenAI Moderation API
- `check_image_prompt` — deny-list keyword check before image generation
- **Rate limiting** — `max_requests_per_hour` (20), enforced in `streamlit_app._validate_input`

---

## 8. Integration Layer

All clients are module-level singletons exposing async methods. HTTP calls to
OpenAI use the **synchronous** SDK on an executor thread
(`asyncio.run_in_executor`) — a deliberate workaround for an async httpx/SSL
issue under Streamlit's `ProactorEventLoop` on Windows (documented in
[`openai_client.py`](../src/ai_content_assistant/integrations/openai_client.py)).

| Client | File | Caching / notes |
|---|---|---|
| OpenAI | `integrations/openai_client.py` | retry + token logging; chat, stream, image |
| SERP | `integrations/serp_client.py` | TTL cache 1 hr / 100 entries |
| Perplexity | `integrations/perplexity_client.py` | OpenAI-compatible `sonar-pro`; no-ops without key |
| Stability AI | `integrations/image_clients.py` | raises without key |

Research synthesis is additionally cached by `MD5(query + result URLs)` (1 hr,
200 entries) in the research agent.

---

## 9. Scalability Considerations

- **Stateless graph** — `build_graph()` compiles once into a lazy singleton
  (`get_graph()`); per-request state is fully isolated in `AgentState`. The graph
  itself can be invoked concurrently.
- **Session state** — currently held in Streamlit `st.session_state` (per-browser
  session, in-memory). For multi-replica deployment this is the first thing to
  externalize (Redis/PostgreSQL), as noted in the project brief's alternatives table.
- **Cost control** — two-tier model strategy (heavy `gpt-4o` vs. cheap
  `gpt-4o-mini` for classification/meta/hashtags), TTL caches on SERP and
  synthesis, and the 5-turn history cap all bound token spend.
- **Concurrency within a request** — the LinkedIn agent runs post/hashtags/variants
  in parallel (`asyncio.gather`); the query handler classifies intent and detects
  follow-ups concurrently.
- **Known bottleneck** — the executor-thread pattern serializes some OpenAI work on
  the default thread pool; under heavy concurrency, tune the executor or move to a
  fully async transport once the Windows SSL constraint no longer applies.

---

## 10. Key Design Trade-offs (summary)

| Decision | Benefit | Cost |
|---|---|---|
| Sync OpenAI SDK on executor | Avoids Windows async SSL bug | Extra thread hop; pool contention at scale |
| 5-turn history cap | Bounded token cost | Limited long-range memory |
| `metadata` catch-all dict | Stable graph schema | Weaker type safety |
| Heuristic readability scoring | No heavy NLP deps | Less precise |
| Key-gated fallbacks only | Simple, predictable | No primary-LLM failover |
| In-memory session state | Simplest UX | Not multi-replica ready |
