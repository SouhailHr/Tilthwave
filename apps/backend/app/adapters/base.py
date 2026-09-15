import dataclasses

from adapters.exceptions import AdaptorException


class BaseAdaptor:
    ENTITY = None
    # Mapper for custom entities
    # TODO  Fix MAPPERS LATER
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
            data = dict()
            entity_value = None
            for field in entity_field_names:
                # 1- value from obj: obj_value
                obj_value = getattr(obj, field)
                # Check if the field is in the Mapper
                if field in cls.BASE_CUSTOM_MAPPER.keys():
                    # get field name in the model
                    field_in_model = cls.BASE_CUSTOM_MAPPER[field]["field_in_model"]
                    # get the object value
                    obj_value = getattr(obj, field_in_model)
                    # Check if we need to convert type
                    if cls.BASE_CUSTOM_MAPPER[field]["convert_to"]:
                        entity_value = cls.BASE_CUSTOM_MAPPER[field]["convert_to"](obj_value)
                else:
                    # assign obj_value to the entity_value
                    entity_value = obj_value
                # 2- add the entity_value to data
                data[field] = entity_value

            entity = cls.ENTITY.from_dict(data=data)
            return entity
        except Exception as e:
            raise AdaptorException(message=str(e))

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
            raise AdaptorException(message=str(e))
