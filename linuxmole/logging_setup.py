#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Logging configuration for LinuxMole.
"""

from __future__ import annotations
import logging
from typing import Optional


# Logger instance
logger = logging.getLogger("linuxmole")


def setup_logging(verbose: bool = False, log_file: Optional[str] = None) -> None:
    """
    Configure logging system.

    Args:
        verbose: If True, set DEBUG level. Otherwise INFO.
        log_file: Optional path to log file. If None, only console logging.
    """
    level = logging.DEBUG if verbose else logging.INFO
    handlers = []

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter('[%(levelname)s] %(message)s'))
    handlers.append(console_handler)

    # File handler (optional)
    if log_file:
        try:
            file_handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
            file_handler.setFormatter(logging.Formatter(
                '%(asctime)s - [%(levelname)s] - %(name)s - %(message)s'
            ))
            handlers.append(file_handler)
            logger.info(f"Logging to file: {log_file}")
        except Exception as e:
            logger.warning(f"Failed to create log file {log_file}: {e}")

    # Configure root logger
    logging.basicConfig(
        level=level,
        handlers=handlers,
        force=True
    )

    logger.setLevel(level)

    if verbose:
        logger.debug("Verbose logging enabled")
