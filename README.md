# Signaux Faibles CESER — Plateforme RAG d'analyse IA

Outil d'analyse par IA des signaux faibles détectés par les 8 CESER en agriculture. L'objectif est de prouver la capacité d'anticipation des instances régionales (5 à 7 ans avant l'émergence d'une crise) en croisant leurs rapports historiques (2015-2025) avec des décisions politiques nationales ou européennes.

## Architecture

```
signaux-faibles-CESER/
├── frontend/          # Next.js 16 + TypeScript + Tailwind + shadcn/ui
├── backend/           # FastAPI + FAISS + LangChain + Mistral
├── data/              # Documents source (PDF CESER + textes légaux)
└── docs/              # Documentation
```

## Stack technique

| Composant | Technologie |
|-----------|-------------|
| Frontend | Next.js (App Router), TypeScript, Tailwind CSS, shadcn/ui |
| Dataviz | Recharts, react-simple-maps |
| Backend | Python 3.11+, FastAPI |
| Base vectorielle | FAISS (indexes séparés par région) |
| LLM | Mistral (via API) |
| Embeddings | sentence-transformers/all-MiniLM-L6-v2 |
| Parsing PDF | Unstructured |

## Démarrage rapide

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # Configurer la clé API Mistral
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

L'application est accessible sur `http://localhost:3000`.

## Pages

- `/dashboard` — Observatoire national, KPIs globaux, cartographie
- `/analysis` — Analyse documentaire détaillée (pipeline RAG)
- `/admin/ingest` — Administration et ingestion des documents

## Pipeline RAG

1. **Parsing** : Extraction du texte via Unstructured (PDF/Word)
2. **Extraction** : Identification des préconisations via Mistral (JSON structuré)
3. **Recherche vectorielle** : Interrogation FAISS sur la base légale nationale
4. **Validation** : Scoring de réutilisation via Mistral (0/1/2) avec sourcing exact

## Licence

MIT — voir [LICENSE](./LICENSE)
