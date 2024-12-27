"""
Configuration Package

This package contains configuration-related classes and utilities that manage
application settings, styles, and environment variables.

Available Configurations:
- AppConfig: Core application configuration
- AIStyleManager: Manages AI response styling and formatting
"""

from config.app_config import AppConfig
from config.ai_style_manager import AIStyleManager

__all__ = [
    'AppConfig',
    'AIStyleManager'
]