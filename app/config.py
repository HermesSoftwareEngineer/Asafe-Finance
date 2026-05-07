from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Variável de produção (Cloud Run injeta via Secret Manager)
    database_url: str = ""

    # Variáveis de desenvolvimento
    dev_db: str = "sqlite"
    sqlite_url: str = "sqlite:///./asafe_finance.db"
    supabase_url: str = ""

    secret_key: str = "asafe-vocal-secret-key-change-in-production"
    admin_email: str = "admin@sistema.com"
    admin_password: str = "admin123"
    frontend_url: str = "http://localhost:5173"

    @property
    def resolved_database_url(self) -> str:
        # Produção: DATABASE_URL injetada diretamente (Cloud Run / Secret Manager)
        if self.database_url:
            return self.database_url
        # Dev: seleciona conforme DEV_DB
        if self.dev_db == "supabase":
            if not self.supabase_url:
                raise ValueError("DEV_DB=supabase mas SUPABASE_URL não está definida no .env")
            return self.supabase_url
        return self.sqlite_url

    @property
    def allowed_origins(self) -> list[str]:
        origins = [self.frontend_url]
        if "localhost" not in self.frontend_url:
            origins.append("http://localhost:5173")
        return origins

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
