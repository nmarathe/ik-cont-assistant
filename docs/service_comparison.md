# Service Comparison Analysis

A comparison of the AI service providers used (and considered) in the AI Content
Assistant, the rationale for each primary choice, a cost-benefit view, and
recommendations by use case and budget. This satisfies the capstone's "Service
Comparison Analysis" deliverable.

> Pricing figures are indicative and change frequently — treat them as relative
> guidance, and confirm current rates on each provider's pricing page before
> committing to a budget.

---

## 1. Choices at a Glance

| Capability | Primary (implemented) | Fallback (implemented) | Considered (not wired) |
|---|---|---|---|
| Orchestration | LangGraph | — | CrewAI, AutoGen, Semantic Kernel |
| LLM | OpenAI GPT-4o / GPT-4o-mini | — | Claude Sonnet, Gemini |
| Research | SERP API | Perplexity Sonar (`sonar-pro`) | You.com, Tavily |
| Images | `gpt-image-1` / DALL·E 3 | Stability AI (SDXL) | Midjourney, Imagen |
| UI | Streamlit | — | Gradio, React, Flask |
| State | LangGraph + `st.session_state` | — | Redis, MongoDB, PostgreSQL |

Fallbacks are **key-gated**: they activate only when the relevant optional API key
is configured (`PERPLEXITY_API_KEY`, `STABILITY_API_KEY`).

---

## 2. Orchestration — LangGraph

**Why chosen.** Explicit graph topology with typed shared state (`AgentState`) and
conditional edges maps cleanly onto a router → specialist-agents design. Streaming
(`astream`) drives the live progress UI, and the reducer pattern gives controlled
conversation memory.

| Option | Pros | Cons |
|---|---|---|
| **LangGraph** | Explicit state graph, conditional routing, streaming, typed state | Steeper learning curve than a linear chain |
| CrewAI | Fast role/task setup | Less control over branching/state |
| AutoGen | Strong multi-agent conversations | Conversation-centric, less graph control |
| Semantic Kernel | Enterprise/.NET integration | Heavier; Python story less mature |

**Verdict:** the right fit when routing and state transitions must be explicit and
testable — which they are here (see the routing whitelist + error edges).

---

## 3. Language Model — OpenAI GPT-4o family

**Why chosen.** Strong general generation quality, reliable JSON mode (used for
classification, hashtags, meta, variants), and streaming. The system applies a
**two-tier strategy**: `gpt-4o` for heavy generation, `gpt-4o-mini` for cheap
classification/metadata/hashtags.

| Model | Relative cost | Best for |
|---|---|---|
| GPT-4o | higher | Blog posts, synthesis, content plans, LinkedIn body |
| GPT-4o-mini | ~10–20× cheaper | Intent classification, follow-up detection, hashtags, SEO meta |
| Claude Sonnet *(considered)* | comparable | Long-form quality; strong instruction following |
| Gemini *(considered)* | competitive | Multimodal, large context |

**Cost-benefit:** the two-tier split is the single biggest cost lever — routing
lightweight calls to `gpt-4o-mini` cuts spend substantially without touching output
quality, since those calls are short and structured. Alternatives (Claude/Gemini)
are deliberately left as swap-in options rather than wired in, to keep the
integration surface small; the `openai_client` abstraction makes a future swap
localized.

---

## 4. Research — SERP API + GPT, with Perplexity fallback

**Why chosen.** SERP API returns clean structured results (`title`, `url`,
`snippet`) that GPT-4o synthesizes into a sourced report. Perplexity Sonar is a
strong fallback because it returns an answer *and* citations in one call.

| Option | Pros | Cons |
|---|---|---|
| **SERP API + GPT** | Structured results, full control over synthesis, source URLs | Two-step (search then synthesize); SERP cost per query |
| **Perplexity Sonar** | One-call answer + citations | Less control over which sources; opaque retrieval |
| You.com / Tavily | AI-search oriented, dev-friendly | Not integrated; another key to manage |

**Cost-benefit:** SERP + synthesis is more controllable and the results are cached
(`MD5(query+URLs)`, 1 hr), so repeated/related queries are nearly free. Perplexity
as fallback buys resilience for the cost of one optional key.

---

## 5. Images — gpt-image-1 / DALL·E 3, with Stability fallback

**Why chosen.** Staying within OpenAI keeps auth and tooling unified. `gpt-image-1`
is the default (returns base64); DALL·E 3 is a drop-in alternative (returns a URL).
Stability AI (SDXL) is the budget/offline-from-OpenAI fallback.

| Option | Output | Notes |
|---|---|---|
| **gpt-image-1** | base64 (`data:` URI) | Default; **may require a verified OpenAI org** |
| **DALL·E 3** | HTTPS URL | Set `IMAGE_MODEL=dall-e-3`; no org-verification friction |
| **Stability AI (SDXL)** | base64 PNG | Key-gated fallback; lower per-image cost |
| Midjourney / Imagen *(considered)* | — | No official simple API path at build time |

**Recommendation:** if org verification is a blocker, default to `dall-e-3`. For
cost-sensitive/high-volume image needs, configure Stability AI and let the fallback
path serve.

---

## 6. UI & State

- **Streamlit** was chosen for speed of building a conversational + preview UI in
  pure Python. Trade-off: less control than React, and in-memory session state.
- **State** is LangGraph (in-flight) + `st.session_state` (session). Fine for a
  single-replica demo; externalize to Redis/PostgreSQL for multi-replica scale
  (see the deployment guide).

---

## 7. Cost Management Levers (implemented)

| Lever | Where | Effect |
|---|---|---|
| Two-tier model routing | `fast_model` vs `default_model` | Big spend reduction on light calls |
| SERP TTL cache | `serp_client.py` (1 hr / 100) | Avoids duplicate search cost |
| Synthesis cache | `research_agent.py` (1 hr / 200) | Avoids re-synthesizing identical result sets |
| 5-turn history cap | `state_management.py` | Bounds prompt size on long sessions |
| Token max_tokens caps | per-agent calls | Prevents runaway completions |
| Rate limiting | `streamlit_app._validate_input` (20/hr) | Caps worst-case spend per user |

---

## 8. Recommendations by Use Case

| Scenario | Recommended configuration |
|---|---|
| **Demo / capstone eval** | Defaults: GPT-4o + GPT-4o-mini, SERP, `dall-e-3` if org unverified |
| **Cost-sensitive / high volume** | Keep two-tier models; add Stability AI for images; rely on caches |
| **Max resilience** | Configure both `PERPLEXITY_API_KEY` and `STABILITY_API_KEY` for full fallback coverage |
| **Enterprise / multi-replica** | Externalize session + caches to Redis; add LangSmith/Helicone observability |
| **Quality-first long-form** | GPT-4o (or evaluate Claude Sonnet via the client abstraction) |

---

## 9. Benchmarking Notes

No formal latency/cost benchmarks are bundled. To produce them, the recommended
approach is to instrument `openai_client.chat_complete` (it already logs token
usage) and aggregate per-agent token counts and wall-clock per node from the
`stream_workflow` `(node_name, delta)` events. This is the natural extension point
for the "performance benchmarks across service combinations" the brief mentions as
a stretch goal.
