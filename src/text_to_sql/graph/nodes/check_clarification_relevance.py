from langchain_core.output_parsers import StrOutputParser

from text_to_sql.ai.model_config import get_llm_model
from text_to_sql.graph.state import AgentState


RELEVANCE_PROMPT = """
You are checking if a user's answer is relevant to a clarification question.

Clarification question:
{clarification_question}

User's answer:
{user_answer}

Determine if the user's answer directly addresses the clarification question.

Rules:
- If the answer provides the requested information (metric, time period, entity, etc.), return "relevant"
- If the answer is unrelated (e.g., "how are you?", "hello", random text), return "irrelevant"
- If the answer is partially relevant but incomplete, return "relevant" (the ambiguity check will handle completeness)

Return ONLY "relevant" or "irrelevant", nothing else.
"""


def check_clarification_relevance(state: AgentState):
    """Check if the user's clarification answer is relevant to the question."""
    clarification_question = state.get("clarification_question", "")
    user_answer = state.get("user_answer", "")

    if not clarification_question or not user_answer:
        return {"is_relevant": True}

    parser = StrOutputParser()
    model = get_llm_model() | parser

    prompt = RELEVANCE_PROMPT.format(
        clarification_question=clarification_question,
        user_answer=user_answer,
    )

    result = model.invoke(prompt).strip().lower()

    is_relevant = result == "relevant"

    if not is_relevant:
        return {
            "is_relevant": False,
            "clarification_question": f"Please answer the clarification question: {clarification_question}",
        }

    return {"is_relevant": True}
