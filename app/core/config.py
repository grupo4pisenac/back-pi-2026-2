from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://admin:adminpassword@localhost:5432/agrotech_db"
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    THINGSPEAK_CHANNEL_ID: str = ""
    # Origens liberadas no CORS, separadas por vírgula: front-end Vite em dev e o deploy na Vercel
    CORS_ORIGINS: str = (
        "http://localhost:5173,http://127.0.0.1:5173,"
        "https://front-pi-2026-2-frmjlecdz-vitorrsantoss.vercel.app"
    )
    # Cada deploy na Vercel ganha um endereço novo (<projeto>-<hash>-<time>.vercel.app); esta
    # expressão libera todos os deploys, previews e o domínio de produção do projeto do time.
    CORS_ORIGIN_REGEX: str = r"^https://front-pi-2026-2(-[a-z0-9-]+)?-vitorrsantoss\.vercel\.app$|^https://front-pi-2026-2\.vercel\.app$"

    # Configuração de envio de e-mail (recuperação de senha)
    MAIL_BACKEND: str = "console"  # "console" (dev) ou "smtp" (produção/Gmail)
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    MAIL_FROM: str = ""
    FRONTEND_RESET_URL: str = "http://localhost:5173/reset-password"

    # Rate limit em memória para /auth/forgot-password (desligável em testes)
    RATE_LIMIT_ENABLED: bool = True
    FORGOT_PASSWORD_RATE_LIMIT_MAX_REQUESTS: int = 5
    FORGOT_PASSWORD_RATE_LIMIT_WINDOW_SECONDS: int = 900

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origins_list(self) -> list[str]:
        return [origem.strip() for origem in self.CORS_ORIGINS.split(",") if origem.strip()]

settings = Settings()
