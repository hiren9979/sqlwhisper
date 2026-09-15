import logging

from fastapi import FastAPI

from text_to_sql.logging_config import setup_logging

setup_logging()

logger = logging.getLogger(__name__)

app = FastAPI(title="Text-to-SQL API")

@app.get("/health")
def health_check():
    logger.info("Health check requested")
    return {"status": "ok"}