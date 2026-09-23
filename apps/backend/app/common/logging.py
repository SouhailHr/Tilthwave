"""
Process-wide logging configuration.

Every entrypoint (API, streamer, flow runner, scripts) calls configure_logging() once; modules
only ever do `logger = logging.getLogger(__name__)`. Two output formats, chosen by LOG_FORMAT:
"text" for a terminal, "json" (one object per line: ts, level, logger, request_id, message,
and exc when there is a traceback) for a log shipper, where level and request_id become fields
a query can filter on instead of substrings to grep for.
"""

import json
import logging
from datetime import UTC, datetime

from common.request_context import RequestIdFilter

# request_id is "-" outside an API request (see common.request_context).
_TEXT_FORMAT = "%(asctime)s %(levelname)-8s [%(request_id)s] %(name)s: %(message)s"

# Third-party loggers that are far too chatty at DEBUG for an application log.
_NOISY_LOGGERS = ("sqlalchemy.engine", "urllib3", "apscheduler")
# uvicorn installs its own handlers (plain text, no request id) and stops propagation; adopting
# them into the root logger gives its startup and access lines the same format as everything else.
_ADOPTED_LOGGERS = ("uvicorn", "uvicorn.error", "uvicorn.access")


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        entry = {
            "ts": datetime.fromtimestamp(record.created, UTC).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "request_id": getattr(record, "request_id", "-"),
            "message": record.getMessage(),
        }
        if record.exc_info:
            entry["exc"] = self.formatException(record.exc_info)
        return json.dumps(entry, ensure_ascii=False)


def configure_logging(level: str = "INFO", log_format: str = "text") -> None:
    """
    Configure the root logger from a level name (e.g. the LOG_LEVEL setting) and a format name.

    @param level: logging level name; unknown names fall back to INFO.
    @param log_format: "json" or "text"; anything else is text.
    """
    numeric_level = logging.getLevelName(level.upper())
    if not isinstance(numeric_level, int):
        numeric_level = logging.INFO
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter() if log_format.lower() == "json" else logging.Formatter(_TEXT_FORMAT))
    handler.addFilter(RequestIdFilter())
    logging.basicConfig(level=numeric_level, handlers=[handler], force=True)
    for name in _NOISY_LOGGERS:
        logging.getLogger(name).setLevel(max(numeric_level, logging.WARNING))
    for name in _ADOPTED_LOGGERS:
        adopted = logging.getLogger(name)
        adopted.handlers.clear()
        adopted.propagate = True
