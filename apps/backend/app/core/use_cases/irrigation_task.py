from common.dates import minutes_since
from core.entities.irrigation_task import IrrigationTask as IrrigationTaskEntity
from core.use_cases.base import BaseUseCase


class IrrigationTaskUseCase(BaseUseCase):
    ENTITY = IrrigationTaskEntity

    @staticmethod
    def get_task_in_progress_duration(task_in_progress):
        """
        Minutes an in-progress task has been running. created_date is stored in UTC, so "now" is
        taken in UTC as well (the container TZ is the farm's local time and must not leak in).
        """
        return int(minutes_since(task_in_progress.created_date))
