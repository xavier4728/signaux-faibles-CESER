from pydantic import BaseModel


class KpiStats(BaseModel):
    taux_conversion_global: float
    documents_analyses: int
    regions_couvertes: int
    preconisations_extraites: int
    preconisations_matchees: int = 0


class RegionStat(BaseModel):
    region: str
    region_id: str = ""
    documents_count: int = 0
    total_precos: int = 0
    matched_precos: int = 0
    taux_conversion: float = 0.0
    score_2_count: int = 0
    score_1_count: int = 0
    score_0_count: int = 0


class ScoreDistribution(BaseModel):
    score_0: int = 0
    score_1: int = 0
    score_2: int = 0


class SimilarityBucket(BaseModel):
    range: str
    count: int = 0


class DocumentRanking(BaseModel):
    filename: str
    region: str
    total_precos: int = 0
    matched_precos: int = 0
    taux_conversion: float = 0.0
    avg_similarity: float = 0.0
    score_2_count: int = 0
    score_1_count: int = 0
    score_0_count: int = 0


class LegalReference(BaseModel):
    legal_doc: str
    citation_count: int = 0


class DashboardResponse(BaseModel):
    kpis: KpiStats
    comparateur_regional: list[RegionStat]
    score_distribution: ScoreDistribution = ScoreDistribution()
    similarity_buckets: list[SimilarityBucket] = []
    top_documents: list[DocumentRanking] = []
    bottom_documents: list[DocumentRanking] = []
    top_legal_refs: list[LegalReference] = []
