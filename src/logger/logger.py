
import sys
from pathlib import Path
from threading import Lock
from datetime import datetime

from loguru import logger as loguru_logger


class Logger:
    """Thread-safe singleton wrapper around Loguru."""

    _instance = None
    _lock = Lock()
    _configured = False

    def __new__(cls, *args, **kwargs):
        # Ensure only one instance is created across the process.
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, log_level: str = "INFO"):
        # Prevent repeated configuration when Logger() is called again.
        with self._lock:
            if self._configured:
                return

            self._configure(log_level)
            self._configured = True

    def _configure(self, log_level: str) -> None:
        # Resolve the project root from this file:
        # project_root/src/logger/logger.py -> project_root
        project_root = Path(__file__).resolve().parents[2]

        # Use the date when the logger is initialized.
        now = datetime.now()
        log_date = now.strftime("%Y-%m-%d")

        # logs/YYYY/MM/YYYY-MM-DD.log
        log_dir = (
            project_root
            / "logs"
            / now.strftime("%Y")
            / now.strftime("%m")
        )
        log_dir.mkdir(parents=True, exist_ok=True)

        log_file = log_dir / f"{log_date}.log"

        # Remove Loguru's default stderr handler before configuring ours.
        loguru_logger.remove()

        # Console output
        loguru_logger.add(
            sys.stderr,
            level=log_level.upper(),
            format=(
                "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
                "<level>{level: <8}</level> | "
                "<cyan>{name}</cyan>:<cyan>{function}</cyan>:"
                "<cyan>{line}</cyan> - <level>{message}</level>"
            ),
            colorize=True,
            backtrace=True,
            diagnose=False,
        )

        # File output
        loguru_logger.add(
            str(log_file),
            level=log_level.upper(),
            format=(
                "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
                "{level: <8} | {name}:{function}:{line} - {message}"
            ),
            encoding="utf-8",
            enqueue=True,
            backtrace=True,
            diagnose=False,
            rotation=None,
            catch=True,
        )

        self._logger = loguru_logger

    @property
    def logger(self):
        """Expose the configured Loguru logger."""
        return self._logger

