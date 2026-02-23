import asyncio
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from loguru import logger

from app.core.config import settings
from app.services.task_manager import task_manager
from app.prompts.extraction import CHATBOT_SYSTEM_PROMPT

router = APIRouter()

_llm_client = None


def _get_llm():
    global _llm_client
    if _llm_client is None:
        from mistralai import Mistral
        _llm_client = Mistral(api_key=settings.MISTRAL_API_KEY)
    return _llm_client


class ChatRequest(BaseModel):
    task_id: str
    message: str
    history: list[dict] = []


class ChatResponse(BaseModel):
    response: str


def _build_analysis_context(result) -> str:
    lines = [
        f"Document source : {result.source_document}",
        f"Total préconisations : {result.total_preconisations}",
        f"Préconisations reprises : {result.matched_preconisations}",
        f"Taux de conversion : {result.taux_conversion}%",
    ]

    if result.synthese:
        lines.append(f"\nSYNTHÈSE ANALYTIQUE :\n{result.synthese}")

    if result.categories:
        lines.append("\nCATÉGORIES THÉMATIQUES :")
        for cat in result.categories:
            lines.append(f"- {cat.categorie}: {cat.matched} reprises, {cat.unmatched} non reprises (précos {cat.preco_ids})")

    lines.append("\nDÉTAIL DES PRÉCONISATIONS :")
    for r in result.results:
        p = r.preconisation
        score = r.match.score_reutilisation if r.match else 0
        sim = r.match.score_similarite if r.match else 0
        status = {0: "Non retrouvé", 1: "Influence indirecte", 2: "Reprise littérale"}.get(score, "?")
        line = f"\n#{p.id} [{status}, similarité {sim}%] ({p.source_doc} p.{p.page})\n  \"{p.preconisation[:300]}\""
        if r.match and score > 0:
            line += f"\n  → Texte légal: {r.match.legal_source_doc} p.{r.match.legal_page}"
            line += f"\n  → Extrait: \"{r.match.extrait_legal_exact[:300]}\""
        elif r.match:
            line += f"\n  → Justification: {r.match.justification}"
        lines.append(line)

    return "\n".join(lines)


@router.post("/message", response_model=ChatResponse)
async def chat_message(req: ChatRequest):
    task = task_manager.get_task(req.task_id)
    if not task or not task.result:
        raise HTTPException(status_code=404, detail="Analyse non trouvée. Lancez d'abord une analyse.")

    context = _build_analysis_context(task.result)
    system_prompt = CHATBOT_SYSTEM_PROMPT.format(analysis_context=context)

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
        logger.info(f"[Chat] task={req.task_id} q=\"{req.message[:60]}\" -> {len(answer)} chars")
        return ChatResponse(response=answer)
    except Exception as e:
        logger.error(f"[Chat] LLM error: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur LLM: {str(e)}")
