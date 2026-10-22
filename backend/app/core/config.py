from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=("../.env", ".env"), extra="ignore")

    app_env: str = "development"
    database_url: str = "postgresql+asyncpg://fieldsync:fieldsync_dev@localhost:5433/fieldsync"
    jwt_secret: str = "dev-only-secret-change-me"
    access_token_minutes: int = 15
    refresh_token_days: int = 30
    storage_backend: str = "local"
    storage_root: str = "./data/storage"
    file_url_secret: str = "dev-only-file-secret"
    file_url_ttl_seconds: int = 300
    max_upload_bytes: int = 15 * 1024 * 1024
    internal_api_key: str = ""
    cors_origins: str = "http://localhost:5173"
    # Place names for coordinates. nominatim = free OpenStreetMap lookup (light use only: usage policy applies,
    # set a real contact in GEOCODER_USER_AGENT); google = Google Geocoding API (needs GOOGLE_MAPS_API_KEY); none = off.
    geocoder: str = "nominatim"
    geocoder_user_agent: str = "FieldSync/0.1 (set GEOCODER_USER_AGENT with a contact email)"
    google_maps_api_key: str = ""


    @model_validator(mode="after")
    def _production_secrets(self):
        """Refuse to run a non-development environment with default/short secrets."""
        if self.app_env != "development":
            weak = [n for n in ("jwt_secret", "file_url_secret")
                    if len(getattr(self, n)) < 32 or getattr(self, n).startswith("dev-only")
                    or getattr(self, n).startswith("change-me")]
            if weak:
                raise ValueError(f"APP_ENV={self.app_env}: set strong (>=32 char) values for {', '.join(weak)}")
        if self.geocoder not in ("nominatim", "google", "none"):
            raise ValueError("GEOCODER must be nominatim, google or none")
        if self.geocoder == "google" and not self.google_maps_api_key:
            raise ValueError("GEOCODER=google requires GOOGLE_MAPS_API_KEY")
        if self.geocoder == "nominatim" and self.app_env != "development" and (
            "@" not in self.geocoder_user_agent or "set GEOCODER_USER_AGENT" in self.geocoder_user_agent
        ):
            # OpenStreetMap's usage policy requires an identifying contact in the User-Agent.
            raise ValueError("GEOCODER=nominatim needs GEOCODER_USER_AGENT with a contact email, e.g. 'FieldSync/1.0 (ops@acme.com)'")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
