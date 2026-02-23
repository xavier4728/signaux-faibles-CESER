from fastapi import APIRouter, UploadFile, File, Form, BackgroundTasks, HTTPException
from fastapi.responses import StreamingResponse
from loguru import logger
import uuid
import json
import asyncio

from app.models.schemas import AnalysisResponse, AnalysisResult, TaskStatus
from app.services.rag_pipeline import RAGPipeline
from app.services.task_manager import task_manager

router = APIRouter()
rag_pipeline = RAGPipeline()


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
