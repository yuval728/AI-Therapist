"""Enhanced logging utilities with clearer console output and structured file logs.

Key improvements:
- Concise, colorized console logs with key fields (time, level, event, cid, uid, sid)
- Structured JSON logs to file for ingestion (serialize=True)
- Correlation ID support using contextvars to trace flows across layers
- Backtrace/diagnose toggles for deep debugging on demand
"""
import sys
from pathlib import Path
from typing import Any, Optional, Union
from loguru import logger
from datetime import datetime, timezone

CONFIGURED = False


def _ensure_extra_defaults(record):
    """Patcher to provide default extra fields for formatting safety."""
    extra = record.get("extra", {})
    extra.setdefault("uid", "-")
    extra.setdefault("sid", "-")


def configure_logging(
    level: str = "INFO",
    log_to_file: bool = True,
    log_dir: Optional[Union[str, Path]] = None,
    include_trace: bool = False,
) -> None:
    """Configure application logging.

    Console: human-friendly, non-JSON, colorized and concise.
    File: structured JSON for ingestion/analysis.
    """
    global CONFIGURED
    if CONFIGURED:
        return

    # Remove default handler
    logger.remove()

    # Console handler: concise and readable
    console_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> "
        "| <level>{level: <7}</level> "
        "| <bold>{message}</bold> "
        "| uid={extra[uid]} sid={extra[sid]}"
    )

    logger.add(
        sys.stdout,
        format=console_format,
        level=level.upper(),
        serialize=False,
        backtrace=include_trace,
        diagnose=include_trace,
        colorize=True,
        enqueue=True,
    )

    # File handler if requested
    if log_to_file:
        log_path = Path(log_dir or "logs") / "app.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)

        logger.add(
            str(log_path),
            # When serialize=True, format is ignored
            format="{message}",
            level=level.upper(),
            rotation="10 MB",
            retention="30 days",
            compression="gz",
            serialize=True,
            backtrace=include_trace,
            diagnose=include_trace,
            enqueue=True,
        )

    CONFIGURED = True


def log_event(
    event: str,
    level: str = "INFO",
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    **fields: Any,
) -> None:
    """Log an event with consistent fields.

    Message shown on console: the event name; key identifiers are shown inline.
    Full payload is captured in the structured file sink.
    """
    log_data = {
        "event": event,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **fields,
    }

    # Keep console line stable even if keys are missing
    safe_bind = {"uid": user_id, "sid": session_id}

    upper_level = level.upper()
    exc_obj = log_data.pop("exc", None)
    bound = logger.bind(**safe_bind, **log_data)
    if upper_level in ("ERROR", "CRITICAL") or isinstance(exc_obj, BaseException):
        bound.opt(exception=exc_obj if isinstance(exc_obj, BaseException) else True, backtrace=True).log(upper_level, event)
    else:
        bound.log(upper_level, event)


def log_therapy_event(
    event: str,
    user_id: str = None,
    session_id: str = None,
    emotion: Optional[str] = None,
    crisis_detected: bool = False,
    processing_time_ms: Optional[int] = None,
    **extra_fields: Any
) -> None:
    """Log therapy-specific events with standardized fields."""
    log_event(
        event=event,
        level="INFO",
        user_id=user_id,
        session_id=session_id,
        emotion=emotion,
        crisis_detected=crisis_detected,
        processing_time_ms=processing_time_ms,
        **extra_fields
    )


def log_security_event(
    event: str,
    attack_type: str,
    user_id: Optional[str] = None,
    content_hash: Optional[str] = None,
    severity: str = "MEDIUM",
    **extra_fields: Any
) -> None:
    """Log security-related events."""
    log_event(
        event=event,
        level="WARNING" if severity in ["HIGH", "CRITICAL"] else "INFO",
        attack_type=attack_type,
        user_id=user_id,
        content_hash=content_hash,
        severity=severity,
        **extra_fields
    )


def log_performance_metric(
    operation: str,
    duration_ms: int,
    success: bool = True,
    user_id: Optional[str] = None,
    **metadata: Any
) -> None:
    """Log performance metrics for monitoring."""
    log_event(
        event="performance_metric",
        level="DEBUG",
        operation=operation,
        duration_ms=duration_ms,
        success=success,
        user_id=user_id,
        **metadata
    )


class LogContext:
    """Context manager for adding structured logging context."""
    
    def __init__(self, **context: Any):
        self.context = context
        self.token = None
    
    def __enter__(self):
        self.token = logger.contextualize(**self.context)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.token:
            self.token.__exit__(exc_type, exc_val, exc_tb)

