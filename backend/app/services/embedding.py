from functools import lru_cache
from io import BytesIO
import numpy as np
import httpx
from PIL import Image
from sentence_transformers import SentenceTransformer

@lru_cache(maxsize=1)
def model():
    return SentenceTransformer("sentence-transformers/clip-ViT-B-32", device="cpu")

def embed_image(data: bytes) -> list[float]:
    image=Image.open(BytesIO(data)).convert("RGB")
    v=model().encode(image, normalize_embeddings=True, convert_to_numpy=True)
    return v.astype(np.float32).tolist()

def embed_image_url(url: str) -> list[float] | None:
    try:
        r=httpx.get(url,timeout=20,follow_redirects=True)
        r.raise_for_status()
        return embed_image(r.content)
    except Exception:
        return None

def embed_text(text: str) -> list[float]:
    v=model().encode(text, normalize_embeddings=True, convert_to_numpy=True)
    return v.astype(np.float32).tolist()

def fused_product_embedding(image_vector, text_vector, image_weight=.75):
    a=np.asarray(image_vector,dtype=np.float32); b=np.asarray(text_vector,dtype=np.float32)
    v=image_weight*a+(1-image_weight)*b
    v=v/(np.linalg.norm(v) or 1.0)
    return v.astype(np.float32).tolist()
