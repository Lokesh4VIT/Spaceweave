"""Secondary product-search provider: Flipkart Affiliate API.

Requires an approved Flipkart affiliate account (Fk-Affiliate-Id /
Fk-Affiliate-Token). The adapter uses the official Search Query based on
Keywords endpoint and never scrapes product pages. Unlike the previous
version of this file, budget is now actually enforced client-side --
previously max_price was accepted nowhere in the call chain and every
Flipkart result was returned regardless of the user's budget.
"""
import httpx

from app.core.config import get_settings

SEARCH_URL = "https://affiliate-api.flipkart.net/affiliate/1.0/search/json"


async def search_flipkart(query: str, max_price: float | None = None, max_results: int = 10):
    s = get_settings()
    if not (s.flipkart_enabled and s.flipkart_affiliate_id and s.flipkart_affiliate_token):
        return []

    headers = {
        "Fk-Affiliate-Id": s.flipkart_affiliate_id,
        "Fk-Affiliate-Token": s.flipkart_affiliate_token,
    }
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.get(
            SEARCH_URL,
            params={"query": query, "resultCount": min(max_results, 10)},
            headers=headers,
        )
        r.raise_for_status()
        data = r.json()

    out = []
    for item in data.get("productInfoList", []):
        b = (item.get("productBaseInfoV1") or {})
        a = b.get("productAttributes") or {}
        prices = a.get("sellingPrice") or {}
        images = b.get("imageUrls") or {}
        price = prices.get("amount")
        if max_price is not None and price is not None and price > max_price:
            continue
        out.append({
            "product_id": b.get("productId"),
            "title": b.get("title"),
            "price_inr": price,
            "currency": "INR",
            "image_url": images.get("400x400") or images.get("200x200"),
            "product_url": b.get("productUrl"),
            "source": "Flipkart",
            "description": b.get("productDescription", ""),
        })
        if len(out) >= max_results:
            break

    return out
