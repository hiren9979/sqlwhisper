from typing import Any, TypedDict

# total=False allows fields to be optional since not all fields
# will be available at the beginning of the workflow.

class AgentState(TypedDict, total=False):
    messages: list[Any]
    user_query: str
    schema_context: list[dict[str, Any]]
    ambiguity_check: bool
    ambiguity_type: str
    missing_slots: list[str]
    clarification_question: str
    sql_query: str
    sql_result: Any
    final_answer: str
    retry_count: int