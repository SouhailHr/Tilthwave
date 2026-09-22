from datetime import datetime

from sqlalchemy import func

from adapters.sensor_record import SensorRecordAdaptor
from core.entities.sensor_record import SensorRecord as SensorRecordEntity
from infrastructure.database.tables.sensor_record import SensorRecord
from infrastructure.repositories.base import BaseDBRepo


class SensorRecordDBRepository(BaseDBRepo):
    """
    Sensor readings: the one table that grows without bound, so the two questions asked of it
    every tick and every dashboard poll are answered in one statement each, never per sensor.
    """

    MODEL = SensorRecord
    ENTITY = SensorRecordEntity
    ADAPTOR = SensorRecordAdaptor
    TENANT_SCOPE = ("via_sensor",)  # record -> sensor.farm_name

    def latest_per_sensor(self, serial_numbers) -> list[SensorRecordEntity]:
        """
        The newest record of each of the given sensors, in one round trip. `id` is monotonic with
        insertion (and never ties, unlike created_date), so the newest row is the max id per
        sensor; the (sensor_serial_number, created_date) index serves the per-sensor scan.
        """
        serial_numbers = list(serial_numbers)
        if not serial_numbers:
            return []
        session = self.Session()
        try:
            model = self.MODEL
            newest_ids = (
                self._apply_tenant(session.query(func.max(model.id)), session)
                .filter(model.sensor_serial_number.in_(serial_numbers))
                .group_by(model.sensor_serial_number)
            )
            rows = session.query(model).filter(model.id.in_(newest_ids.scalar_subquery())).all()
            return [self.ADAPTOR.model_to_entity(row) for row in rows]
        except Exception as e:
            session.rollback()
            raise self._translate("filtering", e) from e
        finally:
            session.close()

    def monthly_consumption(self, serial_numbers, year: int) -> dict[int, float]:
        """
        Sum of data->consumption per calendar month of `year` over the given sensors, in one
        statement: {month: total}. Months without records are absent. Replaces loading every
        record of every source into Python to add them up.
        """
        serial_numbers = list(serial_numbers)
        if not serial_numbers:
            return {}
        session = self.Session()
        try:
            model = self.MODEL
            month = func.extract("month", model.created_date)
            total = func.coalesce(func.sum(model.data["consumption"].as_float()), 0.0)
            query = (
                self._apply_tenant(session.query(month, total), session)
                .filter(
                    model.sensor_serial_number.in_(serial_numbers),
                    model.created_date >= datetime(year, 1, 1),
                    model.created_date < datetime(year + 1, 1, 1),
                )
                .group_by(month)
            )
            return {int(m): float(amount) for m, amount in query.all()}
        except Exception as e:
            session.rollback()
            raise self._translate("filtering", e) from e
        finally:
            session.close()
