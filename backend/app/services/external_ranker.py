import asyncio
from io import BytesIO
import httpx
from PIL import Image
import numpy as np
from app.services.embedding import model
from app.services.spatial import spatial_score, quality_score, value_score
from app.core.config import get_settings

async def fetch_image(url: str):
    if not url: return None
    try:
        async with httpx.AsyncClient(timeout=12, follow_redirects=True) as client:
            r=await client.get(url)
            r.raise_for_status()
            return Image.open(BytesIO(r.content)).convert('RGB')
    except Exception:
        return None

async def rank_external(products, room_image, max_budget, available_width, available_depth, top_k):
    if not products: return []
    mdl=model()
    room=Image.open(BytesIO(room_image)).convert('RGB')
    room_vec=mdl.encode(room, normalize_embeddings=True, convert_to_numpy=True)
    images=await asyncio.gather(*(fetch_image(p.get('image_url')) for p in products[:30]))
    valid=[(p,img) for p,img in zip(products[:30],images) if img is not None]
    if not valid: return products[:top_k]
    img_vecs=mdl.encode([img for _,img in valid], normalize_embeddings=True, convert_to_numpy=True, batch_size=8)
    scores=img_vecs @ room_vec
    s=get_settings(); ranked=[]
    for (p,_),sim in zip(valid,scores):
        price=p.get('price_inr')
        sp,reason=spatial_score(p.get('width_cm'),p.get('depth_cm'),available_width,available_depth,s.spatial_clearance_cm)
        if (available_width or available_depth) and sp==0: continue
        qs=quality_score(p.get('rating'),p.get('review_count'))
        vs=value_score(price,max_budget)
        final=.55*float((sim+1)/2)+.20*sp+.15*qs+.10*vs
        ranked.append((final,p,reason,float((sim+1)/2),sp,qs,vs))
    ranked.sort(reverse=True,key=lambda x:x[0])
    out=[]
    for final,p,reason,sim,sp,qs,vs in ranked[:top_k]:
        out.append({**p,'similarity_score':round(sim,4),'spatial_fit_score':round(sp,4),'quality_score':round(qs,4),'value_score':round(vs,4),'final_score':round(final,4),'fit_status':'good_fit' if sp>=.85 else 'acceptable_fit','fit_reason':reason})
    return out
