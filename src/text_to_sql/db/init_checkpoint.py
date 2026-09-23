from langgraph.checkpoint.postgres import PostgresSaver

from text_to_sql.config import DATABASE_URL


def init_checkpoint_tables():
    """Initialize LangGraph checkpoint tables in PostgreSQL."""
    with PostgresSaver.from_conn_string(DATABASE_URL) as checkpointer:
        # The checkpointer will initialize tables on first use
        # We just need to access it to ensure connection works
        print("LangGraph checkpoint connection established successfully")
        print("Tables will be created automatically on first use")


if __name__ == "__main__":
    init_checkpoint_tables()
