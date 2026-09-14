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
    qdrant_collection: str = "spaceweave_products"

    embedding_model: str = "sentence-transformers/clip-ViT-B-32"
    embedding_dim: int = 512
    candidate_k: int = 120
    default_top_k: int = 8
    spatial_clearance_cm: float = 10.0
    max_upload_mb: int = 10
    seed_catalog: bool = False

    # Primary live-search provider. Needs only a SerpApi account -- no
    # marketplace affiliate/associate approval required -- so this is the
    # provider that actually returns real internet results out of the box.
    serpapi_enabled: bool = False
    serpapi_api_key: str | None = None
    serpapi_gl: str = "in"
    serpapi_hl: str = "en"

    # Secondary live-search provider. Requires an approved Flipkart
    # affiliate account.
    flipkart_enabled: bool = False
    flipkart_affiliate_id: str | None = None
    flipkart_affiliate_token: str | None = None

    # Tertiary live-search provider. Requires an approved Amazon Associates
    # account with active Creators API access (Amazon requires at least 10
    # qualifying referred sales in the trailing 30 days to grant it).
    amazon_enabled: bool = False
    amazon_client_id: str | None = None
    amazon_client_secret: str | None = None
    amazon_partner_tag: str | None = None
    amazon_marketplace: str = "www.amazon.in"
    amazon_token_url: str = "https://api.amazon.com/auth/o2/token"

    model_config = SettingsConfigDict(
    env_file=".env",
    env_ignore_empty=True,
    extra="ignore",
    case_sensitive=False,
)

    @property
    def origins(self) -> list[str]:
        return [
            x.strip()
            for x in self.allowed_origins.split(",")
            if x.strip()
        ]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
