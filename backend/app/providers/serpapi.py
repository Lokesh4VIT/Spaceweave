"""Primary product-search provider: SerpApi's Google Shopping engine.

Unlike the Amazon and Flipkart adapters in this package, this provider
needs no marketplace affiliate/associate approval -- only a SerpApi
account and API key -- so it is the one that reliably returns real,
current internet product results for every deployment, regardless of
whether Amazon/Flipkart access has been granted.

API reference: https://serpapi.com/google-shopping-api
"""
import httpx

from app.core.config import get_settings

SERPAPI_ENDPOINT = "https://serpapi.com/search.json"


def _extracted_price(item: dict) -> float | None:
    price = item.get("extracted_price")
    if isinstance(price, (int, float)):
        return float(price)
    return None


async def search_serpapi(query: str, max_price: float | None = None, max_results: int = 10):
    s = get_settings()
    if not (s.serpapi_enabled and s.serpapi_api_key and query):
        return []

    params = {
        "engine": "google_shopping",
        "q": query,
        "gl": s.serpapi_gl,
        "hl": s.serpapi_hl,
        "api_key": s.serpapi_api_key,
    }

    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.get(SERPAPI_ENDPOINT, params=params)
        r.raise_for_status()
        data = r.json()

    # SerpApi returns HTTP 200 with an "error" field for invalid queries,
    # bad api keys, and exhausted quota rather than a non-2xx status code.
    if data.get("error"):
        raise RuntimeError(f"SerpApi error: {data['error']}")

    out = []
    for item in (data.get("shopping_results") or []):
        price = _extracted_price(item)
        # Real price is never invented and never silently dropped to force
        # a budget match -- results with a price above budget are kept
        # here and left for the ranking/value-score layer to deprioritize.
        if max_price is not None and price is not None and price > max_price * 1.5:
            # Still skip results wildly outside budget so obviously
            # irrelevant listings (e.g. a mismatched accessory) don't
            # crowd out real candidates before ranking sees them.
            continue
        out.append({
            "product_id": str(item.get("product_id") or item.get("position") or ""),
            "title": item.get("title"),
            "price_inr": price,
            "currency": "INR" if s.serpapi_gl == "in" else None,
            "image_url": item.get("thumbnail"),
            "product_url": item.get("product_link") or item.get("link"),
            "source": item.get("source") or "Google Shopping",
            "description": item.get("snippet") or "",
            "rating": item.get("rating"),
            "review_count": item.get("reviews"),
        })
        if len(out) >= max_results:
            break

    return out
