from pydantic import BaseModel
from typing import List, Dict

class KpiStats(BaseModel):
    taux_conversion_global: float
    documents_analyses: int
    regions_couvertes: int
    preconisations_extraites: int

class RegionStat(BaseModel):
    region: str
    count: int
    impact_score: float # Basé sur le taux de conversion

class DashboardResponse(BaseModel):
    kpis: KpiStats
    comparateur_regional: List[RegionStat]
    # Ajoutable plus tard: timeline, cartographie