"""
SuperKalam Application Configuration Backward Compatibility Shim
Re-exports from configs.settings powered by pydantic-settings.
"""

from configs.settings import Settings, get_settings, settings, _BASE_DIR as PROJECT_ROOT

__all__ = ["Settings", "get_settings", "settings", "PROJECT_ROOT"]
