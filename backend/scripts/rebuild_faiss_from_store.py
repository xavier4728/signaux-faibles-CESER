"""
Script de reconstruction de l'index FAISS légal depuis le parent_store.json existant.
Ne nécessite PAS Tesseract — aucun PDF n'est re-parsé.

Usage: python -m scripts.rebuild_faiss_from_store
"""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import settings


def main():
    index_dir = settings.FAISS_INDEX_DIR
    parent_store_path = index_dir / "parent_store.json"

    print(f"\n{'='*60}")
    print(f"  RECONSTRUCTION INDEX FAISS LÉGAL")
    print(f"  Source : {parent_store_path}")
    print(f"  Sortie : {index_dir / 'legal_national.faiss'}")
    print(f"{'='*60}\n")

    # 1. Vérifier que le parent_store existe
    if not parent_store_path.exists():
        print(f"ERREUR : {parent_store_path} introuvable.")
        print("Vous devez d'abord avoir un parent_store.json valide.")
        sys.exit(1)

    print("[1/4] Chargement du parent_store.json...")
    with open(parent_store_path, "r", encoding="utf-8") as f:
        parent_store: dict = json.load(f)

    # Filtrer uniquement les chunks légaux (database == "legal_national" ou pas de database = anciens chunks)
    legal_chunks = {
        pid: chunk for pid, chunk in parent_store.items()
        if chunk.get("database", "legal_national") == "legal_national"
           or "database" not in chunk  # rétrocompatibilité avec les anciens stores sans champ database
    }

    if not legal_chunks:
        print("ERREUR : Aucun chunk légal trouvé dans parent_store.json")
        print(f"         Total chunks dans le store : {len(parent_store)}")
        print(f"         Databases présentes : {set(c.get('database', 'N/A') for c in parent_store.values())}")
        sys.exit(1)

    print(f"         {len(legal_chunks)} chunks légaux trouvés (sur {len(parent_store)} total)")

    # 2. Charger le modèle d'embeddings
    print(f"\n[2/4] Chargement du modèle d'embeddings ({settings.EMBEDDING_MODEL})...")
    from langchain_huggingface import HuggingFaceEmbeddings
    embeddings = HuggingFaceEmbeddings(
        model_name=settings.EMBEDDING_MODEL,
        model_kwargs={"device": "cpu"},
    )
    print("       Modèle chargé.")

    # 3. Construire les Documents LangChain depuis les child chunks
    # On re-découpe les parent chunks en child chunks pour l'indexation FAISS
    print(f"\n[3/4] Génération des child chunks et embeddings...")
    from langchain_core.documents import Document
    from langchain_community.vectorstores import FAISS

    all_child_docs = []
    for parent_id, chunk in legal_chunks.items():
        parent_text = chunk.get("text", "")
        source_doc = chunk.get("source_doc", "unknown")
        page = chunk.get("page", 0)

        if not parent_text.strip():
            continue

        # Re-découpe en child chunks (même logique que l'ingestion originale)
        c_start = 0
        while c_start < len(parent_text):
            c_end = c_start + settings.CHILD_CHUNK_SIZE
            child_text = parent_text[c_start:c_end].strip()
            if child_text:
                all_child_docs.append(Document(
                    page_content=child_text,
                    metadata={
                        "parent_id": parent_id,
                        "source_doc": source_doc,
                        "page": page,
                        "database": "legal_national",
                    },
                ))
            c_start += settings.CHILD_CHUNK_SIZE - settings.CHILD_CHUNK_OVERLAP

    print(f"       {len(all_child_docs)} child chunks générés depuis {len(legal_chunks)} parents")

    if not all_child_docs:
        print("ERREUR : Aucun child chunk généré. Vérifiez le contenu de parent_store.json")
        sys.exit(1)

    print(f"       Création de l'index FAISS (cela peut prendre quelques minutes)...")
    faiss_index = FAISS.from_documents(all_child_docs, embeddings)
    faiss_index.save_local(str(index_dir), index_name="legal_national")

    # 4. Vérification rapide
    print(f"\n[4/4] Vérification de l'index...")
    test_results = faiss_index.similarity_search("politique agricole commune", k=3)
    print(f"       Test recherche 'politique agricole commune' → {len(test_results)} résultats")
    for i, doc in enumerate(test_results):
        print(f"       #{i+1} [{doc.metadata.get('source_doc', '?')} p.{doc.metadata.get('page', '?')}] "
              f"{doc.page_content[:80]}...")

    print(f"\n{'='*60}")
    print(f"  INDEX FAISS RECONSTRUIT AVEC SUCCÈS")
    print(f"  Fichier : {index_dir / 'legal_national.faiss'}")
    print(f"  Chunks  : {len(all_child_docs)} child chunks indexés")
    print(f"  Parents : {len(legal_chunks)} parent chunks dans parent_store.json")
    print(f"{'='*60}\n")
    print("Vous pouvez maintenant relancer le batch analysis.")


if __name__ == "__main__":
    main()