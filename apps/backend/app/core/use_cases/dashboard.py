"""
One round trip for the home page.

The dashboard used to issue seven polling queries (six paginated lists capped at 100 rows each,
plus the farm stats) and count every status breakdown client-side inside that 100-row sample,
which was silently wrong as soon as a table grew past it. Every count here is a database COUNT,
and because it goes through the repositories it is scoped to the caller's farm exactly like every
other read.
"""

from common import constants as global_constants

ACTUATOR_STATUSES = global_constants.ACTUATOR_STATUSES
IRRIGATION_TASK_STATUSES = global_constants.IRRIGATION_TASK_STATUSES


class DashboardUseCase:
    RECENT_TASKS = 6

    def __init__(
        self,
        sensor_repo,
        water_source_repo,
        water_switcher_repo,
        irrigation_task_repo,
        farm_repo,
        zone_repo,
        farm_use_case,
    ):
        self.sensor_repo = sensor_repo
        self.water_source_repo = water_source_repo
        self.water_switcher_repo = water_switcher_repo
        self.irrigation_task_repo = irrigation_task_repo
        self.farm_repo = farm_repo
        self.zone_repo = zone_repo
        self.farm_use_case = farm_use_case

    @staticmethod
    def _count_where(repo, attribute, value) -> int:
        return repo.count([{"attribute": attribute, "value": value, "condition": "eq"}])

    def _count_by(self, repo, attribute, values) -> dict:
        return {value: self._count_where(repo, attribute, value) for value in values}

    def _sensors(self) -> dict:
        total = self.sensor_repo.count([])
        active = self._count_where(self.sensor_repo, "is_active", True)
        inactive = self._count_where(self.sensor_repo, "is_active", False)
        # is_active is NOT NULL, so this is 0 today; kept so the contract stays honest if that
        # ever changes rather than the two buckets silently not adding up to the total.
        return {"total": total, "active": active, "inactive": inactive, "unknown": total - active - inactive}

    def _by_status(self, repo, statuses) -> dict:
        return {"total": repo.count([]), **self._count_by(repo, "status", statuses)}

    def _primary_farm(self) -> dict | None:
        """The caller's farm (the tenant filter leaves exactly theirs), with the same stats
        GET /farms/stats/{farm_name} returns, so the page keeps its consumption chart."""
        farms = self.farm_repo.filter([], order_by="id", order_direction="asc", limit=1)
        if not farms:
            return None
        farm = farms[0]
        return {"farm_name": farm.farm_name, **self.farm_use_case.get_stats(name=farm.farm_name)}

    def summary(self) -> dict:
        recent = self.irrigation_task_repo.filter([], order_by="id", order_direction="desc", limit=self.RECENT_TASKS)
        return {
            "sensors": self._sensors(),
            "water_sources": self._by_status(self.water_source_repo, ACTUATOR_STATUSES),
            "water_switchers": self._by_status(self.water_switcher_repo, ACTUATOR_STATUSES),
            "irrigation_tasks": self._by_status(self.irrigation_task_repo, IRRIGATION_TASK_STATUSES),
            "recent_tasks": [task.to_public_dict() for task in recent],
            "farms": {"total": self.farm_repo.count([])},
            "zones": {"total": self.zone_repo.count([])},
            "farm": self._primary_farm(),
        }
