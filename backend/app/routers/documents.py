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
            {"id": "ceser_normandie", "name": "CESER Normandie", "type": "ceser"},
            {"id": "ceser_bretagne", "name": "CESER Bretagne", "type": "ceser"},
            {"id": "ceser_ile_de_france", "name": "CESER Île-de-France", "type": "ceser"},
            {"id": "ceser_occitanie", "name": "CESER Occitanie", "type": "ceser"},
            {"id": "ceser_auvergne_rhone_alpes", "name": "CESER Auvergne-Rhône-Alpes", "type": "ceser"},
            {"id": "ceser_nouvelle_aquitaine", "name": "CESER Nouvelle-Aquitaine", "type": "ceser"},
            {"id": "ceser_grand_est", "name": "CESER Grand Est", "type": "ceser"},
            {"id": "ceser_hauts_de_france", "name": "CESER Hauts-de-France", "type": "ceser"},
        ]
    }


@router.get("/pdf/{filename:path}")
async def serve_pdf(filename: str):
    """Serve a legal PDF file for in-browser viewing."""
    safe_name = Path(filename).name
    pdf_path = settings.DOCUMENTS_DIR / "legal_national" / safe_name
    if not pdf_path.exists() or not pdf_path.is_file():
        raise HTTPException(status_code=404, detail=f"PDF non trouvé: {safe_name}")
    return FileResponse(
        path=str(pdf_path),
        media_type="application/pdf",
        headers={"Content-Disposition": f"inline; filename=\"{safe_name}\""},
    )


@router.get("/{document_id}")
async def get_document(document_id: str):
    doc = vector_store.get_document(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document non trouvé")
    return doc
