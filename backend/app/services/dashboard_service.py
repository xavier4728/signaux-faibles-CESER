import json
from loguru import logger
from app.core.config import settings
from app.models.dashboard import (
    DashboardResponse, KpiStats, RegionStat,
    ScoreDistribution, SimilarityBucket, DocumentRanking, LegalReference,
    CategoryStatWithRegions, RegionOverlap,
)


class DashboardService:
    def __init__(self):
        self.store_path = settings.FAISS_INDEX_DIR / "analytics_store.json"

    def _load_store(self) -> dict:
        if not self.store_path.exists():
            return {}
        try:
            with open(self.store_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Erreur lecture analytics store: {e}")
            return {}

    def get_global_stats(self) -> DashboardResponse:
        store = self._load_store()
        kpis_data = store.get("global_kpis", {})
        regions_data = store.get("regions", {})

        region_stats = []
        all_docs: list[DocumentRanking] = []
        global_s0, global_s1, global_s2 = 0, 0, 0
        all_similarities: list[float] = []
        legal_counter: dict[str, int] = {}

        for region_id, rdata in regions_data.items():
            r_s0, r_s1, r_s2 = 0, 0, 0

            for doc in rdata.get("documents", []):
                s0 = doc.get("score_0_count", 0)
                s1 = doc.get("score_1_count", 0)
                s2 = doc.get("score_2_count", 0)
                r_s0 += s0
                r_s1 += s1
                r_s2 += s2

                all_docs.append(DocumentRanking(
                    filename=doc.get("filename", ""),
                    region=rdata.get("label", region_id),
                    total_precos=doc.get("total_precos", 0),
                    matched_precos=doc.get("matched_precos", 0),
                    taux_conversion=doc.get("taux_conversion", 0.0),
                    avg_similarity=doc.get("avg_similarity", 0.0),
                    score_2_count=s2,
                    score_1_count=s1,
                    score_0_count=s0,
                ))

                for preco in doc.get("preconisations", []):
                    if preco.get("score", 0) > 0:
                        all_similarities.append(preco.get("similarite", 0.0))
                    legal = preco.get("legal_doc", "")
                    if legal:
                        legal_counter[legal] = legal_counter.get(legal, 0) + 1

            global_s0 += r_s0
            global_s1 += r_s1
            global_s2 += r_s2

            region_stats.append(RegionStat(
                region=rdata.get("label", region_id),
                region_id=region_id,
                documents_count=rdata.get("documents_count", 0),
                total_precos=rdata.get("total_precos", 0),
                matched_precos=rdata.get("matched_precos", 0),
                taux_conversion=rdata.get("taux_conversion", 0.0),
                score_2_count=r_s2,
                score_1_count=r_s1,
                score_0_count=r_s0,
            ))

        # Similarity histogram buckets
        buckets = [
            SimilarityBucket(range="25-40%", count=0),
            SimilarityBucket(range="40-55%", count=0),
            SimilarityBucket(range="55-70%", count=0),
            SimilarityBucket(range="70-85%", count=0),
            SimilarityBucket(range="85-100%", count=0),
        ]
        for s in all_similarities:
            if s < 40:
                buckets[0].count += 1
            elif s < 55:
                buckets[1].count += 1
            elif s < 70:
                buckets[2].count += 1
            elif s < 85:
                buckets[3].count += 1
            else:
                buckets[4].count += 1

        # Sort docs by taux_conversion for rankings
        sorted_docs = sorted(all_docs, key=lambda d: d.taux_conversion, reverse=True)
        top_docs = sorted_docs[:8]
        bottom_docs = sorted(all_docs, key=lambda d: d.taux_conversion)[:8]

        # Top legal references
        top_legal = [
            LegalReference(legal_doc=doc, citation_count=count)
            for doc, count in sorted(legal_counter.items(), key=lambda x: -x[1])[:10]
        ]

        # Category stats & region overlap (stockés dans le store, pas de refresh)
        category_stats = [
            CategoryStatWithRegions(category=s["category"], regions=s.get("regions", {}))
            for s in store.get("category_stats", [])
        ]
        ro_data = store.get("region_overlap")
        region_overlap = RegionOverlap(
            region_ids=ro_data.get("region_ids", []),
            region_labels=ro_data.get("region_labels", {}),
            matrix=ro_data.get("matrix", []),
        ) if ro_data else None

        return DashboardResponse(
            kpis=KpiStats(
                taux_conversion_global=kpis_data.get("taux_conversion", 0.0),
                documents_analyses=kpis_data.get("documents_count", 0),
                regions_couvertes=kpis_data.get("regions_count", 0),
                preconisations_extraites=kpis_data.get("total_precos", 0),
                preconisations_matchees=kpis_data.get("matched_precos", 0),
            ),
            comparateur_regional=region_stats,
            score_distribution=ScoreDistribution(
                score_0=global_s0, score_1=global_s1, score_2=global_s2,
            ),
            similarity_buckets=buckets,
            top_documents=top_docs,
            bottom_documents=bottom_docs,
            top_legal_refs=top_legal,
            category_stats=category_stats,
            region_overlap=region_overlap,
        )

    def get_region_detail(self, region_id: str) -> dict | None:
        store = self._load_store()
        regions = store.get("regions", {})
        return regions.get(region_id)


dashboard_service = DashboardService()
