from typing import Any, TypedDict

# total=False allows fields to be optional since not all fields
# will be available at the beginning of the workflow.

class AgentState(TypedDict, total=False):
    messages: list[Any]
    user_query: str
    user_answer: str
    schema_context: list[dict[str, Any]]
    ambiguity_check: bool
    ambiguity_type: str
    missing_slots: list[str]
    clarification_question: str
    is_relevant: bool
    sql_query: str
    sql_result: Any
    sql_error: Any
    final_answer: str
    retry_count: int