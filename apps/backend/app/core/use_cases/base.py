class BaseUseCase:
    ENTITY = None

    def __init__(self, repo):
        """
        Initialize the use case with a repository.

        @param repo: Repository instance handling data operations.
        """
        self.repo = repo

    def create(self, entity: ENTITY):
        """
        Create an entity using the repository.

        @param entity: Entity instance to be created.
        @return: The created entity.
        """
        return self.repo.create(entity)

    def get(self, id: int):
        """
        Retrieve an entity by its ID using the repository.

        @param id: ID of the entity to retrieve.
        @return: The retrieved entity.
        """
        return self.repo.get(id)

    def delete(self, id: int):
        """
         Delete an entity by its ID using the repository.

         @param id: ID of the entity to delete.
         @return: Boolean indicating success of the deletion.
         """
        return self.repo.delete(id)

    def update(self, id: int, data: dict):
        """
        Update an entity by ID using the repository.

        @param id: ID of the entity to update.
        @param data: Dictionary of data to update.
        @return: The updated entity.
        """
        return self.repo.update(id, data)

    def filter(self, filters=[], order_by="created_date", order_direction="asc"):
        """
        Filter entities based on specified criteria and order the results.

        @param filters: List of dictionaries specifying the filters. Each dictionary should contain:
                        'attribute' - the field name in the entity,
                        'value' - the value to match,
                        'condition' - the condition to apply (eq, ne, gt, lt, gte, lte, in, like, ilike).
        @param order_by: The attribute by which to order the results. Default is "created_date".
        @param order_direction: The direction to order the results ('asc' or 'desc').
        @return: List of filtered entities.
        """
        return self.repo.filter(filters, order_by, order_direction)
