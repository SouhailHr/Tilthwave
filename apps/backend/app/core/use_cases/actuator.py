"""
What a water source and a water switcher have in common: a sensor of one specific type may be
attached, the row is addressed by its own serial or by its sensor's, and commands to its actuator
go through the broker gateway.
"""

import logging

from core.use_cases.base import BaseUseCase

logger = logging.getLogger(__name__)


class ActuatorUseCase(BaseUseCase):
    SENSOR_TYPE: str = ""  # the one sensor type this actuator accepts
    NOUN: str = ""  # for messages: "water source", "water switcher"

    def __init__(self, repo, sensors, broker_repo=None):
        """
        @param repo: this actuator's repository
        @param sensors: SensorUseCase, for the attach rule
        @param broker_repo: the broker gateway (a Null Object everywhere but the flow runner)
        """
        super().__init__(repo)
        self.sensors = sensors
        self.broker_repo = broker_repo

    def create(self, entity):
        if entity.sensor_serial_number:
            self.sensors.require_type(entity.sensor_serial_number, (self.SENSOR_TYPE,), owner=self.NOUN)
        return self.repo.create(entity)

    def update(self, id: int, data: dict):
        if data.get("sensor_serial_number"):
            self.sensors.require_type(data["sensor_serial_number"], (self.SENSOR_TYPE,), owner=self.NOUN)
        return self.repo.update(id, data)

    def update_by_serial_number(self, serial_number, data: dict):
        """
        Update the actuator with this serial; when there is none, detach the sensor named in
        `data` from whichever actuator currently holds it.
        """
        row = self.repo.first([{"attribute": "serial_number", "value": serial_number, "condition": "eq"}])
        if row is not None:
            return self.repo.update(row.id, data)
        holder = self.repo.first(
            [{"attribute": "sensor_serial_number", "value": data["sensor_serial_number"], "condition": "eq"}]
        )
        if holder is not None:
            return self.repo.update(holder.id, {"sensor_serial_number": None})

    def update_by_sensor_serial_number(self, sensor_serial_number, data: dict):
        """Update the actuator whose sensor is `sensor_serial_number`, if any."""
        row = self.repo.first([{"attribute": "sensor_serial_number", "value": sensor_serial_number, "condition": "eq"}])
        if row is not None:
            return self.repo.update(row.id, data)
        return None

    def send_event(self, topic, key, payload):
        return self.broker_repo.send_event(topic=topic, key=key, payload=payload)
