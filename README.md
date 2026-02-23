# Signaux Faibles CESER — Plateforme RAG d'analyse IA

Outil d'analyse par IA des signaux faibles détectés par les CESER (Conseils Economiques, Sociaux et Environnementaux Régionaux) en agriculture. L'objectif est de prouver la capacité d'anticipation des instances régionales (5 à 7 ans avant l'émergence d'une crise) en croisant leurs rapports historiques (2015-2025) avec des décisions politiques nationales ou européennes.

## Architecture

```
signaux-faibles-CESER/
├── frontend/                        # Next.js 16 + TypeScript + Tailwind + shadcn/ui
│   └── src/
│       ├── app/
│       │   ├── dashboard/           # Observatoire national, KPIs, cartographie
│       │   ├── analysis/            # Analyse documentaire (pipeline RAG)
│       │   └── admin/ingest/        # Ingestion des documents
│       └── components/
│           ├── chat-bot.tsx         # Chatbot IA contextuel (post-analyse)
│           ├── layout/              # Sidebar, Header
│           └── ui/                  # Composants shadcn/ui
├── backend/
│   └── app/
│       ├── core/config.py           # Settings (Pydantic, env vars)
│       ├── models/schemas.py        # Schemas Pydantic (request/response)
│       ├── prompts/extraction.py    # Prompts LLM (extraction, validation, synthèse, chatbot)
│       ├── routers/
│       │   ├── analysis.py          # POST /api/analysis/run, GET /status
│       │   ├── chat.py              # POST /api/chat/message
│       │   ├── documents.py         # GET /databases, GET /pdf/{filename}
│       │   └── ingest.py            # POST /api/ingest (single & batch)
│       ├── services/
│       │   ├── rag_pipeline.py      # Pipeline RAG 5 étapes
│       │   ├── ingestion.py         # Ingestion générique (ParentDocument Retriever)
│       │   ├── vector_store.py      # Gestion FAISS
│       │   └── task_manager.py      # Gestionnaire de tâches async in-memory
│       └── scripts/
│           ├── ingest_legal.py      # Ingestion base légale nationale
│           └── ingest_cesers.py     # Ingestion batch des 8 régions CESER
├── data/
│   └── documents/
│       ├── legal_national/          # Textes de loi, décisions politiques
│       ├── ceser_bretagne/          # Rapports CESER Bretagne
│       ├── ceser_centre_val_de_loire/
│       ├── ceser_grand_est/
│       ├── ceser_hauts_de_france/
│       ├── ceser_la_reunion/
│       ├── ceser_normandie/
│       ├── ceser_nouvelle_aquitaine/
│       └── ceser_pays_de_la_loire/
└── .env                             # Clés API, paramètres de chunking
```

## Stack technique

| Composant | Technologie |
|-----------|-------------|
| Frontend | Next.js 16 (App Router), TypeScript, Tailwind CSS, shadcn/ui |
| Dataviz | Recharts, react-simple-maps |
| Chatbot | react-markdown, remark-gfm |
| Backend | Python 3.11+, FastAPI, asyncio |
| Base vectorielle | FAISS (1 index par région + 1 index légal national) |
| LLM | Mistral Large (via API Mistral) |
| Embeddings | sentence-transformers/all-MiniLM-L6-v2 (HuggingFace) |
| Parsing PDF | ocrmypdf (OCR) + pdfplumber (extraction texte) |
| Chunking | ParentDocument Retriever (child 512 tokens → FAISS, parent 2048 tokens → LLM) |

## Prérequis

- **Node.js** >= 18
- **Python** >= 3.11
- **Tesseract OCR** (requis par ocrmypdf) : `brew install tesseract` (macOS) / `apt install tesseract-ocr` (Linux)
- **Clé API Mistral** : [console.mistral.ai](https://console.mistral.ai)

## Installation & Démarrage

### 1. Variables d'environnement

Créer un fichier `.env` à la racine :

```env
MISTRAL_API_KEY=votre_clé_mistral
MISTRAL_MODEL=mistral-large-latest
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
TOP_K_RESULTS=5
MAX_CONCURRENT_LLM_CALLS=5
PARENT_CHUNK_SIZE=2048
PARENT_CHUNK_OVERLAP=256
CHILD_CHUNK_SIZE=512
CHILD_CHUNK_OVERLAP=64
```

### 2. Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate    # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

#### Ingestion des bases de connaissances

Placer les PDFs dans les dossiers correspondants sous `data/documents/`, puis :

```bash
# Base légale nationale
python -m scripts.ingest_legal

# Bases CESER (8 régions)
python -m scripts.ingest_cesers
```

Ces scripts génèrent des index FAISS + parent stores JSON dans `backend/faiss_indexes/`.

#### Lancer le serveur

```bash
uvicorn app.main:app --reload --port 8000
```

API disponible sur `http://localhost:8000` — documentation Swagger sur `/docs`.

### 3. Frontend

```bash
cd frontend
npm install --legacy-peer-deps
npm run dev
```

Application disponible sur `http://localhost:3000`.

## Pipeline RAG (5 étapes)

Le pipeline principal est dans `backend/app/services/rag_pipeline.py` :

| Étape | Description | Fichier prompt |
|-------|-------------|----------------|
| 1. Parsing | OCR + extraction texte via ocrmypdf/pdfplumber, segmentation en child chunks (512 tokens) | — |
| 2. Extraction | Identification des préconisations/positions fortes via Mistral, sortie JSON structurée | `EXTRACTION_SYSTEM_PROMPT` |
| 3. Recherche vectorielle | Recherche FAISS sur les child chunks, récupération des parent chunks (2048 tokens) via ParentDocument Retriever | — |
| 4. Validation & Scoring | Comparaison LLM entre chaque préconisation et les textes légaux. Score de réutilisation (0/1/2) + score de similarité (0-100%) | `VALIDATION_SYSTEM_PROMPT` |
| 5. Synthèse analytique | Génération d'un récapitulatif court + classification par catégorie thématique pour la dataviz | `SYNTHESIS_SYSTEM_PROMPT` |

### ParentDocument Retriever

Stratégie de chunking à deux niveaux :
- **Child chunks** (512 tokens, overlap 64) : indexés dans FAISS pour une recherche fine
- **Parent chunks** (2048 tokens, overlap 256) : stockés dans `parent_store.json`, renvoyés au LLM pour un contexte riche

Quand un child chunk matche, on remonte au parent chunk correspondant pour fournir plus de contexte au LLM lors de la validation.

## Endpoints API

| Méthode | Route | Description |
|---------|-------|-------------|
| `POST` | `/api/analysis/run` | Lance une analyse RAG (upload PDF via multipart) |
| `GET` | `/api/analysis/status/{task_id}` | Polling du statut (progress, results) |
| `POST` | `/api/chat/message` | Chatbot contextuel sur les résultats d'une analyse |
| `POST` | `/api/ingest/upload` | Ingestion d'un document unique |
| `POST` | `/api/ingest/batch` | Ingestion batch |
| `GET` | `/api/documents/databases` | Liste des bases de données disponibles |
| `GET` | `/api/documents/pdf/{filename}` | Sert un PDF pour affichage in-browser |
| `GET` | `/api/health` | Health check |

## Chatbot contextuel

Après une analyse, un assistant IA (icône en bas à droite) permet d'explorer les résultats en langage naturel. Il reçoit en contexte l'intégralité des résultats (préconisations, scores, textes légaux, synthèse, catégories) et répond uniquement à partir de ces données. Endpoint : `POST /api/chat/message` avec `task_id`, `message` et `history`.

## Régions CESER couvertes

Bretagne, Centre-Val de Loire, Grand Est, Hauts-de-France, La Réunion, Normandie, Nouvelle-Aquitaine, Pays de la Loire.

## Licence

MIT — voir [LICENSE](./LICENSE)
