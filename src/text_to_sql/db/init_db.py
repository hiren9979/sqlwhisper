from text_to_sql.db.connection import get_connection


def init_conversations_table():
    """Create the conversations table if it doesn't exist."""
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id UUID PRIMARY KEY,
                    user_id UUID NOT NULL,
                    title TEXT,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    is_deleted BOOLEAN NOT NULL DEFAULT FALSE
                )
            """)
            connection.commit()
            print("Conversations table created successfully")


if __name__ == "__main__":
    init_conversations_table()
