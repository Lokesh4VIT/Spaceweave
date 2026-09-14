"""Tertiary product-search provider: Amazon Creators API.

Amazon retired PA-API 5.0 on 2026-05-15 in favor of the Creators API
(https://affiliate-program.amazon.com/creatorsapi/docs). The two are not
wire-compatible: Creators API uses OAuth2 client-credentials + Bearer
tokens instead of AWS SigV4, and Amazon requires an approved Associates
account with at least 10 qualifying referred sales in the trailing 30
days before it grants Creators API access at all. Because of that,
getting zero results here is an expected, common outcome -- not a bug --
for any account that isn't already an established, active affiliate.
"""
import httpx

from app.core.config import get_settings

CREATORS_API_SCOPE = "creatorsapi::default"
CREATORS_API_SEARCH_URL = "https://creatorsapi.amazon/catalog/v1/searchItems"


async def _token(s) -> str:
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.post(
            s.amazon_token_url,
            json={
                "grant_type": "client_credentials",
                "client_id": s.amazon_client_id,
                "client_secret": s.amazon_client_secret,
                "scope": CREATORS_API_SCOPE,
            },
            headers={"Content-Type": "application/json"},
        )
        r.raise_for_status()
        return r.json()["access_token"]


async def search_amazon(query: str, max_price: float | None = None, max_results: int = 10):
    s = get_settings()
    required = [s.amazon_enabled, s.amazon_client_id, s.amazon_client_secret, s.amazon_partner_tag]
    if not all(required):
        return []

    token = await _token(s)
    payload = {
        "keywords": query,
        "partnerTag": s.amazon_partner_tag,
        "marketplace": s.amazon_marketplace,
        "resources": [
            "images.primary.large",
            "itemInfo.title",
            "itemInfo.features",
            "offersV2.listings.price",
        ],
    }
    async with httpx.AsyncClient(timeout=25) as client:
        r = await client.post(
            CREATORS_API_SEARCH_URL,
            json=payload,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "x-marketplace": s.amazon_marketplace,
            },
        )
        r.raise_for_status()
        data = r.json()

    out = []
    for item in data.get("searchResult", {}).get("items", []):
        listings = (item.get("offersV2", {}) or {}).get("listings") or []
        price = listings[0].get("price", {}).get("amount") if listings else None
        if max_price is not None and price is not None and price > max_price:
            continue
        imgs = (item.get("images", {}) or {}).get("primary", {}) or {}
        img = imgs.get("large", {}).get("url") or imgs.get("medium", {}).get("url")
        item_info = item.get("itemInfo", {}) or {}
        out.append({
            "product_id": item.get("asin"),
            "title": (item_info.get("title") or {}).get("displayValue"),
            "price_inr": price,
            "currency": "INR",
            "image_url": img,
            "product_url": item.get("detailPageURL"),
            "source": "Amazon India",
            "description": " ".join((item_info.get("features") or {}).get("displayValues", []) or []),
        })
        if len(out) >= max_results:
            break

    return out
