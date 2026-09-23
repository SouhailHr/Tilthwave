import logging

from common.dates import utc_now
from core.entities.farm import Farm as FarmEntity
from core.use_cases.base import BaseUseCase

logger = logging.getLogger(__name__)


class FarmUseCase(BaseUseCase):
    ENTITY = FarmEntity
    MONTH_NAMES = (
        "January",
        "February",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December",
    )

    def __init__(self, repo, zone_repo, water_switcher_repo, water_source_repo, tree_repo, sensor_record_repo):
        """The farm's stats are counts and one aggregate over the tables that name it or its zones."""
        super().__init__(repo)
        self.zone_repo = zone_repo
        self.tree_repo = tree_repo
        self.water_switcher_repo = water_switcher_repo
        self.water_source_repo = water_source_repo
        self.sensor_record_repo = sensor_record_repo
        self._past_months: dict[tuple, tuple[int, dict[int, float]]] = {}

    def get_all_zones(self, farm_name: str):
        """
         Get total zones in the farm
        @param farm_name:
        @return: List of zones that belongs to the farm
        """

        filter_by = [{"attribute": "farm_name", "value": farm_name, "condition": "eq"}]

        return self.zone_repo.filter(filters=filter_by)

    def get_total_water_sources(self, farm_name: str):
        """
         The farm's water sources
        @param farm_name:
        @return: list of WaterSource entities
        """

        filter_by = [{"attribute": "farm_name", "value": farm_name, "condition": "eq"}]

        return self.water_source_repo.filter(filters=filter_by)

    def _zone_names(self, farm_name: str) -> list[str]:
        return [zone.zone_name for zone in self.get_all_zones(farm_name=farm_name)]

    def _consumption_by_month(self, farm_name: str, serials: list[str]) -> dict[int, float]:
        """
        This year's consumption per month. Past months never change, so they are computed once
        per process and only the current month is re-summed on each call; the dashboard polls
        this every 30 seconds per open tab, and a year of readings is millions of rows.
        """
        now = utc_now()
        key = (farm_name, now.year, tuple(serials))
        cached = self._past_months.get(key)
        if cached is None or cached[0] != now.month - 1:
            full = self.sensor_record_repo.monthly_consumption(serials, now.year)
            self._past_months[key] = (now.month - 1, {m: v for m, v in full.items() if m < now.month})
            return full
        current = self.sensor_record_repo.monthly_consumption(serials, now.year, from_month=now.month)
        return {**cached[1], **current}

    def get_stats(self, name: str):
        """
        this method gets the farm stats
        @param name:the name of the farm
        @return: dict that contains the farm stats
        eg : {
            "total_zones": 8,
            "total_trees": 123,
            "total_water_sources": 3,
            # data for the chart for Water Consumption
            "chart_data": {
                "January": {"Total": 2000}, water consumption per liters
                "February": {"Total": 3000},
                "March": {"Total": 1500},
                "April": {"Total": 4000},
                "May": {"Total": 1700},
                "June": {"Total": 1800},
                "July": {"Total": 2200},
                "August": {"Total": 2500},
                "September": {"Total": 2700},
                "October": {"Total": 1000},
                "November": {"Total": 12000},
                "December": {"Total": 1700}
            }
        }
        """
        zones = self._zone_names(name)
        in_zones = [{"attribute": "zone_name", "value": zones, "condition": "in"}]
        sources = self.get_total_water_sources(farm_name=name)
        serials = [source.sensor_serial_number for source in sources if source.sensor_serial_number]
        monthly = self._consumption_by_month(name, serials)
        farm_stats: dict = {
            "total_zones": len(zones),
            "total_water_sources": len(sources),
            "total_water_switchers": self.water_switcher_repo.count(in_zones) if zones else 0,
            "total_trees": self.tree_repo.count(in_zones) if zones else 0,
            "chart_data": {name_: {"Total": monthly.get(m, 0)} for m, name_ in enumerate(self.MONTH_NAMES, start=1)},
        }

        return farm_stats
