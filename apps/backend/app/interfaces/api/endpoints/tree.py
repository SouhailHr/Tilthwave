from adapters.tree import TreeAdaptor
from interfaces.api.endpoints.base import BaseCrud, crud_router
from interfaces.api.schemas.tree import TreeCreate, TreeUpdate
from wiring import api_use_cases

use_cases = api_use_cases()


class TreeCrudHelper(BaseCrud):
    ADAPTOR_CLASS = TreeAdaptor
    USE_CASE_INSTANCE = use_cases.tree
    IDENTIFIER = "serial_number"


router = crud_router("/trees", "Trees", TreeCrudHelper, TreeCreate, TreeUpdate, noun="tree")
