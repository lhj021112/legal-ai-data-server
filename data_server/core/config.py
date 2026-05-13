import os

from dotenv import load_dotenv


load_dotenv()


class Settings:
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")


settings = Settings()


def is_placeholder_database_url(database_url: str) -> bool:
    return any(token in database_url for token in ("USER", "PASSWORD", "HOST", "PORT"))
