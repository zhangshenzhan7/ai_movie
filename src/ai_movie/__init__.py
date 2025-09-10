"""
AI Movie Generator

A powerful AI-driven video generation platform that transforms text into engaging videos.
"""

__version__ = "0.1.0"
__author__ = "AI Movie Team"
__email__ = "contact@ai-movie.com"
__description__ = "AI-powered video generation from text descriptions"

from .core.config import Config
from .core.exceptions import VideoGenerationException

__all__ = [
    "Config",
    "VideoGenerationException",
]