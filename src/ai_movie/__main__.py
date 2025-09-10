#!/usr/bin/env python3
"""
AI Movie Generator - Package Main Entry Point

This module allows the package to be executed directly using:
    python -m ai_movie

It provides the same functionality as the CLI command.
"""

import sys
from .cli import main

if __name__ == "__main__":
    main()