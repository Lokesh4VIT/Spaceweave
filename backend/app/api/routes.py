import logging
from io import BytesIO

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from PIL import Image, UnidentifiedImageError

from app.core.config import get_settings
from app.providers.amazon import search_amazon
from app.providers.flipkart import search_flipkart
from app.services.embedding import model as embedding_model
from app.services.external_ranker import rank_external
from app.services.search import run_search
from app.services.vector_store import client, ensure_collection

logger = logging.getLogger("spaceweave.api")
router = APIRouter(prefix="/api/v1")


@router.get("/health")
async def health():
    return {"status": "ok", "service": "spaceweave-api"}


@router.get("/ready")
async def ready():
    settings = get_settings()

    qdrant_error: str | None = None
    points = 0
    try:
        points = ensure_collection()
    except Exception as exc:
        logger.exception("Readiness check: Qdrant unavailable")
        qdrant_error = str(exc)

    # Loading the embedding model is the other hard dependency of /search —
    # check it here too so /ready can actually distinguish "Qdrant is the
    # problem" from "the CLIP model can't load", instead of both surfacing
    # as the same generic 503 from the search endpoint. This reuses the same
    # cached singleton search uses, so a warm instance reports instantly and
    # only a genuinely cold instance pays the load cost here.
    model_error: str | None = None
    try:
        await run_in_threadpool(embedding_model)
    except Exception as exc:
        logger.exception("Readiness check: embedding model failed to load")
        model_error = str(exc)

    overall_ready = qdrant_error is None and model_error is None and points > 0

    return {
        "status": "ready" if overall_ready else "not_ready",
        "qdrant": {
            "connected": qdrant_error is None,
            "collection": settings.qdrant_collection,
            "points": points,
            "error": qdrant_error,
        },
        "embedding_model": {
            "loaded": model_error is None,
            "name": settings.embedding_model,
            "error": model_error,
        },
    }


@router.post("/search")
async def search_endpoint(
    file: UploadFile = File(...),
    query: str = Form(""),
    category: str = Form(""),
    room_type: str = Form(""),
    max_budget: float | None = Form(None),
    available_width: float | None = Form(None),
    available_depth: float | None = Form(None),
    top_k: int = Form(8),
):
    settings = get_settings()

    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=415, detail="Please upload a JPEG, PNG, or WebP image.")

    if max_budget is not None and max_budget < 0:
        raise HTTPException(status_code=422, detail="max_budget must be non-negative.")
    if available_width is not None and available_width <= 0:
        raise HTTPException(status_code=422, detail="available_width must be greater than zero.")
    if available_depth is not None and available_depth <= 0:
        raise HTTPException(status_code=422, detail="available_depth must be greater than zero.")

    top_k = max(1, min(top_k, 10))
    data = await file.read()
    max_bytes = settings.max_upload_mb * 1024 * 1024
    if not data:
        raise HTTPException(status_code=400, detail="Empty image.")
    if len(data) > max_bytes:
        raise HTTPException(status_code=413, detail=f"Image exceeds {settings.max_upload_mb} MB limit.")

    try:
        with Image.open(BytesIO(data)) as image:
            image.verify()
    except (UnidentifiedImageError, OSError) as exc:
        raise HTTPException(status_code=415, detail="The uploaded file is not a valid image.") from exc

    try:
        results, meta = await run_in_threadpool(
            run_search,
            data,
            query.strip(),
            category.strip() or None,
            max_budget,
            room_type.strip() or None,
            available_width,
            available_depth,
            top_k,
        )
    except Exception as exc:
        logger.exception("Vector search failed")
        raise HTTPException(status_code=503, detail="Search service is temporarily unavailable.") from exc

    marketplace = []
    if query.strip() or category.strip():
        search_query = " ".join(
            part for part in [query.strip(), category.strip().replace("_", " ")] if part
        )
        try:
            marketplace += await search_flipkart(search_query, 10)
        except Exception:
            logger.exception("Flipkart provider failed")
        try:
            marketplace += await search_amazon(search_query, max_budget, 10)
        except Exception:
            logger.exception("Amazon provider failed")

    live_ranked = []
    if marketplace:
        try:
            live_ranked = await rank_external(
                marketplace,
                data,
                max_budget,
                available_width,
                available_depth,
                top_k,
            )
        except Exception:
            logger.exception("Live marketplace ranking failed")

    meta["live_marketplace_candidates"] = len(marketplace)
    meta["live_ranked_count"] = len(live_ranked)

    merged = results + live_ranked
    merged.sort(key=lambda item: item.get("final_score", 0), reverse=True)

    return {
        "query": {
            "query": query,
            "category": category or None,
            "room_type": room_type or None,
            "max_budget": max_budget,
            "available_width": available_width,
            "available_depth": available_depth,
        },
        "results": merged[:top_k],
        "metadata": meta,
    }
