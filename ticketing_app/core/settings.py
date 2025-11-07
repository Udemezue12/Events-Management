import os

from dotenv import load_dotenv
from pydantic_settings import BaseSettings


load_dotenv()

# SUPABASE_USER = os.getenv("SUPABASE_USER")
SUPABASE_PASSWORD = os.getenv("SUPABASE_PASSWORD")
SUPABASE_DB = os.getenv("SUPABASE_DB")
# SUPABASE_POOL_HOST = os.getenv("SUPABASE_POOL_HOST")
# SUPABASE_POOL_PORT = os.getenv("SUPABASE_POOL_PORT")

# For async and Alembic
SUPABASE_DIRECT_HOST = os.getenv("SUPABASE_DIRECT_HOST")
SUPABASE_DIRECT_PORT = os.getenv("SUPABASE_DIRECT_PORT")


class Settings(BaseSettings):
    PROJECT_NAME: str = "AUTOPOPULATE API"
    SUPABASE_CA_PATH: str = os.path.join(
        os.path.dirname(__file__), "..", "supabase", "supabase-ca.crt"
    )

  
    DATABASE_URL: str = (
        f"postgresql+psycopg3://postgres:{SUPABASE_PASSWORD}"
        f"@{SUPABASE_DIRECT_HOST}:{SUPABASE_DIRECT_PORT}/{SUPABASE_DB}"
    )

    ASYNC_DATABASE_URL: str = (
        f"postgresql+asyncpg://postgres:{SUPABASE_PASSWORD}"
        f"@{SUPABASE_DIRECT_HOST}:{SUPABASE_DIRECT_PORT}/{SUPABASE_DB}"
    )

    RATE_LIMIT_REDIS_URL: str = (
        f"redis://{os.getenv('RATE_LIMIT_REDIS_USERNAME')}:{os.getenv('RATE_LIMIT_REDIS_PASSWORD')}"
        f"@{os.getenv('RATE_LIMIT_REDIS_HOST')}:{os.getenv('RATE_LIMIT_REDIS_PORT')}/0"
    )
    CELERY_REDIS_URL: str = (
        f"redis://{os.getenv('CELERY_REDIS_USERNAME')}:{os.getenv('CELERY_REDIS_PASSWORD')}"
        f"@{os.getenv('CELERY_REDIS_HOST')}:{os.getenv('CELERY_REDIS_PORT')}/0"
    )
    VERIFY_EMAIL_SALT:str | None = os.getenv("VERIFY_EMAIL_SALT")
    RABBITMQ_MAIN_EXCHANGE: str = "ticketing_main_exchange"
    RABBITMQ_URL: str = os.getenv("RABBITMQ_URL", "")
    RABBITMQ_DLX: str = "dead_letter_exchange"
    RABBITMQ_DLX_QUEUE: str = "dead_letter_queue"
    REDIS_URL: str = os.getenv(
        "REDIS_URL", "rediss://:123456789@gusc1-related-narwhal-32244.upstash.io:6379"
    )
    VERIFY_EMAIL_SECRET_KEY: str | None = os.getenv("EMAIL_SECRET_KEY")
    RATE_LIMIT: str = "20/minute"
    UPTASH_REDIS_TOKEN: str | None = os.getenv("UPSTASH_REDIS_REST_TOKEN")
    UPTASH_REDIS_URL: str | None = os.getenv("UPSTASH_REDIS_REST_URL")

    class Config:
        env_file = ".env"
        extra = "ignore"

        env_file_encoding = "utf-8"
    EMAIL_USER: str | None = os.getenv("EMAIL_USER")
    EMAIL_PASSWORD: str | None = os.getenv("EMAIL_PASSWORD")
    EMAIL_SERVER: str | None = os.getenv("EMAIL_SERVER")
    EMAIL_PORT: int = 587
    EMAIL_USE_TLS: bool = True


settings = Settings()
