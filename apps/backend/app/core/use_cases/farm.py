import logging

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

    def get_total_water_switchers(self, farm_name: str):
        """
         Get total water switchers in the farm
         1- get all farm zones
         2 - for each zone get all water switcher and add them to the total
        @param farm_name:
        @return: int number of water switchers in the farm
        """
        farm_water_switchers_count = 0
        zones = self.get_all_zones(farm_name=farm_name)
        for zone in zones:
            nb_water_switchers = len(self.zone_use_case.get_zone_water_switchers(zone_name=zone.zone_name))
            farm_water_switchers_count += nb_water_switchers
        return farm_water_switchers_count

    def get_total_trees(self, farm_name: str):
        """
         Get total trees in the farm
        @param farm_name:
        @return: int number of trees in the farm
        """

        farm_trees_count = 0
        zones = self.get_all_zones(farm_name=farm_name)
        for zone in zones:
            nb_trees = len(self.zone_use_case.get_zone_trees(zone_name=zone.zone_name))
            farm_trees_count += nb_trees
        return farm_trees_count

    def get_total_water_consumption_by_month(self, farm_name: str):
        """
        Get total water consumption from all water sources for this year by month.

        Logic:
        1. Get all farm water sources.
        2. Get consumption for each water source by month and add it to total consumption for that month.
        3. Add the total consumption for the month to the dict result of all year.

        @param farm_name: Name of the farm.
        @return: Dictionary with total water consumption per month.
        """
        # Initialize dictionary for the result
        total_consumption_by_month = {month: {"Total": 0} for month in range(1, 12 + 1)}

        # Fetch all water sources for the given farm name
        farm_water_sources = self.get_total_water_sources(farm_name=farm_name)

        for water_source in farm_water_sources:
            # Get monthly consumption for the current water source
            monthly_consumption = self.water_source_use_case.get_water_consumption_for_the_year_by_month(
                sensor_serial_number=water_source.sensor_serial_number
            )

            # Aggregate consumption into the total for each month
            for month, consumption in monthly_consumption.items():
                total_consumption_by_month[month]["Total"] += consumption

        # Convert month numbers to month names
        month_names = [
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
        ]
        result = {month_names[month - 1]: total_consumption_by_month[month] for month in total_consumption_by_month}

        return result

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
        farm_stats: dict = {
            "total_zones": len(self.get_all_zones(farm_name=name)),
            "total_water_sources": len(self.get_total_water_sources(farm_name=name)),
            "total_water_switchers": self.get_total_water_switchers(farm_name=name),
            "total_trees": self.get_total_trees(farm_name=name),
            "chart_data": self.get_total_water_consumption_by_month(farm_name=name),
        }

        return farm_stats
