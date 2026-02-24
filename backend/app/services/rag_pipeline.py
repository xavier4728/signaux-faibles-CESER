import asyncio
import json
import tempfile
import uuid
from pathlib import Path
from loguru import logger

from app.core.config import settings
from app.models.schemas import (
    Preconisation,
    LegalMatch,
    PreconisationResult,
    AnalysisResult,
    CategoryStat,
)
from app.prompts.extraction import (
    EXTRACTION_SYSTEM_PROMPT,
    EXTRACTION_USER_PROMPT,
    VALIDATION_SYSTEM_PROMPT,
    VALIDATION_USER_PROMPT,
    SYNTHESIS_SYSTEM_PROMPT,
    SYNTHESIS_USER_PROMPT,
)
from app.services.task_manager import task_manager
from app.services.dashboard_service import dashboard_service
from app.services.vector_store import VectorStoreManager


class RAGPipeline:
    """
    Core RAG pipeline implementing the 5-step analysis:
    1. Document parsing & segmentation (or retrieval from the correct regional shard)
    2. LLM-based structured extraction (parallel)
    3. FAISS vector search against legal base
    4. LLM-based validation & scoring (parallel)
    5. Synthesis
    """

    def __init__(self):
        self._embeddings = None
        self._llm = None
        self._semaphore = asyncio.Semaphore(settings.MAX_CONCURRENT_LLM_CALLS)
        self.vector_store = VectorStoreManager()

    def _get_embeddings(self):
        if self._embeddings is None:
            from langchain_huggingface import HuggingFaceEmbeddings
            self._embeddings = HuggingFaceEmbeddings(
                model_name=settings.EMBEDDING_MODEL,
                model_kwargs={"device": "cpu"},
            )
        return self._embeddings

    def _get_llm_client(self):
        if self._llm is None:
            from mistralai import Mistral
            self._llm = Mistral(api_key=settings.MISTRAL_API_KEY)
        return self._llm

    def _load_parent_store(self) -> dict:
        """
        Loads the LEGAL base parent store (parent_store.json).
        Used exclusively for the vector search comparison step (Step 3).
        Do NOT use this to load CESER document content.
        """
        store_path = settings.FAISS_INDEX_DIR / "parent_store.json"
        if store_path.exists():
            try:
                with open(store_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _load_parent_store_for_database(self, database: str) -> dict:
        """
        Loads the regional CESER parent store shard for a given database name.

        The ingestion scripts (ingest_cesers.py) write one shard per region:
            parent_store_ceser_bretagne.json
            parent_store_ceser_normandie.json
            ... etc.

        Falls back to the default parent_store.json only for the legal base
        (database == "legal_national"), which should never be used as a CESER
        input source but is handled gracefully just in case.

        Args:
            database: The database identifier, e.g. "ceser_bretagne".

        Returns:
            A dict mapping parent_id -> {text, source_doc, page, ...}
        """
        if database == "legal_national":
            # Shouldn't happen in batch analysis of CESER docs, but handle safely
            logger.warning(
                f"_load_parent_store_for_database called with 'legal_national'. "
                "This is the comparison base, not a CESER input source. "
                "Returning empty store."
            )
            return {}

        # Primary path: dedicated regional shard written by ingest_cesers.py
        shard_path = settings.FAISS_INDEX_DIR / f"parent_store_{database}.json"
        if shard_path.exists():
            try:
                with open(shard_path, "r", encoding="utf-8") as f:
                    store = json.load(f)
                logger.info(
                    f"Loaded regional shard '{shard_path.name}' "
                    f"({len(store)} parent chunks)"
                )
                return store
            except Exception as e:
                logger.error(f"Failed to read shard {shard_path}: {e}")
                return {}

        # Fallback: the monolithic parent_store.json may contain mixed content
        # if the user ran ingest_legal.py after an old single-store ingestion.
        fallback_path = settings.FAISS_INDEX_DIR / "parent_store.json"
        if fallback_path.exists():
            logger.warning(
                f"Regional shard '{shard_path.name}' not found. "
                f"Falling back to '{fallback_path.name}'. "
                "Consider re-running ingest_cesers.py to generate dedicated shards."
            )
            try:
                with open(fallback_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to read fallback store {fallback_path}: {e}")

        logger.error(
            f"No parent store found for database '{database}'. "
            f"Checked: {shard_path} and {fallback_path}"
        )
        return {}

    async def run_analysis(
        self,
        task_id: str,
        file_content: bytes | None = None,
        filename: str | None = None,
        document_id: str | None = None,
        region_filter: str | None = None,
    ):
        try:
            logger.info(f"[{task_id}] === DÉBUT ANALYSE === fichier={filename}, doc_id={document_id}")
            task_manager.update_task(task_id, status="processing", progress=0.05, message="Initialisation...")

            # --- ÉTAPE 1 : Récupération des segments ---
            segments = []
            source_doc = filename or "unknown"
            
            # Détermination de la région pour l'enregistrement des stats
            # Par défaut, on utilise le filtre ou "inconnu". Sera mis à jour si doc existant.
            current_region = region_filter if region_filter else "inconnu"

            if file_content and filename:
                # Cas 1 : Fichier uploadé (nouvelle analyse)
                logger.info(f"[{task_id}] ÉTAPE 1 : Parsing du fichier uploadé...")
                segments = await self._parse_document(task_id, file_content, filename, document_id)

            elif document_id:
                # Cas 2 : Analyse d'un document existant (Batch Dashboard)
                logger.info(f"[{task_id}] ÉTAPE 1 : Récupération depuis le shard régional...")

                doc_info = self.vector_store.get_document(document_id)
                if not doc_info:
                    raise ValueError(f"Document ID {document_id} introuvable dans le registre de métadonnées")

                source_doc = doc_info.filename
                database = doc_info.database  # e.g. "ceser_bretagne"
                
                # Mise à jour de la région à partir des métadonnées du document
                if doc_info.metadata and doc_info.metadata.region:
                    current_region = doc_info.metadata.region

                logger.info(
                    f"[{task_id}] Document '{source_doc}' appartient à la base '{database}' (Région: {current_region}). "
                    f"Chargement du shard parent_store_{database}.json..."
                )

                # ✅ FIX: load the correct regional shard, NOT parent_store.json
                parent_store = await asyncio.to_thread(
                    self._load_parent_store_for_database, database
                )

                if not parent_store:
                    raise ValueError(
                        f"Shard régional introuvable pour la base '{database}'. "
                        f"Vérifiez que le fichier parent_store_{database}.json existe "
                        f"dans {settings.FAISS_INDEX_DIR} et relancez ingest_cesers.py si nécessaire."
                    )

                # Retrieve all chunks belonging to this specific document
                relevant_chunks = [
                    chunk for chunk in parent_store.values()
                    if chunk.get("source_doc") == source_doc
                ]

                if not relevant_chunks:
                    # The shard exists but contains no entry for this filename.
                    logger.warning(
                        f"[{task_id}] Aucun chunk trouvé pour '{source_doc}' dans le shard "
                        f"'{database}'. Contenu du shard ({len(parent_store)} chunks) "
                        f"pour les premiers fichiers : "
                        f"{list({c.get('source_doc') for c in list(parent_store.values())[:10]})}"
                    )

                relevant_chunks.sort(key=lambda x: x.get("page", 0))
                segments = [
                    {
                        "text": chunk["text"],
                        "source_doc": source_doc,
                        "page": chunk.get("page", 0),
                    }
                    for chunk in relevant_chunks
                ]

                logger.info(
                    f"[{task_id}] {len(segments)} segments récupérés depuis "
                    f"parent_store_{database}.json pour '{source_doc}'"
                )

            if not segments:
                raise ValueError(
                    f"Aucun segment de texte trouvé pour l'analyse de '{source_doc}'. "
                    "Vérifiez que le document a bien été ingéré via ingest_cesers.py."
                )

            task_manager.update_task(task_id, progress=0.15, message=f"{len(segments)} segments prêts")

            # --- ÉTAPE 2 : Extraction LLM ---
            logger.info(f"[{task_id}] ÉTAPE 2 : Extraction des préconisations ({len(segments)} segments)...")
            preconisations = await self._extract_preconisations(segments, source_doc)

            if not preconisations:
                logger.warning(f"[{task_id}] Aucune préconisation trouvée.")
                empty_result = AnalysisResult(
                    task_id=task_id, status="completed", source_document=source_doc,
                    total_preconisations=0, matched_preconisations=0, taux_conversion=0.0, results=[]
                )
                # Correction ici : Ajout de l'argument current_region
                dashboard_service.save_analysis_result(empty_result, current_region)
                task_manager.update_task(task_id, status="completed", progress=1.0, result=empty_result, message="Aucune préconisation")
                return

            task_manager.update_task(task_id, progress=0.40, message=f"{len(preconisations)} précos extraites")

            # --- ÉTAPE 3 : Recherche Vectorielle (toujours sur la base légale) ---
            logger.info(f"[{task_id}] ÉTAPE 3 : Recherche vectorielle sur la base légale...")
            legal_contexts = await self._search_legal_base(preconisations)
            task_manager.update_task(task_id, progress=0.60, message="Contexte légal récupéré")

            # --- ÉTAPE 4 : Validation et Scoring ---
            logger.info(f"[{task_id}] ÉTAPE 4 : Validation croisée...")
            results = await self._validate_matches(preconisations, legal_contexts)

            matched = sum(1 for r in results if r.match and r.match.score_reutilisation > 0)
            total = len(results)
            taux = (matched / total * 100) if total > 0 else 0.0

            # --- ÉTAPE 5 : Synthèse & Sauvegarde ---
            logger.info(f"[{task_id}] ÉTAPE 5 : Synthèse...")
            synthese, categories = await self._generate_synthesis(results, source_doc, total, matched, taux)

            final_result = AnalysisResult(
                task_id=task_id,
                status="completed",
                source_document=source_doc,
                total_preconisations=total,
                matched_preconisations=matched,
                taux_conversion=round(taux, 1),
                synthese=synthese,
                categories=categories,
                results=results,
            )

            try:
                # Correction ici : Ajout de l'argument current_region
                dashboard_service.save_analysis_result(final_result, current_region)
            except Exception as e:
                logger.error(f"[{task_id}] Erreur sauvegarde dashboard: {e}")

            task_manager.update_task(
                task_id,
                status="completed",
                progress=1.0,
                message=f"Terminé: {matched}/{total} convertis ({taux:.1f}%)",
                result=final_result,
            )

        except Exception as e:
            logger.error(f"[{task_id}] ERREUR FATALE: {e}")
            import traceback
            logger.error(traceback.format_exc())
            task_manager.update_task(task_id, status="failed", message=str(e))

    async def _parse_document(
        self, task_id: str, file_content: bytes | None, filename: str | None, document_id: str | None
    ) -> list[dict]:
        logger.info(f"[{task_id}] Parsing: file_content={len(file_content) if file_content else 0} bytes, filename={filename}")

        if file_content and filename:
            loop = asyncio.get_event_loop()

            def _do_parse():
                import ocrmypdf
                import pdfplumber

                suffix = Path(filename).suffix.lower()
                with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                    tmp.write(file_content)
                    tmp_path = tmp.name

                try:
                    if suffix == ".pdf":
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

                    segments = []
                    for page_num, page_text in pages_text:
                        start = 0
                        while start < len(page_text):
                            end = start + settings.CHILD_CHUNK_SIZE
                            chunk = page_text[start:end]
                            if chunk.strip():
                                segments.append({
                                    "text": chunk.strip(),
                                    "source_doc": filename,
                                    "page": page_num,
                                })
                            start += settings.CHILD_CHUNK_SIZE - settings.CHILD_CHUNK_OVERLAP

                    return segments
                finally:
                    Path(tmp_path).unlink(missing_ok=True)

            return await loop.run_in_executor(None, _do_parse)

        return []

    @staticmethod
    def _sanitize_legal_match(data: dict) -> dict:
        if not isinstance(data, dict): return data
        if data.get("legal_page") is None: data["legal_page"] = 0
        if data.get("score_reutilisation") is None: data["score_reutilisation"] = 0
        if isinstance(data.get("score_reutilisation"), str):
            try: data["score_reutilisation"] = int(data["score_reutilisation"])
            except ValueError: data["score_reutilisation"] = 0
        data["score_reutilisation"] = max(0, min(2, data["score_reutilisation"]))
        if data.get("score_similarite") is None: data["score_similarite"] = 0.0
        if isinstance(data.get("score_similarite"), str):
            try: data["score_similarite"] = float(data["score_similarite"])
            except ValueError: data["score_similarite"] = 0.0
        data["score_similarite"] = max(0.0, min(100.0, float(data["score_similarite"])))
        for str_field in ("justification", "legal_source_doc", "extrait_legal_exact"):
            if data.get(str_field) is None: data[str_field] = ""
        return data

    async def _call_llm(self, system_prompt: str, user_prompt: str) -> str:
        async with self._semaphore:
            client = self._get_llm_client()
            response = await asyncio.to_thread(
                client.chat.complete,
                model=settings.MISTRAL_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
            )
            return response.choices[0].message.content or "[]"

    async def _extract_preconisations(self, segments: list[dict], source_doc: str) -> list[Preconisation]:
        async def extract_one(idx: int, segment: dict) -> list[Preconisation]:
            user_prompt = EXTRACTION_USER_PROMPT.format(
                source_doc=segment["source_doc"],
                page=segment["page"],
                text=segment["text"],
            )
            try:
                raw = await self._call_llm(EXTRACTION_SYSTEM_PROMPT, user_prompt)
                data = json.loads(raw)
                if isinstance(data, dict) and "preconisations" in data:
                    data = data["preconisations"]
                if not isinstance(data, list):
                    data = [data] if isinstance(data, dict) else []
                precos = [Preconisation(**item) for item in data if isinstance(item, dict) and "preconisation" in item]
                return precos
            except Exception as e:
                logger.warning(f"  [Extraction seg {idx+1}] ÉCHEC: {e}")
                return []

        tasks = [extract_one(i, seg) for i, seg in enumerate(segments)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_precos: list[Preconisation] = []
        counter = 1
        for result in results:
            if isinstance(result, list):
                for preco in result:
                    preco.id = counter
                    counter += 1
                    all_precos.append(preco)
        return all_precos

    async def _search_legal_base(self, preconisations: list[Preconisation]) -> dict[int, list[dict]]:
        """
        Searches the LEGAL base (legal_national.faiss + parent_store.json).
        This is intentionally kept separate from the CESER input loading.
        """
        loop = asyncio.get_event_loop()

        def _do_search():
            from langchain_community.vectorstores import FAISS
            embeddings = self._get_embeddings()
            index_path = settings.FAISS_INDEX_DIR / "legal_national.faiss"

            if not index_path.exists():
                logger.error(f"Index FAISS légal non trouvé: {index_path}")
                return {p.id: [] for p in preconisations}

            # Always use the legal base parent store for the comparison step
            legal_parent_store = self._load_parent_store()
            legal_index = FAISS.load_local(
                str(settings.FAISS_INDEX_DIR),
                embeddings,
                index_name="legal_national",
                allow_dangerous_deserialization=True,
            )

            contexts = {}
            for preco in preconisations:
                results = legal_index.similarity_search_with_score(preco.preconisation, k=3)
                parent_results = []
                for doc, score in results:
                    pid = doc.metadata.get("parent_id", "")
                    if legal_parent_store and pid:
                        parent = legal_parent_store.get(pid, {})
                        if parent:
                            parent_results.append({
                                "text": parent.get("text", ""),
                                "source_doc": parent.get("source_doc", ""),
                                "page": parent.get("page", 0),
                                "score": float(score),
                            })
                    else:
                        parent_results.append({
                            "text": doc.page_content,
                            "source_doc": doc.metadata.get("source_doc", "unknown"),
                            "page": doc.metadata.get("page", 0),
                            "score": float(score),
                        })
                contexts[preco.id] = parent_results
            return contexts

        return await loop.run_in_executor(None, _do_search)

    async def _validate_matches(
        self, preconisations: list[Preconisation], legal_contexts: dict[int, list[dict]]
    ) -> list[PreconisationResult]:
        async def validate_one(preco: Preconisation) -> PreconisationResult:
            contexts = legal_contexts.get(preco.id, [])
            if not contexts:
                return PreconisationResult(preconisation=preco)

            legal_texts = "\n\n".join(
                f"[Source: {ctx['source_doc']}, Page {ctx['page']}]\n{ctx['text']}"
                for ctx in contexts
            )

            user_prompt = VALIDATION_USER_PROMPT.format(
                preconisation=preco.preconisation,
                source_doc=preco.source_doc,
                page=preco.page,
                legal_contexts=legal_texts,
            )

            try:
                raw = await self._call_llm(VALIDATION_SYSTEM_PROMPT, user_prompt)
                data = json.loads(raw)
                data = self._sanitize_legal_match(data)
                match = LegalMatch(**data)
                return PreconisationResult(preconisation=preco, match=match)
            except Exception:
                return PreconisationResult(preconisation=preco)

        tasks = [validate_one(preco) for preco in preconisations]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return [r for r in results if isinstance(r, PreconisationResult)]

    async def _generate_synthesis(
        self, results, source_doc, total, matched, taux
    ) -> tuple[str, list[CategoryStat]]:
        matched_lines = []
        unmatched_lines = []

        for r in results:
            score = r.match.score_reutilisation if r.match else 0
            if score > 0 and r.match:
                matched_lines.append(f"- #{r.preconisation.id}: \"{r.preconisation.preconisation[:150]}\"")
            else:
                unmatched_lines.append(f"- #{r.preconisation.id}: \"{r.preconisation.preconisation[:150]}\"")

        user_prompt = SYNTHESIS_USER_PROMPT.format(
            source_doc=source_doc,
            total=total,
            matched=matched,
            unmatched=total - matched,
            taux=round(taux, 1),
            matched_details="\n".join(matched_lines) if matched_lines else "(aucune)",
            unmatched_details="\n".join(unmatched_lines) if unmatched_lines else "(aucune)",
        )

        try:
            raw = await self._call_llm(SYNTHESIS_SYSTEM_PROMPT, user_prompt)
            data = json.loads(raw)
            return data.get("synthese", ""), [CategoryStat(**c) for c in data.get("categories", [])]
        except Exception:
            return "Synthèse indisponible", []