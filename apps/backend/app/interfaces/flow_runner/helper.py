class FlowRunnerCrudHelper:
    ADAPTOR_CLASS = None
    USE_CASE_INSTANCE = None

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
                return result.to_dict()
        except Exception as e:
            raise Exception(f"Error creating entity: {str(e)}")

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
                return result.to_dict()
            else:
                raise ValueError(f"Entity with ID {id} not found")
        except Exception as e:
            raise Exception(f"Error updating entity: {str(e)}")

    @classmethod
    def get_all(cls):
        """
        Retrieve all entities from the data source as a list of dictionaries.
        Without Pagination
        @return "items": [{...}, {...}],
        """
        try:
            result = cls.USE_CASE_INSTANCE.filter()
            return [entity.to_dict() for entity in result]
        except Exception as e:
            raise Exception(f"Error retrieving entities: {str(e)}")
