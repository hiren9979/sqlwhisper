from pgvector.psycopg import register_vector

from text_to_sql.ai.model_config import get_embedding_model
from text_to_sql.db.connection import get_connection


def retrieve_documents(question: str, top_k: int = 5):
    """Retrieve the most relevant schema knowledge for a user question."""
    if not question or not question.strip():
        raise ValueError("Question cannot be empty")

    if top_k <= 0:
        raise ValueError("top_k must be greater than 0")

    embedding_model = get_embedding_model()
    question_embedding = embedding_model.embed_query(question)

    with get_connection() as connection:
        register_vector(connection)

        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    document_key,
                    document_type,
                    content,
                    metadata,
                    embedding <=> %s::vector AS distance
                FROM schema_documents
                ORDER BY embedding <=> %s::vector
                LIMIT %s;
                """,
                (question_embedding, question_embedding, top_k),
            )

            rows = cursor.fetchall()

    return [
        {
            "document_key": row[0],
            "document_type": row[1],
            "content": row[2],
            "metadata": row[3],
            "distance": row[4],
        }
        for row in rows
    ]