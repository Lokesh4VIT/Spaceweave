import httpx
from app.core.config import get_settings

async def search_flipkart(query: str, max_results: int=10):
    s=get_settings()
    if not (s.flipkart_enabled and s.flipkart_affiliate_id and s.flipkart_affiliate_token):
        return []
    url='https://affiliate-api.flipkart.net/affiliate/1.0/search/json'
    headers={'Fk-Affiliate-Id':s.flipkart_affiliate_id,'Fk-Affiliate-Token':s.flipkart_affiliate_token}
    async with httpx.AsyncClient(timeout=20) as client:
        r=await client.get(url,params={'query':query,'resultCount':min(max_results,10)},headers=headers)
        r.raise_for_status(); data=r.json()
    out=[]
    for item in data.get('productInfoList',[]):
        b=item.get('productBaseInfoV1',{})
        a=b.get('productAttributes',{}) or {}
        prices=a.get('sellingPrice',{}) or {}
        images=b.get('imageUrls',{}) or {}
        out.append({'product_id':b.get('productId'),'title':b.get('title'),'price_inr':prices.get('amount'),'currency':'INR','image_url':images.get('400x400') or images.get('200x200'),'product_url':b.get('productUrl'),'source':'Flipkart','description':b.get('productDescription','')})
    return out
