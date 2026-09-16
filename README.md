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

### Model Configuration
- **ai/model_config.py**: Centralized model configuration
- Embeddings: MistralAI (mistral-embed)
- LLM: Groq (llama3-70b-8192) for fast, cost-effective inference

### Testing
- **tests/test1.py**: Comprehensive integration tests covering all phases
- Tests database connection, schema extraction, metadata loading, glossary loading
- Tests embedding generation, ingestion, retrieval
- Tests ambiguity detection with interactive clarification loop
- Tests SQL generation with schema context

### API
- **main.py**: FastAPI application with health endpoint

## 🚧 Planned Features

### Phase 11: SQL Validation
- Validate generated SQL syntax
- Check for dangerous operations (DROP, DELETE, etc.)
- Ensure schema compliance

### Phase 12: SQL Execution
- Execute SQL using read-only database role
- Handle execution errors gracefully
- Return query results

### Phase 13: Final Answer Generation
- Convert SQL results to natural language
- Format results for user-friendly display
- Handle edge cases (empty results, errors)

### Phase 14: Retry Logic
- Automatic retry on SQL generation failures
- Incremental error feedback to LLM
- Max retry limits to prevent infinite loops

### Phase 15: FastAPI Endpoints
- `/query`: Main endpoint for text-to-SQL conversion
- `/health`: Health check (already implemented)
- WebSocket support for real-time clarification

### Phase 16: Frontend
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
    ↓ (planned)
Validate SQL (Phase 11)
    ↓ (planned)
Execute SQL (Phase 12)
    ↓ (planned)
Generate Final Answer (Phase 13)
```

## 📁 Project Structure

```
src/text_to_sql/
├── db/
│   ├── connection.py          # PostgreSQL connection
│   └── schema_extractor.py    # Live schema extraction
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
│   └── nodes/
│       ├── check_ambiguity.py # Ambiguity detection
│       ├── ask_clarification.py # User clarification
│       └── generate_sql.py    # SQL generation
├── ai/
│   └── model_config.py        # Model configuration
├── main.py                    # FastAPI app
└── tests/
    └── test1.py               # Integration tests
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
MISTRAL_API_KEY=your_mistral_api_key
GROQ_API_KEY=your_groq_api_key
DATABASE_URL=postgresql://user:password@localhost:5432/dbname
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
# Run all integration tests
uv run python src/text_to_sql/tests/test1.py
```

The test suite covers:
1. Database connection
2. Schema extraction
3. Metadata and glossary loading
4. Embedding document building
5. Document ingestion with embeddings
6. Semantic retrieval
7. Ambiguity detection
8. Interactive clarification loop
9. SQL generation

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
System: (Retrieves orders, order_items schema)
    ↓
System: (Generates SQL)
    ↓
SQL: SELECT SUM(oi.subtotal) AS total_sales
     FROM orders o
     JOIN order_items oi ON o.id = oi.order_id
     WHERE o.order_date >= date_trunc('month', current_timestamp)
       AND o.order_date < date_trunc('month', current_timestamp) + interval '1 month'
```

## 🛠️ Tech Stack

- **Database**: PostgreSQL with pgvector
- **Embeddings**: MistralAI (mistral-embed)
- **LLM**: Groq (llama3-70b-8192)
- **Orchestration**: LangGraph
- **API**: FastAPI
- **Python**: 3.10+
- **Package Manager**: uv

## 📝 License

MIT License - see LICENSE file for details

## 🤝 Contributing

Contributions welcome! Please read CONTRIBUTING.md for guidelines.

## 📧 Contact

For questions or support, please open an issue on GitHub.
