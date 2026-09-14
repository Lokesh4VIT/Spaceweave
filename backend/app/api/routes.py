import logging
from io import BytesIO

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from PIL import Image, UnidentifiedImageError

from app.core.config import get_settings
from app.providers.amazon import search_amazon
from app.providers.flipkart import search_flipkart
from app.providers.serpapi import search_serpapi
from app.services.embedding import model as embedding_model
from app.services.external_ranker import rank_external
from app.services.search import run_search
from app.services.vector_store import client, ensure_collection

logger = logging.getLogger("spaceweave.api")
router = APIRouter(prefix="/api/v1")

# Stop calling further live-search providers once we already have this many
# marketplace candidates. Keeps latency/cost down on the common case where
# the primary provider alone is enough, while still falling back when it
# isn't (see PROVIDER_CHAIN below).
MIN_LIVE_RESULTS = 5

# Ordered primary -> secondary -> tertiary. SerpApi is first because it is
# the only one of the three that works for every deployment without a
# marketplace affiliate/associate approval process; Flipkart and Amazon are
# real official adapters but legitimately return [] until that approval is
# in place (see the docstrings in their modules).
PROVIDER_CHAIN = (
    ("serpapi", search_serpapi),
    ("flipkart", search_flipkart),
    ("amazon", search_amazon),
)


def _normalize_key(product: dict):
    url = (product.get("product_url") or "").split("?")[0].strip().lower()
    if url:
        return ("url", url)
    title = " ".join((product.get("title") or "").strip().lower().split())
    price = product.get("price_inr")
    price_bucket = round(price / 50) * 50 if isinstance(price, (int, float)) else None
    return ("title", title[:60], price_bucket, product.get("source"))


def _dedupe(products: list[dict]) -> list[dict]:
    seen = set()
    out = []
    for p in products:
        key = _normalize_key(p)
        if key in seen:
            continue
        seen.add(key)
        out.append(p)
    return out


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
        "live_search_providers": {
            "serpapi": settings.serpapi_enabled and bool(settings.serpapi_api_key),
            "flipkart": settings.flipkart_enabled and bool(settings.flipkart_affiliate_id),
            "amazon": settings.amazon_enabled and bool(settings.amazon_client_id),
        },
    }


async def _run_live_search(search_query: str, max_budget: float | None) -> tuple[list[dict], dict]:
    """Sequential fallback across providers, stopping once results are
    sufficient. Every provider call is isolated: a failure or empty result
    from one never blocks the next, and nothing here ever fabricates a
    product -- only what a provider actually returned is kept.
    """
    marketplace: list[dict] = []
    provider_status: dict[str, str] = {}

    for name, provider in PROVIDER_CHAIN:
        if len(marketplace) >= MIN_LIVE_RESULTS:
            provider_status[name] = "skipped_sufficient_results"
            continue
        try:
            results = await provider(search_query, max_budget, 10)
            provider_status[name] = f"ok:{len(results)}"
            marketplace += results
        except Exception:
            logger.exception("%s provider failed", name)
            provider_status[name] = "error"

    return _dedupe(marketplace), provider_status


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

    marketplace: list[dict] = []
    provider_status: dict[str, str] = {}
    if query.strip() or category.strip():
        search_query = " ".join(
            part for part in [query.strip(), category.strip().replace("_", " ")] if part
        )
        marketplace, provider_status = await _run_live_search(search_query, max_budget)

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
    meta["live_search_providers"] = provider_status

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
