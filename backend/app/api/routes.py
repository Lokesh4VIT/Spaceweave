from fastapi import APIRouter, File, Form, UploadFile, HTTPException
from app.services.search import run_search
from app.providers.flipkart import search_flipkart
from app.providers.amazon import search_amazon
from app.services.external_ranker import rank_external

router=APIRouter(prefix='/api/v1')

@router.get('/health')
async def health(): return {'status':'ok','service':'spaceweave-api'}

@router.post('/search')
async def search_endpoint(file: UploadFile=File(...), query: str=Form(''), category: str=Form(''), room_type: str=Form(''), max_budget: float|None=Form(None), available_width: float|None=Form(None), available_depth: float|None=Form(None), top_k: int=Form(8)):
    data=await file.read()
    if not data: raise HTTPException(400,'Empty image')
    if len(data)>10*1024*1024: raise HTTPException(413,'Image exceeds 10 MB limit')
    top_k=max(1,min(top_k,10))
    results,meta=run_search(data,query,category or None,max_budget,room_type or None,available_width,available_depth,top_k)
    # Marketplace adapters are supplemental candidates. They are not silently scraped.
    marketplace=[]
    if query or category:
        q=' '.join(x for x in [query,category.replace('_',' ')] if x)
        try: marketplace += await search_flipkart(q,10)
        except Exception as exc: meta['flipkart_error']=str(exc)
        try: marketplace += await search_amazon(q,max_budget,10)
        except Exception as exc: meta['amazon_error']=str(exc)
    live_ranked=[]
    if marketplace:
        try:
            live_ranked=await rank_external(marketplace,data,max_budget,available_width,available_depth,top_k)
        except Exception as exc:
            meta['live_ranking_error']=str(exc)
    meta['live_marketplace_candidates']=len(marketplace)
    meta['live_ranked_count']=len(live_ranked)
    # Merge local indexed catalog and live marketplace candidates, then take the strongest final scores.
    merged=results+live_ranked
    merged.sort(key=lambda x: x.get('final_score',0), reverse=True)
    return {'query':{'query':query,'category':category or None,'room_type':room_type or None,'max_budget':max_budget,'available_width':available_width,'available_depth':available_depth},'results':merged[:top_k],'metadata':meta}
