from langchain_core.messages import HumanMessage

from text_to_sql.ai.model_config import get_llm_model
from text_to_sql.graph.state import AgentState


def summarize_answer(state: AgentState):
    user_query = state["user_query"]
    sql_result = state["sql_result"]

    prompt = f"""
You are an assistant that answers questions using SQL query results.

Original user question:
{user_query}

SQL query result:
{sql_result}

Instructions:
- Answer the user's original question directly.
- Use only the information present in the SQL result.
- Do not invent, assume, or add information that is not in the result.
- Keep the answer concise and natural.
- If the result is empty, clearly say that no matching data was found.
- Do not mention SQL, database, query execution, or internal processing.
"""

    model = get_llm_model()
    response = model.invoke([HumanMessage(content=prompt)])

    return {"final_answer": response.content}