"""
Compute category_stats and region_overlap from analytics_store preconisations
via LLM categorization, then save back to the store (no refresh on dashboard load).

Usage:
    cd backend && source venv/bin/activate && python -m scripts.compute_category_and_overlap
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import settings
from app.prompts.extraction import CATEGORIZE_SYSTEM_PROMPT
from loguru import logger

STORE_PATH = settings.FAISS_INDEX_DIR / "analytics_store.json"
OUTPUT_SEPARATE_PATH = settings.FAISS_INDEX_DIR / "analytics_category_overlap.json"
BATCH_SIZE = 40
CATEGORIES = [
    "Environnement",
    "Agriculture",
    "Emploi & Formation",
    "Santé",
    "Aménagement du territoire",
    "Gouvernance",
    "Économie",
    "Social",
    "Transport",
    "Énergie",
    "Numérique",
    "Autre",
]


def _get_llm():
    from mistralai import Mistral

    return Mistral(api_key=settings.MISTRAL_API_KEY)


def _call_llm_sync(texts_batch: list[str]) -> list[dict]:
    """Return list of {index, category} for this batch."""
    client = _get_llm()
    numbered = "\n".join(f"{i}. {t[:400]}" for i, t in enumerate(texts_batch))
    user_msg = f"Préconisations à catégoriser (indices 0 à {len(texts_batch)-1}) :\n\n{numbered}\n\nJSON (assignments) :"
    try:
        resp = client.chat.complete(
            model=settings.MISTRAL_MODEL,
            messages=[
                {"role": "system", "content": CATEGORIZE_SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
        )
        raw = (resp.choices[0].message.content or "").strip()
        # Extract JSON (handle markdown code block)
        if "```" in raw:
            raw = raw.split("```")[1].replace("json", "").strip()
        data = json.loads(raw)
        assignments = data.get("assignments", [])
        out = []
        for a in assignments:
            idx = a.get("index", len(out))
            cat = a.get("category", "Autre")
            if cat not in CATEGORIES:
                cat = "Autre"
            out.append({"index": idx, "category": cat})
        # Sort by index and fill gaps with Autre
        by_idx = {a["index"]: a["category"] for a in out}
        return [by_idx.get(i, "Autre") for i in range(len(texts_batch))]
    except Exception as e:
        logger.warning(f"LLM batch error: {e}")
        return ["Autre"] * len(texts_batch)


def main():
    logger.info("Chargement du store...")
    with open(STORE_PATH, "r", encoding="utf-8") as f:
        store = json.load(f)

    regions_data = store.get("regions", {})
    if not regions_data:
        logger.warning("Aucune région dans le store.")
        return

    # Collect (region_id, text) in order
    items: list[tuple[str, str]] = []
    for region_id, rdata in regions_data.items():
        for doc in rdata.get("documents", []):
            for p in doc.get("preconisations", []):
                text = (p.get("text") or "").strip()
                if text:
                    items.append((region_id, text))

    if not items:
        logger.warning("Aucune préconisation dans le store.")
        return

    logger.info(
        f"Catégorisation de {len(items)} préconisations par LLM (batch={BATCH_SIZE})..."
    )
    categories_per_item: list[str] = []
    for start in range(0, len(items), BATCH_SIZE):
        batch = [items[i][1] for i in range(start, min(start + BATCH_SIZE, len(items)))]
        batch_cats = _call_llm_sync(batch)
        categories_per_item.extend(batch_cats)
        logger.info(
            f"  Batch {start // BATCH_SIZE + 1}/{(len(items) + BATCH_SIZE - 1) // BATCH_SIZE} ok."
        )

    # Build category_stats: for each category, count per region_id
    category_counts: dict[str, dict[str, int]] = {}
    for (region_id, _), cat in zip(items, categories_per_item):
        if cat not in category_counts:
            category_counts[cat] = {}
        category_counts[cat][region_id] = category_counts[cat].get(region_id, 0) + 1

    category_stats = [
        {"category": cat, "regions": category_counts[cat]}
        for cat in CATEGORIES
        if cat in category_counts and category_counts[cat]
    ]
    if (
        "Autre" in category_counts
        and category_counts["Autre"]
        and not any(s["category"] == "Autre" for s in category_stats)
    ):
        category_stats.append(
            {"category": "Autre", "regions": category_counts["Autre"]}
        )

    # Build region vector per region: category -> count
    region_vectors: dict[str, dict[str, int]] = {}
    for region_id in regions_data:
        region_vectors[region_id] = {cat: 0 for cat in CATEGORIES}
        region_vectors[region_id]["Autre"] = 0
    for (region_id, _), cat in zip(items, categories_per_item):
        region_vectors[region_id][cat] = region_vectors[region_id].get(cat, 0) + 1

    # Overlap matrix: overlap(i,j) = sum over categories of min(v_i[c], v_j[c])
    region_ids = sorted(region_vectors.keys())
    region_labels = {rid: regions_data[rid].get("label", rid) for rid in region_ids}
    n = len(region_ids)
    matrix = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            if i == j:
                matrix[i][j] = 0.0
            else:
                vi = region_vectors[region_ids[i]]
                vj = region_vectors[region_ids[j]]
                overlap = sum(
                    min(vi.get(c, 0), vj.get(c, 0)) for c in set(vi) | set(vj)
                )
                matrix[i][j] = float(overlap)

    store["category_stats"] = category_stats
    store["region_overlap"] = {
        "region_ids": region_ids,
        "region_labels": region_labels,
        "matrix": matrix,
    }

    with open(STORE_PATH, "w", encoding="utf-8") as f:
        json.dump(store, f, indent=2, ensure_ascii=False)

    output = {
        "category_stats": category_stats,
        "region_overlap": store["region_overlap"],
    }
    with open(OUTPUT_SEPARATE_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    logger.info(
        f"Store mis à jour : {len(category_stats)} catégories, matrice {n}x{n}."
    )
    logger.info(f"Résultat : {STORE_PATH}")
    logger.info(f"Copie dans fichier à part : {OUTPUT_SEPARATE_PATH}")


if __name__ == "__main__":
    main()
