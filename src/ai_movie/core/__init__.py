"""
Core module for AI Movie Generator

Contains fundamental classes and utilities.
"""

from .config import Config
from .exceptions import VideoGenerationException
from .logging_config import get_logger

__all__ = [
    "Config",
    "VideoGenerationException", 
    "get_logger",
]