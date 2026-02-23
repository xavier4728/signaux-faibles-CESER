from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    PROJECT_NAME: str = "Signaux Faibles CESER"
    API_VERSION: str = "v1"

    MISTRAL_API_KEY: str = ""
    MISTRAL_MODEL: str = "mistral-large-latest"

    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"

    FAISS_INDEX_DIR: Path = Path(__file__).parent.parent.parent / "data" / "faiss_indexes"
    DOCUMENTS_DIR: Path = Path(__file__).parent.parent.parent.parent / "data" / "documents"

    PARENT_CHUNK_SIZE: int = 2048
    PARENT_CHUNK_OVERLAP: int = 256
    CHILD_CHUNK_SIZE: int = 512
    CHILD_CHUNK_OVERLAP: int = 64
    TOP_K_RESULTS: int = 5

    MAX_CONCURRENT_LLM_CALLS: int = 5

    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    CESER_REGIONS: list[str] = [
        "bretagne",
        "centre_val_de_loire",
        "grand_est",
        "hauts_de_france",
        "la_reunion",
        "normandie",
        "nouvelle_aquitaine",
        "pays_de_la_loire",
    ]

    class Config:
        env_file = str(Path(__file__).parent.parent.parent.parent / ".env")
        env_file_encoding = "utf-8"


settings = Settings()
