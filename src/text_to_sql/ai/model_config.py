import os
from dotenv import load_dotenv
from langchain_mistralai import MistralAIEmbeddings
from langchain_groq import ChatGroq

load_dotenv()

def get_embedding_model():
    """Get MistralAI embedding model for generating text embeddings."""
    return MistralAIEmbeddings(
        model="mistral-embed",
        mistral_api_key=os.getenv("MISTRAL_API_KEY")
    )


def get_llm_model():
    """Get Groq LLM model for text generation."""
    return ChatGroq(
        model="openai/gpt-oss-safeguard-20b",
        groq_api_key=os.getenv("GROQ_API_KEY")
    )