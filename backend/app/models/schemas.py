from pydantic import BaseModel, Field
from enum import Enum


class DatabaseTarget(str, Enum):
    LEGAL = "legal_national"
    CESER_NORMANDIE = "ceser_normandie"
    CESER_BRETAGNE = "ceser_bretagne"
    CESER_IDF = "ceser_ile_de_france"
    CESER_OCCITANIE = "ceser_occitanie"
    CESER_AURA = "ceser_auvergne_rhone_alpes"
    CESER_NOUVELLE_AQUITAINE = "ceser_nouvelle_aquitaine"
    CESER_GRAND_EST = "ceser_grand_est"
    CESER_HAUTS_DE_FRANCE = "ceser_hauts_de_france"


class DocumentMetadata(BaseModel):
    title: str = ""
    year: int | None = None
    doc_type: str = ""
    theme: str = ""
    region: str = ""


class IngestRequest(BaseModel):
    target_db: DatabaseTarget
    metadata: DocumentMetadata = Field(default_factory=DocumentMetadata)


class IngestResponse(BaseModel):
    task_id: str
    status: str
    message: str


class Preconisation(BaseModel):
    id: int
    preconisation: str
    source_doc: str = ""
    page: int = 0


class LegalMatch(BaseModel):
    score_reutilisation: int = Field(ge=0, le=2)
    score_similarite: float = Field(default=0.0, ge=0, le=100)
    justification: str = ""
    legal_source_doc: str = ""
    legal_page: int = 0
    extrait_legal_exact: str = ""


class PreconisationResult(BaseModel):
    preconisation: Preconisation
    match: LegalMatch | None = None


class AnalysisRequest(BaseModel):
    document_id: str | None = None
    region_filter: str | None = None


class AnalysisResponse(BaseModel):
    task_id: str
    status: str
    message: str


class AnalysisResult(BaseModel):
    task_id: str
    status: str
    source_document: str
    total_preconisations: int
    matched_preconisations: int
    taux_conversion: float
    results: list[PreconisationResult]


class TaskStatus(BaseModel):
    task_id: str
    status: str  # pending, processing, completed, failed
    progress: float = 0.0
    message: str = ""
    result: AnalysisResult | None = None


class DocumentInfo(BaseModel):
    id: str
    filename: str
    database: str
    metadata: DocumentMetadata
    chunk_count: int = 0
