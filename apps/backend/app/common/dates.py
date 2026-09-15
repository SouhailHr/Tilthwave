"""
Date helpers.

The database stores naive UTC datetimes (see TilthwaveBaseModel); entities carry
them as `str(datetime)`. Every comparison with "now" must therefore use UTC,
never the container's local time (TZ is set to the farm's timezone for logs).
"""

from datetime import UTC, datetime

COMMAND_TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M"


def utc_now() -> datetime:
    """Naive UTC now, comparable with the datetimes the database hands back."""
    return datetime.now(UTC).replace(tzinfo=None)


def parse_db_datetime(value) -> datetime:
    """
    Parse a datetime as serialized by the adaptors (`str(datetime)`).

    Handles both 'YYYY-MM-DD HH:MM:SS.ffffff' and 'YYYY-MM-DD HH:MM:SS' (Python
    drops the fraction when microsecond == 0, which broke a fixed-format strptime).
    """
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(value)


def minutes_since(value) -> float:
    """Minutes elapsed between a stored datetime and now (UTC)."""
    return (utc_now() - parse_db_datetime(value)).total_seconds() / 60


def command_timestamp() -> str:
    """Timestamp embedded in broker commands, computed per command (never at import time)."""
    return utc_now().strftime(COMMAND_TIMESTAMP_FORMAT)
