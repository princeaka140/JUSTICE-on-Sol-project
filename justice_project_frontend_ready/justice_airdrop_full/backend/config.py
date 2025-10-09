from pydantic import BaseSettings, AnyHttpUrl, validator
from typing import List, Optional


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "sqlite:///./justice.db"

    # Bot / integration placeholders - replace with real values
    BOT_TOKEN: str = "8410236234:AAFfHYjMvkScJF23So6AW4RxaXzqosNWQo4"
    BOT_API_KEY: str = "REPLACE_BOT_API_KEY"
    # Comma separated list or JSON array of integers
    BOT_OWNER_IDS: Optional[str] = "7561048693"
    ADMIN_GROUP_ID: str = "-1003164352210"
    ADMIN_CHANNEL_ID: str = "-1003140359659"

    # Backend and auth
    BACKEND_URL: AnyHttpUrl = "http://127.0.0.1:8000"
    JWT_SECRET: str = "REPLACE_JWT_SECRET"
    JWT_EXP_SECONDS: int = 3600

    class Config:
        env_file = ".env"

    @property
    def owner_ids(self) -> List[int]:
        raw = (self.BOT_OWNER_IDS or "").strip()
        if not raw:
            return []
        # allow comma separated or JSON-like
        parts = [p.strip() for p in raw.replace('[', '').replace(']', '').split(',') if p.strip()]
        ids = []
        for p in parts:
            try:
                ids.append(int(p))
            except Exception:
                continue
        return ids


settings = Settings()
