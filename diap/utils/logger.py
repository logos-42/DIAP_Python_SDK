import logging
import sys
from typing import Optional
from datetime import datetime


class Logger:
    def __init__(self, name: str, level: int = logging.INFO):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)

        if not self.logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            handler.setLevel(level)
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    def debug(self, message: str, **kwargs):
        self.logger.debug(message, extra=kwargs)

    def info(self, message: str, **kwargs):
        self.logger.info(message, extra=kwargs)

    def warning(self, message: str, **kwargs):
        self.logger.warning(message, extra=kwargs)

    def error(self, message: str, **kwargs):
        self.logger.error(message, extra=kwargs)

    def critical(self, message: str, **kwargs):
        self.logger.critical(message, extra=kwargs)


_loggers = {}
_default_level = logging.INFO


def get_logger(name: str) -> Logger:
    if name not in _loggers:
        _loggers[name] = Logger(name, _default_level)
    return _loggers[name]


def set_log_level(level: int):
    global _default_level
    _default_level = level
    for logger in _loggers.values():
        logger.logger.setLevel(level)
        for handler in logger.logger.handlers:
            handler.setLevel(level)
