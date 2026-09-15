from pydantic import BaseModel

from text_to_sql.ai.model_config import get_llm_model
from text_to_sql.graph.state import AgentState


class SQLGenerationResult(BaseModel):
    sql_query: str


SQL_GENERATION_PROMPT = """
You are a PostgreSQL SQL generation system.

Your job is to convert the user's natural-language question into
a correct PostgreSQL SQL query.

Use ONLY the tables, columns, relationships, business definitions,
and examples provided in the context.

Rules:

1. Generate PostgreSQL SQL only.
2. Do not invent tables or columns.
3. Do not invent relationships between tables.
4. Use the exact column and table names from the schema context.
5. Follow the business definitions from the glossary.
6. Use the few-shot examples as guidance for SQL style and business logic.
7. Prefer explicit JOIN conditions.
8. For customer/product/order queries, respect soft-delete fields when
   the provided examples or business definitions indicate that records
   should be active.
9. Do not use SELECT * unless it is clearly appropriate.
10. Do not add explanations.
11. Return exactly one SQL query.

Resolved user question:
{user_query}

Relevant schema and business context:
{schema_context}

Relevant few-shot examples:
{few_shot_examples}

Return ONLY the SQL query, nothing else.
"""


def format_schema_context(schema_context):
    if not schema_context:
        return "No schema context provided."

    return "\n\n".join(
        f"Document: {document['document_key']}\nType: {document['document_type']}\n{document['content']}"
        for document in schema_context
    )


def format_few_shot_examples(schema_context):
    examples = [doc for doc in schema_context if doc["document_type"] == "few_shot"]

    if not examples:
        return "No few-shot examples provided."

    return "\n\n".join(doc["content"] for doc in examples[:3])


def generate_sql(state: AgentState):
    """Generate PostgreSQL SQL from the resolved user question."""
    user_query = state.get("user_query", "")
    schema_context = state.get("schema_context", [])

    if not user_query.strip():
        raise ValueError("User query cannot be empty")

    if not schema_context:
        raise ValueError("Schema context is required for SQL generation")

    model = get_llm_model()

    formatted_schema_context = format_schema_context(schema_context)
    few_shot_examples = format_few_shot_examples(schema_context)

    prompt = SQL_GENERATION_PROMPT.format(
        user_query=user_query,
        schema_context=formatted_schema_context,
        few_shot_examples=few_shot_examples,
    )

    result = model.invoke(prompt)

    sql_query = result.content.strip()

    # Extract SQL from markdown code blocks if present
    if "```sql" in sql_query:
        sql_query = sql_query.split("```sql")[1].split("```")[0].strip()
    elif "```" in sql_query:
        sql_query = sql_query.split("```")[1].split("```")[0].strip()

    return {"sql_query": sql_query}