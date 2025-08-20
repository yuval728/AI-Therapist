"""Enhanced logging utilities with structured logging support."""
import sys
import logging
import json
from pathlib import Path
from typing import Any, Dict, Optional, Union
from loguru import logger
from datetime import datetime, timezone

CONFIGURED = False


def configure_logging(
    level: str = "INFO",
    log_to_file: bool = True,
    log_dir: Optional[Union[str, Path]] = None,
    structured: bool = True,
    include_trace: bool = False
) -> None:
    """Configure application logging with enhanced options."""
    global CONFIGURED
    if CONFIGURED:
        return

    # Remove default handler
    logger.remove()

    # Console handler with formatting
    console_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level> "
        # "<yellow>{extra}</yellow>"
    )
    
    if structured:
        # When serialize=True, format is ignored; keep simple for non-structured
        console_format = "{message}"

    logger.add(
        sys.stdout,
        format=console_format,
        level=level.upper(),
        serialize=structured,
        backtrace=include_trace,
        diagnose=include_trace,
        colorize=not structured,
        enqueue=True
    )

    # File handler if requested
    if log_to_file:
        log_path = Path(log_dir or "logs") / "app.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)

        logger.add(
            str(log_path),
            format=console_format,
            level=level.upper(),
            rotation="10 MB",
            retention="30 days",
            compression="gz",
            serialize=structured,
            backtrace=include_trace,
            diagnose=include_trace,
            enqueue=True
        )

    CONFIGURED = True


def log_event(
    event: str,
    level: str = "INFO",
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    **fields: Any
) -> None:
    """Log structured event with context."""
    log_data = {
        "event": event,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **fields
    }
    
    if user_id:
        log_data["user_id"] = user_id
    if session_id:
        log_data["session_id"] = session_id
    
    # Enhanced verbosity for errors: include stack traces and exception if provided
    upper_level = level.upper()
    exc_obj = log_data.pop("exc", None)
    if upper_level in ("ERROR", "CRITICAL") or isinstance(exc_obj, BaseException):
        logger.bind(**log_data).opt(
            exception=exc_obj if isinstance(exc_obj, BaseException) else True,
            backtrace=True
        ).log(upper_level, event)
    else:
        logger.bind(**log_data).log(upper_level, event)


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
