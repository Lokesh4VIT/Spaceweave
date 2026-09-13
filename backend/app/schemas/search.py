from pydantic import BaseModel, Field

class ProductResult(BaseModel):
    product_id: str
    title: str
    category: str
    price_inr: float
    currency: str = "INR"
    width_cm: float | None = None
    depth_cm: float | None = None
    height_cm: float | None = None
    rating: float | None = None
    review_count: int = 0
    image_url: str | None = None
    product_url: str | None = None
    source: str
    similarity_score: float
    spatial_fit_score: float
    quality_score: float
    value_score: float
    final_score: float
    fit_status: str
    fit_reason: str

class SearchResponse(BaseModel):
    query: dict
    results: list[ProductResult]
    metadata: dict
