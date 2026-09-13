from functools import lru_cache
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from app.core.config import get_settings
from app.services.catalog import load_catalog
from app.services.embedding import embed_text, embed_image_url, fused_product_embedding

@lru_cache(maxsize=1)
def client():
    s=get_settings(); return QdrantClient(url=s.qdrant_url)

def ensure_collection():
    s=get_settings(); c=client()
    existing=[x.name for x in c.get_collections().collections]
    if s.qdrant_collection not in existing:
        c.create_collection(s.qdrant_collection, vectors_config=VectorParams(size=s.embedding_dim, distance=Distance.COSINE))
        return seed_collection()
    info=c.get_collection(s.qdrant_collection)
    if getattr(info,'points_count',0)==0: return seed_collection()
    return info.points_count

def seed_collection():
    s=get_settings(); c=client(); products=load_catalog(); points=[]; cache={}
    for idx,p in enumerate(products):
        url=p.get('image_url')
        if url not in cache: cache[url]=embed_image_url(url)
        image_vec=cache[url]
        text=f"{p['title']}. {p['description']}. {p['category']}. {p['style']} {p['material']} {p['color']}."
        text_vec=embed_text(text)
        # Prefer product-image semantics, with text adding structured style/category context.
        vec=fused_product_embedding(image_vec,text_vec) if image_vec else text_vec
        payload=dict(p); payload['embedding_source']='product_image+metadata_text' if image_vec else 'metadata_text_fallback'
        points.append(PointStruct(id=idx+1,vector=vec,payload=payload))
        if len(points)>=64:
            c.upsert(s.qdrant_collection,points=points); points=[]
    if points: c.upsert(s.qdrant_collection,points=points)
    return len(products)

def search(vector,limit,category=None,max_budget=None,room_type=None):
    s=get_settings(); ensure_collection()
    must=[]
    from qdrant_client.models import FieldCondition,MatchValue,Range
    if category: must.append(FieldCondition(key='category',match=MatchValue(value=category)))
    if max_budget is not None: must.append(FieldCondition(key='price_inr',range=Range(lte=max_budget)))
    if room_type: must.append(FieldCondition(key='room_types',match=MatchValue(value=room_type)))
    filt={'must':must} if must else None
    return client().search(collection_name=s.qdrant_collection,query_vector=vector,query_filter=filt,limit=limit,with_payload=True)
