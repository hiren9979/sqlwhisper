# Text-to-SQL Clarification Engine — Project Plan

## 1. Project Purpose

A chatbot where a non-technical user asks a business question in plain English,
and the system:
1. Figures out which parts of the database are relevant (without ever embedding raw data).
2. Detects if the question is ambiguous (metric / time / entity / grouping unclear).
3. Asks a clarifying question if needed, before running anything.
4. Generates safe, read-only SQL, validates it, runs it, and explains the result in plain English.

The clarification loop is the core differentiator — most text-to-SQL demos assume a
well-formed question. This one assumes real users ask vague things like
*"give me last month's best performer"* and handles that properly.

---

## 2. Final Tech Stack

| Layer | Technology | Notes |
|---|---|---|
| Package manager | **uv** | dependency + venv management |
| Backend framework | **FastAPI** | REST + SSE/WebSocket for streaming, multi-turn chat |
| Orchestration | **LangChain** | prompts, output parsers, embeddings, model wrappers |
| Agent/flow control | **LangGraph** | stateful graph, cycles, `interrupt()` for clarification pauses |
| LLMs | **Mistral** (primary) + **Gemini** (secondary) | model routing — e.g. cheap/fast model for ambiguity check, stronger model for SQL generation; Gemini as fallback if Mistral fails/rate-limits |
| Vector store | **pgvector** | schema descriptions + glossary + few-shot examples only — never raw row data |
| Target database | **PostgreSQL** | the DB being queried, accessed via a read-only role |
| SQL safety | **sqlglot** | parses generated SQL to confirm SELECT-only, known tables/columns |
| Checkpointing | **LangGraph MemorySaver** (POC) → Postgres checkpointer (later) | required for pause/resume clarification flow |
| Frontend | **React (Vite)** | chat UI, built after backend is solid |
| Auth (POC) | Simple API key / none | full auth deferred |

**Why two LLM providers:** you get model-routing practice (a real production pattern) and a
built-in fallback if one provider is down or rate-limited. Decide per-node which model handles
it — e.g. Mistral Small for ambiguity classification, Mistral Large or Gemini for SQL generation.

---

## 3. Architecture Overview

```
User (React chat)
      │
      ▼
FastAPI /chat endpoint (thread_id based session)
      │
      ▼
LangGraph StateGraph
      │
      ├── retrieve_schema_context   (pgvector similarity search)
      │
      ├── check_ambiguity           (LLM structured output)
      │        │
      │        ├── if ambiguous → interrupt() → clarification question → user answers
      │        │        └── merge answer into user_query → loop back to check_ambiguity
      │        │
      │        └── if not ambiguous → continue
      │
      ├── generate_sql              (LLM + retrieved schema + few-shot examples)
      │
      ├── validate_sql              (sqlglot: SELECT-only, known tables/cols, LIMIT enforced)
      │        └── if invalid → back to generate_sql
      │
      ├── execute_sql               (read-only Postgres role, timeout)
      │        └── if error → back to generate_sql with error context (max 3 retries)
      │
      └── summarize_answer          (LLM turns result rows into plain English)
      │
      ▼
Final answer + SQL + result table → back to FastAPI → React UI
```

---

## 4. Feature List (POC scope)

- **Schema ingestion:** auto-extract tables/columns/types/foreign keys from Postgres `information_schema`.
- **Manual enrichment:** human-readable descriptions per table/column via config (YAML/JSON).
- **Business glossary:** map business terms (revenue, churn, active user) → SQL expressions/columns.
- **pgvector ingestion:** embed schema descriptions + glossary + few-shot examples (never raw data).
- **Context retrieval:** top-k similarity search instead of dumping full schema into prompt.
- **Ambiguity detection:** structured LLM output — `is_ambiguous`, `ambiguity_type`, `missing_slots`, `clarification_question`.
- **Multi-turn clarification loop:** `interrupt()` / `Command(resume=...)`, supports one-shot or iterative resolution.
- **SQL generation:** with retrieved context + resolved intent + few-shot examples.
- **SQL validation:** SELECT-only, known tables/columns, auto-`LIMIT`.
- **Execution + self-correction:** run against read-only role, retry on error (bounded).
- **NL answer summarization:** plain-English answer + SQL + raw table (toggleable).
- **Chat UI:** message history, clarification bubbles / quick-reply buttons, SQL/result toggle.
- **Session management:** per-thread persistence via LangGraph checkpointer.
- **Logging:** node name, input, output, duration, per thread_id.

---

## 5. Step-Wise Build Plan

Each phase below is a checkpoint — small enough to finish and verify in one sitting, big enough
to represent real progress. Work top to bottom. Don't skip validation steps; each phase should
be *demonstrably working* before moving to the next.

### Phase 0 — Architecture & Planning ✅ (this document)
- [x] Confirm tech stack.
- [x] Confirm architecture / data flow.
- [x] Confirm feature list and scope boundary (what's POC vs. future roadmap).

### Phase 1 — Project Scaffolding
- [ ] Init project with `uv`.
- [ ] Create folder structure: `app/`, `app/graph/`, `app/db/`, `app/schema/`, `app/api/`.
- [ ] Add core dependencies: `fastapi`, `uvicorn`, `langchain`, `langgraph`, `langchain-mistralai`, `langchain-google-genai`, `sqlglot`, `psycopg2-binary`, `pgvector`, `pyyaml`.
- [ ] Add `.env` handling (API keys for Mistral + Gemini, DB connection string).
- [ ] Verify: `uv run` starts without errors, dependencies resolve.

### Phase 2 — Common Files + Health Check API
- [ ] `app/main.py` — FastAPI app instance.
- [ ] `app/config.py` — settings loader (env vars, API keys, DB URL).
- [ ] `app/logging_config.py` — basic structured logger setup (used from Phase 2 onward, expanded in Phase 13).
- [ ] `/health` endpoint returning app status.
- [ ] Verify: `curl localhost:8000/health` returns 200.

### Phase 3 — Database Connection Layer
- [ ] `app/db/connection.py` — SQLAlchemy engine + session, connection test function.
- [ ] `app/db/schema_extractor.py` — pull table names, columns, types, foreign keys from `information_schema`.
- [ ] Verify: a script prints extracted schema for your test DB correctly.

### Phase 4 — Schema Metadata + Business Glossary
- [ ] `app/schema/metadata_config.yaml` — human-readable table/column descriptions.
- [ ] `app/schema/metadata_loader.py` — merges config descriptions with live extracted schema.
- [ ] `app/schema/glossary.yaml` — business term → SQL expression/column mapping.
- [ ] `app/schema/glossary_loader.py` — loads glossary.
- [ ] Verify: loader outputs one clean merged object per table + glossary term.

### Phase 5 — pgvector Ingestion
- [ ] Enable `pgvector` extension on your Postgres instance.
- [ ] `app/schema/embed_and_store.py` — script that embeds schema docs + glossary docs + few-shot examples, one row per doc, into a pgvector table.
- [ ] Decide embedding model (Mistral embeddings, or Gemini embeddings — pick one consistently).
- [ ] Verify: table populated, row count matches expected doc count.

### Phase 6 — Schema Context Retriever
- [ ] `app/schema/retriever.py` — takes a user question, returns top-k relevant docs via pgvector similarity search.
- [ ] Verify: a few sample questions return sensible top-k tables/glossary entries.

### Phase 7 — LangGraph State Definition
- [ ] `app/graph/state.py` — `AgentState` TypedDict: `messages`, `user_query`, `schema_context`, `ambiguity_check`, `clarification_question`, `sql_query`, `sql_result`, `final_answer`, `retry_count`.
- [ ] Verify: importable, no circular imports, matches what later nodes will need.

### Phase 8 — Ambiguity Detection Node
- [ ] `app/graph/nodes/check_ambiguity.py` — Pydantic output model (`is_ambiguous`, `ambiguity_type`, `missing_slots`, `clarification_question`) + LLM call (Mistral Small, cheap/fast).
- [ ] Verify: run node standalone on 3–5 test questions (clear ones + vague ones), confirm sensible classification.

### Phase 9 — Clarification Interrupt/Resume Node
- [ ] `app/graph/nodes/ask_clarification.py` — uses `interrupt()` to pause when `is_ambiguous=True`.
- [ ] Logic to merge `Command(resume=user_answer)` back into `user_query`.
- [ ] Verify: manually step through a graph run — pause happens, resume merges correctly, loops back to re-check ambiguity if still incomplete.

### Phase 10 — SQL Generation Node
- [ ] `app/graph/nodes/generate_sql.py` — LLM call (Mistral Large or Gemini) using resolved `user_query` + `schema_context` + 2–3 few-shot examples.
- [ ] Verify: standalone test on a few resolved questions produces plausible SQL.

### Phase 11 — SQL Validation Node
- [ ] `app/graph/nodes/validate_sql.py` — `sqlglot` parse: SELECT-only, known tables/columns, auto-append `LIMIT`.
- [ ] Verify: test against valid SQL, invalid SQL (e.g. `DELETE`), and SQL referencing unknown columns.

### Phase 12 — SQL Execution + Self-Correction Loop
- [ ] `app/graph/nodes/execute_sql.py` — run against read-only DB role, with timeout, capture result or error.
- [ ] Add conditional edge: on error → back to `generate_sql` with error context, max 3 retries → friendly failure message.
- [ ] Verify: force a bad query, confirm retry loop triggers and eventually gives up gracefully.

### Phase 13 — Answer Summarization Node
- [ ] `app/graph/nodes/summarize_answer.py` — LLM turns result rows + original question into plain-English answer.
- [ ] Verify: test with a few result sets, confirm answers read naturally and stay factually grounded in the rows.

### Phase 14 — Wire the Full Graph
- [ ] `app/graph/build_graph.py` — assemble all nodes into one `StateGraph` with correct conditional edges (per architecture diagram above).
- [ ] Compile with `MemorySaver` checkpointer.
- [ ] Verify: run a full end-to-end question through the graph, including at least one clarification round-trip.

### Phase 15 — FastAPI Chat Endpoint
- [ ] `app/api/chat.py` — `POST /chat` accepting `{message, thread_id}`, invoking the graph, correctly handling interrupt/resume, returning either a clarification question or final answer + SQL + result table.
- [ ] Verify: full conversation via `curl`/Postman, including a clarification exchange across two calls with the same `thread_id`.

### Phase 16 — PostgreSQL Checkpoint Persistence
- [ ] 16.1 — Replace MemorySaver with PostgreSQL checkpointer in build_graph
- [ ] 16.2 — Update chat.py to use persistent PostgreSQL checkpointer
- [ ] 16.3 — Add psycopg connection management for checkpointer
- [ ] 16.4 — Create comprehensive checkpoint persistence test
- [ ] 16.5 — Create interactive conversation test with real-time PostgreSQL persistence
- [ ] 16.6 — Fix context manager issues with PostgresSaver.from_conn_string
- [ ] 16.7 — Add proper connection cleanup and error handling
- [ ] 16.8 — Implement conversation resume functionality across application restarts
- [ ] 16.9 — Add test for ambiguity/clarification flow with checkpoint persistence
- [ ] 16.10 — Verify: conversation continues after application restart using same thread_id
- [ ] Verify: state structure works with LangGraph checkpointing.

### Phase 21 — Chat API with Conversation Support
- [ ] Update `/chat` endpoint to accept optional `conversation_id` parameter.
- [ ] Pass `conversation_id` as LangGraph `thread_id` for state persistence.
- [ ] Handle conversation creation on first message if no `conversation_id` provided.
- [ ] Verify: multiple messages with same `conversation_id` maintain conversation context.

### Phase 22 — Conversation Management APIs
- [ ] `POST /conversations` — create new conversation.
- [ ] `GET /conversations` — list user's conversations (paginated).
- [ ] `GET /conversations/{id}` — get conversation details and message history.
- [ ] `DELETE /conversations/{id}` — soft-delete conversation.
- [ ] `PUT /conversations/{id}` — update conversation title.
- [ ] Verify: all endpoints work via curl/Postman with proper error handling.

### Phase 23 — Conversation Isolation Testing
- [ ] Create test script that sends messages to two different conversations.
- [ ] Verify: conversation histories remain isolated from each other.
- [ ] Verify: conversation list returns correct conversations per user.
- [ ] Verify: soft-deleted conversations don't appear in lists.

### Phase 24 — React Chat UI
- [ ] Vite + React scaffold, Tailwind styling.
- [ ] Message list, input box, send button.
- [ ] Distinct bubble style for clarification questions.
- [ ] Verify: basic chat renders, no backend wiring yet.

### Phase 25 — React ↔ FastAPI Integration
- [ ] Wire UI to `/chat`, maintain `conversation_id` in local state across the conversation.
- [ ] Connect conversation list to the UI so users can create, select, and continue previous chats.
- [ ] Correctly render multi-turn clarification exchanges.
- [ ] Verify: full conversation works end-to-end in the browser.

### Phase 26 — Show SQL / Result Toggle
- [ ] Collapsible "View SQL & raw results" section under each answer bubble.
- [ ] Verify: toggle shows correct SQL + table matching that specific answer.

### Phase 27 — Logging & Observability
- [ ] Structured JSON logging at each LangGraph node: node name, input, output, duration.
- [ ] Dump full run logs to `logs/`, keyed by `conversation_id`.
- [ ] Verify: a full run produces a readable, complete log trail.

### Phase 28 — Test Pass & Polish
- [ ] Run 10–15 varied test questions (clear, vague, multi-clarification, deliberately broken) end to end.
- [ ] Fix rough edges in prompts, error messages, and UI states.
- [ ] Write a short README covering setup, env vars, and how to run.

---

## 6. How to Use This Plan With an AI Coding Assistant

For each phase, give the assistant **one focused prompt at a time** — don't combine phases.
A good pattern per phase:

1. State the phase goal in one sentence.
2. List the exact file(s) to create/modify.
3. State the verification step explicitly, so the assistant writes testable code.

Example for Phase 3:
> "Add a Postgres connection module in `app/db/connection.py` using SQLAlchemy. Include a
> connection-test function and a function in `app/db/schema_extractor.py` that extracts table
> names, column names, data types, and foreign keys from `information_schema`. I want to run a
> quick script afterward to print the extracted schema for my test DB."

Check off each box as you verify it works — don't move to the next phase until the current one
is demonstrably working. This keeps the project debuggable: if something breaks in Phase 10,
you know Phases 1–9 were already confirmed solid.