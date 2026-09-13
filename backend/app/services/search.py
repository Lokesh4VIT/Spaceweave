from app.services.embedding import embed_image
from app.services.vector_store import search
from app.services.spatial import spatial_score, quality_score, value_score
from app.core.config import get_settings

def run_search(image_bytes, query, category, max_budget, room_type, available_width, available_depth, top_k):
    s=get_settings(); vector=embed_image(image_bytes)
    hits=search(vector, s.candidate_k, category, max_budget, room_type)
    ranked=[]
    for hit in hits:
        p=hit.payload
        sp, reason=spatial_score(p.get('width_cm'),p.get('depth_cm'),available_width,available_depth,s.spatial_clearance_cm)
        if (available_width or available_depth) and sp == 0: continue
        sim=max(0.0,min(1.0,(float(hit.score)+1)/2))
        qs=quality_score(p.get('rating'),p.get('review_count'))
        vs=value_score(p.get('price_inr'),max_budget)
        final=0.55*sim+0.20*sp+0.15*qs+0.10*vs
        ranked.append((final,sim,sp,qs,vs,reason,p))
    ranked.sort(key=lambda x:x[0], reverse=True)
    results=[]
    for final,sim,sp,qs,vs,reason,p in ranked[:top_k]:
        results.append({**{k:p.get(k) for k in ['product_id','title','category','price_inr','currency','width_cm','depth_cm','height_cm','rating','review_count','image_url','product_url','source']},
                        'similarity_score':round(sim,4),'spatial_fit_score':round(sp,4),'quality_score':round(qs,4),'value_score':round(vs,4),'final_score':round(final,4),
                        'fit_status':'good_fit' if sp>=0.85 else 'acceptable_fit','fit_reason':reason})
    return results, {'candidate_count':len(hits),'result_count':len(results),'embedding_dim':s.embedding_dim,'vector_store':'Qdrant','model':s.embedding_model,'ranking':'0.55 visual + 0.20 spatial + 0.15 quality + 0.10 value','marketplace_status':'Demo catalog unless marketplace adapters are enabled'}
