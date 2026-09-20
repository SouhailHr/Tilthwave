import os
import pathlib

from pydantic_settings import BaseSettings, SettingsConfigDict

env_file = os.path.join(pathlib.Path(__file__).parent.parent.parent, ".env")


class StreamerSettings(BaseSettings):
    BROKER_HOSTS: list[str]
    SENSORS_TOPIC: str
    WATER_CONTROL_TOPIC: str
    # Consumer group of the actuator simulator; distinct from the backend's so both read every command.
    GROUP_ID: str = "tilthwave-simulator-actuators"
    LOG_LEVEL: str = "INFO"
    model_config = SettingsConfigDict(env_file=env_file, env_prefix="STREAMER_", case_sensitive=True, extra="ignore")


class ApiSettings(BaseSettings):
    """Only the sensor simulator talks to the API; the actuator simulator runs without these."""

    BASE_URL: str = "http://api:8080"
    USERNAME: str = "simulator"  # the read-only worker seeded by the backend seed job
    PASSWORD: str = ""
    # The API may still be starting or seeding when the simulator boots: retry the login.
    LOGIN_MAX_ATTEMPTS: int = 30
    LOGIN_RETRY_SECONDS: float = 5.0
    model_config = SettingsConfigDict(env_file=env_file, env_prefix="API_", case_sensitive=True, extra="ignore")


class SensorsSettings(BaseSettings):
    """Shape of the generated readings: one 'round' publishes a reading per zone sensor."""

    ROUNDS: int = 0  # 0 = run forever
    INTERVAL_SECONDS: float = 15.0  # pause between rounds
    CYCLE_ROUNDS: int = 10  # after this many rounds the values wrap back to their start (sawtooth)
    model_config = SettingsConfigDict(env_file=env_file, env_prefix="SENSORS_", case_sensitive=True, extra="ignore")


class Settings(BaseSettings):
    STREAMER: StreamerSettings = StreamerSettings()
    API: ApiSettings = ApiSettings()
    SENSORS: SensorsSettings = SensorsSettings()


settings = Settings()
