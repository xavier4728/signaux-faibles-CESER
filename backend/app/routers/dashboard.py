from fastapi import APIRouter, HTTPException
from app.services.dashboard_service import dashboard_service
from app.models.dashboard import DashboardResponse

router = APIRouter()

@router.get("/stats", response_model=DashboardResponse)
async def get_dashboard_stats():
    try:
        return dashboard_service.get_global_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))