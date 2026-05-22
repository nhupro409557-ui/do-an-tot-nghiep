from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://postgres:anhnhu057@localhost:5432/postgres"
    jwt_secret_key: str = "change-me"
    jwt_algorithm: str = "HS256"
    redis_url: str = "redis://localhost:6379/0"
    ai_rate_limit_per_minute: int = 20
    gemini_api_key: str = ""
    gemini_model: str = "gemini-flash-latest"
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from_email: str = ""
    frontend_url: str = "http://localhost:3000"
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
    momo_ipn_path: str = "/api/v1/payments/momo/ipn"
    momo_request_type: str = "captureWallet"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
