# SpaceWeave AI V2

**AI-powered visual product retrieval + spatial fit ranking for furniture and home products.**

## What the project actually does

1. User uploads a room/furniture photo.
2. User chooses a target such as sofa, dining table, dining chair, bed, stove/hob, desk, etc.
3. User sets a maximum budget.
4. User can provide the available placement width/depth. SpaceWeave never invents centimeter measurements from a single uncalibrated image.
5. The backend embeds the uploaded image with a CLIP image encoder.
6. Qdrant performs vector nearest-neighbor retrieval over the product catalog.
7. Hard filters remove products outside category, budget or room constraints.
8. A ranking layer combines visual similarity, spatial fit, quality/reviews and value.
9. The UI returns the top 5/8/10 products with dimensions, price, fit reason and product link.

## Marketplace reality

The architecture includes **server-side Amazon Creators API and Flipkart Affiliate API adapters**. They are intentionally disabled by default because credentials/affiliate access belong in server environment variables, never in GitHub Pages JavaScript.

The demo catalog is included so the project works immediately without credentials. When legitimate marketplace credentials are added, live candidates can be retrieved and the same ranking pipeline can be extended to them.

There is deliberately **no web scraping** of Amazon, Flipkart, Google or ChatGPT. A universal free API that legally exposes every marketplace's live inventory does not exist. The project uses official marketplace APIs where access is available and a local catalog fallback otherwise.

## Spatial limitation

A single RGB photo without a known scale cannot reliably produce centimeter-accurate room dimensions. Production SpaceWeave should therefore use one of:
- user-provided available width/depth;
- a known reference object;
- AR/LiDAR/depth data;
- calibrated multi-view capture.

This V2 implements the first option and the ranking engine is ready for automatic spatial measurements later.

## Stack

- FastAPI
- Qdrant vector database
- Sentence-Transformers CLIP (`sentence-transformers/clip-ViT-B-32`)
- Pillow
- HTTPX
- Vanilla HTML/CSS/JS frontend
- Docker Compose
- GitHub Actions
- Optional Amazon Creators API + Flipkart Affiliate API

## Run locally

### 1. Start Qdrant

```bash
docker compose up -d qdrant
```

### 2. Create a Python environment

```bash
python -m venv .venv
# Windows PowerShell
.venv\\Scripts\\Activate.ps1
pip install -r backend/requirements.txt
```

### 3. Start API

```bash
$env:PYTHONPATH="backend"
uvicorn app.main:app --reload --port 8000
```

Open `http://localhost:8000`.

The first search downloads the CLIP model from Hugging Face. It is cached locally afterward.

## Docker

```bash
docker compose up --build
```

The first container startup may take time because the CLIP model is downloaded and cached by the backend.

## Enable Flipkart

Set in `.env`:

```text
FLIPKART_ENABLED=true
FLIPKART_AFFILIATE_ID=...
FLIPKART_AFFILIATE_TOKEN=...
```

The adapter uses the official Flipkart Affiliate search endpoint and never scrapes product pages.

## Enable Amazon India

Amazon's current Creators API requires Amazon Associates enrollment and approved API access. Configure:

```text
AMAZON_ENABLED=true
AMAZON_CLIENT_ID=...
AMAZON_CLIENT_SECRET=...
AMAZON_REFRESH_TOKEN=...
AMAZON_PARTNER_TAG=...
AMAZON_MARKETPLACE=www.amazon.in
```

The backend obtains a server-side access token and calls `SearchItems`.

## Production evolution

The next engineering stages are:

- object detection/segmentation for furniture and free-space zones;
- calibrated depth/AR measurement;
- ingestion workers for marketplace feeds;
- image embeddings for every live product image;
- PostgreSQL for normalized product/merchant data;
- Qdrant payload filters + ANN retrieval at large scale;
- reranker trained on click/purchase feedback;
- review-quality/NLP scoring;
- product-in-room visualization;
- cache, rate limiting, observability and background indexing.

The important design point is that marketplace connectors are **data sources**, while multimodal retrieval + spatial ranking is the SpaceWeave intelligence layer.
