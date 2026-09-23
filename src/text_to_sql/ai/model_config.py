import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_mistralai import ChatMistralAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_google_genai import GoogleGenerativeAIEmbeddings

load_dotenv()

def get_embedding_model():
    """Get Google Generative AI embedding model for generating text embeddings."""
    return GoogleGenerativeAIEmbeddings(
        model="gemini-embedding-2",
        google_api_key=os.getenv("GOOGLE_API_KEY"),
        task_type="RETRIEVAL_DOCUMENT",
        output_dimensionality=1024
    )


def get_llm_model():
    """Get LLM model based on the LLM_PROVIDER environment variable."""
    model_provider = os.getenv("LLM_PROVIDER", "gemini").lower()

    if model_provider == "groq":
        return ChatGroq(
            model=os.getenv("GROQ_MODEL", "llama-3.1-70b-versatile"),
            groq_api_key=os.getenv("GROQ_API_KEY")
        )

    elif model_provider == "mistral":
        return ChatMistralAI(
            model=os.getenv("MISTRAL_MODEL", "mistral-small-2603"),
            mistral_api_key=os.getenv("MISTRAL_API_KEY")
        )

    elif model_provider == "gemini":
        return ChatGoogleGenerativeAI(
        model=os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite"),
        google_api_key=os.getenv("GOOGLE_API_KEY")
        )

    else:
        raise ValueError(
            f"Unsupported LLM provider: {model_provider}. "
            "Supported: groq, mistral, gemini"
        )