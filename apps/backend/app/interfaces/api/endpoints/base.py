import json
import logging

from fastapi import Response
from fastapi.responses import JSONResponse
from fastapi_pagination.api import create_page, resolve_params
from starlette import status

from common.exceptions import InvalidFilterError, NotFoundError

logger = logging.getLogger(__name__)


class BaseCrud:
    """
    Template Method for the REST resources: subclasses configure the three class attributes
    and override a hook when a resource needs more than plain CRUD. Errors are not handled
    here: domain exceptions propagate to the handlers in interfaces/api/helpers/errors.py.
    """

    ADAPTOR_CLASS = None
    USE_CASE_INSTANCE = None
    IDENTIFIER = None

    @classmethod
    def _not_found(cls):
        return NotFoundError(f"{cls.ADAPTOR_CLASS.ENTITY.__name__} not found")

    @classmethod
    def create(cls, data, performed_by=None):
        """
        logic:
            1- Get input from user and the username of the current user
            2- Transform input to dict
            3- Transform input from dict to entity
            4- Create an object using its use case
        @param data:
        @param performed_by:
        @return 201 with the dict of the object
        """
        data = data.model_dump()
        data["performed_by"] = performed_by  # Set the username
        entity = cls.ADAPTOR_CLASS.dict_to_entity(data)
        result = cls.USE_CASE_INSTANCE.create(entity)
        return JSONResponse(status_code=status.HTTP_201_CREATED, content=result.to_public_dict())

    @classmethod
    def get_by_id(cls, id: int):
        """
        logic:
            1- Search for an object by id
            2- Return the object if it exists
        @param id:
        @return Dict of the object
        """
        result = cls.USE_CASE_INSTANCE.get(id)
        if not result:
            raise cls._not_found()
        return JSONResponse(status_code=status.HTTP_200_OK, content=result.to_public_dict())

    @classmethod
    def delete_by_id(cls, id: int):
        """
        Logic:
            1- Search for an object by id
            2- If the object exists delete the object from the DB
        @param id:
        @return 204 No Content
        """
        if not cls.USE_CASE_INSTANCE.delete(id=id):
            raise cls._not_found()
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @classmethod
    def update_by_id(cls, id: int, data: dict, performed_by=None):
        """
        Logic:
            1- Search for an object by id
            2- If the object exists update the object from the DB
        @param id:
        @param data: dict of the fields to update (already validated by the resource's *Update schema)
        @param performed_by:
        @return Dict of the object
        """
        data["performed_by"] = performed_by  # Set the username
        result = cls.USE_CASE_INSTANCE.update(id=id, data=data)
        if not result:
            raise cls._not_found()
        return JSONResponse(status_code=status.HTTP_200_OK, content=result.to_public_dict())

    @classmethod
    def _enrich_item(cls, entity) -> dict:
        """
        Hook: the public dict of one listed entity. Override to add computed fields.
        """
        return entity.to_public_dict()

    @classmethod
    def _enrich_items(cls, entities) -> list[dict]:
        """
        Hook: the public dicts of one page. Override when the computed fields need a lookup, so
        it is done once for the page rather than once per row (see SensorCrudHelper).
        """
        return [cls._enrich_item(entity) for entity in entities]

    @classmethod
    def filters_doc(cls) -> str:
        """OpenAPI description of the `filters` query parameter for this resource."""
        return f'JSON object, e.g. {{"search": "..."}} (matches {cls.IDENTIFIER}) or {{"<column>": "<value>"}}'

    @classmethod
    def _parse_filters_str(cls, filters_str, search=None) -> list[dict]:
        """
        Decode the `filters` query parameter (a JSON object) into Filter DSL entries.
        A plain `search` query parameter is the same as {"search": ...} inside `filters`.
        """
        if search:
            return cls.parse_filters({"search": search})
        if not filters_str:
            return []
        try:
            filters_dict = json.loads(filters_str)
        except json.JSONDecodeError as e:
            raise InvalidFilterError("filters must be a JSON object") from e
        if not isinstance(filters_dict, dict):
            raise InvalidFilterError("filters must be a JSON object")
        return cls.parse_filters(filters_dict=filters_dict)

    @classmethod
    def get_all(cls, filters_str=None, search=None):
        """
            Retrieve one page of entities, paginated in the database.
        @return       {
                    "items": [{...}, {...}],
                    "total": 567,
                    "page": 1,
                    "size": 50,
                    "pages": 18
                }
        """
        filters = cls._parse_filters_str(filters_str, search)
        params = resolve_params()
        raw = params.to_raw_params()
        # Newest first, like a log: the dashboard's recent activity already reads that way and a
        # table that opens on the oldest row buries what just happened. `id` rather than
        # created_date because it is monotonic with insertion and never ties (seeded rows share a
        # created_date), so page boundaries are deterministic.
        entities, total = cls.USE_CASE_INSTANCE.paginate(
            filters, order_by="id", order_direction="desc", limit=raw.limit, offset=raw.offset
        )
        return create_page(cls._enrich_items(entities), total=total, params=params)

    @classmethod
    def parse_filters(cls, filters_dict: dict) -> list[dict]:
        """
        Parses a filter string into a list of filter dictionaries.

        Logic:

          We can have 2 type of filters format:
              1- Generic Search: filters_dict = {"search":"XYUZ"} :
                  ==> This means we need to make a search based ob IDENTIFIER field
              2-Custom Search: filters_dict =  {"type":"moisture_sensor","zone_name":"Zone C"}
                  ==> This means we need to filters by the requested filter's attributes

        @param filters_dict: a Dict that contains the filters.
        @type filters_dict: dict

        @return: A list of dictionaries, each containing the keys 'attribute', 'value', and 'condition'.
                 Each dictionary represents a filter parsed from the input string.
                 If the input string is None or empty, an empty list is returned.
        @rtype: tuple

        """
        if not filters_dict:
            return []
        # 1- Check what type of filter we have
        filters = []
        if "search" in filters_dict.keys():
            # Generic Search
            filters.append({"attribute": cls.IDENTIFIER, "value": filters_dict["search"], "condition": "icontains"})
        else:
            # the filters_dict is int this format
            # {"attribute":value ,"attribute":value}
            for attribute, value in filters_dict.items():
                filters.append({"attribute": attribute, "value": value, "condition": "eq"})
        return filters
