from adapters.tree import TreeAdaptor
from core.entities.tree import Tree as TreeEntity
from infrastructure.database.tables.tree import Tree
from infrastructure.repositories.base import BaseDBRepo


class TreeDBRepository(BaseDBRepo):
    """
    TreeDBRepository is a Class that Inherits from the Abstract Class BaseDBRepo
    """

    MODEL = Tree
    ENTITY = TreeEntity
    ADAPTOR = TreeAdaptor
    TENANT_SCOPE = ("via_zone",)
