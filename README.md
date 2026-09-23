# SQLWhisper - Text-to-SQL Clarification Engine

A full-stack AI application that allows non-technical users to ask business questions about a PostgreSQL database using natural language. The system retrieves relevant schema context, detects ambiguity, asks clarification when required, and generates PostgreSQL SQL queries.

## 🎯 Core Feature: Clarification Loop

Unlike traditional text-to-SQL systems that guess user intent, SQLWhisper actively detects ambiguous queries and asks for clarification before generating SQL. This ensures accurate query generation by understanding exactly what the user wants.


## ✅ Currently Implemented

### Phase 1-3: Database Foundation
- PostgreSQL database connection
- Schema extraction from live database
- Environment configuration with `.env` support

### Phase 4: Schema Documentation
- **metadata_config.yaml**: Human/business descriptions for tables and columns
- **metadata_loader.py**: Merges live schema with business descriptions
- **glossary.yaml**: Business terms and their SQL equivalents
- **glossary_loader.py**: Loads glossary for LLM context

### Phase 5: Vector Ingestion
- **embedding_documents.py**: Builds documents from schema, glossary, and few-shot examples
- **embed_and_store.py**: Generates embeddings (MistralAI) and stores in PostgreSQL/pgvector
- Automatic upsert to handle document updates

### Phase 6: Semantic Retrieval
- **retriever.py**: Retrieves relevant schema context using vector similarity search
- Uses pgvector cosine similarity for efficient context retrieval
- Returns top-K most relevant documents for SQL generation

### Phase 7: LangGraph State Management
- **graph/state.py**: Defines shared `AgentState` for workflow data
- Fields: user_query, schema_context, ambiguity_check, sql_query, sql_result, final_answer, messages, retry_count

### Phase 8: Ambiguity Detection
- **graph/nodes/check_ambiguity.py**: Detects ambiguous queries using LLM
- Returns: is_ambiguous, ambiguity_type, missing_slots, clarification_question
- Uses Groq LLM for fast classification

### Phase 9: User Clarification
- **graph/nodes/ask_clarification.py**: Pauses workflow to ask user for missing information
- Uses LangGraph `interrupt()` for interactive clarification
- Updates user query with clarification context

### Phase 10: SQL Generation
- **graph/nodes/generate_sql.py**: Generates PostgreSQL SQL from natural language
- Uses retrieved schema context and few-shot examples
- Respects soft-delete patterns and business definitions
- Uses Groq LLM for SQL generation

### Phase 11: SQL Validation
- **graph/nodes/validate_sql.py**: Validates generated SQL syntax
- Checks for dangerous operations and schema compliance
- Handles validation errors with retry logic

### Phase 12: SQL Execution
- **graph/nodes/execute_sql.py**: Executes SQL against PostgreSQL database
- Uses read-only database role with timeout protection
- Returns query results or error information

### Phase 13: Final Answer Generation
- **graph/nodes/summarize_answer.py**: Converts SQL results to natural language
- Formats results for user-friendly display
- Handles edge cases (empty results, errors)

### Phase 14: Conversation Persistence
- **db/conversations.py**: Conversation management with PostgreSQL
- **db/init_checkpoint.py**: LangGraph checkpoint table initialization
- PostgreSQL-backed LangGraph checkpointer for conversation state persistence
- Conversation resume functionality across application restarts
- Thread-based conversation tracking with user association

### Phase 15: FastAPI Chat Endpoint
- **api/chat.py**: REST API endpoints for chat functionality
- POST /chat: Process text-to-SQL requests with thread management
- POST /conversations: Create new conversations
- GET /conversations/{user_id}: Get user conversations
- Handles clarification flow across multiple API calls

### Model Configuration
- **ai/model_config.py**: Centralized model configuration with multiple provider support
- Embeddings: Google Generative AI (gemini-embedding-2)
- LLM: Configurable provider (Groq, MistralAI, or Google Generative AI)
- Default: Google Generative AI (gemini-3.5-flash-lite) for efficient inference

### Testing
- **tests/test_end_to_end.py**: Comprehensive integration tests covering all phases
- Tests database connection, schema extraction, metadata loading, glossary loading
- Tests embedding generation, ingestion, retrieval
- Tests ambiguity detection with interactive clarification loop
- Tests SQL generation with schema context
- **tests/test_checkpoint_persistence.py**: PostgreSQL checkpoint persistence testing
- **tests/test_interactive_conversation.py**: Real-time interactive conversation testing

### API
- **main.py**: FastAPI application with chat endpoints
- **api/chat.py**: REST API for conversation management and text-to-SQL processing

## 🚧 Planned Features

### Phase 17: Streaming (SSE)
- Convert `/chat` to stream intermediate state updates via Server-Sent Events
- Client sees incremental status updates before final answer arrives
- Error handling for SSE stream interruptions and client disconnections

### Phase 18: Frontend
- React/Vue.js chat interface
- Real-time clarification UI
- Result visualization (tables, charts)

## 🏗️ Architecture

```
User Question
    ↓
Ambiguity Detection (Phase 8)
    ↓ (if ambiguous)
Ask Clarification (Phase 9)
    ↓
Retrieve Schema Context (Phase 6)
    ↓
Generate SQL (Phase 10)
    ↓
Validate SQL (Phase 11)
    ↓ (if validation fails)
Retry SQL Generation
    ↓ (if valid)
Execute SQL (Phase 12)
    ↓
Generate Final Answer (Phase 13)
    ↓
PostgreSQL Checkpoint Persistence (Phase 14)
```

## 📁 Project Structure

```
src/text_to_sql/
├── db/
│   ├── connection.py          # PostgreSQL connection
│   ├── schema_extractor.py    # Live schema extraction
│   ├── conversations.py       # Conversation management
│   ├── init_db.py            # Database initialization
│   └── init_checkpoint.py     # LangGraph checkpoint initialization
├── schema/
│   ├── metadata_config.yaml   # Table/column descriptions
│   ├── metadata_loader.py     # Merge schema with metadata
│   ├── glossary.yaml          # Business terms
│   ├── glossary_loader.py     # Load glossary
│   ├── few_shot_example.yaml  # Example queries
│   ├── embedding_documents.py # Build embedding documents
│   ├── embed_and_store.py     # Generate & store embeddings
│   └── retriever.py           # Retrieve relevant context
├── graph/
│   ├── state.py               # LangGraph state definition
│   ├── build_graph.py         # Graph construction with checkpointer
│   └── nodes/
│       ├── check_ambiguity.py         # Ambiguity detection
│       ├── ask_clarification.py       # User clarification
│       ├── check_clarification_relevance.py # Clarification relevance check
│       ├── generate_sql.py            # SQL generation
│       ├── validate_sql.py            # SQL validation
│       ├── execute_sql.py            # SQL execution
│       ├── retrieve_schema.py         # Schema retrieval
│       └── summarize_answer.py        # Final answer generation
├── ai/
│   └── model_config.py        # Model configuration
├── api/
│   └── chat.py               # REST API endpoints
├── config.py                 # Application configuration
├── main.py                   # FastAPI app
└── tests/
    ├── test_end_to_end.py    # Comprehensive integration tests
    ├── test_checkpoint_persistence.py # Checkpoint persistence tests
    └── test_interactive_conversation.py # Interactive conversation tests
```

## 🚀 Setup

### Prerequisites
- Python 3.10+
- PostgreSQL with pgvector extension
- API keys for MistralAI and Groq

### Installation

```bash
# Clone the repository
git clone https://github.com/hiren9979/sqlwhisper.git
cd sqlwhisper

# Install dependencies
uv sync

# Copy environment variables
cp .env.example .env

# Edit .env with your API keys and database URL
```

### Environment Variables

```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/dbname

# LLM Provider (groq, mistral, or gemini)
LLM_PROVIDER=gemini

# API Keys (based on provider)
GOOGLE_API_KEY=your_google_api_key
GROQ_API_KEY=your_groq_api_key
MISTRAL_API_KEY=your_mistral_api_key

# Model Configuration (optional)
GEMINI_MODEL=gemini-3.5-flash-lite
GROQ_MODEL=llama-3.1-70b-versatile
MISTRAL_MODEL=mistral-small-2603
```

### Database Setup

```bash
# Create PostgreSQL database with pgvector extension
createdb text-to-sql
psql text-to-sql -c "CREATE EXTENSION IF NOT EXISTS vector;"

# Run schema migration (if available)
# Or use your existing database schema
```

## 🧪 Running Tests

```bash
# Run end-to-end integration tests
uv run python src/text_to_sql/tests/test_end_to_end.py

# Run checkpoint persistence tests
uv run python src/text_to_sql/tests/test_checkpoint_persistence.py

# Run interactive conversation test (real-time)
uv run python src/text_to_sql/tests/test_interactive_conversation.py
```

The test suite covers:
1. Database connection and schema extraction
2. Metadata and glossary loading
3. Embedding document building and ingestion
4. Semantic retrieval with vector similarity
5. Ambiguity detection and clarification flow
6. SQL generation with schema context
7. SQL validation and execution
8. Final answer generation
9. PostgreSQL checkpoint persistence
10. Conversation management and resume functionality

## 🏃 Running the Application

```bash
# Start FastAPI server
uv run uvicorn text_to_sql.main:app --reload

# Or use the provided script
uv run python -m text_to_sql.main
```

## 📊 Example Workflow

```
User: "Show me sales"
    ↓
System: (Ambiguity detected)
    ↓
System: "What time period? What metric (total revenue, number of orders)?"
    ↓
User: "Current month, total revenue"
    ↓
System: (Retrieves orders, order_items schema via vector search)
    ↓
System: (Generates SQL with schema context)
    ↓
System: (Validates SQL for safety and correctness)
    ↓
System: (Executes SQL against PostgreSQL)
    ↓
System: (Converts results to natural language)
    ↓
Answer: "The total sales for the current month is $15,234.56"
    ↓
System: (Conversation state persisted in PostgreSQL)
```

## 🛠️ Tech Stack

- **Database**: PostgreSQL with pgvector
- **Embeddings**: Google Generative AI (gemini-embedding-2)
- **LLM**: Configurable (Google Generative AI, Groq, or MistralAI)
- **Orchestration**: LangGraph with PostgreSQL checkpoint persistence
- **API**: FastAPI
- **Python**: 3.10+
- **Package Manager**: uv

## 📝 License

MIT License - see LICENSE file for details

## 🤝 Contributing

Contributions welcome! Please read CONTRIBUTING.md for guidelines.

## 📧 Contact

For questions or support, please open an issue on GitHub.
