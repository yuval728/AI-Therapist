from loguru import logger
import sys
from typing import Any, Dict

CONFIGURED = False

def configure_logging():
    global CONFIGURED
    if CONFIGURED:
        return
    logger.remove()
    logger.add(sys.stdout, serialize=True, backtrace=True, diagnose=False)
    CONFIGURED = True


def log_event(event: str, **fields: Dict[str, Any]):
    logger.bind(**fields).info(event)
