import logging
import os
import pathlib

from pydantic import PostgresDsn, field_validator
from pydantic_core.core_schema import ValidationInfo
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

env_file = os.path.join(pathlib.Path(__file__).parent.parent.parent, ".env")

if not os.path.exists(env_file):
    # Containers pass configuration through environment variables (see deploy/docker-compose.yml);
    # a .env file is only needed for local, non-docker runs.
    logger.warning("No .env file at %s; relying on environment variables only.", env_file)

# Values a copied .env.example would still contain. Refusing them at startup means a stack
# can never come up with a forgeable JWT secret or a well-known admin password.
PLACEHOLDER_MARKERS = ("change-me", "changeme", "secret", "password")
MIN_SECRET_KEY_LENGTH = 32


def reject_placeholder(field_name: str, value: str, min_length: int = 1) -> str:
    """Shared validator body: a secret must be long enough and not an example value."""
    if value is None or len(value) < min_length:
        raise ValueError(f"{field_name} must be at least {min_length} characters long")
    lowered = value.lower()
    if any(marker in lowered for marker in PLACEHOLDER_MARKERS):
        raise ValueError(
            f"{field_name} looks like a placeholder; generate a real value "
            f'(python -c "import secrets;print(secrets.token_urlsafe(48))")'
        )
    return value


class DatabaseSettings(BaseSettings):
    HOST: str
    USER: str
    PASSWORD: str
    DB: str
    PORT: str = "5432"
    URI: str | None = None
    model_config = SettingsConfigDict(env_file=env_file, env_prefix="POSTGRES_", case_sensitive=True, extra="ignore")

    @field_validator("URI", mode="before")
    def assemble_db_uri(cls, field_value, info: ValidationInfo) -> str:
        if isinstance(field_value, str):
            return field_value
        return PostgresDsn.build(
            scheme="postgresql",
            username=info.data.get("USER"),
            password=info.data.get("PASSWORD"),
            host=info.data.get("HOST"),
            path=info.data.get("DB"),
            port=int(info.data.get("PORT")),
        ).unicode_string()


class APISettings(BaseSettings):
    """
    My settings for my API Security.
    """

    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE: int = 120  # (by minute)
    # Browser origins allowed to call the API (the web dashboard). Never "*" with credentials.
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]
    # Failed-or-not login attempts allowed per client IP per minute.
    LOGIN_RATE_LIMIT_PER_MINUTE: int = 10
    # Reverse proxies whose X-Forwarded-For may be believed (none by default: the TCP peer is the client).
    TRUSTED_PROXIES: list[str] = []
    # Interactive docs (/docs, /openapi.json) map the whole attack surface; off unless explicitly enabled.
    DOCS_ENABLED: bool = False
    # Browser session cookies (POST /auth/login with use_cookie=true). Secure needs TLS, so it is
    # off for the plain-http local stack and must be true behind the production proxy.
    COOKIE_SECURE: bool = False
    # None = host-only cookie, right for localhost. Set e.g. ".example.com" when the web app and
    # the API are on different subdomains of one site, so app.example.com receives it too.
    COOKIE_DOMAIN: str | None = None
    model_config = SettingsConfigDict(env_file=env_file, env_prefix="API_", case_sensitive=True, extra="ignore")

    @field_validator("SECRET_KEY")
    def secret_key_is_real(cls, value: str) -> str:
        return reject_placeholder("API_SECRET_KEY", value, MIN_SECRET_KEY_LENGTH)

    @field_validator("COOKIE_DOMAIN", mode="before")
    def blank_domain_is_none(cls, value):
        # compose passes "" when the variable is unset; an empty Domain attribute makes browsers
        # reject the cookie outright, so treat blank as "not set".
        if isinstance(value, str) and not value.strip():
            return None
        return value


class StreamerSettings(BaseSettings):
    BROKER_HOSTS: list[str]
    SENSORS_TOPIC: str
    WATER_CONTROL_TOPIC: str
    # Consumer group of the backend streamer; explicit so offsets survive restarts and
    # the group is never shared with the simulator's consumers.
    GROUP_ID: str = "tilthwave-backend-streamer"
    LOG_LEVEL: str = "INFO"
    model_config = SettingsConfigDict(env_file=env_file, env_prefix="STREAMER_", case_sensitive=True, extra="ignore")


class FlowRunnerSettings(BaseSettings):
    MINUTES: float
    # Safety limits: an irrigation task is force-stopped after MAX_IRRIGATION_MINUTES, and a zone
    # whose latest reading is older than MAX_READING_AGE_MINUTES is treated as blind (no start,
    # stop if running) so a dead sensor feed can never leave a valve open.
    MAX_IRRIGATION_MINUTES: int = 60
    MAX_READING_AGE_MINUTES: int = 30
    model_config = SettingsConfigDict(env_file=env_file, env_prefix="FLOW_RUNNER_", case_sensitive=True, extra="ignore")


class Settings(BaseSettings):
    LOG_LEVEL: str = "INFO"
    DATABASE: DatabaseSettings = DatabaseSettings()
    API: APISettings = APISettings()
    STREAMER: StreamerSettings = StreamerSettings()
    FLOW_RUNNER: FlowRunnerSettings = FlowRunnerSettings()
    model_config = SettingsConfigDict(env_file=env_file, case_sensitive=True, extra="ignore")


settings = Settings()
