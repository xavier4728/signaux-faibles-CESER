from fastapi import APIRouter, UploadFile, File, Form, BackgroundTasks, HTTPException
from fastapi.responses import StreamingResponse
from loguru import logger
import uuid
import json
import asyncio

from app.models.schemas import AnalysisResponse, AnalysisResult, TaskStatus
from app.services.rag_pipeline import RAGPipeline
from app.services.task_manager import task_manager
from app.services.vector_store import VectorStoreManager

router = APIRouter()
rag_pipeline = RAGPipeline()
vector_store = VectorStoreManager()

# Databases that serve as the comparison base and must never be used as
# analysis input in a batch run.
_EXCLUDED_FROM_BATCH = {"legal_national"}


@router.post("/run", response_model=AnalysisResponse)
async def run_analysis(
    background_tasks: BackgroundTasks,
    file: UploadFile | None = File(None),
    document_id: str | None = Form(None),
    region_filter: str | None = Form(None),
):
    if not file and not document_id:
        raise HTTPException(status_code=400, detail="Fournir un fichier ou un document_id existant")

    task_id = str(uuid.uuid4())
    task_manager.create_task(task_id, "Analyse RAG en cours")

    file_content = None
    filename = None
    if file and file.filename:
        file_content = await file.read()
        filename = file.filename

    background_tasks.add_task(
        rag_pipeline.run_analysis,
        task_id=task_id,
        file_content=file_content,
        filename=filename,
        document_id=document_id,
        region_filter=region_filter,
    )

    logger.info(f"Analysis task {task_id} created")
    return AnalysisResponse(task_id=task_id, status="processing", message="Analyse démarrée")


@router.post("/batch-all", response_model=AnalysisResponse)
async def run_batch_all(background_tasks: BackgroundTasks):
    """Lance l'analyse RAG sur tous les documents CESER déjà indexés.
    Les documents de la base légale nationale sont exclus — ils constituent
    la cible de comparaison, pas la source d'analyse.
    """

    # List ALL documents then exclude the legal/reference databases
    all_docs = vector_store.list_documents()
    ceser_docs = [d for d in all_docs if d.database not in _EXCLUDED_FROM_BATCH]

    if not ceser_docs:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Aucun document CESER trouvé dans le Vector Store. "
                f"Total documents: {len(all_docs)}, "
                f"exclus (bases de référence): {len(all_docs) - len(ceser_docs)}. "
                "Lancez d'abord ingest_cesers.py pour ingérer les rapports régionaux."
            ),
        )

    logger.info(
        f"Batch-all: {len(ceser_docs)} documents CESER sélectionnés "
        f"({len(all_docs) - len(ceser_docs)} documents legal_national exclus)"
    )

    batch_task_id = str(uuid.uuid4())
    task_manager.create_task(
        batch_task_id,
        f"Batch Global: 0/{len(ceser_docs)} traités ({len(all_docs) - len(ceser_docs)} legal exclus)",
    )

    async def _process_batch(main_task_id: str, docs: list):
        logger.info(f"Démarrage Batch Global sur {len(docs)} documents CESER")
        processed = 0

        # Max 2 analyses simultanées pour ne pas saturer le serveur
        sem = asyncio.Semaphore(2)

        async def _analyze_safe(doc):
            async with sem:
                sub_task_id = str(uuid.uuid4())
                task_manager.create_task(sub_task_id, f"Subtask {doc.filename}")
                try:
                    await rag_pipeline.run_analysis(task_id=sub_task_id, document_id=doc.id)
                finally:
                    task_manager.delete_task(sub_task_id)

        for doc in docs:
            try:
                await _analyze_safe(doc)
                processed += 1
                progress = processed / len(docs)
                task_manager.update_task(
                    main_task_id,
                    progress=progress,
                    message=f"Batch: {processed}/{len(docs)} — {doc.filename}",
                )
            except Exception as e:
                logger.error(f"Erreur batch sur {doc.filename}: {e}")

        task_manager.update_task(
            main_task_id,
            status="completed",
            message=f"Batch terminé: {processed}/{len(docs)} docs CESER analysés",
        )

    background_tasks.add_task(_process_batch, batch_task_id, ceser_docs)

    return AnalysisResponse(
        task_id=batch_task_id,
        status="processing",
        message=(
            f"Analyse globale lancée sur {len(ceser_docs)} documents CESER "
            f"({len(all_docs) - len(ceser_docs)} documents legal_national exclus)"
        ),
    )


@router.get("/status/{task_id}", response_model=TaskStatus)
async def get_analysis_status(task_id: str):
    status = task_manager.get_task(task_id)
    if not status:
        raise HTTPException(status_code=404, detail="Tâche non trouvée")
    return status


@router.get("/stream/{task_id}")
async def stream_analysis(task_id: str):
    """SSE endpoint for real-time analysis progress."""
    async def event_generator():
        while True:
            status = task_manager.get_task(task_id)
            if not status:
                yield f"data: {json.dumps({'error': 'Task not found'})}\n\n"
                break

            yield f"data: {status.model_dump_json()}\n\n"

            if status.status in ("completed", "failed"):
                break

            await asyncio.sleep(1)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/result/{task_id}", response_model=AnalysisResult)
async def get_analysis_result(task_id: str):
    status = task_manager.get_task(task_id)
    if not status:
        raise HTTPException(status_code=404, detail="Tâche non trouvée")
    if status.status != "completed":
        raise HTTPException(status_code=202, detail="Analyse en cours")
    if not status.result:
        raise HTTPException(status_code=500, detail="Résultat non disponible")
    return status.result