import logging
import sys
from contextvars import ContextVar
from pythonjsonlogger.json import JsonFormatter
from src.config import settings

request_id_var: ContextVar[str] = ContextVar("request_id", default="-")

class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord):
        record.request_id = request_id_var.get()
        return True

def setup_logging():
    log = logging.getLogger("middleware")
    log.setLevel(settings.log_level.upper())
    log.handlers.clear()
    log.propagate = False

    handler = logging.StreamHandler(sys.stdout)
    formatter = JsonFormatter("%(asctime)s %(levelname)s %(request_id)s %(message)s")
    handler.setFormatter(formatter)
    handler.addFilter(RequestIdFilter())
    log.addHandler(handler)
    return log

logger = setup_logging()