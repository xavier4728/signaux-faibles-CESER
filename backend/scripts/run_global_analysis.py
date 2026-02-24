"""
Batch analysis of all CESER documents against the legal base.
Produces analytics_store.json for the global dashboard.

Usage:
    cd backend
    source venv/bin/activate
    python -m scripts.run_global_analysis
"""

import asyncio
import json
import sys
import time
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
from app.core.config import settings
from app.services.rag_pipeline import RAGPipeline

DOCUMENTS_DIR = settings.DOCUMENTS_DIR
OUTPUT_PATH = settings.FAISS_INDEX_DIR / "analytics_store.json"

REGION_LABELS = {
    "ceser_bretagne": "Bretagne",
    "ceser_centre_val_de_loire": "Centre-Val de Loire",
    "ceser_grand_est": "Grand Est",
    "ceser_hauts_de_france": "Hauts-de-France",
    "ceser_la_reunion": "La Réunion",
    "ceser_normandie": "Normandie",
    "ceser_nouvelle_aquitaine": "Nouvelle-Aquitaine",
    "ceser_pays_de_la_loire": "Pays de la Loire",
}


async def analyze_document(pipeline: RAGPipeline, pdf_path: Path, region_id: str) -> dict | None:
    """Run extraction + legal search + validation on a single PDF. Returns a summary dict."""
    filename = pdf_path.name
    logger.info(f"  [{region_id}] Analyse de {filename}...")

    try:
        file_content = pdf_path.read_bytes()

        segments = await pipeline._parse_document(
            task_id=f"batch_{region_id}", file_content=file_content, filename=filename, document_id=None
        )
        if not segments:
            logger.warning(f"  [{region_id}] {filename}: aucun segment extrait, skip")
            return None

        preconisations = await pipeline._extract_preconisations(segments, filename)
        if not preconisations:
            logger.warning(f"  [{region_id}] {filename}: aucune préco extraite, skip")
            return None

        legal_contexts = await pipeline._search_legal_base(preconisations)
        results = await pipeline._validate_matches(preconisations, legal_contexts)

        matched = sum(1 for r in results if r.match and r.match.score_reutilisation > 0)
        total = len(results)
        taux = round((matched / total * 100) if total > 0 else 0.0, 1)

        score_2 = sum(1 for r in results if r.match and r.match.score_reutilisation == 2)
        score_1 = sum(1 for r in results if r.match and r.match.score_reutilisation == 1)
        score_0 = total - score_2 - score_1

        avg_similarity = 0.0
        if matched > 0:
            sims = [r.match.score_similarite for r in results if r.match and r.match.score_reutilisation > 0]
            avg_similarity = round(sum(sims) / len(sims), 1) if sims else 0.0

        categories: dict[str, dict] = {}
        for r in results:
            cat = "Non classé"
            score = r.match.score_reutilisation if r.match else 0
            if cat not in categories:
                categories[cat] = {"matched": 0, "unmatched": 0, "total": 0}
            categories[cat]["total"] += 1
            if score > 0:
                categories[cat]["matched"] += 1
            else:
                categories[cat]["unmatched"] += 1

        precos_detail = []
        for r in results:
            score = r.match.score_reutilisation if r.match else 0
            sim = r.match.score_similarite if r.match else 0
            legal_doc = r.match.legal_source_doc if r.match and score > 0 else ""
            precos_detail.append({
                "id": r.preconisation.id,
                "text": r.preconisation.preconisation[:300],
                "page": r.preconisation.page,
                "score": score,
                "similarite": sim,
                "legal_doc": legal_doc,
            })

        doc_summary = {
            "filename": filename,
            "total_precos": total,
            "matched_precos": matched,
            "taux_conversion": taux,
            "score_2_count": score_2,
            "score_1_count": score_1,
            "score_0_count": score_0,
            "avg_similarity": avg_similarity,
            "preconisations": precos_detail,
        }

        logger.info(f"  [{region_id}] {filename}: {total} précos, {matched} matchées ({taux}%)")
        return doc_summary

    except Exception as e:
        logger.error(f"  [{region_id}] {filename}: ERREUR — {e}")
        return None


def _save_store(global_store: dict, t0: float):
    """Recompute global KPIs from regions and save to disk."""
    regions = global_store["regions"]
    all_total = sum(r["total_precos"] for r in regions.values())
    all_matched = sum(r["matched_precos"] for r in regions.values())
    all_docs = sum(r["documents_count"] for r in regions.values())
    global_taux = round((all_matched / all_total * 100) if all_total > 0 else 0.0, 1)

    global_store["generated_at"] = datetime.now().isoformat()
    global_store["global_kpis"] = {
        "regions_count": len(regions),
        "documents_count": all_docs,
        "total_precos": all_total,
        "matched_precos": all_matched,
        "taux_conversion": global_taux,
        "elapsed_seconds": round(time.time() - t0, 1),
    }

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(global_store, f, indent=2, ensure_ascii=False)

    logger.info(f"  💾 analytics_store.json sauvegardé ({len(regions)} régions, {all_docs} docs, {all_total} précos)")


async def main():
    logger.info("=" * 60)
    logger.info("ANALYSE GLOBALE BATCH — Toutes régions CESER vs base légale")
    logger.info("=" * 60)

    pipeline = RAGPipeline()

    # Load existing store to allow incremental updates
    if OUTPUT_PATH.exists():
        try:
            with open(OUTPUT_PATH, "r", encoding="utf-8") as f:
                content = f.read().strip()
                global_store = json.loads(content) if content else {"regions": {}, "global_kpis": {}}
        except Exception:
            global_store = {"regions": {}, "global_kpis": {}}
    else:
        global_store = {"regions": {}, "global_kpis": {}}

    if "regions" not in global_store:
        global_store["regions"] = {}

    # Build region list sorted by document count (ascending)
    region_queue = []
    for region_id, region_label in REGION_LABELS.items():
        region_dir = DOCUMENTS_DIR / region_id
        if not region_dir.exists():
            continue
        pdfs = sorted(region_dir.glob("*.pdf"))
        if pdfs:
            region_queue.append((region_id, region_label, pdfs))

    region_queue.sort(key=lambda x: len(x[2]))

    logger.info(f"Ordre de traitement ({len(region_queue)} régions) :")
    for rid, rlabel, rpdfs in region_queue:
        already = "✅ déjà fait" if rid in global_store["regions"] else ""
        logger.info(f"  {rlabel}: {len(rpdfs)} docs {already}")

    # Ne traiter que la prochaine région en attente, puis s'arrêter
    next_region = None
    for region_id, region_label, pdfs in region_queue:
        if region_id not in global_store["regions"]:
            next_region = (region_id, region_label, pdfs)
            break

    if not next_region:
        logger.info("\nAucune région en attente — toutes ont déjà été analysées.")
        logger.info("Résultats à jour : " + str(OUTPUT_PATH))
        return

    region_id, region_label, pdfs = next_region
    t0 = time.time()

    logger.info(f"\n{'='*40}")
    logger.info(f"[{region_id}] {region_label} — {len(pdfs)} documents (1 région uniquement)")
    logger.info(f"{'='*40}")

    region_docs = []
    region_total = 0
    region_matched = 0

    for pdf_path in pdfs:
        doc_result = await analyze_document(pipeline, pdf_path, region_id)
        if doc_result:
            region_docs.append(doc_result)
            region_total += doc_result["total_precos"]
            region_matched += doc_result["matched_precos"]

    region_taux = round((region_matched / region_total * 100) if region_total > 0 else 0.0, 1)

    global_store["regions"][region_id] = {
        "label": region_label,
        "documents_count": len(region_docs),
        "total_precos": region_total,
        "matched_precos": region_matched,
        "taux_conversion": region_taux,
        "documents": region_docs,
    }

    logger.info(f"[{region_id}] BILAN: {len(region_docs)} docs, {region_total} précos, {region_matched} matchées ({region_taux}%)")
    _save_store(global_store, t0)

    elapsed = round(time.time() - t0, 1)
    kpis = global_store["global_kpis"]
    logger.info(f"\n{'='*60}")
    logger.info(f"RÉGION TERMINÉE — {region_label} en {elapsed}s")
    logger.info(f"  analytics_store.json mis à jour ({kpis['regions_count']} régions au total)")
    logger.info(f"  Relancez le script pour traiter la région suivante : python -m scripts.run_global_analysis")
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
