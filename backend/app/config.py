import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "VidMind Backend API"
    environment: str = "development"
    debug: bool = True
    host: str = "0.0.0.0"
    port: int = 8000
    secret_key: str = "dev-secret-key-32-chars-minimum-length"

    # Dual Gemini API Keys
    gemini_api_key_1: str = ""
    gemini_api_key_2: str = ""
    gemini_api_key: str = ""  # Backward compatibility fallback

    # Gemini Settings
    gemini_model: str = "gemini-2.5-flash"
    gemini_key_cooldown_seconds: int = 60

    # Playlist & Resource Limits
    max_playlist_videos: int = 50
    max_concurrent_videos: int = 2

    # Database & Storage
    database_url: str = "sqlite:///./vidmind.db"
    artifacts_dir: str = "../artifacts"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    def get_key_1(self) -> str:
        """Returns Gemini Key 1 (or backward-compatible gemini_api_key if set)."""
        return (self.gemini_api_key_1 or self.gemini_api_key or "").strip()

    def get_key_2(self) -> str:
        """Returns Gemini Key 2."""
        return (self.gemini_api_key_2 or "").strip()


settings = Settings()
