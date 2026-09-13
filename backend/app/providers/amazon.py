import httpx
from app.core.config import get_settings

async def _token():
    s=get_settings()
    async with httpx.AsyncClient(timeout=20) as client:
        r=await client.post(s.amazon_token_url,data={'grant_type':'refresh_token','refresh_token':s.amazon_refresh_token,'client_id':s.amazon_client_id,'client_secret':s.amazon_client_secret})
        r.raise_for_status(); return r.json()['access_token']

async def search_amazon(query: str, max_price: float|None=None, max_results: int=10):
    s=get_settings()
    required=[s.amazon_enabled,s.amazon_client_id,s.amazon_client_secret,s.amazon_refresh_token,s.amazon_partner_tag]
    if not all(required): return []
    token=await _token()
    payload={'keywords':query,'partnerTag':s.amazon_partner_tag,'partnerType':'Associates','marketplace':s.amazon_marketplace,'itemCount':min(max_results,10),'resources':['images.primary.large','itemInfo.title','itemInfo.features','offersV2.listings.price','itemInfo.productInfo']}
    if max_price is not None: payload['maxPrice']=int(max_price*100)
    async with httpx.AsyncClient(timeout=25) as client:
        r=await client.post('https://creatorsapi.amazon/catalog/v1/searchItems',json=payload,headers={'Authorization':f'Bearer {token}','Content-Type':'application/json','x-marketplace':s.amazon_marketplace})
        r.raise_for_status(); data=r.json()
    out=[]
    for item in data.get('searchResult',{}).get('items',[]):
        listings=(item.get('offersV2',{}).get('listings') or [])
        price=(listings[0].get('price',{}).get('amount') if listings else None)
        imgs=item.get('images',{}).get('primary',{}); img=imgs.get('large',{}).get('url') or imgs.get('medium',{}).get('url')
        out.append({'product_id':item.get('asin'),'title':item.get('itemInfo',{}).get('title',{}).get('displayValue'),'price_inr':price,'currency':'INR','image_url':img,'product_url':item.get('detailPageURL'),'source':'Amazon India','description':' '.join(item.get('itemInfo',{}).get('features',{}).get('displayValues',[]) or [])})
    return out
