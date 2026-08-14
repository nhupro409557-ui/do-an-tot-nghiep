import hashlib
import os

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


DEFAULT_DATABASE_URL = "postgresql+asyncpg://postgres:anhnhu057@localhost:5432/postgres"


def default_jwt_secret_key() -> str:
    """Keep JWT signatures stable when serverless instances share one database."""
    database_url = os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)
    material = f"electromart-jwt-fallback:{database_url}".encode("utf-8")
    return hashlib.sha256(material).hexdigest()


class Settings(BaseSettings):
    database_url: str = os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)
    jwt_secret_key: str = Field(default_factory=default_jwt_secret_key)
    jwt_algorithm: str = "HS256"
    redis_url: str = "redis://localhost:6379/0"
    ai_rate_limit_per_minute: int = 20
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.5-flash"
    gemini_fallback_model: str = "gemini-3.1-flash-lite"
    gemini_thinking_level: str = "low"
    gemini_interaction_timeout_seconds: float = 12.0
    gemini_interaction_max_retries: int = 1
    gemini_primary_timeout_seconds: float = 6.0
    gemini_primary_max_retries: int = 0
    gemini_embedding_model: str = "gemini-embedding-2"
    gemini_embedding_output_dimensionality: int = 768
    groq_api_key: str = ""
    groq_model: str = "openai/gpt-oss-120b"
    groq_reasoning_effort: str = "medium"
    groq_timeout_seconds: float = 12.0
    groq_max_retries: int = 1
    groq_max_completion_tokens: int = 700
    ai_pgvector_dual_write_enabled: bool = True
    ai_pgvector_search_percent: int = 100
    ai_response_v2_enabled: bool = True
    ai_chat_v2_percent: int = 100
    ai_shadow_mode_enabled: bool = False
    ai_router_v2_enabled: bool = True
    ai_query_planner_enabled: bool = True
    ai_service_query_planner_enabled: bool = True
    ai_read_tools_enabled: bool = True
    ai_model_routing_enabled: bool = True
    ai_verifier_enabled: bool = True
    ai_model_rate_limit_circuit_seconds: int = 300
    ai_model_timeout_circuit_seconds: int = 60
    ai_conversation_memory_enabled: bool = True
    ai_conversation_memory_ttl_minutes: int = 1440
    ai_conversation_recent_turns: int = 6
    ai_handover_failure_threshold: int = 2
    ai_handover_cooldown_minutes: int = 30
    catalog_embedding_index_path: str = "var/cocoindex/catalog_embeddings.json"
    catalog_embedding_request_delay_seconds: float = 1.2
    catalog_embedding_max_documents: int = 0
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from_email: str = ""
    frontend_url: str = "http://localhost:3000"
    google_client_id: str = "293864704533-n31a0a66ro184o9vkq8tv8m0b6l73tp1.apps.googleusercontent.com"
    s3_endpoint_url: str = ""
    s3_bucket: str = ""
    s3_access_key_id: str = ""
    s3_secret_access_key: str = ""
    s3_public_base_url: str = ""
    s3_region: str = "ap-southeast-1"
    s3_presign_expires_seconds: int = 900
    super_admin_ip_whitelist: str = ""
    brand_import_dir: str = "var/brand-imports"
    order_maintenance_enabled: bool = True
    order_maintenance_interval_seconds: int = 300
    order_pending_online_timeout_minutes: int = 15
    order_pending_cod_timeout_hours: int = 24
    sandbox_shipping_free_threshold: int = 3000000
    sandbox_shipping_inner_fee: int = 25000
    sandbox_shipping_near_fee: int = 35000
    sandbox_shipping_far_fee: int = 50000
    momo_endpoint: str = "https://test-payment.momo.vn/v2/gateway/api/create"
    momo_partner_code: str = ""
    momo_access_key: str = ""
    momo_secret_key: str = ""
    momo_redirect_url: str = "http://localhost:3000/dashboard"
    momo_ipn_path: str = "/api/payments/momo/ipn"
    momo_request_type: str = "captureWallet"
    momo_payment_timeout_minutes: int = 15
    zalopay_app_id: int = 2554
    zalopay_key1: str = ""
    zalopay_key2: str = ""
    zalopay_create_endpoint: str = "https://sb-openapi.zalopay.vn/v2/create"
    zalopay_query_endpoint: str = "https://sb-openapi.zalopay.vn/v2/query"
    zalopay_callback_url: str = ""
    zalopay_payment_timeout_minutes: int = 15
    sepay_env: str = "sandbox"
    sepay_merchant_id: str = ""
    sepay_secret_key: str = ""
    sepay_checkout_version: str = "v1"
    sepay_payment_timeout_minutes: int = 15

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
