from fastapi import APIRouter

from wiring import api_use_cases

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])
use_cases = api_use_cases()


@router.get("/summary/")
def summary():
    """
    Everything the home page shows, in one round trip: counts computed in the database and scoped
    to the caller's farm, the most recent irrigation tasks, and the farm's stats.
    """
    return use_cases.dashboard.summary()
