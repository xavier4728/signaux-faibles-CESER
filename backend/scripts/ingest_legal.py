"""
Script d'ingestion batch de la base légale nationale dans FAISS.
Utilise un ParentDocument Retriever: child chunks dans FAISS, parent chunks dans un store JSON.
Usage: python -m scripts.ingest_legal
"""

import sys
import uuid
import json
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import settings


def main():
    docs_dir = settings.DOCUMENTS_DIR / "legal_national"
    index_dir = settings.FAISS_INDEX_DIR
    index_dir.mkdir(parents=True, exist_ok=True)

    pdf_files = list(docs_dir.glob("*.pdf"))
    print(f"\n{'='*60}")
    print(f"  INGESTION BASE LÉGALE NATIONALE (ParentDocument Retriever)")
    print(f"  Dossier source  : {docs_dir}")
    print(f"  Index FAISS     : {index_dir}")
    print(f"  Documents       : {len(pdf_files)} PDF trouvés")
    print(f"  Parent chunks   : {settings.PARENT_CHUNK_SIZE} chars (overlap {settings.PARENT_CHUNK_OVERLAP})")
    print(f"  Child chunks    : {settings.CHILD_CHUNK_SIZE} chars (overlap {settings.CHILD_CHUNK_OVERLAP})")
    print(f"{'='*60}\n")

    if not pdf_files:
        print("Aucun PDF trouvé. Abandon.")
        return

    print("[1/5] Chargement du modèle d'embeddings...")
    from langchain_huggingface import HuggingFaceEmbeddings
    embeddings = HuggingFaceEmbeddings(
        model_name=settings.EMBEDDING_MODEL,
        model_kwargs={"device": "cpu"},
    )
    print(f"       Modèle chargé : {settings.EMBEDDING_MODEL}")

    print(f"\n[2/5] Parsing des {len(pdf_files)} PDF (ocrmypdf + pdfplumber)...")
    import ocrmypdf
    import pdfplumber
    from langchain_core.documents import Document

    all_child_documents = []
    parent_store: dict[str, dict] = {}
    metadata_store = {}

    for i, pdf_path in enumerate(pdf_files):
        print(f"  [{i+1}/{len(pdf_files)}] {pdf_path.name}...", end=" ", flush=True)
        try:
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                ocr_path = tmp.name
            try:
                ocrmypdf.ocr(
                    str(pdf_path), ocr_path,
                    language="fra",
                    skip_text=True,
                    optimize=0,
                    progress_bar=False,
                )
                read_path = ocr_path
            except ocrmypdf.exceptions.PriorOcrFoundError:
                read_path = str(pdf_path)

            pages_text: list[tuple[int, str]] = []
            with pdfplumber.open(read_path) as pdf:
                for page_num, page in enumerate(pdf.pages, start=1):
                    page_text = page.extract_text() or ""
                    if page_text.strip():
                        pages_text.append((page_num, page_text.strip()))

            Path(ocr_path).unlink(missing_ok=True)

            parent_count = 0
            child_count = 0
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
                        "source_doc": pdf_path.name,
                        "page": page_num,
                    }
                    parent_count += 1

                    c_start = 0
                    while c_start < len(parent_text):
                        c_end = c_start + settings.CHILD_CHUNK_SIZE
                        child_text = parent_text[c_start:c_end].strip()
                        if child_text:
                            all_child_documents.append(Document(
                                page_content=child_text,
                                metadata={
                                    "parent_id": parent_id,
                                    "source_doc": pdf_path.name,
                                    "page": page_num,
                                    "database": "legal_national",
                                    "title": pdf_path.stem,
                                },
                            ))
                            child_count += 1
                        c_start += settings.CHILD_CHUNK_SIZE - settings.CHILD_CHUNK_OVERLAP

                    p_start += settings.PARENT_CHUNK_SIZE - settings.PARENT_CHUNK_OVERLAP

            doc_id = str(uuid.uuid4())
            metadata_store[doc_id] = {
                "id": doc_id,
                "filename": pdf_path.name,
                "database": "legal_national",
                "metadata": {
                    "title": pdf_path.stem,
                    "year": None,
                    "doc_type": "legal",
                    "theme": "agriculture",
                    "region": "",
                },
                "chunk_count": child_count,
                "parent_count": parent_count,
            }

            print(f"{parent_count} parents -> {child_count} children")

        except Exception as e:
            print(f"ERREUR: {e}")

    print(f"\n       Total : {len(parent_store)} parents, {len(all_child_documents)} children de {len(pdf_files)} documents")

    if not all_child_documents:
        print("Aucun chunk extrait. Abandon.")
        return

    print(f"\n[3/5] Génération des embeddings et création de l'index FAISS (child chunks)...")
    from langchain_community.vectorstores import FAISS

    faiss_index = FAISS.from_documents(all_child_documents, embeddings)
    faiss_index.save_local(str(index_dir), index_name="legal_national")
    print(f"       Index FAISS sauvegardé : {index_dir / 'legal_national.faiss'}")

    print(f"\n[4/5] Sauvegarde du parent store...")
    parent_store_path = index_dir / "parent_store.json"
    with open(parent_store_path, "w", encoding="utf-8") as f:
        json.dump(parent_store, f, ensure_ascii=False, indent=2)
    print(f"       Parent store sauvegardé : {parent_store_path} ({len(parent_store)} parents)")

    print(f"\n[5/5] Sauvegarde des métadonnées...")
    meta_path = index_dir / "metadata.json"
    existing_meta = {}
    if meta_path.exists():
        with open(meta_path, "r", encoding="utf-8") as f:
            existing_meta = json.load(f)
    existing_meta.update(metadata_store)
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(existing_meta, f, ensure_ascii=False, indent=2)
    print(f"       Métadonnées sauvegardées : {meta_path}")

    print(f"\n{'='*60}")
    print(f"  INGESTION TERMINÉE (ParentDocument Retriever)")
    print(f"  {len(parent_store)} parent chunks stockés")
    print(f"  {len(all_child_documents)} child chunks indexés dans FAISS")
    print(f"  {len(metadata_store)} documents enregistrés")
    print(f"{'='*60}")

    print(f"\n[TEST] Recherche ParentDocument...")
    results = faiss_index.similarity_search("politique agricole commune", k=3)
    seen_parents = set()
    for j, doc in enumerate(results):
        pid = doc.metadata.get("parent_id", "")
        if pid in seen_parents:
            continue
        seen_parents.add(pid)
        parent = parent_store.get(pid, {})
        print(f"  #{j+1} Child: [{doc.metadata.get('source_doc', '?')} p.{doc.metadata.get('page', '?')}]")
        print(f"        Child  ({len(doc.page_content):>4} chars): {doc.page_content[:80]}...")
        print(f"        Parent ({len(parent.get('text', '')):>4} chars): {parent.get('text', '')[:80]}...")
    print()


if __name__ == "__main__":
    main()
