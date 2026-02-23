from fastapi import APIRouter, UploadFile, File, Form, BackgroundTasks, HTTPException
from loguru import logger
import uuid

from app.models.schemas import DatabaseTarget, DocumentMetadata, IngestResponse, TaskStatus
from app.services.ingestion import IngestionService
from app.services.task_manager import task_manager

router = APIRouter()
ingestion_service = IngestionService()


@router.post("/single", response_model=IngestResponse)
async def ingest_single(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    target_db: DatabaseTarget = Form(...),
    title: str = Form(""),
    year: int | None = Form(None),
    doc_type: str = Form(""),
    theme: str = Form(""),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Fichier requis")

    allowed_extensions = {".pdf", ".docx", ".doc", ".txt"}
    ext = "." + file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in allowed_extensions:
        raise HTTPException(status_code=400, detail=f"Format non supporté: {ext}")

    task_id = str(uuid.uuid4())
    metadata = DocumentMetadata(title=title, year=year, doc_type=doc_type, theme=theme)

    file_content = await file.read()

    task_manager.create_task(task_id, f"Ingestion: {file.filename}")

    background_tasks.add_task(
        ingestion_service.ingest_document,
        task_id=task_id,
        filename=file.filename,
        file_content=file_content,
        target_db=target_db,
        metadata=metadata,
    )

    logger.info(f"Ingestion task {task_id} created for {file.filename} -> {target_db}")
    return IngestResponse(task_id=task_id, status="processing", message=f"Ingestion démarrée pour {file.filename}")


@router.post("/batch", response_model=IngestResponse)
async def ingest_batch(
    background_tasks: BackgroundTasks,
    target_db: DatabaseTarget = Form(...),
    source_dir: str = Form(""),
):
    task_id = str(uuid.uuid4())
    task_manager.create_task(task_id, f"Batch ingestion: {target_db}")

    background_tasks.add_task(
        ingestion_service.ingest_batch,
        task_id=task_id,
        target_db=target_db,
        source_dir=source_dir,
    )

    logger.info(f"Batch ingestion task {task_id} created for {target_db}")
    return IngestResponse(task_id=task_id, status="processing", message=f"Ingestion batch démarrée pour {target_db}")


@router.get("/status/{task_id}", response_model=TaskStatus)
async def get_ingest_status(task_id: str):
    status = task_manager.get_task(task_id)
    if not status:
        raise HTTPException(status_code=404, detail="Tâche non trouvée")
    return status
