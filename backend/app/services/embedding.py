from functools import lru_cache
from io import BytesIO

import httpx
import numpy as np
from PIL import Image
from app.core.config import get_settings


@lru_cache(maxsize=1)
def model():
    # Lazy import keeps health/readiness endpoints lightweight and lets the API boot
    # before the ML runtime is first needed.
    from sentence_transformers import SentenceTransformer

    settings = get_settings()
    return SentenceTransformer(settings.embedding_model, device="cpu")


def embed_image(data: bytes) -> list[float]:
    image = Image.open(BytesIO(data)).convert("RGB")
    vector = model().encode(image, normalize_embeddings=True, convert_to_numpy=True)
    return vector.astype(np.float32).tolist()


def embed_image_url(url: str) -> list[float] | None:
    if not url:
        return None
    try:
        response = httpx.get(url, timeout=20, follow_redirects=True)
        response.raise_for_status()
        return embed_image(response.content)
    except Exception:
        return None


def embed_text(text: str) -> list[float]:
    vector = model().encode(text, normalize_embeddings=True, convert_to_numpy=True)
    return vector.astype(np.float32).tolist()


def fused_product_embedding(
    image_vector: list[float] | None,
    text_vector: list[float],
    image_weight: float = 0.75,
) -> list[float]:
    if not image_vector:
        return text_vector
    a = np.asarray(image_vector, dtype=np.float32)
    b = np.asarray(text_vector, dtype=np.float32)
    vector = image_weight * a + (1 - image_weight) * b
    vector = vector / (np.linalg.norm(vector) or 1.0)
    return vector.astype(np.float32).tolist()
