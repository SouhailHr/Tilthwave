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

    def _sensors(self) -> dict:
        counts = self.sensor_repo.count_by("is_active")
        active, inactive = counts.get(True, 0), counts.get(False, 0)
        # is_active is NOT NULL, so unknown is 0 today; kept so the buckets always add up to the total.
        return {"total": sum(counts.values()), "active": active, "inactive": inactive, "unknown": counts.get(None, 0)}

    @staticmethod
    def _by_status(repo, statuses) -> dict:
        """One GROUP BY per table instead of one COUNT per status value."""
        counts = repo.count_by("status")
        return {"total": sum(counts.values()), **{s: counts.get(s, 0) for s in statuses}}

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
