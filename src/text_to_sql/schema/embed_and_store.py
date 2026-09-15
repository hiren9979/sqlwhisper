import logging

from pgvector.psycopg import register_vector
from psycopg.types.json import Jsonb

from text_to_sql.ai.model_config import get_embedding_model
from text_to_sql.db.connection import get_connection
from text_to_sql.schema.embedding_documents import build_all_documents

logger = logging.getLogger(__name__)

def generate_embeddings(documents):
    """Generate embeddings for all documents."""
    if not documents:
        raise ValueError("No documents provided for embedding")

    embedding_model = get_embedding_model()
    texts = [document["content"] for document in documents]

    return embedding_model.embed_documents(texts)


def store_documents(documents, embeddings):
    """Store documents and their embeddings in PostgreSQL."""
    if len(documents) != len(embeddings):
        raise ValueError(
            "Number of documents does not match number of embeddings"
        )

    with get_connection() as connection:
        register_vector(connection)

        with connection.cursor() as cursor:
            for document, embedding in zip(documents, embeddings):
                cursor.execute(
                    """
                    INSERT INTO schema_documents (
                        document_key,
                        document_type,
                        content,
                        metadata,
                        embedding
                    )
                    VALUES (%s, %s, %s, %s, %s::vector)
                    ON CONFLICT (document_key)
                    DO UPDATE SET
                        document_type = EXCLUDED.document_type,
                        content = EXCLUDED.content,
                        metadata = EXCLUDED.metadata,
                        embedding = EXCLUDED.embedding;
                    """,
                    (
                        document["document_key"],
                        document["document_type"],
                        document["content"],
                        Jsonb(document["metadata"]),
                        embedding,
                    ),
                )

    logger.info(
        "Stored %s documents in schema_documents",
        len(documents),
    )


def ingest_documents():
    """Build, embed, and store all schema knowledge documents."""
    documents = build_all_documents()

    logger.info("Prepared %s documents", len(documents))

    embeddings = generate_embeddings(documents)

    logger.info("Generated %s embeddings", len(embeddings))

    store_documents(documents, embeddings)

    return len(documents)