from adapters.base import BaseAdaptor
from core.entities.tree import Tree as TreeEntity


class TreeAdaptor(BaseAdaptor):
    ENTITY = TreeEntity

    CUSTOM_MAPPER = {
        "planting_date": {"field_in_model": "planting_date", "convert_to": str},
    }
