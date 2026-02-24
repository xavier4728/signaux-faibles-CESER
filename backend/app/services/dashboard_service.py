import json
from pathlib import Path
from loguru import logger
from app.core.config import settings
from app.services.vector_store import VectorStoreManager
from app.models.schemas import AnalysisResult
from app.models.dashboard import DashboardResponse, KpiStats, RegionStat

class DashboardService:
    def __init__(self):
        # On stocke le fichier JSON dans le même dossier que les index FAISS pour la persistance
        self.store_path = settings.FAISS_INDEX_DIR / "analytics_store.json"
        self.vector_store = VectorStoreManager()
        self._ensure_store()

    def _ensure_store(self):
        """Crée le fichier JSON s'il n'existe pas."""
        if not self.store_path.exists():
            try:
                with open(self.store_path, "w", encoding="utf-8") as f:
                    json.dump({"analyses": []}, f)
            except Exception as e:
                logger.error(f"Erreur lors de la création du store analytics: {e}")

    def _load_analyses(self) -> list[dict]:
        """Charge l'historique des analyses."""
        if not self.store_path.exists():
            return []
        try:
            with open(self.store_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("analyses", [])
        except Exception as e:
            logger.error(f"Erreur lecture analytics store: {e}")
            return []

    def save_analysis_result(self, result: AnalysisResult):
        """Appelé à la fin d'une analyse pour sauvegarder les stats."""
        try:
            data = self._load_analyses()
            
            # Éviter les doublons basiques (si on ré-analyse le même doc le même jour, on pourrait affiner ici)
            # Pour l'instant on ajoute tout pour avoir l'historique complet
            
            analysis_summary = {
                "task_id": result.task_id,
                "source_document": result.source_document,
                "total_precos": result.total_preconisations,
                "matched_precos": result.matched_preconisations,
                "taux_conversion": result.taux_conversion,
                # On pourrait ajouter un timestamp ici si AnalysisResult en avait un
            }
            
            data.append(analysis_summary)
            
            with open(self.store_path, "w", encoding="utf-8") as f:
                json.dump({"analyses": data}, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Stats Dashboard sauvegardées pour {result.source_document}")
        except Exception as e:
            logger.error(f"Impossible de sauvegarder les stats dashboard: {e}")

    def get_global_stats(self) -> DashboardResponse:
        """Agrège les données pour le frontend."""
        # 1. Récupérer les données d'ingestion (Vector Store)
        try:
            docs = self.vector_store.list_documents()
            # Set pour compter les régions uniques
            regions = {doc.metadata.region for doc in docs if doc.metadata.region}
            nb_docs = len(docs)
        except Exception as e:
            logger.error(f"Erreur lecture VectorStore pour stats: {e}")
            docs = []
            regions = set()
            nb_docs = 0
        
        # 2. Récupérer les données d'analyse (Analytics Store)
        analyses = self._load_analyses()
        
        total_precos = sum(a.get("total_precos", 0) for a in analyses)
        total_matched = sum(a.get("matched_precos", 0) for a in analyses)
        
        # Calcul du taux global (moyenne pondérée)
        taux_global = (total_matched / total_precos * 100) if total_precos > 0 else 0.0

        # 3. Construire la réponse
        return DashboardResponse(
            kpis=KpiStats(
                taux_conversion_global=round(taux_global, 1),
                documents_analyses=nb_docs,
                regions_couvertes=len(regions),
                preconisations_extraites=total_precos
            ),
            comparateur_regional=[] # TODO: Implémenter le détail par région plus tard
        )

# Instance singleton exportée pour être utilisée dans le router et le pipeline
dashboard_service = DashboardService()