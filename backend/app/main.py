from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from loguru import logger

from app.core.config import settings
from app.routers import ingest, analysis, documents, chat, dashboard


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Signaux Faibles CESER API...")
    logger.info(f"FAISS indexes directory: {settings.FAISS_INDEX_DIR}")
    yield
    logger.info("Shutting down Signaux Faibles CESER API...")


app = FastAPI(
    title="Signaux Faibles CESER - API",
    description="API RAG pour l'analyse des signaux faibles des CESER en agriculture",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ingest.router, prefix="/api/ingest", tags=["Ingestion"])
app.include_router(analysis.router, prefix="/api/analysis", tags=["Analysis"])
app.include_router(documents.router, prefix="/api/documents", tags=["Documents"])
app.include_router(chat.router, prefix="/api/chat", tags=["Chat"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["Dashboard"])

@app.get("/api/health")
async def health_check():
    return {"status": "ok", "service": "signaux-faibles-ceser"}
