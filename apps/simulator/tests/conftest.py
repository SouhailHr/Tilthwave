"""Environment for the simulator settings; set before any app module is imported."""

import os

os.environ.update(
    {
        "STREAMER_BROKER_HOSTS": '["broker:9092"]',
        "STREAMER_SENSORS_TOPIC": "test.sensors",
        "STREAMER_WATER_CONTROL_TOPIC": "test.water-control",
        "API_BASE_URL": "http://api:8080",
        "API_USERNAME": "admin",
        "API_PASSWORD": "test-password",
        "API_LOGIN_RETRY_SECONDS": "0",
        "API_LOGIN_MAX_ATTEMPTS": "3",
        "SENSORS_CYCLE_ROUNDS": "10",
    }
)
