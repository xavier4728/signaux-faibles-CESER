import asyncio
import json
import tempfile
import uuid
from pathlib import Path
from loguru import logger

from app.core.config import settings
from app.models.schemas import DatabaseTarget, DocumentMetadata
from app.services.task_manager import task_manager
from app.services.vector_store import VectorStoreManager


class IngestionService:
    """Handles document parsing, chunking, embedding, and FAISS indexing."""

    def __init__(self):
        self.vector_store = VectorStoreManager()
        self._embeddings = None
        self._faiss_indexes: dict[str, object] = {}

    def _get_embeddings(self):
        if self._embeddings is None:
            from langchain_huggingface import HuggingFaceEmbeddings
            self._embeddings = HuggingFaceEmbeddings(
                model_name=settings.EMBEDDING_MODEL,
                model_kwargs={"device": "cpu"},
            )
        return self._embeddings

    async def ingest_document(
        self,
        task_id: str,
        filename: str,
        file_content: bytes,
        target_db: DatabaseTarget,
        metadata: DocumentMetadata,
    ):
        try:
            task_manager.update_task(task_id, status="processing", progress=0.1, message="Parsing du document...")

            chunks, new_parents = await self._parse_and_chunk(filename, file_content)
            task_manager.update_task(task_id, progress=0.4, message=f"{len(chunks)} child chunks, {len(new_parents)} parents")

            task_manager.update_task(task_id, progress=0.5, message="Génération des embeddings...")
            await self._embed_and_index(chunks, target_db, metadata)
            self._save_parents(new_parents)

            doc_id = str(uuid.uuid4())
            self.vector_store.register_document(
                doc_id=doc_id,
                filename=filename,
                database=target_db.value,
                metadata=metadata,
                chunk_count=len(chunks),
            )

            task_manager.update_task(
                task_id,
                status="completed",
                progress=1.0,
                message=f"Ingestion terminée: {len(chunks)} chunks indexés dans {target_db.value}",
            )
            logger.info(f"Task {task_id}: Successfully ingested {filename} ({len(chunks)} chunks)")

        except Exception as e:
            logger.error(f"Task {task_id}: Ingestion failed - {e}")
            task_manager.update_task(task_id, status="failed", message=f"Erreur: {str(e)}")

    async def ingest_batch(
        self,
        task_id: str,
        target_db: DatabaseTarget,
        source_dir: str = "",
    ):
        try:
            dir_path = Path(source_dir) if source_dir else settings.DOCUMENTS_DIR / target_db.value
            if not dir_path.exists():
                task_manager.update_task(task_id, status="failed", message=f"Dossier non trouvé: {dir_path}")
                return

            pdf_files = list(dir_path.glob("*.pdf")) + list(dir_path.glob("*.docx"))
            total = len(pdf_files)

            if total == 0:
                task_manager.update_task(task_id, status="completed", progress=1.0, message="Aucun document trouvé")
                return

            task_manager.update_task(task_id, status="processing", message=f"Traitement de {total} documents...")

            for i, file_path in enumerate(pdf_files):
                task_manager.update_task(
                    task_id,
                    progress=(i / total),
                    message=f"Traitement {i + 1}/{total}: {file_path.name}",
                )
                file_content = file_path.read_bytes()
                chunks, new_parents = await self._parse_and_chunk(file_path.name, file_content)
                metadata = DocumentMetadata(title=file_path.stem, region=target_db.value)
                await self._embed_and_index(chunks, target_db, metadata)
                self._save_parents(new_parents)

                doc_id = str(uuid.uuid4())
                self.vector_store.register_document(
                    doc_id=doc_id,
                    filename=file_path.name,
                    database=target_db.value,
                    metadata=metadata,
                    chunk_count=len(chunks),
                )

            task_manager.update_task(
                task_id,
                status="completed",
                progress=1.0,
                message=f"Batch terminé: {total} documents indexés",
            )

        except Exception as e:
            logger.error(f"Task {task_id}: Batch ingestion failed - {e}")
            task_manager.update_task(task_id, status="failed", message=f"Erreur: {str(e)}")

    async def _parse_and_chunk(self, filename: str, file_content: bytes) -> tuple[list[dict], dict[str, dict]]:
        """Parse document, create parent/child chunks. Returns (child_chunks, parent_store)."""
        loop = asyncio.get_event_loop()

        def _do_parse():
            import fitz  # PyMuPDF

            suffix = Path(filename).suffix.lower()
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                tmp.write(file_content)
                tmp_path = tmp.name

            try:
                if suffix == ".pdf":
                    pages_text: list[tuple[int, str]] = []
                    doc = fitz.open(tmp_path)
                    total_pages = doc.page_count
                    for i, page in enumerate(doc, start=1):
                        text = page.get_text("text") or ""
                        if text.strip():
                            pages_text.append((i, text.strip()))
                    doc.close()

                    text_ratio = len(pages_text) / max(1, total_pages)
                    if text_ratio < 0.3:
                        logger.info(f"PyMuPDF: only {len(pages_text)}/{total_pages} pages → OCR fallback for {filename}")
                        import ocrmypdf
                        import pdfplumber
                        ocr_path = tmp_path + "_ocr.pdf"
                        try:
                            ocrmypdf.ocr(
                                tmp_path, ocr_path,
                                language="fra",
                                skip_text=True,
                                optimize=0,
                                progress_bar=False,
                            )
                        except ocrmypdf.exceptions.PriorOcrFoundError:
                            ocr_path = tmp_path

                        pages_text = []
                        with pdfplumber.open(ocr_path) as pdf:
                            for i, page in enumerate(pdf.pages, start=1):
                                text = page.extract_text() or ""
                                if text.strip():
                                    pages_text.append((i, text.strip()))

                        if ocr_path != tmp_path:
                            Path(ocr_path).unlink(missing_ok=True)
                else:
                    text = file_content.decode("utf-8", errors="ignore")
                    pages_text = [(1, text)] if text.strip() else []

                child_chunks = []
                parent_store: dict[str, dict] = {}

                for page_num, page_text in pages_text:
                    p_start = 0
                    while p_start < len(page_text):
                        p_end = p_start + settings.PARENT_CHUNK_SIZE
                        parent_text = page_text[p_start:p_end].strip()
                        if not parent_text:
                            p_start += settings.PARENT_CHUNK_SIZE - settings.PARENT_CHUNK_OVERLAP
                            continue

                        parent_id = str(uuid.uuid4())
                        parent_store[parent_id] = {
                            "text": parent_text,
                            "source_doc": filename,
                            "page": page_num,
                        }

                        c_start = 0
                        while c_start < len(parent_text):
                            c_end = c_start + settings.CHILD_CHUNK_SIZE
                            child_text = parent_text[c_start:c_end].strip()
                            if child_text:
                                child_chunks.append({
                                    "text": child_text,
                                    "source_doc": filename,
                                    "page": page_num,
                                    "parent_id": parent_id,
                                })
                            c_start += settings.CHILD_CHUNK_SIZE - settings.CHILD_CHUNK_OVERLAP

                        p_start += settings.PARENT_CHUNK_SIZE - settings.PARENT_CHUNK_OVERLAP

                return child_chunks, parent_store
            finally:
                Path(tmp_path).unlink(missing_ok=True)

        return await loop.run_in_executor(None, _do_parse)

    def _save_parents(self, new_parents: dict[str, dict]):
        """Merge new parent chunks into the persistent parent_store.json."""
        parent_store_path = settings.FAISS_INDEX_DIR / "parent_store.json"
        existing: dict[str, dict] = {}
        if parent_store_path.exists():
            with open(parent_store_path, "r", encoding="utf-8") as f:
                existing = json.load(f)
        existing.update(new_parents)
        with open(parent_store_path, "w", encoding="utf-8") as f:
            json.dump(existing, f, ensure_ascii=False, indent=2)
        logger.info(f"Parent store updated: +{len(new_parents)} parents (total {len(existing)})")

    async def _embed_and_index(
        self, chunks: list[dict], target_db: DatabaseTarget, metadata: DocumentMetadata
    ):
        """Generate embeddings and add child chunks to FAISS index."""
        loop = asyncio.get_event_loop()

        def _do_embed():
            from langchain_community.vectorstores import FAISS
            from langchain_core.documents import Document

            embeddings = self._get_embeddings()
            index_path = self.vector_store.get_index_path(target_db.value)

            documents = [
                Document(
                    page_content=chunk["text"],
                    metadata={
                        "parent_id": chunk.get("parent_id", ""),
                        "source_doc": chunk["source_doc"],
                        "page": chunk["page"],
                        "database": target_db.value,
                        "year": metadata.year,
                        "theme": metadata.theme,
                        "title": metadata.title,
                    },
                )
                for chunk in chunks
            ]

            if index_path.exists():
                existing = FAISS.load_local(
                    str(index_path.parent),
                    embeddings,
                    index_name=target_db.value,
                    allow_dangerous_deserialization=True,
                )
                existing.add_documents(documents)
                existing.save_local(str(index_path.parent), index_name=target_db.value)
            else:
                index = FAISS.from_documents(documents, embeddings)
                index.save_local(str(index_path.parent), index_name=target_db.value)

        await loop.run_in_executor(None, _do_embed)
