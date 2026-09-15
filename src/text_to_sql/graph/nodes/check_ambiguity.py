from pydantic import BaseModel

from text_to_sql.ai.model_config import get_llm_model
from text_to_sql.graph.state import AgentState


class AmbiguityResult(BaseModel):
    is_ambiguous: bool
    ambiguity_type: str
    missing_slots: list[str]
    clarification_question: str


AMBIGUITY_PROMPT = """
You are an ambiguity detection system for a Text-to-SQL application.

Your job is to determine whether the user's question contains enough
information to generate correct SQL.

Mark the question as ambiguous when important information is missing,
such as:
- metric
- time period
- entity
- filter
- ranking criteria
- comparison criteria

Do not mark a question as ambiguous when its intent is clear enough
to generate SQL.

Rules:

1. If the question is clear:
   - is_ambiguous must be false
   - ambiguity_type must be "none"
   - missing_slots must be []
   - clarification_question must be ""

2. If the question is ambiguous:
   - is_ambiguous must be true
   - identify the main ambiguity_type
   - list the missing information in missing_slots
   - ask one concise clarification question

3. Do not invent missing information.

4. The clarification question should help the user provide
   the exact information required to generate SQL.

User question:
{user_query}
"""


def check_ambiguity(state: AgentState):
    user_query = state["user_query"]

    if not user_query or not user_query.strip():
        raise ValueError("User query cannot be empty")

    model = get_llm_model().with_structured_output(AmbiguityResult)

    result = model.invoke(AMBIGUITY_PROMPT.format(user_query=user_query))

    return {
        "ambiguity_check": result.is_ambiguous,
        "ambiguity_type": result.ambiguity_type,
        "missing_slots": result.missing_slots,
        "clarification_question": result.clarification_question,
    }