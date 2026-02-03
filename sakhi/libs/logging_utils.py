"""Logging configuration helpers for Sakhi."""

from __future__ import annotations

import json
import logging
import logging.handlers
import os
from datetime import datetime, timezone
from logging.config import dictConfig
from typing import Any, Dict


COLOR_ENABLED = os.getenv("SAKHI_LOG_COLOR", "")
if not COLOR_ENABLED:
    COLOR_ENABLED = "1" if os.getenv("SAKHI_ENVIRONMENT", "dev").lower() in {"local", "dev", "test"} else "0"
COLOR_ENABLED = COLOR_ENABLED == "1"

_COLOR_CODES = {
    "red": "\033[31m",
    "yellow": "\033[33m",
    "green": "\033[32m",
    "cyan": "\033[36m",
    "magenta": "\033[35m",
}


def colorize(text: str, color: str = "red") -> str:
    if not COLOR_ENABLED:
        return text
    prefix = _COLOR_CODES.get(color, "")
    suffix = "\033[0m" if prefix else ""
    return f"{prefix}{text}{suffix}"


class JsonFormatter(logging.Formatter):
    """Minimal JSON formatter that respects extra fields."""

    def format(self, record: logging.LogRecord) -> str:
        payload: Dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key in {"msg", "args", "levelname", "levelno", "pathname", "filename", "module",
                       "exc_info", "exc_text", "stack_info", "lineno", "funcName", "created",
                       "msecs", "relativeCreated", "thread", "threadName", "processName", "process"}:
                continue
            payload[key] = value
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        # Use default=str so UUID/Decimal/datetime-like extras don't break logging.
        return json.dumps(payload, ensure_ascii=False, default=str)


class ColorTextFormatter(logging.Formatter):
    """Formatter that colorizes log output for human-friendly console viewing."""

    def format(self, record: logging.LogRecord) -> str:
        formatted = super().format(record)
        if record.levelno >= logging.ERROR:
            return colorize(formatted, "red")
        if record.levelno >= logging.WARNING:
            return colorize(formatted, "yellow")
        return formatted


def configure_logging() -> None:
    """Configure global logging from environment."""

    environment = os.getenv("SAKHI_ENVIRONMENT", "dev").lower()
    default_level = "DEBUG" if environment in {"local", "dev", "test"} else "INFO"
    log_level = os.getenv("SAKHI_LOG_LEVEL", default_level).upper()
    log_format = os.getenv("SAKHI_LOG_FORMAT", "json").lower()

    formatter_name = "json" if log_format == "json" else "text"

    # File logging configuration
    log_file = os.getenv("SAKHI_LOG_FILE", "")
    if not log_file and environment in {"local", "dev", "test"}:
        # Default to logs/api.log in dev mode
        log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, "api.log")

    handlers_config: Dict[str, Any] = {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": formatter_name,
            "level": log_level,
        }
    }

    root_handlers = ["console"]

    if log_file:
        handlers_config["file"] = {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": log_file,
            "formatter": "text",  # Use text format for file (easier to read)
            "level": log_level,
            "maxBytes": 10 * 1024 * 1024,  # 10 MB
            "backupCount": 3,
        }
        root_handlers.append("file")

    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "json": {
                    "()": JsonFormatter,
                },
                "text": {
                    "()": ColorTextFormatter,
                    "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                },
            },
            "handlers": handlers_config,
            "root": {
                "handlers": root_handlers,
                "level": log_level,
            },
        }
    )

    if log_file:
        logging.getLogger().info(f"Logging to file: {log_file}")
