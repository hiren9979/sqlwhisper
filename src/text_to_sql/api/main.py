from fastapi import FastAPI
from text_to_sql.api.chat import router as chat_router

app = FastAPI(title="Text-to-SQL API")
app.include_router(chat_router)


@app.get("/health")
def health():
    return {"status": "healthy"}
