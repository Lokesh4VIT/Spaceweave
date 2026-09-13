from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "SpaceWeave AI"
    environment: str = "development"
    host: str = "0.0.0.0"
    port: int = 8000
    allowed_origins: str = "http://localhost:8000,http://127.0.0.1:8000"
    qdrant_url: str = "http://qdrant:6333"
    qdrant_api_key: str | None = None
    embedding_model: str = "sentence-transformers/clip-ViT-B-32"
    embedding_dim: int = 512
    candidate_k: int = 120
    default_top_k: int = 8
    spatial_clearance_cm: float = 10.0
    max_upload_mb: int = 10
    # Marketplace adapters are opt-in. Never put secrets in frontend code.
    amazon_enabled: bool = False
    amazon_client_id: str | None = None
    amazon_client_secret: str | None = None
    amazon_refresh_token: str | None = None
    amazon_partner_tag: str | None = None
    amazon_marketplace: str = "www.amazon.in"
    amazon_token_url: str = "https://api.amazon.com/auth/o2/token"
    flipkart_enabled: bool = False
    flipkart_affiliate_id: str | None = None
    flipkart_affiliate_token: str | None = None
    model_config = SettingsConfigDict(env_file='.env', extra='ignore', case_sensitive=False)

    @property
    def origins(self):
        return [x.strip() for x in self.allowed_origins.split(',') if x.strip()]

@lru_cache
def get_settings():
    return Settings()
