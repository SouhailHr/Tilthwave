from collections import defaultdict
from core.entities.irrigation_task import IrrigationTask as IrrigationTaskEntity
from core.use_cases.base import BaseUseCase
from datetime import datetime


class IrrigationTaskUseCase(BaseUseCase):
    ENTITY = IrrigationTaskEntity

    @staticmethod
    def get_task_in_progress_duration(task_in_progress):
        """
        This method calculates the duration of an irrigation task in progress duration
        @param task_in_progress: an irrigation task in progress
        @return: int value represents duration in minutes
        """
        created_date = task_in_progress.created_date
        created_date = datetime.strptime(created_date, '%Y-%m-%d %H:%M:%S.%f')

        # Calculate the duration in seconds
        duration = int((datetime.now() - created_date).total_seconds() / 60)

        return duration

    def get_all_irrigation_tasks(self):
        """
         This method gets all irrigation tasks
        @return: list of irrigation tasks
        """
        irrigation_tasks = self.filter()
        return irrigation_tasks

    def get_average_tasks_per_zone(self):
        """
        This method calculates the average number of irrigation tasks per zone
        @return: int value representing the round of average tasks per zone
        """
        irrigation_tasks = self.get_all_irrigation_tasks()
        zone_task_counts = defaultdict(int)

        # Count the number of tasks per zone
        for task in irrigation_tasks:
            zone_task_counts[task.zone_name] += 1

        if not zone_task_counts:
            return 0.0

        # Calculate the average tasks per zone
        total_tasks = sum(zone_task_counts.values())
        total_zones = len(zone_task_counts)
        average_tasks_per_zone = total_tasks / total_zones

        return round(average_tasks_per_zone)

    def get_average_tasks_per_month(self):
        """
        This method calculates the average number of irrigation tasks per month
        @return: int value representing the round of average tasks per month
        """
        irrigation_tasks = self.get_all_irrigation_tasks()
        task_counts_per_month = defaultdict(int)

        # Count the number of tasks per month
        for task in irrigation_tasks:
            task_date = datetime.strptime(task.created_date, '%Y-%m-%d %H:%M:%S.%f')
            month_key = (task_date.year, task_date.month)
            task_counts_per_month[month_key] += 1

        if not task_counts_per_month:
            return 0.0

        # Calculate the average tasks per month
        total_tasks = sum(task_counts_per_month.values())
        total_months = len(task_counts_per_month)
        average_tasks_per_month = total_tasks / total_months

        return round(average_tasks_per_month)

    def get_chart_data(self):
        """
        This method generates chart data for the irrigation tasks.
        @return: dict representing chart data
        """
        irrigation_tasks = self.get_all_irrigation_tasks()
        chart_data = defaultdict(lambda: defaultdict(int))

        # Initialize all months and zones with zero counts
        months = [
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December"
        ]
        zones = set(task.zone_name for task in irrigation_tasks)
        for month in months:
            for zone in zones:
                chart_data[month][zone] = 0

        # Count the number of tasks per month and zone
        for task in irrigation_tasks:
            task_date = datetime.strptime(task.created_date, '%Y-%m-%d %H:%M:%S.%f')
            month_name = task_date.strftime('%B')
            chart_data[month_name][task.zone_name] += 1

        return chart_data

    def get_stats(self):
        """
        This method gets the farm stats
        @return: dict with total tasks, average tasks per month, average tasks per zone, and chart data
         eg "chart_data":
         {
            "January": {"Zone A": 50, "Zone B": 40, "Zone C": 30, "Zone D": 20},
            "February": {"Zone A": 60, "Zone B": 55, "Zone C": 45, "Zone D": 35},
            "March": {"Zone A": 70, "Zone B": 65, "Zone C": 55, "Zone D": 45},
            "April": {"Zone A": 80, "Zone B": 75, "Zone C": 65, "Zone D": 55},
            "May": {"Zone A": 90, "Zone B": 85, "Zone C": 75, "Zone D": 65},
            "June": {"Zone A": 100, "Zone B": 95, "Zone C": 85, "Zone D": 75},
            "July": {"Zone A": 110, "Zone B": 105, "Zone C": 95, "Zone D": 85},
            "August": {"Zone A": 120, "Zone B": 115, "Zone C": 105, "Zone D": 95},
            "September": {"Zone A": 130, "Zone B": 125, "Zone C": 115, "Zone D": 105},
            "October": {"Zone A": 140, "Zone B": 135, "Zone C": 125, "Zone D": 115},
            "November": {"Zone A": 150, "Zone B": 145, "Zone C": 135, "Zone D": 125},
            "December": {"Zone A": 160, "Zone B": 155, "Zone C": 145, "Zone D": 135}
        }

        """
        irrigation_tasks_stats = {
            "total_tasks": len(self.get_all_irrigation_tasks()),
            "average_tasks_per_month": self.get_average_tasks_per_month(),
            "average_tasks_per_zone": self.get_average_tasks_per_zone(),
            "chart_data": self.get_chart_data()
        }
        return irrigation_tasks_stats
