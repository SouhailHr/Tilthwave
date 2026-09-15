import logging.config
import os
import pathlib
from typing import Optional

from pydantic import PostgresDsn, field_validator
from pydantic_core.core_schema import ValidationInfo
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

DEBUG = "DEBUG"
env_file = os.path.join(pathlib.Path(__file__).parent.parent.parent, '.env')

assert os.path.exists(
    env_file), "Please ensure that you include the .env file in the project's root directory, thank you."


class DatabaseSettings(BaseSettings):
    HOST: str
    USER: str
    PASSWORD: str
    DB: str
    PORT: str = "5432"
    DUMP_PATH: str
    URI: Optional[str] = None
    TEST_URI: Optional[str] = None
    model_config = SettingsConfigDict(env_file=env_file, env_prefix="POSTGRES_", case_sensitive=True)

    @field_validator('URI', mode="before")
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
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE: int  # (by minute)
    model_config = SettingsConfigDict(env_file=env_file, env_prefix="API_", case_sensitive=True)


class StreamerSettings(BaseSettings):
    BROKER_HOSTS: list[str]
    SENSORS_TOPIC: str
    WATER_CONTROL_TOPIC: str
    LOG_LEVEL: str
    LOG_FILENAME: str = ""
    model_config = SettingsConfigDict(env_file=env_file, env_prefix="STREAMER_", case_sensitive=True)


class FlowRunnerSettings(BaseSettings):
    MINUTES: float
    model_config = SettingsConfigDict(env_file=env_file, env_prefix="FLOW_RUNNER_", case_sensitive=True)


class Settings(BaseSettings):
    DATABASE: DatabaseSettings = DatabaseSettings()
    API: APISettings = APISettings()
    STREAMER: StreamerSettings = StreamerSettings()
    FLOW_RUNNER: FlowRunnerSettings = FlowRunnerSettings()


settings = Settings()
