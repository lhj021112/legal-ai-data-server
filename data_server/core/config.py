import os

from dotenv import load_dotenv


load_dotenv()


class Settings:
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    ADMIN_API_KEY: str = os.getenv("ADMIN_API_KEY", "")
    CORS_ALLOW_ORIGINS: str = os.getenv("CORS_ALLOW_ORIGINS", "*")

    @property
    def cors_allow_origins_list(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.CORS_ALLOW_ORIGINS.split(",")
            if origin.strip()
        ]


settings = Settings()


def is_placeholder_database_url(database_url: str) -> bool:
    return any(token in database_url for token in ("USER", "PASSWORD", "HOST", "PORT"))
