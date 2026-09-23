import json

from langchain_core.output_parsers import StrOutputParser

from text_to_sql.ai.model_config import get_llm_model
from text_to_sql.graph.state import AgentState


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

Return your response as a JSON object with these exact keys:
is_ambiguous, ambiguity_type, missing_slots, clarification_question

User question:
{user_query}

Recent conversation context (oldest first; may be empty):
{conversation_context}
"""


def format_conversation_context(messages: list[dict[str, str]]) -> str:
    if not messages:
        return "No previous messages."
    return "\n".join(f"{message['role']}: {message['content']}" for message in messages)


def check_ambiguity(state: AgentState):
    user_query = state["user_query"]
    if not user_query or not user_query.strip():
        raise ValueError("User query cannot be empty")

    parser = StrOutputParser()
    model = get_llm_model() | parser
    content = model.invoke(AMBIGUITY_PROMPT.format(
        user_query=user_query,
        conversation_context=format_conversation_context(state.get("conversation_context", [])),
    ))

    # Extract JSON from markdown code blocks if present
    if "```json" in content:
        content = content.split("```json")[1].split("```")[0].strip()
    elif "```" in content:
        content = content.split("```")[1].split("```")[0].strip()

    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        # Fallback to default values if JSON parsing fails
        return {
            "ambiguity_check": False,
            "ambiguity_type": "none",
            "missing_slots": [],
            "clarification_question": "",
        }

    return {
        "ambiguity_check": parsed.get("is_ambiguous", False),
        "ambiguity_type": parsed.get("ambiguity_type", "none"),
        "missing_slots": parsed.get("missing_slots", []),
        "clarification_question": parsed.get("clarification_question", ""),
    }
