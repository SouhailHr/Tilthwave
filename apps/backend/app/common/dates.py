"""
Date helpers.

The database stores naive UTC datetimes (see TilthwaveBaseModel); entities carry them as
ISO 8601 with an explicit UTC offset (iso_utc). Every comparison with "now" must use UTC, never
the container's local time (TZ is set to the farm's timezone for logs).
"""

from datetime import UTC, datetime

COMMAND_TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M"


def utc_now() -> datetime:
    """Naive UTC now, comparable with the datetimes the database hands back."""
    return datetime.now(UTC).replace(tzinfo=None)


def iso_utc(value: datetime) -> str:
    """A naive-UTC column value as ISO 8601 with its offset: '2026-09-15T16:06:56.266864+00:00'."""
    return (value if value.tzinfo else value.replace(tzinfo=UTC)).isoformat()


def parse_db_datetime(value) -> datetime:
    """
    A datetime as the adaptors serialize it (iso_utc), or as older callers wrote it
    ('YYYY-MM-DD HH:MM:SS[.ffffff]', naive UTC), back to a naive UTC datetime comparable with
    utc_now(). An offset, when present, is honoured and then dropped.
    """
    parsed = value if isinstance(value, datetime) else datetime.fromisoformat(value)
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(UTC).replace(tzinfo=None)
    return parsed


def minutes_since(value) -> float:
    """Minutes elapsed between a stored datetime and now (UTC)."""
    return (utc_now() - parse_db_datetime(value)).total_seconds() / 60


def command_timestamp() -> str:
    """Timestamp embedded in broker commands, computed per command (never at import time)."""
    return utc_now().strftime(COMMAND_TIMESTAMP_FORMAT)
