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


class RAGPipeline:
    """
    Core RAG pipeline implementing the 4-step analysis:
    1. Document parsing & segmentation
    2. LLM-based structured extraction (parallel)
    3. FAISS vector search against legal base
    4. LLM-based validation & scoring (parallel)
    """

    def __init__(self):
        self._embeddings = None
        self._llm = None
        self._semaphore = asyncio.Semaphore(settings.MAX_CONCURRENT_LLM_CALLS)

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
            task_manager.update_task(task_id, status="processing", progress=0.05, message="Préparation de l'analyse...")

            # Step 1: Parse document
            logger.info(f"[{task_id}] ÉTAPE 1/4 : Parsing du document...")
            segments = await self._parse_document(task_id, file_content, filename, document_id)

            if not segments:
                logger.error(f"[{task_id}] ÉCHEC : Aucun segment extrait du document")
                task_manager.update_task(task_id, status="failed", message="Aucun segment extrait du document")
                return

            source_doc = filename or document_id or "unknown"
            logger.info(f"[{task_id}] ÉTAPE 1/4 OK : {len(segments)} segments extraits")
            for i, seg in enumerate(segments[:3]):
                logger.debug(f"[{task_id}]   Segment {i+1} (p.{seg['page']}): {seg['text'][:100]}...")
            task_manager.update_task(task_id, progress=0.15, message=f"{len(segments)} segments extraits")

            # Step 2: Extract preconisations (parallel LLM calls)
            logger.info(f"[{task_id}] ÉTAPE 2/4 : Extraction LLM des préconisations ({len(segments)} segments)...")
            task_manager.update_task(task_id, progress=0.2, message="Extraction des préconisations (LLM)...")
            preconisations = await self._extract_preconisations(segments, source_doc)
            logger.info(f"[{task_id}] ÉTAPE 2/4 OK : {len(preconisations)} préconisations identifiées")
            task_manager.update_task(
                task_id, progress=0.45, message=f"{len(preconisations)} préconisations identifiées"
            )

            if not preconisations:
                logger.warning(f"[{task_id}] Aucune préconisation extraite — fin de l'analyse")
                result = AnalysisResult(
                    task_id=task_id,
                    status="completed",
                    source_document=source_doc,
                    total_preconisations=0,
                    matched_preconisations=0,
                    taux_conversion=0.0,
                    results=[],
                )
                task_manager.update_task(task_id, status="completed", progress=1.0, message="Analyse terminée (aucune préconisation)", result=result)
                return

            # Step 3: Vector search against legal base
            logger.info(f"[{task_id}] ÉTAPE 3/4 : Recherche vectorielle FAISS...")
            task_manager.update_task(task_id, progress=0.5, message="Recherche vectorielle dans la base légale...")
            legal_contexts = await self._search_legal_base(preconisations)
            non_empty = sum(1 for v in legal_contexts.values() if v)
            logger.info(f"[{task_id}] ÉTAPE 3/4 OK : {non_empty}/{len(preconisations)} préconisations ont des contextes légaux")
            task_manager.update_task(task_id, progress=0.65, message="Contextes légaux récupérés")

            # Step 4: Validation & scoring (parallel LLM calls)
            logger.info(f"[{task_id}] ÉTAPE 4/5 : Validation et scoring LLM...")
            task_manager.update_task(task_id, progress=0.7, message="Validation et scoring (LLM)...")
            results = await self._validate_matches(preconisations, legal_contexts)

            matched = sum(1 for r in results if r.match and r.match.score_reutilisation > 0)
            total = len(results)
            taux = (matched / total * 100) if total > 0 else 0.0

# Step 5: Generate synthesis
            logger.info(f"[{task_id}] ÉTAPE 5/5 : Génération de la synthèse analytique...")
            task_manager.update_task(task_id, progress=0.9, message="Génération de la synthèse analytique (LLM)...")
            synthese, categories = await self._generate_synthesis(results, source_doc, total, matched, taux)
            logger.info(f"[{task_id}] ÉTAPE 5/5 OK : Synthèse générée ({len(synthese)} chars), {len(categories)} catégories")

            analysis_result = AnalysisResult(
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

            # --- DÉBUT MODIFICATION SENIOR ---
            # On persiste le résultat pour le dashboard de manière asynchrone/sécurisée
            try:
                logger.info(f"[{task_id}] Sauvegarde des statistiques Dashboard...")
                dashboard_service.save_analysis_result(analysis_result)
            except Exception as e:
                # On log l'erreur mais on ne fail pas la tâche principale pour ça
                logger.error(f"[{task_id}] ERREUR CRITIQUE DASHBOARD: Impossible de sauver les stats: {e}")
            # --- FIN MODIFICATION SENIOR ---

            task_manager.update_task(
                task_id,
                status="completed",
                progress=1.0,
                message=f"Analyse terminée: {matched}/{total} préconisations retrouvées ({taux:.1f}%)",
                result=analysis_result,
            )
            logger.info(f"[{task_id}] === ANALYSE TERMINÉE === {matched}/{total} matches ({taux:.1f}%)")

        except Exception as e:
            logger.error(f"[{task_id}] === ANALYSE ÉCHOUÉE === {type(e).__name__}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            task_manager.update_task(task_id, status="failed", message=f"Erreur: {str(e)}")

    async def _parse_document(
        self, task_id: str, file_content: bytes | None, filename: str | None, document_id: str | None
    ) -> list[dict]:
        logger.info(f"[{task_id}] Parsing: file_content={len(file_content) if file_content else 0} bytes, filename={filename}, doc_id={document_id}")

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
                        logger.info(f"[{task_id}] OCR via ocrmypdf (lang=fra, skip-text)...")
                        try:
                            ocrmypdf.ocr(
                                tmp_path, ocr_path,
                                language="fra",
                                skip_text=True,
                                optimize=0,
                                progress_bar=False,
                            )
                        except ocrmypdf.exceptions.PriorOcrFoundError:
                            logger.info(f"[{task_id}] PDF déjà OCRisé, utilisation directe")
                            ocr_path = tmp_path

                        logger.info(f"[{task_id}] Extraction texte via pdfplumber...")
                        pages_text: list[tuple[int, str]] = []
                        with pdfplumber.open(ocr_path) as pdf:
                            for i, page in enumerate(pdf.pages, start=1):
                                text = page.extract_text() or ""
                                if text.strip():
                                    pages_text.append((i, text.strip()))
                        logger.info(f"[{task_id}] pdfplumber: {len(pages_text)} pages avec du texte sur {len(pdf.pages) if 'pdf' in dir() else '?'} pages totales")

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

                    logger.info(f"[{task_id}] Chunking: {len(pages_text)} pages -> {len(segments)} segments (chunk_size={settings.CHILD_CHUNK_SIZE}, overlap={settings.CHILD_CHUNK_OVERLAP})")
                    return segments
                finally:
                    Path(tmp_path).unlink(missing_ok=True)

            return await loop.run_in_executor(None, _do_parse)

        logger.warning(f"[{task_id}] Pas de file_content ni de document_id valide — retour vide")
        return []

    @staticmethod
    def _sanitize_legal_match(data: dict) -> dict:
        if not isinstance(data, dict):
            return data
        if data.get("legal_page") is None:
            data["legal_page"] = 0
        if data.get("score_reutilisation") is None:
            data["score_reutilisation"] = 0
        if isinstance(data.get("score_reutilisation"), str):
            try:
                data["score_reutilisation"] = int(data["score_reutilisation"])
            except ValueError:
                data["score_reutilisation"] = 0
        data["score_reutilisation"] = max(0, min(2, data["score_reutilisation"]))
        if data.get("score_similarite") is None:
            data["score_similarite"] = 0.0
        if isinstance(data.get("score_similarite"), str):
            try:
                data["score_similarite"] = float(data["score_similarite"])
            except ValueError:
                data["score_similarite"] = 0.0
        data["score_similarite"] = max(0.0, min(100.0, float(data["score_similarite"])))
        for str_field in ("justification", "legal_source_doc", "extrait_legal_exact"):
            if data.get(str_field) is None:
                data[str_field] = ""
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
            content = response.choices[0].message.content or "[]"
            return content

    async def _extract_preconisations(self, segments: list[dict], source_doc: str) -> list[Preconisation]:
        async def extract_one(idx: int, segment: dict) -> list[Preconisation]:
            user_prompt = EXTRACTION_USER_PROMPT.format(
                source_doc=segment["source_doc"],
                page=segment["page"],
                text=segment["text"],
            )
            try:
                raw = await self._call_llm(EXTRACTION_SYSTEM_PROMPT, user_prompt)
                logger.debug(f"  [Extraction seg {idx+1}] Réponse LLM brute ({len(raw)} chars): {raw[:200]}...")
                data = json.loads(raw)
                if isinstance(data, dict) and "preconisations" in data:
                    data = data["preconisations"]
                if not isinstance(data, list):
                    data = [data] if isinstance(data, dict) else []
                precos = [Preconisation(**item) for item in data if isinstance(item, dict) and "preconisation" in item]
                logger.info(f"  [Extraction seg {idx+1}/{len(segments)}] p.{segment['page']} -> {len(precos)} préconisation(s)")
                return precos
            except Exception as e:
                logger.warning(f"  [Extraction seg {idx+1}] ÉCHEC: {type(e).__name__}: {e}")
                return []

        tasks = [extract_one(i, seg) for i, seg in enumerate(segments)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_precos: list[Preconisation] = []
        counter = 1
        errors = 0
        for i, result in enumerate(results):
            if isinstance(result, list):
                for preco in result:
                    preco.id = counter
                    counter += 1
                    all_precos.append(preco)
            elif isinstance(result, Exception):
                errors += 1
                logger.error(f"  [Extraction seg {i+1}] Exception non gérée: {result}")

        logger.info(f"  Extraction terminée: {len(all_precos)} préconisations, {errors} erreurs sur {len(segments)} segments")
        return all_precos

    async def _search_legal_base(self, preconisations: list[Preconisation]) -> dict[int, list[dict]]:
        """ParentDocument Retriever: search child chunks in FAISS, return parent chunks."""
        loop = asyncio.get_event_loop()

        def _do_search():
            from langchain_community.vectorstores import FAISS

            embeddings = self._get_embeddings()
            index_path = settings.FAISS_INDEX_DIR / "legal_national.faiss"
            parent_store_path = settings.FAISS_INDEX_DIR / "parent_store.json"

            if not index_path.exists():
                logger.error(f"Index FAISS non trouvé: {index_path}")
                return {p.id: [] for p in preconisations}

            parent_store: dict[str, dict] = {}
            if parent_store_path.exists():
                with open(parent_store_path, "r", encoding="utf-8") as f:
                    parent_store = json.load(f)
                logger.info(f"Parent store chargé: {len(parent_store)} parents")
            else:
                logger.warning("parent_store.json non trouvé — fallback sur child chunks")

            logger.info(f"Chargement index FAISS: {index_path}")
            legal_index = FAISS.load_local(
                str(settings.FAISS_INDEX_DIR),
                embeddings,
                index_name="legal_national",
                allow_dangerous_deserialization=True,
            )

            contexts = {}
            for preco in preconisations:
                results = legal_index.similarity_search_with_score(
                    preco.preconisation, k=settings.TOP_K_RESULTS * 3
                )

                seen_parents: set[str] = set()
                parent_results: list[dict] = []
                for doc, score in results:
                    pid = doc.metadata.get("parent_id", "")
                    if parent_store and pid and pid not in seen_parents:
                        seen_parents.add(pid)
                        parent = parent_store[pid]
                        parent_results.append({
                            "text": parent["text"],
                            "source_doc": parent["source_doc"],
                            "page": parent["page"],
                            "score": float(score),
                        })
                    elif not parent_store:
                        parent_results.append({
                            "text": doc.page_content,
                            "source_doc": doc.metadata.get("source_doc", "unknown"),
                            "page": doc.metadata.get("page", 0),
                            "score": float(score),
                        })
                    if len(parent_results) >= settings.TOP_K_RESULTS:
                        break

                contexts[preco.id] = parent_results
                if parent_results:
                    logger.debug(f"  [FAISS preco {preco.id}] {len(parent_results)} parents (best score={parent_results[0]['score']:.3f}, {len(parent_results[0]['text'])} chars)")
                else:
                    logger.debug(f"  [FAISS preco {preco.id}] 0 résultats")
            return contexts

        return await loop.run_in_executor(None, _do_search)

    async def _validate_matches(
        self, preconisations: list[Preconisation], legal_contexts: dict[int, list[dict]]
    ) -> list[PreconisationResult]:
        async def validate_one(preco: Preconisation) -> PreconisationResult:
            contexts = legal_contexts.get(preco.id, [])
            if not contexts:
                logger.info(f"  [Validation preco {preco.id}] Aucun contexte légal -> score=0")
                return PreconisationResult(
                    preconisation=preco,
                    match=LegalMatch(
                        score_reutilisation=0,
                        justification="Aucun texte légal trouvé dans la base",
                    ),
                )

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
                logger.debug(f"  [Validation preco {preco.id}] Réponse LLM: {raw[:150]}...")
                data = json.loads(raw)
                data = self._sanitize_legal_match(data)
                match = LegalMatch(**data)
                logger.info(f"  [Validation preco {preco.id}] score={match.score_reutilisation}, source={match.legal_source_doc}")
                return PreconisationResult(preconisation=preco, match=match)
            except Exception as e:
                logger.warning(f"  [Validation preco {preco.id}] ÉCHEC: {type(e).__name__}: {e}")
                return PreconisationResult(
                    preconisation=preco,
                    match=LegalMatch(
                        score_reutilisation=0,
                        justification=f"Erreur lors de la validation: {str(e)}",
                    ),
                )

        tasks = [validate_one(preco) for preco in preconisations]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        validated: list[PreconisationResult] = []
        for result in results:
            if isinstance(result, PreconisationResult):
                validated.append(result)

        return validated

    async def _generate_synthesis(
        self,
        results: list[PreconisationResult],
        source_doc: str,
        total: int,
        matched: int,
        taux: float,
    ) -> tuple[str, list[CategoryStat]]:
        matched_lines: list[str] = []
        unmatched_lines: list[str] = []

        for r in results:
            score = r.match.score_reutilisation if r.match else 0
            if score > 0 and r.match:
                matched_lines.append(
                    f"- #{r.preconisation.id} (score={score}, sim={r.match.score_similarite}%): "
                    f"\"{r.preconisation.preconisation[:150]}\""
                )
            else:
                unmatched_lines.append(
                    f"- #{r.preconisation.id}: \"{r.preconisation.preconisation[:150]}\""
                )

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
            synthese_text = data.get("synthese", "")
            raw_cats = data.get("categories", [])
            categories = [
                CategoryStat(
                    categorie=c.get("categorie", "Autre"),
                    preco_ids=c.get("preco_ids", []),
                    matched=c.get("matched", 0),
                    unmatched=c.get("unmatched", 0),
                )
                for c in raw_cats
                if isinstance(c, dict)
            ]
            return synthese_text, categories
        except json.JSONDecodeError:
            return raw, []
        except Exception as e:
            logger.warning(f"Synthesis generation failed: {e}")
            return "", []
