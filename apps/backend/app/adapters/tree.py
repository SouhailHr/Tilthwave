from adapters.base import BaseAdaptor
from core.entities.tree import Tree as TreeEntity


class TreeAdaptor(BaseAdaptor):
    ENTITY = TreeEntity

    BASE_CUSTOM_MAPPER = {
        "created_date": {"field_in_model": "created_date", "convert_to": str},
        "updated_date": {"field_in_model": "updated_date", "convert_to": str},
        "planting_date": {"field_in_model": "planting_date", "convert_to": str},
    }