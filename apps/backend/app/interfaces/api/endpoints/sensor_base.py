import json
import logging

from fastapi import HTTPException
from fastapi.responses import JSONResponse
from fastapi_pagination.iterables import paginate
from starlette import status

from adapters.sensor import SensorAdaptor
from adapters.zone_sensors import ZoneSensorsAdaptor
from config.settings import settings
from core.use_cases.sensor import SensorUseCase
from core.use_cases.water_source import WaterSourceUseCase
from core.use_cases.water_switcher import WaterSwitcherUseCase
from core.use_cases.zone_sensors import ZoneSensorsUseCase
from infrastructure.repositories.sensor import SensorDBRepository
from infrastructure.repositories.water_source import WaterSourceDBRepository
from infrastructure.repositories.water_switcher import WaterSwitcherDBRepository
from infrastructure.repositories.zone import ZoneDBRepository
from infrastructure.repositories.zone_sensors import ZoneSensorsDBRepository
from interfaces.api.endpoints.base import BaseCrud

zone_repo = ZoneDBRepository(uri=settings.DATABASE.URI)
sensor_repo = SensorDBRepository(uri=settings.DATABASE.URI)
zone_sensors_repo = ZoneSensorsDBRepository(uri=settings.DATABASE.URI)
water_switcher_repo = WaterSwitcherDBRepository(uri=settings.DATABASE.URI)
water_source_repo = WaterSourceDBRepository(uri=settings.DATABASE.URI)
sensor_use_case = SensorUseCase(
    repo=sensor_repo,
    zone_repo=zone_repo,
    zone_sensors_repo=zone_sensors_repo,
    water_source_repo=water_source_repo,
    water_switcher_repo=water_switcher_repo,
)
zone_sensors_use_case = ZoneSensorsUseCase(repo=zone_sensors_repo, sensor_repo=sensor_repo)
water_switcher_use_case = WaterSwitcherUseCase(repo=water_switcher_repo, sensor_repo=sensor_repo)
water_source_use_case = WaterSourceUseCase(repo=water_source_repo, sensor_repo=sensor_repo, sensor_record_repo=None,
                                           broker_repo=None)

logger = logging.getLogger(__name__)


class SensorCrudHelper(BaseCrud):
    ADAPTOR_CLASS = SensorAdaptor
    USE_CASE_INSTANCE = sensor_use_case
    IDENTIFIER = "serial_number"

    @staticmethod
    def _drop_fields(data: dict):
        """
        Drop unnecessary fields from the data dict.
        @param data: dict
        @return:
        """
        fields_to_drop = ["zone_name", "assigned_to_type", "water_switcher", "water_source"]
        for field in fields_to_drop:
            data.pop(field, None)

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
        # transform the pydantic model to a dict
        data = data.model_dump()
        # drop unnecessary fields for sensor create
        cls._drop_fields(data)
        # add performed_by
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
        """
        this method is the zone handler , it will prepare the data to create in the zone_sensors entity
        and use the common process to create the sensor
        @param data: pydantic model
        @param performed_by: the user who performed the operation
        @return: the result of the process_common
        """
        zone_sensors_dict = {
            "zone_name": data.zone_name,
            "sensor_serial_number": data.serial_number,
            "performed_by": performed_by,
        }
        return cls._process_common(data, performed_by, zone_sensors_dict, ZoneSensorsAdaptor,
                                   zone_sensors_use_case.create)

    @classmethod
    def _handle_water_switcher(cls, data, performed_by):
        """
         this method is the water switcher  handler , it will prepare the data to update in the water_switcher entity
        and use the common process to create the sensor
        @param data: pydantic model
        @param performed_by: the user who performed the operation
        @return: the result of the process_common
        """
        water_switcher_dict = {
            "serial_number": data.water_switcher,
            "sensor_serial_number": data.serial_number,
            "performed_by": performed_by,
        }
        return cls._process_common(data, performed_by, water_switcher_dict, None,
                                   water_switcher_use_case.update_by_serial_number)

    @classmethod
    def _handle_water_source(cls, data, performed_by):
        """
         this method is the water source handler , it will prepare the data to update  the water source entity
        and use the common process to create the sensor
        @param data: pydantic model
        @param performed_by: the user who performed the operation
        @return: the result of the process_common
        """
        water_source_dict = {
            "serial_number": data.water_source,
            "sensor_serial_number": data.serial_number,
            "performed_by": performed_by,
        }
        return cls._process_common(data, performed_by, water_source_dict, None,
                                   water_source_use_case.update_by_serial_number)

    @classmethod
    def create(cls, data, performed_by=None):
        """
         this method Creates a new sensor with additional related entities if necessary.
         eg ( zone_sensors , water_source , water_switcher) to establish the relation of the sensor with the other
         entity when we create the sensor
        @param data: pydantic model
        @param performed_by: the user who performed the operation
        @return: JSONResponse if success or HTTPException if failed
        """
        try:
            handler_mapping = {
                "zone": cls._handle_zone,
                "water_switcher": cls._handle_water_switcher,
                "water_source": cls._handle_water_source,
            }

            handler = handler_mapping.get(data.assigned_to_type)
            if handler:
                result = handler(data=data, performed_by=performed_by)
                if result:
                    return JSONResponse(status_code=status.HTTP_200_OK, content=result.to_dict())
            else:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid assigned_to_type")
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @classmethod
    def _update_zone(cls, id, data, performed_by):
        """
            this method update a zone and with additional related sensor entity
        @param id: the sensor id
        @param data: Dictionary of data to update.
        @param performed_by: the user who performed the operation
        @return: result
        """
        zone_sensors_dict = {
            "zone_name": data.get("zone_name"),
            "sensor_serial_number": data.get("serial_number"),
            "performed_by": performed_by,
        }
        data["performed_by"] = performed_by
        result = cls.USE_CASE_INSTANCE.update(id=id, data=data)
        zone_sensors_use_case.update_by_sensor_serial_number(
            sensor_serial_number=data.get("serial_number"),
            data=zone_sensors_dict
        )
        return result

    @classmethod
    def _update_water_switcher(cls, id, data, performed_by):
        """
            this method update a water_switcher and with additional related sensor entity
        @param id: the sensor id
        @param data: Dictionary of data to update.
        @param performed_by: the user who performed the operation
        @return: result
        """
        water_switcher_dict = {
            "water_switcher_serial_number": data.get("water_switcher"),
            "sensor_serial_number": data.get("serial_number"),
            "performed_by": performed_by,
        }
        data["performed_by"] = performed_by
        result = cls.USE_CASE_INSTANCE.update(id=id, data=data)
        water_switcher_use_case.update_by_serial_number(
            serial_number=data.get("water_switcher"),
            data=water_switcher_dict
        )
        return result

    @classmethod
    def _update_water_source(cls, id, data, performed_by):
        """
            this method update a water_source and with additional related sensor entity
        @param id: the sensor id
        @param data: Dictionary of data to update.
        @param performed_by: the user who performed the operation
        @return: result
        """
        water_source_dict = {
            "water_source_serial_number": data.get("water_source"),
            "sensor_serial_number": data.get("serial_number"),
            "performed_by": performed_by,
        }
        data["performed_by"] = performed_by
        result = cls.USE_CASE_INSTANCE.update(id=id, data=data)
        water_source_use_case.update_by_serial_number(
            serial_number=data.get("water_source"),
            data=water_source_dict
        )
        return result

    @classmethod
    def update_by_id(cls, id: int, data, performed_by=None):
        """
            Update an existing sensor by id and handle related entities.
        @param id: the sensor id
        @param data: Dictionary of data to update.
        @param performed_by: the user who performed the operation
        @return: result
        """

        try:
            handler_mapping = {
                "zone": cls._update_zone,
                "water_switcher": cls._update_water_switcher,
                "water_source": cls._update_water_source,
            }

            handler = handler_mapping.get(data.get("assigned_to_type"))
            if handler:
                result = handler(id=id, data=data, performed_by=performed_by)
                if result:
                    return JSONResponse(status_code=status.HTTP_200_OK, content=result.to_dict())
                else:
                    return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={})
            else:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid assigned_to_type")
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    @classmethod
    def _convert_list_entities_to_list_of_dict(cls, entities):
        """
        We need to override this method because for Sensor the Sensor usecase.filter return a list of dict
        so no need to convert it
        @return:
        """
        return entities

    @classmethod
    def get_all(cls, filters_str=None):
        """
            Retrieve all entities from the data source as a list of dictionaries.
        @return       {
                    "items": [{...}, {...}],
                    "total": 567,
                    "page": 1,
                    "size": 50,
                    "pages": 18
                }
        """
        filters_dict = {}
        filters = []
        if filters_str:
            try:
                filters_dict = json.loads(filters_str)
            except json.JSONDecodeError:
                logger.error("Failed to decode filters")
        if filters_dict:
            filters = cls.parse_filters(filters_dict=filters_dict)
        try:
            result = cls.USE_CASE_INSTANCE.filter(filters, order_by="created_date", order_direction="asc")
            list_of_dict = cls._convert_list_entities_to_list_of_dict(entities=result)
            if list_of_dict:
                # Adding Assigned_to to the result
                sensors_list = []
                for entity in list_of_dict:
                    assigned_to = sensor_use_case.check_if_sensor_is_assigned(sensor_serial_number=entity.serial_number,
                                                                              sensor_type=entity.type)
                    sensor_dict = entity.to_dict()
                    # add assigned_to to the sensor_dict
                    sensor_dict['assigned_to'] = assigned_to
                    # add the sensor_dict to the sensor_list
                    sensors_list.append(sensor_dict)

                return paginate(sensors_list, total=len(sensors_list))
            else:
                return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={})
        except Exception as e:
            logger.error(e)
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
