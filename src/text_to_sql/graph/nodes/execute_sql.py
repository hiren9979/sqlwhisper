from text_to_sql.db.connection import get_connection
from text_to_sql.graph.state import AgentState

QUERY_TIMEOUT_MS = 5000

def execute_sql(state: AgentState):
    """Execute validated SQL against the database."""
    sql_query = state.get("sql_query", "")
    if not sql_query.strip():
        raise ValueError("SQL query cannot be empty")

    retry_count = state.get("retry_count", 0)

    try:
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(f"SET LOCAL statement_timeout = {QUERY_TIMEOUT_MS}")
                cursor.execute(sql_query)
                columns = [description.name for description in cursor.description]
                rows = cursor.fetchall()

        result = [dict(zip(columns, row)) for row in rows]
        return {"sql_result": result, "sql_error": ""}
    except Exception as error:
        return {"sql_result": None, "sql_error": str(error), "retry_count": retry_count + 1}