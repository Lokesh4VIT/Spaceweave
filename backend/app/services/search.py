from app.core.config import get_settings
from app.services.embedding import embed_image, embed_text, fused_product_embedding
from app.services.spatial import spatial_score, quality_score, value_score
from app.services.vector_store import search


def run_search(image_bytes, query, category, max_budget, room_type, available_width, available_depth, top_k):
    settings = get_settings()
    image_vector = embed_image(image_bytes)
    vector = image_vector

    # CLIP text is optional. When supplied, blend it with the room image so
    # natural-language preferences affect local vector retrieval as well.
    if query:
        text_vector = embed_text(query)
        vector = fused_product_embedding(image_vector, text_vector, image_weight=0.80)

    hits = search(vector, settings.candidate_k, category, max_budget, room_type)
    ranked = []

    for hit in hits:
        product = hit.payload or {}
        spatial, reason = spatial_score(
            product.get("width_cm"),
            product.get("depth_cm"),
            available_width,
            available_depth,
            settings.spatial_clearance_cm,
        )
        if (available_width or available_depth) and spatial == 0:
            continue

        similarity = max(0.0, min(1.0, (float(hit.score) + 1) / 2))
        quality = quality_score(product.get("rating"), product.get("review_count"))
        value = value_score(product.get("price_inr"), max_budget)
        final = 0.55 * similarity + 0.20 * spatial + 0.15 * quality + 0.10 * value
        ranked.append((final, similarity, spatial, quality, value, reason, product))

    ranked.sort(key=lambda item: item[0], reverse=True)
    results = []
    fields = [
        "product_id", "title", "category", "price_inr", "currency",
        "width_cm", "depth_cm", "height_cm", "rating", "review_count",
        "image_url", "product_url", "source",
    ]

    for final, similarity, spatial, quality, value, reason, product in ranked[:top_k]:
        results.append({
            **{key: product.get(key) for key in fields},
            "similarity_score": round(similarity, 4),
            "spatial_fit_score": round(spatial, 4),
            "quality_score": round(quality, 4),
            "value_score": round(value, 4),
            "final_score": round(final, 4),
            "fit_status": "good_fit" if spatial >= 0.85 else "acceptable_fit",
            "fit_reason": reason,
        })

    return results, {
        "candidate_count": len(hits),
        "result_count": len(results),
        "embedding_dim": settings.embedding_dim,
        "vector_store": "Qdrant",
        "model": settings.embedding_model,
        "ranking": "0.55 visual + 0.20 spatial + 0.15 quality + 0.10 value",
        "marketplace_status": "Demo catalog unless marketplace adapters are enabled",
    }
