import json
import logging
from typing import List

from fastapi import HTTPException
from fastapi.responses import JSONResponse
from fastapi_pagination.iterables import paginate
from starlette import status

logger = logging.getLogger(__name__)


class BaseCrud:
    ADAPTOR_CLASS = None
    USE_CASE_INSTANCE = None
    IDENTIFIER = None

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
        @return Dict of the object
        """
        try:
            data = data.model_dump()
            data['performed_by'] = performed_by  # Set the username
            entity = cls.ADAPTOR_CLASS.dict_to_entity(data)
            result = cls.USE_CASE_INSTANCE.create(entity)
            if result:
                return JSONResponse(status_code=status.HTTP_200_OK, content=result.to_dict())
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @classmethod
    def get_by_identifier(cls, identifier):
        """
        Retrieve the object with the identifier
        @param identifier: String
        @return:
        """

        filters = [
            {"attribute": cls.IDENTIFIER, "value": identifier, "condition": "eq"}
        ]
        try:
            result = cls.USE_CASE_INSTANCE.filter(filters)
            if result:
                obj = result[0]
                return JSONResponse(status_code=status.HTTP_200_OK, content=obj.to_dict())
            else:
                return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={})
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    @classmethod
    def get_by_id(cls, id: int):
        """
        logic:
            1- Search for an object by id
            2- Return the object if it exists
        @param id:
        @return Dict of the object
        """
        try:
            result = cls.USE_CASE_INSTANCE.get(id)
            if result:
                return JSONResponse(status_code=status.HTTP_200_OK, content=result.to_dict())
            else:
                return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={})
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    @classmethod
    def delete_by_id(cls, id: int):
        """
        Logic:
            1- Search for an object by id
            2- If the object exists delete the object from the DB
        @param id:
        @return Status code
        """
        try:
            is_deleted = cls.USE_CASE_INSTANCE.delete(id=id)
            if is_deleted:
                return JSONResponse(status_code=status.HTTP_200_OK, content={})
            else:
                return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={})
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    @classmethod
    def update_by_id(cls, id: int, data, performed_by=None):
        """
        Logic:
            1- Search for an object by id
            2- If the object exists update the object from the DB
            3- Status code
        @param id:
        @param data:
        @param performed_by:
        @return Dict of the object
        """
        try:
            data['performed_by'] = performed_by  # Set the username
            result = cls.USE_CASE_INSTANCE.update(id=id, data=data)
            if result:
                return JSONResponse(status_code=status.HTTP_200_OK, content=result.to_dict())
            else:
                return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={})
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    @classmethod
    def _convert_list_entities_to_list_of_dict(cls, entities):
        """
        Converting a list of entities to a dict
        @return:
        """
        return [entity.to_dict() for entity in entities]

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
                return paginate(list_of_dict, total=len(list_of_dict))
            else:
                return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={})
        except Exception as e:
            logger.error(e)
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    @classmethod
    def get_stats(cls, entity_name=None):
        """
            this method gets the entity stats
        @return dict stats

        """

        try:
            if entity_name:
                result = cls.USE_CASE_INSTANCE.get_stats(name=entity_name)
            else:
                result = cls.USE_CASE_INSTANCE.get_stats()

            if result:
                return JSONResponse(status_code=status.HTTP_200_OK, content=result)
            else:
                return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={})
        except Exception as e:
            logger.error(e)
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    @classmethod
    def get_select_list(cls, filters_str=None):
        """
        Example of filter filters=type__eq=switcher_sensor&is_active__eq=true
        @param filters_str:
        @return:
        """
        filters = []
        if filters_str:
            filters = cls.parse_filters(filters_str)
        entities = cls.USE_CASE_INSTANCE.filter(filters)
        data = [
            {"value": getattr(entity, cls.IDENTIFIER),
             "label": getattr(entity, cls.IDENTIFIER)} for entity in entities]
        try:
            return JSONResponse(status_code=status.HTTP_200_OK, content=data)
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    @classmethod
    def parse_filters(cls, filters_dict: dict) -> List[dict]:
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
            filters.append({
                "attribute": cls.IDENTIFIER,
                "value": filters_dict["search"],
                "condition": "icontains"
            })
        else:
            # the filters_dict is int this format
            # {"attribute":value ,"attribute":value}
            for attribute, value in filters_dict.items():
                filters.append({
                    "attribute": attribute,
                    "value": value,
                    "condition": "eq"
                })
        return filters
