"""
One-off: remove the last 80 unmatched (score 0) preconisations from
Centre-Val de Loire in analytics_store.json, then recompute stats and save.
"""
import json
from pathlib import Path

sys_path = Path(__file__).resolve().parent.parent
import sys
sys.path.insert(0, str(sys_path))

from app.core.config import settings

STORE_PATH = settings.FAISS_INDEX_DIR / "analytics_store.json"
REGION_ID = "ceser_centre_val_de_loire"
TRIM_LAST_N_UNMATCHED = 70


def main():
    with open(STORE_PATH, "r", encoding="utf-8") as f:
        store = json.load(f)

    regions = store.get("regions", {})
    if REGION_ID not in regions:
        print(f"Region {REGION_ID} not in store. Exit.")
        return

    region = regions[REGION_ID]
    documents = region.get("documents", [])

    # Collect (doc_idx, preco_idx) for every preco with score == 0, in order
    unmatched_refs = []
    for doc_idx, doc in enumerate(documents):
        precos = doc.get("preconisations", [])
        for preco_idx, p in enumerate(precos):
            if p.get("score", -1) == 0:
                unmatched_refs.append((doc_idx, preco_idx))

    to_remove = set()
    if len(unmatched_refs) > TRIM_LAST_N_UNMATCHED:
        for ref in unmatched_refs[-TRIM_LAST_N_UNMATCHED:]:
            to_remove.add(ref)
        print(f"Removing last {TRIM_LAST_N_UNMATCHED} unmatched preconisations (of {len(unmatched_refs)} total unmatched).")
    else:
        print(f"Only {len(unmatched_refs)} unmatched; trimming all would remove all. Exiting without change.")
        return

    # Build per-doc sets of preco indices to remove
    to_remove_per_doc = {}
    for (doc_idx, preco_idx) in to_remove:
        to_remove_per_doc.setdefault(doc_idx, set()).add(preco_idx)

    # Filter preconisations and recompute doc stats
    new_docs = []
    region_total = 0
    region_matched = 0

    for doc_idx, doc in enumerate(documents):
        precos = doc.get("preconisations", [])
        remove_indices = to_remove_per_doc.get(doc_idx, set())
        new_precos = [p for i, p in enumerate(precos) if i not in remove_indices]

        s0 = sum(1 for p in new_precos if p.get("score", -1) == 0)
        s1 = sum(1 for p in new_precos if p.get("score", -1) == 1)
        s2 = sum(1 for p in new_precos if p.get("score", -1) == 2)
        matched = s1 + s2
        total = len(new_precos)
        taux = round((matched / total * 100) if total > 0 else 0.0, 1)
        sims = [p.get("similarite", 0) for p in new_precos if p.get("score", 0) > 0]
        avg_sim = round(sum(sims) / len(sims), 1) if sims else 0.0

        new_doc = {
            **doc,
            "preconisations": new_precos,
            "total_precos": total,
            "matched_precos": matched,
            "taux_conversion": taux,
            "score_0_count": s0,
            "score_1_count": s1,
            "score_2_count": s2,
            "avg_similarity": avg_sim,
        }
        new_docs.append(new_doc)
        region_total += total
        region_matched += matched

    region_taux = round((region_matched / region_total * 100) if region_total > 0 else 0.0, 1)
    region["documents"] = new_docs
    region["total_precos"] = region_total
    region["matched_precos"] = region_matched
    region["taux_conversion"] = region_taux

    # Recompute global_kpis
    kpis = store.get("global_kpis", {})
    all_total = sum(r.get("total_precos", 0) for r in regions.values())
    all_matched = sum(r.get("matched_precos", 0) for r in regions.values())
    kpis["total_precos"] = all_total
    kpis["matched_precos"] = all_matched
    kpis["taux_conversion"] = round((all_matched / all_total * 100) if all_total > 0 else 0.0, 1)
    store["global_kpis"] = kpis

    with open(STORE_PATH, "w", encoding="utf-8") as f:
        json.dump(store, f, indent=2, ensure_ascii=False)

    print(f"Centre-Val de Loire: {region_total} précos (was {region_total + len(to_remove)} before trim), {region_matched} matchées ({region_taux}%).")
    print(f"Saved to {STORE_PATH}")


if __name__ == "__main__":
    main()
