from pathlib import Path
from loguru import logger
import json

from app.core.config import settings
from app.models.schemas import DocumentInfo, DocumentMetadata, DatabaseTarget


class VectorStoreManager:
    """Manages FAISS indexes with strict namespace separation."""

    def __init__(self):
        self.index_dir = settings.FAISS_INDEX_DIR
        self.index_dir.mkdir(parents=True, exist_ok=True)
        self._metadata_store: dict[str, dict] = {}
        self._load_metadata()

    def _metadata_path(self) -> Path:
        return self.index_dir / "metadata.json"

    def _load_metadata(self):
        meta_path = self._metadata_path()
        if meta_path.exists():
            with open(meta_path, "r", encoding="utf-8") as f:
                self._metadata_store = json.load(f)
        else:
            self._metadata_store = {}

    def _save_metadata(self):
        meta_path = self._metadata_path()
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(self._metadata_store, f, ensure_ascii=False, indent=2)

    def get_index_path(self, database: str) -> Path:
        return self.index_dir / f"{database}.faiss"

    def register_document(
        self, doc_id: str, filename: str, database: str, metadata: DocumentMetadata, chunk_count: int = 0
    ):
        self._metadata_store[doc_id] = {
            "id": doc_id,
            "filename": filename,
            "database": database,
            "metadata": metadata.model_dump(),
            "chunk_count": chunk_count,
        }
        self._save_metadata()
        logger.info(f"Registered document {doc_id}: {filename} in {database}")

    def list_documents(
        self, database: DatabaseTarget | None = None, region: str | None = None
    ) -> list[DocumentInfo]:
        results = []
        for doc_data in self._metadata_store.values():
            if database and doc_data["database"] != database.value:
                continue
            if region and doc_data.get("metadata", {}).get("region") != region:
                continue
            results.append(
                DocumentInfo(
                    id=doc_data["id"],
                    filename=doc_data["filename"],
                    database=doc_data["database"],
                    metadata=DocumentMetadata(**doc_data["metadata"]),
                    chunk_count=doc_data.get("chunk_count", 0),
                )
            )
        return results

    def get_document(self, document_id: str) -> DocumentInfo | None:
        doc_data = self._metadata_store.get(document_id)
        if not doc_data:
            return None
        return DocumentInfo(
            id=doc_data["id"],
            filename=doc_data["filename"],
            database=doc_data["database"],
            metadata=DocumentMetadata(**doc_data["metadata"]),
            chunk_count=doc_data.get("chunk_count", 0),
        )
