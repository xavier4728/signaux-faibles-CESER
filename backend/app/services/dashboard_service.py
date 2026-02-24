import json
from pathlib import Path
from loguru import logger
from app.core.config import settings
from app.services.vector_store import VectorStoreManager
from app.models.schemas import AnalysisResult
from app.models.dashboard import DashboardResponse, KpiStats, RegionStat

class DashboardService:
    def __init__(self):
        # On ne définit plus self.store_path ici car il est dynamique par région
        self.vector_store = VectorStoreManager()
        # Note: On ne force plus _ensure_store() à l'init car on a plusieurs dossiers potentiels

    def _get_store_path(self, region: str) -> Path:
        """Génère le chemin du fichier JSON pour une région spécifique."""
        return settings.FAISS_INDEX_DIR / region / "analytics_store.json"

    def _ensure_region_store(self, region: str) -> Path:
        """Crée le dossier et le fichier JSON pour la région s'ils n'existent pas."""
        store_path = self._get_store_path(region)
        if not store_path.exists():
            try:
                # Création récursive du dossier parent (ex: data/faiss_indexes/bretagne/)
                store_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Initialisation du fichier JSON vide
                with open(store_path, "w", encoding="utf-8") as f:
                    json.dump({"analyses": []}, f)
            except Exception as e:
                logger.error(f"Erreur lors de la création du store pour la région {region}: {e}")
        return store_path

    def _load_analyses(self, region: str = None) -> list[dict]:
        """
        Charge l'historique des analyses.
        - Si `region` est fourni : charge uniquement le fichier de cette région.
        - Si `region` est None : charge et agrège les fichiers de TOUTES les régions (CESER_REGIONS).
        """
        all_analyses = []
        
        # Détermine quelles régions scanner
        regions_to_scan = [region] if region else settings.CESER_REGIONS

        for reg in regions_to_scan:
            path = self._get_store_path(reg)
            if path.exists():
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        analyses = data.get("analyses", [])
                        # On ajoute tout à la liste globale
                        all_analyses.extend(analyses)
                except Exception as e:
                    logger.error(f"Erreur lecture analytics store pour {reg}: {e}")
        
        return all_analyses

    def save_analysis_result(self, result: AnalysisResult, region: str):
        """
        Sauvegarde les stats d'analyse dans le dossier spécifique à la région.
        L'argument `region` est désormais obligatoire.
        """
        try:
            store_path = self._ensure_region_store(region)
            
            # On charge uniquement les données de CETTE région pour modification
            current_region_data = []
            if store_path.exists():
                with open(store_path, "r", encoding="utf-8") as f:
                    current_region_data = json.load(f).get("analyses", [])
            
            analysis_summary = {
                "task_id": result.task_id,
                "source_document": result.source_document,
                "total_precos": result.total_preconisations,
                "matched_precos": result.matched_preconisations,
                "taux_conversion": result.taux_conversion,
                "region": region,  # On ajoute la région dans l'objet pour traçabilité
                # On pourrait ajouter un timestamp ici
            }
            
            current_region_data.append(analysis_summary)
            
            with open(store_path, "w", encoding="utf-8") as f:
                json.dump({"analyses": current_region_data}, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Stats Dashboard sauvegardées pour {result.source_document} dans {region}")
        except Exception as e:
            logger.error(f"Impossible de sauvegarder les stats dashboard pour {region}: {e}")

    def get_global_stats(self) -> DashboardResponse:
        """Agrège les données de toutes les régions configurées."""
        
        # 1. Récupérer les données d'ingestion (Vector Store) pour comptage docs
        try:
            docs = self.vector_store.list_documents()
            # Set pour compter les régions uniques détectées dans les métadonnées documents
            regions_in_docs = {doc.metadata.region for doc in docs if doc.metadata.region}
            nb_docs = len(docs)
        except Exception as e:
            logger.error(f"Erreur lecture VectorStore pour stats: {e}")
            docs = []
            regions_in_docs = set()
            nb_docs = 0
        
        # 2. Récupérer les données d'analyse (Analytics Store) agrégées via _load_analyses()
        analyses = self._load_analyses(region=None) # None = charge toutes les régions
        
        total_precos = sum(a.get("total_precos", 0) for a in analyses)
        total_matched = sum(a.get("matched_precos", 0) for a in analyses)
        
        # Calcul du taux global (moyenne pondérée sur l'ensemble)
        taux_global = (total_matched / total_precos * 100) if total_precos > 0 else 0.0

        # 3. Construire la réponse
        return DashboardResponse(
            kpis=KpiStats(
                taux_conversion_global=round(taux_global, 1),
                documents_analyses=nb_docs,
                regions_couvertes=len(regions_in_docs),
                preconisations_extraites=total_precos
            ),
            comparateur_regional=[] # TODO: Implémenter le détail par région plus tard si nécessaire
        )

# Instance singleton exportée
dashboard_service = DashboardService()