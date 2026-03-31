import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()


@dataclass
class Settings:
    groq_api_key: str = os.getenv("GROQ_API_KEY", "")
    groq_model_primary: str = os.getenv("GROQ_MODEL_PRIMARY", "llama-3.3-70b-versatile")
    groq_model_secondary: str = os.getenv("GROQ_MODEL_SECONDARY", "llama3-8b-8192")

    embedding_model_name: str = os.getenv(
        "EMBEDDING_MODEL_NAME", "sentence-transformers/all-MiniLM-L6-v2"
    )
    hf_api_token: str | None = os.getenv("HUGGINGFACEHUB_API_TOKEN") or None

    langsmith_tracing_v2: str = os.getenv("LANGCHAIN_TRACING_V2", "false")
    langsmith_api_key: str = os.getenv("LANGCHAIN_API_KEY", "")
    langsmith_project: str = os.getenv("LANGCHAIN_PROJECT", "Nexora-Agent")

    app_host: str = os.getenv("APP_HOST", "0.0.0.0")
    app_port: int = int(os.getenv("APP_PORT", "8000"))
    frontend_origin: str = os.getenv("FRONTEND_ORIGIN", "http://localhost:3000")

    data_dir: Path = Path(os.getenv("DATA_DIR", "./data")).resolve()
    vector_store_dir: Path = Path(os.getenv("VECTOR_STORE_DIR", "./vector_store")).resolve()
    log_file_path: Path = Path(os.getenv("LOG_FILE_PATH", "./logs/requests.jsonl")).resolve()
    vector_db_provider: str = os.getenv("VECTOR_DB_PROVIDER", "qdrant").lower()

    # Qdrant settings (used when VECTOR_DB_PROVIDER=qdrant)
    qdrant_collection_name: str = os.getenv("QDRANT_COLLECTION_NAME", "nexora_docs")
    qdrant_path: str = os.getenv("QDRANT_PATH", "./vector_store/qdrant")
    qdrant_url: str | None = os.getenv("QDRANT_URL") or None
    qdrant_api_key: str | None = os.getenv("QDRANT_API_KEY") or None
    qdrant_port: int = int(os.getenv("QDRANT_PORT", "6333"))

    # Pinecone settings (used when VECTOR_DB_PROVIDER=pinecone)
    pinecone_api_key: str = os.getenv("PINECONE_API_KEY", "")
    pinecone_index_name: str = os.getenv("PINECONE_INDEX_NAME", "nexora")
    pinecone_cloud: str = os.getenv("PINECONE_CLOUD", "aws")
    pinecone_region: str = os.getenv("PINECONE_REGION", "us-east-1")
    pinecone_dimension: int = int(os.getenv("PINECONE_DIMENSION", "384"))
    pinecone_metric: str = os.getenv("PINECONE_METRIC", "cosine")
    pinecone_namespace: str = os.getenv("PINECONE_NAMESPACE", "nexora-prod")

    company_name: str = os.getenv("COMPANY_NAME", "Nexora Systems")
    company_tagline: str = os.getenv(
        "COMPANY_TAGLINE",
        "Nexora Systems is a global artificial intelligence infrastructure company focused on "
        "building monitoring, optimization, and governance platforms for large scale AI deployments.",
    )


settings = Settings()

