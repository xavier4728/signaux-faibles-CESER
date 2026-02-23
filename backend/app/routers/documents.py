from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from loguru import logger
from pathlib import Path

from app.core.config import settings
from app.models.schemas import DocumentInfo, DatabaseTarget
from app.services.vector_store import VectorStoreManager

router = APIRouter()
vector_store = VectorStoreManager()


@router.get("/list", response_model=list[DocumentInfo])
async def list_documents(database: DatabaseTarget | None = None, region: str | None = None):
    try:
        docs = vector_store.list_documents(database=database, region=region)
        return docs
    except Exception as e:
        logger.error(f"Error listing documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/databases")
async def list_databases():
    return {
        "databases": [
            {"id": "legal_national", "name": "Base Légale / Nationale", "type": "legal"},
            {"id": "ceser_bretagne", "name": "CESER Bretagne", "type": "ceser"},
            {"id": "ceser_centre_val_de_loire", "name": "CESER Centre-Val de Loire", "type": "ceser"},
            {"id": "ceser_grand_est", "name": "CESER Grand Est", "type": "ceser"},
            {"id": "ceser_hauts_de_france", "name": "CESER Hauts-de-France", "type": "ceser"},
            {"id": "ceser_la_reunion", "name": "CESER La Réunion", "type": "ceser"},
            {"id": "ceser_normandie", "name": "CESER Normandie", "type": "ceser"},
            {"id": "ceser_nouvelle_aquitaine", "name": "CESER Nouvelle-Aquitaine", "type": "ceser"},
            {"id": "ceser_pays_de_la_loire", "name": "CESER Pays de la Loire", "type": "ceser"},
        ]
    }


@router.get("/pdf/{filename:path}")
async def serve_pdf(filename: str):
    """Serve a PDF file from any document folder."""
    safe_name = Path(filename).name
    for subdir in settings.DOCUMENTS_DIR.iterdir():
        if subdir.is_dir():
            candidate = subdir / safe_name
            if candidate.exists() and candidate.is_file():
                return FileResponse(
                    path=str(candidate),
                    media_type="application/pdf",
                    headers={"Content-Disposition": f"inline; filename=\"{safe_name}\""},
                )
    raise HTTPException(status_code=404, detail=f"PDF non trouvé: {safe_name}")


@router.get("/{document_id}")
async def get_document(document_id: str):
    doc = vector_store.get_document(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document non trouvé")
    return doc
