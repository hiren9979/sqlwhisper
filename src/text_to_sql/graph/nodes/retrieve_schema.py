from text_to_sql.graph.state import AgentState
from text_to_sql.schema.retriever import retrieve_documents


def retrieve_schema(state: AgentState):
    """Retrieve relevant schema context for the user query."""
    user_query = state.get("user_query", "")
    if not user_query.strip():
        raise ValueError("User query cannot be empty")

    schema_context = retrieve_documents(user_query, top_k=5)
    return {"schema_context": schema_context}
