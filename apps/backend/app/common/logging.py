"""
Process-wide logging configuration.

Every entrypoint (API, streamer, flow runner, scripts) calls configure_logging()
once; modules only ever do `logger = logging.getLogger(__name__)`.
"""

import logging

from common.request_context import RequestIdFilter

# request_id is "-" outside an API request (see common.request_context).
_FORMAT = "%(asctime)s %(levelname)-8s [%(request_id)s] %(name)s: %(message)s"

# Third-party loggers that are far too chatty at DEBUG for an application log.
_NOISY_LOGGERS = ("sqlalchemy.engine", "urllib3", "apscheduler")


def configure_logging(level: str = "INFO") -> None:
    """
    Configure the root logger from a level name (e.g. the LOG_LEVEL setting).

    @param level: logging level name; unknown names fall back to INFO.
    """
    numeric_level = logging.getLevelName(level.upper())
    if not isinstance(numeric_level, int):
        numeric_level = logging.INFO
    logging.basicConfig(level=numeric_level, format=_FORMAT, force=True)
    for handler in logging.getLogger().handlers:
        handler.addFilter(RequestIdFilter())
    for name in _NOISY_LOGGERS:
        logging.getLogger(name).setLevel(max(numeric_level, logging.WARNING))
