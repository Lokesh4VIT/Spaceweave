# SpaceWeave AI V2

**AI-powered visual product retrieval + spatial fit ranking for furniture and home products.**

## Production deployment target

SpaceWeave is configured for **Vercel + Qdrant Cloud**.

- **Vercel** runs the FastAPI application and serves the frontend.
- **Qdrant Cloud** stores the persistent product vectors and metadata.
- The catalog is indexed **once**, outside the request path. Vercel never embeds all catalog products during a cold start.
- Marketplace credentials are server-side environment variables and live marketplace adapters are opt-in.
- There is no Amazon, Flipkart, Google, or other marketplace scraping.

Vercel supports FastAPI directly and also supports root-level `Dockerfile.vercel` container functions. This project uses the container path because the CLIP/PyTorch runtime is substantially larger than a minimal Python API.

## What the project actually does

1. User uploads a room/furniture photo.
2. User chooses a target such as sofa, dining table, dining chair, bed, stove/hob, desk, etc.
3. User sets a maximum budget.
4. User can provide the available placement width/depth. SpaceWeave never invents centimeter measurements from a single uncalibrated image.
5. The backend embeds the uploaded image with a CLIP image encoder.
6. Optional natural-language preferences are blended into the CLIP query vector.
7. Qdrant performs vector nearest-neighbor retrieval over the indexed product catalog.
8. Hard filters remove products outside category, budget or room constraints.
9. A ranking layer combines visual similarity, spatial fit, quality/reviews and value.
10. The UI returns the strongest results with dimensions, price, fit reason and product link.

## Important production limitation

The included catalog is a **demo catalog**. Its product images are public image URLs and its product URLs are placeholders. It is not a live Amazon/Flipkart inventory feed.

For real marketplace results, configure an authorized Amazon Creators API and/or Flipkart Affiliate API integration. Do not scrape marketplaces or place credentials in frontend code.

A single RGB photo without a known scale cannot reliably produce centimeter-accurate room dimensions. Production SpaceWeave should use user-provided measurements, a known reference object, AR/LiDAR/depth data, or calibrated multi-view capture.

## Architecture

```text
Browser
   │
   ▼
Vercel Container Function
   │
   ├── FastAPI API
   ├── CLIP image/text embedding
   ├── spatial + quality + value ranking
   └── marketplace adapters (optional)
          │
          ▼
     Qdrant Cloud
     product vectors + metadata
```

## Vercel deployment

### 1. Connect the GitHub repository

Import `Lokesh4VIT/Spaceweave` into Vercel and deploy from the repository root.

Do **not** set a Root Directory such as `backend/`.

Vercel detects the root `Dockerfile.vercel` and builds the container as a Vercel Function.

### 2. Add environment variables in Vercel

Required:

```text
QDRANT_URL=https://your-qdrant-cluster...
QDRANT_API_KEY=your-secret-key
QDRANT_COLLECTION=spaceweave_products
EMBEDDING_MODEL=sentence-transformers/clip-ViT-B-32
EMBEDDING_DIM=512
CANDIDATE_K=120
DEFAULT_TOP_K=8
SPATIAL_CLEARANCE_CM=10
MAX_UPLOAD_MB=10
SEED_CATALOG=false
```

Keep `QDRANT_API_KEY` secret. Never commit it to GitHub or frontend JavaScript.

Optional marketplace variables remain disabled unless valid authorized credentials are available.

### 3. Seed Qdrant once

The Vercel application intentionally does **not** seed 500 products during a request or cold start.

From a local clone:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt
```

Create `.env` from `.env.example` and set:

```text
QDRANT_URL=https://your-qdrant-cluster...
QDRANT_API_KEY=your-secret-key
SEED_CATALOG=false
```

Then run:

```powershell
python scripts/seed_qdrant.py
```

The script downloads the catalog images, creates CLIP embeddings, and uploads the vectors to Qdrant. This is a one-time indexing operation. Re-running it intentionally reuses the same collection and point IDs.

### 4. Verify after deployment

Open:

```text
https://YOUR-VERCEL-DOMAIN/api/v1/health
https://YOUR-VERCEL-DOMAIN/api/v1/ready
```

`/health` confirms the API process is alive.

`/ready` confirms Qdrant connectivity and reports the number of indexed points. Search should only be considered ready when the point count is greater than zero.

Interactive API documentation is available at:

```text
https://YOUR-VERCEL-DOMAIN/docs
```

## Local development

Start Qdrant:

```bash
docker compose up -d qdrant
```

Create an environment and install dependencies:

```bash
python -m venv .venv
# Windows PowerShell
.venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt
```

Start the API:

```powershell
$env:PYTHONPATH="backend"
uvicorn app.main:app --reload --port 8000
```

Open `http://localhost:8000`.

For local Qdrant indexing:

```powershell
python scripts/seed_qdrant.py
```

## Testing

```bash
pytest -q tests/test_spatial.py tests/test_api.py
```

The test suite deliberately does not invoke the CLIP model or seed Qdrant.

## Marketplace integrations

The architecture includes server-side adapters for:

- Amazon Creators API
- Flipkart Affiliate API

They are disabled by default. Authorized credentials must be configured in Vercel environment variables.

## Current V2 scope

Implemented:

- room/product image upload
- CLIP multimodal retrieval
- Qdrant vector search
- category, budget and room filters
- optional natural-language query fusion
- spatial fit using supplied width/depth
- quality/review scoring
- value scoring
- optional authorized marketplace adapters
- server-side secret handling
- production request validation and safe error responses
- Vercel deployment configuration
- one-time external catalog indexing

Not implemented yet:

- automatic centimeter measurement from an uncalibrated RGB image
- segmentation/depth/AR placement
- true product-in-room compositing
- trained click/purchase reranker
- real-time universal web shopping search
- production database for normalized merchant/catalog records

Those are separate engineering stages and should not be claimed as current functionality.
