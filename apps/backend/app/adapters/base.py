import dataclasses

from adapters.exceptions import AdaptorException


class BaseAdaptor:
    ENTITY = None
    # Per-entity mappers, merged over BASE_CUSTOM_MAPPER (e.g. TreeAdaptor converts planting_date)
    CUSTOM_MAPPER = {}
    # Mapper for base cases in all entities
    BASE_CUSTOM_MAPPER = {
        "created_date": {"field_in_model": "created_date", "convert_to": str},
        "updated_date": {"field_in_model": "updated_date", "convert_to": str},
    }

    @classmethod
    def model_to_entity(cls, obj) -> ENTITY:
        """
        Method that convert Base model to Base entity by mapping the fields
        @return: ENTITY
        """
        try:
            entity_field_names = [field.name for field in dataclasses.fields(cls.ENTITY)]
            mappers = {**cls.BASE_CUSTOM_MAPPER, **cls.CUSTOM_MAPPER}
            data = dict()
            for field in entity_field_names:
                mapper = mappers.get(field)
                if mapper:
                    # read the mapped model field and convert it when a converter is configured
                    entity_value = getattr(obj, mapper["field_in_model"])
                    if mapper.get("convert_to") and entity_value is not None:
                        entity_value = mapper["convert_to"](entity_value)
                else:
                    entity_value = getattr(obj, field)
                data[field] = entity_value

            entity = cls.ENTITY.from_dict(data=data)
            return entity
        except Exception as e:
            raise AdaptorException(message=str(e)) from e

    @classmethod
    def dict_to_entity(cls, data: dict) -> ENTITY:
        """
            Method that convert a dict to entity
        @param data:
        @return:
        """
        try:
            return cls.ENTITY.from_dict(data)
        except Exception as e:
            raise AdaptorException(message=str(e)) from e
