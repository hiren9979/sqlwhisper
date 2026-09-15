# Text-to-SQL Clarification Engine — Project Architecture

## 1. Project Overview

A full-stack AI application that allows non-technical users to ask business questions about a PostgreSQL database using natural language.

The system does not directly execute an LLM-generated query. Instead, it first understands the user's intent, retrieves only the relevant database schema knowledge, detects ambiguity, asks clarification when required, generates SQL, validates it, executes it using a read-only database role, and converts the result into a simple natural-language answer.

### Core Differentiator

The main feature is the **clarification loop**.

For example:

> "Give me last month's best performer."

The system should recognize that "best performer" may be ambiguous and ask whether the user means highest sales, highest revenue, most orders, or another metric before generating SQL.

---

# 2. High-Level Architecture

```text
React + Vite Frontend
        │
        ▼
FastAPI API Layer
        │
        ▼
LangGraph Workflow
        │
        ├── Retrieve Schema Context
        │
        ├── Check Ambiguity
        │        │
        │        └── Ambiguous → Ask Clarification
        │                         │
        │                         └── Resume Graph
        │
        ├── Generate SQL
        │
        ├── Validate SQL
        │
        ├── Execute Read-Only SQL
        │        │
        │        └── Error → Retry SQL Generation
        │
        └── Summarize Result
                 │
                 ▼
        Response to React UI
```

---

# 3. Main Components

## Frontend

**Technology:** React + Vite

Responsibilities:

- Chat interface
- User question input
- Display clarification questions
- Display AI answers
- Display generated SQL
- Display query results
- Session/thread management
- Chat history
- Loading and error states

The frontend communicates only with the FastAPI backend.

---

## Backend

**Technology:** Python + FastAPI

Responsibilities:

- HTTP API
- Request validation
- Thread/session handling
- Starting and resuming LangGraph execution
- Returning graph results to the frontend
- Streaming responses where required
- Logging

The API layer should remain thin and should not contain the main AI workflow logic.

---

## AI Workflow

**Technology:** LangGraph

LangGraph is responsible for orchestrating the complete Text-to-SQL workflow.

Main workflow stages:

1. Schema retrieval
2. Ambiguity detection
3. Clarification
4. SQL generation
5. SQL validation
6. SQL execution
7. Error-based retry
8. Result summarization

LangGraph state maintains information throughout the conversation and workflow.

---

# 4. Project Structure

```text
text-to-sql/
│
├── app/
│   │
│   ├── main.py
│   ├── config.py
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   └── chat.py
│   │
│   ├── graph/
│   │   ├── __init__.py
│   │   ├── state.py
│   │   ├── build_graph.py
│   │   │
│   │   └── nodes/
│   │       ├── __init__.py
│   │       ├── retrieve_schema.py
│   │       ├── check_ambiguity.py
│   │       ├── ask_clarification.py
│   │       ├── generate_sql.py
│   │       ├── validate_sql.py
│   │       ├── execute_sql.py
│   │       └── summarize_answer.py
│   │
│   ├── ai/
│   │   ├── __init__.py
│   │   ├── models.py
│   │   ├── embeddings.py
│   │   ├── prompts.py
│   │   └── structured_output.py
│   │
│   ├── db/
│   │   ├── __init__.py
│   │   ├── connection.py
│   │   ├── schema_extractor.py
│   │   └── vector_store.py
│   │
│   ├── schema/
│   │   ├── __init__.py
│   │   ├── metadata_config.yaml
│   │   ├── metadata_loader.py
│   │   ├── glossary.yaml
│   │   ├── glossary_loader.py
│   │   └── retriever.py
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── chat.py
│   │   └── ambiguity.py
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   └── sql_service.py
│   │
│   └── utils/
│       ├── __init__.py
│       └── logger.py
│
├── scripts/
│   ├── ingest_schema.py
│   └── test_graph.py
│
├── tests/
│   ├── test_ambiguity.py
│   ├── test_sql_validation.py
│   └── test_schema_retrieval.py
│
├── logs/
│
├── .env
├── .env.example
├── .gitignore
├── pyproject.toml
├── uv.lock
└── README.md
```

---

# 5. Folder Responsibilities

## `app/api/`

HTTP/API boundary of the application.

Responsibilities:

- Receive frontend requests
- Validate request data
- Start/resume graph execution
- Return API responses
- Handle streaming/SSE where required

Example responsibility:

`chat.py` handles the `/chat` API.

This project does not need a separate `controllers/` folder. In FastAPI, the `api/` layer acts as the HTTP boundary.

---

## `app/graph/`

Contains the LangGraph workflow.

Responsibilities:

- Define graph state
- Define workflow
- Define nodes
- Define conditional routing
- Handle interruption/resumption
- Control retry flow

### `state.py`

Defines the information carried through the graph.

Possible state information includes:

- User question
- Conversation history
- Retrieved schema context
- Ambiguity result
- Clarification question
- User clarification
- Generated SQL
- Validation result
- SQL execution result
- SQL execution error
- Retry count
- Final answer

### `build_graph.py`

Responsible for assembling the complete LangGraph workflow.

It defines how nodes connect and how the workflow moves between them.

### `graph/nodes/`

Each node represents one meaningful step in the workflow.

- `retrieve_schema.py` — retrieves relevant schema knowledge.
- `check_ambiguity.py` — determines whether the user's request is sufficiently specific.
- `ask_clarification.py` — handles clarification interaction.
- `generate_sql.py` — generates SQL based on the question and available schema context.
- `validate_sql.py` — validates generated SQL before execution.
- `execute_sql.py` — executes validated SQL using the read-only database connection.
- `summarize_answer.py` — converts query results into a clear natural-language response.

---

# 6. AI Layer

## `app/ai/`

Central location for reusable AI infrastructure.

Responsibilities:

- LLM configuration
- Embedding configuration
- Prompts
- Structured output configuration

### `models.py`

Centralizes LLM model creation.

Primary model:

- Mistral

Secondary/fallback model:

- Gemini

The rest of the application should obtain models from this central location instead of creating model instances repeatedly across nodes.

This keeps model configuration consistent and makes changing providers easier.

### `embeddings.py`

Contains embedding-model configuration.

Embeddings are used for schema-related retrieval, not for storing raw database records.

### `prompts.py`

Contains prompts used by the different AI operations.

Examples:

- Ambiguity detection prompt
- SQL generation prompt
- SQL correction prompt
- Result summarization prompt

### `structured_output.py`

Contains reusable structured-output handling for AI responses that need predictable fields.

---

# 7. Database Layer

## `app/db/`

Database infrastructure and database-level operations.

Responsibilities:

- PostgreSQL connection
- Schema extraction
- Vector-store infrastructure

### `connection.py`

Responsible for PostgreSQL connection configuration and connection management.

The target database should expose a dedicated **read-only role** for query execution.

### `schema_extractor.py`

Reads database metadata such as:

- Tables
- Columns
- Data types
- Relationships
- Constraints

This information becomes part of the application's schema knowledge.

### `vector_store.py`

Responsible for pgvector-related infrastructure.

The vector store contains searchable knowledge such as:

- Schema descriptions
- Column descriptions
- Business metadata
- Glossary terms
- Few-shot examples

The system should **not embed raw database records for this purpose**.

---

# 8. Schema Knowledge Layer

## `app/schema/`

Contains Text-to-SQL-specific schema knowledge and retrieval logic.

This is separate from the low-level database layer because schema understanding is an application feature, not just database infrastructure.

### `metadata_config.yaml`

Manual metadata that enriches automatically extracted database schema.

Examples:

- Business meaning of a column
- Important relationships
- Preferred fields
- Metric definitions
- Table descriptions

### `metadata_loader.py`

Loads and prepares manual schema metadata.

### `glossary.yaml`

Business terminology and its database meaning.

Examples:

- Customer → customer table
- Revenue → defined revenue calculation
- Active user → business-specific definition

### `glossary_loader.py`

Loads glossary information for use by the application.

### `retriever.py`

Retrieves the most relevant schema knowledge for the user's question.

The retriever combines the user's question with schema metadata, glossary information, and other indexed schema knowledge.

---

# 9. Data Models

## `app/models/`

Contains application-level structured data models.

### `chat.py`

Models related to:

- Chat requests
- Chat responses
- Thread/session information
- Query results

### `ambiguity.py`

Models the structured output of ambiguity detection.

The ambiguity result should capture information such as:

- Whether the question is ambiguous
- Type of ambiguity
- Missing information
- Clarification question

Keeping this structured makes graph routing predictable.

---

# 10. Service Layer

## `app/services/`

Contains reusable application operations that are not themselves LangGraph nodes.

### `sql_service.py`

Responsible for application-level SQL execution behavior.

Responsibilities:

- Execute validated read-only queries
- Handle database errors
- Return structured query results
- Support retry/error information

The LangGraph execution node calls this service instead of putting all database execution logic directly inside the graph node.

---

# 11. Utilities

## `app/utils/`

Contains generic application utilities.

### `logger.py`

Centralized logging configuration.

Logging can capture:

- Request/thread information
- Graph execution stages
- Generated SQL
- Validation failures
- Database errors
- Retry attempts
- Execution timing

Sensitive data should not be logged unnecessarily.

---

# 12. Scripts

## `scripts/`

Contains manual or one-time operational scripts.

### `ingest_schema.py`

Used to:

- Extract database schema
- Combine it with manual metadata
- Process glossary information
- Generate embeddings
- Store schema knowledge in pgvector

### `test_graph.py`

Used to manually run and inspect the LangGraph workflow without going through the frontend.

---

# 13. Tests

## `tests/`

Focused tests for important pieces of the application.

### `test_ambiguity.py`

Tests whether different natural-language questions are correctly identified as ambiguous or sufficiently specific.

### `test_sql_validation.py`

Tests SQL safety and validation rules.

### `test_schema_retrieval.py`

Tests whether relevant schema context is returned for different business questions.

---

# 14. Complete Request Flow

## Step 1 — User asks a question

The user enters a natural-language business question in the React application.

Example:

> "Show me the best performing salesperson last month."

React sends the question with a `thread_id` to FastAPI.

---

## Step 2 — FastAPI receives the request

The API layer:

1. Receives the request.
2. Validates the request.
3. Passes the question and thread information to LangGraph.
4. Returns the graph response or clarification requirement.

The API layer does not decide how SQL should be generated.

---

## Step 3 — Retrieve schema context

The graph retrieves only the schema information relevant to the question.

Potential context:

- Relevant tables
- Relevant columns
- Relationships
- Metric definitions
- Business glossary terms
- Relevant few-shot examples

The purpose is to give the LLM enough database knowledge without sending the entire database schema every time.

---

## Step 4 — Check ambiguity

The ambiguity node analyzes whether the question contains enough information to safely generate SQL.

Possible ambiguity categories:

- Metric ambiguity
- Time-period ambiguity
- Entity ambiguity
- Grouping ambiguity
- Filter ambiguity
- Ranking ambiguity

Example:

> "best performer"

could mean:

- Highest revenue
- Highest sales
- Most orders
- Highest profit

The system should not guess.

---

# 15. Clarification Loop

If the question is ambiguous:

```text
User Question
      │
      ▼
Ambiguity Detection
      │
      ▼
Ambiguous
      │
      ▼
Ask Clarification
      │
      ▼
Wait for User
      │
      ▼
Resume Same Thread
      │
      ▼
Re-check / Continue Workflow
```

LangGraph interruption and resumption are used so the workflow can pause while waiting for the user's answer.

The clarification should be concise and useful instead of asking unnecessary questions.

---

# 16. SQL Generation

Once the user's intent is sufficiently clear:

```text
User Question
      +
Clarification
      +
Schema Context
      +
Business Metadata
      ↓
SQL Generation
```

The generated SQL must be based only on the known schema and confirmed user intent.

The model should not invent:

- Tables
- Columns
- Relationships
- Metrics
- Business definitions

---

# 17. SQL Validation

Every generated SQL statement passes through a validation layer before execution.

Validation should ensure:

- Query is read-only
- Query is a SELECT-style analytical query
- Known tables are used
- Known columns are used
- Unsafe operations are rejected
- Query complexity is controlled where appropriate
- Result size is limited where appropriate
- SQL syntax is valid

`sqlglot` is used for SQL parsing and validation.

The system should never rely only on the LLM to produce safe SQL.

---

# 18. Read-Only SQL Execution

Validated SQL is executed against PostgreSQL using a dedicated read-only database role.

Architecture:

```text
Generated SQL
     │
     ▼
SQL Validation
     │
     ├── Invalid → Reject / Regenerate
     │
     ▼
Read-Only PostgreSQL Role
     │
     ▼
Query Result
```

The database permission layer provides an additional safety boundary even if an application-level validation mistake occurs.

---

# 19. SQL Error Self-Correction

If a validated query fails during execution:

```text
Execute SQL
    │
    ├── Success → Summarize Result
    │
    └── Error
          │
          ▼
      SQL Regeneration
          │
          ▼
      Validate Again
          │
          ▼
      Execute Again
```

Retry attempts should be limited.

For the POC, the maximum retry count is **3**.

The error message and relevant context can be passed back to the SQL-generation step so the model can correct the query.

---

# 20. Result Summarization

After successful execution:

```text
SQL Result
    +
Original Question
    +
Confirmed Intent
       │
       ▼
Result Summarization
       │
       ▼
Natural Language Answer
```

The final response should explain the result in simple business language.

The response can optionally expose:

- Natural-language answer
- Generated SQL
- Query result table
- Relevant explanation

---

# 21. Memory and Thread Management

The application uses LangGraph thread-based state.

Each conversation receives a `thread_id`.

The thread allows the system to remember the current workflow context, especially when a graph is interrupted for clarification.

### POC

Use:

- LangGraph `MemorySaver`

### Later

Move to:

- PostgreSQL-backed LangGraph checkpointer

This allows persistent conversation/workflow state.

---

# 22. Vector Knowledge Architecture

The vector database is used for **knowledge retrieval**, not as a replacement for the PostgreSQL database.

```text
PostgreSQL Schema
       │
       ▼
Schema Extraction
       │
       +
Manual Metadata
       │
       +
Business Glossary
       │
       ▼
Embeddings
       │
       ▼
pgvector
       │
       ▼
Relevant Schema Context
       │
       ▼
SQL Generation
```

### What is stored in pgvector?

- Table descriptions
- Column descriptions
- Relationships
- Business definitions
- Glossary terms
- Few-shot SQL examples

### What is not stored for retrieval?

- Raw customer records
- Raw transactions
- Complete database data dumps

PostgreSQL remains the source of truth for actual business data.

---

# 23. AI Model Architecture

The application uses multiple model providers behind a centralized AI layer.

```text
                 AI Layer
                    │
        ┌───────────┴───────────┐
        │                       │
     Mistral                  Gemini
     Primary                 Secondary
        │                       │
        └───────────┬───────────┘
                    │
              Graph Nodes
```

The rest of the application should not depend directly on provider-specific model initialization.

This makes it easier to:

- Change models
- Add fallbacks
- Maintain consistent configuration
- Control model usage
- Test different models

---

# 24. Security Architecture

The application should treat generated SQL as untrusted output.

Security layers:

```text
User Input
    │
    ▼
LLM
    │
    ▼
Generated SQL
    │
    ▼
SQL Parser / Validator
    │
    ▼
Read-Only Database Role
    │
    ▼
PostgreSQL
```

Important principles:

- Never allow write operations.
- Never give the application a privileged database role.
- Validate SQL before execution.
- Restrict accessible schema/tables where possible.
- Limit query/result size where appropriate.
- Do not blindly execute model output.
- Keep secrets in environment variables.
- Avoid logging sensitive database information.

---

# 25. Why There Is No `controllers/` Folder

This project uses:

```text
app/api/
```

instead of:

```text
app/controllers/
```

The reason is that FastAPI applications commonly organize HTTP endpoints by API/resource rather than requiring a controller naming convention.

For this project:

```text
api/chat.py
```

is responsible for the HTTP boundary.

While:

```text
graph/nodes/
```

contains the actual workflow logic.

And:

```text
services/
```

contains reusable application operations.

The separation is therefore:

```text
API Layer
   ↓
Graph / Application Workflow
   ↓
Services
   ↓
Database / AI Infrastructure
```

---

# 26. Architecture Responsibilities at a Glance

| Layer | Responsibility |
|---|---|
| `api/` | HTTP/API boundary |
| `graph/` | LangGraph workflow |
| `graph/nodes/` | Individual workflow steps |
| `ai/` | LLM, embeddings and prompts |
| `db/` | PostgreSQL and vector infrastructure |
| `schema/` | Schema knowledge and retrieval |
| `models/` | Structured application models |
| `services/` | Reusable application operations |
| `utils/` | Generic utilities |
| `scripts/` | Manual/one-time jobs |
| `tests/` | Automated tests |
| `logs/` | Application logs |

---

# 27. Technology Stack

## Backend

- Python
- FastAPI
- uv

## AI

- LangChain
- LangGraph
- Mistral
- Gemini
- Structured LLM output

## Database

- PostgreSQL
- pgvector
- Read-only PostgreSQL role

## SQL

- sqlglot

## Memory

- LangGraph MemorySaver for POC
- PostgreSQL checkpointer later

## Frontend

- React
- Vite

---

# 28. POC Scope

The first working version should focus on the core AI workflow.

### Required

- PostgreSQL schema ingestion
- Manual schema metadata
- Business glossary
- pgvector schema retrieval
- Structured ambiguity detection
- Clarification loop
- LangGraph interrupt/resume
- SQL generation
- SQL validation
- Read-only SQL execution
- SQL error correction
- Natural-language result summarization
- React chat UI
- Thread/session management
- Logging
- Core tests

### Later Enhancements

- Persistent PostgreSQL checkpointer
- Authentication
- Multiple database connections
- Advanced permissions
- Query analytics
- Better streaming UX
- Query history
- Saved questions
- Dashboard generation
- Advanced observability

---

# 29. Recommended Development Order

```text
1. Project Scaffolding
        ↓
2. Configuration
        ↓
3. PostgreSQL Connection
        ↓
4. Schema Extraction
        ↓
5. Metadata + Glossary
        ↓
6. pgvector Ingestion
        ↓
7. Schema Retrieval
        ↓
8. LangGraph State
        ↓
9. Ambiguity Detection
        ↓
10. Clarification Loop
        ↓
11. SQL Generation
        ↓
12. SQL Validation
        ↓
13. SQL Execution
        ↓
14. SQL Error Retry
        ↓
15. Result Summarization
        ↓
16. Complete Graph
        ↓
17. FastAPI `/chat`
        ↓
18. Streaming / SSE
        ↓
19. React UI
        ↓
20. End-to-End Integration
        ↓
21. Tests + Logging + README
```

---

# 30. Final Architecture Principle

The project should remain **simple but properly separated**.

The goal is not to create a large enterprise architecture. Each folder should exist because it has a clear responsibility.

The core separation is:

```text
React
  ↓
FastAPI API
  ↓
LangGraph
  ↓
AI + Schema Knowledge + Services
  ↓
PostgreSQL / pgvector
```

The most important business flow is:

```text
Ask
 ↓
Understand
 ↓
Retrieve Schema
 ↓
Detect Ambiguity
 ↓
Clarify if Needed
 ↓
Generate SQL
 ↓
Validate
 ↓
Execute Safely
 ↓
Self-Correct if Needed
 ↓
Explain Result
```

The **clarification-before-SQL** behavior is the central feature that differentiates this project from a basic Text-to-SQL chatbot.
