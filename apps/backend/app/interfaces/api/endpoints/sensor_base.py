import logging

from fastapi.responses import JSONResponse
from starlette import status

import common.constants as global_constants
from adapters.sensor import SensorAdaptor
from adapters.zone_sensors import ZoneSensorsAdaptor
from common.exceptions import NotFoundError
from core.use_cases.exceptions import UseCaseException
from interfaces.api.endpoints.base import BaseCrud
from wiring import api_use_cases

use_cases = api_use_cases()
logger = logging.getLogger(__name__)


class SensorCrudHelper(BaseCrud):
    """
    A sensor is created/updated together with the relation named by `assigned_to_type`
    (zone -> zone_sensors row, water_switcher / water_source -> their sensor_serial_number).
    """

    ADAPTOR_CLASS = SensorAdaptor
    USE_CASE_INSTANCE = use_cases.sensor
    IDENTIFIER = "serial_number"

    # Request fields that describe the relation, not the sensor row itself.
    RELATION_FIELDS = ("zone_name", "assigned_to_type", "water_switcher", "water_source")

    @classmethod
    def _drop_relation_fields(cls, data: dict):
        for field in cls.RELATION_FIELDS:
            data.pop(field, None)

    @classmethod
    def _invalid_assignment(cls):
        return UseCaseException(
            class_name=cls.__name__, message="assigned_to_type must be one of: zone, water_switcher, water_source"
        )

    @classmethod
    def _require_target(cls, use_case, attribute, value, label):
        """
        The relation target (zone / switcher / source) must exist within the caller's farm.
        Checked before any write so a wrong or foreign target is a 404 with nothing persisted
        (the tenant filter hides other farms' rows, hence "not found", not "forbidden").
        """
        if value is None or use_case.first([{"attribute": attribute, "value": value, "condition": "eq"}]) is None:
            raise NotFoundError(f"{label} not found")

    # What each relation accepts; checked from the request before any write, so a mismatch is a
    # 422 with nothing persisted rather than a sensor row left behind by a failed link (whose
    # corrected retry then hit the unique serial and answered 409).
    ALLOWED_TYPES = {
        "zone": tuple(global_constants.ZONE_SENSORS),
        "water_switcher": (global_constants.SWITCHER_SENSOR,),
        "water_source": (global_constants.SOURCE_SENSOR,),
    }

    @classmethod
    def _require_type_for(cls, assigned_to_type, sensor_type):
        allowed = cls.ALLOWED_TYPES.get(assigned_to_type)
        if allowed and sensor_type not in allowed:
            owner = assigned_to_type.replace("_", " ")
            raise UseCaseException(
                class_name=cls.__name__, message=f"{owner} can only have a sensor of type {', '.join(allowed)}"
            )

    @classmethod
    def _check_assignment(cls, assigned_to_type, zone_name, water_switcher, water_source):
        if assigned_to_type == "zone":
            cls._require_target(use_cases.zone, "zone_name", zone_name, "Zone")
        elif assigned_to_type == "water_switcher":
            cls._require_target(use_cases.water_switcher, "serial_number", water_switcher, "Water switcher")
        elif assigned_to_type == "water_source":
            cls._require_target(use_cases.water_source, "serial_number", water_source, "Water source")

    # ---- create -----------------------------------------------------------------------------

    @classmethod
    def _process_common(cls, data, performed_by, extra_dict, adaptor_class, use_case_method):
        """
         This method handles the common process when creating a sensor
        @param data: pydantic model
        @param performed_by: the user who performed the operation
        @param extra_dict: the dict of the other entity eg ( zone_sensors , water_source, water_switcher )
        @param adaptor_class: the adaptor of the other entity  eg ( zone_sensors , water_source, water_switcher )
        @param use_case_method: the use case of the other entity eg (create , update )
        @return: result
        """
        data = data.model_dump()
        cls._drop_relation_fields(data)
        data["performed_by"] = performed_by
        sensor_entity = cls.ADAPTOR_CLASS.dict_to_entity(data)
        result = cls.USE_CASE_INSTANCE.create(sensor_entity)

        if adaptor_class:
            extra_entity = adaptor_class.dict_to_entity(extra_dict)
            use_case_method(entity=extra_entity)
        else:
            use_case_method(serial_number=extra_dict["serial_number"], data=extra_dict)

        return result

    @classmethod
    def _handle_zone(cls, data, performed_by):
        zone_sensors_dict = {
            "zone_name": data.zone_name,
            "sensor_serial_number": data.serial_number,
            "performed_by": performed_by,
        }
        return cls._process_common(
            data, performed_by, zone_sensors_dict, ZoneSensorsAdaptor, use_cases.zone_sensors.create
        )

    @classmethod
    def _handle_water_switcher(cls, data, performed_by):
        water_switcher_dict = {
            "serial_number": data.water_switcher,
            "sensor_serial_number": data.serial_number,
            "performed_by": performed_by,
        }
        return cls._process_common(
            data, performed_by, water_switcher_dict, None, use_cases.water_switcher.update_by_serial_number
        )

    @classmethod
    def _handle_water_source(cls, data, performed_by):
        water_source_dict = {
            "serial_number": data.water_source,
            "sensor_serial_number": data.serial_number,
            "performed_by": performed_by,
        }
        return cls._process_common(
            data, performed_by, water_source_dict, None, use_cases.water_source.update_by_serial_number
        )

    @classmethod
    def create(cls, data, performed_by=None):
        """
         Creates a new sensor with its related entity (zone_sensors, water_source or water_switcher)
        @param data: pydantic model
        @param performed_by: the user who performed the operation
        @return: 201 with the sensor dict
        """
        handler_mapping = {
            "zone": cls._handle_zone,
            "water_switcher": cls._handle_water_switcher,
            "water_source": cls._handle_water_source,
        }
        handler = handler_mapping.get(data.assigned_to_type)
        if not handler:
            raise cls._invalid_assignment()
        cls._require_type_for(data.assigned_to_type, data.type)
        cls._check_assignment(data.assigned_to_type, data.zone_name, data.water_switcher, data.water_source)
        result = handler(data=data, performed_by=performed_by)
        return JSONResponse(status_code=status.HTTP_201_CREATED, content=cls._enrich_items([result])[0])

    # ---- update -----------------------------------------------------------------------------

    @classmethod
    def _update_sensor(cls, id, data, performed_by):
        sensor_data = dict(data)
        cls._drop_relation_fields(sensor_data)
        sensor_data["performed_by"] = performed_by
        return cls.USE_CASE_INSTANCE.update(id=id, data=sensor_data)

    @classmethod
    def _detach(cls, serial_number):
        """
        A sensor is attached to exactly one thing. Moving it detaches it everywhere first (its
        zone link, the switcher or source that holds it), then the new target takes it: no stale
        link left behind, and no unique-constraint clash when the new holder is of the same kind.
        """
        use_cases.zone_sensors.detach(serial_number)
        use_cases.water_switcher.update_by_sensor_serial_number(serial_number, {"sensor_serial_number": None})
        use_cases.water_source.update_by_sensor_serial_number(serial_number, {"sensor_serial_number": None})

    @classmethod
    def _update_zone(cls, id, data, performed_by):
        result = cls._update_sensor(id, data, performed_by)
        if result:
            cls._detach(result.serial_number)
            use_cases.zone_sensors.update_by_sensor_serial_number(
                sensor_serial_number=result.serial_number,
                data={
                    "zone_name": data.get("zone_name"),
                    "sensor_serial_number": result.serial_number,
                    "performed_by": performed_by,
                },
            )
        return result

    @classmethod
    def _update_water_switcher(cls, id, data, performed_by):
        result = cls._update_sensor(id, data, performed_by)
        if result:
            cls._detach(result.serial_number)
            use_cases.water_switcher.update_by_serial_number(
                serial_number=data.get("water_switcher"),
                data={"sensor_serial_number": result.serial_number, "performed_by": performed_by},
            )
        return result

    @classmethod
    def _update_water_source(cls, id, data, performed_by):
        result = cls._update_sensor(id, data, performed_by)
        if result:
            cls._detach(result.serial_number)
            use_cases.water_source.update_by_serial_number(
                serial_number=data.get("water_source"),
                data={"sensor_serial_number": result.serial_number, "performed_by": performed_by},
            )
        return result

    @classmethod
    def update_by_id(cls, id: int, data: dict, performed_by=None):
        """
            Update an existing sensor by id and, when assigned_to_type is given, its relation.
        @param id: the sensor id
        @param data: dict of fields to update (validated by SensorUpdate)
        @param performed_by: the user who performed the operation
        @return: the sensor dict
        """
        handler_mapping = {
            None: cls._update_sensor,
            "zone": cls._update_zone,
            "water_switcher": cls._update_water_switcher,
            "water_source": cls._update_water_source,
        }
        handler = handler_mapping.get(data.get("assigned_to_type"), None)
        if handler is None:
            raise cls._invalid_assignment()
        if data.get("assigned_to_type"):
            sensor_type = data.get("type") or getattr(cls.USE_CASE_INSTANCE.get(id), "type", None)
            cls._require_type_for(data["assigned_to_type"], sensor_type)
        cls._check_assignment(
            data.get("assigned_to_type"), data.get("zone_name"), data.get("water_switcher"), data.get("water_source")
        )
        result = handler(id=id, data=data, performed_by=performed_by)
        if not result:
            raise cls._not_found()
        return JSONResponse(status_code=status.HTTP_200_OK, content=cls._enrich_items([result])[0])

    # ---- list -------------------------------------------------------------------------------

    @classmethod
    def _enrich_items(cls, entities) -> list[dict]:
        """
        Each listed sensor carries `assigned_to`: the zone name or the switcher/source serial.
        Looked up for the whole page in three queries, not one per row (a page of 20 was 21
        queries; the FK picker's page of 100 was 101).
        """
        entities = list(entities)
        assigned = cls.USE_CASE_INSTANCE.assignments_for(entities)
        return [{**entity.to_public_dict(), "assigned_to": assigned.get(entity.serial_number)} for entity in entities]
