import os
import pathlib

from pydantic_settings import SettingsConfigDict, BaseSettings

env_file = os.path.join(pathlib.Path(__file__).parent.parent.parent, '.env')


class StreamerSettings(BaseSettings):
    BROKER_HOSTS: list[str]
    SENSORS_TOPIC: str
    WATER_CONTROL_TOPIC: str
    LOG_LEVEL: str
    LOG_FILENAME: str = ""
    model_config = SettingsConfigDict(env_file=env_file, env_prefix="STREAMER_", case_sensitive=True, extra="ignore")


class ApiSettings(BaseSettings):
    BASE_URL: str
    USERNAME: str
    PASSWORD: str
    model_config = SettingsConfigDict(env_file=env_file, env_prefix="API_", case_sensitive=True, extra="ignore")


class Settings(BaseSettings):
    STREAMER: StreamerSettings = StreamerSettings()
    API: ApiSettings = ApiSettings()


settings = Settings()
