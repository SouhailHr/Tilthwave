import logging

from common.dates import utc_now
from core.entities.farm import Farm as FarmEntity
from core.use_cases.base import BaseUseCase
from core.use_cases.water_source import WaterSourceUseCase
from core.use_cases.zone import ZoneUseCase

logger = logging.getLogger(__name__)


class FarmUseCase(BaseUseCase):
    ENTITY = FarmEntity

    def __init__(self, repo, zone_repo, water_switcher_repo, water_source_repo, tree_repo, sensor_record_repo):
        """
        Initialize the use case with a repository.
        we are passing sensor_repo to handle validation
        of the sensor_type

        @param repo: Repository instance handling data operations.
        @param sensor_repo: Repository instance handling data operations for sensor entity

        """
        super().__init__(repo)
        self.zone_repo = zone_repo
        self.tree_repo = tree_repo
        self.water_switcher_repo = water_switcher_repo
        self.water_source_repo = water_source_repo
        self.sensor_record_repo = sensor_record_repo
        self.zone_use_case = ZoneUseCase(
            repo=self.zone_repo,
            sensor_repo=None,
            irrigation_task_repo=None,
            sensor_record_repo=None,
            water_source_repo=None,
            water_switcher_repo=self.water_switcher_repo,
            zone_sensors_repo=None,
            tree_repo=tree_repo,
        )
        self.water_source_use_case = WaterSourceUseCase(
            repo=self.water_source_repo, sensor_repo=None, sensor_record_repo=sensor_record_repo, broker_repo=None
        )

    def get_all_zones(self, farm_name: str):
        """
         Get total zones in the farm
        @param farm_name:
        @return: List of zones that belongs to the farm
        """

        filter_by = [{"attribute": "farm_name", "value": farm_name, "condition": "eq"}]

        zones = self.zone_use_case.filter(filters=filter_by)
        return zones

    def get_total_water_sources(self, farm_name: str):
        """
         Get total water sources in the farm
        @param farm_name:
        @return: int number of zones in the farm
        """

        filter_by = [{"attribute": "farm_name", "value": farm_name, "condition": "eq"}]

        water_sources = self.water_source_use_case.filter(filter_by)

        return water_sources

    def _zone_names(self, farm_name: str) -> list[str]:
        return [zone.zone_name for zone in self.get_all_zones(farm_name=farm_name)]

    def get_total_water_switchers(self, farm_name: str):
        """
         Number of water switchers in the farm: one count over the farm's zones, not one query per zone.
        @param farm_name:
        @return: int number of water switchers in the farm
        """
        zones = self._zone_names(farm_name)
        if not zones:
            return 0
        return self.water_switcher_repo.count([{"attribute": "zone_name", "value": zones, "condition": "in"}])

    def get_total_trees(self, farm_name: str):
        """
         Number of trees in the farm: one count over the farm's zones.
        @param farm_name:
        @return: int number of trees in the farm
        """
        zones = self._zone_names(farm_name)
        if not zones:
            return 0
        return self.tree_repo.count([{"attribute": "zone_name", "value": zones, "condition": "in"}])

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

    def get_total_water_consumption_by_month(self, farm_name: str):
        """
        Total water consumption of the farm's water sources this year, per month, as the chart
        wants it: {"January": {"Total": 2000}, ...}. One aggregate query over every source
        sensor of the farm (see SensorRecordDBRepository.monthly_consumption); this used to load
        every record of every source into Python.
        @param farm_name: Name of the farm.
        """
        serials = [
            source.sensor_serial_number
            for source in self.get_total_water_sources(farm_name=farm_name)
            if source.sensor_serial_number
        ]
        monthly = self.sensor_record_repo.monthly_consumption(serials, utc_now().year)
        return {name: {"Total": monthly.get(month, 0)} for month, name in enumerate(self.MONTH_NAMES, start=1)}

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
        monthly = self.sensor_record_repo.monthly_consumption(serials, utc_now().year)
        farm_stats: dict = {
            "total_zones": len(zones),
            "total_water_sources": len(sources),
            "total_water_switchers": self.water_switcher_repo.count(in_zones) if zones else 0,
            "total_trees": self.tree_repo.count(in_zones) if zones else 0,
            "chart_data": {name_: {"Total": monthly.get(m, 0)} for m, name_ in enumerate(self.MONTH_NAMES, start=1)},
        }

        return farm_stats
