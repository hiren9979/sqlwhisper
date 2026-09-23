import uuid
from datetime import datetime
from typing import Optional

from text_to_sql.db.connection import get_connection


def create_conversation(user_id: uuid.UUID, title: Optional[str] = None, conversation_id: Optional[uuid.UUID] = None) -> uuid.UUID:
    """Create a new conversation and return its ID.
    
    Args:
        user_id: The user's UUID
        title: Optional conversation title
        conversation_id: Optional specific conversation ID. If not provided, generates a new UUID.
    
    Returns:
        The conversation ID (either provided or generated)
    """
    if conversation_id is None:
        conversation_id = uuid.uuid4()
    
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO conversations (id, user_id, title, created_at, updated_at, is_deleted)
                VALUES (%s, %s, %s, NOW(), NOW(), FALSE)
                RETURNING id
                """,
                (conversation_id, user_id, title)
            )
            connection.commit()
            return conversation_id


def get_conversation(conversation_id: uuid.UUID) -> Optional[dict]:
    """Get a conversation by ID, return None if not found or deleted."""
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, user_id, title, created_at, updated_at, is_deleted
                FROM conversations
                WHERE id = %s AND is_deleted = FALSE
                """,
                (conversation_id,)
            )
            row = cursor.fetchone()
            if row:
                return {
                    "id": str(row[0]),
                    "user_id": str(row[1]),
                    "title": row[2],
                    "created_at": row[3].isoformat() if row[3] else None,
                    "updated_at": row[4].isoformat() if row[4] else None,
                    "is_deleted": row[5]
                }
            return None


def update_conversation(conversation_id: uuid.UUID, title: Optional[str] = None) -> bool:
    """Update conversation title and updated_at timestamp."""
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE conversations
                SET title = %s, updated_at = NOW()
                WHERE id = %s AND is_deleted = FALSE
                """,
                (title, conversation_id)
            )
            connection.commit()
            return cursor.rowcount > 0


def delete_conversation(conversation_id: uuid.UUID) -> bool:
    """Soft delete a conversation by setting is_deleted to TRUE."""
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE conversations
                SET is_deleted = TRUE, updated_at = NOW()
                WHERE id = %s
                """,
                (conversation_id,)
            )
            connection.commit()
            return cursor.rowcount > 0


def get_user_conversations(user_id: uuid.UUID) -> list[dict]:
    """Get all non-deleted conversations for a user."""
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, user_id, title, created_at, updated_at, is_deleted
                FROM conversations
                WHERE user_id = %s AND is_deleted = FALSE
                ORDER BY updated_at DESC
                """,
                (user_id,)
            )
            rows = cursor.fetchall()
            return [
                {
                    "id": str(row[0]),
                    "user_id": str(row[1]),
                    "title": row[2],
                    "created_at": row[3].isoformat() if row[3] else None,
                    "updated_at": row[4].isoformat() if row[4] else None,
                    "is_deleted": row[5]
                }
                for row in rows
            ]
