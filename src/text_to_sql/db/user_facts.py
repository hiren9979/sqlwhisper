import uuid
from typing import Optional

from text_to_sql.db.connection import get_connection


def upsert_user_fact(user_id: uuid.UUID, fact_key: str, fact_value: str) -> None:
    """Insert or update a user fact.
    
    Args:
        user_id: The user's UUID
        fact_key: The fact key (e.g., "name", "email", "preference")
        fact_value: The fact value
    """
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO user_facts (user_id, fact_key, fact_value, created_at, updated_at)
                VALUES (%s, %s, %s, NOW(), NOW())
                ON CONFLICT (user_id, fact_key)
                DO UPDATE SET fact_value = %s, updated_at = NOW()
                """,
                (user_id, fact_key, fact_value, fact_value)
            )
            connection.commit()


def get_user_fact(user_id: uuid.UUID, fact_key: str) -> Optional[str]:
    """Get a specific fact for a user.
    
    Args:
        user_id: The user's UUID
        fact_key: The fact key to retrieve
        
    Returns:
        The fact value if found, None otherwise
    """
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT fact_value
                FROM user_facts
                WHERE user_id = %s AND fact_key = %s
                """,
                (user_id, fact_key)
            )
            row = cursor.fetchone()
            return row[0] if row else None


def get_all_user_facts(user_id: uuid.UUID) -> dict[str, str]:
    """Get all facts for a user.
    
    Args:
        user_id: The user's UUID
        
    Returns:
        Dictionary mapping fact_key to fact_value
    """
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT fact_key, fact_value
                FROM user_facts
                WHERE user_id = %s
                """,
                (user_id,)
            )
            return {row[0]: row[1] for row in cursor.fetchall()}


def delete_user_fact(user_id: uuid.UUID, fact_key: str) -> bool:
    """Delete a specific fact for a user.
    
    Args:
        user_id: The user's UUID
        fact_key: The fact key to delete
        
    Returns:
        True if a fact was deleted, False otherwise
    """
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                DELETE FROM user_facts
                WHERE user_id = %s AND fact_key = %s
                """,
                (user_id, fact_key)
            )
            connection.commit()
            return cursor.rowcount > 0
