from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from text_to_sql.graph.nodes.ask_clarification import ask_clarification
from text_to_sql.graph.nodes.check_ambiguity import check_ambiguity
from text_to_sql.graph.nodes.check_clarification_relevance import check_clarification_relevance
from text_to_sql.graph.nodes.execute_sql import execute_sql
from text_to_sql.graph.nodes.generate_sql import generate_sql
from text_to_sql.graph.nodes.retrieve_schema import retrieve_schema
from text_to_sql.graph.nodes.summarize_answer import summarize_answer
from text_to_sql.graph.nodes.validate_sql import validate_sql_node
from text_to_sql.graph.state import AgentState


def route_after_ambiguity(state: AgentState):
    if state["ambiguity_check"]:
        return "ask_clarification"
    return "generate_sql"


def route_after_relevance(state: AgentState):
    if not state.get("is_relevant", True):
        return "ask_clarification"
    return "check_ambiguity"


def route_after_validation(state: AgentState):
    if state.get("sql_error"):
        return "generate_sql"
    return "execute_sql"


def route_after_execution(state: AgentState):
    if state.get("sql_error"):
        return "generate_sql"
    return "summarize_answer"


def build_graph():
    graph = StateGraph(AgentState)

    # Nodes
    graph.add_node("retrieve_schema", retrieve_schema)
    graph.add_node("check_ambiguity", check_ambiguity)
    graph.add_node("ask_clarification", ask_clarification)
    graph.add_node("check_clarification_relevance", check_clarification_relevance)
    graph.add_node("generate_sql", generate_sql)
    graph.add_node("validate_sql", validate_sql_node)
    graph.add_node("execute_sql", execute_sql)
    graph.add_node("summarize_answer", summarize_answer)

    # Start
    graph.add_edge(START, "retrieve_schema")

    # Schema → ambiguity check
    graph.add_edge("retrieve_schema", "check_ambiguity")

    # Ambiguity routing
    graph.add_conditional_edges(
        "check_ambiguity",
        route_after_ambiguity,
        {
            "ask_clarification": "ask_clarification",
            "generate_sql": "generate_sql",
        },
    )

    # After clarification, check relevance
    graph.add_edge("ask_clarification", "check_clarification_relevance")

    # Relevance routing
    graph.add_conditional_edges(
        "check_clarification_relevance",
        route_after_relevance,
        {
            "ask_clarification": "ask_clarification",
            "check_ambiguity": "check_ambiguity",
        },
    )

    # SQL generation pipeline
    graph.add_edge("generate_sql", "validate_sql")

    # Validation routing
    graph.add_conditional_edges(
        "validate_sql",
        route_after_validation,
        {
            "generate_sql": "generate_sql",
            "execute_sql": "execute_sql",
        },
    )

    # Execution routing
    graph.add_conditional_edges(
        "execute_sql",
        route_after_execution,
        {
            "generate_sql": "generate_sql",
            "summarize_answer": "summarize_answer",
        },
    )

    # Final answer
    graph.add_edge("summarize_answer", END)

    # Compile with in-memory checkpointer
    memory = MemorySaver()
    return graph.compile(checkpointer=memory)