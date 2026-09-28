import uuid

from text_to_sql.db.conversations import get_recent_messages
from text_to_sql.graph.state import AgentState


def load_conversation_context(state: AgentState):
    """Load recent conversation context for the current conversation."""
    conversation_id_str = state.get("conversation_id", "")
    
    if not conversation_id_str:
        return {"conversation_context": []}
    
    try:
        conversation_id = uuid.UUID(conversation_id_str)
    except ValueError:
        return {"conversation_context": []}
    
    conversation_context = get_recent_messages(conversation_id, limit=10)
    return {"conversation_context": conversation_context}
