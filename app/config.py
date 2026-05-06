from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite:///./asafe_finance.db"
    secret_key: str = "asafe-vocal-secret-key-change-in-production"
    admin_email: str = "admin@sistema.com"
    admin_password: str = "admin123"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
