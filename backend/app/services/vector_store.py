from functools import lru_cache

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

from app.core.config import get_settings
from app.services.catalog import load_catalog
from app.services.embedding import embed_text, embed_image_url, fused_product_embedding


@lru_cache(maxsize=1)
def client() -> QdrantClient:
    s = get_settings()
    return QdrantClient(url=s.qdrant_url, api_key=s.qdrant_api_key)


def ensure_collection() -> int:
    """Ensure the collection exists without doing expensive indexing in a request."""
    s = get_settings()
    c = client()

    if not c.collection_exists(s.qdrant_collection):
        c.create_collection(
            s.qdrant_collection,
            vectors_config=VectorParams(size=s.embedding_dim, distance=Distance.COSINE),
        )

    info = c.get_collection(s.qdrant_collection)
    points = int(getattr(info, "points_count", 0) or 0)
    if points == 0 and s.seed_catalog:
        return seed_collection()
    return points


def seed_collection() -> int:
    """One-time catalog indexing command. Do not run this from a user request in production."""
    s = get_settings()
    c = client()
    products = load_catalog()
    points: list[PointStruct] = []
    image_cache: dict[str, list[float] | None] = {}

    if not c.collection_exists(s.qdrant_collection):
        c.create_collection(
            s.qdrant_collection,
            vectors_config=VectorParams(size=s.embedding_dim, distance=Distance.COSINE),
        )

    for idx, product in enumerate(products):
        url = product.get("image_url")
        if url not in image_cache:
            image_cache[url] = embed_image_url(url)
        image_vec = image_cache[url]
        text = (
            f"{product['title']}. {product['description']}. {product['category']}. "
            f"{product['style']} {product['material']} {product['color']}."
        )
        text_vec = embed_text(text)
        vec = fused_product_embedding(image_vec, text_vec) if image_vec else text_vec
        payload = dict(product)
        payload["embedding_source"] = (
            "product_image+metadata_text" if image_vec else "metadata_text_fallback"
        )
        points.append(PointStruct(id=idx + 1, vector=vec, payload=payload))

        if len(points) >= 64:
            c.upsert(s.qdrant_collection, points=points)
            points = []

    if points:
        c.upsert(s.qdrant_collection, points=points)

    return len(products)


def search(vector: list[float], limit: int, category=None, max_budget=None, room_type=None):
    s = get_settings()
    ensure_collection()

    from qdrant_client.models import FieldCondition, MatchValue, Range

    must = []
    if category:
        must.append(FieldCondition(key="category", match=MatchValue(value=category)))
    if max_budget is not None:
        must.append(FieldCondition(key="price_inr", range=Range(lte=max_budget)))
    if room_type:
        must.append(FieldCondition(key="room_types", match=MatchValue(value=room_type)))

    filt = {"must": must} if must else None
    return client().search(
        collection_name=s.qdrant_collection,
        query_vector=vector,
        query_filter=filt,
        limit=limit,
        with_payload=True,
    )
