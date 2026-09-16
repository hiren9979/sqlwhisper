from langgraph.types import interrupt
from text_to_sql.graph.state import AgentState


def ask_clarification(state: AgentState):
    """Pause the graph and ask the user for missing information."""
    if not state.get("ambiguity_check"):
        return {}

    clarification_question = state.get("clarification_question", "")
    if not clarification_question:
        raise ValueError("Clarification question is missing")

    user_answer = interrupt(clarification_question)

    updated_query = f"{state['user_query']}\nUser clarification: {user_answer}"

    return {"user_query": updated_query, "user_answer": user_answer}