import asyncio
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from loguru import logger

from app.core.config import settings
from app.services.dashboard_service import dashboard_service
from app.models.dashboard import DashboardResponse
from app.prompts.extraction import OBSERVATOIRE_CHATBOT_SYSTEM_PROMPT

router = APIRouter()

_llm_client = None


def _get_llm():
    global _llm_client
    if _llm_client is None:
        from mistralai import Mistral
        _llm_client = Mistral(api_key=settings.MISTRAL_API_KEY)
    return _llm_client


def _build_observatoire_context(stats: DashboardResponse) -> str:
    lines = [
        "=== KPIs GLOBAUX ===",
        f"Taux de conversion global : {stats.kpis.taux_conversion_global}%",
        f"Documents analysés : {stats.kpis.documents_analyses}",
        f"Régions couvertes : {stats.kpis.regions_couvertes}",
        f"Préconisations extraites : {stats.kpis.preconisations_extraites}",
        f"Préconisations matchées : {stats.kpis.preconisations_matchees}",
        "",
        "=== RÉPARTITION DES SCORES ===",
        f"Non retrouvées (score 0) : {stats.score_distribution.score_0}",
        f"Reprises partielles (score 1) : {stats.score_distribution.score_1}",
        f"Reprises directes (score 2) : {stats.score_distribution.score_2}",
        "",
        "=== COMPARATEUR RÉGIONAL (par région) ===",
    ]
    for r in stats.comparateur_regional:
        lines.append(
            f"- {r.region} : {r.documents_count} docs, {r.total_precos} préconisations, "
            f"{r.matched_precos} matchées, taux {r.taux_conversion}% "
            f"(reprises directes: {r.score_2_count}, partielles: {r.score_1_count}, non retrouvées: {r.score_0_count})"
        )
    lines.extend(["", "=== MEILLEURES RÉFÉRENCES LÉGALES (citations) ==="])
    for ref in (stats.top_legal_refs or [])[:10]:
        lines.append(f"- {ref.legal_doc} : {ref.citation_count} citations")
    lines.extend(["", "=== PART DES RÉGIONS PAR THÉMATIQUE (category_stats) ==="])
    for s in (stats.category_stats or []):
        total_cat = sum(s.regions.values())
        lines.append(f"- {s.category} : total {total_cat} ; par région : {s.regions}")
    if stats.region_overlap:
        lines.extend(["", "=== RECOUPEMENT ENTRE RÉGIONS (matrice de similarité) ==="])
        lines.append(f"Régions : {stats.region_overlap.region_ids}")
        lines.append(f"Labels : {stats.region_overlap.region_labels}")
        for i, row in enumerate(stats.region_overlap.matrix):
            rid = stats.region_overlap.region_ids[i] if i < len(stats.region_overlap.region_ids) else i
            lines.append(f"  {stats.region_overlap.region_labels.get(rid, rid)} : {row}")
    return "\n".join(lines)


class DashboardChatRequest(BaseModel):
    message: str
    history: list[dict] = []


class DashboardChatResponse(BaseModel):
    response: str


@router.get("/stats", response_model=DashboardResponse)
async def get_dashboard_stats():
    try:
        return dashboard_service.get_global_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat", response_model=DashboardChatResponse)
async def dashboard_chat(req: DashboardChatRequest):
    try:
        stats = dashboard_service.get_global_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail="Impossible de charger les données de l'Observatoire.")
    context = _build_observatoire_context(stats)
    system_prompt = OBSERVATOIRE_CHATBOT_SYSTEM_PROMPT.format(observatoire_context=context)
    messages = [{"role": "system", "content": system_prompt}]
    for msg in req.history[-10:]:
        messages.append({"role": msg.get("role", "user"), "content": msg.get("content", "")})
    messages.append({"role": "user", "content": req.message})
    try:
        client = _get_llm()
        response = await asyncio.to_thread(
            client.chat.complete,
            model=settings.MISTRAL_MODEL,
            messages=messages,
        )
        answer = response.choices[0].message.content or ""
        logger.info(f"[Dashboard Chat] q=\"{req.message[:60]}\" -> {len(answer)} chars")
        return DashboardChatResponse(response=answer)
    except Exception as e:
        logger.error(f"[Dashboard Chat] LLM error: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur LLM: {str(e)}")