import uuid
from typing import Any

import psycopg
from fastapi import APIRouter
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.types import Command
from pydantic import BaseModel

from text_to_sql.config import DATABASE_URL
from text_to_sql.db.conversations import create_conversation, get_conversation, get_user_conversations
from text_to_sql.graph.build_graph import build_graph

router = APIRouter(prefix="/api")

# Global checkpointer (initialized once at startup)
_checkpointer = None
_graph = None

def get_graph():
    """Get or create the graph with PostgreSQL checkpointer."""
    global _checkpointer, _graph
    if _graph is None:
        # Create a persistent connection for the checkpointer
        conn = psycopg.connect(DATABASE_URL, autocommit=True)
        _checkpointer = PostgresSaver(conn)
        _checkpointer.setup()
        _graph = build_graph(checkpointer=_checkpointer)
    return _graph

graph = get_graph()


class ChatRequest(BaseModel):
    message: str
    thread_id: str
    user_id: str


class CreateConversationRequest(BaseModel):
    user_id: str
    title: str | None = None


@router.post("/chat")
def chat(request: ChatRequest) -> dict[str, Any]:
    """Process Text-to-SQL request and return final answer."""
    message = request.message.strip()
    thread_id = request.thread_id.strip()
    user_id_str = request.user_id.strip()

    if not message:
        return {"error": "Message is required"}

    if not thread_id:
        return {"error": "thread_id is required"}

    if not user_id_str:
        return {"error": "user_id is required"}

    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        return {"error": "Invalid user_id format"}

    # Check if conversation exists, create if not
    try:
        conversation_id = uuid.UUID(thread_id)
        conversation = get_conversation(conversation_id)
        
        if conversation is None:
            # Create new conversation with this thread_id as conversation_id
            create_conversation(user_id, title=message[:50], conversation_id=conversation_id)
    except ValueError:
        return {"error": "Invalid thread_id format (must be UUID)"}

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


@router.post("/conversations")
def create_conversation_endpoint(request: CreateConversationRequest) -> dict[str, Any]:
    """Create a new conversation and return its ID."""
    user_id_str = request.user_id.strip()

    if not user_id_str:
        return {"error": "user_id is required"}

    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        return {"error": "Invalid user_id format"}

    try:
        conversation_id = create_conversation(user_id, request.title)
        return {
            "status": "created",
            "conversation_id": str(conversation_id),
            "user_id": str(user_id),
            "title": request.title
        }
    except (ValueError, RuntimeError, ConnectionError) as e:
        return {"error": f"Failed to create conversation: {str(e)}"}


@router.get("/conversations/{user_id}")
def get_user_conversations_endpoint(user_id: str) -> dict[str, Any]:
    """Get all conversations for a user."""
    user_id_str = user_id.strip()

    if not user_id_str:
        return {"error": "user_id is required"}

    try:
        user_uuid = uuid.UUID(user_id_str)
    except ValueError:
        return {"error": "Invalid user_id format"}

    try:
        conversations = get_user_conversations(user_uuid)
        return {
            "status": "success",
            "conversations": conversations,
            "count": len(conversations)
        }
    except (ValueError, RuntimeError, ConnectionError) as e:
        return {"error": f"Failed to get conversations: {str(e)}"}