from typing import Any

from fastapi import APIRouter
from langgraph.types import Command
from pydantic import BaseModel

from text_to_sql.graph.build_graph import build_graph

router = APIRouter(prefix="/api")
graph = build_graph()


class ChatRequest(BaseModel):
    message: str
    thread_id: str


@router.post("/chat")
def chat(request: ChatRequest) -> dict[str, Any]:
    """Process Text-to-SQL request and return final answer."""
    message = request.message.strip()
    thread_id = request.thread_id.strip()

    if not message:
        return {"error": "Message is required"}

    if not thread_id:
        return {"error": "thread_id is required"}

    config = {"configurable": {"thread_id": thread_id}}
    state = graph.get_state(config)

    if state.next:
        result = graph.invoke(Command(resume=message), config=config)
    else:
        initial_state = {
            "messages": [],
            "user_query": message,
            "schema_context": "",
            "ambiguity_check": False,
            "ambiguity_type": "",
            "missing_slots": [],
            "clarification_question": "",
            "sql_query": "",
            "sql_result": [],
            "final_answer": "",
            "retry_count": 0,
            "sql_error": None,
        }
        result = graph.invoke(initial_state, config=config)

    if result.get("ambiguity_check"):
        return {"status": "clarification_required", "question": result["clarification_question"]}

    return {
        "status": "completed",
        "answer": result.get("final_answer"),
        "sql": result.get("sql_query"),
        "result": result.get("sql_result"),
    }